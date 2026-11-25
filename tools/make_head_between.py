"""침대 헤드 수납장 3D 모델: 라샘 높은 비트윈800 3P세트 (일반2+도어1) IH21119, 화이트.

    "C:/Program Files/Blender Foundation/Blender 5.3/blender.exe" -b -P tools/make_head_between.py

치수 (mm, 상품 정보): 세트 1800 × 150 × 800 = 모듈(600 × 150 × 800) 3개.
생김새(상품 사진): 15 mm 화이트 LPM 판. 맨 위는 위에서 쓰는 얕은 트레이(깊이 약 90, 바닥에 전선 구멍 2개),
앞(침대 쪽) 위에 높이 150 띠, 그 아래 일반형은 중간 선반 하나로 나뉜 열린 칸, 도어형은 손잡이 없는 문 한 짝.
아래 모서리에 작은 금색 조절발. 여기서는 열린 칸·문 쪽이 침대를 보고, 가운데가 도어형.
좌표: 바닥 가운데 = 원점, 단위 m. 앞(침대 쪽) = three.js +z = Blender -Y, 긴 변 = x.
결과: docs/models/head_between800_white.glb
"""
import bpy, math, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'docs', 'models', 'head_between800_white.glb')

MW, D, H = .6, .15, .8          # 모듈 하나
T = .015                        # 판 두께
FOOT = .012                     # 조절발 높이
BAND = .15                      # 앞 위 띠 높이
TRAY_Z = H - .09                # 트레이 바닥 윗면
SHELF_Z = .425                  # 열린 칸 중간 선반 윗면

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


def material(name, color, rough=.5, metal=0.):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    return m


WHITE = material('lpm_white', (.9, .9, .88), rough=.4)
GROM = material('grommet', (.82, .82, .8), rough=.5)
HOLE = material('grommet_slot', (.05, .05, .05), rough=.8)
BRASS = material('foot_brass', (.62, .46, .24), rough=.35, metal=.8)


def box(name, sx, sy, sz, cx, cy, cz, mat=WHITE, bevel=.0012):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(cx, cy, cz))
    o = bpy.context.object; o.name = name; o.scale = (sx, sy, sz)
    bpy.ops.object.transform_apply(scale=True)
    if bevel:
        bv = o.modifiers.new('bev', 'BEVEL'); bv.width = bevel; bv.segments = 2
        bpy.ops.object.modifier_apply(modifier='bev')
    o.data.materials.append(mat)
    for p in o.data.polygons: p.use_smooth = False
    return o


def disc(name, r, h, x, y, z, mat):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=h, location=(x, y, z), vertices=32)
    o = bpy.context.object; o.name = name; o.data.materials.append(mat)
    for p in o.data.polygons: p.use_smooth = True
    return o


yf, yb = -D / 2, D / 2           # 앞(침대 쪽), 뒤(벽 쪽)
iw = MW - 2 * T                  # 안쪽 폭


def module(cx, kind, k):
    zb = FOOT
    for s in (-1, 1):            # 옆판 (바닥 ~ 꼭대기)
        box(f'side{k}{s}', T, D, H - zb, cx + s * (MW / 2 - T / 2), 0, zb + (H - zb) / 2)
    box(f'back{k}', iw, T, H - zb, cx, yb - T / 2, zb + (H - zb) / 2)                       # 뒤판 (벽 쪽, 꼭대기까지)
    box(f'band{k}', iw, T, BAND, cx, yf + T / 2, H - BAND / 2)                              # 앞 위 띠 (침대 쪽)
    box(f'bottom{k}', iw, D - T, T, cx, -T / 2, zb + T / 2)                                 # 바닥판
    box(f'tray{k}', iw, D - 2 * T, T, cx, 0, TRAY_Z - T / 2)                                # 트레이 바닥
    for gx in (-.15, .15):                                                                  # 전선 구멍 마개
        disc(f'grom{k}{gx}', .03, .004, cx + gx, 0, TRAY_Z + .002, GROM)
        disc(f'slot{k}{gx}', .007, .0045, cx + gx, 0, TRAY_Z + .0022, HOLE)
    if kind == 'open':
        box(f'shelf{k}', iw, D - T - .01, T, cx, -T / 2 + .005, SHELF_Z - T / 2)            # 중간 선반 (앞에서 5 mm 들어감)
    else:
        top = H - BAND - .004                                                               # 문: 바닥판 앞 ~ 띠 아래, 둘레 2 mm 틈
        box(f'door{k}', iw - .004, .016, top - (zb + .002), cx, yf + .008, (zb + .002 + top) / 2, bevel=.0015)
        box(f'pull{k}', .12, .006, .004, cx, yf + .003, top - .002, HOLE, bevel=0)          # 문 위 손가락 홈 그늘
    for sx in (-1, 1):                                                                      # 조절발
        for sy in (-1, 1):
            disc(f'foot{k}{sx}{sy}', .011, FOOT, cx + sx * (MW / 2 - .03), sy * (D / 2 - .025), FOOT / 2, BRASS)


for k, (cx, kind) in enumerate(((-MW, 'open'), (0, 'door'), (MW, 'open'))):
    module(cx, kind, k)

bpy.ops.object.select_all(action='SELECT')
bpy.context.view_layer.objects.active = scene.objects['back0']
bpy.ops.object.join()
o = bpy.context.object; o.name = 'head_between800_white'
xs = [v.co for v in o.data.vertices]
print('bbox mm', *[round((max(c[i] for c in xs) - min(c[i] for c in xs)) * 1000) for i in range(3)])
print('faces', len(o.data.polygons))
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', export_apply=True, export_yup=True)
print('saved', OUT, os.path.getsize(OUT) // 1024, 'KB')
