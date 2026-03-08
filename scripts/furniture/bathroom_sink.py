import bpy
import bmesh
import math

# ============================================================
# HELPERS
# ============================================================

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


def apply_and_finish(obj, material, coll_name):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bpy.ops.object.shade_flat()
    if material is not None:
        if len(obj.data.materials) == 0:
            obj.data.materials.append(material)
        else:
            obj.data.materials[0] = material
    move_to_collection(obj, coll_name)
    return obj


def make_box(name, cx, cy, cz, sx, sy, sz, material, collection):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(cx, cy, cz))
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (sx, sy, sz)
    return apply_and_finish(obj, material, collection)


def make_cylinder(name, cx, cy, cz, radius, depth, verts, rot_x, rot_z, material, collection):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=verts, radius=radius, depth=depth,
        location=(cx, cy, cz),
        rotation=(rot_x, 0, rot_z)
    )
    obj = bpy.context.active_object
    obj.name = name
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    bpy.ops.object.shade_flat()
    if material is not None:
        if len(obj.data.materials) == 0:
            obj.data.materials.append(material)
        else:
            obj.data.materials[0] = material
    move_to_collection(obj, collection)
    return obj


# ============================================================
# MATERIALS
# ============================================================

def mat(name, color, roughness=0.8, metallic=0.0):
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return m


mat_porcelain = mat("sink_porcelain", (0.95, 0.95, 0.93), roughness=0.2)
mat_faucet    = mat("sink_faucet",    (0.70, 0.70, 0.72), roughness=0.15, metallic=0.8)
mat_mirror    = mat("sink_mirror",    (0.70, 0.80, 0.90), roughness=0.05, metallic=0.8)
mat_knob      = mat("sink_knob",      (0.65, 0.65, 0.67), roughness=0.2, metallic=0.6)

COLL = "Bathroom_Sink"

# ============================================================
# DIMENSIONS
# ============================================================
# Sink is centered at X=0, Y=0.
# The basin "back" (wall side) is at +Y, front hangs forward toward -Y.
# Bottom at Z=0.

WALL_Y = 0.05   # Y offset of the back of the pedestal from world center

# --- Pedestal column ---
PED_W     = 0.10
PED_D     = 0.10
PED_H     = 0.80
PED_CY    = WALL_Y - PED_D / 2   # back flush with wall side

# --- Basin — flared box, wider than pedestal, low profile ---
BASIN_W_BOT = 0.42  # X width at basin base
BASIN_W_TOP = 0.50  # X width at rim (flared)
BASIN_D_BOT = 0.28  # Y depth at base
BASIN_D_TOP = 0.34  # Y depth at rim
BASIN_H     = 0.15  # height of basin
BASIN_Z     = PED_H # bottom of basin sits on top of pedestal

# Basin center Y: back aligned with back of pedestal, front overhangs forward
BASIN_CY    = PED_CY

# Basin hollow (inset box representing the interior well)
HOLLOW_W    = 0.30
HOLLOW_D    = 0.20
HOLLOW_H    = 0.03
HOLLOW_Z    = BASIN_Z + BASIN_H - HOLLOW_H / 2
HOLLOW_CY   = BASIN_CY - 0.01  # slightly toward front

# Drain — tiny dark cylinder in the bottom of the hollow
DRAIN_R     = 0.018
DRAIN_Z     = BASIN_Z + 0.01

# --- Faucet (centered over basin near back) ---
PIPE_R      = 0.018
PIPE_H      = 0.12
PIPE_CX     = 0.0
PIPE_CY     = BASIN_CY + BASIN_D_TOP * 0.3
PIPE_CZ     = BASIN_Z + BASIN_H + PIPE_H / 2

SPOUT_W     = 0.025
SPOUT_D     = 0.10
SPOUT_H     = 0.022

# --- Knob handles — left and right of faucet ---
KNOB_R      = 0.022
KNOB_H      = 0.035
KNOB_X_OFF  = 0.09   # X distance from center

# --- Mirror above basin ---
MIRROR_W    = 0.50
MIRROR_H_DIM = 0.60
MIRROR_T    = 0.018
MIRROR_CZ   = 1.50   # center Z height (~1.2 to 1.8 range)
MIRROR_CY   = WALL_Y  # slight offset from wall

# ============================================================
# 1. PEDESTAL — narrow column from floor to basin
# ============================================================
make_box(
    "sink_pedestal",
    0, PED_CY, PED_H / 2,
    PED_W, PED_D, PED_H,
    mat_porcelain, COLL
)

# ============================================================
# 2. BASIN — flared box via bmesh (wider at top than bottom)
# ============================================================
basin_mesh = bpy.data.meshes.new("sink_basin_mesh")
basin_obj  = bpy.data.objects.new("sink_basin", basin_mesh)
bpy.context.scene.collection.objects.link(basin_obj)

bm = bmesh.new()

hw_bot = BASIN_W_BOT / 2
hd_bot = BASIN_D_BOT / 2
hw_top = BASIN_W_TOP / 2
hd_top = BASIN_D_TOP / 2
cy     = BASIN_CY
bz     = BASIN_Z
th     = BASIN_H

# Bottom ring (4 verts)
B = [
    bm.verts.new((-hw_bot, cy - hd_bot, bz)),
    bm.verts.new(( hw_bot, cy - hd_bot, bz)),
    bm.verts.new(( hw_bot, cy + hd_bot, bz)),
    bm.verts.new((-hw_bot, cy + hd_bot, bz)),
]
# Top ring (4 verts, flared)
T = [
    bm.verts.new((-hw_top, cy - hd_top, bz + th)),
    bm.verts.new(( hw_top, cy - hd_top, bz + th)),
    bm.verts.new(( hw_top, cy + hd_top, bz + th)),
    bm.verts.new((-hw_top, cy + hd_top, bz + th)),
]

bm.verts.ensure_lookup_table()

# Bottom face
bm.faces.new([B[0], B[3], B[2], B[1]])
# Top face
bm.faces.new([T[0], T[1], T[2], T[3]])
# Four side faces
for i in range(4):
    j = (i + 1) % 4
    bm.faces.new([B[i], B[j], T[j], T[i]])

bm.to_mesh(basin_mesh)
bm.free()

bpy.ops.object.select_all(action='DESELECT')
basin_obj.select_set(True)
bpy.context.view_layer.objects.active = basin_obj
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
bpy.ops.object.shade_flat()
basin_obj.data.materials.append(mat_porcelain)
move_to_collection(basin_obj, COLL)
if basin_obj.name in bpy.context.scene.collection.objects:
    bpy.context.scene.collection.objects.unlink(basin_obj)

# ============================================================
# 3. BASIN HOLLOW — dark inset box showing the interior
# ============================================================
mat_hollow = mat("sink_hollow", (0.25, 0.30, 0.35), roughness=0.5)
make_box(
    "sink_basin_hollow",
    0, HOLLOW_CY, HOLLOW_Z,
    HOLLOW_W, HOLLOW_D, HOLLOW_H,
    mat_hollow, COLL
)

# Drain dot inside the hollow
mat_drain = mat("sink_drain", (0.15, 0.15, 0.16), roughness=0.3, metallic=0.5)
make_cylinder(
    "sink_drain",
    0, HOLLOW_CY, DRAIN_Z,
    radius=DRAIN_R, depth=0.015, verts=8,
    rot_x=0.0, rot_z=0.0,
    material=mat_drain, collection=COLL
)

# ============================================================
# 4. FAUCET RISER
# ============================================================
make_cylinder(
    "sink_faucet_riser",
    PIPE_CX, PIPE_CY, PIPE_CZ,
    radius=PIPE_R, depth=PIPE_H, verts=8,
    rot_x=0.0, rot_z=0.0,
    material=mat_faucet, collection=COLL
)

# Angled spout — angled forward and downward
SPOUT_CY = PIPE_CY - SPOUT_D * 0.45
SPOUT_CZ = BASIN_Z + BASIN_H + PIPE_H - 0.02

bpy.ops.mesh.primitive_cube_add(
    size=1,
    location=(PIPE_CX, SPOUT_CY, SPOUT_CZ)
)
spout = bpy.context.active_object
spout.name = "sink_faucet_spout"
spout.scale = (SPOUT_W, SPOUT_D, SPOUT_H)
spout.rotation_euler = (math.radians(-25), 0, 0)
bpy.ops.object.select_all(action='DESELECT')
spout.select_set(True)
bpy.context.view_layer.objects.active = spout
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
bpy.ops.object.shade_flat()
spout.data.materials.append(mat_faucet)
move_to_collection(spout, COLL)

# ============================================================
# 5. KNOB HANDLES — linked duplicates, left and right of faucet
# ============================================================
KNOB_CY  = PIPE_CY
KNOB_CZ  = BASIN_Z + BASIN_H + KNOB_H / 2 + 0.01

# Base knob (left)
make_cylinder(
    "sink_knob_L",
    -KNOB_X_OFF, KNOB_CY, KNOB_CZ,
    radius=KNOB_R, depth=KNOB_H, verts=8,
    rot_x=0.0, rot_z=0.0,
    material=mat_knob, collection=COLL
)

# Get the left knob object to use as linked duplicate source
knob_L = bpy.data.objects.get("sink_knob_L")

# Right knob as linked duplicate
bpy.ops.object.select_all(action='DESELECT')
knob_L.select_set(True)
bpy.context.view_layer.objects.active = knob_L
bpy.ops.object.duplicate(linked=True)
knob_R = bpy.context.active_object
knob_R.name = "sink_knob_R"
knob_R.location = (KNOB_X_OFF, KNOB_CY, KNOB_CZ)
move_to_collection(knob_R, COLL)

# ============================================================
# 6. MIRROR — thin reflective rectangle above the basin
# ============================================================
# The mirror frame: slightly larger box in a dark mat, then mirror surface on top
FRAME_T   = 0.015
FRAME_W   = MIRROR_W + FRAME_T * 2
FRAME_H   = MIRROR_H_DIM + FRAME_T * 2
MIRROR_Y  = MIRROR_CY - MIRROR_T / 2 - 0.005  # just in front of wall

mat_frame = mat("sink_mirror_frame", (0.20, 0.20, 0.20), roughness=0.6)

make_box(
    "sink_mirror_frame",
    0, MIRROR_Y - 0.003, MIRROR_CZ,
    FRAME_W, MIRROR_T * 0.5, FRAME_H,
    mat_frame, COLL
)

make_box(
    "sink_mirror",
    0, MIRROR_Y, MIRROR_CZ,
    MIRROR_W, MIRROR_T, MIRROR_H_DIM,
    mat_mirror, COLL
)

# ============================================================
# DONE
# ============================================================
bpy.ops.object.select_all(action='DESELECT')
print("Bathroom sink created successfully.")
