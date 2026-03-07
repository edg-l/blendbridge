import bpy
import bmesh
import math

bpy.ops.object.select_all(action='DESELECT')

# Cleanup previous
if "FF_Sword" in bpy.data.objects:
    bpy.data.objects.remove(bpy.data.objects["FF_Sword"], do_unlink=True)
for m in list(bpy.data.meshes):
    if m.users == 0: bpy.data.meshes.remove(m)
for m in list(bpy.data.materials):
    if m.users == 0: bpy.data.materials.remove(m)

mesh = bpy.data.meshes.new("FF_Sword")
obj = bpy.data.objects.new("FF_Sword", mesh)
bpy.context.scene.collection.objects.link(obj)
bpy.context.view_layer.objects.active = obj
obj.select_set(True)
bm = bmesh.new()

# ── Materials ──
def make_mat(name, color, metallic=0.0, roughness=0.5):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Roughness"].default_value = roughness
    return m

mat_steel   = make_mat("steel_blade",   (0.75, 0.78, 0.82), 0.9, 0.25)
mat_gold    = make_mat("gold_guard",    (0.83, 0.65, 0.15), 0.95, 0.3)
mat_grip    = make_mat("leather_grip",  (0.15, 0.08, 0.05), 0.0, 0.85)
mat_crystal = make_mat("blue_crystal",  (0.1, 0.3, 0.9),   0.1, 0.15)

mesh.materials.append(mat_steel)   # 0
mesh.materials.append(mat_gold)    # 1
mesh.materials.append(mat_grip)    # 2
mesh.materials.append(mat_crystal) # 3

# ── Helpers ──
def prof12(w, rx, groove=0.0, eb=0.001):
    """12-vert profile: hex with fuller groove + edge bevels for lighting."""
    gw = w * 0.12
    gx = (rx - groove) if groove > 0 else rx
    return [
        ( eb,  -w),           # 0  L edge upper
        ( rx,  -w * 0.45),    # 1  upper-left
        ( gx,  -gw),          # 2  groove UL
        ( gx,   gw),          # 3  groove UR
        ( rx,   w * 0.45),    # 4  upper-right
        ( eb,   w),           # 5  R edge upper
        (-eb,   w),           # 6  R edge lower
        (-rx,   w * 0.45),    # 7  lower-right
        (-gx,   gw),          # 8  groove LR
        (-gx,  -gw),          # 9  groove LL
        (-rx,  -w * 0.45),    # 10 lower-left
        (-eb,  -w),           # 11 L edge lower
    ]

def hex6(w, rx):
    return [(0,-w),(rx,-w*0.45),(rx,w*0.45),(0,w),(-rx,w*0.45),(-rx,-w*0.45)]

def mk(z, profile):
    return [bm.verts.new((x, y, z)) for x, y in profile]

def bridge(a, b, mat=0):
    n = len(a)
    for i in range(n):
        j = (i + 1) % n
        f = bm.faces.new([a[i], a[j], b[j], b[i]])
        f.material_index = mat

def fan(r, pt, mat=0, rev=False):
    v = list(reversed(r)) if rev else r
    for i in range(len(v)):
        f = bm.faces.new([v[i], v[(i+1) % len(v)], pt])
        f.material_index = mat

def cap(r, mat=0, flip=False):
    bm.faces.new(list(reversed(r)) if flip else r).material_index = mat

# ══════════════════════════════════════════════════════
# PROPORTIONS — blade ~79%, handle+pommel ~21%
#   Pommel crystal:  -0.18 to -0.02  (independent)
#   Gold pommel cap: -0.02 to  0.04  (chain start)
#   Handle:           0.04 to  0.40
#   Guard ring:       0.40 to  0.44
#   Guard center:     0.44 to  0.58
#   Collar/ricasso:   0.58 to  0.72
#   Blade:            0.72 to  3.55
# ══════════════════════════════════════════════════════

# ── Pommel crystal (independent, aligned to blade axis) ──
pom_r = 0.050
pom_cz = -0.14   # equator lower so top is inside the gold cap
pom_top = bm.verts.new((0, 0, -0.04))   # top sits inside gold setting
pom_bot = bm.verts.new((0, 0, -0.24))
pom_vs = []
for i in range(6):
    a = i * math.pi / 3 + math.pi / 6  # rotated so facets align with blade
    pom_vs.append(bm.verts.new((pom_r * math.cos(a), pom_r * math.sin(a), pom_cz)))
for i in range(6):
    j = (i + 1) % 6
    bm.faces.new([pom_vs[i], pom_vs[j], pom_top]).material_index = 3
    bm.faces.new([pom_vs[j], pom_vs[i], pom_bot]).material_index = 3

# ── Gold pommel cap / crystal setting ──
hr = 0.038  # 15-20% thicker handle
pcap = [
    mk(-0.08, prof12(0.058, 0.054)),   # wraps around crystal upper half
    mk(-0.04, prof12(0.060, 0.056)),   # widest — cradles crystal top
    mk(-0.01, prof12(0.052, 0.046)),   # taper above crystal
    mk( 0.02, prof12(0.044, 0.040)),   # narrowing to handle
    mk( 0.04, prof12(hr, hr)),          # match handle
]
cap(pcap[0], mat=1, flip=True)
for i in range(len(pcap) - 1):
    bridge(pcap[i], pcap[i + 1], mat=1)

# ── Handle (5 segments, thicker, cleaner) ──
handle = [
    (0.04,  1.00),
    (0.10,  1.22),   # band 1 peak
    (0.16,  0.88),   # valley
    (0.22,  1.22),   # band 2 peak
    (0.28,  0.88),   # valley
    (0.34,  1.22),   # band 3 peak
    (0.40,  1.00),   # end
]
h_rings = [mk(z, prof12(hr * m, hr * m)) for z, m in handle]
bridge(pcap[-1], h_rings[0], mat=2)
for i in range(len(h_rings) - 1):
    bridge(h_rings[i], h_rings[i + 1], mat=2)

# ── Guard ring (decorative band above handle) ──
gr = [
    mk(0.42, prof12(0.056, 0.050)),   # flare out
    mk(0.44, prof12(0.050, 0.044)),   # narrow back to guard
]
bridge(h_rings[-1], gr[0], mat=1)
bridge(gr[0], gr[1], mat=1)

# ── Guard center (12-vert, gold) ──
guard = [
    mk(0.46, prof12(0.065, 0.056)),
    mk(0.49, prof12(0.078, 0.068)),
    mk(0.51, prof12(0.084, 0.074)),   # widest
    mk(0.53, prof12(0.078, 0.068)),
    mk(0.56, prof12(0.065, 0.056)),
    mk(0.58, prof12(0.055, 0.048)),   # top
]
bridge(gr[-1], guard[0], mat=1)
for i in range(len(guard) - 1):
    bridge(guard[i], guard[i + 1], mat=1)

# ── Collar / ricasso (flares from guard width → blade width) ──
collar = [
    mk(0.60, prof12(0.070, 0.055)),
    mk(0.63, prof12(0.092, 0.054)),
    mk(0.66, prof12(0.112, 0.052)),
    mk(0.69, prof12(0.125, 0.050, 0.003)),
    mk(0.72, prof12(0.130, 0.048, 0.005)),   # matches blade base
]
bridge(guard[-1], collar[0], mat=1)
for i in range(len(collar) - 1):
    m = 1 if i < 3 else 0
    bridge(collar[i], collar[i + 1], m)

# ── Blade (belly curve, fuller stops at ~65%, supporting edge bevels) ──
# Blade length: 0.72 → 3.55 = 2.83 units
# Fuller stops at 65%: 0.72 + 2.83*0.65 ≈ 2.56
blade_specs = [
    # (z,     w,     rx,    groove, edge_bevel)
    (0.80,  0.136, 0.050, 0.008,  0.003),   # base, widening
    (0.95,  0.144, 0.052, 0.012,  0.004),   # building belly
    (1.15,  0.152, 0.052, 0.015,  0.005),   # belly approaching peak
    (1.40,  0.158, 0.050, 0.016,  0.005),   # belly peak (widest!)
    (1.65,  0.152, 0.048, 0.016,  0.005),   # still wide
    (1.90,  0.138, 0.046, 0.014,  0.004),   # narrowing
    (2.12,  0.118, 0.042, 0.011,  0.004),
    (2.32,  0.096, 0.036, 0.007,  0.003),
    (2.50,  0.074, 0.030, 0.003,  0.003),   # fuller fading
    (2.60,  0.060, 0.026, 0.000,  0.003),   # fuller ends (~66%)
    (2.78,  0.042, 0.020, 0.000,  0.002),
    (2.95,  0.026, 0.014, 0.000,  0.002),
    (3.10,  0.014, 0.008, 0.000,  0.001),   # last ring — decisive taper
]
b_rings = [mk(z, prof12(w, rx, gd, eb)) for z, w, rx, gd, eb in blade_specs]
bridge(collar[-1], b_rings[0], mat=0)
for i in range(len(b_rings) - 1):
    bridge(b_rings[i], b_rings[i + 1], mat=0)

# Blade tip — clean point, not drawn out
blade_tip = bm.verts.new((0, 0, 3.22))
fan(b_rings[-1], blade_tip, mat=0, rev=True)

# ── Guard wings (bases penetrate into guard body for seamless look) ──
guard_cz = 0.51   # guard center Z
wing_data = [
    # (y_off, x_half, z_half, z_sweep)
    (0.03,  0.068, 0.068, 0.000),   # inside guard body (no cap needed)
    (0.08,  0.058, 0.058, 0.000),   # at guard edge — transition
    (0.17,  0.050, 0.062, 0.012),
    (0.26,  0.044, 0.066, 0.042),
    (0.36,  0.036, 0.058, 0.095),
    (0.46,  0.028, 0.048, 0.165),
    (0.54,  0.022, 0.038, 0.245),
    (0.60,  0.016, 0.028, 0.320),
    (0.64,  0.012, 0.020, 0.380),   # thicker tip
]

for side in [1, -1]:
    w_rings = []
    for y_off, xh, zh, z_sw in wing_data:
        cz = guard_cz + z_sw
        cy = side * y_off
        w_rings.append([
            bm.verts.new((0, cy, cz + zh)),    # top
            bm.verts.new((xh, cy, cz)),         # front
            bm.verts.new((0, cy, cz - zh)),     # bottom
            bm.verts.new((-xh, cy, cz)),        # back
        ])
    for i in range(len(w_rings) - 1):
        if side == 1:
            bridge(w_rings[i], w_rings[i + 1], mat=1)
        else:
            bridge(w_rings[i + 1], w_rings[i], mat=1)
    # Wing tip
    tip_v = bm.verts.new((0, side * 0.68, guard_cz + 0.43))
    if side == 1:
        fan(w_rings[-1], tip_v, mat=1, rev=True)
    else:
        fan(w_rings[-1], tip_v, mat=1)
    # No base cap — the base is inside the guard body

# ── Guard gem (hex pyramid, base hidden inside guard body) ──
gem_r = 0.024
gem_cz = guard_cz
guard_face_x = 0.070

for sign in [1, -1]:
    # Base ring sits inside guard body — hidden by guard geometry
    base_x = sign * (guard_face_x - 0.008)
    tip_x = sign * (guard_face_x + 0.032)
    g_ring = []
    for i in range(6):
        a = i * math.pi / 3
        g_ring.append(bm.verts.new((
            base_x,
            gem_r * math.sin(a),
            gem_cz + gem_r * math.cos(a)
        )))
    g_tip = bm.verts.new((tip_x, 0, gem_cz))
    if sign == 1:
        for i in range(6):
            bm.faces.new([g_ring[i], g_ring[(i+1) % 6], g_tip]).material_index = 3
    else:
        for i in range(6):
            bm.faces.new([g_ring[(i+1) % 6], g_ring[i], g_tip]).material_index = 3

# ── Finalize ──
bm.to_mesh(mesh)
bm.free()

bpy.ops.object.shade_flat()
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.mesh.normals_make_consistent(inside=False)
bpy.ops.object.mode_set(mode='OBJECT')

bpy.context.scene.cursor.location = (0, 0, 0)
bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

tri_count = sum(len(f.vertices) - 2 for f in mesh.polygons)
print(f"FF Sword: {len(mesh.vertices)} verts, {len(mesh.polygons)} polys, ~{tri_count} tris")
