import paho.mqtt.client as mqtt
import json
import time
import math
import sys
import os
import random
import argparse

# --- ARGUMENT PARSING ---
parser = argparse.ArgumentParser(description="HORNET HIVE - Target Simulator")
parser.add_argument("id", nargs="?", default="TARGET_1", help="Target ID")
parser.add_argument("--type", default="⛵️", help="Target Icon (⛵️, ⛑️, 🪖, 📡, ☢︎)")
parser.add_argument("--action", default="MEDKIT", help="Required action (SENSOR, RESCUE_TUBE, MEDKIT, STRIKE)")
parser.add_argument("--radius", type=float, default=50.0, help="Detection radius in meters")
parser.add_argument("--drift", type=float, default=0.0, help="Drift speed in m/s")
parser.add_argument("--area", type=float, default=2000.0, help="Search area radius in meters")
parser.add_argument("--pos", default=None, help="Fixed starting position as X,Y (e.g. 500,-200)")
parser.add_argument("--offset", default="0,0", help="Center of the random search area as X,Y (default 0,0)")
parser.add_argument("--max-alt", type=float, default=60.0, help="Max altitude for detection (meters)")
parser.add_argument("--delay", type=float, default=0.0, help="Mean initial delay for activation (seconds)")
parser.add_argument("--mqtt-host", default="localhost", help="MQTT Broker Host")
parser.add_argument("--log", action="store_true", help="Enable file logging")
parser.add_argument("--debug", action="store_true", help="Enable verbose debug output")
args = parser.parse_args()

ID = args.id
ICON = args.type
REQUIRED_ACTION = args.action
DETECTION_RADIUS = args.radius
DRIFT_SPEED = args.drift
AREA_RADIUS = args.area
MAX_ALT = args.max_alt
DELAY = args.delay
MQTT_HOST = args.mqtt_host

# Logging Setup
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
if args.log or args.debug:
    if not os.path.exists(LOG_DIR): os.makedirs(LOG_DIR)

def log_debug(msg):
    if args.debug:
        print(f"[DEBUG] {msg}")

def log_event(msg):
    print(f"[*] {msg}")
    if args.log:
        with open(os.path.join(LOG_DIR, f"target_events_{time.strftime('%Y-%m-%d')}.log"), "a") as f:
            f.write(f"[{time.ctime()}] {ID}: {msg}\n")

HOME = None
pos = {"x": 0.0, "y": 0.0, "z": 0.0}
detected = False
detected_by = None
mission_complete = False
drift_angle = random.uniform(0, 2 * math.pi)
mayday_last_sent = 0
rough_lat = 0
rough_lon = 0

# Drone tracking
drones = {}
activation_time = 0
activated = False
alert_msg = ""

# --- MQTT HANDLERS ---
def on_message(client, userdata, msg):
    global HOME, pos, drones, detected, detected_by, rough_lat, rough_lon, mayday_last_sent, mission_complete, activation_time, activated, alert_msg
    
    payload_str = msg.payload.decode()
    
    if msg.topic == "hive/sys/config":
        if HOME is not None: return 
        try:
            sys_cfg = json.loads(payload_str)
            HOME = [sys_cfg["home_lat"], sys_cfg["home_lon"]]
            
            # --- TACTICAL POSITIONING ---
            off_x, off_y = 0.0, 0.0
            if args.offset:
                try: off_x, off_y = map(float, args.offset.split(','))
                except: pass

            if args.pos:
                try:
                    px, py = map(float, args.pos.split(','))
                    pos["x"], pos["y"] = px, py
                except:
                    # Fallback to random if parsing fails
                    angle = random.uniform(0, 2 * math.pi)
                    dist = random.uniform(AREA_RADIUS * 0.3, AREA_RADIUS)
                    pos["x"] = off_x + math.cos(angle) * dist
                    pos["y"] = off_y + math.sin(angle) * dist
            else:
                # Random position within the area relative to offset
                angle = random.uniform(0, 2 * math.pi)
                dist = random.uniform(AREA_RADIUS * 0.3, AREA_RADIUS)
                pos["x"] = off_x + math.cos(angle) * dist
                pos["y"] = off_y + math.sin(angle) * dist
            
            # --- DYNAMIC MAYDAY MESSAGES ---
            MESSAGES = {
                "RESCUE_TUBE": "MAYDAY! SOS! Vessel in distress. Requesting immediate rescue!",
                "MEDKIT": "MEDICAL EMERGENCY! Casualties reported. Need urgent medevac!",
                "SENSOR": f"ANOMALY DETECTED! Search area identified for {ID}. Investigation required.",
                "STRIKE": "HOSTILE ACTIVITY! Threat identified in sector. Requesting tactical engagement!"
            }
            
            # Use the search area center (offset) for the Mayday signal (Original Logic)
            rough_lat = HOME[0] + (off_y / 111111)
            rough_lon = HOME[1] + (off_x / (111111 * math.cos(math.radians(HOME[0]))))

            # --- INITIAL DELAY (Realism) ---
            if DELAY > 0:
                actual_delay = max(0, random.normalvariate(DELAY, DELAY * 0.2))
                activation_time = time.time() + actual_delay
                log_event(f"Target PENDING: Activation in {round(actual_delay, 2)}s")
            else:
                activation_time = time.time()
                
            alert_msg = MESSAGES.get(REQUIRED_ACTION, f"ALERT! Objective {ID} active. Need {REQUIRED_ACTION}!")
            
        except Exception as e:
            print(f"[-] Config Error: {e}")
        return

    if HOME is None or mission_complete: return

    # 1. Telemetry / Detection
    if "hive/drone/" in msg.topic and "/telemetry" in msg.topic:
        try:
            data = json.loads(payload_str)
            drone_id = data["id"]
            
            # Check for detection
            if not detected:
                dx = data["x"] - pos["x"]
                dy = data["y"] - pos["y"]
                dist = math.sqrt(dx**2 + dy**2)
                
                if dist < DETECTION_RADIUS and data["altitude"] < MAX_ALT:
                    detected = True
                    detected_by = drone_id
                    log_event(f"TARGET DETECTED by {drone_id}!")
                    
                    lat = HOME[0] + (pos["y"] / 111111)
                    lon = HOME[1] + (pos["x"] / (111111 * math.cos(math.radians(HOME[0]))))
                    
                    client.publish("hive/alerts/detection", json.dumps({
                        "sensor": drone_id,
                        "id": ID,
                        "type": "TARGET",
                        "icon": ICON,
                        "lat": lat,
                        "lon": lon,
                        "x": pos["x"],
                        "y": pos["y"],
                        "event": "FOUND",
                        "ts": int(time.time())
                    }))
                    
                    # Also update Mayday with specific request
                    client.publish("hive/alerts/mayday", json.dumps({
                        "id": ID,
                        "icon": ICON,
                        "msg": f"VISUAL CONTACT! Requesting {REQUIRED_ACTION} at this location.",
                        "rough_lat": lat,
                        "rough_lon": lon,
                        "ts": int(time.time())
                    }), retain=True)
        except Exception as e:
            pass

    # 2. Action Performance
    if msg.topic == "hive/alerts/action_performed":
        try:
            data = json.loads(payload_str)
            
            # Verify action type matches requirement
            if data["capability"] == REQUIRED_ACTION:
                dx = data["x"] - pos["x"]
                dy = data["y"] - pos["y"]
                dist = math.sqrt(dx**2 + dy**2)
                
                if dist < 50.0:
                    mission_complete = True
                    log_event(f"MISSION SUCCESS: Target {ID} serviced by {data['drone_id']} with {REQUIRED_ACTION}")
                    
                    client.publish("hive/alerts/mission_success", json.dumps({
                        "id": ID,
                        "serviced_by": data["drone_id"],
                        "action": REQUIRED_ACTION,
                        "lat": data["lat"],
                        "lon": data["lon"],
                        "ts": int(time.time())
                    }))
                    
                    # Clear retained Mayday
                    client.publish("hive/alerts/mayday", b"", retain=True)
                else:
                    log_event(f"ACTION FAILED: {data['drone_id']} dropped {REQUIRED_ACTION} but missed! (Dist: {round(dist)}m)")
        except Exception as e:
            print(f"[-] Action Handler Error: {e}")

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_message = on_message

# --- MQTT CONNECTION WITH RETRY ---
connected = False
while not connected:
    try:
        print(f"[*] {ID} connecting to MQTT at {MQTT_HOST}...")
        client.connect(MQTT_HOST, 1883, 60)
        connected = True
        print(f"[+] {ID} connected to MQTT.")
    except Exception as e:
        print(f"[-] {ID} connection failed ({e}). Retrying in 10s...")
        time.sleep(10)

client.subscribe("hive/sys/config")
client.subscribe("hive/drone/+/telemetry")
client.subscribe("hive/alerts/action_performed")
client.loop_start()

log_event(f"Starting Target Simulator: {ID} ({ICON}) - Goal: {REQUIRED_ACTION}")

last_t = time.time()
last_telemetry = 0

try:
    while True:
        now = time.time()
        dt = now - last_t
        last_t = now

        if HOME and not mission_complete:
            # 0. Activation Logic (Non-blocking delay)
            if not activated:
                if now >= activation_time:
                    activated = True
                    log_event(f"TARGET DEPLOYED: {ICON} {ID} at ({round(pos['x'])}, {round(pos['y'])}) - REQ: {REQUIRED_ACTION}")
                    # Force immediate publish in the repetition block
                    mayday_last_sent = 0 
                else:
                    time.sleep(0.5)
                    continue

            # 1. Drift Logic
            if DRIFT_SPEED > 0:
                pos["x"] += math.cos(drift_angle) * DRIFT_SPEED * dt
                pos["y"] += math.sin(drift_angle) * DRIFT_SPEED * dt
                # Slowly change drift angle
                drift_angle += random.uniform(-0.05, 0.05) * dt

            # 2. Mayday Repetition (Original 60s interval)
            if not detected and (now - mayday_last_sent) > 60.0:
                 log_debug(f"Sending/Repeating MAYDAY for {ID}")
                 client.publish("hive/alerts/mayday", json.dumps({
                    "id": ID,
                    "icon": ICON,
                    "msg": alert_msg,
                    "rough_lat": rough_lat,
                    "rough_lon": rough_lon,
                    "radius": AREA_RADIUS,
                    "ts": int(now)
                }), retain=True)
                 mayday_last_sent = now

            # 3. Status Update
            if now - last_telemetry > 2.0:
                lat = HOME[0] + (pos["y"] / 111111)
                lon = HOME[1] + (pos["x"] / (111111 * math.cos(math.radians(HOME[0]))))
                
                status_payload = {
                    "id": ID,
                    "type": "TARGET",
                    "icon": ICON,
                    "lat": lat,
                    "lon": lon,
                    "x": pos["x"],
                    "y": pos["y"],
                    "detected": detected,
                    "detected_by": detected_by,
                    "mission_complete": mission_complete,
                    "ts": int(now)
                }
                
                if detected:
                    client.publish(f"hive/target/{ID}/telemetry", json.dumps(status_payload))
                
                client.publish(f"hive/debug/target/{ID}", json.dumps(status_payload))
                last_telemetry = now

        time.sleep(0.5)

except KeyboardInterrupt:
    client.loop_stop()
    sys.exit()
