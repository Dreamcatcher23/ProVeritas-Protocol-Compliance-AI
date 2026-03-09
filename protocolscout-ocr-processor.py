# ─────────────────────────────────────────────────────────────────────────────
# Lambda: protocolscout-ocr-processor
# Memory: 1024 MB | Timeout: 15 min
# Env Vars:
#   DOCUMENTS_BUCKET = protocolscout-documents-[YOUR-ID]
# Triggered by: upload-handler (async Lambda invoke)
# ─────────────────────────────────────────────────────────────────────────────

import json
import boto3
import time
import os
from datetime import datetime

# ── Clients ──────────────────────────────────────────────────────────────────
textract      = boto3.client("textract")
s3            = boto3.client("s3")
lambda_client = boto3.client("lambda")

BUCKET = os.environ["DOCUMENTS_BUCKET"]


# ─────────────────────────────────────────────────────────────────────────────
# TEXTRACT: start + full paginated poll
# ─────────────────────────────────────────────────────────────────────────────
def run_textract(s3_key):
    """
    Start Textract document analysis (TEXT + TABLES + FORMS),
    poll until complete, paginate ALL result pages.

    Returns dict:
        text     – full plain-text (all lines joined)
        tables   – raw TABLE blocks
        forms    – raw KEY_VALUE_SET blocks
        pages    – number of result pages consumed
        job_id   – Textract Job ID
    """
    print(f"Starting Textract on s3://{BUCKET}/{s3_key}")

    resp   = textract.start_document_analysis(
        DocumentLocation = {"S3Object": {"Bucket": BUCKET, "Name": s3_key}},
        FeatureTypes     = ["TABLES", "FORMS"],
    )
    job_id = resp["JobId"]
    print(f"Textract Job ID: {job_id}")

    # ── Poll until SUCCEEDED / FAILED ────────────────────────────────────────
    for attempt in range(180):          # max 15 min (180 × 5 s)
        result = textract.get_document_analysis(JobId=job_id)
        status = result["JobStatus"]
        print(f"  Textract status={status} (attempt {attempt + 1})")

        if status == "SUCCEEDED":
            break
        if status == "FAILED":
            raise RuntimeError(f"Textract job failed: {result.get('StatusMessage')}")

        time.sleep(5)
    else:
        raise RuntimeError("Textract polling timed out after 15 minutes.")

    # ── Collect ALL pages via NextToken ───────────────────────────────────────
    all_blocks  = []
    page_count  = 0
    next_token  = None

    while True:
        if next_token:
            result = textract.get_document_analysis(JobId=job_id, NextToken=next_token)

        for block in result["Blocks"]:
            all_blocks.append(block)

        page_count += 1
        next_token  = result.get("NextToken")
        if not next_token:
            break

    print(f"  Textract: {len(all_blocks)} blocks across {page_count} result pages.")

    # ── Separate block types ──────────────────────────────────────────────────
    text_lines = []
    tables     = []
    forms      = []

    for block in all_blocks:
        bt = block["BlockType"]
        if bt == "LINE":
            text_lines.append(block.get("Text", ""))
        elif bt == "TABLE":
            tables.append(block)
        elif bt == "KEY_VALUE_SET":
            forms.append(block)

    return {
        "text"   : "\n".join(text_lines),
        "tables" : tables,
        "forms"  : forms,
        "pages"  : page_count,
        "job_id" : job_id,
        "lines"  : len(text_lines),
    }


# ─────────────────────────────────────────────────────────────────────────────
# SAVE to S3
# ─────────────────────────────────────────────────────────────────────────────
def save_to_s3(protocol_id, ocr_result):
    """Persist text, tables, forms JSON to S3 under extracted/{protocol_id}/"""
    ts = datetime.utcnow().isoformat()

    s3.put_object(
        Bucket      = BUCKET,
        Key         = f"extracted/{protocol_id}/text.json",
        Body        = json.dumps({
            "protocol_id"    : protocol_id,
            "text"           : ocr_result["text"],
            "line_count"     : ocr_result["lines"],
            "result_pages"   : ocr_result["pages"],
            "textract_job_id": ocr_result["job_id"],
            "extracted_at"   : ts,
        }, ensure_ascii=False).encode("utf-8"),
        ContentType = "application/json",
    )

    s3.put_object(
        Bucket      = BUCKET,
        Key         = f"extracted/{protocol_id}/tables.json",
        Body        = json.dumps({
            "protocol_id": protocol_id,
            "tables"     : ocr_result["tables"],
            "count"      : len(ocr_result["tables"]),
        }).encode("utf-8"),
        ContentType = "application/json",
    )

    s3.put_object(
        Bucket      = BUCKET,
        Key         = f"extracted/{protocol_id}/forms.json",
        Body        = json.dumps({
            "protocol_id": protocol_id,
            "forms"      : ocr_result["forms"],
            "count"      : len(ocr_result["forms"]),
        }).encode("utf-8"),
        ContentType = "application/json",
    )

    print(f"  Saved text/tables/forms to S3 under extracted/{protocol_id}/")


# ─────────────────────────────────────────────────────────────────────────────
# HANDLER
# ─────────────────────────────────────────────────────────────────────────────
def lambda_handler(event, context):
    """
    Steps:
      1. Run Textract (full pagination – ALL pages)
      2. Save extracted text / tables / forms to S3
      3. Trigger entity extractor Lambda (async)
    """
    try:
        protocol_id = event["protocol_id"]
        s3_key      = event["s3_key"]

        print(f"\n{'='*60}")
        print(f"OCR Processor  |  protocol_id={protocol_id}")
        print(f"{'='*60}")

        # ── OCR ──────────────────────────────────────────────────────────────
        ocr_result = run_textract(s3_key)
        print(f"  Lines extracted : {ocr_result['lines']:,}")
        print(f"  Tables found    : {len(ocr_result['tables'])}")
        print(f"  Form fields     : {len(ocr_result['forms'])}")

        # ── Persist ──────────────────────────────────────────────────────────
        save_to_s3(protocol_id, ocr_result)

        # ── Trigger next stage ───────────────────────────────────────────────
        lambda_client.invoke(
            FunctionName   = "protocolscout-entity-extractor",
            InvocationType = "Event",
            Payload        = json.dumps({
                "protocol_id" : protocol_id,
                "bucket"      : BUCKET,
            }),
        )
        print("  Entity extractor triggered (async).")

        return {
            "statusCode": 200,
            "body": json.dumps({
                "protocol_id"   : protocol_id,
                "status"        : "ocr_complete",
                "lines_extracted": ocr_result["lines"],
                "tables_found"  : len(ocr_result["tables"]),
            }),
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise      # Let Lambda log the error; retries can happen if needed