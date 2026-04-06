import paho.mqtt.client as mqtt
import json
import time
import math
import sys
import os
import random
import argparse

# --- ARGUMENT PARSING ---
parser = argparse.ArgumentParser(description="HORNET HIVE - Drone Simulator")
parser.add_argument("id", help="Drone ID (e.g. ALPHA, DJI_1)")
parser.add_argument("model", help="Drone Model (from drone_models.json)")
parser.add_argument("--mqtt-host", default="localhost", help="MQTT Broker Host")
parser.add_argument("--log", action="store_true", help="Enable file logging")
parser.add_argument("--debug", action="store_true", help="Enable verbose debug output")
args = parser.parse_args()

ID = args.id
MODEL_KEY = args.model

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
        with open(os.path.join(LOG_DIR, f"drone_events_{time.strftime('%Y-%m-%d')}.log"), "a") as f:
            f.write(f"[{time.ctime()}] {ID}: {msg}\n")

# Load Drone Models
MODELS = {}
try:
    with open(os.path.join(os.path.dirname(__file__), 'drone_models.json'), 'r') as f:
        data = json.load(f)
        for cat in data:
            for m in data[cat]:
                MODELS[m] = data[cat][m]
except Exception as e:
    print(f"[!] Failed to load drone_models.json: {e}")
    sys.exit(1)

if MODEL_KEY not in MODELS:
    print(f"[!] Invalid Drone Model: {MODEL_KEY}. Check drone_models.json")
    sys.exit(1)

CONFIG = MODELS[MODEL_KEY]
CAPABILITY = CONFIG.get("capability", "SENSOR")

# Internal State
HOME = None
pos = {"lat": 0.0, "lon": 0.0, "x": 0.0, "y": 0.0, "z": 0.0}
target = {"x": 0.0, "y": 0.0, "z": 0.0}
start_offset = {"x": 0.0, "y": 0.0}
heading = 0.0
battery = 100.0
status = "GROUNDED"
mission_type = "IDLE"
is_loitering = False
orbit_angle = 0.0
emergency_lock = False

# --- MQTT HANDLERS ---
def on_message(client, userdata, msg):
    global HOME, target, mission_type, status, is_loitering, start_offset, emergency_lock
    
    payload_str = msg.payload.decode()
    
    if msg.topic == "hive/sys/config":
        if HOME is not None: return 
        try:
            sys_cfg = json.loads(payload_str)
            HOME = [sys_cfg["home_lat"], sys_cfg["home_lon"]]
            start_offset["x"] = random.uniform(-10, 10)
            start_offset["y"] = random.uniform(-10, 10)
            pos["x"], pos["y"] = start_offset["x"], start_offset["y"]
            target["x"], target["y"] = pos["x"], pos["y"]
            log_event(f"System Online. Drone {ID} ({MODEL_KEY}) ready at Home: {HOME}")
        except: pass
        return

    if HOME is None: return

    if msg.topic == "hive/swarm/target":
        try:
            data = json.loads(payload_str)
            target_id = data.get("target_id")
            if target_id == "ALL" or str(target_id) == str(ID):
                log_debug(f"Received command: {data.get('mission', 'MOVE')}")
                cmd = data.get("command", "MOVE").upper()
                
                if cmd == "RTL":
                    target["x"], target["y"] = start_offset["x"], start_offset["y"]
                    target["z"] = CONFIG["min_alt"]
                    mission_type = "RTL"
                    status = "RETURNING"
                    is_loitering = False
                    emergency_lock = False 
                else:
                    if emergency_lock: return 
                    target["x"] = float(data.get("x", pos["x"]))
                    target["y"] = float(data.get("y", pos["y"]))
                    req_z = float(data.get("z", CONFIG["min_alt"]))
                    target["z"] = max(CONFIG["min_alt"], min(CONFIG["max_alt"], req_z))
                    mission_type = data.get("mission", "TRANSIT").upper()
                    status = "TRANSIT"
                    is_loitering = False
                    
                log_event(f"NEW ORDERS: {mission_type} to ({round(target['x'])}, {round(target['y'])}) at {target['z']}m")
        except Exception as e:
            print(f"[-] Command Error: {e}")

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_message = on_message

# --- MQTT CONNECTION WITH RETRY ---
connected = False
while not connected:
    try:
        print(f"[*] {ID} connecting to MQTT at {args.mqtt_host}...")
        client.connect(args.mqtt_host, 1883, 60)
        connected = True
        print(f"[+] {ID} connected to MQTT.")
    except Exception as e:
        print(f"[-] {ID} connection failed ({e}). Retrying in 10s...")
        time.sleep(10)

client.subscribe("hive/sys/config")
client.loop_start()

while HOME is None:
    time.sleep(0.5)

client.subscribe("hive/swarm/target")

def get_map_tile(lat, lon, alt):
    if alt < 15: zoom = 19
    elif alt < 40: zoom = 18
    elif alt < 120: zoom = 17
    elif alt < 300: zoom = 16
    elif alt < 600: zoom = 15
    elif alt < 1200: zoom = 14
    else: zoom = 13
    n = 2.0 ** zoom
    xtile = int((lon + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.log(math.tan(math.radians(lat)) + (1 / math.cos(math.radians(lat)))) / math.pi) / 2.0 * n)
    return f"https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{zoom}/{ytile}/{xtile}"

def perform_action(now):
    global mission_type, status, is_loitering, target
    event_type = "DROP"
    if CAPABILITY == "STRIKE": event_type = "DETONATION"
    if CAPABILITY == "SENSOR": event_type = "SCAN"
    
    client.publish("hive/alerts/detection", json.dumps({
        "sensor": ID, "event": event_type, "lat": pos["lat"], "lon": pos["lon"], "ts": int(now)
    }))
    client.publish("hive/alerts/action_performed", json.dumps({
        "drone_id": ID, "capability": CAPABILITY, "event": event_type, 
        "lat": pos["lat"], "lon": pos["lon"], "x": pos["x"], "y": pos["y"], "ts": int(now)
    }))
    
    log_event(f"ACTION EXECUTED: {event_type} ({CAPABILITY})")
    
    if CONFIG.get("behavior_type") == "KAMIKAZE": 
        log_event("IMPACT! Kamikaze objective reached. Terminating process.")
        sys.exit()
    
    if CAPABILITY == "STRIKE":
        mission_type = "RTL"
        target["x"], target["y"] = start_offset["x"], start_offset["y"]
        target["z"] = max(120, CONFIG.get("min_alt", 50))
        is_loitering = False
        log_event("Strike completed. Returning to base.")
    else:
        if CONFIG["type"] == "FIXED_WING":
            is_loitering = True
            status = "LOITERING (ORBIT)"
        else:
            mission_type = "IDLE"
            status = "HOVERING"

last_t = time.time()
last_telemetry = 0

try:
    while True:
        now = time.time()
        dt = now - last_t
        last_t = now

        # 0. Core Physics Pre-calculations
        dx, dy = target["x"] - pos["x"], target["y"] - pos["y"]
        dist_to_center = math.sqrt(dx**2 + dy**2)

        if HOME and status != "STASIS":
            # 1. Vertical Physics
            current_target_z = target["z"]
            
            # RTL Descent Trigger
            if mission_type == "RTL" and target["z"] > 0:
                if dist_to_center < 15.0:
                    target["z"] = 0
                    log_event("OVER HOME: Commencing final descent for landing.")
                else:
                    current_target_z = pos["z"] # Hold altitude until home

            # Kamikaze Dive: High speed descent when near target
            is_kamikaze = (mission_type == "STRIKE" and CONFIG.get("behavior_type") == "KAMIKAZE")
            if is_kamikaze and dist_to_center < 400.0:
                current_target_z = 0

            dz = current_target_z - pos["z"]
            if abs(dz) > 0.1:
                v_speed = CONFIG["climb_rate"]
                if is_kamikaze and dz < 0: v_speed *= 3.0 # Dive faster
                pos["z"] += math.copysign(min(abs(dz), v_speed * dt), dz)

            # Landing Detection
            if pos["z"] < 0.2 and target["z"] == 0:
                pos["z"] = 0
                status = "CRASHED/GROUNDED" if emergency_lock else "GROUNDED"
                mission_type = "IDLE"
                is_loitering = False
                target["z"] = -1 # Locked state until next command
                log_event("Touchdown successful. System grounded.")

            # 2. Horizontal Physics
            if pos["z"] > 0.5:
                if CONFIG["type"] == "FIXED_WING":
                    orbit_radius = 200.0
                    cruise_speed = CONFIG.get("stall_speed", 30) * 1.2
                    is_kamikaze_dive = (mission_type == "STRIKE" and CONFIG.get("behavior_type") == "KAMIKAZE")
                    is_rtl_descending = (mission_type == "RTL" and target["z"] <= 0)

                    # Dynamic Orbit Radius for Landing (Spiral down)
                    if is_rtl_descending:
                        # Shrink radius as we descend: 200m at high alt, down to 15m near ground
                        orbit_radius = max(15.0, min(200.0, pos["z"] * 2.0))

                    # FIXED WING: Kamikaze Dive Logic (No loitering, direct impact)
                    if is_kamikaze_dive:
                        angle = math.atan2(dy, dx)
                        pos["x"] += math.cos(angle) * CONFIG["max_speed"] * dt
                        pos["y"] += math.sin(angle) * CONFIG["max_speed"] * dt
                        heading = math.degrees(angle)
                        status = "STRIKE (DIVE)"
                        if dist_to_center < 10.0 and pos["z"] < 5.0:
                            perform_action(now)

                    # FIXED WING: Loitering / Landing / Action Logic
                    elif (dist_to_center < 15.0 or is_loitering or is_rtl_descending):
                        if not is_loitering:
                            is_loitering = True
                            orbit_angle = math.atan2(pos["y"] - target["y"], pos["x"] - target["x"])
                            if mission_type in ["STRIKE", "SENSOR", "RESCUE_TUBE", "MEDKIT"]:
                                perform_action(now)
                        
                        orbit_angle += (cruise_speed / orbit_radius) * dt
                        tx = target["x"] + math.cos(orbit_angle) * orbit_radius
                        ty = target["y"] + math.sin(orbit_angle) * orbit_radius
                        tdx, tdy = tx - pos["x"], ty - pos["y"]
                        angle = math.atan2(tdy, tdx)
                        pos["x"] += math.cos(angle) * cruise_speed * dt
                        pos["y"] += math.sin(angle) * cruise_speed * dt
                        heading = math.degrees(angle)
                        status = "LANDING (ORBIT)" if is_rtl_descending else "LOITERING (ORBIT)"
                    
                    # FIXED WING: Transit Logic
                    else:
                        angle = math.atan2(dy, dx)
                        speed = CONFIG["max_speed"] if mission_type != "RTL" else cruise_speed
                        pos["x"] += math.cos(angle) * speed * dt
                        pos["y"] += math.sin(angle) * speed * dt
                        heading = math.degrees(angle)
                        status = "RETURNING" if mission_type == "RTL" else "TRANSIT"

                else: # ROTARY
                    if dist_to_center > 2.0: 
                        angle = math.atan2(dy, dx)
                        pos["x"] += math.cos(angle) * CONFIG["max_speed"] * dt
                        pos["y"] += math.sin(angle) * CONFIG["max_speed"] * dt
                        heading = math.degrees(angle)
                        status = "RETURNING" if mission_type == "RTL" else "TRANSIT"
                    else:
                        if mission_type in ["STRIKE", "SENSOR", "RESCUE_TUBE", "MEDKIT"]:
                            perform_action(now)
                        else:
                            status = "HOVERING"

            # Battery & GPS Update
            battery -= CONFIG["battery_drain"] * dt
            if battery < 5 and not emergency_lock:
                emergency_lock = True
                mission_type, target["z"] = "RTL", 0
                log_event("CRITICAL BATTERY: Initiating emergency RTL and landing.")
            
            if dist_to_center < 50 and pos["z"] < 1: 
                if battery < 100:
                    battery = min(100, battery + 5.0 * dt)

            pos["lat"] = HOME[0] + (pos["y"] / 111111)
            pos["lon"] = HOME[1] + (pos["x"] / (111111 * math.cos(math.radians(HOME[0]))))

            if now - last_telemetry > 1.0:
                client.publish(f"hive/drone/{ID}/telemetry", json.dumps({
                    "id": ID, "model": MODEL_KEY, "lat": pos["lat"], "lon": pos["lon"],
                    "x": pos["x"], "y": pos["y"], "altitude": round(pos["z"], 1),
                    "heading": round(heading), "battery": round(battery, 1), "status": status, "capability": CAPABILITY,
                    "video_snapshot": get_map_tile(pos["lat"], pos["lon"], pos["z"]), "ts": int(now)
                }))
                last_telemetry = now

        time.sleep(0.1)

except KeyboardInterrupt:
    log_event("Shutdown command received.")
    client.loop_stop()
    sys.exit()
