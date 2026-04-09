import paho.mqtt.client as mqtt
import json
import time
import os
import argparse

def main():
    parser = argparse.ArgumentParser(description="HORNET HIVE | Logic Gate Alarm Bridge")
    parser.add_argument("--mqtt-host", default="localhost", help="MQTT Broker Host")
    parser.add_argument("--rules", default="assets/alarm_rules.json", help="Path to rules JSON")
    parser.add_argument("--cooldown", type=int, default=60, help="Cooldown between alerts (seconds)")
    parser.add_argument("--log", action="store_true", help="Enable console logging")
    args = parser.parse_args()

    # --- LOAD RULES ---
    rules = {}
    try:
        rules_path = os.path.join(os.getcwd(), args.rules)
        with open(rules_path, "r") as f:
            rules = json.load(f)
        if args.log: print(f"[*] ALARM BRIDGE: Loaded {len(rules)} rule categories from {args.rules}")
    except Exception as e:
        print(f"[!] ERROR: Could not load alarm rules: {e}")
        return

    # Tracking for cooldowns to avoid spamming
    last_alerts = {} 

    def on_connect(client, userdata, flags, rc, properties=None):
        if rc == 0:
            if args.log: print("[*] ALARM BRIDGE: Connected to MQTT. Monitoring hive/data/+/telemetry")
            client.subscribe("hive/data/+/telemetry")
        else:
            print(f"[!] ALARM BRIDGE: Connection failed with code {rc}")

    def on_message(client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            asset_id = payload.get("id")
            asset_type = payload.get("type")
            metric = payload.get("metric")
            value = payload.get("v")

            if not all([asset_id, asset_type, metric, value is not None]):
                return

            # --- RULE CHECKING ---
            category_rules = rules.get(asset_type, {})
            rule = category_rules.get(metric)

            if rule:
                min_val = rule.get("min")
                max_val = rule.get("max")
                alert_triggered = False

                if min_val is not None and value < min_val: alert_triggered = True
                if max_val is not None and value > max_val: alert_triggered = True

                if alert_triggered:
                    now = time.time()
                    alert_key = f"{asset_id}_{metric}"
                    
                    # Check cooldown
                    if now - last_alerts.get(alert_key, 0) > args.cooldown:
                        last_alerts[alert_key] = now
                        
                        icon = "🆘"
                        if asset_type == "CARDIAC": icon = "🫀"
                        elif asset_type == "VITAL": icon = "⛑️"
                        elif asset_type == "ENV": icon = "🔥"

                        alert_msg = {
                            "id": f"ALARM_{asset_id}",
                            "icon": icon,
                            "msg": f"{rule.get('alert_msg', 'ANOMALY')}! {asset_id} {metric}: {value}{payload.get('u','')}",
                            "rough_lat": 0, # Could be linked to asset's location if available
                            "rough_lon": 0,
                            "ts": int(now)
                        }
                        
                        client.publish("hive/alerts/mayday", json.dumps(alert_msg), retain=True)
                        if args.log: print(f"[!] ALERT TRIGGERED: {asset_id} -> {metric}={value}")

        except Exception as e:
            if args.log: print(f"[-] ERROR: Failed to process telemetry: {e}")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message

    connected = False
    while not connected:
        try:
            client.connect(args.mqtt_host, 1883, 60)
            connected = True
        except Exception as e:
            print(f"[-] ALARM BRIDGE: MQTT connection failed ({e}). Retrying in 10s...")
            time.sleep(10)

    client.loop_forever()

if __name__ == "__main__":
    main()
