# 📖 TACTICAL GLOSSARY: C4I & Drone Operations

A comprehensive guide to terms, acronyms, and standards used in modern autonomous systems and the **Hornet Hive** ecosystem. This glossary is designed to bridge the gap between simulation, gaming, and real-world tactical operations.

---

### 📡 C2 & Operations (Command & Control)

**C2 (Command and Control)**
The exercise of authority and direction by a properly designated commander over assigned and attached forces in the accomplishment of the mission. The acronym C3 (Command, Control and Communication) is also used.

**C4I (Command, Control, Communications, Computers, and Intelligence)**
The integrated framework used to manage assets, sensors, and data in real-time. It represents the "nervous system" of modern military and emergency response operations. The acronyms C4ISR (Command, Control, Communications, Computers, Intelligence, Surveillance, and Reconnaissance) and C<sup>4</sup>I<sup>2</sup> (Command, Control, Communications, Computers, Intelligence, Interoperability) are used too.

**ISR (Intelligence, Surveillance, and Reconnaissance)**
An activity that synchronizes and integrates the planning and operation of sensors and assets to provide timely and accurate information for decision-makers. The ISTAR acronym adds the target acquisition phase.

**POI (Point of Interest)**
Specific spatial markers (coordinates) of tactical or operational significance used for navigation, targeting, or surveillance.

**Capability / Payload**
The specific functional equipment of a UAV that defines its mission role. In Hornet Hive, capabilities include **SENSOR** (detection), **RESCUE_TUBE** (maritime rescue), **MEDKIT** (medical supply), and **STRIKE** (kinetic engagement).

**Action Loop (OODA)**
A full mission lifecycle implemented in the station: **Observe** (Detection), **Orient** (UI Analysis), **Decide** (Operator Command), and **Act** (Rescue or Strike).

**MAYDAY / SOS**
An international distress signal. In the simulation, targets emit periodic Mayday signals via MQTT to trigger the search phase of a mission.

**ROE (Rules of Engagement)**
Directives issued by competent authority that delineate the circumstances and limitations under which forces will initiate and/or continue engagement.

**RTL / RTH (Return To Launch / Home)**
A critical safety protocol where an Unmanned Aerial Vehicle (UAV) automatically flies back to its starting coordinates, triggered by low battery, signal loss, or manual command.

**SAM (Surface-to-Air Missile)**
A Surface-to-Air Missile site, is a location where missiles are deployed to target and destroy aerial threats, such as aircraft or missiles. 

**SITREP (Situational Report)**
A periodic report used to update the commander or GCS on the current status of assets, missions, or environmental conditions.

**WRA (Weapon Release Authority)**
The specific protocol and authorization level required to engage a target. In high-stakes environments, this often involves a "Human-in-the-Loop" (HITL) confirmation to prevent automated errors.

---

### 🤖 AI & Computer Vision

**AI (Artificial Intelligence)**
The simulation of human intelligence processes by computer systems. These processes include learning (the acquisition of information and rules for using it), reasoning (using rules to reach approximate or definite conclusions), and self-correction.

**Computer Vision (CV)**
A field of AI that enables computers and systems to derive meaningful information from digital images, videos, and other visual inputs — and take actions or make recommendations based on that information.

**Edge AI**
The practice of running AI algorithms locally on a hardware device (the "edge") rather than in a remote cloud. This ensures low latency and high privacy for real-time tactical decisions.

**HMI (Human-Machine Interface)**
The hardware and software through which a human operator interacts with a complex system. Effective HMI is crucial for maintaining situational awareness without cognitive overload.

**Inference**
The process of using a trained AI model to make predictions or classifications on new, unseen data (e.g., recognizing a "tank" in a live video stream).

**LLM (Large Language Model)**
A type of Artificial Intelligence trained on vast amounts of text data to understand and generate human-like language. In C4I, it acts as a "Tactical Brain" to translate natural language objectives into executable mission plans.

**MediaPipe**
An open-source framework by Google for building multimodal applied machine learning pipelines. In this ecosystem, it is used for high-fidelity hand tracking and gesture recognition (HMI).

**Neural Network**
A series of algorithms that endeavors to recognize underlying relationships in a set of data through a process that mimics the way the human brain operates.

**YOLO (You Only Look Once)**
A state-of-the-art, real-time object detection system. Unlike older systems that scan an image multiple times, YOLO processes the entire image in a single pass, making it ideal for high-speed drone surveillance.

---

### 🛡️ Security & Surveillance

**False Positive / Negative**
- **False Positive**: An alarm triggered when no real threat is present (e.g., a cat detected as a person).
- **False Negative**: A failure to detect a real threat that is actually present.

**Intrusion Detection**
The process of identifying unauthorized access or presence within a specific geographical or digital perimeter (e.g., using YOLO to monitor a "restricted area").

**Notification / Alert**
A real-time message (e.g., via Telegram or SMS) sent to an operator when a specific condition is met, such as the detection of a target with high confidence.

**Object Classification**
The AI's ability to not just detect something, but to categorize it (e.g., distinguishing between a "Car," "Person," or "Dog").

**VMS (Video Management System)**
Software used to manage, record, and analyze video from multiple camera sources simultaneously. Hornet Hive acts as a specialized tactical VMS.

---

### 🛸 Drone & Aviation Tech

**AGL (Above Ground Level)**
Altitude measured relative to the terrain directly below the aircraft. Critical for low-flying rotary drones to avoid obstacles.

**DIY (Do It Yourself)**
DIY stands for "Do It Yourself," referring to the hands-on practice of building, customizing, and programming drones from individual components like frames, motors, and flight controllers, rather than buying pre-assembled models.

**Fixed-Wing vs. Rotary**
- **Fixed-Wing**: Aircraft with stationary wings (like a plane). Efficient for long distances but cannot hover.
- **Rotary-Wing**: Aircraft with rotating blades (like a quadcopter). Capable of hovering and vertical takeoff.

**GCS (Ground Control Station)**
The land- or sea-based control center that provides the facilities for human control of Unmanned Aerial Vehicles (UAVs).

**HALE / MALE (High-Altitude / Medium-Altitude Long-Endurance)**
Categories of strategic UAVs (like the MQ-9 Reaper or RQ-4 Global Hawk) designed for persistent, long-range missions.

**MSL (Mean Sea Level)**
Altitude measured relative to the average sea level. Used by high-altitude strategic assets for global navigation.

**OSD (On-Screen Display)**
The graphical overlay of telemetry data (such as battery levels, altitude, and alerts) directly onto a video feed or tactical map.
It provides the operator with immediate situational awareness without requiring them to look away from the primary mission interface.

**SAR (Search and Rescue)**
A mission to locate and assist people in distress.

**SAR (Synthetic Aperture Radar)**
SAR is a radar used to create high-resolution images of landscapes, even through clouds or darkness.

**UAV / UAS (Unmanned Aerial Vehicle / System)**
Commonly known as a "drone." A UAS includes the aircraft, the ground control station (GCS), and the communication link.

---

### 🌐 Communications & Protocols

**Broker**
A central hub (like Mosquitto) in an MQTT network that receives all messages from clients and then routes them to the appropriate destination.

**IOT (Internet of Things)**
The Internet of things is a network of interrelated devices that connect and exchange data with other IoT devices and the cloud.

**MQTT (Message Queuing Telemetry Transport)**
A lightweight, "publish-subscribe" network protocol. It is the standard for IoT and real-time telemetry due to its low bandwidth requirements.

**RTSP (Real Time Streaming Protocol)**
A network control protocol designed for controlling streaming media servers (used for high-speed video feeds from cameras).

**Telemetry**
The automated process by which data is collected at remote points and transmitted to receiving equipment for monitoring.

---

### 🅰️ Phonetic Alphabet (ICAO/NATO)
The standard radiotelephony alphabet used to ensure clear communication of asset IDs and coordinates.

| Letter | Word | Letter | Word | Letter | Word |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **A** | Alpha | **J** | Juliet | **S** | Sierra |
| **B** | Bravo | **K** | Kilo | **T** | Tango |
| **C** | Charlie | **L** | Lima | **U** | Uniform |
| **D** | Delta | **M** | Mike | **V** | Victor |
| **E** | Echo | **N** | November | **W** | Whiskey |
| **F** | Foxtrot | **O** | Oscar | **X** | X-ray |
| **G** | Golf | **P** | Papa | **Y** | Yankee |
| **H** | Hotel | **Q** | Quebec | **Z** | Zulu |
| **I** | India | **R** | Romeo | | |

---
*Glossary v2.5 - Finalized for Hornet Hive Tactical Operations.*
