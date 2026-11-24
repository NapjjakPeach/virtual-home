"""냉장고 3D 모델: 캐리어 312L 2도어 콤비냉장고 KRNC312WPM1 (화이트, 상냉장·하냉동).

    "C:/Program Files/Blender Foundation/Blender 5.3/blender.exe" -b -P tools/make_fridge_312.py

치수 (mm, 제품 표기): 가로 595 × 높이 1855 × 깊이 635.
생김새(쿠팡 상품 사진): 평평한 흰색 메탈 문 두 짝(위 냉장 약 57%, 아래 냉동), 앞에 디스플레이 없음,
두 문 사이 가로로 긴 회색 홈 손잡이(너비의 약 70%, 가운데), 위 문 오른쪽 위 작은 회색 로고,
옆판도 흰색, 아래 짧은 다리와 어두운 받침 틈.
좌표: 바닥 가운데 = 원점, 단위 m. 앞(문) = three.js +z = Blender -Y.
결과: docs/models/fridge_carrier_312w.glb
"""
import bpy, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'docs', 'models', 'fridge_carrier_312w.glb')

W, H, D = .595, 1.855, .635
DOOR_T = .042                    # 문 두께
BODY_D = D - DOOR_T
BASE = .038                      # 아래 받침(다리) 높이
SPLIT = .80                      # 냉동실 문 윗면 높이 (사진: 냉동 문이 전체의 약 43%)
GAP = .004                       # 문 사이 틈
HW = W * .70                     # 홈 손잡이 너비

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


def material(name, color, rough=.5, metal=0.):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    return m


# 색은 선형값 (흰 문 ≈ sRGB #f3f2ef)
M_DOOR = material('white_door', (.90, .885, .86), rough=.2)            # 광택 있는 흰색 도장 메탈
M_SIDE = material('white_side', (.87, .86, .84), rough=.3)
M_GROOVE = material('handle_groove', (.10, .105, .11), rough=.55)      # 손 넣는 홈 안쪽
M_HANDLE = material('handle_gray', (.42, .43, .44), rough=.35, metal=.3)   # 회색 손잡이 띠
M_DARK = material('dark', (.025, .025, .028), rough=.6)
M_FOOT = material('foot', (.30, .30, .31), rough=.5)
M_LOGO = material('logo', (.35, .36, .38), rough=.4)


def box(name, sx, sy, sz, cx, cy, cz, mat, bevel=0.):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(cx, cy, cz))
    o = bpy.context.object; o.name = name; o.scale = (sx, sy, sz)
    bpy.ops.object.transform_apply(scale=True)
    if bevel:
        bv = o.modifiers.new('bev', 'BEVEL'); bv.width = bevel; bv.segments = 3
        bpy.ops.object.modifier_apply(modifier='bev')
    o.data.materials.append(mat)
    return o


yf = -D / 2                                        # 앞 (문 바깥면)
yb = yf + DOOR_T                                   # 몸통 앞면
box('body', W, BODY_D, H - BASE, 0, yb + BODY_D / 2, BASE + (H - BASE) / 2, M_SIDE, bevel=.006)
box('base', W - .05, BODY_D - .03, BASE, 0, yb + BODY_D / 2 + .015, BASE / 2, M_DARK)        # 아래 그늘 틈
for sx in (-1, 1):                                                                               # 앞 다리
    box(f'foot{sx}', .045, .04, BASE, sx * (W / 2 - .045), yf + .05, BASE / 2, M_FOOT, bevel=.004)
# 냉동(아래) 문: 윗부분에 손 넣는 홈 (가운데, 너비 70%)
fz0, fz1 = BASE + .004, SPLIT
box('door_freezer', W - .004, DOOR_T, fz1 - fz0, 0, yf + DOOR_T / 2, (fz0 + fz1) / 2, M_DOOR, bevel=.005)
box('handle_groove', HW, DOOR_T * .55, .026, 0, yf + DOOR_T * .55 / 2 - .001, fz1 - .012, M_GROOVE)
box('handle_strip', HW, .006, .012, 0, yf - .0015, fz1 - .03, M_HANDLE, bevel=.002)              # 홈 아래 회색 띠
# 냉장(위) 문
rz0, rz1 = SPLIT + GAP, H - .004
box('door_fridge', W - .004, DOOR_T, rz1 - rz0, 0, yf + DOOR_T / 2, (rz0 + rz1) / 2, M_DOOR, bevel=.005)
box('fridge_lip', HW, .004, .008, 0, yf - .001, rz0 + .006, M_HANDLE, bevel=.0015)              # 위 문 아래 손잡이 테
# 작은 로고 (위 문 오른쪽 위)
box('logo', .06, .0015, .009, W / 2 - .075, yf - .0008, H - .045, M_LOGO)
# 위 경첩 덮개 (흰색, 오른쪽)
box('hinge_top', .05, .03, .01, W / 2 - .04, yf + .02, H - .001, M_SIDE, bevel=.003)

bpy.ops.object.select_all(action='SELECT')
bpy.context.view_layer.objects.active = scene.objects['body']
bpy.ops.object.join()
o = bpy.context.object; o.name = 'fridge_carrier_312w'
for p in o.data.polygons: p.use_smooth = False
print('faces', len(o.data.polygons))
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', export_apply=True, export_yup=True)
print('saved', OUT, os.path.getsize(OUT) // 1024, 'KB')
