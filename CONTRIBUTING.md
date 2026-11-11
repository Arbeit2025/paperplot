# Contributing

paperplot への貢献ありがとうございます。

## 開発の流れ

1. Issue で内容を相談（任意ですが、大きな変更は先に相談を推奨）
2. ブランチを切って変更
3. テストを実行して全て通ることを確認
4. Pull Request を作成

## ローカル実行とテスト

```bash
pip install -r requirements.txt
python app.py
pip install pytest
python -m pytest tests/
```

## 方針

- 単一ファイル（app.py）構成を保つ
- 標準ライブラリと Flask 以外の依存を増やさない
- 生成ロジックは決定的に保つ（同じ入力 → 同じ出力）
