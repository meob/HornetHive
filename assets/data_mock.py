import paho.mqtt.client as mqtt
import json
import time
import random
import math
import argparse

def main():
    parser = argparse.ArgumentParser(description="HORNET HIVE | Universal Data Mock")
    parser.add_argument("id", help="Asset ID (e.g. PATIENT_01)")
    parser.add_argument("--type", default="GENERIC", help="Asset Type (e.g. MEDICAL, ENERGY)")
    parser.add_argument("--metric", default="Value", help="Metric Name (e.g. BPM, Temp)")
    parser.add_argument("--unit", default="", help="Metric Unit (e.g. bpm, °C)")
    parser.add_argument("--min", type=float, default=60.0)
    parser.add_argument("--max", type=float, default=100.0)
    parser.add_argument("--freq", type=float, default=1.0, help="Publish frequency (seconds)")
    parser.add_argument("--trend", choices=['stable', 'sine', 'random', 'drift', 'heartbeat'], default='random')
    parser.add_argument("--mqtt-host", default="localhost")
    args = parser.parse_args()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(args.mqtt_host, 1883, 60)
    client.loop_start()

    print(f"[*] DATA MOCK ACTIVE: {args.id} ({args.metric}) -> hive/data/{args.id}/telemetry")
    
    start_time = time.time()
    current_val = (args.min + args.max) / 2
    step_counter = 0

    try:
        while True:
            # Use fixed step instead of elapsed time for a cleaner, more stable wave
            # freq=0.1s -> 10 points per sec. 20 points for a full 2s cycle.
            t = (step_counter * args.freq) % 2.0 
            step_counter += 1
            
            if args.trend == 'stable':
                val = current_val + random.uniform(-0.5, 0.5)
            elif args.trend == 'sine':
                mid = (args.min + args.max) / 2
                amp = (args.max - args.min) / 2
                val = mid + amp * math.sin(t * math.pi) + random.uniform(-0.2, 0.2)
            elif args.trend == 'heartbeat':
                # Cleaner Synthetic ECG: P-QRS-T complex
                # Baseline
                val = (args.min + args.max) / 2
                
                # P-wave (Atrial contraction - smooth bump)
                if 0.2 < t < 0.4: val += 1.5 * math.sin((t-0.2) * math.pi / 0.2)
                # QRS complex (Ventricular contraction - sharp sharp spike)
                if 0.5 < t < 0.55: val -= 3 * math.sin((t-0.5) * math.pi / 0.05)
                if 0.55 < t < 0.65: val += 18 * math.sin((t-0.55) * math.pi / 0.1)
                if 0.65 < t < 0.75: val -= 4 * math.sin((t-0.65) * math.pi / 0.1)
                # T-wave (Ventricular recovery - smooth medium bump)
                if 1.0 < t < 1.4: val += 4 * math.sin((t-1.0) * math.pi / 0.4)
                
                # Small physiological noise for natural look (0.3 instead of 0.1)
                val += random.uniform(-0.3, 0.3)
            elif args.trend == 'drift':
                current_val += random.uniform(-1.0, 1.0)
                val = max(args.min, min(args.max, current_val))
                current_val = val
            else: # random
                val = random.uniform(args.min, args.max)

            payload = {
                "id": args.id,
                "type": args.type,
                "metric": args.metric,
                "v": round(val, 2),
                "u": args.unit,
                "status": "ONLINE",
                "ts": int(time.time())
            }

            client.publish(f"hive/data/{args.id}/telemetry", json.dumps(payload))
            time.sleep(args.freq)

    except KeyboardInterrupt:
        client.disconnect()

if __name__ == "__main__":
    main()
