"""가구 모델용 질감(침대·헤드 선반)을 직접 생성한다 (사진을 쓰지 않음, 전부 수식으로 그림).

    python tools/make_bed_tex.py

- oak    : 오크 무늬 (프레임). 0.5 m × 1.0 m 한 장, 결은 세로(v) 방향
- quilt  : 필로우탑 윗면. 0.28 m 정사각 한 장에 다이아몬드 누빔선 + 단추
- wave   : 매트리스 옆면. 가로 0.24 m × 옆면 높이 전체. 위아래 박음선 사이에 두 줄 물결 자수
- band   : 필로우탑 옆 띠. 가로 0.12 m × 띠 높이 전체. 잔 격자 누빔
각각 _diff(색) / _nor(요철) 를 bake/bed_tex/ 에 PNG로 저장 (Blender 스크립트가 읽어서 GLB에 JPEG로 넣음)
"""
import os
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'bake', 'bed_tex')
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(11)


def to_srgb(c): c = np.clip(c, 0, 1); return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)
def to_lin(c): return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
def hexlin(h): return to_lin(np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], np.float32) / 255)
def norm(a): return (a - a.mean()) / (a.std() + 1e-6)
def noise(shape, s, wrap=True): return norm(gaussian_filter(rng.standard_normal(shape).astype(np.float32), s, mode='wrap' if wrap else 'reflect'))


def save_rgb(a, name):
    Image.fromarray((np.clip(a, 0, 1) * 255 + .5).astype(np.uint8)).save(os.path.join(OUT, name))
    print('  ', name, a.shape[1], 'x', a.shape[0])


def normal_from_height(h, strength, px_m):
    """h: 높이(m), px_m: 픽셀당 m. OpenGL 방식(+Y 위) 노멀맵"""
    gy, gx = np.gradient(h * strength / px_m)
    n = np.stack([-gx, gy, np.ones_like(h)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return n * .5 + .5


def puff(mask, s):
    """박음선(mask=1)에서 움푹, 사이가 볼록한 누빔 높이 (0~1)"""
    d = gaussian_filter(mask.astype(np.float32), s, mode='wrap')
    d /= d.max() + 1e-6
    return 1 - np.clip(d * 1.6, 0, 1) ** .7


def weave(shape):   # 원단 잔결 (0.3 mm 수준)
    return .6 * noise(shape, .7) + .4 * noise(shape, (0.6, 2.5))


# ---------------- 오크 ----------------
def oak(W=1024, H=2048):
    print('oak')
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    warp = noise((H // 8, W // 8), 6, False)
    warp = np.asarray(Image.fromarray(warp).resize((W, H), Image.BICUBIC))
    u = x + warp * 26 + 14 * np.sin(y / H * 2 * np.pi * 1.0)
    rings = np.sin(u / W * 2 * np.pi * 9 + noise((1, W), 30)[0] * .0)   # 굵은 결
    fine = noise((H, W), (40, 1.2))                                       # 가는 결 (세로로 길게)
    pores = (noise((H, W), (6, .6)) > 2.0).astype(np.float32)             # 물관 (짧은 세로 홈)
    flecks = gaussian_filter((rng.random((H, W)) > .9993).astype(np.float32), (10, 1.5))   # 오크 반점
    t = .45 * rings + .35 * fine
    t = (t - t.min()) / (t.max() - t.min())
    light, dark = hexlin('#cfa676'), hexlin('#a57a4a')
    col = light * (1 - t[..., None] * .55) + dark * (t[..., None] * .55)
    col *= (1 - .18 * pores)[..., None]
    col *= (1 + 1.5 * flecks / (flecks.max() + 1e-6) * .06)[..., None]
    save_rgb(to_srgb(col), 'oak_diff.png')
    h = -.00015 * pores + .00004 * fine
    save_rgb(normal_from_height(h, 1, .5 / W), 'oak_nor.png')


# ---------------- 메이플 (침대 헤드 선반) ----------------
def maple(W=1024, H=1024):
    """메이플: 오크보다 밝고 결이 곱고 물관이 거의 없다. 0.5 m × 0.5 m, 결은 가로(u) 방향"""
    print('maple')
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    warp = np.asarray(Image.fromarray(noise((H // 8, W // 8), 5, False)).resize((W, H), Image.BICUBIC))
    v = y + warp * 18
    rings = np.sin(v / H * 2 * np.pi * 14)
    fine = noise((H, W), (1.0, 50))                                       # 가로로 긴 가는 결
    t = .35 * rings + .5 * fine
    t = (t - t.min()) / (t.max() - t.min())
    light, dark = hexlin('#e6cda6'), hexlin('#c9a77a')
    col = light * (1 - t[..., None] * .5) + dark * (t[..., None] * .5)
    save_rgb(to_srgb(col), 'maple_diff.png')
    save_rgb(normal_from_height(.00003 * fine, 1, .5 / W), 'maple_nor.png')


# ---------------- 원목 (한샘 포레 식탁) ----------------
def fore(W=1024, H=2048):
    """포레 식탁 원목: 오크보다 따뜻한 꿀색, 결이 길고 물관이 얕다. 0.5 m × 1.0 m, 결은 세로(v) 방향 (상품 사진 색)"""
    print('fore')
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    warp = np.asarray(Image.fromarray(noise((H // 8, W // 8), 6, False)).resize((W, H), Image.BICUBIC))
    u = x + warp * 30 + 10 * np.sin(y / H * 2 * np.pi * 1.3)
    rings = np.sin(u / W * 2 * np.pi * 7)
    fine = noise((H, W), (45, 1.1))
    pores = (noise((H, W), (5, .6)) > 2.2).astype(np.float32)
    t = .45 * rings + .4 * fine
    t = (t - t.min()) / (t.max() - t.min())
    # 사이트에서 가구는 고른 채움빛 + 노출 1.5로 보이므로 사진보다 한 단계 진하게 (화면에서 상품 사진 색이 되도록)
    light, dark = hexlin('#b97c45'), hexlin('#7f4c22')
    col = light * (1 - t[..., None] * .62) + dark * (t[..., None] * .62)
    col *= (1 - .14 * pores)[..., None]
    save_rgb(to_srgb(col), 'fore_diff.png')
    save_rgb(normal_from_height(-.0001 * pores + .00003 * fine, 1, .5 / W), 'fore_nor.png')


# ---------------- 고무나무 (룸앤홈 보메 식탁 다리·테두리) ----------------
def rubber(W=1024, H=2048):
    """고무나무 원목: 밝은 노란 베이지, 결이 곧고 잔잔하다. 0.5 m × 1.0 m, 결은 세로(v) 방향.
    사이트 조명(노출 1.5)에서 상품 사진 색이 되도록 사진보다 한 단계 진하게"""
    print('rubber')
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    warp = np.asarray(Image.fromarray(noise((H // 8, W // 8), 6, False)).resize((W, H), Image.BICUBIC))
    u = x + warp * 20 + 6 * np.sin(y / H * 2 * np.pi * 1.1)
    rings = np.sin(u / W * 2 * np.pi * 11)
    fine = noise((H, W), (50, 1.0))
    pores = (noise((H, W), (4, .5)) > 2.4).astype(np.float32)
    streak = noise((H, W), (300, 2.5))                                    # 결 따라 길게 진한 줄
    t = .35 * rings + .45 * fine + .3 * np.clip(streak, 0, None)
    t = (t - t.min()) / (t.max() - t.min())
    light, dark = hexlin('#d0a466'), hexlin('#9a6a34')
    col = light * (1 - t[..., None] * .68) + dark * (t[..., None] * .68)
    col *= (1 - .16 * pores)[..., None]
    save_rgb(to_srgb(col), 'rubber_diff.png')
    save_rgb(normal_from_height(-.00008 * pores + .00003 * fine, 1, .5 / W), 'rubber_nor.png')


# ---------------- 합판 옆면 (식탁 상판 모서리) ----------------
def ply(W=512, H=512):
    """합판 단면: 1.5 mm 안팎의 얇은 층이 밝고 어둡게 번갈아 쌓임. 0.1 m × 0.1 m, 층은 가로(u) 방향"""
    print('ply')
    y = np.arange(H, dtype=np.float32)[:, None]
    jitter = noise((H, 1), 3)[:, :1] * 1.5
    layer = (np.floor((y + jitter) / (H * .015)) % 2).astype(np.float32)   # 1.5 mm 층
    layer = gaussian_filter(np.repeat(layer, W, 1), (.8, 0), mode='wrap')
    fine = noise((H, W), (1.0, 40))
    t = np.clip(.65 * layer + .2 * fine * .5 + .2, 0, 1)
    light, dark = hexlin('#d2a86f'), hexlin('#a87b46')
    col = light * (1 - t[..., None] * .6) + dark * (t[..., None] * .6)
    save_rgb(to_srgb(col), 'ply_diff.png')


# ---------------- 코듀로이 (더블린 체어 치즈 · 딥그린) ----------------
def cord(N=1024):
    """코듀로이: 4 mm 간격 골(이랑)이 세로(v)로 길게. 0.2 m × 0.2 m 한 장.
    색은 상품 색상 칩(치즈 #f1ae47, 딥그린 #4f6338)을 사이트 조명에 맞춰 한 단계 진하게"""
    print('cord')
    x = np.arange(N, dtype=np.float32)[None, :]
    pitch = N * .004 / .2                                                 # 4 mm
    s = np.abs(np.sin(np.pi * x / pitch))
    rib = np.repeat(s ** .6, N, 0)                                        # 이랑 높이 (0 = 골)
    pile = noise((N, N), (6, .5)) * .5 + noise((N, N), 30) * .5           # 털 결 얼룩
    fibre = noise((N, N), (4, .35))                                       # 이랑 위 잔털
    for name, base in (('cheese', '#f6b040'), ('green', '#617a45')):
        col = hexlin(base) * (.64 + .42 * rib[..., None] + .05 * pile[..., None] + .04 * fibre[..., None] * rib[..., None])
        save_rgb(to_srgb(col), f'cord_{name}_diff.png')
    save_rgb(normal_from_height(.0016 * rib + .00004 * pile + .00002 * fibre, 1, .2 / N), 'cord_nor.png')


# ---------------- 슬럽 직물 (싱겔 패브릭 체어 크림 · 차콜) ----------------
def slub(N=1024):
    """폴리에스터 평직: 0.8 mm 실이 가로·세로로 엇갈리고, 실 굵기가 고르지 않은(슬럽) 마디와 섞인 색 실이 보인다.
    0.1 m × 0.1 m 한 장. 색은 상품 사진(크림 #e9e2d6, 차콜 #3d3f43)을 사이트 조명에 맞춤"""
    print('slub')
    y, x = np.mgrid[0:N, 0:N].astype(np.float32)
    p = 8.0                                                               # 실 간격 0.8 mm
    wx, wy = noise((N, N), (40, 2)) * 1.2, noise((N, N), (2, 40)) * 1.2  # 실이 살짝 굽음
    cx, cy = np.floor((x + wx) / p), np.floor((y + wy) / p)
    over = ((cx + cy) % 2).astype(np.float32)                             # 평직: 가로실·세로실이 번갈아 위로
    fx, fy = ((x + wx) / p) % 1, ((y + wy) / p) % 1
    weft = np.sin(np.pi * fy) ** .7 * (1 + .5 * np.clip(noise((N, N), (1.5, 60)), -1, 2))   # 가로실 + 슬럽 마디
    warp = np.sin(np.pi * fx) ** .7 * (1 + .3 * np.clip(noise((N, N), (60, 1.5)), -1, 2))
    h = over * weft + (1 - over) * warp
    tone = noise((N // 8, N // 8), .6)                         # 실마다 다른 섞인 색
    tone = np.asarray(Image.fromarray(tone).resize((N, N), Image.NEAREST))
    fleck = (noise((N, N), (1.2, 25)) > 2.3).astype(np.float32)           # 밝은 색 실 마디
    for name, base, fl in (('cream', '#f7f0e4', .06), ('charcoal', '#6f737a', .5)):
        col = hexlin(base) * (.84 + .2 * h[..., None] + .05 * tone[..., None])
        col = col * (1 - fleck[..., None] * fl * .5) + hexlin('#8a8a88') * fleck[..., None] * fl * .5
        save_rgb(to_srgb(col), f'slub_{name}_diff.png')
    save_rgb(normal_from_height(.00035 * h, 1, .1 / N), 'slub_nor.png')


# ---------------- 헤어라인 메탈 (냉장고 문) ----------------
def steel(W=1024, H=1024):
    """가로 헤어라인(브러시드) 은색 메탈. 0.3 m × 0.3 m 반복"""
    print('steel')
    streak = noise((H, W), (.6, 60))                                       # 가로로 아주 긴 잔줄
    blot = noise((H, W), 60) * .25                                         # 넓은 얼룩 (빛 받을 때 살짝)
    t = .75 * streak + blot
    t = (t - t.min()) / (t.max() - t.min())
    col = hexlin('#c9ccce') * (.9 + .16 * t[..., None])
    save_rgb(to_srgb(col), 'steel_diff.png')
    save_rgb(normal_from_height(.000012 * streak, 1, .3 / W), 'steel_nor.png')


# ---------------- 필로우탑 윗면 ----------------
def quilt(N=1024, size=.28):
    print('quilt')
    S = 2   # 2배로 그린 뒤 줄임
    im = Image.new('L', (N * S, N * S), 0); d = ImageDraw.Draw(im)
    M = N * S
    # 다이아몬드 누빔선: 대각선 두 방향, 타일당 2칸 (0.14 m 간격)
    for k in range(-4, 5):
        o = k * M / 2
        d.line([(o, 0), (o + M, M)], fill=255, width=5 * S)
        d.line([(o + M, 0), (o, M)], fill=255, width=5 * S)
    lines = np.asarray(im.resize((N, N), Image.LANCZOS)).astype(np.float32) / 255
    h = puff(lines, 9) * .010                                   # 볼록 10 mm
    # 단추: 선이 만나는 자리 (타일 모서리, 가운데, 변 가운데)
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
    dimple = np.zeros((N, N), np.float32); button = np.zeros((N, N), np.float32)
    for cx, cy in [(0, 0), (N, 0), (0, N), (N, N), (N / 2, N / 2), (N / 2, 0), (0, N / 2), (N, N / 2), (N / 2, N)]:
        r = np.hypot(xx - cx, yy - cy)
        dimple += np.exp(-(r / (N * .09)) ** 2)
        button = np.maximum(button, (r < N * .014).astype(np.float32))
    h -= np.clip(dimple, 0, 1) * .012
    h += .0003 * weave((N, N))
    px = size / N
    ivory = hexlin('#f2ede2')
    shade = .82 + .18 * (h - h.min()) / (h.max() - h.min())
    col = ivory * shade[..., None]
    col = col * (1 - .55 * button[..., None]) + hexlin('#e3dccb') * (.55 * button[..., None])
    col *= (1 + .025 * weave((N, N)))[..., None]
    save_rgb(to_srgb(col), 'quilt_diff.png')
    save_rgb(normal_from_height(gaussian_filter(h, .8, mode='wrap'), 1, px), 'quilt_nor.png')


# ---------------- 매트리스 옆면 (물결 자수) ----------------
def wave(W=1024, H=1152, width=.24, height=.27):
    print('wave')
    S = 2; Ws, Hs = W * S, H * S
    im = Image.new('L', (Ws, Hs), 0); d = ImageDraw.Draw(im)
    # 위아래 박음선 (가로 두 줄씩)
    for fy in (.08, .11, .89, .92):
        d.line([(0, fy * Hs), (Ws, fy * Hs)], fill=255, width=3 * S)
    # 가운데 물결 두 줄 (반 주기 엇갈림) → 서로 감기는 S자 무늬, 타일당 1.5 주기
    t = np.linspace(0, 1, 1200)
    for ph in (0, np.pi):
        for off in (-.035, .035):
            pts = [(tt * Ws, (.5 + .2 * np.sin(tt * 2 * np.pi * 1.5 + ph) + off) * Hs) for tt in t]
            d.line(pts, fill=255, width=4 * S)
    lines = np.asarray(im.resize((W, H), Image.LANCZOS)).astype(np.float32) / 255
    h = puff(lines, 7) * .006
    h += .00035 * weave((H, W))
    ivory = hexlin('#efe9dc')
    shade = .84 + .16 * (h - h.min()) / (h.max() - h.min())
    col = ivory * shade[..., None] * (1 + .03 * weave((H, W)))[..., None]
    save_rgb(to_srgb(col), 'wave_diff.png')
    save_rgb(normal_from_height(gaussian_filter(h, .8, mode='wrap'), 1, width / W), 'wave_nor.png')


# ---------------- 필로우탑 옆 띠 (잔 격자) ----------------
def band(W=1024, H=768, width=.12, height=.09):
    print('band')
    S = 2; Ws, Hs = W * S, H * S
    im = Image.new('L', (Ws, Hs), 0); d = ImageDraw.Draw(im)
    step = Ws / 6
    for k in range(-8, 14):
        o = k * step
        d.line([(o, 0), (o + Hs * .8, Hs)], fill=255, width=3 * S)
        d.line([(o, Hs), (o + Hs * .8, 0)], fill=255, width=3 * S)
    for fy in (.12, .88):
        d.line([(0, fy * Hs), (Ws, fy * Hs)], fill=255, width=3 * S)
    lines = np.asarray(im.resize((W, H), Image.LANCZOS)).astype(np.float32) / 255
    h = puff(lines, 6) * .004 + .0003 * weave((H, W))
    ivory = hexlin('#efe9dc')
    shade = .86 + .14 * (h - h.min()) / (h.max() - h.min())
    save_rgb(to_srgb(ivory * shade[..., None]), 'band_diff.png')
    save_rgb(normal_from_height(gaussian_filter(h, .8, mode='wrap'), 1, width / W), 'band_nor.png')


# ---------------- 라탄 (이케아 톨크닝 침대헤드) ----------------
RATTAN_L, RATTAN_D = '#d6a865', '#a8763c'   # 꿀색 라탄 (사이트 조명에서 사진 색이 되도록 한 단계 진하게)


def rattan():
    """lattice: 납작한 등나무 띠(폭 13 mm)가 대각선으로 엮인 마름모 격자, 구멍은 투명(알파). 0.2 m × 0.2 m 한 장.
    wrap: 기둥에 감은 등나무 껍질 띠(폭 약 6 mm), u = 기둥 길이 방향. 0.05 m 한 장"""
    print('rattan')
    N = 1024
    y, x = np.mgrid[0:N, 0:N].astype(np.float32)
    s = N / 5                                     # 같은 방향 띠 사이 (가로 방향) 간격 → 수직 간격 ≈ 28 mm
    w = 66 / 2                                    # 띠 반폭 (띠 폭 13 mm, 구멍과 비슷하게)
    a, b = (x + y) % s, (x - y) % s               # 두 방향 띠까지 거리 (대각선 좌표)
    da, db = np.minimum(a, s - a) / np.sqrt(2) * np.sqrt(2), np.minimum(b, s - b)
    da = np.minimum(a, s - a) / np.sqrt(2); db = np.minimum(b, s - b) / np.sqrt(2)
    ia, ib = da < w, db < w
    ka, kb = np.floor((x + y) / s), np.floor((x - y) / s)
    a_top = ((ka + kb) % 2 == 0)                  # 엇갈려 엮기: 교차점마다 위로 오는 띠가 번갈아
    fibre_a = noise((N, N), (1.2, 1.2)) * .5 + noise((N, N), 6) * .5
    t = np.zeros((N, N), np.float32); h = np.zeros((N, N), np.float32)
    # 띠 단면: 가운데 볼록, 가장자리 어둡게. 결은 띠 방향으로 길게
    prof_a = np.cos(np.clip(da / w, 0, 1) * np.pi / 2) ** .6
    prof_b = np.cos(np.clip(db / w, 0, 1) * np.pi / 2) ** .6
    streak = norm(gaussian_filter(rng.standard_normal((N, N)).astype(np.float32), (0, 0)))
    sa = gaussian_filter(streak, (6, 6)) * 0 + noise((N, N), (8, 8)) * .3
    show_a = ia & (~ib | a_top); show_b = ib & (~ia | ~a_top)
    t[show_a] = (.55 + .45 * prof_a)[show_a]; t[show_b] = (.55 + .45 * prof_b)[show_b]
    under = (ia & ib)                              # 교차점: 아래 띠는 그늘
    tone = .5 + .5 * noise((N // 16, N // 16), 1.5)
    tone = np.asarray(Image.fromarray(tone.astype(np.float32)).resize((N, N), Image.BICUBIC))
    light, dark = hexlin(RATTAN_L), hexlin(RATTAN_D)
    k = np.clip(.35 + .4 * tone + .15 * fibre_a, 0, 1)
    col = light * (1 - k[..., None]) + dark * k[..., None]
    col *= t[..., None]
    # 교차점에서 위 띠 가장자리 아래로 생기는 그늘
    edge = (ia & ib) & (((da > w * .7) & a_top) | ((db > w * .7) & ~a_top))
    col[edge] *= .7
    alpha = (ia | ib).astype(np.float32)
    alpha = gaussian_filter(alpha, .6, mode='wrap')
    rgba = np.dstack([to_srgb(col), alpha])
    Image.fromarray((np.clip(rgba, 0, 1) * 255 + .5).astype(np.uint8), 'RGBA').save(os.path.join(OUT, 'rattan_lattice.png'))
    h = np.where(show_a, prof_a, 0) + np.where(show_b, prof_b, 0) + .4 * ((ia & ib) & (show_a ^ show_b))
    save_rgb(normal_from_height(.0015 * gaussian_filter(h.astype(np.float32), 1, mode='wrap'), 1, .2 / N), 'rattan_lattice_nor.png')
    print('   rattan_lattice.png', N, 'x', N)
    # 감은 띠: u 방향(기둥 길이)으로 폭 6 mm 띠가 살짝 비스듬히, 띠마다 색이 조금씩
    W, H = 512, 128
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    pitch = W / 8.3
    u = xx + yy * .35                              # 살짝 나선
    ph = (u % pitch) / pitch
    band = np.sin(np.pi * ph) ** .5
    idx = np.floor(u / pitch)
    btone = (np.sin(idx * 12.9898) * 43758.5453) % 1
    k = np.clip(.25 + .45 * btone + .2 * noise((H, W), (.8, 6)), 0, 1)
    col = (light * (1 - k[..., None]) + dark * k[..., None]) * (.6 + .4 * band[..., None])
    save_rgb(to_srgb(col), 'rattan_wrap.png')
    save_rgb(normal_from_height(.0012 * band, 1, .05 / W), 'rattan_wrap_nor.png')


if __name__ == '__main__':
    import sys
    only = sys.argv[1:]   # 예: python tools/make_bed_tex.py maple
    for f in (oak, quilt, wave, band, maple, steel, fore, rubber, ply, cord, slub, rattan):
        if not only or f.__name__ in only: f()
    print('->', OUT)
