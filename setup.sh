#!/usr/bin/env bash
# نصب وابستگی‌ها + دانلود همه مدل‌ها. هر بار قابل اجراست؛ فایل کامل را دوباره نمی‌گیرد.
#
#   bash setup.sh              # محیط، پکیج‌ها، Mana + Vosk + Pocket
#   bash setup.sh --core       # فقط Mana + Vosk (سبک، بدون Pocket ~470MB)
#   bash setup.sh --mms        # به‌علاوه torch برای MMS-TTS
#   bash setup.sh --start      # بعد از نصب، سرور را هم بالا بیاور
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

CORE_ONLY=0
WITH_MMS=0
DO_START=0
for arg in "$@"; do
  case "$arg" in
    --core) CORE_ONLY=1 ;;
    --mms) WITH_MMS=1 ;;
    --start) DO_START=1 ;;
    -h|--help)
      sed -n '2,10p' "$0"
      exit 0
      ;;
  esac
done

PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "python3 پیدا نشد."
  exit 1
fi

echo "==> venv"
if [[ ! -d .venv ]]; then
  "$PYTHON_BIN" -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

echo "==> pip packages"
python -m pip install -U pip
python -m pip install -r requirements.txt

if [[ "$WITH_MMS" -eq 1 ]]; then
  echo "==> MMS extras (torch + transformers)"
  python -m pip install torch transformers accelerate --index-url https://download.pytorch.org/whl/cpu || \
    python -m pip install torch transformers accelerate
fi

echo "==> models"
if [[ "$CORE_ONLY" -eq 1 ]]; then
  python scripts/download_models.py
else
  python scripts/download_models.py --all
fi

echo
echo "آماده است."
echo "  چت:       source .venv/bin/activate && python run.py"
echo "  آدرس:     http://127.0.0.1:8765"
echo "  تنظیمات:  http://127.0.0.1:8765/settings"

if [[ "$DO_START" -eq 1 ]]; then
  echo "==> starting server"
  exec python run.py
fi
