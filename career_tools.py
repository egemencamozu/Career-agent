"""
Career Agent Tools
==================
Email notification and unknown question detection tools for the Career Assistant AI Agent.
"""

import os
import json
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(override=True)

# ─── Logging Setup ───────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("career_agent.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ─── Email Configuration ─────────────────────────────────────────────
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
NOTIFICATION_EMAIL = os.getenv("NOTIFICATION_EMAIL")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))


def send_email_notification(subject: str, body: str) -> dict:
    """
    Send an email notification to the user.
    Falls back to console logging if email credentials are not configured.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not all([EMAIL_ADDRESS, EMAIL_PASSWORD, NOTIFICATION_EMAIL]):
        logger.warning("Email credentials not configured. Logging notification to console.")
        logger.info(f"📧 NOTIFICATION [{timestamp}]")
        logger.info(f"   Subject: {subject}")
        logger.info(f"   Body: {body}")
        return {"status": "logged_to_console", "timestamp": timestamp, "subject": subject}

    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = NOTIFICATION_EMAIL
        msg["Subject"] = f"[Career Agent] {subject}"

        email_body = f"""
Career Assistant AI Agent Notification
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Time: {timestamp}

{body}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This is an automated notification from your Career Assistant AI Agent.
"""
        msg.attach(MIMEText(email_body, "plain", "utf-8"))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, NOTIFICATION_EMAIL, msg.as_string())

        logger.info(f"📧 Email sent successfully: {subject}")
        return {"status": "email_sent", "timestamp": timestamp, "subject": subject}

    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        logger.info(f"📧 FALLBACK NOTIFICATION [{timestamp}]: {subject} — {body}")
        return {"status": "email_failed", "error": str(e), "timestamp": timestamp}


# ─── Tool Functions ──────────────────────────────────────────────────

def notify_new_employer_message(employer_name: str, message_preview: str) -> dict:
    """Send a notification when a new employer message arrives."""
    subject = f"New message from {employer_name}"
    body = f"You received a new message from {employer_name}.\n\nPreview:\n{message_preview[:300]}"
    result = send_email_notification(subject, body)
    logger.info(f"New employer message notification: {employer_name}")
    return result


def notify_response_approved(employer_name: str, response_text: str, evaluation_score: float) -> dict:
    """Send a notification when a response is approved and ready to send."""
    subject = f"Response approved for {employer_name} (Score: {evaluation_score}/10)"
    body = (
        f"Your response to {employer_name} has been approved by the evaluator.\n\n"
        f"Evaluation Score: {evaluation_score}/10\n\n"
        f"Response:\n{response_text}"
    )
    result = send_email_notification(subject, body)
    logger.info(f"Response approved notification: {employer_name}, score={evaluation_score}")
    return result


def flag_unknown_question(question: str, reason: str, confidence_score: float) -> dict:
    """
    Flag a question that the agent cannot confidently answer.
    Triggers notification and logs the event for human review.
    """
    subject = f"⚠️ Unknown Question — Human Intervention Needed (Confidence: {confidence_score:.0%})"
    body = (
        f"The Career Agent encountered a question it cannot confidently answer.\n\n"
        f"Question: {question}\n\n"
        f"Reason: {reason}\n\n"
        f"Confidence Score: {confidence_score:.0%}\n\n"
        f"Action Required: Please review and provide a manual response."
    )
    result = send_email_notification(subject, body)
    logger.warning(f"Unknown question flagged: {question} | Reason: {reason} | Confidence: {confidence_score}")
    return {**result, "flagged": True, "question": question, "reason": reason, "confidence_score": confidence_score}


# ─── OpenAI Tool JSON Definitions ────────────────────────────────────

notify_new_message_json = {
    "name": "notify_new_employer_message",
    "description": "Use this tool to send a notification when a new employer message arrives. Call this at the start of processing every new employer message.",
    "parameters": {
        "type": "object",
        "properties": {
            "employer_name": {
                "type": "string",
                "description": "The name of the employer or company that sent the message"
            },
            "message_preview": {
                "type": "string",
                "description": "A brief preview of the employer's message"
            }
        },
        "required": ["employer_name", "message_preview"],
        "additionalProperties": False
    }
}

notify_response_approved_json = {
    "name": "notify_response_approved",
    "description": "Use this tool to send a notification when the final response has been approved by the evaluator and is ready to be sent to the employer.",
    "parameters": {
        "type": "object",
        "properties": {
            "employer_name": {
                "type": "string",
                "description": "The name of the employer or company"
            },
            "response_text": {
                "type": "string",
                "description": "The full approved response text"
            },
            "evaluation_score": {
                "type": "number",
                "description": "The evaluation score out of 10"
            }
        },
        "required": ["employer_name", "response_text", "evaluation_score"],
        "additionalProperties": False
    }
}

flag_unknown_question_json = {
    "name": "flag_unknown_question",
    "description": "Use this tool when you encounter a question you cannot confidently answer. This includes: salary negotiations, legal questions (non-compete, contracts), deep technical questions outside Egemen's expertise, ambiguous job offers, or any question where your confidence is low. Always use this tool rather than making up an answer.",
    "parameters": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The question that cannot be confidently answered"
            },
            "reason": {
                "type": "string",
                "description": "Why this question cannot be answered (e.g., 'salary_negotiation', 'legal_question', 'outside_expertise', 'ambiguous_offer', 'low_confidence')"
            },
            "confidence_score": {
                "type": "number",
                "description": "Your confidence in answering this question, from 0.0 to 1.0. Use this tool when confidence is below 0.5."
            }
        },
        "required": ["question", "reason", "confidence_score"],
        "additionalProperties": False
    }
}

# ─── Tool Registry ───────────────────────────────────────────────────

tools = [
    {"type": "function", "function": notify_new_message_json},
    {"type": "function", "function": notify_response_approved_json},
    {"type": "function", "function": flag_unknown_question_json},
]

tool_functions = {
    "notify_new_employer_message": notify_new_employer_message,
    "notify_response_approved": notify_response_approved,
    "flag_unknown_question": flag_unknown_question,
}
