"""
house_shell.py — Low-poly game house shell (no furniture).
3 rooms: Kitchen (front-left), Bathroom (front-right), Bedroom (back full-width).
Player-enterable with doorways between all rooms and a front door.
"""

import bpy
import bmesh
from mathutils import Vector

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
X_MIN, X_MAX = -4.0, 4.0
Y_MIN, Y_MAX = -3.0, 3.0
X_MID = 0.0        # Kitchen / Bathroom divider
Y_MID = 0.0        # Front rooms / Bedroom divider

WT = 0.15          # Wall thickness
WH = 2.5           # Wall height
DOOR_W = 1.0       # Doorway width
DOOR_H = 1.8       # Doorway height

# Doorway centers (used to split walls)
# Front door opening (exterior, front wall at Y_MIN)
FRONT_DOOR_X_MIN = -1.5
FRONT_DOOR_X_MAX = -0.5

# Kitchen <-> Bedroom  (interior Y_MID wall, left segment)
KIT_BED_X_MIN = -2.5
KIT_BED_X_MAX = -1.5

# Bathroom <-> Bedroom  (interior Y_MID wall, right segment)
BATH_BED_X_MIN = 1.5
BATH_BED_X_MAX = 2.5

# Kitchen <-> Bathroom  (interior X_MID wall)
KIT_BATH_Y_MIN = -1.5
KIT_BATH_Y_MAX = -0.5


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def ensure_collection(name: str, parent=None):
    """Return existing or create a new collection, linked to parent (or scene)."""
    if name in bpy.data.collections:
        col = bpy.data.collections[name]
    else:
        col = bpy.data.collections.new(name)
        if parent is None:
            bpy.context.scene.collection.children.link(col)
        else:
            parent.children.link(col)
    return col


def make_material(name: str, color, roughness=0.8, metallic=0.0):
    """Return existing or create a simple Principled BSDF material."""
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return mat


def add_box(name: str, cx, cy, cz, sx, sy, sz, collection, material):
    """
    Create a UV-cube box centred at (cx, cy, cz) with full dimensions (sx, sy, sz).
    Scale is applied immediately so all transforms are clean.
    """
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(cx, cy, cz))
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (sx, sy, sz)
    bpy.ops.object.transform_apply(scale=True)

    # Move to target collection
    for col in list(obj.users_collection):
        col.objects.unlink(obj)
    collection.objects.link(obj)

    # Assign material
    if obj.data.materials:
        obj.data.materials[0] = material
    else:
        obj.data.materials.append(material)

    return obj


def add_floor_patch(name: str, x_min, x_max, y_min, y_max, z, collection, material):
    """Thin floor slab (0.02 thick) for floor / gap patches."""
    cx = (x_min + x_max) / 2
    cy = (y_min + y_max) / 2
    sx = x_max - x_min
    sy = y_max - y_min
    return add_box(name, cx, cy, z, sx, sy, 0.02, collection, material)


# ---------------------------------------------------------------------------
# Scene reset
# ---------------------------------------------------------------------------

def reset_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for col in list(bpy.data.collections):
        bpy.data.collections.remove(col)
    for mat in list(bpy.data.materials):
        bpy.data.materials.remove(mat)


reset_scene()


# ---------------------------------------------------------------------------
# Collections
# ---------------------------------------------------------------------------

col_ext   = ensure_collection("Walls_Exterior")
col_int   = ensure_collection("Walls_Interior")
col_floor = ensure_collection("Floors")
col_roof  = ensure_collection("Roof")
col_doors = ensure_collection("Doors")
col_env   = ensure_collection("Environment")


# ---------------------------------------------------------------------------
# Materials
# ---------------------------------------------------------------------------

mat_ext_wall  = make_material("ext_wall",   (0.76, 0.60, 0.42), roughness=0.9)   # warm stone
mat_int_wall  = make_material("int_wall",   (0.92, 0.90, 0.85), roughness=0.85)  # off-white
mat_wood      = make_material("floor_wood", (0.55, 0.35, 0.18), roughness=0.75)  # wood planks
mat_tile      = make_material("floor_tile", (0.80, 0.78, 0.75), roughness=0.4)   # light tile
mat_roof      = make_material("roof",       (0.72, 0.28, 0.15), roughness=0.85)  # terracotta
mat_door      = make_material("door",       (0.22, 0.14, 0.08), roughness=0.7)   # dark wood
mat_grass     = make_material("grass",      (0.25, 0.52, 0.18), roughness=0.95)  # grass


# ---------------------------------------------------------------------------
# Exterior Walls
# (each wall is split around doorway openings into up to 3 segments:
#  left/right of opening, and the header above the opening)
# ---------------------------------------------------------------------------

# Z centre for a full-height wall slab
WZ = WH / 2.0
# Z centre and height of the header piece above a doorway
HEADER_Z  = DOOR_H + (WH - DOOR_H) / 2.0
HEADER_SZ = WH - DOOR_H

# --- Front wall (Y = Y_MIN, runs X_MIN..X_MAX) —— has front door ---
# Left segment: X_MIN .. FRONT_DOOR_X_MIN
add_box("EW_Front_Left",
        cx=(X_MIN + FRONT_DOOR_X_MIN) / 2, cy=Y_MIN + WT / 2, cz=WZ,
        sx=FRONT_DOOR_X_MIN - X_MIN, sy=WT, sz=WH,
        collection=col_ext, material=mat_ext_wall)

# Right segment: FRONT_DOOR_X_MAX .. X_MAX
add_box("EW_Front_Right",
        cx=(FRONT_DOOR_X_MAX + X_MAX) / 2, cy=Y_MIN + WT / 2, cz=WZ,
        sx=X_MAX - FRONT_DOOR_X_MAX, sy=WT, sz=WH,
        collection=col_ext, material=mat_ext_wall)

# Header above front door
add_box("EW_Front_Header",
        cx=(FRONT_DOOR_X_MIN + FRONT_DOOR_X_MAX) / 2, cy=Y_MIN + WT / 2, cz=HEADER_Z,
        sx=DOOR_W, sy=WT, sz=HEADER_SZ,
        collection=col_ext, material=mat_ext_wall)

# --- Back wall (Y = Y_MAX, no opening) ---
add_box("EW_Back",
        cx=0.0, cy=Y_MAX - WT / 2, cz=WZ,
        sx=X_MAX - X_MIN, sy=WT, sz=WH,
        collection=col_ext, material=mat_ext_wall)

# --- Left wall (X = X_MIN, no opening) ---
add_box("EW_Left",
        cx=X_MIN + WT / 2, cy=0.0, cz=WZ,
        sx=WT, sy=Y_MAX - Y_MIN, sz=WH,
        collection=col_ext, material=mat_ext_wall)

# --- Right wall (X = X_MAX, no opening) ---
add_box("EW_Right",
        cx=X_MAX - WT / 2, cy=0.0, cz=WZ,
        sx=WT, sy=Y_MAX - Y_MIN, sz=WH,
        collection=col_ext, material=mat_ext_wall)


# ---------------------------------------------------------------------------
# Interior Walls
# ---------------------------------------------------------------------------

# Helper: wall segment along X axis with doorway cutout
def x_wall_with_door(prefix, x_min, x_max, y_pos, door_x_min, door_x_max, col):
    """Horizontal interior wall (constant Y) with a doorway cut out."""
    half_t = WT / 2
    # Left of door
    if door_x_min > x_min:
        add_box(f"{prefix}_SegL",
                cx=(x_min + door_x_min) / 2, cy=y_pos, cz=WZ,
                sx=door_x_min - x_min, sy=WT, sz=WH,
                collection=col, material=mat_int_wall)
    # Right of door
    if door_x_max < x_max:
        add_box(f"{prefix}_SegR",
                cx=(door_x_max + x_max) / 2, cy=y_pos, cz=WZ,
                sx=x_max - door_x_max, sy=WT, sz=WH,
                collection=col, material=mat_int_wall)
    # Header
    add_box(f"{prefix}_Header",
            cx=(door_x_min + door_x_max) / 2, cy=y_pos, cz=HEADER_Z,
            sx=DOOR_W, sy=WT, sz=HEADER_SZ,
            collection=col, material=mat_int_wall)


def y_wall_with_door(prefix, y_min, y_max, x_pos, door_y_min, door_y_max, col):
    """Vertical interior wall (constant X) with a doorway cut out."""
    # Bottom of door
    if door_y_min > y_min:
        add_box(f"{prefix}_SegB",
                cx=x_pos, cy=(y_min + door_y_min) / 2, cz=WZ,
                sx=WT, sy=door_y_min - y_min, sz=WH,
                collection=col, material=mat_int_wall)
    # Top of door
    if door_y_max < y_max:
        add_box(f"{prefix}_SegT",
                cx=x_pos, cy=(door_y_max + y_max) / 2, cz=WZ,
                sx=WT, sy=y_max - door_y_max, sz=WH,
                collection=col, material=mat_int_wall)
    # Header
    add_box(f"{prefix}_Header",
            cx=x_pos, cy=(door_y_min + door_y_max) / 2, cz=HEADER_Z,
            sx=WT, sy=DOOR_W, sz=HEADER_SZ,
            collection=col, material=mat_int_wall)


# Front rooms / Bedroom divider (Y = Y_MID), runs X_MIN..X_MAX
# Two separate doorways: Kitchen<->Bedroom (left), Bathroom<->Bedroom (right)
# Build as 4 solid segments + 2 headers

# Segment: X_MIN .. KIT_BED_X_MIN
add_box("IW_YMid_Seg1",
        cx=(X_MIN + KIT_BED_X_MIN) / 2, cy=Y_MID, cz=WZ,
        sx=KIT_BED_X_MIN - X_MIN, sy=WT, sz=WH,
        collection=col_int, material=mat_int_wall)
# Header above Kitchen<->Bedroom door
add_box("IW_YMid_Header1",
        cx=(KIT_BED_X_MIN + KIT_BED_X_MAX) / 2, cy=Y_MID, cz=HEADER_Z,
        sx=DOOR_W, sy=WT, sz=HEADER_SZ,
        collection=col_int, material=mat_int_wall)
# Segment: KIT_BED_X_MAX .. BATH_BED_X_MIN
add_box("IW_YMid_Seg2",
        cx=(KIT_BED_X_MAX + BATH_BED_X_MIN) / 2, cy=Y_MID, cz=WZ,
        sx=BATH_BED_X_MIN - KIT_BED_X_MAX, sy=WT, sz=WH,
        collection=col_int, material=mat_int_wall)
# Header above Bathroom<->Bedroom door
add_box("IW_YMid_Header2",
        cx=(BATH_BED_X_MIN + BATH_BED_X_MAX) / 2, cy=Y_MID, cz=HEADER_Z,
        sx=DOOR_W, sy=WT, sz=HEADER_SZ,
        collection=col_int, material=mat_int_wall)
# Segment: BATH_BED_X_MAX .. X_MAX
add_box("IW_YMid_Seg3",
        cx=(BATH_BED_X_MAX + X_MAX) / 2, cy=Y_MID, cz=WZ,
        sx=X_MAX - BATH_BED_X_MAX, sy=WT, sz=WH,
        collection=col_int, material=mat_int_wall)

# Kitchen / Bathroom divider (X = X_MID), runs Y_MIN..Y_MID, doorway in middle
y_wall_with_door("IW_XMid", Y_MIN, Y_MID, X_MID,
                 KIT_BATH_Y_MIN, KIT_BATH_Y_MAX, col_int)


# ---------------------------------------------------------------------------
# Floors
# ---------------------------------------------------------------------------

FLOOR_Z = 0.0   # top of floor slab at Z=0
SLAB_T  = 0.02

# Kitchen: X_MIN+WT .. X_MID, Y_MIN+WT .. Y_MID
add_floor_patch("Floor_Kitchen",
                X_MIN + WT, X_MID, Y_MIN + WT, Y_MID,
                FLOOR_Z, col_floor, mat_tile)

# Bathroom: X_MID .. X_MAX-WT, Y_MIN+WT .. Y_MID
add_floor_patch("Floor_Bathroom",
                X_MID, X_MAX - WT, Y_MIN + WT, Y_MID,
                FLOOR_Z, col_floor, mat_tile)

# Bedroom: X_MIN+WT .. X_MAX-WT, Y_MID .. Y_MAX-WT
add_floor_patch("Floor_Bedroom",
                X_MIN + WT, X_MAX - WT, Y_MID, Y_MAX - WT,
                FLOOR_Z, col_floor, mat_wood)

# Doorway gap patches — floor under each opening so there are no holes
# Front door opening (exterior threshold, kitchen side)
add_floor_patch("Floor_FrontDoor",
                FRONT_DOOR_X_MIN, FRONT_DOOR_X_MAX, Y_MIN, Y_MIN + WT,
                FLOOR_Z, col_floor, mat_tile)

# Kitchen <-> Bedroom doorway
add_floor_patch("Floor_KitBed",
                KIT_BED_X_MIN, KIT_BED_X_MAX, Y_MID - WT / 2, Y_MID + WT / 2,
                FLOOR_Z, col_floor, mat_tile)

# Bathroom <-> Bedroom doorway
add_floor_patch("Floor_BathBed",
                BATH_BED_X_MIN, BATH_BED_X_MAX, Y_MID - WT / 2, Y_MID + WT / 2,
                FLOOR_Z, col_floor, mat_tile)

# Kitchen <-> Bathroom doorway
add_floor_patch("Floor_KitBath",
                X_MID - WT / 2, X_MID + WT / 2, KIT_BATH_Y_MIN, KIT_BATH_Y_MAX,
                FLOOR_Z, col_floor, mat_tile)


# ---------------------------------------------------------------------------
# Roof — triangular prism via bmesh (gable roof, ridge along X axis)
# ---------------------------------------------------------------------------

ROOF_OVERHANG = 0.3
RIDGE_H = 1.2   # height of the ridge above the walls

rx_min = X_MIN - ROOF_OVERHANG
rx_max = X_MAX + ROOF_OVERHANG
ry_min = Y_MIN - ROOF_OVERHANG
ry_max = Y_MAX + ROOF_OVERHANG
rz_base = WH
rz_ridge = WH + RIDGE_H

# 6 vertices of the triangular prism
verts = [
    (rx_min, ry_min, rz_base),   # 0 front-left eave
    (rx_max, ry_min, rz_base),   # 1 front-right eave
    (rx_max, ry_max, rz_base),   # 2 back-right eave
    (rx_min, ry_max, rz_base),   # 3 back-left eave
    (rx_min, 0.0,    rz_ridge),  # 4 front ridge (mid-Y)
    (rx_max, 0.0,    rz_ridge),  # 5 back ridge  (mid-Y)
]

# Faces: gable ends (triangles) + roof slopes (quads)
faces = [
    (0, 1, 5, 4),   # front slope (facing -Y)
    (3, 4, 5, 2),   # back slope  (facing +Y) — note winding
    (0, 4, 3),      # left gable
    (1, 2, 5),      # right gable  (reversed winding for outward normal)
    (0, 3, 2, 1),   # soffit / ceiling (optional, faces inward)
]

mesh = bpy.data.meshes.new("RoofMesh")
bm = bmesh.new()
bm_verts = [bm.verts.new(v) for v in verts]
for f in faces:
    bm.faces.new([bm_verts[i] for i in f])
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.to_mesh(mesh)
bm.free()

roof_obj = bpy.data.objects.new("Roof", mesh)
roof_obj.data.materials.append(mat_roof)
col_roof.objects.link(roof_obj)

# Apply transforms (already at world origin, no extra transform needed)
bpy.context.view_layer.objects.active = roof_obj
roof_obj.select_set(True)
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
roof_obj.select_set(False)


# ---------------------------------------------------------------------------
# Door frame / slab for front door (visible door object, not a collision wall)
# ---------------------------------------------------------------------------

# Thin door slab sitting in the front door opening, slightly ajar
DOOR_THICK = 0.05
door_cx = (FRONT_DOOR_X_MIN + FRONT_DOOR_X_MAX) / 2
add_box("Door_Front",
        cx=door_cx, cy=Y_MIN + WT + DOOR_THICK / 2, cz=DOOR_H / 2,
        sx=DOOR_W, sy=DOOR_THICK, sz=DOOR_H,
        collection=col_doors, material=mat_door)


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

# Ground plane at Z = -0.15 (below floor, no z-fighting)
add_box("Ground",
        cx=0.0, cy=0.0, cz=-0.15 - 0.05,
        sx=30.0, sy=30.0, sz=0.1,
        collection=col_env, material=mat_grass)

# Sun light
bpy.ops.object.light_add(type='SUN', location=(5.0, -8.0, 10.0))
sun = bpy.context.active_object
sun.name = "Sun"
sun.data.energy = 3.0
sun.rotation_euler = (0.785, 0.0, 0.523)
for col in list(sun.users_collection):
    col.objects.unlink(sun)
col_env.objects.link(sun)

# Interior point light (centre of house, mid-height)
bpy.ops.object.light_add(type='POINT', location=(0.0, 0.0, 1.8))
pt_light = bpy.context.active_object
pt_light.name = "Interior_Light"
pt_light.data.energy = 200.0
pt_light.data.color = (1.0, 0.95, 0.85)
for col in list(pt_light.users_collection):
    col.objects.unlink(pt_light)
col_env.objects.link(pt_light)

# Camera — outside front, slightly elevated, looking at house centre
bpy.ops.object.camera_add(location=(-2.0, -9.0, 3.5))
cam = bpy.context.active_object
cam.name = "Camera"
cam.rotation_euler = (1.15, 0.0, -0.2)
bpy.context.scene.camera = cam
for col in list(cam.users_collection):
    col.objects.unlink(cam)
col_env.objects.link(cam)


# ---------------------------------------------------------------------------
# Apply all remaining transforms (safety pass)
# ---------------------------------------------------------------------------

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
bpy.ops.object.select_all(action='DESELECT')


# ---------------------------------------------------------------------------
# Viewport: Material Preview mode
# ---------------------------------------------------------------------------

for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        for space in area.spaces:
            if space.type == 'VIEW_3D':
                space.shading.type = 'MATERIAL'
        break

print("house_shell.py: done — house shell created.")
