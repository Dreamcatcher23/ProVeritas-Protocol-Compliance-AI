# ProtocolScout Flask Web Application

AI-Powered Clinical Trial Protocol Compliance Checker for Indian Regulations

## Features

- 🤖 **AI-Powered Analysis** - Uses Amazon Bedrock (Claude 3.5) for intelligent compliance checking
- 📄 **OCR Processing** - Extracts text from PDF protocols using Amazon Textract
- 🏥 **Medical Entity Extraction** - Identifies drugs, conditions, and procedures with Amazon Comprehend Medical
- ✅ **Compliance Checking** - Validates against 50+ Indian regulatory rules (ICMR, CDSCO, NDCT, ICH-GCP, DPDP)
- 📊 **Detailed Reports** - Generate compliance reports in PDF, DOCX, and JSON formats
- 🔐 **User Authentication** - Secure login/registration with password hashing and session management
- 🔒 **Secure** - All data encrypted with AWS KMS

## Prerequisites

- Python 3.9 or higher
- AWS Account with the following services configured:
  - Lambda functions (already deployed)
  - S3 buckets
  - DynamoDB tables
  - IAM roles and permissions
- AWS credentials (Access Key ID and Secret Access Key)

## Installation

### 1. Clone or Download

Download all files to your local machine.

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure AWS Credentials

Create a `.env` file in the project root (copy from `.env.example`):

```bash
cp .env.example .env
```

Edit `.env` and add your AWS credentials:

```env
# AWS Configuration
AWS_REGION=ap-south-1
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
DOCUMENTS_BUCKET=protocolscout-documents

# Flask Configuration
SECRET_KEY=your-secret-key-change-in-production
FLASK_ENV=development
```

**Important:** Replace the placeholder values with your actual AWS credentials and bucket name.

Generate a secure SECRET_KEY for production:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 4. Set Up Authentication

Create the DynamoDB users table:

```bash
python create_users_table.py
```

This creates a `users` table in DynamoDB for storing user accounts.

For detailed authentication setup, see [AUTHENTICATION_SETUP.md](AUTHENTICATION_SETUP.md).

### 5. Verify Lambda Functions

Make sure these Lambda functions are deployed in your AWS account:
- `protocolscout-upload-handler`
- `protocolscout-ocr-processor`
- `protocolscout-entity-extractor`
- `protocolscout-regulatory-processor`
- `protocolscout-compliance-engine`
- `protocolscout-report-generator`
- `protocolscout-status-checker`

### 6. Verify DynamoDB Tables

Ensure these tables exist:
- `compliance_rules`
- `protocol_audit`
- `compliance_results`
- `users` (created in step 4)

## Running the Application

### Development Mode

```bash
python app.py
```

The application will start on `http://localhost:5000`

### Production Mode (with Gunicorn)

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## Usage

### 1. Create an Account

1. Navigate to `http://localhost:5000/register`
2. Fill in your details:
   - Full Name
   - Email Address
   - Institution / Organization
   - Password (minimum 8 characters)
3. Click "Create Account"
4. You'll be automatically logged in

### 2. Upload Protocol

1. Navigate to `http://localhost:5000/upload` (requires login)
2. Enter protocol title
3. Select your protocol PDF file (max 50MB)
4. Click "Upload and Analyze"
5. Note the Protocol ID for tracking

### 3. Check Status

- The upload page will show your Protocol ID
- Processing typically takes 3-5 minutes
- You'll be redirected to the results page automatically

### 4. View Results

1. Navigate to `http://localhost:5000/results/<protocol_id>` (requires login)
2. View compliance score and violations
3. Download reports in PDF, DOCX, or JSON format

### 5. Dashboard

1. Navigate to `http://localhost:5000/dashboard` (requires login)
2. View all your uploaded protocols
3. Click on any protocol to see its results

## Project Structure

```
protocolscout-web/
├── app.py                          # Main Flask application
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment variables template
├── README.md                       # This file
├── AUTHENTICATION_SETUP.md         # Authentication setup guide
├── create_users_table.py           # Script to create users table
├── templates/                      # HTML templates
│   ├── base.html                  # Base template with navbar/footer
│   ├── index.html                 # Home page
│   ├── upload.html                # Upload protocol page
│   ├── results.html               # Compliance results page
│   ├── dashboard.html             # User dashboard
│   ├── about.html                 # About page
│   ├── login.html                 # Login page
│   ├── register.html              # Registration page
│   ├── 404.html                   # 404 error page
│   └── 500.html                   # 500 error page
└── static/                         # Static files (optional)
```

## API Endpoints

### Web Pages
- `GET /` - Home page
- `GET /login` - Login page
- `GET /register` - Registration page
- `GET /upload` - Upload form (requires authentication)
- `GET /results/<protocol_id>` - View results (requires authentication)
- `GET /dashboard` - User dashboard (requires authentication)
- `GET /about` - About page
- `GET /logout` - Logout (requires authentication)

### API Endpoints
- `POST /login` - User login
- `POST /register` - User registration
- `POST /upload` - Upload protocol (returns protocol_id, requires authentication)
- `GET /status/<protocol_id>` - Check processing status
- `GET /api/results/<protocol_id>` - Get compliance results (JSON)
- `GET /api/protocols/<user_id>` - Get user's protocols (JSON)
- `GET /download/<protocol_id>/<format>` - Download report (pdf/docx/json)

## AWS Services Used

- **Amazon Bedrock (Claude 3.5)** - AI reasoning for compliance analysis
- **Amazon Textract** - OCR for PDF text extraction
- **Amazon Comprehend Medical** - Medical entity extraction
- **AWS Lambda** - Serverless compute
- **Amazon S3** - Document storage
- **Amazon DynamoDB** - Database for rules and results
- **AWS KMS** - Encryption key management

## Troubleshooting

### Lambda Function Not Found
- Verify Lambda function names match exactly
- Check AWS region is set to `ap-south-1`
- Ensure IAM permissions allow Lambda invocation

### S3 Access Denied
- Verify bucket name in `.env` file
- Check IAM user has S3 read/write permissions
- Ensure bucket exists in `ap-south-1` region

### DynamoDB Table Not Found
- Verify table names: `compliance_rules`, `protocol_audit`, `compliance_results`
- Check tables exist in `ap-south-1` region
- Ensure IAM user has DynamoDB permissions

### Upload Fails
- Check file size (max 50MB)
- Verify file is PDF format
- Check CloudWatch logs for Lambda errors

## Security Notes

- Never commit `.env` file to version control
- Use strong SECRET_KEY in production
- Rotate AWS credentials regularly
- Enable MFA on AWS account
- Use IAM roles with least privilege
- Enable CloudTrail for audit logging

## Performance

- Typical processing time: 3-5 minutes per protocol
- Supports protocols up to 50MB
- Concurrent uploads supported
- Auto-scaling with AWS Lambda

## Cost Estimation

Approximate AWS costs per protocol analysis:
- Textract: $0.15 - $0.50
- Bedrock (Claude): $0.10 - $0.30
- Comprehend Medical: $0.05 - $0.15
- Lambda: $0.01 - $0.05
- S3/DynamoDB: $0.01 - $0.02

**Total: ~$0.32 - $1.02 per protocol**

## Support

For issues or questions:
1. Check CloudWatch logs for Lambda errors
2. Verify AWS service quotas
3. Review IAM permissions
4. Check the implementation guide: `AWS_CONSOLE_IMPLEMENTATION_GUIDE.md`

## License

This project is for educational and research purposes.

## Acknowledgments

- Built with Flask and Bootstrap 5
- Powered by AWS AI/ML services
- Regulatory data from ICMR, CDSCO, NDCT, ICH, and DPDP Act 2023
