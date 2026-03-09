"""
Check protocol status in DynamoDB
"""
import boto3
import os
from dotenv import load_dotenv

load_dotenv()

AWS_REGION = os.environ.get('AWS_REGION', 'ap-south-1')
DOCUMENTS_BUCKET = os.environ.get('DOCUMENTS_BUCKET', 'protocolscout-documents')

dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
s3_client = boto3.client('s3', region_name=AWS_REGION)
audit_table = dynamodb.Table('protocol_audit')

def check_protocol(protocol_id):
    """Check protocol status"""
    print(f"\n{'='*70}")
    print(f"Checking Protocol: {protocol_id}")
    print(f"{'='*70}\n")
    
    # Check DynamoDB
    try:
        response = audit_table.scan(
            FilterExpression='protocol_id = :pid',
            ExpressionAttributeValues={':pid': protocol_id}
        )
        
        items = response.get('Items', [])
        if items:
            print("📋 DynamoDB Record:")
            for key, value in items[0].items():
                print(f"  {key}: {value}")
        else:
            print("❌ No DynamoDB record found")
    except Exception as e:
        print(f"❌ DynamoDB Error: {str(e)}")
    
    # Check S3 reports
    print(f"\n📦 S3 Reports:")
    try:
        report_key = f"reports/{protocol_id}/compliance_report.json"
        s3_client.head_object(Bucket=DOCUMENTS_BUCKET, Key=report_key)
        print(f"  ✅ JSON report exists: {report_key}")
    except:
        print(f"  ❌ JSON report not found")
    
    try:
        report_key = f"reports/{protocol_id}/compliance_report.txt"
        s3_client.head_object(Bucket=DOCUMENTS_BUCKET, Key=report_key)
        print(f"  ✅ TXT report exists: {report_key}")
    except:
        print(f"  ❌ TXT report not found")
    
    print(f"\n{'='*70}\n")

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        protocol_id = sys.argv[1]
        check_protocol(protocol_id)
    else:
        print("Usage: python check_protocol_status.py PROTO-xxx")
