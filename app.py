"""
Career Assistant AI Agent — Gradio Frontend
============================================
Clean, professional web interface.
"""

import gradio as gr
from career_agent import CareerAgent


CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
* { font-family: 'Inter', sans-serif !important; }

footer { display: none !important; }

.header-area {
    text-align: center;
    padding: 28px 20px 12px;
}
.header-area h1 {
    font-size: 1.5rem !important;
    font-weight: 700 !important;
    color: #1e293b !important;
    margin: 0 !important;
}
.header-area p {
    color: #64748b !important;
    font-size: 0.85rem !important;
    margin-top: 4px !important;
}

.scenario-btn {
    border: 1px solid #e2e8f0 !important;
    border-radius: 10px !important;
    background: #fff !important;
    color: #334155 !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    padding: 12px 16px !important;
    text-align: left !important;
    transition: all 0.15s ease !important;
}
.scenario-btn:hover {
    border-color: #6366f1 !important;
    background: #f5f3ff !important;
    color: #4338ca !important;
}

.send-btn {
    background: #4f46e5 !important;
    border: none !important;
    border-radius: 10px !important;
    color: white !important;
    font-weight: 600 !important;
    padding: 12px 28px !important;
}
.send-btn:hover {
    background: #4338ca !important;
}

.side-section h3 {
    font-size: 0.82rem !important;
    color: #94a3b8 !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.04em !important;
    margin-bottom: 8px !important;
}
.side-section p {
    font-size: 0.82rem !important;
    color: #64748b !important;
    line-height: 1.6 !important;
}

.footer-line {
    text-align: center;
    padding: 8px 0 4px;
}
.footer-line p {
    color: #cbd5e1 !important;
    font-size: 0.7rem !important;
}
"""


def create_ui():
    agent = CareerAgent()

    with gr.Blocks(
        title="Career Assistant — Egemen ÇAMÖZÜ",
    ) as ui:

        # ─── Header ──────────────────────────────────
        gr.Markdown(
            "# 🤖 Career Assistant\n"
            "Communicate with employers on your behalf — powered by AI",
            elem_classes="header-area",
        )

        # ─── Main ────────────────────────────────────
        chatbot = gr.Chatbot(
            label="Conversation",
            height="70vh",
        )

        with gr.Group():
            with gr.Row():
                message_input = gr.Textbox(
                    show_label=False,
                    placeholder="Paste an employer message here...",
                    scale=5,
                    lines=2,
                )
                send_btn = gr.Button("Send", variant="primary", scale=1, elem_classes="send-btn")

        with gr.Row():
            example_btn1 = gr.Button("📩 Interview Invitation", elem_classes="scenario-btn")
            example_btn2 = gr.Button("💻 Technical Question", elem_classes="scenario-btn")
            example_btn3 = gr.Button("⚠️ Tricky / Unknown Question", elem_classes="scenario-btn")

        with gr.Accordion("ℹ️ About", open=False):
            gr.Markdown(
                "This agent reads your CV & LinkedIn, drafts a professional reply, "
                "self-evaluates it on a 1–10 scale, and revises if needed. "
                "You get an email when a response is ready or a question needs your attention."
            )

        gr.Markdown(
            "Egemen ÇAMÖZÜ · 20220808076 · Akdeniz University",
            elem_classes="footer-line",
        )

        # ─── Data ────────────────────────────────────
        examples = {
            "interview": (
                "Dear Egemen,\n\n"
                "We reviewed your profile and were impressed by your full-stack development experience. "
                "We'd like to invite you for a technical interview for our Junior Full-Stack Developer position "
                "at our Istanbul office. The role involves working with Angular and Spring Boot, which aligns "
                "with your skills. Would you be available next week for a 45-minute video call?\n\n"
                "Best regards,\nAhmet Yıldız\nHR Manager, TechCorp Istanbul"
            ),
            "technical": (
                "Hi Egemen,\n\n"
                "We're evaluating candidates for our backend team. Could you describe your experience with "
                "Spring Boot and RESTful API design? Specifically:\n"
                "1. Have you worked with microservices architecture?\n"
                "2. What database technologies have you used?\n"
                "3. Do you have experience with Docker and CI/CD pipelines?\n\n"
                "Thanks,\nMehmet Kaya\nTech Lead, InnovateTech"
            ),
            "unknown": (
                "Hello Egemen,\n\n"
                "We have a senior position that might interest you. Before we proceed:\n"
                "1. What is your minimum acceptable salary in Turkish Lira?\n"
                "2. Are you willing to sign a 2-year non-compete clause?\n"
                "3. Can you demonstrate expertise in Rust and low-level systems programming?\n"
                "4. We need you to start within 2 weeks — is that possible?\n\n"
                "Regards,\nAyşe Demir\nCTO, CryptoStartup"
            ),
        }

        example_btn1.click(lambda: examples["interview"], outputs=[message_input])
        example_btn2.click(lambda: examples["technical"], outputs=[message_input])
        example_btn3.click(lambda: examples["unknown"], outputs=[message_input])

        def respond(message, history):
            if not message.strip():
                return history, ""
            user_msg = {"role": "user", "content": f"📩 **Employer Message:**\n\n{message}"}
            response = agent.chat(message, history)
            assistant_msg = {"role": "assistant", "content": response}
            return history + [user_msg, assistant_msg], ""

        send_btn.click(respond, [message_input, chatbot], [chatbot, message_input])
        message_input.submit(respond, [message_input, chatbot], [chatbot, message_input])

    return ui


if __name__ == "__main__":
    ui = create_ui()
    ui.launch(
        inbrowser=True,
        theme=gr.themes.Soft(
            primary_hue="indigo",
            secondary_hue="slate",
            font=gr.themes.GoogleFont("Inter"),
        ),
        css=CUSTOM_CSS,
    )
