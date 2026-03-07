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

def make_box(name, cx, cy, cz, sx, sy, sz, material, collection):
    """Create a box with applied scale, material, and collection assignment."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=(cx, cy, cz))
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (sx, sy, sz)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bpy.ops.object.shade_flat()
    obj.data.materials.append(material)
    move_to_collection(obj, collection)
    return obj

def make_cylinder(name, cx, cy, cz, radius, depth, verts, material, collection):
    """Create a cylinder with applied transforms."""
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=radius, depth=depth, location=(cx, cy, cz))
    obj = bpy.context.active_object
    obj.name = name
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bpy.ops.object.shade_flat()
    obj.data.materials.append(material)
    move_to_collection(obj, collection)
    return obj

# ============================================================
# MATERIALS — create once, reuse everywhere
# ============================================================
def mat(name, color, roughness=0.8, metallic=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return m

mat_ext_wall  = mat("ext_wall",   (0.85, 0.78, 0.65, 1))       # warm stone
mat_int_wall  = mat("int_wall",   (0.92, 0.90, 0.85, 1))       # off-white
mat_floor_wood= mat("floor_wood", (0.55, 0.38, 0.20, 1))       # wood floor
mat_floor_tile= mat("floor_tile", (0.75, 0.75, 0.73, 1))       # grey tile
mat_roof      = mat("roof",       (0.50, 0.16, 0.10, 1))       # terracotta
mat_door      = mat("door",       (0.35, 0.22, 0.10, 1))       # dark wood
mat_counter   = mat("counter",    (0.65, 0.60, 0.55, 1))       # light stone
mat_appliance = mat("appliance",  (0.85, 0.85, 0.85, 1), 0.3, 0.4)  # steel
mat_stove_top = mat("stove_top",  (0.15, 0.15, 0.15, 1), 0.4)  # dark
mat_fridge    = mat("fridge",     (0.90, 0.90, 0.92, 1), 0.3, 0.2)
mat_wood      = mat("wood",       (0.50, 0.33, 0.15, 1))       # furniture wood
mat_bed_frame = mat("bed_frame",  (0.45, 0.30, 0.15, 1))       # bed wood
mat_mattress  = mat("mattress",   (0.90, 0.88, 0.82, 1))       # cream
mat_pillow    = mat("pillow",     (0.95, 0.95, 0.95, 1))       # white
mat_blanket   = mat("blanket",    (0.25, 0.35, 0.55, 1))       # blue
mat_porcelain = mat("porcelain",  (0.95, 0.95, 0.93, 1), 0.2)  # white ceramic
mat_mirror    = mat("mirror",     (0.7, 0.8, 0.9, 1), 0.05, 0.8)  # reflective
mat_water     = mat("water",      (0.5, 0.7, 0.85, 1), 0.1)    # blue tint
mat_curtain   = mat("curtain",    (0.70, 0.55, 0.40, 1))       # warm fabric
mat_grass     = mat("grass",      (0.25, 0.55, 0.15, 1))
mat_chair_seat= mat("chair_seat", (0.60, 0.25, 0.15, 1))       # reddish wood

# ============================================================
# DIMENSIONS — everything derived from these
# ============================================================
# House exterior: 8 wide (X), 6 deep (Y), 2.5 tall
HW = 8.0   # house width
HD = 6.0   # house depth
WH = 2.5   # wall height
WT = 0.15  # wall thickness

# Room boundaries
X_MIN, X_MAX = -HW/2, HW/2          # -4, 4
Y_MIN, Y_MAX = -HD/2, HD/2          # -3, 3
X_MID = 0.0   # kitchen/bathroom divider
Y_MID = 0.0   # front rooms / bedroom divider

# Door dimensions
DOOR_W = 1.0
DOOR_H = 1.8

# ============================================================
# FLOOR — per room with different materials
# ============================================================
# Kitchen floor (tile)
make_box("floor_kitchen", -2, -1.5, -0.025, 4-WT, 3-WT, 0.05, mat_floor_tile, "Floors")
# Bathroom floor (tile)
make_box("floor_bathroom", 2, -1.5, -0.025, 4-WT, 3-WT, 0.05, mat_floor_tile, "Floors")
# Bedroom floor (wood)
make_box("floor_bedroom", 0, 1.5, -0.025, 8-WT, 3-WT, 0.05, mat_floor_wood, "Floors")

# Doorway floor patches (fill the gap under wall thickness)
# Kitchen ↔ Bedroom doorway (X: -2.5 to -1.5, Y: 0)
make_box("floor_door_kit_bed", -2.0, 0, -0.025, DOOR_W, WT + 0.02, 0.05, mat_floor_wood, "Floors")
# Bathroom ↔ Bedroom doorway (X: 1.5 to 2.5, Y: 0)
make_box("floor_door_bath_bed", 2.0, 0, -0.025, DOOR_W, WT + 0.02, 0.05, mat_floor_wood, "Floors")
# Kitchen ↔ Bathroom doorway (X: 0, Y: -1.5 to -0.5)
make_box("floor_door_kit_bath", 0, -1.0, -0.025, WT + 0.02, DOOR_W, 0.05, mat_floor_tile, "Floors")

# ============================================================
# EXTERIOR WALLS — with door opening in front
# ============================================================
# Front wall: two segments with gap for door (X: -0.5 to 0.5)
front_door_x = -1.0  # door center X
door_left  = front_door_x - DOOR_W/2   # -1.5
door_right = front_door_x + DOOR_W/2   # -0.5

# Front-left segment: X_MIN to door_left
seg_w = door_left - X_MIN  # 2.5
make_box("wall_front_L", X_MIN + seg_w/2, Y_MIN, WH/2, seg_w, WT, WH, mat_ext_wall, "Walls_Exterior")

# Front-right segment: door_right to X_MAX
seg_w = X_MAX - door_right  # 4.5
make_box("wall_front_R", door_right + seg_w/2, Y_MIN, WH/2, seg_w, WT, WH, mat_ext_wall, "Walls_Exterior")

# Front wall above door
make_box("wall_front_above_door", front_door_x, Y_MIN, DOOR_H + (WH - DOOR_H)/2,
         DOOR_W, WT, WH - DOOR_H, mat_ext_wall, "Walls_Exterior")

# Back wall (solid)
make_box("wall_back", 0, Y_MAX, WH/2, HW, WT, WH, mat_ext_wall, "Walls_Exterior")

# Left wall (solid)
make_box("wall_left", X_MIN, 0, WH/2, WT, HD, WH, mat_ext_wall, "Walls_Exterior")

# Right wall (solid)
make_box("wall_right", X_MAX, 0, WH/2, WT, HD, WH, mat_ext_wall, "Walls_Exterior")

# ============================================================
# INTERIOR WALLS
# ============================================================
# Horizontal wall at Y=0 (front rooms ↔ bedroom)
# Doorway from kitchen to bedroom at X: -2.5 to -1.5
# Doorway from bathroom to bedroom at X: 1.5 to 2.5
int_doors = [(-2.0, "kit_bed"), (2.0, "bath_bed")]  # door centers

# Segments: X_MIN to -2.5 | -1.5 to 1.5 | 2.5 to X_MAX
segs_h = [
    (X_MIN, -2.5),
    (-1.5,   1.5),
    ( 2.5, X_MAX),
]
for i, (x1, x2) in enumerate(segs_h):
    w = x2 - x1
    make_box(f"wall_int_h_{i}", (x1+x2)/2, Y_MID, WH/2, w, WT, WH, mat_int_wall, "Walls_Interior")

# Above interior horizontal doorways
for dx, label in int_doors:
    make_box(f"wall_int_h_above_{label}", dx, Y_MID, DOOR_H + (WH-DOOR_H)/2,
             DOOR_W, WT, WH - DOOR_H, mat_int_wall, "Walls_Interior")

# Vertical wall at X=0 (kitchen ↔ bathroom), Y: Y_MIN to Y_MID
# Doorway at Y: -1.5 to -0.5
make_box("wall_int_v_bot", X_MID, (Y_MIN + -1.5)/2, WH/2,
         WT, (-1.5 - Y_MIN), WH, mat_int_wall, "Walls_Interior")
make_box("wall_int_v_top", X_MID, (-0.5 + Y_MID)/2, WH/2,
         WT, (Y_MID - -0.5), WH, mat_int_wall, "Walls_Interior")
make_box("wall_int_v_above_door", X_MID, -1.0, DOOR_H + (WH-DOOR_H)/2,
         WT, DOOR_W, WH - DOOR_H, mat_int_wall, "Walls_Interior")

# ============================================================
# FRONT DOOR (actual door panel, slightly ajar)
# ============================================================
make_box("front_door", door_left + 0.05, Y_MIN - 0.02, DOOR_H/2,
         0.05, DOOR_W * 0.6, DOOR_H, mat_door, "Doors")

# ============================================================
# ROOF — triangular prism, separate object (can hide for top-down view)
# ============================================================
mesh = bpy.data.meshes.new("roof_mesh")
roof_obj = bpy.data.objects.new("roof", mesh)
bpy.context.collection.objects.link(roof_obj)

bm = bmesh.new()
ov = 0.3  # overhang
rw = HW/2 + ov
rd = HD/2 + ov
peak = 1.5
base_z = WH

rv = [
    bm.verts.new((-rw, -rd, base_z)),
    bm.verts.new(( rw, -rd, base_z)),
    bm.verts.new(( rw,  rd, base_z)),
    bm.verts.new((-rw,  rd, base_z)),
    bm.verts.new((  0, -rd, base_z + peak)),
    bm.verts.new((  0,  rd, base_z + peak)),
]
bm.faces.new([rv[0], rv[1], rv[4]])
bm.faces.new([rv[2], rv[3], rv[5]])
bm.faces.new([rv[0], rv[4], rv[5], rv[3]])
bm.faces.new([rv[1], rv[2], rv[5], rv[4]])
bm.faces.new([rv[0], rv[3], rv[2], rv[1]])
bm.to_mesh(mesh)
bm.free()

roof_obj.data.materials.append(mat_roof)
bpy.context.view_layer.objects.active = roof_obj
roof_obj.select_set(True)
bpy.ops.object.shade_flat()
move_to_collection(roof_obj, "Roof")

# ============================================================
# KITCHEN FURNITURE (X: -4 to 0, Y: -3 to 0)
# ============================================================
COLL_K = "Kitchen_Furniture"

# Counter along left wall only (L-shape would block bedroom doorway at X:-2.5 to -1.5)
counter_h = 0.85
counter_d = 0.5
# Left wall counter (along X=-4, from front wall to interior wall)
make_box("counter_left", X_MIN + WT/2 + counter_d/2, -1.5, counter_h/2,
         counter_d, 3 - WT, counter_h, mat_counter, COLL_K)

# Stove (freestanding against back wall, away from doorway)
stove_x = -3.2
stove_y = Y_MID - WT/2 - 0.3
make_box("stove_body", stove_x, stove_y, counter_h/2,
         0.6, 0.55, counter_h, mat_appliance, COLL_K)
# Stove burners
for bx, by_off in [(-0.12, -0.1), (0.12, -0.1), (-0.12, 0.1), (0.12, 0.1)]:
    make_box("burner", stove_x + bx, stove_y + by_off, counter_h + 0.02,
             0.12, 0.12, 0.02, mat_stove_top, COLL_K)

# Sink on left counter (sits on top)
make_box("sink_kitchen", X_MIN + WT/2 + counter_d/2, -0.8, counter_h + 0.02,
         0.35, 0.4, 0.08, mat_appliance, COLL_K)

# Fridge (tall box, right side of kitchen near bathroom wall)
make_box("fridge", X_MID - WT/2 - 0.35, Y_MIN + WT/2 + 0.35, 0.9,
         0.65, 0.65, 1.8, mat_fridge, COLL_K)

# Small kitchen table
table_x, table_y = -2.0, -1.8
make_box("kitchen_table_top", table_x, table_y, 0.7, 0.8, 0.6, 0.05, mat_wood, COLL_K)
# Table legs (linked duplicates)
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
leg_tmpl = bpy.context.active_object
leg_tmpl.name = "ktable_leg_tmpl"
leg_tmpl.scale = (0.05, 0.05, 0.7)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
bpy.ops.object.shade_flat()
leg_tmpl.data.materials.append(mat_wood)
move_to_collection(leg_tmpl, COLL_K)

for i, (lx, ly) in enumerate([(-0.35, -0.25), (0.35, -0.25), (-0.35, 0.25), (0.35, 0.25)]):
    if i == 0:
        leg_tmpl.location = (table_x + lx, table_y + ly, 0.35)
    else:
        leg = leg_tmpl.copy()
        leg.name = f"ktable_leg_{i}"
        leg.location = (table_x + lx, table_y + ly, 0.35)
        get_or_create_collection(COLL_K).objects.link(leg)

# Kitchen chairs (2, on opposite sides of table)
kchair_seat_z = 0.42
# Chair template
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
kc_seat_tmpl = bpy.context.active_object
kc_seat_tmpl.name = "kchair_seat_tmpl"
kc_seat_tmpl.scale = (0.35, 0.35, 0.04)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
bpy.ops.object.shade_flat()
kc_seat_tmpl.data.materials.append(mat_chair_seat)
move_to_collection(kc_seat_tmpl, COLL_K)

# Chair 1: left side, facing +X (toward table)
kc1_x = table_x - 0.7
kc_seat_tmpl.location = (kc1_x, table_y, kchair_seat_z)
make_box("kchair_back_0", kc1_x - 0.16, table_y, kchair_seat_z + 0.22, 0.04, 0.35, 0.4, mat_chair_seat, COLL_K)

# Chair 2: right side, facing -X (toward table)
kc2_x = table_x + 0.7
kc2 = kc_seat_tmpl.copy()
kc2.name = "kchair_seat_1"
kc2.location = (kc2_x, table_y, kchair_seat_z)
get_or_create_collection(COLL_K).objects.link(kc2)
make_box("kchair_back_1", kc2_x + 0.16, table_y, kchair_seat_z + 0.22, 0.04, 0.35, 0.4, mat_chair_seat, COLL_K)

# ============================================================
# BATHROOM FURNITURE (X: 0 to 4, Y: -3 to 0)
# ============================================================
COLL_B = "Bathroom_Furniture"

# Bathtub along right wall
tub_x = X_MAX - WT/2 - 0.4
make_box("bathtub_outer", tub_x, -1.5, 0.3, 0.75, 1.6, 0.6, mat_porcelain, COLL_B)
# Inner tub (slightly smaller, slightly raised, water color)
make_box("bathtub_water", tub_x, -1.5, 0.32, 0.6, 1.4, 0.5, mat_water, COLL_B)

# Sink (wall-mounted on the interior vertical wall at X=0)
sink_y = -2.2
make_box("sink_pedestal", X_MID + WT/2 + 0.2, sink_y, 0.4, 0.3, 0.3, 0.8, mat_porcelain, COLL_B)
make_box("sink_basin", X_MID + WT/2 + 0.2, sink_y, 0.82, 0.4, 0.35, 0.08, mat_porcelain, COLL_B)

# Mirror above sink
make_box("mirror", X_MID + 0.01, sink_y, 1.5, 0.02, 0.5, 0.6, mat_mirror, COLL_B)

# Toilet
toilet_y = Y_MIN + WT/2 + 0.35
toilet_x = 1.5
make_box("toilet_base", toilet_x, toilet_y, 0.2, 0.4, 0.5, 0.4, mat_porcelain, COLL_B)
make_box("toilet_tank", toilet_x, toilet_y + 0.2, 0.45, 0.35, 0.15, 0.5, mat_porcelain, COLL_B)
make_box("toilet_seat", toilet_x, toilet_y - 0.05, 0.42, 0.35, 0.35, 0.04, mat_porcelain, COLL_B)

# ============================================================
# BEDROOM FURNITURE (X: -4 to 4, Y: 0 to 3)
# ============================================================
COLL_BR = "Bedroom_Furniture"

# Bed against back wall, centered
bed_x = 0.0
bed_y = Y_MAX - WT/2 - 1.05

# Bed frame
make_box("bed_frame", bed_x, bed_y, 0.25, 1.6, 2.0, 0.3, mat_bed_frame, COLL_BR)
# Headboard
make_box("headboard", bed_x, Y_MAX - WT/2 - 0.05, 0.6, 1.6, 0.08, 0.9, mat_bed_frame, COLL_BR)
# Mattress
make_box("mattress", bed_x, bed_y, 0.45, 1.5, 1.9, 0.15, mat_mattress, COLL_BR)
# Pillow
make_box("pillow", bed_x, bed_y + 0.7, 0.56, 0.6, 0.25, 0.1, mat_pillow, COLL_BR)
# Blanket (covers lower 2/3 of bed)
make_box("blanket", bed_x, bed_y - 0.3, 0.52, 1.5, 1.2, 0.06, mat_blanket, COLL_BR)

# Bedside table (right of bed)
bst_x = bed_x + 1.1
bst_y = bed_y + 0.2
make_box("bedside_table", bst_x, bst_y, 0.3, 0.4, 0.4, 0.6, mat_wood, COLL_BR)

# Desk against left wall
desk_x = X_MIN + WT/2 + 0.4
desk_y = 1.5
make_box("desk_top", desk_x, desk_y, 0.78, 1.0, 0.5, 0.05, mat_wood, COLL_BR)
# Desk legs (linked duplicates)
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
dleg_tmpl = bpy.context.active_object
dleg_tmpl.name = "desk_leg_tmpl"
dleg_tmpl.scale = (0.05, 0.05, 0.78)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
bpy.ops.object.shade_flat()
dleg_tmpl.data.materials.append(mat_wood)
move_to_collection(dleg_tmpl, COLL_BR)

for i, (lx, ly) in enumerate([(-0.45, -0.2), (0.45, -0.2), (-0.45, 0.2), (0.45, 0.2)]):
    if i == 0:
        dleg_tmpl.location = (desk_x + lx, desk_y + ly, 0.39)
    else:
        leg = dleg_tmpl.copy()
        leg.name = f"desk_leg_{i}"
        leg.location = (desk_x + lx, desk_y + ly, 0.39)
        get_or_create_collection(COLL_BR).objects.link(leg)

# Chair at desk
chair_x = desk_x
chair_y = desk_y - 0.55
seat_z = 0.45
# Seat
make_box("chair_seat", chair_x, chair_y, seat_z, 0.4, 0.4, 0.05, mat_chair_seat, COLL_BR)
# Backrest (at -Y edge so chair faces +Y toward desk)
make_box("chair_back", chair_x, chair_y - 0.18, seat_z + 0.25, 0.4, 0.05, 0.45, mat_chair_seat, COLL_BR)
# Chair legs (linked duplicates)
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
cleg_tmpl = bpy.context.active_object
cleg_tmpl.name = "chair_leg_tmpl"
cleg_tmpl.scale = (0.04, 0.04, seat_z - 0.025)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
bpy.ops.object.shade_flat()
cleg_tmpl.data.materials.append(mat_wood)
move_to_collection(cleg_tmpl, COLL_BR)

for i, (lx, ly) in enumerate([(-0.16, -0.16), (0.16, -0.16), (-0.16, 0.16), (0.16, 0.16)]):
    if i == 0:
        cleg_tmpl.location = (chair_x + lx, chair_y + ly, (seat_z - 0.025)/2)
    else:
        leg = cleg_tmpl.copy()
        leg.name = f"chair_leg_{i}"
        leg.location = (chair_x + lx, chair_y + ly, (seat_z - 0.025)/2)
        get_or_create_collection(COLL_BR).objects.link(leg)

# ============================================================
# GROUND PLANE
# ============================================================
make_box("ground", 0, 0, -0.15, 20, 20, 0.1, mat_grass, "Environment")

# ============================================================
# LIGHTING
# ============================================================
bpy.ops.object.light_add(type='SUN', location=(5, -5, 10))
sun = bpy.context.active_object
sun.name = "sun"
sun.data.energy = 3.0
sun.rotation_euler = (math.radians(50), math.radians(10), math.radians(-30))
move_to_collection(sun, "Environment")

# Interior point light (so rooms aren't dark)
bpy.ops.object.light_add(type='POINT', location=(0, 0, 2.2))
pt = bpy.context.active_object
pt.name = "interior_light"
pt.data.energy = 50
pt.data.shadow_soft_size = 1.0
move_to_collection(pt, "Environment")

# ============================================================
# CAMERA
# ============================================================
bpy.ops.object.camera_add(location=(10, -10, 9))
cam = bpy.context.active_object
cam.name = "camera"
cam.rotation_euler = (math.radians(55), 0, math.radians(45))
bpy.context.scene.camera = cam
move_to_collection(cam, "Environment")

# ============================================================
# VIEWPORT — Material Preview + angle to see inside
# ============================================================
for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        for space in area.spaces:
            if space.type == 'VIEW_3D':
                space.shading.type = 'MATERIAL'
                rv3d = space.region_3d
                from mathutils import Vector, Euler
                rv3d.view_location = Vector((0, 0, 1.2))
                rv3d.view_distance = 14
                rv3d.view_rotation = Euler((math.radians(60), 0, math.radians(30))).to_quaternion()
        break

print("House interior scene created!")
