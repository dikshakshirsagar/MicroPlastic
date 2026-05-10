import sys, io
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
"""
auto_label.py  — µPlastic Detection System  (Step 2)
=====================================================
Reads detection/thresholds.json (produced by analyze_dataset.py)
then processes every image in train/ and valid/ to:

  1. Detect the petri dish (HoughCircles) and mask to inner 85 %
  2. Apply CLAHE enhancement for better particle visibility
  3. Threshold at the computed particle_threshold value
  4. Find bright contours that pass area / solidity / border filters
  5. Save YOLO-format  .txt  label file next to each image
  6. Write  detection/data.yaml  for YOLOv8 training

Usage
-----
  python detection/auto_label.py
"""

import os, json, cv2, numpy as np

# ── Paths ──────────────────────────────────────────────────────────────
TRAIN_DIR     = r"C:\Users\Nitya Kalyani\Desktop\dataset\train"
VALID_DIR     = r"C:\Users\Nitya Kalyani\Desktop\dataset\valid"

BASE_DIR      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DETECTION_DIR = os.path.join(BASE_DIR, "detection")
THRESH_JSON   = os.path.join(DETECTION_DIR, "thresholds.json")
DATA_YAML     = os.path.join(DETECTION_DIR, "data.yaml")

# ── Fallback thresholds if JSON is missing ─────────────────────────────
DEFAULTS = {
    "particle_threshold":     100.0,
    "clahe_clip_limit":       4.0,
    "min_contour_area_px":    6,
    "max_contour_area_px":    None,     # computed per-image at 2 %
    "inner_radius_ratio":     0.85,
}


# ══════════════════════════════════════════════════════════════════════
def load_thresholds():
    if os.path.exists(THRESH_JSON):
        with open(THRESH_JSON) as f:
            t = json.load(f)
        print(f"[AutoLabel] Loaded thresholds from {THRESH_JSON}")
        print(f"  particle_threshold : {t.get('particle_threshold', '?')}")
        print(f"  clahe_clip_limit   : {t.get('clahe_clip_limit', '?')}")
        print(f"  min_contour_area   : {t.get('min_contour_area_px', '?')} px²")
        return t
    else:
        print(f"[AutoLabel] WARNING: {THRESH_JSON} not found — using defaults.")
        print("  Run  python detection/analyze_dataset.py  first for best results.")
        return DEFAULTS.copy()


def find_dish_mask(gray, h, w, inner_ratio=0.85):
    """
    Detect the petri dish circle via HoughCircles.
    Returns (mask_uint8, cx, cy, inner_r, outer_r).
    Falls back to a centred ellipse if no circle is found.
    """
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

    if circles is not None:
        circles = np.round(circles[0, :]).astype("int")
        cx, cy, r = circles[0]
        inner_r   = int(r * inner_ratio)
        cv2.circle(mask, (cx, cy), inner_r, 255, -1)
        return mask, cx, cy, inner_r, r
    else:
        cx, cy = w // 2, h // 2
        rw = int(w * 0.38); rh = int(h * 0.38)
        cv2.ellipse(mask, (cx, cy), (rw, rh), 0, 0, 360, 255, -1)
        inner_r = min(rw, rh)
        return mask, cx, cy, inner_r, inner_r


def label_image(img_path, thresh_cfg):
    """
    Process one image and write YOLO label .txt beside it.
    Returns the number of detections written.
    """
    img = cv2.imread(img_path)
    if img is None:
        return 0

    h, w     = img.shape[:2]
    img_area = h * w

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    inner_ratio = float(thresh_cfg.get("inner_radius_ratio", 0.85))
    mask, cx, cy, inner_r, outer_r = find_dish_mask(gray, h, w, inner_ratio)

    # ── CLAHE enhancement inside dish ──────────────────────────────
    clip   = float(thresh_cfg.get("clahe_clip_limit", 4.0))
    clahe  = cv2.createCLAHE(clipLimit=clip, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    # Apply dish mask before thresholding
    masked_enhanced = cv2.bitwise_and(enhanced, enhanced, mask=mask)

    # ── Threshold ──────────────────────────────────────────────────
    # Use stored threshold, but also adapt to this specific image's mean
    raw_mean   = float(cv2.mean(gray, mask=mask)[0])
    stored_thr = float(thresh_cfg.get("particle_threshold", 100.0))
    # Adaptive blend: stored global + per-image offset keeps it robust
    img_thresh = raw_mean + (stored_thr - float(thresh_cfg.get("global_mean_brightness", raw_mean)))
    img_thresh = max(img_thresh, 70.0)
    img_thresh = min(img_thresh, 220.0)

    _, binary = cv2.threshold(masked_enhanced, img_thresh, 255, cv2.THRESH_BINARY)

    # Morphological cleanup
    kernel  = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    cleaned = cv2.morphologyEx(binary, cv2.MORPH_OPEN,  kernel, iterations=1)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel, iterations=1)

    # ── Find contours ──────────────────────────────────────────────
    contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    min_area = int(thresh_cfg.get("min_contour_area_px", 6))
    max_area_cfg = thresh_cfg.get("max_contour_area_px", None)
    max_area = float(max_area_cfg) if max_area_cfg else img_area * 0.02

    yolo_lines = []

    for cnt in contours:
        area = cv2.contourArea(cnt)

        if area < min_area:
            continue
        if area > max_area:
            continue

        x, y, bw, bh = cv2.boundingRect(cnt)

        # Reject if touching image border
        if x <= 2 or y <= 2 or x + bw >= w - 2 or y + bh >= h - 2:
            continue

        # Solidity filter: microplastic particles are mostly solid
        hull_area = cv2.contourArea(cv2.convexHull(cnt))
        if hull_area < 1:
            continue
        solidity = area / hull_area
        if solidity < 0.25:
            continue

        # ── YOLO format: class cx cy w h  (all normalised 0-1) ──────
        cx_n = (x + bw / 2) / w
        cy_n = (y + bh / 2) / h
        bw_n = bw / w
        bh_n = bh / h

        yolo_lines.append(f"0 {cx_n:.6f} {cy_n:.6f} {bw_n:.6f} {bh_n:.6f}")

    # Write label file (even if empty — YOLO needs it for negatives)
    label_path = os.path.splitext(img_path)[0] + ".txt"
    with open(label_path, "w") as f:
        f.write("\n".join(yolo_lines))

    return len(yolo_lines)


def write_data_yaml():
    """Write detection/data.yaml for YOLOv8 training."""
    content = (
        f"train: {TRAIN_DIR}\n"
        f"val:   {VALID_DIR}\n"
        f"nc: 1\n"
        f"names: ['microplastic']\n"
    )
    with open(DATA_YAML, "w") as f:
        f.write(content)
    print(f"  data.yaml written -> {DATA_YAML}")


# ----------------------------------------------------------------------
def process_folder(folder, thresh_cfg, split_name):
    if not os.path.isdir(folder):
        print(f"\n[AutoLabel] WARNING: Folder not found — {folder}")
        return 0, 0

    img_files = sorted([
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ])

    total_imgs      = len(img_files)
    total_particles = 0
    imgs_with_parts = 0

    print(f"\n[AutoLabel] Processing {split_name}: {total_imgs} images …")

    for i, path in enumerate(img_files, 1):
        n = label_image(path, thresh_cfg)
        total_particles += n
        if n > 0:
            imgs_with_parts += 1

        if i % 50 == 0 or i == total_imgs:
            print(f"  [{i:4d}/{total_imgs}] particles so far: {total_particles}")

    print(f"  OK {split_name}: {total_imgs} images, "
          f"{total_particles} labels, {imgs_with_parts} with detections")
    return total_imgs, total_particles


def main():
    print("=" * 60)
    print("  uPlastic Auto-Labeler — Step 2")
    print("=" * 60)

    thresh_cfg = load_thresholds()

    ti, tp = process_folder(TRAIN_DIR, thresh_cfg, "train")
    vi, vp = process_folder(VALID_DIR, thresh_cfg, "valid")

    write_data_yaml()

    print("\n" + "=" * 60)
    print("  LABELING SUMMARY")
    print("=" * 60)
    print(f"  Train : {ti} images -> {tp} particle labels")
    print(f"  Valid : {vi} images -> {vp} particle labels")
    print(f"  YOLO data.yaml -> {DATA_YAML}")
    print("=" * 60)
    print("\nLabeling complete.")
    print("   Next step: python train_model.py --yolo\n")


if __name__ == "__main__":
    main()
