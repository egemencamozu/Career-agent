"""
Career Assistant AI Agent
=========================
LangGraph-based agent with Worker (Career Agent) + Evaluator (Response Critic) nodes.
Based on Ed Donner's Sidekick pattern from Week 4 (LangGraph).
"""

from typing import Annotated, List, Any, Optional, Dict
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from pypdf import PdfReader
from datetime import datetime
from career_tools import tools, tool_functions, notify_new_employer_message, notify_response_approved, flag_unknown_question
import json
import uuid
import logging
import os

load_dotenv(override=True)
logger = logging.getLogger(__name__)


# ─── State Definition ────────────────────────────────────────────────

class AgentState(TypedDict):
    messages: Annotated[List[Any], add_messages]
    employer_message: str
    evaluation_score: Optional[float]
    evaluation_feedback: Optional[str]
    is_approved: bool
    is_unknown: bool
    revision_count: int


# ─── Evaluator Structured Output ─────────────────────────────────────

class EvaluationResult(BaseModel):
    score: float = Field(description="Overall quality score from 1 to 10")
    professional_tone: bool = Field(description="Whether the response has a professional tone")
    clarity: bool = Field(description="Whether the response is clear and easy to understand")
    completeness: bool = Field(description="Whether the response fully addresses the employer's message")
    safety: bool = Field(description="Whether the response is safe (no hallucinations, no false claims)")
    relevance: bool = Field(description="Whether the response is relevant to the employer's message")
    feedback: str = Field(description="Detailed feedback for improvement")
    is_approved: bool = Field(description="Whether the response meets the quality threshold (score >= 7)")


# ─── Career Agent Class ──────────────────────────────────────────────

class CareerAgent:

    SCORE_THRESHOLD = 7.0
    MAX_REVISIONS = 3

    def __init__(self):
        self.agent_id = str(uuid.uuid4())
        self.memory = MemorySaver()
        self.graph = None

        # Load profile data
        self.name = "Egemen ÇAMÖZÜ"
        self.summary = ""
        self.linkedin = ""
        self._load_profile()

        # LLMs
        worker_llm = ChatOpenAI(model="gpt-4o-mini")
        evaluator_llm = ChatOpenAI(model="gpt-4o-mini")
        self.worker_llm = worker_llm
        self.evaluator_llm = evaluator_llm.with_structured_output(EvaluationResult)

        # Build graph
        self._build_graph()

    def _load_profile(self):
        """Load CV summary and LinkedIn PDF."""
        base_dir = os.path.dirname(os.path.abspath(__file__))

        summary_path = os.path.join(base_dir, "me", "summary.txt")
        if os.path.exists(summary_path):
            with open(summary_path, "r", encoding="utf-8") as f:
                self.summary = f.read()

        linkedin_path = os.path.join(base_dir, "me", "linkedin.pdf")
        if os.path.exists(linkedin_path):
            reader = PdfReader(linkedin_path)
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    self.linkedin += text

        logger.info(f"Profile loaded: summary={len(self.summary)} chars, linkedin={len(self.linkedin)} chars")

    def _system_prompt(self, state: AgentState) -> str:
        """Build the system prompt with CV context."""
        prompt = f"""You are acting as {self.name}'s Career Assistant AI Agent. 
You communicate with potential employers ON BEHALF of {self.name}.
The current date is {datetime.now().strftime("%Y-%m-%d")}.

YOUR ROLE:
- Receive messages from potential employers and generate professional responses
- Maintain a professional, concise, and polite tone at all times
- Use {self.name}'s CV/profile information to answer questions accurately

YOUR CAPABILITIES:
1. Answer interview invitations — express enthusiasm and confirm availability
2. Respond to technical questions — based ONLY on {self.name}'s actual skills and experience
3. Politely decline offers — when they don't match {self.name}'s interests or availability
4. Ask clarifying questions — when the employer's message is vague or needs more detail

YOUR TOOLS:
- notify_new_employer_message: Call this FIRST when processing a new employer message
- notify_response_approved: Call this when your response is finalized and approved
- flag_unknown_question: Call this when you encounter questions about:
  * Salary expectations or negotiations
  * Legal matters (contracts, non-compete clauses, NDAs)
  * Technical topics outside {self.name}'s expertise
  * Ambiguous or unclear job offers
  * Any question where your confidence is below 50%

IMPORTANT RESPONSE FORMAT:
- You MUST write the FULL response text in your message content
- After writing your full response, THEN call tools (notify, flag, etc.)
- Do NOT put your response only inside tool call arguments
- The evaluator will judge your message content, so it must contain the complete response

IMPORTANT RULES:
- NEVER fabricate skills, experience, or qualifications not in the profile
- NEVER commit to salary figures or legal agreements
- NEVER share personal contact information beyond what's in the profile
- If unsure, use the flag_unknown_question tool and politely tell the employer you'll get back to them
- Always respond in the same language as the employer's message

## {self.name}'s Profile Summary:
{self.summary}

## {self.name}'s LinkedIn Profile:
{self.linkedin}
"""

        if state.get("evaluation_feedback") and state.get("revision_count", 0) > 0:
            prompt += f"""

## REVISION REQUIRED
Your previous response was evaluated and did NOT meet the quality threshold.
Evaluator Feedback: {state['evaluation_feedback']}
Please revise your response addressing this feedback.
This is revision attempt {state['revision_count']} of {self.MAX_REVISIONS}.
"""
        return prompt

    # ─── Graph Nodes ──────────────────────────────────────────────────

    def career_worker(self, state: AgentState) -> Dict[str, Any]:
        """The main career agent that generates responses to employer messages."""
        system_msg = self._system_prompt(state)

        messages = list(state["messages"])

        # Update or insert system message
        has_system = False
        for msg in messages:
            if isinstance(msg, SystemMessage):
                msg.content = system_msg
                has_system = True
                break
        if not has_system:
            messages = [SystemMessage(content=system_msg)] + messages

        response = self.worker_llm.invoke(messages, tools=tools)

        return {"messages": [response]}

    def tool_handler(self, state: AgentState) -> Dict[str, Any]:
        """Handle tool calls from the career agent."""
        last_message = state["messages"][-1]
        results = []
        is_unknown = state.get("is_unknown", False)

        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            for tool_call in last_message.tool_calls:
                tool_name = tool_call["name"]
                arguments = tool_call["args"]

                logger.info(f"Tool called: {tool_name} with args: {json.dumps(arguments, ensure_ascii=False)}")

                func = tool_functions.get(tool_name)
                if func:
                    result = func(**arguments)
                    if tool_name == "flag_unknown_question":
                        is_unknown = True
                else:
                    result = {"error": f"Unknown tool: {tool_name}"}

                results.append({
                    "role": "tool",
                    "content": json.dumps(result, ensure_ascii=False),
                    "tool_call_id": tool_call["id"]
                })

        return {"messages": results, "is_unknown": is_unknown}

    def _extract_agent_response(self, state: AgentState) -> str:
        """Extract the substantive response from the message history.
        
        Priority:
        1. Look for notify_response_approved tool call args (always has the full response)
        2. Look for substantive AI message content (filter out meta-messages)
        3. Last resort: return whatever we can find
        """
        # Priority 1: Check tool call arguments for the actual response text
        for msg in reversed(state["messages"]):
            if isinstance(msg, AIMessage) and hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    if tc["name"] == "notify_response_approved":
                        response_text = tc["args"].get("response_text", "")
                        if response_text:
                            return response_text

        # Priority 2: Look for AI message with real content (skip meta-messages)
        meta_phrases = [
            "I have successfully sent",
            "I've sent the",
            "I've successfully",
            "successfully sent",
            "notification has been",
            "If there are any further",
            "please let me know",
        ]
        for msg in reversed(state["messages"]):
            if isinstance(msg, AIMessage) and msg.content and len(msg.content) > 50:
                if "Evaluation Result" in msg.content:
                    continue
                # Skip meta-messages about tool execution
                if any(phrase.lower() in msg.content.lower() for phrase in meta_phrases):
                    continue
                return msg.content

        # Priority 3: Last resort — return the last AI message content
        for msg in reversed(state["messages"]):
            if isinstance(msg, AIMessage) and msg.content:
                if "Evaluation Result" not in msg.content:
                    return msg.content

        last = state["messages"][-1]
        return last.content if hasattr(last, "content") else str(last)

    def response_evaluator(self, state: AgentState) -> Dict[str, Any]:
        """Evaluate the career agent's response for quality."""
        last_response = self._extract_agent_response(state)
        employer_msg = state.get("employer_message", "")

        eval_prompt = f"""You are evaluating a Career Assistant AI Agent's response to an employer message.

EMPLOYER'S ORIGINAL MESSAGE:
{employer_msg}

AGENT'S RESPONSE TO EVALUATE:
{last_response}

Evaluate the response on these criteria:
1. Professional tone — Is it professional, polite, and appropriate?
2. Clarity — Is it clear and easy to understand?
3. Completeness — Does it fully address the employer's message?
4. Safety — Are there any hallucinations, false claims, or inappropriate commitments?
5. Relevance — Is the response relevant to what the employer asked?

Score from 1 to 10. Approve if score >= 7.
Provide detailed feedback for any areas that need improvement.
"""
        eval_messages = [
            SystemMessage(content="You are a strict but fair evaluator of professional correspondence."),
            HumanMessage(content=eval_prompt)
        ]

        eval_result = self.evaluator_llm.invoke(eval_messages)

        logger.info(
            f"Evaluation: score={eval_result.score}, approved={eval_result.is_approved}, "
            f"tone={eval_result.professional_tone}, clarity={eval_result.clarity}, "
            f"completeness={eval_result.completeness}, safety={eval_result.safety}, "
            f"relevance={eval_result.relevance}"
        )
        logger.info(f"Evaluator feedback: {eval_result.feedback}")

        return {
            "evaluation_score": eval_result.score,
            "evaluation_feedback": eval_result.feedback,
            "is_approved": eval_result.is_approved,
            "messages": [{
                "role": "assistant",
                "content": (
                    f"📊 **Evaluation Result**\n"
                    f"- **Score:** {eval_result.score}/10\n"
                    f"- **Professional Tone:** {'✅' if eval_result.professional_tone else '❌'}\n"
                    f"- **Clarity:** {'✅' if eval_result.clarity else '❌'}\n"
                    f"- **Completeness:** {'✅' if eval_result.completeness else '❌'}\n"
                    f"- **Safety:** {'✅' if eval_result.safety else '❌'}\n"
                    f"- **Relevance:** {'✅' if eval_result.relevance else '❌'}\n"
                    f"- **Feedback:** {eval_result.feedback}\n"
                    f"- **Status:** {'✅ Approved' if eval_result.is_approved else '🔄 Revision Required'}"
                )
            }]
        }

    # ─── Routing Functions ────────────────────────────────────────────

    def worker_router(self, state: AgentState) -> str:
        """Route after worker: if tool calls exist, go to tools; otherwise evaluate."""
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "tools"
        return "evaluator"

    def evaluation_router(self, state: AgentState) -> str:
        """Route after evaluation: if approved go to END, otherwise revise."""
        if state.get("is_approved", False):
            return "END"
        if state.get("revision_count", 0) >= self.MAX_REVISIONS:
            logger.warning(f"Max revisions ({self.MAX_REVISIONS}) reached. Accepting response as-is.")
            return "END"
        return "revise"

    def increment_revision(self, state: AgentState) -> Dict[str, Any]:
        """Increment the revision counter before sending back to worker."""
        return {"revision_count": state.get("revision_count", 0) + 1}

    # ─── Graph Construction ───────────────────────────────────────────

    def _build_graph(self):
        """Build the LangGraph state graph."""
        graph_builder = StateGraph(AgentState)

        # Add nodes
        graph_builder.add_node("worker", self.career_worker)
        graph_builder.add_node("tools", self.tool_handler)
        graph_builder.add_node("evaluator", self.response_evaluator)
        graph_builder.add_node("revise", self.increment_revision)

        # Add edges
        graph_builder.add_edge(START, "worker")
        graph_builder.add_conditional_edges(
            "worker",
            self.worker_router,
            {"tools": "tools", "evaluator": "evaluator"}
        )
        graph_builder.add_edge("tools", "worker")
        graph_builder.add_conditional_edges(
            "evaluator",
            self.evaluation_router,
            {"END": END, "revise": "revise"}
        )
        graph_builder.add_edge("revise", "worker")

        # Compile with memory
        self.graph = graph_builder.compile(checkpointer=self.memory)
        logger.info("Career Agent graph compiled successfully.")

    # ─── Public Interface ─────────────────────────────────────────────

    def process_employer_message(self, employer_message: str, history: list) -> dict:
        """
        Process an employer message and return the agent's response with evaluation.
        
        Returns dict with: response, evaluation_score, evaluation_feedback, is_approved, is_unknown
        """
        config = {"configurable": {"thread_id": self.agent_id}}

        state = {
            "messages": [HumanMessage(content=employer_message)],
            "employer_message": employer_message,
            "evaluation_score": None,
            "evaluation_feedback": None,
            "is_approved": False,
            "is_unknown": False,
            "revision_count": 0,
        }

        result = self.graph.invoke(state, config=config)

        # Extract the agent's response using our improved extraction method
        agent_response = self._extract_agent_response(result)

        # Find evaluation message
        eval_message = ""
        for msg in reversed(result["messages"]):
            content = msg["content"] if isinstance(msg, dict) else (msg.content if hasattr(msg, "content") else "")
            if "Evaluation Result" in str(content):
                eval_message = content
                break

        return {
            "response": agent_response,
            "evaluation_score": result.get("evaluation_score"),
            "evaluation_feedback": result.get("evaluation_feedback"),
            "is_approved": result.get("is_approved", False),
            "is_unknown": result.get("is_unknown", False),
            "eval_display": eval_message,
            "revision_count": result.get("revision_count", 0),
        }

    def chat(self, message: str, history: list) -> str:
        """Gradio chat interface."""
        result = self.process_employer_message(message, history)

        response_parts = []

        # Main response
        if result["response"]:
            response_parts.append(f"**📨 Response to Employer:**\n\n{result['response']}")

        # Score bar visualization
        score = result.get("evaluation_score", 0) or 0
        score_int = int(round(score))
        score_bar = "█" * score_int + "░" * (10 - score_int)
        unknown_flag = "Yes ⚠️" if result["is_unknown"] else "No"

        score_card = (
            f"\n\n---\n"
            f"**📊 Score:** `{score_bar}` **{score}/10** | "
            f"**Unknown:** {unknown_flag}"
        )

        if result["revision_count"] > 0:
            score_card += f" | **Revisions:** {result['revision_count']}"

        response_parts.append(score_card)

        # Detailed evaluation info
        if result["eval_display"]:
            response_parts.append(f"\n{result['eval_display']}")

        if result["is_unknown"]:
            response_parts.append("\n⚠️ **Some questions were flagged for human review.**")

        return "\n".join(response_parts)
