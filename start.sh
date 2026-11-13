#!/usr/bin/env bash
# اجرای سرور. اگر مدل/venv نباشد، اول setup.sh را صدا می‌زند.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [[ ! -x .venv/bin/python ]]; then
  echo "محیط آماده نیست؛ setup.sh اجرا می‌شود..."
  bash setup.sh
fi

source .venv/bin/activate
exec python run.py
