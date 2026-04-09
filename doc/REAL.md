# 🔌 Hornet Hive | Real-World Integration Guide

This guide provides technical insights and "tips & tricks" for connecting physical hardware to the Hornet Hive C4I station. 

---

## 📷 RTSP Cameras (Intelligence Bridge)

The `camera_bridge.py` module uses YOLOv8 to process RTSP streams.

### 1. Configuration
- **Environment Variables:** Define your streams using `CAM_01_URL`, `CAM_02_URL`, etc.
- **Protocol:** Most IP cameras use RTSP on port **554**.
- **URL Format:** `rtsp://username:password@IP_ADDRESS:554/stream_path`

### 💡 Tips & Tricks: TP-Link Tapo Cameras
- **The "Cloud" Trap:** You **cannot** use your TP-Link ID (email) and app password for RTSP.
- **Solution:** You must create a **"Camera Account"** specifically for local integration:
    1. Open the Tapo App.
    2. Go to `Camera Settings` -> `Advanced Settings` -> `Camera Account`.
    3. Create a dedicated username and password here. Use these credentials in your RTSP URL.
- **Stream Choice:** Tapo usually provides `/stream1` (HD) and `/stream2` (SD). Use `/stream2` for lower latency if your AI processing server is under heavy load.

---

## 📡 ESP32 & IoT Sensors

Integrate custom hardware (motion sensors, tripwires, environmental sensors) via MQTT.

### 1. MQTT Topic Structure
To trigger an alert in Hornet Hive, your ESP32 should publish a JSON payload to:
`hive/alerts/detection`

**Payload Example:**
```json
{
  "sensor": "ESP32_PERIMETER_NORTH",
  "event": "PIR_MOTION",
  "lat": 41.209, 
  "lon": 9.275,
  "ts": 1712245200
}
```

### 💡 Tips & Tricks: ESP32 Connectivity
- **Static IPs:** Always assign static IPs to your sensors in your router's DHCP table to avoid losing connection during lease renewals.
- **Deep Sleep:** If battery-powered, use ESP32 Deep Sleep but keep the MQTT connection logic efficient. Reconnecting to WiFi takes 2-5 seconds; factor this into your "detection-to-alert" latency.
- **Capacitors:** Add a 10uF - 100uF capacitor across the VCC/GND of the ESP32 to handle the current spikes during WiFi transmission, which often cause "ghost" reboots.

---

## 🌐 Networking & WiFi Stability

### 1. The Dual-Band Dilemma
- **Interference:** Most drones (like DJI Tello) and ESP32 modules operate exclusively on the **2.4GHz** band.
- **Band Steering:** Modern routers try to "steer" devices to 5GHz. This often causes connection drops for IoT devices.
- **Recommendation:** Disable "Smart Connect" or "Band Steering" on your router. Create a dedicated 2.4GHz SSID (e.g., `HORNET_HIVE_IOT`) specifically for your assets.
- **Channels:** Use non-overlapping channels (1, 6, or 11) to minimize interference in crowded areas.

### 2. Latency vs. Docker
- **The Bridge Overhead:** While Docker is great for portability, it adds a network layer. 
- **Real-time AI:** If you are using an Apple Silicon Mac (M3), run the `camera_bridge.py` **natively** (outside Docker) to fully leverage the Metal Performance Shaders (MPS) and reduce frame-processing latency.

---

## 🛸 Hardware Drones (Tello / MAVLink)

### 1. DJI Tello
- **Direct Connection:** The Tello acts as an Access Point. Your computer must connect directly to the Tello's WiFi.
- **Bridge:** Use `python assets/tello_bridge.py`. It translates MQTT commands from the UI into Tello SDK UDP packets.

### 2. MAVLink (Pixhawk / ArduPilot)
- **Connection:** Use a USB-to-Telemetry radio or a direct USB connection to the Flight Controller.
- **GCS Conflict:** Do not run Mission Planner or QGroundControl simultaneously with `mavlink_bridge.py` on the same COM/Serial port. Use a MAVProxy splitter if you need both.

---

## 🛠️ Debugging "Real" Issues

- **MQTT Monitor:** Use `python assets/mqtt_debug.py` to see the raw traffic. If the UI isn't updating, check if the "Real" device is actually publishing valid JSON.
- **Firewalls:** Ensure ports **1883** (MQTT) and **3000** (UI) are open on the host machine running Hornet Hive.
- **Log Monitoring:** Keep a terminal open with `tail -f logs/drone_events_YYYY-MM-DD.log` to monitor physical asset handshakes.

---

## 🌡️ DIY Weather Station (ESP32 + BME280)

You can replace the `meteo_mock.py` with a real physical sensor station.

### 1. Hardware Setup
- **Sensor:** BME280 (I2C).
- **MCU:** ESP32.
- **Connections:** SDA (GPIO 21), SCL (GPIO 22).

### 2. Software (ESPHome)
Use the configuration in `integrations/esp32-bme280-weather/weather_station.yaml`. The ESP32 will publish a JSON payload to `hive/weather/telemetry` every 60 seconds.

**Format Compatibility:**
Hornet Hive requires specific fields to render the weather hexagon. Even if your sensor doesn't provide them, you must send "mocked" values:
```json
{
  "temp": 22.5,
  "humidity": 45,
  "pressure": 1013,
  "wind_speed": 0,
  "wind_deg": 0,
  "description": "LOCAL SENSOR",
  "icon": "50d"
}
```

### 💡 Tips & Tricks: BME280 Calibration
- **Self-Heating:** The ESP32 generates heat. Keep the sensor at least 5cm away from the MCU or use a `lambda` filter in ESPHome to subtract an offset (usually -2.0°C).
- **I2C Address:** If the sensor isn't detected, check the address. Generic modules often use `0x76`, while original Bosch sensors use `0x77`.
