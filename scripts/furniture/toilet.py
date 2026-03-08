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


def make_cylinder(name, cx, cy, cz, radius, depth, verts, rot_x, material, collection):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=verts, radius=radius, depth=depth,
        location=(cx, cy, cz),
        rotation=(rot_x, 0, 0)
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


mat_porcelain = mat("toilet_porcelain",   (0.95, 0.95, 0.93), roughness=0.2)
mat_seat      = mat("toilet_seat",        (0.92, 0.92, 0.90), roughness=0.35)
mat_water     = mat("toilet_water",       (0.60, 0.75, 0.85), roughness=0.1)
mat_handle    = mat("toilet_handle",      (0.70, 0.70, 0.72), roughness=0.2, metallic=0.6)

COLL = "Toilet"

# ============================================================
# DIMENSIONS
# ============================================================
# Overall toilet is centered at X=0, Y=0, bottom at Z=0.
# Bowl faces forward (-Y), tank is at the back (+Y).

# --- Pedestal / base ---
PED_W_BOT = 0.38   # X at floor level
PED_L_BOT = 0.52   # Y at floor level
PED_W_TOP = 0.32   # X at top of pedestal
PED_L_TOP = 0.46   # Y
PED_H     = 0.38   # height of pedestal up to bowl underside

# --- Bowl box (sits on top of pedestal) ---
BOWL_W    = 0.34
BOWL_L    = 0.50   # total front-to-back
BOWL_H    = 0.18
BOWL_Z    = PED_H  # bottom of bowl at top of pedestal

# Bowl is shifted forward (toward -Y) so tank can be behind
BOWL_CY   = -0.04

# Hollow inside the bowl — darker inset box representing the interior
HOLLOW_W  = 0.22
HOLLOW_L  = 0.30
HOLLOW_H  = 0.04  # thin slab just under the rim level
HOLLOW_Z  = BOWL_Z + BOWL_H - HOLLOW_H / 2

# Water inside the bowl — sits inside the hollow
WATER_W   = 0.18
WATER_L   = 0.24
WATER_Z   = BOWL_Z + BOWL_H * 0.4

# --- Seat --- (thin ring on top of bowl)
SEAT_W    = BOWL_W + 0.01
SEAT_L    = BOWL_L * 0.88
SEAT_H    = 0.025
SEAT_Z    = BOWL_Z + BOWL_H  # sits on top of bowl

# Seat opening (darker box inside the seat)
SEAT_HOLE_W = HOLLOW_W + 0.01
SEAT_HOLE_L = HOLLOW_L + 0.01
SEAT_HOLE_H = SEAT_H + 0.002

# --- Lid --- (flat box, slightly tilted back)
LID_W     = SEAT_W
LID_L     = SEAT_L
LID_H     = 0.025

# --- Tank --- (box at the back)
TANK_W    = 0.30
TANK_L    = 0.16
TANK_H    = 0.38
TANK_CY   = BOWL_CY + BOWL_L / 2 - TANK_L / 2  # flush with back of bowl footprint
TANK_CZ   = PED_H + TANK_H / 2

# Flush handle on right side of tank
HANDLE_L  = 0.06
HANDLE_R  = 0.012
HANDLE_CX = TANK_W / 2 + HANDLE_L / 2
HANDLE_CY = TANK_CY + TANK_L * 0.1
HANDLE_CZ = PED_H + TANK_H - 0.06

# ============================================================
# 1. PEDESTAL — tapered via bmesh (wider at bottom)
# ============================================================
ped_mesh = bpy.data.meshes.new("toilet_pedestal_mesh")
ped_obj  = bpy.data.objects.new("toilet_pedestal", ped_mesh)
bpy.context.scene.collection.objects.link(ped_obj)

bm = bmesh.new()

hw_bot = PED_W_BOT / 2
hl_bot = PED_L_BOT / 2
hw_top = PED_W_TOP / 2
hl_top = PED_L_TOP / 2

# Bottom verts (wider), shifted to center bowl footprint
cy_offset = BOWL_CY * 0.3  # slight centering shift

B = [
    bm.verts.new((-hw_bot, -hl_bot + cy_offset, 0)),
    bm.verts.new(( hw_bot, -hl_bot + cy_offset, 0)),
    bm.verts.new(( hw_bot,  hl_bot + cy_offset, 0)),
    bm.verts.new((-hw_bot,  hl_bot + cy_offset, 0)),
]
T = [
    bm.verts.new((-hw_top, -hl_top + cy_offset, PED_H)),
    bm.verts.new(( hw_top, -hl_top + cy_offset, PED_H)),
    bm.verts.new(( hw_top,  hl_top + cy_offset, PED_H)),
    bm.verts.new((-hw_top,  hl_top + cy_offset, PED_H)),
]

bm.verts.ensure_lookup_table()

# Bottom face
bm.faces.new([B[0], B[3], B[2], B[1]])
# Top face
bm.faces.new([T[0], T[1], T[2], T[3]])
# Side faces
for i in range(4):
    j = (i + 1) % 4
    bm.faces.new([B[i], B[j], T[j], T[i]])

bm.to_mesh(ped_mesh)
bm.free()

bpy.ops.object.select_all(action='DESELECT')
ped_obj.select_set(True)
bpy.context.view_layer.objects.active = ped_obj
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
bpy.ops.object.shade_flat()
ped_obj.data.materials.append(mat_porcelain)
move_to_collection(ped_obj, COLL)
if ped_obj.name in bpy.context.scene.collection.objects:
    bpy.context.scene.collection.objects.unlink(ped_obj)

# ============================================================
# 2. BOWL BOX
# ============================================================
make_box(
    "toilet_bowl",
    0, BOWL_CY, BOWL_Z + BOWL_H / 2,
    BOWL_W, BOWL_L, BOWL_H,
    mat_porcelain, COLL
)

# ============================================================
# 3. HOLLOW INTERIOR (dark inset box showing the opening)
# ============================================================
mat_hollow = mat("toilet_hollow", (0.30, 0.40, 0.45), roughness=0.5)
make_box(
    "toilet_bowl_hollow",
    0, BOWL_CY - 0.02, HOLLOW_Z,
    HOLLOW_W, HOLLOW_L, HOLLOW_H,
    mat_hollow, COLL
)

# ============================================================
# 4. WATER INSIDE BOWL
# ============================================================
make_box(
    "toilet_water",
    0, BOWL_CY - 0.02, WATER_Z,
    WATER_W, WATER_L, 0.01,
    mat_water, COLL
)

# ============================================================
# 5. SEAT — ring shape: outer box + hole inset box on top
# ============================================================
make_box(
    "toilet_seat",
    0, BOWL_CY, SEAT_Z + SEAT_H / 2,
    SEAT_W, SEAT_L, SEAT_H,
    mat_seat, COLL
)

# Seat hole — slightly darker inset to imply the opening
mat_seat_hole = mat("toilet_seat_hole", (0.15, 0.15, 0.15), roughness=0.6)
make_box(
    "toilet_seat_hole",
    0, BOWL_CY - 0.02, SEAT_Z + SEAT_HOLE_H / 2,
    SEAT_HOLE_W, SEAT_HOLE_L, SEAT_HOLE_H,
    mat_seat_hole, COLL
)

# ============================================================
# 6. LID — flat, resting closed on the seat
# ============================================================
LID_Z = SEAT_Z + SEAT_H + LID_H / 2
make_box(
    "toilet_lid",
    0, BOWL_CY + LID_L * 0.04,  # very slight forward shift
    LID_Z,
    LID_W, LID_L, LID_H,
    mat_seat, COLL
)

# ============================================================
# 7. TANK
# ============================================================
make_box(
    "toilet_tank",
    0, TANK_CY, TANK_CZ,
    TANK_W, TANK_L, TANK_H,
    mat_porcelain, COLL
)

# Tank lid — flat box on top of tank
make_box(
    "toilet_tank_lid",
    0, TANK_CY, PED_H + TANK_H + 0.015,
    TANK_W + 0.01, TANK_L + 0.01, 0.028,
    mat_porcelain, COLL
)

# ============================================================
# 8. FLUSH HANDLE — small cylinder on side of tank
# ============================================================
make_cylinder(
    "toilet_flush_handle",
    HANDLE_CX, HANDLE_CY, HANDLE_CZ,
    radius=HANDLE_R, depth=HANDLE_L, verts=8,
    rot_x=0.0,
    material=mat_handle, collection=COLL
)

# ============================================================
# DONE
# ============================================================
bpy.ops.object.select_all(action='DESELECT')
print("Toilet created successfully.")
