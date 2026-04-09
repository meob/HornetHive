import paho.mqtt.client as mqtt
import json
import time
import requests
import argparse
import sys
import os
import random
import threading

# Global cache for the last known weather
weather_cache = None
cache_lock = threading.Lock()

def get_weather(lat, lon, api_key):
    """Fetch real-time weather data from OpenWeatherMap."""
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {
                "temp": data["main"]["temp"],
                "humidity": data["main"]["humidity"],
                "pressure": data["main"]["pressure"],
                "wind_speed": data["wind"]["speed"],
                "wind_deg": data["wind"]["deg"],
                "description": data["weather"][0]["description"],
                "icon": data["weather"][0]["icon"],
                "city": data.get("name", "Unknown Area")
            }
        else:
            print(f"[!] OWM Error: {response.status_code} - {response.text}", flush=True)
            return None
    except Exception as e:
        print(f"[!] Connection Error: {e}", flush=True)
        return None

def fetch_worker(args, api_key):
    """Background worker to update weather data at long intervals."""
    global weather_cache
    
    # Initial data if no API or while waiting for first fetch
    current_mock = {
        "temp": 22.5, "humidity": 45, "pressure": 1013,
        "wind_speed": 8.2, "wind_deg": 134,
        "description": "clear sky", "icon": "01d", "city": args.city
    }

    while True:
        try:
            new_data = None
            if api_key:
                new_data = get_weather(args.lat, args.lon, api_key)
            
            with cache_lock:
                if new_data:
                    weather_cache = new_data
                elif not weather_cache:
                    # Simulation mode: apply very light jitter to dummy data
                    current_mock["temp"] += random.uniform(-0.01, 0.01)
                    current_mock["humidity"] = max(0, min(100, current_mock["humidity"] + random.uniform(-0.02, 0.02)))
                    current_mock["wind_speed"] = max(0, current_mock["wind_speed"] + random.uniform(-0.01, 0.01))
                    current_mock["wind_deg"] = (current_mock["wind_deg"] + random.uniform(-0.1, 0.1)) % 360
                    weather_cache = current_mock.copy()
                else:
                    # Keep last cache but add a tiny jitter to keep it "alive"
                    weather_cache["temp"] += random.uniform(-0.005, 0.005)
                    weather_cache["wind_speed"] = max(0, weather_cache["wind_speed"] + random.uniform(-0.005, 0.005))
                    weather_cache["wind_deg"] = (weather_cache["wind_deg"] + random.uniform(-0.05, 0.05)) % 360

            if api_key and new_data:
                print(f"[*] {args.id}: API Update @ {weather_cache['temp']:.1f}°C in {weather_cache['city']}", flush=True)
        except Exception as e:
            print(f"[!] {args.id}: Fetch worker error: {e}", flush=True)
        
        time.sleep(args.interval)

def main():
    parser = argparse.ArgumentParser(description="HORNET HIVE | Weather Mock Service")
    parser.add_argument("--id", type=str, default="SENS_01", help="Unique ID for this station")
    parser.add_argument("--lat", type=float, default=45.0, help="Latitude")
    parser.add_argument("--lon", type=float, default=7.0, help="Longitude")
    parser.add_argument("--api-key", type=str, help="OWM API Key")
    parser.add_argument("--city", type=str, default="Classified Area", help="City name")
    parser.add_argument("--interval", type=int, default=600, help="API fetch interval (default: 600s)")
    parser.add_argument("--mqtt-host", type=str, default="localhost", help="MQTT Host")
    
    args = parser.parse_args()
    api_key = args.api_key or os.environ.get("OWM_API_KEY")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.loop_start()

    connected = False
    while not connected:
        try:
            print(f"[*] {args.id} connecting to MQTT at {args.mqtt_host}...", flush=True)
            client.connect(args.mqtt_host, 1883, 60)
            connected = True
        except Exception as e:
            print(f"[!] MQTT Connection failed: {e}. Retrying...", flush=True)
            time.sleep(2)

    # Start the fetching worker thread
    threading.Thread(target=fetch_worker, args=(args, api_key), daemon=True).start()

    print(f"[*] {args.id} ACTIVE. Heartbeat every 1s to hive/weather/{args.id}/telemetry", flush=True)

    while True:
        with cache_lock:
            if weather_cache:
                data = weather_cache.copy()
                data["id"] = args.id
                data["type"] = "WEATHER"
                data["icon_type"] = "🌡️"
                data["timestamp"] = time.time()
                client.publish(f"hive/weather/{args.id}/telemetry", json.dumps(data), retain=True)
        
        time.sleep(1) # Fast publish for UI reliability

if __name__ == "__main__":
    main()
