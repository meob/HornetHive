import paho.mqtt.client as mqtt
import json
import time
import argparse

class MqttBridge:
    def __init__(self, args):
        self.args = args
        self.buffer = []
        self.last_send = time.time()

        # Source Client
        self.src_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.src_client.on_message = self.on_message
        
        # Destination Client (Hornet Hive)
        self.dst_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

    def on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload)
            # Value extraction (simple top-level key)
            val = data.get(self.args.key)
            if val is None: return

            if self.args.interval == 0:
                self.forward(float(val))
            else:
                self.buffer.append(float(val))
                if time.time() - self.last_send >= self.args.interval:
                    avg = sum(self.buffer) / len(self.buffer)
                    self.forward(avg)
                    self.buffer = []
                    self.last_send = time.time()
        except Exception as e:
            print(f"[!] Bridge Error: {e}")

    def forward(self, value):
        payload = {
            "id": self.args.id,
            "type": "BRIDGE",
            "metric": self.args.metric or self.args.key,
            "v": round(value, 2),
            "u": self.args.unit,
            "status": "ONLINE",
            "ts": int(time.time())
        }
        topic = f"hive/data/{self.args.id}/telemetry"
        self.dst_client.publish(topic, json.dumps(payload))
        print(f"[*] Bridged {self.args.key}={value} -> {topic}")

    def run(self):
        self.dst_client.connect(self.args.dst_host, 1883)
        self.dst_client.loop_start()

        self.src_client.connect(self.args.src_host, 1883)
        self.src_client.subscribe(self.args.src_topic)
        
        print(f"[*] Bridge ACTIVE: {self.args.src_host}:{self.args.src_topic} -> {self.args.dst_host}")
        self.src_client.loop_forever()

def main():
    parser = argparse.ArgumentParser(description="HORNET HIVE | MQTT Bridge & Averager")
    parser.add_argument("--id", required=True, help="Target Asset ID for HH")
    parser.add_argument("--src-host", required=True)
    parser.add_argument("--src-topic", required=True)
    parser.add_argument("--key", required=True, help="JSON key to extract from source")
    parser.add_argument("--dst-host", default="localhost")
    parser.add_argument("--metric", help="Metric name for HH")
    parser.add_argument("--unit", default="")
    parser.add_argument("--interval", type=int, default=0, help="Averaging interval in seconds (0 = real-time)")
    
    args = parser.parse_args()
    bridge = MqttBridge(args)
    bridge.run()

if __name__ == "__main__":
    main()
