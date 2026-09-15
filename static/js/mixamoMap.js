// Maps Kalidokit's VRM-style humanoid bone names (what Pose.solve /
// Hand.solve return) onto this project's avatar's actual skeleton names.
//
// The source file (avatar/xbot.glb) names its bones "mixamorig:LeftArm"
// etc, but Three.js's GLTFLoader strips the colon when it builds the scene
// graph (a known quirk with Mixamo-exported glTF/GLB files), so the loaded
// THREE.Bone objects end up named "mixamorigLeftArm" -- confirmed by
// logging Object.keys(bones) against the actual loaded avatar. These maps
// target that stripped form, not the raw file's names.

export const POSE_BONE_MAP = {
  LeftUpperArm: "mixamorigLeftArm",
  LeftLowerArm: "mixamorigLeftForeArm",
  LeftHand: "mixamorigLeftHand",
  RightUpperArm: "mixamorigRightArm",
  RightLowerArm: "mixamorigRightForeArm",
  RightHand: "mixamorigRightHand",
  Spine: "mixamorigSpine",
};

function fingerMap(side) {
  // Kalidokit calls the little finger "Little"; Mixamo calls it "Pinky".
  const fingers = [
    ["Thumb", "Thumb"],
    ["Index", "Index"],
    ["Middle", "Middle"],
    ["Ring", "Ring"],
    ["Little", "Pinky"],
  ];
  const map = {};
  for (const [kName, mName] of fingers) {
    map[`${side}${kName}Proximal`] = `mixamorig${side}Hand${mName}1`;
    map[`${side}${kName}Intermediate`] = `mixamorig${side}Hand${mName}2`;
    map[`${side}${kName}Distal`] = `mixamorig${side}Hand${mName}3`;
  }
  return map;
}

export const HAND_BONE_MAP = { ...fingerMap("Left"), ...fingerMap("Right") };

export const ALL_BONE_MAP = { ...POSE_BONE_MAP, ...HAND_BONE_MAP };
