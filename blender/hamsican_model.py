# Hamsican — Blender character model (skin-modifier body, sculpted head, particle curly hair)
# Usage:  blender -b -P hamsican_model.py -- --out <folder> [--low]
#   --low : fast preview (small resolution, few samples)
import bpy, bmesh, math, sys, os
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[argv.index("--out") + 1] if "--out" in argv else os.path.join(os.path.dirname(os.path.abspath(__file__)), "render")
LOW = "--low" in argv
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------- scene reset
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 24 if LOW else 160
def _has_oidn():
    # Linux distro builds of Blender ship without OpenImageDenoise; the official Windows/macOS builds have it.
    try:
        import _cycles
        return bool(getattr(_cycles, 'with_openimagedenoise', True))
    except Exception:
        return sys.platform != 'linux'
HAS_OIDN = _has_oidn()
scene.cycles.use_denoising = bool(HAS_OIDN)
if not HAS_OIDN: scene.cycles.samples = 48 if LOW else 256   # no denoiser in this build: more samples instead
scene.render.resolution_x, scene.render.resolution_y = (540, 960) if LOW else (1080, 1920)
scene.render.film_transparent = False
scene.view_settings.view_transform = 'AgX' if 'AgX' in [i.identifier for i in scene.view_settings.bl_rna.properties['view_transform'].enum_items] else 'Filmic'
scene.view_settings.look = 'None'

def enable_gpu():
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        for kind in ('OPTIX', 'CUDA', 'HIP', 'ONEAPI', 'METAL'):
            try:
                prefs.compute_device_type = kind
                prefs.get_devices()
                devs = [d for d in prefs.devices if d.type == kind]
                if devs:
                    for d in prefs.devices: d.use = True
                    scene.cycles.device = 'GPU'
                    print("GPU:", kind, [d.name for d in devs]); return
            except Exception:
                pass
    except Exception as e:
        print("GPU setup skipped:", e)
    print("Rendering on CPU")
enable_gpu()

# ---------------------------------------------------------------- materials
def mat(name, color, rough=0.5, metal=0.0, sss=0.0, sheen=0.0, coat=0.0, spec=0.5):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    for key, val in (("Subsurface Weight", sss), ("Subsurface", sss)):
        if key in b.inputs: b.inputs[key].default_value = val; break
    if "Subsurface Radius" in b.inputs: b.inputs["Subsurface Radius"].default_value = (1.0, 0.35, 0.2)
    if "Subsurface Scale" in b.inputs: b.inputs["Subsurface Scale"].default_value = 0.012
    for key in ("Sheen Weight", "Sheen"):
        if key in b.inputs: b.inputs[key].default_value = sheen; break
    for key in ("Coat Weight", "Clearcoat"):
        if key in b.inputs: b.inputs[key].default_value = coat; break
    return m

def srgb(h):
    c = [((h >> s) & 255) / 255 for s in (16, 8, 0)]
    return tuple((v / 12.92) if v <= 0.04045 else (((v + 0.055) / 1.055) ** 2.4) for v in c)

SKIN = mat("Skin", srgb(0xe2a882), 0.45, sss=0.25)
SHIRT = mat("Shirt", srgb(0x7ec8e3), 0.75, sheen=0.4)
PANTS = mat("Pants", srgb(0x2a3f66), 0.8, sheen=0.3)
SHOE = mat("Shoe", srgb(0xf1eee6), 0.35)
SOLE = mat("Sole", srgb(0x1b1b1b), 0.6)
BLACK = mat("Bow", srgb(0x111111), 0.4, sheen=0.3)
GOLD = mat("Gold", srgb(0xd4a640), 0.25, metal=1.0)
WHITE = mat("Sclera", srgb(0xf4f1ec), 0.2, coat=1.0)
IRIS = mat("Iris", srgb(0x4a2a14), 0.25)
PUPIL = mat("Pupil", (0.0, 0.0, 0.0), 0.2)
LIP = mat("Lip", srgb(0xb36a62), 0.4, sss=0.2)
BROW = mat("Brow", srgb(0x24170e), 0.6)
BUTTON = mat("Button", srgb(0xf5f5f5), 0.3)
CORNEA = bpy.data.materials.new("Cornea"); CORNEA.use_nodes = True
nt = CORNEA.node_tree; nt.nodes.clear()
g = nt.nodes.new("ShaderNodeBsdfGlass"); g.inputs["Roughness"].default_value = 0.0; g.inputs["IOR"].default_value = 1.376
o = nt.nodes.new("ShaderNodeOutputMaterial"); nt.links.new(g.outputs[0], o.inputs[0])
HAIR = bpy.data.materials.new("Hair"); HAIR.use_nodes = True
nt = HAIR.node_tree; nt.nodes.clear()
hb = nt.nodes.new("ShaderNodeBsdfHairPrincipled")
if "Melanin" in hb.inputs: hb.inputs["Melanin"].default_value = 0.88
if "Melanin Redness" in hb.inputs: hb.inputs["Melanin Redness"].default_value = 0.45
if "Roughness" in hb.inputs: hb.inputs["Roughness"].default_value = 0.35
if "Random Color" in hb.inputs: hb.inputs["Random Color"].default_value = 0.15
o = nt.nodes.new("ShaderNodeOutputMaterial"); nt.links.new(hb.outputs[0], o.inputs[0])

def link(obj): bpy.context.collection.objects.link(obj); return obj
def smooth(obj):
    for p in obj.data.polygons: p.use_smooth = True
def subsurf(obj, lv=2):
    m = obj.modifiers.new("Sub", 'SUBSURF'); m.levels = lv; m.render_levels = lv; return m
def sphere(name, r, loc, material, scale=(1, 1, 1), seg=48, rings=32):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=r)
    bm.to_mesh(me); bm.free()
    ob = link(bpy.data.objects.new(name, me)); ob.location = loc; ob.scale = scale
    ob.data.materials.append(material); smooth(ob); return ob

# ---------------------------------------------------------------- body (skin modifier)
# Blender axes: Z up, -Y forward.
J = {  # name: (x, y, z, radius_x, radius_y)
    'pelvis': (0, 0, 0.95, 0.165, 0.12), 'spine': (0, 0, 1.12, 0.155, 0.11), 'chest': (0, 0, 1.30, 0.185, 0.125),
    'upper': (0, 0, 1.43, 0.17, 0.11), 'neck0': (0, 0.0, 1.50, 0.058, 0.058), 'neck1': (0, 0.005, 1.585, 0.052, 0.052),
}
for s, x in (('L', 1), ('R', -1)):
    J.update({
        f'sh{s}': (0.205 * x, 0, 1.44, 0.068, 0.068), f'el{s}': (0.25 * x, 0.01, 1.17, 0.05, 0.05),
        f'wr{s}': (0.27 * x, 0.0, 0.94, 0.037, 0.033), f'hd{s}': (0.278 * x, -0.005, 0.85, 0.042, 0.024),
        f'th{s}': (0.245 * x, -0.03, 0.9, 0.013, 0.013),
        f'hp{s}': (0.095 * x, 0, 0.9, 0.1, 0.1), f'kn{s}': (0.105 * x, -0.01, 0.52, 0.068, 0.068),
        f'an{s}': (0.105 * x, 0.01, 0.1, 0.05, 0.05), f'to{s}': (0.105 * x, -0.13, 0.045, 0.055, 0.038),
    })
E = [('pelvis', 'spine'), ('spine', 'chest'), ('chest', 'upper'), ('upper', 'neck0'), ('neck0', 'neck1')]
for s in 'LR':
    E += [('upper', f'sh{s}'), (f'sh{s}', f'el{s}'), (f'el{s}', f'wr{s}'), (f'wr{s}', f'hd{s}'), (f'wr{s}', f'th{s}'),
          ('pelvis', f'hp{s}'), (f'hp{s}', f'kn{s}'), (f'kn{s}', f'an{s}'), (f'an{s}', f'to{s}')]
names = list(J.keys())
me = bpy.data.meshes.new("Body")
me.from_pydata([J[n][:3] for n in names], [(names.index(a), names.index(b)) for a, b in E], [])
body = link(bpy.data.objects.new("Body", me))
sk = body.modifiers.new("Skin", 'SKIN'); sk.use_smooth_shade = True
for i, n in enumerate(names):
    v = me.skin_vertices[0].data[i]; v.radius = (J[n][3], J[n][4]); v.use_root = (n == 'pelvis')
bpy.context.view_layer.objects.active = body; body.select_set(True)
bpy.ops.object.modifier_apply(modifier="Skin")
# material zones by height / limb
for m in (SHIRT, PANTS, SKIN, SHOE, SOLE): body.data.materials.append(m)
for p in body.data.polygons:
    c = p.center
    if c.z < 0.075 and c.z > 0.0: idx = 3
    if c.z <= 0.02: idx = 4
    elif c.z < 0.14: idx = 3                      # shoes
    elif c.z < 0.97 and abs(c.x) < 0.215: idx = 1   # pants
    elif c.z > 1.505: idx = 2                     # neck
    elif abs(c.x) > 0.245 and c.z < 0.955: idx = 2 # hands
    else: idx = 0                                 # shirt
    p.material_index = idx
smooth(body); subsurf(body, 2)

# ---------------------------------------------------------------- head (sculpted)
HZ = 1.68
def gau(dx, dy, sx, sy): return math.exp(-((dx / sx) ** 2 + (dy / sy) ** 2))
hm = bpy.data.meshes.new("Head"); bm = bmesh.new()
bmesh.ops.create_uvsphere(bm, u_segments=96, v_segments=72, radius=1.0)
for v in bm.verts:
    x, fz, y = v.co.x, -v.co.y, v.co.z      # x right, fz forward, y up (unit sphere)
    front = max(0.0, fz)
    X, Y, Z = x * 0.102, y * 0.124, fz * 0.112
    if y < 0:
        k = (-y) ** 1.6; X *= 1 - 0.3 * k; Z *= 1 - 0.1 * k
    if fz < 0: Z *= 0.94
    out = 0.0
    out += 0.016 * gau(x, y + 0.78, 0.26, 0.18) * front
    out += 0.0045 * gau(x, y - 0.24, 0.55, 0.08) * front
    out -= 0.0065 * (gau(x - 0.37, y - 0.08, 0.17, 0.12) + gau(x + 0.37, y - 0.08, 0.17, 0.12)) * front
    out += 0.0045 * (gau(x - 0.52, y + 0.12, 0.17, 0.12) + gau(x + 0.52, y + 0.12, 0.17, 0.12)) * front
    ridge = gau(x, 0, 0.075, 1) * min(1, max(0, (0.16 - y) / 0.36)) * (1 if y > -0.32 else 0)
    out += (0.0115 * ridge + 0.0085 * gau(x, y + 0.2, 0.13, 0.1) + 0.0035 * (gau(x - 0.11, y + 0.24, 0.07, 0.06) + gau(x + 0.11, y + 0.24, 0.07, 0.06))) * max(0, fz - 0.6) / 0.4
    out += 0.0035 * gau(x, y + 0.48, 0.3, 0.1) * front
    out -= 0.002 * gau(x, y + 0.62, 0.25, 0.05) * front
    L = math.sqrt(X * X + Y * Y + Z * Z)
    X += X / L * out; Y += Y / L * out; Z += Z / L * out
    v.co = Vector((X, -Z, Y))
bm.to_mesh(hm); bm.free()
head = link(bpy.data.objects.new("Head", hm)); head.location = (0, 0, HZ); head.data.materials.append(SKIN); smooth(head); subsurf(head, 1)

# scalp vertex group (above the hairline) for the hair particles
def hairline(nx, ny, nz):  # unit dir: nx right, ny up, nz forward
    az = abs(math.atan2(nx, nz)) / math.pi
    return (0.42 + (0.24 - 0.42) * az / 0.5) if az < 0.5 else (0.24 + (-0.42 - 0.24) * (az - 0.5) / 0.5)
vg = head.vertex_groups.new(name="scalp")
for v in hm.vertices:
    d = v.co.normalized(); nx, ny, nz = d.x, d.z, -d.y
    w = max(0.0, min(1.0, (ny - hairline(nx, ny, nz)) / 0.06))
    if w > 0: vg.add([v.index], w, 'REPLACE')

# ears
for sx in (1, -1):
    e = sphere(f"Ear{sx}", 0.028, (sx * 0.1, 0.004, HZ - 0.01), SKIN, (0.34, 0.6, 0.82))
    bpy.ops.mesh.primitive_torus_add(major_radius=0.019, minor_radius=0.005, location=(sx * 0.104, 0.008, HZ - 0.008), rotation=(0, math.pi / 2, 0))
    rim = bpy.context.active_object; rim.scale = (1.12, 0.72, 1); rim.data.materials.append(SKIN); smooth(rim)

# eyes
for sx in (1, -1):
    c = Vector((sx * 0.037, -0.086, HZ + 0.009))
    sphere(f"Sclera{sx}", 0.0172, c, WHITE)
    sphere(f"Iris{sx}", 0.0094, c + Vector((0, -0.0152, 0)), IRIS, (1, 0.35, 1), 32, 16)
    sphere(f"Pupil{sx}", 0.0045, c + Vector((0, -0.0176, 0)), PUPIL, (1, 0.3, 1), 24, 12)
    lid = sphere(f"Lid{sx}", 0.0186, c, SKIN, seg=48, rings=24)
    bm2 = bmesh.new(); bm2.from_mesh(lid.data)
    bmesh.ops.delete(bm2, geom=[v for v in bm2.verts if v.co.z < 0.0115], context='VERTS'); bm2.to_mesh(lid.data); bm2.free()
    lid.rotation_euler = (math.radians(-12), 0, 0)
    # brow
    bpy.ops.mesh.primitive_cylinder_add(radius=0.0042, depth=0.04, location=(sx * 0.039, -0.1, HZ + 0.042), rotation=(0, math.pi / 2, sx * -0.12))
    br = bpy.context.active_object; br.scale = (1, 1, 1); br.data.materials.append(BROW); smooth(br); subsurf(br, 1)

# nostrils + mouth
for sx in (1, -1):
    sphere(f"Nostril{sx}", 0.004, (sx * 0.0085, -0.119, HZ - 0.031), PUPIL, (1, 0.6, 0.55), 16, 8)
bpy.ops.mesh.primitive_torus_add(major_radius=0.017, minor_radius=0.0038, location=(0, -0.094, HZ - 0.062), rotation=(math.pi / 2, 0, 0))
lo = bpy.context.active_object; lo.scale = (1, 0.55, 0.55); lo.data.materials.append(LIP); smooth(lo)
bm2 = bmesh.new(); bm2.from_mesh(lo.data); bmesh.ops.delete(bm2, geom=[v for v in bm2.verts if v.co.z > 0.0], context='VERTS'); bm2.to_mesh(lo.data); bm2.free()
bpy.ops.mesh.primitive_cylinder_add(radius=0.0028, depth=0.04, location=(0, -0.097, HZ - 0.058), rotation=(0, math.pi / 2, 0))
up = bpy.context.active_object; up.data.materials.append(LIP); smooth(up); subsurf(up, 1)

# ---------------------------------------------------------------- hair (particle system)
ps = head.modifiers.new("Hair", 'PARTICLE_SYSTEM').particle_system
st = ps.settings
st.type = 'HAIR'; st.use_advanced_hair = False
try: st.count = 1800 if LOW else 5000
except Exception as e: print('skip', 'count', e)
try: st.hair_length = 0.032
except Exception as e: print('skip', 'hair_length', e)
try: st.emit_from = 'FACE'
except Exception as e: print('skip', 'emit_from', e)
try: st.render_type = 'PATH'
except Exception as e: print('skip', 'render_type', e)
try: st.child_type = 'INTERPOLATED'
except Exception as e: print('skip', 'child_type', e)
try: st.rendered_child_count = 12 if LOW else 40
except Exception as e: print('skip', 'rendered_child_count', e)
try: st.kink = 'CURL'
except Exception as e: print('skip', 'kink', e)
try: st.kink_amplitude = 0.0055
except Exception as e: print('skip', 'kink_amplitude', e)
try: st.kink_frequency = 9.0
except Exception as e: print('skip', 'kink_frequency', e)
try: st.kink_shape = 0.2
except Exception as e: print('skip', 'kink_shape', e)
try: st.roughness_1 = 0.004
except Exception as e: print('skip', 'roughness_1', e)
try: st.roughness_endpoint = 0.004
except Exception as e: print('skip', 'roughness_endpoint', e)
st.root_radius = 1.0; st.tip_radius = 0.2; st.radius_scale = 0.0012
try: st.clump_factor = 0.35
except Exception as e: print('skip', 'clump_factor', e)
head.data.materials.append(HAIR)
try: st.material = len(head.data.materials)
except Exception as e: print('skip', 'material', e)
ps.vertex_group_density = "scalp"
ps.vertex_group_length = "scalp"
try: st.use_hair_bspline = True
except Exception as e: print('skip', 'use_hair_bspline', e)
st.display_step = 4; st.render_step = 5

# ---------------------------------------------------------------- shirt details
for i in range(4):
    sphere(f"Button{i}", 0.0065, (0, -0.124 + i * 0.004, 1.40 - i * 0.09), BUTTON, (1, 0.4, 1), 16, 8)
for sx in (1, -1):
    bpy.ops.mesh.primitive_cone_add(radius1=0.026, depth=0.05, location=(sx * 0.026, -0.065, 1.505), rotation=(0, sx * math.pi / 2, 0))
    c = bpy.context.active_object; c.scale = (1, 0.5, 1); c.data.materials.append(BLACK); smooth(c)
sphere("BowKnot", 0.011, (0, -0.07, 1.505), BLACK)
bpy.ops.mesh.primitive_cube_add(size=1, location=(0.08, -0.12, 1.38)); bd = bpy.context.active_object; bd.scale = (0.06, 0.006, 0.032); bd.data.materials.append(GOLD)
bev = bd.modifiers.new("Bevel", 'BEVEL'); bev.width = 0.002; bev.segments = 3
for sx in (1, -1):   # collar
    bpy.ops.mesh.primitive_cube_add(size=1, location=(sx * 0.035, -0.06, 1.525), rotation=(math.radians(-35), sx * math.radians(30), sx * math.radians(30)))
    co = bpy.context.active_object; co.scale = (0.06, 0.004, 0.04); co.data.materials.append(SHIRT); b2 = co.modifiers.new("Bevel", 'BEVEL'); b2.width = 0.003; b2.segments = 3
bpy.ops.mesh.primitive_torus_add(major_radius=0.15, minor_radius=0.012, location=(0, 0, 0.99)); belt = bpy.context.active_object
belt.scale = (1.08, 0.78, 1.2); belt.data.materials.append(BLACK)
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, -0.122, 0.99)); bk = bpy.context.active_object; bk.scale = (0.045, 0.008, 0.03); bk.data.materials.append(GOLD)

# ---------------------------------------------------------------- stage, lights, camera
bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, 0)); fl = bpy.context.active_object
fl.data.materials.append(mat("Floor", srgb(0x2a2f3a), 0.6))
bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 4, 5), rotation=(math.pi / 2, 0, 0)); bg = bpy.context.active_object
bg.data.materials.append(mat("Backdrop", srgb(0x1b2238), 0.9))
world = bpy.data.worlds.new("World"); scene.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.02, 0.025, 0.04, 1); world.node_tree.nodes["Background"].inputs[1].default_value = 1.0

def area(name, loc, rot, energy, size, color=(1, 1, 1)):
    d = bpy.data.lights.new(name, 'AREA'); d.energy = energy; d.size = size; d.color = color
    ob = link(bpy.data.objects.new(name, d)); ob.location = loc; ob.rotation_euler = rot; return ob
def aim(ob, target):
    ob.rotation_euler = (Vector(target) - ob.location).to_track_quat('-Z', 'Y').to_euler()
key = area("Key", (-1.2, -1.6, 2.3), (0, 0, 0), 220, 1.2, (1.0, 0.95, 0.88)); aim(key, (0, 0, 1.5))
fill = area("Fill", (1.6, -1.4, 1.6), (0, 0, 0), 70, 1.5, (0.85, 0.9, 1.0)); aim(fill, (0, 0, 1.4))
rim = area("Rim", (0.4, 1.4, 2.4), (0, 0, 0), 260, 0.8, (0.75, 0.85, 1.0)); aim(rim, (0, 0, 1.6))

cam_d = bpy.data.cameras.new("Cam"); cam = link(bpy.data.objects.new("Cam", cam_d)); scene.camera = cam
cam_d.sensor_width = 36
cam_d.dof.use_dof = True; cam_d.dof.aperture_fstop = 2.8

def shot(name, loc, target, lens, focus):
    cam.location = loc; aim(cam, target); cam_d.lens = lens
    cam_d.dof.focus_distance = focus
    scene.render.filepath = os.path.join(OUT, name)
    bpy.ops.render.render(write_still=True)
    print("rendered", scene.render.filepath)

shot("hamsican_yuz_on.png", (0, -0.75, HZ + 0.01), (0, 0, HZ), 85, 0.72)
shot("hamsican_yuz_capraz.png", (0.5, -0.58, HZ + 0.03), (0, 0, HZ), 85, 0.74)
shot("hamsican_boy.png", (0.9, -3.4, 1.05), (0, 0, 0.95), 50, 3.4)
