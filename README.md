# 🏥 MediWatch AI — Healthcare Agentic AI System

## 📌 Overview
MediWatch AI is a real-time patient monitoring dashboard powered by Agentic AI. It continuously monitors patient vitals, detects life-threatening anomalies, and autonomously generates clinical recommendations using LLaMA 3.1 via Groq.

## 🌐 Live Demo
👉 https://mediwatch-ai.onrender.com

## 🚀 Features
- ✅ Real-time vital signs monitoring (Heart Rate, Blood Pressure, Oxygen)
- ✅ Automatic anomaly detection with color-coded alerts (Normal/Warning/Critical)
- ✅ AI-powered clinical recommendations using Groq LLaMA 3.1
- ✅ Live heart rate trend charts and blood pressure graphs
- ✅ Add new patients via the dashboard
- ✅ Export patient data as CSV
- ✅ Smart alarm system for new critical patients
- ✅ Auto-refresh every 30 seconds
- ✅ Sensor API endpoint for real hardware integration

## 🛠️ Tech Stack
- **Backend**: Python, FastAPI, Uvicorn
- **AI**: Groq API (LLaMA 3.1 8B Instant)
- **Frontend**: HTML, CSS, JavaScript, Chart.js
- **Deployment**: Render

## ⚙️ How to Run Locally

### 1. Clone the repository
git clone https://github.com/guptavernit2-afk/mediwatch-ai.git
cd mediwatch-ai

### 2. Install dependencies
pip install -r requirements.txt

### 3. Set up API key
Create a .env file:
GROQ_API_KEY=your-groq-api-key-here

### 4. Run the app
uvicorn app:app --host 0.0.0.0 --port 8000 --reload

### 5. Open in browser
http://localhost:8000

## 🔌 Sensor Integration API
To connect a real hardware sensor, send a POST request to:
POST https://mediwatch-ai.onrender.com/api/patients

With this JSON body:
{
  "name": "Patient Name",
  "age": 25,
  "heart_rate": 98,
  "blood_pressure_sys": 120,
  "blood_pressure_dia": 80,
  "oxygen": 97
}

## 🏗️ Architecture
Sensor / User Input
       ↓
FastAPI Backend (app.py)
       ↓
Anomaly Detection Engine → Groq LLaMA 3.1 AI
       ↓
Real-time Dashboard (index.html)

## 📊 How it Works
1. Data Ingestion — Patient vitals monitored in real-time with live fluctuations
2. Anomaly Engine — Detects dangerous drifts in Heart Rate, Blood Pressure, and Oxygen
3. Agentic AI — LLaMA 3.1 analyzes trends and generates specific clinical recommendations
4. Alert System — Critical patients trigger instant visual and audio alerts

## 👤 Built For
Gen-AI Hackathon 2026 — Healthcare Agentic AI Track