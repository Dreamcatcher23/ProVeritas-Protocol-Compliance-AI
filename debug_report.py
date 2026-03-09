#!/usr/bin/env python3
"""
Debug script to check S3 report structure
"""

import boto3
import json
import sys
from dotenv import load_dotenv
import os

load_dotenv()

def check_report(protocol_id):
    """Check the JSON report structure"""
    try:
        s3 = boto3.client('s3', region_name=os.environ.get('AWS_REGION'))
        bucket = os.environ.get('DOCUMENTS_BUCKET')
        
        report_key = f"reports/{protocol_id}/compliance_report.json"
        
        print(f"📄 Fetching: s3://{bucket}/{report_key}\n")
        
        response = s3.get_object(Bucket=bucket, Key=report_key)
        report_data = json.loads(response['Body'].read())
        
        print("✅ Report found!")
        print("\n" + "="*70)
        print("REPORT STRUCTURE:")
        print("="*70)
        print(json.dumps(report_data, indent=2))
        
        print("\n" + "="*70)
        print("KEY FIELDS:")
        print("="*70)
        print(f"Keys in report: {list(report_data.keys())}")
        
        if 'compliance_score' in report_data:
            print(f"✅ compliance_score: {report_data['compliance_score']}")
        else:
            print("❌ compliance_score: NOT FOUND")
            
        if 'total_rules_checked' in report_data:
            print(f"✅ total_rules_checked: {report_data['total_rules_checked']}")
        else:
            print("❌ total_rules_checked: NOT FOUND")
            
        if 'gaps' in report_data:
            print(f"✅ gaps: {len(report_data['gaps'])} violations found")
            if report_data['gaps']:
                print("\nFirst gap structure:")
                print(json.dumps(report_data['gaps'][0], indent=2))
        else:
            print("❌ gaps: NOT FOUND")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python debug_report.py <protocol_id>")
        print("\nExample:")
        print("  python debug_report.py PROTO-1773042761-0DE44027")
        sys.exit(1)
    
    protocol_id = sys.argv[1]
    check_report(protocol_id)
