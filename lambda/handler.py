import os
import json
import boto3
from boto3.dynamodb.conditions import Key
from decimal import Decimal
from urllib.parse import unquote

# DynamoDB setup
TABLE_NAME = os.environ.get("COURSES_TABLE", "lms-courses")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)


# ----------------------------
# JSON Serializer for Decimal
# ----------------------------
def default_serializer(obj):
    if isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        else:
            return float(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


# ----------------------------
# Unified HTTP Response
# ----------------------------
def response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",  # Allow from all origins (can restrict later)
            "Access-Control-Allow-Methods": "GET,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type,X-Tenant-Id,Authorization",
        },
        "body": json.dumps(body, default=default_serializer),
    }


# ----------------------------
# Lambda Handler
# ----------------------------
def lambda_handler(event, context):
    try:
        headers = event.get("headers") or {}
        tenant_id = headers.get("x-tenant-id") or headers.get("X-Tenant-Id")

        http_method = event.get("requestContext", {}).get("http", {}).get("method", "GET")
        path = event.get("rawPath", "/")

        # ✅ Handle CORS Preflight (OPTIONS)
        if http_method == "OPTIONS":
            return {
                "statusCode": 200,
                "headers": {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET,OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type,X-Tenant-Id,Authorization",
                },
                "body": json.dumps({"message": "CORS preflight success"}),
            }

        # ✅ Check tenant header
        if not tenant_id:
            return response(400, {"error": "Missing header x-tenant-id"})

        # ✅ GET /courses → List all courses for a tenant
        if http_method == "GET" and path == "/courses":
            result = table.query(KeyConditionExpression=Key("tenant_id").eq(tenant_id))
            items = result.get("Items", [])
            return response(200, {"items": items})

        # ✅ GET /courses/{course_id} → Get one course
        if http_method == "GET" and path.startswith("/courses/"):
            course_id_encoded = path.split("/courses/")[1]
            course_id = unquote(course_id_encoded)  # Decode %23, etc.

            result = table.get_item(Key={"tenant_id": tenant_id, "course_id": course_id})
            if "Item" not in result:
                return response(404, {"error": "Course not found"})

            return response(200, result["Item"])

        # Fallback for unknown route
        return response(404, {"error": "Not found"})

    except Exception as e:
        print("Error:", str(e))
        return response(500, {"error": str(e)})