# 📡 MQTT Protocol | Hornet Hive


**MQTT (Message Queuing Telemetry Transport)** isa lightweight, publish/subscribe messaging protocol designed for IoT and machine-to-machine (M2M) communication. 
It operates on top of TCP/IP, optimized for low bandwidth, high latency, or unreliable networks. Its publish/subscribe model decouples clients, making it highly efficient for remote, resource-constrained devices. 

Core Components of MQTT
* Publisher/Subscriber: Clients that send (publish) or receive (subscribe to) data. They do not connect directly to each other.
* Broker: The central hub that receives all messages and filters/distributes them to interested subscribers.
* Topics: Virtual channels or "subjects" used by the broker to route messages (e.g., home/livingroom/temp). 

Key Features and Benefits
* Lightweight and Efficient: Minimal packet overhead, ideal for low-power sensors and battery-powered devices.
* Publish/Subscribe Model: Decouples communication, facilitating scalable systems.
* Quality of Service (QoS): Supports levels 0, 1, and 2 to guarantee message delivery, ranging from "at most once" to "exactly once".
* Retained Messages: Brokers can keep the last known good value for a topic and send it to new subscribers immediately.
* Last Will and Testament: Enables notifications if a client unexpectedly disconnects. 

In few words: MQTT is an OASIS standard messaging protocol for the Internet of Things (IoT) and is implemented by popular brokers like Eclipse Mosquitto, HiveMQ, and EMQX. 



# 🐝 Hornet Hive & MQTT 📡

**Hornet Hive** relies on MQTT for real-time, low-latency communication between the Command Center (CC) and various assets (drones, sensors, targets).

---

## 🏗️ Architecture
The system follows the standard **Publish/Subscribe** MQTT pattern. A central Broker handles message routing.
The HH examples use Mosquitto.

- **Broker Default Port**: `1883`
- **Topic Prefix**: All topics start with `hive/`

---

## 📋 Topic Structure

### 1. 🛸 Assets (Drones & Hardware)
| Topic | Description | Direction |
| --- | --- | --- |
| `hive/drone/{id}/telemetry` | Position, battery, altitude, heading. | Asset -> CC |
| `hive/swarm/target` | Movement commands (lat, lon, alt). | CC -> Swarm |
| `hive/target/{id}/telemetry` | Mock target positions (e.g., ships). | Mock -> CC |

### 2. 📊 Universal Data (Sensors & Medical)
| Topic | Description | Direction |
| --- | --- | --- |
| `hive/data/{id}/telemetry` | Generic numerical metrics (BPM, SpO2, Temp, BP, etc.). | Sensor -> CC |
| `hive/weather/{id}/telemetry` | Environmental data (wind, temp, humidity). | Station -> CC |

### 3. 🛡️ Alerts & Intelligence
| Topic | Description | Direction |
| --- | --- | --- |
| `hive/alerts/status` | LWT (Last Will) and Online/Offline heartbeats. | Asset -> CC |
| `hive/alerts/detection` | AI detections (YOLO) with Base64 snapshots. | Bridge -> CC |
| `hive/alerts/mayday` | SOS signals from targets in distress. | Target -> CC |

### 4. 🧠 AI & Authority
| Topic | Description | Direction |
| --- | --- | --- |
| `hive/ai/objective` | Natural language commands for the AI. | CC -> AI |
| `hive/ai/feedback` | LLM reasoning status (Thinking, Ready). | AI -> CC |
| `hive/operator/confirm` | Gesture confirmation (WRA) for actions. | Bridge -> CC |

---

## ⚙️ Payload Standards
Most payloads are **JSON** objects.

**Example (Universal Data):**
```json
{
  "id": "P1_BPM",
  "type": "CARDIAC",
  "metric": "HEART_RATE",
  "v": 72.5,
  "u": "bpm",
  "status": "ONLINE",
  "ts": 1712245200
}
```

---

## 🔒 Security
Last but not least: security! A MQTT secure configuration is described in **[MQTT Security](MQTT_SEC.md)** 📖.