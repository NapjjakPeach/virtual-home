"""의자 3D 모델: 룸앤홈 싱겔 패브릭 체어 (크림 · 차콜).

    python tools/make_bed_tex.py slub      (질감 먼저)
    "C:/Program Files/Blender Foundation/Blender 5.3/blender.exe" -b -P tools/make_chair_singel.py

치수 (mm, 상품 정보): 460 × 560 × 780, 좌석 높이 470. 소재: 강재(분체도장), 폴리에스터 100%, 스펀지.
생김새(상품 사진): 무광 검정 강관 다리, 두툼하고 모서리가 푹신하게 둥근 사각 좌석, 모서리가 둥근 직사각 등받이.
앞다리는 바닥에서 좌석 밑까지 올라와 뒤로 꺾여 옆 받침대가 되고, 뒷다리는 바닥(뒤로 벌어짐)에서
좌석 뒤를 지나 등받이 뒤 옆쪽까지 한 줄로 올라간다. 뒷다리 사이에 좌석 밑 가로대.
좌표: 바닥 가운데 = 원점, 단위 m. 앞(앉는 쪽) = three.js +z = Blender -Y.
결과: docs/models/chair_singel_cream.glb, docs/models/chair_singel_charcoal.glb
"""
import bpy, bmesh, math, os
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEX = os.path.join(ROOT, 'bake', 'bed_tex')

TUBE = .0105                     # 강관 반지름 (지름 21)
LX = .214                        # 다리 가운데 x (바닥에서 바깥 약 450)
SEAT_Z, SEAT_T = .47, .08        # 좌석 윗면 높이, 쿠션 두께
SEAT_W, SEAT_D, SEAT_CY = .452, .43, -.03
RAIL_Z = SEAT_Z - SEAT_T - TUBE  # 옆 받침대 높이
FRONT_FOOT_Y, FRONT_TOP_Y = -.257, -.226          # 앞다리: 바닥에서 살짝 앞으로 벌어짐
BACK_FOOT_Y, BACK_SEAT_Y, BACK_TOP_Y = .28, .2, .222   # 뒷다리: 바닥, 좌석 높이, 위끝
BACK_TOP_Z = .72
BR_W, BR_H, BR_T, BR_CZ = .44, .25, .05, .78 - .125     # 등받이


def rrect(w, d, r, n=10):
    pts = []
    for cx, cy, a0 in ((w / 2 - r, -d / 2 + r, -90), (w / 2 - r, d / 2 - r, 0), (-w / 2 + r, d / 2 - r, 90), (-w / 2 + r, -d / 2 + r, 180)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n); pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def build(color):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene

    steel = bpy.data.materials.new('black_steel'); steel.use_nodes = True
    b = steel.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (.018, .018, .02, 1); b.inputs['Metallic'].default_value = .4; b.inputs['Roughness'].default_value = .42
    cap = bpy.data.materials.new('foot_cap'); cap.use_nodes = True
    cap.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.03, .03, .03, 1)

    fab = bpy.data.materials.new(f'slub_{color}'); fab.use_nodes = True
    nt = fab.node_tree; b = nt.nodes['Principled BSDF']
    b.inputs['Roughness'].default_value = .9
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(os.path.join(TEX, f'slub_{color}_diff.png'))
    nt.links.new(t.outputs['Color'], b.inputs['Base Color'])
    im = bpy.data.images.load(os.path.join(TEX, 'slub_nor.png')); im.colorspace_settings.name = 'Non-Color'
    tn = nt.nodes.new('ShaderNodeTexImage'); tn.image = im
    nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = .8
    nt.links.new(tn.outputs['Color'], nm.inputs['Color']); nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])

    def fabric_uv(o, size=.1):
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
        pts = [Vector(p) for p in pts]
        path = [pts[0]]
        for i in range(1, len(pts) - 1):
            p, a, c = pts[i], (pts[i] - pts[i - 1]).normalized(), (pts[i + 1] - pts[i]).normalized()
            ang = math.acos(max(-1, min(1, -a.dot(c))))
            tt = min(r / math.tan(ang / 2), (pts[i] - pts[i - 1]).length * .45, (pts[i + 1] - pts[i]).length * .45)
            p0, p1 = p - a * tt, p + c * tt
            for k in range(17):
                s = k / 16; path.append((1 - s) ** 2 * p0 + 2 * (1 - s) * s * p + s * s * p1)
        path.append(pts[-1])
        cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'
        cu.bevel_depth = TUBE; cu.bevel_resolution = 6; cu.use_fill_caps = True
        sp = cu.splines.new('POLY'); sp.points.add(len(path) - 1)
        for k, q in enumerate(path): sp.points[k].co = (q.x, q.y, q.z, 1)
        o = bpy.data.objects.new(name, cu); scene.collection.objects.link(o)
        bpy.context.view_layer.objects.active = o; o.select_set(True)
        bpy.ops.object.convert(target='MESH'); o.select_set(False)
        o.data.materials.append(steel)
        for p in o.data.polygons: p.use_smooth = True
        return o

    def soft_slab(name, outline, z0, z1, bev, inset=.008):
        """둥근 사각 윤곽을 세운 쿠션: 위·아래 모서리를 크게 굴리고 한 번 매끈하게"""
        bm = bmesh.new()
        lo = [bm.verts.new((x, y, z0)) for x, y in outline(inset)]
        hi = [bm.verts.new((x, y, z1)) for x, y in outline(0)]
        n = len(lo)
        bm.faces.new(lo[::-1]); bm.faces.new(hi)
        for i in range(n): bm.faces.new([lo[i], lo[(i + 1) % n], hi[(i + 1) % n], hi[i]])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
        o = bpy.data.objects.new(name, me); scene.collection.objects.link(o)
        bpy.context.view_layer.objects.active = o
        bv = o.modifiers.new('bev', 'BEVEL'); bv.width = bev; bv.segments = 6; bv.limit_method = 'ANGLE'; bv.angle_limit = math.radians(60)
        bpy.ops.object.modifier_apply(modifier='bev')
        sub = o.modifiers.new('sub', 'SUBSURF'); sub.levels = 1
        bpy.ops.object.modifier_apply(modifier='sub')
        return o

    back_rail_y = BACK_FOOT_Y + (BACK_SEAT_Y - BACK_FOOT_Y) * RAIL_Z / (SEAT_Z - .06)
    for sx in (-1, 1):
        x = sx * LX
        tube(f'front{sx}', [(x, FRONT_FOOT_Y, 0), (x, FRONT_TOP_Y, RAIL_Z), (x, back_rail_y, RAIL_Z)], r=.04)
        tube(f'back{sx}', [(x, BACK_FOOT_Y, 0), (x, BACK_SEAT_Y, SEAT_Z - .06), (x, BACK_TOP_Y, BACK_TOP_Z)], r=.06)
        for fy in (FRONT_FOOT_Y, BACK_FOOT_Y):
            bpy.ops.mesh.primitive_cylinder_add(radius=TUBE + .0012, depth=.006, location=(x, fy, .003), vertices=16)
            bpy.context.object.data.materials.append(cap)
    tube('cross', [(-LX, back_rail_y, RAIL_Z), (LX, back_rail_y, RAIL_Z)])

    # 좌석: 두툼하고 모서리가 푹신한 둥근 사각, 윗면이 살짝 부풂
    seat = soft_slab('seat', lambda i: [(x, y + SEAT_CY) for x, y in rrect(SEAT_W - 2 * i, SEAT_D - 2 * i, .07 - i)],
                     SEAT_Z - SEAT_T, SEAT_Z, .03)
    for v in seat.data.vertices:
        if v.co.z > SEAT_Z - .025:
            v.co.z += .008 * max(0, 1 - (2 * v.co.x / SEAT_W) ** 2) * max(0, 1 - (2 * (v.co.y - SEAT_CY) / SEAT_D) ** 2)
    fabric_uv(seat)
    for p in seat.data.polygons: p.use_smooth = True

    # 등받이: 모서리 둥근 직사각 쿠션 (세로로 세움), 양 끝이 아주 살짝 앞으로
    yb = BACK_TOP_Y - TUBE - .002                                   # 뒷면 (강관 바로 앞)
    bm = bmesh.new()
    ring = rrect(BR_W, BR_H, .07)
    front = [bm.verts.new((x, yb - BR_T, BR_CZ + z)) for x, z in ring]
    back = [bm.verts.new((x, yb, BR_CZ + z)) for x, z in ring]
    n = len(ring)
    bm.faces.new(front); bm.faces.new(back[::-1])
    for i in range(n): bm.faces.new([front[i], back[i], back[(i + 1) % n], front[(i + 1) % n]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new('backrest'); bm.to_mesh(me); bm.free()
    br = bpy.data.objects.new('backrest', me); scene.collection.objects.link(br)
    bpy.context.view_layer.objects.active = br
    bv = br.modifiers.new('bev', 'BEVEL'); bv.width = .02; bv.segments = 6; bv.limit_method = 'ANGLE'
    bpy.ops.object.modifier_apply(modifier='bev')
    sub = br.modifiers.new('sub', 'SUBSURF'); sub.levels = 1
    bpy.ops.object.modifier_apply(modifier='sub')
    for v in br.data.vertices: v.co.y -= .25 * v.co.x ** 2
    fabric_uv(br)
    for p in br.data.polygons: p.use_smooth = True

    bpy.ops.object.select_all(action='SELECT')
    bpy.context.view_layer.objects.active = seat
    bpy.ops.object.join()
    o = bpy.context.object; o.name = f'chair_singel_{color}'
    xs = [v.co for v in o.data.vertices]
    lo = [min(c[i] for c in xs) for i in range(3)]; hi = [max(c[i] for c in xs) for i in range(3)]
    cy = (hi[1] + lo[1]) / 2
    for v in o.data.vertices: v.co.y -= cy
    print('bbox mm', *[round((hi[i] - lo[i]) * 1000) for i in range(3)],
          'feet three z: front', round(-(FRONT_FOOT_Y - cy), 3), 'back', round(-(BACK_FOOT_Y - cy), 3))
    out = os.path.join(ROOT, 'docs', 'models', f'chair_singel_{color}.glb')
    bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', export_image_format='JPEG',
                              export_jpeg_quality=85, export_apply=True, export_yup=True)
    print('faces', len(o.data.polygons), 'saved', out, os.path.getsize(out) // 1024, 'KB')


for col in ('cream', 'charcoal'):
    build(col)
