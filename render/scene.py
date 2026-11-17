import os
import bpy, bmesh, math, random, sys
from mathutils import Vector, Euler, Matrix

S = os.environ.get("LEDSTAR_WORK", os.path.dirname(os.path.abspath(__file__)))
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
RESX = int(argv[0]) if argv else 640
SAMPLES = int(argv[1]) if len(argv) > 1 else 32
OUT = argv[2] if len(argv) > 2 else S + "/test.png"
random.seed(7)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'
cy = sc.cycles
cy.samples = SAMPLES
cy.use_denoising = os.environ.get("DENOISE", "1") == "1"
CAM = os.environ.get("CAM", "front")
DEVICE = os.environ.get("DEVICE", "CPU")  # HIP (AMD), OPTIX/CUDA (NVIDIA), CPU
if DEVICE != "CPU":
    cy.device = 'GPU'
    _p = bpy.context.preferences.addons['cycles'].preferences
    _p.compute_device_type = DEVICE
    _p.get_devices()
    for _d in _p.devices:
        _d.use = _d.type != 'CPU' and (DEVICE != 'HIP' or 'RX' in _d.name or 'Radeon RX' in _d.name)
    print("DEVICES", [(d.name, d.type, d.use) for d in _p.devices])
try:
    cy.denoiser = 'OPENIMAGEDENOISE'
except TypeError:
    cy.denoiser = 'OPTIX' if DEVICE == 'OPTIX' else 'OPENIMAGEDENOISE'
cy.max_bounces = 8
cy.caustics_reflective = False
cy.caustics_refractive = False
cy.sample_clamp_indirect = 3
cy.sample_clamp_direct = 30
cy.use_adaptive_sampling = True
cy.time_limit = int(os.environ.get('TLIM', '900'))
cy.adaptive_threshold = 0.02
sc.render.resolution_x = RESX
sc.render.resolution_y = int(RESX * 2 / 3)
sc.render.resolution_percentage = 100
sc.view_settings.view_transform = 'Filmic'
sc.view_settings.look = 'Medium High Contrast'
sc.view_settings.exposure = 0.0
sc.cycles_curves.shape = 'THICK'
sc.cycles_curves.subdivisions = 2


# ------------------------------------------------------------ materials
def mat(name, color, rough=0.5, metal=0.0, emit=None, strength=0.0, **kw):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = strength
    for k, v in kw.items():
        b.inputs[k.replace("_", " ")].default_value = v
    return m


# ------------------------------------------------------------ import board
bpy.ops.import_scene.gltf(filepath=S + "/board.glb")
root = bpy.data.objects["Node_0"]
board_meshes = [o for o in bpy.data.objects if o.type == 'MESH']
leds = {o.name: o for o in bpy.data.objects if o.type == 'EMPTY' and o.name.startswith('D')}
import os
LEDSET = os.environ.get("LEDSET", "yw")
GROUPS = {"W": ["D1", "D5", "D9", "D13", "D17"], "Y": ["D21", "D22", "D23", "D24", "D25"],
          "B": ["D4", "D8", "D12", "D16", "D20"], "R": ["D2", "D6", "D10", "D14", "D18"],
          "G": ["D3", "D7", "D11", "D15", "D19"]}
COLS = {"W": (1.0, 0.93, 0.80), "Y": (1.0, 0.62, 0.05), "B": (0.03, 0.20, 1.0), "R": (1.0, 0.07, 0.04), "G": (0.10, 1.0, 0.25)}
GAIN = {"W": 1.0, "Y": 1.0, "B": 1.0, "R": 1.0, "G": 0.9}
SETS = {"yw": "YW", "bw": "BW", "rg": "RG"}
led_col, led_gain = {}, {}
for g in SETS[LEDSET]:
    for n in GROUPS[g]:
        led_col[n] = COLS[g]; led_gain[n] = GAIN[g]
glow_leds = list(led_col)

# orient: back of the PCB faces the camera (-Y), hang hole at top (+Z)
root.rotation_mode = 'XYZ'
root.rotation_euler = Euler((math.radians(90), 0, math.radians(180)), 'XYZ')
bpy.context.view_layer.update()


def bbox(objs):
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    return Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))), \
           Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))


lo, hi = bbox(board_meshes)
ctr = (lo + hi) / 2
root.location = -ctr  # board centred on origin
bpy.context.view_layer.update()
lo, hi = bbox(board_meshes)
print("BOARD bbox mm", [round(v * 1000, 1) for v in lo], [round(v * 1000, 1) for v in hi])

# tweak PCB materials
for m in bpy.data.materials:
    if not m.use_nodes:
        continue
    b = m.node_tree.nodes.get("Principled BSDF")
    if not b:
        continue
    r = b.inputs["Roughness"].default_value
    if m.name in ("mat_17", "mat_18"):  # soldermask (front/back): glossy white LPI mask, like a white JLCPCB board
        b.inputs["Base Color"].default_value = (0.90, 0.90, 0.88, 1.0)
        b.inputs["Alpha"].default_value = 1.0
        b.inputs["Roughness"].default_value = 0.28
        b.inputs["Specular IOR Level"].default_value = 0.5
        b.inputs["Coat Weight"].default_value = 0.6
        b.inputs["Coat Roughness"].default_value = 0.06
        b.inputs["Coat IOR"].default_value = 1.5
        b.inputs["Subsurface Weight"].default_value = 0.08
        b.inputs["Subsurface Scale"].default_value = 0.0004
        m.blend_method = 'OPAQUE' if hasattr(m, "blend_method") else None
    if m.name in ("mat_15", "mat_16"):  # silkscreen: matte black ink on top of the mask
        b.inputs["Base Color"].default_value = (0.025, 0.025, 0.025, 1.0)
        b.inputs["Roughness"].default_value = 0.65
    if m.name in ("mat_19",):          # FR4 core, visible at the board edges: pale cream glass-fibre
        b.inputs["Base Color"].default_value = (0.78, 0.74, 0.60, 1.0)
        b.inputs["Roughness"].default_value = 0.6
    if m.name in ("mat_13", "mat_14"):  # copper/gold
        b.inputs["Metallic"].default_value = 1.0

# LEDs: dark housings only — we replace the glow with our own emitters
back_y = lo.y  # camera-facing PCB surface (min Y)
thick = hi.y - lo.y
print("thickness mm", thick * 1000)


# --- per-LED materials: glowing white/yellow, others dark unlit lenses
lens_slots = {"mat_0", "mat_1", "mat_4", "mat_5"}
def led_mesh_of(name):
    return [o for o in bpy.data.objects if o.type == 'MESH' and o.parent and o.parent.name == name]
for name, e in leds.items():
    for o in led_mesh_of(name):
        o.data = o.data.copy()
        for i, m in enumerate(o.data.materials):
            if m is None or m.name.split(".")[0] not in lens_slots:
                continue
            if name in glow_leds:
                c = led_col[name]
                o.data.materials[i] = mat("lens_" + name, c, emit=c, strength=60.0 * led_gain[name])
            else:
                o.data.materials[i] = mat("dead_" + name, (0.015, 0.015, 0.02), rough=0.25, Coat_Weight=0.5)

def adopt(o):
    o.parent = root
    o.matrix_parent_inverse = root.matrix_world.inverted()

def halo_mat(name, col, strength):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Location"].default_value = (-0.5, -0.5, 0)
    mp.inputs["Scale"].default_value = (2, 2, 2)
    gr = nt.nodes.new("ShaderNodeTexGradient")
    gr.gradient_type = 'SPHERICAL'
    cr = nt.nodes.new("ShaderNodeMath"); cr.operation = 'POWER'; cr.inputs[1].default_value = 2.2
    em = nt.nodes.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (*col, 1); em.inputs["Strength"].default_value = strength
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mx = nt.nodes.new("ShaderNodeMixShader")
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(tc.outputs["Generated"], mp.inputs[0])
    nt.links.new(mp.outputs[0], gr.inputs[0])
    nt.links.new(gr.outputs["Fac"], cr.inputs[0])
    nt.links.new(cr.outputs[0], mx.inputs[0])
    nt.links.new(tr.outputs[0], mx.inputs[1])
    nt.links.new(em.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs[0])
    return m

for n in glow_leds:
    e = leds[n]
    p = e.matrix_world.translation.copy()
    col = led_col[n]
    gain = led_gain[n]
    # emissive window disc just inside the hole, facing -Y
    bpy.ops.mesh.primitive_circle_add(vertices=24, radius=0.0006, fill_type='NGON',
                                      location=(p.x, back_y + 0.0004, p.z), rotation=(math.radians(90), 0, 0))
    d = bpy.context.object
    d.name = "glow_" + n
    d.data.materials.append(mat("emit_" + n, col, emit=col, strength=1600.0 * gain))
    adopt(d)
    # frosted diffuser film over the window: wider, softer glowing disc proud of the surface
    bpy.ops.mesh.primitive_circle_add(vertices=32, radius=0.0011, fill_type='NGON',
                                      location=(p.x, back_y - 0.00006, p.z), rotation=(math.radians(90), 0, 0))
    f = bpy.context.object
    f.name = "diff_" + n
    f.data.materials.append(mat("diff_" + n, col, emit=col, strength=420.0 * gain))
    f.visible_shadow = False
    adopt(f)
    # large soft halo sprite on the back surface (artistic: stronger than the real LED would give)
    bpy.ops.mesh.primitive_plane_add(size=0.020, location=(p.x, back_y - 0.0003, p.z), rotation=(math.radians(90), 0, 0))
    h = bpy.context.object
    h.name = "halo_" + n
    h.data.materials.append(halo_mat("halo_" + n, col, 14.0 * gain))
    h.visible_shadow = False
    h.visible_diffuse = False
    h.visible_glossy = False
    adopt(h)
    bpy.ops.object.light_add(type='POINT', location=(p.x, back_y - 0.0012, p.z))
    L = bpy.context.object
    L.name = "led_light_" + n
    L.data.color = col
    L.data.energy = 0.0018 * gain
    L.data.shadow_soft_size = 0.0008
    adopt(L)

# ------------------------------------------------------------ hanging thread
hole = None
top = Vector((0, 0, 0))
# top arm hang hole: top-most LED position x, higher z
thread_top = Vector((0.0, back_y - 0.002, 0.30))
# find hang hole x ~ x of top-arm LEDs (D17..?) -> use arm LED with highest z
arm = leds['D2']
hole_pos = Vector((arm.matrix_world.translation.x + 0.0001, back_y + 0.0008, arm.matrix_world.translation.z + 0.003734))
print("arm top LED", arm.name, arm.matrix_world.translation, "hole est", hole_pos)


# tilt board a bit so it reads as hanging in the air
root_parent = bpy.data.objects.new("pivot", None)
bpy.context.collection.objects.link(root_parent)
root.parent = root_parent


import numpy as np
# ------------------------------------------------------------ room
bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, -1.0))
bpy.context.object.data.materials.append(mat("floor", (0.07, 0.04, 0.025), rough=0.4))
bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 4.0, 10), rotation=(math.radians(90), 0, 0))
bpy.context.object.data.materials.append(mat("wall", (0.09, 0.055, 0.04), rough=0.9))
bpy.ops.mesh.primitive_plane_add(size=40, location=(-7, 0, 10), rotation=(0, math.radians(90), 0))
bpy.context.object.data.materials.append(mat("wall2", (0.09, 0.055, 0.04), rough=0.9))

# ------------------------------------------------------------ real Poly Haven fir sapling (CC0) -> dense tree
with bpy.data.libraries.load(S + "/dl_tree/fir_sapling/fir_sapling_2k.blend", link=False) as (a, b):
    b.objects = a.objects
base = {}
for o in b.objects:
    base[o.name[-1]] = o.data   # a, b, c meshes
    bpy.data.objects.remove(o)
for m in bpy.data.materials:
    if m.name.startswith("fir_sapling_twigs"):
        nt = m.node_tree
        for n in nt.nodes:
            if n.type == 'BSDF_PRINCIPLED':
                n.inputs["Roughness"].default_value = 0.85
                n.inputs["Specular IOR Level"].default_value = 0.1
                n.inputs["Subsurface Weight"].default_value = 0.0
tree_objs = []
def place(kind, x, y, sc_, rz):
    o = bpy.data.objects.new("fir_" + kind, base[kind])
    bpy.context.collection.objects.link(o)
    o.location = (x, y, 0)
    o.scale = (sc_, sc_, sc_)
    o.rotation_euler = (math.radians(random.uniform(-4, 4)), math.radians(random.uniform(-4, 4)), rz)
    tree_objs.append(o)
place('a', 0, 0, 1.55, 0.3)
place('a', 0.05, 0.05, 1.25, 2.0)
for i in range(7):
    ang = 2 * math.pi * i / 7 + random.uniform(-.2, .2)
    place(random.choice('ab'), 0.27 * math.cos(ang), 0.27 * math.sin(ang), random.uniform(1.15, 1.4), random.uniform(0, 6.28))
for i in range(11):
    ang = 2 * math.pi * i / 11 + random.uniform(-.2, .2)
    place(random.choice('abc'), 0.52 * math.cos(ang), 0.52 * math.sin(ang), random.uniform(0.95, 1.2), random.uniform(0, 6.28))
for i in range(12):
    ang = 2 * math.pi * i / 12 + random.uniform(-.2, .2)
    place(random.choice('bc'), 0.78 * math.cos(ang), 0.78 * math.sin(ang), random.uniform(0.7, 0.95), random.uniform(0, 6.28))
bpy.context.view_layer.update()

# vertex cache (world, tree-local origin at (0,0,0))
vcache = {}
for k, me in base.items():
    arr = np.empty(len(me.vertices) * 3, dtype=np.float32)
    me.vertices.foreach_get("co", arr)
    vcache[k] = arr.reshape(-1, 3)
allv = []
for o in tree_objs:
    k = o.name[4]
    M = np.array(o.matrix_world)
    v = vcache[k]
    w = v @ M[:3, :3].T + M[:3, 3]
    allv.append(w[::7])
allv = np.concatenate(allv)
print("TREE verts", allv.shape, allv.min(0), allv.max(0))

# anchor: front-most branch tip between 1.0 and 1.5 m height near centre column
sel = allv[(allv[:, 2] > 0.95) & (allv[:, 2] < 1.5) & (abs(allv[:, 0]) < 0.35)]
anchor_local = sel[np.argmin(sel[:, 1])]
anchor_local = Vector(anchor_local.tolist())
print("anchor local", anchor_local)

bpy.context.view_layer.update()
hole_w = hole_pos.copy()   # board is still untilted here
anchor_w = hole_w + Vector((0.004, 0.010, 0.040))
shift = anchor_w - anchor_local
for o in tree_objs:
    o.location += shift
allv = allv + np.array(shift)
bpy.context.view_layer.update()
# hang point: the ORIGINAL spot (dense foliage straight above the hole), rope over a real woody stem found there
hxh, hyh, hzh = hole_pos.x, hole_pos.y, hole_pos.z
cl = allv[(allv[:, 2] > hzh + 0.030) & (allv[:, 2] < hzh + 0.080) & (np.abs(allv[:, 0] - hxh) < 0.06)]
bestB, bcost = None, 1e9
for c in cl[::max(1, len(cl) // 400)]:
    if int((np.linalg.norm(allv - c, axis=1) < 0.015).sum()) < 6:
        continue
    cost = abs(c[0] - hxh) + abs(c[1] - hyh)
    if cost < bcost:
        bcost, bestB = cost, c
if bestB is None:
    bestB = np.array(anchor_w)
shift_old = np.array([hxh - bestB[0], hyh - bestB[1], 0.0])
for o in tree_objs:
    o.location += Vector(shift_old.tolist())
allv = allv + shift_old
bpy.context.view_layer.update()
print("original placement, shift mm", (shift_old * 1000).round(1))
# woody stems: thick limbs ('branches' material) and the twig stems inside the needle mesh (large islands of the twigs material)
def islands(me, mat_idx, min_n):
    par = {}
    def fnd(x):
        while par.setdefault(x, x) != x:
            par[x] = par[par[x]]; x = par[x]
        return x
    for pg in me.polygons:
        if pg.material_index != mat_idx: continue
        vs_ = list(pg.vertices)
        r0 = fnd(vs_[0])
        for v_ in vs_[1:]:
            r1 = fnd(v_)
            if r1 != r0: par[r1] = r0
    comps_ = {}
    for v_ in list(par): comps_.setdefault(fnd(v_), []).append(v_)
    return [np.array(c_) for c_ in comps_.values() if len(c_) >= min_n]
limb_comp, twig_comp = {}, {}
for k, me in base.items():
    limb_comp[k] = islands(me, 0, 15)
    twig_comp[k] = [c_ for c_ in islands(me, 1, 40)]
    print("stems in", k, "limbs", len(limb_comp[k]), "twig stems", len(twig_comp[k]))
Cands = []
for o in tree_objs:
    k = o.name[4]
    Mw = np.array(o.matrix_world)
    for kind_, comps_ in (("limb", limb_comp[k]), ("twig", twig_comp[k])):
        for vs_ in comps_:
            p = vcache[k][vs_] @ Mw[:3, :3].T + Mw[:3, 3]
            c = p.mean(0)
            if abs(c[0] - hxh) > 0.35 or abs(c[1] - hyh) > 0.35 or abs(c[2] - hzh) > 0.35: continue
            ax0 = np.linalg.svd(p - c, full_matrices=False)[2][0]
            t = (p - c) @ ax0
            if t.max() - t.min() < 0.06: continue
            for t0 in np.linspace(t.min() + 0.02, t.max() - 0.02, 12):
                m_ = np.abs(t - t0) < 0.02
                if m_.sum() < 8: continue
                pl = p[m_]; cl_ = pl.mean(0)
                ax = np.linalg.svd(pl - cl_, full_matrices=False)[2][0]
                if abs(ax[2]) > 0.35 or abs(ax[0]) < 0.55: continue
                tl = (pl - cl_) @ ax
                rr_ = np.linalg.norm((pl - cl_) - np.outer(tl, ax), axis=1)
                Rl = float(np.percentile(rr_, 90))
                if Rl < 0.0012 or Rl > 0.0065: continue
                Cands.append((o, vs_, ax, cl_, Rl, kind_))
print("stem candidates near the spot", len(Cands))
Ssamp = allv[::3]
bestC, bestS = None, 1e18
for win in (0.03, 0.05, 0.08, 0.12):
    for cd in Cands:
        o_, vs_, ax, P0, Rl, kind_ = cd
        zlo, zhi = hzh + 0.020 + Rl, hzh + 0.055 + Rl
        sh_ = np.array([hxh - P0[0], hyh - P0[1], min(max(P0[2], zlo), zhi) - P0[2]])
        if np.linalg.norm(sh_) > win: continue
        q = Ssamp + sh_
        inx = np.abs(q[:, 0] - hxh) < 0.048
        inz = (q[:, 2] > hzh - 0.085) & (q[:, 2] < hzh + 0.008)
        occl = int((inx & inz & (q[:, 1] < lo.y - 0.001) & (q[:, 1] > lo.y - 0.30)).sum())
        inb = int((inx & inz & (q[:, 1] >= lo.y - 0.001) & (q[:, 1] < hi.y + 0.003)).sum())
        sc_ = 3 * occl + 6 * inb + 3000 * float(np.linalg.norm(sh_)) + 800 * abs(ax[2])
        if sc_ < bestS: bestS, bestC = sc_, (cd, sh_, occl, inb)
    if bestC is not None:
        print("stem search radius m", win, "score", round(bestS))
        break
(limb_obj, limb_vs, limb_ax, limb_P, limb_R, limb_kind), shift2, _oc, _ib = bestC
print("STEM chosen:", limb_kind, "on", limb_obj.name, "R mm %.1f" % (limb_R * 1000), "axis", limb_ax.round(2), "needle pts in front", _oc, "in board", _ib, "extra shift mm", (shift2 * 1000).round(1))
for o in tree_objs:
    o.location += Vector(shift2.tolist())
allv = allv + shift2
bpy.context.view_layer.update()
BR = Vector((limb_P + shift2).tolist())
LIMB_AX = Vector(limb_ax.tolist())
print("hang stem centre", BR)

# hide near-vertical bare trunks (they give away that the tree is several separate saplings); needles cover them in a real tree
import bmesh
for k, me in base.items():
    kill = set()
    for vs_ in limb_comp[k]:
        p_ = vcache[k][vs_]
        if limb_kind == 'limb' and k == limb_obj.name[4] and len(vs_) == len(limb_vs) and (vs_ == limb_vs).all(): continue
        if abs(np.linalg.svd(p_ - p_.mean(0), full_matrices=False)[2][0][2]) > 0.55:
            kill.update(int(v_) for v_ in vs_)
    bm_ = bmesh.new(); bm_.from_mesh(me)
    bm_.verts.ensure_lookup_table()
    fd_ = [f for f in bm_.faces if f.material_index == 0 and f.verts[0].index in kill]
    bmesh.ops.delete(bm_, geom=fd_, context='FACES_ONLY')
    bm_.to_mesh(me); bm_.free()
    print("hid", len(fd_), "trunk faces in", k)
floor_z = -1.0
# floor under the tree
for o in bpy.data.objects:
    if o.name.startswith("Plane") and abs(o.location.z + 1.0) < 1e-6:
        o.location.z = float(allv[:, 2].min()) - 0.02

# ------------------------------------------------------------ fairy lights on branch tips + baubles
bulb_cols = [(1.0, 0.72, 0.34), (1.0, 0.82, 0.55), (1.0, 0.2, 0.08), (1.0, 0.58, 0.14)]
bm = [mat("bulb%d" % i, c, emit=c, strength=150.0) for i, c in enumerate(bulb_cols)]
bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=10, radius=0.0065)
proto = bpy.context.object
proto.name = "bulb_proto"
pts = allv
board_c = Vector((0, 0, 0))
cands = pts[(pts[:, 1] > anchor_w.y + 0.03) & (pts[:, 1] < anchor_w.y + 0.65)]
# keep ones around the outside of the foliage
rng = np.random.default_rng(3)
idx = rng.permutation(len(cands))
placed = []
for i in idx:
    p = cands[i]
    pv = Vector(p.tolist())
    if (pv - board_c).length < 0.075:   # not on top of the snowflake
        continue
    if any((pv - q).length < 0.085 for q in placed):
        continue
    placed.append(pv)
    if len(placed) >= 85:
        break
for j, pv in enumerate(placed):
    o = proto.copy()
    o.data = proto.data
    o.location = pv
    o.data.materials.clear()
    o.data.materials.append(bm[j % 4 if j % 5 else 0])
    bpy.context.collection.objects.link(o)
    # little socket
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.0032, depth=0.01, location=pv + Vector((0, 0.002, 0.008)))
    bpy.context.object.data.materials.append(mat("socket", (0.01, 0.03, 0.01), rough=0.6))
bpy.data.objects.remove(proto)
# real light sources hidden in the tree
for pv in placed[::5]:
    bpy.ops.object.light_add(type='POINT', location=pv + Vector((0, 0.01, 0)))
    L = bpy.context.object
    L.data.color = (1.0, 0.65, 0.3)
    L.data.energy = 0.25
    L.data.shadow_soft_size = 0.01

# baubles hung from tips, left/right of the snowflake
bcol = [((0.55, 0.01, 0.02), 0.08, 0.1), ((0.85, 0.62, 0.15), 0.12, 1.0), ((0.6, 0.02, 0.03), 0.06, 0.2)]
bsel = cands[(abs(cands[:, 0]) > 0.07) & (abs(cands[:, 0]) < 0.115) & (cands[:, 1] < anchor_w.y + 0.25) & (cands[:, 2] > -0.07) & (cands[:, 2] < 0.07)]
bplaced = []
for i in rng.permutation(len(bsel)):
    p = Vector(bsel[i].tolist())
    if any((p - q).length < 0.09 for q in bplaced):
        continue
    # skip spots where the ball would poke into foliage below the hook point
    _c = np.array([p.x, p.y, p.z - 0.024])
    if ((np.linalg.norm(pts - _c, axis=1) < 0.031) & (np.linalg.norm(pts - np.array([p.x, p.y, p.z]), axis=1) > 0.008)).any():
        continue
    bplaced.append(p)
    if len(bplaced) >= 3:
        break

for j, p in enumerate(bplaced):
    c, r, m_ = bcol[j % 3]
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=32, radius=0.021, location=p + Vector((0, 0, -0.024)))
    bpy.ops.object.shade_smooth()
    ob = bpy.context.object
    ob.data.materials.append(mat("bauble", c, rough=r, metal=m_ if m_ > 0.5 else 0.0, Coat_Weight=1.0 if m_ < 0.5 else 0.0))
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.0075, depth=0.006, location=p + Vector((0, 0, -0.0015)))
    bpy.context.object.data.materials.append(mat("cap", (0.8, 0.65, 0.25), rough=0.3, metal=1.0))

# ------------------------------------------------------------ hanging: plumb string hooked over a real branch
hx, hy, hz = hole_pos.x, hole_pos.y, hole_pos.z
_cm = np.mean([np.array((o.matrix_world @ v.co)[:]) for o in board_meshes for v in o.data.vertices], axis=0)
print("GRAVITY check: board centre minus hole (mm)", [round(float(d) * 1000, 2) for d in (_cm - np.array([hx, hy, hz]))])
bpy.context.view_layer.update()
M = root_parent.matrix_world
Minv = M.inverted()
def W(x, y, z):   # pre-tilt board coordinates -> world
    return M @ Vector((x, y, z))
holeW = W(hx, hy, hz)
boardC = W(0.0, 0.0, 0.0)
tipz = -1e9                       # top of the board at the hang hole
for o in board_meshes:
    Mo = o.matrix_world
    for v in o.data.vertices:
        p = Minv @ (Mo @ v.co)
        if abs(p.x - hx) < 0.0015 and abs(p.y - hy) < 0.0030 and p.z > tipz:
            tipz = p.z
print("hole z", hz, "tip z", tipz, "mm above hole", (tipz - hz) * 1000)
PCB_T = 0.0016                    # measured: (thickness 1.6) in the .kicad_pcb
yF = hy - PCB_T / 2 - 0.0002      # string lies on the camera-side face
yB = hy + PCB_T / 2 + 0.0004      # and on the back face
tipT = tipz + 0.0004
H = Vector(BR)
# ---- real branch (passive collider) + rope loop draped over it, both ends tied through the hang hole to the board
scene = bpy.context.scene
def _select_only(o):
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
Rm = M.to_3x3()
ex, ey, ez = Rm @ Vector((1, 0, 0)), Rm @ Vector((0, 1, 0)), Rm @ Vector((0, 0, 1))
Av = LIMB_AX.normalized()
Uv = ez.cross(Av).normalized()
if Uv.dot(ey) < 0: Uv = -Uv                           # horizontal, across the limb, toward the back
Vv = Av.cross(Uv).normalized()
if Vv.dot(ez) < 0: Vv = -Vv                           # up, perpendicular to the limb
RB = limb_R
RR = (RB + 0.0013) / 0.92                             # rope centre line radius around the limb
Cb = Vector(BR)
DZ = 0.008                                            # board starts this much too high -> rope slack
HC_t = Vector(holeW); HC_s = holeW + ez * DZ
def Qt(side): return holeW + Uv * (0.0013 * side) + ez * 0.0004
def arcp(j, m=4):
    th_ = math.pi * (1 - j / m)
    return Cb + Uv * (RR * math.cos(th_)) + Vv * (RR * math.sin(th_))
def zz(A, B, n, h, sgn):
    out = []
    for k in range(1, n):
        out.append(A + (B - A) * (k / n) + Av * (h * (-1) ** k * sgn))
    return out
def plen(pts_): return sum((pts_[i + 1] - pts_[i]).length for i in range(len(pts_) - 1))
def solve_h(A, B, n, target):
    lo_, hi_ = 0.0, 0.03
    for _ in range(60):
        mid = (lo_ + hi_) / 2
        if plen([A] + zz(A, B, n, mid, 1) + [B]) < target: lo_ = mid
        else: hi_ = mid
    return (lo_ + hi_) / 2
NZ = 6
M0, M4 = arcp(0), arcp(4)
Qf_s, Qb_s = Qt(-1) + ez * DZ, Qt(+1) + ez * DZ
hf = solve_h(Qf_s, M0, NZ, (M0 - Qt(-1)).length)
hb = solve_h(Qb_s, M4, NZ, (M4 - Qt(+1)).length)
nodes = [HC_s, Qf_s] + zz(Qf_s, M0, NZ, hf, 1) + [arcp(j) for j in range(5)] + zz(M4, Qb_s, NZ, hb, -1) + [Qb_s, HC_s]
# node ordering fix: zigzag lists run A->B excluding ends, so add the ends explicitly
nodes = [HC_s, Qf_s] + zz(Qf_s, M0, NZ, hf, 1)
nodes_ = nodes + [M0] + [arcp(j) for j in range(1, 4)] + [M4] + zz(M4, Qb_s, NZ, hb, -1) + [Qb_s, HC_s]
nodes = nodes_
NLINK = len(nodes) - 1
print("ROPE nodes", len(nodes), "links", NLINK, "hf,hb mm", hf * 1000, hb * 1000, "taut length mm", ((Qt(-1) - HC_t).length + (M0 - Qt(-1)).length) * 1000)
assert NLINK <= 19
# board body (box at board size, origin at its centre of mass)
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 0))
proxy = bpy.context.object
proxy.name = "board_body"
proxy.scale = (hi.x - lo.x, hi.y - lo.y, hi.z - lo.z)
_select_only(proxy); bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)   # real size in the mesh, no object scale
proxy.hide_render = True; proxy.display_type = 'WIRE'
root.parent = proxy
_select_only(proxy)
bpy.ops.rigidbody.world_add()
bpy.ops.rigidbody.object_add(type='ACTIVE')
rb = proxy.rigid_body
rb.mass = 0.006; rb.collision_shape = 'BOX'
rb.linear_damping = 0.5; rb.angular_damping = 0.9
rb.collision_collections = [False] * 20
rbw = scene.rigidbody_world
rbw.substeps_per_frame = 120
rbw.solver_iterations = 200
# collider: an invisible cylinder fitted to the real limb at the rope position (the limb mesh itself is what you see)
bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=RB * 0.97, depth=0.035, location=Cb)
br = bpy.context.object; br.name = "tree_limb_collider"
br.rotation_mode = 'QUATERNION'; br.rotation_quaternion = Av.to_track_quat('Z', 'Y')
br.hide_render = True; br.display_type = 'WIRE'
_select_only(br); bpy.ops.rigidbody.object_add(type='PASSIVE')
br.rigid_body.collision_shape = 'CYLINDER'
br.rigid_body.use_margin = True; br.rigid_body.collision_margin = 0.0001
br.rigid_body.friction = 1.0
br.rigid_body.collision_collections = [False] + [True] * 19
# links
links = []
for i in range(NLINK):
    a_, b_ = nodes[i], nodes[i + 1]
    d_ = b_ - a_
    ln = d_.length
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(a_ + b_) / 2)
    lk = bpy.context.object; lk.name = "rope_link_%d" % (i + 1)
    lk.scale = (ln, 0.0010, 0.0010)
    lk.rotation_mode = 'QUATERNION'; lk.rotation_quaternion = d_.normalized().to_track_quat('X', 'Y')
    lk.hide_render = True; lk.display_type = 'WIRE'
    _select_only(lk); bpy.ops.rigidbody.object_add(type='ACTIVE')
    r_ = lk.rigid_body
    r_.mass = 0.0003; r_.collision_shape = 'BOX'
    r_.use_margin = True; r_.collision_margin = 0.00005
    r_.linear_damping = 0.5; r_.angular_damping = 0.9; r_.friction = 1.0
    cc = [False] * 20; cc[i + 1] = True
    r_.collision_collections = cc
    links.append(lk)
# joints
for i in range(NLINK + 1):
    jt = bpy.data.objects.new("rope_joint_%d" % i, None)
    bpy.context.collection.objects.link(jt)
    jt.location = nodes[i]
    _select_only(jt); bpy.ops.rigidbody.constraint_add(type='POINT')
    jt.rigid_body_constraint.object1 = proxy if i == 0 else links[i - 1]
    jt.rigid_body_constraint.object2 = proxy if i == NLINK else links[i]
# visible rope: one beveled poly curve through all joints
cu = bpy.data.curves.new("thread", 'CURVE')
cu.dimensions = '3D'
sp = cu.splines.new('POLY')
sp.points.add(len(nodes) - 1)
for i, pv in enumerate(nodes):
    if i in (0, len(nodes) - 1): pv = HC_t      # hole end sits at the board's rest hole (hooked to the board)
    sp.points[i].co = (pv.x, pv.y, pv.z, 1.0)
cu.bevel_depth = 0.00045
cu.bevel_resolution = 3
th = bpy.data.objects.new("thread", cu)
bpy.context.collection.objects.link(th)
cu.materials.append(mat("thread", (0.55, 0.04, 0.03), rough=0.7))
th.visible_shadow = True
bpy.context.view_layer.update()
def add_hook(obj, ob, idx):
    m_ = obj.modifiers.new("hook_" + ob.name, 'HOOK')
    m_.object = ob
    m_.vertex_indices_set(idx)
    m_.matrix_inverse = ob.matrix_world.inverted()
hole_e = bpy.data.objects.new("hole_point", None)
bpy.context.collection.objects.link(hole_e)
hole_e.parent = proxy
hole_e.matrix_parent_inverse = proxy.matrix_world.inverted()
hole_e.location = HC_t
bpy.context.view_layer.update()
add_hook(th, hole_e, [0, len(nodes) - 1])
for i in range(1, NLINK):          # joint node i rides with link i (its start)
    add_hook(th, links[i], [i])
# release: board hangs from the hole, raised DZ with slack rope, tilted 20 deg
proxy.matrix_world = Matrix.Translation(HC_s) @ Matrix.Rotation(math.radians(20.0), 4, 'Y') @ Matrix.Translation(-holeW)
scene.render.fps = 24
scene.frame_start = 1
scene.frame_end = 240
scene.rigidbody_world.point_cache.frame_start = 1
scene.rigidbody_world.point_cache.frame_end = 240
scene.frame_set(1)
bpy.data.objects.remove(root_parent)

     # the old empty is no longer needed

# ------------------------------------------------------------ world & lights
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
bg = w.node_tree.nodes["Background"]
bg.inputs["Color"].default_value = (0.012, 0.015, 0.03, 1); bg.inputs["Strength"].default_value = 1.0
def area(loc, col, e, size, tgt):
    bpy.ops.object.light_add(type='AREA', location=loc)
    L = bpy.context.object
    L.data.color = col; L.data.energy = e; L.data.size = size
    L.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return L
area((-1.3, -0.9, 0.15), (1.0, 0.45, 0.16), 4.0, 0.6, (0, 0, 0))      # fireplace glow, camera-left
area((1.2, 0.9, 0.5), (0.45, 0.6, 1.0), 1.2, 0.8, (0, 0.2, 0))         # cool moon rim from right-back
area((-0.4, -0.7, 0.30), (1.0, 0.6, 0.3), 0.5, 0.5, (0, 0, 0))
tree_rec = bpy.data.collections.new("tree_rec")
bpy.context.scene.collection.children.link(tree_rec)
for o in tree_objs:
    tree_rec.objects.link(o)
tf = area((-0.6, -1.0, 0.35), (1.0, 0.55, 0.25), 20.0, 0.8, (0, 0.2, 0.0))
tf.light_linking.receiver_collection = tree_rec         # small warm key on the back of the board
# out-of-focus warm lights in the room far behind the tree
for k in range(14):
    p = Vector((random.uniform(-2.2, 2.2), 3.7, random.uniform(-0.4, 1.8)))
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=8, radius=0.05, location=p)
    c = random.choice(bulb_cols)
    bpy.context.object.data.materials.append(mat("fairy_bg%d" % k, c, emit=c, strength=40.0))

# ------------------------------------------------------------ compositor glow
sc.use_nodes = True
ct = sc.node_tree
for n in list(ct.nodes):
    ct.nodes.remove(n)
rl = ct.nodes.new("CompositorNodeRLayers")
gl = ct.nodes.new("CompositorNodeGlare")
gl.glare_type = 'FOG_GLOW'
gl.quality = 'HIGH'
gl.threshold = 1.2
gl.size = 8
gl.mix = -0.25
out = ct.nodes.new("CompositorNodeComposite")
ct.links.new(rl.outputs["Image"], gl.inputs["Image"])
ct.links.new(gl.outputs["Image"], out.inputs["Image"])

for o in bpy.data.objects:
    if o.type == 'MESH' and o.data.materials and o.data.materials[0] and o.data.materials[0].name.startswith('fairy'):
        o.visible_diffuse = False
        o.visible_glossy = False
        o.visible_transmission = False
        o.visible_shadow = False
sc.view_layers[0].use_pass_object_index = True
for o in board_meshes:
    o.pass_index = 1
for o in bpy.data.objects:
    if o.type == 'MESH' and o.parent and o.parent.name in leds:
        o.pass_index = 1
im = ct.nodes.new("CompositorNodeIDMask")
im.index = 1
im.use_antialiasing = True
fo = ct.nodes.new("CompositorNodeOutputFile")
fo.base_path = os.path.dirname(OUT)
fo.file_slots[0].path = "mask_%s_%s_" % (CAM, LEDSET)
fo.format.file_format = 'PNG'
fo.format.color_mode = 'BW'
ct.links.new(rl.outputs["IndexOB"], im.inputs[0])
ct.links.new(im.outputs[0], fo.inputs[0])
# ------------------------------------------------------------ camera(s)
CAMS = {
    "front": (Vector((0.05, -0.36, boardC.z + 0.008)), boardC, 50),
    "left": (Vector((-0.27, -0.30, boardC.z + 0.028)), boardC, 50),
    "right": (Vector((0.28, -0.30, boardC.z + 0.010)), boardC, 50),
    "close": (holeW + Vector((0.02, -0.17, 0.030)), holeW + Vector((0.0, 0.0, 0.020)), 70),
}
cloc, ctgt, clens = CAMS[CAM]
bpy.ops.object.camera_add(location=cloc)
cam = bpy.context.object
sc.camera = cam
cam.data.lens = clens
cam.data.sensor_width = 36
d = ctgt - cam.location
cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
cam.data.dof.use_dof = True
cam.data.dof.focus_distance = d.length
cam.data.dof.aperture_fstop = 3.5 if CAM != "close" else 2.8
cam.data.dof.aperture_blades = 7
cam.data.dof.aperture_rotation = 0.3

if os.environ.get("SAVE_BLEND"):   # editable scene file instead of a render
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=os.environ["SAVE_BLEND"], compress=True)
    print("SAVED", os.environ["SAVE_BLEND"])
else:
    for _f in range(1, int(os.environ.get('PHYS_FRAME', '229')) + 1):   # step the simulation frame by frame
        sc.frame_set(_f)
        if os.environ.get('PHYS_LOG') and (_f <= 12 or _f % 20 == 0):
            _hp = proxy.matrix_world @ (Vector(holeW))   # proxy local origin = board centre; holeW is pre-body world pos
            _dn = (proxy.matrix_world.to_3x3() @ (boardC - holeW)).normalized()
            print("PHYS", _f, "hole_z_mm", round((_hp.z - holeW.z) * 1000, 2), "tilt_deg", round(math.degrees(math.acos(max(-1, min(1, -_dn.z)))), 2), flush=True)
    if os.environ.get('PHYS_LOG'):
        for _i, _lk in enumerate(links):
            _d = _lk.matrix_world.translation - Cb
            _t = _d.dot(Av); _r = (_d - Av * _t)
            print("LINK", _i + 1, "along_mm", round(_t * 1000, 1), "radial_mm", round(_r.length * 1000, 1), "up_mm", round(_r.dot(Vv) * 1000, 1), "side_mm", round(_r.dot(Uv) * 1000, 1))
        print("LIMB R at rope mm", RB * 1000, "RR", RR * 1000)
        _dg = bpy.context.evaluated_depsgraph_get(); _te = th.evaluated_get(_dg); _m = _te.to_mesh()
        _far = max(((_te.matrix_world @ v.co) - Cb).length for v in _m.vertices)
        print("THREAD farthest vertex from the stem mm %.1f" % (_far * 1000))
        _nrm = proxy.matrix_world.to_3x3() @ Vector((0, -1, 0))   # camera-facing (back) side normal at rest = -Y
        print("YAW: back-side normal now", [round(v, 3) for v in _nrm], "yaw deg", round(math.degrees(math.atan2(_nrm.x, -_nrm.y)), 1))
    sc.render.filepath = OUT
    bpy.ops.render.render(write_still=True)
print("DONE", OUT)

