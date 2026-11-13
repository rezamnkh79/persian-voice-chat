# گفتگوی صوتی فارسی (متن ↔ صوت)

داشبورد چت + صفحه تنظیمات برای انتخاب سرویس‌های **آفلاین/آنلاین** TTS و STT.

## پیش‌فرض پیشنهادی (بدون اینترنت)

| نقش | سرویس | چرا |
|-----|--------|-----|
| TTS | **Mana Persian Piper** | سبک، سریع روی CPU، فارسی خوب |
| STT | **Vosk فارسی** | آفلاین، مدل کوچک ~۵۰MB |

## سرویس‌های پشتیبانی‌شده

### TTS
- `piper_mana` — Mana Persian Piper (آفلاین، پیش‌فرض)
- `edge` — Microsoft Edge TTS دلارا/فرید (آنلاین)
- `mms` — facebook/mms-tts-fas (آفلاین، نیاز به `torch` + `transformers`، مجوز NC)
- `pocket` — Pocket TTS Farsi v2 ONNX (آفلاین، ~۴۷۰MB، مجوز NC)

### STT
- `vosk` — مدل فارسی کوچک (آفلاین، پیش‌فرض)
- `google` — Google Web Speech (آنلاین)
- `browser` — Web Speech API در مرورگر

## نصب و اجرا

همهٔ وابستگی‌ها و مدل‌ها (Mana + Vosk + Pocket) با یک اسکریپت:

```bash
cd "voice project"
bash setup.sh
bash start.sh
```

گزینه‌ها:

```bash
bash setup.sh              # کامل (شامل Pocket ~470MB)
bash setup.sh --core       # فقط Mana + Vosk (سبک)
bash setup.sh --mms        # به‌علاوه torch برای MMS
bash setup.sh --start      # نصب و بلافاصله اجرای سرور
```

اگر مدلی ناقص باشد، همان `setup.sh` را دوباره بزن؛ فایل‌های کامل را رد می‌کند.

- چت: http://127.0.0.1:8765  
- تنظیمات: http://127.0.0.1:8765/settings  

دستی:

```bash
source .venv/bin/activate
python scripts/download_models.py --all
python run.py
```

## MMS (اختیاری)

```bash
bash setup.sh --mms
```

سپس در تنظیمات، TTS را روی **MMS-TTS Persian** بگذارید.

## Pocket TTS

با `bash setup.sh` دانلود می‌شود. اگر فقط Pocket مانده:

```bash
source .venv/bin/activate
python scripts/download_models.py --only-pocket
```

اگر مدل آماده نباشد، چت به‌صورت خودکار به Piper برمی‌گردد.

## نکات

- برای کار کاملاً آفلاین: TTS=Piper و STT=Vosk
- Edge / Google / Browser فقط با اینترنت
- مجوز MMS و Pocket فعلاً CC-BY-NC-4.0 است (غیرتجاری مگر با مجوز)
