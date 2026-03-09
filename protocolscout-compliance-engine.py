# ─────────────────────────────────────────────────────────────────────────────
# Lambda: protocolscout-compliance-engine
# Memory: 2048 MB | Timeout: 15 min
# Env Vars:
#   DOCUMENTS_BUCKET = protocolscout-documents-[YOUR-ID]
#   RULES_TABLE      = compliance_rules
#   RESULTS_TABLE    = compliance_results
# Triggered by: entity-extractor (async Lambda invoke)
# ─────────────────────────────────────────────────────────────────────────────

import json
import boto3
import re
import uuid
import os
from datetime import datetime

# ── Clients ──────────────────────────────────────────────────────────────────
bedrock       = boto3.client("bedrock-runtime", region_name="ap-south-1")
dynamodb      = boto3.resource("dynamodb")
s3            = boto3.client("s3")
lambda_client = boto3.client("lambda")

BUCKET        = os.environ["DOCUMENTS_BUCKET"]
RULES_TABLE   = dynamodb.Table(os.environ["RULES_TABLE"])
RESULTS_TABLE = dynamodb.Table(os.environ["RESULTS_TABLE"])

MODEL_ID = os.environ.get("BEDROCK_MODEL_ARN", "arn:aws:bedrock:ap-south-1:654654564205:application-inference-profile/zqbmpo8gwq9u")


# ─────────────────────────────────────────────────────────────────────────────
# LOAD HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def load_s3_json(key):
    obj = s3.get_object(Bucket=BUCKET, Key=key)
    return json.loads(obj["Body"].read())


def load_all_compliance_rules():
    """
    Full DynamoDB scan with pagination – loads every rule in compliance_rules.
    In production with 1000+ rules, add a status filter to fetch only 'active' rules.
    """
    print("Loading compliance rules from DynamoDB…")
    rules    = []
    kwargs   = {}

    while True:
        resp  = RULES_TABLE.scan(**kwargs)
        rules.extend(resp.get("Items", []))
        if "LastEvaluatedKey" not in resp:
            break
        kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]

    print(f"  Loaded {len(rules)} compliance rules.")
    return rules


# ─────────────────────────────────────────────────────────────────────────────
# PROMPT BUILDER
# ─────────────────────────────────────────────────────────────────────────────
def build_prompt(protocol_id, entities, eligibility, timelines, rules):
    """Build the Bedrock prompt from all structured inputs."""

    # Entity summary (counts per type)
    entity_summary = {}
    for e in entities[:200]:        # cap to keep prompt manageable
        t = e.get("Type", "UNKNOWN")
        entity_summary[t] = entity_summary.get(t, 0) + 1

    # Rules split by severity
    critical_rules = [r for r in rules if r.get("severity") == "critical"][:20]
    high_rules     = [r for r in rules if r.get("severity") == "high"][:15]
    medium_rules   = [r for r in rules if r.get("severity") == "medium"][:10]

    def fmt_rules(rule_list):
        lines = []
        for r in rule_list:
            lines.append(
                f"  [{r.get('rule_id','?')}] ({r.get('source','?')}) "
                f"{r.get('rule_text','')}"
                f" — cite: {r.get('citation','N/A')}"
            )
        return "\n".join(lines) if lines else "  None loaded."

    prompt = f"""You are a senior clinical trial compliance auditor specialising in Indian regulations:
ICMR National Ethical Guidelines 2017, NDCT Rules 2019, CDSCO requirements, ICH E6(R2) GCP, DPDP Act 2023.

TASK: Analyse the clinical trial protocol below and identify ALL compliance gaps against the loaded rules.

PROTOCOL ID: {protocol_id}

MEDICAL ENTITIES DETECTED (type → count):
{json.dumps(entity_summary, indent=2)}

ELIGIBILITY CRITERIA:
  Inclusion: {len(eligibility.get('inclusion', []))} items
  Exclusion: {len(eligibility.get('exclusion', []))} items

TIMELINE OBLIGATIONS FOUND: {len(timelines)}
{json.dumps(timelines[:10], indent=2)}

─── COMPLIANCE RULES TO CHECK ───────────────────────────────────────────────

CRITICAL (must comply):
{fmt_rules(critical_rules)}

HIGH PRIORITY:
{fmt_rules(high_rules)}

MEDIUM PRIORITY:
{fmt_rules(medium_rules)}

─── ANALYSIS REQUIRED ───────────────────────────────────────────────────────

Check each area below thoroughly:

1. INFORMED CONSENT (ICMR 2017)
   - Verify all 19 ICMR-required consent elements are addressed
   - Voluntariness, right to withdraw, language of consent
   - Consent for minors / vulnerable populations

2. SAFETY REPORTING (NDCT Rules 2019)
   - SAE reporting within 24 hours (Rule 15)
   - Adverse event definitions and grading
   - Sponsor notification procedures

3. ETHICS COMMITTEE (ICMR 2017 / NDCT)
   - EC approval mentioned
   - Protocol amendment notification procedure
   - EC composition requirements addressed

4. VULNERABLE POPULATIONS (ICMR 2017 Chapter 7)
   - Children, pregnant women, economically disadvantaged
   - Additional consent/assent procedures

5. DATA PRIVACY (DPDP Act 2023)
   - Data retention policy specified
   - Consent for data processing
   - Security measures for personal health data

6. INVESTIGATOR QUALIFICATIONS (ICH E6 R2)
   - Qualifications and training documented
   - GCP training mentioned

7. PROTOCOL DEVIATIONS
   - Procedure for documenting and reporting deviations
   - CDSCO notification requirements

─── OUTPUT FORMAT ────────────────────────────────────────────────────────────

Return ONLY valid JSON (no markdown, no preamble):

{{
  "compliance_score": <integer 0-100>,
  "overall_status": "<compliant|minor_gaps|major_gaps|non_compliant>",
  "gaps": [
    {{
      "gap_id": "GAP-001",
      "rule_id": "<exact rule_id from rules list above>",
      "category": "<informed_consent|safety_reporting|ethics_committee|vulnerable_populations|data_privacy|investigator|protocol_deviation>",
      "severity": "<critical|high|medium|low>",
      "description": "<specific, clear description of the gap>",
      "location": "<section/page if identifiable, else 'Not found in protocol'>",
      "recommendation": "<specific, actionable fix>",
      "regulatory_citation": "<ICMR 2017 Section X / NDCT Rule Y / ICH E6 R2 Z>"
    }}
  ],
  "strengths": ["<list compliant areas found in the protocol>"],
  "summary": "<2-3 sentence overall assessment>"
}}
"""
    return prompt


# ─────────────────────────────────────────────────────────────────────────────
# BEDROCK CALL + JSON PARSE
# ─────────────────────────────────────────────────────────────────────────────
def call_bedrock(prompt):
    """Call Claude via Bedrock Converse API; return parsed dict or raise."""
    response = bedrock.converse(
        modelId          = MODEL_ID,
        messages         = [{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig  = {"maxTokens": 8000, "temperature": 0.2},
    )

    raw_text = response["output"]["message"]["content"][0]["text"]

    # Strip markdown fences if present
    text = raw_text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$",          "", text).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Last resort: find the first {...} block
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError(f"Bedrock returned non-JSON output:\n{raw_text[:500]}")


# ─────────────────────────────────────────────────────────────────────────────
# SAVE GAPS TO DYNAMODB
# ─────────────────────────────────────────────────────────────────────────────
def save_gaps(protocol_id, gaps):
    """Write each compliance gap as an individual DynamoDB item."""
    ts = datetime.utcnow().isoformat()
    saved = 0

    with RESULTS_TABLE.batch_writer() as batch:
        for gap in gaps:
            result_id = f"RESULT-{uuid.uuid4().hex[:12]}"
            batch.put_item(
                Item={
                    "result_id"          : result_id,
                    "protocol_id"        : protocol_id,
                    "gap_id"             : gap.get("gap_id", result_id),
                    "rule_id"            : gap.get("rule_id", "UNKNOWN"),
                    "category"           : gap.get("category", "general"),
                    "severity"           : gap.get("severity", "medium"),
                    "description"        : gap.get("description", ""),
                    "location"           : gap.get("location", "Not specified"),
                    "recommendation"     : gap.get("recommendation", ""),
                    "regulatory_citation": gap.get("regulatory_citation", ""),
                    "detected_at"        : ts,
                }
            )
            saved += 1

    print(f"  Saved {saved} gaps to DynamoDB ({RESULTS_TABLE.name}).")
    return saved


# ─────────────────────────────────────────────────────────────────────────────
# HANDLER
# ─────────────────────────────────────────────────────────────────────────────
def lambda_handler(event, context):
    """
    Steps:
      1. Load entities / eligibility / timelines from S3
      2. Load ALL compliance rules from DynamoDB
      3. Build prompt and call Bedrock Claude
      4. Store compliance assessment JSON to S3
      5. Write each gap to DynamoDB compliance_results
      6. Trigger report generator (async)
    """
    try:
        protocol_id = event["protocol_id"]

        print(f"\n{'='*60}")
        print(f"Compliance Engine  |  protocol_id={protocol_id}")
        print(f"{'='*60}")

        # ── Load structured data ─────────────────────────────────────────────
        entities_data = load_s3_json(f"structured/{protocol_id}/entities.json")
        eligibility   = load_s3_json(f"structured/{protocol_id}/eligibility.json")
        timelines     = load_s3_json(f"structured/{protocol_id}/timelines.json")

        entities = entities_data.get("entities", [])
        print(f"  Entities  : {len(entities)}")
        print(f"  Timelines : {len(timelines)}")

        # ── Load rules ───────────────────────────────────────────────────────
        rules = load_all_compliance_rules()

        # ── Build prompt ─────────────────────────────────────────────────────
        prompt = build_prompt(protocol_id, entities, eligibility, timelines, rules)
        print(f"  Prompt length: {len(prompt):,} chars")

        # ── Bedrock ──────────────────────────────────────────────────────────
        print("  Invoking Bedrock Claude…")
        assessment = call_bedrock(prompt)

        score = assessment.get("compliance_score", 0)
        gaps  = assessment.get("gaps", [])
        print(f"  Compliance score : {score}/100")
        print(f"  Gaps identified  : {len(gaps)}")

        # ── Save assessment to S3 ────────────────────────────────────────────
        s3.put_object(
            Bucket      = BUCKET,
            Key         = f"structured/{protocol_id}/compliance_assessment.json",
            Body        = json.dumps(assessment, indent=2, ensure_ascii=False).encode("utf-8"),
            ContentType = "application/json",
        )
        print("  Assessment JSON saved to S3.")

        # ── Save gaps to DynamoDB ────────────────────────────────────────────
        save_gaps(protocol_id, gaps)

        # ── Trigger report generator ─────────────────────────────────────────
        lambda_client.invoke(
            FunctionName   = "protocolscout-report-generator",
            InvocationType = "Event",
            Payload        = json.dumps({
                "protocol_id"     : protocol_id,
                "bucket"          : BUCKET,
                "compliance_score": score,
            }),
        )
        print("  Report generator triggered (async).")

        return {
            "statusCode": 200,
            "body": json.dumps({
                "protocol_id"     : protocol_id,
                "status"          : "compliance_checked",
                "compliance_score": score,
                "gaps_found"      : len(gaps),
            }),
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise