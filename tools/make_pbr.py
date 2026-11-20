"""마루·벽지 실사 재질(PBR: 색 + 요철 노멀 + 광택)을 만든다.

    python tools/make_pbr.py

마루: Poly Haven 'laminate_floor_03' (CC0, 2.08m 정사각) → 판 방향을 기존과 같게 90° 돌리고
      영상 속 우리집 마루(docs/tex/wood.jpg) 색으로 맞춘다. 원본은 bake/src/ 에 (저장소에는 안 올림)
벽지: 실크벽지 요철을 직접 생성 (가로세로로 이어지는 0.5m 타일, 0.5mm/픽셀)
      - 잔 모래알 요철 + 가로·세로 섬유결 + 아주 큰 얼룩
      - 구운 빛(방향 없는 빛)에서도 요철이 보이도록 위쪽 빛 기준 음영을 색 지도에 살짝 넣는다
결과: docs/tex/floor_{diff,nor,rough}.jpg, docs/tex/paper_{diff,nor,rough}.jpg
"""
import os
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'bake', 'src', 'laminate_floor_03')
TEX = os.path.join(ROOT, 'docs', 'tex')


def load(p): return np.asarray(Image.open(p).convert('RGB')).astype(np.float32) / 255.0
def to_lin(c): return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
def to_srgb(c): c = np.clip(c, 0, 1); return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)
def save(a, name, size, q=86):
    im = Image.fromarray((np.clip(a, 0, 1) * 255 + .5).astype(np.uint8))
    if im.size[0] != size: im = im.resize((size, size), Image.LANCZOS)
    im.save(os.path.join(TEX, name), quality=q, optimize=True, progressive=True)
    print(f'  {name}: {size}px, {os.path.getsize(os.path.join(TEX, name)) // 1024} KB')


def floor():
    print('floor (laminate_floor_03 → 우리집 색)')
    diff = np.rot90(load(os.path.join(SRC, 'laminate_floor_03_diff_2k.jpg')))
    nor = load(os.path.join(SRC, 'laminate_floor_03_nor_gl_2k.jpg'))
    rough = np.rot90(load(os.path.join(SRC, 'laminate_floor_03_rough_2k.jpg')))
    # 노멀맵을 90° 돌리면 접선 방향도 돈다: (x, y) → (-y, x)
    n = np.rot90(nor * 2 - 1); n = np.stack([-n[..., 1], n[..., 0], n[..., 2]], -1)
    nor = n * .5 + .5
    # 색 맞추기: 선형 공간에서 채널별 평균 비율만 맞춰 결의 대비는 그대로 둔다
    target = to_lin(load(os.path.join(TEX, 'wood.jpg'))).reshape(-1, 3).mean(0)
    lin = to_lin(diff); lin *= target / lin.reshape(-1, 3).mean(0)
    save(to_srgb(lin), 'floor_diff.jpg', 2048, 84)
    save(nor, 'floor_nor.jpg', 2048, 90)
    save(rough, 'floor_rough.jpg', 1024, 86)


def wallpaper(N=1024, seed=7):
    print('wallpaper (실크벽지 요철 생성)')
    r = np.random.default_rng(seed)
    w = lambda: r.standard_normal((N, N)).astype(np.float32)
    g = lambda a, s: gaussian_filter(a, s, mode='wrap')
    norm = lambda a: (a - a.mean()) / (a.std() + 1e-6)
    sand = norm(g(w(), 1.1))                              # 0.5mm 알갱이
    grain = norm(g(w(), 2.6))                             # 1~2mm 굴곡
    fib_h = norm(g(w(), (0.8, 7.0)))                      # 가로 섬유결
    fib_v = norm(g(w(), (7.0, 0.8)))                      # 세로 섬유결
    cloud = norm(g(w(), 40))                              # 큰 얼룩 (빛 받을 때만 은은히)
    h = .55 * sand + .45 * grain + .35 * fib_h + .25 * fib_v
    h = norm(h)
    # 노멀: 높이 기울기 (픽셀 0.5mm, 요철 높이 약 0.08mm)
    k = 2.2
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * .5 * k / 8
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * .5 * k / 8
    n = np.stack([-dx, dy, np.ones_like(h)], -1); n /= np.linalg.norm(n, axis=-1, keepdims=True)
    # 색: 거의 흰색(재질 색이 실제 벽지 색). 오목한 곳 살짝 어둡게 + 위쪽 빛 음영을 약하게
    light = np.array([0, .55, .835]); light /= np.linalg.norm(light)
    shade = (n @ light); shade = (shade - shade.mean()) / (shade.std() + 1e-6)
    lum = 1 + .011 * shade + .007 * np.clip(h, -3, 3) / 3 + .005 * cloud
    lum = lum / lum.max() * .985
    diff = np.repeat(lum[..., None], 3, -1)
    rough = np.clip(.62 + .05 * np.clip(-h, -2, 2) / 2 + .03 * cloud / 3, 0, 1)
    save(diff, 'paper_diff.jpg', N, 90)
    save(n * .5 + .5, 'paper_nor.jpg', N, 92)
    save(np.repeat(rough[..., None], 3, -1), 'paper_rough.jpg', 512, 88)


if __name__ == '__main__':
    floor()
    wallpaper()
