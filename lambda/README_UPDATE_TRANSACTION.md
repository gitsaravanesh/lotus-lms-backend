# Lambda Function: lms-infra-update-transaction

This Lambda function handles Razorpay payment status updates and stores transaction data in DynamoDB.

## Overview

- **Function Name**: `lms-infra-update-transaction`
- **Handler**: `lambda_function.lambda_handler`
- **Runtime**: Python 3.9 or higher
- **DynamoDB Table**: `lms-transactions`

## Functionality

This Lambda function:
1. Accepts payment status updates from the frontend
2. Validates all required fields and status values
3. Stores transaction data in DynamoDB with proper timestamps
4. Returns appropriate responses with CORS headers for frontend integration
5. Logs all operations to CloudWatch for monitoring

## Request Format

### Required Fields

```json
{
  "razorpay_payment_id": "pay_xxxxxxxxxxxxx",
  "razorpay_order_id": "order_xxxxxxxxxxxxx",
  "status": "success"
}
```

### Optional Fields

```json
{
  "razorpay_payment_id": "pay_xxxxxxxxxxxxx",
  "razorpay_order_id": "order_xxxxxxxxxxxxx",
  "status": "success",
  "amount": 1000,
  "currency": "INR",
  "user_id": "user123",
  "course_id": "course456",
  "email": "user@example.com",
  "phone": "+919876543210",
  "razorpay_signature": "signature_xxxxxxxxxxxxx"
}
```

### Field Descriptions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `razorpay_payment_id` | String | Yes | Unique payment ID from Razorpay |
| `razorpay_order_id` | String | Yes | Order ID from Razorpay |
| `status` | String | Yes | Payment status: "success" or "failed" |
| `amount` | Number | No | Payment amount (will be stored as Decimal) |
| `currency` | String | No | Currency code (defaults to "INR") |
| `user_id` | String | No | User identifier |
| `course_id` | String | No | Course identifier |
| `email` | String | No | User email address |
| `phone` | String | No | User phone number |
| `razorpay_signature` | String | No | Payment signature for verification |

## Response Format

### Success Response (200)

```json
{
  "message": "Transaction updated successfully",
  "transaction_id": "pay_xxxxxxxxxxxxx",
  "status": "success",
  "timestamp": "2025-11-23T12:00:00.000000Z"
}
```

### Error Responses

#### Bad Request (400) - Missing Required Field

```json
{
  "error": "Missing required field: razorpay_payment_id"
}
```

#### Bad Request (400) - Invalid Status

```json
{
  "error": "Invalid status. Must be 'success' or 'failed'",
  "received_status": "pending"
}
```

#### Bad Request (400) - Invalid JSON

```json
{
  "error": "Invalid JSON format",
  "details": "Expecting value: line 1 column 1 (char 0)"
}
```

#### Internal Server Error (500) - DynamoDB Error

```json
{
  "error": "Failed to store transaction in database",
  "details": "ResourceNotFoundException: Requested resource not found"
}
```

#### Internal Server Error (500) - Unexpected Error

```json
{
  "error": "Internal server error",
  "details": "Error message details"
}
```

## DynamoDB Table Structure

### Table Name
`lms-transactions` (configurable via `TRANSACTIONS_TABLE` environment variable)

### Schema

| Attribute | Type | Key Type | Description |
|-----------|------|----------|-------------|
| `transaction_id` | String | Partition Key | Unique transaction ID (uses razorpay_payment_id) |
| `razorpay_payment_id` | String | - | Payment ID from Razorpay |
| `razorpay_order_id` | String | - | Order ID from Razorpay |
| `status` | String | - | Payment status ("success" or "failed") |
| `amount` | Number (Decimal) | - | Payment amount |
| `currency` | String | - | Currency code (default: "INR") |
| `user_id` | String | - | User identifier |
| `course_id` | String | - | Course identifier |
| `email` | String | - | User email |
| `phone` | String | - | User phone number |
| `razorpay_signature` | String | - | Payment signature |
| `created_at` | String | - | ISO 8601 timestamp (UTC) |
| `updated_at` | String | - | ISO 8601 timestamp (UTC) |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TRANSACTIONS_TABLE` | No | `lms-transactions` | DynamoDB table name for transactions |
| `CORS_ALLOWED_ORIGIN` | No | `*` | Allowed origin for CORS (use specific domain in production) |

## IAM Permissions Required

The Lambda function requires the following IAM permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem"
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

Replace `REGION` and `ACCOUNT_ID` with your AWS region and account ID.

## Deployment

### Prerequisites

1. AWS Lambda function `lms-infra-update-transaction` created via Terraform
2. DynamoDB table `lms-transactions` with primary key `transaction_id` (String)
3. API Gateway configured to trigger this Lambda function

### Steps

1. **Package the Lambda function:**
   ```bash
   cd lambda
   zip -r lambda_function.zip lambda_function.py
   ```

2. **Update the Lambda function:**
   ```bash
   aws lambda update-function-code \
     --function-name lms-infra-update-transaction \
     --zip-file fileb://lambda_function.zip
   ```

3. **Verify environment variables:**
   ```bash
   aws lambda get-function-configuration \
     --function-name lms-infra-update-transaction
   ```

4. **Set environment variable (if needed):**
   ```bash
   aws lambda update-function-configuration \
     --function-name lms-infra-update-transaction \
     --environment "Variables={TRANSACTIONS_TABLE=lms-transactions}"
   ```

## Testing

### Using AWS CLI

```bash
aws lambda invoke \
  --function-name lms-infra-update-transaction \
  --payload '{"body":"{\"razorpay_payment_id\":\"pay_test123\",\"razorpay_order_id\":\"order_test456\",\"status\":\"success\",\"amount\":1000,\"currency\":\"INR\",\"user_id\":\"user123\",\"course_id\":\"course456\"}"}' \
  response.json

cat response.json
```

### Using curl (API Gateway)

```bash
curl -X POST https://your-api-gateway-url/update-transaction \
  -H "Content-Type: application/json" \
  -d '{
    "razorpay_payment_id": "pay_test123",
    "razorpay_order_id": "order_test456",
    "status": "success",
    "amount": 1000,
    "currency": "INR",
    "user_id": "user123",
    "course_id": "course456"
  }'
```

### Test Cases

1. **Valid Success Payment:**
   ```json
   {
     "razorpay_payment_id": "pay_12345",
     "razorpay_order_id": "order_67890",
     "status": "success",
     "amount": 1000
   }
   ```

2. **Valid Failed Payment:**
   ```json
   {
     "razorpay_payment_id": "pay_12346",
     "razorpay_order_id": "order_67891",
     "status": "failed"
   }
   ```

3. **Missing Required Field:**
   ```json
   {
     "razorpay_order_id": "order_67890",
     "status": "success"
   }
   ```
   Expected: 400 error

4. **Invalid Status:**
   ```json
   {
     "razorpay_payment_id": "pay_12345",
     "razorpay_order_id": "order_67890",
     "status": "pending"
   }
   ```
   Expected: 400 error

## CloudWatch Logs

The function logs the following information:
- Incoming event details
- Validation errors
- DynamoDB operations
- Success/failure of transaction updates

Access logs via:
```bash
aws logs tail /aws/lambda/lms-infra-update-transaction --follow
```

## CORS Configuration

The function includes CORS headers for frontend integration:
- `Access-Control-Allow-Origin: *`
- `Access-Control-Allow-Methods: POST,OPTIONS`
- `Access-Control-Allow-Headers: Content-Type,X-Tenant-Id,Authorization`

The function handles OPTIONS preflight requests automatically.

## Error Handling

The function implements comprehensive error handling:
1. **JSON Parsing Errors**: Returns 400 with invalid JSON error
2. **Missing Required Fields**: Returns 400 with specific field error
3. **Invalid Status Values**: Returns 400 with valid options
4. **DynamoDB Errors**: Returns 500 with error details
5. **Unexpected Errors**: Returns 500 with error details

All errors are logged to CloudWatch for debugging.

## Monitoring

Monitor the Lambda function using:
1. **CloudWatch Metrics**: Invocations, errors, duration, throttles
2. **CloudWatch Logs**: Detailed execution logs
3. **X-Ray Tracing**: If enabled, provides detailed execution traces

## Security Considerations

1. **Input Validation**: All inputs are validated before processing
2. **Error Messages**: Sensitive infrastructure details are not exposed in API responses (only logged to CloudWatch)
3. **IAM Permissions**: Follow principle of least privilege
4. **Logging**: Avoid logging sensitive payment information
5. **CORS**: Configure `CORS_ALLOWED_ORIGIN` environment variable with specific domain(s) in production (default `*` is for development only)
6. **Duplicate Prevention**: The function uses conditional expressions to prevent accidental overwrites of existing transactions

## Troubleshooting

### Common Issues

1. **ResourceNotFoundException**
   - Verify DynamoDB table exists and name matches
   - Check IAM permissions for DynamoDB access

2. **Timeout Errors**
   - Increase Lambda timeout (default: 3 seconds, recommended: 10 seconds)
   - Check DynamoDB table performance

3. **Invalid JSON Errors**
   - Verify request body is valid JSON
   - Check API Gateway request/response mapping

4. **CORS Errors**
   - Verify API Gateway CORS configuration
   - Check OPTIONS method is configured

### Debug Steps

1. Check CloudWatch logs:
   ```bash
   aws logs tail /aws/lambda/lms-infra-update-transaction --follow
   ```

2. Test with AWS Console:
   - Go to Lambda → Functions → lms-infra-update-transaction
   - Use Test tab with sample event

3. Verify DynamoDB table:
   ```bash
   aws dynamodb describe-table --table-name lms-transactions
   ```

## Support

For issues or questions, refer to:
- CloudWatch Logs: `/aws/lambda/lms-infra-update-transaction`
- AWS Lambda Console
- DynamoDB Console for transaction records
