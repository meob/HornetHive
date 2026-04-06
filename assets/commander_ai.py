import paho.mqtt.client as mqtt
import json
import requests
import time
import argparse
import re
import os
import threading

# --- CLI ARGUMENTS ---
parser = argparse.ArgumentParser(description="HORNET HIVE - AI Swarm Commander")
parser.add_argument("--model", type=str, default="llama3:8b", help="Ollama model name")
parser.add_argument("--url", type=str, default="http://localhost:11434/api/generate", help="Ollama API URL")
parser.add_argument("--mqtt-host", type=str, default="localhost", help="MQTT Broker Host")
parser.add_argument("--log", action="store_true", help="Enable file logging")
parser.add_argument("--debug", action="store_true", help="Enable detailed AI debug logging")
args = parser.parse_args()

# Setup Logging
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
if args.log or args.debug:
    if not os.path.exists(LOG_DIR): os.makedirs(LOG_DIR)

def log_debug(msg):
    if args.debug:
        print(msg)
        with open(os.path.join(LOG_DIR, f"debug_ai_commander.log"), "a") as f:
            f.write(f"[{time.ctime()}] {msg}\n")

def log_event(msg):
    print(msg)
    if args.log:
        with open(os.path.join(LOG_DIR, f"mission_events_{time.strftime('%Y-%m-%d')}.log"), "a") as f:
            f.write(f"[{time.ctime()}] AI_COMMANDER: {msg}\n")

# Tactical Memory
drones = {}
scenario_config = {}
tactical_rules = {}

# Load Tactical Rules
try:
    rules_path = os.path.join(os.path.dirname(__file__), 'tactical_rules.json')
    with open(rules_path, 'r') as f:
        tactical_rules = json.load(f)
except Exception as e:
    print(f"[!] Warning: Could not load tactical_rules.json: {e}")

# --- MQTT SETUP ---
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

def on_message(client, userdata, msg):
    global scenario_config
    try:
        topic = msg.topic
        payload = json.loads(msg.payload.decode())
        if "telemetry" in topic: drones[payload['id']] = payload
        elif topic == "hive/sys/config": 
            scenario_config = payload
            print(f"[*] AI COMMANDER: Context updated - {payload.get('scenario')} ({payload.get('mission_type')})")
        elif topic == "hive/ai/objective":
            # LAUNCH IN A SEPARATE THREAD TO PREVENT BLOCKING MQTT
            threading.Thread(target=process_objective, args=(payload['text'],)).start()
    except Exception as e:
        print(f"[-] MQTT Message Error: {e}")

def extract_json_object(text):
    """Extract the strategy JSON object from LLM response."""
    match = re.search(r'(\{.*\})', text, re.DOTALL)
    if match:
        return match.group(1)
    return text

def process_objective(user_text):
    # 0. Immediate Acknowledgment to stop Server Watchdog
    client.publish("hive/ai/feedback", json.dumps({"status": "RECEIVED", "log": "Analyzing mission profile..."}))

    if not drones:
        client.publish("hive/ai/feedback", json.dumps({"status": "ERROR", "log": "No drones online. Power up the swarm first."}))
        return

    # 1. Build Context
    mission_type = scenario_config.get('mission_type', 'TRAINING')
    doctrine = tactical_rules.get(mission_type, {}).get('doctrine', 'Follow standard flight rules.')
    spatial_markers = scenario_config.get('spatial_markers', {})
    
    fleet_info = ""
    valid_ids = []
    for d_id, d_data in drones.items():
        # Include current relative position (X, Y) in fleet info
        x_pos = d_data.get('x', 0)
        y_pos = d_data.get('y', 0)
        fleet_info += f"- ID: {d_id} | Model: {d_data['model']} | Pos: X={x_pos}, Y={y_pos} | Alt: {d_data['altitude']}m | Bat: {d_data['battery']}%\n"
        valid_ids.append(d_id)

    poi_info = ""
    if spatial_markers:
        poi_info = "KNOWN POINTS OF INTEREST (POI) IN THIS SCENARIO:\n"
        for name, coords in spatial_markers.items():
            poi_info += f"- {name}: X={coords['x']}, Y={coords['y']}, Z={coords.get('z', 10)}\n"

    # 2. Enhanced Tactical Prompt
    system_prompt = f"""
    You are the AI Tactical Commander of the Hornet Hive.
    CURRENT SCENARIO: {scenario_config.get('scenario', 'Training')}
    MISSION TYPE: {mission_type}
    OPERATIONAL DOCTRINE: {doctrine}
    
    AVAILABLE FLEET (Use these IDs EXACTLY):
    {fleet_info}

    {poi_info}

    TASK:
    Translate USER OBJECTIVE into drone commands. 
    Use EXACT IDs from the list: {valid_ids}.
    If the user mentions a POI (e.g., 'Hospital', 'Gallery', 'Reactor'), use the X, Y, Z coordinates provided in the POI list.
    
    RESPONSE FORMAT (STRICT JSON):
    {{
      "strategy_explanation": "Explain your tactical choice.",
      "commands": [
        {{
          "target_id": "EXACT_ID or ALL",
          "command": "MOVE or RTL",
          "mission": "TRANSIT, STRIKE, SAR, or DELIVERY",
          "x": east_meters, "y": north_meters, "z": altitude_agl
        }}
      ]
    }}

    RULES:
    - Fixed-wing (REAPER, FALCO, BAYRAKTAR, TRITON): Altitude MUST be > 150m.
    - Rotary (MAVIC, TELLO, WING): Altitude MUST be < 80m.
    - Negative X = West, Negative Y = South.
    
    USER OBJECTIVE: "{user_text}"
    """

    print(f"[*] AI COMMANDER: Prompting {args.model} for objective: {user_text}")
    client.publish("hive/ai/feedback", json.dumps({"status": "THINKING...", "log": f"Consulting {args.model} for {mission_type} strategy..."}))
    
    try:
        response = requests.post(args.url, json={
            "model": args.model,
            "prompt": system_prompt,
            "stream": False,
            "format": "json"
        }, timeout=90)
        
        if response.status_code != 200:
            raise ConnectionError(f"Ollama Error: {response.status_code}")

        resp_raw = response.json().get('response', '')
        
        # RESTORE DEBUG LOGGING
        if args.debug:
            log_file = os.path.join(LOG_DIR, f"ai_debug_{time.strftime('%Y-%m-%d')}.log")
            with open(log_file, "a") as f:
                f.write(f"--- {time.ctime()} ---\nPROMPT:\n{system_prompt}\nRESPONSE:\n{resp_raw}\n\n")

        json_str = extract_json_object(resp_raw)
        result = json.loads(json_str)
        
        explanation = result.get('strategy_explanation', 'Executing mission.')
        commands = result.get('commands', [])

        # Dispatch explanation and commands
        client.publish("hive/ai/feedback", json.dumps({"status": "EXECUTING", "log": explanation}))
        
        for cmd in commands:
            # Normalize ID case and handle ALFA/ALPHA common mismatch
            raw_id = str(cmd['target_id']).upper()
            if raw_id in valid_ids:
                cmd['target_id'] = raw_id
            elif raw_id == "ALFA" and "ALPHA" in valid_ids:
                cmd['target_id'] = "ALPHA"
            elif raw_id == "ALPHA" and "ALFA" in valid_ids:
                cmd['target_id'] = "ALFA"
            
            client.publish("hive/swarm/target", json.dumps(cmd))
            print(f"[!] AI DISPATCH: {cmd['target_id']} -> {cmd['mission']}")
        
        time.sleep(1)
        client.publish("hive/ai/feedback", json.dumps({"status": "READY", "log": "Strategy executed successfully."}))

    except Exception as e:
        print(f"[!] AI COMMANDER ERROR: {e}")
        client.publish("hive/ai/feedback", json.dumps({"status": "ERROR", "log": str(e)[:100]}))

client.on_message = on_message

# --- MQTT CONNECTION WITH RETRY ---
connected = False
while not connected:
    try:
        print(f"[*] AI COMMANDER connecting to MQTT at {args.mqtt_host}...")
        client.connect(args.mqtt_host, 1883, 60)
        connected = True
        print(f"[+] AI COMMANDER connected to MQTT.")
    except Exception as e:
        print(f"[-] AI COMMANDER connection failed ({e}). Retrying in 10s...")
        time.sleep(10)

client.subscribe([("hive/drone/+/telemetry", 0), ("hive/sys/config", 0), ("hive/ai/objective", 0)])
client.loop_start()

print(f"[*] AI COMMANDER: Multi-threaded Brain Online ({args.model}).")

try:
    while True: time.sleep(1)
except KeyboardInterrupt:
    client.loop_stop()
