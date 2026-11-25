"""이동식 TV 3D 모델: 와이드뷰 '와이드무빙뷰' 32인치 스마트 TV + 이동식 스탠드 (화이트 에디션).

    "C:/Program Files/Blender Foundation/Blender 5.3/blender.exe" -b -P tools/make_tvstand.py

치수 (판매처 표기 + 사진 비율로 추정):
  스탠드: 원판 받침 지름 400mm(아래 바퀴 5개), 기둥 지름 40mm, 높이 948~1148 → 화면 가운데 1050mm로 둠
  TV: 32인치 16:9 화면 708×398 + 테두리 → 본체 724×432×72mm, 앞은 검은 유리, 옆·뒤는 흰색
좌표: 바닥 가운데(받침 중심) = 원점, 단위 m. 앞(화면) = three.js +z = Blender -Y.
가구 자리(바닥 차지)는 받침 400×400이고 화면은 그 위로 넓게 나간다.
결과: docs/models/tv_widevu_32_white.glb
"""
import bpy, math, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'docs', 'models', 'tv_widevu_32_white.glb')

BASE_R, BASE_T, CASTER_H = .200, .028, .038
POLE_R = .020
CENTER = 1.050                       # 화면 가운데 높이
TV_W, TV_H, TV_D = .724, .432, .072
SCR_W, SCR_H = .708, .398

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


def material(name, color, rough=.4, metal=0., coat=0.):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    if coat: b.inputs['Coat Weight'].default_value = coat
    return m


M_WHITE = material('white_paint', (.9, .9, .89), rough=.3, coat=.3)
M_SCREEN = material('screen_glass', (.012, .013, .016), rough=.06, coat=1.)
M_BEZEL = material('bezel_black', (.02, .02, .022), rough=.4)
M_RUBBER = material('caster_rubber', (.05, .05, .05), rough=.8)


def cyl(name, r, h, z, mat, verts=48, x=0, y=0, rot=None):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=h, location=(x, y, z), rotation=rot or (0, 0, 0))
    o = bpy.context.object; o.name = name; o.data.materials.append(mat)
    for p in o.data.polygons: p.use_smooth = True
    return o


def box(name, sx, sy, sz, cx, cy, cz, mat, bevel=0.):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(cx, cy, cz))
    o = bpy.context.object; o.name = name; o.scale = (sx, sy, sz)
    bpy.ops.object.transform_apply(scale=True)
    if bevel:
        bv = o.modifiers.new('bev', 'BEVEL'); bv.width = bevel; bv.segments = 3
        bpy.ops.object.modifier_apply(modifier='bev')
    o.data.materials.append(mat)
    return o


# 받침: 둥근 원판 (가장자리 둥글게) + 아래 바퀴 5개
base = cyl('base', BASE_R, BASE_T, CASTER_H + BASE_T / 2, M_WHITE, verts=72)
bv = base.modifiers.new('bev', 'BEVEL'); bv.width = .008; bv.segments = 4
bpy.context.view_layer.objects.active = base; bpy.ops.object.modifier_apply(modifier='bev')
for i in range(5):
    a = math.radians(90 + i * 72)
    cyl(f'caster{i}', .018, .024, .018, M_RUBBER, verts=24, x=math.cos(a) * BASE_R * .72, y=math.sin(a) * BASE_R * .72, rot=(math.pi / 2, 0, a))
    cyl(f'caster_cap{i}', .022, .016, CASTER_H - .006, M_RUBBER, verts=24, x=math.cos(a) * BASE_R * .72, y=math.sin(a) * BASE_R * .72)
# 기둥 + 위 받침목
top = CENTER - .06
cyl('pole', POLE_R, top - CASTER_H - BASE_T, (CASTER_H + BASE_T + top) / 2, M_WHITE, verts=32)
box('mount', .12, .05, .16, 0, TV_D / 2 + .02, CENTER, M_WHITE, bevel=.006)
# TV 본체: 흰 몸통 + 앞 검은 유리 + 아래 흰 턱
yf = -TV_D / 2
box('tv_body', TV_W, TV_D - .004, TV_H, 0, .002, CENTER, M_WHITE, bevel=.006)
box('tv_front', TV_W - .004, .004, TV_H - .022, 0, yf + .001, CENTER + .009, M_BEZEL, bevel=.002)
box('tv_screen', SCR_W, .002, SCR_H, 0, yf - .0012, CENTER + .012, M_SCREEN)

bpy.ops.object.select_all(action='SELECT')
bpy.context.view_layer.objects.active = scene.objects['base']
bpy.ops.object.join()
o = bpy.context.object; o.name = 'tv_widevu_32_white'
for p in o.data.polygons:
    pass
print('faces', len(o.data.polygons), 'top', CENTER + TV_H / 2)
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', export_apply=True, export_yup=True)
print('saved', OUT, os.path.getsize(OUT) // 1024, 'KB')
