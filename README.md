# 🏥 MediWatch AI: Next-Gen Clinical Support & Live Monitoring

**MediWatch AI** is an intelligent, real-time healthcare dashboard designed to bridge the gap between hardware monitoring and AI-driven clinical insights. Built for the 2026 Hackathon, it combines live Arduino sensor data with the power of Agentic AI to provide localized, actionable medical recommendations.

---

## 🌟 Key Features

* **❤️ Real-Time Vitals Tracking:** Live heart rate monitoring via Arduino hardware integration with a dynamic fallback to AI-simulated data.
* **🤖 Advanced Agentic AI:** Powered by **LLaMA 3.3 (70B)** on Groq, the system analyzes vitals and provides clinical recommendations in seconds.
* **🌍 Multi-Lingual Support (i18n):** Full UI and AI generation support for **English, Hindi, and Kannada**, making it accessible for rural healthcare.
* **🚨 Automated Alerts:** Instant **Slack integration** that notifies medical staff the moment a patient enters a critical state.
* **📊 Clinical Radar & Trends:** Visualizes patient health through historical trend charts and a "Vitals Radar" for quick diagnostic assessment.
* **🔊 Voice Accessibility:** Integrated Text-to-Speech (TTS) that reads out AI recommendations in the selected local language.

---

## 🛠️ Tech Stack

| Layer | Technology |
| :--- | :--- |
| **Backend** | Python, FastAPI, Uvicorn |
| **AI / LLM** | Groq Cloud, LLaMA 3.3 (70B) |
| **Frontend** | HTML5, CSS3 (Modern Glassmorphism), JavaScript (Vanilla), Chart.js |
| **Hardware** | Arduino, Pulse Sensor, C++, Python Serial Bridge |
| **Communication** | Slack Webhooks API |
| **Deployment** | Render (Cloud), GitHub |

---

## 🔌 Hardware Setup

1.  **Arduino:** Connect the Pulse Sensor to Pin `A0`.
2.  **Logic:** The Arduino uses a moving average filter and auto-thresholding for clean BPM detection.
3.  **Bridge:** Run `bridge.py` on a local machine to pipe Serial data from the USB port to the Cloud API.

---

## 🚀 Getting Started

### Local Development
1. Clone the repo: `git clone <your-repo-url>`
2. Install requirements: `pip install -r requirements.txt`
3. Set up `.env` with `GROQ_API_KEY` and `SLACK_WEBHOOK`.
4. Run server: `uvicorn app:app --reload`

### Hardware Bridge
1. Plug in Arduino.
2. Update `SERIAL_PORT` in `bridge.py`.
3. Run: `python bridge.py`

---


*Built with ❤️ for a healthier future.*# 👨‍💻