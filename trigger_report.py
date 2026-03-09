#!/usr/bin/env python3
"""
Manually trigger report generation for a protocol
"""

import boto3
import json
import sys
from dotenv import load_dotenv
import os

load_dotenv()

def trigger_report_generation(protocol_id, format='pdf'):
    """Trigger report generator Lambda"""
    try:
        lambda_client = boto3.client('lambda', region_name=os.environ.get('AWS_REGION'))
        
        print(f"🚀 Triggering report generation for: {protocol_id}")
        print(f"   Format: {format}")
        
        response = lambda_client.invoke(
            FunctionName='protocolscout-report-generator',
            InvocationType='RequestResponse',  # Wait for response
            Payload=json.dumps({
                'protocol_id': protocol_id,
                'format': format
            })
        )
        
        # Parse response
        response_payload = json.loads(response['Payload'].read())
        
        print(f"\n✅ Response:")
        print(json.dumps(response_payload, indent=2))
        
        if response_payload.get('statusCode') == 200:
            print(f"\n✅ Report generation triggered successfully!")
            print(f"   Check S3 bucket for: reports/{protocol_id}/compliance_report.{format}")
        else:
            print(f"\n❌ Report generation failed")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def check_s3_for_reports(protocol_id):
    """Check if reports exist in S3"""
    try:
        s3 = boto3.client('s3', region_name=os.environ.get('AWS_REGION'))
        bucket = os.environ.get('DOCUMENTS_BUCKET')
        
        print(f"\n🔍 Checking S3 for existing reports...")
        print(f"   Bucket: {bucket}")
        print(f"   Protocol: {protocol_id}")
        
        # List objects with protocol_id prefix
        response = s3.list_objects_v2(
            Bucket=bucket,
            Prefix=f"reports/{protocol_id}/"
        )
        
        if 'Contents' in response:
            print(f"\n✅ Found {len(response['Contents'])} file(s):")
            for obj in response['Contents']:
                size_kb = obj['Size'] / 1024
                print(f"   - {obj['Key']} ({size_kb:.2f} KB)")
        else:
            print(f"\n❌ No reports found in S3")
            print(f"   Looking for: reports/{protocol_id}/")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python trigger_report.py <protocol_id> [format]")
        print("\nExample:")
        print("  python trigger_report.py PROTO-1773011406-06D8B47C pdf")
        print("\nFormats: pdf, docx, json")
        sys.exit(1)
    
    protocol_id = sys.argv[1]
    format = sys.argv[2] if len(sys.argv) > 2 else 'pdf'
    
    # Check existing reports
    check_s3_for_reports(protocol_id)
    
    # Trigger report generation
    print("\n" + "="*70)
    trigger_report_generation(protocol_id, format)
