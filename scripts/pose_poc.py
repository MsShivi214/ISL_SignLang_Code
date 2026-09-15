import sys

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

VIDEO_PATH = sys.argv[1] if len(sys.argv) > 1 else "VideoData/Hello.mp4"

hand_options = vision.HandLandmarkerOptions(
    base_options=mp_python.BaseOptions(model_asset_path="mp_models/hand_landmarker.task"),
    running_mode=vision.RunningMode.VIDEO,
    num_hands=2,
)
pose_options = vision.PoseLandmarkerOptions(
    base_options=mp_python.BaseOptions(model_asset_path="mp_models/pose_landmarker_lite.task"),
    running_mode=vision.RunningMode.VIDEO,
)

hand_landmarker = vision.HandLandmarker.create_from_options(hand_options)
pose_landmarker = vision.PoseLandmarker.create_from_options(pose_options)

cap = cv2.VideoCapture(VIDEO_PATH)
fps = cap.get(cv2.CAP_PROP_FPS) or 30
frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

frame_idx = 0
frames_with_pose = 0
frames_with_one_hand = 0
frames_with_two_hands = 0
total_frames = 0

while True:
    ok, frame = cap.read()
    if not ok:
        break
    total_frames += 1
    timestamp_ms = int((frame_idx / fps) * 1000)
    frame_idx += 1

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

    pose_result = pose_landmarker.detect_for_video(mp_image, timestamp_ms)
    hand_result = hand_landmarker.detect_for_video(mp_image, timestamp_ms)

    if pose_result.pose_landmarks:
        frames_with_pose += 1

    n_hands = len(hand_result.hand_landmarks)
    if n_hands == 1:
        frames_with_one_hand += 1
    elif n_hands >= 2:
        frames_with_two_hands += 1

cap.release()

print(f"video: {VIDEO_PATH}")
print(f"resolution: {frame_w}x{frame_h}, fps: {fps:.1f}, total_frames: {total_frames}")
print(f"frames with pose detected: {frames_with_pose}/{total_frames} ({100*frames_with_pose/max(total_frames,1):.1f}%)")
print(f"frames with exactly 1 hand detected: {frames_with_one_hand}/{total_frames} ({100*frames_with_one_hand/max(total_frames,1):.1f}%)")
print(f"frames with 2 hands detected: {frames_with_two_hands}/{total_frames} ({100*frames_with_two_hands/max(total_frames,1):.1f}%)")
