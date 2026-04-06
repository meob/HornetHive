import json
import time
import math
import paho.mqtt.client as mqtt
import argparse
import os

# --- CLI ARGUMENTS ---
parser = argparse.ArgumentParser(description="HORNET HIVE - Tactical Radar Mock (Lightweight)")
parser.add_argument("--id", type=str, default="RADAR_01", help="Unique ID for this radar")
parser.add_argument("--range", type=int, default=1000, help="Radar range in meters")
parser.add_argument("--speed", type=float, default=60.0, help="Sweep rotation speed (deg/sec)")
parser.add_argument("--min-alt", type=float, default=10.0, help="Minimum altitude to detect an object (meters)")
parser.add_argument("--mqtt-host", default="localhost", help="MQTT Broker Host")
parser.add_argument("--log", action="store_true", help="Enable file logging")
parser.add_argument("--debug", action="store_true", help="Enable radar debug logging")
args = parser.parse_args()

# Setup Logging
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
if args.log or args.debug:
    if not os.path.exists(LOG_DIR): os.makedirs(LOG_DIR)

def log_debug(msg):
    if args.debug:
        with open(os.path.join(LOG_DIR, f"debug_radar_{args.id}.log"), "a") as f:
            f.write(f"[*] {time.ctime()} - {msg}\n")

if args.debug:
    log_debug(f"{args.id} STARTED (Range: {args.range}m, MinAlt: {args.min_alt}m, Speed: {args.speed}deg/s)")

# --- CONFIGURATION ---
RADAR_ID = args.id
MAX_RANGE = args.range
MIN_ALT = args.min_alt
SWEEP_SPEED = args.speed

# --- STATE ---
drones = {}  # id: {x, y, dist, angle, last_seen}
sweep_angle = 0
last_time = time.time()

# --- MQTT SETUP ---
def on_message(client, userdata, msg):
    global drones
    try:
        topic = msg.topic
        payload = json.loads(msg.payload.decode())
        
        if "telemetry" in topic:
            d_id = payload.get("id")
            dx, dy = payload.get("x", 0), payload.get("y", 0)
            alt = payload.get("altitude", 0)
            
            # Calculate angle (0 is Right, CW rotation in UI coordinate space)
            # atan2(-dy, dx) matches original logic where Y is inverted for screen
            angle = math.degrees(math.atan2(-dy, dx)) % 360
            dist = math.sqrt(dx**2 + dy**2)
            
            # Filter by Range AND Altitude
            if dist <= MAX_RANGE and alt >= MIN_ALT:
                drones[d_id] = {
                    "id": d_id,
                    "x": dx, "y": dy, 
                    "dist": dist,
                    "angle": angle,
                    "last_seen": time.time()
                }
            elif d_id in drones:
                del drones[d_id] # Out of range or below minimum altitude
    except Exception as e:
        if args.debug: log_debug(f"Error parsing telemetry: {e}")

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_message = on_message

# --- MQTT CONNECTION WITH RETRY ---
connected = False
while not connected:
    try:
        print(f"[*] {RADAR_ID} connecting to MQTT at {args.mqtt_host}...")
        client.connect(args.mqtt_host, 1883, 60)
        connected = True
        print(f"[+] {RADAR_ID} connected to MQTT.")
    except Exception as e:
        print(f"[-] {RADAR_ID} connection failed ({e}). Retrying in 2s...")
        time.sleep(2)

client.subscribe("hive/drone/+/telemetry")
client.subscribe("hive/target/+/telemetry") # Also detect targets!
client.loop_start()

print(f"[*] {RADAR_ID}: Tactical Radar Active (Range: {MAX_RANGE}m)")

try:
    while True:
        now = time.time()
        dt = now - last_time
        last_time = now
        
        # 1. Update Sweep
        sweep_angle = (sweep_angle + SWEEP_SPEED * dt) % 360
        
        # 2. Filter old drones (dead drop-off)
        expired = [d_id for d_id, d in drones.items() if now - d["last_seen"] > 5.0]
        for d_id in expired: del drones[d_id]

        # 3. Collect Blips
        # We only send blips that are "hit" by the sweep? 
        # Or let the UI handle the persistence? 
        # Sending all drones in range is better, UI will show them when sweep passes.
        blips = []
        for d_id, d in drones.items():
            blips.append({
                "id": d["id"],
                "dist": round(d["dist"], 1),
                "angle": round(d["angle"], 1)
            })

        # 4. Publish to HIVE
        # We send raw data instead of snapshot image.
        client.publish("hive/alerts/status", json.dumps({
            "sensor": RADAR_ID,
            "status": "ONLINE",
            "sweep": round(sweep_angle, 1),
            "blips": blips,
            "range": MAX_RANGE,
            "ts": int(now)
        }))

        # 10 FPS is enough for smooth UI interpolation
        time.sleep(0.1)

except KeyboardInterrupt:
    client.publish("hive/alerts/status", json.dumps({"sensor": RADAR_ID, "status": "OFFLINE"}))
    client.loop_stop()
    client.disconnect()
