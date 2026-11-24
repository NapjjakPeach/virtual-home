"""침대 모델용 질감을 직접 생성한다 (사진을 쓰지 않음, 전부 수식으로 그림).

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


if __name__ == '__main__':
    oak(); quilt(); wave(); band()
    print('->', OUT)
