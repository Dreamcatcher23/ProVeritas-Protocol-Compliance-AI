#!/usr/bin/env python3
"""
Check AWS Setup and Find Correct Configuration
"""

import boto3
from dotenv import load_dotenv
import os

load_dotenv()

def print_section(title):
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def check_s3_buckets():
    print_section("S3 Buckets")
    try:
        s3 = boto3.client('s3', region_name=os.environ.get('AWS_REGION'))
        response = s3.list_buckets()
        
        documents_buckets = []
        rules_buckets = []
        
        for bucket in response['Buckets']:
            name = bucket['Name']
            if 'protocolscout' in name.lower():
                if 'document' in name.lower():
                    documents_buckets.append(name)
                    print(f"✅ Documents Bucket: {name}")
                elif 'rule' in name.lower():
                    rules_buckets.append(name)
                    print(f"✅ Rules Bucket: {name}")
        
        if documents_buckets:
            print(f"\n📝 Update .env with:")
            print(f"DOCUMENTS_BUCKET={documents_buckets[0]}")
            return documents_buckets[0]
        else:
            print("❌ No protocolscout-documents bucket found!")
            print("\nAll buckets:")
            for bucket in response['Buckets']:
                print(f"  - {bucket['Name']}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def check_lambda_functions():
    print_section("Lambda Functions")
    try:
        lambda_client = boto3.client('lambda', region_name=os.environ.get('AWS_REGION'))
        
        functions = [
            'protocolscout-upload-handler',
            'protocolscout-ocr-processor',
            'protocolscout-entity-extractor',
            'protocolscout-compliance-engine',
            'protocolscout-report-generator',
            'protocolscout-status-checker'
        ]
        
        found_bucket = None
        
        for func_name in functions:
            try:
                response = lambda_client.get_function_configuration(FunctionName=func_name)
                env_vars = response.get('Environment', {}).get('Variables', {})
                bucket = env_vars.get('DOCUMENTS_BUCKET', 'Not set')
                
                print(f"✅ {func_name}")
                print(f"   DOCUMENTS_BUCKET: {bucket}")
                
                if bucket != 'Not set' and not found_bucket:
                    found_bucket = bucket
                    
            except Exception as e:
                print(f"❌ {func_name}: {str(e)}")
        
        if found_bucket:
            print(f"\n📝 Lambda functions are using: {found_bucket}")
            return found_bucket
        
        return None
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def check_dynamodb_tables():
    print_section("DynamoDB Tables")
    try:
        dynamodb = boto3.client('dynamodb', region_name=os.environ.get('AWS_REGION'))
        
        tables = ['compliance_rules', 'protocol_audit', 'compliance_results']
        
        for table_name in tables:
            try:
                response = dynamodb.describe_table(TableName=table_name)
                item_count = response['Table'].get('ItemCount', 0)
                print(f"✅ {table_name} (Items: {item_count})")
            except Exception as e:
                print(f"❌ {table_name}: Not found")
                
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    print("\n🔍 ProtocolScout AWS Configuration Checker")
    
    # Check S3
    s3_bucket = check_s3_buckets()
    
    # Check Lambda
    lambda_bucket = check_lambda_functions()
    
    # Check DynamoDB
    check_dynamodb_tables()
    
    # Recommendation
    print_section("Recommendation")
    
    correct_bucket = lambda_bucket or s3_bucket
    
    if correct_bucket:
        print(f"\n✅ Use this bucket name in your .env file:")
        print(f"\nDOCUMENTS_BUCKET={correct_bucket}")
        
        # Update .env file
        print(f"\n📝 Updating .env file...")
        
        with open('.env', 'r') as f:
            lines = f.readlines()
        
        with open('.env', 'w') as f:
            for line in lines:
                if line.startswith('DOCUMENTS_BUCKET='):
                    f.write(f'DOCUMENTS_BUCKET={correct_bucket}\n')
                else:
                    f.write(line)
        
        print(f"✅ .env file updated with: DOCUMENTS_BUCKET={correct_bucket}")
        print(f"\n🔄 Restart your Flask app: python app.py")
    else:
        print("❌ Could not find the correct bucket name.")
        print("\nPlease check:")
        print("1. AWS Console → S3 → Look for protocolscout-documents-* bucket")
        print("2. AWS Console → Lambda → Check environment variables")

if __name__ == '__main__':
    main()
