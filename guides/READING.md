# 読み方と表示環境

[連載目次へ](../README.md)

## 連載の読み方

全6回は第1回から順に読む構成だが、各回は単独でも読めるように結論・前提・数式・用語を記述している。時間がなければ[第6回 まとめ](../articles/06-series-summary.md)から入り、§1の表と§6のチェックリストで必要な回へ戻る。

- 経営資源の考え方を押さえたい：第1回・第2回
- 滞留・蓄積・フィードバックの仕組みを知りたい：第3回
- いま何に投資すべきか判断したい：第4回
- AI導入後の経営モデルと制度を設計したい：第5回

本連載の数値例（工程能力、シャドープライス、待ち時間、契約別の粗利益、投資回収）はすべて仮想値である。自組織で使うには、まず4週間程度の基準値を取得し、介入の前後で比較する。

## GitHubのMarkdownで読む

リポジトリのREADMEから各回を開き、Preview表示を使う。図は相対リンク先のSVG、数式はGitHubが対応する `$x$` と `$$` のブロックで表示される。公式仕様は [Writing mathematical expressions](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/writing-mathematical-expressions) を参照する。

## HTMLで読む

GitHub Pagesで公開されたページ、またはローカルで生成した `_site/index.html` を開く。右上の「目次」から各回へ移動できる。全回を1ファイルにした `_site/complete.html` は、外部通信なしで読める持ち運び用である。

HTMLの数式はPandocの `--mathml` で生成したネイティブMathMLであり、JavaScriptや外部CDNを使わない。現行の主要ブラウザで表示できるが、古いブラウザやメール内プレビューでは崩れる場合がある。その場合は通常のブラウザで開くか、GitHubのMarkdown表示で読む。

## 再生成する

Python 3.11以降とPandoc 3.xを使う。追加パッケージは不要である。

```sh
python3 scripts/build.py
python3 scripts/check_html.py
```

`check_html.py` は、生成ページの相対リンクと画像がすべて実在すること、各記事にMathMLが含まれること、`<script>` が含まれないことを確認する。
