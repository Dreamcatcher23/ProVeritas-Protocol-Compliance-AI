# ProtocolScout - Quick Start Guide

Get your Flask web application running in 5 minutes!

## Step 1: Install Python Dependencies

```bash
pip install -r requirements.txt
```

## Step 2: Configure AWS Credentials

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Edit `.env` and add your AWS credentials:
```env
AWS_REGION=ap-south-1
AWS_ACCESS_KEY_ID=AKIA...your_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
DOCUMENTS_BUCKET=protocolscout-documents-prod-2026
SECRET_KEY=change-this-to-random-string
```

**Where to find your AWS credentials:**
- Go to AWS Console → IAM → Users → Your User → Security Credentials
- Click "Create access key"
- Copy Access Key ID and Secret Access Key

**Where to find your bucket name:**
- Go to AWS Console → S3
- Look for bucket starting with `protocolscout-documents-`
- Copy the full bucket name

## Step 3: Run the Application

### Option A: Using the startup script (Recommended)

**Linux/Mac:**
```bash
chmod +x run.sh
./run.sh
```

**Windows:**
```cmd
run.bat
```

### Option B: Run directly

```bash
python app.py
```

## Step 4: Access the Application

Open your browser and go to:
```
http://localhost:5000
```

## Step 5: Upload Your First Protocol

1. Click "Upload Protocol" in the navigation
2. Fill in your details:
   - User ID: `test@example.com`
   - Institution: `Test Hospital`
   - Protocol Title: `Test Clinical Trial`
3. Select a PDF file
4. Click "Upload and Analyze"
5. Wait 3-5 minutes for processing
6. View your compliance report!

## Troubleshooting

### "Lambda function not found"
- Check that all Lambda functions are deployed in AWS
- Verify function names match exactly
- Ensure AWS region is `ap-south-1`

### "Access Denied" errors
- Verify AWS credentials in `.env` file
- Check IAM user has necessary permissions
- Ensure bucket name is correct

### "Module not found" errors
```bash
pip install -r requirements.txt --upgrade
```

### Port 5000 already in use
Edit `app.py` and change the port:
```python
app.run(debug=True, host='0.0.0.0', port=8080)
```

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Check [AWS_CONSOLE_IMPLEMENTATION_GUIDE.md](AWS_CONSOLE_IMPLEMENTATION_GUIDE.md) for AWS setup
- Explore the dashboard at `/dashboard`
- View the about page at `/about`

## Production Deployment

For production, use Gunicorn:

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

Or deploy to:
- AWS Elastic Beanstalk
- AWS EC2
- Heroku
- Google Cloud Run
- Azure App Service

## Support

If you encounter issues:
1. Check CloudWatch logs in AWS Console
2. Verify all Lambda functions are working
3. Test Lambda functions individually in AWS Console
4. Check DynamoDB tables have data

## Quick Links

- Home: http://localhost:5000/
- Upload: http://localhost:5000/upload
- Dashboard: http://localhost:5000/dashboard
- About: http://localhost:5000/about

---

**Ready to check compliance? Start uploading protocols!** 🚀
