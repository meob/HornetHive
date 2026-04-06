import cv2
import json
import time
import paho.mqtt.client as mqtt
import argparse
import base64
import numpy as np
from ultralytics import YOLO
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# --- CLI ARGUMENTS ---
parser = argparse.ArgumentParser(description="HORNET HIVE - Intelligence Bridge with Gesture Auth")
parser.add_argument("--id", type=str, default="HIVE_EYE_01", help="Unique ID for this sensor")
parser.add_argument("--targets", type=str, default="person,car", help="COCO classes to monitor")
parser.add_argument("--source", type=str, default="0", help="Video source")
parser.add_argument("--mqtt-host", type=str, default="localhost", help="MQTT Broker Host")
parser.add_argument("--device", type=str, default="mps", help="Inference device")
parser.add_argument("--show", action="store_true", help="Show local debug window")
args = parser.parse_args()

# --- CONFIGURATION ---
AI_DEVICE = args.device
MODEL_FILE = "yolov8n.pt"
GESTURE_MODEL = "hand_landmarker.task"
MONITOR_PROFILE = args.targets.split(",")
VIDEO_SOURCE = int(args.source) if args.source.isdigit() else args.source

STREAK_REQUIRED = 2
REPORT_INTERVAL = 3 
GRACE_PERIOD = 15
CONFIDENCE_MIN = 0.5
ALIVE_INTERVAL = 10 # Send context snapshot every 10s

# --- MEDIAPIPE SETUP (Gesture Recognition) ---
base_options = python.BaseOptions(model_asset_path=GESTURE_MODEL)
options = vision.HandLandmarkerOptions(base_options=base_options, num_hands=1)
detector = vision.HandLandmarker.create_from_options(options)

def is_ok_gesture(hand_landmarks):
    """Detects 'OK' gesture: thumb and index touching, others extended."""
    l = hand_landmarks[0]
    def dist(p1, p2):
        return np.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)
    # 1. Check if Thumb (4) and Index (8) tips are close
    tip_dist = dist(l[4], l[8])
    # 2. Check if other fingers are extended
    middle_ext = l[12].y < l[10].y
    ring_ext = l[16].y < l[14].y
    pinky_ext = l[20].y < l[18].y
    return tip_dist < 0.05 and middle_ext and ring_ext and pinky_ext

# --- STATE TRACKING ---
state = {cls: {"streak": 0, "missing": 0, "active": False, "last_report": 0} for cls in MONITOR_PROFILE}
last_alive_snapshot = 0

# --- MQTT SETUP ---
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
lwt_payload = json.dumps({"sensor": args.id, "status": "OFFLINE", "ts": int(time.time())})
client.will_set("hive/alerts/status", lwt_payload, qos=1, retain=False)

# --- MQTT CONNECTION WITH RETRY ---
connected = False
while not connected:
    try:
        print(f"[*] {args.id} connecting to MQTT at {args.mqtt_host}...")
        client.connect(args.mqtt_host, 1883, 60)
        connected = True
        print(f"[+] {args.id} connected to MQTT.")
    except Exception as e:
        print(f"[-] {args.id} connection failed ({e}). Retrying in 10s...")
        time.sleep(10)

client.loop_start()

# --- AI MODELS & CAPTURE ---
model = YOLO(MODEL_FILE)
cap = cv2.VideoCapture(VIDEO_SOURCE)

def get_base64_snapshot(frame):
    small = cv2.resize(frame, (320, 240))
    _, buffer = cv2.imencode('.jpg', small, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
    return base64.b64encode(buffer).decode('utf-8')

# Camera Warm-up: Skip first 15 frames to allow auto-exposure
print(f"[*] {args.id}: Warming up camera...")
for _ in range(15):
    cap.read()

# Send initial ONLINE status with a clean snapshot
success, frame = cap.read()
if success:
    initial_snap = get_base64_snapshot(frame)
    client.publish("hive/alerts/status", json.dumps({"sensor": args.id, "status": "ONLINE", "snapshot": initial_snap}), retain=True)
    last_alive_snapshot = time.time()

print(f"[*] {args.id}: Active. Monitoring {MONITOR_PROFILE}")

try:
    while cap.isOpened():
        success, frame = cap.read()
        if not success: break

        now = time.time()

        # 0. ALIVE SNAPSHOT (Heartbeat)
        if (now - last_alive_snapshot) > ALIVE_INTERVAL:
            snap = get_base64_snapshot(frame)
            client.publish("hive/alerts/status", json.dumps({"sensor": args.id, "status": "ONLINE", "snapshot": snap}))
            last_alive_snapshot = now

        # 1. GESTURE DETECTION
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        gesture_results = detector.detect(mp_image)
        gesture_confirmed = False
        
        if gesture_results.hand_landmarks:
            if is_ok_gesture(gesture_results.hand_landmarks):
                gesture_confirmed = True
                if args.show:
                    cv2.putText(frame, "OK GESTURE - AUTHORIZED", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                # Isolated gesture confirmation
                client.publish("hive/operator/confirm", json.dumps({
                    "sensor": args.id, "action": "SYSTEM_AUTHORIZED", "ts": int(now)
                }))

        # 2. OBJECT DETECTION
        results = model(frame, verbose=False, device=AI_DEVICE)
        current_detections = {}
        for r in results:
            for box in r.boxes:
                conf = float(box.conf[0])
                if conf > CONFIDENCE_MIN:
                    label = model.names[int(box.cls[0])]
                    if label in MONITOR_PROFILE:
                        if label not in current_detections or conf > current_detections[label]:
                            current_detections[label] = conf

        # 3. LOGIC & MQTT
        for cls in MONITOR_PROFILE:
            s = state[cls]
            if cls in current_detections:
                s["streak"] += 1
                s["missing"] = 0
                if s["streak"] >= STREAK_REQUIRED:
                    if not s["active"] or (now - s["last_report"]) >= REPORT_INTERVAL or gesture_confirmed:
                        snapshot = get_base64_snapshot(frame)
                        client.publish("hive/alerts/detection", json.dumps({
                            "sensor": args.id, "detected": cls.upper(), "status": "DETECTED",
                            "conf": round(current_detections[cls], 2), "snapshot": snapshot,
                            "operator_auth": gesture_confirmed, "ts": int(now)
                        }))
                        s["active"] = True
                        s["last_report"] = now
                        last_alive_snapshot = now # Reset alive timer on alert
            else:
                if s["active"]:
                    s["missing"] += 1
                    if s["missing"] >= GRACE_PERIOD:
                        client.publish("hive/alerts/detection", json.dumps({
                            "sensor": args.id, "detected": cls.upper(), "status": "CLEARED", "ts": int(now)
                        }))
                        s["active"] = False
                        s["missing"] = 0
                else:
                    s["streak"] = 0

        if args.show:
            cv2.imshow(f"DEBUG: {args.id}", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'): break

finally:
    # Explicitly send OFFLINE message on exit
    client.publish("hive/alerts/status", json.dumps({"sensor": args.id, "status": "OFFLINE", "ts": int(time.time())}))
    cap.release()
    cv2.destroyAllWindows()
    client.loop_stop()
    client.disconnect()
