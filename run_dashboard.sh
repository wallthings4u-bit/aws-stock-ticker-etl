#!/usr/bin/env bash
set -e

# スクリプト自身の場所（プロジェクトルート）へ移動
cd "$(dirname "$0")"

# 仮想環境 .venv が未作成の場合は自動構築＆依存パッケージをインストール
if [ ! -d ".venv" ]; then
  echo "[INFO] 仮想環境(.venv)を作成し、パッケージをインストールしています..."
  python3 -m venv .venv
  .venv/bin/pip install --upgrade pip
  .venv/bin/pip install -r src/dashboard/requirements.txt
fi

echo "[INFO] Streamlit ダッシュボードを起動します..."
exec .venv/bin/streamlit run src/dashboard/app.py
