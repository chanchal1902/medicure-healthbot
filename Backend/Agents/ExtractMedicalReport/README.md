# 🧠 ExtractMedicalReport Agent

The `ExtractMedicalReport` agent is designed to process uploaded medical reports and extract clinical insights using a Bedrock-powered orchestration. It is invoked by the `extractor_fe` Lambda and returns structured summaries that are stored in DynamoDB and used in downstream workflows such as appointment confirmation. Also, this agent maintains safety through guardrails.

---

## 🛠 Agent Configuration Summary

| Setting                     | Value                                                                |
|-----------------------------|----------------------------------------------------------------------|
| **Agent Name**              | `ExtractMedicalReport`                                               |
| **Model**                   | `Nova Premier 1.0`                                                   |
| **Agent Resource Role**     | `arn:aws:iam::25xxxxxxxxxx:role/bedrock_med`                         |
| **Code Interpreter**        | Disabled                                                             |
| **User Input**              | Disabled                                                             |
| **Idle Session Timeout**    | `600 seconds`                                                        |
| **Session Summarization**   | Disabled                                                             |
| **Orchestration Strategy**  | Default (Pre-processing, Post-processing, Knowledge Base: Default)   |

---

## 📦 Action Group: `extractor_fetch`

This agent uses a single action group to delegate document processing to a Lambda function.

### Action Group Configuration

| Property                     | Value                                  |
|------------------------------|----------------------------------------|
| **Action Group Name**        | `extractor_fetch`                      |
| **Type**                     | Define with function details           |
| **Invocation Method**        | Select an existing Lambda function     |
| **Linked Lambda Function**   | `extractor_backend`                    |
| **Group Function Name**      | `process_return`                       |
| **Confirmation Required**    | Disabled                               |
| **Action Status**            | Enabled                                |

### Parameters

| Name | Description     | Type   | Required |
|------|------------------|--------|----------|
| `sid` | Submission ID   | string | ✅ Yes    |

---

## 📋 Agent Instructions

The agent is configured with the instructions below:
(Please refer  MediCure\Backend\Agents\ExtractMedicalReport\Agent_Instruction.txt)


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

1. A user uploads a medical report via the UI.
2. `uploadToS3.py` stores the report in S3 and triggers `extractor_fe.py`.
3. `extractor_fe.py` invokes the `ExtractMedicalReport` agent with the session ID.
4. The agent calls the `extractor_backend` Lambda via the `extractor_fetch` action group.
5. Extracted insights are returned and stored in DynamoDB.

---



