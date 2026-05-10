"""
image_detector.py  — µPlastic Detection System
================================================
Dual-mode detector:

  1. YOLO mode   — loads detection/microplastic_model/weights/best.pt
                   (created by train_model.py --yolo) when available.
                   Uses ultralytics inside a try/except so the app
                   keeps running even if torch/ultralytics is broken.

  2. OpenCV mode — self-calibrating bright-spot detector (no ML).
                   Always available, guaranteed to run.

Pipeline (OpenCV fallback)
--------------------------
  A — Petri-dish masking  : HoughCircles, 85 % radius → exclude rim
  B — CLAHE enhancement   : improve contrast in very dark images
  C — Self-calibrating threshold: mean_inside_dish + 30
  D — Saturation OR-combined for coloured particles (red/blue fibres)
  E — Contour filtering   : area 6 px²–2 % image, solidity ≥ 0.25
  F — Fiber / Fragment / Film classification
  G — Water-quality thresholds
"""

import cv2
import math
import numpy as np
import base64
import os
import json
from datetime import datetime

# ── Model path (written by train_model.py --yolo) ─────────────────────
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "detection", "microplastic_model", "weights", "best.pt")
THRESH_JSON = os.path.join(BASE_DIR, "detection", "thresholds.json")


# ══════════════════════════════════════════════════════════════════════
# Standalone detect() — used by train_model.py tests / CLI callers
# ══════════════════════════════════════════════════════════════════════

def detect(image_path: str) -> list:
    """
    Detect microplastic particles in an image file.

    Returns a list of dicts with keys:
      x, y, w, h, area, circularity, shape, size_mm, confidence
    """
    img = cv2.imread(image_path)
    if img is None:
        return []

    # ── Try YOLO model first if available ────────────────────────────
    if os.path.exists(MODEL_PATH):
        try:
            from ultralytics import YOLO
            model = YOLO(MODEL_PATH)
            results = model(image_path, conf=0.35, verbose=False)
            particles = []
            for box in results[0].boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                w  = x2 - x1
                h  = y2 - y1
                area   = w * h
                aspect = max(w, h) / (min(w, h) + 1e-5)
                perim  = 2 * (w + h)
                circ   = (4 * math.pi * area) / (perim ** 2 + 1e-5)

                if aspect >= 2.5 and circ < 0.5:
                    shape = "Fiber"
                elif circ >= 0.5:
                    shape = "Fragment"
                else:
                    shape = "Film"

                particles.append({
                    "x":           x1,
                    "y":           y1,
                    "w":           w,
                    "h":           h,
                    "area":        area,
                    "circularity": round(circ, 3),
                    "shape":       shape,
                    "size_mm":     round(math.sqrt(area) * 0.05, 3),
                    "confidence":  round(float(box.conf), 2),
                })
            return particles
        except Exception as e:
            print(f"[Detector] YOLO failed, using OpenCV fallback: {e}")

    # ── OpenCV fallback ───────────────────────────────────────────────
    return _detect_opencv_list(img)


def _detect_opencv_list(img) -> list:
    """Run the OpenCV pipeline and return a plain list (no annotated image)."""
    h, w     = img.shape[:2]
    img_area = h * w
    gray     = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    mask = _make_dish_mask(gray, h, w)

    # CLAHE enhancement
    clip  = _load_clahe_clip()
    clahe = cv2.createCLAHE(clipLimit=clip, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    masked_enh = cv2.bitwise_and(enhanced, enhanced, mask=mask)

    # Self-calibrating threshold
    mean_val = float(cv2.mean(gray, mask=mask)[0])
    thr      = int(mean_val + 30)
    thr      = max(thr, 80)
    thr      = min(thr, 200)
    _, binary = cv2.threshold(masked_enh, thr, 255, cv2.THRESH_BINARY)

    kernel  = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    cleaned = cv2.morphologyEx(binary, cv2.MORPH_OPEN,  kernel, iterations=1)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel, iterations=1)

    contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    particles = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 6 or area > img_area * 0.02:
            continue
        x, y, bw, bh = cv2.boundingRect(cnt)
        if x <= 2 or y <= 2 or x + bw >= w - 2 or y + bh >= h - 2:
            continue
        hull_area = cv2.contourArea(cv2.convexHull(cnt))
        if hull_area < 1 or area / hull_area < 0.25:
            continue

        perimeter   = cv2.arcLength(cnt, True)
        circularity = (4 * math.pi * area) / (perimeter ** 2 + 1e-5)
        aspect      = float(max(bw, bh)) / (min(bw, bh) + 1e-5)
        shape, _    = _classify(circularity, aspect)

        particles.append({
            "x":           x,
            "y":           y,
            "w":           bw,
            "h":           bh,
            "area":        int(area),
            "circularity": round(circularity, 3),
            "shape":       shape,
            "size_mm":     round(math.sqrt(float(area)) * 0.05, 3),
            "confidence":  0.0,
        })
    return particles


# ══════════════════════════════════════════════════════════════════════
# MicroplasticDetector class (used by app.py via analyze())
# ══════════════════════════════════════════════════════════════════════

class MicroplasticDetector:
    """Detect and classify microplastic particles in petri-dish images."""

    def __init__(self):
        self._yolo_model = None
        self._yolo_tried = False

        if os.path.exists(MODEL_PATH):
            print(f"[Detector] YOLO model found at {MODEL_PATH}")
            print("[Detector] Will attempt YOLO on first call.")
        else:
            print("[Detector] No YOLO model — OpenCV-only pipeline active.")

    # ── public API ──────────────────────────────────────────────────────────
    def analyze(self, image_bytes: bytes, settings: dict | None = None) -> dict:
        """
        Analyse raw image bytes for microplastic particles.

        Parameters
        ----------
        image_bytes : bytes   Raw JPG / PNG / BMP / TIFF data
        settings    : dict    Optional overrides (currently unused, reserved)

        Returns
        -------
        dict with keys: stats, particles, annotated_image
        or  {"error": "..."} on failure
        """
        settings = settings or {}

        np_arr = np.frombuffer(image_bytes, np.uint8)
        orig   = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if orig is None:
            return {"error": "Cannot decode image — unsupported or corrupt file"}

        H, W     = orig.shape[:2]
        img_area = H * W

        # ── Try YOLO model first ────────────────────────────────────────
        if os.path.exists(MODEL_PATH) and not self._yolo_tried:
            try:
                from ultralytics import YOLO as _YOLO
                self._yolo_model = _YOLO(MODEL_PATH)
                self._yolo_tried = True
                print("[Detector] YOLO model loaded successfully.")
            except Exception as e:
                print(f"[Detector] YOLO load failed ({e}) — using OpenCV fallback.")
                self._yolo_tried = True
                self._yolo_model = None

        if self._yolo_model is not None:
            try:
                return self._analyze_yolo(orig, H, W, img_area)
            except Exception as e:
                print(f"[Detector] YOLO inference error ({e}) — falling back to OpenCV.")
                self._yolo_model = None   # disable for future calls

        # ── OpenCV fallback ─────────────────────────────────────────────
        return self._analyze_opencv(orig, H, W, img_area)

    # ═══════════════════════════════════════════════════════════════════════
    # YOLO inference path
    # ═══════════════════════════════════════════════════════════════════════
    def _analyze_yolo(self, img, H, W, img_area):
        """Run YOLOv8 inference and build the standard result dict."""
        # Write img to a temp bytes buffer then infer from array
        # (ultralytics accepts numpy arrays directly)
        results = self._yolo_model(img, conf=0.35, verbose=False)

        annotated = img.copy()
        particles = []

        for box in results[0].boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            bw = x2 - x1
            bh = y2 - y1
            area   = bw * bh
            aspect = float(max(bw, bh)) / (min(bw, bh) + 1e-5)
            perim  = 2 * (bw + bh)
            circ   = (4 * math.pi * area) / (perim ** 2 + 1e-5)

            shape, color = _classify(circ, aspect)
            size_mm      = round(math.sqrt(float(area)) * 0.05, 3)
            pid          = len(particles) + 1

            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            cv2.putText(
                annotated, f"#{pid} {shape}",
                (x1, max(y1 - 4, 12)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 255, 220), 1, cv2.LINE_AA
            )

            particles.append({
                "id":          pid,
                "size_mm":     size_mm,
                "shape":       shape,
                "circularity": round(circ, 3),
                "area_px":     int(area),
                "confidence":  round(float(box.conf), 2),
            })

        print(f"[Detector] YOLO: {len(particles)} particles detected.")
        return self._build_result(annotated, particles, H, W, img_area, model="yolo")

    # ═══════════════════════════════════════════════════════════════════════
    # OpenCV fallback pipeline
    # ═══════════════════════════════════════════════════════════════════════
    def _analyze_opencv(self, img, h, w, img_area):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # ── STEP A  Find the petri dish ────────────────────────────────────
        mask, dish_circle = _make_dish_mask_with_info(gray, h, w)

        # ── STEP B  CLAHE enhancement ──────────────────────────────────────
        clip  = _load_clahe_clip()
        clahe = cv2.createCLAHE(clipLimit=clip, tileGridSize=(8, 8))
        enhanced   = clahe.apply(gray)
        masked_enh = cv2.bitwise_and(enhanced, enhanced, mask=mask)

        # ── STEP C  Self-calibrating brightness threshold ──────────────────
        mean_val = float(cv2.mean(gray, mask=mask)[0])
        thr      = int(mean_val + 30)
        thr      = max(thr, 80)
        thr      = min(thr, 200)
        print(f"[Detector] mean_inside={mean_val:.1f}  threshold={thr}")

        _, binary = cv2.threshold(masked_enh, thr, 255, cv2.THRESH_BINARY)

        # ── STEP D  Saturation channel (coloured fibres / films) ───────────
        hsv           = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        sat           = hsv[:, :, 1]
        masked_sat    = cv2.bitwise_and(sat, sat, mask=mask)
        _, sat_binary = cv2.threshold(masked_sat, 50, 255, cv2.THRESH_BINARY)

        combined = cv2.bitwise_or(binary, sat_binary)

        # Morphological cleanup
        kernel  = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        cleaned = cv2.morphologyEx(combined, cv2.MORPH_OPEN,  kernel, iterations=1)
        cleaned = cv2.morphologyEx(cleaned,  cv2.MORPH_CLOSE, kernel, iterations=1)

        # ── STEP E  Find contours ──────────────────────────────────────────
        contours, _ = cv2.findContours(
            cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        print(f"[Detector] Contours before filter: {len(contours)}")

        annotated = img.copy()
        particles = []

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 6:
                continue
            if area > img_area * 0.02:
                continue

            x, y, bw, bh = cv2.boundingRect(cnt)
            if x <= 2 or y <= 2 or x + bw >= w - 2 or y + bh >= h - 2:
                continue

            hull_area = cv2.contourArea(cv2.convexHull(cnt))
            solidity  = area / (hull_area + 1e-5)
            if solidity < 0.25:
                continue

            perimeter   = cv2.arcLength(cnt, True)
            circularity = (4 * math.pi * area) / (perimeter ** 2 + 1e-5)
            aspect      = float(max(bw, bh)) / (min(bw, bh) + 1e-5)

            shape, color = _classify(circularity, aspect)
            size_mm      = round(math.sqrt(float(area)) * 0.05, 3)
            pid          = len(particles) + 1

            cv2.rectangle(annotated, (x, y), (x + bw, y + bh), color, 2)
            cv2.putText(
                annotated, f"#{pid} {shape}",
                (x, max(y - 4, 12)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 255, 220), 1, cv2.LINE_AA
            )

            particles.append({
                "id":          pid,
                "size_mm":     size_mm,
                "shape":       shape,
                "circularity": round(circularity, 3),
                "area_px":     int(area),
                "confidence":  None,
            })

        print(f"[Detector] Particles after filter: {len(particles)}")

        # Draw dish boundary for reference
        if dish_circle is not None:
            cv2.circle(annotated,
                       (dish_circle[0], dish_circle[1]),
                       dish_circle[2], (80, 50, 15), 2)

        return self._build_result(annotated, particles, h, w, img_area, model="opencv")

    # ── Build result dict ─────────────────────────────────────────────────
    def _build_result(self, annotated, particles, H, W, img_area, model="opencv"):
        n          = len(particles)
        status_str = _status(n)

        # Summary banner overlay
        overlay = annotated.copy()
        cv2.rectangle(overlay, (0, 0), (340, 46), (5, 5, 5), -1)
        cv2.addWeighted(overlay, 0.55, annotated, 0.45, 0, annotated)
        cv2.putText(
            annotated,
            f"Detected: {n} particles  [{status_str}]",
            (8, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (0, 221, 180), 2, cv2.LINE_AA
        )

        sizes  = [p["size_mm"] for p in particles]
        shapes = [p["shape"]   for p in particles]
        dominant = (
            max(["Fragment", "Fiber", "Film"], key=lambda s: shapes.count(s))
            if shapes else "—"
        )

        stats = {
            "total":     n,
            "avg_size":  round(float(np.mean(sizes)),  4) if sizes else 0.0,
            "min_size":  round(float(min(sizes)),       4) if sizes else 0.0,
            "max_size":  round(float(max(sizes)),       4) if sizes else 0.0,
            "fragments": shapes.count("Fragment"),
            "fibers":    shapes.count("Fiber"),
            "films":     shapes.count("Film"),
            "dominant":  dominant,
            "status":    status_str,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "model":     model,
        }

        _, buf = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 88])
        b64    = base64.b64encode(buf).decode("utf-8")

        return {"stats": stats, "particles": particles[:50], "annotated_image": b64}


# ══════════════════════════════════════════════════════════════════════
# Module-level helper functions (shared by class and standalone detect())
# ══════════════════════════════════════════════════════════════════════

def _make_dish_mask(gray, h, w, inner_ratio=0.85):
    """Return a binary mask covering the inner INNER_RATIO of the petri dish."""
    mask, _ = _make_dish_mask_with_info(gray, h, w, inner_ratio)
    return mask


def _make_dish_mask_with_info(gray, h, w, inner_ratio=0.85):
    """Return (mask, dish_circle_or_None)."""
    blurred = cv2.GaussianBlur(gray, (9, 9), 2)
    circles = cv2.HoughCircles(
        blurred,
        cv2.HOUGH_GRADIENT,
        dp        = 1.2,
        minDist   = 100,
        param1    = 50,
        param2    = 30,
        minRadius = int(min(h, w) * 0.25),
        maxRadius = int(min(h, w) * 0.55),
    )

    mask = np.zeros((h, w), dtype=np.uint8)
    dish_circle = None

    if circles is not None:
        circles = np.round(circles[0, :]).astype("int")
        cx, cy, r = circles[0]
        inner_r   = int(r * inner_ratio)
        cv2.circle(mask, (cx, cy), inner_r, 255, -1)
        dish_circle = (cx, cy, inner_r)
        print(f"[Detector] Dish: centre=({cx},{cy}) r={r} → inner={inner_r}")
    else:
        cx, cy = w // 2, h // 2
        cv2.ellipse(mask, (cx, cy),
                    (int(w * 0.35), int(h * 0.35)),
                    0, 0, 360, 255, -1)
        print("[Detector] No circle found — using centre ellipse fallback")

    return mask, dish_circle


def _load_clahe_clip() -> float:
    """Load clipLimit from thresholds.json, default 4.0."""
    if os.path.exists(THRESH_JSON):
        try:
            with open(THRESH_JSON) as f:
                return float(json.load(f).get("clahe_clip_limit", 4.0))
        except Exception:
            pass
    return 4.0


def _classify(circ: float, aspect: float):
    """Returns (shape_name, BGR_colour)."""
    if aspect >= 2.5 and circ < 0.5:
        return "Fiber",    (80,  160, 255)   # blue
    if circ >= 0.5:
        return "Fragment", (0,   220, 100)   # green
    return "Film",         (30,  200, 255)   # orange-cyan


def _status(n: int) -> str:
    """Map particle count to water-quality label."""
    if n == 0:   return "Clean"
    if n <= 5:   return "Low"
    if n <= 20:  return "Moderate"
    if n <= 50:  return "High"
    return               "Severe"
