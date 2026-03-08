"""PBR texture helper — applies downloaded AmbientCG maps to objects via Principled BSDF.

Usage from a script:
    from bl_ext.user_default.blendbridge_addon.textures import apply_pbr
    apply_pbr(obj, "/path/to/Metal049A_2K/")
"""

import os

import bpy


# AmbientCG filename suffix → (channel_key, description)
_SUFFIX_MAP = {
    "_Color": "color",
    "_NormalGL": "normal",
    "_Roughness": "roughness",
    "_AmbientOcclusion": "ao",
    "_Displacement": "displacement",
}


def _scan_maps(texture_dir: str) -> dict:
    """Return a dict of channel -> absolute file path for maps found in texture_dir."""
    maps = {}
    for fname in os.listdir(texture_dir):
        fpath = os.path.join(texture_dir, fname)
        if not os.path.isfile(fpath):
            continue
        stem, _ = os.path.splitext(fname)
        for suffix, channel in _SUFFIX_MAP.items():
            if stem.endswith(suffix):
                maps[channel] = fpath
                break
    return maps


def _ensure_uv_map(obj):
    """Run Smart UV Project if the object has no UV layers."""
    if obj.type != "MESH":
        return
    if obj.data.uv_layers:
        return
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    try:
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(angle_limit=1.15192)  # ~66 degrees
    finally:
        bpy.ops.object.mode_set(mode="OBJECT")


def _get_or_create_gltf_group_tree():
    """Get or create the shared 'glTF Material Output' node group tree."""
    existing = bpy.data.node_groups.get("glTF Material Output")
    if existing:
        # Ensure Occlusion socket exists (may differ across Blender versions)
        names = {item.name for item in existing.interface.items_tree}
        if "Occlusion" not in names:
            existing.interface.new_socket("Occlusion", in_out="INPUT", socket_type="NodeSocketFloat")
        return existing
    group_tree = bpy.data.node_groups.new("glTF Material Output", "ShaderNodeTree")
    group_tree.interface.new_socket("Occlusion", in_out="INPUT", socket_type="NodeSocketFloat")
    return group_tree


def apply_pbr(obj, texture_dir: str, displacement: bool = False) -> bpy.types.Material:
    """Apply PBR texture maps from a directory to an object.

    Detects AmbientCG map files by filename suffix, creates a Principled BSDF
    material with available maps wired up, and assigns it to the object.
    Auto-runs Smart UV Project if the object has no UV layers.

    Wiring:
    - Color       → Base Color
    - NormalGL    → Normal Map node → Normal
    - Roughness   → Roughness
    - AO          → glTF Material Output Occlusion (read by Godot/Bevy)
    - Displacement → Displacement (off by default — causes artifacts on thin/game-scale geometry)

    Args:
        obj: Blender mesh object to apply the material to.
        texture_dir: Directory containing AmbientCG PBR image files.
        displacement: Enable displacement mapping (default False). Only enable
            for large, thick geometry where subtle surface deformation is desired.

    Returns:
        The created material.

    Note:
        Replaces all existing material slots on the object.
    """
    if obj.type != "MESH":
        raise TypeError(f"apply_pbr requires a MESH object, got {obj.type!r}")

    texture_dir = os.path.abspath(texture_dir)
    mat_name = os.path.basename(texture_dir.rstrip("/\\"))
    maps = _scan_maps(texture_dir)

    if not maps:
        print(f"textures: no PBR maps found in {texture_dir!r}")

    # Ensure UV map exists before applying textures
    _ensure_uv_map(obj)

    # Create material
    mat = bpy.data.materials.new(name=mat_name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    # Core nodes
    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (600, 0)

    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (300, 0)
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

    tex_coord = nodes.new("ShaderNodeTexCoord")
    tex_coord.location = (-600, 0)

    # Helper to create and wire an image texture node
    def _add_image_node(path: str, x: float, y: float, non_color: bool = False):
        img = bpy.data.images.load(path, check_existing=True)
        if non_color:
            img.colorspace_settings.name = "Non-Color"
        node = nodes.new("ShaderNodeTexImage")
        node.image = img
        node.location = (x, y)
        links.new(tex_coord.outputs["UV"], node.inputs["Vector"])
        return node

    y_offset = 0

    # Color map → Base Color
    if "color" in maps:
        color_node = _add_image_node(maps["color"], -200, y_offset)
        links.new(color_node.outputs["Color"], bsdf.inputs["Base Color"])
        y_offset -= 280

    # Normal map → Normal Map node → Normal
    if "normal" in maps:
        normal_img_node = _add_image_node(maps["normal"], -200, y_offset, non_color=True)
        normal_map_node = nodes.new("ShaderNodeNormalMap")
        normal_map_node.location = (50, y_offset)
        links.new(normal_img_node.outputs["Color"], normal_map_node.inputs["Color"])
        links.new(normal_map_node.outputs["Normal"], bsdf.inputs["Normal"])
        y_offset -= 280

    # Roughness map → Roughness
    if "roughness" in maps:
        roughness_node = _add_image_node(maps["roughness"], -200, y_offset, non_color=True)
        links.new(roughness_node.outputs["Color"], bsdf.inputs["Roughness"])
        y_offset -= 280

    # AO map → glTF Material Output Occlusion
    if "ao" in maps:
        ao_node = _add_image_node(maps["ao"], -200, y_offset, non_color=True)
        # Find or create glTF occlusion group node in this material
        gltf_group = nodes.new("ShaderNodeGroup")
        gltf_group.node_tree = _get_or_create_gltf_group_tree()
        gltf_group.location = (300, y_offset)
        links.new(ao_node.outputs["Color"], gltf_group.inputs["Occlusion"])
        y_offset -= 280

    # Displacement map → Material Output Displacement (off by default)
    if displacement and "displacement" in maps:
        disp_node = _add_image_node(maps["displacement"], -200, y_offset, non_color=True)
        disp_shader = nodes.new("ShaderNodeDisplacement")
        disp_shader.location = (300, y_offset)
        disp_shader.inputs["Scale"].default_value = 0.05
        links.new(disp_node.outputs["Color"], disp_shader.inputs["Height"])
        links.new(disp_shader.outputs["Displacement"], output.inputs["Displacement"])

    # Assign to object (replace all existing material slots)
    obj.data.materials.clear()
    obj.data.materials.append(mat)

    print(f"textures: applied {mat_name!r} with maps: {list(maps.keys())}")
    return mat
