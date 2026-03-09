#!/usr/bin/env python3
"""
ProtocolScout Configuration Checker
Verifies AWS setup and connectivity
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def print_header(text):
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60)

def print_status(check_name, status, message=""):
    status_icon = "✅" if status else "❌"
    print(f"{status_icon} {check_name}: {message if message else ('OK' if status else 'FAILED')}")

def check_environment_variables():
    print_header("Checking Environment Variables")
    
    required_vars = {
        'AWS_REGION': 'AWS Region',
        'AWS_ACCESS_KEY_ID': 'AWS Access Key ID',
        'AWS_SECRET_ACCESS_KEY': 'AWS Secret Access Key',
        'DOCUMENTS_BUCKET': 'S3 Documents Bucket',
        'SECRET_KEY': 'Flask Secret Key'
    }
    
    all_ok = True
    for var, description in required_vars.items():
        value = os.environ.get(var)
        if value:
            # Mask sensitive values
            if 'KEY' in var or 'SECRET' in var:
                display_value = value[:4] + "..." + value[-4:] if len(value) > 8 else "***"
            else:
                display_value = value
            print_status(description, True, display_value)
        else:
            print_status(description, False, "Not set")
            all_ok = False
    
    return all_ok

def check_aws_connectivity():
    print_header("Checking AWS Connectivity")
    
    try:
        import boto3
        
        # Check AWS credentials
        try:
            sts = boto3.client('sts')
            identity = sts.get_caller_identity()
            print_status("AWS Credentials", True, f"Account: {identity['Account']}")
        except Exception as e:
            print_status("AWS Credentials", False, str(e))
            return False
        
        # Check S3 bucket
        try:
            s3 = boto3.client('s3', region_name=os.environ.get('AWS_REGION'))
            bucket = os.environ.get('DOCUMENTS_BUCKET')
            s3.head_bucket(Bucket=bucket)
            print_status("S3 Bucket Access", True, bucket)
        except Exception as e:
            print_status("S3 Bucket Access", False, str(e))
            return False
        
        # Check DynamoDB tables
        try:
            dynamodb = boto3.client('dynamodb', region_name=os.environ.get('AWS_REGION'))
            
            tables_to_check = ['compliance_rules', 'protocol_audit', 'compliance_results']
            for table_name in tables_to_check:
                try:
                    dynamodb.describe_table(TableName=table_name)
                    print_status(f"DynamoDB Table: {table_name}", True)
                except:
                    print_status(f"DynamoDB Table: {table_name}", False, "Not found")
        except Exception as e:
            print_status("DynamoDB Access", False, str(e))
        
        # Check Lambda functions
        try:
            lambda_client = boto3.client('lambda', region_name=os.environ.get('AWS_REGION'))
            
            functions_to_check = [
                'protocolscout-upload-handler',
                'protocolscout-ocr-processor',
                'protocolscout-entity-extractor',
                'protocolscout-compliance-engine',
                'protocolscout-report-generator',
                'protocolscout-status-checker'
            ]
            
            for func_name in functions_to_check:
                try:
                    lambda_client.get_function(FunctionName=func_name)
                    print_status(f"Lambda: {func_name}", True)
                except:
                    print_status(f"Lambda: {func_name}", False, "Not found")
        except Exception as e:
            print_status("Lambda Access", False, str(e))
        
        return True
        
    except ImportError:
        print_status("boto3 library", False, "Not installed. Run: pip install boto3")
        return False

def check_python_dependencies():
    print_header("Checking Python Dependencies")
    
    required_packages = [
        'flask',
        'boto3',
        'werkzeug',
        'python-dotenv',
        'gunicorn'
    ]
    
    all_ok = True
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print_status(package, True)
        except ImportError:
            print_status(package, False, "Not installed")
            all_ok = False
    
    return all_ok

def main():
    print("\n" + "🔍 ProtocolScout Configuration Checker".center(60))
    
    # Check .env file
    if not os.path.exists('.env'):
        print("\n❌ ERROR: .env file not found!")
        print("Please create .env file from .env.example")
        print("\nRun: cp .env.example .env")
        print("Then edit .env with your AWS credentials")
        sys.exit(1)
    
    print("✅ .env file found")
    
    # Run checks
    env_ok = check_environment_variables()
    deps_ok = check_python_dependencies()
    aws_ok = check_aws_connectivity()
    
    # Summary
    print_header("Summary")
    
    if env_ok and deps_ok and aws_ok:
        print("\n✅ All checks passed! Your configuration is ready.")
        print("\nYou can now run the application:")
        print("  python app.py")
        print("\nOr use the startup script:")
        print("  ./run.sh (Linux/Mac)")
        print("  run.bat (Windows)")
        sys.exit(0)
    else:
        print("\n❌ Some checks failed. Please fix the issues above.")
        print("\nCommon fixes:")
        print("  - Install dependencies: pip install -r requirements.txt")
        print("  - Configure .env file with AWS credentials")
        print("  - Verify AWS Lambda functions are deployed")
        print("  - Check AWS IAM permissions")
        sys.exit(1)

if __name__ == '__main__':
    main()
