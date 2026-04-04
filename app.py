import os
import random
import csv
import time
from io import StringIO
from datetime import datetime
from pydantic import BaseModel
from groq import Groq
from dotenv import load_dotenv

# 1. LOAD ENV SECURELY
load_dotenv()

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
import uvicorn

# 2. SLACK ALERTS
from slack_alerts import send_slack_alert, send_slack_test_message

# Securely load the API key from Render's Vault or your local .env file
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
app = FastAPI()

# Clinical Thresholds
THRESHOLDS = {
    "heart_rate": {"min": 60, "max": 100},
    "blood_pressure_sys": {"min": 90, "max": 140},
    "blood_pressure_dia": {"min": 60, "max": 90},
    "oxygen": {"min": 95, "max": 100},
}

PATIENTS_DATA = [
    {"patient_id": "P001", "name": "Raj Sharma",   "age": 45, "heart_rate": 72,  "blood_pressure_sys": 120, "blood_pressure_dia": 80,  "oxygen": 98, "is_sensor": False, "last_ai_update": 0, "cached_rec": "", "cached_lang": "en"},
    {"patient_id": "P002", "name": "Priya Patel",  "age": 32, "heart_rate": 65,  "blood_pressure_sys": 115, "blood_pressure_dia": 75,  "oxygen": 99, "is_sensor": False, "last_ai_update": 0, "cached_rec": "", "cached_lang": "en"},
    # Fixed Amit Verma's ghost sensor!
    {"patient_id": "P003", "name": "Amit Verma",   "age": 60, "heart_rate": 105, "blood_pressure_sys": 160, "blood_pressure_dia": 100, "oxygen": 91, "is_sensor": False, "last_ai_update": 0, "cached_rec": "", "cached_lang": "en"},
    {"patient_id": "P004", "name": "Sunita Rao",   "age": 28, "heart_rate": 88,  "blood_pressure_sys": 118, "blood_pressure_dia": 76,  "oxygen": 97, "is_sensor": False, "last_ai_update": 0, "cached_rec": "", "cached_lang": "en"},
    {"patient_id": "P005", "name": "Vikram Singh", "age": 55, "heart_rate": 48,  "blood_pressure_sys": 85,  "blood_pressure_dia": 55,  "oxygen": 93, "is_sensor": False, "last_ai_update": 0, "cached_rec": "", "cached_lang": "en"},
]

HR_HISTORY = {p["patient_id"]: [p["heart_rate"]] * 6 for p in PATIENTS_DATA}


def detect_anomalies(entry: dict) -> list:
    anomalies = []
    for vital, limits in THRESHOLDS.items():
        val = entry.get(vital)
        if val is not None and (val < limits["min"] or val > limits["max"]):
            anomalies.append({"vital": vital, "value": val, "min": limits["min"], "max": limits["max"]})
    return anomalies


def get_status(anomalies):
    if not anomalies: return "normal"
    elif len(anomalies) >= 3: return "critical"
    else: return "warning"


def get_ai_recommendation(patient: dict, anomalies: list, hr_history: list, lang: str = "en") -> str:
    anomaly_text = ", ".join([f"{a['vital']}={a['value']} (normal {a['min']}-{a['max']})" for a in anomalies])
    trend = " -> ".join([str(h) for h in hr_history])
    
    lang_map = {"en": "English", "hi": "Hindi", "kn": "Kannada"}
    target_lang = lang_map.get(lang, "English")
    
    prompt = f"Patient {patient['name']} (Age {patient['age']}). HR Trend: {trend}. Anomalies: {anomaly_text}. Give a 2-sentence medical recommendation."
    
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile", # Using the smart model for perfect translations
            messages=[
                # Strict language enforcement in the system prompt
                {"role": "system", "content": f"You are a clinical AI. You MUST write your entire response strictly in {target_lang}. Do NOT use English."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"AI temporarily unavailable: {str(e)}"


# --- MODELS ---
class PatientCreate(BaseModel):
    name: str
    age: int
    heart_rate: int
    blood_pressure_sys: int
    blood_pressure_dia: int
    oxygen: int

class SensorData(BaseModel):
    patient_id: str
    heart_rate: int
    is_active: bool = True


# --- API ENDPOINTS ---
@app.post("/api/sensor")
def receive_sensor_data(data: SensorData):
    """Bridge Endpoint: Receives live hardware data from the Arduino."""
    for p in PATIENTS_DATA:
        if p["patient_id"] == data.patient_id:
            p["heart_rate"] = data.heart_rate
            p["is_sensor"] = data.is_active
            return {"status": "success", "message": f"Updated live HR for {p['name']}"}
    return {"status": "error", "message": "Patient not found"}


@app.post("/api/patients")
def add_patient(patient: PatientCreate):
    new_id = f"P{len(PATIENTS_DATA) + 1:03d}"
    new_patient = {
        "patient_id": new_id,
        "name": patient.name,
        "age": patient.age,
        "heart_rate": patient.heart_rate,
        "blood_pressure_sys": patient.blood_pressure_sys,
        "blood_pressure_dia": patient.blood_pressure_dia,
        "oxygen": patient.oxygen,
        "is_sensor": False,
        "last_ai_update": 0,
        "cached_rec": "",
        "cached_lang": "en"
    }
    PATIENTS_DATA.append(new_patient)
    HR_HISTORY[new_id] = [patient.heart_rate] * 6

    anomalies = detect_anomalies(new_patient)
    status = get_status(anomalies)
    if anomalies:
        rec = get_ai_recommendation(new_patient, anomalies, HR_HISTORY[new_id])
        send_slack_alert(patient={**new_patient, "status": status, "hr_history": HR_HISTORY[new_id]}, anomalies=anomalies, recommendation=rec)

    return {"status": "success", "patient_id": new_id}


@app.get("/api/patients")
def get_patients(lang: str = "en"):
    results = []
    current_time = time.time()
    
    for p in PATIENTS_DATA:
        pid = p["patient_id"]
        
        # --- SMART FALLBACK LOGIC ---
        if p.get("is_sensor", False):
            # 🔌 SENSOR PLUGGED IN: Use exact Arduino numbers
            new_hr = p["heart_rate"]
            new_sys = p["blood_pressure_sys"]
            new_dia = p["blood_pressure_dia"]
            new_o2 = p["oxygen"]
        else:
            # 🤖 AI SIMULATION: Simulate natural fluctuations
            new_hr  = p["heart_rate"] + random.randint(-2, 2)
            new_sys = p["blood_pressure_sys"] + random.randint(-1, 1)
            new_dia = p["blood_pressure_dia"] + random.randint(-1, 1)
            new_o2  = min(100, p["oxygen"] + random.randint(-1, 1))
            
            p["heart_rate"] = new_hr
            p["blood_pressure_sys"] = new_sys
            p["blood_pressure_dia"] = new_dia
            p["oxygen"] = new_o2
        # ----------------------------

        HR_HISTORY[pid].append(new_hr)
        HR_HISTORY[pid] = HR_HISTORY[pid][-6:]

        entry = {
            "patient_id": pid,
            "name": p["name"],
            "age": p["age"],
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "heart_rate": new_hr,
            "blood_pressure_sys": new_sys,
            "blood_pressure_dia": new_dia,
            "oxygen": new_o2,
            "hr_history": HR_HISTORY[pid],
            "is_sensor": p.get("is_sensor", False)
        }
        
        anomalies = detect_anomalies(entry)
        entry["anomalies"] = anomalies
        entry["status"] = get_status(anomalies)
        
        # --- GROQ API SHIELD (Smart Language Cache) ---
        if anomalies:
            # ONLY ask Groq if 20 seconds passed, OR if it's blank, OR if the language changed!
            if current_time - p.get("last_ai_update", 0) >= 20 or not p.get("cached_rec") or p.get("cached_lang") != lang:
                new_rec = get_ai_recommendation(entry, anomalies, HR_HISTORY[pid], lang)
                p["cached_rec"] = new_rec
                p["last_ai_update"] = current_time
                p["cached_lang"] = lang  # Remember the exact language we just translated to!
                entry["recommendation"] = new_rec
            else:
                entry["recommendation"] = p["cached_rec"] # Use safe cached text
        else:
            # Normal status
            if lang == "hi": entry["recommendation"] = "सभी विटल्स स्थिर हैं। नियमित निगरानी जारी रखें।"
            elif lang == "kn": entry["recommendation"] = "ಎಲ್ಲಾ ಪ್ರಮುಖ ಅಂಶಗಳು ಸ್ಥಿರವಾಗಿವೆ. ದಿನನಿತ್ಯದ ಮೇಲ್ವಿಚಾರಣೆಯನ್ನು ಮುಂದುವರಿಸಿ."
            else: entry["recommendation"] = "All vitals stable. Continue routine monitoring."

        # Alerting
        if entry["status"] in ("warning", "critical"):
            # Only trigger slack if it's a fresh update to avoid spamming the channel
            if current_time - p.get("last_ai_update", 0) <= 2: 
                send_slack_alert(
                    patient=entry,
                    anomalies=anomalies,
                    recommendation=entry["recommendation"]
                )

        results.append(entry)
    return results


@app.get("/api/export")
def export_csv():
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["patient_id", "name", "age", "heart_rate", "blood_pressure_sys", "blood_pressure_dia", "oxygen", "sensor_active"])
    for p in PATIENTS_DATA:
        writer.writerow([p["patient_id"], p["name"], p["age"], p["heart_rate"], p["blood_pressure_sys"], p["blood_pressure_dia"], p["oxygen"], p.get("is_sensor", False)])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=patients.csv"}
    )


@app.get("/api/slack/test")
def test_slack():
    success = send_slack_test_message()
    if success:
        return JSONResponse({"status": "ok", "message": "Test message sent to Slack successfully!"})
    else:
        return JSONResponse(
            {"status": "error", "message": "Failed to send. Check SLACK_WEBHOOK_URL in your .env file."},
            status_code=500
        )


@app.get("/", response_class=HTMLResponse)
def dashboard():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)