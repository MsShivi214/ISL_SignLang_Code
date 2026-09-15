from pygltflib import GLTF2

gltf = GLTF2().load("avatar/xbot.glb")

print("=== meshes ===")
for i, mesh in enumerate(gltf.meshes):
    print(f"mesh {i}: {mesh.name}")
    for p in mesh.primitives:
        targets = p.targets or []
        print(f"  primitive attrs: {list(p.attributes.__dict__.keys())}, morph targets: {len(targets)}")
    if mesh.weights:
        print(f"  weights: {len(mesh.weights)}")

print()
print("=== animations ===")
for i, anim in enumerate(gltf.animations):
    print(f"animation {i}: {anim.name}, channels={len(anim.channels)}, samplers={len(anim.samplers)}")

print()
print("=== skins ===")
for i, skin in enumerate(gltf.skins):
    print(f"skin {i}: joints={len(skin.joints)}, skeleton root node={skin.skeleton}")

print()
print("=== node extras (facial blendshape names on mesh nodes) ===")
for i, node in enumerate(gltf.nodes):
    if node.mesh is not None:
        print(f"node {i} '{node.name}' -> mesh {node.mesh}")
