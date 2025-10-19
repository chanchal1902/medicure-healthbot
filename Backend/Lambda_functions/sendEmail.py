import boto3
import json
import os

# Initialize the SES client with region from environment variable
ses = boto3.client('ses', region_name=os.environ.get('REGION', 'us-east-1'))  

def lambda_handler(event, context):
    """
    AWS Lambda function to send a confirmation email to the patient
    after booking a medical appointment. Email includes appointment details
    and extracted medical report summary.

    Parameters:
        event (dict): Incoming event with appointment and user details.
        context (LambdaContext): Runtime information provided by AWS Lambda.

    Returns:
        dict: HTTP response with status code and message.
    """
    print("Recieved event:", event)
    # Extract required fields from the event payload
    unique_id = event.get('uniqueId')
    user_name = event.get('userName')
    user_email = event.get('userEmail')
    symptoms_summary = event.get('symptomsSummary')
    extraction_summary = event.get('extractionSummary')
    specialist_type = event.get('specialistType')
    doctor_name = event.get('doctorName')
    appointment_time = event.get('appointmentTime')
    urgency_level = event.get('urgencyLevel')
  
    # Validate required fields
    if not all([unique_id, user_name, user_email, specialist_type, doctor_name, appointment_time]):
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Missing required fields in the event payload.'})
        }

    # Retrieve sender email address from environment variable
    sender_email = os.environ.get('SENDER_EMAIL', 'yourbotapp@gmail.com')

    # Email subject and HTML body 
    subject = "Your Appointment Confirmation"
    body_html = f"""
    <html>
    <head></head>
    <body>
      <p>Dear {user_name},</p>
      <p>We are pleased to confirm your medical appointment. Below are the details:</p>
      <table style="border-collapse: collapse; width: 100%;">
        <tr>
          <td style="padding: 8px; border: 1px solid #ccc;"><strong>Confirmation ID</strong></td>
          <td style="padding: 8px; border: 1px solid #ccc;">{unique_id}</td>
        </tr>
        <tr>
          <td style="padding: 8px; border: 1px solid #ccc;"><strong>Priority</strong></td>
          <td style="padding: 8px; border: 1px solid #ccc;">{urgency_level}</td>
        </tr>
        <tr>
          <td style="padding: 8px; border: 1px solid #ccc;"><strong>Specialist Type</strong></td>
          <td style="padding: 8px; border: 1px solid #ccc;">{specialist_type}</td>
        </tr>
        <tr>
          <td style="padding: 8px; border: 1px solid #ccc;"><strong>Assigned Doctor</strong></td>
          <td style="padding: 8px; border: 1px solid #ccc;">{doctor_name}</td>
        </tr>
        <tr>
          <td style="padding: 8px; border: 1px solid #ccc;"><strong>Appointment Time</strong></td>
          <td style="padding: 8px; border: 1px solid #ccc;">{appointment_time} IST</td>
        </tr>
        <tr>
          <td style="padding: 8px; border: 1px solid #ccc;"><strong>Symptoms</strong></td>
          <td style="padding: 8px; border: 1px solid #ccc;">{symptoms_summary}</td>
        </tr>
        <tr>
          <td style="padding: 8px; border: 1px solid #ccc;"><strong>Report Insights</strong></td>
          <td style="padding: 8px; border: 1px solid #ccc;">{extraction_summary}</td>
        </tr>
      </table>
      <p>Thank you,<br/>Healthcare Support Team</p>
    </body>
    </html>
    """
    # Send email via SES
    try:
        response = ses.send_email(
            Source=sender_email,
            Destination={'ToAddresses': [user_email]},
            Message={
                'Subject': {'Data': subject},
                'Body': {
                    'Html': {'Data': body_html}
                }
            }
        )
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Confirmation email sent successfully.', 
            'response': response})
        }
    except Exception as e:
        print("Error sending email:", str(e))
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }