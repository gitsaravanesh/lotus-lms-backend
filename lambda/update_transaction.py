import os
import json
import boto3
from decimal import Decimal
from datetime import datetime, timezone

# ----------------------------
# DynamoDB setup
# ----------------------------
TABLE_NAME = os.environ.get("TRANSACTIONS_TABLE", "lms-transactions")
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
            "Access-Control-Allow-Methods": "POST,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type,X-Tenant-Id,Authorization",
        },
        "body": json.dumps(body, default=default_serializer),
    }


# ----------------------------
# Lambda Handler
# ----------------------------
def lambda_handler(event, context):
    """
    Lambda handler for updating transaction status in DynamoDB.
    
    Expected input:
    - razorpay_payment_id (required): Razorpay payment ID
    - razorpay_order_id (required): Razorpay order ID
    - status (required): Payment status ("success" or "failed")
    - amount (optional): Payment amount
    - currency (optional): Currency code (default: INR)
    - user_id (optional): User ID
    - course_id (optional): Course ID
    - email (optional): User email
    - phone (optional): User phone number
    - razorpay_signature (optional): Razorpay signature for verification
    
    Returns:
    - 200: Transaction updated successfully
    - 400: Invalid input (missing fields, invalid status, etc.)
    - 500: Internal server error
    """
    print("Event:", json.dumps(event))
    
    try:
        # Handle CORS Preflight
        http_method = event.get("httpMethod") or event.get("requestContext", {}).get("http", {}).get("method", "")
        if http_method == "OPTIONS":
            return response(200, {"message": "CORS preflight success"})
        
        # Parse request body
        body = event.get("body", "{}")
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {str(e)}")
                return response(400, {
                    "error": "Invalid JSON format",
                    "details": str(e)
                })
                
        tenant_id = event.get("headers", {}).get("X-Tenant-Id") or event.get("headers", {}).get("x-tenant-id")

        if not tenant_id:
            print("Missing tenant_id in headers")
            return response(400, {
                "error": "Missing required header",
                "details": "X-Tenant-Id header is required"
            })
        # Validate required fields
        razorpay_payment_id = body.get("razorpay_payment_id")
        razorpay_order_id = body.get("razorpay_order_id")
        status = body.get("status")
        
        missing_fields = []
        if not razorpay_payment_id:
            missing_fields.append("razorpay_payment_id")
        if not razorpay_order_id:
            missing_fields.append("razorpay_order_id")
        if not status:
            missing_fields.append("status")
        
        if missing_fields:
            print(f"Missing required fields: {missing_fields}")
            return response(400, {
                "error": "Missing required fields",
                "missing_fields": missing_fields
            })
        
        # Validate status value
        if status not in ["success", "failed"]:
            print(f"Invalid status value: {status}")
            return response(400, {
                "error": "Invalid status value",
                "details": "Status must be either 'success' or 'failed'"
            })
        
        # Prepare transaction item
        timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        transaction_item = {
            "tenant_id": tenant_id,
            "transaction_id": razorpay_payment_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_order_id": razorpay_order_id,
            "status": status,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        
        # Add optional fields if provided
        optional_fields = [
            "amount", "currency", "user_id", "course_id", 
            "email", "phone", "razorpay_signature"
        ]
        
        for field in optional_fields:
            if field in body and body[field] is not None:
                value = body[field]
                # Convert amount to Decimal if provided
                if field == "amount":
                    try:
                        value = Decimal(str(value))
                    except (ValueError, TypeError) as e:
                        print(f"Invalid amount value: {value}, error: {str(e)}")
                        return response(400, {
                            "error": "Invalid amount value",
                            "details": "Amount must be a valid number"
                        })
                transaction_item[field] = value
        
        # Set default currency if not provided
        if "currency" not in transaction_item:
            transaction_item["currency"] = "INR"
        
        # Store in DynamoDB
        try:
            print(f"Storing transaction: {transaction_item}")
            table.put_item(Item=transaction_item)
            print(f"Transaction stored successfully: {razorpay_payment_id}")
        except Exception as db_error:
            print(f"DynamoDB error: {str(db_error)}")
            return response(500, {
                "error": "Failed to store transaction",
                "details": str(db_error)
            })
        
        # Return success response
        return response(200, {
            "message": "Transaction updated successfully",
            "transaction_id": razorpay_payment_id,
            "status": status,
            "timestamp": timestamp
        })
        
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return response(500, {
            "error": "Internal server error",
            "details": str(e)
        })
