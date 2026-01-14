# Industry News Dashboard / Discord Bot

## 概要

本リポジトリは、**任意の業界に特化したニュースを自動収集・蓄積・分析し、
Discord 配信＋Web ダッシュボードで可視化するための汎用ニュース分析基盤**です。

RSS を情報源として、

* 業界ニュースの自動収集
* SQLite による履歴データの蓄積（最大で年単位）
* 日別件数・カテゴリ別・ソース別の時系列分析
* Chart.js を用いた Web ダッシュボードの自動生成
* Discord への自動投稿（AI要約あり／なし切替可）
* Excel（xlsx）形式でのデータエクスポート

を **完全自動** で行います。

---

## このプロジェクトの思想（重要）

このプロジェクトは **特定業界に固定されたツールではありません**。

* サイバーセキュリティ
* 金融
* 半導体
* AI / スタートアップ
* 医療
* エネルギー
* 政策・公共分野
* 学術研究分野

など、**RSS が存在する業界であればすべて対応可能**です。

どの業界を対象にするかは
👉 **`config.yaml` を編集するユーザー自身が決める設計**
になっています。

---

## 主な機能

### 1. 業界ニュースの自動収集（RSS）

* 複数メディアの RSS を定期取得
* 重複記事（URLベース）を自動排除
* 記事タイトルからカテゴリを自動付与
* 業界キーワードに基づく関連性フィルタリング

---

### 2. データベースによる履歴蓄積（SQLite）

* `data/news.db` に全記事を保存
* 同一URLは一度しか保存されない（upsert）
* 数ヶ月〜数年単位でデータを蓄積可能
* 過去データを使ったトレンド分析が可能

---

### 3. 分析・可視化（Webダッシュボード）

`docs/index.html` として自動生成されます。

表示内容：

* 日別記事数（Total）
* カテゴリ別（日別推移）
* ソース別（日別推移）
* 表示期間の切替（例：30日 / 90日 / 1年 / 3年）

👉 GitHub Pages でそのまま公開可能

---

### 4. Discord への自動配信

* 毎日決まった時間に Discord に投稿
* OpenAI API を使った **日本語業界要約**（ON/OFF可）
* AI失敗時は自動で簡易版にフォールバック

---

### 5. Excel エクスポート

* 記事データを `.xlsx` 形式で出力
* 業界レポート作成・分析・共有にそのまま利用可能
* GitHub Pages 経由でダウンロードも可能

---

## ディレクトリ構成

```
.
├── src/
│   ├── main.py              # メイン処理（取得〜保存〜配信）
│   ├── analytics.py         # 集計・分析ロジック
│   ├── dashboard.py         # HTMLダッシュボード生成
│   ├── export_excel.py      # Excelエクスポート
│   ├── db.py                # SQLite操作
│   └── config.yaml          # ★業界設定ファイル（最重要）
│
├── data/
│   └── news.db              # SQLiteデータベース
│
├── docs/
│   ├── index.html           # ダッシュボード
│   ├── data/                # 集計結果JSON
│   └── exports/             # Excelファイル
│
├── .github/workflows/
│   └── daily.yml            # GitHub Actions（自動実行）
│
├── requirements.txt
└── README.md
```

---

## 初めて使う人向け：セットアップ手順

### 1. リポジトリをクローン

```bash
git clone https://github.com/yourname/industry-news-dashboard.git
cd industry-news-dashboard
```

---

### 2. Python環境を準備

```bash
python -m venv .venv
source .venv/bin/activate   # Windowsは .venv\Scripts\activate
pip install -r requirements.txt
```

---

### 3. config.yaml を編集（最重要）

このプロジェクトの **すべての挙動は config.yaml で決まります**。

#### config.yaml の基本構造

```yaml
industry: "あなたの研究したい業界名"

use_ai_summary: true
top_n: 5

keywords:
  カテゴリ名1:
    - キーワードA
    - キーワードB
  カテゴリ名2:
    - キーワードC
    - キーワードD

sources:
  - name: メディア名
    rss: https://example.com/rss
```

---

### 4. industry の設定

```yaml
industry: "半導体業界"
```

👉

* ダッシュボードの表示名
* Discord投稿のタイトル
* AI要約の文脈

に使われます。

---

### 5. keywords の設定（超重要）

ここで **「何を業界ニュースとみなすか」** を定義します。

#### 例：サイバーセキュリティ

```yaml
keywords:
  脆弱性:
    - CVE
    - vulnerability
  マルウェア:
    - malware
    - ransomware
  攻撃:
    - attack
    - breach
```

#### 例：金融業界

```yaml
keywords:
  金融政策:
    - interest rate
    - inflation
  市場:
    - stock
    - bond
    - market
```

* **タイトルに含まれる単語**でカテゴリ判定されます
* 英語・日本語どちらでもOK
* あいまいでもOK（研究用途向け）

---

### 6. RSS の設定

```yaml
sources:
  - name: Reuters
    rss: https://www.reuters.com/rssFeed/businessNews
  - name: Bloomberg
    rss: https://www.bloomberg.com/feed/podcast/etf-report.xml
```

* RSSが存在するサイトなら何でも可
* メディア名は表示用
* 研究対象業界に応じて自由に変更してください

---

## 実行方法（ローカル）

```bash
python -m src.main
```

* DBが更新される
* docs/index.html が生成される
* Discord に投稿される
* Excel が出力される

---

## 自動実行（GitHub Actions）

`.github/workflows/daily.yml` により、

* 毎日決まった時間に自動実行
* データ更新 → GitHub に自動コミット
* GitHub Pages で最新ダッシュボードが公開

が行われます。

---

## 対象ユーザー

* 業界分析を行う学生・研究者
* コンサルタント
* データアナリスト
* エンジニア
* 個人研究者
* 業界動向を定点観測したい人

---

## ライセンス・利用について

* 個人・研究・教育用途：自由
* 商用利用：自己責任で可
* RSS利用規約は各サイトに従ってください

---

## 最後に

このプロジェクトは
**「ニュースを読む」から「ニュースをデータとして扱う」**
ための基盤です。

業界を変えれば、そのまま

* 市場分析ツール
* 研究用データ収集基盤
* 社内インテリジェンスツール

として使えます。


