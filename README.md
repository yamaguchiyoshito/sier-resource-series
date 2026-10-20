# AI時代のSIer経営を資源から再設計する

## 保有から変換へ、変換から制約へ、制約から経営モデルへ

![連載の全体像：第1回から第5回までの流れと、第6回のまとめ](assets/06-series-map.svg)

**経営の中心は保有量の最大化ではなく、資源から価値と将来の生産能力を作ることである。**

SIerの経営を「人月を何人投入したか」ではなく、「資源を何に変換し、何が全体を制約し、どれだけの能力が組織に残ったか」で捉え直す全6回の連載。経営資源の定義と分類（第1〜2回）、Stock・Flow・Feedbackによる資源変換システム（第3回）、制約理論と限界価値による資源配分（第4回）、AI駆動型SIerの経営モデル（第5回）を順に論じ、第6回で5つの命題・概念と数式の対応・経営の運転サイクル・チェックリストに束ねる。各回は単独でも読める。

[第1回から読む](articles/01-management-resources.md) ／ [まとめを読む](articles/06-series-summary.md) ／ [読み方](guides/READING.md)

## 目次

| 回 | 記事 | 問い |
|---|---|---|
| 01 | [経営資源とは何か —— 保有から変換へ](articles/01-management-resources.md) | 経営資源を持つことと使いこなすことの違い。AIが変える資源構造 |
| 02 | [経営資源の分類体系 —— 種類・性質・能力・戦略価値](articles/02-resource-taxonomy.md) | ペンローズからティースまでの理論系譜、7分類、3階層、8軸、3つの価値 |
| 03 | [資源の流れと変換 —— Stock・Flow・Feedbackで企業を捉える](articles/03-stock-flow-transformation.md) | 滞留と蓄積の違い、7変換類型、SECI、強化と抑制のループ、二重の価値創出 |
| 04 | [資源配分と制約 —— 全体最適を阻むボトルネック](articles/04-allocation-constraints.md) | 制約理論・機会費用・シャドープライス・待ち行列・探索と深化 |
| 05 | [AI時代のSIer経営モデル —— 人月依存から能力蓄積型へ](articles/05-ai-sier-model.md) | 5層モデル、収益モデル、知識資産、自律度、組織、移行ロードマップ |
| 06 | [まとめ —— 資源から制約へ、制約から経営モデルへ](articles/06-series-summary.md) | 5つの命題、概念と数式の対応、運転サイクル、チェックリスト |

本連載の数値例はすべて仮想値であり、実在企業の実績ではない。引用した研究は理論や調査を参照するものであり、仮想計算の根拠ではない。各回末尾の参考文献と、[参考文献と確認範囲](references/bibliography.md)を参照する。

<!-- SITE-INDEX-END: 以下はリポジトリ利用者向け。HTML閲覧版のトップページには含めない。 -->

## ファイル構成

```text
sier-resource-series/
├── README.md                  # サイトのトップページ原稿（マーカーより上）＋リポジトリ案内
├── series.json                # 連載定義（題名、各回のパス、図）
├── articles/                  # 本文（Markdown）
│   ├── 01-management-resources.md
│   ├── 02-resource-taxonomy.md
│   ├── 03-stock-flow-transformation.md
│   ├── 04-allocation-constraints.md
│   ├── 05-ai-sier-model.md
│   └── 06-series-summary.md
├── assets/                    # 図（SVG）。ファイル名は記事の連載番号で始める
├── simulation/                # 図の元データ（CSV）
├── guides/READING.md          # 読み方と表示環境
├── references/bibliography.md # 参考文献と確認範囲
├── site-src/styles.css        # 閲覧サイトのスタイル
├── scripts/
│   ├── build.py               # Markdown → _site/（HTML、MathML）
│   └── check_html.py          # _site/ のリンク・数式・スクリプト不在を検査
├── .github/workflows/pages.yml# mainへのpushでビルドしGitHub Pagesへ公開
└── claudedocs/                # 改稿の記録（サイトには載せない）
```

生成物 `_site/` は `.gitignore` で除外する。

## GitHubで読む

このREADMEと各回の `.md` をGitHubのPreviewで開く。図は相対リンク先のSVG、数式は `$...$` と `$$...$$` の数式として表示される。閲覧のためにPagesや専用アプリは必要ない。

## ブラウザで読む（ローカル生成）

Python 3.11以降とPandoc 3.xを使う。Python標準ライブラリだけで動き、追加パッケージは不要である。この版はPython 3.13・Pandoc 3.7.0.2で検証した。

```sh
python3 scripts/build.py
python3 scripts/check_html.py
```

`_site/index.html` をブラウザで開く。目次ドロワー、相対リンクの図、MathMLの数式をローカルで表示する。全回を1ファイルにまとめた `_site/complete.html` も生成され、単独で持ち運べる。

## GitHub Pagesで公開する

1. リポジトリを作成し、この内容を `main` へpushする。
2. Settings → Pages → Build and deployment の Source を **GitHub Actions** にする。
3. `main` へのpush（または Actions の「Build and publish reader」を手動実行）で `_site/` がビルドされ、公開される。URLはActionsの成功したジョブから取得する。

ワークフローはPandoc 3.7.0.2を固定して取得し、`scripts/build.py` と `scripts/check_html.py` を実行してから公開する。検証に失敗した場合は公開しない。Markdown原本・スクリプト・`claudedocs/` はサイトへ配置しない。

## 編集ルール

1. 記事は単独で読めるように結論・前提・数式・用語を記述する。
2. SVGとCSVのファイル名は各記事と同じ連載番号を使う。
3. 図表の数値を変更するときは、SVG・記事内の表・CSVを整合させる。
4. 引用・参考文献は各記事末尾と `references/bibliography.md` で確認する。掲載した出典は研究や理論を参照するものであり、仮想計算の実績根拠ではない。
5. 顧客固有情報や権利上再利用できない成果物は共通資産へ転用しない。
6. 記事を追加・改題したときは `series.json` と本READMEの目次を更新し、`scripts/build.py` と `scripts/check_html.py` を通す。
