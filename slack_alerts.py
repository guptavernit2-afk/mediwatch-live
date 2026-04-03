"""
slack_alerts.py — MediWatch AI Slack Alerting Module
Sends real-time Slack notifications when patient vitals breach thresholds.
"""

import os
import time
import requests
from datetime import datetime

# ─── Config ──────────────────────────────────────────────────────────────────
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

# Cooldown: don't re-alert the same patient for the same vital within X seconds
ALERT_COOLDOWN_SECONDS = int(os.getenv("ALERT_COOLDOWN_SECONDS", "300"))  # 5 minutes default

# In-memory cooldown tracker: { "P001_heart_rate": <timestamp> }
_alert_cooldown: dict[str, float] = {}


# ─── Severity Helper ─────────────────────────────────────────────────────────
def _get_severity(status: str) -> dict:
    """Return emoji, color, and label based on patient status."""
    if status == "critical":
        return {"emoji": "🚨", "color": "#FF0000", "label": "CRITICAL"}
    elif status == "warning":
        return {"emoji": "⚠️", "color": "#FFA500", "label": "WARNING"}
    else:
        return {"emoji": "✅", "color": "#36A64F", "label": "NORMAL"}


def _vital_display_name(vital_key: str) -> str:
    """Convert internal vital key to human-readable name."""
    names = {
        "heart_rate": "Heart Rate",
        "blood_pressure_sys": "Blood Pressure (Systolic)",
        "blood_pressure_dia": "Blood Pressure (Diastolic)",
        "oxygen": "Oxygen Saturation (SpO₂)",
    }
    return names.get(vital_key, vital_key)


def _vital_unit(vital_key: str) -> str:
    """Return the unit for a vital."""
    units = {
        "heart_rate": "bpm",
        "blood_pressure_sys": "mmHg",
        "blood_pressure_dia": "mmHg",
        "oxygen": "%",
    }
    return units.get(vital_key, "")


# ─── Cooldown Logic ──────────────────────────────────────────────────────────
def _is_on_cooldown(patient_id: str, vital: str) -> bool:
    """Return True if we recently sent an alert for this patient+vital combo."""
    key = f"{patient_id}_{vital}"
    last_sent = _alert_cooldown.get(key, 0)
    return (time.time() - last_sent) < ALERT_COOLDOWN_SECONDS


def _mark_alerted(patient_id: str, vital: str):
    """Record that we just sent an alert for this patient+vital."""
    key = f"{patient_id}_{vital}"
    _alert_cooldown[key] = time.time()


# ─── Slack Message Builder ───────────────────────────────────────────────────
def _build_slack_payload(patient: dict, anomalies: list, recommendation: str) -> dict:
    """Build a rich Slack Block Kit message payload."""
    severity = _get_severity(patient.get("status", "warning"))
    timestamp = datetime.now().strftime("%d %b %Y, %I:%M:%S %p")

    # Build anomaly lines
    anomaly_lines = []
    for a in anomalies:
        name = _vital_display_name(a["vital"])
        unit = _vital_unit(a["vital"])
        direction = "↑ HIGH" if a["value"] > a["max"] else "↓ LOW"
        anomaly_lines.append(
            f"• *{name}*: `{a['value']} {unit}` {direction} _(normal: {a['min']}–{a['max']} {unit})_"
        )
    anomaly_text = "\n".join(anomaly_lines)

    # HR trend if available
    hr_history = patient.get("hr_history", [])
    trend_text = ""
    if hr_history:
        trend_visual = " → ".join([str(h) for h in hr_history])
        trend_text = f"\n*HR Trend (last 6 readings):* `{trend_visual}`"

    return {
        "text": f"{severity['emoji']} [{severity['label']}] Patient Alert: {patient['name']}",
        "attachments": [
            {
                "color": severity["color"],
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"{severity['emoji']} MediWatch Alert — {severity['label']}",
                            "emoji": True
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*Patient:*\n{patient['name']}"},
                            {"type": "mrkdwn", "text": f"*Patient ID:*\n{patient.get('patient_id', 'N/A')}"},
                            {"type": "mrkdwn", "text": f"*Age:*\n{patient.get('age', 'N/A')} years"},
                            {"type": "mrkdwn", "text": f"*Time:*\n{timestamp}"},
                        ]
                    },
                    {"type": "divider"},
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*🔴 Abnormal Vitals Detected:*\n{anomaly_text}{trend_text}"
                        }
                    },
                    {"type": "divider"},
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*🤖 AI Clinical Recommendation:*\n_{recommendation}_"
                        }
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": "⚕️ *MediWatch AI* — Automated Patient Monitoring System | Please verify with clinical judgment."
                            }
                        ]
                    }
                ]
            }
        ]
    }


# ─── Main Alert Function ──────────────────────────────────────────────────────
def send_slack_alert(patient: dict, anomalies: list, recommendation: str) -> bool:
    """
    Send a Slack alert for a patient with abnormal vitals.

    - Respects per-vital cooldown to avoid spam.
    - Returns True if at least one alert was sent, False otherwise.
    - Silently skips if SLACK_WEBHOOK_URL is not configured.
    """
    if not SLACK_WEBHOOK_URL:
        print("[SlackAlert] SLACK_WEBHOOK_URL not set — skipping alert.")
        return False

    patient_id = patient.get("patient_id", "UNKNOWN")

    # Filter anomalies that are NOT on cooldown
    new_anomalies = [
        a for a in anomalies if not _is_on_cooldown(patient_id, a["vital"])
    ]

    if not new_anomalies:
        print(f"[SlackAlert] Patient {patient_id} — all alerts on cooldown, skipping.")
        return False

    payload = _build_slack_payload(
        patient={**patient, "status": patient.get("status", "warning")},
        anomalies=new_anomalies,
        recommendation=recommendation
    )

    try:
        response = requests.post(
            SLACK_WEBHOOK_URL,
            json=payload,
            timeout=5
        )
        if response.status_code == 200:
            # Mark each new anomaly as alerted
            for a in new_anomalies:
                _mark_alerted(patient_id, a["vital"])
            print(f"[SlackAlert] ✅ Alert sent for {patient['name']} ({patient_id}) — vitals: {[a['vital'] for a in new_anomalies]}")
            return True
        else:
            print(f"[SlackAlert] ❌ Slack returned {response.status_code}: {response.text}")
            return False
    except requests.exceptions.Timeout:
        print("[SlackAlert] ❌ Request timed out.")
        return False
    except requests.exceptions.RequestException as e:
        print(f"[SlackAlert] ❌ Request failed: {e}")
        return False


def send_slack_test_message() -> bool:
    """Send a test ping to verify the webhook is working."""
    if not SLACK_WEBHOOK_URL:
        print("[SlackAlert] SLACK_WEBHOOK_URL not set.")
        return False

    payload = {
        "text": "✅ *MediWatch AI — Slack Integration Test*\nYour Slack alerts are configured correctly! You will receive real-time patient vital alerts here.",
        "attachments": [
            {
                "color": "#36A64F",
                "text": f"Test sent at {datetime.now().strftime('%d %b %Y, %I:%M:%S %p')}"
            }
        ]
    }

    try:
        response = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"[SlackAlert] Test failed: {e}")
        return False
