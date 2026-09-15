"""
STEP 2 — Convert Landmarks → Bone Rotations
=============================================
MediaPipe gives us X,Y,Z positions of joints.
But a 3D avatar needs ROTATION ANGLES for each bone.

This script converts the position data into Euler angles
that Three.js can directly apply to avatar bones.

Why this is needed:
  - Avatar bone: "rotate the forearm 45 degrees"  ← Three.js understands this
  - MediaPipe output: "wrist is at position (0.3, -0.5, 0.1)"  ← raw position
  - This script does the math to convert position → rotation

Install:
    pip install numpy scipy

Run:
    python 2_landmark_to_rotation.py --input gesture_data/namaste.json
"""

import numpy as np
import json
import argparse
import os
from scipy.spatial.transform import Rotation as R


# ── Vector math helpers ───────────────────────────────────────────────────────

def vec(d: dict) -> np.ndarray:
    """Convert landmark dict {x,y,z} to numpy array."""
    return np.array([d["x"], d["y"], d["z"]], dtype=float)


def normalize_vec(v: np.ndarray) -> np.ndarray:
    """Return unit vector."""
    norm = np.linalg.norm(v)
    return v / norm if norm > 1e-6 else v


def angle_between(v1: np.ndarray, v2: np.ndarray) -> float:
    """Return angle in radians between two vectors."""
    v1u = normalize_vec(v1)
    v2u = normalize_vec(v2)
    return float(np.arccos(np.clip(np.dot(v1u, v2u), -1.0, 1.0)))


def look_rotation(direction: np.ndarray, up: np.ndarray = None) -> np.ndarray:
    """
    Compute Euler angles (XYZ) from a direction vector.
    This is what Kalidokit does internally — we replicate it here.
    """
    if up is None:
        up = np.array([0, 1, 0])
    direction = normalize_vec(direction)
    right = normalize_vec(np.cross(up, direction))
    up    = np.cross(direction, right)
    mat   = np.array([right, up, direction]).T  # 3x3 rotation matrix
    try:
        rot = R.from_matrix(mat)
        return rot.as_euler("xyz", degrees=False)  # radians
    except Exception:
        return np.zeros(3)


# ── Pose (body) rotations ─────────────────────────────────────────────────────

def compute_arm_rotations(pose: dict, side: str) -> dict:
    """
    Compute upper arm and forearm rotations from pose landmarks.
    side = 'left' or 'right'
    """
    if not pose:
        return {}

    s = side  # 'left' or 'right'
    rotations = {}

    try:
        shoulder = vec(pose[f"{s}_shoulder"])
        elbow    = vec(pose[f"{s}_elbow"])
        wrist    = vec(pose[f"{s}_wrist"])

        # Upper arm direction: shoulder → elbow
        upper_arm_dir = elbow - shoulder
        rotations[f"{s}_upper_arm"] = look_rotation(upper_arm_dir).tolist()

        # Forearm direction: elbow → wrist
        forearm_dir = wrist - elbow
        rotations[f"{s}_forearm"] = look_rotation(forearm_dir).tolist()

    except KeyError as e:
        pass  # landmark missing in this frame

    return rotations


# ── Hand rotations ────────────────────────────────────────────────────────────

def compute_hand_rotations(hand: dict, side: str) -> dict:
    """
    Compute rotation for wrist + all 5 fingers (4 joints each).
    This is the key part for sign language — finger positions matter most.
    """
    if not hand:
        return {}

    rotations = {}
    finger_chains = {
        "thumb":  ["thumb_cmc",  "thumb_mcp",  "thumb_ip",   "thumb_tip"],
        "index":  ["index_mcp",  "index_pip",  "index_dip",  "index_tip"],
        "middle": ["middle_mcp", "middle_pip", "middle_dip", "middle_tip"],
        "ring":   ["ring_mcp",   "ring_pip",   "ring_dip",   "ring_tip"],
        "pinky":  ["pinky_mcp",  "pinky_pip",  "pinky_dip",  "pinky_tip"],
    }

    # Wrist rotation — direction from wrist to middle finger base
    try:
        wrist      = vec(hand["wrist"])
        mid_base   = vec(hand["middle_mcp"])
        wrist_dir  = mid_base - wrist
        rotations[f"{side}_wrist"] = look_rotation(wrist_dir).tolist()
    except KeyError:
        pass

    # Each finger — compute rotation at each joint
    for finger_name, chain in finger_chains.items():
        for i in range(len(chain) - 1):
            joint_name = chain[i]
            next_name  = chain[i + 1]
            try:
                p1  = vec(hand[joint_name])
                p2  = vec(hand[next_name])
                dir = p2 - p1
                rot = look_rotation(dir)
                key = f"{side}_{finger_name}_{i}"  # e.g. right_index_0
                rotations[key] = rot.tolist()
            except KeyError:
                pass

    return rotations


# ── Finger curl helper ────────────────────────────────────────────────────────
# This converts raw rotations into a simpler "curl" value (0=straight, 1=fully curled)
# Useful for ISL hand shapes like fist, open hand, thumbs up, etc.

def compute_finger_curl(hand: dict, finger: str) -> float:
    """
    Returns 0.0 (finger straight) to 1.0 (finger fully curled/fist).
    Uses angle between mcp→pip→tip vectors.
    """
    chains = {
        "thumb":  ["thumb_cmc",  "thumb_mcp",  "thumb_tip"],
        "index":  ["index_mcp",  "index_pip",  "index_tip"],
        "middle": ["middle_mcp", "middle_pip", "middle_tip"],
        "ring":   ["ring_mcp",   "ring_pip",   "ring_tip"],
        "pinky":  ["pinky_mcp",  "pinky_pip",  "pinky_tip"],
    }
    chain = chains.get(finger, [])
    if len(chain) < 3:
        return 0.0
    try:
        p1 = vec(hand[chain[0]])
        p2 = vec(hand[chain[1]])
        p3 = vec(hand[chain[2]])
        v1 = p2 - p1
        v2 = p3 - p2
        angle = angle_between(v1, v2)
        # Max curl angle ≈ π radians — normalize to 0–1
        return float(np.clip(angle / np.pi, 0.0, 1.0))
    except KeyError:
        return 0.0


# ── Process entire gesture JSON ───────────────────────────────────────────────

def process_gesture(input_path: str, output_dir: str = "rotation_data"):
    """
    Reads landmark JSON → computes rotations for every frame → saves rotation JSON.
    This rotation JSON is what Three.js will consume directly.
    """
    os.makedirs(output_dir, exist_ok=True)

    with open(input_path) as f:
        data = json.load(f)

    gesture_name = data["gesture"]
    fps          = data["fps"]
    frames_in    = data["frames"]

    print(f"[INFO] Processing '{gesture_name}' — {len(frames_in)} frames")

    frames_out = []

    for frame in frames_in:
        pose       = frame.get("pose", {})
        left_hand  = frame.get("left_hand", {})
        right_hand = frame.get("right_hand", {})

        frame_rotations = {
            "frame":     frame["frame"],
            "timestamp": frame["timestamp"],
            "bones":     {}
        }

        # Body arm rotations
        frame_rotations["bones"].update(compute_arm_rotations(pose, "left"))
        frame_rotations["bones"].update(compute_arm_rotations(pose, "right"))

        # Hand rotations (all finger joints)
        frame_rotations["bones"].update(compute_hand_rotations(left_hand,  "left"))
        frame_rotations["bones"].update(compute_hand_rotations(right_hand, "right"))

        # Finger curl values — useful for hand shape classification
        curls = {}
        for finger in ["thumb", "index", "middle", "ring", "pinky"]:
            curls[f"left_{finger}_curl"]  = compute_finger_curl(left_hand,  finger)
            curls[f"right_{finger}_curl"] = compute_finger_curl(right_hand, finger)
        frame_rotations["finger_curls"] = curls

        frames_out.append(frame_rotations)

    output = {
        "gesture":      gesture_name,
        "fps":          fps,
        "total_frames": len(frames_out),
        "frames":       frames_out
    }

    out_path = os.path.join(output_dir, f"{gesture_name}_rotations.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"[DONE] Rotation data saved → {out_path}")
    return out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Landmark to Rotation Converter")
    parser.add_argument("--input",  required=True, help="Path to landmark JSON from Step 1")
    parser.add_argument("--output", default="rotation_data", help="Output directory")
    args = parser.parse_args()

    process_gesture(args.input, args.output)

# ── HOW TO RUN ────────────────────────────────────────────────────────────────
# python 2_landmark_to_rotation.py --input gesture_data/namaste.json
# Output: rotation_data/namaste_rotations.json
#
# The output JSON has this structure per frame:
# {
#   "frame": 0,
#   "timestamp": 0.033,
#   "bones": {
#     "right_upper_arm": [0.12, -0.45, 0.02],   ← Euler XYZ in radians
#     "right_forearm":   [0.08, -0.30, 0.01],
#     "right_wrist":     [0.05, -0.10, 0.00],
#     "right_index_0":   [0.20, 0.00,  0.00],
#     ... all other finger joints ...
#   },
#   "finger_curls": {
#     "right_index_curl": 0.85,   ← 0=straight, 1=fully curled
#     "right_thumb_curl": 0.20,
#     ...
#   }
# }
