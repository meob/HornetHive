# 📋 HORNET HIVE - Project Roadmap & TODO

The **Drone Simulation** component is functionally complete, despite some imperfections, encompassing flight physics, battery management, satellite view, and controls.
Integration with **External Sensors** such as RTSP cameras, object detection, standard/DIY sensors, and alarms with Telegram 
is also complete but generally requires specific customization and configuration. 
**Drone Swarm** management, **Real Drone integration** and **AI-assisted flight control** are a proof of concept (POC) and can be extended in various directions.

## 🕹️ Gaming & Simulation
- [x] **Action Loop (OODA)**: Search -> Detect -> Action workflow implemented with mission success states.
- [x] **Tactical Radar**: Proximity radar mock for spatial awareness implemented.
- [x] **POI Expansion**: Scenarios (eg. Fukushima) can include tactical offsets and targets for the AI Commander.
- [x] **Data Graphs**: Line Graphs available in the honeycomb.
- [x] **Data Mock**: Custom data generation.
- [x] **Alarm System**: Simple rule based alarm system.
- [x] **UI Reordering (Drag & Drop)**: Allow operators to manually move hexagons to customize the C2 layout.
- [x] **Honeycomb Zoom**: ~~Add a slider~~ Double-click on an hexagon opens a zoomed-in new browser window.
- [ ] **Spiral Search**: Add a new button to start a drone spiral search 🌀
- [ ] **Multi-Waypoint Missions**: Allow users to click multiple points on the map to define a complex flight path.
- [ ] **Scenario Editor**: A UI tool to add new scenarios (Lat/Lon/Zoom) without editing JSON.
- [ ] **3D Visualization**: Explore integration with CesiumJS or Mapbox for a 3D tactical view.
- [ ] **Game score**: Really ???
- [ ] **Automatic target generation**: Really ???

## 🔌 Real-world Integration
- [x] **Camera**: RTSP camera streams integrated.
- [x] **Notification System**: Telegram Bridge implemented for real-time mobile alerts with photo proof.
- [x] **Alerting (Telegram)**: Real-time mobile alerts with photo proof implemented.
- [ ] **MAVLink Full Support**: Move from POC to a stable bridge supporting ArduPilot/PX4 missions.
- [ ] **Sensors**: Wider IoT sensors support.

## 🧠 AI & Research
- [x] **Threaded Camera Bridge**: High-performance RTSP handling.
- [x] **Operational States**: WRA logic and status indicators implemented.
- [x] **WRA Logic (Weapon Release)**: Gesture-based strike authorization implemented with 30s timeout.
- [x] **Mission Logic (Cooldown)**: Notification throttling and "Found once" logic implemented in UI.
- [x] **AI Commander**: Basic commands managed by AI (LLM model hosted locally on Ollama).
- [ ] **AI Commander Actions**: Enhance `commander_ai.py` to trigger specialized actions (Rescue/Strike) based on mission state.
- [ ] **Visual SLAM**: Basic simulation of position tracking via camera feed.

## 🛡️ Stability & Security
- [x] **Tiered Logging**: Standardized logging with --log and --debug flags implemented.
- [x] **Dockerization**: Scenario-based `docker-compose` files for HH, SAR, DEF, and MIL missions.
- [x] **Docker Optimization**: Separation of AI and Mock images for edge deployment.
- [ ] **Data Alarm Bridge**: Generic threshold-based alerting logic (Medical Emergency, Fire, Industrial Failure).
- [ ] **Authentication**: Add a login layer to the C4I Dashboard.
- [x] **Security**: MQTT security documentation.
- [ ] **NIS2/PRESTO Compliance**: Research and implement encryption (TLS/AES) for MQTT and RTSP streams.
- [ ] **Heartbeat Optimization**: More robust handling of high-latency MQTT connections.

