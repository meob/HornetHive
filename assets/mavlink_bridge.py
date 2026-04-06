import time
import json
import paho.mqtt.client as mqtt
import argparse
import math

# Try importing pymavlink, handle missing gracefully for plan verification
try:
    from pymavlink import mavutil
except ImportError:
    print("[!] Warning: pymavlink not found. This bridge requires 'pip install pymavlink'.")

# --- CLI ARGUMENTS ---
parser = argparse.ArgumentParser(description="HORNET HIVE - MAVLink Professional Bridge")
parser.add_argument("--id", type=str, default="MAV_01", help="Unique ID for this drone")
parser.add_argument("--connect", type=str, default="udp:127.0.0.1:14550", help="MAVLink connection string")
args = parser.parse_args()

# --- GEOGRAPHIC UTILS ---
# Standard conversion: 1 degree latitude ~= 111111 meters
def gps_to_meters(lat, lon, home_lat, home_lon):
    y = (lat - home_lat) * 111111
    x = (lon - home_lon) * (111111 * math.cos(math.radians(home_lat)))
    return x, y

# --- MQTT SETUP ---
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
home_gps = None

def on_message(client, userdata, msg):
    global home_gps
    if msg.topic == "hive/sys/config":
        try:
            cfg = json.loads(msg.payload.decode())
            home_gps = [cfg["home_lat"], cfg["home_lon"]]
            print(f"[*] {args.id}: Home coordinates set to {home_gps}")
        except: pass

client.on_message = on_message
client.connect("localhost", 1883)
client.subscribe("hive/sys/config")
client.loop_start()

# --- MAVLINK CONNECTION ---
print(f"[*] {args.id}: Connecting to MAVLink source {args.connect}...")
try:
    master = mavutil.mavlink_connection(args.connect)
    master.wait_heartbeat()
    print(f"[*] {args.id}: Heartbeat received from Flight Controller")
except Exception as e:
    print(f"[!] MAVLink Connection Failed: {e}")
    exit(1)

# --- MAIN LOOP ---
try:
    while True:
        # 1. Read MAVLink Data
        msg_gps = master.recv_match(type='GLOBAL_POSITION_INT', blocking=True, timeout=1.0)
        msg_sys = master.recv_match(type='SYS_STATUS', blocking=True, timeout=1.0)
        
        if msg_gps and home_gps:
            curr_lat = msg_gps.lat / 1e7
            curr_lon = msg_gps.lon / 1e7
            curr_alt = msg_gps.relative_alt / 1000.0 # mm to m
            curr_hdg = msg_gps.hdg / 100.0 # cdeg to deg
            
            # Convert to Hive Cartesian Space
            rel_x, rel_y = gps_to_meters(curr_lat, curr_lon, home_gps[0], home_gps[1])
            
            telemetry = {
                "id": args.id,
                "model": "MAVLINK_DRONE",
                "status": "ACTIVE",
                "battery": msg_sys.battery_remaining if msg_sys else 0,
                "altitude": round(curr_alt, 1),
                "heading": round(curr_hdg, 1),
                "lat": curr_lat,
                "lon": curr_lon,
                "video_snapshot": "" # Requires separate video bridge for MAVLink
            }
            client.publish(f"hive/drone/{args.id}/telemetry", json.dumps(telemetry))

        time.sleep(0.5)

except KeyboardInterrupt:
    print(f"[*] {args.id}: MAVLink Bridge shutting down...")
    client.loop_stop()
    client.disconnect()
