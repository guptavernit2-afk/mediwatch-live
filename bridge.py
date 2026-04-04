import serial
import requests
import time
import json

# --- CONFIGURATION ---
SERIAL_PORT = "COM5" 
BAUD_RATE = 9600     

API_URL = "https://mediwatch-live.onrender.com/api/sensor"
PATIENT_ID = "P001"   

# Trackers for the "Ghost Badge" fix
last_pulse_time = time.time()
sensor_currently_active = False

def update_dashboard(bpm_val, is_active):
    global sensor_currently_active
    payload = {
        "patient_id": PATIENT_ID,
        "heart_rate": bpm_val,
        "is_active": is_active
    }
    try:
        response = requests.post(API_URL, json=payload, timeout=5)
        sensor_currently_active = is_active
        print(f"☁️ Cloud Updated | Active: {is_active} | Status: {response.status_code}")
    except Exception as e:
        print(f"❌ Cloud Error: {e}")

print("🚀 Starting MediWatch Hardware Bridge...")

while True:
    try:
        print(f"🔌 Looking for Arduino on {SERIAL_PORT}...")
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print("✅ Sensor Connected! Waiting for pulse...")

        while True:
            current_time = time.time()

            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                
                if line.isdigit():
                    bpm = int(line)
                    if bpm > 40:
                        print(f"❤️ Pulse Detected: {bpm} bpm")
                        update_dashboard(bpm, True)
                        last_pulse_time = current_time # Reset the timer
                
            # --- THE GHOST FIX ---
            # If 5 seconds pass with NO data, tell the cloud to turn off the badge
            if (current_time - last_pulse_time > 5) and sensor_currently_active:
                print("💤 No finger detected for 5 seconds. Turning off Live Badge...")
                update_dashboard(75, False) # Send 75 as a safe fallback
            
            time.sleep(0.1)

    except serial.SerialException:
        print("❌ Arduino Unplugged!")
        update_dashboard(75, False)
        time.sleep(3)