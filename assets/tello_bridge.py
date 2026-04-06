import time
import json
import base64
import cv2
import paho.mqtt.client as mqtt
from djitellopy import Tello
import argparse

# --- CLI ARGUMENTS ---
parser = argparse.ArgumentParser(description="HORNET HIVE - DJI Tello Real Bridge")
parser.add_argument("--id", type=str, default="TELLO_01", help="Unique ID for this drone")
args = parser.parse_args()

# --- MQTT SETUP ---
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        if data.get("target_id") in ["ALL", args.id]:
            cmd = data.get("command", "MOVE").upper()
            
            if cmd == "RTL" or data.get("mission") == "RTL":
                print(f"[*] {args.id}: RTL triggered. Landing...")
                tello.land()
            elif cmd == "MOVE":
                # Tello uses relative movement in cm
                # Simple mapping: 1m in UI = 100cm in Tello
                # This is a simplified direct command mapping
                x = int(data.get("x", 0) * 100)
                y = int(data.get("y", 0) * 100)
                z = int(data.get("z", 30) * 100)
                
                if not tello.is_flying:
                    print(f"[*] {args.id}: Taking off...")
                    tello.takeoff()
                
                print(f"[*] {args.id}: Moving to relative {x}, {y}, {z}")
                # Note: Tello move commands are blocking in this library by default
                # Real implementation would need a non-blocking queue
                try:
                    tello.go_xyz_speed(x, y, z, 50)
                except Exception as e:
                    print(f"[!] Flight Error: {e}")

    except Exception as e:
        print(f"[-] Command Parse Error: {e}")

client.on_message = on_message
client.connect("localhost", 1883)
client.subscribe("hive/swarm/target")
client.loop_start()

# --- TELLO INITIALIZATION ---
print(f"[*] {args.id}: Connecting to Tello WiFi...")
tello = Tello()
try:
    tello.connect()
    tello.streamon()
    print(f"[*] {args.id}: Connected. Battery: {tello.get_battery()}%")
except Exception as e:
    print(f"[!] Tello Connection Failed: {e}")
    exit(1)

def get_base64_frame(frame):
    """Compresses Tello frame for MQTT/UI transport."""
    small = cv2.resize(frame, (320, 240))
    _, buffer = cv2.imencode('.jpg', small, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
    return base64.b64encode(buffer).decode('utf-8')

# --- MAIN LOOP (Telemetry & Video) ---
try:
    while True:
        # 1. Capture Real Video
        frame = tello.get_frame_read().frame
        if frame is not None:
            snapshot = get_base64_frame(frame)
        else:
            snapshot = ""

        # 2. Collect Real Telemetry
        # Note: Tello doesn't have GPS, using 0,0 relative to HOME
        telemetry = {
            "id": args.id,
            "model": "DJI_TELLO",
            "status": "FLYING" if tello.is_flying else "GROUNDED",
            "battery": tello.get_battery(),
            "altitude": tello.get_distance_tof() / 100.0, # Convert cm to m
            "heading": 0, # Tello heading requires IMU calculation
            "lat": 0, # Tello lacks GPS
            "lon": 0,
            "video_snapshot": f"data:image/jpeg;base64,{snapshot}"
        }

        # 3. Publish to Hive
        client.publish(f"hive/drone/{args.id}/telemetry", json.dumps(telemetry))

        # 4. Safety Check
        if tello.get_battery() < 10 and tello.is_flying:
            print(f"[!] {args.id}: CRITICAL BATTERY. Auto-landing.")
            tello.land()

        time.sleep(0.5) # 2Hz telemetry update

except KeyboardInterrupt:
    print(f"[*] {args.id}: Shutting down...")
    tello.streamoff()
    if tello.is_flying: tello.land()
    client.loop_stop()
    client.disconnect()
