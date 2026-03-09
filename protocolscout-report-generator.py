# ─────────────────────────────────────────────────────────────────────────────
# Lambda: protocolscout-report-generator
# Memory: 1024 MB | Timeout: 5 min
# Env Vars:
#   DOCUMENTS_BUCKET = protocolscout-documents-[YOUR-ID]
#   RESULTS_TABLE    = compliance_results
#   AUDIT_TABLE      = protocol_audit
# Triggered by: compliance-engine (async Lambda invoke)
# ─────────────────────────────────────────────────────────────────────────────

import json
import boto3
import os
from datetime import datetime

# ── Clients ──────────────────────────────────────────────────────────────────
s3       = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")

BUCKET        = os.environ["DOCUMENTS_BUCKET"]
RESULTS_TABLE = dynamodb.Table(os.environ["RESULTS_TABLE"])
AUDIT_TABLE   = dynamodb.Table(os.environ["AUDIT_TABLE"])


# ─────────────────────────────────────────────────────────────────────────────
# LOAD HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def load_s3_json(key):
    obj = s3.get_object(Bucket=BUCKET, Key=key)
    return json.loads(obj["Body"].read())


def load_gaps_from_dynamodb(protocol_id):
    """
    Scan compliance_results for all gaps belonging to this protocol.
    Uses a FilterExpression because protocol_id is not the primary key.
    (In production add a GSI on protocol_id for faster lookups.)
    """
    from boto3.dynamodb.conditions import Attr

    gaps   = []
    kwargs = {
        "FilterExpression": Attr("protocol_id").eq(protocol_id)
    }

    while True:
        resp = RESULTS_TABLE.scan(**kwargs)
        gaps.extend(resp.get("Items", []))
        if "LastEvaluatedKey" not in resp:
            break
        kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]

    print(f"  Loaded {len(gaps)} gaps from DynamoDB.")
    return gaps


# ─────────────────────────────────────────────────────────────────────────────
# JSON REPORT
# ─────────────────────────────────────────────────────────────────────────────
def build_json_report(protocol_id, assessment, gaps, compliance_score):
    """Structured machine-readable compliance report."""
    by_sev = lambda s: [g for g in gaps if g.get("severity") == s]

    return {
        "report_metadata": {
            "protocol_id"   : protocol_id,
            "generated_at"  : datetime.utcnow().isoformat() + "Z",
            "report_version": "2.0",
            "system"        : "ProtocolScout AI Compliance System",
        },
        "executive_summary": {
            "compliance_score": compliance_score,
            "overall_status"  : assessment.get("overall_status", "unknown"),
            "total_gaps"      : len(gaps),
            "critical_gaps"   : len(by_sev("critical")),
            "high_gaps"       : len(by_sev("high")),
            "medium_gaps"     : len(by_sev("medium")),
            "low_gaps"        : len(by_sev("low")),
        },
        "full_assessment"    : assessment,
        "detailed_gaps"      : gaps,
        "recommendations": {
            "immediate_actions": [
                g["recommendation"]
                for g in gaps if g.get("severity") in ("critical", "high")
            ],
            "suggested_improvements": [
                g["recommendation"]
                for g in gaps if g.get("severity") in ("medium", "low")
            ],
        },
        "regulatory_references": {
            "ICMR_2017" : "National Ethical Guidelines for Biomedical and Health Research, ICMR 2017",
            "NDCT_2019" : "New Drugs and Clinical Trials Rules, 2019",
            "DPDP_2023" : "Digital Personal Data Protection Act, 2023",
            "ICH_E6_R2" : "ICH E6(R2) Good Clinical Practice Guidelines",
            "CDSCO"     : "Central Drugs Standard Control Organisation requirements",
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# TEXT REPORT
# ─────────────────────────────────────────────────────────────────────────────
def build_text_report(protocol_id, assessment, gaps, compliance_score):
    """Human-readable compliance report."""
    now      = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    status   = assessment.get("overall_status", "unknown").upper()
    summary  = assessment.get("summary", "No summary available.")
    strengths = assessment.get("strengths", [])

    by_sev = lambda s: [g for g in gaps if g.get("severity") == s]
    cnt    = lambda s: len(by_sev(s))

    # Score bar
    filled = int(compliance_score / 5)
    bar    = "█" * filled + "░" * (20 - filled)

    lines = [
        "╔══════════════════════════════════════════════════════════════════╗",
        "║           PROTOCOLSCOUT – COMPLIANCE AUDIT REPORT               ║",
        "╚══════════════════════════════════════════════════════════════════╝",
        f"",
        f"  Protocol ID : {protocol_id}",
        f"  Generated   : {now}",
        f"  System      : ProtocolScout AI  (AWS Bedrock Claude 3.5 Sonnet)",
        f"",
        "──────────────────────────────────────────────────────────────────",
        f"  COMPLIANCE SCORE  :  {compliance_score}/100",
        f"  [{bar}]",
        f"  STATUS            :  {status}",
        "──────────────────────────────────────────────────────────────────",
        f"",
        "  EXECUTIVE SUMMARY",
        f"  {summary}",
        f"",
        "  GAP BREAKDOWN",
        f"    Critical : {cnt('critical')}",
        f"    High     : {cnt('high')}",
        f"    Medium   : {cnt('medium')}",
        f"    Low      : {cnt('low')}",
        f"    TOTAL    : {len(gaps)}",
        f"",
    ]

    # Detailed findings per severity
    for sev in ("critical", "high", "medium", "low"):
        sev_gaps = by_sev(sev)
        if not sev_gaps:
            continue

        lines.append(f"══ {sev.upper()} GAPS {'═' * (55 - len(sev))}")
        for i, gap in enumerate(sev_gaps, 1):
            lines += [
                f"",
                f"  [{i}] {gap.get('description', '')}",
                f"      Rule        : {gap.get('rule_id', 'N/A')}",
                f"      Category    : {gap.get('category', 'N/A')}",
                f"      Location    : {gap.get('location', 'Not specified')}",
                f"      Regulation  : {gap.get('regulatory_citation', 'N/A')}",
                f"      ✅ Fix      : {gap.get('recommendation', 'N/A')}",
            ]
        lines.append("")

    # Strengths
    if strengths:
        lines.append("══ PROTOCOL STRENGTHS " + "═" * 44)
        for s in strengths:
            lines.append(f"  ✓ {s}")
        lines.append("")

    # Regulatory references
    lines += [
        "══ REGULATORY REFERENCES " + "═" * 41,
        "  • ICMR 2017  – National Ethical Guidelines for Biomedical and Health Research",
        "  • NDCT 2019  – New Drugs and Clinical Trials Rules",
        "  • DPDP 2023  – Digital Personal Data Protection Act",
        "  • ICH E6 R2  – Good Clinical Practice Guidelines",
        "  • CDSCO      – Central Drugs Standard Control Organisation",
        "",
        "──────────────────────────────────────────────────────────────────",
        "  Generated by ProtocolScout AI Compliance System",
        "  Powered by Amazon Bedrock (Claude 3.5 Sonnet) | AWS India Region",
        "──────────────────────────────────────────────────────────────────",
    ]

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# HANDLER
# ─────────────────────────────────────────────────────────────────────────────
def lambda_handler(event, context):
    """
    Steps:
      1. Load compliance assessment JSON from S3
      2. Load all gaps from DynamoDB compliance_results
      3. Generate JSON report  → S3 reports/{protocol_id}/compliance_report.json
      4. Generate text report  → S3 reports/{protocol_id}/compliance_report.txt
      5. Update audit record in DynamoDB with 'completed' status
    """
    try:
        protocol_id      = event["protocol_id"]
        compliance_score = int(event.get("compliance_score", 0))

        print(f"\n{'='*60}")
        print(f"Report Generator  |  protocol_id={protocol_id}")
        print(f"{'='*60}")

        # ── Load assessment ──────────────────────────────────────────────────
        assessment = load_s3_json(f"structured/{protocol_id}/compliance_assessment.json")

        # ── Load gaps ────────────────────────────────────────────────────────
        gaps = load_gaps_from_dynamodb(protocol_id)

        # Fallback: use gaps from assessment if DynamoDB is empty
        if not gaps:
            gaps = assessment.get("gaps", [])
            print("  Warning: No gaps in DynamoDB; using assessment JSON gaps.")

        # ── Build reports ────────────────────────────────────────────────────
        json_report = build_json_report(protocol_id, assessment, gaps, compliance_score)
        text_report = build_text_report(protocol_id, assessment, gaps, compliance_score)

        # ── Save JSON report ─────────────────────────────────────────────────
        json_key = f"reports/{protocol_id}/compliance_report.json"
        s3.put_object(
            Bucket      = BUCKET,
            Key         = json_key,
            Body        = json.dumps(json_report, indent=2, ensure_ascii=False, default=str).encode("utf-8"),
            ContentType = "application/json",
        )
        print(f"  JSON report saved → s3://{BUCKET}/{json_key}")

        # ── Save text report ─────────────────────────────────────────────────
        txt_key = f"reports/{protocol_id}/compliance_report.txt"
        s3.put_object(
            Bucket      = BUCKET,
            Key         = txt_key,
            Body        = text_report.encode("utf-8"),
            ContentType = "text/plain; charset=utf-8",
        )
        print(f"  Text report saved → s3://{BUCKET}/{txt_key}")

        # ── Update audit table ───────────────────────────────────────────────
        AUDIT_TABLE.put_item(
            Item={
                "protocol_id"     : protocol_id,
                "timestamp"       : int(datetime.utcnow().timestamp()),
                "action"          : "report_generated",
                "status"          : "completed",
                "compliance_score": compliance_score,
                "gaps_found"      : len(gaps),
                "report_json"     : f"s3://{BUCKET}/{json_key}",
                "report_txt"      : f"s3://{BUCKET}/{txt_key}",
                "completed_at"    : datetime.utcnow().isoformat(),
            }
        )
        print("  Audit record updated → completed.")

        return {
            "statusCode": 200,
            "body": json.dumps({
                "protocol_id"     : protocol_id,
                "status"          : "completed",
                "compliance_score": compliance_score,
                "gaps_found"      : len(gaps),
                "report_json"     : f"s3://{BUCKET}/{json_key}",
                "report_txt"      : f"s3://{BUCKET}/{txt_key}",
            }),
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise