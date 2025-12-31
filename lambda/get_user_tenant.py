import os
import json
import boto3
from decimal import Decimal

# ----------------------------
# DynamoDB setup
# ----------------------------
TABLE_NAME = os.environ.get("USER_TENANT_TABLE", "lms-user-tenant-mapping")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)


# ----------------------------
# JSON Serializer for Decimal
# ----------------------------
def default_serializer(obj):
    """Convert Decimal types to int or float for JSON serialization."""
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


# ----------------------------
# Unified HTTP Response with CORS
# ----------------------------
def response(status_code, body):
    """Return standardized API Gateway response with CORS headers."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type,X-Tenant-Id,Authorization",
        },
        "body": json.dumps(body, default=default_serializer),
    }


# ----------------------------
# Lambda Handler
# ----------------------------
def lambda_handler(event, context):
    """
    Lambda handler for retrieving user-tenant mapping from DynamoDB.
    
    Expected input:
    - user_id (required): User ID from query parameters or path parameters
    
    Returns:
    - 200: User mapping found
    - 400: Missing user_id parameter
    - 404: User mapping not found
    - 500: Internal server error
    """
    print("Event:", json.dumps(event))
    
    try:
        # Handle CORS Preflight
        http_method = event.get("httpMethod") or event.get("requestContext", {}).get("http", {}).get("method", "")
        if http_method == "OPTIONS":
            return response(200, {"message": "CORS preflight success"})
        
        # Extract user_id from path parameters or query parameters
        user_id = None
        
        # Try path parameters first
        path_params = event.get("pathParameters") or {}
        if path_params:
            user_id = path_params.get("user_id")
        
        # Fallback to query parameters
        if not user_id:
            query_params = event.get("queryStringParameters") or {}
            user_id = query_params.get("user_id")
        
        # Validate user_id is provided
        if not user_id:
            print("Missing user_id parameter")
            return response(400, {
                "error": "Missing required parameter: user_id"
            })
        
        # Query DynamoDB for user-tenant mapping
        try:
            print(f"Querying DynamoDB for user_id: {user_id}")
            result = table.get_item(Key={"user_id": user_id})
            
            item = result.get("Item")
            if not item:
                print(f"User mapping not found for user_id: {user_id}")
                return response(404, {
                    "error": "User mapping not found",
                    "user_id": user_id
                })
            
            print(f"User mapping found: {item}")
            return response(200, item)
            
        except Exception as db_error:
            print(f"DynamoDB error: {str(db_error)}")
            return response(500, {
                "error": "Internal server error",
                "details": str(db_error)
            })
        
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return response(500, {
            "error": "Internal server error",
            "details": str(e)
        })
