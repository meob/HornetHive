import paho.mqtt.client as mqtt
import argparse
import json
import sys
import time
from datetime import datetime

# --- CLI ARGUMENTS ---
parser = argparse.ArgumentParser(description="HORNET HIVE - MQTT Debugger & Tracer")
parser.add_argument("--filter", type=str, default=None, help="Filter output by topic or payload content (case-insensitive)")
parser.add_argument("--exclude", type=str, default=None, help="Exclude output containing this string")
parser.add_argument("--host", type=str, default="localhost", help="MQTT Broker Host")
args = parser.parse_args()

# --- CONFIGURATION ---
FILTER_STR = args.filter.lower() if args.filter else None
EXCLUDE_STR = args.exclude.lower() if args.exclude else None

# Colors
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def on_connect(client, userdata, flags, rc, properties=None):
    print(f"{Colors.HEADER}[*] Connected to MQTT Broker at {args.host}. Subscribing to ALL topics (#)...{Colors.ENDC}")
    client.subscribe("#")

def on_message(client, userdata, msg):
    try:
        topic = msg.topic
        payload_str = msg.payload.decode()
        
        # Filtering Logic
        content_for_search = f"{topic} {payload_str}".lower()
        
        if FILTER_STR and FILTER_STR not in content_for_search:
            return
            
        if EXCLUDE_STR and EXCLUDE_STR in content_for_search:
            return

        # Pretty Print
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        
        # Color coding based on topic
        color = Colors.ENDC
        if "telemetry" in topic: color = Colors.GREEN
        elif "alerts" in topic: color = Colors.RED
        elif "commands" in topic or "target" in topic: color = Colors.YELLOW
        elif "ai" in topic: color = Colors.BLUE

        # Truncate long payloads (like base64 images) for display
        display_payload = payload_str
        if len(display_payload) > 200:
             display_payload = display_payload[:200] + f"... [truncated {len(display_payload)-200} chars]"

        print(f"{Colors.BOLD}[{ts}]{Colors.ENDC} {color}{topic}{Colors.ENDC} -> {display_payload}")

    except Exception as e:
        print(f"[-] Error decoding message: {e}")

# --- MAIN ---
try:
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(args.host, 1883, 60)
    client.loop_forever()
except KeyboardInterrupt:
    print("\n[*] Debugger stopped.")
    sys.exit(0)
except Exception as e:
    print(f"[!] Connection Error: {e}")
