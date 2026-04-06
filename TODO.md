# 📋 HORNET HIVE - Project Roadmap & TODO

## 🕹️ Gaming & Simulation
- [ ] **Multi-Waypoint Missions**: Allow users to click multiple points on the map to define a complex flight path.
- [ ] **Scenario Editor**: A UI tool to add new scenarios (Lat/Lon/Zoom) without editing JSON.
- [x] **Spatial Markers (POI)**: Ability to define Points of Interest for the AI Commander.
- [x] **Tactical Radar**: Proximity radar mock for spatial awareness implemented.
- [x] **POI Expansion**: Scenarios (eg. Fukushima) now can include tactical offsets and targets.
- [ ] **3D Visualization**: Explore integration with CesiumJS or Mapbox for a 3D tactical view.
- [x] **Action Loop (OODA)**: Search -> Detect -> Action workflow implemented with mission success states.

## 🧠 AI & Research
- [x] **Threaded Camera Bridge**: High-performance RTSP handling on Apple M3.
- [x] **Operational States**: WRA logic and status indicators implemented.
- [x] **Mission Logic (Cooldown)**: Notification throttling and "Found once" logic implemented in UI.
- [ ] **Visual SLAM**: Basic simulation of position tracking via camera feed.
- [x] **AI Commander**: Basic commands managed by Ai (LLM model hosted locally on Ollama).
- [ ] **AI Commander Actions**: Enhance `commander_ai.py` to trigger specialized actions (Rescue/Strike) based on mission state.

## 🔌 Real-world Integration
- [x] **Camera**: RTSP camera streams integrated.
- [x] **Alerting (Telegram)**: Real-time mobile alerts with photo proof implemented.
- [ ] **MAVLink Full Support**: Move from POC to a stable bridge supporting ArduPilot/PX4 missions.
- [x] **WRA Logic (Weapon Release)**: Gesture-based strike authorization implemented with 30s timeout.
- [x] **Notification System**: Telegram Bridge implemented for real-time mobile alerts with photo proof.
- [ ] **Sensors**: IoT sensors support.

## 🛡️ Stability & Security
- [x] **Tiered Logging**: Standardized logging with --log and --debug flags implemented.
- [ ] **Authentication**: Add a login layer to the C4I Dashboard.
- [ ] **NIS2/PRESTO Compliance**: Research and implement encryption (TLS/AES) for MQTT and RTSP streams.
- [ ] **Heartbeat Optimization**: More robust handling of high-latency MQTT connections.
- [x] **Dockerization**: Scenario-based `docker-compose` files for HH, SAR, DEF, and MIL missions.
- [x] **Docker Optimization**: Separation of AI and Mock images for edge deployment.
