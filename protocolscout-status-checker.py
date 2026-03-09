# ─────────────────────────────────────────────────────────────────────────────
# Lambda: protocolscout-status-checker
# Memory: 256 MB | Timeout: 30 sec
# Env Vars:
#   AUDIT_TABLE      = protocol_audit
#   DOCUMENTS_BUCKET = protocolscout-documents-[YOUR-ID]
# Trigger: API Gateway GET /protocols/{protocol_id}
# ─────────────────────────────────────────────────────────────────────────────

import json
import boto3
import os

# ── Clients ──────────────────────────────────────────────────────────────────
dynamodb    = boto3.resource("dynamodb")
s3          = boto3.client("s3")

AUDIT_TABLE = dynamodb.Table(os.environ["AUDIT_TABLE"])
BUCKET      = os.environ["DOCUMENTS_BUCKET"]


# ─────────────────────────────────────────────────────────────────────────────
# HANDLER
# ─────────────────────────────────────────────────────────────────────────────
def lambda_handler(event, context):
    """
    Returns current processing status for a protocol.

    API Gateway path: GET /protocols/{protocol_id}

    Response includes:
      - status       : uploaded | processing | ocr_complete | extraction_complete
                       | compliance_checked | completed | failed
      - compliance_score  (once completed)
      - gaps_found        (once completed)
      - report_json       (S3 path, once completed)
      - report_txt        (S3 path, once completed)
      - report_url        (pre-signed URL valid 1 hour, once completed)
    """
    try:
        # ── Extract protocol_id from path ────────────────────────────────────
        path_params = event.get("pathParameters") or {}
        protocol_id = path_params.get("protocol_id")

        if not protocol_id:
            # Fallback for direct Lambda test invocations
            protocol_id = event.get("protocol_id")

        if not protocol_id:
            return _error(400, "Missing protocol_id in path parameters.")

        print(f"Status check for: {protocol_id}")

        # ── Scan audit table for ALL records for this protocol ───────────────
        # Sorted descending so index 0 is the latest action.
        from boto3.dynamodb.conditions import Key, Attr

        resp  = AUDIT_TABLE.scan(
            FilterExpression=Attr("protocol_id").eq(protocol_id)
        )
        items = resp.get("Items", [])

        # Paginate if needed
        while "LastEvaluatedKey" in resp:
            resp  = AUDIT_TABLE.scan(
                FilterExpression=Attr("protocol_id").eq(protocol_id),
                ExclusiveStartKey=resp["LastEvaluatedKey"]
            )
            items.extend(resp.get("Items", []))

        if not items:
            return _error(404, f"Protocol '{protocol_id}' not found.")

        # Sort by timestamp descending → latest record first
        items.sort(key=lambda x: int(x.get("timestamp", 0)), reverse=True)
        latest = items[0]

        status = latest.get("status", "unknown")
        action = latest.get("action", "unknown")

        payload = {
            "protocol_id"  : protocol_id,
            "status"       : status,
            "action"       : action,
            "last_updated" : latest.get("completed_at") or latest.get("created_at"),
        }

        # Add compliance data once available
        if status == "completed":
            payload["compliance_score"] = latest.get("compliance_score")
            payload["gaps_found"]       = latest.get("gaps_found")
            payload["report_json"]      = latest.get("report_json")
            payload["report_txt"]       = latest.get("report_txt")

            # Generate pre-signed URL for the text report (valid 1 hour)
            try:
                report_key = f"reports/{protocol_id}/compliance_report.txt"
                presigned  = s3.generate_presigned_url(
                    "get_object",
                    Params     = {"Bucket": BUCKET, "Key": report_key},
                    ExpiresIn  = 3600,
                )
                payload["report_download_url"] = presigned
            except Exception as e:
                print(f"  Warning: could not generate pre-signed URL: {e}")

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type"                : "application/json",
                "Access-Control-Allow-Origin" : "*",
            },
            "body": json.dumps(payload, default=str),
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return _error(500, str(e))


# ─────────────────────────────────────────────────────────────────────────────
# HELPER
# ─────────────────────────────────────────────────────────────────────────────
def _error(code, message):
    return {
        "statusCode": code,
        "headers": {"Access-Control-Allow-Origin": "*"},
        "body": json.dumps({"error": message}),
    }