"""
train_model.py  — µPlastic Detection System
============================================
Full 3-step pipeline:
  Step 1 — detection/analyze_dataset.py   → detection/thresholds.json
  Step 2 — detection/auto_label.py        → YOLO .txt labels + data.yaml
  Step 3 — train_yolo()                   → detection/microplastic_model/weights/best.pt

Dataset paths
-------------
  Train  : C:\\Users\\Nitya Kalyani\\Desktop\\dataset\\train
  Valid  : C:\\Users\\Nitya Kalyani\\Desktop\\dataset\\valid

Images: JPG only — NO pre-existing label files.
Auto-labeling creates YOLO .txt labels from bright-particle detection.

Usage
-----
  python train_model.py --yolo     # run all 3 steps then train
  python train_model.py --cnn      # MobileNetV2 (legacy CSV path)
  python train_model.py            # auto-detect

Output
------
  YOLO  → detection/microplastic_model/weights/best.pt
          (image_detector.py loads this automatically)
  CNN   → models/microplastic_classifier.h5
"""

import os
import sys
import argparse

# ── Dataset paths ──────────────────────────────────────────────────
TRAIN_DIR = r"C:\Users\Nitya Kalyani\Desktop\dataset\train"
VALID_DIR = r"C:\Users\Nitya Kalyani\Desktop\dataset\valid"

# ── Output paths ───────────────────────────────────────────────────
BASE_DIR        = os.path.dirname(os.path.abspath(__file__))
DETECTION_DIR   = os.path.join(BASE_DIR, "detection")
YOLO_OUT_DIR    = DETECTION_DIR                          # project dir for YOLO
YOLO_NAME       = "microplastic_model"                   # run name
YOLO_WEIGHTS    = os.path.join(DETECTION_DIR, YOLO_NAME, "weights", "best.pt")
# data.yaml is written by auto_label.py into detection/
DATA_YAML       = os.path.join(DETECTION_DIR, "data.yaml")

CNN_MODEL_DIR   = os.path.join(BASE_DIR, "models")
CNN_MODEL_PATH  = os.path.join(CNN_MODEL_DIR, "microplastic_classifier.h5")

# ── YOLO training params ───────────────────────────────────────────
YOLO_EPOCHS     = 60
YOLO_IMGSZ      = 640
YOLO_BATCH      = 8
YOLO_PATIENCE   = 15

# ── CNN training params ────────────────────────────────────────────
IMG_SIZE        = 64
BATCH_SIZE      = 32
EPOCHS_TOP      = 12
EPOCHS_FINE     = 6
LR_TOP          = 1e-3
LR_FINE         = 5e-5
PADDING         = 8
NEGS_PER_IMG    = 3
RANDOM_SEED     = 42


# ═══════════════════════════════════════════════════════════════════
#  YOLO TRAINING PATH  (Steps 1 → 2 → 3)
# ═══════════════════════════════════════════════════════════════════

def _run_step1_analyze():
    """Run detection/analyze_dataset.py to produce thresholds.json."""
    import subprocess
    analyze_script = os.path.join(DETECTION_DIR, "analyze_dataset.py")
    if not os.path.exists(analyze_script):
        print(f"  WARNING: {analyze_script} not found — skipping Step 1")
        return
    print("\n[1/3] Running analyze_dataset.py …")
    result = subprocess.run([sys.executable, analyze_script], check=False)
    if result.returncode != 0:
        print("  WARNING: analyze_dataset.py exited with errors — continuing anyway.")


def _run_step2_label():
    """Run detection/auto_label.py to create YOLO .txt labels + data.yaml."""
    import subprocess
    label_script = os.path.join(DETECTION_DIR, "auto_label.py")
    if not os.path.exists(label_script):
        print(f"  WARNING: {label_script} not found — skipping Step 2")
        return
    print("\n[2/3] Running auto_label.py …")
    result = subprocess.run([sys.executable, label_script], check=False)
    if result.returncode != 0:
        print("  WARNING: auto_label.py exited with errors — continuing anyway.")


def train_yolo():
    """
    Full 3-step pipeline:
      Step 1 — analyze_dataset.py  → thresholds.json
      Step 2 — auto_label.py       → YOLO .txt labels + data.yaml
      Step 3 — YOLOv8n training    → best.pt
    """
    try:
        from ultralytics import YOLO
    except ImportError:
        print("ERROR: ultralytics not installed.")
        print("  Run: pip install ultralytics")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("  µPlastic YOLOv8 Training  (3-step pipeline)")
    print("=" * 60)

    # Validate dataset paths
    for path in [TRAIN_DIR, VALID_DIR]:
        if not os.path.isdir(path):
            print(f"\nERROR: Dataset folder not found:\n  {path}")
            print("Please verify TRAIN_DIR / VALID_DIR at the top of this script.")
            sys.exit(1)

    os.makedirs(DETECTION_DIR, exist_ok=True)

    # ── Step 1: derive thresholds from dataset ───────────────────────
    _run_step1_analyze()

    # ── Step 2: auto-label every image ──────────────────────────────
    _run_step2_label()

    # ── Step 3: train YOLOv8n ───────────────────────────────────────
    if not os.path.exists(DATA_YAML):
        print(f"\nERROR: data.yaml not found at {DATA_YAML}")
        print("  auto_label.py should have created it. Check the output above.")
        sys.exit(1)

    print(f"\n[3/3] Loading YOLOv8n pretrained weights …")
    model = YOLO("yolov8n.pt")   # downloads from ultralytics hub on first run

    print(f"  Training for up to {YOLO_EPOCHS} epochs …")
    print(f"  imgsz={YOLO_IMGSZ}  batch={YOLO_BATCH}  patience={YOLO_PATIENCE}")
    print(f"  Output → {os.path.join(YOLO_OUT_DIR, YOLO_NAME)}\n")

    results = model.train(
        data      = DATA_YAML,
        epochs    = YOLO_EPOCHS,
        imgsz     = YOLO_IMGSZ,
        batch     = YOLO_BATCH,
        patience  = YOLO_PATIENCE,
        augment   = True,        # enable built-in augmentation
        hsv_v     = 0.5,         # brightness augment — critical for dark images
        degrees   = 45,          # rotation — particles can be anywhere
        fliplr    = 0.5,
        flipud    = 0.5,
        mosaic    = 0.5,
        project   = YOLO_OUT_DIR,
        name      = YOLO_NAME,
        exist_ok  = True,        # overwrite previous run
        verbose   = True,
    )

    # Confirm weights saved
    best_pt = os.path.join(str(results.save_dir), "weights", "best.pt")
    if os.path.exists(best_pt):
        print("\n" + "=" * 60)
        print(f"  ✅ YOLOv8 model saved → {best_pt}")
        print("  Restart app.py — image_detector.py will auto-load it.")
        print("=" * 60)
    elif os.path.exists(YOLO_WEIGHTS):
        print(f"\n✅ Model saved → {YOLO_WEIGHTS}")
    else:
        print(f"\n⚠  Weights not found at expected path:\n  {YOLO_WEIGHTS}")
        print("  Check the YOLO_OUT_DIR / YOLO_NAME settings above.")

    return results


# ═══════════════════════════════════════════════════════════════════
#  MobileNetV2 TRAINING PATH (fallback / legacy)
# ═══════════════════════════════════════════════════════════════════

def _iou(boxA, boxB):
    xA = max(boxA[0], boxB[0]); yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2]); yB = min(boxA[3], boxB[3])
    inter = max(0, xB - xA) * max(0, yB - yA)
    areaA = (boxA[2]-boxA[0]) * (boxA[3]-boxA[1])
    areaB = (boxB[2]-boxB[0]) * (boxB[3]-boxB[1])
    union = areaA + areaB - inter + 1e-6
    return inter / union


def extract_crops(img_dir, csv_path, split_name):
    import random, numpy as np, cv2, pandas as pd
    random.seed(RANDOM_SEED); np.random.seed(RANDOM_SEED)

    if not os.path.exists(csv_path):
        print(f"  WARNING: annotations file not found: {csv_path}")
        return (np.zeros((0, IMG_SIZE, IMG_SIZE, 3), "float32"),
                np.zeros(0, "int32"))

    df = pd.read_csv(csv_path)
    print(f"\n  [{split_name}] {len(df)} rows, {df['filename'].nunique()} images")

    X, y = [], []
    for fname, grp in df.groupby("filename"):
        img = cv2.imread(os.path.join(img_dir, fname))
        if img is None:
            print(f"    ⚠ Cannot read: {fname}"); continue

        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        H, W    = img.shape[:2]
        boxes   = grp[["xmin","ymin","xmax","ymax"]].values.tolist()

        for box in boxes:
            x1,y1,x2,y2 = box
            x1 = max(0,int(x1)-PADDING); y1 = max(0,int(y1)-PADDING)
            x2 = min(W-1,int(x2)+PADDING); y2 = min(H-1,int(y2)+PADDING)
            if x2 <= x1 or y2 <= y1: continue
            crop = img_rgb[y1:y2, x1:x2]
            if crop.size == 0: continue
            X.append(cv2.resize(crop,(IMG_SIZE,IMG_SIZE)).astype("float32")/255.0)
            y.append(1)

        import random as _r
        min_dim = min(IMG_SIZE, 40)
        for _ in range(NEGS_PER_IMG):
            for _a in range(20):
                ph = _r.randint(min_dim, max(min_dim+1, H//4))
                pw = _r.randint(min_dim, max(min_dim+1, W//4))
                rx = _r.randint(0, max(0, W-pw-1))
                ry = _r.randint(0, max(0, H-ph-1))
                nb = [rx,ry,rx+pw,ry+ph]
                if all(_iou(nb,b) < 0.1 for b in boxes):
                    c = img_rgb[ry:ry+ph, rx:rx+pw]
                    if c.size == 0: continue
                    X.append(cv2.resize(c,(IMG_SIZE,IMG_SIZE)).astype("float32")/255.0)
                    y.append(0); break

    X = np.array(X, "float32"); y = np.array(y, "int32")
    pos = int(y.sum())
    print(f"    → {len(y)} crops | {pos} positive | {len(y)-pos} negative")
    return X, y


def train_cnn():
    """Fine-tune MobileNetV2 on bounding-box crops (CSV annotation format)."""
    import random, numpy as np
    random.seed(RANDOM_SEED); np.random.seed(RANDOM_SEED)

    try:
        import pandas as pd
    except ImportError:
        print("ERROR: pip install pandas"); sys.exit(1)
    try:
        import tensorflow as tf
        print(f"TensorFlow {tf.__version__} detected.")
    except ImportError:
        print("ERROR: pip install tensorflow"); sys.exit(1)

    from tensorflow.keras.applications import MobileNetV2
    from tensorflow.keras.layers import (GlobalAveragePooling2D, Dense,
                                         Dropout, BatchNormalization)
    from tensorflow.keras.models import Model
    from tensorflow.keras.optimizers import Adam
    from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau

    AUTOTUNE = tf.data.AUTOTUNE
    TRAIN_CSV = os.path.join(TRAIN_DIR, "_annotations.csv")
    VALID_CSV = os.path.join(VALID_DIR, "_annotations.csv")

    print("\n" + "="*60)
    print("  µPlastic MobileNetV2 Training (CNN)")
    print("="*60)
    print("\n[1/5] Extracting annotated crops from dataset …")
    X_train, y_train = extract_crops(TRAIN_DIR, TRAIN_CSV, "train")
    X_valid, y_valid = extract_crops(VALID_DIR, VALID_CSV, "valid")

    if len(X_train) == 0:
        print("\nERROR: No training samples. Check TRAIN_DIR / CSV paths.")
        sys.exit(1)

    idx = np.random.permutation(len(X_train))
    X_train, y_train = X_train[idx], y_train[idx]

    print("\n[2/5] Setting up augmentation pipeline …")

    def augment(image, label):
        image = tf.image.random_flip_left_right(image)
        image = tf.image.random_flip_up_down(image)
        image = tf.image.random_brightness(image, 0.15)
        image = tf.image.random_contrast(image, 0.85, 1.15)
        image = tf.image.random_saturation(image, 0.8, 1.2)
        return tf.clip_by_value(image, 0.0, 1.0), label

    train_ds = (tf.data.Dataset.from_tensor_slices((X_train, y_train))
                .shuffle(len(X_train), seed=RANDOM_SEED)
                .map(augment, num_parallel_calls=AUTOTUNE)
                .batch(BATCH_SIZE).prefetch(AUTOTUNE))
    valid_ds = (tf.data.Dataset.from_tensor_slices((X_valid, y_valid))
                .batch(BATCH_SIZE).prefetch(AUTOTUNE))

    print("\n[3/5] Building MobileNetV2 model …")
    base = MobileNetV2(input_shape=(IMG_SIZE,IMG_SIZE,3),
                       include_top=False, weights="imagenet")
    base.trainable = False
    x   = GlobalAveragePooling2D()(base.output)
    x   = BatchNormalization()(x)
    x   = Dense(128, activation="relu")(x)
    x   = Dropout(0.4)(x)
    x   = Dense(32,  activation="relu")(x)
    out = Dense(1,   activation="sigmoid")(x)
    model = Model(inputs=base.input, outputs=out)

    pos_count = int(y_train.sum())
    neg_count = len(y_train) - pos_count
    class_weight = {0: 1.0, 1: neg_count / max(pos_count, 1)}
    print(f"    Class weights → bg: 1.00 | particle: {class_weight[1]:.2f}")

    callbacks = [
        EarlyStopping(monitor="val_loss", patience=4,
                      restore_best_weights=True, verbose=1),
        ReduceLROnPlateau(monitor="val_loss", factor=0.5,
                          patience=2, min_lr=1e-7, verbose=1),
    ]

    print(f"\n[4/5] Phase 1 — head-only ({EPOCHS_TOP} epochs) …")
    model.compile(optimizer=Adam(LR_TOP), loss="binary_crossentropy",
                  metrics=["accuracy",
                           tf.keras.metrics.AUC(name="auc"),
                           tf.keras.metrics.Precision(name="precision"),
                           tf.keras.metrics.Recall(name="recall")])
    model.fit(train_ds, epochs=EPOCHS_TOP, validation_data=valid_ds,
              class_weight=class_weight, callbacks=callbacks, verbose=1)

    print(f"\n[4/5] Phase 2 — fine-tune last 30 layers ({EPOCHS_FINE} epochs) …")
    for layer in base.layers[-30:]:
        layer.trainable = True
    model.compile(optimizer=Adam(LR_FINE), loss="binary_crossentropy",
                  metrics=["accuracy",
                           tf.keras.metrics.AUC(name="auc"),
                           tf.keras.metrics.Precision(name="precision"),
                           tf.keras.metrics.Recall(name="recall")])
    model.fit(train_ds, epochs=EPOCHS_FINE, validation_data=valid_ds,
              class_weight=class_weight, callbacks=callbacks, verbose=1)

    os.makedirs(CNN_MODEL_DIR, exist_ok=True)
    print(f"\n[5/5] Saving model → {CNN_MODEL_PATH}")
    model.save(CNN_MODEL_PATH)

    results = model.evaluate(valid_ds, verbose=0)
    print("\n" + "="*60)
    print("  Final Validation Metrics")
    print("="*60)
    for name, val in zip(model.metrics_names, results):
        print(f"  {name:12s}: {val:.4f}")

    print(f"\n✅ CNN model saved → {CNN_MODEL_PATH}")
    print("   Note: image_detector.py uses the YOLO model (best.pt).")
    print("   Run with --yolo to train the YOLOv8 model instead.")


# ═══════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════

def _has_yolo_layout():
    """Return True if the dataset looks like YOLO format (images/ + labels/)."""
    return (os.path.isdir(os.path.join(TRAIN_DIR, "images")) and
            os.path.isdir(os.path.join(TRAIN_DIR, "labels")))


def _has_csv_layout():
    """Return True if the dataset has a CSV annotation file."""
    return os.path.exists(os.path.join(TRAIN_DIR, "_annotations.csv"))


def _yolo_available():
    try:
        import ultralytics  # noqa: F401
        return True
    except ImportError:
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Train microplastic detection model."
    )
    parser.add_argument("--yolo", action="store_true",
                        help="Force YOLOv8 training")
    parser.add_argument("--cnn",  action="store_true",
                        help="Force MobileNetV2 (CNN) training")
    args = parser.parse_args()

    if args.yolo:
        train_yolo()
    elif args.cnn:
        train_cnn()
    else:
        # Auto-detect: prefer YOLO if ultralytics installed + YOLO layout present
        if _yolo_available() and (_has_yolo_layout() or not _has_csv_layout()):
            print("Auto-detected: YOLO dataset layout + ultralytics available.")
            print("Launching YOLOv8 training. Use --cnn to train CNN instead.\n")
            train_yolo()
        elif _has_csv_layout():
            print("Auto-detected: CSV annotation layout.")
            print("Launching MobileNetV2 training. Use --yolo to train YOLOv8 instead.\n")
            train_cnn()
        else:
            print("ERROR: Could not auto-detect dataset format.")
            print(f"  Checked TRAIN_DIR: {TRAIN_DIR}")
            print("  Expected either:")
            print("    YOLO format → train/images/ + train/labels/")
            print("    CSV  format → train/_annotations.csv")
            sys.exit(1)
