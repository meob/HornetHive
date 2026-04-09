# 🛸 UAV Assets Documentation (C4I Simulation)

This document provides a detailed overview of the Unmanned Aerial Vehicles (UAVs) integrated into the 
**Hornet Hive** C4I simulation system. Each asset is now defined by its **Capability**, which determines its role in the OODA loop.
Drones are defined in the /assets/drone_models.json file.

---

## 1. Recreational & Dual-Use (Low-Altitude ISR)

Commercial-off-the-shelf (COTS) drones used for training or rapid tactical reconnaissance.

| Model | Type | Origin | Capability | Description |
| --- | --- | --- | --- | --- |
| **TELLO** | Rotary | China | None | Educational micro-drone. Ideal for indoor swarm logic testing. |
| **MINI 4** | Rotary | China | 📷 SENSOR | Ultralight asset, providing high-quality video with low visual signature. |
| **HORNET** | Rotary | AI | 📷 SENSOR | High-performance **fictional drone (no battery drain)**. |

---

## 2. Professional & SAR (Search and Rescue)

Industrial-grade assets equipped with advanced payloads for emergency response and lifesaving actions.

*   **AR5 LIFE RAY:** Specialized maritime SAR fixed-wing  (Tekever). 
    *   **Capability:** 🛟 **RESCUE_TUBE**
    *   **Role:** Long-range search and automatic deployment of life rafts in open sea.
*   **MAVIC 3 T:** Specialized rotary unit with a $640 \times 512$ thermal sensor.
    *   **Capability:** 📷 **SENSOR**
    *   **Role:** Heat signature detection and night search operations.
*   **MATRICE 350 RTK:** Heavy-duty industrial platform.
    *   **Capability:** ⛑️ **MEDKIT**
    *   **Role:** Extreme environment stability and medical supply delivery.

---

## 3. Logistics & Delivery

UAVs optimized for autonomous transport and precise waypoint navigation.

*   **ZIPLINE:** Autonomous medical delivery fixed-wing drone.
    *   **Capability:** ⛑️ **MEDKIT**
*   **WING DRONE:** Alphabet Wing’s urban delivery solution.
    *   **Capability:** 📷 **SENSOR**
*   **AGRAS T40:** Heavy-payload agricultural DJI drone.
    *   **Capability:** 📷 **SENSOR**

---

## 4. Military Tactical (Combat & ISR)

Combat-proven assets used for direct troop support and precision engagement.

| Model | Behavior | Capability | Description |
| --- | --- | --- | --- |
| **R18** | Standard | 🔥 STRIKE | Ukraine (Aerorozvidka) drone for night attacks. |
| **FALCO EVO** | Standard | 🔥 STRIKE | Italian (Leonardo) for persistent tactical surveillance. |
| **BAYRAKTAR TB2** | Standard | 🔥 STRIKE | Battle-proven MALE UAV for ISTAR and strike missions. |
| **ORLAN 10** | Standard | 📷 SENSOR | Tactical UAV used for artillery fire correction and EW. |
| **SHAHED-136** | Kamikaze | 🔥 STRIKE | Loitering munition designed for swarm saturation. |
| **SWITCHBLADE 300** | Kamikaze | 🔥 STRIKE | Lightweight loitering munition for surgical precision strikes. |
| **EAGLE** | Standard | 📷 SENSOR | High-performance **fictional drone (no battery drain)**. |
| **KESTREL** | Standard | 🔥 STRIKE | High-performance **fictional drone (no battery drain)**. |

---

## 5. Military Strategic (HALE/MALE)

High-altitude assets providing persistent wide-area surveillance and kinetic capabilities.

*   **MQ 9 REAPER:**The quintessential hunter-killer UAV (USA). Backbone of long-range ISR and precision strike operations.
    *   **Capability:** 🔥 **STRIKE**

*   **HERON TP:** All-weather strategic UAV for deep intelligence missions (Israel).
    *   **Capability:** 🔥 **STRIKE**

*   **MQ 4C TRITON / RQ 4 GLOBAL HAWK:** HALE platforms for persistent wide-area maritime and land surveillance (USA).
    *   **Capability:** 📷 **SENSOR**

---

## ⚙️ Mission Logic: Capabilities

The simulation engine uses the `capability` field from `drone_models.json` to enforce mission rules:

1.  **Detection**: Only drones with a capability (eg. `SENSOR`, `MEDKIT`) can find a target.
2.  **Action**: To complete a mission, a drone must perform an action matching the target's requirements:
    *   **SAR (Sea)**: Requires `RESCUE_TUBE` 🛟
    *   **SAR (Mountain)**: Requires `MEDKIT` ⛑️
    *   **DEFENSE**: Requires `SENSOR` 📷
    *   **MILITARY**: Requires `STRIKE` 🔥
3.  **Proximity**: Actions must be performed within **50 meters** of the detected target position.
