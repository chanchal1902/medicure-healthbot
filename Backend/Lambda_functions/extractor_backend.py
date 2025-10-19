import boto3
import json
import fitz  # PyMuPDF
import os

# Initialize S3 client
s3 = boto3.client("s3")

def extract_text_from_pdf(file_path):
    """
    Extracts text from all pages of a PDF file.

    Parameters:
        file_path (str): Local path to the PDF file.

    Returns:
        str: Combined text from all pages.
    """
    doc = fitz.open(file_path)
    text = "".join(page.get_text() for page in doc)
    doc.close()
    return text

def chunk_text(text, max_chars=20000):
    """
    Splits a long string into chunks of max_chars length.

    Parameters:
        text (str): The full text to split.
        max_chars (int): Maximum characters per chunk.

    Returns:
        list: List of text chunks.
    """
    return [text[i:i+max_chars] for i in range(0, len(text), max_chars)]

def lambda_handler(event, context):
    """
    Lambda function invoked by Bedrock agent via action group `extractor_fetch`.
    It retrieves PDF files from S3 for a given Session ID, extracts text,
    and returns the result to the agent.

    Parameters:
        event (dict): Contains actionGroup, function, parameters, etc.
        context (LambdaContext): AWS Lambda context object.

    Returns:
        dict: Structured response for Bedrock agent.
    """
    try:
        print("Recieved event:", event)
        
        # Extract metadata from event
        action_group = event["actionGroup"]
        function = event["function"]
        message_version = event.get("messageVersion", 1)
        parameters = event.get("parameters", [])
        
        # Extract submission ID from parameters
        submission_id = next((p["value"] for p in parameters if p["name"] == "sid"), None)
        if not submission_id:
            raise KeyError("Missing 'sid' parameter")
        
        # Get bucket name from environment variable
        bucket = os.environ.get("UPLOAD_BUCKET", "user-data-agent")
        prefix = f"uploads/{submission_id}/"
        
        # List PDF files under the submission prefix
        files = s3.list_objects_v2(Bucket=bucket, Prefix=prefix).get("Contents", [])
        extracted_docs = []

        for file in files:
            key = file["Key"]
            if key.endswith(".pdf"):
                tmp_path = f"/tmp/{os.path.basename(key)}"
                s3.download_file(bucket, key, tmp_path)
                pdf_text = extract_text_from_pdf(tmp_path)
                extracted_docs.append({
                    "file_name": key,
                    "extracted_text": pdf_text
                })

        # Construct response body for Bedrock agent
        response_body = {
            "TEXT": {
                "body": json.dumps({
                    "submission_id": submission_id,
                    "documents": extracted_docs
                }, default=str)
            }
        }

        return {
            "response": {
                "actionGroup": action_group,
                "function": function,
                "functionResponse": {"responseBody": response_body}
            },
            "messageVersion": message_version
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
