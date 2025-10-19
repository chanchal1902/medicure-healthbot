import boto3
import logging
import json
import os
from typing import Dict, Any, List, Optional
from boto3.dynamodb.conditions import Attr
from datetime import datetime
import uuid
import re

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables with fallback defaults
DOCTORS_TABLE_NAME = os.getenv('DOCTORS_TABLE_NAME')
DOCTOR_SCHEDULES_TABLE_NAME = os.getenv('DOCTOR_SCHEDULES_TABLE_NAME')
MEDICAL_SUMMARY_TABLE_NAME = os.getenv('MEDICAL_SUMMARY_TABLE_NAME')
EMAIL_LAMBDA_ARN = os.getenv('EMAIL_LAMBDA_ARN')
AWS_REGION = os.getenv('AWS_REG')

# Initialize AWS resources
dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
doctors_table = dynamodb.Table(DOCTORS_TABLE_NAME)
doctor_schedules_table = dynamodb.Table(DOCTOR_SCHEDULES_TABLE_NAME)
medical_summary_table = dynamodb.Table(MEDICAL_SUMMARY_TABLE_NAME)
lambda_client = boto3.client('lambda', region_name=AWS_REGION)


def get_param_value(params: List[Dict[str, str]], key: str) -> Optional[str]:
    """
    Extract parameter value by key from parameters list.
    
    Args:
        params: List of parameter dictionaries with 'name' and 'value' keys
        key: Parameter name to search for
        
    Returns:
        Parameter value if found, None otherwise
    """
    for param in params:
        if param.get('name') == key:
            return param.get('value')
    return None


def send_confirmation_email(unique_id: str, user_name: str, user_email: str, 
                          symptoms_summary: str, specialist_type: str, 
                          doctor_name: str, appointment_time: str, 
                          extraction_summary: Optional[str] = None) -> bool:
    """
    Send confirmation email by invoking the sendemail lambda function.
    
    Args:
        unique_id: Unique identifier for the appointment
        user_name: Name of the patient
        user_email: Email address of the patient
        symptoms_summary: Summary of patient symptoms
        specialist_type: Type of medical specialist
        doctor_name: Name of the doctor
        appointment_time: Scheduled appointment time
        extraction_summary: Optional medical extraction summary
        
    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        email_payload = {
            'uniqueId': unique_id,
            'userName': user_name,
            'userEmail': user_email,
            'symptomsSummary': symptoms_summary,
            'extractionSummary': extraction_summary or "NA",
            'specialistType': specialist_type,
            'doctorName': doctor_name,
            'appointmentTime': appointment_time
        }
        logger.info(f"Sending confirmation email with payload: {email_payload}")

        response = lambda_client.invoke(
            FunctionName=EMAIL_LAMBDA_ARN,
            InvocationType='Event',  # Asynchronous invocation
            Payload=json.dumps(email_payload)
        )

        logger.info(f"Email lambda invoked successfully: {response}")
        return True

    except Exception as e:
        logger.error(f"Error invoking email lambda: {e}")
        return False


def fetch_medical_summary_by_session_id(session_id: str) -> str:
    """
    Fetch medical summary from DynamoDB table by session ID.
    
    Args:
        session_id: Session identifier to search for
        
    Returns:
        Medical summary string or 'NA' if not found
    """
    try:
        response = medical_summary_table.get_item(
            Key={'submission_id': session_id}
        )
        item = response.get('Item')
        
        if item:
            key_value = item.get('key_value', [])
            # Return first value if it's a list with items
            if isinstance(key_value, list) and key_value:
                raw_summary = key_value[0]
                cleaned_summary = re.sub(r'\*\*(.*?)\*\*', r'\1', raw_summary)
                cleaned_summary = cleaned_summary.strip()
                return cleaned_summary  
        return 'NA'
        
    except Exception as e:
        logger.error(f"Error fetching medical summary for session_id {session_id}: {e}", exc_info=True)
        return 'NA'


def get_next_timeslots_for_doctor(doctor_id: str) -> List[str]:
    """
    Get the next available timeslots for a specific doctor.
    
    Args:
        doctor_id: Unique identifier of the doctor
        
    Returns:
        List of available future timeslots (max 3) in ISO format
    """
    try:
        # Scan for doctor's schedule
        response = doctor_schedules_table.scan(
            FilterExpression=Attr('doctor_id').eq(doctor_id)
        )
        items = response.get('Items', [])
        logger.info(f"Found {len(items)} schedule records for doctor_id: {doctor_id}")
        
        if not items:
            return []

        raw_timeslots = items[0].get('timeslots', {})
        logger.info(f"Raw timeslots: {raw_timeslots}")
        
        timeslot_strs = []

        # Handle different timeslot data formats
        if isinstance(raw_timeslots, dict):
            # Sort timeslots by key for consistent ordering
            sorted_slots = sorted(raw_timeslots.items(), key=lambda x: x[0])
            for slot_key, slot_value in sorted_slots:
                if isinstance(slot_value, str):
                    timeslot_strs.append(slot_value)
                else:
                    logger.warning(f"Unexpected slot value format for {slot_key}: {slot_value}")
        elif isinstance(raw_timeslots, list):
            # Handle list format (DynamoDB attribute value format)
            for ts in raw_timeslots:
                if isinstance(ts, dict) and 'S' in ts:
                    timeslot_strs.append(ts['S'])
                elif isinstance(ts, str):
                    timeslot_strs.append(ts)

        logger.info(f"Processed timeslots: {timeslot_strs}")
        
        # Filter future timeslots only
        now = datetime.utcnow()
        future_timeslots = []
        
        for ts in timeslot_strs:
            try:
                ts_datetime = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")
                if ts_datetime > now:
                    future_timeslots.append(ts)
            except ValueError as e:
                logger.error(f"Error parsing timeslot {ts}: {e}")
                continue
        
        # Return max 3 future timeslots, sorted chronologically
        future_timeslots = sorted(future_timeslots)[:3]
        logger.info(f"Future timeslots: {future_timeslots}")
        
        return future_timeslots

    except Exception as e:
        logger.error(f"Error in get_next_timeslots_for_doctor: {e}", exc_info=True)
        return []


def get_doctor_id_by_name(name: str) -> Optional[str]:
    """
    Get doctor ID by searching for doctor name.
    
    Args:
        name: Doctor's name to search for
        
    Returns:
        Doctor ID if found, None otherwise
    """
    try:
        # Try exact match first
        response = doctors_table.scan(
            FilterExpression=Attr('name').eq(name)
        )
        items = response.get('Items', [])
        
        # If no exact match, try case-insensitive contains
        if not items:
            response = doctors_table.scan(
                FilterExpression=Attr('name').contains(name)
            )
            items = response.get('Items', [])
            
        return items[0].get('doctor_id') if items else None
        
    except Exception as e:
        logger.error(f"Error in get_doctor_id_by_name: {e}", exc_info=True)
        return None


def remove_timeslot_by_timestamp(doctor_id: str, selected_timestamp: str) -> Optional[Dict]:
    """
    Remove a specific timeslot from doctor's schedule.
    
    Args:
        doctor_id: Unique identifier of the doctor
        selected_timestamp: Timestamp of the slot to remove
        
    Returns:
        DynamoDB update response if successful, None otherwise
    """
    try:
        logger.info(f"Attempting to remove timeslot {selected_timestamp} for doctor {doctor_id}")
        
        # Get doctor's schedule
        response = doctor_schedules_table.scan(
            FilterExpression=Attr('doctor_id').eq(doctor_id)
        )
        items = response.get('Items', [])
        
        if not items:
            logger.warning(f"No schedules found for doctor_id: {doctor_id}")
            return None

        schedule = items[0]
        schedule_id = schedule['schedule_id']
        timeslots = schedule.get('timeslots', {})
        
        logger.info(f"Current timeslots in schedule {schedule_id}: {timeslots}")

        # Find the slot key to remove
        slot_key_to_remove = None
        for slot_key, slot_val in timeslots.items():
            # Handle different slot value formats
            if isinstance(slot_val, str):
                ts_val = slot_val
            elif isinstance(slot_val, dict) and 'S' in slot_val:
                ts_val = slot_val['S']
            else:
                logger.warning(f"Unexpected slot value format: {slot_val}")
                continue
                
            logger.info(f"Comparing {ts_val} with {selected_timestamp}")
            if ts_val == selected_timestamp:
                slot_key_to_remove = slot_key
                break

        if not slot_key_to_remove:
            logger.error(f"No matching slot found for timestamp {selected_timestamp} in schedule {schedule_id}")
            logger.error(f"Available slots: {list(timeslots.items())}")
            return None

        # Remove the timeslot from DynamoDB
        response = doctor_schedules_table.update_item(
            Key={"schedule_id": schedule_id},
            UpdateExpression="REMOVE timeslots.#slot",
            ExpressionAttributeNames={"#slot": slot_key_to_remove},
            ReturnValues="UPDATED_NEW"
        )
        
        logger.info(f"Successfully removed slot {slot_key_to_remove} from schedule {schedule_id}")
        return response

    except Exception as e:
        logger.error(f"Error removing timeslot: {e}", exc_info=True)
        return None


def book_appointment_slot(doctor_id: str, selected_slot: str, doctor_name: Optional[str] = None, 
                         user_name: Optional[str] = None, user_email: Optional[str] = None, 
                         symptoms_summary: Optional[str] = None, specialist_type: Optional[str] = None, 
                         session_id: Optional[str] = None, extraction_summary: Optional[str] = None) -> Dict[str, Any]:
    """
    Books an appointment slot and removes it from availability.
    
    Args:
        doctor_id: Unique identifier of the doctor
        selected_slot: Slot number selected by user (1-based index)
        doctor_name: Name of the doctor
        user_name: Name of the patient
        user_email: Email of the patient
        symptoms_summary: Summary of patient symptoms
        specialist_type: Type of medical specialist
        session_id: Session identifier for confirmation
        extraction_summary: Medical extraction summary
        
    Returns:
        Dictionary containing booking result and details
    """
    try:
        logger.info(f"Booking slot {selected_slot} for doctor {doctor_id}")
        
        # Get available timeslots
        timeslots = get_next_timeslots_for_doctor(doctor_id)
        
        if not timeslots:
            return {
                'success': False,
                'message': "No available timeslots found for this doctor."
            }
        
        # Validate slot selection
        try:
            slot_index = int(selected_slot) - 1  # Convert to 0-based index
            if slot_index < 0 or slot_index >= len(timeslots):
                return {
                    'success': False,
                    'message': f"Invalid slot number. Please select from 1 to {len(timeslots)}."
                }
        except ValueError:
            return {
                'success': False,
                'message': "Invalid slot number format. Please provide a number."
            }
        
        # Get the selected timestamp and remove it from availability
        selected_timestamp = timeslots[slot_index]
        removal_result = remove_timeslot_by_timestamp(doctor_id, selected_timestamp)
        
        if removal_result is None:
            return {
                'success': False,
                'message': "Unable to book this slot. It may have been taken by another patient. Please select a different slot."
            }
        
        # Format the appointment datetime for display
        dt = datetime.strptime(selected_timestamp, "%Y-%m-%dT%H:%M:%SZ")
        formatted_date = dt.strftime("%B %d, %Y at %I:%M %p")
        
        # Use sessionId as confirmation ID, fallback to UUID if not available
        unique_id = session_id if session_id else str(uuid.uuid4())[:8].upper()
        
        # Send confirmation email
        email_sent = False
        email_sent = send_confirmation_email(
            unique_id=unique_id,                            
            user_name=user_name or "ABC",  # Default fallback values
            user_email=user_email or "test@gmail.com",
            symptoms_summary=symptoms_summary or "General consultation",
            specialist_type=specialist_type or "General",    
            doctor_name=doctor_name or doctor_id,
            appointment_time=formatted_date,
            extraction_summary=extraction_summary or "NA"  
        )

        return {
            'success': True,
            'message': f"Successfully booked Slot {selected_slot}: {formatted_date}",
            'doctor_name': doctor_name or doctor_id,
            'slot_number': selected_slot,
            'appointment_datetime': formatted_date,
            'timestamp': selected_timestamp,
            'unique_id': unique_id,
            'email_sent': email_sent
        }
        
    except Exception as e:
        logger.error(f"Error in book_appointment_slot: {e}", exc_info=True)
        return {
            'success': False,
            'message': "An error occurred while booking the appointment. Please try again."
        }


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler function for appointment booking system.
    
    Handles three main functions:
    1. get_doctors_by_specialty - Find doctors by specialty and location
    2. get_doctor_timeslots - Get available timeslots for a specific doctor
    3. book_appointment_slot - Book a specific appointment slot
    
    Args:
        event: Lambda event containing function parameters and session data
        context: Lambda context object
        
    Returns:
        Dictionary containing the response for the action group
    """
    try:
        logger.info(f"Received event: {json.dumps(event, default=str)}")
        
        # Extract event parameters
        action_group = event['actionGroup']
        function = event['function']
        message_version = event.get('messageVersion', 1)
        parameters = event.get('parameters', [])
        
        # Extract session attributes and sessionId
        session_attributes = event.get('sessionAttributes', {})
        session_id = session_attributes.get('session_id', event.get('sessionId'))
        input_text = event.get('inputText', '')

        # Extract function parameters
        specialty = get_param_value(parameters, 'specialty')
        location = get_param_value(parameters, 'location')
        doctor_id = get_param_value(parameters, 'doctor_id')
        doctor_name = get_param_value(parameters, 'doctor_name')
        selected_slot = get_param_value(parameters, 'selected_slot')
        user_name = get_param_value(parameters, 'user_name')
        user_email = get_param_value(parameters, 'user_email')
        
        # Get symptoms_summary from session attributes
        symptoms_summary = session_attributes.get('symptoms_summary', '')
        
        logger.info(f"Function: {function}")
        logger.info(f"Session ID: {session_id}")
        logger.info(f"Parameters - specialty: {specialty}, location: {location}, doctor_id: {doctor_id}, doctor_name: {doctor_name}, selected_slot: {selected_slot}")
        logger.info(f"Session attributes: {session_attributes}")
        logger.info(f"Input text: {input_text}")

        response_body = {}
        updated_session_attributes = session_attributes.copy()

        # Function 1: Get doctors by specialty and location
        if function == 'get_doctors_by_specialty' and specialty and location:
            logger.info(f"Getting doctors for specialty: {specialty}, location: {location}")
            
            # Store specialty in session attributes for later use
            updated_session_attributes['current_specialty'] = specialty
            
            # Set appropriate symptoms based on specialty
            if not symptoms_summary:
                specialty_symptoms = {
                    'Pulmonology': 'Respiratory concerns (e.g., shortness of breath, cough, wheezing)',
                    'Cardiology': 'Heart-related symptoms (e.g., chest pain, palpitations, fatigue)',
                    'Dermatology': 'Skin condition (e.g., rashes, acne, infections, pigmentation)',
                    'Neurology': 'Neurological symptoms (e.g., headaches, seizures, dizziness, memory issues)',
                    'Orthopedics': 'Musculoskeletal issues (e.g., joint pain, fractures, back pain)',
                    'Gastroenterology': 'Digestive system concerns (e.g., abdominal pain, bloating, acid reflux)',
                    'ENT': 'Ear, nose, or throat issues (e.g., sinus problems, hearing loss, sore throat)',
                    'Ophthalmology': 'Eye-related concerns (e.g., blurred vision, redness, eye pain)',
                    'Psychiatry': 'Mental health consultation (e.g., anxiety, depression, sleep issues)',
                    'Gynecology': 'Women\'s health consultation (e.g., menstrual problems, PCOS, fertility)',
                    'Urology': 'Urinary or kidney concerns (e.g., frequent urination, UTI, kidney stones)',
                    'Endocrinology': 'Hormonal or metabolic issues (e.g., thyroid disorders, diabetes)',
                    'Rheumatology': 'Autoimmune and inflammatory conditions (e.g., arthritis, lupus)',
                    'Pediatrics': 'Child health issues (e.g., fever, infections, development concerns)',
                    'Oncology': 'Cancer-related concerns (e.g., abnormal growths, diagnosis follow-up)',
                    'Hematology': 'Blood-related issues (e.g., anemia, clotting disorders)',
                    'Nephrology': 'Kidney-related concerns (e.g., chronic kidney disease, proteinuria)',
                    'Hepatology': 'Liver-related conditions (e.g., hepatitis, liver function issues)',
                    'Infectious Disease': 'Infection-related concerns (e.g., fever, viral illness, long COVID)',
                    'General Medicine': 'General consultation or non-specific symptoms (e.g., fatigue, weakness)',
                    'Allergy and Immunology': 'Allergic reactions and immune system concerns (e.g., hay fever, hives)',
                    'Pain Management': 'Chronic or acute pain (e.g., migraines, neuropathy)',
                    'Plastic Surgery': 'Cosmetic or reconstructive surgery consultation',
                    'Dentistry': 'Tooth or oral health issues (e.g., pain, decay, gum issues)',
                    'Sexology': 'Sexual health concerns (e.g., performance issues, STIs)',
                    'Nutrition & Dietetics': 'Dietary guidance and nutritional issues (e.g., weight management, deficiency)',
                }
                default_symptom = specialty_symptoms.get(specialty, f'{specialty} consultation')
                updated_session_attributes['symptoms_summary'] = default_symptom
                logger.info(f"Set symptoms_summary to: {default_symptom}")

            # Enhanced symptom capture from user input
            if input_text and len(input_text.strip()) > 5:
                # Expanded symptom keywords for better capture
                symptom_keywords = [
                    'breathing', 'cough', 'chest', 'pain', 'headache', 'fever', 
                    'dizzy', 'nausea', 'stomach', 'back', 'joint', 'fatigue',
                    'shortness of breath', 'difficulty breathing', 'wheezing',
                    'heart', 'palpitations', 'anxiety', 'depression', 'skin',
                    'rash', 'allergy', 'sore throat', 'congestion', 'ache',
                    'hurt', 'discomfort', 'problem', 'issue', 'trouble'
                ]
                
                input_lower = input_text.lower()
                if any(keyword in input_lower for keyword in symptom_keywords):
                    updated_session_attributes['symptoms_summary'] = f"Patient reported: {input_text}"
                    logger.info(f"Captured symptoms from input: {input_text}")
                    
            # Query doctors table for matching specialty and location
            response = doctors_table.scan(
                FilterExpression=Attr('specialty').eq(specialty) & Attr('location').eq(location)
            )
            items = response.get('Items', [])
            logger.info(f"Found {len(items)} doctors")

            # Build doctors list with available timeslots
            doctors = []
            for item in items:
                doctor_id_item = item.get("doctor_id")
                timeslots = get_next_timeslots_for_doctor(doctor_id_item)
                doctors.append({
                    "doctor_id": doctor_id_item,
                    "name": item.get("name"),
                    "specialty": item.get("specialty"),
                    "location": item.get("location"),
                    "next_available_timeslots": timeslots
                })

            response_body = {
                'TEXT': {
                    'body': json.dumps({"doctors": doctors})
                }
            }

        # Function 2: Get doctor timeslots (ONLY for showing available slots)
        elif function == 'get_doctor_timeslots' and (doctor_id or doctor_name):
            logger.info(f"Getting timeslots for doctor_id: {doctor_id}, doctor_name: {doctor_name}")
            
            # Get doctor_id from name if not provided
            if not doctor_id and doctor_name:
                doctor_id = get_doctor_id_by_name(doctor_name)

            if not doctor_id:
                response_body = {
                    'TEXT': {
                        'body': "Doctor not found. Please try again."
                    }
                }

            else:
                timeslots = get_next_timeslots_for_doctor(doctor_id)
                response_body = {
                    'TEXT': {
                        'body': json.dumps({
                            "doctor_id": doctor_id,
                            "doctor_name": doctor_name,
                            "next_available_timeslots": timeslots
                        })
                    }
                }

        # Function 3: Book appointment slot
        elif function == 'book_appointment_slot' and selected_slot and (doctor_id or doctor_name):
            logger.info(f"Booking appointment - doctor_id: {doctor_id}, doctor_name: {doctor_name}, selected_slot: {selected_slot}")
            
            # Get doctor_id from name if not provided
            if not doctor_id and doctor_name:
                doctor_id = get_doctor_id_by_name(doctor_name)

            if not doctor_id:
                response_body = {
                    'TEXT': {
                        'body': "Doctor not found. Unable to book appointment."
                    }
                }
            else:
                # Get specialty and symptoms from session attributes
                specialist_type = updated_session_attributes.get('current_specialty')
                symptoms_summary = updated_session_attributes.get('symptoms_summary')
                
                # If specialty not found in session, get from doctor's record
                if not specialist_type:
                    try:
                        doctor_response = doctors_table.get_item(Key={'doctor_id': doctor_id})
                        if 'Item' in doctor_response:
                            specialist_type = doctor_response['Item'].get('specialty', 'General')
                            logger.info(f"Retrieved specialty from doctor record: {specialist_type}")
                        else:
                            specialist_type = 'General'
                    except Exception as e:
                        logger.error(f"Error fetching doctor specialty: {e}")
                        specialist_type = 'General'
                
                # Set appropriate symptoms based on specialty if not already set
                if not symptoms_summary:
                    specialty_symptoms = {
                        'Pulmonology': 'Respiratory concerns',
                        'Cardiology': 'Heart-related symptoms', 
                        'Dermatology': 'Skin condition',
                        'Neurology': 'Neurological symptoms',
                        'Orthopedics': 'Musculoskeletal issues',
                        'Gastroenterology': 'Digestive system concerns',
                        'ENT': 'Ear, nose, or throat issues',
                        'Ophthalmology': 'Eye-related concerns',
                        'Psychiatry': 'Mental health consultation',
                        'Gynecology': 'Women\'s health consultation'
                    }
                    symptoms_summary = specialty_symptoms.get(specialist_type, f'{specialist_type} consultation')
                
                # Enhanced logging for debugging
                logger.info(f"Final values - Specialty: {specialist_type}, Symptoms: {symptoms_summary}")
                logger.info(f"Using session_id as confirmation ID: {session_id}")
                
                # Fetch medical summary for the session
                extraction_summary = fetch_medical_summary_by_session_id(session_id)
                    
                # Book the appointment
                booking_result = book_appointment_slot(
                    doctor_id=doctor_id, 
                    selected_slot=selected_slot, 
                    doctor_name=doctor_name,
                    user_name=user_name,
                    user_email=user_email,
                    symptoms_summary=symptoms_summary,
                    specialist_type=specialist_type,
                    session_id=session_id,
                    extraction_summary=extraction_summary
                )

                # Format response based on booking result
                if booking_result['success']:
                    email_status = " A confirmation email has been sent to your email address." if booking_result.get('email_sent') else ""
                    response_body = {
                        'TEXT': {
                            'body': (
                                f"You have successfully scheduled Slot {booking_result['slot_number']}: "
                                f"{booking_result['appointment_datetime']} with {booking_result['doctor_name']} "
                                f"({specialist_type}).\n"
                                f"Your appointment confirmation ID is: {booking_result['unique_id']}\n"
                                f"Your appointment has been confirmed and the slot has been reserved for you."
                                f"{email_status}\n"
                                f"If you need further assistance, please let me know."
                            )
                        }
                    }

                else:
                    response_body = {
                        'TEXT': {
                            'body': booking_result['message']
                        }
                    }


        else:
            # Handle missing or invalid parameters
            error_msg = f"Missing or invalid parameters for function '{function}'. Please provide the required parameters."
            logger.error(f"{error_msg} Function: {function}, Parameters: {parameters}")
            response_body = {
                'TEXT': {
                    'body': error_msg
                }
            }


        logger.info(f"Returning response for function: {function}")
        return {
            'response': {
                "actionGroup": action_group,
                "function": function,
                "functionResponse": {
                    "responseBody": response_body
                }
            },
            'messageVersion': message_version,
            'sessionAttributes': updated_session_attributes  # Return updated session attributes
        }

    except Exception as e:
        logger.error(f"Unexpected error in lambda_handler: {e}", exc_info=True)
        return {
            'response': {
                "actionGroup": event.get('actionGroup', ''),
                "function": event.get('function', ''),
                "functionResponse": {
                    "responseBody": {
                        'TEXT': {
                            'body': "Internal server error occurred. Please try again later."
                        }
                    }
                }
            },
            'messageVersion': event.get('messageVersion', 1)
        }