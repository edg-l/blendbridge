import bpy
import bmesh

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


mat_frame   = mat("bed_frame", (0.45, 0.30, 0.15), roughness=0.85)
mat_mattress = mat("mattress",  (0.90, 0.88, 0.82), roughness=0.90)
mat_pillow  = mat("pillow",    (0.95, 0.95, 0.95), roughness=0.92)
mat_blanket = mat("blanket",   (0.25, 0.35, 0.55), roughness=0.95)

COLL = "Bed"

# ============================================================
# BED DIMENSIONS
# ============================================================
# Overall frame outer dimensions
BED_W  = 1.60   # X — width
BED_L  = 2.10   # Y — length
FH     = 0.30   # frame rail height
FT     = 0.07   # frame rail thickness (wall thickness of the rail)
MATTRESS_TOP = 0.48  # Z height of mattress top surface

# Leg dimensions
LEG_W  = 0.08
LEG_H  = FH      # legs fill the frame height
LEG_R  = LEG_W / 2  # half-width for positioning

# Rail inner boundary (legs sit at corners, rails span between them)
INNER_X = BED_W / 2 - LEG_W  # inner edge of leg
INNER_Y = BED_L / 2 - LEG_W

# Headboard / footboard
HB_H   = 0.85   # headboard height above floor
HB_T   = 0.06   # thickness
HB_W   = BED_W + 0.04  # slightly wider than frame
FB_H   = 0.42   # footboard height
FB_T   = 0.06

# Mattress sits inside frame, slightly inset from inner rail edges
M_W    = BED_W - FT * 2 - 0.01   # X
M_L    = BED_L - HB_T - FB_T - 0.01  # Y (clears boards)
M_H    = 0.18   # mattress thickness
M_BOT  = FH     # mattress bottom sits on top of frame rails
M_CZ   = M_BOT + M_H / 2

# Blanket covers lower 2/3 of mattress in Y, extends slightly in X
BLK_L  = M_L * (2 / 3)
BLK_H  = 0.06
BLK_W  = M_W + 0.06  # slight drape
# Blanket centred toward -Y end (foot end)
BLK_CY = -BED_L / 2 + FB_T + BLK_L / 2 + 0.02
BLK_CZ = M_BOT + M_H + BLK_H / 2

# Pillow near headboard
PIL_W  = 0.60   # X
PIL_L  = 0.38   # Y
PIL_H  = 0.10   # Z
PIL_Z  = M_BOT + M_H + PIL_H / 2
PIL_Y  = BED_L / 2 - HB_T - PIL_L / 2 - 0.04
PIL_XO = 0.31   # X offset from centre for each pillow

# ============================================================
# 1. FRAME — four side rails and corner posts handled via legs
# ============================================================

# Long side rails (along Y, left and right)
rail_x_offset = BED_W / 2 - FT / 2
make_box("frame_rail_L", -rail_x_offset, 0, FH / 2, FT, BED_L, FH, mat_frame, COLL)
make_box("frame_rail_R",  rail_x_offset, 0, FH / 2, FT, BED_L, FH, mat_frame, COLL)

# Short end rails (along X, head and foot) — span between the legs
end_rail_w = BED_W - LEG_W * 2
rail_y_offset = BED_L / 2 - LEG_W / 2
make_box("frame_rail_head", 0,  rail_y_offset, FH / 2, end_rail_w, LEG_W, FH, mat_frame, COLL)
make_box("frame_rail_foot", 0, -rail_y_offset, FH / 2, end_rail_w, LEG_W, FH, mat_frame, COLL)

# ============================================================
# 2. LEGS — 4 corner cube legs using linked duplicates
# ============================================================

lx = BED_W / 2 - LEG_R
ly = BED_L / 2 - LEG_R

# Create the first leg mesh, then link-duplicate the rest
bpy.ops.mesh.primitive_cube_add(size=1, location=(-lx, -ly, LEG_H / 2))
leg_base = bpy.context.active_object
leg_base.name = "leg_FL"
leg_base.scale = (LEG_W, LEG_W, LEG_H)
apply_and_finish(leg_base, mat_frame, COLL)

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
# 3. HEADBOARD — shaped top via bmesh
# ============================================================
# Build headboard manually with bmesh to get a flat-arch top:
# base rectangle + two extra top-centre vertices for a subtle peak

hb_mesh = bpy.data.meshes.new("headboard_mesh")
hb_obj  = bpy.data.objects.new("headboard", hb_mesh)
bpy.context.scene.collection.objects.link(hb_obj)

bm = bmesh.new()

hb_y = BED_L / 2 + HB_T / 2   # Y centre of headboard slab
hb_x = HB_W / 2
# Bottom corners
bl = bm.verts.new((-hb_x, 0, 0))
br = bm.verts.new(( hb_x, 0, 0))
# Mid-top corners (full height at sides)
tl = bm.verts.new((-hb_x, 0, HB_H))
tr = bm.verts.new(( hb_x, 0, HB_H))
# Centre arch peak — slightly higher than the side tops
arch_h = HB_H + 0.05
tc_l = bm.verts.new((-hb_x * 0.25, 0, arch_h))
tc_r = bm.verts.new(( hb_x * 0.25, 0, arch_h))

bm.verts.ensure_lookup_table()

# Front face (slab has depth HB_T, extrude in Y)
# Build the front profile polygon
front_verts = [bl, br, tr, tc_r, tc_l, tl]
bm.faces.new(front_verts)

bm.to_mesh(hb_mesh)
bm.free()

# Give it depth by solidifying
bpy.ops.object.select_all(action='DESELECT')
hb_obj.select_set(True)
bpy.context.view_layer.objects.active = hb_obj
bpy.ops.object.modifier_add(type='SOLIDIFY')
hb_obj.modifiers["Solidify"].thickness = HB_T
hb_obj.modifiers["Solidify"].offset = 1.0  # grow toward -Y (into bed)
bpy.ops.object.modifier_apply(modifier="Solidify")

# Position: back face at Y = BED_L/2, so front face at Y = BED_L/2 - HB_T
hb_obj.location = (0, BED_L / 2, 0)

bpy.ops.object.select_all(action='DESELECT')
hb_obj.select_set(True)
bpy.context.view_layer.objects.active = hb_obj
bpy.ops.object.transform_apply(location=True, rotation=False, scale=True)
bpy.ops.object.shade_flat()
hb_obj.data.materials.append(mat_frame)
move_to_collection(hb_obj, COLL)
# Unlink from scene root collection after moving
if hb_obj.name in bpy.context.scene.collection.objects:
    bpy.context.scene.collection.objects.unlink(hb_obj)

# ============================================================
# 4. FOOTBOARD — simple flat board, shorter
# ============================================================
fb_mesh = bpy.data.meshes.new("footboard_mesh")
fb_obj  = bpy.data.objects.new("footboard", fb_mesh)
bpy.context.scene.collection.objects.link(fb_obj)

bm = bmesh.new()
fb_x = HB_W / 2
fb_bl = bm.verts.new((-fb_x, 0, 0))
fb_br = bm.verts.new(( fb_x, 0, 0))
fb_tl = bm.verts.new((-fb_x, 0, FB_H))
fb_tr = bm.verts.new(( fb_x, 0, FB_H))
bm.faces.new([fb_bl, fb_br, fb_tr, fb_tl])
bm.to_mesh(fb_mesh)
bm.free()

bpy.ops.object.select_all(action='DESELECT')
fb_obj.select_set(True)
bpy.context.view_layer.objects.active = fb_obj
bpy.ops.object.modifier_add(type='SOLIDIFY')
fb_obj.modifiers["Solidify"].thickness = FB_T
fb_obj.modifiers["Solidify"].offset = 1.0  # grow toward +Y (into bed)
bpy.ops.object.modifier_apply(modifier="Solidify")

fb_obj.location = (0, -BED_L / 2, 0)
bpy.ops.object.select_all(action='DESELECT')
fb_obj.select_set(True)
bpy.context.view_layer.objects.active = fb_obj
bpy.ops.object.transform_apply(location=True, rotation=False, scale=True)
bpy.ops.object.shade_flat()
fb_obj.data.materials.append(mat_frame)
move_to_collection(fb_obj, COLL)
if fb_obj.name in bpy.context.scene.collection.objects:
    bpy.context.scene.collection.objects.unlink(fb_obj)

# ============================================================
# 5. MATTRESS
# ============================================================
# Centre Y: mattress spans from just inside footboard to just inside headboard
M_CY = (-BED_L / 2 + FB_T + 0.005 + BED_L / 2 - HB_T - 0.005) / 2  # ≈ 0
make_box("mattress", 0, M_CY, M_CZ, M_W, M_L, M_H, mat_mattress, COLL)

# ============================================================
# 6. BLANKET / DUVET — lower 2/3 of mattress, slightly draped
# ============================================================
make_box("blanket", 0, BLK_CY, BLK_CZ, BLK_W, BLK_L, BLK_H, mat_blanket, COLL)

# ============================================================
# 7. PILLOWS — linked duplicates, two side by side near headboard
# ============================================================
bpy.ops.mesh.primitive_cube_add(size=1, location=(-PIL_XO, PIL_Y, PIL_Z))
pil_base = bpy.context.active_object
pil_base.name = "pillow_L"
pil_base.scale = (PIL_W, PIL_L, PIL_H)
apply_and_finish(pil_base, mat_pillow, COLL)

# Right pillow as a linked duplicate
bpy.ops.object.select_all(action='DESELECT')
pil_base.select_set(True)
bpy.context.view_layer.objects.active = pil_base
bpy.ops.object.duplicate(linked=True)
pil_r = bpy.context.active_object
pil_r.name = "pillow_R"
pil_r.location = (PIL_XO, PIL_Y, PIL_Z)
move_to_collection(pil_r, COLL)

# ============================================================
# DONE — deselect all for a clean state
# ============================================================
bpy.ops.object.select_all(action='DESELECT')
print("Bed created successfully.")
