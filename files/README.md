# ISL Avatar System — Complete Pipeline

## What This Does
Takes your ISL gesture video → extracts hand/body landmarks → converts to bone rotations → drives a 3D avatar.

---

## File Structure
```
isl-avatar-system/
│
├── 1_extract_landmarks.py       ← Step 1: Run on your video → produces landmark JSON
├── 2_landmark_to_rotation.py    ← Step 2: Converts landmarks → bone rotations JSON
├── 3_avatar_player.html         ← Step 3: 3D viewer (open in browser)
│
├── gesture_data/                ← Auto-created by Step 1
│   └── namaste.json             ← Raw landmark output
│
├── rotation_data/               ← Auto-created by Step 2
│   └── namaste_rotations.json   ← Bone rotation output (Three.js ready)
│
└── avatar.glb                   ← YOUR avatar file (download from Ready Player Me)
```

---

## Setup

### Python (Steps 1 & 2)
```bash
pip install mediapipe opencv-python numpy scipy
```

### Avatar File
1. Go to https://readyplayer.me
2. Create a free avatar
3. Download as GLB
4. Place file as: `avatar.glb` (same folder as the HTML)

---

## Step-by-Step Run

### Step 1 — Extract Landmarks
```bash
python 1_extract_landmarks.py --video namaste.mp4 --gesture namaste
# Output: gesture_data/namaste.json
```

### Step 2 — Convert to Rotations
```bash
python 2_landmark_to_rotation.py --input gesture_data/namaste.json
# Output: rotation_data/namaste_rotations.json
```

### Step 3 — Play in Browser
1. Open `3_avatar_player.html` in Chrome
2. In the browser console, call:
   ```javascript
   loadGestureFromJSON('./rotation_data/namaste_rotations.json', 'Namaste')
   ```
3. Click "Namaste" in the sidebar → "Perform Sign"

---

## Bone Name Map (if your avatar uses different names)
Edit the `BONE_MAP` object in `3_avatar_player.html`:
```javascript
const BONE_MAP = {
  'right_upper_arm': 'YOUR_BONE_NAME_HERE',
  ...
}
```
To find your avatar's bone names, open browser console and run:
```javascript
avatar.traverse(obj => { if(obj.isBone) console.log(obj.name); })
```

---

## Data Sources for ISL
- ISLRTC: https://islrtc.nic.in
- INCLUDE Dataset (IIT Delhi): search on Kaggle
- OpenISL: search on GitHub
