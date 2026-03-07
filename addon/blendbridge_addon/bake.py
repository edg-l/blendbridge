"""Bake helper — converts procedural materials to image-backed textures for game engine export.

Usage from a script:
    from bl_ext.user_default.blendbridge_addon.bake import bake_object, bake_all
    bake_object("mallet_head", size=1024)
    bake_all(size=1024)
"""

import os
import tempfile

import bpy


def _has_procedural_nodes(mat):
    """Check if a material has procedural texture nodes (not just Image Texture)."""
    if not mat or not mat.use_nodes:
        return False
    procedural_types = {
        "ShaderNodeTexNoise",
        "ShaderNodeTexWave",
        "ShaderNodeTexVoronoi",
        "ShaderNodeTexMusgrave",
        "ShaderNodeTexMagic",
        "ShaderNodeTexBrick",
        "ShaderNodeTexChecker",
        "ShaderNodeTexGradient",
    }
    return any(node.bl_idname in procedural_types for node in mat.node_tree.nodes)


def _ensure_uv_map(obj):
    """Add a Smart UV Project if the object has no UV map."""
    if obj.data.uv_layers:
        return
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=1.15192)  # ~66 degrees
    bpy.ops.object.mode_set(mode="OBJECT")


def _find_bsdf(mat):
    """Find the Principled BSDF node in a material."""
    for node in mat.node_tree.nodes:
        if node.bl_idname == "ShaderNodeBsdfPrincipled":
            return node
    return None


def _get_or_create_gltf_group_tree():
    """Get or create the shared 'glTF Material Output' node group tree."""
    existing = bpy.data.node_groups.get("glTF Material Output")
    if existing:
        return existing
    group_tree = bpy.data.node_groups.new("glTF Material Output", "ShaderNodeTree")
    group_tree.interface.new_socket("Occlusion", in_out="INPUT", socket_type="NodeSocketFloat")
    return group_tree


def _bake_pass(mat, pass_type, pass_filter, img_name, size, textures_dir, margin):
    """Bake a single pass and save to disk. Returns (image, node, path)."""
    img = bpy.data.images.new(img_name, width=size, height=size)

    nodes = mat.node_tree.nodes
    bake_node = nodes.new("ShaderNodeTexImage")
    bake_node.name = f"BakeTarget_{pass_type}"
    bake_node.image = img
    nodes.active = bake_node

    bpy.context.scene.render.bake.margin = margin
    bpy.ops.object.bake(
        type=pass_type,
        pass_filter=pass_filter,
        use_clear=True,
    )

    img_path = os.path.join(textures_dir, f"{img_name}.png")
    img.filepath_raw = img_path
    img.file_format = "PNG"
    img.save()
    print(f"bake: saved {img_path}")

    return img, bake_node, img_path


def bake_object(name, size=1024, textures_dir=None, margin=16):
    """Bake procedural material on an object to image textures.

    Bakes both diffuse color and ambient occlusion. The AO map is wired
    to the glTF-compatible occlusion slot so both Godot and Bevy pick it
    up automatically from the exported GLB.

    Bakes the first material slot that contains procedural nodes. Other
    material slots are left unchanged.

    Args:
        name: Name of the Blender object to bake.
        size: Texture resolution (square), default 1024.
        textures_dir: Directory to save baked images. Defaults to a temp dir.
        margin: Bake margin in pixels to prevent seam bleeding. Default 16.

    Returns:
        Path to the saved diffuse image file, or None if baking was skipped.
    """
    obj = bpy.data.objects.get(name)
    if not obj or obj.type != "MESH":
        print(f"bake: object '{name}' not found or not a mesh")
        return None

    if not obj.data.materials:
        print(f"bake: object '{name}' has no materials")
        return None

    # Find first material slot with procedural nodes
    mat = None
    mat_index = 0
    for i, m in enumerate(obj.data.materials):
        if _has_procedural_nodes(m):
            mat = m
            mat_index = i
            break

    if not mat:
        print(f"bake: object '{name}' has no procedural nodes in any material slot, skipping")
        return None

    # Resolve output directory
    if textures_dir is None:
        textures_dir = os.path.join(tempfile.gettempdir(), "blendbridge", "textures")
    os.makedirs(textures_dir, exist_ok=True)

    # Store and switch render engine
    original_engine = bpy.context.scene.render.engine
    bpy.context.scene.render.engine = "CYCLES"
    bpy.context.scene.cycles.samples = 64
    bpy.context.scene.cycles.device = "CPU"

    try:
        # Ensure UV map exists
        _ensure_uv_map(obj)

        # Select the object and set active material index
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        obj.active_material_index = mat_index

        # --- Bake diffuse color ---
        diffuse_img, diffuse_node, diffuse_path = _bake_pass(
            mat, "DIFFUSE", {"COLOR"}, f"{name}_bake", size, textures_dir, margin,
        )

        # --- Bake ambient occlusion ---
        ao_img, ao_node, ao_path = _bake_pass(
            mat, "AO", set(), f"{name}_ao", size, textures_dir, margin,
        )

        # Rewire material for export
        _rewire_material(mat, diffuse_node, ao_node)

        return diffuse_path

    finally:
        # Restore render engine
        bpy.context.scene.render.engine = original_engine


def _rewire_material(mat, diffuse_node, ao_node=None):
    """Replace procedural nodes with baked image textures."""
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    bsdf = _find_bsdf(mat)
    if not bsdf:
        print("bake: no Principled BSDF found, cannot rewire")
        return

    # Remove all links going into Base Color
    base_color_input = bsdf.inputs["Base Color"]
    for link in list(links):
        if link.to_socket == base_color_input:
            links.remove(link)

    # Connect diffuse bake to Base Color
    links.new(diffuse_node.outputs["Color"], base_color_input)

    # Connect AO to the glTF-compatible occlusion slot
    if ao_node:
        # Find existing glTF group node in this material, or create one
        gltf_group = None
        for node in nodes:
            if node.bl_idname == "ShaderNodeGroup" and node.node_tree and \
               node.node_tree.name == "glTF Material Output":
                gltf_group = node
                break

        if not gltf_group:
            gltf_group = nodes.new("ShaderNodeGroup")
            gltf_group.node_tree = _get_or_create_gltf_group_tree()

        links.new(ao_node.outputs["Color"], gltf_group.inputs["Occlusion"])

    # Remove procedural texture nodes (keep BSDF, output, image textures, glTF group)
    keep_types = {
        "ShaderNodeBsdfPrincipled",
        "ShaderNodeOutputMaterial",
        "ShaderNodeTexImage",
        "ShaderNodeGroup",
    }
    for node in list(nodes):
        if node.bl_idname not in keep_types:
            nodes.remove(node)


def bake_all(size=1024, textures_dir=None, margin=16):
    """Bake all mesh objects that have procedural materials.

    Args:
        size: Texture resolution (square), default 1024.
        textures_dir: Directory to save baked images.
        margin: Bake margin in pixels to prevent seam bleeding. Default 16.

    Returns:
        List of (object_name, image_path) tuples for successfully baked objects.
    """
    # Resolve output directory
    if textures_dir is None:
        textures_dir = os.path.join(tempfile.gettempdir(), "blendbridge", "textures")
    os.makedirs(textures_dir, exist_ok=True)

    # Collect objects to bake
    to_bake = []
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        if not obj.data.materials:
            continue
        if any(_has_procedural_nodes(mat) for mat in obj.data.materials):
            to_bake.append(obj.name)

    if not to_bake:
        return []

    # Switch engine once for all objects
    original_engine = bpy.context.scene.render.engine
    bpy.context.scene.render.engine = "CYCLES"
    bpy.context.scene.cycles.samples = 64
    bpy.context.scene.cycles.device = "CPU"

    results = []
    try:
        for obj_name in to_bake:
            # bake_object will try to switch engine again but it's already Cycles,
            # so the save/restore is a no-op. This is simpler than refactoring
            # bake_object to optionally skip the engine switch.
            path = bake_object(obj_name, size=size, textures_dir=textures_dir, margin=margin)
            if path:
                results.append((obj_name, path))
    finally:
        bpy.context.scene.render.engine = original_engine

    return results
