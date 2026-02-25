# Career Assistant AI Agent — Design Report
**Egemen ÇAMÖZÜ — Akdeniz University**  
**Advanced Web Technologies — Spring 2026**

---

## 1. Introduction

This report describes the design and implementation of a **Career Assistant AI Agent** that communicates with potential employers on behalf of the user. The agent receives employer messages, generates professional responses using the user's CV/profile data, self-evaluates those responses, and notifies the user of important events via email.

The system is built using **LangGraph** for the agent loop, **OpenAI GPT-4o-mini** as the language model, and **Gradio** for the frontend interface.

---

## 2. Design Decisions

### 2.1 Architecture: LangGraph StateGraph

The agent uses a **graph-based architecture** with LangGraph's `StateGraph`. This was chosen because:

- **Explicit control flow**: Each step (generation → tool handling → evaluation → revision) is a distinct node with clear routing logic.
- **State management**: `AgentState` (TypedDict) tracks messages, evaluation scores, revision counts, and flags across the entire pipeline.
- **Conditional routing**: `worker_router` and `evaluation_router` decide the next step based on tool calls and evaluation results.

The graph consists of 4 nodes:

| Node | Role |
|------|------|
| `worker` | Generates responses using CV context + system prompt |
| `tools` | Executes tool calls (email, flagging) |
| `evaluator` | Scores the response using Structured Output (Pydantic) |
| `revise` | Increments revision counter and sends back to worker |

### 2.2 Modular File Structure

Unlike a single-file approach, the project separates concerns:

- **`career_tools.py`** — Tool definitions and implementations (email, flagging)
- **`career_agent.py`** — Agent class with LangGraph graph, LLMs, and profile loading
- **`app.py`** — Gradio frontend (no business logic)
- **`test_cases.py`** — Test scenarios (no agent logic)

This follows the **Single Responsibility Principle** and makes each component independently testable.

### 2.3 LLM Choice: GPT-4o-mini

- **Cost-effective**: Significantly cheaper than GPT-4o while maintaining high quality for professional correspondence
- **Fast inference**: Suitable for the multi-turn evaluation loop (worker → evaluator → revision)
- **Structured Output support**: The evaluator uses `with_structured_output(EvaluationResult)` for reliable JSON parsing

### 2.4 Email over Push Notifications

Gmail SMTP was chosen because:
- No third-party service dependencies (unlike Pushover)
- Email provides a permanent record of interactions
- Console fallback ensures the agent works even without email credentials

---

## 3. Evaluation Strategy

### 3.1 LLM-as-a-Judge Pattern

The evaluator uses **GPT-4o-mini with Structured Output** to score responses on 5 criteria:

| Criterion | Description |
|-----------|-------------|
| **Professional Tone** | Is the response polite, formal, and appropriate? |
| **Clarity** | Is it easy to understand and well-structured? |
| **Completeness** | Does it fully address the employer's message? |
| **Safety** | Are there any hallucinations, false claims, or risky commitments? |
| **Relevance** | Does it directly address what the employer asked? |

### 3.2 Scoring and Threshold

- **Score range**: 1.0 to 10.0
- **Approval threshold**: Score ≥ 7.0
- **Max revisions**: 3 attempts before accepting the response as-is
- **Revision feedback**: The evaluator's feedback is injected into the system prompt for the next attempt

### 3.3 Structured Output (Pydantic)

The `EvaluationResult` model ensures type-safe evaluation:

```python
class EvaluationResult(BaseModel):
    score: float
    professional_tone: bool
    clarity: bool
    completeness: bool
    safety: bool
    relevance: bool
    feedback: str
    is_approved: bool
```

This eliminates JSON parsing errors and guarantees consistent evaluation structure.

---

## 4. Test Results

### 4.1 Test Case 1: Interview Invitation ✅

- **Input**: TechCorp Istanbul invites for a Junior Full-Stack Developer interview
- **Result**: Score 9/10, approved on first pass
- **Tools**: `notify_new_employer_message`, `notify_response_approved`
- **Observation**: Agent correctly expressed enthusiasm, confirmed availability, and asked for time slots

### 4.2 Test Case 2: Technical Question ✅

- **Input**: InnovateTech asks about Spring Boot, microservices, databases, Docker/CI-CD
- **Result**: Score 8/10, approved
- **Tools**: `notify_new_employer_message`, `flag_unknown_question` (microservices flagged as outside expertise)
- **Observation**: Agent honestly stated limited microservices experience — evaluator praised this honesty

### 4.3 Test Case 3: Unknown/Unsafe Question ⚠️

- **Input**: CryptoStartup asks about salary, non-compete clause, Rust expertise, immediate start
- **Result**: Score 5/10, max revisions reached (3), `is_unknown` flagged
- **Tools**: `flag_unknown_question` triggered 4 times (salary, legal, outside expertise, ambiguous offer)
- **Observation**: This is the **expected and correct behavior** — the agent refuses to fabricate answers about salary or claim skills it doesn't have

---

## 5. Failure Cases and Edge Cases

### 5.1 Evaluator–Worker Loop Tension

In Test Case 3, the evaluator scored the response low (4-5/10) because it wanted the agent to provide salary figures and negotiate non-compete terms. However, the worker was explicitly instructed **not** to commit to salary or legal agreements.

**Root cause**: The evaluator's "completeness" criterion conflicts with the worker's safety rules. The evaluator sees an unanswered question as incomplete, while the worker correctly defers to human intervention.

**Solution**: This tension is actually a feature — it demonstrates that the agent prioritizes safety over completeness. The max revision limit (3) prevents infinite loops.

### 5.2 Response Extraction Bug (Fixed)

Initially, the evaluator evaluated `state["messages"][-1].content`, which could be a tool result message or a brief summary instead of the actual response text. This was fixed by implementing `_extract_agent_response()` which:
1. Scans for the last substantive AI message (content > 50 chars)
2. Falls back to tool call arguments (e.g., `notify_response_approved` contains the full response)
3. Last resort: uses whatever the last message content is

### 5.3 Tool Call Content Issue

When the worker calls `notify_response_approved`, it sometimes puts the full response only in the tool arguments and writes a brief "I've sent the notification" in the message content. This was mitigated by updating the system prompt with explicit instructions:
- "You MUST write the FULL response text in your message content"
- "After writing your full response, THEN call tools"

---

## 6. Reflection

### What Worked Well
- **LangGraph's StateGraph** made the agent loop explicit and debuggable
- **Structured Output** eliminated JSON parsing issues in evaluation
- **The self-revision loop** demonstrably improved responses (Test 1: first draft → revised draft)
- **Email notifications** provided real-time alerts during testing
- **Honest handling** of unknown questions — the agent never fabricated skills it doesn't have

### What Could Be Improved
- **Evaluator calibration**: The evaluator could be better calibrated for cases where deferring to human review is the correct action (not penalizing for "incompleteness")
- **Multi-turn conversation**: Currently each message is processed independently; a full conversation thread would enable context-aware responses
- **Response speed**: The evaluate–revise loop adds latency (3-4 LLM calls per message). Caching or parallel evaluation could help
- **Deployment**: The current implementation runs locally; cloud deployment (e.g., Hugging Face Spaces) would make it accessible

### Lessons Learned
1. **Self-critic patterns** are powerful but need careful prompt design to avoid conflicting objectives
2. **Safety vs. completeness** is a real tension in AI agents — sometimes the right answer is "I don't know"
3. **Graph-based architectures** (LangGraph) provide much better visibility into agent behavior than simple prompt chains
4. **Structured Output** (Pydantic) is essential for reliable evaluation — raw JSON parsing is fragile

---

## 7. References

- Ed Donner, "Agentic AI" course materials (Weeks 1-4)
- LangGraph documentation: https://langchain-ai.github.io/langgraph/
- OpenAI Structured Output: https://platform.openai.com/docs/guides/structured-outputs
