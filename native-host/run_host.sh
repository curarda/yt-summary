#!/bin/zsh
DIR="$(cd "$(dirname "$0")/.." && pwd)"
exec "$DIR/.venv/bin/python" "$DIR/native-host/yt_summary_host.py"
