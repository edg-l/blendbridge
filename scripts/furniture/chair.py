import bpy

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


# ============================================================
# MATERIALS
# ============================================================

def mat(name, color, roughness=0.85, metallic=0.0):
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return m


mat_wood = mat("chair_wood", (0.50, 0.33, 0.15))
mat_seat = mat("seat_pad",   (0.60, 0.25, 0.15))

COLL = "Chair"

# ============================================================
# CHAIR DIMENSIONS
# ============================================================
CHAIR_W  = 0.42   # X seat width
CHAIR_D  = 0.42   # Y seat depth
SEAT_H   = 0.45   # Z height of seat top surface

LEG_W    = 0.04   # leg cross-section (square)
SEAT_T   = 0.04   # seat slab thickness
SEAT_CZ  = SEAT_H - SEAT_T / 2

LEG_H    = SEAT_H - SEAT_T  # legs run from floor to underside of seat

# Leg corner positions — legs sit at the seat corners
LEG_OX   = CHAIR_W / 2 - LEG_W / 2
LEG_OY   = CHAIR_D / 2 - LEG_W / 2

# ---- Backrest ----
BR_POST_W  = 0.03    # slat cross-section width
BR_POST_D  = 0.03    # slat cross-section depth
BR_POST_H  = 0.40    # height of slats above seat top
# Slats are positioned near the left and right edges of the seat back
BR_POST_OX = CHAIR_W / 2 - BR_POST_W / 2 - 0.02
BR_POST_CY = CHAIR_D / 2 - BR_POST_D / 2   # flush with back face of seat
BR_POST_BOT = SEAT_H   # base of slat sits on top of seat level (flush)
BR_POST_CZ  = BR_POST_BOT + BR_POST_H / 2

# Top crossbar connects the two slats at their very top
XBAR_W   = CHAIR_W - (BR_POST_W * 2) + BR_POST_W   # spans outer faces of slats
XBAR_H   = 0.03
XBAR_D   = BR_POST_D
XBAR_CZ  = BR_POST_BOT + BR_POST_H - XBAR_H / 2
XBAR_CY  = BR_POST_CY

# ---- Front crossbar (structural detail between front legs) ----
FXBAR_H  = 0.015   # thin bar
FXBAR_W  = CHAIR_W - LEG_W * 2 + LEG_W * 0.5   # spans between front legs
FXBAR_D  = LEG_W
FXBAR_CZ = 0.15    # height above floor
FXBAR_CY = -LEG_OY  # same Y as front legs

# ============================================================
# 1. SEAT SLAB
# ============================================================
make_box("seat", 0, 0, SEAT_CZ, CHAIR_W, CHAIR_D, SEAT_T, mat_seat, COLL)

# ============================================================
# 2. LEGS — 4 corner legs using linked duplicates
# ============================================================
bpy.ops.mesh.primitive_cube_add(size=1, location=(-LEG_OX, -LEG_OY, LEG_H / 2))
leg_base = bpy.context.active_object
leg_base.name = "leg_FL"
leg_base.scale = (LEG_W, LEG_W, LEG_H)
apply_and_finish(leg_base, mat_wood, COLL)

leg_positions = [
    ("leg_FR",  LEG_OX, -LEG_OY),
    ("leg_BL", -LEG_OX,  LEG_OY),
    ("leg_BR",  LEG_OX,  LEG_OY),
]
for leg_name, lx2, ly2 in leg_positions:
    bpy.ops.object.select_all(action='DESELECT')
    leg_base.select_set(True)
    bpy.context.view_layer.objects.active = leg_base
    bpy.ops.object.duplicate(linked=True)
    dup = bpy.context.active_object
    dup.name = leg_name
    dup.location = (lx2, ly2, LEG_H / 2)
    move_to_collection(dup, COLL)

# ============================================================
# 3. BACKREST — two vertical slats + horizontal crossbar
# ============================================================

# Left slat (base mesh)
bpy.ops.mesh.primitive_cube_add(size=1, location=(-BR_POST_OX, BR_POST_CY, BR_POST_CZ))
slat_base = bpy.context.active_object
slat_base.name = "backrest_slat_L"
slat_base.scale = (BR_POST_W, BR_POST_D, BR_POST_H)
apply_and_finish(slat_base, mat_wood, COLL)

# Right slat as a linked duplicate
bpy.ops.object.select_all(action='DESELECT')
slat_base.select_set(True)
bpy.context.view_layer.objects.active = slat_base
bpy.ops.object.duplicate(linked=True)
slat_r = bpy.context.active_object
slat_r.name = "backrest_slat_R"
slat_r.location = (BR_POST_OX, BR_POST_CY, BR_POST_CZ)
move_to_collection(slat_r, COLL)

# Top crossbar
make_box("backrest_crossbar", 0, XBAR_CY, XBAR_CZ, XBAR_W, XBAR_D, XBAR_H, mat_wood, COLL)

# ============================================================
# 4. FRONT CROSSBAR (structural detail)
# ============================================================
make_box("front_crossbar", 0, FXBAR_CY, FXBAR_CZ, FXBAR_W, FXBAR_D, FXBAR_H, mat_wood, COLL)

# ============================================================
# DONE
# ============================================================
bpy.ops.object.select_all(action='DESELECT')
print("Chair created successfully.")
