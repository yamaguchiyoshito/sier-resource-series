#!/usr/bin/env python3
"""Markdown原稿からGitHub Pages用の閲覧サイト(_site/)を生成する。数式はネイティブMathML。Pandoc 3.x が必要。"""
from __future__ import annotations
import argparse
import base64
import html
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
READER = 'markdown+tex_math_dollars+footnotes+pipe_tables+autolink_bare_uris'
SITE_INDEX_END = '<!-- SITE-INDEX-END'
STATIC_DIRS = ('assets', 'simulation')


def site_index_text(text: str) -> str:
    """READMEのうち、閲覧サイトのトップページへ載せる範囲(マーカーより前)を返す。"""
    head, marker, _ = text.partition(SITE_INDEX_END)
    return head.rstrip() + '\n' if marker else text


def run_pandoc(text: str, args: list[str]) -> str:
    if not shutil.which('pandoc'):
        raise RuntimeError('Pandoc 3.x が必要である。guides/READING.md を参照。')
    result = subprocess.run(['pandoc', *args], input=text, text=True, encoding='utf-8', capture_output=True, check=False)
    if result.returncode or result.stderr.strip():
        raise RuntimeError(f'Pandoc conversion failed: {result.stderr.strip()}')
    return result.stdout


def parse_markdown(text: str) -> dict:
    # --columns を十分大きくし、パイプテーブルに区切り行由来の相対列幅(colgroup)を付けさせない。
    # 列幅はブラウザが内容に応じて決める(番号列は狭く、本文列は広く)。
    return json.loads(run_pandoc(text, ['--from', READER, '--to', 'json', '--columns=10000']))


def map_url(url: str) -> str:
    parsed = urlsplit(url)
    if parsed.scheme or url.startswith(('#', '//')):
        return url
    path = parsed.path
    if path.endswith('.md'):
        path = path[:-3] + '.html'
        if Path(path).name == 'README.html':
            path = path[:-len('README.html')] + 'index.html'
    return path + ('?' + parsed.query if parsed.query else '') + ('#' + parsed.fragment if parsed.fragment else '')


def transform_links(node: object) -> None:
    if isinstance(node, dict):
        if node.get('t') in ('Link', 'Image'):
            node['c'][-1][0] = map_url(node['c'][-1][0])
        for child in node.values():
            transform_links(child)
    elif isinstance(node, list):
        for child in node:
            transform_links(child)


def render(text: str, prefix: str = '') -> str:
    ast = parse_markdown(text)
    transform_links(ast)
    args = ['--from', 'json', '--to', 'html5', '--mathml', '--wrap=none']
    if prefix:
        args += ['--id-prefix', prefix]
    output = run_pandoc(json.dumps(ast, ensure_ascii=False), args)
    if prefix:
        output = output.replace('id="footnotes"', f'id="{prefix}footnotes"')
    return wrap_tables(output)


def wrap_tables(output: str) -> str:
    """<table> を横スクロール用の <div class="table-wrap"> で包む。table 自体を display:block にすると行が内容幅で止まるため。"""
    output = re.sub(r'<table(\s[^>]*)?>', lambda m: f'<div class="table-wrap"><table{m.group(1) or ""}>', output)
    return output.replace('</table>', '</table></div>')


def wrap_page(title: str, body: str, source: Path, series: dict, css: str) -> str:
    depth = len(source.parent.parts)
    root_link = '../' * depth
    site_title = series['title']
    links = []

    def link(c: dict) -> str:
        current = source.as_posix() == c['path']
        cls = ' current' if current else ''
        aria = ' aria-current="page"' if current else ''
        return (f'<a class="chapter-link{cls}" href="{root_link}{map_url(c["path"])}"{aria}>'
                f'<span>{c["number"]:02d}</span>{html.escape(c["title"])}</a>')

    for k in series.get('cours', []):
        lo, hi = k['chapters']
        members = [c for c in series['chapters'] if lo <= c['number'] <= hi]
        if not members:
            continue
        if len(series['cours']) > 1:
            links.append(f'<div class="toc-cour">第{k["number"]}部　{html.escape(k["title"])}</div>')
        for c in members:
            links.append(link(c))
    footer_label = f'全{len(series["chapters"])}回 / 第{str(series.get("version", "1")).split(".")[0]}版'
    return f'''<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light dark"><title>{html.escape(site_title) if title == site_title else html.escape(title) + ' | ' + html.escape(site_title)}</title>
<style>{css}</style></head><body>
<a class="skip" href="#main">本文へ移動</a>
<input type="checkbox" id="toc-state" class="toc-state" aria-label="目次を開く">
<header class="topbar"><a href="{root_link}index.html" class="brand">{html.escape(site_title)}<span>{html.escape(series.get("eyebrow", ""))}</span></a><div class="topbar-actions"><a href="{root_link}guides/READING.html">読み方</a><label class="toc-toggle" for="toc-state"><svg viewBox="0 0 20 20" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M3 5h14M3 10h14M3 15h14"/></svg>目次</label></div></header>
<label class="toc-backdrop" for="toc-state" aria-hidden="true"></label>
<aside class="toc-drawer" aria-label="連載の目次"><div class="toc-drawer-head"><strong>連載の目次</strong><label class="toc-close" for="toc-state" title="閉じる"><svg viewBox="0 0 20 20" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M5 5l10 10M15 5L5 15"/></svg></label></div><nav aria-label="連載の目次">{''.join(links)}</nav><div class="toc-drawer-foot"><p>{html.escape(series.get("tagline", ""))}</p><a href="{root_link}references/bibliography.html">参考文献と確認範囲</a></div></aside>
<div class="layout"><main id="main" tabindex="-1"><article>{body}</article><footer>{footer_label} — 本文はMarkdown、図はSVG、数式はMathML。<br>数値例はすべて仮想値であり、実在企業の実績ではない。</footer></main></div></body></html>'''


def make_book(series: dict, css: str, dest: Path, cour: dict) -> None:
    """全回を1ファイルにまとめた持ち運び用HTMLを生成する。SVGは埋め込み、他の相対リンクはサイトルート基準へ直す。"""
    lo, hi = cour['chapters']
    chapters = [c for c in series['chapters'] if lo <= c['number'] <= hi]
    anchors = {str((ROOT / c['path']).resolve()): f'#chapter-{c["number"]:02d}' for c in chapters}
    pieces = []
    for c in chapters:
        source = ROOT / c['path']
        body = render(source.read_text(encoding='utf-8'), prefix=f'c{c["number"]:02d}-')

        def rewrite(match: re.Match) -> str:
            attr, url = match.group(1), html.unescape(match.group(2))
            parsed = urlsplit(url)
            if parsed.scheme or url.startswith(('#', '//', 'data:')):
                return match.group(0)
            raw = parsed.path
            if attr == 'src' and raw.endswith('.svg'):
                path = (source.parent / raw).resolve()
                path.relative_to(ROOT)
                encoded = base64.b64encode(path.read_bytes()).decode('ascii')
                return f'src="data:image/svg+xml;base64,{encoded}"'
            if attr == 'href':
                if raw.endswith('index.html'):
                    return 'href="#book-contents"'
                target = (source.parent / (raw[:-5] + '.md' if raw.endswith('.html') else raw)).resolve()
                if str(target) in anchors:
                    return f'href="{anchors[str(target)]}{"#" + parsed.fragment if parsed.fragment else ""}"'
                try:
                    rel = target.relative_to(ROOT).as_posix()
                except ValueError:
                    return match.group(0)
                return f'href="{map_url(rel)}"'
            return match.group(0)

        body = re.sub(r'(href|src)="([^"]*)"', rewrite, body)
        pieces.append(f'<section class="book-chapter" id="chapter-{c["number"]:02d}">{body}</section>')
    toc = ''.join(f'<li><a href="#chapter-{c["number"]:02d}">第{c["number"]}回　{html.escape(c["title"])}</a></li>' for c in chapters)
    title = html.escape(series['title'])
    doc = f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title} — 全{len(chapters)}回</title><style>{css}
.book{{max-width:860px;margin:auto;padding:32px 24px}}.book-chapter{{padding-top:55px;margin-top:65px;border-top:2px solid var(--line)}}@media print{{.book-chapter{{break-before:page}}}}</style></head><body><main class="book"><section id="book-contents"><p class="eyebrow">{html.escape(series.get("eyebrow", ""))} — COMPLETE SERIES</p><h1>{title}</h1><h2>{html.escape(series["subtitle"])}</h2><p>このファイルは外部通信なしで閲覧できる。数式はネイティブMathML、図は埋め込みSVGで表示する。</p><ol>{toc}</ol></section>{''.join(pieces)}</main></body></html>'''
    dest.write_text(doc, encoding='utf-8')


def build(output: Path) -> dict:
    output = output.resolve()
    if output == ROOT or ROOT.is_relative_to(output):
        raise RuntimeError('出力先にはリポジトリ自身またはその親を指定できない。')
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    series = json.loads((ROOT / 'series.json').read_text(encoding='utf-8'))
    css = (ROOT / 'site-src/styles.css').read_text(encoding='utf-8')
    documents = [ROOT / 'README.md',
                 *(ROOT / c['path'] for c in series['chapters']),
                 *sorted((ROOT / 'guides').glob('*.md')),
                 ROOT / 'references/bibliography.md']
    count = 0
    for p in documents:
        source = p.relative_to(ROOT)
        target = output / map_url(source.as_posix())
        target.parent.mkdir(parents=True, exist_ok=True)
        text = p.read_text(encoding='utf-8')
        if p.name == 'README.md':
            text = site_index_text(text)
        title = re.search(r'^# (.+)', text, re.M).group(1)
        content = render(text)
        count += content.count('<math ')
        target.write_text(wrap_page(title, content, source, series, css), encoding='utf-8')
    for name in STATIC_DIRS:
        shutil.copytree(ROOT / name, output / name, dirs_exist_ok=True, ignore=shutil.ignore_patterns('.DS_Store'))
    shutil.copy2(ROOT / 'series.json', output / 'series.json')
    (output / '.nojekyll').write_text('', encoding='utf-8')
    standalone = []
    for k in series.get('cours', []):
        lo, hi = k['chapters']
        if not any(lo <= c['number'] <= hi for c in series['chapters']):
            continue
        name = 'complete.html' if len(series['cours']) == 1 else f'complete-{k["number"]}.html'
        make_book(series, css, output / name, k)
        standalone.append(name)
    result = dict(pages=len(documents), chapters=len(series['chapters']), math_nodes=count,
                  svg_files=len(list((output / 'assets').rglob('*.svg'))), standalone=standalone)
    (output / 'build-report.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / '_site')
    args = parser.parse_args()
    try:
        print(json.dumps(build(args.output), ensure_ascii=False, indent=2))
        return 0
    except (RuntimeError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
