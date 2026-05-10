# 🔬 Microplastic Detection Dashboard

A real-time microplastic detection system combining a YOLOv8 ML model with an OpenCV
fallback pipeline, Flask web dashboard, and ESP32 IR sensor integration.

---

## ✅ Environment Setup (Conda — Windows)

> **The working Python environment is Conda, NOT the system Python or venv.**

| Item | Value |
|---|---|
| Miniconda path | `D:\Miniconda3` |
| Environment name | `microplastic` |
| Python version | `3.10.20` |
| Python executable | `D:\Miniconda3\envs\microplastic\python.exe` |

### First-time setup (already done — for reference only)

```powershell
# Accept Conda ToS
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/msys2

# Create environment
conda create -n microplastic python=3.10 -y
conda activate microplastic

# Install PyTorch (CPU)
pip install torch torchvision torchaudio

# Install all other dependencies
pip install ultralytics flask flask-socketio opencv-python matplotlib scipy firebase-admin pandas requests pyserial Pillow
```

---

## 🚀 How to Run the Dashboard

### Option 1 — Double-click launcher (easiest)
```
run.bat
```

### Option 2 — PowerShell terminal
```powershell
.\run.ps1
```

### Option 3 — Direct Python command (any terminal)
```powershell
D:\Miniconda3\envs\microplastic\python.exe app.py
```

### Option 4 — VS Code
- Press **F5** → selects "Run app.py (Conda microplastic)"
- Or press **Ctrl+Shift+B** → runs "Start Dashboard" task

> ⚠️ Do NOT use plain `python app.py` unless you have confirmed the active
> Python is `D:\Miniconda3\envs\microplastic\python.exe`.
> The VS Code `.vscode/settings.json` configures this automatically.

Open the dashboard at: **http://localhost:5000**

---

## 📁 Project Structure

```
Microplastic/
├── app.py                          # Flask backend (main entry point)
├── run.bat                         # ← Double-click to start (Windows)
├── run.ps1                         # ← PowerShell launcher
├── requirements.txt                # Python dependencies
├── train_model.py                  # YOLO training pipeline
├── data_log.json                   # Persistent sensor readings
│
├── detection/
│   ├── image_detector.py           # Dual-mode detector (YOLO + OpenCV)
│   ├── thresholds.json             # Calibration values (CLAHE clip, etc.)
│   ├── data.yaml                   # YOLO dataset config
│   ├── analyze_dataset.py          # Dataset statistics
│   ├── auto_label.py               # Auto-labelling pipeline
│   └── microplastic_model/
│       └── weights/
│           └── best.pt             # ✅ Trained YOLOv8 model
│
├── static/                         # CSS, JS, images
├── index.html                      # Main dashboard
├── image_analysis.html             # Image upload & detection UI
├── export.html                     # Data export page
├── settings.html                   # Settings page
├── login.html                      # Login page
│
├── .vscode/
│   ├── settings.json               # Pins Conda interpreter for VS Code
│   ├── launch.json                 # F5 debug config
│   └── tasks.json                  # Ctrl+Shift+B task config
│
└── esp32_code/                     # Arduino firmware for IR sensor
```

---

## 🤖 Detection Pipeline

### YOLO mode (primary)
- Model: `detection/microplastic_model/weights/best.pt` (YOLOv8n, 6.2 MB)
- Trained with `python train_model.py --yolo`
- Confidence threshold: 0.35

### OpenCV fallback (automatic if YOLO unavailable)
- Petri dish rim masking via HoughCircles
- Self-calibrating brightness threshold (`mean + 30`, clamped 80–200)
- CLAHE contrast enhancement
- Saturation channel OR-combined for coloured fibres
- Contour classification → Fragment / Fiber / Film

### Water quality thresholds
| Particles | Status |
|---|---|
| 0 | Clean |
| 1–5 | Low |
| 6–20 | Moderate |
| 21–50 | High |
| 51+ | Severe |

---

## 🔌 ESP32 Integration

The ESP32 IR sensor posts to:
- `POST /api/sensor-data` → `{"count": 5, "state": "PARTICLE PRESENT"}`
- `GET  /api/sensor-data` → returns latest cached snapshot

Legacy ADC format also supported via `POST /data`.

---

## 📦 Key Package Versions (Conda env)

| Package | Version |
|---|---|
| Python | 3.10.20 |
| PyTorch | 2.5.1 (CPU) |
| Ultralytics (YOLO) | 8.4.46 |
| Flask | 3.1.3 |
| OpenCV | 4.13.0 |
| NumPy | 2.0.1 |
