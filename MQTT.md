# 📡 MQTT Protocol | Hornet Hive

Hornet Hive relies on **MQTT (Message Queuing Telemetry Transport)** for real-time, low-latency communication between the Command Center (CC) and various assets (drones, sensors, targets).

---

## 🏗️ Architecture
The system follows a standard **Publish/Subscribe** pattern. A central Broker (e.g., Mosquitto) handles message routing.

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
