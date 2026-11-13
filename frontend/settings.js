(() => {
  "use strict";

  const form = document.getElementById("settingsForm");
  const flash = document.getElementById("settingsFlash");
  const ttsCards = document.getElementById("ttsCards");
  const sttCards = document.getElementById("sttCards");
  const testAudio = document.getElementById("testAudio");

  let selectedTts = "piper_mana";
  let selectedStt = "vosk";

  function showFlash(text, ok = true) {
    flash.textContent = text;
    flash.classList.remove("hidden", "ok", "err");
    flash.classList.add(ok ? "ok" : "err");
  }

  function cardHtml(p, group) {
    const badge = p.offline ? "آفلاین" : "آنلاین";
    const ready = p.ready ? "آماده" : "نیاز به نصب/مدل";
    const readyClass = p.ready ? "ready" : "not-ready";
    return `
      <label class="provider-card ${readyClass}">
        <input type="radio" name="${group}" value="${p.id}" />
        <div>
          <div class="provider-title">${p.title}</div>
          <div class="provider-desc">${p.description}</div>
          <div class="provider-meta">
            <span class="tag">${badge}</span>
            <span class="tag ${readyClass}">${ready}</span>
          </div>
          <div class="provider-detail">${p.detail || ""}${p.license_note ? " · " + p.license_note : ""}</div>
        </div>
      </label>`;
  }

  function fillProviders(data) {
    ttsCards.innerHTML = data.providers.tts.map((p) => cardHtml(p, "tts")).join("");
    sttCards.innerHTML = data.providers.stt.map((p) => cardHtml(p, "stt")).join("");

    selectedTts = data.settings.tts_provider;
    selectedStt = data.settings.stt_provider;

    const ttsRadio = form.querySelector(`input[name="tts"][value="${selectedTts}"]`);
    const sttRadio = form.querySelector(`input[name="stt"][value="${selectedStt}"]`);
    if (ttsRadio) ttsRadio.checked = true;
    if (sttRadio) sttRadio.checked = true;

    document.getElementById("piperLength").value = data.settings.piper_length_scale ?? 1;
    document.getElementById("piperPath").value = data.settings.piper_model_path || "";
    document.getElementById("edgeVoice").value = data.settings.edge_voice || "female";
    document.getElementById("mmsModel").value = data.settings.mms_model_id || "facebook/mms-tts-fas";
    document.getElementById("pocketDir").value = data.settings.pocket_model_dir || "";
    document.getElementById("pocketVoice").value = data.settings.pocket_voice || "female";
    document.getElementById("voskPath").value = data.settings.vosk_model_path || "";
    document.getElementById("sttLang").value = data.settings.stt_language || "fa-IR";
  }

  async function load() {
    const res = await fetch("/api/settings");
    if (!res.ok) throw new Error("خواندن تنظیمات ناموفق بود");
    fillProviders(await res.json());
  }

  function collectPayload() {
    const tts = form.querySelector('input[name="tts"]:checked');
    const stt = form.querySelector('input[name="stt"]:checked');
    return {
      tts_provider: tts ? tts.value : selectedTts,
      stt_provider: stt ? stt.value : selectedStt,
      piper_length_scale: Number(document.getElementById("piperLength").value || 1),
      piper_model_path: document.getElementById("piperPath").value.trim(),
      edge_voice: document.getElementById("edgeVoice").value,
      mms_model_id: document.getElementById("mmsModel").value.trim(),
      pocket_model_dir: document.getElementById("pocketDir").value.trim(),
      pocket_voice: document.getElementById("pocketVoice").value,
      vosk_model_path: document.getElementById("voskPath").value.trim(),
      stt_language: document.getElementById("sttLang").value.trim() || "fa-IR",
    };
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      const res = await fetch("/api/settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(collectPayload()),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "ذخیره ناموفق");
      fillProviders(data);
      showFlash("تنظیمات ذخیره شد.");
    } catch (err) {
      showFlash(err.message || String(err), false);
    }
  });

  document.getElementById("resetBtn").addEventListener("click", async () => {
    if (!confirm("تنظیمات به حالت پیش‌فرض برگردد؟")) return;
    const res = await fetch("/api/settings/reset", { method: "POST" });
    const data = await res.json();
    fillProviders(data);
    showFlash("پیش‌فرض‌ها بازیابی شد.");
  });

  document.getElementById("testTtsBtn").addEventListener("click", async () => {
    try {
      // save first so test uses current form values
      await fetch("/api/settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(collectPayload()),
      });
      const res = await fetch("/api/tts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: "سلام، این یک آزمایش سرویس متن به گفتار فارسی است.",
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "تست TTS ناموفق بود");
      }
      const blob = await res.blob();
      testAudio.src = URL.createObjectURL(blob);
      testAudio.classList.remove("hidden");
      await testAudio.play().catch(() => {});
      const provider = res.headers.get("X-TTS-Provider") || "?";
      showFlash(`تست TTS موفق بود · ارائه‌دهنده: ${provider}`);
    } catch (err) {
      showFlash(err.message || String(err), false);
    }
  });

  load().catch((err) => showFlash(err.message || String(err), false));
})();
