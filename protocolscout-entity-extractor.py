# ─────────────────────────────────────────────────────────────────────────────
# Lambda: protocolscout-entity-extractor
# Memory: 1024 MB | Timeout: 10 min
# Env Vars:
#   DOCUMENTS_BUCKET = protocolscout-documents-[YOUR-ID]
# Triggered by: ocr-processor (async Lambda invoke)
# ─────────────────────────────────────────────────────────────────────────────

import json
import boto3
import re
import os
from datetime import datetime

# ── Clients ──────────────────────────────────────────────────────────────────
comprehend_medical = boto3.client("comprehendmedical")
s3                 = boto3.client("s3")
lambda_client      = boto3.client("lambda")

BUCKET             = os.environ["DOCUMENTS_BUCKET"]

# Comprehend Medical hard limit: 20 000 UTF-8 bytes per call
CM_CHUNK_BYTES = 19_000


# ─────────────────────────────────────────────────────────────────────────────
# COMPREHEND MEDICAL  –  chunked entity extraction
# ─────────────────────────────────────────────────────────────────────────────
def chunk_text_for_comprehend(text):
    """Split text into chunks that fit within CM's 20 000-byte limit."""
    chunks        = []
    current_chunk = []
    current_bytes = 0

    for line in text.split("\n"):
        line_bytes = len(line.encode("utf-8")) + 1   # +1 for the newline
        if current_bytes + line_bytes > CM_CHUNK_BYTES and current_chunk:
            chunks.append("\n".join(current_chunk))
            current_chunk = []
            current_bytes = 0
        current_chunk.append(line)
        current_bytes += line_bytes

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks


def extract_medical_entities(text):
    """Run Comprehend Medical on all chunks; return combined entity list."""
    chunks      = chunk_text_for_comprehend(text)
    all_entities = []

    print(f"  Running Comprehend Medical on {len(chunks)} chunk(s)…")

    for idx, chunk in enumerate(chunks):
        try:
            resp = comprehend_medical.detect_entities_v2(Text=chunk)
            entities = resp.get("Entities", [])
            # Tag each entity with chunk index for traceability
            for e in entities:
                e["chunk_index"] = idx
            all_entities.extend(entities)
            print(f"    Chunk {idx + 1}/{len(chunks)} → {len(entities)} entities")
        except Exception as e:
            print(f"    Chunk {idx + 1} CM error: {e} – skipping.")

    print(f"  Total entities extracted: {len(all_entities)}")
    return all_entities


# ─────────────────────────────────────────────────────────────────────────────
# ELIGIBILITY CRITERIA
# ─────────────────────────────────────────────────────────────────────────────
def extract_eligibility_criteria(text):
    """
    Use regex to pull inclusion / exclusion criteria blocks.
    Returns: { "inclusion": [...], "exclusion": [...] }
    """
    criteria = {"inclusion": [], "exclusion": []}

    # Inclusion block
    inc_match = re.search(
        r"inclusion\s+criteria[:\s]*(.*?)(?=exclusion\s+criteria|$)",
        text, re.IGNORECASE | re.DOTALL
    )
    if inc_match:
        block = inc_match.group(1)
        criteria["inclusion"] = [
            item.strip()
            for item in re.split(r"[\n\r]+|\d+\.\s+|\•\s+|\-\s+", block)
            if len(item.strip()) > 10
        ][:30]     # cap at 30 items

    # Exclusion block
    exc_match = re.search(
        r"exclusion\s+criteria[:\s]*(.*?)(?=study\s+procedures|objectives|endpoints|$)",
        text, re.IGNORECASE | re.DOTALL
    )
    if exc_match:
        block = exc_match.group(1)
        criteria["exclusion"] = [
            item.strip()
            for item in re.split(r"[\n\r]+|\d+\.\s+|\•\s+|\-\s+", block)
            if len(item.strip()) > 10
        ][:30]

    print(f"  Inclusion criteria : {len(criteria['inclusion'])}")
    print(f"  Exclusion criteria : {len(criteria['exclusion'])}")
    return criteria


# ─────────────────────────────────────────────────────────────────────────────
# TIMELINE OBLIGATIONS
# ─────────────────────────────────────────────────────────────────────────────
def extract_timelines(text):
    """
    Find all "within N hours/days/weeks" regulatory timeline obligations.
    Returns list of dicts with duration, unit, and surrounding context.
    """
    pattern = re.compile(
        r"within\s+(\d+)\s+(hour|day|week|month)s?",
        re.IGNORECASE
    )
    timelines = []

    for match in pattern.finditer(text):
        start   = max(0, match.start() - 120)
        end     = min(len(text), match.end() + 120)
        context = text[start:end].replace("\n", " ").strip()
        timelines.append({
            "duration" : match.group(1),
            "unit"     : match.group(2).lower(),
            "context"  : context,
        })

    # Deduplicate by context
    seen      = set()
    unique_tl = []
    for tl in timelines:
        key = tl["context"][:80]
        if key not in seen:
            seen.add(key)
            unique_tl.append(tl)

    print(f"  Timeline obligations found: {len(unique_tl)}")
    return unique_tl


# ─────────────────────────────────────────────────────────────────────────────
# SAVE STRUCTURED DATA
# ─────────────────────────────────────────────────────────────────────────────
def save_structured(protocol_id, entities, eligibility, timelines):
    ts = datetime.utcnow().isoformat()

    s3.put_object(
        Bucket      = BUCKET,
        Key         = f"structured/{protocol_id}/entities.json",
        Body        = json.dumps({
            "protocol_id"  : protocol_id,
            "entities"     : entities,
            "entity_count" : len(entities),
            "extracted_at" : ts,
        }, default=str).encode("utf-8"),
        ContentType = "application/json",
    )

    s3.put_object(
        Bucket      = BUCKET,
        Key         = f"structured/{protocol_id}/eligibility.json",
        Body        = json.dumps(eligibility, ensure_ascii=False).encode("utf-8"),
        ContentType = "application/json",
    )

    s3.put_object(
        Bucket      = BUCKET,
        Key         = f"structured/{protocol_id}/timelines.json",
        Body        = json.dumps(timelines, ensure_ascii=False).encode("utf-8"),
        ContentType = "application/json",
    )

    print(f"  Structured data saved to S3 (structured/{protocol_id}/)")


# ─────────────────────────────────────────────────────────────────────────────
# HANDLER
# ─────────────────────────────────────────────────────────────────────────────
def lambda_handler(event, context):
    """
    Steps:
      1. Load OCR text from S3
      2. Run Comprehend Medical (chunked, all text)
      3. Extract eligibility criteria
      4. Extract timeline obligations
      5. Save structured JSON to S3
      6. Trigger compliance engine (async)
    """
    try:
        protocol_id = event["protocol_id"]

        print(f"\n{'='*60}")
        print(f"Entity Extractor  |  protocol_id={protocol_id}")
        print(f"{'='*60}")

        # ── Load text ────────────────────────────────────────────────────────
        obj       = s3.get_object(Bucket=BUCKET, Key=f"extracted/{protocol_id}/text.json")
        text_data = json.loads(obj["Body"].read())
        full_text = text_data["text"]
        print(f"  Text length: {len(full_text):,} chars")

        # ── Comprehend Medical ───────────────────────────────────────────────
        entities    = extract_medical_entities(full_text)

        # ── Eligibility & timelines ──────────────────────────────────────────
        eligibility = extract_eligibility_criteria(full_text)
        timelines   = extract_timelines(full_text)

        # ── Persist ──────────────────────────────────────────────────────────
        save_structured(protocol_id, entities, eligibility, timelines)

        # ── Trigger compliance engine ────────────────────────────────────────
        lambda_client.invoke(
            FunctionName   = "protocolscout-compliance-engine",
            InvocationType = "Event",
            Payload        = json.dumps({
                "protocol_id" : protocol_id,
                "bucket"      : BUCKET,
            }),
        )
        print("  Compliance engine triggered (async).")

        return {
            "statusCode": 200,
            "body": json.dumps({
                "protocol_id"   : protocol_id,
                "status"        : "extraction_complete",
                "entities_found": len(entities),
                "timelines_found": len(timelines),
            }),
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise