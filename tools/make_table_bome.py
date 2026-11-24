"""식탁 3D 모델: 룸앤홈 보메 원목 식탁 1200 (1200 × 700 × 740, 화이트).

    python tools/make_bed_tex.py rubber ply      (질감 먼저)
    "C:/Program Files/Blender Foundation/Blender 5.3/blender.exe" -b -P tools/make_table_bome.py

치수 (mm, 상품 정보): 1200 × 700 × 740. 소재: 고무나무, 합판, HPM.
생김새(상품 사진): 흰 HPM 상판, 모서리가 둥글고(반지름 약 50) 옆면은 합판 층이 보이며 아래쪽으로 비스듬히 깎임,
상판 아래 고무나무 테두리(에이프런), 다리는 위가 굵고 아래로 가늘어지며 바깥으로 벌어짐(긴 변 쪽이 더 많이).
좌표: 바닥 가운데 = 원점, 단위 m. 앞 = three.js +z = Blender -Y, 긴 변 = x.
결과: docs/models/table_bome_1200.glb
"""
import bpy, bmesh, math, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEX = os.path.join(ROOT, 'bake', 'bed_tex')
OUT = os.path.join(ROOT, 'docs', 'models', 'table_bome_1200.glb')

W, D, H = 1.2, .70, .74
TOP_T = .018                      # 상판(합판 + HPM) 두께
HPM_T = .0012                     # 흰 HPM 판 두께
R = .05                           # 상판 모서리 반지름
UNDER = .007                      # 상판 아래쪽 깎인 폭 (옆에서 보면 비스듬한 합판 띠)
AH, AT = .055, .02                # 테두리 높이, 두께
LEG_T, LEG_B = .045, .03          # 다리 굵기 (위·아래)
TOP_X, TOP_Y = .49, .265          # 다리 윗면 가운데
FOOT_X, FOOT_Y = .555, .29        # 다리 바닥 가운데

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


def tex_mat(name, diff, nor=None, rough=.5, nstr=.4):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    b.inputs['Roughness'].default_value = rough
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(os.path.join(TEX, diff))
    nt.links.new(t.outputs['Color'], b.inputs['Base Color'])
    if nor:
        im = bpy.data.images.load(os.path.join(TEX, nor)); im.colorspace_settings.name = 'Non-Color'
        tn = nt.nodes.new('ShaderNodeTexImage'); tn.image = im
        nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = nstr
        nt.links.new(tn.outputs['Color'], nm.inputs['Color']); nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])
    return m


WOOD = tex_mat('rubberwood', 'rubber_diff.png', 'rubber_nor.png', rough=.5)
PLY = tex_mat('plywood_edge', 'ply_diff.png', rough=.6)
HPM = bpy.data.materials.new('hpm_white'); HPM.use_nodes = True
hb = HPM.node_tree.nodes['Principled BSDF']
hb.inputs['Base Color'].default_value = (.93, .93, .915, 1); hb.inputs['Roughness'].default_value = .38


def box_uv(o, grain, size=(.5, 1.0)):
    """상자 투영 UV. 결(v)이 grain 축('x', 'y' 또는 'z')을 따르게"""
    me = o.data
    while me.uv_layers: me.uv_layers.remove(me.uv_layers[0])
    uv = me.uv_layers.new(name='UVMap')
    for p in me.polygons:
        n = [abs(c) for c in p.normal]; ax = n.index(max(n))
        for li in p.loop_indices:
            co = o.matrix_world @ me.vertices[me.loops[li].vertex_index].co
            if grain == 'x':
                a, bb = (co.y, co.x) if ax == 2 else (co.z, co.x) if ax == 1 else (co.z, co.y)
            elif grain == 'y':
                a, bb = (co.x, co.y) if ax == 2 else (co.z, co.y) if ax == 0 else (co.x, co.z)
            else:
                a, bb = (co.x, co.z) if ax == 1 else (co.y, co.z) if ax == 0 else (co.x, co.y)
            uv.data[li].uv = (a / size[0], bb / size[1])


def new_obj(name, bm):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); scene.collection.objects.link(o); return o


def bevel(o, w, seg=3):
    bv = o.modifiers.new('bev', 'BEVEL'); bv.width = w; bv.segments = seg; bv.limit_method = 'ANGLE'
    bpy.context.view_layer.objects.active = o; bpy.ops.object.modifier_apply(modifier='bev')


def rrect(w, d, r, n=8):
    """둥근 사각형 윤곽 (반시계)"""
    pts = []
    for cx, cy, a0 in ((w / 2 - r, -d / 2 + r, -90), (w / 2 - r, d / 2 - r, 0), (-w / 2 + r, d / 2 - r, 90), (-w / 2 + r, -d / 2 + r, 180)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n); pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def slab(name, w, d, r, z0, z1, inset0=0.):
    """윤곽을 z0(아래, inset0만큼 안쪽)에서 z1(위)까지 세운 판"""
    bm = bmesh.new()
    lo = [bm.verts.new((x, y, z0)) for x, y in rrect(w - 2 * inset0, d - 2 * inset0, r - inset0)]
    hi = [bm.verts.new((x, y, z1)) for x, y in rrect(w, d, r)]
    n = len(lo)
    bm.faces.new(lo[::-1]); bm.faces.new(hi)
    for i in range(n): bm.faces.new([lo[i], lo[(i + 1) % n], hi[(i + 1) % n], hi[i]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return new_obj(name, bm)


# 상판: 합판(옆이 아래로 비스듬히 깎임) + 위에 흰 HPM
ply_o = slab('top_ply', W, D, R, H - TOP_T, H - HPM_T, UNDER)
box_uv(ply_o, 'x', (.1, .1)); ply_o.data.materials.append(PLY)
hpm_o = slab('top_hpm', W, D, R, H - HPM_T, H)
box_uv(hpm_o, 'x'); hpm_o.data.materials.append(HPM)


def box(name, sx, sy, sz, cx, cy, cz, grain):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(cx, cy, cz))
    o = bpy.context.object; o.name = name; o.scale = (sx, sy, sz)
    bpy.ops.object.transform_apply(location=False, scale=True)
    bevel(o, .002, 2); box_uv(o, grain); o.data.materials.append(WOOD); return o


# 테두리: 다리 윗면 바깥과 맞춘다
AW, AD = 2 * TOP_X + LEG_T, 2 * TOP_Y + LEG_T
az = H - TOP_T - AH / 2
for s in (-1, 1):
    box(f'apron_long{s}', AW - 2 * LEG_T, AT, AH, 0, s * (AD / 2 - AT / 2), az, 'x')
    box(f'apron_short{s}', AT, AD - 2 * LEG_T, AH, s * (AW / 2 - AT / 2), 0, az, 'y')

# 다리: 위 굵게 → 바닥 가늘게, 바깥으로 벌어짐. 윗면·바닥면은 수평
for sx in (-1, 1):
    for sy in (-1, 1):
        ct = (sx * TOP_X, sy * TOP_Y, H - TOP_T)
        cb = (sx * FOOT_X, sy * FOOT_Y, 0)
        bm = bmesh.new()
        sq = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
        bot = [bm.verts.new((cb[0] + a * LEG_B / 2, cb[1] + c * LEG_B / 2, cb[2])) for a, c in sq]
        tp = [bm.verts.new((ct[0] + a * LEG_T / 2, ct[1] + c * LEG_T / 2, ct[2])) for a, c in sq]
        bm.faces.new(bot[::-1]); bm.faces.new(tp)
        for i in range(4): bm.faces.new([bot[i], bot[(i + 1) % 4], tp[(i + 1) % 4], tp[i]])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        leg = new_obj(f'leg{sx}{sy}', bm); bevel(leg, .007, 3); box_uv(leg, 'z'); leg.data.materials.append(WOOD)

for o in scene.objects:
    for p in o.data.polygons: p.use_smooth = False
bpy.ops.object.select_all(action='SELECT')
bpy.context.view_layer.objects.active = scene.objects['top_hpm']
bpy.ops.object.join()
o = bpy.context.object; o.name = 'table_bome_1200'
xs = [v.co for v in o.data.vertices]
print('bbox mm', *[round((max(c[i] for c in xs) - min(c[i] for c in xs)) * 1000) for i in range(3)])
print('faces', len(o.data.polygons))
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', export_image_format='JPEG',
                          export_jpeg_quality=85, export_apply=True, export_yup=True)
print('saved', OUT, os.path.getsize(OUT) // 1024, 'KB')
