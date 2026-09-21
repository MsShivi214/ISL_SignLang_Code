import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { FBXLoader } from "three/addons/loaders/FBXLoader.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { buildRestChildDirections } from "./retarget.js";

const MODEL_CONFIG = {
  glb: { format: "glb", url: "/static/avatar/xbot.glb" },
  fbx: { format: "fbx", url: "/static/avatar/Waving.fbx" },
  fbx2: { format: "fbx", url: "/static/avatar/Avatar.fbx" },
};

// Matches "mixamorig" bone names with an optional numeric namespace suffix,
// e.g. "mixamorig4LeftArm" -- DCC tools (Blender/Maya) append a digit like
// this to a duplicate armature's bone prefix when a second Mixamo rig gets
// imported into the same scene before export, to avoid a name collision
// with one already present. Capturing group 1 is the bone's identity
// (e.g. "LeftArm") with that prefix stripped.
const MIXAMO_PREFIX_RE = /^mixamorig\d*(.+)$/;

function collectBones(root) {
  const bones = {};
  // First-occurrence-wins: some FBX exports (confirmed on the newer
  // "avatar (1).fbx") add a zero-offset leaf/pivot child under every bone
  // that repeats its parent's exact name (a known Blender FBX-export
  // artifact from "Add Leaf Bones"). traverse() visits a bone before its
  // children, so the first time a name is seen is always the real,
  // correctly-offset bone -- letting a same-named descendant overwrite it
  // would silently point retargeting at the wrong (identity-offset) node.
  root.traverse((obj) => {
    if (obj.isBone && !(obj.name in bones)) bones[obj.name] = obj;
  });

  // Alias every bone onto its canonical "mixamorigXyz" name (stripping any
  // numeric namespace suffix), so retarget.js's hardcoded "mixamorigXyz"
  // bone names -- and every already-baked SignAnimations/*.json track,
  // which stores keys in that same canonical form -- resolve correctly
  // against any Mixamo-derived skeleton regardless of which namespace
  // suffix its export happened to end up with. A no-op for skeletons that
  // already use the bare "mixamorig" prefix (xbot.glb, Waving.fbx).
  for (const name of Object.keys(bones)) {
    const m = name.match(MIXAMO_PREFIX_RE);
    if (!m) continue;
    const canonical = "mixamorig" + m[1];
    if (!(canonical in bones)) bones[canonical] = bones[name];
  }

  return bones;
}

function captureRestQuaternions(bones) {
  const restQuaternions = {};
  for (const [name, bone] of Object.entries(bones)) {
    restQuaternions[name] = bone.quaternion.clone();
  }
  return restQuaternions;
}

function makeResetPose(bones, restQuaternions) {
  return function resetPose() {
    for (const [name, bone] of Object.entries(bones)) {
      bone.quaternion.copy(restQuaternions[name]);
    }
  };
}

// Loads one avatar as a standalone root Object3D plus its bone maps. Doesn't
// touch any scene -- the caller adds/removes `root`. Every avatar here turns
// out to be a Mixamo-derived skeleton (confirmed by inspecting each one's
// bone hierarchy directly, never assumed), so retarget.js's chain specs work
// unmodified against any of them once collectBones() has normalized their
// bone names onto the canonical "mixamorigXyz" form -- only the loader and
// the unit scale differ per format.
async function loadAvatarModel(avatarType) {
  const config = MODEL_CONFIG[avatarType];
  if (!config) throw new Error(`Unknown avatar type: ${avatarType}`);

  let root;
  if (config.format === "fbx") {
    const loader = new FBXLoader();
    root = await loader.loadAsync(config.url);
    // Mixamo FBX exports are authored in centimeters; this scene (camera,
    // grid, OrbitControls target) assumes a ~1.7-unit-tall, meter-scale
    // avatar like the GLB, so scale the FBX down to match.
    root.scale.setScalar(0.01);
  } else {
    const loader = new GLTFLoader();
    const gltf = await loader.loadAsync(config.url);
    root = gltf.scene;
  }

  const bones = collectBones(root);
  const restQuaternions = captureRestQuaternions(bones);
  // Same rest-pose-child-direction computation retarget.js uses at bake
  // time (see its own comment for the geometry) -- needed again here so
  // baked clips can be correctly re-aimed per avatar at playback time; see
  // applyRetargetedQuaternionPose() below for why.
  const restDirs = buildRestChildDirections(bones);
  return { root, bones, restQuaternions, restDirs, resetPose: makeResetPose(bones, restQuaternions) };
}

// Every SignAnimations/*.json clip today was baked against the GLB avatar
// (it's the only one that existed until the FBX avatars were added). Each
// saved quaternion is the *absolute* result of
// setFromUnitVectors(GLB_restDir, observedDir) computed during baking --
// its value is only meaningful relative to GLB's OWN restDir (the fixed
// local direction its bone points at rest, from buildRestChildDirections).
// A different skeleton's same-named bone can have a different restDir even
// with an identical (typically identity) restQuaternion -- confirmed by
// testing that a restQuaternion-based calibration was a no-op here, since
// Mixamo rigs bind with identity bone rotations and encode the T-pose
// shape entirely via bone *positions* instead. So the fix has to work in
// direction space, not quaternion-delta space: recover the direction the
// original bake observed (rotate GLB's restDir by the baked quaternion),
// then re-solve for the rotation that aims *this* avatar's own restDir at
// that same direction -- see applyRetargetedQuaternionPose() below.
// getReferenceRestDirs() loads the GLB once (never added to any scene,
// just to read off this) so it's available regardless of which avatar is
// actually being shown.
let _referenceRestDirsPromise = null;
export function getReferenceRestDirs() {
  if (!_referenceRestDirsPromise) {
    _referenceRestDirsPromise = loadAvatarModel("glb").then((m) => m.restDirs);
  }
  return _referenceRestDirsPromise;
}

export async function createAvatarScene(canvas, avatarType = "glb") {
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
  renderer.setPixelRatio(window.devicePixelRatio || 1);

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0xeeeeee);

  const camera = new THREE.PerspectiveCamera(35, 1, 0.1, 100);
  camera.position.set(0, 1.4, 3.2);

  scene.add(new THREE.HemisphereLight(0xffffff, 0x444444, 1.2));
  const dirLight = new THREE.DirectionalLight(0xffffff, 0.9);
  dirLight.position.set(2, 4, 3);
  scene.add(dirLight);

  const grid = new THREE.GridHelper(4, 8, 0xcccccc, 0xdddddd);
  scene.add(grid);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.target.set(0, 1.1, 0);
  controls.enableDamping = false;
  controls.update();

  function resize() {
    const w = canvas.clientWidth || 1;
    const h = canvas.clientHeight || 1;
    const needResize = canvas.width !== w || canvas.height !== h;
    if (needResize) {
      renderer.setSize(w, h, false);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    }
  }

  function render() {
    resize();
    renderer.render(scene, camera);
  }

  controls.addEventListener("change", render);
  window.addEventListener("resize", render);

  // A plain on-demand render (only on controls/resize/animation-frame
  // events) worked fine for the GLB avatar because GLTFLoader's loadAsync
  // waits for embedded textures to finish decoding before resolving.
  // FBXLoader resolves as soon as the mesh/skeleton is parsed and keeps
  // loading textures in the background, so without a running render loop
  // the canvas would keep showing the pre-texture (black) frame until some
  // other event happened to trigger a render. A continuous loop sidesteps
  // that timing gap for any loader/format.
  renderer.setAnimationLoop(render);

  const ctx = {
    scene,
    camera,
    renderer,
    render,
    avatarType: null,
    avatarRoot: null,
    bones: {},
    restQuaternions: {},
    restDirs: {},
    resetPose: () => {},
  };

  // Swaps in a different avatar model, replacing whichever one (if any) is
  // currently in the scene. Updates ctx.bones/restQuaternions/resetPose in
  // place on the same object callers already hold, so re-destructuring them
  // from the resolved createAvatarScene() result always picks up whichever
  // avatar is currently active.
  ctx.switchAvatar = async function switchAvatar(type) {
    const model = await loadAvatarModel(type);
    if (ctx.avatarRoot) scene.remove(ctx.avatarRoot);
    scene.add(model.root);
    ctx.avatarRoot = model.root;
    ctx.avatarType = type;
    ctx.bones = model.bones;
    ctx.restQuaternions = model.restQuaternions;
    ctx.restDirs = model.restDirs;
    ctx.resetPose = model.resetPose;
    render();
    return ctx;
  };

  await ctx.switchAvatar(avatarType);
  return ctx;
}

export function eulerToQuaternion(x, y, z) {
  return new THREE.Quaternion().setFromEuler(new THREE.Euler(x, y, z, "XYZ"));
}

export function applyQuaternionPose(bones, boneName, quat) {
  const bone = bones[boneName];
  if (!bone) return false;
  bone.quaternion.copy(quat);
  return true;
}

// Kalidokit's rotations are relative to a VRM-style rest pose (arms at the
// signer's sides), but this avatar is bound in T-pose -- so we can't apply
// its output as an absolute rotation without the result twisting badly.
// Instead we calibrate: capture each bone's Kalidokit rotation on the first
// tracked frame of a clip as a "neutral" reference, then apply only the
// *change* from that reference on top of the avatar's own rest orientation.
// This cancels out the fixed convention mismatch without needing to
// hand-tune a per-bone correction offset.
export function calibratedQuaternion(restQuat, referenceQuat, currentQuat) {
  const delta = referenceQuat.clone().invert().multiply(currentQuat);
  return restQuat.clone().multiply(delta);
}

const _observedDir = new THREE.Vector3();

// Re-aims a baked quaternion sample (recorded against the reference
// skeleton's restDir for this bone) onto this avatar's own restDir for the
// same bone -- see the comment on getReferenceRestDirs() above for why a
// quaternion-delta calibration doesn't work for this and direction-space
// re-solving is needed instead. Degrades gracefully to applying the sample
// unchanged if either skeleton has no restDir for this bone (e.g. it's not
// one retarget.js tracks) so a bone missing from one side never throws.
export function applyRetargetedQuaternionPose(bones, restDirs, referenceRestDirs, boneName, quat) {
  const bone = bones[boneName];
  if (!bone) return false;
  const restDir = restDirs[boneName];
  const referenceDir = referenceRestDirs[boneName];
  if (!restDir || !referenceDir) {
    bone.quaternion.copy(quat);
    return true;
  }
  _observedDir.copy(referenceDir).applyQuaternion(quat).normalize();
  bone.quaternion.setFromUnitVectors(restDir, _observedDir);
  return true;
}

export function quaternionToArray(q) {
  return [q.x, q.y, q.z, q.w];
}

export function quaternionFromArray(arr) {
  return new THREE.Quaternion(arr[0], arr[1], arr[2], arr[3]);
}
