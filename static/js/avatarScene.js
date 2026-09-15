import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { FBXLoader } from "three/addons/loaders/FBXLoader.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

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
  return { root, bones, restQuaternions, resetPose: makeResetPose(bones, restQuaternions) };
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

export function quaternionToArray(q) {
  return [q.x, q.y, q.z, q.w];
}

export function quaternionFromArray(arr) {
  return new THREE.Quaternion(arr[0], arr[1], arr[2], arr[3]);
}
