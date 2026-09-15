from pygltflib import GLTF2

gltf = GLTF2().load("avatar/xbot.glb")

print(f"scenes: {len(gltf.scenes)}, nodes: {len(gltf.nodes)}, skins: {len(gltf.skins)}")
print(f"meshes: {len(gltf.meshes)}, animations: {len(gltf.animations)}")
print()

for i, node in enumerate(gltf.nodes):
    name = node.name or f"<unnamed {i}>"
    print(f"{i}: {name}  (children={node.children})")
