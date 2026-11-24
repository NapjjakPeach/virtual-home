"""침대 헤드 선반 3D 모델: 우드레이 '루이 저상형 침대헤드 겸 틈새수납장' 850 (메이플).

    python tools/make_bed_tex.py maple      (질감 먼저)
    "C:/Program Files/Blender Foundation/Blender 5.3/blender.exe" -b -P tools/make_headshelf.py

치수 (mm, 판매처 문의 답변 기준): 가로 850 × 깊이 150 × 높이 480, 판 두께 15 (안쪽 폭 = 가로 - 30),
선반 윗면 높이 약 420, 그 위로 테두리가 60mm 올라온 트레이, 뒤쪽은 선반 아래가 뚫려 있음(전선용),
선반 한쪽 끝에 둥근 전선 구멍.
좌표: 바닥 가운데 = 원점, 단위 m. 앞(침대 쪽) = three.js +z = Blender -Y.
결과: docs/models/head_louis_850_maple.glb
"""
import bpy, bmesh, math, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEX = os.path.join(ROOT, 'bake', 'bed_tex')
OUT = os.path.join(ROOT, 'docs', 'models', 'head_louis_850_maple.glb')

W, D, H, T = .850, .150, .480, .015
SHELF_TOP = .420

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


def material(name, diff=None, nor=None, color=(1, 1, 1), rough=.6, nstr=.5):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    b.inputs['Roughness'].default_value = rough
    b.inputs['Base Color'].default_value = (*color, 1)
    if diff:
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(os.path.join(TEX, diff))
        nt.links.new(t.outputs['Color'], b.inputs['Base Color'])
    if nor:
        im = bpy.data.images.load(os.path.join(TEX, nor)); im.colorspace_settings.name = 'Non-Color'
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = im
        n = nt.nodes.new('ShaderNodeNormalMap'); n.inputs['Strength'].default_value = nstr
        nt.links.new(t.outputs['Color'], n.inputs['Color']); nt.links.new(n.outputs['Normal'], b.inputs['Normal'])
    return m


M_WOOD = material('maple', 'maple_diff.png', 'maple_nor.png', rough=.5)
M_EDGE = material('maple_edge', 'maple_diff.png', None, color=(.93, .88, .8), rough=.55)   # 판 옆면(마감 띠)은 살짝 밝게
M_HOLE = material('hole_dark', color=(.03, .03, .03), rough=.9)
M_RING = material('grommet', color=(.85, .83, .79), rough=.45)


def board(name, sx, sy, sz, cx, cy, cz):
    """판 하나: 살짝 둥근 모서리 + 상자 투영 UV (결은 긴 쪽 방향). 넓은 면 = 무늬, 좁은 면 = 마감 띠"""
    bpy.ops.mesh.primitive_cube_add(size=1, location=(cx, cy, cz))
    o = bpy.context.object; o.name = name; o.scale = (sx, sy, sz)
    bpy.ops.object.transform_apply(scale=True)
    bev = o.modifiers.new('bev', 'BEVEL'); bev.width = .0015; bev.segments = 2
    bpy.ops.object.modifier_apply(modifier='bev')
    me = o.data
    while me.uv_layers: me.uv_layers.remove(me.uv_layers[0])
    uv = me.uv_layers.new(name='UVMap')
    me.materials.append(M_WOOD); me.materials.append(M_EDGE)
    thin = min(sx, sy, sz)
    for p in me.polygons:
        n = [abs(c) for c in p.normal]
        ax = n.index(max(n))                       # 면이 향하는 축
        dims = [sx, sy, sz]; dims[ax] = 0
        p.material_index = 1 if (sx, sy, sz)[ax] != thin else 0   # 판 두께 쪽 면 = 마감 띠
        for li in p.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            a = [co.x, co.y, co.z]; a.pop(ax)
            uv.data[li].uv = (a[0] / .5, a[1] / .5) if ax != 0 else (a[0] / .5, a[1] / .5)
    for p in me.polygons: p.use_smooth = False
    return o


y_front, y_back = -D / 2, D / 2
board('front', W, T, H, 0, y_front + T / 2, H / 2)                                   # 침대 쪽 앞판 (전체 높이)
for s in (-1, 1):
    board(f'side{s}', T, D - T, H, s * (W / 2 - T / 2), (D - T) / 2 - D / 2 + T, H / 2)   # 옆판
board('shelf', W - 2 * T, D - T, T, 0, T / 2, SHELF_TOP - T / 2)                      # 선반
board('rim_back', W - 2 * T, T, H - SHELF_TOP, 0, y_back - T / 2, (H + SHELF_TOP) / 2)   # 선반 위 뒤쪽 테두리
board('rail_back', W - 2 * T, T, .06, 0, y_back - T / 2, SHELF_TOP - T - .03)         # 선반 아래 뒤 보강대 (아래는 뚫림)

# 전선 구멍: 선반 한쪽 끝, 밝은 고리 + 안쪽 어둠
hx, hy = W / 2 - T - .07, T / 2
bpy.ops.mesh.primitive_cylinder_add(vertices=40, radius=.028, depth=.003, location=(hx, hy, SHELF_TOP + .0012))
r = bpy.context.object; r.name = 'grommet'; r.data.materials.append(M_RING)
bpy.ops.mesh.primitive_cylinder_add(vertices=40, radius=.021, depth=.003, location=(hx, hy, SHELF_TOP + .0022))
h = bpy.context.object; h.name = 'hole'; h.data.materials.append(M_HOLE)

for ob in scene.objects:
    if ob.type == 'MESH':
        if not ob.data.uv_layers: ob.data.uv_layers.new(name='UVMap')
        for extra in list(ob.data.uv_layers)[1:]: ob.data.uv_layers.remove(extra)
        ob.data.uv_layers[0].name = 'UVMap'
bpy.ops.object.select_all(action='SELECT')
bpy.context.view_layer.objects.active = scene.objects['front']
bpy.ops.object.join()
o = bpy.context.object; o.name = 'head_louis_850_maple'
print('faces', len(o.data.polygons))
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', export_image_format='JPEG',
                          export_jpeg_quality=85, export_apply=True, export_yup=True)
print('saved', OUT, os.path.getsize(OUT) // 1024, 'KB')
