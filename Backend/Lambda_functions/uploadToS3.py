import boto3
import base64
import os
import json

def lambda_handler(event, context):
    """
    AWS Lambda function to handle file uploads triggered via Function URL from the frontend chatbot.
    It stores the uploaded file in S3 and asynchronously triggers an extraction Lambda
    that uses a Bedrock agent to generate report insights.

    Parameters:
        event (dict): API Gateway event with headers and body.
        context (LambdaContext): AWS Lambda context object.

    Returns:
        dict: HTTP response with status code and message.
    """

    print("Received event:", event)

    # Extract session ID and HTTP method
    session_id = event['headers'].get('session-id')
    method = event.get("requestContext", {}).get("http", {}).get("method", "")
    print("HTTP method:", method)
    
    # Handle CORS preflight request
    if method == "OPTIONS":
        print("Handling CORS preflight")
        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, file-name, session-id"
            },
            "body": ""
        }

    # Extract file metadata from headers
    file_name = event.get("headers", {}).get("file-name", "uploaded_file.pdf")
    content_type = event.get("headers", {}).get("content-type", "application/pdf")
    print("File name:", file_name)
    print("Content type:", content_type)
    
    # Decode file data from base64 or UTF-8
    try:
        if event.get("isBase64Encoded", False):
            print("Decoding base64 body")
            file_data = base64.b64decode(event["body"])
        else:
            print("Body is not base64 encoded")
            file_data = event["body"].encode("utf-8")
    except Exception as e:
        print("Error decoding file data:", str(e))
        return {
            "statusCode": 400,
            "body": f"Error decoding file data: {str(e)}"
        }

    # Upload file to S3
    try:
        bucket = os.environ.get('UPLOAD_BUCKET', 'user-data-agent')  # Retrieve Bucket name from environment variable
        key = f"uploads/{session_id}/{file_name}"
        print(f"Uploading to S3 bucket: {bucket}, key: {key}")

        s3 = boto3.client('s3')
        s3.put_object(Bucket=bucket, Key=key, Body=file_data, ContentType=content_type)
        print("Upload successful")
    except Exception as e:
        print("Error uploading to S3:", str(e))
        return {
            "statusCode": 500,
            "body": f"Error uploading to S3: {str(e)}"
        }

    # Trigger extraction Lambda for Bedrock agent processing
    try:
        extractor_lambda_name = os.environ.get('EXTRACTOR_LAMBDA', 'extractor_fe')  # Retrieve Extractor Lambda name from env variable
        payload = { "sid": session_id }

        print(f"Invoking extraction Lambda '{extractor_lambda_name}' with payload: {payload}")
        lambda_client = boto3.client('lambda')
        response = lambda_client.invoke(
            FunctionName=extractor_lambda_name,
            InvocationType='Event',  # Asynchronous invocation
            Payload=json.dumps(payload).encode('utf-8')
        )
        print("Extraction lambda triggered successfully:", response)
    except Exception as e:
        print("Error invoking Lambda:", str(e))
        return {
            "statusCode": 500,
            "body": f"Error invoking Lambda: {str(e)}"
        }
    
    # Return success response to UI
    return {
        "statusCode": 200,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, file-name, session-id"
        },
        "body": "File uploaded successfully"
    }