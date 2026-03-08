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


mat_wood    = mat("desk_wood",    (0.50, 0.33, 0.15))
mat_drawer  = mat("drawer_front", (0.55, 0.38, 0.20))
mat_handle  = mat("handle",       (0.50, 0.50, 0.50), roughness=0.3, metallic=0.7)

COLL = "Desk"

# ============================================================
# DESK DIMENSIONS
# ============================================================
DESK_W  = 1.00   # X total width
DESK_D  = 0.50   # Y total depth
DESK_H  = 0.78   # Z total height (floor to top of desktop)

LEG_W   = 0.05   # leg cross-section (square)
TOP_T   = 0.04   # desktop slab thickness
OVHG    = 0.02   # desktop overhang beyond legs on all sides

# Leg positions: legs sit just inside the overhang border
LEG_INNER_X = DESK_W / 2 - OVHG - LEG_W / 2   # X offset from centre
LEG_INNER_Y = DESK_D / 2 - OVHG - LEG_W / 2   # Y offset from centre

# Leg height: from floor up to underside of desktop
LEG_H   = DESK_H - TOP_T

# Desktop slab
TOP_W   = DESK_W   # full width (includes overhang)
TOP_D   = DESK_D   # full depth
TOP_CZ  = DESK_H - TOP_T / 2

# Drawer sits in the apron space below the desktop, centred in X
APR_H   = 0.10   # apron / side-panel height below desktop
APR_BOT = LEG_H - APR_H   # Z of apron bottom
# The drawer front protrudes 0.01 beyond the front face of the legs
DRW_W   = DESK_W * 0.40   # drawer width (centred)
DRW_H   = APR_H - 0.01    # slightly shorter than apron
DRW_D   = 0.025            # protrusion depth (visible box on front face)
DRW_CX  = 0.0
DRW_CY  = -(DESK_D / 2 - OVHG) - DRW_D / 2  # flush/slightly proud of front leg face
DRW_CZ  = APR_BOT + DRW_H / 2 + 0.005

# Handle: small cylinder knob centred on drawer front face
HDL_R   = 0.012
HDL_D   = 0.022   # depth of knob
HDL_CY  = DRW_CY - DRW_D / 2 - HDL_D / 2
HDL_CZ  = DRW_CZ

# Back panel: thin board connecting the two back legs, spanning apron height
BACK_W  = DESK_W - LEG_W * 2   # spans between back legs
BACK_H  = APR_H
BACK_T  = 0.015
BACK_CY = DESK_D / 2 - OVHG - BACK_T / 2   # just inside back leg front face
BACK_CZ = APR_BOT + BACK_H / 2

# ============================================================
# 1. DESKTOP SLAB
# ============================================================
make_box("desk_top", 0, 0, TOP_CZ, TOP_W, TOP_D, TOP_T, mat_wood, COLL)

# ============================================================
# 2. LEGS — 4 corner legs using linked duplicates
# ============================================================
lx = LEG_INNER_X
ly = LEG_INNER_Y

bpy.ops.mesh.primitive_cube_add(size=1, location=(-lx, -ly, LEG_H / 2))
leg_base = bpy.context.active_object
leg_base.name = "leg_FL"
leg_base.scale = (LEG_W, LEG_W, LEG_H)
apply_and_finish(leg_base, mat_wood, COLL)

leg_positions = [
    ("leg_FR",  lx, -ly),
    ("leg_BL", -lx,  ly),
    ("leg_BR",  lx,  ly),
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
# 3. SIDE APRON PANELS (left and right, connecting front-back legs)
# ============================================================
APR_D = DESK_D - OVHG * 2 - LEG_W   # span between leg inner faces
APR_T = 0.015
APR_CZ = APR_BOT + APR_H / 2

for side_name, side_x in [("apron_L", -lx), ("apron_R", lx)]:
    make_box(side_name, side_x, 0, APR_CZ, APR_T, APR_D, APR_H, mat_wood, COLL)

# ============================================================
# 4. BACK PANEL
# ============================================================
make_box("back_panel", 0, BACK_CY, BACK_CZ, BACK_W, BACK_T, BACK_H, mat_wood, COLL)

# ============================================================
# 5. DRAWER FRONT (protrudes from front face)
# ============================================================
make_box("drawer_front", DRW_CX, DRW_CY, DRW_CZ, DRW_W, DRW_D, DRW_H, mat_drawer, COLL)

# ============================================================
# 6. DRAWER HANDLE (cylinder knob)
# ============================================================
bpy.ops.mesh.primitive_cylinder_add(
    radius=HDL_R,
    depth=HDL_D,
    vertices=8,
    location=(0, HDL_CY, HDL_CZ)
)
handle = bpy.context.active_object
handle.name = "drawer_handle"
# Orient knob to protrude in Y
handle.rotation_euler = (math.radians(90), 0, 0)
bpy.ops.object.select_all(action='DESELECT')
handle.select_set(True)
bpy.context.view_layer.objects.active = handle
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
bpy.ops.object.shade_flat()
handle.data.materials.append(mat_handle)
move_to_collection(handle, COLL)

# ============================================================
# DONE
# ============================================================
bpy.ops.object.select_all(action='DESELECT')
print("Desk created successfully.")
