"""식탁 3D 모델: 한샘 포레 원목 4인 식탁 (1200 × 750 × 760).

    python tools/make_bed_tex.py fore      (원목 질감 먼저)
    "C:/Program Files/Blender Foundation/Blender 5.3/blender.exe" -b -P tools/make_table_fore.py

치수 (mm, 상품 상세 치수도): 상판 1200 × 750, 높이 760, 상판 아래 테두리(앞 930 · 옆 465) 아래 끝 높이 675,
다리는 밖으로 벌어져 바닥에서 바깥 1158 × 692. 상판 긴 변이 아주 살짝 볼록하고 모서리가 둥글다.
좌표: 바닥 가운데 = 원점, 단위 m. 앞 = three.js +z = Blender -Y, 긴 변 = x.
결과: docs/models/table_fore_1200.glb
"""
import bpy, bmesh, math, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEX = os.path.join(ROOT, 'bake', 'bed_tex')
OUT = os.path.join(ROOT, 'docs', 'models', 'table_fore_1200.glb')

W, D, H = 1.2, .75, .76
TOP_T = .025                      # 상판 두께
BOW = .008                        # 긴 변 가운데가 볼록한 정도
AW, AD, AH, AT = .93, .465, .06, .02   # 테두리(에이프런) 바깥 가로·세로, 높이, 두께
LEG_T, LEG_B = .045, .03          # 다리 굵기 (위·아래)
FOOT_X, FOOT_Y = 1.158 / 2 - LEG_B / 2, .692 / 2 - LEG_B / 2   # 바닥에서 다리 가운데

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

m = bpy.data.materials.new('wood_fore'); m.use_nodes = True
nt = m.node_tree; b = nt.nodes['Principled BSDF']
b.inputs['Roughness'].default_value = .45
t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(os.path.join(TEX, 'fore_diff.png'))
nt.links.new(t.outputs['Color'], b.inputs['Base Color'])
im = bpy.data.images.load(os.path.join(TEX, 'fore_nor.png')); im.colorspace_settings.name = 'Non-Color'
tn = nt.nodes.new('ShaderNodeTexImage'); tn.image = im
nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = .5
nt.links.new(tn.outputs['Color'], nm.inputs['Color']); nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])
WOOD = m


def wood_uv(o, grain):
    """상자 투영 UV. 질감의 결(v)이 grain 축('x' 또는 'z')을 따르게. 질감 한 장 = 0.5 m × 1.0 m"""
    me = o.data
    while me.uv_layers: me.uv_layers.remove(me.uv_layers[0])
    uv = me.uv_layers.new(name='UVMap')
    for p in me.polygons:
        n = [abs(c) for c in p.normal]; ax = n.index(max(n))
        for li in p.loop_indices:
            co = o.matrix_world @ me.vertices[me.loops[li].vertex_index].co
            if grain == 'x':      # 결이 가로(긴 변) 방향
                a, bb = (co.y, co.x) if ax == 2 else (co.z, co.x) if ax == 1 else (co.z, co.y)
            else:                 # 결이 세로(다리) 방향
                a, bb = (co.x, co.z) if ax == 1 else (co.y, co.z) if ax == 0 else (co.x, co.y)
            uv.data[li].uv = (a / .5, bb / 1.0)
    me.materials.append(WOOD)


def bevel(o, w, seg=3):
    bv = o.modifiers.new('bev', 'BEVEL'); bv.width = w; bv.segments = seg; bv.limit_method = 'ANGLE'
    bpy.context.view_layer.objects.active = o; bpy.ops.object.modifier_apply(modifier='bev')


def new_obj(name, bm):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); scene.collection.objects.link(o); return o


# 상판: 긴 변이 살짝 볼록한 윤곽을 위로 밀어 올린다
bm = bmesh.new()
pts = []
N = 24
for i in range(N + 1):                                    # 앞 변 (y = -D/2, 가운데가 앞으로 볼록)
    x = -W / 2 + W * i / N; pts.append((x, -D / 2 - BOW * math.cos(math.pi * x / W)))
for i in range(N + 1):                                    # 뒤 변
    x = W / 2 - W * i / N; pts.append((x, D / 2 + BOW * math.cos(math.pi * x / W)))
vs = [bm.verts.new((x, y, H - TOP_T)) for x, y in pts]
f = bm.faces.new(vs)
ext = bmesh.ops.extrude_face_region(bm, geom=[f])
for v in [e for e in ext['geom'] if isinstance(e, bmesh.types.BMVert)]: v.co.z += TOP_T
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
top = new_obj('top', bm); bevel(top, .004); wood_uv(top, 'x')

# 테두리(에이프런) 네 쪽
def box(name, sx, sy, sz, cx, cy, cz, grain):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(cx, cy, cz))
    o = bpy.context.object; o.name = name; o.scale = (sx, sy, sz)
    bpy.ops.object.transform_apply(location=False, scale=True)
    bevel(o, .002, 2); wood_uv(o, grain); return o

az = H - TOP_T - AH / 2
for s in (-1, 1):
    box(f'apron_long{s}', AW - 2 * LEG_T, AT, AH, 0, s * (AD / 2 - AT / 2), az, 'x')
    box(f'apron_short{s}', AT, AD - 2 * LEG_T, AH, s * (AW / 2 - AT / 2), 0, az, 'x')

# 다리: 위(테두리 모서리 안쪽) 굵게 → 바닥(바깥으로 벌어짐) 가늘게. 윗면·바닥면은 수평
for sx in (-1, 1):
    for sy in (-1, 1):
        ct = (sx * (AW / 2 - LEG_T / 2), sy * (AD / 2 - LEG_T / 2), H - TOP_T)
        cb = (sx * FOOT_X, sy * FOOT_Y, 0)
        bm = bmesh.new()
        sq = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
        bot = [bm.verts.new((cb[0] + a * LEG_B / 2, cb[1] + c * LEG_B / 2, cb[2])) for a, c in sq]
        tp = [bm.verts.new((ct[0] + a * LEG_T / 2, ct[1] + c * LEG_T / 2, ct[2])) for a, c in sq]
        bm.faces.new(bot[::-1]); bm.faces.new(tp)
        for i in range(4): bm.faces.new([bot[i], bot[(i + 1) % 4], tp[(i + 1) % 4], tp[i]])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        leg = new_obj(f'leg{sx}{sy}', bm); bevel(leg, .005, 3); wood_uv(leg, 'z')

for o in scene.objects:
    for p in o.data.polygons: p.use_smooth = False
bpy.ops.object.select_all(action='SELECT')
bpy.context.view_layer.objects.active = scene.objects['top']
bpy.ops.object.join()
o = bpy.context.object; o.name = 'table_fore_1200'
print('faces', len(o.data.polygons))
bpy.ops.export_scene.gltf(filepath=OUT, export_format='GLB', export_image_format='JPEG',
                          export_jpeg_quality=85, export_apply=True, export_yup=True)
print('saved', OUT, os.path.getsize(OUT) // 1024, 'KB')
