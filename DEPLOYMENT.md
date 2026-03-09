# ProtocolScout - Production Deployment Guide

This guide covers deploying ProtocolScout Flask application to production environments.

## Pre-Deployment Checklist

- [ ] All AWS Lambda functions deployed and tested
- [ ] DynamoDB tables created and populated with rules
- [ ] S3 buckets configured with proper permissions
- [ ] IAM roles and policies configured
- [ ] AWS credentials secured (use IAM roles, not access keys)
- [ ] Environment variables configured
- [ ] SSL/TLS certificate obtained (for HTTPS)
- [ ] Domain name configured (optional)

## Deployment Options

### Option 1: AWS Elastic Beanstalk (Recommended)

**Pros:** Fully managed, auto-scaling, load balancing, easy deployment
**Cost:** ~$20-50/month

#### Steps:

1. Install EB CLI:
```bash
pip install awsebcli
```

2. Initialize Elastic Beanstalk:
```bash
eb init -p python-3.11 protocolscout-web
```

3. Create environment:
```bash
eb create protocolscout-prod
```

4. Set environment variables:
```bash
eb setenv AWS_REGION=ap-south-1 \
  DOCUMENTS_BUCKET=your-bucket-name \
  SECRET_KEY=your-secret-key
```

5. Deploy:
```bash
eb deploy
```

6. Open application:
```bash
eb open
```

### Option 2: AWS EC2 with Nginx

**Pros:** Full control, cost-effective
**Cost:** ~$10-30/month

#### Steps:

1. Launch EC2 instance (Ubuntu 22.04, t3.small or larger)

2. SSH into instance:
```bash
ssh -i your-key.pem ubuntu@your-ec2-ip
```

3. Install dependencies:
```bash
sudo apt update
sudo apt install python3-pip python3-venv nginx -y
```

4. Clone/upload your application:
```bash
mkdir /home/ubuntu/protocolscout
cd /home/ubuntu/protocolscout
# Upload your files here
```

5. Create virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

6. Configure environment variables:
```bash
nano .env
# Add your AWS credentials
```

7. Create systemd service:
```bash
sudo nano /etc/systemd/system/protocolscout.service
```

Add:
```ini
[Unit]
Description=ProtocolScout Flask Application
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/protocolscout
Environment="PATH=/home/ubuntu/protocolscout/venv/bin"
EnvironmentFile=/home/ubuntu/protocolscout/.env
ExecStart=/home/ubuntu/protocolscout/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 app:app

[Install]
WantedBy=multi-user.target
```

8. Configure Nginx:
```bash
sudo nano /etc/nginx/sites-available/protocolscout
```

Add:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

9. Enable and start services:
```bash
sudo ln -s /etc/nginx/sites-available/protocolscout /etc/nginx/sites-enabled/
sudo systemctl start protocolscout
sudo systemctl enable protocolscout
sudo systemctl restart nginx
```

10. Configure SSL with Let's Encrypt:
```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d your-domain.com
```

### Option 3: Docker Container

**Pros:** Portable, consistent environments
**Cost:** Depends on hosting platform

#### Dockerfile:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

#### Build and run:

```bash
docker build -t protocolscout-web .
docker run -p 5000:5000 --env-file .env protocolscout-web
```

#### Deploy to AWS ECS/Fargate:

1. Push to ECR:
```bash
aws ecr create-repository --repository-name protocolscout-web
docker tag protocolscout-web:latest <account-id>.dkr.ecr.ap-south-1.amazonaws.com/protocolscout-web:latest
docker push <account-id>.dkr.ecr.ap-south-1.amazonaws.com/protocolscout-web:latest
```

2. Create ECS task definition and service via AWS Console

### Option 4: Serverless (AWS Lambda + API Gateway)

**Pros:** Pay per request, auto-scaling, no server management
**Cost:** Very low for low traffic

Use Zappa or AWS SAM to deploy Flask as Lambda function.

## Security Best Practices

### 1. Use IAM Roles Instead of Access Keys

For EC2/ECS deployments, attach IAM role to instance:

```bash
# Don't use AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in .env
# Instead, attach IAM role to EC2 instance
```

### 2. Enable HTTPS

Always use SSL/TLS in production:
- Use AWS Certificate Manager (ACM) for free certificates
- Or use Let's Encrypt with Certbot

### 3. Secure Environment Variables

- Never commit `.env` to version control
- Use AWS Systems Manager Parameter Store or Secrets Manager
- Rotate credentials regularly

### 4. Configure Security Groups

EC2 Security Group rules:
- Port 80 (HTTP): 0.0.0.0/0
- Port 443 (HTTPS): 0.0.0.0/0
- Port 22 (SSH): Your IP only

### 5. Enable CloudWatch Logging

```python
import logging
from logging.handlers import CloudWatchLogHandler

logger = logging.getLogger(__name__)
handler = CloudWatchLogHandler(log_group='protocolscout-web')
logger.addHandler(handler)
```

### 6. Set Strong SECRET_KEY

```python
import secrets
print(secrets.token_hex(32))
```

## Performance Optimization

### 1. Use Gunicorn with Multiple Workers

```bash
gunicorn -w 4 -b 0.0.0.0:5000 --timeout 300 app:app
```

Workers = (2 × CPU cores) + 1

### 2. Enable Caching

Add Flask-Caching:
```python
from flask_caching import Cache
cache = Cache(app, config={'CACHE_TYPE': 'simple'})
```

### 3. Use CDN for Static Assets

- Upload static files to S3
- Enable CloudFront CDN
- Update templates to use CDN URLs

### 4. Database Connection Pooling

Already handled by boto3 for DynamoDB.

### 5. Enable Gzip Compression

In Nginx:
```nginx
gzip on;
gzip_types text/plain text/css application/json application/javascript;
```

## Monitoring and Logging

### 1. CloudWatch Metrics

Monitor:
- Lambda invocations and errors
- API Gateway requests
- DynamoDB read/write capacity
- S3 bucket size

### 2. Application Logging

```python
import logging
logging.basicConfig(level=logging.INFO)
```

### 3. Error Tracking

Consider integrating:
- Sentry
- Rollbar
- AWS X-Ray

### 4. Uptime Monitoring

Use:
- AWS CloudWatch Alarms
- UptimeRobot
- Pingdom

## Scaling Considerations

### Auto-Scaling

For EC2:
1. Create AMI from configured instance
2. Create Launch Template
3. Create Auto Scaling Group
4. Configure scaling policies

For Elastic Beanstalk:
- Auto-scaling is built-in
- Configure in EB console

### Load Balancing

- Use Application Load Balancer (ALB)
- Configure health checks
- Enable sticky sessions if needed

## Backup and Disaster Recovery

### 1. DynamoDB Backups

Enable point-in-time recovery (already enabled in setup).

### 2. S3 Versioning

Already enabled in setup.

### 3. Database Exports

Schedule regular DynamoDB exports to S3:
```bash
aws dynamodb export-table-to-point-in-time \
  --table-arn arn:aws:dynamodb:ap-south-1:xxx:table/compliance_rules \
  --s3-bucket protocolscout-backups \
  --export-format DYNAMODB_JSON
```

## Cost Optimization

### 1. Use Reserved Instances

For EC2, purchase 1-year reserved instances for 40% savings.

### 2. Enable S3 Lifecycle Policies

Move old reports to S3 Glacier after 90 days.

### 3. Use DynamoDB On-Demand

Already configured - only pay for what you use.

### 4. Monitor Costs

- Set up AWS Budgets
- Enable Cost Explorer
- Review monthly bills

## Troubleshooting Production Issues

### Check Application Logs

```bash
# Systemd service logs
sudo journalctl -u protocolscout -f

# Nginx logs
sudo tail -f /var/log/nginx/error.log
```

### Check AWS Lambda Logs

```bash
aws logs tail /aws/lambda/protocolscout-upload-handler --follow
```

### Test Lambda Functions

```bash
aws lambda invoke \
  --function-name protocolscout-status-checker \
  --payload '{"protocol_id":"test"}' \
  response.json
```

## Rollback Procedure

### Elastic Beanstalk

```bash
eb deploy --version previous-version
```

### EC2

1. Stop application: `sudo systemctl stop protocolscout`
2. Restore previous code
3. Start application: `sudo systemctl start protocolscout`

## Support and Maintenance

### Regular Maintenance Tasks

- [ ] Weekly: Review CloudWatch logs for errors
- [ ] Monthly: Update Python dependencies
- [ ] Monthly: Review AWS costs
- [ ] Quarterly: Security audit
- [ ] Quarterly: Performance review

### Update Procedure

1. Test updates in staging environment
2. Create backup
3. Deploy to production during low-traffic period
4. Monitor for errors
5. Rollback if issues occur

---

**Need help?** Check CloudWatch logs and Lambda function execution history for detailed error messages.
