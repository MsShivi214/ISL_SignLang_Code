// Direct landmark-to-bone retargeting, computed against this avatar's own
// rest-pose skeleton -- replaces the earlier Kalidokit-based approach,
// which assumed a VRM-convention rest pose that doesn't match this
// Mixamo-rigged avatar and produced visibly wrong poses.
//
// Method: for each bone with a known "aim" child (e.g. UpperArm aims at
// ForeArm), compute the rotation that swings the bone's fixed rest-pose
// child-direction onto the direction observed between the two matching
// MediaPipe landmarks, expressed in the bone's PARENT's current world
// space (so hierarchy composes correctly: rotating the upper arm carries
// the forearm with it, same as a real skeleton). This never assumes any
// external rig convention -- only this avatar's own geometry.
import * as THREE from "three";

// MediaPipe Pose landmark indices (33-point model).
const POSE_IDX = {
  left_shoulder: 11, right_shoulder: 12,
  left_elbow: 13, right_elbow: 14,
  left_wrist: 15, right_wrist: 16,
};

// MediaPipe Hand landmark indices (21-point model): wrist + 4 points per
// finger (thumb uses cmc/mcp/ip/tip; others use mcp/pip/dip/tip -- same
// 4-point structure either way, which is what matters for chaining).
const HAND_FINGER_IDX = {
  Thumb: [1, 2, 3, 4],
  Index: [5, 6, 7, 8],
  Middle: [9, 10, 11, 12],
  Ring: [13, 14, 15, 16],
  Pinky: [17, 18, 19, 20],
};
const HAND_WRIST_IDX = 0;

// MediaPipe's landmark space has Y increasing downward and Z increasing
// into the screen (confirmed empirically: nose world_y=-0.61 vs
// ankle world_y=+0.35, i.e. "up" is negative Y) -- the opposite handedness
// of Three.js (Y up, Z toward viewer). Flip both to convert.
export function mpToThree(lm) {
  return new THREE.Vector3(lm.x, -lm.y, -lm.z);
}

// Every bone this module can animate, as [boneName, aimChildBoneName]
// pairs -- the fixed reference used to compute each bone's rest-pose
// "pointing direction" once, at avatar-load time.
export function allBoneChildPairs() {
  const pairs = [];
  for (const side of ["Left", "Right"]) {
    pairs.push([`mixamorig${side}Arm`, `mixamorig${side}ForeArm`]);
    pairs.push([`mixamorig${side}ForeArm`, `mixamorig${side}Hand`]);
    pairs.push([`mixamorig${side}Hand`, `mixamorig${side}HandMiddle1`]);
    for (const finger of Object.keys(HAND_FINGER_IDX)) {
      pairs.push([`mixamorig${side}Hand${finger}1`, `mixamorig${side}Hand${finger}2`]);
      pairs.push([`mixamorig${side}Hand${finger}2`, `mixamorig${side}Hand${finger}3`]);
      pairs.push([`mixamorig${side}Hand${finger}3`, `mixamorig${side}Hand${finger}4`]);
    }
  }
  return pairs;
}

// Call once after the avatar loads. child.position is the fixed local
// offset from parent to child baked into the file -- this is the bone's
// own "at rest, my child is over there" direction, independent of any
// external convention.
export function buildRestChildDirections(bones) {
  const dirs = {};
  for (const [boneName, childName] of allBoneChildPairs()) {
    const bone = bones[boneName];
    const child = bones[childName];
    if (!bone || !child || child.position.lengthSq() < 1e-10) continue;
    dirs[boneName] = child.position.clone().normalize();
  }
  return dirs;
}

function poseChainSpecs(poseLandmarks) {
  const specs = [];
  for (const side of ["Left", "Right"]) {
    const s = side === "Left" ? "left" : "right";
    const shoulder = mpToThree(poseLandmarks[POSE_IDX[`${s}_shoulder`]]);
    const elbow = mpToThree(poseLandmarks[POSE_IDX[`${s}_elbow`]]);
    const wrist = mpToThree(poseLandmarks[POSE_IDX[`${s}_wrist`]]);
    specs.push([`mixamorig${side}Arm`, shoulder, elbow]);
    specs.push([`mixamorig${side}ForeArm`, elbow, wrist]);
  }
  return specs;
}

function handChainSpecs(handLandmarks, side) {
  const specs = [];
  const wrist = mpToThree(handLandmarks[HAND_WRIST_IDX]);
  const middleMcp = mpToThree(handLandmarks[HAND_FINGER_IDX.Middle[0]]);
  specs.push([`mixamorig${side}Hand`, wrist, middleMcp]);

  for (const [finger, idxs] of Object.entries(HAND_FINGER_IDX)) {
    const pts = idxs.map((i) => mpToThree(handLandmarks[i]));
    specs.push([`mixamorig${side}Hand${finger}1`, pts[0], pts[1]]);
    specs.push([`mixamorig${side}Hand${finger}2`, pts[1], pts[2]]);
    specs.push([`mixamorig${side}Hand${finger}3`, pts[2], pts[3]]);
  }
  return specs;
}

const _parentWorldQuat = new THREE.Quaternion();
const _observedLocalDir = new THREE.Vector3();

// specs must be given parent-before-child (arm before forearm, hand
// before fingers) so each bone's parent has already been updated this
// frame when we read its current world orientation.
function applyChain(bones, restDirs, specs) {
  const applied = {};
  for (const [boneName, fromPoint, toPoint] of specs) {
    const bone = bones[boneName];
    const restDir = restDirs[boneName];
    if (!bone || !restDir || !bone.parent) continue;

    const observedWorldDir = toPoint.clone().sub(fromPoint);
    if (observedWorldDir.lengthSq() < 1e-8) continue;
    observedWorldDir.normalize();

    bone.parent.getWorldQuaternion(_parentWorldQuat);
    _observedLocalDir.copy(observedWorldDir).applyQuaternion(_parentWorldQuat.clone().invert()).normalize();

    const quat = new THREE.Quaternion().setFromUnitVectors(restDir, _observedLocalDir);
    bone.quaternion.copy(quat);
    bone.updateMatrixWorld(true);
    applied[boneName] = quat;
  }
  return applied;
}

// Retargets both arms from pose landmarks, then (if given) each hand's
// fingers from hand landmarks. Mutates bone quaternions directly (for live
// preview) and returns { boneName: THREE.Quaternion } for every bone it
// touched, so the caller can save it into a track.
export function retargetFrame(bones, restDirs, { poseLandmarks, leftHandLandmarks, rightHandLandmarks }) {
  const applied = {};
  if (poseLandmarks) {
    Object.assign(applied, applyChain(bones, restDirs, poseChainSpecs(poseLandmarks)));
  }
  if (leftHandLandmarks) {
    Object.assign(applied, applyChain(bones, restDirs, handChainSpecs(leftHandLandmarks, "Left")));
  }
  if (rightHandLandmarks) {
    Object.assign(applied, applyChain(bones, restDirs, handChainSpecs(rightHandLandmarks, "Right")));
  }
  return applied;
}
