import cv2
import numpy as np
import requests
import time
import json
from datetime import datetime

# ── Config ─────────────────────────────────────
PHONE_STREAM = "http://192.168.x.x:8080/video"  # edit your IP
FLASK_URL    = "http://localhost:5001/camera_data"
PIXEL_TO_UM  = 2.5   # calibrate: measure known object in pixels

# ── Particle Detection ──────────────────────────
def detect_particles(frame):
    gray    = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Adaptive threshold works better than fixed for varying lighting
    thresh  = cv2.adaptiveThreshold(
        blurred, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 11, 3
    )

    # Remove tiny noise
    kernel  = np.ones((2, 2), np.uint8)
    cleaned = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)

    contours, _ = cv2.findContours(
        cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    particles = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if 15 < area < 8000:              # ignore dust noise + large debris
            diameter_px = np.sqrt(4 * area / np.pi)
            diameter_um = diameter_px * PIXEL_TO_UM

            if diameter_um > 10:          # only particles > 10µm
                x, y, w, h = cv2.boundingRect(cnt)
                particles.append({
                    "diameter_um": round(diameter_um, 1),
                    "area_px":     round(area, 1),
                    "x": x, "y": y
                })

                # Draw on frame
                cv2.drawContours(frame, [cnt], -1, (0, 255, 0), 2)
                cv2.putText(frame, f"{diameter_um:.0f}µm",
                            (x, y - 5),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.4, (0, 255, 0), 1)

    return frame, particles

# ── Size Classification ─────────────────────────
def classify(particles):
    if not particles:
        return "Good", 0
    sizes = [p["diameter_um"] for p in particles]
    count = len(particles)
    avg   = np.mean(sizes)

    if count < 5:   return "Good",         count
    if count < 20:  return "Moderate",     count
    return              "Contaminated", count

# ── Send to Flask Dashboard ─────────────────────
def send_to_flask(particles, status, count):
    try:
        payload = {
            "cam_particles": count,
            "cam_status":    status,
            "avg_size":      round(np.mean([p["diameter_um"] 
                             for p in particles]), 1) if particles else 0,
            "timestamp":     datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        requests.post(FLASK_URL, json=payload, timeout=1)
    except:
        pass   # don't crash if flask is down

# ── Main Loop ───────────────────────────────────
def main():
    cap = cv2.VideoCapture(PHONE_STREAM)
    
    if not cap.isOpened():
        print("Cannot open stream — check IP and that IP Webcam is running")
        return

    print("Stream opened. Press Q to quit, S to save frame.")
    last_send = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Frame lost, retrying...")
            time.sleep(0.5)
            continue

        annotated, particles = detect_particles(frame.copy())
        status, count        = classify(particles)

        # Overlay info on frame
        cv2.putText(annotated,
                    f"Particles: {count} | Status: {status}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                    0.8, (0, 200, 255), 2)

        cv2.imshow("Microplastic Detection", annotated)

        # Send to Flask every 3 seconds
        if time.time() - last_send > 3:
            send_to_flask(particles, status, count)
            last_send = time.time()
            print(f"Sent — Count: {count}, Status: {status}")

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        if key == ord('s'):
            fname = f"sample_{datetime.now().strftime('%H%M%S')}.jpg"
            cv2.imwrite(fname, annotated)
            print(f"Saved {fname}")

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()