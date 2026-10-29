#!/usr/bin/env python3
"""連載の図版（全29点）を決定論的に生成する。データ図は simulation/*.csv を読み、系列を計算する図はCSVも書き出す。

体裁：幅1000px、最小フォント14px（本文では720pxに縮小表示されるため、実寸で約10px）、同じ配色。
"""
from __future__ import annotations
import csv
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets'
SIM = ROOT / 'simulation'

BG = '#fcfdfd'; INK = '#18324b'; T1 = '#223e53'; T2 = '#36556d'; MUTED = '#5d6c75'
LINE = '#607a91'; STROKE = '#8ea6b2'; ACCENT = '#c0604a'; GREEN = '#5aa06f'; PURPLE = '#8a6cc1'; BAR = '#9dbbd3'; SOFT = '#eef3f1'
FILLS = ['#e1edf8', '#e0f0e9', '#f7e9d4', '#e9e4f5', '#f6e4e8']
FONT = 'font-family="sans-serif"'
MIN_FONT = 14


def esc(s: str) -> str:
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def text(x, y, s, size=17, weight=400, fill=T2, anchor='middle', extra=''):
    size = max(size, MIN_FONT)
    w = f' font-weight="{weight}"' if weight != 400 else ''
    return f'<text x="{x:.0f}" y="{y:.0f}" text-anchor="{anchor}" {FONT} font-size="{size:g}"{w} fill="{fill}"{extra}>{esc(s)}</text>'


def title(s):
    return text(50, 50, s, 24, 700, INK, 'start')


def box(x, y, w, h, fill, head, sub=None, hs=20, ss=15, stroke=STROKE, sw=1):
    out = [f'<rect x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="{h:.0f}" rx="12" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>']
    cx = x + w / 2
    if sub:
        out.append(text(cx, y + h / 2 - 4, head, hs, 700, T1))
        out.append(text(cx, y + h / 2 + 20, sub, ss))
    else:
        out.append(text(cx, y + h / 2 + 7, head, hs, 700, T1))
    return ''.join(out)


def arrow(x1, y1, x2, y2, dashed=False, color=LINE, width=3):
    dx, dy = x2 - x1, y2 - y1
    L = math.hypot(dx, dy); ux, uy = dx / L, dy / L
    ex, ey = x2 - ux * 10, y2 - uy * 10
    nx, ny = -uy, ux
    dash = ' stroke-dasharray="8 6"' if dashed else ''
    return (f'<path d="M{x1:.1f} {y1:.1f} L{ex:.1f} {ey:.1f}" stroke="{color}" stroke-width="{width}" fill="none"{dash}/>'
            f'<polygon points="{x2:.1f},{y2:.1f} {x2 - ux * 12 + nx * 7:.1f},{y2 - uy * 12 + ny * 7:.1f} {x2 - ux * 12 - nx * 7:.1f},{y2 - uy * 12 - ny * 7:.1f}" fill="{color}"/>')


def path_arrow(d, end, color=LINE, dashed=False, width=3):
    x, y, ux, uy = end; nx, ny = -uy, ux
    dash = ' stroke-dasharray="8 6"' if dashed else ''
    return (f'<path d="{d}" stroke="{color}" stroke-width="{width}" fill="none"{dash}/>'
            f'<polygon points="{x:.1f},{y:.1f} {x - ux * 12 + nx * 7:.1f},{y - uy * 12 + ny * 7:.1f} {x - ux * 12 - nx * 7:.1f},{y - uy * 12 - ny * 7:.1f}" fill="{color}"/>')


def note(y, s, size=15):
    return text(500, y, s, size, 400, MUTED)


def svg(w, h, label, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{esc(label)}">\n'
            f'<rect width="100%" height="100%" fill="{BG}"/>\n' + '\n'.join(body) + '\n</svg>\n')


def loop(cx, cy, R, nodes, bw, bh, label, fill_offset=0, start=-90, polarity=None, label_size=24):
    """円環上にノードを置き、時計回りの矢頭を付けた因果ループ。polarity は各リンク（i→i+1）の符号リスト（'+'/'-'）。"""
    n = len(nodes)
    out = [f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="none" stroke="{LINE}" stroke-width="3"/>']
    for i in range(n):
        am = math.radians(start + 360 * (i + 0.5) / n)
        px, py = cx + R * math.cos(am), cy + R * math.sin(am)
        tx, ty = -math.sin(am), math.cos(am)
        nx, ny = math.cos(am), math.sin(am)
        neg = polarity is not None and polarity[i] == '-'
        color = ACCENT if neg else LINE
        tip = (px + tx * 11, py + ty * 11); b1 = (px - tx * 9 + nx * 8, py - ty * 9 + ny * 8); b2 = (px - tx * 9 - nx * 8, py - ty * 9 - ny * 8)
        out.append(f'<polygon points="{tip[0]:.1f},{tip[1]:.1f} {b1[0]:.1f},{b1[1]:.1f} {b2[0]:.1f},{b2[1]:.1f}" fill="{color}"/>')
        if polarity is not None:
            lx, ly = px + nx * 26, py + ny * 26
            out.append(f'<circle cx="{lx:.0f}" cy="{ly:.0f}" r="12" fill="{BG}" stroke="{color}" stroke-width="2"/>')
            out.append(text(lx, ly + 5, polarity[i], 15, 700, color))
    for i, (head, sub) in enumerate(nodes):
        a = math.radians(start + 360 * i / n)
        x, y = cx + R * math.cos(a), cy + R * math.sin(a)
        out.append(box(x - bw / 2, y - bh / 2, bw, bh, FILLS[(i + fill_offset) % 5], head, sub, hs=16, ss=14))
    if label:
        out.append(f'<circle cx="{cx}" cy="{cy}" r="30" fill="{BG}" stroke="{LINE}" stroke-width="2"/>')
        out.append(text(cx, cy + 9, label, label_size, 700, INK))
    return out


def bars(x0, y0, w, h, labels, values, vmax, highlight=None, outline=None, limit=None, limit_label=''):
    out = [f'<path d="M{x0} {y0} V{y0 + h} H{x0 + w}" stroke="{STROKE}" stroke-width="2" fill="none"/>']
    n = len(values); slot = w / n; bwid = slot * 0.56
    for i, (lab, v) in enumerate(zip(labels, values)):
        bx = x0 + slot * i + (slot - bwid) / 2; bh = h * v / vmax; by = y0 + h - bh
        fill = ACCENT if i == highlight else BAR
        stroke = f' stroke="{ACCENT}" stroke-width="3" stroke-dasharray="6 4"' if i == outline else ''
        out.append(f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bwid:.1f}" height="{bh:.1f}" rx="4" fill="{fill}"{stroke}/>')
        out.append(text(bx + bwid / 2, by - 8, str(v), 16, 700, T1))
        out.append(text(bx + bwid / 2, y0 + h + 24, lab, 15))
    if limit is not None:
        ly = y0 + h - h * limit / vmax
        out.append(f'<path d="M{x0} {ly:.1f} H{x0 + w}" stroke="{ACCENT}" stroke-width="2" stroke-dasharray="8 6"/>')
        if limit_label:
            out.append(text(x0 + w, ly - 8, limit_label, 14, 700, ACCENT, 'end'))
    return out


def line_chart(x0, y0, w, h, xmin, xmax, ymin, ymax, xticks, yticks, xlabel, ylabel, series, legend=True, zero_line=False, end_labels=True, xfmt=str, yfmt=str):
    """series: [(label, [(x, y), ...], color, {'points': bool, 'dashed': bool, 'end_label': str|None})]"""
    out = []
    def px(x): return x0 + w * (x - xmin) / (xmax - xmin)
    def py(y): return y0 + h - h * (y - ymin) / (ymax - ymin)
    for yv in yticks:
        out.append(f'<path d="M{x0} {py(yv):.1f} H{x0 + w}" stroke="{STROKE}" stroke-width="1" stroke-dasharray="2 6"/>')
        out.append(text(x0 - 12, py(yv) + 5, yfmt(yv), 14, anchor='end'))
    for xv in xticks:
        out.append(f'<path d="M{px(xv):.1f} {y0 + h} v6" stroke="{STROKE}" stroke-width="2"/>')
        out.append(text(px(xv), y0 + h + 24, xfmt(xv), 14))
    out.append(f'<path d="M{x0} {y0 - 6} V{y0 + h} H{x0 + w + 6}" stroke="{STROKE}" stroke-width="2" fill="none"/>')
    if zero_line and ymin < 0 < ymax:
        out.append(f'<path d="M{x0} {py(0):.1f} H{x0 + w}" stroke="{T1}" stroke-width="1.5"/>')
    out.append(text(x0 + w / 2, y0 + h + 52, xlabel, 15, 700, T1))
    out.append(text(x0 - 62, y0 + h / 2, ylabel, 15, 700, T1, 'middle', f' transform="rotate(-90 {x0 - 62:.0f} {y0 + h / 2:.0f})"'))
    for j, (label, pts, color, opt) in enumerate(series):
        d = ' '.join(f'{px(x):.1f},{py(y):.1f}' for x, y in pts)
        dash = ' stroke-dasharray="8 6"' if opt.get('dashed') else ''
        out.append(f'<polyline points="{d}" fill="none" stroke="{color}" stroke-width="3"{dash}/>')
        if opt.get('points', True):
            for x, y in pts:
                out.append(f'<circle cx="{px(x):.1f}" cy="{py(y):.1f}" r="4.5" fill="{color}" stroke="#fff" stroke-width="1.5"/>')
        if end_labels and opt.get('end_label') is not None:
            x, y = pts[-1]
            out.append(text(px(x) + 12, py(y) + 5, opt['end_label'], 15, 700, color, 'start'))
        if legend:
            ly = y0 + 14 + j * 24
            out.append(f'<rect x="{x0 + 18}" y="{ly - 6}" width="28" height="6" rx="3" fill="{color}"/>')
            out.append(text(x0 + 56, ly + 1, label, 14, 700, color, 'start'))
    return out, px, py


def read_csv(name):
    with (SIM / name).open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def write_csv(name, header, rows):
    with (SIM / name).open('w', encoding='utf-8', newline='') as f:
        w = csv.writer(f); w.writerow(header); w.writerows(rows)


# =====================================================================
# 第1回
# =====================================================================
def fig_01_resource_system():
    body = [title('経営資源から価値を生み出す循環')]
    steps = [('経営資源', '人的・技術・財務・知識・組織・関係・権利'), ('組織能力', '資源を組み合わせ、反復可能な仕事へ変換する'),
             ('顧客価値と収益', '成果物・信頼・対価を獲得する'), ('再投資と能力蓄積', '利益と経験を次の生産力へ転換する')]
    ys = [90, 200, 310, 420]
    for i, ((h, s), y) in enumerate(zip(steps, ys)):
        body.append(box(140, y, 760, 82, FILLS[i], h, s, hs=20, ss=15))
        if i < 3: body.append(arrow(520, y + 82, 520, ys[i + 1]))
    body.append(path_arrow('M140 461 H70 V131 H128', (140, 131, 1, 0), dashed=True))
    body.append(text(70, 300, '再投入', 14, 700, LINE, 'middle', ' transform="rotate(-90 70 300)"'))
    body.append(note(548, '循環を成立させるには、学習・改善・再配分が必要。再投入（破線）が無ければ一方向の投入→成果で終わる'))
    return svg(1000, 575, '経営資源が組織能力を経て顧客価値と収益になり、再投資と能力蓄積を通じて経営資源へ戻る循環', body)


def fig_01_conversion_chain():
    steps = [('① ヒト × 時間', '→ ソースコード・設計書'), ('② ヒト × 情報', '→ ノウハウ・技術的知識'), ('③ ノウハウ × 仕組み', '→ 標準化・自動化'),
             ('④ カネ × 仕組み', '→ スケール可能な開発基盤'), ('⑤ 品質 × 納期遵守', '→ 顧客の信用'), ('⑥ 信用 × 顧客関係', '→ 継続受注・収益')]
    body = [title('6つの資源変換と再帰構造')]
    bw, bh = 250, 84
    xs = [110, 375, 640]
    for i, (h, s) in enumerate(steps[:3]):
        body.append(box(xs[i], 110, bw, bh, FILLS[i % 5], h, s, hs=18, ss=14))
        if i < 2: body.append(arrow(xs[i] + bw, 152, xs[i + 1], 152))
    for i, (h, s) in enumerate(steps[3:]):
        x = xs[2 - i]
        body.append(box(x, 300, bw, bh, FILLS[(i + 3) % 5], h, s, hs=18, ss=14))
        if i < 2: body.append(arrow(x, 342, xs[1 - i] + bw, 342))
    body.append(arrow(765, 194, 765, 300))
    body.append(path_arrow('M110 342 H55 V152 H98', (110, 152, 1, 0), dashed=True, width=3))
    body.append(text(55, 247, '再投入', 14, 700, LINE, 'middle', ' transform="rotate(-90 55 247)"'))
    body.append(text(500, 445, '⑥の成果（収益・信用）は①の資源（ヒト・時間・情報）へ再投入される（破線）', 16, 700, T1))
    body.append(note(478, '変換は資源の用途・価値創出機能を変える過程。知識は形式化しても元の人間から失われない'))
    return svg(1000, 505, '6つの資源変換が環をなし、成果が次の活動の資源になる再帰構造', body)


# =====================================================================
# 第2回
# =====================================================================
def fig_02_three_levels():
    body = [title('資源と能力の3階層')]
    levels = [('Level 3　変革能力 Dynamic Capability', '既存の資源や能力を創出・変更・再構成する。例：モデル更新を受けてテスト方式と責任分担を変える', FILLS[2], 100),
              ('Level 2　組織能力 Capability', '複数の資源を組み合わせ、成果を反復して生む。例：仕様からテストを設計し、実行・検証する', FILLS[1], 230),
              ('Level 1　基礎資源 Resource', '企業が保有・利用できるもの。例：技術者、GitLab、Playwright、Agent Skill、業務仕様', FILLS[0], 360)]
    for h, s, fill, y in levels:
        body.append(box(120, y, 760, 86, fill, h, s, hs=19, ss=14))
    body.append(arrow(500, 360, 500, 316 + 2, width=3)); body.append(text(520, 342, '統合して、反復可能な成果にする', 14, 700, LINE, 'start'))
    body.append(arrow(500, 230, 500, 186 + 2, width=3)); body.append(text(520, 212, '能力そのものを作り替える', 14, 700, LINE, 'start'))
    body.append(note(492, '保有量と組織能力の大きさは比例しない。Skillを100個持つことと、10個のSkillで成果を反復することは別である'))
    return svg(1000, 520, '基礎資源を統合して組織能力にし、組織能力を再構成する変革能力までの3階層を下から上へ示す図', body)


def fig_02_four_dimensions():
    body = [title('経営資源を4つの次元で捉える')]
    cx, cy = 500, 340
    body.append(box(cx - 120, cy - 42, 240, 84, '#fff', 'ある資源', '例：Agent Skill', hs=20, ss=14, stroke=LINE))
    dims = [('① 種類', '何を持っているか', '技術資源・知識資源', 500, 130),
            ('② 性質', 'どう振る舞うか', '複製可能・非競合・陳腐化する', 500, 550),
            ('③ 機能', '何を実現できるか', '自律検証という組織能力の構成要素', 170, 340),
            ('④ 戦略価値', 'なぜ優位性を生むか', '業務知識と統合されるほど模倣困難', 830, 340)]
    for i, (h, q, ex, x, y) in enumerate(dims):
        w, hh = 290, 96
        body.append(f'<rect x="{x - w / 2}" y="{y - hh / 2}" width="{w}" height="{hh}" rx="12" fill="{FILLS[i]}" stroke="{STROKE}"/>')
        body.append(text(x, y - 14, h, 19, 700, T1)); body.append(text(x, y + 9, q, 14)); body.append(text(x, y + 31, ex, 14, 400, MUTED))
        dx, dy = x - cx, y - cy
        if dx == 0:
            y1 = cy - 42 if dy < 0 else cy + 42; y2 = y + hh / 2 if dy < 0 else y - hh / 2
            body.append(f'<path d="M{cx} {y1} V{y2}" stroke="{LINE}" stroke-width="3"/>')
        else:
            x1 = cx - 120 if dx < 0 else cx + 120; x2 = x + w / 2 if dx < 0 else x - w / 2
            body.append(f'<path d="M{x1} {cy} H{x2}" stroke="{LINE}" stroke-width="3"/>')
    body.append(note(640, '4次元は独立した分類軸として組み合わせる。既存理論を統合した分析モデルであり、単一の理論ではない'))
    return svg(1000, 670, '一つの資源を種類・性質・機能・戦略価値の4次元から見る図', body)


def fig_02_theory_timeline():
    """縦型タイムライン。年が密集する1989〜1997を重ねずに並べるため、行は等間隔（年に比例しない）。"""
    body = [title('経営資源論の発展：保有から組み合わせへ、そして変革能力へ')]
    events = [(1959, 'ペンローズ', '企業成長の理論', '資源と、資源が提供するサービスは異なる'),
              (1989, 'ディーリックス／クール', '資産ストックの蓄積', '買える資源と、時間をかけて蓄積する資源を区別する'),
              (1991, 'バーニー', '資源ベース理論（RBV）', '希少性・模倣困難性が競争優位を左右する'),
              (1996, 'グラント', '知識ベース理論（KBV）', '企業は専門知識を統合する仕組みである'),
              (1997, 'ティースら', 'ダイナミック・ケイパビリティ', '資源を再構成する能力そのものが経営能力になる'),
              (2007, 'ティース', '変革能力の3要素', 'Sensing・Seizing・Transforming')]
    ax = 150; y0 = 130; step = 92
    body.append(f'<path d="M{ax} {y0 - 30} V{y0 + step * 5 + 30}" stroke="{STROKE}" stroke-width="3"/>')
    for i, (yr, who, what, why) in enumerate(events):
        y = y0 + step * i
        body.append(text(ax - 18, y + 6, str(yr), 16, 700, LINE, 'end'))
        body.append(f'<circle cx="{ax}" cy="{y}" r="8" fill="{LINE}" stroke="#fff" stroke-width="2"/>')
        body.append(f'<path d="M{ax + 8} {y} H{ax + 30}" stroke="{STROKE}" stroke-width="2"/>')
        body.append(f'<rect x="{ax + 30}" y="{y - 38}" width="570" height="76" rx="10" fill="#fff" stroke="{STROKE}"/>')
        body.append(text(ax + 46, y - 12, who, 16, 700, T1, 'start'))
        body.append(text(ax + 46, y + 10, what, 14, 400, T2, 'start'))
        body.append(text(ax + 46, y + 30, why, 14, 400, MUTED, 'start'))
    # 視点の帯（縦のバー）。対象の回の行にまたがる
    bands = [('資源の保有', 0, 2, FILLS[0]), ('資源の組み合わせ・サービス', 0, 4, FILLS[1]), ('資源と能力の変革', 4, 5, FILLS[3])]
    body.append(text(865, y0 - 46, '視点の移り変わり', 14, 700, MUTED))
    for j, (lab, a, b, fill) in enumerate(bands):
        x = 780 + j * 60; ya = y0 + step * a - 36; yb = y0 + step * b + 36
        body.append(f'<rect x="{x}" y="{ya}" width="48" height="{yb - ya}" rx="10" fill="{fill}" stroke="{STROKE}"/>')
        cy = (ya + yb) / 2
        body.append(text(x + 24, cy, lab, 14, 700, T1, 'middle', f' transform="rotate(-90 {x + 24} {cy:.0f})"'))
    body.append(note(y0 + step * 5 + 76, '視点は「何を持つか」から「どう組み合わせるか」、さらに「資源と能力をどう作り替えるか」へ移ってきた'))
    body.append(note(y0 + step * 5 + 98, '行は等間隔に並べており、年の間隔には比例しない'))
    return svg(1000, y0 + step * 5 + 126, 'ペンローズ（1959）からティース（2007）までの経営資源論の系譜を縦に並べ、保有から組み合わせ、変革能力への視点の移行を帯で示した図', body)


def fig_02_asset_stock_bathtub():
    body = [title('買える資源と、蓄積しなければ得られない資源')]
    def tub(x, label, examples, water_h, flow_w, stream_color):
        body.append(text(x + 180, 108, label, 19, 700, T1))
        body.append(f'<path d="M{x} 200 V380 Q{x} 410 {x + 30} 410 H{x + 330} Q{x + 360} 410 {x + 360} 380 V200" fill="#fff" stroke="{LINE}" stroke-width="3"/>')
        body.append(f'<path d="M{x + 6} {410 - 6 - water_h} V378 Q{x + 6} 404 {x + 30} 404 H{x + 330} Q{x + 354} 404 {x + 354} 378 V{410 - 6 - water_h} Z" fill="{FILLS[0]}"/>')
        body.append(f'<rect x="{x + 100}" y="140" width="110" height="12" rx="4" fill="{LINE}"/>')
        body.append(f'<rect x="{x + 180 - 20:.0f}" y="150" width="40" height="28" rx="4" fill="{LINE}"/>')
        body.append(f'<rect x="{x + 180 - flow_w / 2:.0f}" y="178" width="{flow_w}" height="{410 - 6 - water_h - 178}" fill="{stream_color}" opacity="0.85"/>')
        for i, e in enumerate(examples):
            body.append(text(x + 180, 442 + i * 22, e, 14, 400, MUTED))
    tub(80, '購入・調達できる資源', ['AIモデルのAPI利用権、CI/CDサービス', 'テスト自動化ツール、外部の専門技術者'], 160, 44, '#bcd3e6')
    body.append(text(260, 300, '蛇口を開ければすぐ満たせる', 15, 700, LINE))
    tub(560, '内部で蓄積する必要がある資源', ['AIを使いこなす組織能力、検証の習慣', 'システム固有のテスト知識、チーム間の協調関係'], 60, 8, '#bcd3e6')
    body.append(text(740, 300, '流入速度に上限があり、時間がかかる', 15, 700, ACCENT))
    body.append(arrow(914, 398, 975, 398, dashed=True, color=ACCENT, width=3))
    body.append(text(985, 384, '陳腐化・離職で流出', 14, 700, ACCENT, 'end'))
    body.append(note(505, 'ディーリックス／クール（1989）の資産ストックの比喩。'))
    body.append(note(527, '資金を一気に投じても蓄積資産の流入は速くならず、この時間差が競争優位の持続性を生む'))
    return svg(1000, 552, '蛇口を開ければすぐ満たせる購入資源の浴槽と、流入速度に上限がある蓄積資源の浴槽の比較', body)


# =====================================================================
# 第3回
# =====================================================================
def fig_03_flow_system():
    body = [title('Stock・Flow・Transformation・Feedback：6要素の基本モデル')]
    steps = [('① 保有 Stock', '人的能力・知識資産・共通部品'), ('② 投入 Flow', '採用・投資・案件への配置'), ('③ 変換 Transformation', '生産・標準化・教育・自動化'),
             ('④ 成果 Output', '顧客価値・利益・納品物'), ('⑤ 蓄積 Accumulation', '経験・知識・信頼の増加'), ('⑥ 再投入 Feedback', '評価・再投資・ルール更新')]
    bw, bh = 250, 84
    xs = [110, 375, 640]
    for i, (h, s) in enumerate(steps[:3]):
        body.append(box(xs[i], 110, bw, bh, FILLS[i % 5], h, s, hs=17, ss=14))
        if i < 2: body.append(arrow(xs[i] + bw, 152, xs[i + 1], 152))
    for i, (h, s) in enumerate(steps[3:]):
        x = xs[2 - i]
        body.append(box(x, 300, bw, bh, FILLS[(i + 3) % 5], h, s, hs=17, ss=14))
        if i < 2: body.append(arrow(x, 342, xs[1 - i] + bw, 342))
    body.append(arrow(765, 194, 765, 300))
    body.append(path_arrow('M110 342 H55 V152 H98', (110, 152, 1, 0), dashed=True))
    body.append(text(55, 247, '循環', 14, 700, LINE, 'middle', ' transform="rotate(-90 55 247)"'))
    body.append(text(500, 445, '⑥から①へ戻る破線が無ければ、活動は一方向の「投入 → 成果」で終わる', 16, 700, T1))
    body.append(note(478, '基礎モデル。実際には変換過程からの消耗・流出と、外部環境からのフィードバックも存在する'))
    return svg(1000, 505, '保有、投入、変換、成果、蓄積、再投入の6要素が環をなす資源変換システムの基本モデル', body)


def fig_03_flow_bottleneck():
    body = [title('流入が処理能力を上回ると、滞留が積み上がる')]
    body.append(box(60, 250, 230, 90, FILLS[0], '実装完了（流入）', '20件/日', hs=19, ss=16))
    body.append(arrow(290, 295, 385, 295))
    body.append(f'<rect x="385" y="265" width="230" height="60" rx="12" fill="{FILLS[2]}" stroke="{ACCENT}" stroke-width="3"/>')
    body.append(text(500, 290, 'レビュー処理能力', 17, 700, T1)); body.append(text(500, 312, '12件/日（制約）', 15, 700, ACCENT))
    body.append(arrow(615, 295, 710, 295))
    body.append(box(710, 250, 230, 90, FILLS[1], '完了', '12件/日', hs=19, ss=16))
    for k in range(5):
        body.append(f'<rect x="{420 + k * 4}" y="{200 - k * 14}" width="160" height="12" rx="3" fill="{ACCENT}" opacity="{0.35 + k * 0.13:.2f}"/>')
    body.append(arrow(500, 225, 500, 262, color=ACCENT, width=2))
    body.append(text(500, 112, '未レビュー（滞留Stock）', 17, 700, T1))
    body.append(text(500, 134, '20 − 12 = 8件/日ずつ増加 → 10営業日後に80件', 15, 400, ACCENT))
    body.append(text(500, 395, '実装能力を30件/日へ上げても完了は12件/日のまま。滞留は18件/日ずつ増え、10営業日で180件', 16, 700, T1))
    body.append(note(428, '初期滞留0件、毎日一定流入、差し戻し・休日・作業サイズ差を無視した単純化モデル'))
    return svg(1000, 460, '流入20件/日に対し処理能力12件/日のレビュー工程で滞留が増える図', body)


def fig_03_knowledge_stock():
    K0, add, decay, years, stop_after = 100.0, 25.0, 0.10, 6, 3
    cont, stop = [K0], [K0]
    for t in range(1, years + 1):
        cont.append(round(cont[-1] * (1 - decay) + add, 2))
        stop.append(round(stop[-1] * (1 - decay) + (add if t <= stop_after else 0), 2))
    write_csv('03-knowledge-stock.csv', ['year', 'continue_adding', 'stop_after_year3'], [[t, cont[t], stop[t]] for t in range(years + 1)])
    body = [title('組織知ストックの推移（仮想）：追加を止めると劣化が上回る')]
    chart, px, py = line_chart(110, 110, 760, 360, 0, 6, 0, 200, range(0, 7), range(0, 201, 50), '年', '知識資産指数',
                               [('毎年25を追加、毎年10%劣化', list(enumerate(cont)), LINE, {'end_label': f'{cont[-1]:.0f}'}),
                                ('4年目以降は追加を停止', list(enumerate(stop)), ACCENT, {'end_label': f'{stop[-1]:.0f}', 'dashed': True})])
    body += chart
    body.append(f'<path d="M{px(3):.1f} {py(0):.1f} V{py(200):.1f}" stroke="{STROKE}" stroke-width="1.5" stroke-dasharray="4 6"/>')
    body.append(text(px(3) + 8, py(195), '追加停止', 14, 700, ACCENT, 'start'))
    body.append(note(560, 'K(t+1) = 0.9 K(t) + 25、K(0) = 100。「知識資産指数」は定義して測る必要があり、図は実測値ではない'))
    return svg(1000, 590, '知識資産指数の6年間の推移。毎年追加すると170へ増え、4年目以降に追加を止めると10%の劣化で103まで下がる', body)


def fig_03_feedback_loops():
    body = [title('強化ループと抑制ループ')]
    body.append(text(250, 96, '強化ループ R：成果が次の成果を生む', 18, 700, T1))
    body.append(text(750, 96, '抑制ループ B：成長が新しい制約を生む', 18, 700, T1))
    body.append(f'<path d="M500 86 V650" stroke="{STROKE}" stroke-width="1" stroke-dasharray="4 6"/>')
    body += loop(255, 385, 172, [('開発活動', '案件の遂行'), ('経験', '障害対応・判断'), ('標準・Skill', '形式化・配布'), ('生産性向上', '工数減・品質向上'), ('改善機会', '余力と知見')],
                 150, 54, 'R', polarity=['+', '+', '+', '+', '+'])
    body += loop(745, 385, 172, [('AI実装量の増加', '流入が増える'), ('レビュー待ち増加', '滞留Stock'), ('リードタイム悪化', '提供速度の低下'), ('完了量の制約', '投入を抑える圧力')],
                 160, 54, 'B', fill_offset=2, polarity=['+', '+', '+', '-'])
    body.append(text(250, 630, '成立条件：経験が検証・共有され、標準やSkillへ反映されること', 14, 400, MUTED))
    body.append(text(750, 630, '対策：WIP制限、レビュー自動化、承認権限の再設計', 14, 400, MUTED))
    body.append(note(672, '＋は同方向、−は逆方向の因果。Rは＋だけで増幅し、Bは−を1つ含み目標との偏差を縮める。経験が個人に閉じるとRは途中で断絶する'))
    return svg(1000, 700, '強化ループ（開発活動→経験→標準・Skill→生産性→改善機会）と抑制ループ（AI実装増→レビュー待ち→リードタイム悪化→完了量制約→投入抑制）', body)


def fig_03_dual_output():
    body = [title('経営は二重の価値創出を管理する')]
    body.append(box(50, 250, 230, 110, FILLS[0], '経営資源', '人材・知識・技術・資金・組織・関係', hs=20, ss=14))
    body.append(arrow(280, 305, 370, 305))
    body.append(box(370, 250, 230, 110, FILLS[2], '生産活動', '案件遂行・設計・実装・検証', hs=20, ss=14))
    body.append(arrow(600, 285, 690, 200))
    body.append(arrow(600, 325, 690, 410))
    body.append(box(690, 150, 270, 100, FILLS[1], '第一の成果', '現在の価値：納品・対価・売上', hs=19, ss=14))
    body.append(box(690, 360, 270, 100, FILLS[3], '第二の成果', '将来の能力：経験・知識・技術・信頼', hs=19, ss=14))
    body.append(path_arrow('M825 150 V95 H165 V238', (165, 250, 0, 1), dashed=True))
    body.append(path_arrow('M825 460 V520 H165 V372', (165, 360, 0, -1), dashed=True))
    body.append(text(500, 85, '利益の再投資', 14, 700, LINE))
    body.append(text(500, 542, '蓄積した能力の再投入（次の活動の生産能力を増強）', 14, 700, LINE))
    body.append(note(588, '実線は価値創出、破線は再投資と資源の再投入。第二の成果を測らない経営は、将来の生産能力の低下に気づけない'))
    return svg(1000, 612, '生産活動が現在の価値と未来の価値創出能力という二重の成果を生み、両方が経営資源へ戻る図', body)


# =====================================================================
# 第4回
# =====================================================================
def fig_04_toc():
    body = [title('制約理論（TOC）の5つの集中ステップ：制約は移動する')]
    body += loop(500, 405, 235, [('① 制約を特定する', 'MR作成→マージの時間を分析'), ('② 制約を最大限活用する', '観点標準化・事前CI・MR分割'), ('③ 他の活動を制約に従属させる', '実装の開始量を調整する'),
                                 ('④ 制約の能力を高める', 'レビュアー育成・AI一次レビュー'), ('⑤ 制約を再評価する', '次の制約：検証・承認・要求')], 270, 60, '', fill_offset=0)
    body.append(text(500, 398, '制約が解消すると', 16, 700, T1)); body.append(text(500, 422, '次の制約へ移る', 16, 700, T1))
    body.append(note(705, '特に重要なのは③。非制約工程に「余力があるから」と作業を投入すると滞留が増える。投入量は制約の処理能力に合わせる'))
    return svg(1000, 735, '制約を特定し、活用し、他を従属させ、能力を高め、再評価するという5ステップが循環する図', body)


def fig_04_constraint_shift():
    rows = read_csv('04-process-capacity.csv')
    labels = [r['stage'] for r in rows]
    before = [int(r['before_per_day']) for r in rows]; after = [int(r['after_review_boost_per_day']) for r in rows]
    body = [title('制約は解消すると移動する')]
    body.append(text(270, 98, '現状：レビューが制約（上限10件/日）', 17, 700, T1))
    body.append(text(730, 98, 'レビューを16件/日へ増強：次は検証が制約（上限14件/日）', 17, 700, T1))
    body += bars(70, 130, 400, 330, labels, before, 28, highlight=before.index(min(before)), limit=min(before))
    body += bars(530, 130, 400, 330, labels, after, 28, highlight=after.index(min(after)), limit=min(after))
    body.append(text(500, 300, '→', 30, 700, LINE))
    body.append(note(528, '縦軸は1日あたり処理能力（件/日）。赤の棒が制約工程、破線が理論上限'))
    body.append(note(550, '各工程が必須で同じ作業単位を処理し、手戻りと変動を無視した単純化モデル'))
    return svg(1000, 578, '5工程の処理能力の棒グラフ。現状はレビュー10件/日が制約、レビューを16件/日へ増強すると検証14件/日が次の制約になる', body)


def fig_04_review_backlog():
    rows = read_csv('04-review-backlog.csv')
    s20 = [(int(r['day']), float(r['incoming_20_review_12'])) for r in rows]
    s30 = [(int(r['day']), float(r['incoming_30_review_12'])) for r in rows]
    body = [title('レビュー滞留の増加（仮想）：実装を速めるほど未レビューが積み上がる')]
    chart, px, py = line_chart(110, 110, 760, 360, 0, 10, 0, 200, range(0, 11), range(0, 201, 40), '経過営業日', '未レビューMR数',
                               [('実装20件/日（レビュー12件/日）', s20, LINE, {'end_label': '80件'}),
                                ('実装30件/日（レビュー12件/日）', s30, ACCENT, {'end_label': '180件'})])
    body += chart
    body.append(note(560, 'B(d) = max(0, λ − μ) × d。初期滞留0件、毎日一定流入、差し戻し・休日・作業サイズ差・処理変動は考慮しない'))
    return svg(1000, 590, '実装20件/日と30件/日の未レビューMR数の推移。10営業日後にそれぞれ80件と180件になる', body)


def fig_04_utilization_queue():
    rows = read_csv('04-mm1-wait.csv')
    pts = [(float(r['utilization_pct']), float(r['wait_days'])) for r in rows]
    mu = 10.0
    curve = [(u, (u / 100) / (mu * (1 - u / 100))) for u in [30 + i * 0.5 for i in range(int((98.5 - 30) / 0.5) + 1)]]
    body = [title('稼働率と待ち時間（M/M/1モデル）：高稼働ほど待ちは非線形に増える')]
    chart, px, py = line_chart(110, 110, 760, 360, 30, 100, 0, 6, range(30, 101, 10), range(0, 7), '稼働率（%）', '平均待ち時間（日）',
                               [('平均待ち時間（レビュー能力10件/日）', curve, LINE, {'points': False}),
                                ('CSVの計算点', pts, LINE, {'end_label': None})], legend=False)
    body += chart
    body.append(f'<rect x="{px(31)}" y="{py(5.9)}" width="28" height="6" rx="3" fill="{LINE}"/>'); body.append(text(px(31) + 38, py(5.9) + 7, 'Wq = ρ / (μ(1−ρ))、μ = 10件/日', 14, 700, LINE, 'start'))
    for u, d, dy in ((80, 0.4, -30), (95, 1.9, -30)):
        body.append(f'<circle cx="{px(u):.1f}" cy="{py(d):.1f}" r="7" fill="{ACCENT}" stroke="#fff" stroke-width="2"/>')
        body.append(text(px(u) - 10, py(d) + dy, f'{u}%：{d:.1f}日', 15, 700, ACCENT, 'end'))
    body.append(text(px(62), py(3.3), '80% → 95%：15ポイントで待ち時間は4.75倍', 15, 700, ACCENT))
    body.append(note(560, 'モデル上の値であり実測の予測ではない。複数レビュアー、優先度、差し戻し、レビュー所要時間の分布で変わる'))
    return svg(1000, 590, '稼働率30%から98%までの平均待ち時間の曲線。80%で0.4日、95%で1.9日と非線形に増える', body)


def fig_04_lp_feasible_region():
    case = {r['item']: r for r in read_csv('04-lp-case.csv')}
    xa_opt = float(case['optimal_units']['project_A']); xb_opt = float(case['optimal_units']['project_B'])
    X0, X1, Y0, Y1 = 130, 880, 560, 120
    def px(xa): return X0 + (X1 - X0) * xa / 5
    def py(xb): return Y0 - (Y0 - Y1) * xb / 4
    body = [title('2案件の配分問題：実行可能領域と最適解')]
    poly = [(0, 0), (4, 0), (xa_opt, xb_opt), (0, 3)]
    body.append('<polygon points="' + ' '.join(f'{px(a):.1f},{py(b):.1f}' for a, b in poly) + f'" fill="{FILLS[0]}" stroke="none"/>')
    body.append(f'<path d="M{X0} {Y1 - 10} V{Y0} H{X1 + 10}" stroke="{STROKE}" stroke-width="2" fill="none"/>')
    for i in range(6):
        body.append(text(px(i), Y0 + 24, str(i), 14)); body.append(f'<path d="M{px(i):.1f} {Y0} v6" stroke="{STROKE}" stroke-width="2"/>')
    for j in range(5):
        body.append(text(X0 - 14, py(j) + 5, str(j), 14, anchor='end')); body.append(f'<path d="M{X0} {py(j):.1f} h-6" stroke="{STROKE}" stroke-width="2"/>')
    body.append(text((X0 + X1) / 2, Y0 + 52, '案件Aの単位数 xA', 15, 700, T1))
    body.append(text(60, (Y0 + Y1) / 2, '案件Bの単位数 xB', 15, 700, T1, 'middle', f' transform="rotate(-90 60 {(Y0 + Y1) / 2:.0f})"'))
    # 目的関数の等高線（薄い）→ 最適値の線（濃い）
    for v in (200, 280):
        xa_at_top = (v - 60 * 4) / 80; xa_at_zero = v / 80
        p1 = (max(xa_at_top, 0), 4 if xa_at_top >= 0 else v / 60)
        body.append(f'<path d="M{px(p1[0]):.1f} {py(p1[1]):.1f} L{px(xa_at_zero):.1f} {py(0):.1f}" stroke="{T1}" stroke-width="1.2" stroke-dasharray="4 6" opacity="0.6"/>')
        body.append(text(px(xa_at_zero) - 6, py(0) - 8, f'{v}', 14, 400, MUTED, 'end'))
    body.append(f'<path d="M{px(2):.1f} {py(4):.1f} L{px(4):.1f} {py(0):.1f}" stroke="{LINE}" stroke-width="3"/>')
    body.append(text(px(2.15) + 10, py(3.55), '実装 40xA + 20xB ≤ 160', 14, 700, LINE, 'start'))
    body.append(f'<path d="M{px(0):.1f} {py(3):.1f} L{px(5):.1f} {py(0.5):.1f}" stroke="{ACCENT}" stroke-width="3"/>')
    body.append(text(px(0.2), py(3) - 14, 'レビュー 10xA + 20xB ≤ 60', 14, 700, ACCENT, 'start'))
    body.append(f'<path d="M{px(346.6667 / 80 - 60 * 4 / 80):.1f} {py(4):.1f} L{px(346.6667 / 80):.1f} {py(0):.1f}" stroke="{T1}" stroke-width="2" stroke-dasharray="8 6"/>')
    body.append(text(px(1.2) - 8, py(3.75), '80xA + 60xB = 346.7（最適値）', 14, 400, T1, 'end'))
    body.append(f'<circle cx="{px(xa_opt):.1f}" cy="{py(xb_opt):.1f}" r="8" fill="{ACCENT}" stroke="#fff" stroke-width="2"/>')
    body.append(text(px(xa_opt) + 16, py(xb_opt) - 12, f'最適解 ({xa_opt:.2f}, {xb_opt:.2f})', 15, 700, T1, 'start'))
    body.append(text(px(xa_opt) + 16, py(xb_opt) + 10, '貢献利益 346.7万円', 14, 400, T1, 'start'))
    body.append(text(px(1.3), py(1.0), '実行可能領域', 15, 700, LINE))
    body.append(note(655, '破線は目的関数の等高線（200・280・346.7万円）。最適点で両制約が有効。シャドープライスは実装1.67万円/h、レビュー1.33万円/h'))
    return svg(1000, 685, '実装制約とレビュー制約で囲まれた実行可能領域と、両制約の交点にある最適解を示す線形計画の図', body)


def fig_04_constraint_layers():
    body = [title('制約は4つの階層に分けて管理する')]
    layers = [('④ 市場・戦略制約', '例：顧客需要不足、収益モデルの限界', '対策：提供価値・価格・事業モデルの変更'),
              ('③ 制度・意思決定制約', '例：過剰な承認、権限集中', '対策：権限委譲・ルール変更'),
              ('② フロー制約', '例：WIP過多、作業順序の不整合', '対策：WIP制限・優先順位・工程調整'),
              ('① 物理・能力制約', '例：テスト環境不足、レビュアー不足', '対策：増強・自動化・育成')]
    bottom = 690
    for i, (h, ex, ms) in enumerate(layers):
        w = 920 - i * 150; y = 85 + i * 100; hh = bottom - y
        x = 500 - w / 2
        body.append(f'<rect x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="{hh:.0f}" rx="16" fill="{FILLS[3 - i]}" stroke="{STROKE}"/>')
        body.append(text(x + 18, y + 30, h, 17, 700, T1, 'start'))
        body.append(text(x + 18, y + 54, ex, 14, 400, T2, 'start'))
        body.append(text(x + 18, y + 76, ms, 14, 400, MUTED, 'start'))
    body.append(arrow(560, 560, 930, 110, color=ACCENT, width=3))
    body.append(text(500, 722, '赤い矢印：AIで内側の制約を解くほど、制約は外側（制度・市場）へ移る', 15, 700, ACCENT))
    body.append(note(750, '経営分析向けの整理であり、TOCの公式分類ではない。開発生産性の改善と企業経営の改善を結ぶ境界は③と④にある'))
    return svg(1000, 775, '物理・能力、フロー、制度・意思決定、市場・戦略の4階層を同心の枠で示し、制約が内側から外側へ移ることを示す図', body)


def fig_04_mr_lifecycle():
    body = [title('MRのライフサイクルと計測点')]
    xs = [120, 320, 520, 720, 920]; y = 250
    events = [('MR作成', '流入'), ('レビュー可能状態', 'Draft解除／レビュー依頼'), ('初回レビュー', '最初のコメント'), ('承認', '必要承認数の充足'), ('マージ', '統合')]
    body.append(f'<path d="M{xs[0]} {y} H{xs[-1]}" stroke="{STROKE}" stroke-width="3"/>')
    for x, (h, s) in zip(xs, events):
        body.append(f'<circle cx="{x}" cy="{y}" r="11" fill="{BG}" stroke="{LINE}" stroke-width="3"/>')
        body.append(text(x, y - 38, h, 16, 700, T1)); body.append(text(x, y - 18, s, 14, 400, MUTED))
    def bracket(a, b, yy, label, color=LINE):
        body.append(f'<path d="M{a} {yy - 8} V{yy} H{b} V{yy - 8}" stroke="{color}" stroke-width="2" fill="none"/>')
        body.append(text((a + b) / 2, yy + 22, label, 14, 700, color))
    bracket(xs[1], xs[2], 300, 'レビュー待ち時間（レビュー制約）', ACCENT)
    bracket(xs[2], xs[3], 300, 'レビュー作業・差し戻し', LINE)
    bracket(xs[3], xs[4], 300, '統合待ち（CI・コンフリクト）', LINE)
    bracket(xs[0], xs[4], 372, 'MRリードタイム（統合速度）', T1)
    body.append(f'<rect x="{xs[0]}" y="{130}" width="{xs[-1] - xs[0]}" height="36" rx="8" fill="{FILLS[2]}" stroke="{STROKE}"/>')
    body.append(text(520, 153, 'Open MR ＝ 作成済みで未マージ（期末の件数が滞留Stock）', 15, 700, T1))
    body.append(text(xs[0], 100, 'MR作成数（週次の流入量）', 14, 700, LINE, 'start'))
    body.append(text(xs[-1], 100, 'MRマージ数（週次の処理能力）', 14, 700, LINE, 'end'))
    body.append(note(470, '「レビュー可能状態」をDraft解除時刻にするかレビュー依頼イベントにするかで待ち時間が変わる。組織で定義を統一してから計測する'))
    return svg(1000, 500, 'MR作成、レビュー可能状態、初回レビュー、承認、マージの5つの計測点と、レビュー待ち時間・MRリードタイムなどの区間の対応', body)


def fig_04_stage_gate():
    body = [title('探索投資の段階的な判断：ゲートごとに続行か撤退かを決める')]
    stages = [('小規模な技術検証', '数十時間・1〜2名', 160), ('技術成立性', '動くか、再現するか', 150), ('実務適用性', '案件で使えるか', 140), ('経済価値', '純便益と回収期間', 130)]
    x = 30; yc = 250; hh = 120
    for i, (h, s, w) in enumerate(stages):
        body.append(box(x, yc - hh / 2, w, hh, FILLS[i], h, s, hs=16, ss=14))
        if i < len(stages) - 1:
            gx = x + w + 26
            body.append(f'<polygon points="{gx},{yc - 26} {gx + 22},{yc} {gx},{yc + 26} {gx - 22},{yc}" fill="#fff" stroke="{ACCENT}" stroke-width="2"/>')
            body.append(text(gx, yc + 5, f'G{i + 1}', 14, 700, ACCENT))
            body.append(arrow(gx + 24, yc, gx + 38, yc, width=2))
            body.append(arrow(gx, yc + 28, gx, yc + 74, color=ACCENT, width=2, dashed=True))
            body.append(text(gx, yc + 94, '撤退', 14, 700, ACCENT)); body.append(text(gx, yc + 112, '学びを記録', 14, 400, MUTED))
            x = gx + 40
        else:
            x = x + w
    body.append(arrow(x + 4, yc, x + 22, yc, width=3))
    body.append(box(x + 24, yc - 50, 150, 100, FILLS[4], '既存能力の深化へ', 'Skill・CIへ展開', hs=16, ss=14))
    body.append(text(500, 420, '投入資源は段階ごとに増やし、評価基準は段階ごとに変える（成立性 → 適用性 → 経済価値）', 15, 700, T1))
    body.append(note(450, '短期ROIだけで評価すると能力が形成される前に打ち切られ、評価せずに続ければ資源を消耗する。撤退条件を事前に決める'))
    return svg(1000, 478, '小規模な技術検証から技術成立性、実務適用性、経済価値の3つのゲートを経て既存能力の深化へ進み、各ゲートで撤退も選ぶ段階投資の図', body)


# =====================================================================
# 第5回
# =====================================================================
def fig_05_sier_layers():
    body = [title('AI駆動型SIerの5層モデル')]
    layers = [('L5 事業', '顧客価値を収益に変える', '売上総利益、継続率、価値提供', FILLS[0]),
              ('L4 統制', '品質・リスク・責任を制御する', '欠陥流出、承認時間、重大事故', FILLS[1]),
              ('L3 生産', '人間とAIで成果物を作る', '完成スループット、工数、リードタイム', FILLS[2]),
              ('L2 組織能力', '生産方法を再利用・標準化する', '資産適用率、実測効果、保守費', FILLS[3]),
              ('L1 資源', '必要な資源を調達・育成する', '技術力、投資額、調達費、能力充足', FILLS[4])]
    y = 90
    for i, (h, r, m, fill) in enumerate(layers):
        emph = h.startswith('L2')
        body.append(f'<rect x="120" y="{y}" width="760" height="78" rx="12" fill="{fill}" stroke="{ACCENT if emph else STROKE}" stroke-width="{3 if emph else 1}"/>')
        body.append(text(150, y + 47, h, 20, 700, T1, 'start'))
        body.append(text(330, y + 36, r, 15, 700, T2, 'start')); body.append(text(330, y + 58, '評価：' + m, 14, 400, MUTED, 'start'))
        y += 90
    body.append(text(130, 92, '経営上の責任 ／ 評価すべきもの', 14, 400, MUTED, 'start', ' transform="translate(200 -14)"'))
    body.append(text(500, 560, 'L2が案件横断の経営資産を形成する層。個別案件へのAI導入だけではL3の局所改善に留まる', 15, 700, ACCENT))
    body.append(note(590, '5層を別々に管理するのではなく、企業全体の価値創出システムとして管理する'))
    return svg(1000, 615, '事業、統制、生産、組織能力、資源の5層を積層で示し、案件横断の資産を形成するL2を強調した図', body)


def fig_05_contract_margin():
    rows = read_csv('05-contract-margin.csv')
    body = [title('同じ40%の工数削減でも、契約方式で粗利益は逆に動く')]
    X0, Y0, H = 120, 460, 330; vmax = 700
    def py(v): return Y0 - H * v / vmax
    body.append(f'<path d="M{X0} {Y0 - H - 10} V{Y0} H920" stroke="{STROKE}" stroke-width="2" fill="none"/>')
    for v in range(0, 701, 100):
        body.append(text(X0 - 12, py(v) + 5, f'{v}', 14, anchor='end')); body.append(f'<path d="M{X0} {py(v):.1f} H920" stroke="{STROKE}" stroke-width="1" stroke-dasharray="2 6"/>')
    body.append(text(60, 290, '粗利益（万円）', 15, 700, T1, 'middle', ' transform="rotate(-90 60 290)"'))
    for gx, r in ((300, rows[0]), (700, rows[1])):
        b, a = int(r['gross_margin_before_10k_yen']), int(r['gross_margin_after_10k_yen'])
        body.append(f'<rect x="{gx - 130}" y="{py(b):.1f}" width="110" height="{Y0 - py(b):.1f}" rx="4" fill="{BAR}"/>')
        body.append(text(gx - 75, py(b) - 8, f'{b}', 16, 700, T1)); body.append(text(gx - 75, Y0 + 24, '従来', 14))
        color = GREEN if a >= b else ACCENT
        body.append(f'<rect x="{gx + 10}" y="{py(a):.1f}" width="110" height="{Y0 - py(a):.1f}" rx="4" fill="{color}"/>')
        body.append(text(gx + 65, py(a) - 8, f'{a}', 16, 700, T1)); body.append(text(gx + 65, Y0 + 24, 'AI導入後', 14))
        delta = a - b
        body.append(text(gx, Y0 + 56, r['contract'], 18, 700, T1))
        body.append(text(gx, Y0 + 80, f'粗利益 {"+" if delta > 0 else "−"}{abs(delta)}万円（売上 {r["revenue_before_10k_yen"]} → {r["revenue_after_10k_yen"]}万円）', 14, 700, color))
    body.append(note(588, '緑＝粗利益の増加、赤＝減少。仮想値：従来1,000h → 600h、原価6,000円/h、AI費40万円'))
    body.append(note(610, '固定価格は契約額不変、時間精算は600hを1万円/hで全額請求と仮定'))
    return svg(1000, 638, '固定価格契約では粗利益が400万円から600万円へ増え、時間精算契約では400万円から200万円へ減る棒グラフ', body)


def fig_05_knowledge_scenarios():
    params = read_csv('05-knowledge-params.csv')
    series = {}
    for r in params:
        K = float(r['K0']); a, b, d, E, R = (float(r[k]) for k in ('alpha', 'beta', 'delta', 'E', 'R'))
        vals = [K]
        for _ in range(int(r['periods'])):
            K = (1 - d) * K + a * E + b * R; vals.append(round(K, 2))
        series[r['scenario']] = (r['label'], vals)
    keys = list(series.keys())
    write_csv('05-knowledge-scenarios.csv', ['period', *keys], [[i, *(series[s][1][i] for s in keys)] for i in range(len(series[keys[0]][1]))])
    colors = {'base': LINE, 'low_alpha': ACCENT, 'high_delta': PURPLE}
    body = [title('知識資産の蓄積：変換効率と陳腐化で到達点が変わる')]
    chart, px, py = line_chart(110, 110, 740, 390, 0, 10, 0, 260, range(0, 11), range(0, 261, 50), '期（年）', '知識資産指数 K',
                               [(label, list(enumerate(vals)), colors[key], {'end_label': f'{vals[-1]:.0f}'}) for key, (label, vals) in series.items()])
    body += chart
    body.append(text(500, 582, 'K(t+1) = (1−δ)K(t) + αE + βR。E=30（案件経験）、R=10（改善投資）、β=1.0、K0=100', 14, 400, T2))
    body.append(note(608, '仮想値。案件経験が同じでも、変換効率αが低ければ組織知は増えず、保守を怠ればδが上がって到達点が下がる'))
    return svg(1000, 635, '知識資産指数の10期の推移。基準シナリオは198、変換効率が低いと139、陳腐化が速いと122で頭打ちになる', body)


def fig_05_investment():
    rows = read_csv('05-asset-investment.csv')
    pts = [(int(r['year']), float(r['cumulative_net_hours'])) for r in rows]
    body = [title('共通資産への投資：累積純削減工数（仮想）')]
    chart, px, py = line_chart(120, 110, 750, 360, 0, 5, -500, 2500, range(0, 6), range(-500, 2501, 500), '経過年', '累積純削減工数（時間）',
                               [('累積純削減工数 N(y) = 600y − 1000', pts, LINE, {'end_label': '2,000時間'})], zero_line=True, yfmt=lambda v: f'{v:,}')
    body += chart
    body.append(text(px(1) + 12, py(-400) + 22, '1年目 −400時間（投資が先行）', 14, 700, ACCENT, 'start'))
    body.append(f'<circle cx="{px(2):.1f}" cy="{py(200):.1f}" r="8" fill="{GREEN}" stroke="#fff" stroke-width="2"/>')
    body.append(text(px(2) + 14, py(200) - 12, '2年目に累積がプラスへ（+200時間）', 14, 700, GREEN, 'start'))
    body.append(note(560, '構築1,000時間、年20案件×40時間削減、保守200時間/年。API費用、品質差、資金の時間価値、需要不確実性は含まない'))
    return svg(1000, 590, '共通Skill投資の累積純削減工数。1年目は−400時間、2年目に+200時間で回収し、5年目に2,000時間', body)


def fig_05_autonomy_matrix():
    body = [title('AIの自律度はリスクと検証可能性で決める')]
    X0, X1, Y0, Y1 = 130, 940, 560, 118
    body.append(f'<rect x="{X0}" y="{Y1}" width="{X1 - X0}" height="{Y0 - Y1}" fill="{SOFT}" stroke="{STROKE}"/>')
    body.append(arrow(X0, Y0 + 30, X1, Y0 + 30, color=STROKE, width=2)); body.append(text((X0 + X1) / 2, Y0 + 58, '失敗の影響（小 → 大）', 15, 700, T1))
    body.append(arrow(X0 - 30, Y0, X0 - 30, Y1, color=STROKE, width=2)); body.append(text(70, (Y0 + Y1) / 2, '独立した検証で失敗を検出できる確率（低 → 高）', 15, 700, T1, 'middle', f' transform="rotate(-90 70 {(Y0 + Y1) / 2:.0f})"'))
    levels = [('A4 統制下の自律運用', '定義範囲で工程を遂行'), ('A3 条件付き統合', '基準を満たせば自動反映'), ('A2 検証付き実行', '実行し証跡を残す'), ('A1 生成', '生成し、人間が採否'), ('A0 提案', '提案のみ、人間が判断')]
    n = len(levels); bw = (X1 - X0) / n; bh = (Y0 - Y1) / n
    for i, (h, s) in enumerate(levels):
        x = X0 + bw * i; y = Y1 + bh * i
        body.append(f'<rect x="{x + 5:.0f}" y="{y + 5:.0f}" width="{bw - 10:.0f}" height="{bh - 10:.0f}" rx="12" fill="{FILLS[i]}" stroke="{STROKE}"/>')
        body.append(text(x + bw / 2, y + bh / 2 - 4, h, 15, 700, T1)); body.append(text(x + bw / 2, y + bh / 2 + 17, s, 14, 400, MUTED))
    body.append(text(X0 + bw * 3.5, Y1 + bh * 0.85, '影響が大きくても検出確率が高ければ A2〜A3', 14, 400, T2))
    body.append(text(X0 + bw * 3.5, Y1 + bh * 1.15, '（自動回帰テストと証跡で担保）', 14, 400, MUTED))
    body.append(text(X0 + bw * 1.5, Y1 + bh * 3.85, '影響が小さくても検出できなければ A1 止まり', 14, 400, T2))
    body.append(text(X0 + bw * 1.5, Y1 + bh * 4.15, '（検証手段を先に作る）', 14, 400, MUTED))
    ux, uy = X0 + bw * 1.0, Y1 + bh * 1.0
    body.append(f'<path d="M{ux:.0f} {uy:.0f} L{X0 + bw * 2.0:.0f} {Y1 + bh * 0.35:.0f}" stroke="{LINE}" stroke-width="1.5"/>')
    body.append(f'<circle cx="{ux:.0f}" cy="{uy:.0f}" r="8" fill="{LINE}" stroke="#fff" stroke-width="2"/>')
    body.append(text(X0 + bw * 2.05, Y1 + bh * 0.3, '例：UIコンポーネントの表示修正 → A3〜A4', 14, 700, LINE, 'start'))
    dx, dy = X0 + bw * 4.0, Y1 + bh * 4.0
    body.append(f'<path d="M{dx:.0f} {dy:.0f} L{X0 + bw * 3.0:.0f} {Y1 + bh * 4.7:.0f}" stroke="{ACCENT}" stroke-width="1.5"/>')
    body.append(f'<circle cx="{dx:.0f}" cy="{dy:.0f}" r="8" fill="{ACCENT}" stroke="#fff" stroke-width="2"/>')
    body.append(text(X0 + bw * 2.95, Y1 + bh * 4.75, '例：決済金額の計算ロジック変更 → A0〜A1', 14, 700, ACCENT, 'end'))
    body.append(note(628, '提案モデル（公的規格ではない）。自律度はAIの能力ではなく、失敗の影響と独立検証で検出できる確率で決める'))
    return svg(1000, 655, '失敗の影響と検証可能性の2軸にA0からA4の自律度を配置した図。UI表示修正は高自律、決済ロジック変更は低自律', body)


def fig_05_constraint_shift():
    rows = read_csv('05-process-capacity.csv')
    labels = [r['stage'] for r in rows]; vals = [int(r['per_day']) for r in rows]
    body = [title('AI導入後に制約はどこへ移るか')]
    lo = min(vals); i_lo = vals.index(lo)
    rest = sorted((v, i) for i, v in enumerate(vals) if i != i_lo); nxt = rest[0][1]
    body += bars(110, 120, 780, 360, labels, vals, 44, highlight=i_lo, outline=nxt, limit=lo)
    body.append(text(500, 530, f'実装を40件/日まで増やしても完成は{lo}件/日（破線）。レビューを改善すると、次は{labels[nxt]}（{vals[nxt]}件/日、点線枠）が制約になり得る', 15, 700, T1))
    body.append(note(562, '全作業が5工程を1回ずつ通過し、各件の作業量が同一で、手戻り・変動・並列処理の干渉を無視した仮想モデル'))
    return svg(1000, 590, 'AI導入後の5工程の処理能力の棒グラフ。実装40件/日に対しレビュー12件/日が制約で、次の制約はリリース15件/日', body)


def fig_05_organization_model():
    body = [title('案件組織と資産組織を分離する')]
    body.append(box(30, 190, 290, 130, FILLS[0], '① 事業・案件組織', '顧客価値・納期・収益・品質', hs=18, ss=14))
    body.append(box(355, 190, 290, 130, FILLS[1], '② プラットフォーム・能力開発組織', '標準・CI・Skill・評価基盤の保守', hs=15, ss=14))
    body.append(box(680, 190, 290, 130, FILLS[3], '③ 探索・変革組織', '新しいAI能力の検証と将来モデル', hs=18, ss=14))
    body.append(path_arrow('M320 220 H343', (355, 220, 1, 0))); body.append(text(337, 172, '改善要求・案件経験', 14, 400, LINE))
    body.append(path_arrow('M355 290 H332', (320, 290, -1, 0))); body.append(text(337, 345, '標準・Skill・CI・評価基盤', 14, 400, LINE))
    body.append(path_arrow('M680 220 H657', (645, 220, -1, 0))); body.append(text(662, 172, '検証済み技術の移管', 14, 400, LINE))
    body.append(path_arrow('M645 290 H668', (680, 290, 1, 0))); body.append(text(662, 345, '制約・需要・実測データ', 14, 400, LINE))
    body.append(text(500, 405, '予算・責任・成果指標を分ける。小規模組織では同じメンバーが兼務してよい', 16, 700, T1))
    body.append(text(500, 435, '②の提供物は案件の将来原価と生産能力に影響する経営資産。リリース管理・品質保証・サポート・廃止判断まで責任を持つ', 14, 400, MUTED))
    body.append(note(490, '案件遂行と共通能力開発を同じ責任体系で管理すると、共通資産への投資が短期案件の優先順位に押し負けやすい'))
    return svg(1000, 520, '事業・案件組織、プラットフォーム・能力開発組織、探索・変革組織の3つの責任領域と、その間の流れを示す図', body)


# =====================================================================
# 第6回
# =====================================================================
def fig_06_series_map():
    body = [title('連載の全体像：資源から制約へ、制約から経営モデルへ')]
    items = [('第1回 経営資源とは何か', '保有量ではなく、資源を何に変換できるかを問う'), ('第2回 分類体系', '種類・性質・能力の階層・戦略価値の多軸で資源を見る'),
             ('第3回 流れと変換', 'Stock・Flow・Feedbackで企業を動的なシステムとして捉える'), ('第4回 配分と制約', '全資源の稼働最大化と全体価値の最大化は一致しない'),
             ('第5回 AI時代のSIer経営モデル', '競争優位は実装速度ではなく、検証・資産化・変革の能力')]
    y = 80
    for i, (h, s) in enumerate(items):
        body.append(box(140, y, 760, 80, FILLS[i], h, s, hs=21, ss=15))
        if i < 4: body.append(arrow(520, y + 80, 520, y + 108))
        y += 108
    body.append(path_arrow('M140 552 H70 V120 H128', (140, 120, 1, 0), dashed=True))
    body.append(text(70, 336, '次の資源へ', 14, 700, LINE, 'middle', ' transform="rotate(-90 70 336)"'))
    body.append(note(650, '蓄積した能力は次の資源になる。第5回の出口は第1回の入口へ戻る（破線）。各回の「本稿の問い」は第6回のチェックリストに集約する'))
    return svg(1000, 680, '第1回から第5回までの流れと、第5回の出口が第1回へ戻る循環を示した連載の全体像', body)


def fig_06_operating_cycle():
    body = [title('経営の運転サイクル：測る → 制約 → 配分 → 実行 → 資産化 → 再評価')]
    body += loop(500, 405, 240, [('① 測る', '流入・完了・滞留・変動'), ('② 制約を特定する', 'TOC、制約の4階層'), ('③ 配分する', '限界価値、探索と深化'),
                                 ('④ 実行する', '責務分離、自律度、WIP制限'), ('⑤ 資産化する', '7変換、SECI、L2へ横展開'), ('⑥ 再評価する', '制約の移動、能力の更新')], 205, 60, '')
    body.append(text(500, 392, 'R：① → ⑤ → ① の強化ループ', 16, 700, T1)); body.append(text(500, 420, 'B：② ③ ④ で滞留を制御', 16, 700, T1))
    body.append(note(706, '6段階のどれか一つを省くと残りが機能しない。測らずに制約は見つからず、資産化しなければ生産性は複利にならない'))
    return svg(1000, 735, '測る、制約を特定する、配分する、実行する、資産化する、再評価するの6段階を円環で示した経営の運転サイクル', body)


def fig_06_formula_hierarchy():
    body = [title('問いの階層：下の問いは上の問いの答えを前提にする')]
    layers = [('蓄積', '資源はどう増減するか', 'S(t+1) = S(t) + A(t) − D(t)　／　K(t+1) = (1−δ)K(t) + αE(t) + βR(t)', '第2回・第3回・第5回'),
              ('流れ', '仕事はどれだけ滞留するか', 'L = λW　／　Wq = ρ ÷ ( μ(1−ρ) )', '第4回'),
              ('配分', '資源をどこへ配分するか', 'max V(x)  s.t.  Ax ≤ b　／　MVi = ∂V/∂xi', '第4回'),
              ('投資評価', '共通資産は割に合うか', 'V_asset = Σ(ΔCi − C_apply,i) − C_build − C_maint', '第2回・第3回・第5回'),
              ('境界', '内製か外注か', 'C_internal  vs.  C_external + C_coordination + C_risk', '第5回')]
    y = 88
    for i, (h, q, f, ref) in enumerate(layers):
        w = 600 + i * 80; x = 500 - w / 2
        body.append(f'<rect x="{x:.0f}" y="{y}" width="{w:.0f}" height="78" rx="12" fill="{FILLS[i]}" stroke="{STROKE}"/>')
        body.append(text(x + 18, y + 30, f'{i + 1}. {h}', 18, 700, T1, 'start')); body.append(text(x + 18, y + 56, q, 14, 400, MUTED, 'start'))
        body.append(text(x + w - 18, y + 30, f, 14, 400, T1, 'end')); body.append(text(x + w - 18, y + 56, ref, 14, 400, MUTED, 'end'))
        if i < len(layers) - 1:
            body.append(arrow(500, y + 78, 500, y + 78 + 22, width=2))
        y += 100
    body.append(note(y + 18, '滞留を測らずに配分は決められず、資産の価値を測らずに内製と外注は比べられない。上の段の答えが下の段の入力になる'))
    return svg(1000, y + 48, '蓄積、流れ、配分、投資評価、境界の5段に連載の数式を対応させ、上の段の答えが下の段の前提になることを示す図', body)


FIGURES = {
    '01-resource-system.svg': fig_01_resource_system,
    '01-conversion-chain.svg': fig_01_conversion_chain,
    '02-three-levels.svg': fig_02_three_levels,
    '02-four-dimensions.svg': fig_02_four_dimensions,
    '02-theory-timeline.svg': fig_02_theory_timeline,
    '02-asset-stock-bathtub.svg': fig_02_asset_stock_bathtub,
    '03-flow-system.svg': fig_03_flow_system,
    '03-flow-bottleneck.svg': fig_03_flow_bottleneck,
    '03-knowledge-stock.svg': fig_03_knowledge_stock,
    '03-feedback-loops.svg': fig_03_feedback_loops,
    '03-dual-output.svg': fig_03_dual_output,
    '04-toc.svg': fig_04_toc,
    '04-constraint-shift.svg': fig_04_constraint_shift,
    '04-review-backlog.svg': fig_04_review_backlog,
    '04-utilization-queue.svg': fig_04_utilization_queue,
    '04-lp-feasible-region.svg': fig_04_lp_feasible_region,
    '04-constraint-layers.svg': fig_04_constraint_layers,
    '04-mr-lifecycle.svg': fig_04_mr_lifecycle,
    '04-stage-gate.svg': fig_04_stage_gate,
    '05-sier-layers.svg': fig_05_sier_layers,
    '05-contract-margin.svg': fig_05_contract_margin,
    '05-knowledge-scenarios.svg': fig_05_knowledge_scenarios,
    '05-investment.svg': fig_05_investment,
    '05-autonomy-matrix.svg': fig_05_autonomy_matrix,
    '05-constraint-shift.svg': fig_05_constraint_shift,
    '05-organization-model.svg': fig_05_organization_model,
    '06-series-map.svg': fig_06_series_map,
    '06-operating-cycle.svg': fig_06_operating_cycle,
    '06-formula-hierarchy.svg': fig_06_formula_hierarchy,
}


def main() -> int:
    ASSETS.mkdir(exist_ok=True)
    for name, fn in FIGURES.items():
        (ASSETS / name).write_text(fn(), encoding='utf-8')
    print(f'wrote {len(FIGURES)} figures')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
