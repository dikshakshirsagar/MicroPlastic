# 💧 MicroPlastic Detection in Water

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.x-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.x-5C3EE8?logo=opencv&logoColor=white)](https://opencv.org)
[![TensorFlow](https://img.shields.io/badge/TensorFlow-2.x-FF6F00?logo=tensorflow&logoColor=white)](https://tensorflow.org)
[![Firebase](https://img.shields.io/badge/Firebase-Auth-FFCA28?logo=firebase&logoColor=black)](https://firebase.google.com)
[![ESP32](https://img.shields.io/badge/Hardware-ESP32-E7352C?logo=espressif&logoColor=white)](https://espressif.com)


**MicroPlastic Detection in Water** is a low-cost, portable, real-time system that detects and classifies microplastic particles in water samples using laser-based optical sensing, embedded electronics (ESP32), and custom-trained machine learning models — all connected to a live web dashboard.

---

## 📌 Table of Contents

- [Overview](#-overview)
- [Problem Statement](#-problem-statement)
- [System Architecture](#-system-architecture)
- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Hardware Components](#-hardware-components)
- [ML Pipeline](#-ml-pipeline)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
  - [Prerequisites](#prerequisites)
  - [Environment Variables](#environment-variables)
  - [Backend Setup](#backend-setup)
  - [Frontend Setup](#frontend-setup)
  - [ESP32 Firmware](#esp32-firmware)
- [Usage](#-usage)
- [API Reference](#-api-reference)
- [Detection Pipeline](#-detection-pipeline)
- [Future Scope](#-future-scope)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🌊 Overview

Microplastics are tiny plastic fragments smaller than 5mm found in drinking water, oceans, and even human blood. Traditional lab-based detection is expensive, slow, and inaccessible for field use. This project builds an **affordable, intelligent, IoT-connected detection system** that works anywhere — no laboratory required.

The system pumps a water sample through an optical chamber, uses a **red laser + UV LED** to scatter and fluoresce particles, captures pulses via a **90° photodetector**, extracts features on an **ESP32**, classifies particles with a **TensorFlow ML model**, and displays everything on a **real-time web dashboard**.

---

## ⚠️ Problem Statement

- Microplastics are detected in **drinking water, marine ecosystems, and human blood**
- Existing lab methods require **expensive equipment and specialized personnel**
- There is an urgent need for **portable, real-time, low-cost monitoring tools**
- Current solutions are **not scalable** for widespread environmental surveillance

This project bridges that gap with an end-to-end embedded + AI solution that anyone can deploy in the field.

---

## 🏗️ System Architecture

```
Water Sample
     │
     ▼
┌──────────────────────────┐
│   Flow & Optics Chamber  │  ← Red Laser + UV LED + 90° Photodetector
└────────────┬─────────────┘
             │ Analog Pulse Signal
             ▼
┌──────────────────────────┐
│   ESP32 Microcontroller  │  ← ADC Sampling + Feature Extraction + Wi-Fi
└────────────┬─────────────┘
             │ Features (amplitude, width, area, shape)
             ▼
┌──────────────────────────┐
│   Flask Backend           │  ← REST API + Image Processing (OpenCV)
│   (app.py / detector.py)  │
└────────────┬─────────────┘
             │
     ┌───────┴────────┐
     │                │
     ▼                ▼
┌─────────┐    ┌────────────┐
│  ML     │    │  Firebase  │
│  Model  │    │  Auth      │
│  (TF)   │    │            │
└────┬────┘    └────────────┘
     │
     ▼
┌──────────────────────────┐
│   Web Dashboard           │  ← Real-time Charts + Detection Results
│   (HTML + CSS + JS)       │
└──────────────────────────┘
```

---

## ✨ Features

**Optical Sensing**
- Red laser generates light scattering through the water sample flow path
- Optional UV LED excites fluorescence in plastic particles for improved accuracy
- Photodetector placed at 90° captures scattered and fluorescent pulses precisely

**Embedded Intelligence**
- ESP32 performs real-time ADC sampling of photodetector output
- On-device feature extraction: pulse amplitude, width, area, and shape
- Wi-Fi connectivity streams extracted features directly to the backend

**ML Classification**
- Custom-trained TensorFlow model classifies particle type and concentration
- OpenCV-based image processing pipeline for camera-captured samples
- Confidence scoring for each detection result

**Real-Time Dashboard**
- Live particle count graph and concentration display (particles/L)
- Detection history log with timestamps
- Clean dark-themed UI with interactive charts

**User Authentication**
- Firebase-powered login with Email/Password and Google Sign-In
- Secure session management per user

---

## 🛠️ Tech Stack

### Frontend
| Technology | Purpose |
|---|---|
| **HTML** | Page structure — dashboard, login, results pages |
| **CSS** | Dark-theme UI, responsive layout, button styles |
| **JavaScript** | Interactivity, live charts, Firebase auth, API calls |

### Backend
| Technology | Purpose |
|---|---|
| **Python** | Core server language |
| **Flask** | REST API server, routing, request handling |
| **OpenCV** | Image-based microplastic detection (`detector.py`) |

### ML & AI
| Technology | Purpose |
|---|---|
| **TensorFlow** | Particle classification model training & inference |
| **OpenCV** | Computer vision preprocessing pipeline |

### Hardware & Firmware
| Technology | Purpose |
|---|---|
| **ESP32 (Arduino/C)** | ADC sampling, feature extraction, Wi-Fi transmission |
| **Buck Converters** | Stable power regulation for all hardware components |

### Database & Auth
| Technology | Purpose |
|---|---|
| **Firebase Authentication** | Email & Google login, secure user sessions |

---

## 🔩 Hardware Components

| Component | Role |
|---|---|
| ESP32 Microcontroller | ADC sampling, feature extraction, Wi-Fi data transmission |
| Red Laser Module | Generates scattering light path through water chamber |
| UV LED (optional) | Excites fluorescence in plastic particles |
| Photodetector (90°) | Captures scattered and fluorescent light pulses |
| Transparent Flow Chamber | Controlled water sample flow through the light path |
| Buck Converters | Power regulation for laser, LED, ESP32, and photodetector |

---

## 🧠 ML Pipeline

```
Photodetector Pulse Signal
           │
           ▼
  Feature Extraction (ESP32)
    ├── Pulse Amplitude
    ├── Pulse Width
    ├── Pulse Area
    └── Pulse Shape
           │
           ▼
  Custom ML Model (TensorFlow)
    ├── Microplastic vs. Non-plastic Classification
    ├── Particle Size Estimation
    └── Concentration Calculation
           │
           ▼
  Results → Flask API → Web Dashboard
```

Each particle interaction generates a pulse. Features from that pulse are classified by the trained model to distinguish microplastics from other suspended matter in water.

---

## 📁 Project Structure

```
MicroPlastic/
│
├── frontend/
│   ├── index.html              # Main dashboard page
│   ├── login.html              # Login / signup page
│   ├── style.css               # Dark theme UI and layout styling
│   └── app.js                  # Charts, Firebase auth, API calls
│
├── backend/
│   ├── app.py                  # Flask server & REST API endpoints
│   └── detector.py             # OpenCV microplastic detection logic
│
├── ml_model/
│   ├── model.h5                # Trained TensorFlow classification model
│   └── train.py                # Model training script
│
├── esp32/
│   └── main.ino                # ESP32 firmware: ADC + feature extraction + Wi-Fi
│
├── requirements.txt            # Python dependencies
└── README.md
```

---

## ⚙️ Getting Started

### Prerequisites

- **Python 3.10+**
- **Node.js 18+** (optional, for serving frontend)
- A Firebase project with Authentication enabled
- ESP32 board + Arduino IDE (for hardware deployment)

### Environment Variables

Create a `.env` file inside the `backend/` directory:

```env
FLASK_ENV=development
FLASK_PORT=5000
FIREBASE_API_KEY=your_firebase_api_key_here
```

> **Note:** Firebase config for the frontend goes inside `app.js` under the `firebaseConfig` object.

### Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # Linux/macOS
# venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt

# Start the Flask server
python app.py
```

Backend runs at **http://localhost:5000**

### Frontend Setup

Open `frontend/index.html` directly in your browser, or serve it:

```bash
# Quick static server (Python)
cd frontend
python -m http.server 3000
```

Frontend runs at **http://localhost:3000**

### ESP32 Firmware

1. Open `esp32/main.ino` in **Arduino IDE**
2. Install **ESP32 board support** via Board Manager
3. Install required libraries: `WiFi.h`, `HTTPClient.h`
4. Update these values in the sketch:
   ```cpp
   const char* ssid     = "YOUR_WIFI_SSID";
   const char* password = "YOUR_WIFI_PASSWORD";
   const char* serverURL = "http://<YOUR_PC_IP>:5000/data";
   ```
5. Flash to your ESP32 board

---

## 🖥️ Usage

### 1. Live Dashboard
View **real-time particle counts** and **microplastic concentration** (particles/L) as data streams in from the ESP32. A live chart updates with every new detection event.

### 2. Detection Log
Browse the **history of all detected particles** with timestamps, classification labels, and confidence scores.

### 3. Image Analysis
Upload a **microscope image** of a water sample. The backend runs it through the OpenCV + TensorFlow pipeline and returns detected microplastic regions highlighted on the image.

### 4. Login / Signup
Authenticate via **Email or Google** using Firebase. Each user's detection history is stored securely under their account.

---

## 📡 API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check — confirms server is running |
| `POST` | `/data` | Receive ESP32 feature data and run ML classification |
| `POST` | `/detect` | Analyze an uploaded water sample image via OpenCV |
| `GET` | `/results` | Fetch all past detection results |
| `GET` | `/concentration` | Get current microplastic concentration (particles/L) |
| `DELETE` | `/results` | Clear all detection history |

Full interactive API docs available at **http://localhost:5000/docs** when backend is running.

---

## 🔬 Detection Pipeline

The end-to-end flow from hardware signal to dashboard update:

```
ESP32 ADC Samples Photodetector Signal
               │
               ▼
      Extract Features (on-device)
               │
               ▼
      POST to Flask /data endpoint
               │
               ▼
      TensorFlow Model Inference
        ├── Microplastic? (Yes / No)
        ├── Particle size estimate
        └── Confidence score
               │
               ▼
      Store result + Update concentration
               │
               ▼
      Frontend polls /results
               │
               ▼
      Live Dashboard Update
```

---

## 🚀 Future Scope

- [ ] Deploy TFLite model directly on ESP32 (fully offline inference)
- [ ] GPS tagging for geographic water quality mapping
- [ ] Multi-wavelength laser for improved particle type classification
- [ ] Mobile app (Android/iOS) for remote monitoring
- [ ] Cloud database (Firebase Firestore) for large-scale data storage
- [ ] Automated PDF/CSV report generation for regulatory submissions
- [ ] Multi-sensor array for simultaneous multi-point water sampling

---

## 🤝 Contributing

Contributions are welcome! Here's how to get started:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/your-feature`)
3. **Commit** your changes (`git commit -m 'Add your feature'`)
4. **Push** to the branch (`git push origin feature/your-feature`)
5. **Open** a Pull Request

