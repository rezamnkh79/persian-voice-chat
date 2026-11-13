(() => {
  "use strict";

  const chatEl = document.getElementById("chat");
  const formEl = document.getElementById("composer");
  const inputEl = document.getElementById("messageInput");
  const micBtn = document.getElementById("micBtn");
  const stopBtn = document.getElementById("stopBtn");
  const sendBtn = document.getElementById("sendBtn");
  const fileInput = document.getElementById("fileInput");
  const voiceSelect = document.getElementById("voiceSelect");
  const edgeVoiceField = document.getElementById("edgeVoiceField");
  const statusPill = document.getElementById("statusPill");
  const recordingBar = document.getElementById("recordingBar");
  const recTimer = document.getElementById("recTimer");

  let mediaRecorder = null;
  let recordedChunks = [];
  let recordingStartedAt = 0;
  let timerInterval = null;
  let busy = false;
  let activeSettings = null;
  let browserRecognition = null;

  function setStatus(state, text) {
    statusPill.dataset.state = state;
    statusPill.textContent = text;
  }

  function setBusy(value) {
    busy = value;
    sendBtn.disabled = value;
    micBtn.disabled = value && !mediaRecorder && !browserRecognition;
    fileInput.disabled = value;
  }

  function formatTime(ms) {
    const total = Math.floor(ms / 1000);
    const m = String(Math.floor(total / 60)).padStart(2, "0");
    const s = String(total % 60).padStart(2, "0");
    return `${m}:${s}`.replace(/\d/g, (d) => "۰۱۲۳۴۵۶۷۸۹"[d]);
  }

  function clearEmptyHint() {
    const hint = chatEl.querySelector(".empty-hint");
    if (hint) hint.remove();
  }

  function addBubble({ role, title, text, audioUrl, error }) {
    clearEmptyHint();
    const bubble = document.createElement("article");
    bubble.className = `bubble ${error ? "error" : role}`;

    const meta = document.createElement("div");
    meta.className = "meta";
    const now = new Date();
    const time = now.toLocaleTimeString("fa-IR", { hour: "2-digit", minute: "2-digit" });
    meta.innerHTML = `<span>${title}</span><span>${time}</span>`;
    bubble.appendChild(meta);

    if (text) {
      const body = document.createElement("div");
      body.textContent = text;
      bubble.appendChild(body);
    }

    if (audioUrl) {
      const audio = document.createElement("audio");
      audio.controls = true;
      audio.preload = "metadata";
      audio.src = audioUrl;
      bubble.appendChild(audio);
      audio.play().catch(() => {});
    }

    chatEl.appendChild(bubble);
    chatEl.scrollTop = chatEl.scrollHeight;
    return bubble;
  }

  function showWelcome() {
    if (chatEl.children.length) return;
    const hint = document.createElement("div");
    hint.className = "empty-hint";
    hint.innerHTML =
      "متن بنویسید تا به صوت تبدیل شود.<br/>" +
      "یا ویس بگیرید تا به متن تبدیل شود.<br/>" +
      "سرویس‌ها را از صفحه <a href='/settings'>تنظیمات</a> عوض کنید.";
    chatEl.appendChild(hint);
  }

  async function checkHealth() {
    try {
      const res = await fetch("/api/health");
      if (!res.ok) throw new Error("health failed");
      const data = await res.json();
      activeSettings = data.settings;
      const tts = data.tts ? data.tts.title : data.settings.tts_provider;
      const stt = data.stt ? data.stt.title : data.settings.stt_provider;
      const offlineBits = [];
      if (data.tts && data.tts.offline) offlineBits.push("TTS آفلاین");
      if (data.stt && data.stt.offline) offlineBits.push("STT آفلاین");
      const mode = offlineBits.length ? offlineBits.join(" · ") : "حالت آنلاین ممکن است";
      setStatus(
        data.tts && data.tts.ready === false ? "error" : "ok",
        `${tts} / ${stt}`
      );
      statusPill.title = mode;

      if (edgeVoiceField) {
        edgeVoiceField.style.display =
          data.settings.tts_provider === "edge" ? "" : "none";
      }
    } catch {
      setStatus("error", "سرور در دسترس نیست");
    }
  }

  async function textToSpeech(text) {
    const payload = { text };
    if (activeSettings && activeSettings.tts_provider === "edge") {
      payload.voice = voiceSelect.value || "female";
    }
    const res = await fetch("/api/tts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      let detail = "خطا در تبدیل متن به صوت";
      try {
        const err = await res.json();
        detail = err.detail || detail;
      } catch (_) {}
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }

    const blob = await res.blob();
    return {
      url: URL.createObjectURL(blob),
      provider: res.headers.get("X-TTS-Provider") || "",
    };
  }

  async function blobToWav(blob) {
    const arrayBuffer = await blob.arrayBuffer();
    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    let decoded;
    try {
      decoded = await audioCtx.decodeAudioData(arrayBuffer.slice(0));
    } finally {
      await audioCtx.close().catch(() => {});
    }

    const channels = decoded.numberOfChannels;
    const inputLength = decoded.length;
    const mono = new Float32Array(inputLength);
    for (let i = 0; i < inputLength; i++) {
      let sum = 0;
      for (let c = 0; c < channels; c++) sum += decoded.getChannelData(c)[i];
      mono[i] = sum / channels;
    }

    const targetRate = 16000;
    const pcm =
      decoded.sampleRate === targetRate
        ? mono
        : resampleLinear(mono, decoded.sampleRate, targetRate);

    return new Blob([encodeWav(pcm, targetRate)], { type: "audio/wav" });
  }

  function resampleLinear(input, fromRate, toRate) {
    if (fromRate === toRate) return input;
    const ratio = fromRate / toRate;
    const outLength = Math.max(1, Math.round(input.length / ratio));
    const output = new Float32Array(outLength);
    for (let i = 0; i < outLength; i++) {
      const srcIndex = i * ratio;
      const i0 = Math.floor(srcIndex);
      const i1 = Math.min(i0 + 1, input.length - 1);
      const t = srcIndex - i0;
      output[i] = input[i0] * (1 - t) + input[i1] * t;
    }
    return output;
  }

  function encodeWav(samples, sampleRate) {
    const buffer = new ArrayBuffer(44 + samples.length * 2);
    const view = new DataView(buffer);

    function writeString(offset, str) {
      for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i));
    }

    writeString(0, "RIFF");
    view.setUint32(4, 36 + samples.length * 2, true);
    writeString(8, "WAVE");
    writeString(12, "fmt ");
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, 1, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    writeString(36, "data");
    view.setUint32(40, samples.length * 2, true);

    let offset = 44;
    for (let i = 0; i < samples.length; i++, offset += 2) {
      const s = Math.max(-1, Math.min(1, samples[i]));
      view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    }
    return buffer;
  }

  async function speechToText(blob) {
    const wavBlob = await blobToWav(blob);
    const form = new FormData();
    form.append("audio", wavBlob, "speech.wav");
    form.append("language", (activeSettings && activeSettings.stt_language) || "fa-IR");

    const res = await fetch("/api/stt", { method: "POST", body: form });
    if (!res.ok) {
      let detail = "خطا در تبدیل صوت به متن";
      try {
        const err = await res.json();
        detail = err.detail || detail;
      } catch (_) {}
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
    return res.json();
  }

  async function handleTextSubmit(event) {
    event.preventDefault();
    if (busy) return;

    const text = (inputEl.value || "").trim();
    if (!text) {
      inputEl.focus();
      return;
    }

    addBubble({ role: "user", title: "شما · متن", text });
    inputEl.value = "";
    setBusy(true);

    try {
      const { url, provider } = await textToSpeech(text);
      addBubble({
        role: "bot",
        title: `سیستم · صوت${provider ? " · " + provider : ""}`,
        text: "صوت آماده است.",
        audioUrl: url,
      });
    } catch (err) {
      addBubble({ role: "bot", title: "خطا", text: err.message || String(err), error: true });
    } finally {
      setBusy(false);
      inputEl.focus();
    }
  }

  async function processAudioBlob(blob, label) {
    setBusy(true);
    addBubble({
      role: "user",
      title: label,
      text: "در حال تشخیص گفتار...",
      audioUrl: URL.createObjectURL(blob),
    });

    try {
      const result = await speechToText(blob);
      addBubble({
        role: "bot",
        title: `سیستم · متن${result.provider ? " · " + result.provider : ""}`,
        text: result.text,
      });
      inputEl.value = result.text;
    } catch (err) {
      addBubble({ role: "bot", title: "خطا", text: err.message || String(err), error: true });
    } finally {
      setBusy(false);
    }
  }

  function startTimer() {
    recordingStartedAt = Date.now();
    recTimer.textContent = formatTime(0);
    timerInterval = setInterval(() => {
      recTimer.textContent = formatTime(Date.now() - recordingStartedAt);
    }, 250);
  }

  function stopTimer() {
    if (timerInterval) {
      clearInterval(timerInterval);
      timerInterval = null;
    }
  }

  function useBrowserStt() {
    return activeSettings && activeSettings.stt_provider === "browser";
  }

  function startBrowserRecognition() {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      addBubble({
        role: "bot",
        title: "خطا",
        text: "Web Speech API در این مرورگر پشتیبانی نمی‌شود. STT را روی Vosk بگذارید.",
        error: true,
      });
      return;
    }

    browserRecognition = new SR();
    browserRecognition.lang = (activeSettings && activeSettings.stt_language) || "fa-IR";
    browserRecognition.interimResults = false;
    browserRecognition.maxAlternatives = 1;
    browserRecognition.continuous = false;

    browserRecognition.onresult = (event) => {
      const text = event.results[0][0].transcript;
      addBubble({ role: "user", title: "شما · ویس مرورگر", text: "(ضبط شد)" });
      addBubble({ role: "bot", title: "سیستم · متن · browser", text });
      inputEl.value = text;
    };
    browserRecognition.onerror = (event) => {
      addBubble({
        role: "bot",
        title: "خطا",
        text: "خطای تشخیص مرورگر: " + (event.error || "نامشخص"),
        error: true,
      });
    };
    browserRecognition.onend = () => {
      browserRecognition = null;
      stopTimer();
      recordingBar.classList.add("hidden");
      micBtn.classList.remove("recording");
      stopBtn.classList.add("hidden");
      setBusy(false);
    };

    setBusy(true);
    micBtn.classList.add("recording");
    stopBtn.classList.remove("hidden");
    recordingBar.classList.remove("hidden");
    startTimer();
    browserRecognition.start();
  }

  async function startRecording() {
    if (busy || mediaRecorder || browserRecognition) return;

    if (useBrowserStt()) {
      startBrowserRecognition();
      return;
    }

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      addBubble({
        role: "bot",
        title: "خطا",
        text: "مرورگر شما از میکروفون پشتیبانی نمی‌کند.",
        error: true,
      });
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          channelCount: 1,
        },
      });

      recordedChunks = [];
      const mime = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : MediaRecorder.isTypeSupported("audio/webm")
          ? "audio/webm"
          : "";

      mediaRecorder = mime
        ? new MediaRecorder(stream, { mimeType: mime })
        : new MediaRecorder(stream);

      mediaRecorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) recordedChunks.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        stopTimer();
        recordingBar.classList.add("hidden");
        micBtn.classList.remove("recording");
        stopBtn.classList.add("hidden");

        const type = mediaRecorder.mimeType || "audio/webm";
        mediaRecorder = null;

        const blob = new Blob(recordedChunks, { type });
        recordedChunks = [];

        if (!blob.size) {
          addBubble({
            role: "bot",
            title: "خطا",
            text: "صوتی ضبط نشد. دوباره تلاش کنید.",
            error: true,
          });
          return;
        }

        await processAudioBlob(blob, "شما · ویس");
      };

      mediaRecorder.start(200);
      micBtn.classList.add("recording");
      stopBtn.classList.remove("hidden");
      recordingBar.classList.remove("hidden");
      startTimer();
    } catch (err) {
      addBubble({
        role: "bot",
        title: "خطا",
        text: "دسترسی به میکروفون ممکن نشد: " + (err.message || String(err)),
        error: true,
      });
    }
  }

  function stopRecording() {
    if (browserRecognition) {
      try {
        browserRecognition.stop();
      } catch (_) {}
      return;
    }
    if (mediaRecorder && mediaRecorder.state !== "inactive") {
      mediaRecorder.stop();
    }
  }

  formEl.addEventListener("submit", handleTextSubmit);

  inputEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      formEl.requestSubmit();
    }
  });

  micBtn.addEventListener("click", () => {
    if (mediaRecorder || browserRecognition) stopRecording();
    else startRecording();
  });

  stopBtn.addEventListener("click", stopRecording);

  fileInput.addEventListener("change", async () => {
    const file = fileInput.files && fileInput.files[0];
    fileInput.value = "";
    if (!file) return;
    if (useBrowserStt()) {
      addBubble({
        role: "bot",
        title: "توجه",
        text: "برای آپلود فایل، STT را روی Vosk یا Google بگذارید.",
        error: true,
      });
      return;
    }
    await processAudioBlob(file, "شما · فایل صوتی");
  });

  showWelcome();
  checkHealth();
})();
