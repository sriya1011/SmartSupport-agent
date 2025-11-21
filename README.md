# SmartSupport-agent
# 📨 SmartSupport — AI-Powered Multi-Agent Customer Support Assistant

SmartSupport is a **multi-agent AI system** that automates customer support workflows by:
- Classifying support tickets (billing, technical, account, general)
- Assigning priority and escalation levels
- Generating polite auto-replies using a knowledge base
- Maintaining long-term customer history for contextual responses
- Providing a sleek, professional **Gradio-based UI**

This project is built for the **Google x Kaggle AI Agents Capstone (2025)** under the **Enterprise Agents** track.

---

## 🚀 Features

| Feature | Description |
|---------|------------|
| **Multi-Agent Pipeline** | Intake → Classification → Reply Generation → Escalation |
| **Rule-based Classification** | Detects intent and urgency from text |
| **Auto-Replies** | Uses predefined FAQ knowledge base |
| **Long-Term Memory** | Stores past tickets in JSON and personalizes responses |
| **Professional UI** | Dark theme, animated cards, technical dashboard look |
| **Observability** | Raw ticket JSON view for debugging and transparency |

---

## 📂 Project Structure
SmartSupport-Agent/
│
├── app.py # Full Gradio application
├── requirements.txt # Dependencies for Hugging Face / local setup
├── tickets_log.json # Stored ticket history (created automatically)
└── README.md # Documentation

----

**Live demo**
click here[https://huggingface.co/spaces/sriya1011/SmartSupport-agent]

---

🏆 Project Context

This project was developed as a submission for:

**Google x Kaggle — 5-Day AI Agents Intensive Capstone (2025)**
**Track: Enterprise Agents**
The goal is to demonstrate:
- Multi-agent orchestration
- Tools & context state
- Memory persistence
- Observability
- Human-in-the-loop escalation logic

---

👩‍💻 Author
- Sriya Sahu
