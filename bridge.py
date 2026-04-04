import serial
import requests
import time
import json

# --- CONFIGURATION ---
SERIAL_PORT = "COM5"  # Make sure this matches Device Manager!
BAUD_RATE = 9600      # Changed to 9600 (Standard Arduino speed). Change to 115200 if using your friend's original code.

API_URL = "https://mediwatch-live.onrender.com/api/sensor"
PATIENT_ID = "P001"   # Maps to Raj Sharma

def update_dashboard(bpm_val, is_active):
    payload = {
        "patient_id": PATIENT_ID,
        "heart_rate": bpm_val,
        "is_active": is_active
    }
    try:
        response = requests.post(API_URL, json=payload, timeout=5)
        # THE X-RAY: This prints exactly what the cloud server is thinking
        print(f"☁️ Server Status: {response.status_code} | Response: {response.text.strip()}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to send to cloud: {e}")

print("🚀 Starting MediWatch Hardware Bridge...")

while True:
    try:
        print(f"🔌 Looking for Arduino on {SERIAL_PORT}...")
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2)
        print("✅ Sensor Connected! Forwarding live data to Dashboard...")

        while True:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                
                if not line:
                    continue

                bpm = 0
                
                # --- SMART DETECTOR ---
                # 1. If Arduino sends JSON (your friend's format)
                if line.startswith("{") and line.endswith("}"):
                    try:
                        data = json.loads(line)
                        bpm = data.get("bpm", 0)
                    except json.JSONDecodeError:
                        pass
                
                # 2. If Arduino sends raw integers (my format)
                elif line.isdigit():
                    bpm = int(line)

                # --- SEND TO CLOUD ---
                # Only send realistic heart rates to prevent crashing the dashboard
                if bpm > 40 and bpm < 200:
                    print(f"❤️ Live Pulse: {bpm} bpm")
                    update_dashboard(bpm, is_active=True)
                        
            time.sleep(0.1)

    except serial.SerialException:
        print("❌ Sensor Unplugged or Port Busy! Dashboard reverting to AI simulation...")
        update_dashboard(75, is_active=False) 
        time.sleep(3)