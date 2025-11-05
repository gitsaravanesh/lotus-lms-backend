import os
import json
import boto3
import base64
import requests
from boto3.dynamodb.conditions import Key

# Initialize DynamoDB
dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ.get("COURSES_TABLE", "lms-courses")
table = dynamodb.Table(TABLE_NAME)

# Razorpay credentials from environment variables
RAZORPAY_KEY_ID = os.environ["RAZORPAY_KEY_ID"]
RAZORPAY_KEY_SECRET = os.environ["RAZORPAY_KEY_SECRET"]

def lambda_handler(event, context):
    try:
        print("Event:", event)
        body = json.loads(event.get("body", "{}"))
        tenant_id = body.get("tenant_id")
        course_id = body.get("course_id")

        if not tenant_id or not course_id:
            return _response(400, {"error": "tenant_id and course_id are required"})

        # Fetch course info from DynamoDB
        result = table.get_item(Key={"tenant_id": tenant_id, "course_id": course_id})
        course = result.get("Item")

        if not course:
            return _response(404, {"error": "Course not found"})

        # Convert price to paise
        amount = int(course["price"]) * 100
        currency = course.get("currency", "INR")

        # Razorpay order creation
        razorpay_url = "https://api.razorpay.com/v1/orders"
        auth_header = base64.b64encode(f"{RAZORPAY_KEY_ID}:{RAZORPAY_KEY_SECRET}".encode()).decode()

        payload = {
            "amount": amount,
            "currency": currency,
            "receipt": f"{tenant_id}-{course_id}",
        }

        response = requests.post(
            razorpay_url,
            headers={
                "Authorization": f"Basic {auth_header}",
                "Content-Type": "application/json",
            },
            data=json.dumps(payload),
        )

        if response.status_code != 200:
            print("Razorpay error:", response.text)
            return _response(500, {"error": "Failed to create order", "details": response.text})

        order = response.json()
        print("Order created:", order)

        return _response(200, order)

    except Exception as e:
        print("Error:", str(e))
        return _response(500, {"error": str(e)})


def _response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        },
        "body": json.dumps(body),
    }