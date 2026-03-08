import bpy
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
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    coll.objects.link(obj)


def apply_transforms(obj, location=False, rotation=False, scale=True):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=location, rotation=rotation, scale=scale)


def finish(obj, material, coll_name):
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
    return finish(obj, material, collection)


def make_cylinder(name, cx, cy, cz, radius, depth, verts, material, collection,
                  rx=0.0, ry=0.0, rz=0.0):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=verts, radius=radius, depth=depth,
        location=(cx, cy, cz),
        rotation=(rx, ry, rz),
    )
    obj = bpy.context.active_object
    obj.name = name
    return finish(obj, material, collection)


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


mat_top        = mat("counter_top",  (0.75, 0.73, 0.70), roughness=0.6)
mat_cabinet    = mat("cabinet",      (0.85, 0.78, 0.65), roughness=0.85)
mat_knob       = mat("knob",         (0.5,  0.5,  0.5),  roughness=0.3, metallic=0.8)
mat_sink       = mat("sink",         (0.85, 0.85, 0.87), roughness=0.2, metallic=0.4)
mat_backsplash = mat("backsplash",   (0.90, 0.88, 0.85), roughness=0.5)

COLL = "Kitchen_Counter"

# ============================================================
# DIMENSIONS
# L-shape: long arm extends along +Y (length 2.0), short arm along +X (length 1.0)
# The corner of the L is at origin.
# Cabinet base height 0.85, depth 0.5.
#
# Long arm:   X in [-0.5, 0],  Y in [0, 2.0]  (0.5 wide, 2.0 long)
# Short arm:  X in [0, 1.0],   Y in [0, 0.5]  (1.0 wide, 0.5 deep)
# Both share the corner region already covered by the long arm's width.
# ============================================================

CAB_H  = 0.85
DEPTH  = 0.5      # Y depth of each arm
OVERHANG = 0.02

LONG_ARM_W = 0.5   # X width of long arm
LONG_ARM_L = 2.0   # Y length of long arm
SHORT_ARM_W = 1.0  # X length of short arm
SHORT_ARM_D = DEPTH  # Y depth of short arm (same as depth)

# Long arm centred in X at -0.25, centred in Y at 1.0
LONG_CX = -LONG_ARM_W / 2   # -0.25
LONG_CY =  LONG_ARM_L / 2   #  1.0
LONG_CZ =  CAB_H / 2        #  0.425

# Short arm: covers X in [0, 1.0], Y in [0, 0.5]
# But the corner (X in [-0.5,0], Y in [0,0.5]) is already covered by long arm.
# Short arm adds the extra piece X in [0, 1.0], Y in [0, 0.5].
SHORT_CX = (0 + SHORT_ARM_W) / 2   # 0.5
SHORT_CY = SHORT_ARM_D / 2          # 0.25
SHORT_CZ = CAB_H / 2

# ============================================================
# 1. CABINET BASES
# ============================================================

make_box("cabinet_base_long",  LONG_CX,  LONG_CY,  LONG_CZ,
         LONG_ARM_W, LONG_ARM_L, CAB_H,  mat_cabinet, COLL)

make_box("cabinet_base_short", SHORT_CX, SHORT_CY, SHORT_CZ,
         SHORT_ARM_W, SHORT_ARM_D, CAB_H, mat_cabinet, COLL)

# ============================================================
# 2. COUNTERTOP — slightly wider/deeper (overhang on front and sides)
# Long arm countertop: X in [-0.5-overhang, 0+overhang], Y in [-overhang, 2.0+overhang]
# Short arm countertop: X in [0, 1.0+overhang], Y in [-overhang, 0.5+overhang]
# Countertop thickness
# ============================================================

TOP_T  = 0.04   # countertop thickness
TOP_Z  = CAB_H + TOP_T / 2

# Long arm top
make_box("counter_top_long",
         LONG_CX - OVERHANG / 2,
         LONG_CY + OVERHANG / 2,
         TOP_Z,
         LONG_ARM_W + OVERHANG * 2,
         LONG_ARM_L + OVERHANG * 2,
         TOP_T,
         mat_top, COLL)

# Short arm top (X from 0 to SHORT_ARM_W+overhang, with overhang at far end)
make_box("counter_top_short",
         SHORT_CX + OVERHANG / 2,
         SHORT_CY,
         TOP_Z,
         SHORT_ARM_W + OVERHANG,
         SHORT_ARM_D + OVERHANG * 2,
         TOP_T,
         mat_top, COLL)

# ============================================================
# 3. CABINET DOORS (inset thin rectangles on front faces)
# Front face of long arm faces -Y direction (front at Y=0 side... wait)
# Long arm front face: Y = 0 side (minimum Y). Doors are on Y=0 face.
# Short arm front face: Y = 0 side as well.
#
# Long arm: 2 doors side by side in X, centred in Y per half of long arm.
# Actually long arm runs Y 0..2.0, front face at Y=0.
# Doors sit on front face, recessed slightly into the box.
# ============================================================

DOOR_T    = 0.02   # door thickness (how far it protrudes from cabinet face)
DOOR_INSET = 0.005  # gap between door edge and cabinet edge
DOOR_GAP   = 0.04   # gap between doors

# Long arm has 2 doors stacked in Y (upper and lower half of the arm)
# Door width = arm width minus insets, door height = half arm height minus gap
LONG_DOOR_W = LONG_ARM_W - DOOR_INSET * 2
LONG_DOOR_H = (CAB_H / 2) - DOOR_INSET * 2 - DOOR_GAP / 2
# Door 1: lower half of long arm (Y near 0, so in Y 0..1.0 region)
LONG_D1_CY = LONG_ARM_L * 0.25   # 0.5
LONG_D1_CZ = CAB_H * 0.25        # lower quarter

# Door 2: upper half of long arm
LONG_D2_CY = LONG_ARM_L * 0.75   # 1.5
LONG_D2_CZ = CAB_H * 0.75

# Doors sit on front face of long arm (front face at Y = 0)
DOOR_Y_LONG = 0.0 - DOOR_T / 2  # slightly outside front face (protrudes forward)

make_box("door_long_1",
         LONG_CX, LONG_D1_CY, LONG_D1_CZ - DOOR_INSET,
         LONG_DOOR_W, DOOR_T, LONG_DOOR_H,
         mat_cabinet, COLL)

make_box("door_long_2",
         LONG_CX, LONG_D2_CY, LONG_D2_CZ + DOOR_INSET,
         LONG_DOOR_W, DOOR_T, LONG_DOOR_H,
         mat_cabinet, COLL)

# Short arm: 1 door on its front face (Y=0 side)
SHORT_DOOR_W = SHORT_ARM_W - DOOR_INSET * 2
SHORT_DOOR_H = CAB_H - DOOR_INSET * 2 - DOOR_GAP
SHORT_DOOR_CX = SHORT_CX
SHORT_DOOR_CY = 0.0 - DOOR_T / 2
SHORT_DOOR_CZ = CAB_H / 2

make_box("door_short_1",
         SHORT_DOOR_CX, SHORT_DOOR_CY, SHORT_DOOR_CZ,
         SHORT_DOOR_W, DOOR_T, SHORT_DOOR_H,
         mat_cabinet, COLL)

# ============================================================
# 4. KNOBS — linked duplicates on each door
# ============================================================

KNOB_R  = 0.018
KNOB_D  = 0.025
KNOB_PY = -DOOR_T  # in front of door face, along Y

# First knob on long door 1 (used as the base mesh)
bpy.ops.mesh.primitive_cylinder_add(
    vertices=8, radius=KNOB_R, depth=KNOB_D,
    location=(LONG_CX + 0.08, LONG_D1_CY, LONG_D1_CZ - DOOR_INSET),
    rotation=(math.pi / 2, 0, 0),
)
knob_base = bpy.context.active_object
knob_base.name = "knob_long1"
finish(knob_base, mat_knob, COLL)

knob_positions = [
    ("knob_long2",  LONG_CX + 0.08, LONG_D2_CY,  LONG_D2_CZ + DOOR_INSET),
    ("knob_short1", SHORT_DOOR_CX + 0.08, SHORT_DOOR_CY, SHORT_DOOR_CZ),
]
for kname, kx, ky, kz in knob_positions:
    bpy.ops.object.select_all(action='DESELECT')
    knob_base.select_set(True)
    bpy.context.view_layer.objects.active = knob_base
    bpy.ops.object.duplicate(linked=True)
    dup = bpy.context.active_object
    dup.name = kname
    dup.location = (kx, ky, kz)
    move_to_collection(dup, COLL)

# ============================================================
# 5. SINK BASIN — rectangular inset in countertop on long arm
# Sink sits on the long arm, centred around Y=0.6 (lower portion of long arm)
# ============================================================

SINK_W   = 0.35   # X
SINK_L   = 0.30   # Y
SINK_D   = 0.15   # depth (Z into counter)
SINK_CX  = LONG_CX
SINK_CY  = 0.6
SINK_T   = 0.02   # wall thickness

# Sink outer shell (slightly recessed below countertop)
SINK_OUT_CZ = CAB_H - SINK_D / 2 + 0.01
make_box("sink_basin",
         SINK_CX, SINK_CY, SINK_OUT_CZ,
         SINK_W, SINK_L, SINK_D,
         mat_sink, COLL)

# ============================================================
# 6. FAUCET — cylinder base + angled box spout
# ============================================================

FAUCET_BASE_R = 0.018
FAUCET_BASE_H = 0.10
FAUCET_CX = SINK_CX
FAUCET_CY = SINK_CY - SINK_L / 2 - 0.04
FAUCET_BASE_CZ = CAB_H + FAUCET_BASE_H / 2

make_cylinder("faucet_base",
              FAUCET_CX, FAUCET_CY, FAUCET_BASE_CZ,
              radius=FAUCET_BASE_R, depth=FAUCET_BASE_H,
              verts=8, material=mat_sink, collection=COLL)

# Spout: angled box projecting over sink
SPOUT_W = 0.025
SPOUT_L = 0.12
SPOUT_H = 0.018
SPOUT_CZ = CAB_H + FAUCET_BASE_H - 0.01
SPOUT_CY = FAUCET_CY + SPOUT_L / 2

bpy.ops.mesh.primitive_cube_add(
    size=1,
    location=(FAUCET_CX, SPOUT_CY, SPOUT_CZ),
)
spout = bpy.context.active_object
spout.name = "faucet_spout"
spout.scale = (SPOUT_W, SPOUT_L, SPOUT_H)
spout.rotation_euler = (math.radians(15), 0, 0)
finish(spout, mat_sink, COLL)
# Re-apply location after rotation
apply_transforms(spout, location=True, rotation=True, scale=False)

# ============================================================
# 7. BACKSPLASH — thin tall strip along back edges
# Back of long arm: Y = LONG_ARM_L = 2.0
# Back of short arm: Y = DEPTH = 0.5, but only for X > 0
# ============================================================

BS_H  = 0.20   # height above countertop
BS_T  = 0.02   # thickness
BS_CZ = CAB_H + TOP_T + BS_H / 2

# Long arm backsplash (along back edge, X from -0.5 to 0)
make_box("backsplash_long",
         LONG_CX, LONG_ARM_L - BS_T / 2, BS_CZ,
         LONG_ARM_W + OVERHANG * 2, BS_T, BS_H,
         mat_backsplash, COLL)

# Short arm backsplash (along right side / back edge, Y from 0 to 0.5)
# The short arm's back is at Y = DEPTH, and it spans X from 0 to SHORT_ARM_W
make_box("backsplash_short",
         SHORT_CX + OVERHANG / 2, SHORT_ARM_D - BS_T / 2, BS_CZ,
         SHORT_ARM_W + OVERHANG, BS_T, BS_H,
         mat_backsplash, COLL)

# ============================================================
# DONE
# ============================================================
bpy.ops.object.select_all(action='DESELECT')
print("Kitchen counter created successfully.")
