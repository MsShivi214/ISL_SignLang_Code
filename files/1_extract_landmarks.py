"""
STEP 1 — ISL Landmark Extractor
================================
Run this on your gesture video (e.g., namaste.mp4)
It extracts MediaPipe Holistic landmarks (body + both hands + face)
and saves them as a JSON file ready for the avatar.

Install:
    pip install mediapipe opencv-python numpy

Run:
    python 1_extract_landmarks.py --video namaste.mp4 --gesture namaste
"""

import cv2
import mediapipe as mp
import numpy as np
import json
import argparse
import os

# ── MediaPipe setup ────────────────────────────────────────────────────────────
mp_holistic   = mp.solutions.holistic
mp_drawing    = mp.solutions.drawing_utils

# Landmark indices we care about for ISL signing
# MediaPipe Holistic gives:
#   33 pose landmarks  (body skeleton)
#   21 left hand landmarks
#   21 right hand landmarks
#   468 face landmarks (we use a subset)

POSE_LANDMARKS = {
    "nose":            0,
    "left_shoulder":   11,
    "right_shoulder":  12,
    "left_elbow":      13,
    "right_elbow":     14,
    "left_wrist":      15,
    "right_wrist":     16,
    "left_hip":        23,
    "right_hip":       24,
}

HAND_LANDMARKS = {
    "wrist":           0,
    "thumb_cmc":       1,  "thumb_mcp":  2,  "thumb_ip":  3,  "thumb_tip":  4,
    "index_mcp":       5,  "index_pip":  6,  "index_dip": 7,  "index_tip":  8,
    "middle_mcp":      9,  "middle_pip": 10, "middle_dip":11, "middle_tip": 12,
    "ring_mcp":        13, "ring_pip":   14, "ring_dip":  15, "ring_tip":   16,
    "pinky_mcp":       17, "pinky_pip":  18, "pinky_dip": 19, "pinky_tip":  20,
}


def extract_landmarks(video_path: str, gesture_name: str, output_dir: str = "gesture_data"):
    """
    Extract all holistic landmarks frame by frame from a video.
    Normalizes coordinates relative to body center (hip midpoint).
    Saves output as:  gesture_data/<gesture_name>.json
    """
    os.makedirs(output_dir, exist_ok=True)
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video: {video_path}")

    fps        = cap.get(cv2.CAP_PROP_FPS)
    total      = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"[INFO] Video: {video_path} | FPS: {fps:.1f} | Frames: {total}")

    gesture_sequence = []   # list of per-frame landmark dicts

    with mp_holistic.Holistic(
        static_image_mode=False,
        model_complexity=2,          # 2 = most accurate
        smooth_landmarks=True,
        min_detection_confidence=0.6,
        min_tracking_confidence=0.6
    ) as holistic:

        frame_idx = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            # MediaPipe expects RGB
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = holistic.process(rgb)

            # ── Get hip center for normalization ──────────────────────────────
            # We normalize ALL coordinates relative to hip center
            # so the data is camera-distance independent
            hip_center = [0.0, 0.0, 0.0]
            if results.pose_landmarks:
                lh = results.pose_landmarks.landmark[23]  # left hip
                rh = results.pose_landmarks.landmark[24]  # right hip
                hip_center = [
                    (lh.x + rh.x) / 2,
                    (lh.y + rh.y) / 2,
                    (lh.z + rh.z) / 2
                ]

            frame_data = {
                "frame":      frame_idx,
                "timestamp":  round(frame_idx / fps, 4),
                "pose":       {},
                "left_hand":  {},
                "right_hand": {},
                "detected":   {
                    "pose":       results.pose_landmarks       is not None,
                    "left_hand":  results.left_hand_landmarks  is not None,
                    "right_hand": results.right_hand_landmarks is not None,
                }
            }

            # ── POSE landmarks ────────────────────────────────────────────────
            if results.pose_landmarks:
                for name, idx in POSE_LANDMARKS.items():
                    lm = results.pose_landmarks.landmark[idx]
                    frame_data["pose"][name] = normalize(lm, hip_center)

            # ── LEFT HAND landmarks ───────────────────────────────────────────
            if results.left_hand_landmarks:
                for name, idx in HAND_LANDMARKS.items():
                    lm = results.left_hand_landmarks.landmark[idx]
                    frame_data["left_hand"][name] = normalize(lm, hip_center)

            # ── RIGHT HAND landmarks ──────────────────────────────────────────
            if results.right_hand_landmarks:
                for name, idx in HAND_LANDMARKS.items():
                    lm = results.right_hand_landmarks.landmark[idx]
                    frame_data["right_hand"][name] = normalize(lm, hip_center)

            gesture_sequence.append(frame_data)
            frame_idx += 1

            # Progress
            if frame_idx % 30 == 0:
                print(f"  Processed {frame_idx}/{total} frames...")

    cap.release()

    # ── Save JSON ─────────────────────────────────────────────────────────────
    output = {
        "gesture":    gesture_name,
        "fps":        fps,
        "total_frames": len(gesture_sequence),
        "frames":     gesture_sequence
    }
    out_path = os.path.join(output_dir, f"{gesture_name}.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n[DONE] Saved {len(gesture_sequence)} frames → {out_path}")
    return out_path


def normalize(landmark, hip_center):
    """
    Normalize landmark coordinates relative to hip center.
    Returns dict with x, y, z, visibility.
    """
    return {
        "x":          round(landmark.x - hip_center[0], 6),
        "y":          round(landmark.y - hip_center[1], 6),
        "z":          round(landmark.z - hip_center[2], 6),
        "visibility": round(getattr(landmark, "visibility", 1.0), 4)
    }


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ISL Landmark Extractor")
    parser.add_argument("--video",   required=True, help="Path to gesture video file")
    parser.add_argument("--gesture", required=True, help="Gesture name (e.g. namaste, hi, sorry)")
    parser.add_argument("--output",  default="gesture_data", help="Output directory")
    args = parser.parse_args()

    extract_landmarks(args.video, args.gesture, args.output)

# ── HOW TO RUN ────────────────────────────────────────────────────────────────
# python 1_extract_landmarks.py --video namaste.mp4  --gesture namaste
# python 1_extract_landmarks.py --video hi.mp4       --gesture hi
# python 1_extract_landmarks.py --video thankyou.mp4 --gesture thank_you
#
# Output will be saved to: gesture_data/namaste.json
