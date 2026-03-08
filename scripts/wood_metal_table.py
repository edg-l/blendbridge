import bpy
import bmesh
import math
from bl_ext.user_default.blendbridge_addon.textures import apply_pbr

# --- Dimensions ---
TABLE_W = 1.2   # X
TABLE_D = 0.7   # Y
TABLE_H = 0.75  # Z total height
TOP_THICK = 0.04
LEG_SIZE = 0.04   # square tube cross-section
FRAME_W = 0.04    # frame bar width/height

# Derived
top_z = TABLE_H - TOP_THICK / 2
frame_z = TABLE_H - TOP_THICK - FRAME_W / 2
actual_leg_h = TABLE_H - TOP_THICK - FRAME_W  # floor to bottom of frame
actual_leg_z = actual_leg_h / 2

# Insets for frame/legs from table edge
inset_x = 0.06
inset_y = 0.06
fx = TABLE_W / 2 - inset_x
fy = TABLE_D / 2 - inset_y

# --- Texture paths ---
WOOD_TEX = "/home/edgar/textures_2d/WoodFloor043_2K"
METAL_TEX = "/home/edgar/textures_2d/Metal046A_2K"

# --- Helpers ---
def cube_uv(obj):
    """UV unwrap with cube projection — best for box-like shapes."""
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.cube_project(cube_size=1.0)
    bpy.ops.object.mode_set(mode='OBJECT')

def remove_displacement(mat):
    """Remove displacement nodes — causes artifacts on game-scale geometry."""
    nodes = mat.node_tree.nodes
    to_remove = [n for n in nodes if n.type == 'DISPLACEMENT' or
                 (n.type == 'TEX_IMAGE' and n.image and 'Displacement' in n.image.name)]
    for n in to_remove:
        nodes.remove(n)

def apply_metal(obj):
    """Apply metal PBR with cube UVs, no displacement, smooth shading."""
    cube_uv(obj)
    apply_pbr(obj, METAL_TEX)
    remove_displacement(obj.data.materials[0])
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.shade_smooth()
    bpy.ops.object.select_all(action='DESELECT')

bpy.ops.object.select_all(action='DESELECT')

# === Tabletop ===
bpy.ops.mesh.primitive_cube_add(size=1)
top = bpy.context.active_object
top.name = "tabletop"
top.scale = (TABLE_W, TABLE_D, TOP_THICK)
top.location = (0, 0, top_z)
bpy.ops.object.transform_apply(scale=True)

# Bevel edges before texturing
bm = bmesh.new()
bm.from_mesh(top.data)
bmesh.ops.bevel(bm, geom=bm.edges[:], offset=0.003, segments=2)
bm.to_mesh(top.data)
bm.free()

cube_uv(top)
apply_pbr(top, WOOD_TEX)
remove_displacement(top.data.materials[0])
top.select_set(True)
bpy.context.view_layer.objects.active = top
bpy.ops.object.shade_smooth()
bpy.ops.object.select_all(action='DESELECT')

# === Metal frame + legs (single unified mesh, no overlaps) ===
frame_top = TABLE_H - TOP_THICK
frame_bot = frame_top - FRAME_W
hw = FRAME_W / 2  # half-width of frame bar cross-section

bm = bmesh.new()

def bm_box(x0, y0, z0, x1, y1, z1):
    """Add an axis-aligned box to the bmesh."""
    verts = [
        bm.verts.new((x0, y0, z0)), bm.verts.new((x1, y0, z0)),
        bm.verts.new((x1, y1, z0)), bm.verts.new((x0, y1, z0)),
        bm.verts.new((x0, y0, z1)), bm.verts.new((x1, y0, z1)),
        bm.verts.new((x1, y1, z1)), bm.verts.new((x0, y1, z1)),
    ]
    bm.faces.new([verts[0], verts[3], verts[2], verts[1]])  # bottom
    bm.faces.new([verts[4], verts[5], verts[6], verts[7]])  # top
    bm.faces.new([verts[0], verts[1], verts[5], verts[4]])  # front
    bm.faces.new([verts[2], verts[3], verts[7], verts[6]])  # back
    bm.faces.new([verts[0], verts[4], verts[7], verts[3]])  # left
    bm.faces.new([verts[1], verts[2], verts[6], verts[5]])  # right

# Lower legs — floor to frame bottom (below the bars)
for lx, ly in [(fx, fy), (fx, -fy), (-fx, fy), (-fx, -fy)]:
    bm_box(lx - hw, ly - hw, 0, lx + hw, ly + hw, frame_bot)

# Corner blocks — same height as frame bars, at each corner
for lx, ly in [(fx, fy), (fx, -fy), (-fx, fy), (-fx, -fy)]:
    bm_box(lx - hw, ly - hw, frame_bot, lx + hw, ly + hw, frame_top)

# Long bars (along X) — fit BETWEEN corner blocks
bm_box(-fx + hw,  fy - hw, frame_bot,  fx - hw,  fy + hw, frame_top)  # back
bm_box(-fx + hw, -fy - hw, frame_bot,  fx - hw, -fy + hw, frame_top)  # front

# Short bars (along Y) — fit BETWEEN corner blocks
bm_box( fx - hw, -fy + hw, frame_bot,  fx + hw,  fy - hw, frame_top)  # right
bm_box(-fx - hw, -fy + hw, frame_bot, -fx + hw,  fy - hw, frame_top)  # left

# Merge touching vertices where pieces meet
bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=0.001)

# Remove duplicate faces (shared internal faces between touching pieces)
face_map = {}
for f in bm.faces:
    key = frozenset(v.index for v in f.verts)
    face_map.setdefault(key, []).append(f)
dupes = []
for faces in face_map.values():
    if len(faces) > 1:
        dupes.extend(faces)
if dupes:
    bmesh.ops.delete(bm, geom=dupes, context='FACES_ONLY')

# Clean up normals
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])

# Create the mesh object
frame_mesh = bpy.data.meshes.new("frame_mesh")
bm.to_mesh(frame_mesh)
bm.free()

frame_obj = bpy.data.objects.new("metal_frame", frame_mesh)
bpy.context.collection.objects.link(frame_obj)
bpy.context.view_layer.objects.active = frame_obj
frame_obj.select_set(True)

apply_metal(frame_obj)

# === Lighting (3-point, tracked to tabletop) ===
def add_tracked_light(name, loc, energy, color, size):
    bpy.ops.object.light_add(type='AREA', location=loc)
    light = bpy.context.active_object
    light.name = name
    light.data.energy = energy
    light.data.color = color
    light.data.size = size
    c = light.constraints.new('TRACK_TO')
    c.target = bpy.data.objects["tabletop"]
    c.track_axis = 'TRACK_NEGATIVE_Z'
    c.up_axis = 'UP_Y'

add_tracked_light("key_light",  (3.0, -3.0, 4.0), 300, (1.0, 0.95, 0.9), 2.0)
add_tracked_light("fill_light", (-3.0, -1.5, 3.0), 100, (0.85, 0.9, 1.0), 2.0)
add_tracked_light("rim_light",  (0.0, 3.0, 3.5),    80, (1.0, 1.0, 1.0),  1.5)

# === Camera ===
bpy.ops.object.camera_add(location=(1.8, -2.2, 1.3))
cam = bpy.context.active_object
cam.name = "Camera"
cam.data.lens = 55
c = cam.constraints.new('TRACK_TO')
c.target = bpy.data.objects["tabletop"]
c.track_axis = 'TRACK_NEGATIVE_Z'
c.up_axis = 'UP_Y'
bpy.context.scene.camera = cam

print("Table created successfully")
