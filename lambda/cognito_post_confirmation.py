import json
import os
import boto3
from datetime import datetime


def lambda_handler(event, context):
    """
    Cognito Post Confirmation trigger to provision user in DynamoDB.
    
    This function is triggered after a user confirms their signup/email in Cognito.
    It automatically creates user records in two DynamoDB tables:
    - lotus-lms-users: Main user profile table
    - lms-user-tenant-mapping: User-tenant relationship table
    
    Args:
        event: Cognito Post Confirmation trigger event containing user attributes
        context: Lambda context object
    
    Returns:
        event: The original event object unchanged (required by Cognito)
    """
    print("Post Confirmation Event:", json.dumps(event))
    
    # Extract user data from Cognito event
    user_id = event['userName']
    user_attrs = event['request']['userAttributes']
    email = user_attrs.get('email', '')
    username = user_attrs.get('custom:username', email)
    full_name = user_attrs.get('name', '')
    
    # Get current timestamp in ISO 8601 format
    created_at = datetime.utcnow().isoformat() + 'Z'
    
    # Get DynamoDB table names from environment variables
    users_table_name = os.environ.get('USERS_TABLE', 'lotus-lms-users')
    user_tenant_mapping_table_name = os.environ.get('USER_TENANT_MAPPING_TABLE', 'lms-user-tenant-mapping')
    
    # Initialize DynamoDB resource
    dynamodb = boto3.resource('dynamodb')
    users_table = dynamodb.Table(users_table_name)
    user_tenant_mapping_table = dynamodb.Table(user_tenant_mapping_table_name)
    
    # Insert user record into lotus-lms-users table
    try:
        user_item = {
            'user_id': user_id,
            'email': email,
            'username': username,
            'full_name': full_name,
            'created_at': created_at,
            'status': 'active'
        }
        
        print(f"Creating user record in {users_table_name}: {user_item}")
        users_table.put_item(Item=user_item)
        print(f"Successfully created user record for {user_id}")
        
    except Exception as e:
        print(f"Error creating user record: {str(e)}")
        import traceback
        print(f"Stack trace: {traceback.format_exc()}")
    
    # Insert user-tenant mapping into lms-user-tenant-mapping table
    try:
        user_tenant_item = {
            'user_id': user_id,
            'tenant_id': 'trainer1',
            'role': 'student',
            'email': email,
            'created_at': created_at
        }
        
        print(f"Creating tenant mapping in {user_tenant_mapping_table_name}: {user_tenant_item}")
        user_tenant_mapping_table.put_item(Item=user_tenant_item)
        print(f"Successfully created tenant mapping for {user_id}")
        
    except Exception as e:
        print(f"Error creating tenant mapping: {str(e)}")
        import traceback
        print(f"Stack trace: {traceback.format_exc()}")
    
    # MUST return the event for Cognito to complete the signup flow
    return event
