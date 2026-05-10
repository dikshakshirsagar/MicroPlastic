"""
Microplastic Detection Dashboard — Flask Backend
=================================================
Routes:
  GET  /                    → Dashboard
  GET  /image-analysis      → Image analysis page
  GET  /export              → Data export page
  GET  /settings            → Settings page
  GET  /login               → Login page

  POST /data                → Legacy ESP32 sensor data (raw ADC)
  GET  /data                → Latest legacy data (polled by dashboard)
  GET  /history             → Full reading history

  POST /api/sensor-data     → New ESP32 IR sensor data (particle count)
  GET  /api/sensor-data     → Latest IR sensor snapshot

  POST /analyze-image       → OpenCV / YOLO image analysis
  GET  /export/json         → Download history JSON
  GET  /export/csv          → Download history CSV

Run:  python app.py
"""

from flask import Flask, request, jsonify, send_file, Response
from datetime import datetime
import json
import os

from detection.image_detector import MicroplasticDetector

app = Flask(__name__, static_folder='static')

# ── Image Analysis ────────────────────────────────────────────────
detector = MicroplasticDetector()

# ── In-memory data stores ─────────────────────────────────────────
latest_data = {
    "particles": 0,
    "size": 0,
    "status": "Good",
    "timestamp": None
}

# ── NEW: IR sensor cache (populated by ESP32 POST /api/sensor-data) ──
sensor_cache = {
    "particle_count": 0,
    "state":          "CLEAR",
    "water_quality":  "Good",
    "timestamp":      None,
    "last_seen":      None   # ISO string used for online/offline detection
}

history   = []        # stores last 500 readings
DATA_FILE = "data_log.json"
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))


# ── Serve Frontend Pages ──────────────────────────────────────────
@app.route('/')
def index():
    return send_file(os.path.join(BASE_DIR, 'index.html'))


@app.route('/login')
def login():
    return send_file(os.path.join(BASE_DIR, 'login.html'))


@app.route('/image-analysis')
def image_analysis():
    return send_file(os.path.join(BASE_DIR, 'image_analysis.html'))


@app.route('/export')
def export_page():
    return send_file(os.path.join(BASE_DIR, 'export.html'))


@app.route('/settings')
def settings_page():
    return send_file(os.path.join(BASE_DIR, 'settings.html'))


# ── API: Receive data from ESP32 (legacy ADC format) ─────────────
@app.route('/data', methods=['POST'])
def receive_data():
    """
    Legacy ESP32 sends:
      POST /data
      {"particles": 45, "size": 20, "status": "Moderate"}
    """
    try:
        incoming  = request.get_json(force=True)
        particles = int(incoming.get('particles', 0))
        size      = int(incoming.get('size', 0))
        status    = incoming.get('status', 'Good')

        if particles > 100:
            status = 'Contaminated'
        elif particles > 50:
            status = 'Moderate'

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        latest_data['particles'] = particles
        latest_data['size']      = size
        latest_data['status']    = status
        latest_data['timestamp'] = timestamp

        record = {
            "particles": particles,
            "size":      size,
            "status":    status,
            "timestamp": timestamp
        }
        history.append(record)
        if len(history) > 500:
            history.pop(0)

        save_to_file(record)

        print(f"[{timestamp}]  Particles: {particles}  |  Size: {size}µm  |  Status: {status}")
        return jsonify({"message": "Data received", "data": record}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ── API: Get latest legacy data (polled by frontend) ─────────────
@app.route('/data', methods=['GET'])
def get_data():
    return jsonify(latest_data), 200


# ── API: Get full history ─────────────────────────────────────────
@app.route('/history', methods=['GET'])
def get_history():
    return jsonify(history), 200


# ═══════════════════════════════════════════════════════════════════
# NEW: ESP32 IR Sensor endpoints
# ═══════════════════════════════════════════════════════════════════

def _calculate_quality(count: int) -> str:
    """Map raw particle count to water-quality label."""
    if count == 0:    return "Good"
    if count <= 5:    return "Moderate"
    if count <= 15:   return "Poor"
    return                   "Contaminated"


@app.route('/api/sensor-data', methods=['POST'])
def receive_sensor_data():
    """
    ESP32 IR sensor sends:
      POST /api/sensor-data
      {"count": 5, "state": "PARTICLE PRESENT"}
    """
    try:
        data  = request.get_json(force=True)
        count = int(data.get('count', 0))
        state = str(data.get('state', 'CLEAR')).upper()
        now   = datetime.now()

        quality = _calculate_quality(count)

        sensor_cache['particle_count'] = count
        sensor_cache['state']          = state
        sensor_cache['water_quality']  = quality
        sensor_cache['timestamp']      = now.strftime('%Y-%m-%d %H:%M:%S')
        sensor_cache['last_seen']      = now.isoformat()

        # Also mirror into the legacy data store so history table updates
        latest_data['particles'] = count
        latest_data['status']    = quality
        latest_data['timestamp'] = sensor_cache['timestamp']

        record = {
            "particles": count,
            "size":      0,
            "status":    quality,
            "timestamp": sensor_cache['timestamp'],
            "source":    "ir_sensor",
            "state":     state,
        }
        history.append(record)
        if len(history) > 500:
            history.pop(0)
        save_to_file(record)

        print(f"[IR Sensor] Count: {count} | State: {state} | Quality: {quality}")
        return jsonify({"message": "Sensor data received", "quality": quality}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route('/api/sensor-data', methods=['GET'])
def get_sensor_data():
    """Return the latest cached IR sensor snapshot."""
    return jsonify(sensor_cache), 200


# ── API: Export history as JSON ───────────────────────────────────
@app.route('/export/json', methods=['GET'])
def export_json():
    """Return all detection history as a downloadable JSON file."""
    all_data = _load_all_data()
    return jsonify(all_data), 200


# ── API: Export history as CSV ────────────────────────────────────
@app.route('/export/csv', methods=['GET'])
def export_csv():
    """Return all detection history as a CSV string."""
    all_data = _load_all_data()
    lines = ["Timestamp,Particles,Size (µm),Status"]
    for r in all_data:
        lines.append(
            f"{r.get('timestamp','')},{r.get('particles',0)},"
            f"{r.get('size',0)},{r.get('status','')}"
        )
    csv_content = "\n".join(lines)
    return Response(
        csv_content,
        mimetype='text/csv',
        headers={"Content-Disposition": "attachment; filename=microplastic_data.csv"}
    )


# ── Persist to JSON file ──────────────────────────────────────────
def save_to_file(record):
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
        else:
            data = []
        data.append(record)
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save to file — {e}")


def _load_all_data():
    """Load all persisted + in-memory records."""
    file_data = []
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                file_data = json.load(f)
        except Exception:
            pass
    return file_data if file_data else history


# ── API: Analyze uploaded image ───────────────────────────────────
@app.route('/analyze-image', methods=['POST'])
def analyze_image():
    """
    Accepts multipart/form-data POST with field 'image'.
    Returns JSON with detection results + base64 annotated image.
    Optional form field 'settings' (JSON string) for tuning.
    """
    f = request.files.get('image')
    if not f:
        return jsonify({"success": False, "error": "No image provided"}), 400

    if f.filename == '':
        return jsonify({"success": False, "error": "Empty filename"}), 400

    allowed = {'jpg', 'jpeg', 'png', 'bmp', 'tiff', 'tif'}
    ext = f.filename.rsplit('.', 1)[-1].lower() if '.' in f.filename else ''
    if ext not in allowed:
        return jsonify({"success": False,
                        "error": f"Unsupported format '{ext}'. Use JPG/PNG/BMP/TIFF."}), 415

    # Parse optional settings JSON
    settings = {}
    settings_raw = request.form.get('settings', '')
    if settings_raw:
        try:
            settings = json.loads(settings_raw)
        except Exception:
            pass

    try:
        raw = detector.analyze(f.read(), settings=settings)

        if "error" in raw and "stats" not in raw:
            return jsonify({"success": False, "error": raw["error"]}), 422

        stats        = raw.get("stats", {})
        particles_in = raw.get("particles", [])

        # Convert size_mm → size_um for the UI (×1000)
        particles_out = [{
            "id":          p.get("id"),
            "size_um":     round(p.get("size_mm", 0) * 1000, 1),
            "shape":       p.get("shape"),
            "circularity": p.get("circularity"),
            "area_px":     p.get("area_px"),
        } for p in particles_in]

        # Save scan to history
        scan_record = {
            "timestamp":  stats.get("timestamp", datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            "particles":  stats.get("total", 0),
            "size":       round(stats.get("avg_size", 0) * 1000, 1),
            "status":     stats.get("status", "Clean"),
            "source":     "image_analysis",
            "dominant":   stats.get("dominant", "—"),
        }
        history.append(scan_record)
        if len(history) > 500:
            history.pop(0)
        save_to_file(scan_record)

        return jsonify({
            "success":         True,
            "total_particles": stats.get("total", 0),
            "avg_size_um":     round(stats.get("avg_size", 0) * 1000, 1),
            "min_size_um":     round(stats.get("min_size", 0) * 1000, 1),
            "max_size_um":     round(stats.get("max_size", 0) * 1000, 1),
            "dominant_shape":  stats.get("dominant", "—"),
            "status":          stats.get("status", "Clean"),
            "model_used":      stats.get("model", "opencv"),
            "shape_counts": {
                "Fragment": stats.get("fragments", 0),
                "Fiber":    stats.get("fibers",    0),
                "Film":     stats.get("films",     0),
            },
            "particles":       particles_out,
            "annotated_image": raw.get("annotated_image", ""),
            "analyzed_at":     stats.get("timestamp", ""),
        }), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


# ── Camera Data ────────────────────────────────────────────────────
camera_data = {}


@app.route('/camera_data', methods=['POST'])
def receive_camera():
    global camera_data
    camera_data = request.get_json(force=True)
    return jsonify({"status": "ok"})


@app.route('/camera_data', methods=['GET'])
def get_camera():
    return jsonify(camera_data)


# ── Run Server ─────────────────────────────────────────────────────
if __name__ == '__main__':
    print("\n" + "=" * 55)
    print("  µPlastic Detection Dashboard")
    print("  Open in browser: http://localhost:5000")
    print("=" * 55 + "\n")
    app.run(host='0.0.0.0', port=5000, debug=True)
