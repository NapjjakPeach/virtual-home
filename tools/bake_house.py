"""Blender(Cycles)로 집 전체의 빛(햇빛·하늘빛·벽에서 튄 빛·구석 그늘)을 구워 웹용 파일로 만든다.

준비: tools/devserver.py로 사이트를 열고 주소 뒤에 ?export → bake/house_raw.glb 생김
실행:
    "C:/Program Files/Blender Foundation/Blender 5.3/blender.exe" -b -P tools/bake_house.py -- [--size 2048] [--samples 1024]
결과: docs/baked/house.glb (모양 + 빛 지도용 두 번째 UV), docs/baked/lightmap.png, docs/baked/meta.json

빛 지도는 '색을 뺀 확산광'(Cycles DIFFUSE, 직접+간접)이다. 사이트는 원래 재질(텍스처·광택)을 그대로 쓰고
여기에 이 빛만 곱하므로 마루 결·타일 줄눈이 흐려지지 않는다. 8비트 PNG에 넓은 밝기 범위를 담으려고
log2(1+L)/RANGE 로 저장하고, 사이트 셰이더에서 되돌린다.
"""
import bpy, json, math, os, sys, time
import numpy as np
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, 'bake', 'house_raw.glb')
RAW_META = os.path.join(ROOT, 'bake', 'house_raw.json')
OUT = os.path.join(ROOT, 'docs', 'baked')

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def arg(name, default):
    return type(default)(argv[argv.index(name) + 1]) if name in argv else default
SIZE = arg('--size', 2048)
SAMPLES = arg('--samples', 1024)
RANGE = 4.0            # 저장 범위: L = 2^4-1 = 15 까지 (굽기 최댓값 약 6)
SUN_W = 9.0            # 햇빛 세기(W/m²) — 하늘(1.0)과의 비율이 낮 실내 밝기를 정한다
SKY = 1.0
GAIN = arg('--gain', 1.0)     # 사이트에서 빛 지도를 몇 배로 쓸지 (밝기 맞추기)
RANGE = arg('--range', RANGE)

t0 = time.time()
def log(*a): print(f'[bake {time.time() - t0:6.1f}s]', *a, flush=True)

def save_lightmap(px):
    """로그 인코딩 8비트 PNG로 저장 (디더 없음: 텍셀마다 다른 디더가 벽에 점무늬로 보였다)"""
    rgb = px.reshape(-1, 4)[:, :3]
    lum = rgb @ np.array([.2126, .7152, .0722], np.float32)
    log('L stats: p50 %.3f p90 %.3f p99 %.3f max %.3f' % tuple(np.percentile(lum, [50, 90, 99]).tolist() + [float(lum.max())]))
    enc = np.clip(np.log2(1.0 + np.maximum(rgb, 0)) / RANGE, 0, 1)
    out = np.ones((SIZE * SIZE, 4), np.float32); out[:, :3] = enc
    os.makedirs(OUT, exist_ok=True)
    enc_img = bpy.data.images.new('LMenc', SIZE, SIZE, alpha=False)
    enc_img.colorspace_settings.name = 'Non-Color'
    enc_img.pixels.foreach_set(out.ravel())
    enc_img.filepath_raw = os.path.join(OUT, 'lightmap.png'); enc_img.file_format = 'PNG'
    enc_img.save()
    log('saved lightmap.png', os.path.getsize(enc_img.filepath_raw) // 1024, 'KB')


def write_meta(sig):
    meta = {
        'sig': sig, 'lightmap': 'lightmap.png', 'range': RANGE,
        'intensity': math.pi * GAIN, 'env': 0.22, 'hemi': 0.12, 'exposure': 1.5,
        'size': SIZE, 'samples': SAMPLES, 'sunW': SUN_W, 'sky': SKY,
        'bakedAt': time.strftime('%Y%m%d%H%M%S'),
    }
    json.dump(meta, open(os.path.join(OUT, 'meta.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    log('done', meta)


# --encode-only: 굽기 없이 bake/lm_dn.exr(지난 결과)로 PNG·meta만 다시 만든다
if '--encode-only' in argv:
    src = bpy.data.images.load(os.path.join(ROOT, 'bake', 'lm_dn.exr'))
    SIZE = src.size[0]
    px = np.empty(SIZE * SIZE * 4, np.float32); src.pixels.foreach_get(px)
    save_lightmap(px)
    write_meta(json.load(open(os.path.join(OUT, 'meta.json'), encoding='utf-8'))['sig'])
    sys.exit(0)

meta_in = json.load(open(RAW_META, encoding='utf-8'))

# ---------- 장면 준비 ----------
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=RAW)
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
for o in list(bpy.context.scene.objects):
    if o.type != 'MESH': bpy.data.objects.remove(o, do_unlink=True)
log('imported', len(meshes), 'meshes')

bpy.ops.object.select_all(action='DESELECT')
for o in meshes: o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
bpy.ops.object.join()
house = bpy.context.view_layer.objects.active
house.name = 'house'
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
me = house.data
log('joined:', len(me.polygons), 'faces,', len(me.materials), 'materials')

# ---------- 빛 지도용 두 번째 UV ----------
base_uv = me.uv_layers[0]
lm_uv = me.uv_layers.new(name='LM')
for u in me.uv_layers: u.active_render = (u == base_uv)   # 재질 텍스처는 원래 UV
me.uv_layers.active = lm_uv                                 # 굽기·편집은 LM
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.0, area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
bpy.ops.uv.pack_islands(rotate=True, margin_method='FRACTION', margin=4.0 / SIZE)
bpy.ops.object.mode_set(mode='OBJECT')
log('lightmap UV packed')

# ---------- 하늘·햇빛 ----------
world = bpy.data.worlds.new('sky'); bpy.context.scene.world = world
world.use_nodes = True
nt = world.node_tree; nt.nodes.clear()
tc = nt.nodes.new('ShaderNodeTexCoord'); sep = nt.nodes.new('ShaderNodeSeparateXYZ')
ramp = nt.nodes.new('ShaderNodeValToRGB'); bg = nt.nodes.new('ShaderNodeBackground'); outn = nt.nodes.new('ShaderNodeOutputWorld')
nt.links.new(tc.outputs['Generated'], sep.inputs[0]); nt.links.new(sep.outputs['Z'], ramp.inputs['Fac'])
el = ramp.color_ramp.elements
el[0].position = 0.0; el[0].color = (0.30, 0.29, 0.25, 1)      # 땅(아래) — 반사광
el[1].position = 1.0; el[1].color = (0.42, 0.62, 0.90, 1)      # 천정
e2 = el.new(0.5); e2.color = (0.92, 0.95, 1.0, 1)                # 지평선 — 밝은 하늘
e3 = el.new(0.49); e3.color = (0.45, 0.45, 0.40, 1)
nt.links.new(ramp.outputs['Color'], bg.inputs['Color']); bg.inputs['Strength'].default_value = SKY
nt.links.new(bg.outputs[0], outn.inputs['Surface'])
# Generated 좌표의 Z는 -1..1 방향 → 0..1로 맞추기
mr = nt.nodes.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = -1; mr.inputs['From Max'].default_value = 1
nt.links.new(sep.outputs['Z'], mr.inputs['Value']); nt.links.new(mr.outputs['Result'], ramp.inputs['Fac'])

sx, sy, sz = meta_in['sun']                       # three 좌표(Y 위) → Blender(Z 위)
sun_dir = Vector((sx, -sz, sy)).normalized()
sun_data = bpy.data.lights.new('sun', 'SUN'); sun_data.energy = SUN_W; sun_data.angle = math.radians(1.0)
sun_data.color = (1.0, 0.93, 0.83)
sun = bpy.data.objects.new('sun', sun_data); bpy.context.scene.collection.objects.link(sun)
sun.rotation_euler = (-sun_dir).to_track_quat('-Z', 'Y').to_euler()

# ---------- Cycles ----------
sc = bpy.context.scene
sc.render.engine = 'CYCLES'
prefs = bpy.context.preferences.addons['cycles'].preferences
for kind in ('OPTIX', 'CUDA'):
    try:
        prefs.compute_device_type = kind; prefs.refresh_devices()
        gpus = [d for d in prefs.devices if d.type == kind]
        if gpus:
            for d in prefs.devices: d.use = (d.type == kind)
            sc.cycles.device = 'GPU'; log('device', kind, gpus[0].name); break
    except Exception as e:
        log('no', kind, e)
sc.cycles.samples = SAMPLES
sc.cycles.use_adaptive_sampling = False
sc.cycles.max_bounces = 8; sc.cycles.diffuse_bounces = 6; sc.cycles.glossy_bounces = 2
sc.cycles.transmission_bounces = 2; sc.cycles.transparent_max_bounces = 4
sc.cycles.sample_clamp_indirect = 8.0
sc.render.bake.margin = 6
sc.render.bake.margin_type = 'EXTEND'
sc.render.bake.use_pass_direct = True; sc.render.bake.use_pass_indirect = True; sc.render.bake.use_pass_color = False

img = bpy.data.images.new('LM', SIZE, SIZE, alpha=False, float_buffer=True)
img.colorspace_settings.name = 'Non-Color'
bake_nodes = []
for mat in me.materials:
    if not mat: continue
    mat.use_nodes = True
    n = mat.node_tree.nodes.new('ShaderNodeTexImage'); n.image = img
    uvn = mat.node_tree.nodes.new('ShaderNodeUVMap'); uvn.uv_map = 'LM'
    bake_nodes.append((mat, (n, uvn)))
    mat.node_tree.links.new(uvn.outputs['UV'], n.inputs['Vector'])
    for x in mat.node_tree.nodes: x.select = False
    n.select = True; mat.node_tree.nodes.active = n

bpy.ops.object.select_all(action='DESELECT'); house.select_set(True); bpy.context.view_layer.objects.active = house
log(f'baking {SIZE}x{SIZE} @ {SAMPLES} samples …')
bpy.ops.object.bake(type='DIFFUSE', pass_filter={'DIRECT', 'INDIRECT'}, use_clear=True, margin=6)
log('baked')

# ---------- 잡티 제거: 컴포지터 Denoise(OIDN)를 빈 장면에서 한 번 돌린다 ----------
def denoise(src):
    tmp_in = os.path.join(ROOT, 'bake', 'lm_raw.exr'); tmp_out = os.path.join(ROOT, 'bake', 'lm_dn.exr')
    src.filepath_raw = tmp_in; src.file_format = 'OPEN_EXR'; src.save()
    dsc = bpy.data.scenes.new('denoise')
    dsc.render.engine = 'BLENDER_WORKBENCH'
    dsc.render.resolution_x = dsc.render.resolution_y = SIZE; dsc.render.resolution_percentage = 100
    dsc.render.use_compositing = True
    dsc.view_settings.view_transform = 'Standard'
    dsc.render.image_settings.file_format = 'OPEN_EXR'; dsc.render.image_settings.color_depth = '32'
    ng = bpy.data.node_groups.new('denoise', 'CompositorNodeTree')
    dsc.compositing_node_group = ng
    ng.interface.new_socket('Image', in_out='OUTPUT', socket_type='NodeSocketColor')
    ni = ng.nodes.new('CompositorNodeImage'); ni.image = bpy.data.images.load(tmp_in)
    dn = ng.nodes.new('CompositorNodeDenoise'); dn.inputs['HDR'].default_value = True
    no = ng.nodes.new('NodeGroupOutput')
    ng.links.new(ni.outputs['Image'], dn.inputs['Image']); ng.links.new(dn.outputs['Image'], no.inputs[0])
    bpy.ops.render.render(scene=dsc.name)
    bpy.data.images['Render Result'].save_render(tmp_out, scene=dsc)
    out = bpy.data.images.load(tmp_out)
    p = np.empty(SIZE * SIZE * 4, np.float32); out.pixels.foreach_get(p)
    return p
try:
    px = denoise(img); log('denoised')
except Exception as e:   # 컴포지터 API가 바뀐 버전이면 잡티 그대로 저장
    log('denoise skipped:', e)
    px = np.empty(SIZE * SIZE * 4, np.float32); img.pixels.foreach_get(px)

save_lightmap(px)

# ---------- 모양 내보내기 (텍스처 없이, 재질 이름과 두 UV만) ----------
for mat, nodes in bake_nodes:
    for x in nodes: mat.node_tree.nodes.remove(x)
bpy.ops.object.select_all(action='DESELECT'); house.select_set(True)
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, 'house.glb'), export_format='GLB', use_selection=True,
                          export_texcoords=True, export_normals=True, export_materials='EXPORT', export_image_format='NONE',
                          export_apply=True, export_yup=True)
log('saved house.glb', os.path.getsize(os.path.join(OUT, 'house.glb')) // 1024, 'KB')

write_meta(meta_in['sig'])
