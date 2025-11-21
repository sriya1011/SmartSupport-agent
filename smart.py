# ================== IMPORTS ==================
import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Dict, Any, Optional

import gradio as gr

logging.basicConfig(level=logging.INFO)

# ================== DATA MODEL ==================
@dataclass
class Ticket:
    ticket_id: str
    customer_id: str
    channel: str
    text: str
    created_at: str
    true_category: Optional[str] = None
    predicted_category: Optional[str] = None
    priority: Optional[str] = None
    auto_reply: Optional[str] = None
    escalated: bool = False
    escalation_reason: Optional[str] = None


# ================== TOOLS: STORAGE & HISTORY ==================
TICKET_LOG_FILE = "tickets_log.json"


def save_ticket(ticket: Ticket):
    """Append a ticket to JSON log (acts as long-term memory)."""
    try:
        data = json.load(open(TICKET_LOG_FILE, "r", encoding="utf-8"))
    except FileNotFoundError:
        data = []
    data.append(asdict(ticket))
    with open(TICKET_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logging.info(f"[TicketStore] Saved ticket {ticket.ticket_id}")


def load_all_tickets() -> List[Dict[str, Any]]:
    try:
        return json.load(open(TICKET_LOG_FILE, "r", encoding="utf-8"))
    except FileNotFoundError:
        return []


def get_customer_history(customer_id: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Return last N tickets for this customer (simple memory)."""
    all_tickets = load_all_tickets()
    history = [t for t in all_tickets if t.get("customer_id") == customer_id]
    return history[-limit:]


# ================== TOOL: KNOWLEDGE BASE ==================
FAQ = [
    {
        "category": "billing",
        "question": "refund policy",
        "answer": "Our refund policy allows refunds within 7 days of purchase."
    },
    {
        "category": "technical",
        "question": "app not working",
        "answer": "Please try restarting the app, checking your connection, and reinstalling if the issue persists."
    },
    {
        "category": "account",
        "question": "password reset",
        "answer": "You can reset your password by clicking 'Forgot Password' on the login page."
    },
    {
        "category": "general",
        "question": "support hours",
        "answer": "Our support team is available 9 AM – 6 PM, Monday to Friday."
    },
]


def search_knowledge_base(category: str, ticket_text: str) -> str:
    """Very simple KB lookup by category."""
    for entry in FAQ:
        if entry["category"] == category:
            return entry["answer"]
    return (
        "Thank you for contacting support. We have received your message and "
        "will get back to you shortly after reviewing your issue."
    )


# ================== AGENTS ==================
def intake_agent(raw_text: str, ticket_id: str, customer_id: str, channel: str = "email") -> Ticket:
    """Creates the initial Ticket object from raw input."""
    ticket = Ticket(
        ticket_id=ticket_id,
        customer_id=customer_id,
        channel=channel,
        text=raw_text,
        created_at=datetime.now().isoformat()
    )
    logging.info(f"[IntakeAgent] Created ticket {ticket_id}")
    return ticket


def classify_and_prioritize_agent(ticket: Ticket) -> Ticket:
    """Classifies ticket into category + priority with simple rules."""
    text = ticket.text.lower()

    # Category rules
    if any(k in text for k in ["refund", "charged twice", "billing", "invoice", "payment issue"]):
        category = "billing"
    elif any(k in text for k in ["crash", "error", "bug", "not working", "issue", "fail"]):
        category = "technical"
    elif any(k in text for k in ["login", "password", "account", "sign in"]):
        category = "account"
    else:
        category = "general"

    # Priority rules
    if any(k in text for k in ["urgent", "asap", "immediately", "cannot access", "down"]):
        priority = "urgent"
    elif any(k in text for k in ["not working", "failed", "error"]):
        priority = "high"
    else:
        priority = "medium"

    ticket.predicted_category = category
    ticket.priority = priority
    logging.info(f"[ClassifierAgent] {ticket.ticket_id}: category={category}, priority={priority}")
    return ticket


def reply_generation_agent(ticket: Ticket) -> Ticket:
    """Generates a reply using the FAQ tool + customer history."""
    kb_answer = search_knowledge_base(ticket.predicted_category, ticket.text)
    history = get_customer_history(ticket.customer_id)

    history_note = ""
    if history:
        history_note = (
            f"\n\nWe noticed you contacted us {len(history)} time(s) before. "
            f"Thank you for your patience while we resolve this."
        )

    reply = (
        "Hi,\n\n"
        "Thanks for reaching out to our support team.\n\n"
        f"{kb_answer}"
        f"{history_note}\n\n"
        "If this does not fully solve your issue, please reply to this message "
        "and a human support agent will assist you further.\n\n"
        "Best regards,\n"
        "SmartSupport Team"
    )

    ticket.auto_reply = reply
    logging.info(f"[ReplyAgent] Generated reply for {ticket.ticket_id}")
    return ticket


def escalation_agent(ticket: Ticket) -> Ticket:
    """Decides whether to escalate ticket to a human agent."""
    escalate = False
    reason = None

    if ticket.priority == "urgent":
        escalate = True
        reason = "Urgent priority issue"
    elif ticket.predicted_category == "general" and len(ticket.text) > 400:
        escalate = True
        reason = "Long, unclear general query"

    ticket.escalated = escalate
    ticket.escalation_reason = reason
    logging.info(f"[EscalationAgent] {ticket.ticket_id}: escalated={escalate}, reason={reason}")
    return ticket


# ================== ORCHESTRATOR ==================
def process_ticket(raw_text: str, ticket_id: str, customer_id: str, channel: str = "email") -> Ticket:
    """Sequentially runs the multi-agent pipeline."""
    # 1. Intake
    ticket = intake_agent(raw_text, ticket_id, customer_id, channel)

    # 2. Classification & Priority
    ticket = classify_and_prioritize_agent(ticket)

    # 3. Reply Generation
    ticket = reply_generation_agent(ticket)

    # 4. Escalation Decision
    ticket = escalation_agent(ticket)

    # 5. Persist
    save_ticket(ticket)

    return ticket


# ================== GRADIO WRAPPER ==================
def gradio_process_ticket(text: str, customer_id: str, channel: str):
    """Wrapper function for Gradio UI."""
    if not text.strip():
        return (
            "", "", "", "", "", "Please enter a ticket message.", "{}"
        )

    if not customer_id.strip():
        customer_id = "anonymous"

    ticket_id = "UI-" + datetime.now().strftime("%Y%m%d%H%M%S")

    ticket = process_ticket(
        raw_text=text,
        ticket_id=ticket_id,
        customer_id=customer_id,
        channel=channel.lower()
    )

    escalated_str = "Yes" if ticket.escalated else "No"
    escalation_reason = ticket.escalation_reason or ""

    ticket_json = json.dumps(asdict(ticket), indent=2, ensure_ascii=False)

    return (
        ticket.ticket_id,
        ticket.predicted_category or "",
        ticket.priority or "",
        escalated_str,
        escalation_reason,
        ticket.auto_reply or "",
        ticket_json
    )


def clear_all():
    """Clear all UI fields."""
    return (
        "",      # text_input
        "",      # customer_input
        "email", # channel_input
        "",      # ticket_id_out
        "",      # category_out
        "",      # priority_out
        "",      # escalated_out
        "",      # reason_out
        "",      # reply_out
        "{}",    # raw_json_out
    )


# ================== PROFESSIONAL, SUBTLE CSS ==================
custom_css = """
/* Dark technical background */
body {
    background: radial-gradient(circle at top, #0b1120 0, #020617 45%, #020617 100%);
    color: #e5e7eb;
}

/* Title & subtitle */
#app-title {
    font-size: 2.4rem;
    font-weight: 800;
    text-align: center;
    margin-bottom: 0.15rem;
    letter-spacing: 0.05em;
    color: #e5e7eb;
    animation: titleFade 0.7s ease-out;
}

#app-subtitle {
    text-align: center;
    color: #9ca3af;
    margin-bottom: 1.4rem;
    font-size: 0.95rem;
    animation: subtitleFade 0.9s ease-out;
}

@keyframes titleFade {
    0% { opacity: 0; transform: translateY(-6px); }
    100% { opacity: 1; transform: translateY(0); }
}

@keyframes subtitleFade {
    0% { opacity: 0; transform: translateY(4px); }
    100% { opacity: 1; transform: translateY(0); }
}

/* Card layout – subtle, technical */
.card {
    border-radius: 14px;
    padding: 18px;
    border: 1px solid rgba(31, 41, 55, 0.9);
    background: linear-gradient(135deg, #020617 0%, #020617 60%, #020617 100%);
    box-shadow: 0 18px 40px rgba(15, 23, 42, 0.55);
    position: relative;
    overflow: hidden;
    transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
}

/* Accent bar on left for technical feel */
.card::before {
    content: "";
    position: absolute;
    left: 0;
    top: 0;
    width: 4px;
    height: 100%;
    background: linear-gradient(to bottom, #38bdf8, #6366f1);
    opacity: 0.9;
}

/* Subtle hover */
.card:hover {
    transform: translateY(-3px);
    box-shadow: 0 22px 50px rgba(15, 23, 42, 0.7);
    border-color: rgba(99, 102, 241, 0.7);
}

/* Labels small, professional */
.label-small label {
    font-size: 0.78rem !important;
    color: #9ca3af !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}

/* Inputs & textareas */
input, textarea, select {
    border-radius: 10px !important;
    border-color: #1f2937 !important;
    background-color: #020617 !important;
    color: #e5e7eb !important;
    font-size: 0.9rem !important;
}

/* Focus state */
input:focus, textarea:focus, select:focus {
    outline: none !important;
    border-color: #6366f1 !important;
    box-shadow: 0 0 0 1px rgba(99, 102, 241, 0.6) !important;
}

/* Buttons – flat, technical, with micro animation */
button {
    border-radius: 999px !important;
    font-weight: 600 !important;
    letter-spacing: 0.03em;
    padding: 0.45rem 1.1rem !important;
    border: 1px solid transparent !important;
    transition: background 0.16s ease, transform 0.12s ease, box-shadow 0.16s ease, border-color 0.16s ease;
}

button:hover {
    transform: translateY(-1px);
    box-shadow: 0 10px 24px rgba(15, 23, 42, 0.6);
}

button:active {
    transform: translateY(0);
    box-shadow: 0 4px 12px rgba(15, 23, 42, 0.5);
}

button.primary, button[aria-label*="Analyze"] {
    background: linear-gradient(90deg, #2563eb, #4f46e5) !important;
    border-color: #1d4ed8 !important;
    color: white !important;
}

button.secondary, button[aria-label*="Clear"] {
    background: transparent !important;
    border-color: #4b5563 !important;
    color: #e5e7eb !important;
}

/* Accordion JSON box */
code, pre {
    border-radius: 12px !important;
    background-color: #020617 !important;
}

/* Small tip text */
.tip-text {
    font-size: 0.8rem;
    color: #6b7280;
}
"""


# ================== GRADIO UI ==================
with gr.Blocks(theme=gr.themes.Soft(), css=custom_css) as demo:
    # Title section
    gr.Markdown('<div id="app-title">SmartSupport</div>')
    gr.Markdown(
        '<div id="app-subtitle">'
        'Enterprise-grade multi-agent ticket assistant: classify → prioritize → escalate → reply.'
        '</div>'
    )

    with gr.Row():
        # LEFT: Input card
        with gr.Column(scale=5):
            with gr.Group(elem_classes="card"):
                gr.Markdown("#### Ticket Input")

                text_input = gr.Textbox(
                    lines=7,
                    label="Ticket Message",
                    placeholder="Example: Hi, I was charged twice for my subscription this month. Please refund ASAP."
                )

                with gr.Row():
                    customer_input = gr.Textbox(
                        label="Customer ID",
                        placeholder="e.g., C123 (used for history/memory)",
                    )
                    channel_input = gr.Dropdown(
                        ["email", "chat", "web"],
                        value="email",
                        label="Channel",
                    )

                with gr.Row():
                    submit_btn = gr.Button("Analyze Ticket", elem_classes=["primary"])
                    clear_btn = gr.Button("Clear", elem_classes=["secondary"])

                gr.Markdown(
                    "<span class='tip-text'>Tip: Use the same Customer ID for multiple tickets to see how history affects replies.</span>"
                )

        # RIGHT: Output card
        with gr.Column(scale=5):
            with gr.Group(elem_classes="card"):
                gr.Markdown("#### Agent Decision & Reply")

                with gr.Row():
                    ticket_id_out = gr.Textbox(
                        label="Ticket ID",
                        interactive=False,
                        elem_classes=["label-small"]
                    )
                    category_out = gr.Textbox(
                        label="Category",
                        interactive=False,
                        elem_classes=["label-small"]
                    )
                    priority_out = gr.Textbox(
                        label="Priority",
                        interactive=False,
                        elem_classes=["label-small"]
                    )

                with gr.Row():
                    escalated_out = gr.Textbox(
                        label="Escalated?",
                        interactive=False,
                        elem_classes=["label-small"]
                    )
                    reason_out = gr.Textbox(
                        label="Escalation Reason",
                        interactive=False,
                        elem_classes=["label-small"]
                    )

                reply_out = gr.Textbox(
                    label="Auto-Generated Reply",
                    lines=9,
                    interactive=False,
                )

            with gr.Accordion("Advanced: Raw Ticket Object (observability)", open=False):
                raw_json_out = gr.Code(
                    label="Ticket JSON",
                    language="json"
                )

    # Button actions
    submit_btn.click(
        fn=gradio_process_ticket,
        inputs=[text_input, customer_input, channel_input],
        outputs=[
            ticket_id_out,
            category_out,
            priority_out,
            escalated_out,
            reason_out,
            reply_out,
            raw_json_out,
        ],
    )

    clear_btn.click(
        fn=clear_all,
        inputs=None,
        outputs=[
            text_input,
            customer_input,
            channel_input,
            ticket_id_out,
            category_out,
            priority_out,
            escalated_out,
            reason_out,
            reply_out,
            raw_json_out,
        ],
    )

demo.launch()

