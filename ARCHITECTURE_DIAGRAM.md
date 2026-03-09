# ProtocolScout - Visual Architecture Diagram



This document provides a visual representation of the ProtocolScout architecture in a style similar to the AWS architecture diagram you provided.

---

## Architecture Overview Diagram

```
                    ┌─────────────────────────────────────────────────┐
                    │         USERS (Researchers & Coordinators)      │
                    │  👨‍⚕️ 👨‍⚕️    Web Browser    Mobile App    👩‍⚕️ 👩‍⚕️  │
                    └────────────────────┬────────────────────────────┘
                                         │
                                         │ HTTPS
                                         │
    ┌────────────────────────────────────▼────────────────────────────────────┐
    │                                                                          │
    │                         AWS CLOUD (ap-south-1)                           │
    │                                                                          │
    │  ┌────────────────────────────────────────────────────────────────┐    │
    │  │                    🌐 Amazon CloudFront                         │    │
    │  │                    Global CDN + Caching                         │    │
    │  └────────────────────────┬───────────────────────────────────────┘    │
    │                           │                                              │
    │  ┌────────────────────────▼───────────────────────────────────────┐    │
    │  │                    🛡️ AWS WAF                                   │    │
    │  │              DDoS Protection + Rate Limiting                    │    │
    │  └────────────────────────┬───────────────────────────────────────┘    │
    │                           │                                              │
    │  ┌────────────────────────▼───────────────────────────────────────┐    │
    │  │                                                                 │    │
    │  │              ┌──────────────────┐    ┌──────────────────┐     │    │
    │  │              │  🔐 Amazon       │◄───┤  🚪 Amazon API   │     │    │
    │  │              │     Cognito      │    │     Gateway      │     │    │
    │  │              │  Authentication  │    │   REST API       │     │    │
    │  │              └──────────────────┘    └────────┬─────────┘     │    │
    │  │                                               │                │    │
    │  └───────────────────────────────────────────────┼────────────────┘    │
    │                                                   │                     │
    │  ┌────────────────────────────────────────────────▼──────────────────┐ │
    │  │                    VPC (Private Subnet)                           │ │
    │  │                                                                   │ │
    │  │  ┌──────────────────────────────────────────────────────────┐   │ │
    │  │  │           ⚡ AWS Lambda Functions (Serverless)            │   │ │
    │  │  │                                                           │   │ │
    │  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │   │ │
    │  │  │  │  Lambda 1   │  │  Lambda 2   │  │  Lambda 3   │     │   │ │
    │  │  │  │  Document   │─►│     OCR     │─►│Information  │     │   │ │
    │  │  │  │  Processor  │  │Orchestrator │  │  Extractor  │     │   │ │
    │  │  │  └─────────────┘  └─────────────┘  └──────┬──────┘     │   │ │
    │  │  │                                            │            │   │ │
    │  │  │  ┌─────────────┐  ┌─────────────┐        │            │   │ │
    │  │  │  │  Lambda 5   │◄─│  Lambda 4   │◄───────┘            │   │ │
    │  │  │  │   Report    │  │    Rules    │                     │   │ │
    │  │  │  │  Generator  │  │   Engine    │                     │   │ │
    │  │  │  └─────────────┘  └─────────────┘                     │   │ │
    │  │  └──────────────────────────────────────────────────────────┘   │ │
    │  │                                                                   │ │
    │  └───────────────────────────────────────────────────────────────────┘ │
    │                           │                                              │
    │  ┌────────────────────────▼───────────────────────────────────────┐    │
    │  │                    🤖 AWS AI Services                           │    │
    │  │                                                                 │    │
    │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │    │
    │  │  │   Amazon     │  │   Amazon     │  │   Amazon     │        │    │
    │  │  │   Textract   │  │  Comprehend  │  │   Bedrock    │        │    │
    │  │  │              │  │   Medical    │  │   (Claude)   │        │    │
    │  │  │  OCR + Forms │  │  Medical NLP │  │  Reasoning   │        │    │
    │  │  └──────────────┘  └──────────────┘  └──────────────┘        │    │
    │  └─────────────────────────────────────────────────────────────────    │
    │                           │                                              │
    │  ┌────────────────────────▼───────────────────────────────────────┐    │
    │  │                    💾 Data Storage Layer                        │    │
    │  │                                                                 │    │
    │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │    │
    │  │  │   Amazon S3  │  │   Amazon     │  │  ElastiCache │        │    │
    │  │  │              │  │  DynamoDB    │  │    (Redis)   │        │    │
    │  │  │  Documents   │  │  Audit Trail │  │    Cache     │        │    │
    │  │  │  & Reports   │  │  & Metadata  │  │              │        │    │
    │  │  └──────────────┘  └──────────────┘  └──────────────┘        │    │
    │  └─────────────────────────────────────────────────────────────────    │
    │                           │                                              │
    │  ┌────────────────────────▼───────────────────────────────────────┐    │
    │  │                 📊 Monitoring & Security                        │    │
    │  │                                                                 │    │
    │  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │    │
    │  │  │   Amazon     │  │   AWS X-Ray  │  │   AWS KMS    │        │    │
    │  │  │  CloudWatch  │  │              │  │              │        │    │
    │  │  │  Logs/Metrics│  │   Tracing    │  │  Encryption  │        │    │
    │  │  └──────────────┘  └──────────────┘  └──────────────┘        │    │
    │  └─────────────────────────────────────────────────────────────────    │
    │                                                                          │
    └──────────────────────────────────────────────────────────────────────────┘
```

---

## Detailed Component Layout (AWS Services Style)



### Layer 1: User Access Layer

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER ACCESS LAYER                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   👨‍⚕️ Clinical Researchers        👩‍⚕️ Research Coordinators          │
│   👨‍🔬 Principal Investigators     👨‍💼 Regulatory Affairs Officers    │
│                                                                     │
│   Access Methods:                                                   │
│   • Web Browser (Desktop/Laptop)                                   │
│   • Mobile App (iOS/Android)                                       │
│   • API Integration (Hospital Systems)                             │
│                                                                     │
│   Locations:                                                        │
│   • Hospitals & Research Centers                                   │
│   • Academic Institutions                                          │
│   • CROs (Contract Research Organizations)                         │
│   • Ethics Committee Offices                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### Layer 2: Edge & Security Layer

```
┌─────────────────────────────────────────────────────────────────────┐
│                      EDGE & SECURITY LAYER                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌───────────────────────────────────────────────────────────┐    │
│  │  🌐 Amazon CloudFront (Global CDN)                         │    │
│  │  ─────────────────────────────────────────────────────────│    │
│  │  • Edge Locations: 400+ worldwide                         │    │
│  │  • Static Content Caching                                 │    │
│  │  • SSL/TLS Termination                                    │    │
│  │  • Origin: S3 (static) + API Gateway (dynamic)            │    │
│  └───────────────────────────────────────────────────────────┘    │
│                            ▼                                        │
│  ┌───────────────────────────────────────────────────────────┐    │
│  │  🛡️ AWS WAF (Web Application Firewall)                    │    │
│  │  ─────────────────────────────────────────────────────────│    │
│  │  • Rate Limiting: 100 req/5min per IP                     │    │
│  │  • SQL Injection Protection                               │    │
│  │  • XSS Protection                                         │    │
│  │  • Bot Detection & Blocking                               │    │
│  │  • Geo-Blocking (if needed)                               │    │
│  └───────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

### Layer 3: API & Authentication Layer

```
┌─────────────────────────────────────────────────────────────────────┐
│                   API & AUTHENTICATION LAYER                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────────────┐    ┌──────────────────────────┐     │
│  │  🚪 Amazon API Gateway   │    │  🔐 Amazon Cognito       │     │
│  │  ──────────────────────  │    │  ──────────────────────  │     │
│  │  REST API Endpoints:     │◄───┤  User Pool:              │     │
│  │                          │    │  • Email/Password        │     │
│  │  POST /protocols         │    │  • MFA (optional)        │     │
│  │  GET  /protocols/{id}    │    │  • OAuth 2.0             │     │
│  │  GET  /protocols/{id}/   │    │                          │     │
│  │       report             │    │  User Groups:            │     │
│  │  PUT  /protocols/{id}/   │    │  • Researchers           │     │
│  │       gaps/{gap_id}      │    │  • Coordinators          │     │
│  │  POST /rules             │    │  • Admins                │     │
│  │  GET  /rules             │    │                          │     │
│  │                          │    │  Identity Pool:          │     │
│  │  Features:               │    │  • Federated Identity    │     │
│  │  • Rate Limiting         │    │  • Temporary Credentials │     │
│  │  • Request Validation    │    │                          │     │
│  │  • CORS Enabled          │    │                          │     │
│  │  • API Keys              │    │                          │     │
│  └──────────────────────────┘    └──────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────┘
```

### Layer 4: Compute Layer (AWS Lambda)

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SERVERLESS COMPUTE LAYER                         │
│                         (AWS Lambda)                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  ⚡ Lambda 1: Document Processor                            │  │
│  │  ───────────────────────────────────────────────────────────│  │
│  │  Runtime: Python 3.12                                       │  │
│  │  Memory: 512 MB                                             │  │
│  │  Timeout: 5 minutes                                         │  │
│  │  Concurrency: 100 (reserved)                                │  │
│  │                                                             │  │
│  │  Responsibilities:                                          │  │
│  │  • Validate PDF format                                      │  │
│  │  • Generate protocol_id                                     │  │
│  │  • Upload to S3                                             │  │
│  │  • Create audit record                                      │  │
│  │  • Trigger next Lambda                                      │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                            ▼                                        │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  ⚡ Lambda 2: OCR Orchestrator                              │  │
│  │  ───────────────────────────────────────────────────────────│  │
│  │  Runtime: Python 3.12                                       │  │
│  │  Memory: 1024 MB                                            │  │
│  │  Timeout: 15 minutes                                        │  │
│  │  Concurrency: 50                                            │  │
│  │                                                             │  │
│  │  Responsibilities:                                          │  │
│  │  • Call Amazon Textract                                     │  │
│  │  • Poll for completion                                      │  │
│  │  • Handle pagination                                        │  │
│  │  • Merge results                                            │  │
│  │  • Store extracted text                                     │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                            ▼                                        │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  ⚡ Lambda 3: Information Extractor                         │  │
│  │  ───────────────────────────────────────────────────────────│  │
│  │  Runtime: Python 3.12                                       │  │
│  │  Memory: 2048 MB                                            │  │
│  │  Timeout: 10 minutes                                        │  │
│  │  Layers: Medical terminology library                        │  │
│  │                                                             │  │
│  │  Responsibilities:                                          │  │
│  │  • Call Comprehend Medical                                  │  │
│  │  • Extract eligibility criteria                             │  │
│  │  • Parse timelines                                          │  │
│  │  • Identify AE requirements                                 │  │
│  │  • Store structured data                                    │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                            ▼                                        │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  ⚡ Lambda 4: Rules Engine                                  │  │
│  │  ───────────────────────────────────────────────────────────│  │
│  │  Runtime: Python 3.12                                       │  │
│  │  Memory: 3008 MB                                            │  │
│  │  Timeout: 15 minutes                                        │  │
│  │  VPC: Private subnet                                        │  │
│  │                                                             │  │
│  │  Responsibilities:                                          │  │
│  │  • Load ICMR/CDSCO rules                                    │  │
│  │  • Call Bedrock for reasoning                               │  │
│  │  • Generate compliance score                                │  │
│  │  • Identify gaps                                            │  │
│  │  • Store results                                            │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                            ▼                                        │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  ⚡ Lambda 5: Report Generator                              │  │
│  │  ───────────────────────────────────────────────────────────│  │
│  │  Runtime: Python 3.12                                       │  │
│  │  Memory: 2048 MB                                            │  │
│  │  Timeout: 10 minutes                                        │  │
│  │  Layers: python-docx, reportlab                             │  │
│  │                                                             │  │
│  │  Responsibilities:                                          │  │
│  │  • Fetch all results                                        │  │
│  │  • Generate executive summary                               │  │
│  │  • Create PDF/Word reports                                  │  │
│  │  • Update audit trail                                       │  │
│  │  • Send notifications                                       │  │
│  └─────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### Layer 5: AI Services Layer



```
┌─────────────────────────────────────────────────────────────────────┐
│                        AWS AI SERVICES LAYER                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  📄 Amazon Textract                                          │  │
│  │  ────────────────────────────────────────────────────────────│  │
│  │  Purpose: OCR and Document Analysis                          │  │
│  │                                                              │  │
│  │  Features:                                                   │  │
│  │  • Text extraction (95%+ accuracy)                           │  │
│  │  • Forms extraction (key-value pairs)                        │  │
│  │  • Tables extraction (structured data)                       │  │
│  │  • Signature detection                                       │  │
│  │  • Layout analysis                                           │  │
│  │                                                              │  │
│  │  APIs Used:                                                  │  │
│  │  • StartDocumentTextDetection                                │  │
│  │  • StartDocumentAnalysis                                     │  │
│  │  • GetDocumentTextDetection                                  │  │
│  │  • GetDocumentAnalysis                                       │  │
│  │                                                              │  │
│  │  Performance:                                                │  │
│  │  • 100 pages in 2-3 minutes                                  │  │
│  │  • Parallel processing                                       │  │
│  │                                                              │  │
│  │  Cost: ₹20-40 per 100-page document                         │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  🏥 Amazon Comprehend Medical                                │  │
│  │  ────────────────────────────────────────────────────────────│  │
│  │  Purpose: Medical NLP and Entity Recognition                 │  │
│  │                                                              │  │
│  │  Features:                                                   │  │
│  │  • Medical entity recognition                                │  │
│  │    - MEDICAL_CONDITION                                       │  │
│  │    - MEDICATION                                              │  │
│  │    - TREATMENT_NAME                                          │  │
│  │    - TEST_TREATMENT_PROCEDURE                                │  │
│  │  • ICD-10-CM coding                                          │  │
│  │  • RxNorm concept mapping                                    │  │
│  │  • PHI detection                                             │  │
│  │                                                              │  │
│  │  APIs Used:                                                  │  │
│  │  • DetectEntitiesV2                                          │  │
│  │  • InferICD10CM                                              │  │
│  │  • InferRxNormConcepts                                       │  │
│  │  • DetectPHI                                                 │  │
│  │                                                              │  │
│  │  Performance:                                                │  │
│  │  • 1000 characters in <1 second                              │  │
│  │  • 90%+ F1-score on medical entities                         │  │
│  │                                                              │  │
│  │  Cost: ₹10-20 per document                                   │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  🤖 Amazon Bedrock (Claude 3.5 Sonnet)                       │  │
│  │  ────────────────────────────────────────────────────────────│  │
│  │  Purpose: Advanced Reasoning & Compliance Analysis           │  │
│  │                                                              │  │
│  │  Model: anthropic.claude-3-5-sonnet-20241022-v2:0           │  │
│  │                                                              │  │
│  │  Features:                                                   │  │
│  │  • 200K token context window                                 │  │
│  │  • Multi-turn conversations                                  │  │
│  │  • Structured output generation                              │  │
│  │  • Complex reasoning                                         │  │
│  │  • Regulatory knowledge                                      │  │
│  │                                                              │  │
│  │  Use Cases:                                                  │  │
│  │  • Compliance gap identification                             │  │
│  │  • Redline suggestion generation                             │  │
│  │  • Regulatory citation matching                              │  │
│  │  • Executive summary creation                                │  │
│  │  • Question answering                                        │  │
│  │                                                              │  │
│  │  Configuration:                                              │  │
│  │  • Temperature: 0.3 (deterministic)                          │  │
│  │  • Max tokens: 8000 output                                   │  │
│  │  • Input: 50K tokens (protocol + rules)                      │  │
│  │  • Output: 5K tokens (assessment)                            │  │
│  │                                                              │  │
│  │  Performance:                                                │  │
│  │  • Compliance report in 30-60 seconds                        │  │
│  │                                                              │  │
│  │  Cost: ₹15-30 per protocol                                   │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### Layer 6: Data Storage Layer

```
┌─────────────────────────────────────────────────────────────────────┐
│                       DATA STORAGE LAYER                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  🗄️ Amazon S3 (protocolscout-documents)                      │  │
│  │  ────────────────────────────────────────────────────────────│  │
│  │  Purpose: Document and Report Storage                        │  │
│  │                                                              │  │
│  │  Bucket Structure:                                           │  │
│  │  protocolscout-documents/                                    │  │
│  │  ├── uploads/{protocol_id}/                                  │  │
│  │  │   ├── original.pdf                                        │  │
│  │  │   └── metadata.json                                       │  │
│  │  ├── extracted/{protocol_id}/                                │  │
│  │  │   ├── text.json                                           │  │
│  │  │   ├── tables.json                                         │  │
│  │  │   └── forms.json                                          │  │
│  │  ├── structured/{protocol_id}/                               │  │
│  │  │   ├── entities.json                                       │  │
│  │  │   ├── eligibility.json                                    │  │
│  │  │   ├── timelines.json                                      │  │
│  │  │   └── adverse_events.json                                 │  │
│  │  └── reports/{protocol_id}/                                  │  │
│  │      ├── compliance_report.pdf                               │  │
│  │      ├── compliance_report.docx                              │  │
│  │      └── compliance_data.json                                │  │
│  │                                                              │  │
│  │  Features:                                                   │  │
│  │  • Versioning enabled                                        │  │
│  │  • KMS encryption (SSE-KMS)                                  │  │
│  │  • Lifecycle policies (Glacier after 90 days)                │  │
│  │  • Cross-region replication (DR)                             │  │
│  │  • VPC endpoints (private access)                            │  │
│  │                                                              │  │
│  │  Performance:                                                │  │
│  │  • 5,500 GET/sec per prefix                                  │  │
│  │  • 3,500 PUT/sec per prefix                                  │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  📊 Amazon DynamoDB                                          │  │
│  │  ────────────────────────────────────────────────────────────│  │
│  │  Purpose: Audit Trails, Metadata, Compliance Rules          │  │
│  │                                                              │  │
│  │  Tables:                                                     │  │
│  │                                                              │  │
│  │  1. protocol_audit                                           │  │
│  │     PK: protocol_id                                          │  │
│  │     SK: timestamp                                            │  │
│  │     Attributes: user_id, status, document_hash,              │  │
│  │                 processing_duration, aws_request_ids         │  │
│  │     GSI: user_id_index, status_index                         │  │
│  │                                                              │  │
│  │  2. compliance_rules                                         │  │
│  │     PK: jurisdiction (ICMR/CDSCO/state)                      │  │
│  │     SK: rule_id                                              │  │
│  │     Attributes: category, severity, rule_text,               │  │
│  │                 validation_logic, citation                   │  │
│  │     GSI: category_index                                      │  │
│  │                                                              │  │
│  │  3. compliance_results                                       │  │
│  │     PK: protocol_id                                          │  │
│  │     SK: gap_id                                               │  │
│  │     Attributes: severity, regulatory_domain, rule_id,        │  │
│  │                 current_text, issue, suggested_redline       │  │
│  │     GSI: severity_index                                      │  │
│  │                                                              │  │
│  │  Features:                                                   │  │
│  │  • On-demand capacity (auto-scaling)                         │  │
│  │  • Point-in-time recovery                                    │  │
│  │  • Encryption at rest (SSE)                                  │  │
│  │  • Daily automated backups                                   │  │
│  │  • 7-year TTL (ICMR requirement)                             │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  ⚡ Amazon ElastiCache (Redis)                               │  │
│  │  ────────────────────────────────────────────────────────────│  │
│  │  Purpose: Session Caching, Temporary Data                    │  │
│  │                                                              │  │
│  │  Configuration:                                              │  │
│  │  • Node Type: cache.t3.medium                                │  │
│  │  • Engine: Redis 7.0                                         │  │
│  │  • Cluster Mode: Disabled                                    │  │
│  │  • Replicas: 1 (high availability)                           │  │
│  │                                                              │  │
│  │  Use Cases:                                                  │  │
│  │  • Cache extracted text                                      │  │
│  │  • Store user session data                                   │  │
│  │  • Cache frequently accessed rules                           │  │
│  │  • Temporary processing data                                 │  │
│  │                                                              │  │
│  │  Performance:                                                │  │
│  │  • Sub-millisecond latency                                   │  │
│  │  • 100K+ operations/second                                   │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### Layer 7: Monitoring & Security Layer



```
┌─────────────────────────────────────────────────────────────────────┐
│                  MONITORING & SECURITY LAYER                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  📊 Amazon CloudWatch                                        │  │
│  │  ────────────────────────────────────────────────────────────│  │
│  │  Purpose: Metrics, Logs, and Alarms                          │  │
│  │                                                              │  │
│  │  Custom Metrics:                                             │  │
│  │  • ProtocolsProcessed (count)                                │  │
│  │  • ProcessingDuration (milliseconds)                         │  │
│  │  • ComplianceScore (average)                                 │  │
│  │  • ErrorRate (percentage)                                    │  │
│  │  • CostPerProtocol (₹)                                       │  │
│  │  • LambdaInvocations (count)                                 │  │
│  │  • TextractJobsCompleted (count)                             │  │
│  │  • BedrockTokensUsed (count)                                 │  │
│  │                                                              │  │
│  │  Alarms:                                                     │  │
│  │  • High error rate (>5% failures)                            │  │
│  │  • Long processing time (>10 min)                            │  │
│  │  • Lambda throttling                                         │  │
│  │  • DynamoDB capacity exceeded                                │  │
│  │  • S3 bucket size exceeding budget                           │  │
│  │                                                              │  │
│  │  Log Groups:                                                 │  │
│  │  • /aws/lambda/document-processor                            │  │
│  │  • /aws/lambda/ocr-orchestrator                              │  │
│  │  • /aws/lambda/information-extractor                         │  │
│  │  • /aws/lambda/rules-engine                                  │  │
│  │  • /aws/lambda/report-generator                              │  │
│  │                                                              │  │
│  │  Retention: 90 days                                          │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  🔍 AWS X-Ray                                                │  │
│  │  ────────────────────────────────────────────────────────────│  │
│  │  Purpose: Distributed Tracing                                │  │
│  │                                                              │  │
│  │  Trace Segments:                                             │  │
│  │  • API Gateway request                                       │  │
│  │  • Lambda execution time                                     │  │
│  │  • Textract processing time                                  │  │
│  │  • Comprehend Medical API calls                              │  │
│  │  • Bedrock invocation time                                   │  │
│  │  • DynamoDB query latency                                    │  │
│  │  • S3 upload/download time                                   │  │
│  │                                                              │  │
│  │  Analysis:                                                   │  │
│  │  • Identify bottlenecks                                      │  │
│  │  • Track cold start latency                                  │  │
│  │  • Monitor service performance                               │  │
│  │  • Debug processing failures                                 │  │
│  │                                                              │  │
│  │  Service Map:                                                │  │
│  │  • Visual representation of request flow                     │  │
│  │  • Latency distribution                                      │  │
│  │  • Error rates per service                                   │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  🔐 AWS KMS (Key Management Service)                         │  │
│  │  ────────────────────────────────────────────────────────────│  │
│  │  Purpose: Encryption Key Management                          │  │
│  │                                                              │  │
│  │  Keys:                                                       │  │
│  │  • protocolscout-s3-key                                      │  │
│  │    - For S3 bucket encryption                                │  │
│  │    - Automatic annual rotation                               │  │
│  │                                                              │  │
│  │  • protocolscout-dynamodb-key                                │  │
│  │    - For DynamoDB encryption                                 │  │
│  │    - Automatic annual rotation                               │  │
│  │                                                              │  │
│  │  Features:                                                   │  │
│  │  • Customer-managed keys                                     │  │
│  │  • Automatic key rotation                                    │  │
│  │  • CloudTrail logging                                        │  │
│  │  • Fine-grained access control                               │  │
│  │                                                              │  │
│  │  Encryption:                                                 │  │
│  │  • Data at rest: KMS encryption                              │  │
│  │  • Data in transit: TLS 1.3                                  │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  🔒 AWS IAM (Identity and Access Management)                 │  │
│  │  ────────────────────────────────────────────────────────────│  │
│  │  Purpose: Access Control                                     │  │
│  │                                                              │  │
│  │  Roles:                                                      │  │
│  │  • LambdaExecutionRole                                       │  │
│  │    - Textract, Comprehend, Bedrock access                    │  │
│  │    - S3, DynamoDB read/write                                 │  │
│  │    - CloudWatch Logs write                                   │  │
│  │                                                              │  │
│  │  • APIGatewayRole                                            │  │
│  │    - Lambda invoke permissions                               │  │
│  │    - CloudWatch Logs write                                   │  │
│  │                                                              │  │
│  │  Policies:                                                   │  │
│  │  • Least privilege principle                                 │  │
│  │  • Resource-based policies                                   │  │
│  │  • Service control policies                                  │  │
│  │                                                              │  │
│  │  Features:                                                   │  │
│  │  • Multi-factor authentication                               │  │
│  │  • Password policies                                         │  │
│  │  • Access analyzer                                           │  │
│  │  • CloudTrail integration                                    │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagram (Sequence)

```
User                CloudFront    API Gateway    Lambda 1      S3         Lambda 2
 │                      │              │            │           │            │
 │  Upload Protocol     │              │            │           │            │
 ├─────────────────────►│              │            │           │            │
 │                      │  Forward     │            │           │            │
 │                      ├─────────────►│            │           │            │
 │                      │              │  Invoke    │           │            │
 │                      │              ├───────────►│           │            │
 │                      │              │            │  Store    │            │
 │                      │              │            ├──────────►│            │
 │                      │              │            │           │            │
 │                      │              │            │  Trigger  │            │
 │                      │              │            ├──────────────────────►│
 │                      │              │            │           │            │
 │  Job ID              │              │            │           │            │
 │◄─────────────────────┴──────────────┴────────────┘           │            │
 │                                                               │            │
                                                                 │            │
Textract    Lambda 3    Comprehend    Lambda 4    Bedrock    DynamoDB    Lambda 5
   │           │         Medical         │           │           │           │
   │  Extract  │            │            │           │           │           │
   │◄──────────┤            │            │           │           │           │
   │           │            │            │           │           │           │
   │  Results  │            │            │           │           │           │
   ├──────────►│            │            │           │           │           │
   │           │  Analyze   │            │           │           │           │
   │           ├───────────►│            │           │           │           │
   │           │            │  Entities  │           │           │           │
   │           │◄───────────┤            │           │           │           │
   │           │            │            │           │           │           │
   │           │  Trigger   │            │           │           │           │
   │           ├───────────────────────►│           │           │           │
   │           │            │            │  Evaluate │           │           │
   │           │            │            ├──────────►│           │           │
   │           │            │            │           │  Gaps     │           │
   │           │            │            │◄──────────┤           │           │
   │           │            │            │           │           │           │
   │           │            │            │  Store    │           │           │
   │           │            │            ├──────────────────────►│           │
   │           │            │            │           │           │           │
   │           │            │            │  Trigger  │           │           │
   │           │            │            ├──────────────────────────────────►│
   │           │            │            │           │           │           │
   │           │            │            │           │           │  Generate │
   │           │            │            │           │           │  Report   │
   │           │            │            │           │           │◄──────────┤
   │           │            │            │           │           │           │
                                                                 │           │
                                                                 │  Store    │
                                                                 │  Report   │
                                                                 ├──────────►S3
                                                                 │           │
                                                                 │  Notify   │
                                                                 ├──────────►User
```

---

## Network Architecture (VPC Layout)



```
┌─────────────────────────────────────────────────────────────────────────┐
│                    AWS Region: ap-south-1 (Mumbai)                      │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                            VPC                                    │ │
│  │                     CIDR: 10.0.0.0/16                             │ │
│  │                                                                   │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │  Availability Zone A (ap-south-1a)                          │ │ │
│  │  │                                                             │ │ │
│  │  │  ┌──────────────────────────────────────────────────────┐  │ │ │
│  │  │  │  Public Subnet (10.0.1.0/24)                         │  │ │ │
│  │  │  │  • NAT Gateway                                       │  │ │ │
│  │  │  │  • Internet Gateway                                  │  │ │ │
│  │  │  └──────────────────────────────────────────────────────┘  │ │ │
│  │  │                                                             │ │ │
│  │  │  ┌──────────────────────────────────────────────────────┐  │ │ │
│  │  │  │  Private Subnet (10.0.11.0/24)                       │  │ │ │
│  │  │  │  • Lambda Functions                                  │  │ │ │
│  │  │  │  • ElastiCache Primary Node                          │  │ │ │
│  │  │  │  • VPC Endpoints (S3, DynamoDB)                      │  │ │ │
│  │  │  └──────────────────────────────────────────────────────┘  │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  │                                                                   │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │  Availability Zone B (ap-south-1b)                          │ │ │
│  │  │                                                             │ │ │
│  │  │  ┌──────────────────────────────────────────────────────┐  │ │ │
│  │  │  │  Public Subnet (10.0.2.0/24)                         │  │ │ │
│  │  │  │  • NAT Gateway                                       │  │ │ │
│  │  │  └──────────────────────────────────────────────────────┘  │ │ │
│  │  │                                                             │ │ │
│  │  │  ┌──────────────────────────────────────────────────────┐  │ │ │
│  │  │  │  Private Subnet (10.0.12.0/24)                       │  │ │ │
│  │  │  │  • Lambda Functions (failover)                       │  │ │ │
│  │  │  │  • ElastiCache Replica Node                          │  │ │ │
│  │  │  │  • VPC Endpoints (S3, DynamoDB)                      │  │ │ │
│  │  │  └──────────────────────────────────────────────────────┘  │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  │                                                                   │ │
│  │  ┌─────────────────────────────────────────────────────────────┐ │ │
│  │  │  Availability Zone C (ap-south-1c)                          │ │ │
│  │  │                                                             │ │ │
│  │  │  ┌──────────────────────────────────────────────────────┐  │ │ │
│  │  │  │  Private Subnet (10.0.13.0/24)                       │  │ │ │
│  │  │  │  • Lambda Functions (failover)                       │  │ │ │
│  │  │  │  • VPC Endpoints (S3, DynamoDB)                      │  │ │ │
│  │  │  └──────────────────────────────────────────────────────┘  │ │ │
│  │  └─────────────────────────────────────────────────────────────┘ │ │
│  │                                                                   │ │
│  │  Security Groups:                                                 │ │
│  │  • Lambda-SG: Allow outbound to AWS services                     │ │
│  │  • ElastiCache-SG: Allow inbound from Lambda-SG on port 6379     │ │
│  │                                                                   │ │
│  │  Network ACLs:                                                    │ │
│  │  • Allow all inbound/outbound (default)                          │ │
│  │  • Custom rules for additional security                          │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  External Services (Outside VPC):                                       │
│  • Amazon Textract (AWS managed)                                        │
│  • Amazon Comprehend Medical (AWS managed)                              │
│  • Amazon Bedrock (AWS managed)                                         │
│  • Amazon S3 (accessed via VPC endpoint)                                │
│  • Amazon DynamoDB (accessed via VPC endpoint)                          │
│  • Amazon CloudWatch (AWS managed)                                      │
│  • AWS X-Ray (AWS managed)                                              │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Cost Optimization Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    COST OPTIMIZATION STRATEGIES                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. Serverless Architecture                                         │
│     └─► Pay only for actual usage (no idle costs)                  │
│     └─► Auto-scaling (0 to 1000+ concurrent)                       │
│     └─► No server management overhead                              │
│                                                                     │
│  2. S3 Lifecycle Policies                                           │
│     └─► Standard (0-30 days): Frequent access                      │
│     └─► Standard-IA (30-90 days): Infrequent access                │
│     └─► Glacier (90+ days): Archive                                │
│     └─► 70% storage cost reduction                                 │
│                                                                     │
│  3. DynamoDB On-Demand                                              │
│     └─► Pay per request (no provisioned capacity)                  │
│     └─► Auto-scales with traffic                                   │
│     └─► No over-provisioning waste                                 │
│                                                                     │
│  4. Lambda Optimization                                             │
│     └─► Right-sized memory allocation                              │
│     └─► Efficient code (minimize execution time)                   │
│     └─► Reuse connections (reduce cold starts)                     │
│     └─► Reserved concurrency for predictable workloads             │
│                                                                     │
│  5. CloudWatch Log Retention                                        │
│     └─► 90-day retention (vs. indefinite)                          │
│     └─► Export old logs to S3 Glacier                              │
│     └─► 60% log storage cost reduction                             │
│                                                                     │
│  6. ElastiCache Right-Sizing                                        │
│     └─► cache.t3.medium (sufficient for 100 protocols/month)       │
│     └─► Reserved instances for predictable usage                   │
│     └─► 40% cost savings vs. on-demand                             │
│                                                                     │
│  7. Data Transfer Optimization                                      │
│     └─► VPC endpoints (avoid NAT Gateway charges)                  │
│     └─► CloudFront caching (reduce origin requests)                │
│     └─► S3 Transfer Acceleration (only when needed)                │
│                                                                     │
│  8. AI Service Optimization                                         │
│     └─► Batch Textract requests where possible                     │
│     └─► Cache Comprehend Medical results                           │
│     └─► Optimize Bedrock prompts (reduce token usage)              │
│     └─► Use appropriate model (Claude 3.5 Sonnet vs. Haiku)        │
│                                                                     │
│  Total Cost Savings: 50-60% vs. non-optimized architecture         │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Disaster Recovery Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                  DISASTER RECOVERY STRATEGY                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Primary Region: ap-south-1 (Mumbai)                                │
│  DR Region: ap-southeast-1 (Singapore)                              │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │  Multi-AZ Deployment (Primary Region)                         │ │
│  │  ─────────────────────────────────────────────────────────────│ │
│  │  • Lambda: Automatic failover across 3 AZs                    │ │
│  │  • DynamoDB: Automatic replication across 3 AZs               │ │
│  │  • ElastiCache: Primary + Replica in different AZs            │ │
│  │  • S3: Automatic replication across AZs                       │ │
│  │                                                                │ │
│  │  RTO (Recovery Time Objective): < 5 minutes                   │ │
│  │  RPO (Recovery Point Objective): 0 (synchronous replication)  │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │  Cross-Region Replication (DR Region)                        │ │
│  │  ─────────────────────────────────────────────────────────────│ │
│  │  • S3: Cross-region replication (CRR) enabled                 │ │
│  │  • DynamoDB: Global tables (optional, for critical data)      │ │
│  │  • Lambda: Deployment packages stored in DR region            │ │
│  │  • CloudFormation: Infrastructure as Code for quick rebuild   │ │
│  │                                                                │ │
│  │  RTO (Recovery Time Objective): < 1 hour                      │ │
│  │  RPO (Recovery Point Objective): 15 minutes                   │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │  Backup Strategy                                              │ │
│  │  ─────────────────────────────────────────────────────────────│ │
│  │  • DynamoDB: Daily automated backups (35-day retention)       │ │
│  │  • S3: Versioning enabled (recover deleted objects)           │ │
│  │  • Lambda: Code stored in CodeCommit/GitHub                   │ │
│  │  • Configuration: Stored in Parameter Store                   │ │
│  │                                                                │ │
│  │  Backup Retention: 7 years (ICMR requirement)                 │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │  Failover Procedure                                           │ │
│  │  ─────────────────────────────────────────────────────────────│ │
│  │  1. Detect failure (CloudWatch alarms)                        │ │
│  │  2. Notify operations team (SNS)                              │ │
│  │  3. Verify DR region readiness                                │ │
│  │  4. Update Route 53 DNS (point to DR region)                  │ │
│  │  5. Deploy Lambda functions in DR region                      │ │
│  │  6. Verify system functionality                               │ │
│  │  7. Monitor and adjust                                        │ │
│  │                                                                │ │
│  │  Automated Failover: Partial (DNS, Lambda)                    │ │
│  │  Manual Failover: Full system (requires approval)             │ │
│  └───────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Summary

This architecture document provides a comprehensive visual representation of the ProtocolScout system, aligned with AWS best practices and the reference architecture style you provided. The system leverages:

- **13 AWS services** for a complete, production-ready solution
- **Serverless architecture** for cost optimization and scalability
- **Multi-AZ deployment** for high availability
- **Comprehensive monitoring** for operational excellence
- **Strong security** with encryption, IAM, and WAF
- **India-specific compliance** with ICMR and CDSCO requirements

The architecture is designed to process 100+ protocols per month with 99.9% uptime, 5-minute processing time, and ₹64 per protocol cost.

