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


mat_body   = mat("body",   (0.90, 0.90, 0.92), roughness=0.4)
mat_door   = mat("door",   (0.92, 0.92, 0.94), roughness=0.35)
mat_handle = mat("handle", (0.7,  0.7,  0.72), roughness=0.25, metallic=0.6)

COLL = "Fridge"

# ============================================================
# DIMENSIONS — centred at origin, bottom at Z=0
# ============================================================

W = 0.70    # X width
D = 0.65    # Y depth
H = 1.80    # Z total height

# Door split
FREEZER_H = 0.50    # upper freezer door height
FRIDGE_H  = 1.20    # lower fridge door height
GAP_H     = 0.015   # visible gap between doors

# Doors protrude from front face
DOOR_PROTO = 0.02
DOOR_W     = W - 0.04   # doors slightly narrower than body

FRONT_Y    = -D / 2      # front face of body

# ============================================================
# 1. MAIN BODY
# ============================================================

make_box("fridge_body", 0, 0, H / 2, W, D, H, mat_body, COLL)

# ============================================================
# 2. FREEZER DOOR (upper, shorter)
# Door bottom at Z = FRIDGE_H + GAP_H, top at Z = FRIDGE_H + GAP_H + FREEZER_H
# ============================================================

FREEZER_CZ = FRIDGE_H + GAP_H + FREEZER_H / 2
FREEZER_CY = FRONT_Y - DOOR_PROTO / 2

make_box("freezer_door",
         0, FREEZER_CY, FREEZER_CZ,
         DOOR_W, DOOR_PROTO, FREEZER_H,
         mat_door, COLL)

# ============================================================
# 3. FRIDGE DOOR (lower, taller)
# Door bottom at Z = 0, top at Z = FRIDGE_H
# ============================================================

FRIDGE_CZ = FRIDGE_H / 2
FRIDGE_CY = FRONT_Y - DOOR_PROTO / 2

make_box("fridge_door",
         0, FRIDGE_CY, FRIDGE_CZ,
         DOOR_W, DOOR_PROTO, FRIDGE_H,
         mat_door, COLL)

# ============================================================
# 4. GAP STRIP — subtle dark line between doors
# A thin box at the gap position, slightly recessed into body
# ============================================================

GAP_STRIP_T = 0.005
make_box("door_gap",
         0, FRONT_Y - GAP_STRIP_T / 2, FRIDGE_H + GAP_H / 2,
         DOOR_W, GAP_STRIP_T, GAP_H,
         mat_body, COLL)

# ============================================================
# 5. HANDLES — vertical bar on each door (thin tall boxes)
# Handles are on the right side of each door (positive X offset)
# ============================================================

HANDLE_X    = DOOR_W / 2 - 0.06   # offset from centre toward right edge
HANDLE_W    = 0.025                # X width of handle bar
HANDLE_D    = 0.030                # Y depth (protrudes from door)
HANDLE_CY   = FRONT_Y - DOOR_PROTO - HANDLE_D / 2

# Freezer door handle — shorter, centred vertically on freezer door
FREEZER_HANDLE_H = FREEZER_H * 0.50
FREEZER_HANDLE_CZ = FREEZER_CZ

# Fridge door handle — taller, centred on fridge door upper portion
FRIDGE_HANDLE_H = FRIDGE_H * 0.35
FRIDGE_HANDLE_CZ = FRIDGE_CZ + FRIDGE_H * 0.15

# Create freezer handle as base mesh for linked duplicate
bpy.ops.mesh.primitive_cube_add(
    size=1,
    location=(HANDLE_X, HANDLE_CY, FREEZER_HANDLE_CZ),
)
handle_base = bpy.context.active_object
handle_base.name = "handle_freezer"
handle_base.scale = (HANDLE_W, HANDLE_D, FREEZER_HANDLE_H)
finish(handle_base, mat_handle, COLL)

# Fridge door handle as independent copy (different scale than freezer handle)
handle_fridge = make_box("handle_fridge", HANDLE_X, HANDLE_CY, FRIDGE_HANDLE_CZ,
                         HANDLE_W, HANDLE_D, FRIDGE_HANDLE_H, mat_handle, COLL)

# ============================================================
# DONE
# ============================================================
bpy.ops.object.select_all(action='DESELECT')
print("Fridge created successfully.")
