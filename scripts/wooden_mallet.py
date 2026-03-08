import bpy
import bmesh
import math

# ─── Clear scene (including orphan data) ───
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
for c in list(bpy.data.collections):
    bpy.data.collections.remove(c)
# Purge orphan materials/meshes from previous runs
bpy.ops.outliner.orphans_purge(do_recursive=True)

# ─── Helpers ───
def get_or_create_collection(name):
    if name in bpy.data.collections:
        return bpy.data.collections[name]
    coll = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(coll)
    return coll

def move_to_collection(obj, coll_name):
    coll = get_or_create_collection(coll_name)
    for c in obj.users_collection:
        c.objects.unlink(obj)
    coll.objects.link(obj)

# ═══════════════════════════════════════════
#  MATERIALS — Rich procedural wood shaders
# ═══════════════════════════════════════════

def create_head_material():
    """Rich stump wood: vertical grain, knot patterns, bump detail."""
    mat = bpy.data.materials.new(name="wood_head")

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (1200, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (900, 0)
    bsdf.inputs["Roughness"].default_value = 0.92
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

    # ── Coordinate system: Object coords for consistent 3D mapping ──
    tex_coord = nodes.new("ShaderNodeTexCoord")
    tex_coord.location = (-1200, 0)

    mapping = nodes.new("ShaderNodeMapping")
    mapping.location = (-1000, 0)
    mapping.inputs["Scale"].default_value = (5.0, 5.0, 1.0)
    links.new(tex_coord.outputs["Object"], mapping.inputs["Vector"])

    # ── Layer 1: Base wood grain (wave bands + noise distortion) ──
    wave = nodes.new("ShaderNodeTexWave")
    wave.location = (-500, 200)
    wave.wave_type = "BANDS"
    wave.bands_direction = "X"
    wave.wave_profile = "SAW"
    wave.inputs["Scale"].default_value = 4.0
    wave.inputs["Distortion"].default_value = 6.0
    wave.inputs["Detail"].default_value = 3.0
    wave.inputs["Detail Scale"].default_value = 1.2

    noise_warp = nodes.new("ShaderNodeTexNoise")
    noise_warp.location = (-700, 100)
    noise_warp.inputs["Scale"].default_value = 2.5
    noise_warp.inputs["Detail"].default_value = 5.0
    noise_warp.inputs["Roughness"].default_value = 0.6
    links.new(mapping.outputs["Vector"], noise_warp.inputs["Vector"])

    # Mix noise into wave coords for organic warping
    mix_warp = nodes.new("ShaderNodeMix")
    mix_warp.location = (-600, 200)
    mix_warp.data_type = "VECTOR"
    mix_warp.inputs["Factor"].default_value = 0.12
    links.new(mapping.outputs["Vector"], mix_warp.inputs[4])
    links.new(noise_warp.outputs["Color"], mix_warp.inputs[5])
    links.new(mix_warp.outputs[1], wave.inputs["Vector"])

    # Grain color ramp
    grain_ramp = nodes.new("ShaderNodeValToRGB")
    grain_ramp.location = (-200, 200)
    grain_ramp.color_ramp.elements[0].position = 0.25
    grain_ramp.color_ramp.elements[0].color = (0.22, 0.13, 0.04, 1.0)  # dark grain
    grain_ramp.color_ramp.elements[1].position = 0.6
    grain_ramp.color_ramp.elements[1].color = (0.52, 0.35, 0.16, 1.0)  # light wood
    # Add mid tone
    mid = grain_ramp.color_ramp.elements.new(0.42)
    mid.color = (0.38, 0.24, 0.09, 1.0)
    links.new(wave.outputs["Fac"], grain_ramp.inputs["Fac"])

    # ── Layer 2: Wood knots (voronoi → concentric distortion) ──
    knot_mapping = nodes.new("ShaderNodeMapping")
    knot_mapping.location = (-1000, -300)
    knot_mapping.inputs["Scale"].default_value = (1.5, 1.5, 2.5)
    links.new(tex_coord.outputs["Object"], knot_mapping.inputs["Vector"])

    voronoi = nodes.new("ShaderNodeTexVoronoi")
    voronoi.location = (-700, -300)
    voronoi.feature = "F1"
    voronoi.inputs["Scale"].default_value = 2.0
    voronoi.inputs["Randomness"].default_value = 0.7
    links.new(knot_mapping.outputs["Vector"], voronoi.inputs["Vector"])

    # Use voronoi distance to create concentric ring pattern around each cell
    knot_wave = nodes.new("ShaderNodeTexWave")
    knot_wave.location = (-400, -300)
    knot_wave.wave_type = "RINGS"
    knot_wave.wave_profile = "SIN"
    knot_wave.inputs["Scale"].default_value = 12.0
    knot_wave.inputs["Distortion"].default_value = 3.0
    knot_wave.inputs["Detail"].default_value = 2.0

    # Feed voronoi position into wave for ring patterns centered at cells
    knot_mix_coord = nodes.new("ShaderNodeMix")
    knot_mix_coord.location = (-550, -350)
    knot_mix_coord.data_type = "VECTOR"
    knot_mix_coord.inputs["Factor"].default_value = 0.6
    links.new(knot_mapping.outputs["Vector"], knot_mix_coord.inputs[4])
    links.new(voronoi.outputs["Position"], knot_mix_coord.inputs[5])
    links.new(knot_mix_coord.outputs[1], knot_wave.inputs["Vector"])

    # Knot color ramp — darker rings
    knot_ramp = nodes.new("ShaderNodeValToRGB")
    knot_ramp.location = (-200, -300)
    knot_ramp.color_ramp.elements[0].position = 0.25
    knot_ramp.color_ramp.elements[0].color = (0.12, 0.06, 0.02, 1.0)
    knot_ramp.color_ramp.elements[1].position = 0.65
    knot_ramp.color_ramp.elements[1].color = (0.38, 0.24, 0.10, 1.0)
    links.new(knot_wave.outputs["Fac"], knot_ramp.inputs["Fac"])

    # Knot mask — where knots appear (near voronoi cell centers)
    knot_mask_ramp = nodes.new("ShaderNodeValToRGB")
    knot_mask_ramp.location = (-400, -450)
    knot_mask_ramp.color_ramp.elements[0].position = 0.0
    knot_mask_ramp.color_ramp.elements[0].color = (1, 1, 1, 1)
    knot_mask_ramp.color_ramp.elements[1].position = 0.5
    knot_mask_ramp.color_ramp.elements[1].color = (0, 0, 0, 1)
    links.new(voronoi.outputs["Distance"], knot_mask_ramp.inputs["Fac"])

    # ── Combine grain + knots ──
    mix_color = nodes.new("ShaderNodeMix")
    mix_color.location = (300, 100)
    mix_color.data_type = "RGBA"
    links.new(knot_mask_ramp.outputs["Color"], mix_color.inputs["Factor"])
    links.new(grain_ramp.outputs["Color"], mix_color.inputs[6])
    links.new(knot_ramp.outputs["Color"], mix_color.inputs[7])

    # ── Layer 3: Large-scale color variation (warm/cool shifts across surface) ──
    noise_large = nodes.new("ShaderNodeTexNoise")
    noise_large.location = (-500, -550)
    noise_large.inputs["Scale"].default_value = 1.5
    noise_large.inputs["Detail"].default_value = 2.0
    noise_large.inputs["Roughness"].default_value = 0.5
    links.new(mapping.outputs["Vector"], noise_large.inputs["Vector"])

    large_ramp = nodes.new("ShaderNodeValToRGB")
    large_ramp.location = (-200, -550)
    large_ramp.color_ramp.elements[0].position = 0.35
    large_ramp.color_ramp.elements[0].color = (0.90, 0.85, 0.75, 1.0)  # warm tint
    large_ramp.color_ramp.elements[1].position = 0.65
    large_ramp.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)     # neutral
    links.new(noise_large.outputs["Fac"], large_ramp.inputs["Fac"])

    # Multiply color variation into base
    mix_variation = nodes.new("ShaderNodeMix")
    mix_variation.location = (500, 50)
    mix_variation.data_type = "RGBA"
    mix_variation.blend_type = "MULTIPLY"
    mix_variation.inputs["Factor"].default_value = 0.4
    links.new(mix_color.outputs[2], mix_variation.inputs[6])
    links.new(large_ramp.outputs["Color"], mix_variation.inputs[7])
    links.new(mix_variation.outputs[2], bsdf.inputs["Base Color"])

    # ── Subsurface scattering — wood warmth/translucency ──
    bsdf.inputs["Subsurface Weight"].default_value = 0.08
    bsdf.inputs["Subsurface Radius"].default_value = (0.5, 0.25, 0.1)
    # Subsurface color: warm orange-brown
    bsdf.inputs["Subsurface Scale"].default_value = 0.05

    # ── Roughness map — grain-driven variation ──
    rough_ramp = nodes.new("ShaderNodeValToRGB")
    rough_ramp.location = (400, -400)
    rough_ramp.color_ramp.elements[0].position = 0.3
    rough_ramp.color_ramp.elements[0].color = (0.82, 0.82, 0.82, 1.0)  # grain valleys rougher
    rough_ramp.color_ramp.elements[1].position = 0.7
    rough_ramp.color_ramp.elements[1].color = (0.95, 0.95, 0.95, 1.0)  # grain peaks roughest
    links.new(wave.outputs["Fac"], rough_ramp.inputs["Fac"])
    links.new(rough_ramp.outputs["Color"], bsdf.inputs["Roughness"])

    # ── Fine surface noise for natural micro-variation ──
    noise_fine = nodes.new("ShaderNodeTexNoise")
    noise_fine.location = (-500, -700)
    noise_fine.inputs["Scale"].default_value = 15.0
    noise_fine.inputs["Detail"].default_value = 8.0
    noise_fine.inputs["Roughness"].default_value = 0.7
    links.new(mapping.outputs["Vector"], noise_fine.inputs["Vector"])

    # ── Bump: grain + knots + fine noise for layered depth ──
    bump_grain = nodes.new("ShaderNodeMath")
    bump_grain.location = (400, -200)
    bump_grain.operation = "ADD"
    links.new(wave.outputs["Fac"], bump_grain.inputs[0])
    links.new(noise_fine.outputs["Fac"], bump_grain.inputs[1])

    # Add knot bump layer
    bump_knot = nodes.new("ShaderNodeMath")
    bump_knot.location = (500, -250)
    bump_knot.operation = "MULTIPLY"
    links.new(knot_wave.outputs["Fac"], bump_knot.inputs[0])
    links.new(knot_mask_ramp.outputs["Color"], bump_knot.inputs[1])

    bump_total = nodes.new("ShaderNodeMath")
    bump_total.location = (600, -200)
    bump_total.operation = "ADD"
    links.new(bump_grain.outputs["Value"], bump_total.inputs[0])
    links.new(bump_knot.outputs["Value"], bump_total.inputs[1])

    bump = nodes.new("ShaderNodeBump")
    bump.location = (750, -200)
    bump.inputs["Strength"].default_value = 0.18
    bump.inputs["Distance"].default_value = 0.01
    links.new(bump_total.outputs["Value"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    return mat


def create_handle_material():
    """Worn handle wood: straight grain along length, darker than head."""
    mat = bpy.data.materials.new(name="wood_handle")

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (1200, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (900, 0)
    bsdf.inputs["Roughness"].default_value = 0.95
    bsdf.inputs["Specular IOR Level"].default_value = 0.0
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

    # Subtle subsurface for wood warmth
    bsdf.inputs["Subsurface Weight"].default_value = 0.04
    bsdf.inputs["Subsurface Radius"].default_value = (0.4, 0.2, 0.08)
    bsdf.inputs["Subsurface Scale"].default_value = 0.03

    tex_coord = nodes.new("ShaderNodeTexCoord")
    tex_coord.location = (-1100, 0)

    # Handle along X: stretch radially (Y/Z high), keep X low = grain along length
    # Same logic as head material but rotated 90°
    mapping = nodes.new("ShaderNodeMapping")
    mapping.location = (-900, 0)
    mapping.inputs["Scale"].default_value = (1.0, 5.0, 5.0)
    links.new(tex_coord.outputs["Object"], mapping.inputs["Vector"])

    # ── Primary grain: bands perpendicular to Y = lines along X on cylinder ──
    wave = nodes.new("ShaderNodeTexWave")
    wave.location = (-400, 200)
    wave.wave_type = "BANDS"
    wave.bands_direction = "Y"
    wave.wave_profile = "SAW"
    wave.inputs["Scale"].default_value = 4.0
    wave.inputs["Distortion"].default_value = 4.0
    wave.inputs["Detail"].default_value = 2.0
    wave.inputs["Detail Scale"].default_value = 1.0

    # Gentle organic warping
    noise_warp = nodes.new("ShaderNodeTexNoise")
    noise_warp.location = (-700, 150)
    noise_warp.inputs["Scale"].default_value = 2.5
    noise_warp.inputs["Detail"].default_value = 4.0
    noise_warp.inputs["Roughness"].default_value = 0.5
    links.new(mapping.outputs["Vector"], noise_warp.inputs["Vector"])

    mix_warp = nodes.new("ShaderNodeMix")
    mix_warp.location = (-500, 200)
    mix_warp.data_type = "VECTOR"
    mix_warp.inputs["Factor"].default_value = 0.08
    links.new(mapping.outputs["Vector"], mix_warp.inputs[4])
    links.new(noise_warp.outputs["Color"], mix_warp.inputs[5])
    links.new(mix_warp.outputs[1], wave.inputs["Vector"])

    # ── Secondary: finer grain detail ──
    wave2 = nodes.new("ShaderNodeTexWave")
    wave2.location = (-400, 0)
    wave2.wave_type = "BANDS"
    wave2.bands_direction = "Y"
    wave2.wave_profile = "SIN"
    wave2.inputs["Scale"].default_value = 7.0
    wave2.inputs["Distortion"].default_value = 2.0
    wave2.inputs["Detail"].default_value = 1.0
    links.new(mix_warp.outputs[1], wave2.inputs["Vector"])

    # Blend: primary + 25% secondary
    grain_scale = nodes.new("ShaderNodeMath")
    grain_scale.location = (-200, 0)
    grain_scale.operation = "MULTIPLY"
    grain_scale.inputs[1].default_value = 0.25
    links.new(wave2.outputs["Fac"], grain_scale.inputs[0])

    grain_mix = nodes.new("ShaderNodeMath")
    grain_mix.location = (-100, 150)
    grain_mix.operation = "ADD"
    grain_mix.use_clamp = True
    links.new(wave.outputs["Fac"], grain_mix.inputs[0])
    links.new(grain_scale.outputs["Value"], grain_mix.inputs[1])

    # Color ramp — tight range, all dark tones to avoid bright spots under light
    grain_ramp = nodes.new("ShaderNodeValToRGB")
    grain_ramp.location = (100, 200)
    grain_ramp.color_ramp.elements[0].position = 0.25
    grain_ramp.color_ramp.elements[0].color = (0.10, 0.05, 0.02, 1.0)   # dark grain line
    mid = grain_ramp.color_ramp.elements.new(0.45)
    mid.color = (0.16, 0.09, 0.04, 1.0)                                  # mid tone
    grain_ramp.color_ramp.elements[1].position = 0.65
    grain_ramp.color_ramp.elements[1].color = (0.20, 0.12, 0.05, 1.0)   # lighter (still dark)
    links.new(grain_mix.outputs["Value"], grain_ramp.inputs["Fac"])

    # Direct grain to base color — no variation layer needed on small handle
    links.new(grain_ramp.outputs["Color"], bsdf.inputs["Base Color"])

    # Flat roughness — no variation map, avoids specular hotspots on small handle

    # No bump on handle — too small, bump creates white highlight artifacts

    return mat


def create_bark_material():
    """Dark rough bark for worn edges — very dark, rough texture."""
    mat = bpy.data.materials.new(name="wood_bark")

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (900, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (600, 0)
    bsdf.inputs["Roughness"].default_value = 0.98
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

    tex_coord = nodes.new("ShaderNodeTexCoord")
    tex_coord.location = (-800, 0)

    mapping = nodes.new("ShaderNodeMapping")
    mapping.location = (-600, 0)
    mapping.inputs["Scale"].default_value = (3.0, 3.0, 2.0)
    links.new(tex_coord.outputs["Object"], mapping.inputs["Vector"])

    # Rough chunky noise
    noise1 = nodes.new("ShaderNodeTexNoise")
    noise1.location = (-300, 100)
    noise1.inputs["Scale"].default_value = 8.0
    noise1.inputs["Detail"].default_value = 6.0
    noise1.inputs["Roughness"].default_value = 0.8
    links.new(mapping.outputs["Vector"], noise1.inputs["Vector"])

    # Voronoi for cracked surface
    voronoi = nodes.new("ShaderNodeTexVoronoi")
    voronoi.location = (-300, -100)
    voronoi.feature = "F1"
    voronoi.inputs["Scale"].default_value = 12.0
    links.new(mapping.outputs["Vector"], voronoi.inputs["Vector"])

    # Combine noise + voronoi
    mix_tex = nodes.new("ShaderNodeMix")
    mix_tex.location = (0, 0)
    mix_tex.data_type = "FLOAT"
    mix_tex.inputs["Factor"].default_value = 0.4
    links.new(noise1.outputs["Fac"], mix_tex.inputs[2])
    links.new(voronoi.outputs["Distance"], mix_tex.inputs[3])

    # Very dark bark colors
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.location = (200, 0)
    ramp.color_ramp.elements[0].position = 0.2
    ramp.color_ramp.elements[0].color = (0.06, 0.03, 0.01, 1.0)
    ramp.color_ramp.elements[1].position = 0.7
    ramp.color_ramp.elements[1].color = (0.16, 0.09, 0.03, 1.0)
    links.new(mix_tex.outputs[0], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])

    # Strong bump for rough surface
    bump = nodes.new("ShaderNodeBump")
    bump.location = (400, -150)
    bump.inputs["Strength"].default_value = 0.3
    bump.inputs["Distance"].default_value = 0.015
    links.new(mix_tex.outputs[0], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    return mat


# ─── Create materials ───
mat_head = create_head_material()
mat_handle = create_handle_material()
mat_bark = create_bark_material()

# ═══════════════════════════════════════════
#  GEOMETRY
# ═══════════════════════════════════════════

# ─── Dimensions ───
HEAD_RADIUS = 0.28
HEAD_HEIGHT = 0.65
HEAD_SEGMENTS = 28

HANDLE_RADIUS = 0.045
HANDLE_LENGTH = 0.85
HANDLE_SEGMENTS = 16

HEAD_Z = HEAD_HEIGHT / 2
HANDLE_Z = HEAD_HEIGHT * 0.48

# ─── Hammer Head ───
# Build with bmesh for full control over edge bevels and material assignment
bpy.ops.mesh.primitive_cylinder_add(
    vertices=HEAD_SEGMENTS,
    radius=HEAD_RADIUS,
    depth=HEAD_HEIGHT,
    location=(0, 0, HEAD_Z)
)
head = bpy.context.active_object
head.name = "mallet_head"
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

# Two material slots: 0=head wood, 1=bark (for edge faces)
head.data.materials.append(mat_head)
head.data.materials.append(mat_bark)

bm = bmesh.new()
bm.from_mesh(head.data)

# Subdivide along height — a plain cylinder has no mid-height verts to deform
bm.verts.ensure_lookup_table()
top_z = max(v.co.z for v in bm.verts)
bot_z = min(v.co.z for v in bm.verts)
# Select vertical edges (connect top ring to bottom ring)
vert_edges = [e for e in bm.edges
              if abs(e.verts[0].co.z - e.verts[1].co.z) > 0.01]
bmesh.ops.subdivide_edges(bm, edges=vert_edges, cuts=6)

bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()

# Inverted barrel — middle worn inward from use, edges stay wider
for v in bm.verts:
    z = v.co.z
    t = (z + HEAD_HEIGHT / 2) / HEAD_HEIGHT  # 0=bottom, 1=top
    # Concave: pinch inward at center, wider at edges
    concave = 1.0 - 0.10 * (1.0 - (2.0 * t - 1.0) ** 2)
    dist = math.sqrt(v.co.x ** 2 + v.co.y ** 2)
    if dist > 0.01:
        v.co.x *= concave
        v.co.y *= concave

# Find top and bottom edge loops after deformation
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
top_z = max(v.co.z for v in bm.verts)
bot_z = min(v.co.z for v in bm.verts)

top_edges = [e for e in bm.edges
             if all(abs(v.co.z - top_z) < 0.001 for v in e.verts)
             and all(math.sqrt(v.co.x**2 + v.co.y**2) > 0.01 for v in e.verts)]
bot_edges = [e for e in bm.edges
             if all(abs(v.co.z - bot_z) < 0.001 for v in e.verts)
             and all(math.sqrt(v.co.x**2 + v.co.y**2) > 0.01 for v in e.verts)]

# Bevel both edges equally — worn flat look
for edges in [top_edges, bot_edges]:
    if edges:
        result = bmesh.ops.bevel(bm, geom=edges, offset=0.032, segments=3,
                                 affect='EDGES', profile=0.5)
        for f in result.get("faces", []):
            f.material_index = 1

bm.to_mesh(head.data)
bm.free()

bpy.ops.object.shade_smooth()
move_to_collection(head, "Mallet")

# ─── Handle ───
bpy.ops.mesh.primitive_cylinder_add(
    vertices=HANDLE_SEGMENTS,
    radius=HANDLE_RADIUS,
    depth=HANDLE_LENGTH,
    location=(0, 0, 0),
    rotation=(0, math.radians(90), 0)
)
handle = bpy.context.active_object
handle.name = "mallet_handle"

handle_center_x = -(HANDLE_LENGTH / 2 - HEAD_RADIUS * 0.35)
handle.location = (handle_center_x, 0, HANDLE_Z)
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

# Add edge loops along handle length for smooth shading
bm = bmesh.new()
bm.from_mesh(handle.data)
bm.edges.ensure_lookup_table()

# Subdivide horizontal edges (the ones along the length)
horiz_edges = [e for e in bm.edges
               if abs(e.verts[0].co.z - e.verts[1].co.z) > 0.001
               or abs(e.verts[0].co.y - e.verts[1].co.y) > 0.001]
# Actually: subdivide the vertical edges (along X = handle axis)
long_edges = [e for e in bm.edges
              if abs(e.verts[0].co.x - e.verts[1].co.x) > 0.01]
bmesh.ops.subdivide_edges(bm, edges=long_edges, cuts=4)

bm.verts.ensure_lookup_table()

# Taper handle
for v in bm.verts:
    t = (v.co.x + HANDLE_LENGTH / 2) / HANDLE_LENGTH  # 0=grip, 1=head
    scale_factor = 0.80 + 0.30 * t  # 0.80 at grip, 1.10 at head
    v.co.y *= scale_factor
    v.co.z *= scale_factor

bm.to_mesh(handle.data)
bm.free()

bpy.ops.object.shade_smooth()
handle.data.materials.append(mat_handle)
move_to_collection(handle, "Mallet")

# ─── Handle grip end — smooth rounded cap ───
grip_x = handle_center_x - HANDLE_LENGTH / 2
grip_radius = HANDLE_RADIUS * 0.80
bpy.ops.mesh.primitive_uv_sphere_add(
    segments=12, ring_count=6,
    radius=grip_radius,
    location=(grip_x, 0, HANDLE_Z)
)
grip = bpy.context.active_object
grip.name = "handle_grip"
grip.scale = (0.55, 1.0, 1.0)
bpy.ops.object.transform_apply(scale=True)
bpy.ops.object.shade_smooth()
grip.data.materials.append(mat_handle)
move_to_collection(grip, "Mallet")

# ─── Handle-head smooth transition ───
junction_x = handle_center_x + HANDLE_LENGTH / 2 - HEAD_RADIUS * 0.28
bpy.ops.mesh.primitive_torus_add(
    major_segments=HANDLE_SEGMENTS,
    minor_segments=6,
    major_radius=HANDLE_RADIUS * 1.10,
    minor_radius=HANDLE_RADIUS * 0.40,
    location=(junction_x, 0, HANDLE_Z),
    rotation=(0, math.radians(90), 0)
)
junction = bpy.context.active_object
junction.name = "handle_junction"
bpy.ops.object.shade_smooth()
junction.data.materials.append(mat_handle)
move_to_collection(junction, "Mallet")

# ─── Parent everything to head ───
bpy.ops.object.select_all(action='DESELECT')
for obj in bpy.data.collections["Mallet"].objects:
    if obj != head:
        obj.select_set(True)
bpy.context.view_layer.objects.active = head
head.select_set(True)
bpy.ops.object.parent_set(type='OBJECT')
bpy.ops.object.select_all(action='DESELECT')

# ─── Lighting (soft, diffuse — lets wood detail show) ───
# Key light: softer sun, lower energy
bpy.ops.object.light_add(type='SUN', location=(3, -2, 5))
sun = bpy.context.active_object
sun.name = "key_light"
sun.data.energy = 1.8
sun.data.angle = math.radians(15)  # softer shadows
sun.rotation_euler = (math.radians(50), math.radians(10), math.radians(-25))

# Fill light: strong fill to reduce harsh shadows
bpy.ops.object.light_add(type='SUN', location=(-3, 2, 3))
fill = bpy.context.active_object
fill.name = "fill_light"
fill.data.energy = 1.5
fill.data.angle = math.radians(30)
fill.rotation_euler = (math.radians(55), math.radians(-15), math.radians(150))

# Rim light: subtle backlight for silhouette
bpy.ops.object.light_add(type='SUN', location=(-1, -3, 4))
rim = bpy.context.active_object
rim.name = "rim_light"
rim.data.energy = 0.8
rim.data.angle = math.radians(20)
rim.rotation_euler = (math.radians(35), math.radians(25), math.radians(200))

# Warmer, brighter ambient
world = bpy.context.scene.world
if world is None:
    world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world

bg = world.node_tree.nodes["Background"]
bg.inputs["Color"].default_value = (0.18, 0.16, 0.14, 1.0)
bg.inputs["Strength"].default_value = 0.5

print("Wooden mallet created!")
