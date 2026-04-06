import cv2
import json
import time
import paho.mqtt.client as mqtt
import argparse
import base64
import numpy as np
import os
import threading
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# --- CLI ARGUMENTS ---
parser = argparse.ArgumentParser(description="HORNET HIVE - Operator Authority Bridge (WRA)")
parser.add_argument("--id", type=str, default="OPERATOR_01", help="Unique ID for this operator station")
parser.add_argument("--source", type=str, default="0", help="Webcam source (0, 1, or rtsp:// URL)")
parser.add_argument("--mqtt-host", type=str, default="localhost", help="MQTT Broker Host")
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
        with open(os.path.join(LOG_DIR, f"debug_authority_{args.id}.log"), "a") as f:
            f.write(f"[{time.ctime()}] {msg}\n")

def log_event(msg):
    print(msg)
    if args.log:
        with open(os.path.join(LOG_DIR, f"mission_events_{time.strftime('%Y-%m-%d')}.log"), "a") as f:
            f.write(f"[{time.ctime()}] {args.id}: {msg}\n")

# --- CONFIGURATION ---
GESTURE_MODEL = "hand_landmarker.task"
VIDEO_SOURCE = int(args.source) if args.source.isdigit() else args.source
ALIVE_INTERVAL = 10 

# --- THREADED CAPTURE ---
class VideoStream:
    def __init__(self, src):
        self.stream = cv2.VideoCapture(src)
        self.stream.set(cv2.CAP_PROP_BUFFERSIZE, 1)
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

# --- MEDIAPIPE SETUP ---
base_options = python.BaseOptions(model_asset_path=GESTURE_MODEL)
options = vision.HandLandmarkerOptions(base_options=base_options, num_hands=1)
detector = vision.HandLandmarker.create_from_options(options)

def is_thumbs_up(hand_landmarks):
    # landmarks[0] is a list of 21 points
    l = hand_landmarks[0]
    
    def dist_sq(p1, p2):
        return (p1.x - p2.x)**2 + (p1.y - p2.y)**2

    # Wrist is point 0. We check distance of tips vs middle joints
    wrist = l[0]
    
    thumb_ext = dist_sq(l[4], wrist) > dist_sq(l[2], wrist)
    index_closed = dist_sq(l[8], wrist) < dist_sq(l[6], wrist)
    middle_closed = dist_sq(l[12], wrist) < dist_sq(l[10], wrist)
    ring_closed = dist_sq(l[16], wrist) < dist_sq(l[14], wrist)
    pinky_closed = dist_sq(l[20], wrist) < dist_sq(l[18], wrist)
    
    # Thumb should be higher than the wrist (Vertical Thumb Up)
    is_vertical = l[4].y < l[2].y
    
    return thumb_ext and index_closed and middle_closed and ring_closed and pinky_closed and is_vertical

# --- STATE TRACKING ---
last_alive_snapshot = 0
gesture_start_time = None
last_auth_time = 0
HOLD_DURATION = 1.0  # Seconds to hold the gesture
COOLDOWN_DURATION = 5.0  # Seconds to wait after an authorization

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

def get_base64_snapshot(frame):
    if frame is None: return ""
    small = cv2.resize(frame, (320, 240))
    _, buffer = cv2.imencode('.jpg', small, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
    return base64.b64encode(buffer).decode('utf-8')

print(f"[*] {args.id}: Connecting to operator camera {VIDEO_SOURCE}...")
vs = VideoStream(VIDEO_SOURCE).start()
time.sleep(2.0) # Warmup

print(f"[*] {args.id}: Authority Bridge Online. Awaiting 'THUMBS UP' gesture for WRA.")

try:
    while True:
        grabbed, frame = vs.read()
        
        if not grabbed or vs.stopped:
            print(f"[!] {args.id}: Camera error. Reconnecting...")
            vs.release()
            time.sleep(5)
            vs = VideoStream(VIDEO_SOURCE).start()
            continue

        if frame is None: continue

        now = time.time()

        # Heartbeat / Status update
        if (now - last_alive_snapshot) > ALIVE_INTERVAL:
            snap = get_base64_snapshot(frame)
            client.publish("hive/alerts/status", json.dumps({"sensor": args.id, "status": "ONLINE", "snapshot": snap}))
            last_alive_snapshot = now

        # GESTURE DETECTION (HMI) with Hold-to-Confirm logic
        if now - last_auth_time < COOLDOWN_DURATION:
            if args.show:
                cv2.putText(frame, "SYSTEM AUTHORIZED - COOLDOWN", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        else:
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            gesture_results = detector.detect(mp_image)
            
            if gesture_results.hand_landmarks and is_thumbs_up(gesture_results.hand_landmarks):
                if gesture_start_time is None:
                    gesture_start_time = now
                
                elapsed = now - gesture_start_time
                if elapsed >= HOLD_DURATION:
                    client.publish("hive/operator/confirm", json.dumps({
                        "sensor": args.id, "action": "SYSTEM_AUTHORIZED", "ts": int(now)
                    }))
                    print(f"[!] {args.id}: WRA AUTHORIZED (Thumbs Up held for {HOLD_DURATION}s)")
                    last_auth_time = now
                    gesture_start_time = None
                    if args.show:
                        cv2.putText(frame, "AUTHORIZED!", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 3)
                else:
                    if args.show:
                        # Progress bar for holding gesture
                        bar_w = int(200 * (elapsed / HOLD_DURATION))
                        cv2.rectangle(frame, (50, 60), (250, 80), (0, 255, 255), 2)
                        cv2.rectangle(frame, (50, 60), (50 + bar_w, 80), (0, 255, 255), -1)
                        cv2.putText(frame, f"HOLDING: {elapsed:.1f}s", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            else:
                gesture_start_time = None

        if args.show:
            cv2.imshow(f"AUTHORITY: {args.id}", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'): break

except KeyboardInterrupt:
    print(f"\n[*] {args.id}: Shutdown requested by operator.")

finally:
    # 1. Stop MQTT
    client.publish("hive/alerts/status", json.dumps({"sensor": args.id, "status": "OFFLINE", "ts": int(time.time())}))
    client.loop_stop()
    client.disconnect()

    # 2. Stop Video Thread
    if 'vs' in locals():
        vs.release()

    # 3. Explicitly close MediaPipe detector
    if 'detector' in locals():
        detector.close()
    
    # 4. Cleanup UI
    cv2.destroyAllWindows()
    cv2.waitKey(1) 
    print(f"[*] {args.id}: Resources released. Terminal safe.")
