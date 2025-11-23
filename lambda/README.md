# Lambda Functions Documentation

This directory contains AWS Lambda functions for the Lotus LMS backend.

## update_transaction.py

### Overview
Lambda function that handles Razorpay payment status updates and stores transaction records in DynamoDB.

**Function Name**: `lms-infra-update-transaction`  
**Handler**: `update_transaction.lambda_handler`  
**DynamoDB Table**: `lms-transactions`

### Request Format

#### Required Fields
```json
{
  "razorpay_payment_id": "pay_XXXXXXXXXXXXX",
  "razorpay_order_id": "order_XXXXXXXXXXXXX",
  "status": "success"
}
```

#### Optional Fields
```json
{
  "razorpay_payment_id": "pay_XXXXXXXXXXXXX",
  "razorpay_order_id": "order_XXXXXXXXXXXXX",
  "status": "success",
  "amount": 50000,
  "currency": "INR",
  "user_id": "user123",
  "course_id": "course456",
  "email": "user@example.com",
  "phone": "+919876543210",
  "razorpay_signature": "signature_string"
}
```

#### Field Descriptions
- **razorpay_payment_id** (string, required): Unique payment ID from Razorpay
- **razorpay_order_id** (string, required): Order ID associated with the payment
- **status** (string, required): Payment status - must be either "success" or "failed"
- **amount** (number, optional): Payment amount in smallest currency unit (e.g., paise for INR)
- **currency** (string, optional): Currency code (default: "INR")
- **user_id** (string, optional): ID of the user making the payment
- **course_id** (string, optional): ID of the course being purchased
- **email** (string, optional): User's email address
- **phone** (string, optional): User's phone number
- **razorpay_signature** (string, optional): Razorpay signature for payment verification

### Response Format

#### Success Response (200)
```json
{
  "message": "Transaction updated successfully",
  "transaction_id": "pay_XXXXXXXXXXXXX",
  "status": "success",
  "timestamp": "2024-01-01T12:00:00.000000Z"
}
```

#### Error Response - Missing Fields (400)
```json
{
  "error": "Missing required fields",
  "missing_fields": ["razorpay_payment_id", "razorpay_order_id"]
}
```

#### Error Response - Invalid Status (400)
```json
{
  "error": "Invalid status value",
  "details": "Status must be either 'success' or 'failed'"
}
```

#### Error Response - Invalid JSON (400)
```json
{
  "error": "Invalid JSON format",
  "details": "Expecting value: line 1 column 1 (char 0)"
}
```

#### Error Response - DynamoDB Error (500)
```json
{
  "error": "Failed to store transaction",
  "details": "Error message from DynamoDB"
}
```

#### Error Response - Internal Error (500)
```json
{
  "error": "Internal server error",
  "details": "Error details"
}
```

### DynamoDB Schema

**Table Name**: `lms-transactions`  
**Primary Key**: `transaction_id` (String)

#### Attributes
| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| transaction_id | String | Yes | Primary key, same as razorpay_payment_id |
| razorpay_payment_id | String | Yes | Razorpay payment ID |
| razorpay_order_id | String | Yes | Razorpay order ID |
| status | String | Yes | Payment status ("success" or "failed") |
| created_at | String | Yes | ISO 8601 timestamp when record was created |
| updated_at | String | Yes | ISO 8601 timestamp when record was last updated |
| amount | Number | No | Payment amount (stored as Decimal) |
| currency | String | No | Currency code (default: "INR") |
| user_id | String | No | User ID |
| course_id | String | No | Course ID |
| email | String | No | User email |
| phone | String | No | User phone number |
| razorpay_signature | String | No | Razorpay signature |

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| TRANSACTIONS_TABLE | lms-transactions | Name of the DynamoDB table |

### IAM Permissions Required

The Lambda function requires the following IAM permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:GetItem"
      ],
      "Resource": "arn:aws:dynamodb:REGION:ACCOUNT_ID:table/lms-transactions"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:REGION:ACCOUNT_ID:log-group:/aws/lambda/lms-infra-update-transaction:*"
    }
  ]
}
```

### Usage Examples

#### Example 1: Basic Transaction Update
```bash
curl -X POST https://your-api-gateway-url/update-transaction \
  -H "Content-Type: application/json" \
  -d '{
    "razorpay_payment_id": "pay_ABC123",
    "razorpay_order_id": "order_XYZ789",
    "status": "success"
  }'
```

#### Example 2: Complete Transaction with Optional Fields
```bash
curl -X POST https://your-api-gateway-url/update-transaction \
  -H "Content-Type: application/json" \
  -d '{
    "razorpay_payment_id": "pay_ABC123",
    "razorpay_order_id": "order_XYZ789",
    "status": "success",
    "amount": 50000,
    "currency": "INR",
    "user_id": "user123",
    "course_id": "course456",
    "email": "student@example.com",
    "phone": "+919876543210",
    "razorpay_signature": "abc123signature"
  }'
```

#### Example 3: Failed Transaction
```bash
curl -X POST https://your-api-gateway-url/update-transaction \
  -H "Content-Type: application/json" \
  -d '{
    "razorpay_payment_id": "pay_DEF456",
    "razorpay_order_id": "order_UVW321",
    "status": "failed"
  }'
```

### CORS Configuration

The Lambda function includes CORS headers to support frontend integration:

- **Access-Control-Allow-Origin**: `*` (allows all origins)
- **Access-Control-Allow-Methods**: `POST,OPTIONS`
- **Access-Control-Allow-Headers**: `Content-Type,X-Tenant-Id,Authorization`

The function handles OPTIONS requests for CORS preflight.

### Logging

All operations are logged to CloudWatch Logs:
- Incoming event details
- Validation errors
- DynamoDB operations
- Error messages with stack traces

CloudWatch log group: `/aws/lambda/lms-infra-update-transaction`

### Error Handling

The function implements comprehensive error handling:

1. **JSON Parsing Errors**: Returns 400 with details
2. **Missing Required Fields**: Returns 400 with list of missing fields
3. **Invalid Status Values**: Returns 400 with valid options
4. **Invalid Amount Format**: Returns 400 with error details
5. **DynamoDB Errors**: Returns 500 with error details
6. **Unexpected Errors**: Returns 500 with error message

### Deployment

1. Ensure the Lambda function `lms-infra-update-transaction` is created via Terraform
2. Package the Lambda function:
   ```bash
   cd lambda
   zip -r update_transaction.zip update_transaction.py
   ```
3. Deploy using AWS CLI:
   ```bash
   aws lambda update-function-code \
     --function-name lms-infra-update-transaction \
     --zip-file fileb://update_transaction.zip
   ```
4. Update handler configuration:
   ```bash
   aws lambda update-function-configuration \
     --function-name lms-infra-update-transaction \
     --handler update_transaction.lambda_handler
   ```

### Testing

#### Unit Testing
Test with sample events:
```python
event = {
    "body": json.dumps({
        "razorpay_payment_id": "pay_TEST123",
        "razorpay_order_id": "order_TEST456",
        "status": "success",
        "amount": 50000
    })
}
result = lambda_handler(event, None)
print(result)
```

#### Integration Testing
Use AWS Lambda console test feature with sample events or invoke via API Gateway.

### Monitoring

Monitor the Lambda function using:
- **CloudWatch Metrics**: Invocations, errors, duration, throttles
- **CloudWatch Logs**: Detailed execution logs
- **X-Ray**: Distributed tracing (if enabled)

Key metrics to monitor:
- Error rate
- Execution duration
- DynamoDB write latency
- Concurrent executions

### Troubleshooting

#### Common Issues

1. **Missing Environment Variable**
   - Error: Table not found
   - Solution: Set TRANSACTIONS_TABLE environment variable

2. **Permission Denied**
   - Error: Access denied to DynamoDB
   - Solution: Ensure Lambda execution role has proper permissions

3. **Invalid JSON**
   - Error: JSON decode error
   - Solution: Verify request body is valid JSON

4. **Timeout**
   - Error: Task timed out
   - Solution: Increase Lambda timeout (default: 3 seconds, recommended: 10 seconds)

### Version History

- **v1.0.0**: Initial implementation with core functionality
  - Payment status updates
  - DynamoDB storage
  - Error handling
  - CORS support
  - CloudWatch logging
