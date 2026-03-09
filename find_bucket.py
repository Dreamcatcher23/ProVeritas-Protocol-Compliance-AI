#!/usr/bin/env python3
"""
Find the correct S3 bucket name for ProtocolScout
"""

import boto3
from dotenv import load_dotenv

load_dotenv()

print("🔍 Finding your ProtocolScout S3 buckets...\n")

try:
    s3 = boto3.client('s3')
    
    # List all buckets
    response = s3.list_buckets()
    
    # Filter for protocolscout buckets
    protocolscout_buckets = []
    
    for bucket in response['Buckets']:
        bucket_name = bucket['Name']
        if 'protocolscout' in bucket_name.lower():
            protocolscout_buckets.append(bucket_name)
            print(f"✅ Found: {bucket_name}")
    
    if not protocolscout_buckets:
        print("❌ No ProtocolScout buckets found!")
        print("\nAll your buckets:")
        for bucket in response['Buckets']:
            print(f"  - {bucket['Name']}")
    else:
        print(f"\n📋 Found {len(protocolscout_buckets)} ProtocolScout bucket(s)")
        print("\nUpdate your .env file with:")
        print("-" * 60)
        
        # Find documents bucket
        docs_bucket = None
        for bucket in protocolscout_buckets:
            if 'document' in bucket.lower():
                docs_bucket = bucket
                break
        
        if docs_bucket:
            print(f"DOCUMENTS_BUCKET={docs_bucket}")
        else:
            print(f"DOCUMENTS_BUCKET={protocolscout_buckets[0]}")
        
        print("-" * 60)

except Exception as e:
    print(f"❌ Error: {e}")
    print("\nMake sure your AWS credentials are correct in .env file")
