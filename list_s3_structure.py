#!/usr/bin/env python3
"""
List S3 bucket structure to find report locations
"""

import boto3
from dotenv import load_dotenv
import os

load_dotenv()

def list_bucket_structure(protocol_id=None):
    """List all files in the documents bucket"""
    try:
        s3 = boto3.client('s3', region_name=os.environ.get('AWS_REGION'))
        bucket = os.environ.get('DOCUMENTS_BUCKET')
        
        print(f"📦 Bucket: {bucket}")
        print("="*70)
        
        if protocol_id:
            # List specific protocol
            print(f"\n🔍 Files for protocol: {protocol_id}\n")
            
            response = s3.list_objects_v2(
                Bucket=bucket,
                Prefix=protocol_id
            )
            
            if 'Contents' in response:
                for obj in response['Contents']:
                    size_kb = obj['Size'] / 1024
                    print(f"  {obj['Key']}")
                    print(f"    Size: {size_kb:.2f} KB")
                    print(f"    Modified: {obj['LastModified']}")
                    print()
            else:
                print(f"  ❌ No files found with prefix: {protocol_id}")
            
            # Also check reports folder
            print(f"\n🔍 Checking reports folder...\n")
            response = s3.list_objects_v2(
                Bucket=bucket,
                Prefix=f"reports/{protocol_id}"
            )
            
            if 'Contents' in response:
                for obj in response['Contents']:
                    size_kb = obj['Size'] / 1024
                    print(f"  {obj['Key']}")
                    print(f"    Size: {size_kb:.2f} KB")
                    print(f"    Modified: {obj['LastModified']}")
                    print()
            else:
                print(f"  ❌ No files found in: reports/{protocol_id}")
                
        else:
            # List all folders
            print("\n📁 Bucket Structure:\n")
            
            response = s3.list_objects_v2(
                Bucket=bucket,
                Delimiter='/'
            )
            
            if 'CommonPrefixes' in response:
                print("Top-level folders:")
                for prefix in response['CommonPrefixes']:
                    print(f"  📁 {prefix['Prefix']}")
                    
                    # List contents of each folder
                    folder_response = s3.list_objects_v2(
                        Bucket=bucket,
                        Prefix=prefix['Prefix'],
                        MaxKeys=5
                    )
                    
                    if 'Contents' in folder_response:
                        count = len(folder_response['Contents'])
                        print(f"     ({count}+ files)")
                        
                        # Show first few files
                        for obj in folder_response['Contents'][:3]:
                            print(f"       - {obj['Key']}")
                    print()
            
            # List recent protocols
            print("\n📄 Recent Protocol Files (last 10):\n")
            response = s3.list_objects_v2(
                Bucket=bucket,
                MaxKeys=10
            )
            
            if 'Contents' in response:
                # Sort by last modified
                sorted_objects = sorted(response['Contents'], key=lambda x: x['LastModified'], reverse=True)
                
                for obj in sorted_objects[:10]:
                    size_kb = obj['Size'] / 1024
                    print(f"  {obj['Key']}")
                    print(f"    Size: {size_kb:.2f} KB | Modified: {obj['LastModified']}")
                    print()
                    
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        protocol_id = sys.argv[1]
        list_bucket_structure(protocol_id)
    else:
        print("Usage: python list_s3_structure.py [protocol_id]")
        print("\nExamples:")
        print("  python list_s3_structure.py                           # List all")
        print("  python list_s3_structure.py PROTO-1773011406-06D8B47C # List specific protocol")
        print("\n" + "="*70)
        list_bucket_structure()
