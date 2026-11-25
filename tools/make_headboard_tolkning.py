"""침대헤드 3D 모델: 이케아 TOLKNING 톨크닝 침대헤드, 핸드메이드 라탄 (105.126.32).

    python tools/make_bed_tex.py rattan      (질감 먼저)
    "C:/Program Files/Blender Foundation/Blender 5.3/blender.exe" -b -P tools/make_headboard_tolkning.py

치수 (상품 정보): 폭 100 cm, 높이 96 cm, 두께 3 cm (매트리스 폭 90 cm용, 바닥에 세워 벽에 기대는 독립형).
생김새(상품 사진): 등나무 껍질을 감은 굵은 라탄 기둥(약 28 mm)으로 모서리가 둥근 사각 틀,
그 안쪽에 가는 테두리와 짧은 살대로 띄워 단 마름모 엮음 판(납작한 띠, 구멍이 비침),
틀 아래로 바닥까지 내려가는 가는 다리 두 개(뒤쪽).
좌표: 바닥 가운데 = 원점, 단위 m. 앞(침대 쪽) = three.js +z = Blender -Y, 폭 = x.
결과: docs/models/headboard_tolkning.glb
"""
import bpy, bmesh, math, os
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEX = os.path.join(ROOT, 'bake', 'bed_tex')
OUT = os.path.join(ROOT, 'docs', 'models', 'headboard_tolkning.glb')

W, H = 1.0, .96
R_FRAME = .014                  # 바깥 틀 기둥 반지름
FRAME_Z0 = .20                  # 틀 아래 끝 높이 (그 아래는 다리)
CORNER = .06
INSET = .05                     # 바깥 틀 중심선 → 안쪽 테두리 중심선
R_INNER = .005
R_ROD, ROD_STEP = .0025, .045   # 살대
R_LEG, LEG_X = .009, .27

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


def tex_mat(name, diff, nor=None, rough=.6, cutout=False, size=None):
    """size: 사이트용 파일 크기를 줄이려고 그림을 이 크기(px)로 줄여서 넣는다 (투명 PNG라 JPEG로 못 줄임)"""
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    b.inputs['Roughness'].default_value = rough
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(os.path.join(TEX, diff))
    if size: t.image.scale(size, size)
    nt.links.new(t.outputs['Color'], b.inputs['Base Color'])
    if cutout:                   # 구멍: 알파를 반올림해서 잘라내기 (glTF alphaMode MASK)
        rnd = nt.nodes.new('ShaderNodeMath'); rnd.operation = 'ROUND'
        nt.links.new(t.outputs['Alpha'], rnd.inputs[0]); nt.links.new(rnd.outputs[0], b.inputs['Alpha'])
        m.use_backface_culling = False
    if nor:
        im = bpy.data.images.load(os.path.join(TEX, nor)); im.colorspace_settings.name = 'Non-Color'
        if size: im.scale(size, size)
        tn = nt.nodes.new('ShaderNodeTexImage'); tn.image = im
        nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = .7
        nt.links.new(tn.outputs['Color'], nm.inputs['Color']); nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])
    return m


WRAP = tex_mat('rattan_wrap', 'rattan_wrap.png', 'rattan_wrap_nor.png', rough=.55)
LATTICE = tex_mat('rattan_lattice', 'rattan_lattice.png', 'rattan_lattice_nor.png', rough=.6, cutout=True, size=512)


def rrect_path(w, h, r, cz, n=10):
    """XZ 평면의 둥근 사각 (닫힌 꺾은선, 가운데 높이 cz)"""
    pts = []
    for cx, cy, a0 in ((w / 2 - r, -h / 2 + r, -90), (w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n); pts.append(Vector((cx + r * math.cos(a), 0, cz + cy + r * math.sin(a))))
    return pts


def tube(name, path, radius, mat, cyclic=False, wrap_uv=True):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'
    cu.bevel_depth = radius; cu.bevel_resolution = 4; cu.use_fill_caps = not cyclic
    sp = cu.splines.new('POLY'); sp.points.add(len(path) - 1); sp.use_cyclic_u = cyclic
    for k, q in enumerate(path): sp.points[k].co = (q.x, q.y, q.z, 1)
    o = bpy.data.objects.new(name, cu); scene.collection.objects.link(o)
    bpy.context.view_layer.objects.active = o; o.select_set(True)
    bpy.ops.object.convert(target='MESH'); o.select_set(False)
    me = o.data
    while me.uv_layers: me.uv_layers.remove(me.uv_layers[0])
    uv = me.uv_layers.new(name='UVMap')
    if wrap_uv:                  # u = 기둥 길이 방향 거리 (감은 띠가 기둥을 가로지르게), v = 둘레 각
        segs, acc = [], 0.
        pp = path + ([path[0]] if cyclic else [])
        for i in range(len(pp) - 1):
            a, b = pp[i], pp[i + 1]; L = (b - a).length; segs.append((a, b, acc, L)); acc += L
        for li, lp in enumerate(me.loops):
            co = me.vertices[lp.vertex_index].co
            best = None
            for a, b, s0, L in segs:
                d = b - a; t = max(0., min(1., (co - a).dot(d) / max(L * L, 1e-9))); q = a + d * t
                dist = (co - q).length_squared
                if best is None or dist < best[0]: best = (dist, s0 + t * L, q, d)
            _, s, q, d = best
            off = co - q; side = d.normalized().cross(Vector((0, 1, 0)))
            ang = math.atan2(off.y, off.dot(side) if side.length > 1e-6 else off.x)
            uv.data[li].uv = (s / .05, ang / (2 * math.pi) * (2 * math.pi * radius) / .0125)
    me.materials.append(mat)
    for p in me.polygons: p.use_smooth = True
    return o


cz = (FRAME_Z0 + H) / 2
fw, fh = W - 2 * R_FRAME, H - FRAME_Z0 - 2 * R_FRAME
outer = rrect_path(fw, fh, CORNER, cz)
tube('frame', outer, R_FRAME, WRAP, cyclic=True)
iw, ih = fw - 2 * INSET, fh - 2 * INSET
inner = rrect_path(iw, ih, .035, cz)
tube('inner', inner, R_INNER, WRAP, cyclic=True)

# 살대: 안쪽 테두리와 바깥 틀 사이 (곧은 구간만)
k = 0
for side in ('top', 'bottom', 'left', 'right'):
    if side in ('top', 'bottom'):
        span = iw / 2 - .035; zi = cz + (ih / 2 if side == 'top' else -ih / 2); zo = cz + (fh / 2 if side == 'top' else -fh / 2)
        n = int(2 * span / ROD_STEP)
        for i in range(n + 1):
            x = -span + 2 * span * i / n
            tube(f'rod{k}', [Vector((x, 0, zi)), Vector((x, 0, zo))], R_ROD, WRAP, wrap_uv=False); k += 1
    else:
        span = ih / 2 - .035; xi = (iw / 2) * (1 if side == 'right' else -1); xo = (fw / 2) * (1 if side == 'right' else -1)
        n = int(2 * span / ROD_STEP)
        for i in range(n + 1):
            z = cz - span + 2 * span * i / n
            tube(f'rod{k}', [Vector((xi, 0, z)), Vector((xo, 0, z))], R_ROD, WRAP, wrap_uv=False); k += 1

# 다리: 틀 뒤(벽 쪽)로 바닥에서 틀 아래 기둥 위까지
for sx in (-1, 1):
    yl = R_FRAME + R_LEG - .004
    tube(f'leg{sx}', [Vector((sx * LEG_X, yl, 0)), Vector((sx * LEG_X, yl, FRAME_Z0 + .12))], R_LEG, WRAP)

# 엮음 판: 안쪽 테두리 안을 채우는 얇은 판 (알파로 구멍)
bm = bmesh.new()
pw, ph = iw - .006, ih - .006
vs = [bm.verts.new((x, 0, cz + z)) for x, z in ((-pw / 2, -ph / 2), (pw / 2, -ph / 2), (pw / 2, ph / 2), (-pw / 2, ph / 2))]
f = bm.faces.new(vs)
me = bpy.data.meshes.new('lattice'); bm.to_mesh(me); bm.free()
lat = bpy.data.objects.new('lattice', me); scene.collection.objects.link(lat)
uv = me.uv_layers.new(name='UVMap')
for li, lp in enumerate(me.loops):
    co = me.vertices[lp.vertex_index].co
    uv.data[li].uv = ((co.x + pw / 2) / .2, (co.z - cz + ph / 2) / .2)
me.materials.append(LATTICE)
# 판 앞면이 침대 쪽(-Y)을 보게
if me.polygons[0].normal.y > 0: me.flip_normals()

for ob in scene.objects:
    if ob.type == 'MESH' and len(ob.data.uv_layers) > 1:
        for extra in list(ob.data.uv_layers)[1:]: ob.data.uv_layers.remove(extra)
bpy.ops.object.select_all(action='SELECT')
bpy.context.view_layer.objects.active = scene.objects['frame']
bpy.ops.object.join()
o = bpy.context.object; o.name = 'headboard_tolkning'
xs = [v.co for v in o.data.vertices]
lo = [min(c[i] for c in xs) for i in range(3)]; hi = [max(c[i] for c in xs) for i in range(3)]
cy = (hi[1] + lo[1]) / 2
for v in o.data.vertices: v.co.y -= cy
print('bbox mm', *[round((hi[i] - lo[i]) * 1000) for i in range(3)], 'leg three z', round(-(R_FRAME + R_LEG - .004 - cy), 4))
print('faces', len(o.data.polygons))
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', export_image_format='AUTO', export_apply=True, export_yup=True)
print('saved', OUT, os.path.getsize(OUT) // 1024, 'KB')
