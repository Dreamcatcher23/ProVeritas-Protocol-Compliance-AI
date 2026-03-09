import boto3
import json
import time
import uuid
import re
import math

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────
REGION          = "ap-south-1"
BUCKET          = "protocolscout-raw-pdfs"
PDF_PREFIX      = "regulatory/"
TMP_PREFIX      = "tmp/pipeline/"

RULE_TABLE      = "compliance_rules"
PROCESSED_TABLE = "processed_documents"

MODEL_ARN       = "arn:aws:bedrock:ap-south-1:654654564205:application-inference-profile/zqbmpo8gwq9u"

# ── Tuning ────────────────────────────────────────────────────────────────────
BEDROCK_CHUNK      = 120      # lines per Bedrock call (smaller = fewer tokens = less throttle)
TRANSLATE_CHUNK    = 9_000    # bytes per Translate call
TIME_BUFFER_MS     = 120_000  # stop 2 min before Lambda hard timeout

# Backoff schedule (seconds to wait BEFORE attempt index N)
# Index 0 = first attempt (no wait), then longer waits on each retry
BACKOFF_SECS       = [0, 15, 35, 65, 100, 140]

INTER_CHUNK_PAUSE  = 3        # seconds between successful Bedrock chunks (prevents burst)
MIN_BEDROCK_GAP    = 2.0      # minimum seconds between any two Bedrock calls
MAX_PARALLEL_TEXTRACT = 8     # how many Textract jobs to pre-submit at startup

# ─────────────────────────────────────────────────────────────────────────────
# STATUS CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
S_PENDING           = "pending"
S_TEXTRACT_STARTED  = "textract_started"
S_TEXT_READY        = "text_ready"
S_RULES_EXTRACTING  = "rules_extracting"
S_COMPLETED         = "completed"
S_FAILED            = "failed"

# ─────────────────────────────────────────────────────────────────────────────
# AWS CLIENTS
# ─────────────────────────────────────────────────────────────────────────────
s3               = boto3.client("s3",               region_name=REGION)
textract_client  = boto3.client("textract",         region_name=REGION)
translate_client = boto3.client("translate",        region_name=REGION)
bedrock          = boto3.client("bedrock-runtime",  region_name=REGION)
ddb              = boto3.resource("dynamodb",       region_name=REGION)

rule_table      = ddb.Table(RULE_TABLE)
processed_table = ddb.Table(PROCESSED_TABLE)

# Global timestamp of last Bedrock call (rate limiter)
_last_bedrock_call_ts = 0.0


# ─────────────────────────────────────────────────────────────────────────────
# TABLE CREATION
# ─────────────────────────────────────────────────────────────────────────────
def create_tables():
    client   = boto3.client("dynamodb", region_name=REGION)
    existing = client.list_tables()["TableNames"]

    if RULE_TABLE not in existing:
        print(f"Creating table: {RULE_TABLE}")
        client.create_table(
            TableName=RULE_TABLE,
            KeySchema=[{"AttributeName": "rule_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "rule_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST"
        )
        client.get_waiter("table_exists").wait(TableName=RULE_TABLE)

    if PROCESSED_TABLE not in existing:
        print(f"Creating table: {PROCESSED_TABLE}")
        client.create_table(
            TableName=PROCESSED_TABLE,
            KeySchema=[{"AttributeName": "pdf_name", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "pdf_name", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST"
        )
        client.get_waiter("table_exists").wait(TableName=PROCESSED_TABLE)

    print("Tables verified.")


# ─────────────────────────────────────────────────────────────────────────────
# STATE MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────
def get_doc_state(pdf_name):
    resp = processed_table.get_item(Key={"pdf_name": pdf_name})
    return resp.get("Item")


def set_doc_state(pdf_name, status, **extra):
    item = {"pdf_name": pdf_name, "status": status, "timestamp": int(time.time())}
    item.update(extra)
    processed_table.put_item(Item=item)


def update_doc_state(pdf_name, **kwargs):
    kwargs["timestamp"] = int(time.time())
    set_expr   = "SET " + ", ".join(f"#{k} = :{k}" for k in kwargs)
    expr_names = {f"#{k}": k for k in kwargs}
    expr_vals  = {f":{k}": v for k, v in kwargs.items()}
    processed_table.update_item(
        Key={"pdf_name": pdf_name},
        UpdateExpression=set_expr,
        ExpressionAttributeNames=expr_names,
        ExpressionAttributeValues=expr_vals
    )


# ─────────────────────────────────────────────────────────────────────────────
# S3 HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _s3_key_for(pdf_name, suffix):
    safe = pdf_name.replace("/", "__")
    return f"{TMP_PREFIX}{safe}{suffix}"


def save_to_s3(pdf_name, data, suffix):
    key  = _s3_key_for(pdf_name, suffix)
    body = json.dumps(data, ensure_ascii=False)
    s3.put_object(Bucket=BUCKET, Key=key, Body=body.encode("utf-8"))
    return key


def load_from_s3(s3_key):
    obj = s3.get_object(Bucket=BUCKET, Key=s3_key)
    return json.loads(obj["Body"].read().decode("utf-8"))


# ─────────────────────────────────────────────────────────────────────────────
# LIST PDFs
# ─────────────────────────────────────────────────────────────────────────────
def list_pdfs():
    results = []
    kwargs  = {"Bucket": BUCKET, "Prefix": PDF_PREFIX}
    while True:
        resp = s3.list_objects_v2(**kwargs)
        for obj in resp.get("Contents", []):
            if obj["Key"].endswith(".pdf"):
                results.append(obj["Key"])
        if resp.get("IsTruncated"):
            kwargs["ContinuationToken"] = resp["NextContinuationToken"]
        else:
            break
    return results


# ─────────────────────────────────────────────────────────────────────────────
# TEXTRACT  –  start + poll + full pagination
# ─────────────────────────────────────────────────────────────────────────────
def start_textract(pdf_name):
    resp = textract_client.start_document_text_detection(
        DocumentLocation={"S3Object": {"Bucket": BUCKET, "Name": pdf_name}}
    )
    return resp["JobId"]


def poll_and_collect_textract(job_id, context):
    """
    Returns:
        str  – full text (succeeded)
        None – Lambda timeout approaching; job still running (resume next run)
        ""   – Textract job itself failed
    """
    while True:
        if context and context.get_remaining_time_in_millis() < TIME_BUFFER_MS:
            print("    Time budget low during Textract poll – state saved.")
            return None

        result = textract_client.get_document_text_detection(JobId=job_id)
        status = result["JobStatus"]

        if status == "FAILED":
            print(f"    Textract FAILED: {job_id}")
            return ""
        if status == "SUCCEEDED":
            break

        print(f"    Textract status={status}. Waiting 10 s …")
        time.sleep(10)

    # Collect ALL pages
    text_lines = []
    pages      = 0
    while True:
        for block in result["Blocks"]:
            if block["BlockType"] == "LINE":
                text_lines.append(block["Text"])
        pages     += 1
        next_token = result.get("NextToken")
        if not next_token:
            break
        result = textract_client.get_document_text_detection(
            JobId=job_id, NextToken=next_token
        )

    print(f"    Textract: {len(text_lines):,} lines  |  {pages} result pages.")
    return "\n".join(text_lines)


# ─────────────────────────────────────────────────────────────────────────────
# TRANSLATE
# ─────────────────────────────────────────────────────────────────────────────
def translate_if_needed(text):
    if not text:
        return text
    try:
        sample = translate_client.translate_text(
            Text=text[:500], SourceLanguageCode="auto", TargetLanguageCode="en"
        )
        if sample.get("SourceLanguageCode", "en") == "en":
            return text
        print(f"    Detected non-English ({sample['SourceLanguageCode']}) – translating …")
    except Exception as e:
        print(f"    Translate detection error: {e} – skipping.")
        return text

    parts = []
    for i in range(0, len(text), TRANSLATE_CHUNK):
        chunk = text[i: i + TRANSLATE_CHUNK]
        try:
            resp = translate_client.translate_text(
                Text=chunk, SourceLanguageCode="auto", TargetLanguageCode="en"
            )
            parts.append(resp["TranslatedText"])
        except Exception as e:
            print(f"    Translate chunk error: {e} – keeping original.")
            parts.append(chunk)
    return "\n".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# FILTER
# ─────────────────────────────────────────────────────────────────────────────
KEYWORDS = [
    "must", "shall", "required", "mandatory", "ethics",
    "consent", "report", "within", "prohibited",
    "investigator", "safety", "trial", "approval",
    "documentation", "notify", "obligation",
    "participant", "sponsor", "protocol", "adverse"
]

def filter_text(text):
    filtered = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        if any(k in line.lower() for k in KEYWORDS):
            filtered.append(line)
    return filtered


# ─────────────────────────────────────────────────────────────────────────────
# BEDROCK JSON PARSER
# ─────────────────────────────────────────────────────────────────────────────
def parse_bedrock_json(raw):
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text.strip()).strip()

    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            for key in ("rules", "compliance_rules", "extracted_rules", "data"):
                if key in result and isinstance(result[key], list):
                    return result[key]
            return [result]
    except json.JSONDecodeError:
        pass

    match = re.search(r"\[.*?\]", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass

    print(f"    WARNING: Could not parse Bedrock JSON. Preview: {raw[:300]}")
    return []


# ─────────────────────────────────────────────────────────────────────────────
# BEDROCK RULE EXTRACTION  –  smart backoff + throttle handling
# ─────────────────────────────────────────────────────────────────────────────
EXTRACT_PROMPT = """\
You are a senior clinical regulatory analyst with expertise in:
ICH GCP, New Drugs and Clinical Trials Rules (India), ICMR National Ethical Guidelines,
CDSCO requirements, and data protection/patient-safety regulations.

Extract ONLY actionable regulatory compliance rules from the text below.

A valid rule defines: mandatory requirements, regulatory obligations, ethical requirements,
safety-reporting rules, approval requirements, documentation requirements,
timelines, investigator responsibilities, patient-protection, or data-privacy obligations.

IGNORE: introductions, background, definitions, historical notes, examples, references.

Focus on lines with: must / shall / required / mandatory / within /
not permitted / prohibited / must report / must obtain approval.

For every rule output EXACTLY these fields:
  rule_id           short label e.g. "INF_CONSENT_01"
  source            document name or section
  category          one of: ethics_committee | informed_consent | safety_reporting |
                    adverse_events | trial_approval | investigator_responsibilities |
                    data_privacy | participant_protection | protocol_compliance | documentation
  severity          critical | high | medium | low
  rule_text         the exact actionable rule statement
  citation          section/clause reference, or ""
  regulatory_intent brief explanation of the rule's purpose

Return ONLY a valid JSON array starting with [ and ending with ].
No markdown fences. No preamble. No extra text.

Text:
{text}
"""


def extract_rules_from_chunk(lines, chunk_idx):
    global _last_bedrock_call_ts

    text   = "\n".join(lines)
    prompt = EXTRACT_PROMPT.format(text=text)

    for attempt in range(len(BACKOFF_SECS)):

        # ── Enforce minimum gap between any two Bedrock calls ────────────────
        elapsed = time.time() - _last_bedrock_call_ts
        if elapsed < MIN_BEDROCK_GAP:
            time.sleep(MIN_BEDROCK_GAP - elapsed)

        # ── Scheduled backoff BEFORE this attempt ────────────────────────────
        wait = BACKOFF_SECS[attempt]
        if wait > 0:
            print(f"    Backoff {wait}s before attempt {attempt + 1} …")
            time.sleep(wait)

        try:
            _last_bedrock_call_ts = time.time()

            response = bedrock.converse(
                modelId=MODEL_ARN,
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                inferenceConfig={"maxTokens": 3000, "temperature": 0.1}
            )
            raw   = response["output"]["message"]["content"][0]["text"]
            rules = parse_bedrock_json(raw)
            print(f"    Chunk {chunk_idx}: {len(rules)} rules.")
            return rules

        except Exception as e:
            err = str(e)
            is_throttle = "ThrottlingException" in err or "Too many requests" in err

            if is_throttle:
                # Extra flat wait on top of the scheduled backoff so the
                # per-minute quota window can fully reset
                extra = 25 * (attempt + 1)
                print(f"    Throttled (attempt {attempt + 1}). Extra pause {extra}s …")
                time.sleep(extra)
            else:
                print(f"    Bedrock error (attempt {attempt + 1}): {e}")

            if attempt == len(BACKOFF_SECS) - 1:
                print(f"    Chunk {chunk_idx}: all attempts exhausted → skipping chunk.")
                return []

    return []


# ─────────────────────────────────────────────────────────────────────────────
# SAVE RULES  –  globally unique IDs
# ─────────────────────────────────────────────────────────────────────────────
def save_rules(rules, pdf_name, chunk_idx):
    saved = 0
    for r in rules:
        if not isinstance(r, dict):
            continue
        original        = str(r.get("rule_id", "rule"))[:20].replace(" ", "_")
        r["rule_id"]    = f"{uuid.uuid4().hex[:10]}_{original}"
        r["source_pdf"] = pdf_name
        r["chunk_idx"]  = chunk_idx
        r["created_at"] = int(time.time())
        try:
            rule_table.put_item(Item=r)
            saved += 1
        except Exception as e:
            print(f"    Error saving rule: {e}")
    return saved


# ─────────────────────────────────────────────────────────────────────────────
# PARALLEL TEXTRACT PRE-SUBMIT
# ─────────────────────────────────────────────────────────────────────────────
def kickoff_pending_textract_jobs(pdf_files):
    """
    Submit Textract jobs for all PENDING PDFs right at startup (up to MAX_PARALLEL_TEXTRACT).
    Textract jobs run in parallel inside AWS – while we process PDF #1, PDFs #2-8
    are already being OCR'd. This removes the 3-5 min Textract wait from each PDF.
    """
    submitted = 0
    for pdf in pdf_files:
        if submitted >= MAX_PARALLEL_TEXTRACT:
            break
        state  = get_doc_state(pdf)
        status = state["status"] if state else S_PENDING
        if status != S_PENDING:
            continue
        try:
            job_id = start_textract(pdf)
            set_doc_state(pdf, S_TEXTRACT_STARTED, textract_job_id=job_id)
            print(f"  [PRE-SUBMIT] Textract started: {pdf}")
            submitted += 1
        except Exception as e:
            print(f"  Pre-submit failed for {pdf}: {e}")

    if submitted:
        print(f"\n  Pre-submitted {submitted} Textract jobs (running in parallel).\n")


def _submit_one_more_textract(pdf_files):
    """After completing a PDF, immediately start the next pending Textract job."""
    for pdf in pdf_files:
        state  = get_doc_state(pdf)
        status = state["status"] if state else S_PENDING
        if status == S_PENDING:
            try:
                job_id = start_textract(pdf)
                set_doc_state(pdf, S_TEXTRACT_STARTED, textract_job_id=job_id)
                print(f"  [ROLLING SUBMIT] Textract started: {pdf}")
            except Exception as e:
                print(f"  Rolling submit failed: {e}")
            break


# ─────────────────────────────────────────────────────────────────────────────
# PROGRESS DISPLAY
# ─────────────────────────────────────────────────────────────────────────────
def _count_rules():
    try:
        count = 0
        resp  = rule_table.scan(Select="COUNT")
        count += resp.get("Count", 0)
        while "LastEvaluatedKey" in resp:
            resp   = rule_table.scan(Select="COUNT",
                                     ExclusiveStartKey=resp["LastEvaluatedKey"])
            count += resp.get("Count", 0)
        return count
    except Exception:
        return "?"


def print_progress(pdf_files):
    counts = {
        S_PENDING: 0, S_TEXTRACT_STARTED: 0, S_TEXT_READY: 0,
        S_RULES_EXTRACTING: 0, S_COMPLETED: 0, S_FAILED: 0
    }
    for pdf in pdf_files:
        state  = get_doc_state(pdf)
        status = state["status"] if state else S_PENDING
        counts[status] = counts.get(status, 0) + 1

    total_rules = _count_rules()

    print("\n── PIPELINE PROGRESS ──────────────────────────────────────────────")
    for k, v in counts.items():
        bar = "▓" * v + "░" * (22 - v)
        print(f"   {k:<22} : {v:>2}  [{bar}]")
    print(f"\n   Total rules in DynamoDB : {total_rules}")
    print("────────────────────────────────────────────────────────────────────\n")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────────────────────────────────────
def run_pipeline(context=None):
    create_tables()

    pdf_files = list_pdfs()
    print(f"Total PDFs in S3: {len(pdf_files)}")
    print_progress(pdf_files)

    # Pre-submit Textract for all pending PDFs so they run in parallel
    kickoff_pending_textract_jobs(pdf_files)

    for pdf in pdf_files:

        # ── Global time check ────────────────────────────────────────────────
        if context and context.get_remaining_time_in_millis() < TIME_BUFFER_MS:
            print("⏱  Time budget exhausted. Stopping cleanly. Next run will resume.")
            break

        state  = get_doc_state(pdf)
        status = state["status"] if state else S_PENDING

        if status == S_COMPLETED:
            print(f"[SKIP – done]   {pdf}")
            continue
        if status == S_FAILED:
            print(f"[SKIP – failed] {pdf}")
            continue

        print(f"\n{'═'*66}")
        print(f"[PROCESSING]  {pdf}  (status={status})")
        print(f"{'═'*66}")

        # ════════════════════════════════════════════════════════════════════
        # STAGE 1 – Submit Textract (if not already pre-submitted)
        # ════════════════════════════════════════════════════════════════════
        if status == S_PENDING:
            job_id = start_textract(pdf)
            set_doc_state(pdf, S_TEXTRACT_STARTED, textract_job_id=job_id)
            status = S_TEXTRACT_STARTED
            print(f"  Textract submitted: {job_id}")

        # ════════════════════════════════════════════════════════════════════
        # STAGE 2 – Wait for Textract, extract text, filter, save to S3
        # ════════════════════════════════════════════════════════════════════
        if status == S_TEXTRACT_STARTED:
            state  = get_doc_state(pdf)
            job_id = state["textract_job_id"]

            text = poll_and_collect_textract(job_id, context)

            if text is None:      # Lambda timing out – resume next run
                continue
            if text == "":        # Textract job failed
                update_doc_state(pdf, status=S_FAILED, fail_reason="textract_failed")
                continue

            text     = translate_if_needed(text)
            filtered = filter_text(text)
            print(f"  Filtered regulatory lines: {len(filtered):,}")

            if not filtered:
                print("  No regulatory lines → marking completed.")
                update_doc_state(pdf, status=S_COMPLETED)
                _submit_one_more_textract(pdf_files)
                continue

            s3_key = save_to_s3(pdf, filtered, "_filtered.json")
            set_doc_state(pdf, S_TEXT_READY,
                          textract_job_id=job_id,
                          s3_filtered_key=s3_key,
                          bedrock_chunk_offset=0)
            status = S_TEXT_READY
            print(f"  Saved filtered lines → {s3_key}")

        # ════════════════════════════════════════════════════════════════════
        # STAGE 3 – Bedrock rule extraction (chunked + resumable)
        # ════════════════════════════════════════════════════════════════════
        if status in (S_TEXT_READY, S_RULES_EXTRACTING):
            state        = get_doc_state(pdf)
            s3_key       = state["s3_filtered_key"]
            chunk_offset = int(state.get("bedrock_chunk_offset", 0))

            filtered     = load_from_s3(s3_key)
            total_chunks = max(1, math.ceil(len(filtered) / BEDROCK_CHUNK))

            print(f"  Bedrock chunks: {total_chunks}  |  Resuming from: {chunk_offset}")
            update_doc_state(pdf, status=S_RULES_EXTRACTING)

            completed_all  = True
            rules_this_pdf = 0

            for chunk_idx in range(chunk_offset, total_chunks):

                # Per-chunk time check
                if context and context.get_remaining_time_in_millis() < TIME_BUFFER_MS:
                    update_doc_state(pdf, status=S_RULES_EXTRACTING,
                                     bedrock_chunk_offset=chunk_idx)
                    print(f"  ⏱ Time hit at chunk {chunk_idx}/{total_chunks} – "
                          f"offset saved. Will resume next run.")
                    completed_all = False
                    break

                chunk_lines = filtered[chunk_idx * BEDROCK_CHUNK:
                                       (chunk_idx + 1) * BEDROCK_CHUNK]
                rules       = extract_rules_from_chunk(chunk_lines, chunk_idx)
                n_saved     = save_rules(rules, pdf, chunk_idx)
                rules_this_pdf += n_saved

                # Save progress after every chunk (crash-safe)
                update_doc_state(pdf, status=S_RULES_EXTRACTING,
                                 bedrock_chunk_offset=chunk_idx + 1)

                print(f"  [{chunk_idx + 1}/{total_chunks}]  {n_saved} rules saved  "
                      f"(PDF running total: {rules_this_pdf})")

                # Pause between chunks to avoid burst throttle
                if chunk_idx < total_chunks - 1:
                    time.sleep(INTER_CHUNK_PAUSE)

            if completed_all:
                update_doc_state(pdf, status=S_COMPLETED)
                print(f"\n  ✓ COMPLETED  {pdf}  →  {rules_this_pdf} rules")
                # Immediately roll in the next PDF's Textract job
                _submit_one_more_textract(pdf_files)

        time.sleep(2)   # small pause between PDFs

    # ── Final summary ─────────────────────────────────────────────────────────
    print("\n═══ FINAL SUMMARY ═══")
    print_progress(pdf_files)


# ─────────────────────────────────────────────────────────────────────────────
# LAMBDA ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
def lambda_handler(event, context):
    print("Lambda started.")
    run_pipeline(context)
    return {
        "statusCode": 200,
        "body": json.dumps("Pipeline run finished. Check logs + DynamoDB for status.")
    }