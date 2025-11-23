import os
import json
import boto3
import logging
from datetime import datetime
from decimal import Decimal

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize DynamoDB
dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ.get("TRANSACTIONS_TABLE", "lms-transactions")
table = dynamodb.Table(TABLE_NAME)


class DecimalEncoder(json.JSONEncoder):
    """Helper class to convert a DynamoDB item to JSON serializable types."""
    def default(self, o):
        if isinstance(o, Decimal):
            # Convert Decimal to int if it's integral, otherwise float
            if o % 1 == 0:
                return int(o)
            else:
                return float(o)
        return super(DecimalEncoder, self).default(o)


def build_response(status_code: int, body: dict):
    """Standard API Gateway response with CORS headers."""
    # Get allowed origin from environment variable or default to * for development
    # In production, this should be set to specific domains
    allowed_origin = os.environ.get("CORS_ALLOWED_ORIGIN", "*")
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": allowed_origin,
            "Access-Control-Allow-Methods": "POST,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type,X-Tenant-Id,Authorization",
        },
        "body": json.dumps(body, cls=DecimalEncoder),
    }


def lambda_handler(event, context):
    """
    Lambda handler to update Razorpay payment status in DynamoDB.
    
    Expected input (from frontend via API Gateway):
    {
        "razorpay_payment_id": "pay_xxxxx",
        "razorpay_order_id": "order_xxxxx",
        "status": "success" or "failed",
        "amount": 1000 (optional),
        "currency": "INR" (optional, defaults to INR),
        "user_id": "user123" (optional),
        "course_id": "course123" (optional),
        "email": "user@example.com" (optional),
        "phone": "+919876543210" (optional),
        "razorpay_signature": "signature_xxxxx" (optional)
    }
    
    Response: 
    - 200: Success with transaction details
    - 400: Bad request (missing fields, invalid status)
    - 500: Internal server error (DynamoDB errors)
    """
    logger.info("Received event: %s", json.dumps(event))
    
    try:
        # Handle CORS preflight
        http_method = event.get("httpMethod", "")
        if http_method == "OPTIONS":
            return build_response(200, {"message": "CORS preflight success"})
        
        # Parse request body
        body_str = event.get("body", "{}")
        try:
            body = json.loads(body_str) if isinstance(body_str, str) else body_str
        except json.JSONDecodeError as e:
            logger.error("Invalid JSON format: %s", str(e))
            return build_response(400, {
                "error": "Invalid JSON format",
                "details": str(e)
            })
        
        # Validate required fields
        razorpay_payment_id = body.get("razorpay_payment_id")
        razorpay_order_id = body.get("razorpay_order_id")
        status = body.get("status")
        
        if not razorpay_payment_id:
            logger.error("Missing required field: razorpay_payment_id")
            return build_response(400, {
                "error": "Missing required field: razorpay_payment_id"
            })
        
        if not razorpay_order_id:
            logger.error("Missing required field: razorpay_order_id")
            return build_response(400, {
                "error": "Missing required field: razorpay_order_id"
            })
        
        if not status:
            logger.error("Missing required field: status")
            return build_response(400, {
                "error": "Missing required field: status"
            })
        
        # Validate status value
        if status not in ["success", "failed"]:
            logger.error("Invalid status value: %s", status)
            return build_response(400, {
                "error": "Invalid status. Must be 'success' or 'failed'",
                "received_status": status
            })
        
        # Prepare timestamp
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        # Build DynamoDB item
        item = {
            "transaction_id": razorpay_payment_id,  # Primary key
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_order_id": razorpay_order_id,
            "status": status,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        
        # Add optional fields if present
        if "amount" in body and body["amount"] is not None:
            # Convert to Decimal for DynamoDB
            item["amount"] = Decimal(str(body["amount"]))
        
        if "currency" in body and body["currency"]:
            item["currency"] = body["currency"]
        else:
            item["currency"] = "INR"  # Default currency
        
        if "user_id" in body and body["user_id"]:
            item["user_id"] = body["user_id"]
        
        if "course_id" in body and body["course_id"]:
            item["course_id"] = body["course_id"]
        
        if "email" in body and body["email"]:
            item["email"] = body["email"]
        
        if "phone" in body and body["phone"]:
            item["phone"] = body["phone"]
        
        if "razorpay_signature" in body and body["razorpay_signature"]:
            item["razorpay_signature"] = body["razorpay_signature"]
        
        # Store in DynamoDB
        try:
            logger.info("Storing transaction in DynamoDB: %s", razorpay_payment_id)
            # Use ConditionExpression to prevent accidental overwrites of existing transactions
            # This will fail if the transaction_id already exists
            table.put_item(
                Item=item,
                ConditionExpression='attribute_not_exists(transaction_id)'
            )
            logger.info("Transaction stored successfully: %s", razorpay_payment_id)
        except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
            # Transaction already exists - this is okay, just update the timestamp
            logger.warning("Transaction already exists, updating: %s", razorpay_payment_id)
            item['updated_at'] = datetime.utcnow().isoformat() + "Z"
            table.put_item(Item=item)
            logger.info("Transaction updated successfully: %s", razorpay_payment_id)
        except Exception as e:
            logger.error("DynamoDB error: %s", str(e), exc_info=True)
            return build_response(500, {
                "error": "Failed to store transaction in database"
            })
        
        # Return success response
        response_data = {
            "message": "Transaction updated successfully",
            "transaction_id": razorpay_payment_id,
            "status": status,
            "timestamp": timestamp
        }
        
        logger.info("Transaction update successful: %s", response_data)
        return build_response(200, response_data)
        
    except Exception as e:
        logger.exception("Unexpected error processing transaction update: %s", str(e))
        return build_response(500, {
            "error": "Internal server error"
        })
