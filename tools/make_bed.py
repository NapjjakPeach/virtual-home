"""방 2 침대 3D 모델: 삼익 로우브 저상형 깔판 평상형 LK (오크) + 에이스 벨루체 K 원매트리스.

    python tools/make_bed_tex.py      (질감 먼저)
    "C:/Program Files/Blender Foundation/Blender 5.3/blender.exe" -b -P tools/make_bed.py

치수 (mm, 제품 표기):
  프레임  1800 × 2100 × 100  (윗판 40 + 안쪽으로 들어간 받침 60)
  매트리스 1670 × 2075 × 360  (옆면 270 + 필로우탑 90), 프레임 가운데에 놓임
좌표: 바닥 가운데 = 원점, 단위 m. Blender +Y(= three.js -z)가 머리 쪽.
결과: docs/models/bed_lowb_velluce_k.glb
"""
import bpy, bmesh, math, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEX = os.path.join(ROOT, 'bake', 'bed_tex')
OUT = os.path.join(ROOT, 'docs', 'models', 'bed_lowb_velluce_k.glb')
os.makedirs(os.path.dirname(OUT), exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

FW, FD, FH = 1.800, 2.100, 0.100          # 프레임
TOP_T = 0.040                             # 윗판 두께
INSET = 0.045                             # 받침이 안쪽으로 들어간 정도
MW, MD = 1.670, 2.075                     # 매트리스
BODY_H, PT_H = 0.270, 0.090               # 옆면 / 필로우탑
R_BODY, R_PT = 0.055, 0.070               # 평면 모서리 반지름


# ---------------- 재질 ----------------
def img(name, color=True):
    im = bpy.data.images.load(os.path.join(TEX, name), check_existing=True)
    if not color: im.colorspace_settings.name = 'Non-Color'
    return im


def material(name, diff=None, nor=None, color=(1, 1, 1), rough=.8, metal=0., nstr=1.):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    b.inputs['Base Color'].default_value = (*color, 1)
    if diff:
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = img(diff)
        nt.links.new(t.outputs['Color'], b.inputs['Base Color'])
    if nor:
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = img(nor, False)
        n = nt.nodes.new('ShaderNodeNormalMap'); n.inputs['Strength'].default_value = nstr
        nt.links.new(t.outputs['Color'], n.inputs['Color']); nt.links.new(n.outputs['Normal'], b.inputs['Normal'])
    return m


M_OAK = material('oak', 'oak_diff.png', 'oak_nor.png', rough=.55, nstr=.6)
M_OAK_DARK = material('oak_under', 'oak_diff.png', None, color=(.55, .5, .45), rough=.7)
M_TOP = material('fabric_top', 'quilt_diff.png', 'quilt_nor.png', rough=.9)
M_SIDE = material('fabric_side', 'wave_diff.png', 'wave_nor.png', rough=.88)
M_BAND = material('fabric_band', 'band_diff.png', 'band_nor.png', rough=.88)
M_PIPE = material('piping', color=(.86, .83, .77), rough=.75)
M_GOLD = material('vent_gold', color=(.78, .6, .3), rough=.35, metal=1.)


def obj_from_bm(bm, name, mats):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    for m in mats: me.materials.append(m)
    o = bpy.data.objects.new(name, me); scene.collection.objects.link(o)
    for p in me.polygons: p.use_smooth = True
    return o


# ---------------- 둥근 직사각형 둘레 ----------------
def rr_points(w, d, r, seg=10):
    """둥근 직사각형 둘레 점 (반시계), 각 점의 둘레 거리도 함께"""
    hw, hd = w / 2 - r, d / 2 - r
    pts = []
    for cx, cy, a0 in [(hw, hd, 0), (-hw, hd, 90), (-hw, -hd, 180), (hw, -hd, 270)]:
        for i in range(seg + 1):
            a = math.radians(a0 + 90 * i / seg)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    s = [0.]
    for i in range(1, len(pts)): s.append(s[-1] + math.dist(pts[i - 1], pts[i]))
    s.append(s[-1] + math.dist(pts[-1], pts[0]))   # 닫는 길이
    return pts, s


def rr_prism(name, w, d, r, z0, profile, side_mat, side_u, side_v, top_mat=None, top_uv=None, cap_bottom=True, seg=10):
    """둥근 직사각형 기둥. profile = [(높이, 안쪽으로 들어간 거리)] 아래→위.
    옆면 UV: u = 둘레 거리 / side_u (m), v = (높이) / side_v. 윗면 UV: (x, y) / top_uv"""
    bm = bmesh.new(); uvl = bm.loops.layers.uv.new('UVMap')
    rings = []
    for (h, ins) in profile:
        pts, s = rr_points(w - 2 * ins, d - 2 * ins, max(.005, r - ins), seg)
        rings.append(([bm.verts.new((x, y, z0 + h)) for x, y in pts], s, h))
    n = len(rings[0][0])
    for k in range(len(rings) - 1):
        (A, sA, hA), (B, sB, hB) = rings[k], rings[k + 1]
        for i in range(n):
            j = (i + 1) % n
            f = bm.faces.new((A[i], A[j], B[j], B[i])); f.material_index = 0
            s0 = sA[i]; s1 = sA[i + 1] if j else sA[-1]
            for lp, (ss, hh) in zip(f.loops, [(s0, hA), (s1, hA), (s1, hB), (s0, hB)]):
                lp[uvl].uv = (ss / side_u, hh / side_v)
    top = bm.faces.new(rings[-1][0]); top.material_index = 1 if top_mat else 0
    for lp in top.loops: lp[uvl].uv = (lp.vert.co.x / (top_uv or 1), lp.vert.co.y / (top_uv or 1))
    if cap_bottom:
        bot = bm.faces.new(list(reversed(rings[0][0]))); bot.material_index = 0
    bm.normal_update()
    return obj_from_bm(bm, name, [side_mat] + ([top_mat] if top_mat else []))


def tube_along(name, w, d, r, z, radius, mat, seg=10):
    """둘레를 따라가는 파이핑(가는 관)"""
    pts, _ = rr_points(w, d, r, seg)
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'
    sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
    for p, (x, y) in zip(sp.points, pts): p.co = (x, y, z, 1)
    sp.use_cyclic_u = True
    cu.bevel_depth = radius; cu.bevel_resolution = 3
    o = bpy.data.objects.new(name, cu); scene.collection.objects.link(o)
    o.data.materials.append(mat)
    bpy.context.view_layer.objects.active = o; o.select_set(True)
    bpy.ops.object.convert(target='MESH'); o.select_set(False)
    o.data.uv_layers.new(name='UVMap')   # 합칠 때 UV가 한 벌이 되도록
    return o


def box_uv(o, scale_u, scale_v):
    """상자 투영 UV (나뭇결은 길이 방향 = Y)"""
    me = o.data
    while me.uv_layers: me.uv_layers.remove(me.uv_layers[0])
    uv = me.uv_layers.new(name='UVMap')
    for p in me.polygons:
        nx, ny, nz = (abs(c) for c in p.normal)
        for li in p.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            if nz >= max(nx, ny): u, v = co.x, co.y
            elif nx >= ny: u, v = co.z, co.y
            else: u, v = co.x, co.z
            uv.data[li].uv = (u / scale_u, v / scale_v)


# ---------------- 프레임 ----------------
bpy.ops.mesh.primitive_cube_add(size=1)
deck = bpy.context.object; deck.name = 'frame_top'
deck.scale = (FW, FD, TOP_T); deck.location = (0, 0, FH - TOP_T / 2)
bpy.ops.object.transform_apply(scale=True)
bev = deck.modifiers.new('bev', 'BEVEL'); bev.width = .004; bev.segments = 3
bpy.ops.object.modifier_apply(modifier='bev')
deck.data.materials.append(M_OAK); box_uv(deck, .5, 1.0)
bpy.ops.object.shade_auto_smooth() if hasattr(bpy.ops.object, 'shade_auto_smooth') else None

bpy.ops.mesh.primitive_cube_add(size=1)
base = bpy.context.object; base.name = 'frame_base'
base.scale = (FW - 2 * INSET, FD - 2 * INSET, FH - TOP_T); base.location = (0, 0, (FH - TOP_T) / 2)
bpy.ops.object.transform_apply(scale=True)
base.data.materials.append(M_OAK_DARK); box_uv(base, .5, 1.0)

# ---------------- 매트리스 ----------------
z_body = FH
# 옆면: 위아래 모서리를 살짝 둥글게
rr_prism('mattress_body', MW, MD, R_BODY, z_body,
         [(0, .008), (.006, .0015), (.014, 0), (BODY_H - .014, 0), (BODY_H - .006, .0015), (BODY_H, .008)],
         M_SIDE, .24, BODY_H, cap_bottom=True)
# 필로우탑: 아래가 조금 들어가고 위쪽이 부풀었다가 둥글게 덮이는 모양
z_pt = z_body + BODY_H
rr_prism('mattress_pillowtop', MW - .012, MD - .012, R_PT, z_pt,
         [(0, .010), (.010, .002), (.030, 0), (.060, 0), (.076, .008), (.085, .022), (PT_H, .040)],
         M_BAND, .12, PT_H, top_mat=M_TOP, top_uv=.36, cap_bottom=False)
# 파이핑: 옆면 위·아래, 필로우탑 윗선
tube_along('pipe_low', MW - .004, MD - .004, R_BODY, z_body + .010, .0055, M_PIPE)
tube_along('pipe_mid', MW - .004, MD - .004, R_BODY, z_pt - .004, .0055, M_PIPE)
tube_along('pipe_top', MW - .012 - .044, MD - .012 - .044, R_PT - .022, z_pt + PT_H - .012, .005, M_PIPE)
# 공기 구멍 (금색 고리) : 긴 옆면마다 가운데쯤에 8개
for side in (-1, 1):
    for i in range(8):
        y = -.42 + i * .12
        bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=.0075, depth=.004,
                                            location=(side * (MW / 2 + .0015), y, z_body + BODY_H * .52),
                                            rotation=(0, math.pi / 2, 0))
        v = bpy.context.object; v.name = f'vent_{side}_{i}'; v.data.materials.append(M_GOLD)

# ---------------- 합치고 내보내기 ----------------
for ob in scene.objects:   # UV는 이름이 같은 한 벌만 (다르면 합칠 때 여러 벌로 갈라짐)
    if ob.type == 'MESH' and ob.data.uv_layers:
        for extra in list(ob.data.uv_layers)[1:]: ob.data.uv_layers.remove(extra)
        ob.data.uv_layers[0].name = 'UVMap'
bpy.ops.object.select_all(action='SELECT')
bpy.context.view_layer.objects.active = deck
bpy.ops.object.join()
o = bpy.context.object; o.name = 'bed_lowb_velluce_k'
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
print('faces', len(o.data.polygons), 'verts', len(o.data.vertices))
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', export_image_format='JPEG',
                          export_jpeg_quality=85, export_apply=True, export_yup=True)
print('saved', OUT, os.path.getsize(OUT) // 1024, 'KB')
