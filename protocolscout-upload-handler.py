# ─────────────────────────────────────────────────────────────────────────────
# Lambda: protocolscout-upload-handler
# Memory: 512 MB | Timeout: 5 min
# Env Vars:
#   DOCUMENTS_BUCKET = protocolscout-documents-[YOUR-ID]
#   AUDIT_TABLE      = protocol_audit
#   REGION           = ap-south-1
# Trigger: API Gateway POST /protocols
# ─────────────────────────────────────────────────────────────────────────────

import json
import boto3
import base64
import hashlib
import uuid
import os
from datetime import datetime

# ── Clients ──────────────────────────────────────────────────────────────────
s3             = boto3.client("s3")
dynamodb       = boto3.resource("dynamodb")
lambda_client  = boto3.client("lambda")

# ── Config from env vars ─────────────────────────────────────────────────────
BUCKET      = os.environ["DOCUMENTS_BUCKET"]
AUDIT_TABLE = dynamodb.Table(os.environ["AUDIT_TABLE"])


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _create_audit_record(protocol_id, metadata, doc_hash, s3_key, file_size):
    """Write the initial audit record to DynamoDB."""
    AUDIT_TABLE.put_item(
        Item={
            "protocol_id"     : protocol_id,
            "timestamp"       : int(datetime.utcnow().timestamp()),
            "user_id"         : metadata.get("user_id", "unknown"),
            "institution"     : metadata.get("institution", "unknown"),
            "action"          : "uploaded",
            "status"          : "processing",
            "document_hash"   : doc_hash,
            "s3_location"     : f"s3://{BUCKET}/{s3_key}",
            "file_size_bytes" : file_size,
            "created_at"      : datetime.utcnow().isoformat(),
        }
    )


def _trigger_ocr(protocol_id, s3_key):
    """Fire-and-forget invocation of the OCR processor Lambda."""
    lambda_client.invoke(
        FunctionName   = "protocolscout-ocr-processor",
        InvocationType = "Event",          # async – no wait
        Payload        = json.dumps({
            "protocol_id" : protocol_id,
            "bucket"      : BUCKET,
            "s3_key"      : s3_key,
        }),
    )


# ─────────────────────────────────────────────────────────────────────────────
# HANDLER
# ─────────────────────────────────────────────────────────────────────────────
def lambda_handler(event, context):
    """
    Receives a JSON body from API Gateway:
      {
        "file"     : "<base64-encoded PDF>",
        "metadata" : { "user_id": "...", "institution": "..." }
      }

    Steps:
      1. Decode PDF bytes
      2. Generate unique protocol_id
      3. Upload PDF to S3
      4. Write audit record to DynamoDB
      5. Trigger OCR processor asynchronously
      6. Return protocol_id + status to caller
    """
    try:
        # ── Parse body ───────────────────────────────────────────────────────
        if "body" in event:
            body = json.loads(event["body"]) if isinstance(event["body"], str) else event["body"]
        else:
            body = event

        if "file" not in body:
            return {
                "statusCode": 400,
                "headers": {"Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"error": "Missing 'file' field (base64-encoded PDF required)"}),
            }

        # Strip whitespace and fix padding (handles PowerShell/copy-paste artifacts)
        b64_string = body["file"].strip().replace(" ", "+")
        b64_string += "=" * (-len(b64_string) % 4)
        file_bytes = base64.b64decode(b64_string)
        metadata   = body.get("metadata", {})

        # ── Generate IDs ─────────────────────────────────────────────────────
        protocol_id = f"PROTO-{int(datetime.utcnow().timestamp())}-{uuid.uuid4().hex[:8].upper()}"
        doc_hash    = hashlib.sha256(file_bytes).hexdigest()

        print(f"protocol_id   : {protocol_id}")
        print(f"file_size     : {len(file_bytes):,} bytes")
        print(f"doc_hash      : {doc_hash[:16]}…")
        print(f"user_id       : {metadata.get('user_id', 'unknown')}")

        # ── Upload PDF to S3 ─────────────────────────────────────────────────
        s3_key = f"uploads/{protocol_id}/original.pdf"
        s3.put_object(
            Bucket                 = BUCKET,
            Key                    = s3_key,
            Body                   = file_bytes,
            ContentType            = "application/pdf",
            ServerSideEncryption   = "aws:kms",
            Metadata               = {
                "protocol-id"  : protocol_id,
                "user-id"      : metadata.get("user_id", "unknown"),
                "institution"  : metadata.get("institution", "unknown"),
                "uploaded-at"  : datetime.utcnow().isoformat(),
            },
        )
        print(f"Uploaded → s3://{BUCKET}/{s3_key}")

        # ── Audit record ─────────────────────────────────────────────────────
        _create_audit_record(protocol_id, metadata, doc_hash, s3_key, len(file_bytes))
        print("Audit record created.")

        # ── Kick off OCR ─────────────────────────────────────────────────────
        _trigger_ocr(protocol_id, s3_key)
        print("OCR processor triggered (async).")

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type"                 : "application/json",
                "Access-Control-Allow-Origin"  : "*",
            },
            "body": json.dumps({
                "protocol_id"          : protocol_id,
                "status"               : "processing",
                "message"              : "Protocol received. Processing started.",
                "estimated_completion" : "5-8 minutes",
                "check_status_url"     : f"/protocols/{protocol_id}",
            }),
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "statusCode": 500,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": str(e), "message": "Upload failed."}),
        }