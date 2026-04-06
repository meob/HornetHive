import paho.mqtt.client as mqtt
import json
import argparse
import time

def main():
    parser = argparse.ArgumentParser(description="HORNET HIVE | MQTT Quick Send")
    parser.add_argument("type", choices=['data', 'alert', 'weather', 'raw'], help="Type of message")
    parser.add_argument("--id", default="TEST_01")
    parser.add_argument("--val", type=float, default=0.0)
    parser.add_argument("--metric", default="Value")
    parser.add_argument("--unit", default="")
    parser.add_argument("--topic", help="Custom topic (required for raw)")
    parser.add_argument("--msg", help="Custom JSON message (required for raw)")
    parser.add_argument("--mqtt-host", default="localhost")
    args = parser.parse_args()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(args.mqtt_host, 1883, 60)

    topic = args.topic
    payload = {}

    if args.type == 'data':
        topic = topic or f"hive/data/{args.id}/telemetry"
        payload = {"id": args.id, "v": args.val, "metric": args.metric, "u": args.unit, "status": "ONLINE", "ts": int(time.time())}
    elif args.type == 'alert':
        topic = topic or "hive/alerts/detection"
        payload = {"sensor": args.id, "event": "MANUAL_TEST", "status": "DETECTED", "detected": args.metric}
    elif args.type == 'weather':
        topic = topic or f"hive/weather/{args.id}/telemetry"
        payload = {"id": args.id, "temp": args.val, "humidity": 50, "wind_speed": 0, "wind_deg": 0}
    else: # raw
        if not args.topic or not args.msg:
            print("[!] Error: --topic and --msg are required for raw type")
            return
        payload = json.loads(args.msg)

    client.publish(topic, json.dumps(payload))
    print(f"[*] Sent to {topic}: {payload}")
    client.disconnect()

if __name__ == "__main__":
    main()
