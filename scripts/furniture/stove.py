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


mat_body      = mat("body",      (0.25, 0.25, 0.25), roughness=0.5)
mat_stovetop  = mat("stovetop",  (0.15, 0.15, 0.15), roughness=0.4)
mat_burner    = mat("burner",    (0.35, 0.30, 0.28), roughness=0.7)
mat_knob      = mat("knob",      (0.6,  0.6,  0.6),  roughness=0.4, metallic=0.5)
mat_handle    = mat("handle",    (0.7,  0.7,  0.7),  roughness=0.3, metallic=0.7)
mat_oven_door = mat("oven_door", (0.20, 0.20, 0.22), roughness=0.35)

COLL = "Stove"

# ============================================================
# DIMENSIONS — centred at origin, bottom at Z=0
# ============================================================

W = 0.60   # X width
D = 0.55   # Y depth
H = 0.85   # Z total height

# ============================================================
# 1. MAIN BODY
# ============================================================

make_box("stove_body", 0, 0, H / 2, W, D, H, mat_body, COLL)

# ============================================================
# 2. STOVETOP SURFACE — thin slab on top, same X/Y footprint
# ============================================================

TOP_T = 0.025
make_box("stovetop", 0, 0, H + TOP_T / 2, W, D, TOP_T, mat_stovetop, COLL)

# ============================================================
# 3. BURNER RINGS — 8-vertex flat cylinders, 2x2 grid on top
# Arranged symmetrically: 2 in X, 2 in Y
# ============================================================

BURNER_R     = 0.085
BURNER_T     = 0.015   # thickness (flat)
BURNER_CZ    = H + TOP_T + BURNER_T / 2
BURNER_SPACE_X = W * 0.28   # X offset from centre
BURNER_SPACE_Y = D * 0.28   # Y offset from centre

burner_positions = [
    ("burner_FL", -BURNER_SPACE_X, -BURNER_SPACE_Y),
    ("burner_FR",  BURNER_SPACE_X, -BURNER_SPACE_Y),
    ("burner_BL", -BURNER_SPACE_X,  BURNER_SPACE_Y),
    ("burner_BR",  BURNER_SPACE_X,  BURNER_SPACE_Y),
]

# Create first burner as the base mesh for linked duplicates
bx0, by0 = burner_positions[0][1], burner_positions[0][2]
bpy.ops.mesh.primitive_cylinder_add(
    vertices=8, radius=BURNER_R, depth=BURNER_T,
    location=(bx0, by0, BURNER_CZ),
)
burner_base = bpy.context.active_object
burner_base.name = burner_positions[0][0]
finish(burner_base, mat_burner, COLL)

for bname, bx, by in burner_positions[1:]:
    bpy.ops.object.select_all(action='DESELECT')
    burner_base.select_set(True)
    bpy.context.view_layer.objects.active = burner_base
    bpy.ops.object.duplicate(linked=True)
    dup = bpy.context.active_object
    dup.name = bname
    dup.location = (bx, by, BURNER_CZ)
    move_to_collection(dup, COLL)

# ============================================================
# 4. OVEN DOOR — inset rectangle on front face
# Front face of body is at Y = -D/2
# Oven door covers roughly the lower 2/3 of the front face
# ============================================================

DOOR_INSET = 0.01    # how far door protrudes from body front
DOOR_W     = W - 0.06
DOOR_H     = H * 0.60
DOOR_CZ    = DOOR_H / 2 + 0.02
DOOR_CY    = -D / 2 - DOOR_INSET / 2

make_box("oven_door",
         0, DOOR_CY, DOOR_CZ,
         DOOR_W, DOOR_INSET, DOOR_H,
         mat_oven_door, COLL)

# ============================================================
# 5. OVEN DOOR HANDLE — horizontal bar centred on door
# ============================================================

HANDLE_W   = DOOR_W * 0.55   # shorter than door width
HANDLE_R   = 0.018
HANDLE_CZ  = DOOR_CZ + DOOR_H / 2 - 0.06   # near top of door
HANDLE_CY  = DOOR_CY - 0.04                 # protrudes further forward

make_cylinder("oven_handle",
              0, HANDLE_CY, HANDLE_CZ,
              radius=HANDLE_R, depth=HANDLE_W,
              verts=8, material=mat_handle, collection=COLL,
              rx=0, ry=math.pi / 2, rz=0)

# ============================================================
# 6. CONTROL KNOBS — 2 knobs above the oven door on front face
# ============================================================

KNOB_R    = 0.025
KNOB_D    = 0.030
KNOB_CZ   = DOOR_CZ + DOOR_H / 2 + 0.05   # above oven door
KNOB_CY   = -D / 2 - KNOB_D / 2
KNOB_SEP  = 0.12   # X separation

# First knob as base mesh
bpy.ops.mesh.primitive_cylinder_add(
    vertices=8, radius=KNOB_R, depth=KNOB_D,
    location=(-KNOB_SEP / 2, KNOB_CY, KNOB_CZ),
    rotation=(math.pi / 2, 0, 0),
)
knob_base = bpy.context.active_object
knob_base.name = "knob_L"
finish(knob_base, mat_knob, COLL)

# Second knob as linked duplicate
bpy.ops.object.select_all(action='DESELECT')
knob_base.select_set(True)
bpy.context.view_layer.objects.active = knob_base
bpy.ops.object.duplicate(linked=True)
knob_r = bpy.context.active_object
knob_r.name = "knob_R"
knob_r.location = (KNOB_SEP / 2, KNOB_CY, KNOB_CZ)
move_to_collection(knob_r, COLL)

# ============================================================
# DONE
# ============================================================
bpy.ops.object.select_all(action='DESELECT')
print("Stove created successfully.")
