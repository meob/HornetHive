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
- `--type`: Category (e.g., `CARDIAC`, `ENERGY`, `VITAL`).
- `--metric`: Label (e.g., `HEART_RATE`, `O2_SAT`, `BP_SYS`).
- `--unit`: Measurement unit (e.g., `bpm`, `%`, `mmHg`, `°C`, `mV`).
- `--trend`:
  - `stable`: Small random noise around a value.
  - `sine`: Periodic oscillation.
  - `drift`: Random walk within a range.
  - `heartbeat`: **Synthetic ECG (P-QRS-T complex)**.
- `--freq`: Update frequency (seconds). `0.1` is recommended for ECG pulses.

---

## 🎨 UI Sparklines (Honeycomb OSD)
The frontend uses the HTML5 **Canvas API** to draw real-time charts over the hexagonal assets.

### How it works:
1. **Buffer**: The UI mantiene un buffer (`dataHistory`) degli ultimi 50 punti ricevuti per ogni asset.
2. **Min-Max Logic**: Calcola automaticamente il `Range (Min-Max)` e lo visualizza in un font discreto sotto il valore principale.
3. **Responsive Scaling**: Il grafico viene scalato automaticamente per adattarsi all'altezza e larghezza dell'esagono.

---

## 🧪 Simulation Examples

### 1. Stable Temperature
```bash
python assets/data_mock.py P1_TEMP --metric BODY_TEMP --unit °C --min 36.5 --max 37.5 --trend stable
```

### 2. High-Frequency ECG (Pulse)
```bash
python assets/data_mock.py P1_ECG --metric ECG --trend heartbeat --freq 0.1
```

### 3. Oxygen Saturation (SpO2)
```bash
python assets/data_mock.py P1_SPO2 --metric O2_SAT --unit % --min 95 --max 99 --trend drift
```

---
*Developed for tactical Situational Awareness and medical monitoring research.*
