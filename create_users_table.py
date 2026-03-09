"""
Script to create the DynamoDB users table for authentication
Run this once to set up the users table in your AWS account
"""
import boto3
from botocore.exceptions import ClientError
import os
from dotenv import load_dotenv

load_dotenv()

AWS_REGION = os.environ.get('AWS_REGION', 'ap-south-1')

def create_users_table():
    """Create the users table in DynamoDB"""
    dynamodb = boto3.client('dynamodb', region_name=AWS_REGION)
    
    try:
        # Check if table already exists
        try:
            dynamodb.describe_table(TableName='users')
            print("✅ Table 'users' already exists!")
            return
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceNotFoundException':
                raise
        
        # Create table
        print("Creating 'users' table...")
        
        response = dynamodb.create_table(
            TableName='users',
            KeySchema=[
                {
                    'AttributeName': 'email',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'email',
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PAY_PER_REQUEST'  # On-demand billing
        )
        
        print("⏳ Waiting for table to be created...")
        
        # Wait for table to be created
        waiter = dynamodb.get_waiter('table_exists')
        waiter.wait(TableName='users')
        
        print("✅ Table 'users' created successfully!")
        print("\nTable details:")
        print(f"  - Table Name: users")
        print(f"  - Primary Key: email (String)")
        print(f"  - Billing Mode: PAY_PER_REQUEST")
        print(f"  - Region: {AWS_REGION}")
        
    except ClientError as e:
        print(f"❌ Error creating table: {e.response['Error']['Message']}")
        raise
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        raise

if __name__ == '__main__':
    print("="*70)
    print("ProtocolScout - DynamoDB Users Table Setup")
    print("="*70)
    print()
    
    create_users_table()
    
    print()
    print("="*70)
    print("Setup complete! You can now use the authentication system.")
    print("="*70)
