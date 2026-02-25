# Career Assistant AI Agent  
**Egemen ÇAMÖZÜ — 20220808076**  
Advanced Web Technologies — Akdeniz University

A self-evaluating AI agent that communicates with potential employers on behalf of the user, built with **LangGraph**, **OpenAI GPT-4o-mini**, and **Gradio**.

## Architecture

The system consists of 4 core components:

| Component | Description |
|---|---|
| **Career Worker** | Primary agent that generates professional responses using CV/profile context |
| **Response Evaluator** | Self-critic (LLM-as-a-Judge) that scores responses on 5 criteria |
| **Email Notification** | Sends Gmail alerts for new messages, approvals, and unknown questions |
| **Unknown Question Detector** | Detects questions outside expertise and triggers human intervention |

### System Flow (LangGraph StateGraph)

```
Employer Message (Gradio UI)
        |
  [Career Worker] — generates response using CV context
        |
  Tool Calls? ──> Yes ──> [Tool Handler] ──> back to Worker
        | No
  [Response Evaluator] — LLM-as-a-Judge (Structured Output)
        |
  Score >= 7? ──> Yes ──> ✅ Approved ──> Email Notification ──> Return to Employer
        | No
  Revisions < 3? ──> Yes ──> 🔄 Revision (feedback injected) ──> back to Worker
        | No
  Max revisions ──> Accept response as-is
```

## Project Structure

```
career_agent/
├── career_agent.py           # Main agent: LangGraph graph (Worker + Evaluator + Tools)
├── career_tools.py           # Tools: email notification, unknown question detection
├── app.py                    # Gradio frontend with test scenario buttons
├── test_cases.py             # 3 test scenarios with JSON output
├── test_results.json         # Structured test results (auto-generated)
├── career_agent.log          # Detailed execution logs
├── README.md                 # This file
├── reports/
│   ├── report.md             # 3-5 page design report
│   └── prompt_documentation.md  # Prompt design documentation
└── me/
    ├── summary.txt           # Personal summary for agent context
    └── linkedin.pdf          # LinkedIn profile (PDF) for agent context
```

## Quick Start

### Prerequisites
```bash
pip install langchain-openai langgraph gradio pypdf python-dotenv pydantic
```

### Environment Variables
Create a `.env` file in the parent directory:
```
OPENAI_API_KEY=your_openai_api_key
EMAIL_ADDRESS=your_gmail@gmail.com
EMAIL_PASSWORD=your_gmail_app_password
NOTIFICATION_EMAIL=your_email@gmail.com
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
```

### Run the Agent
```bash
# Launch Gradio UI
python app.py

# Run test cases
python test_cases.py
```
Opens Gradio chat interface at `http://127.0.0.1:7860`

## Test Cases

| # | Test | Tools Triggered | Score | Result |
|---|---|---|---|---|
| 1 | **Interview Invitation** — TechCorp Istanbul | notify_new_employer_message, notify_response_approved | 9/10 | ✅ PASS |
| 2 | **Technical Question** — Spring Boot, Docker, microservices | notify_new_employer_message, flag_unknown_question | 8/10 | ✅ PASS |
| 3 | **Unknown/Unsafe Question** — Salary, legal, Rust, start date | flag_unknown_question (x4) | 5/10 | ⚠️ FLAGGED |

## Key Features

### Self-Evaluating Response Loop (LangGraph)
- Worker generates a draft response using CV context
- Evaluator scores it on 5 criteria via **Structured Output** (Pydantic)
- Score < 7 triggers automatic revision with feedback injection
- Max 3 revision attempts before graceful acceptance

### Tool Execution (OpenAI Function Calling)
- **notify_new_employer_message(employer_name, message_preview)** — Email alert for new messages
- **notify_response_approved(employer_name, response_text, score)** — Email alert for approved responses
- **flag_unknown_question(question, reason, confidence_score)** — Flags salary, legal, outside expertise questions

### Email Notifications (Gmail SMTP)
4 notification types:
1. New employer message (instant email)
2. Response approved (with score)
3. Unknown question flagged (with confidence level)
4. Console fallback if email is not configured

### Evaluation Criteria (Structured Output)
```json
{
  "score": 9.0,
  "professional_tone": true,
  "clarity": true,
  "completeness": true,
  "safety": true,
  "relevance": true,
  "feedback": "Well-structured professional response...",
  "is_approved": true
}
```

### Confidence Visualization
Score bar and boolean checks displayed in chat:
```
📊 Score: █████████░ 9/10 | Unknown: No
✅ Professional Tone | ✅ Clarity | ✅ Completeness | ✅ Safety | ✅ Relevance
```

## Tech Stack

| Technology | Purpose |
|---|---|
| **OpenAI GPT-4o-mini** | LLM API (worker + evaluator) |
| **LangGraph** | Agent graph framework (StateGraph) |
| **LangChain** | LLM integration (ChatOpenAI) |
| **Gradio** | Chat interface (frontend) |
| **Gmail SMTP** | Email notifications |
| **pypdf** | LinkedIn PDF parsing |
| **Pydantic** | Structured evaluation output |
| **Python** | Core language |

## Author

**Egemen ÇAMÖZÜ**  
Computer Engineering Student — Akdeniz University, Antalya
