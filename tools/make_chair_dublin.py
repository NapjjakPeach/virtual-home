"""의자 3D 모델: 룸앤홈 더블린 체어 (치즈 코듀로이 · 딥그린 코듀로이).

    python tools/make_bed_tex.py cord      (질감 먼저)
    "C:/Program Files/Blender Foundation/Blender 5.3/blender.exe" -b -P tools/make_chair_dublin.py

치수 (mm, 상품 치수도): 500 × 500 × 800, 좌석 높이 450, 좌석 윗면 430 × 400, 등받이 높이 280,
바닥에서 다리 바깥 400(가로) × 450(세로), 크롬 강관 지름 19.
생김새: 둥근 타원 등받이(쿠션), 두툼한 사각 좌석 쿠션, 크롬 다리.
앞다리는 올라와 좌석 밑에서 뒤로 꺾여 옆 받침대가 되고, 뒷다리는 바닥에서 등받이 뒤까지 한 줄로 올라간다.
좌표: 바닥 가운데 = 원점, 단위 m. 앞(앉는 쪽) = three.js +z = Blender -Y.
결과: docs/models/chair_dublin_cheese.glb, docs/models/chair_dublin_green.glb
"""
import bpy, bmesh, math, os
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEX = os.path.join(ROOT, 'bake', 'bed_tex')

TUBE = .0095                     # 강관 반지름
LX = .19                         # 다리 가운데 x (바깥 400)
SEAT_Z, SEAT_T = .45, .065       # 좌석 윗면 높이, 쿠션 두께
SEAT_W, SEAT_D, SEAT_CY = .44, .41, -.025
RAIL_Z = SEAT_Z - SEAT_T - TUBE  # 옆 받침대 높이
FRONT_Y = -.205                  # 앞다리
BACK_FOOT_Y, BACK_SEAT_Y, BACK_TOP_Y = .25, .205, .235   # 뒷다리: 바닥, 좌석 높이, 위끝
BACK_TOP_Z = .74
BR_W, BR_H, BR_T, BR_CZ = .50, .28, .045, .66            # 등받이


def build(color):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene

    chrome = bpy.data.materials.new('chrome'); chrome.use_nodes = True
    b = chrome.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (.8, .8, .82, 1); b.inputs['Metallic'].default_value = 1.; b.inputs['Roughness'].default_value = .16
    rubber = bpy.data.materials.new('foot_cap'); rubber.use_nodes = True
    rubber.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.03, .03, .03, 1)

    fab = bpy.data.materials.new(f'cord_{color}'); fab.use_nodes = True
    nt = fab.node_tree; b = nt.nodes['Principled BSDF']
    b.inputs['Roughness'].default_value = .88
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(os.path.join(TEX, f'cord_{color}_diff.png'))
    nt.links.new(t.outputs['Color'], b.inputs['Base Color'])
    im = bpy.data.images.load(os.path.join(TEX, 'cord_nor.png')); im.colorspace_settings.name = 'Non-Color'
    tn = nt.nodes.new('ShaderNodeTexImage'); tn.image = im
    nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = .8
    nt.links.new(tn.outputs['Color'], nm.inputs['Color']); nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])

    def fabric_uv(o, size=.2):
        """상자 투영. 골(이랑)은 질감의 v 방향: 좌석 윗면은 앞뒤로, 옆면·등받이는 세로로"""
        me = o.data
        while me.uv_layers: me.uv_layers.remove(me.uv_layers[0])
        uv = me.uv_layers.new(name='UVMap')
        for p in me.polygons:
            n = [abs(c) for c in p.normal]; ax = n.index(max(n))
            for li in p.loop_indices:
                co = me.vertices[me.loops[li].vertex_index].co
                a, bb = (co.x, co.y) if ax == 2 else (co.x, co.z) if ax == 1 else (co.y, co.z)
                uv.data[li].uv = (a / size, bb / size)
        me.materials.append(fab)

    def tube(name, pts, r=.035):
        """꺾이는 곳을 반지름 r로 둥글게 한 강관"""
        pts = [Vector(p) for p in pts]
        path = [pts[0]]
        for i in range(1, len(pts) - 1):
            p, a, c = pts[i], (pts[i] - pts[i - 1]).normalized(), (pts[i + 1] - pts[i]).normalized()
            ang = math.acos(max(-1, min(1, -a.dot(c))))
            tt = min(r / math.tan(ang / 2), (pts[i] - pts[i - 1]).length * .45, (pts[i + 1] - pts[i]).length * .45)
            p0, p1 = p - a * tt, p + c * tt
            for k in range(17):                                    # 2차 베지어로 굽힘
                s = k / 16; path.append((1 - s) ** 2 * p0 + 2 * (1 - s) * s * p + s * s * p1)
        path.append(pts[-1])
        cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'
        cu.bevel_depth = TUBE; cu.bevel_resolution = 6; cu.use_fill_caps = True
        sp = cu.splines.new('POLY'); sp.points.add(len(path) - 1)
        for k, q in enumerate(path): sp.points[k].co = (q.x, q.y, q.z, 1)
        o = bpy.data.objects.new(name, cu); scene.collection.objects.link(o)
        bpy.context.view_layer.objects.active = o; o.select_set(True)
        bpy.ops.object.convert(target='MESH'); o.select_set(False)
        o.data.materials.append(chrome)
        for p in o.data.polygons: p.use_smooth = True
        return o

    back_rail_y = BACK_FOOT_Y + (BACK_SEAT_Y - BACK_FOOT_Y) * RAIL_Z / (SEAT_Z - .05)
    for sx in (-1, 1):
        x = sx * LX
        # 앞다리 → 좌석 밑에서 뒤로 꺾여 옆 받침대 → 뒷다리에 붙음
        tube(f'front{sx}', [(x, FRONT_Y, 0), (x, FRONT_Y, RAIL_Z), (x, back_rail_y, RAIL_Z)])
        # 뒷다리: 바닥(뒤로 벌어짐) → 좌석 뒤 → 등받이 뒤 (살짝 뒤로 기움)
        tube(f'back{sx}', [(x, BACK_FOOT_Y, 0), (x, BACK_SEAT_Y, SEAT_Z - .05), (x, BACK_TOP_Y, BACK_TOP_Z)], r=.06)
        for fy in (FRONT_Y, BACK_FOOT_Y):                          # 바닥 고무 패킹
            bpy.ops.mesh.primitive_cylinder_add(radius=TUBE + .001, depth=.006, location=(x, fy, .003), vertices=16)
            bpy.context.object.data.materials.append(rubber)
    tube('cross', [(-LX, back_rail_y, RAIL_Z), (LX, back_rail_y, RAIL_Z)])   # 뒷다리 사이 가로대

    def rrect(w, d, r, n=10):
        pts = []
        for cx, cy, a0 in ((w / 2 - r, -d / 2 + r, -90), (w / 2 - r, d / 2 - r, 0), (-w / 2 + r, d / 2 - r, 90), (-w / 2 + r, -d / 2 + r, 180)):
            for i in range(n + 1):
                a = math.radians(a0 + 90 * i / n); pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        return pts

    def piping(name, pts):
        """솔기 테두리(파이핑): 닫힌 윤곽을 따라 가는 천 줄"""
        cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'
        cu.bevel_depth = .0032; cu.bevel_resolution = 2
        sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1); sp.use_cyclic_u = True
        for k, q in enumerate(pts): sp.points[k].co = (*q, 1)
        o = bpy.data.objects.new(name, cu); scene.collection.objects.link(o)
        bpy.context.view_layer.objects.active = o; o.select_set(True)
        bpy.ops.object.convert(target='MESH'); o.select_set(False)
        fabric_uv(o, .05)
        for p in o.data.polygons: p.use_smooth = True
        return o

    # 좌석 쿠션: 위에서 보면 모서리가 둥근 사각, 윗면이 살짝 부풀고 위·아래 모서리가 둥글다
    bm = bmesh.new()
    lo = [bm.verts.new((x, y + SEAT_CY, SEAT_Z - SEAT_T)) for x, y in rrect(SEAT_W - .01, SEAT_D - .01, .055)]
    hi = [bm.verts.new((x, y + SEAT_CY, SEAT_Z)) for x, y in rrect(SEAT_W, SEAT_D, .06)]
    n = len(lo)
    bm.faces.new(lo[::-1]); bm.faces.new(hi)
    for i in range(n): bm.faces.new([lo[i], lo[(i + 1) % n], hi[(i + 1) % n], hi[i]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new('seat'); bm.to_mesh(me); bm.free()
    seat = bpy.data.objects.new('seat', me); scene.collection.objects.link(seat)
    bpy.context.view_layer.objects.active = seat
    bv = seat.modifiers.new('bev', 'BEVEL'); bv.width = .02; bv.segments = 6; bv.limit_method = 'ANGLE'; bv.angle_limit = math.radians(60)
    bpy.ops.object.modifier_apply(modifier='bev')
    sub = seat.modifiers.new('sub', 'SUBSURF'); sub.levels = 1
    bpy.ops.object.modifier_apply(modifier='sub')
    for v in seat.data.vertices:                                    # 윗면 가운데가 살짝 부풀게
        if v.co.z > SEAT_Z - .02:
            v.co.z += .006 * (1 - (2 * v.co.x / SEAT_W) ** 2) * (1 - (2 * (v.co.y - SEAT_CY) / SEAT_D) ** 2)
    fabric_uv(seat)
    for p in seat.data.polygons: p.use_smooth = True
    piping('seat_pipe', [(x, y + SEAT_CY, SEAT_Z - .017) for x, y in rrect(SEAT_W + .002, SEAT_D + .002, .061)])

    # 등받이: 납작한 타원(초타원) 쿠션, 양 끝이 앞으로 살짝 감싸게 휨
    bm = bmesh.new(); N = 64
    ring = []
    for i in range(N):
        a = 2 * math.pi * i / N; c, s = math.cos(a), math.sin(a)
        ring.append((BR_W / 2 * math.copysign(abs(c) ** .7, c), BR_H / 2 * math.copysign(abs(s) ** .7, s)))
    yb = BACK_TOP_Y - TUBE - .002 - .01                             # 뒷면 (강관 바로 앞)
    front = [bm.verts.new((x, yb - BR_T, BR_CZ + z)) for x, z in ring]
    back = [bm.verts.new((x, yb, BR_CZ + z)) for x, z in ring]
    bm.faces.new(front); bm.faces.new(back[::-1])
    for i in range(N): bm.faces.new([front[i], back[i], back[(i + 1) % N], front[(i + 1) % N]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new('backrest'); bm.to_mesh(me); bm.free()
    br = bpy.data.objects.new('backrest', me); scene.collection.objects.link(br)
    bpy.context.view_layer.objects.active = br
    bv = br.modifiers.new('bev', 'BEVEL'); bv.width = .016; bv.segments = 5; bv.limit_method = 'ANGLE'
    bpy.ops.object.modifier_apply(modifier='bev')
    for v in br.data.vertices: v.co.y -= .35 * v.co.x ** 2
    fabric_uv(br)
    for p in br.data.polygons: p.use_smooth = True
    # 등받이 앞면 둘레 솔기
    yp = yb - BR_T + .006                                          # 둥근 모서리 위 (앞면에서 6 mm 뒤, 6 mm 안쪽)
    kx, kz = 1 - .006 / (BR_W / 2), 1 - .006 / (BR_H / 2)
    piping('back_pipe', [(x * kx, yp - .35 * (x * kx) ** 2, BR_CZ + z * kz) for x, z in ring])

    bpy.ops.object.select_all(action='SELECT')
    bpy.context.view_layer.objects.active = seat
    bpy.ops.object.join()
    o = bpy.context.object; o.name = f'chair_dublin_{color}'
    xs = [v.co for v in o.data.vertices]
    lo = [min(c[i] for c in xs) for i in range(3)]; hi = [max(c[i] for c in xs) for i in range(3)]
    print('bbox mm', *[round((hi[i] - lo[i]) * 1000) for i in range(3)], 'center y mm', round((hi[1] + lo[1]) / 2 * 1000))
    # 가운데를 원점으로 (앞뒤로 치우치지 않게)
    cy = (hi[1] + lo[1]) / 2
    for v in o.data.vertices: v.co.y -= cy
    out = os.path.join(ROOT, 'docs', 'models', f'chair_dublin_{color}.glb')
    bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', export_image_format='JPEG',
                              export_jpeg_quality=85, export_apply=True, export_yup=True)
    print('faces', len(o.data.polygons), 'saved', out, os.path.getsize(out) // 1024, 'KB')


for col in ('cheese', 'green'):
    build(col)
