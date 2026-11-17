import bpy, bmesh, math, random, sys
from mathutils import Vector, Euler, Matrix

import os
S = os.environ.get('LEDSTAR_WORK', os.path.dirname(os.path.abspath(__file__)) + '/work')
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
cy.use_denoising = False
cy.max_bounces = 8
cy.caustics_reflective = False
cy.caustics_refractive = False
cy.sample_clamp_indirect = 3
cy.sample_clamp_direct = 30
cy.use_adaptive_sampling = True
cy.time_limit = 1150
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
WHITE = ["D1", "D5", "D9", "D13", "D17"]
YELLOW = ["D21", "D22", "D23", "D24", "D25"]
glow_leds = WHITE + YELLOW

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
    if m.name in ("mat_19",):          # soldermask / body
        b.inputs["Roughness"].default_value = 0.38
        b.inputs["Coat Weight"].default_value = 0.35
        b.inputs["Coat Roughness"].default_value = 0.15
    if m.name in ("mat_17", "mat_18"):  # silkscreen
        b.inputs["Roughness"].default_value = 0.55
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
                c = (1.0, 0.93, 0.8) if name in WHITE else (1.0, 0.62, 0.05)
                o.data.materials[i] = mat("lens_" + name, c, emit=c, strength=25.0)
            else:
                o.data.materials[i] = mat("dead_" + name, (0.015, 0.015, 0.02), rough=0.25, Coat_Weight=0.5)

wcol = (1.0, 0.93, 0.80)   # warm-ish white LED
ycol = (1.0, 0.62, 0.05)   # amber yellow
for n in glow_leds:
    e = leds[n]
    p = e.matrix_world.translation.copy()
    col = wcol if n in WHITE else ycol
    # emissive window disc just inside the hole, facing -Y
    bpy.ops.mesh.primitive_circle_add(vertices=24, radius=0.0006, fill_type='NGON',
                                      location=(p.x, back_y + 0.0004, p.z),
                                      rotation=(math.radians(90), 0, 0))
    d = bpy.context.object
    d.name = "glow_" + n
    d.data.materials.append(mat("emit_" + n, col, emit=col, strength=1600.0))
    # soft local light for the halo on the back mask
    bpy.ops.object.light_add(type='POINT', location=(p.x, back_y - 0.0007, p.z))
    L = bpy.context.object
    L.name = "led_light_" + n
    L.data.color = col
    L.data.energy = 0.0005 if n in WHITE else 0.0005
    L.data.shadow_soft_size = 0.0006
    # light from LED on the other side of the window: blocked by PCB; this one sits in front

# ------------------------------------------------------------ hanging thread
hole = None
top = Vector((0, 0, 0))
# top arm hang hole: top-most LED position x, higher z
thread_top = Vector((0.0, back_y - 0.002, 0.30))
# find hang hole x ~ x of top-arm LEDs (D17..?) -> use arm LED with highest z
arm = max(leds.values(), key=lambda o: o.matrix_world.translation.z)
hole_pos = Vector((arm.matrix_world.translation.x, back_y - 0.0005, hi.z - 0.0045))
print("arm top LED", arm.name, arm.matrix_world.translation, "hole est", hole_pos)

# ------------------------------------------------------------ camera
bpy.ops.object.camera_add(location=(0.05, -0.36, 0.028))
cam = bpy.context.object
sc.camera = cam
cam.data.lens = 50
cam.data.sensor_width = 36
tgt = Vector((0.0, 0.0, 0.020))
d = tgt - cam.location
cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
cam.data.dof.use_dof = True
cam.data.dof.focus_distance = d.length
cam.data.dof.aperture_fstop = 3.5
cam.data.dof.aperture_blades = 7
cam.data.dof.aperture_rotation = 0.3

# tilt board a bit so it reads as hanging in the air
root_parent = bpy.data.objects.new("pivot", None)
bpy.context.collection.objects.link(root_parent)
root.parent = root_parent
root_parent.rotation_euler = Euler((math.radians(-2), math.radians(2), math.radians(-8)), 'XYZ')


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
hole_w = root_parent.matrix_world @ hole_pos
anchor_w = hole_w + Vector((0.004, 0.010, 0.040))
shift = anchor_w - anchor_local
for o in tree_objs:
    o.location += shift
allv = allv + np.array(shift)
bpy.context.view_layer.update()
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
bsel = cands[(abs(cands[:, 0]) > 0.075) & (abs(cands[:, 0]) < 0.16) & (cands[:, 1] < anchor_w.y + 0.25) & (cands[:, 2] > -0.10) & (cands[:, 2] < 0.12)]
bplaced = []
for i in rng.permutation(len(bsel)):
    p = Vector(bsel[i].tolist())
    if any((p - q).length < 0.09 for q in bplaced):
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

# ------------------------------------------------------------ thread
bpy.ops.curve.primitive_bezier_curve_add()
th = bpy.context.object
th.name = "thread"
th.data.bevel_depth = 0.00035
th.data.materials.append(mat("thread", (0.55, 0.05, 0.04), rough=0.6))
sp = th.data.splines[0]
bp = sp.bezier_points
bp[0].co = hole_w
bp[0].handle_left = hole_w + Vector((0, 0, -0.01)); bp[0].handle_right = hole_w + Vector((0, 0, 0.02))
bp[1].co = anchor_w
bp[1].handle_left = anchor_w + Vector((0, 0.002, -0.025)); bp[1].handle_right = anchor_w + Vector((0, 0, 0.01))

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
gl.threshold = 2.5
gl.size = 6
gl.mix = -0.6
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
fo.base_path = S
fo.file_slots[0].path = "mask_"
fo.format.file_format = 'PNG'
fo.format.color_mode = 'BW'
ct.links.new(rl.outputs["IndexOB"], im.inputs[0])
ct.links.new(im.outputs[0], fo.inputs[0])
sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("DONE", OUT)
