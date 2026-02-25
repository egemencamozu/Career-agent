"""
Career Assistant AI Agent — Test Cases
=======================================
3 test scenarios as required by the assignment.
Results are saved to test_results.json for documentation.
"""

from career_agent import CareerAgent
from datetime import datetime
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def print_separator():
    print("\n" + "=" * 80 + "\n")


def run_test_case(agent: CareerAgent, test_id: int, test_name: str, employer_message: str,
                  expected_tools: list = None, expect_unknown: bool = False):
    """Run a single test case, display results, and return structured data."""
    print_separator()
    print(f"🧪 TEST CASE {test_id}: {test_name}")
    print_separator()
    print(f"📩 EMPLOYER MESSAGE:\n{employer_message}")
    print_separator()

    result = agent.process_employer_message(employer_message, [])

    # Build score bar visualization
    score = result.get("evaluation_score", 0) or 0
    score_int = int(round(score))
    score_bar = "█" * score_int + "░" * (10 - score_int)

    print(f"📨 AGENT RESPONSE:\n{result['response']}")
    print_separator()

    print("📊 EVALUATION:")
    print(f"   Score: {score_bar} {score}/10")
    print(f"   Approved: {'✅ Yes' if result['is_approved'] else '❌ No'}")
    print(f"   Feedback: {result['evaluation_feedback']}")
    print(f"   Revisions: {result['revision_count']}")
    print(f"   Unknown Flagged: {'⚠️ Yes' if result['is_unknown'] else '✅ No'}")
    print_separator()

    # Determine pass/fail
    notes = []
    passed = True

    if expect_unknown:
        if result["is_unknown"]:
            notes.append("✅ Unknown question correctly flagged")
        else:
            notes.append("❌ Expected unknown flag but was not set")
            passed = False
    else:
        if not result["is_approved"]:
            notes.append(f"⚠️ Response not approved (score: {score}/10)")
            passed = False
        else:
            notes.append(f"✅ Response approved with score {score}/10")

    if result["revision_count"] > 0:
        notes.append(f"🔄 {result['revision_count']} revision(s) performed")

    # Build structured result
    test_result = {
        "test_id": test_id,
        "test_name": test_name,
        "message": employer_message,
        "reply": result["response"],
        "score": score,
        "is_approved": result["is_approved"],
        "is_unknown": result["is_unknown"],
        "revision_count": result["revision_count"],
        "feedback": result["evaluation_feedback"],
        "passed": passed,
        "notes": notes,
        "timestamp": datetime.now().isoformat(),
    }

    return test_result


def main():
    print("\n🤖 Career Assistant AI Agent — Test Suite")
    print("=" * 80)

    agent = CareerAgent()
    all_results = []

    # ─── Test Case 1: Standard Interview Invitation ───────────────────
    test1 = run_test_case(
        agent, 1, "Job Offer — Interview Invitation",
        (
            "Dear Egemen,\n\n"
            "We reviewed your profile and were impressed by your full-stack development experience. "
            "We'd like to invite you for a technical interview for our Junior Full-Stack Developer position "
            "at our Istanbul office. The role involves working with Angular and Spring Boot, which aligns "
            "with your skills. Would you be available next week for a 45-minute video call?\n\n"
            "Best regards,\nAhmet Yıldız\nHR Manager, TechCorp Istanbul"
        ),
        expected_tools=["notify_new_employer_message", "notify_response_approved"],
    )
    all_results.append(test1)

    # ─── Test Case 2: Technical Question ──────────────────────────────
    test2 = run_test_case(
        agent, 2, "Technical Background Question",
        (
            "Hi Egemen,\n\n"
            "We're evaluating candidates for our backend team. Could you describe your experience with "
            "Spring Boot and RESTful API design? Specifically:\n"
            "1. Have you worked with microservices architecture?\n"
            "2. What database technologies have you used?\n"
            "3. Do you have experience with Docker and CI/CD pipelines?\n\n"
            "Thanks,\nMehmet Kaya\nTech Lead, InnovateTech"
        ),
        expected_tools=["notify_new_employer_message"],
    )
    all_results.append(test2)

    # ─── Test Case 3: Unknown/Unsafe Question ─────────────────────────
    test3 = run_test_case(
        agent, 3, "Unknown/Unsafe Question — Salary, Legal, Outside Expertise",
        (
            "Hello Egemen,\n\n"
            "We have a senior position that might interest you. Before we proceed:\n"
            "1. What is your minimum acceptable salary in Turkish Lira?\n"
            "2. Are you willing to sign a 2-year non-compete clause?\n"
            "3. Can you demonstrate expertise in Rust and low-level systems programming?\n"
            "4. We need you to start within 2 weeks — is that possible?\n\n"
            "Regards,\nAyşe Demir\nCTO, CryptoStartup"
        ),
        expected_tools=["notify_new_employer_message", "flag_unknown_question"],
        expect_unknown=True,
    )
    all_results.append(test3)

    # ─── Save Results to JSON ─────────────────────────────────────────
    with open("test_results.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print("💾 Test results saved to test_results.json")

    # ─── Summary ──────────────────────────────────────────────────────
    print_separator()
    print("📋 TEST SUMMARY")
    print_separator()
    for r in all_results:
        status = "✅ PASS" if r["passed"] else "⚠️ REVIEW"
        unknown = " [FLAGGED]" if r["is_unknown"] else ""
        print(f"  {status} | {r['test_name']} | Score: {r['score']}/10 | Revisions: {r['revision_count']}{unknown}")

    print_separator()
    passed_count = sum(1 for r in all_results if r["passed"])
    print(f"🏁 {passed_count}/{len(all_results)} test cases passed.")


if __name__ == "__main__":
    main()
