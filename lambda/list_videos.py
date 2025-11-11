import os
import json
import logging
from decimal import Decimal
import boto3
from boto3.dynamodb.conditions import Key, Attr
#re-run
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Read table name from env var, fallback to the known table name if not provided
VIDEOS_TABLE = os.environ.get("VIDEOS_TABLE", "lotus-lms-videos")

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(VIDEOS_TABLE)


class DecimalEncoder(json.JSONEncoder):
    """Helper class to convert a DynamoDB item to JSON serializable types."""
    def default(self, o):
        if isinstance(o, Decimal):
            # convert Decimal to int if it's integral, otherwise float
            if o % 1 == 0:
                return int(o)
            else:
                return float(o)
        return super(DecimalEncoder, self).default(o)


def build_response(status_code: int, body: dict):
    """Standard API Gateway response with common CORS headers used in the infra."""
    return {
        "statusCode": status_code,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,X-Tenant-Id,Authorization",
            "Access-Control-Allow-Methods": "GET,OPTIONS",
        },
        "body": json.dumps(body, cls=DecimalEncoder),
    }


def handler(event, context):
    """
    Lambda handler to return videos for a given course_id.

    Expected trigger: API Gateway (REST) GET /courses/{course_id}/videos
    - Path parameter: course_id
    - Alternatively accepts query string parameter course_id for non-proxy integrations.

    Response: JSON object { "course_id": "<id>", "videos": [ ... ] }
    """
    logger.info("Received event: %s", json.dumps(event))

    # Try to get course_id from pathParameters (typical for /courses/{course_id}/videos)
    course_id = None
    if event.get("pathParameters"):
        course_id = event["pathParameters"].get("course_id")
    # fallback to query string
    if not course_id and event.get("queryStringParameters"):
        course_id = event["queryStringParameters"].get("course_id")

    if not course_id:
        logger.warning("No course_id provided in request")
        return build_response(400, {"message": "Missing required parameter: course_id"})

    try:
        # Query DynamoDB using course_id as partition key
        # The table is expected to have partition key 'course_id' and sort key 'video_id'
        resp = table.query(
            KeyConditionExpression=Key("course_id").eq(course_id),
            # optional: you can set Limit, ScanIndexForward=False to reverse order, etc.
        )

        items = resp.get("Items", [])
        # Optionally sort client-side by video_id if needed (string sort)
        items.sort(key=lambda x: x.get("video_id", ""))

        body = {
            "course_id": course_id,
            "count": len(items),
            "videos": items,
        }
        return build_response(200, body)

    except Exception as e:
        logger.exception("Error querying videos table for course_id=%s", course_id)
        return build_response(500, {"message": "Internal server error", "error": str(e)})
