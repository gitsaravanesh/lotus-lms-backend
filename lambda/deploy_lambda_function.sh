#!/bin/bash
# Deployment script for lms-infra-update-transaction Lambda function

set -e

FUNCTION_NAME="lms-infra-update-transaction"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "======================================"
echo "Deploying Lambda Function: ${FUNCTION_NAME}"
echo "======================================"

# Create deployment package
echo "Creating deployment package..."
cd "${SCRIPT_DIR}"
zip -r lambda_function.zip lambda_function.py
echo "✓ Package created: lambda_function.zip"

# Check if AWS CLI is available
if ! command -v aws &> /dev/null; then
    echo "Error: AWS CLI is not installed"
    exit 1
fi

# Update Lambda function
echo "Updating Lambda function code..."
aws lambda update-function-code \
    --function-name ${FUNCTION_NAME} \
    --zip-file fileb://lambda_function.zip

echo "✓ Lambda function updated successfully"

# Verify function configuration
echo ""
echo "Current function configuration:"
aws lambda get-function-configuration \
    --function-name ${FUNCTION_NAME} \
    --query '{Runtime:Runtime,Handler:Handler,Timeout:Timeout,MemorySize:MemorySize,Environment:Environment}' \
    --output json

echo ""
echo "======================================"
echo "Deployment completed successfully!"
echo "======================================"
echo ""
echo "To set environment variables, run:"
echo "aws lambda update-function-configuration \\"
echo "  --function-name ${FUNCTION_NAME} \\"
echo "  --environment 'Variables={TRANSACTIONS_TABLE=lms-transactions,CORS_ALLOWED_ORIGIN=https://yourdomain.com}'"
echo ""
echo "To test the function, run:"
echo "aws lambda invoke \\"
echo "  --function-name ${FUNCTION_NAME} \\"
echo "  --payload '{\"body\":\"{\\\"razorpay_payment_id\\\":\\\"pay_test123\\\",\\\"razorpay_order_id\\\":\\\"order_test456\\\",\\\"status\\\":\\\"success\\\"}\"}' \\"
echo "  response.json"
echo ""
echo "To view logs, run:"
echo "aws logs tail /aws/lambda/${FUNCTION_NAME} --follow"
