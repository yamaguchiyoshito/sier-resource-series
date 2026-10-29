#!/usr/bin/env python3
"""トラフィックが矢印の上を流れるアニメーション版を生成する。

1つの軌道定義から、(1) SMIL アニメーションの SVG（assets/animated/）と、(2) 6秒・15fps のフレームを
rsvg-convert と ffmpeg で合成した GIF（assets/gif/）を出力する。周期は 6.0 秒で、t=0 と t=6 の状態が一致する。
文字と箱は動かさない。箱の内側はマスクで隠し、トラフィックは箱の「中」を通るときに見えなくなる。
"""
from __future__ import annotations
import argparse
import math
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import draw_figures as df  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT_SVG = ROOT / 'assets' / 'animated'
OUT_GIF = ROOT / 'assets' / 'gif'
CYCLE = 6.0
FPS = 15
GIF_WIDTH = 800
LIGHT = '#bcd3e6'


# ---------------------------------------------------------------- 軌道
class Poly:
    """折れ線の軌道。弧長パラメータで位置を返す。"""
    def __init__(self, pts):
        self.pts = [(float(x), float(y)) for x, y in pts]
        self.seg = [math.dist(self.pts[i], self.pts[i + 1]) for i in range(len(self.pts) - 1)]
        self.length = sum(self.seg)

    def point(self, u):
        s = max(0.0, min(1.0, u)) * self.length
        for i, L in enumerate(self.seg):
            if s <= L or i == len(self.seg) - 1:
                f = 0 if L == 0 else s / L
                (x1, y1), (x2, y2) = self.pts[i], self.pts[i + 1]
                return (x1 + (x2 - x1) * f, y1 + (y2 - y1) * f)
            s -= L
        return self.pts[-1]

    def d(self):
        return 'M' + ' L'.join(f'{x:.1f} {y:.1f}' for x, y in self.pts)


class Circle:
    """円周の軌道（時計回り、start は度）。"""
    def __init__(self, cx, cy, r, start=-90.0):
        self.cx, self.cy, self.r, self.start = cx, cy, r, start
        self.length = 2 * math.pi * r

    def point(self, u):
        a = math.radians(self.start + 360 * (u % 1.0))
        return (self.cx + self.r * math.cos(a), self.cy + self.r * math.sin(a))

    def d(self):
        x0, y0 = self.point(0); x1, y1 = self.point(0.5)
        return f'M{x0:.1f} {y0:.1f} A{self.r} {self.r} 0 1 1 {x1:.1f} {y1:.1f} A{self.r} {self.r} 0 1 1 {x0:.1f} {y0:.1f}'


# ---------------------------------------------------------------- 要素
class Token:
    """1粒のトラフィック。begin 秒に出発し、profile（(時刻, 進捗) の折れ線）で進み、終点で消える。"""
    def __init__(self, path, begin, travel, color=df.LINE, r=6, profile=None, fade=0.15, color_at=None):
        self.path, self.begin, self.travel, self.color, self.r, self.fade = path, begin, travel, color, r, fade
        self.profile = profile or [(0.0, 0.0), (travel, 1.0)]
        self.color_at = color_at  # (時刻, 色)：その時刻以降は色を変える

    def progress(self, tau):
        """出発からの経過 tau（0..travel）→ 進捗 0..1"""
        pr = self.profile
        if tau <= pr[0][0]: return pr[0][1]
        for (t1, u1), (t2, u2) in zip(pr, pr[1:]):
            if tau <= t2:
                return u1 + (u2 - u1) * (tau - t1) / (t2 - t1)
        return pr[-1][1]

    def state(self, t):
        tau = (t - self.begin) % CYCLE
        if tau > self.travel:
            return None
        u = self.progress(tau)
        op = 1.0 if self.fade <= 0 else min(1.0, tau / self.fade, (self.travel - tau) / self.fade)
        color = self.color
        if self.color_at and tau >= self.color_at[0]:
            color = self.color_at[1]
        return self.path.point(u), max(0.0, op), color

    def smil(self, pid):
        kt = [f'{t / CYCLE:.4f}' for t, _ in self.profile] + ['1']
        kp = [f'{u:.4f}' for _, u in self.profile] + [f'{self.profile[-1][1]:.4f}']
        T, f = self.travel, self.fade
        op_t = [0, 0, f, T - f, T, CYCLE]
        op_v = [0, 0, 1, 1, 0, 0]
        if T >= CYCLE - 1e-9:
            op_t, op_v = [0, f, T - f, T], [0, 1, 1, 0]
        out = [f'<circle r="{self.r}" fill="{self.color}" opacity="{1 if f <= 0 else 0}">']
        out.append(f'<animateMotion dur="{CYCLE}s" begin="-{(-self.begin) % CYCLE:.3f}s" repeatCount="indefinite" calcMode="linear" '
                   f'keyTimes="{";".join(kt)}" keyPoints="{";".join(kp)}"><mpath href="#{pid}" xlink:href="#{pid}"/></animateMotion>')
        if f > 0:
            out.append(f'<animate attributeName="opacity" dur="{CYCLE}s" begin="-{(-self.begin) % CYCLE:.3f}s" repeatCount="indefinite" calcMode="linear" '
                       f'keyTimes="{";".join(f"{t / CYCLE:.4f}" for t in op_t)}" values="{";".join(str(v) for v in op_v)}"/>')
        if self.color_at:
            tc = self.color_at[0]
            out.append(f'<animate attributeName="fill" dur="{CYCLE}s" begin="-{(-self.begin) % CYCLE:.3f}s" repeatCount="indefinite" calcMode="discrete" '
                       f'keyTimes="0;{tc / CYCLE:.4f}" values="{self.color};{self.color_at[1]}"/>')
        out.append('</circle>')
        return ''.join(out)


def pulse_fn(times, dur=0.6, peak=0.9):
    """複数の到着時刻の三角パルスを合成した opacity(t)。周期 6 秒で折り返す。"""
    def f(t):
        best = 0.0
        for ta in times:
            for sh in (-CYCLE, 0, CYCLE):
                x = t - (ta + sh)
                if 0 <= x <= dur:
                    best = max(best, peak * (x / (dur * 0.3)) if x < dur * 0.3 else peak * (1 - (x - dur * 0.3) / (dur * 0.7)))
        return best
    return f


def pulse_keyframes(times, dur=0.6, peak=0.9):
    f = pulse_fn(times, dur, peak)
    bps = {0.0, CYCLE}
    for ta in times:
        for sh in (-CYCLE, 0, CYCLE):
            for x in (0, dur * 0.3, dur):
                v = ta + sh + x
                if 0 <= v <= CYCLE: bps.add(round(v, 4))
    ts = sorted(bps)
    return ts, [f(t) for t in ts]


class Glow:
    """箱の外側に出る光の輪。times の各時刻に 0.6 秒だけ光る。"""
    def __init__(self, shape, times, color=df.LINE, peak=0.9, dur=0.6):
        self.shape, self.times, self.color, self.peak, self.dur = shape, [t % CYCLE for t in times], color, peak, dur
        self.fn = pulse_fn(self.times, dur, peak)

    def _base(self, extra):
        s = self.shape
        if s[0] == 'rect':
            _, x, y, w, h, rx = s
            return f'<rect x="{x - 4}" y="{y - 4}" width="{w + 8}" height="{h + 8}" rx="{rx + 4}" fill="none" stroke="{self.color}" stroke-width="7" filter="url(#glow)"{extra}/>'
        _, cx, cy, r = s
        return f'<circle cx="{cx}" cy="{cy}" r="{r + 6}" fill="none" stroke="{self.color}" stroke-width="6" filter="url(#glow)"{extra}/>'

    def static(self, t):
        return self._base(f' opacity="{self.fn(t):.3f}"')

    def smil(self):
        ts, vs = pulse_keyframes(self.times, self.dur, self.peak)
        anim = (f'<animate attributeName="opacity" dur="{CYCLE}s" repeatCount="indefinite" calcMode="linear" '
                f'keyTimes="{";".join(f"{t / CYCLE:.4f}" for t in ts)}" values="{";".join(f"{v:.3f}" for v in vs)}"/>')
        return self._base(' opacity="0"').replace('/>', f'>{anim}</rect>' if self.shape[0] == 'rect' else f'>{anim}</circle>')


class Bounce:
    """小さな印（円）が到着時に少し膨らむ。文字は動かさない。"""
    def __init__(self, cx, cy, r, times, color, grow=4):
        self.cx, self.cy, self.r, self.times, self.color, self.grow = cx, cy, r, [t % CYCLE for t in times], color, grow
        self.fn = pulse_fn(self.times, 0.5, 1.0)

    def static(self, t):
        k = self.fn(t)
        return f'<circle cx="{self.cx:.0f}" cy="{self.cy:.0f}" r="{self.r + self.grow * k:.2f}" fill="none" stroke="{self.color}" stroke-width="2" opacity="{0.35 + 0.65 * k:.3f}"/>'

    def smil(self):
        ts, vs = pulse_keyframes(self.times, 0.5, 1.0)
        kt = ';'.join(f'{t / CYCLE:.4f}' for t in ts)
        return (f'<circle cx="{self.cx:.0f}" cy="{self.cy:.0f}" r="{self.r}" fill="none" stroke="{self.color}" stroke-width="2" opacity="0.35">'
                f'<animate attributeName="r" dur="{CYCLE}s" repeatCount="indefinite" calcMode="linear" keyTimes="{kt}" values="{";".join(f"{self.r + self.grow * v:.2f}" for v in vs)}"/>'
                f'<animate attributeName="opacity" dur="{CYCLE}s" repeatCount="indefinite" calcMode="linear" keyTimes="{kt}" values="{";".join(f"{0.35 + 0.65 * v:.3f}" for v in vs)}"/></circle>')


class Breathe:
    """既存要素のゆっくりした明滅（stroke-opacity）。period 秒周期。"""
    def __init__(self, selector_d, period, lo=0.45, hi=1.0, color=df.ACCENT, width=3, dashed=False):
        self.d, self.period, self.lo, self.hi, self.color, self.width, self.dashed = selector_d, period, lo, hi, color, width, dashed

    def value(self, t):
        return self.lo + (self.hi - self.lo) * (0.5 - 0.5 * math.cos(2 * math.pi * t / self.period))

    def static(self, t):
        dash = ' stroke-dasharray="8 6"' if self.dashed else ''
        return f'<path d="{self.d}" fill="none" stroke="{self.color}" stroke-width="{self.width}" opacity="{self.value(t):.3f}"{dash}/>'

    def smil(self):
        dash = ' stroke-dasharray="8 6"' if self.dashed else ''
        return (f'<path d="{self.d}" fill="none" stroke="{self.color}" stroke-width="{self.width}" opacity="{self.lo}"{dash}>'
                f'<animate attributeName="opacity" dur="{self.period}s" repeatCount="indefinite" calcMode="spline" keySplines="0.4 0 0.6 1;0.4 0 0.6 1" '
                f'keyTimes="0;0.5;1" values="{self.lo};{self.hi};{self.lo}"/></path>')


class Scene:
    def __init__(self, name, static_svg, mask_boxes=True):
        self.name, self.static, self.mask_boxes = name, static_svg, mask_boxes
        self.paths, self.tokens, self.glows, self.bounces, self.breathes = {}, [], [], [], []

    def path(self, key, p):
        self.paths[key] = p; return p

    def mask(self):
        """静止図の箱（rx付きrect）と節点（円）を黒で塗り、粒を隠すマスク。"""
        parts = []
        for m in (re.finditer(r'<rect x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)" rx="([\d.]+)"', self.static) if self.mask_boxes else []):
            parts.append(f'<rect x="{m.group(1)}" y="{m.group(2)}" width="{m.group(3)}" height="{m.group(4)}" rx="{m.group(5)}" fill="#000"/>')
        for m in re.finditer(r'<circle cx="([\d.]+)" cy="([\d.]+)" r="(\d+)" fill="#fcfdfd"', self.static):
            if int(m.group(3)) >= 11:
                parts.append(f'<circle cx="{m.group(1)}" cy="{m.group(2)}" r="{m.group(3)}" fill="#000"/>')
        W = re.search(r'viewBox="0 0 (\d+) (\d+)"', self.static)
        return (f'<mask id="boxmask" maskUnits="userSpaceOnUse" x="0" y="0" width="{W.group(1)}" height="{W.group(2)}">'
                f'<rect x="0" y="0" width="{W.group(1)}" height="{W.group(2)}" fill="#fff"/>' + ''.join(parts) + '</mask>')

    def defs(self):
        return ('<defs><filter id="glow" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="3.5"/></filter>' + self.mask() +
                ''.join(f'<path id="{k}" d="{p.d()}" fill="none" stroke="none"/>' for k, p in self.paths.items()) + '</defs>')

    def _wrap(self, layer):
        i = self.static.rindex('</svg>')
        head = self.static.replace('<svg xmlns="http://www.w3.org/2000/svg"', '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"', 1)
        i = head.rindex('</svg>')
        return head[:i] + self.defs() + layer + '\n</svg>\n'

    def smil(self):
        layer = ['<g>'] + [g.smil() for g in self.glows] + [b.smil() for b in self.breathes] + ['</g>', '<g mask="url(#boxmask)">']
        for tk in self.tokens:
            pid = next(k for k, p in self.paths.items() if p is tk.path)
            layer.append(tk.smil(pid))
        layer += ['</g>', '<g>'] + [b.smil() for b in self.bounces] + ['</g>']
        return self._wrap('\n'.join(layer))

    def frame(self, t):
        layer = ['<g>'] + [g.static(t) for g in self.glows] + [b.static(t) for b in self.breathes] + ['</g>', '<g mask="url(#boxmask)">']
        for tk in self.tokens:
            st = tk.state(t)
            if st:
                (x, y), op, color = st
                layer.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{tk.r}" fill="{color}" opacity="{op:.3f}"/>')
        layer += ['</g>', '<g>'] + [b.static(t) for b in self.bounces] + ['</g>']
        return self._wrap('\n'.join(layer))


# ---------------------------------------------------------------- 各図
def scene_flow_bottleneck():
    sc = Scene('03-flow-bottleneck', df.fig_03_flow_bottleneck())
    p_pass = sc.path('pass', Poly([(180, 295), (385, 295), (615, 295), (825, 295)]))
    p_queue = sc.path('queue', Poly([(180, 295), (385, 295), (430, 236), (500, 206)]))
    done_times, queue_times = [], []
    for i in range(10):
        b = 0.6 * i
        if i % 5 in (0, 1, 2):
            sc.tokens.append(Token(p_pass, b, 3.0)); done_times.append(b + 3.0)
        else:
            sc.tokens.append(Token(p_queue, b, 1.8, color=df.ACCENT)); queue_times.append(b + 1.8)
    sc.glows.append(Glow(('rect', 710, 250, 230, 90, 12), done_times, df.GREEN))
    sc.glows.append(Glow(('rect', 416, 140, 184, 76, 6), queue_times, df.ACCENT, peak=0.8))
    sc.breathes.append(Breathe('M385 265 H615 V325 H385 Z', 1.5, lo=0.0, hi=0.6, color=df.ACCENT, width=3))
    return sc


def scene_mr_lifecycle():
    sc = Scene('04-mr-lifecycle', df.fig_04_mr_lifecycle())
    xs = [120, 320, 520, 720, 920]
    p = sc.path('line', Poly([(120, 250), (920, 250)]))
    stops = [0.0, 0.8, 3.2, 4.0, 4.8]
    profile = [(stops[k], k / 4) for k in range(5)]
    node_times = [[] for _ in xs]
    for i in range(5):
        b = 1.2 * i
        sc.tokens.append(Token(p, b, 4.8, profile=profile, color_at=(0.8, df.ACCENT)))
        for k in range(5):
            node_times[k].append(b + stops[k])
    for k, x in enumerate(xs):
        sc.glows.append(Glow(('circle', x, 250, 11), node_times[k], df.ACCENT if k in (1, 2) else df.LINE, peak=0.8))
    sc.breathes.append(Breathe('M320 292 V300 H520 V292', 1.2, lo=0.3, hi=1.0, color=df.ACCENT, width=3))
    return sc


def scene_stage_gate():
    sc = Scene('04-stage-gate', df.fig_04_stage_gate(), mask_boxes=False)
    speed = 221.0; lane = 290
    p_pass = sc.path('pass', Poly([(44, lane), (970, lane)]))
    drops = {1: 216, 2: 432, 3: 638}
    p_drop = {g: sc.path(f'drop{g}', Poly([(44, lane), (gx, lane), (gx, lane + 60)])) for g, gx in drops.items()}
    entries = {'b2': 256, 'b3': 472, 'b4': 678, 'final': 832}
    glow_times = {k: [] for k in entries}
    assign = {0: None, 1: 1, 2: 2, 3: None, 4: 1, 5: 3}
    for i in range(12):
        b = 0.5 * i
        g = assign[i % 6]
        if g is None:
            sc.tokens.append(Token(p_pass, b, p_pass.length / speed))
            for k, x in entries.items(): glow_times[k].append(b + (x - 44) / speed)
        else:
            gx = drops[g]; path = p_drop[g]
            sc.tokens.append(Token(path, b, path.length / speed, color_at=((gx - 44) / speed, df.ACCENT)))
            for k, x in entries.items():
                if x < gx: glow_times[k].append(b + (x - 44) / speed)
    boxes = {'b2': (256, 190, 150, 120), 'b3': (472, 190, 140, 120), 'b4': (678, 190, 130, 120), 'final': (832, 200, 150, 100)}
    for k, (x, y, w, h) in boxes.items():
        sc.glows.append(Glow(('rect', x, y, w, h, 12), glow_times[k], df.GREEN if k == 'final' else df.LINE, peak=0.7))
    return sc


def scene_feedback_loops():
    sc = Scene('03-feedback-loops', df.fig_03_feedback_loops())
    R = 172
    cR = sc.path('loopR', Circle(255, 385, R)); cB = sc.path('loopB', Circle(745, 385, R))
    # R：4粒が等速で6秒に1周
    for i in range(4):
        sc.tokens.append(Token(cR, 1.5 * i, CYCLE, fade=0.0))
    # B：3粒。「完了量の制約」（u=0.75）の手前で詰まる
    profB = [(0.0, 0.0), (3.3, 0.62), (4.68, 0.70), (6.0, 1.0)]
    def tB(u):
        for (t1, u1), (t2, u2) in zip(profB, profB[1:]):
            if u <= u2: return t1 + (t2 - t1) * (u - u1) / (u2 - u1)
        return 6.0
    for i in range(3):
        sc.tokens.append(Token(cB, 2.0 * i, CYCLE, profile=profB, fade=0.0, color_at=(3.3, df.ACCENT)))
    def node_box(cx, cy, k, n, bw):
        a = math.radians(-90 + 360 * k / n); x, y = cx + R * math.cos(a), cy + R * math.sin(a)
        return ('rect', x - bw / 2, y - 27, bw, 54, 12)
    for k in range(5):
        sc.glows.append(Glow(node_box(255, 385, k, 5, 150), [1.5 * i + 6 * k / 5 for i in range(4)], df.LINE, peak=0.6))
    for k in range(4):
        sc.glows.append(Glow(node_box(745, 385, k, 4, 160), [2.0 * i + tB(k / 4) for i in range(3)], df.ACCENT if k == 3 else df.LINE, peak=0.6))
    def ring(cx, cy, k, n):
        am = math.radians(-90 + 360 * (k + 0.5) / n)
        px, py = cx + R * math.cos(am), cy + R * math.sin(am)
        return px + math.cos(am) * 26, py + math.sin(am) * 26
    for k in range(5):
        x, y = ring(255, 385, k, 5)
        sc.bounces.append(Bounce(x, y, 12, [1.5 * i + 6 * (k + 0.5) / 5 for i in range(4)], df.LINE))
    for k in range(4):
        x, y = ring(745, 385, k, 4)
        sc.bounces.append(Bounce(x, y, 12, [2.0 * i + tB((k + 0.5) / 4) for i in range(3)], df.ACCENT if k == 3 else df.LINE))
    return sc


def scene_dual_output():
    sc = Scene('03-dual-output', df.fig_03_dual_output())
    fa = sc.path('fa', Poly([(165, 305), (370, 305), (485, 305), (600, 285), (690, 200), (825, 200)]))
    fb = sc.path('fb', Poly([(165, 305), (370, 305), (485, 305), (600, 325), (690, 410), (825, 410)]))
    ra = sc.path('ra', Poly([(825, 200), (825, 95), (165, 95), (165, 305)]))
    rb = sc.path('rb', Poly([(825, 410), (825, 520), (165, 520), (165, 305)]))
    t1, t2, res, prod = [], [], [], []
    for i in range(6):
        b = 1.0 * i
        fwd, ret = (fa, ra) if i % 2 == 0 else (fb, rb)
        tf = fwd.length / 250.0
        sc.tokens.append(Token(fwd, b, tf))
        (t1 if i % 2 == 0 else t2).append(b + tf)
        prod.append(b + 205 / 250.0)
        tr = ret.length / 420.0
        sc.tokens.append(Token(ret, b + tf + 0.2, tr, color=LIGHT, r=5))
        res.append(b + tf + 0.2 + tr)
    sc.glows.append(Glow(('rect', 690, 150, 270, 100, 12), t1, df.GREEN, peak=0.8))
    sc.glows.append(Glow(('rect', 690, 360, 270, 100, 12), t2, df.PURPLE, peak=0.8))
    sc.glows.append(Glow(('rect', 370, 250, 230, 110, 12), prod, df.LINE, peak=0.35))
    sc.glows.append(Glow(('rect', 50, 250, 230, 110, 12), res, df.LINE, peak=0.6))
    return sc


SCENES = {
    '03-flow-bottleneck': scene_flow_bottleneck,
    '04-mr-lifecycle': scene_mr_lifecycle,
    '04-stage-gate': scene_stage_gate,
    '03-feedback-loops': scene_feedback_loops,
    '03-dual-output': scene_dual_output,
}


# ---------------------------------------------------------------- 出力
def render_gif(sc: Scene, workdir: Path) -> Path:
    if not shutil.which('rsvg-convert') or not shutil.which('ffmpeg'):
        raise RuntimeError('GIF 生成には rsvg-convert と ffmpeg が必要である')
    frames = int(CYCLE * FPS)
    fdir = workdir / sc.name; fdir.mkdir(parents=True, exist_ok=True)
    assert sc.frame(0.0) == sc.frame(CYCLE), f'{sc.name}: t=0 と t=6 のフレームが一致しない'
    for k in range(frames):
        t = k / FPS
        svg_path = fdir / f'f{k:03d}.svg'
        svg_path.write_text(sc.frame(t), encoding='utf-8')
        subprocess.run(['rsvg-convert', '-w', str(GIF_WIDTH), '-b', df.BG, str(svg_path), '-o', str(fdir / f'f{k:03d}.png')], check=True)
    out = OUT_GIF / f'{sc.name}.gif'
    vf = 'format=rgb24,split[a][b];[a]palettegen=max_colors=96:stats_mode=diff[p];[b][p]paletteuse=dither=none:diff_mode=rectangle'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', str(fdir / 'f%03d.png'), '-vf', vf, '-loop', '0', str(out)], check=True)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--only', nargs='*', help='対象の図名（省略時は全部）')
    ap.add_argument('--no-gif', action='store_true', help='SVG のみ生成する')
    ap.add_argument('--workdir', type=Path, default=None, help='フレームの作業ディレクトリ（省略時は一時領域）')
    args = ap.parse_args()
    OUT_SVG.mkdir(parents=True, exist_ok=True); OUT_GIF.mkdir(parents=True, exist_ok=True)
    names = args.only or list(SCENES)
    work = args.workdir or Path(tempfile.mkdtemp(prefix='anim-'))
    for name in names:
        sc = SCENES[name]()
        (OUT_SVG / f'{name}.svg').write_text(sc.smil(), encoding='utf-8')
        print('svg ', name)
        if not args.no_gif:
            out = render_gif(sc, work)
            print('gif ', name, f'{out.stat().st_size / 1e6:.2f} MB')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
