import cv2
import json
import time
import paho.mqtt.client as mqtt
import argparse
import base64
import numpy as np
import os
import threading
from ultralytics import YOLO

# --- FFMPEG OPTIMIZATION FOR RTSP ---
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"

# --- CLI ARGUMENTS ---
parser = argparse.ArgumentParser(description="HORNET HIVE - AI Vision Bridge (ISR)")
parser.add_argument("--id", type=str, default="CAM_01", help="Unique ID for this camera/sensor")
parser.add_argument("--targets", type=str, default="person,car", help="COCO classes to monitor")
parser.add_argument("--source", type=str, default="0", help="Video source (0, 1, or rtsp:// URL)")
parser.add_argument("--mqtt-host", type=str, default="localhost", help="MQTT Broker Host")
parser.add_argument("--device", type=str, default="mps", help="Inference device (mps, cpu, cuda)")
parser.add_argument("--show", action="store_true", help="Show local debug window")
parser.add_argument("--log", action="store_true", help="Enable file logging")
parser.add_argument("--debug", action="store_true", help="Enable verbose debug output")
args = parser.parse_args()

# --- LOGGING SETUP ---
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
if args.log or args.debug:
    if not os.path.exists(LOG_DIR): os.makedirs(LOG_DIR)

def log_debug(msg):
    if args.debug:
        print(msg)
        with open(os.path.join(LOG_DIR, f"debug_camera_{args.id}.log"), "a") as f:
            f.write(f"[{time.ctime()}] {msg}\n")

def log_event(msg):
    print(msg)
    if args.log:
        with open(os.path.join(LOG_DIR, f"mission_events_{time.strftime('%Y-%m-%d')}.log"), "a") as f:
            f.write(f"[{time.ctime()}] {args.id}: {msg}\n")

# --- CONFIGURATION ---
AI_DEVICE = args.device
MODEL_FILE = "yolov8n.pt"
MONITOR_PROFILE = args.targets.split(",")
VIDEO_SOURCE = int(args.source) if args.source.isdigit() else args.source

STREAK_REQUIRED = 2
REPORT_INTERVAL = 3 
GRACE_PERIOD = 15
CONFIDENCE_MIN = 0.5
ALIVE_INTERVAL = 10 

# --- THREADED CAPTURE ---
class VideoStream:
    def __init__(self, src):
        self.stream = cv2.VideoCapture(src, cv2.CAP_FFMPEG)
        self.stream.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.stream.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000)
        (self.grabbed, self.frame) = self.stream.read()
        self.stopped = False
        self.lock = threading.Lock()

    def start(self):
        t = threading.Thread(target=self.update, args=())
        t.daemon = True
        t.start()
        return self

    def update(self):
        while True:
            if self.stopped: return
            (grabbed, frame) = self.stream.read()
            with self.lock:
                self.grabbed = grabbed
                self.frame = frame
            if not grabbed:
                self.stopped = True

    def read(self):
        with self.lock:
            return self.grabbed, self.frame

    def release(self):
        self.stopped = True
        self.stream.release()

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

# --- AI MODELS ---
model = YOLO(MODEL_FILE)

def get_base64_snapshot(frame):
    if frame is None: return ""
    small = cv2.resize(frame, (320, 240))
    _, buffer = cv2.imencode('.jpg', small, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
    return base64.b64encode(buffer).decode('utf-8')

print(f"[*] {args.id}: Connecting to source {VIDEO_SOURCE}...")
vs = VideoStream(VIDEO_SOURCE).start()
time.sleep(2.0) # Warmup

print(f"[*] {args.id}: Monitoring {MONITOR_PROFILE} for ISR.")

try:
    while True:
        grabbed, frame = vs.read()
        
        if not grabbed or vs.stopped:
            print(f"[!] {args.id}: Stream error. Reconnecting...")
            vs.release()
            time.sleep(5)
            vs = VideoStream(VIDEO_SOURCE).start()
            continue

        if frame is None: continue

        now = time.time()

        # Heartbeat
        if (now - last_alive_snapshot) > ALIVE_INTERVAL:
            snap = get_base64_snapshot(frame)
            client.publish("hive/alerts/status", json.dumps({"sensor": args.id, "status": "ONLINE", "snapshot": snap}))
            last_alive_snapshot = now

        # 1. OBJECT DETECTION (ISR)
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

        # 2. LOGIC
        for cls in MONITOR_PROFILE:
            s = state[cls]
            if cls in current_detections:
                s["streak"] += 1
                s["missing"] = 0
                if s["streak"] >= STREAK_REQUIRED:
                    if not s["active"] or (now - s["last_report"]) >= REPORT_INTERVAL:
                        snapshot = get_base64_snapshot(frame)
                        client.publish("hive/alerts/detection", json.dumps({
                            "sensor": args.id, "detected": cls.upper(), "status": "DETECTED",
                            "conf": round(current_detections[cls], 2), "snapshot": snapshot,
                            "ts": int(now)
                        }))
                        s["active"] = True
                        s["last_report"] = now
                        last_alive_snapshot = now
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
            cv2.imshow(f"ISR: {args.id}", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'): break

finally:
    client.publish("hive/alerts/status", json.dumps({"sensor": args.id, "status": "OFFLINE", "ts": int(time.time())}))
    vs.release()
    cv2.destroyAllWindows()
    client.loop_stop()
    client.disconnect()
