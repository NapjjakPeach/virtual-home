"""냉장고 3D 모델: 캐리어 클라윈드 피트인 302L KRNC302SEI1 (실버 메탈, 상냉장·하냉동 2도어).

    python tools/make_bed_tex.py steel      (질감 먼저)
    "C:/Program Files/Blender Foundation/Blender 5.3/blender.exe" -b -P tools/make_fridge.py

치수 (mm, 제품 표기): 가로 595 × 높이 1880 × 깊이 630.
생김새(제품 사진): 헤어라인 메탈 문 두 짝(위 냉장 약 62%, 아래 냉동), 두 문 사이 손을 넣는 홈 손잡이,
위 문 왼쪽 위에 검은 디스플레이, 옆판은 회색 도장, 위 오른쪽 경첩 덮개, 아래 받침.
좌표: 바닥 가운데 = 원점, 단위 m. 앞(문) = three.js +z = Blender -Y.
결과: docs/models/fridge_clawind_302.glb
"""
import bpy, math, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEX = os.path.join(ROOT, 'bake', 'bed_tex')
OUT = os.path.join(ROOT, 'docs', 'models', 'fridge_clawind_302.glb')

W, H, D = .595, 1.880, .630
DOOR_T = .045                    # 문 두께
BODY_D = D - DOOR_T
BASE = .045                      # 아래 받침 높이
SPLIT = .705                     # 냉동실 문 윗면 높이 (사진 비율: 냉장 문이 전체의 약 62%)
GAP = .004                       # 문 사이 틈

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


def material(name, diff=None, nor=None, color=(1, 1, 1), rough=.5, metal=0., nstr=.4, emit=None):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    b.inputs['Base Color'].default_value = (*color, 1)
    if emit:
        b.inputs['Emission Color'].default_value = (*emit, 1); b.inputs['Emission Strength'].default_value = 1.0
    if diff:
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(os.path.join(TEX, diff))
        nt.links.new(t.outputs['Color'], b.inputs['Base Color'])
    if nor:
        im = bpy.data.images.load(os.path.join(TEX, nor)); im.colorspace_settings.name = 'Non-Color'
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = im
        n = nt.nodes.new('ShaderNodeNormalMap'); n.inputs['Strength'].default_value = nstr
        nt.links.new(t.outputs['Color'], n.inputs['Color']); nt.links.new(n.outputs['Normal'], b.inputs['Normal'])
    return m


M_DOOR = material('steel_door', 'steel_diff.png', 'steel_nor.png', rough=.32, metal=.75)
M_SIDE = material('side_paint', color=(.62, .64, .65), rough=.45, metal=.3)
M_DARK = material('dark', color=(.025, .025, .028), rough=.6)
M_DISP = material('display', color=(.02, .02, .025), rough=.08, emit=(.0, .0, .0))
M_ICON = material('display_icon', color=(.9, .93, 1.0), rough=.3, emit=(.55, .65, .8))
M_PLAST = material('plastic_gray', color=(.35, .36, .37), rough=.5)


def box(name, sx, sy, sz, cx, cy, cz, mat, bevel=0., uvscale=.3):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(cx, cy, cz))
    o = bpy.context.object; o.name = name; o.scale = (sx, sy, sz)
    bpy.ops.object.transform_apply(scale=True)
    if bevel:
        bv = o.modifiers.new('bev', 'BEVEL'); bv.width = bevel; bv.segments = 3
        bpy.ops.object.modifier_apply(modifier='bev')
    me = o.data
    while me.uv_layers: me.uv_layers.remove(me.uv_layers[0])
    uv = me.uv_layers.new(name='UVMap')
    for p in me.polygons:   # 앞면 기준 상자 투영: 헤어라인이 가로(x) 방향
        n = [abs(c) for c in p.normal]; ax = n.index(max(n))
        for li in p.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            u, v = (co.x, co.z) if ax == 1 else (co.y, co.z) if ax == 0 else (co.x, co.y)
            uv.data[li].uv = (u / uvscale, v / uvscale)
    me.materials.append(mat)
    for p in me.polygons: p.use_smooth = False
    return o


yf = -D / 2                                        # 앞 (문 바깥면)
yb = yf + DOOR_T                                   # 몸통 앞면
box('body', W, BODY_D, H - BASE, 0, yb + BODY_D / 2, BASE + (H - BASE) / 2, M_SIDE, bevel=.006)
box('base', W - .04, BODY_D - .02, BASE, 0, yb + BODY_D / 2 + .01, BASE / 2, M_DARK)                  # 아래 받침 (그늘)
box('kick', W - .02, .012, BASE - .008, 0, yb + .03, BASE / 2, M_PLAST)                                  # 앞 아래 덮개
# 문: 냉장(위) / 냉동(아래). 냉동 문 윗부분은 손 넣는 홈을 위해 깊이 18mm 파여 들어간 띠를 둔다
fz0, fz1 = BASE + .005, SPLIT
box('door_freezer', W - .004, DOOR_T, fz1 - fz0 - .028, 0, yf + DOOR_T / 2, fz0 + (fz1 - fz0 - .028) / 2, M_DOOR, bevel=.005)
box('handle_groove', W - .03, DOOR_T - .018, .028, 0, yf + .018 + (DOOR_T - .018) / 2, fz1 - .014, M_DARK)   # 홈 (안쪽 어둠)
box('groove_lip', W - .004, .008, .006, 0, yf + .004, fz1 - .025, M_DOOR, bevel=.002)                     # 홈 아래 테두리
rz0, rz1 = SPLIT + GAP, H - .006
box('door_fridge', W - .004, DOOR_T, rz1 - rz0, 0, yf + DOOR_T / 2, (rz0 + rz1) / 2, M_DOOR, bevel=.005)
# 디스플레이 (위 문 왼쪽 위, 검은 유리) + 작은 표시등
dx, dz = -W / 2 + .095, H - .15
box('display', .058, .003, .1, dx, yf - .0012, dz, M_DISP, bevel=.003)
for k, zz in enumerate((.028, .0, -.028)):
    box(f'icon{k}', .022, .002, .006, dx, yf - .003, dz + zz, M_ICON)
# 위 경첩 덮개 (오른쪽)
box('hinge_top', .05, .03, .012, W / 2 - .04, yf + .02, H - .002, M_PLAST, bevel=.003)

for ob in scene.objects:
    if ob.type == 'MESH':
        for extra in list(ob.data.uv_layers)[1:]: ob.data.uv_layers.remove(extra)
        if ob.data.uv_layers: ob.data.uv_layers[0].name = 'UVMap'
bpy.ops.object.select_all(action='SELECT')
bpy.context.view_layer.objects.active = scene.objects['body']
bpy.ops.object.join()
o = bpy.context.object; o.name = 'fridge_clawind_302'
print('faces', len(o.data.polygons))
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', export_image_format='JPEG',
                          export_jpeg_quality=85, export_apply=True, export_yup=True)
print('saved', OUT, os.path.getsize(OUT) // 1024, 'KB')
