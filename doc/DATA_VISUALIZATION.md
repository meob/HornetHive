# 📊 Data Visualization & Mocking | Hornet Hive

Hornet Hive features a dynamic, real-time data visualization system that renders sparkline charts directly within the hexagonal Honeycomb UI.

---

## 🛠️ Data Generation (`data_mock.py`)

To simulate live data without physical sensors, use the `assets/data_mock.py` script.

### Usage

```bash
python assets/data_mock.py [ID] [OPTIONS]
```

### Key Parameters

- `--type`: Category (e.g., `ENERGY, CARDIAC`, `VITAL`).
- `--metric`: Label (e.g., `HEART_RATE`, `O2_SAT`, `BP_SYS`).
- `--unit`: Measurement unit (e.g., `bpm`, `%`, `mmHg`, `°C`, `mV`).
- `--trend`:
  - `stable`: Small random noise around a value.
  - `sine`: Periodic oscillation.
  - `drift`: Random walk within a range.
  - `heartbeat`: Synthetic ECG (P-QRS-T complex).
- `--freq`: Update frequency (seconds). `0.1` is recommended for ECG pulses.

---

## 🎨 UI Sparklines (Honeycomb OSD)

The frontend uses the HTML5 **Canvas API** to draw real-time charts over the hexagonal assets.

### How it works:

1. **Buffer**: The UI maintains a buffer (`dataHistory`) of the last 50 points received for each asset.
2. **Min-Max Logic**: Automatically calculates the `Range (Min-Max)` and displays it in a discrete font below the main value.
3. **Responsive Scaling**: The chart is automatically scaled to fit the height and width of the hexagon.

---

## 🧪 Simulation Examples

### 1. Stable Temperature

    python assets/data_mock.py P1_TEMP --metric BODY_TEMP --unit °C --min 36.5 --max 37.5 --trend stable

### 2. High-Frequency ECG (Pulse)

    python assets/data_mock.py P1_ECG --metric ECG --trend heartbeat --freq 0.1

### 3. Oxygen Saturation (SpO2)

    python assets/data_mock.py P1_SPO2 --metric O2_SAT --unit % --min 95 --max 99 --trend drift

### 4. CCU (Coronary Care Unit) full example

    docker-compose -f docker-compose.CCU.yml up --build

The result is this:
<img alt="HORNET HIVE CCU example" src="CCU.webp" width="80%">   
---

*Developed for tactical Situational Awareness and medical monitoring research.*
