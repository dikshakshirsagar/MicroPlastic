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
│
├── .vscode/                          # VS Code workspace settings
│   ├── launch.json                   # Debug launch configuration
│   ├── settings.json                 # Editor settings
│   └── tasks.json                    # Task runner configuration
│
├── detection/                        # Core detection module
│   ├── microplastic_model/           # Trained ML model files
│   ├── __init__.py                   # Package initializer
│   ├── analyze_dataset.py            # Dataset analysis script
│   ├── auto_label.py                 # Auto-labelling for training data
│   ├── data.yaml                     # Dataset config for YOLOv8 training
│   ├── image_detector.py             # Image-based detection logic
│   ├── particle_analysis.py          # Particle feature analysis
│   └── thresholds.json               # Detection threshold configuration
│
├── esp32_code/                       # ESP32 hardware firmware
│   └── esp32_sensor.ino              # ADC sampling + feature extraction + Wi-Fi
│
├── static/                           # Frontend static assets
│   ├── auth.css                      # Authentication page styles
│   ├── auth.js                       # Firebase authentication logic
│   ├── script.js                     # Dashboard interactivity & API calls
│   └── style.css                     # Main dark-theme UI styles
│
├── .gitignore                        # Git ignore rules
├── app.py                            # Flask server & all REST API endpoints
├── export.html                       # Exported detection report (HTML)
├── image_analysis.html               # Image analysis dashboard page
├── index.html                        # Main live dashboard page
├── login.html                        # Login / signup page
├── README.md                         # Project documentation
├── requirements.txt                  # Python dependencies
├── run.bat                           # Windows startup script
├── run.ps1                           # PowerShell startup script
├── settings.html                     # User settings page
├── test_sender.py                    # ESP32 data simulation & testing script
├── train_model.py                    # ML model training script
└── yolov8n.pt                        # Pre-trained YOLOv8 nano model weights
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
