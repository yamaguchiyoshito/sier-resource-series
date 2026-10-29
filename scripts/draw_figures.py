#!/usr/bin/env python3
"""追加図版を決定論的に生成する。データ図は simulation/*.csv を読む。既存の図（ChatGPT出力の10点）は対象外。"""
from __future__ import annotations
import csv
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets'
SIM = ROOT / 'simulation'

BG = '#fcfdfd'; INK = '#18324b'; T1 = '#223e53'; T2 = '#36556d'; MUTED = '#5d6c75'
LINE = '#607a91'; STROKE = '#8ea6b2'; ACCENT = '#c0604a'; BAR = '#9dbbd3'; SOFT = '#eef3f1'
FILLS = ['#e1edf8', '#e0f0e9', '#f7e9d4', '#e9e4f5', '#f6e4e8']
FONT = 'font-family="sans-serif"'


def esc(s: str) -> str:
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def text(x, y, s, size=17, weight=400, fill=T2, anchor='middle', extra=''):
    w = f' font-weight="{weight}"' if weight != 400 else ''
    return f'<text x="{x:.0f}" y="{y:.0f}" text-anchor="{anchor}" {FONT} font-size="{size}"{w} fill="{fill}"{extra}>{esc(s)}</text>'


def title(s):
    return text(50, 51, s, 27, 700, INK, 'start')


def box(x, y, w, h, fill, head, sub=None, hs=20, ss=15, stroke=STROKE):
    out = [f'<rect x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="{h:.0f}" rx="12" fill="{fill}" stroke="{stroke}"/>']
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
    tip = f'{x2:.1f},{y2:.1f}'
    b1 = f'{x2 - ux * 12 + nx * 7:.1f},{y2 - uy * 12 + ny * 7:.1f}'
    b2 = f'{x2 - ux * 12 - nx * 7:.1f},{y2 - uy * 12 - ny * 7:.1f}'
    return (f'<path d="M{x1:.1f} {y1:.1f} L{ex:.1f} {ey:.1f}" stroke="{color}" stroke-width="{width}" fill="none"{dash}/>'
            f'<polygon points="{tip} {b1} {b2}" fill="{color}"/>')


def path_arrow(d, end, color=LINE, dashed=False, width=3):
    """任意パス d の終点 end=(x,y,ux,uy) に矢頭を付ける。"""
    x, y, ux, uy = end; nx, ny = -uy, ux
    dash = ' stroke-dasharray="8 6"' if dashed else ''
    return (f'<path d="{d}" stroke="{color}" stroke-width="{width}" fill="none"{dash}/>'
            f'<polygon points="{x:.1f},{y:.1f} {x - ux * 12 + nx * 7:.1f},{y - uy * 12 + ny * 7:.1f} {x - ux * 12 - nx * 7:.1f},{y - uy * 12 - ny * 7:.1f}" fill="{color}"/>')


def note(y, s, size=16):
    return text(500, y, s, size, 400, MUTED)


def svg(w, h, label, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{esc(label)}">\n'
            f'<rect width="100%" height="100%" fill="{BG}"/>\n' + '\n'.join(body) + '\n</svg>\n')


def loop(cx, cy, R, nodes, bw, bh, label, fill_offset=0, start=-90):
    """円環上にノードを置き、時計回りの矢頭を付けた因果ループを描く。"""
    n = len(nodes)
    out = [f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="none" stroke="{LINE}" stroke-width="3"/>']
    for i in range(n):
        am = math.radians(start + 360 * (i + 0.5) / n)
        px, py = cx + R * math.cos(am), cy + R * math.sin(am)
        tx, ty = -math.sin(am), math.cos(am)
        nx, ny = math.cos(am), math.sin(am)
        tip = (px + tx * 11, py + ty * 11); b1 = (px - tx * 9 + nx * 8, py - ty * 9 + ny * 8); b2 = (px - tx * 9 - nx * 8, py - ty * 9 - ny * 8)
        out.append(f'<polygon points="{tip[0]:.1f},{tip[1]:.1f} {b1[0]:.1f},{b1[1]:.1f} {b2[0]:.1f},{b2[1]:.1f}" fill="{LINE}"/>')
    for i, (head, sub) in enumerate(nodes):
        a = math.radians(start + 360 * i / n)
        x, y = cx + R * math.cos(a), cy + R * math.sin(a)
        out.append(box(x - bw / 2, y - bh / 2, bw, bh, FILLS[(i + fill_offset) % 5], head, sub, hs=17, ss=13))
    out.append(f'<circle cx="{cx}" cy="{cy}" r="28" fill="{BG}" stroke="{LINE}" stroke-width="2"/>')
    out.append(text(cx, cy + 9, label, 24, 700, INK))
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
        out.append(text(x0 + w, ly - 8, limit_label, 14, 700, ACCENT, 'end'))
    return out


def read_csv(name):
    with (SIM / name).open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


# ---------- 第1回 ----------
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
    body.append(path_arrow('M110 342 H60 V152 H98', (110, 152, 1, 0), dashed=True))
    body.append(text(500, 450, '⑥の成果（収益・信用）は①の資源（ヒト・時間・情報）へ再投入される', 16, 700, T1))
    body.append(note(482, '変換は資源の用途・価値創出機能を変える過程。知識は形式化しても元の人間から失われない'))
    return svg(1000, 510, '6つの資源変換が環をなし、成果が次の活動の資源になる再帰構造', body)


# ---------- 第2回 ----------
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
        body.append(text(x, y - 14, h, 19, 700, T1)); body.append(text(x, y + 9, q, 14)); body.append(text(x, y + 31, ex, 13, 400, MUTED))
        dx, dy = x - cx, y - cy
        if dx == 0:
            y1 = cy - 42 if dy < 0 else cy + 42; y2 = y + hh / 2 if dy < 0 else y - hh / 2
            body.append(f'<path d="M{cx} {y1} V{y2}" stroke="{LINE}" stroke-width="3"/>')
        else:
            x1 = cx - 120 if dx < 0 else cx + 120; x2 = x + w / 2 if dx < 0 else x - w / 2
            body.append(f'<path d="M{x1} {cy} H{x2}" stroke="{LINE}" stroke-width="3"/>')
    body.append(note(640, '4次元は独立した分類軸として組み合わせる。既存理論を統合した分析モデルであり、単一の理論ではない'))
    return svg(1000, 670, '一つの資源を種類・性質・機能・戦略価値の4次元から見る図', body)


# ---------- 第3回 ----------
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
    body.append(text(500, 118, '未レビュー（滞留Stock）', 17, 700, T1))
    body.append(text(500, 140, '20 − 12 = 8件/日ずつ増加 → 10営業日後に80件', 15, 400, ACCENT))
    body.append(text(500, 395, '実装能力を30件/日へ上げても完了は12件/日のまま。滞留は18件/日ずつ増え、10営業日で180件', 16, 700, T1))
    body.append(note(428, '初期滞留0件、毎日一定流入、差し戻し・休日・作業サイズ差を無視した単純化モデル'))
    return svg(1000, 460, '流入20件/日に対し処理能力12件/日のレビュー工程で滞留が増える図', body)


def fig_03_feedback_loops():
    body = [title('強化ループと抑制ループ')]
    body.append(text(250, 100, '強化ループ R：成果が次の成果を生む', 18, 700, T1))
    body.append(text(750, 100, '抑制ループ B：成長が新しい制約を生む', 18, 700, T1))
    body.append(f'<path d="M500 90 V640" stroke="{STROKE}" stroke-width="1" stroke-dasharray="4 6"/>')
    body += loop(250, 380, 180, [('開発活動', '案件の遂行'), ('経験', '障害対応・判断'), ('標準・Skill', '形式化・配布'), ('生産性向上', '工数減・品質向上'), ('改善機会', '余力と知見')], 150, 54, 'R')
    body += loop(750, 380, 180, [('AI実装量の増加', '流入が増える'), ('レビュー待ち増加', '滞留Stock'), ('リードタイム悪化', '提供速度の低下'), ('完了量の制約', '投入を抑える圧力')], 170, 54, 'B', fill_offset=2)
    body.append(text(250, 628, '条件：経験が検証・共有され、標準やSkillへ反映されること', 14, 400, MUTED))
    body.append(text(750, 628, '対策：WIP制限、レビュー自動化、承認権限の再設計', 14, 400, MUTED))
    body.append(note(668, 'R は同方向に増幅する循環、B は目標との偏差を縮める循環。経験が個人に閉じると R は途中で断絶する'))
    return svg(1000, 700, '強化ループ（開発活動→経験→標準・Skill→生産性→改善機会）と抑制ループ（AI実装増→レビュー待ち→リードタイム悪化→完了量制約）', body)


def fig_03_dual_output():
    body = [title('経営は二重の価値創出を管理する')]
    body.append(box(60, 250, 230, 110, FILLS[0], '経営資源', '人材・知識・技術・資金・組織・関係', hs=20, ss=13))
    body.append(arrow(290, 305, 385, 305))
    body.append(box(385, 250, 230, 110, FILLS[2], '生産活動', '案件遂行・設計・実装・検証', hs=20, ss=13))
    body.append(arrow(615, 285, 710, 200))
    body.append(arrow(615, 325, 710, 410))
    body.append(box(710, 150, 240, 100, FILLS[1], '第一の成果', '現在の価値創出：納品・対価・売上', hs=19, ss=13))
    body.append(box(710, 360, 240, 100, FILLS[3], '第二の成果', '未来の価値創出能力：経験・知識・技術・信頼', hs=19, ss=12))
    body.append(path_arrow('M830 150 V95 H175 V238', (175, 250, 0, 1), dashed=True))
    body.append(path_arrow('M830 460 V520 H175 V372', (175, 360, 0, -1), dashed=True))
    body.append(text(500, 85, '利益の再投資', 14, 400, LINE))
    body.append(text(500, 540, '蓄積した能力の再投入（次の活動の生産能力を増強）', 14, 400, LINE))
    body.append(note(585, '実線は価値創出、破線は再投資と資源の再投入。第二の成果を測らない経営は、将来の生産能力の低下に気づけない'))
    return svg(1000, 610, '生産活動が現在の価値と未来の価値創出能力という二重の成果を生み、両方が経営資源へ戻る図', body)


# ---------- 第4回 ----------
def fig_04_constraint_shift():
    rows = read_csv('04-process-capacity.csv')
    labels = [r['stage'] for r in rows]
    before = [int(r['before_per_day']) for r in rows]; after = [int(r['after_review_boost_per_day']) for r in rows]
    body = [title('制約は解消すると移動する')]
    body.append(text(270, 100, '現状：レビューが制約（上限10件/日）', 17, 700, T1))
    body.append(text(730, 100, 'レビューを16件/日へ増強：次は検証が制約（上限14件/日）', 17, 700, T1))
    body += bars(70, 130, 400, 330, labels, before, 28, highlight=before.index(min(before)), limit=min(before), limit_label='')
    body += bars(530, 130, 400, 330, labels, after, 28, highlight=after.index(min(after)), limit=min(after), limit_label='')
    body.append(text(500, 300, '→', 30, 700, LINE))
    body.append(note(530, '縦軸は1日あたり処理能力（件/日）。各工程が必須で同じ作業単位を処理し、手戻りと変動を無視した単純化モデル'))
    return svg(1000, 560, '5工程の処理能力の棒グラフ。現状はレビュー10件/日が制約、レビューを16件/日へ増強すると検証14件/日が次の制約になる', body)


def fig_04_lp_feasible_region():
    case = {r['item']: r for r in read_csv('04-lp-case.csv')}
    xa_opt = float(case['optimal_units']['project_A']); xb_opt = float(case['optimal_units']['project_B'])
    # 座標変換：xA 0..5, xB 0..4
    X0, X1, Y0, Y1 = 130, 880, 560, 120
    def px(xa): return X0 + (X1 - X0) * xa / 5
    def py(xb): return Y0 - (Y0 - Y1) * xb / 4
    body = [title('2案件の配分問題：実行可能領域と最適解')]
    # 実行可能領域
    poly = [(0, 0), (4, 0), (xa_opt, xb_opt), (0, 3)]
    body.append('<polygon points="' + ' '.join(f'{px(a):.1f},{py(b):.1f}' for a, b in poly) + f'" fill="{FILLS[0]}" stroke="none"/>')
    # 軸
    body.append(f'<path d="M{X0} {Y1 - 10} V{Y0} H{X1 + 10}" stroke="{STROKE}" stroke-width="2" fill="none"/>')
    for i in range(6):
        body.append(text(px(i), Y0 + 24, str(i), 14)); body.append(f'<path d="M{px(i):.1f} {Y0} v6" stroke="{STROKE}" stroke-width="2"/>')
    for j in range(5):
        body.append(text(X0 - 14, py(j) + 5, str(j), 14, anchor='end')); body.append(f'<path d="M{X0} {py(j):.1f} h-6" stroke="{STROKE}" stroke-width="2"/>')
    body.append(text((X0 + X1) / 2, Y0 + 52, '案件Aの単位数 xA', 15, 700, T1))
    body.append(text(60, (Y0 + Y1) / 2, '案件Bの単位数 xB', 15, 700, T1, 'middle', f' transform="rotate(-90 60 {(Y0 + Y1) / 2:.0f})"'))
    # 制約直線
    body.append(f'<path d="M{px(2):.1f} {py(4):.1f} L{px(4):.1f} {py(0):.1f}" stroke="{LINE}" stroke-width="3"/>')
    body.append(text(px(2.15) + 10, py(3.55), '実装 40xA + 20xB ≤ 160', 14, 700, LINE, 'start'))
    body.append(f'<path d="M{px(0):.1f} {py(3):.1f} L{px(5):.1f} {py(0.5):.1f}" stroke="{ACCENT}" stroke-width="3"/>')
    body.append(text(px(0.2), py(3) - 14, 'レビュー 10xA + 20xB ≤ 60', 14, 700, ACCENT, 'start'))
    # 目的関数（最適値）
    body.append(f'<path d="M{px(346.6667 / 80 - 60 * 4 / 80):.1f} {py(4):.1f} L{px(346.6667 / 80):.1f} {py(0):.1f}" stroke="{T1}" stroke-width="2" stroke-dasharray="8 6"/>')
    body.append(text(px(1.2) - 8, py(3.75), '80xA + 60xB = 346.7（最適値）', 14, 400, T1, 'end'))
    # 最適点
    body.append(f'<circle cx="{px(xa_opt):.1f}" cy="{py(xb_opt):.1f}" r="8" fill="{ACCENT}" stroke="#fff" stroke-width="2"/>')
    body.append(text(px(xa_opt) + 16, py(xb_opt) - 12, f'最適解 ({xa_opt:.2f}, {xb_opt:.2f})', 15, 700, T1, 'start'))
    body.append(text(px(xa_opt) + 16, py(xb_opt) + 10, '貢献利益 346.7万円', 14, 400, T1, 'start'))
    body.append(text(px(1.3), py(1.0), '実行可能領域', 15, 700, LINE))
    body.append(note(655, '最適点で両制約が有効。シャドープライスは実装 1.67万円/h、レビュー 1.33万円/h（上限を1時間緩めたときの貢献利益の増分）'))
    return svg(1000, 685, '実装制約とレビュー制約で囲まれた実行可能領域と、両制約の交点にある最適解を示す線形計画の図', body)


def fig_04_constraint_layers():
    body = [title('制約は4つの階層に分けて管理する')]
    layers = [('④ 市場・戦略制約', '顧客需要不足、収益モデルの限界 ／ 対策：提供価値・価格・事業モデルの変更'),
              ('③ 制度・意思決定制約', '過剰な承認、権限集中 ／ 対策：権限委譲・ルール変更'),
              ('② フロー制約', 'WIP過多、作業順序の不整合 ／ 対策：WIP制限・優先順位・工程調整'),
              ('① 物理・能力制約', 'テスト環境不足、レビュアー不足 ／ 対策：増強・自動化・育成')]
    cx, cy = 500, 390
    for i, (h, s) in enumerate(layers):
        w, hh = 880 - i * 210, 500 - i * 118
        x, y = cx - w / 2, cy - hh / 2
        body.append(f'<rect x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="{hh:.0f}" rx="16" fill="{FILLS[3 - i]}" stroke="{STROKE}"/>')
        body.append(text(x + 18, y + 30, h, 17, 700, T1, 'start'))
        body.append(text(x + 18, y + 52, s, 12.5, 400, MUTED, 'start'))
    body.append(arrow(600, 440, 905, 165, color=ACCENT, width=3))
    body.append(text(500, 655, '赤い矢印：AIで内側の制約を解くほど、制約は外側（制度・市場）へ移る', 15, 700, ACCENT))
    body.append(note(685, '経営分析向けの整理であり、TOCの公式分類ではない。開発生産性の改善と企業経営の改善を結ぶ境界は③と④にある'))
    return svg(1000, 710, '物理・能力、フロー、制度・意思決定、市場・戦略の4階層を同心の枠で示し、制約が内側から外側へ移ることを示す図', body)


# ---------- 第5回 ----------
def fig_05_contract_margin():
    rows = read_csv('05-contract-margin.csv')
    body = [title('同じ40%の工数削減でも、契約方式で粗利益は逆に動く')]
    X0, Y0, H = 120, 460, 330; vmax = 700
    def py(v): return Y0 - H * v / vmax
    body.append(f'<path d="M{X0} {Y0 - H - 10} V{Y0} H920" stroke="{STROKE}" stroke-width="2" fill="none"/>')
    for v in range(0, 701, 100):
        body.append(text(X0 - 12, py(v) + 5, f'{v}', 13, anchor='end')); body.append(f'<path d="M{X0} {py(v):.1f} H920" stroke="{STROKE}" stroke-width="1" stroke-dasharray="2 6"/>')
    body.append(text(60, 290, '粗利益（万円）', 14, 700, T1, 'middle', ' transform="rotate(-90 60 290)"'))
    groups = [(300, rows[0]), (700, rows[1])]
    for gx, r in groups:
        b, a = int(r['gross_margin_before_10k_yen']), int(r['gross_margin_after_10k_yen'])
        body.append(f'<rect x="{gx - 130}" y="{py(b):.1f}" width="110" height="{Y0 - py(b):.1f}" rx="4" fill="{BAR}"/>')
        body.append(text(gx - 75, py(b) - 8, f'{b}', 16, 700, T1)); body.append(text(gx - 75, Y0 + 24, '従来', 14))
        color = '#5aa06f' if a >= b else ACCENT
        body.append(f'<rect x="{gx + 10}" y="{py(a):.1f}" width="110" height="{Y0 - py(a):.1f}" rx="4" fill="{color}"/>')
        body.append(text(gx + 65, py(a) - 8, f'{a}', 16, 700, T1)); body.append(text(gx + 65, Y0 + 24, 'AI導入後', 14))
        delta = a - b
        body.append(text(gx, Y0 + 56, r['contract'], 18, 700, T1))
        body.append(text(gx, Y0 + 80, f'粗利益 {"+" if delta > 0 else "−"}{abs(delta)}万円（売上 {r["revenue_before_10k_yen"]} → {r["revenue_after_10k_yen"]}万円）', 14, 700, color))
    body.append(note(590, '仮想値：従来1,000h → 600h、原価6,000円/h、AI費40万円。固定価格は契約額不変、時間精算は600hを1万円/hで全額請求と仮定', 15))
    return svg(1000, 620, '固定価格契約では粗利益が400万円から600万円へ増え、時間精算契約では400万円から200万円へ減る棒グラフ', body)


def fig_05_autonomy_matrix():
    body = [title('AIの自律度はリスクと検証可能性で決める')]
    X0, X1, Y0, Y1 = 150, 900, 560, 120
    body.append(f'<rect x="{X0}" y="{Y1}" width="{X1 - X0}" height="{Y0 - Y1}" fill="{SOFT}" stroke="{STROKE}"/>')
    body.append(arrow(X0, Y0 + 30, X1, Y0 + 30, color=STROKE, width=2)); body.append(text((X0 + X1) / 2, Y0 + 58, '失敗の影響（小 → 大）', 15, 700, T1))
    body.append(arrow(X0 - 30, Y0, X0 - 30, Y1, color=STROKE, width=2)); body.append(text(80, (Y0 + Y1) / 2, '独立した検証で失敗を検出できる確率（低 → 高）', 15, 700, T1, 'middle', f' transform="rotate(-90 80 {(Y0 + Y1) / 2:.0f})"'))
    levels = [('L4 統制された自律運用', '定義済み範囲で一連の工程を遂行'), ('L3 条件付き統合', '基準を満たせば自動反映'), ('L2 検証付き実行', '実行し証跡を残す'),
              ('L1 生成', '成果物を生成、人間が採否'), ('L0 提案', 'AIは提案のみ、人間が判断')]
    n = len(levels); bw = (X1 - X0) / n; bh = (Y0 - Y1) / n
    for i, (h, s) in enumerate(levels):
        x = X0 + bw * i; y = Y1 + bh * i
        body.append(f'<rect x="{x + 6:.0f}" y="{y + 6:.0f}" width="{bw - 12:.0f}" height="{bh - 12:.0f}" rx="12" fill="{FILLS[i]}" stroke="{STROKE}"/>')
        body.append(text(x + bw / 2, y + bh / 2 - 4, h, 15, 700, T1)); body.append(text(x + bw / 2, y + bh / 2 + 17, s, 12, 400, MUTED))
    ux, uy = X0 + bw * 1.0, Y1 + bh * 1.0
    lx, ly = X0 + bw * 2.4, Y1 + bh * 0.45
    body.append(f'<path d="M{ux:.0f} {uy:.0f} L{lx - 10:.0f} {ly + 6:.0f}" stroke="{LINE}" stroke-width="1.5"/>')
    body.append(f'<circle cx="{ux:.0f}" cy="{uy:.0f}" r="8" fill="{LINE}" stroke="#fff" stroke-width="2"/>')
    body.append(text(lx, ly, '例：UIコンポーネントの表示修正', 14, 700, LINE, 'start'))
    body.append(text(lx, ly + 20, '影響が小さく、自動検証で検出しやすい → L3〜L4', 12, 400, LINE, 'start'))
    dx, dy = X0 + bw * 4.0, Y1 + bh * 4.0
    mx, my = X0 + bw * 0.3, Y1 + bh * 4.55
    body.append(f'<path d="M{dx:.0f} {dy:.0f} L{mx + 300:.0f} {my - 6:.0f}" stroke="{ACCENT}" stroke-width="1.5"/>')
    body.append(f'<circle cx="{dx:.0f}" cy="{dy:.0f}" r="8" fill="{ACCENT}" stroke="#fff" stroke-width="2"/>')
    body.append(text(mx, my, '例：決済金額の計算ロジック変更', 14, 700, ACCENT, 'start'))
    body.append(text(mx, my + 20, '影響が大きく、見逃しの代償が高い → L0〜L1', 12, 400, ACCENT, 'start'))
    body.append(note(630, '提案モデル（公的規格ではない）。自律度はAIの能力ではなく、失敗の影響と独立検証で検出できる確率で決める'))
    return svg(1000, 660, '失敗の影響と検証可能性の2軸にL0からL4の自律度を配置した図。UI表示修正は高自律、決済ロジック変更は低自律', body)


def fig_05_constraint_shift():
    rows = read_csv('05-process-capacity.csv')
    labels = [r['stage'] for r in rows]; vals = [int(r['per_day']) for r in rows]
    body = [title('AI導入後に制約はどこへ移るか')]
    lo = min(vals); i_lo = vals.index(lo)
    rest = sorted((v, i) for i, v in enumerate(vals) if i != i_lo); nxt = rest[0][1]
    body += bars(110, 120, 780, 360, labels, vals, 44, highlight=i_lo, outline=nxt, limit=lo, limit_label='')
    body.append(text(500, 530, f'実装を40件/日まで増やしても完成は{lo}件/日。レビューを改善すると、次は{labels[nxt]}（{vals[nxt]}件/日）が制約になり得る', 16, 700, T1))
    body.append(note(562, '全作業が5工程を1回ずつ通過し、各件の作業量が同一で、手戻り・変動・並列処理の干渉を無視した仮想モデル'))
    return svg(1000, 590, 'AI導入後の5工程の処理能力の棒グラフ。実装40件/日に対しレビュー12件/日が制約で、次の制約はリリース15件/日', body)


def fig_05_organization_model():
    body = [title('案件組織と資産組織を分離する')]
    body.append(box(60, 200, 260, 130, FILLS[0], '① 事業・案件組織', '顧客価値・納期・収益・品質', hs=19, ss=13))
    body.append(box(370, 200, 260, 130, FILLS[1], '② プラットフォーム・能力開発組織', '標準・CI・Skill・評価基盤の保守と展開', hs=15, ss=12))
    body.append(box(680, 200, 260, 130, FILLS[3], '③ 探索・変革組織', '新しいAI能力の検証、将来の工程・事業モデル', hs=19, ss=12))
    body.append(path_arrow('M320 230 H358', (370, 230, 1, 0))); body.append(text(345, 180, '改善要求・案件経験', 13, 400, LINE))
    body.append(path_arrow('M370 300 H332', (320, 300, -1, 0))); body.append(text(345, 350, '標準・Skill・CI・評価基盤', 13, 400, LINE))
    body.append(path_arrow('M680 230 H642', (630, 230, -1, 0))); body.append(text(655, 180, '検証済み技術の移管', 13, 400, LINE))
    body.append(path_arrow('M630 300 H668', (680, 300, 1, 0))); body.append(text(655, 350, '制約・需要・実測データ', 13, 400, LINE))
    body.append(text(500, 410, '予算・責任・成果指標を分ける。小規模組織では同じメンバーが兼務してよい', 16, 700, T1))
    body.append(text(500, 440, '②の提供物は案件の将来原価と生産能力に影響する経営資産。リリース管理・品質保証・サポート・廃止判断まで責任を持つ', 14, 400, MUTED))
    body.append(note(495, '案件遂行と共通能力開発を同じ責任体系で管理すると、共通資産への投資が短期案件の優先順位に押し負けやすい'))
    return svg(1000, 525, '事業・案件組織、プラットフォーム・能力開発組織、探索・変革組織の3つの責任領域と、その間の流れを示す図', body)


# ---------- 第6回 ----------
def fig_06_operating_cycle():
    body = [title('経営の運転サイクル：測る → 制約 → 配分 → 実行 → 資産化 → 再評価')]
    body += loop(500, 400, 240, [('① 測る', '流入・完了・滞留・変動'), ('② 制約を特定する', 'TOC、制約の4階層'), ('③ 配分する', '限界価値、探索と深化'),
                                 ('④ 実行する', '責務分離、自律度、WIP制限'), ('⑤ 資産化する', '7変換、SECI、L2へ横展開'), ('⑥ 再評価する', '制約の移動、能力の更新')], 190, 58, '')
    body.append(text(500, 392, 'R：① → ⑤ → ① の強化ループ', 15, 700, T1)); body.append(text(500, 416, 'B：② ③ ④ で滞留を制御', 15, 700, T1))
    body.append(note(700, '6段階のどれか一つを省くと残りが機能しない。測らずに制約は見つからず、資産化しなければ生産性は複利にならない'))
    return svg(1000, 730, '測る、制約を特定する、配分する、実行する、資産化する、再評価するの6段階を円環で示した経営の運転サイクル', body)


FIGURES = {
    '01-conversion-chain.svg': fig_01_conversion_chain,
    '02-four-dimensions.svg': fig_02_four_dimensions,
    '03-flow-bottleneck.svg': fig_03_flow_bottleneck,
    '03-feedback-loops.svg': fig_03_feedback_loops,
    '03-dual-output.svg': fig_03_dual_output,
    '04-constraint-shift.svg': fig_04_constraint_shift,
    '04-lp-feasible-region.svg': fig_04_lp_feasible_region,
    '04-constraint-layers.svg': fig_04_constraint_layers,
    '05-contract-margin.svg': fig_05_contract_margin,
    '05-autonomy-matrix.svg': fig_05_autonomy_matrix,
    '05-constraint-shift.svg': fig_05_constraint_shift,
    '05-organization-model.svg': fig_05_organization_model,
    '06-operating-cycle.svg': fig_06_operating_cycle,
}


def main() -> int:
    ASSETS.mkdir(exist_ok=True)
    for name, fn in FIGURES.items():
        (ASSETS / name).write_text(fn(), encoding='utf-8')
        print('wrote', name)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
