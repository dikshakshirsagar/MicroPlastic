import sys, io
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
"""
analyze_dataset.py  — µPlastic Detection System  (Step 1)
==========================================================
Scans every image in the train/ folder, finds the petri dish via
HoughCircles, masks to the inner 85% water region, and collects
brightness statistics to derive tuned detection thresholds.

Outputs
-------
  detection/thresholds.json  — thresholds used by auto_label.py

Usage
-----
  python detection/analyze_dataset.py
"""

import os, json, cv2, numpy as np

# ── Paths ──────────────────────────────────────────────────────────────
TRAIN_DIR      = r"C:\Users\Nitya Kalyani\Desktop\dataset\train"
BASE_DIR       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DETECTION_DIR  = os.path.join(BASE_DIR, "detection")
OUT_JSON       = os.path.join(DETECTION_DIR, "thresholds.json")

# ── Constants ──────────────────────────────────────────────────────────
INNER_RATIO    = 0.85          # keep 85 % of detected radius (exclude rim)
TOP_PCT        = 0.05          # brightest 5 % pixels = particle candidates
MIN_IMAGES     = 5             # warn if fewer images found


# ══════════════════════════════════════════════════════════════════════
def find_disk_mask(gray, h, w):
    """
    Detect petri-dish circle and return a mask covering the inner
    INNER_RATIO of the radius.  Falls back to a centred ellipse.
    Returns (mask, cx, cy, r) — r is the inner radius actually used.
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
        inner_r   = int(r * INNER_RATIO)
        cv2.circle(mask, (cx, cy), inner_r, 255, -1)
        return mask, cx, cy, inner_r
    else:
        # Fallback: centred ellipse
        cx, cy = w // 2, h // 2
        rw, rh = int(w * 0.38), int(h * 0.38)
        cv2.ellipse(mask, (cx, cy), (rw, rh), 0, 0, 360, 255, -1)
        return mask, cx, cy, min(rw, rh)


def analyze_image(img_path):
    """
    Returns dict of per-image stats, or None if the image is unreadable.
    """
    img = cv2.imread(img_path)
    if img is None:
        return None

    h, w      = img.shape[:2]
    img_area  = h * w
    gray      = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    mask, cx, cy, inner_r = find_disk_mask(gray, h, w)

    # Restrict statistics to interior of the dish
    masked_vals = gray[mask == 255].astype(np.float32)
    if len(masked_vals) == 0:
        return None

    mean_brightness = float(np.mean(masked_vals))
    std_brightness  = float(np.std(masked_vals))

    # Percentile threshold: brightness value at top 5 % of masked region
    pct_thresh = float(np.percentile(masked_vals, (1 - TOP_PCT) * 100))

    # Classic self-calibrating threshold
    auto_thresh = mean_brightness + 2 * std_brightness

    return {
        "mean":       mean_brightness,
        "std":        std_brightness,
        "pct95":      pct_thresh,      # 95th percentile of brightness inside dish
        "auto_thresh": auto_thresh,    # mean + 2*std
        "inner_r":    inner_r,
        "img_area":   img_area,
    }


# ══════════════════════════════════════════════════════════════════════
def main():
    print("=" * 60)
    print("  µPlastic Dataset Analyzer — Step 1")
    print("=" * 60)

    if not os.path.isdir(TRAIN_DIR):
        print(f"\nERROR: Train folder not found:\n  {TRAIN_DIR}")
        return

    # Collect all JPG images
    img_files = sorted([
        os.path.join(TRAIN_DIR, f)
        for f in os.listdir(TRAIN_DIR)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ])

    if len(img_files) < MIN_IMAGES:
        print(f"\nWARNING: Only {len(img_files)} image(s) found in:\n  {TRAIN_DIR}")
        print("  Expected 500+. Check TRAIN_DIR path.\n")

    print(f"\nFound {len(img_files)} images in train/\n")

    # ── Process every image ──────────────────────────────────────────
    results = []
    failed  = 0

    for i, path in enumerate(img_files, 1):
        stats = analyze_image(path)
        if stats is None:
            failed += 1
            continue
        results.append(stats)

        if i % 50 == 0 or i == len(img_files):
            print(f"  [{i:4d}/{len(img_files)}] "
                  f"mean={stats['mean']:.1f}  "
                  f"std={stats['std']:.1f}  "
                  f"thresh={stats['auto_thresh']:.1f}")

    if not results:
        print("\nERROR: No images could be analyzed. Check dataset folder.")
        return

    # ── Aggregate statistics ─────────────────────────────────────────
    arr_mean  = np.array([r["mean"]       for r in results])
    arr_std   = np.array([r["std"]        for r in results])
    arr_pct95 = np.array([r["pct95"]      for r in results])
    arr_at    = np.array([r["auto_thresh"] for r in results])
    arr_area  = np.array([r["img_area"]   for r in results])

    global_mean  = float(np.mean(arr_mean))
    global_std   = float(np.mean(arr_std))
    global_pct95 = float(np.mean(arr_pct95))
    global_at    = float(np.mean(arr_at))

    # ── Derive recommended parameters ───────────────────────────────
    # Particle threshold: use 95th-pct averaged across all images, but
    # never less than mean+2*std and never less than 80.
    particle_thresh = max(global_at, global_pct95 * 0.85, 80.0)
    particle_thresh = min(particle_thresh, 220.0)

    # CLAHE clipLimit: higher contrast needed when std is low (flat images)
    # Typical values 2-8.  For very dark, low-std images use higher clip.
    if global_std < 15:
        clip_limit = 6.0
    elif global_std < 30:
        clip_limit = 4.0
    else:
        clip_limit = 2.5

    # Min contour area: 6 px² is the absolute minimum; if images are large
    # we keep it at 6 because particles can be tiny.
    min_contour_area = 6

    avg_img_area     = float(np.mean(arr_area))
    max_contour_area = avg_img_area * 0.02   # 2 % of image

    # ── Print summary ────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  ANALYSIS RESULTS")
    print("=" * 60)
    print(f"  Images processed       : {len(results)}  (failed: {failed})")
    print(f"  Avg mean brightness    : {global_mean:.2f}")
    print(f"  Avg std deviation      : {global_std:.2f}")
    print(f"  Avg 95th pct brightness: {global_pct95:.2f}")
    print(f"  Avg particle threshold : {global_at:.2f}  (mean + 2·std)")
    print(f"  -- Recommended thresholds --------------")
    print(f"  Particle threshold     : {particle_thresh:.1f}")
    print(f"  CLAHE clipLimit        : {clip_limit}")
    print(f"  Min contour area (px2) : {min_contour_area}")
    print(f"  Max contour area (px2) : {max_contour_area:.0f}  (2% of avg image)")
    print("=" * 60)

    # ── Save JSON ────────────────────────────────────────────────────
    thresholds = {
        "global_mean_brightness":    round(global_mean, 2),
        "global_std_brightness":     round(global_std, 2),
        "global_pct95_brightness":   round(global_pct95, 2),
        "global_auto_thresh":        round(global_at, 2),
        "particle_threshold":        round(particle_thresh, 1),
        "clahe_clip_limit":          clip_limit,
        "min_contour_area_px":       min_contour_area,
        "max_contour_area_px":       round(max_contour_area, 0),
        "avg_image_area_px":         round(avg_img_area, 0),
        "images_analyzed":           len(results),
        "inner_radius_ratio":        INNER_RATIO,
    }

    os.makedirs(DETECTION_DIR, exist_ok=True)
    with open(OUT_JSON, "w") as f:
        json.dump(thresholds, f, indent=2)

    print(f"\nThresholds saved -> {OUT_JSON}")
    print("   Next step: python detection/auto_label.py\n")


if __name__ == "__main__":
    main()
