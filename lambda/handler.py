import os
import json
import boto3
from boto3.dynamodb.conditions import Key
from decimal import Decimal
from urllib.parse import unquote

# ----------------------------
# DynamoDB setup
# ----------------------------
TABLE_NAME = os.environ.get("COURSES_TABLE", "lms-courses")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)


# ----------------------------
# JSON Serializer for Decimal
# ----------------------------
def default_serializer(obj):
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


# ----------------------------
# Unified HTTP Response with CORS
# ----------------------------
def response(status_code, body):
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
    print("Event:", json.dumps(event))
    try:
        # Normalize headers (API Gateway sometimes lowercases)
        headers = event.get("headers") or {}
        tenant_id = headers.get("x-tenant-id") or headers.get("X-Tenant-Id")

        http_method = event.get("httpMethod") or event.get("requestContext", {}).get("http", {}).get("method", "")
        raw_path = event.get("path") or event.get("rawPath", "/")
        path_params = event.get("pathParameters") or {}

        # ✅ Handle CORS Preflight
        if http_method == "OPTIONS":
            return response(200, {"message": "CORS preflight success"})

        # ✅ Check for tenant header
        if not tenant_id:
            return response(400, {"error": "Missing header x-tenant-id"})

        # ✅ GET /courses → List all courses
        if http_method == "GET" and (raw_path.endswith("/courses") or raw_path == "/courses"):
            result = table.query(KeyConditionExpression=Key("tenant_id").eq(tenant_id))
            items = result.get("Items", [])
            return response(200, {"items": items})

        # ✅ GET /courses/{course_id} → Get a specific course
        if http_method == "GET" and (
            raw_path.startswith("/courses/") or "course_id" in path_params
        ):
            # Extract the course ID (either from pathParameters or path)
            course_id_encoded = (
                path_params.get("course_id") or raw_path.split("/courses/")[1]
            )
            course_id = unquote(course_id_encoded)

            result = table.get_item(Key={"tenant_id": tenant_id, "course_id": course_id})
            item = result.get("Item")
            if not item:
                return response(404, {"error": "Course not found"})

            return response(200, item)

        # ❌ Unknown route
        return response(404, {"error": "Not found"})

    except Exception as e:
        print("Error:", str(e))
        return response(500, {"error": str(e)})