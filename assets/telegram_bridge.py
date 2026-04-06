import paho.mqtt.client as mqtt
import json
import requests
import base64
import argparse
import io
import time

# --- CLI ARGUMENTS ---
parser = argparse.ArgumentParser(description="HORNET HIVE - Telegram Notification Bridge")
parser.add_argument("--token", type=str, required=True, help="Telegram Bot Token")
parser.add_argument("--chat_id", type=str, required=True, help="Telegram Chat ID")
parser.add_argument("--broker", type=str, default="localhost", help="MQTT Broker Host")
args = parser.parse_args()

TELEGRAM_API = f"https://api.telegram.org/bot{args.token}/sendPhoto"

def send_telegram_alert(detected_obj, sensor_id, confidence, snapshot_b64):
    """Sends a photo and message to the specified Telegram Chat."""
    message = f"🚨 *HORNET HIVE ALERT*\n\nTarget: `{detected_obj}`\nSensor: `{sensor_id}`\nConfidence: `{confidence}`"
    
    try:
        # Prepare the photo from Base64
        image_data = base64.b64decode(snapshot_b64)
        image_file = io.BytesIO(image_data)
        image_file.name = "detection.jpg"

        # Call Telegram API
        payload = {
            "chat_id": args.chat_id,
            "caption": message,
            "parse_mode": "Markdown"
        }
        files = {"photo": image_file}
        
        response = requests.post(TELEGRAM_API, data=payload, files=files, timeout=10)
        
        if response.status_code == 200:
            print(f"[*] Telegram: Alert dispatched for {detected_obj}")
        else:
            print(f"[!] Telegram Error: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"[!] Notification Failed: {e}")

# --- MQTT HANDLERS ---
def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        
        # Only notify on NEW detections
        if data.get("status") == "DETECTED":
            # Avoid flooding: you might want to add a local cooldown here too
            send_telegram_alert(
                data.get("detected", "UNKNOWN"),
                data.get("sensor", "ANONYMOUS"),
                data.get("conf", "N/A"),
                data.get("snapshot", "")
            )
    except Exception as e:
        print(f"[-] MQTT Bridge Error: {e}")

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_message = on_message

# --- MQTT CONNECTION WITH RETRY ---
connected = False
while not connected:
    try:
        print(f"[*] TELEGRAM BRIDGE connecting to MQTT at {args.broker}...")
        client.connect(args.broker, 1883, 60)
        connected = True
        print(f"[+] TELEGRAM BRIDGE connected to MQTT.")
    except Exception as e:
        print(f"[-] TELEGRAM BRIDGE connection failed ({e}). Retrying in 10s...")
        time.sleep(10)

client.subscribe("hive/alerts/detection")
client.loop_start()
print(f"[*] TELEGRAM BRIDGE: Online and monitoring alerts.")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("[*] Shutting down Telegram Bridge...")
    client.loop_stop()
    client.disconnect()
