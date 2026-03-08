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
    move_to_collection(obj, coll_name=collection)
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


mat_porcelain = mat("bathtub_porcelain", (0.95, 0.95, 0.93), roughness=0.2)
mat_faucet    = mat("bathtub_faucet",    (0.70, 0.70, 0.72), roughness=0.15, metallic=0.8)
mat_water     = mat("bathtub_water",     (0.50, 0.70, 0.85), roughness=0.1)

COLL = "Bathtub"

# ============================================================
# DIMENSIONS
# ============================================================
TUB_W  = 0.75   # X
TUB_L  = 1.60   # Y
TUB_H  = 0.55   # Z
WALL   = 0.06   # wall thickness
RIM    = 0.02   # rim overhang beyond outer body

WATER_Z = 0.30  # water surface height

# Faucet end is at +Y
FAUCET_END_Y = TUB_L / 2

# ============================================================
# 1. OUTER SHELL — tapered ends via bmesh
# ============================================================
# Build a custom mesh: outer hull with slightly pinched Y ends for a gentle taper.
# Top and bottom are flat; the four vertical sides taper in X at the Y ends.

TAPER = 0.04  # how much to pinch each end inward in X at the very tips

shell_mesh = bpy.data.meshes.new("bathtub_shell_mesh")
shell_obj  = bpy.data.objects.new("bathtub_shell", shell_mesh)
bpy.context.scene.collection.objects.link(shell_obj)

bm = bmesh.new()

hw = TUB_W / 2
hl = TUB_L / 2
h  = TUB_H

# Bottom ring (6 verts, going around CCW from foot-left)
B = [
    bm.verts.new((-hw + TAPER, -hl, 0)),  # 0 foot-left
    bm.verts.new(( hw - TAPER, -hl, 0)),  # 1 foot-right
    bm.verts.new(( hw,          0,  0)),  # 2 mid-right
    bm.verts.new(( hw - TAPER,  hl, 0)),  # 3 head-right
    bm.verts.new((-hw + TAPER,  hl, 0)),  # 4 head-left
    bm.verts.new((-hw,          0,  0)),  # 5 mid-left
]
# Top ring
T = [
    bm.verts.new((-hw + TAPER, -hl, h)),  # 0
    bm.verts.new(( hw - TAPER, -hl, h)),  # 1
    bm.verts.new(( hw,          0,  h)),  # 2
    bm.verts.new(( hw - TAPER,  hl, h)),  # 3
    bm.verts.new((-hw + TAPER,  hl, h)),  # 4
    bm.verts.new((-hw,          0,  h)),  # 5
]

bm.verts.ensure_lookup_table()

# Bottom face
bm.faces.new([B[0], B[5], B[4], B[3], B[2], B[1]])

# Top face
bm.faces.new([T[0], T[1], T[2], T[3], T[4], T[5]])

# Side faces (6 quads wrapping around)
n = len(B)
for i in range(n):
    j = (i + 1) % n
    bm.faces.new([B[i], B[j], T[j], T[i]])

bm.to_mesh(shell_mesh)
bm.free()

bpy.ops.object.select_all(action='DESELECT')
shell_obj.select_set(True)
bpy.context.view_layer.objects.active = shell_obj
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
bpy.ops.object.shade_flat()
shell_obj.data.materials.append(mat_porcelain)
move_to_collection(shell_obj, COLL)
if shell_obj.name in bpy.context.scene.collection.objects:
    bpy.context.scene.collection.objects.unlink(shell_obj)

# ============================================================
# 2. INNER BOX — hollow out the inside visually with a darker inset
# The "inside" is a slightly smaller box raised from the bottom, same color
# (in low-poly, we just leave the shell open-top; inner is implied).
# Add a thin inner floor box to close the bottom visually.
# ============================================================
inner_floor_z = WALL
inner_w = TUB_W - WALL * 2
inner_l = TUB_L - WALL * 2
make_box(
    "bathtub_inner_floor",
    0, 0, inner_floor_z / 2,
    inner_w, inner_l, inner_floor_z,
    mat_porcelain, COLL
)

# ============================================================
# 3. RIM — thin flat box overhanging the top edge on all sides
# ============================================================
rim_w = TUB_W + RIM * 2
rim_l = TUB_L + RIM * 2
rim_h = 0.025
make_box(
    "bathtub_rim",
    0, 0, TUB_H + rim_h / 2,
    rim_w, rim_l, rim_h,
    mat_porcelain, COLL
)

# ============================================================
# 4. WATER SURFACE — flat plane inside the tub
# ============================================================
make_box(
    "bathtub_water",
    0, 0, WATER_Z,
    inner_w - 0.01, inner_l - 0.01, 0.01,
    mat_water, COLL
)

# ============================================================
# 5. FAUCET — at the head (+Y) end
# ============================================================
# Vertical riser pipe
PIPE_R   = 0.025
PIPE_H   = 0.18
PIPE_CX  = 0.0
PIPE_CY  = FAUCET_END_Y - WALL - 0.03
PIPE_BOT = TUB_H + rim_h  # sits on the rim top
PIPE_CZ  = PIPE_BOT + PIPE_H / 2

make_cylinder(
    "faucet_riser",
    PIPE_CX, PIPE_CY, PIPE_CZ,
    radius=PIPE_R, depth=PIPE_H, verts=8,
    rot_x=0.0,
    material=mat_faucet, collection=COLL
)

# Angled spout box — rotated slightly forward and down toward the tub interior
SPOUT_W = 0.04
SPOUT_D = 0.14
SPOUT_H = 0.035
# Spout starts at top of riser, angles into the tub (-Y direction)
SPOUT_CY = PIPE_CY - SPOUT_D / 2 * math.cos(math.radians(20))
SPOUT_CZ = PIPE_BOT + PIPE_H - SPOUT_H / 2 - 0.01

bpy.ops.mesh.primitive_cube_add(
    size=1,
    location=(PIPE_CX, SPOUT_CY, SPOUT_CZ)
)
spout = bpy.context.active_object
spout.name = "faucet_spout"
spout.scale = (SPOUT_W, SPOUT_D, SPOUT_H)
spout.rotation_euler = (math.radians(-20), 0, 0)
bpy.ops.object.select_all(action='DESELECT')
spout.select_set(True)
bpy.context.view_layer.objects.active = spout
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
bpy.ops.object.shade_flat()
spout.data.materials.append(mat_faucet)
move_to_collection(spout, COLL)

# ============================================================
# DONE
# ============================================================
bpy.ops.object.select_all(action='DESELECT')
print("Bathtub created successfully.")
