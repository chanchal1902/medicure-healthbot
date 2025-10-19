# 🩺 MedicalAssignment Agent

The `MedicalAssignment` agent is designed to assist users in finding and booking medical appointments based on their symptoms, location, and preferred specialty. It integrates with backend Lambda functions to retrieve doctor availability, confirm bookings, and maintain session context — all while enforcing safety through guardrails.

---

## 🛠 Agent Configuration Summary

| Setting                     | Value                                                                |
|-----------------------------|----------------------------------------------------------------------|
| **Agent Name**              | `MedicalAssignmentAgent`                                             |
| **Model**                   | `Nova Premier 1.0`                                                   |
| **Agent Resource Role**     | `arn:aws:iam::xxxxxxxxxxxx:role/bedrock_med`                         |
| **Code Interpreter**        | Disabled                                                             |
| **User Input**              | Disabled                                                             |
| **Idle Session Timeout**    | `600 seconds`                                                        |
| **Session Summarization**   | Disabled                                                             |
| **Orchestration Strategy**  | Default (Pre-processing, Post-processing, Knowledge Base: Default)   |

---

## 📦 Action Group: `doctor_assign`

This agent uses a single action group to delegate appointment logic to the backend Lambda.

| Property                     | Value                                  |
|------------------------------|----------------------------------------|
| **Action Group Name**        | `doctor_assign`                        |
| **Type**                     | Define with function details           |
| **Invocation Method**        | Select an existing Lambda function     |
| **Linked Lambda Function**   | `doctor_assign`                        |
| **Action Status**            | Enabled                                |
| **Confirmation Required**    | Disabled                               |

---

### 🧠 Action Group Functions

#### 1. `get_doctors_by_specialty`

| Description | Finds doctors based on specialty and location |
|-------------|-----------------------------------------------|

**Parameters**:

| Name       | Description                        | Type   | Required |
|------------|------------------------------------|--------|----------|
| `specialty`| Medical specialty                  | string | ✅ Yes    |
| `location` | City or region to filter doctors   | string | ✅ Yes    |

---

#### 2. `get_doctor_timeslots`

| Description | Fetches the upcoming timeslots for a doctor |
|-------------|----------------------------------------------|

**Parameters**:

| Name         | Description                   | Type   | Required |
|--------------|-------------------------------|--------|----------|
| `doctor_id`  | The unique ID of the doctor   | string | ❌ No     |
| `doctor_name`| The name of the doctor        | string | ❌ No     |

---

#### 3. `book_appointment_slot`

| Description | Books a specific appointment slot for a doctor and removes it from availability |
|-------------|----------------------------------------------------------------------------------|

**Parameters**:

| Name          | Description                                      | Type   | Required |
|---------------|--------------------------------------------------|--------|----------|
| `doctor_id`   | The unique ID of the doctor                      | string | ✅ Yes    |
| `selected_slot`| The slot number to book (e.g., 1, 2, or 3)      | string | ✅ Yes    |
| `user_email`  | The patient's email address for confirmation     | string | ❌ No     |
| `user_name`   | The patient's full name                          | string | ❌ No     |
| `doctor_name` | The name of the doctor for confirmation          | string | ❌ No     |

---

## 📋 Agent Instructions

The agent is configured with the instructions below:
(Please refer  MediCure\Backend\Agents\MedicalAssignment\README.md)

---

## 🛡️ Guardrail Configuration

| Setting                        | Value                                                                                  |
|--------------------------------|----------------------------------------------------------------------------------------|
| **Guardrail Name**             | `Medical_Gaurdrail`                                                                    |
| **Description**                | Restrict agents to healthcare-related topics and prevent unsafe or irrelevant content. |
| **Content Filters Tier**       | Classic                                                                                |
| **Prompt Filters**             | Enabled                                                                                |
| **Response Filters**           | Enabled                                                                                |

### Harmful Category Filters (All BLOCKED at High Strength)

- Hate (Prompt & Response)
- Insults (Prompt & Response)
- Sexual (Prompt & Response)
- Violence (Prompt & Response)
- Misconduct (Prompt & Response)

### Blocked Messaging

- **Prompt Block Message**:  
  _"Sorry, I can’t process that request because it seems to contain sensitive or restricted information. Please remove any personal or confidential details and try again."_

- **Response Block Message**:  
  _"Sorry, I can’t process that request because it seems to contain sensitive or restricted information. Please remove any personal or confidential details and try again."_

---

## 🔄 Invocation Flow

1. A user interacts with the bot and shares symptoms or requests a specialist.
2. The `MedicalAssignmentAgent` is triggered via Amazon Lex to handle the request.
3. The agent calls the `doctor_assign` Lambda via the `doctor_assign` action group.
4. The Lambda returns doctor matches, timeslots, or booking confirmation.
5. The agent responds with structured output and updates session attributes.

---

