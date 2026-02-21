# ブランチ戦略 & 貢献ガイド

## 推奨ブランチ戦略

### オプション1: シンプル型（ソロ開発・素早いイテレーション向け）✨ 推奨

ハッカソンで素早く実験したい場合に最適。

```
main (安定版・ドキュメント)
  ↓
playground/[poc-name]/ で直接開発
  ↓
動作確認したらそのままpush
```

**メリット**:
- 最速でイテレーション
- ブランチ管理のオーバーヘッドなし
- playgroundは実験場所なので壊れても問題なし

**ルール**:
- ✅ playground配下は自由に実験
- ✅ README等のドキュメントは直接mainに push
- ⚠️ 動かないコードをpushする場合はREADMEに`[WIP]`マーク

**使い方**:
```bash
# 新しいPOC開始
mkdir playground/my-new-poc
cd playground/my-new-poc

# 開発
# ... コーディング ...

# そのままpush
git add .
git commit -m "Add: my-new-poc initial implementation"
git push origin main
```

---

### オプション2: Dev/Main型（複数人・中規模プロジェクト向け）

複数人で開発する、またはmainを常に動く状態にしたい場合。

```
main (安定版のみ)
  ↑
  └─ dev (実験・WIP)
       ↑
       └─ feature/poc-name (個別POC)
```

**ブランチ説明**:
- `main`: 動作確認済み、デモ可能な状態
- `dev`: 実験中のコード、WIP可
- `feature/xxx`: 特定のPOC開発

**使い方**:
```bash
# 新しいPOC開始
git checkout dev
git checkout -b feature/medical-diagnosis-poc

# 開発
# ... コーディング ...

# devにマージ
git checkout dev
git merge feature/medical-diagnosis-poc
git push origin dev

# 動作確認できたらmainへ
git checkout main
git merge dev
git push origin main
```

**メリット**:
- mainが常にクリーン
- 並行開発がしやすい
- レビュープロセスを入れられる

**デメリット**:
- 少し手間がかかる
- ハッカソンには重い可能性

---

### オプション3: POCブランチ型（多数のアイデアを並行試行）

複数のアイデアを同時に試したい場合。

```
main (ドキュメントのみ)
  ↑
  ├─ poc/medical-diagnosis
  ├─ poc/legacy-migration
  ├─ poc/travel-planner
  └─ poc/music-generator
```

**使い方**:
```bash
# 新しいPOC開始
git checkout -b poc/medical-diagnosis

# playground配下に実装
mkdir playground/medical-diagnosis
# ... 開発 ...

# POCブランチにpush
git add playground/medical-diagnosis
git commit -m "WIP: medical diagnosis POC"
git push origin poc/medical-diagnosis

# 完成したらmainにマージ
git checkout main
git merge poc/medical-diagnosis
git push origin main

# 不要になったブランチは削除
git branch -d poc/medical-diagnosis
git push origin --delete poc/medical-diagnosis
```

**メリット**:
- 複数アイデアを独立して管理
- 失敗したPOCはブランチごと削除可能
- 並行開発が非常にしやすい

---

## 状況別の推奨

| 状況 | 推奨戦略 | 理由 |
|------|---------|------|
| **1人で開発** | オプション1（シンプル型） | 最速、オーバーヘッドなし |
| **2-3人のチーム** | オプション2（Dev/Main型） | 並行開発しやすく、mainを守れる |
| **5個以上のPOCを試す** | オプション3（POCブランチ型） | アイデアごとに独立管理 |
| **ハッカソン当日** | オプション1（シンプル型） | スピード最優先 |
| **長期プロジェクト** | オプション2（Dev/Main型） | 安定性と開発速度のバランス |

---

## 現在の状況に合わせた提案

現状、playground配下で実験しているので、**オプション1（シンプル型）** が最適です。

### 今すぐ実施すべきこと

#### 1. .gitignoreの調整
```bash
# .gitignoreに追加（既に設定済み）
*.log
.env
__pycache__/
node_modules/
```

#### 2. READMEにWIPマークのルール追加
```markdown
# playground/my-poc/README.md
# [WIP] My POC Title

現在開発中です。動作しない可能性があります。
```

#### 3. コミットメッセージの規約（オプション）
```bash
# 新機能
git commit -m "Add: new feature description"

# バグ修正
git commit -m "Fix: bug description"

# WIP（動かない状態でpush）
git commit -m "WIP: working on feature X"

# ドキュメント
git commit -m "Docs: update README"
```

---

## チーム開発に移行する場合

### ステップ1: devブランチの作成
```bash
git checkout -b dev
git push -u origin dev
```

### ステップ2: ブランチ保護ルールの設定（GitHub）
1. Settings > Branches
2. "Add rule" for `main`
3. ✅ Require pull request reviews before merging
4. ✅ Require status checks to pass

### ステップ3: Pull Request テンプレート作成
```bash
mkdir -p .github
```

```markdown
<!-- .github/pull_request_template.md -->
## 概要
<!-- このPRで何を実装したか -->

## 変更内容
- [ ] 新しいPOC追加
- [ ] バグ修正
- [ ] ドキュメント更新

## 動作確認
- [ ] ローカルで動作確認済み
- [ ] サンプルコード実行済み

## スクリーンショット（あれば）

## レビュー観点
<!-- レビュワーに特に見てほしいポイント -->
```

---

## FAQ

### Q: 壊れたコードをpushしても良い？
A: playground配下なら問題なし。ただしREADMEに`[WIP]`マークを付けること。

### Q: main直pushとPRどちらが良い？
A:
- 1人開発: main直push（オプション1）
- チーム開発: PR経由（オプション2）

### Q: ブランチはいつ削除する？
A:
- POCが失敗 → すぐ削除
- POCが成功してmainにマージ済み → 削除
- まだ実験中 → 残す

### Q: コンフリクトが起きたら？
A:
```bash
# 最新のmainを取得
git fetch origin main

# 現在のブランチにマージ
git merge origin/main

# コンフリクトを解決
# ... エディタで修正 ...

git add .
git commit -m "Merge: resolve conflicts with main"
```

---

## まとめ

**現在の状況（playgroundで実験中）**
→ **オプション1（シンプル型）を推奨** 🎯

理由:
- ✅ ハッカソンは速度が命
- ✅ playground配下は実験場所なので自由に壊せる
- ✅ ドキュメントは別ディレクトリなので影響なし
- ✅ オーバーヘッド最小

必要に応じて後からオプション2や3に移行可能です。
