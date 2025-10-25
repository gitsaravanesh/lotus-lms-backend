import os
import json
import boto3
from boto3.dynamodb.conditions import Key, Attr

dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ.get("COURSES_TABLE", "lms-courses")
table = dynamodb.Table(TABLE_NAME)


def response(status, body):
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body)
    }


def lambda_handler(event, context):
    headers = event.get("headers") or {}
    tenant_id = headers.get("x-tenant-id") or headers.get("X-Tenant-Id")

    if not tenant_id:
        return response(400, {"error": "Missing header x-tenant-id"})

    path = event.get("rawPath", "/")
    method = event.get("requestContext", {}).get("http", {}).get("method", "GET")

    try:
        # GET /courses
        if method == "GET" and path == "/courses":
            result = table.query(
                KeyConditionExpression=Key("tenant_id").eq(tenant_id)
            )
            return response(200, {"items": result.get("Items", [])})

        # GET /courses/{course_id}
        if method == "GET" and path.startswith("/courses/"):
            course_id = path.split("/courses/")[1]
            result = table.get_item(
                Key={"tenant_id": tenant_id, "course_id": course_id}
            )
            if "Item" not in result:
                return response(404, {"error": "Course not found"})
            return response(200, result["Item"])

        return response(404, {"error": "Not found"})

    except Exception as e:
        return response(500, {"error": str(e)})
