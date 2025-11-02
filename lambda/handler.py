import os
import json
import boto3
from boto3.dynamodb.conditions import Key, Attr
from decimal import Decimal
from urllib.parse import unquote

# DynamoDB setup
TABLE_NAME = os.environ.get("COURSES_TABLE", "lms-courses")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)

# ------------------------------------------------------------
# JSON serialization helper for DynamoDB Decimal objects
# ------------------------------------------------------------
def default_serializer(obj):
    if isinstance(obj, Decimal):
        # Convert Decimals to int or float
        if obj % 1 == 0:
            return int(obj)
        else:
            return float(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

# ------------------------------------------------------------
# Helper for API Gateway proxy response
# ------------------------------------------------------------
def response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(body, default=default_serializer)
    }

# ------------------------------------------------------------
# Lambda entrypoint
# ------------------------------------------------------------
def lambda_handler(event, context):
    try:
        headers = event.get("headers") or {}
        tenant_id = headers.get("x-tenant-id") or headers.get("X-Tenant-Id")

        if not tenant_id:
            return response(400, {"error": "Missing header x-tenant-id"})

        http_method = event.get("requestContext", {}).get("http", {}).get("method", "GET")
        path = event.get("rawPath", "/")
        query_params = event.get("queryStringParameters") or {}

        # --------------------------------------------------------
        # GET /courses  → List all courses for a tenant
        # --------------------------------------------------------
        if http_method == "GET" and path == "/courses":
            result = table.query(
                KeyConditionExpression=Key("tenant_id").eq(tenant_id)
            )
            items = result.get("Items", [])
            return response(200, {"items": items})

        # --------------------------------------------------------
        # GET /courses/{course_id} → Get one course
        # --------------------------------------------------------
        if http_method == "GET" and path.startswith("/courses/"):
            # Decode course_id (in case it's URL-encoded, e.g., course%231)
            course_id_encoded = path.split("/courses/")[1]
            course_id = unquote(course_id_encoded)

            result = table.get_item(
                Key={"tenant_id": tenant_id, "course_id": course_id}
            )

            if "Item" not in result:
                return response(404, {"error": "Course not found"})

            return response(200, result["Item"])

        # --------------------------------------------------------
        # If no route matched
        # --------------------------------------------------------
        return response(404, {"error": "Not found"})

    except Exception as e:
        # Log to CloudWatch automatically
        print("Error:", str(e))
        return response(500, {"error": str(e)})