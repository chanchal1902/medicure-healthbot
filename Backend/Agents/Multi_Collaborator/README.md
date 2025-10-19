# 🤝 Multi_Collaborator Agent

The `Multi_Collaborator` agent is a supervisor agent configured to coordinate responses across multiple specialized agents using **multi-agent collaboration**. It intelligently routes user queries to the appropriate collaborator based on domain expertise, ensuring accurate, contextual, and actionable responses.

---

## 🧠 Agent Configuration Summary

| Setting                     | Value                                                                |
|-----------------------------|----------------------------------------------------------------------|
| **Agent Name**              | `Multi_Collaborator`                                                 |
| **Model**                   | `Nova Premier 1.0`                                                   |
| **Agent Resource Role**     | `arn:aws:iam::xxxxxxxxxxxx:role/bedrock_med`                         |
| **Code Interpreter**        | Disabled                                                             |
| **User Input**              | Disabled                                                             |
| **Idle Session Timeout**    | `600 seconds`                                                        |
| **Session Summarization**   | Disabled                                                             |
| **Orchestration Strategy**  | Default (Pre-processing, Post-processing, Knowledge Base: Default)   |
| **Multi-Agent Collaboration** | Enabled                                                            |
| **Collaboration Mode**      | Supervisor with routing                                              |

---

## 👥 Collaborator Agents

### 1. 🩺 `MedicalAssignmentAgent` (Alias: select latest alias)

**Role**: Handles doctor booking workflow.

**Responsibilities**:
- Collect symptoms from the user.
- Determine location.
- Suggest available doctors based on symptom and location.
- Allow doctor and slot selection.
- Confirm booking and provide details.

**Routing Behavior**:
- Responds only to booking and assignment-related queries.
- For unrelated questions, replies with:  
  _“I’m not able to answer this question; please ask the Knowledge Base Agent.”_

**Tone**: Concise, professional, and actionable.

---

### 2. ❓ `QNAAgent` (Alias: select latest alias)

**Role**: Answers system-related questions using the Knowledge Base.

**Responsibilities**:
- Explain system processes, document uploads, extraction, validation, and assignment rules.
- Summarize relevant KB entries clearly.
- Avoid booking or symptom-related topics.

**Routing Behavior**:
- For unclear or out-of-scope questions, replies with:  
  _“I’m unable to find information on this topic in the Knowledge Base.”_

**Tone**: Factual, professional, and assumption-free.

---

## 📋 Agent Instructions

The agent is configured with the instructions below:
(Please refer  MediCure\Backend\Agents\Multi_Collaborator\Agent_Instruction.txt)

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

