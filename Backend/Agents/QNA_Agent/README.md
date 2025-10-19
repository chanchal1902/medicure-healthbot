# ❓ QNA_Agent

The `QNA_Agent` is designed to answer user questions related to the medical report workflow, including document upload, extraction, assignment, and system interactions. It uses a **Knowledge Base (Medical_KB)** powered by Retrieval-Augmented Generation (RAG) to provide accurate and context-aware responses — all while enforcing safety through guardrails.

---

## 🧠 Agent Configuration Summary

| Setting                     | Value                                                                |
|-----------------------------|----------------------------------------------------------------------|
| **Agent Name**              | `QNA_Agent`                                                          |
| **Model**                   | `Nova Premier 1.0`                                                   |
| **Agent Resource Role**     | `arn:aws:iam::xxxxxxxxxxxx:role/bedrock_med`                         |
| **Code Interpreter**        | Disabled                                                             |
| **User Input**              | Disabled                                                             |
| **Idle Session Timeout**    | `600 seconds`                                                        |
| **Session Summarization**   | Disabled                                                             |
| **Orchestration Strategy**  | Default (Pre-processing, Post-processing, Knowledge Base: Default)   |

---
## 📋 Agent Instructions

The agent is configured with the instructions below:
(Please refer  MediCure\Backend\Agents\QNA_Agent\Agent_Instruction.txt)

---

## 📚 Knowledge Base: `Medical_KB`

This agent is connected to a Bedrock Knowledge Base that enables it to answer questions using indexed documents stored in S3.

### Configuration

| Property                     | Value                                                                |
|------------------------------|----------------------------------------------------------------------|
| **Knowledge Base Name**      | `Medical_KB`                                                         |
| **RAG Type**                 | Vector Store                                                         |
| **Service Role**             | Refer Agents\QNA_Agent\KB_permissions.json to create IAM role        |
| **Embeddings Model**         | `Titan Text Embeddings v2`                                           | 
| **Vector Dimensions**        | `1024`                                                               |
| **Vector Store Type**        | `Amazon OpenSearch Serverless`                                       |
| **Vector Index Name**        | `bedrock-knowledge-base-default-index`                               |
| **Vector Field Name**        | `bedrock-knowledge-base-default-vector`                              |
| **Text Field Name**          | `AMAZON_BEDROCK_TEXT`                                                |
| **Metadata Field Name**      | `AMAZON_BEDROCK_METADATA`                                            |
| **Multimodal Storage**       | `s3://user-data-agent/KB/kb_entries.json`                            |
| **KB Data Source**           | `kb_entries.json` stored in s3                                       |
| **Knowledge Base Status**    | Enabled                                                              |

### Agent Instruction for KB

Use this Knowledge Base to answer all questions related to document upload, extraction, assignment, and system interactions.

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

