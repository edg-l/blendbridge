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


mat_wood  = mat("table_wood", (0.55, 0.38, 0.20))
mat_apron = mat("apron",      (0.50, 0.33, 0.15))

COLL = "Dining_Table"

# ============================================================
# DIMENSIONS
# ============================================================

TABLE_W  = 0.90   # X — total width
TABLE_D  = 0.70   # Y — total depth
TABLE_H  = 0.75   # Z — height to top surface of tabletop

TOP_T    = 0.05   # tabletop slab thickness
OVERHANG = 0.02   # tabletop overhang beyond leg outer face

LEG_W    = 0.05   # leg cross-section (square, both X and Y)
LEG_INSET = 0.05  # leg inset from table edge (to leg center)

# Leg height = full table height minus tabletop thickness
LEG_H    = TABLE_H - TOP_T

# Leg center offsets from origin
LEG_OX   = TABLE_W / 2 - LEG_INSET
LEG_OY   = TABLE_D / 2 - LEG_INSET

# Tabletop slab: extends overhang beyond the outer leg faces
TOP_W    = (LEG_OX + LEG_W / 2) * 2 + OVERHANG * 2
TOP_D    = (LEG_OY + LEG_W / 2) * 2 + OVERHANG * 2
TOP_CZ   = TABLE_H - TOP_T / 2

# Apron rails sit just under the tabletop, flush with inner leg faces
APRON_T  = 0.015   # apron board thickness (Y or X direction)
APRON_H  = 0.08    # apron board height (Z)
APRON_CZ = TABLE_H - TOP_T - APRON_H / 2

# Long apron rails (run along X, one per Y side)
# Span between inner faces of the short-side legs
APRON_LONG_W = (LEG_OX - LEG_W / 2) * 2    # inner gap between legs on long axis
APRON_LONG_OY = LEG_OY - LEG_W / 2 - APRON_T / 2   # flush with inner leg face

# Short apron rails (run along Y, one per X side)
APRON_SHORT_D = (LEG_OY - LEG_W / 2) * 2
APRON_SHORT_OX = LEG_OX - LEG_W / 2 - APRON_T / 2

# ============================================================
# 1. TABLETOP SLAB
# ============================================================
make_box("tabletop", 0, 0, TOP_CZ, TOP_W, TOP_D, TOP_T, mat_wood, COLL)

# ============================================================
# 2. LEGS — one template + 3 linked duplicates
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
for leg_name, lx, ly in leg_positions:
    bpy.ops.object.select_all(action='DESELECT')
    leg_base.select_set(True)
    bpy.context.view_layer.objects.active = leg_base
    bpy.ops.object.duplicate(linked=True)
    dup = bpy.context.active_object
    dup.name = leg_name
    dup.location = (lx, ly, LEG_H / 2)
    move_to_collection(dup, COLL)

# ============================================================
# 3. APRON RAILS
# ============================================================

# Front rail (−Y side)
make_box(
    "apron_front",
    0, -APRON_LONG_OY, APRON_CZ,
    APRON_LONG_W, APRON_T, APRON_H,
    mat_apron, COLL,
)

# Back rail (+Y side)
make_box(
    "apron_back",
    0, APRON_LONG_OY, APRON_CZ,
    APRON_LONG_W, APRON_T, APRON_H,
    mat_apron, COLL,
)

# Left rail (−X side)
make_box(
    "apron_left",
    -APRON_SHORT_OX, 0, APRON_CZ,
    APRON_T, APRON_SHORT_D, APRON_H,
    mat_apron, COLL,
)

# Right rail (+X side)
make_box(
    "apron_right",
    APRON_SHORT_OX, 0, APRON_CZ,
    APRON_T, APRON_SHORT_D, APRON_H,
    mat_apron, COLL,
)

# ============================================================
# DONE
# ============================================================
bpy.ops.object.select_all(action='DESELECT')
print("Dining table created successfully.")
