import boto3
import json
import os
from datetime import datetime, timezone
from botocore.config import Config

# Configure Bedrock agent runtime client
bedrock_agent = boto3.client(
    'bedrock-agent-runtime',
    config=Config(
        connect_timeout=10,  # time to establish connection
        read_timeout=120,     # time to wait for the response
        retries={
            'max_attempts': 3,
            'mode': 'standard'
        }
    )
)

# Initialize DynamoDB table
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get("SUMMARY_TABLE", "medical_summary"))

# Bedrock agent configuration
AGENT_ID = os.environ.get("BEDROCK_AGENT_ID", "FDB7SXFQZR")
AGENT_ALIAS_ID = os.environ.get("BEDROCK_AGENT_ALIAS_ID", "KPPYOEENVI")
      
def lambda_handler(event, context):
    """
    Lambda function triggered after a medical report is uploaded.
    It invokes a Bedrock agent to extract insights and stores the summary in DynamoDB.

    Parameters:
        event (dict): Contains 'sid' (session ID) for the uploaded report.
        context (LambdaContext): AWS Lambda context object.

    Returns:
        list or str: Extracted summary or error message.
    """

    print("Received event:", event)
    submission_id = event["sid"]
    
    if not submission_id:
        return {"error": "Missing 'sid' in event"}

    try:
        extracted_data = extract_fields_in_batches(submission_id, chunk_size=10)
        print(f'extracted_data is : {extracted_data}')
        upsert_submission(submission_id, extracted_data)
        return extracted_data
    except Exception as e:
        print("Error in extraction flow:", str(e))
        return {"error": str(e)}

def get_docid():
    """Generates a unique session ID based on UTC timestamp."""
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")[2:]

def extract_fields_in_batches(submission_id, chunk_size=10):
    """
    Invokes the Bedrock agent to extract insights from the uploaded report.

    Parameters:
        submission_id (str): Unique ID for the uploaded report.
        chunk_size (int): Reserved for future use (batching).

    Returns:
        list: Extracted insights from the report.
    """
    final_results = []

    session_id = get_docid() 
    print("Generated session ID:", session_id)

    try:
        #Invoke bedrock agent for extraction
        response_stream = bedrock_agent.invoke_agent(
            agentId=AGENT_ID,
            agentAliasId=AGENT_ALIAS_ID,
            sessionId=session_id,
            inputText=f'{submission_id}'
        )
                
        final_output = ""
        for event in response_stream['completion']:
            # If 'chunk' exists and it has 'bytes', decode and append
            chunk = event.get("chunk")
            if chunk and "bytes" in chunk:
                chunk_text = chunk["bytes"].decode("utf-8")
                final_output += chunk_text

        sanitized = final_output.strip()

        # If it's valid JSON, then parse it - else keep it as text
        try:
            body = json.loads(sanitized)
        except json.JSONDecodeError:
            body = sanitized

        response = body
        print("Parsed response:", response)
    except Exception as e:
        print("Error invoking Bedrock agent:", str(e))
        return str(e)  

    # Normalize response
    try:
        if isinstance(response, str):
            # Treat as a single text item
            response_data = [response.strip()]
        elif isinstance(response, list):
            response_data = response
        elif isinstance(response, dict):
            response_data = [response]
        else:
            raise ValueError(f"Unexpected response type: {type(response)}")

        # Merge into final results
        final_results.extend(response_data)

    except Exception as e:
        print(f"Error parsing response: {response}")
        status = "failed"
        raise e

    return final_results     
        
def upsert_submission(submission_id, extracted_data):
    """
    Inserts or updates the extracted summary in DynamoDB.

    Parameters:
        submission_id (str): Unique ID for the report.
        extracted_data (list): Summary data to store.
    """
    # current timestamp
    now = datetime.utcnow().isoformat()
    
    try:
        # Check if record exists
        response = table.get_item(Key={"submission_id": submission_id})

        if "Item" in response:  
            # Update existing record
            table.update_item(
                Key={"submission_id": submission_id},
                UpdateExpression="SET #kv = :kv, last_updated = :lu",
                ExpressionAttributeNames={"#kv": "key_value"},
                ExpressionAttributeValues={
                    ":kv": extracted_data,
                    ":lu": now
                }
            )
            print(f"Updated submission_id {submission_id}")
        else:
            # Insert new record
            table.put_item(
                Item={
                    "submission_id": submission_id,
                    "key_value": extracted_data,
                    "created_date": now,
                    "last_updated": now
                }
            )
            print(f"Inserted new submission_id {submission_id}")    
    except Exception as e:
        print("Error writing to DynamoDB:", str(e))
        raise e      