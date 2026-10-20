#!/usr/bin/env python3
"""生成した _site/ を検査する。相対リンクと画像の実在、各記事のMathML存在、外部スクリプト不在を確認する。"""
from __future__ import annotations
from html.parser import HTMLParser
import json
from pathlib import Path
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / '_site'


class Collector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.refs: list[tuple[str, str]] = []
        self.scripts = 0
        self.math = 0
        self.ids: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if tag == 'script':
            self.scripts += 1
        if tag == 'math':
            self.math += 1
        if a.get('id'):
            self.ids.add(a['id'])
        for attr in ('href', 'src'):
            if a.get(attr):
                self.refs.append((attr, a[attr]))


def main() -> int:
    if not SITE.exists():
        print('_site/ がない。先に scripts/build.py を実行する。', file=sys.stderr)
        return 1
    series = json.loads((ROOT / 'series.json').read_text(encoding='utf-8'))
    # 原稿に $ を含む記事だけ、MathMLへの変換を要求する
    math_pages = {SITE / (c['path'][:-3] + '.html') for c in series['chapters'] if '$' in (ROOT / c['path']).read_text(encoding='utf-8')}
    errors: list[str] = []
    pages = sorted(SITE.rglob('*.html'))
    for page in pages:
        parser = Collector()
        parser.feed(page.read_text(encoding='utf-8'))
        if parser.scripts:
            errors.append(f'{page.relative_to(SITE)}: <script> を含む')
        if page in math_pages and parser.math == 0:
            errors.append(f'{page.relative_to(SITE)}: MathML が無い')
        for attr, ref in parser.refs:
            parsed = urlsplit(ref)
            if parsed.scheme or ref.startswith(('#', '//', 'data:')):
                if ref.startswith('#') and ref[1:] and ref[1:] not in parser.ids:
                    errors.append(f'{page.relative_to(SITE)}: ページ内アンカー {ref} が無い')
                continue
            target = (page.parent / unquote(parsed.path)).resolve()
            if not target.exists():
                errors.append(f'{page.relative_to(SITE)}: {attr}="{ref}" が解決しない')
    for e in errors:
        print(e, file=sys.stderr)
    print(json.dumps({'pages': len(pages), 'errors': len(errors)}, ensure_ascii=False))
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
