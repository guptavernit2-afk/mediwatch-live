import serial
import requests
import time
import json

# --- CONFIGURATION ---
# Teammate needs to check his Arduino IDE to see which COM port his board is using
SERIAL_PORT = "COM9"  
BAUD_RATE = 115200    # Matches his Arduino Serial.begin(115200)

API_URL = "https://mediwatch-live.onrender.com"
PATIENT_ID = "P001"   # This will map the sensor to Raj Sharma on your dashboard

def update_dashboard(bpm_val, is_active):
    try:
        requests.post(API_URL, json={
            "patient_id": PATIENT_ID,
            "heart_rate": bpm_val,
            "is_active": is_active
        }, timeout=2)
    except requests.exceptions.RequestException:
        pass # Dashboard might not be running yet, just ignore

print("🚀 Starting MediWatch Hardware Bridge...")

while True:
    try:
        print(f"🔌 Looking for Arduino on {SERIAL_PORT}...")
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2)
        print("✅ Sensor Connected! Forwarding live data to Dashboard...")

        while True:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                
                # Check if the line looks like the JSON his Arduino is sending
                if line.startswith("{") and line.endswith("}"):
                    try:
                        data = json.loads(line)
                        bpm = data.get("bpm", 0)
                        
                        # Only send valid, non-zero heart rates
                        if bpm > 0:
                            update_dashboard(bpm, is_active=True)
                            print(f"❤️ Live Pulse: {bpm} bpm")
                            
                    except json.JSONDecodeError:
                        pass # Ignore garbled serial data
                        
            time.sleep(0.1)

    except serial.SerialException:
        print("❌ Sensor Unplugged or Port Busy! Dashboard reverting to AI simulation...")
        update_dashboard(75, is_active=False) # Tell the dashboard to fall back to simulation
        time.sleep(3) # Wait 3 seconds and try to reconnect