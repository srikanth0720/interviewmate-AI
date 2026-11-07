const $ = (id) => document.getElementById(id);
let sessionId = null,
  questions = [],
  questionIndex = 0,
  stream = null,
  audioContext = null,
  processor = null,
  source = null;
let pcmChunks = [],
  recording = false,
  startedAt = 0,
  timerHandle = null,
  lastEvaluation = null,
  currentQuestion = "";

async function api(url, options = {}) {
  const response = await fetch(url, options);
  const data = await response
    .json()
    .catch(() => ({ detail: "Unexpected server response" }));
  if (!response.ok)
    throw new Error(data.detail || `Request failed: ${response.status}`);
  return data;
}
function showError(message) {
  $("sessionNotice").textContent = message;
  $("sessionNotice").classList.add("error");
}
function setNotice(message) {
  $("sessionNotice").textContent = message;
  $("sessionNotice").classList.remove("error");
}
async function checkHealth() {
  try {
    const h = await api("/api/health");
    $("apiStatus").textContent = h.gnani_key_configured
      ? "Gnani AI"
      : "Add Gnani API key";
    if (!h.gnani_key_configured) $("apiStatus").style.color = "#ffb3a8";
  } catch {
    $("apiStatus").textContent = "Backend unavailable";
  }
}
async function startInterview() {
  try {
    const category = $("category").value,
      language = $("language").value;
    const data = await api("/api/interview/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ category, language }),
    });
    const q = await api(
      `/api/questions?category=${encodeURIComponent(category)}`,
    );
    sessionId = data.session_id;
    questions = q.questions;
    questionIndex = 0;
    $("categoryTag").textContent = category.toUpperCase();
    renderQuestion();
    $("recordBtn").disabled = false;
    $("nextBtn").disabled = true;
    $("submitBtn").disabled = true;
    $("results").classList.add("hidden");
    $("transcriptBox").classList.add("hidden");
    setNotice(`Session #${sessionId} started. Record your answer to begin.`);
  } catch (e) {
    showError(e.message);
  }
}
function renderQuestion() {
  currentQuestion = questions[questionIndex];
  $("questionText").textContent = currentQuestion;
  $("questionCount").textContent =
    `Question ${questionIndex + 1} of ${questions.length}`;
  $("transcriptBox").classList.add("hidden");
}
function floatTo16BitPCM(float32) {
  const buffer = new ArrayBuffer(44 + float32.length * 2),
    view = new DataView(buffer);
  const write = (offset, str) => {
    for (let i = 0; i < str.length; i++)
      view.setUint8(offset + i, str.charCodeAt(i));
  };
  write(0, "RIFF");
  view.setUint32(4, 36 + float32.length * 2, true);
  write(8, "WAVE");
  write(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, 16000, true);
  view.setUint32(28, 32000, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  write(36, "data");
  view.setUint32(40, float32.length * 2, true);
  let offset = 44;
  for (let i = 0; i < float32.length; i++) {
    let s = Math.max(-1, Math.min(1, float32[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    offset += 2;
  }
  return new Blob([view], { type: "audio/wav" });
}
function downsample(buffer, inputRate, outputRate) {
  if (outputRate === inputRate) return buffer;
  const ratio = inputRate / outputRate,
    length = Math.round(buffer.length / ratio),
    result = new Float32Array(length);
  let offsetResult = 0,
    offsetBuffer = 0;
  while (offsetResult < result.length) {
    const nextOffsetBuffer = Math.round((offsetResult + 1) * ratio);
    let accum = 0,
      count = 0;
    for (let i = offsetBuffer; i < nextOffsetBuffer && i < buffer.length; i++) {
      accum += buffer[i];
      count++;
    }
    result[offsetResult] = count ? accum / count : 0;
    offsetResult++;
    offsetBuffer = nextOffsetBuffer;
  }
  return result;
}
async function startRecording() {
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
      },
    });
    audioContext = new (window.AudioContext || window.webkitAudioContext)();
    source = audioContext.createMediaStreamSource(stream);
    processor = audioContext.createScriptProcessor(4096, 1, 1);
    pcmChunks = [];
    recording = true;
    startedAt = Date.now();
    processor.onaudioprocess = (event) => {
      if (recording) {
        const data = event.inputBuffer.getChannelData(0);
        pcmChunks.push(new Float32Array(data));
      }
    };
    source.connect(processor);
    processor.connect(audioContext.destination);
    $("recordBtn").classList.add("recording");
    $("recordLabel").textContent = "Recording… tap to stop";
    $("wave").classList.add("active");
    $("submitBtn").disabled = true;
    $("nextBtn").disabled = true;
    timerHandle = setInterval(() => {
      const sec = Math.min(30, Math.floor((Date.now() - startedAt) / 1000));
      $("recTime").textContent = `00:${String(sec).padStart(2, "0")}`;
      if (sec >= 30) stopRecording();
    }, 250);
  } catch (e) {
    showError(
      "Microphone access failed. Allow microphone permission and try again.",
    );
  }
}
async function stopRecording() {
  if (!recording) return;
  recording = false;
  clearInterval(timerHandle);
  try {
    processor.disconnect();
    source.disconnect();
  } catch {}
  stream?.getTracks().forEach((t) => t.stop());
  const allLength = pcmChunks.reduce((n, c) => n + c.length, 0),
    merged = new Float32Array(allLength);
  let pos = 0;
  for (const c of pcmChunks) {
    merged.set(c, pos);
    pos += c.length;
  }
  const mono = downsample(merged, audioContext.sampleRate, 16000);
  window.recordedWav = floatTo16BitPCM(mono);
  await audioContext.close();
  $("recordBtn").classList.remove("recording");
  $("recordLabel").textContent = "Recording ready";
  $("wave").classList.remove("active");
  $("submitBtn").disabled = !window.recordedWav;
  $("recTime").textContent =
    `00:${String(Math.floor((Date.now() - startedAt) / 1000)).padStart(2, "0")}`;
  setNotice("Recording ready. Select Transcribe & evaluate.");
}
async function submitAnswer() {
  if (!sessionId || !window.recordedWav) return;
  $("submitBtn").disabled = true;
  $("submitBtn").textContent = "Processing…";
  try {
    const form = new FormData();
    form.append("audio", window.recordedWav, "answer.wav");
    form.append("language_code", $("language").value);
    setNotice("Prisma is transcribing your answer…");
    const transcript = await api("/api/transcribe", {
      method: "POST",
      body: form,
    });
    $("transcriptText").textContent = transcript.transcript;
    $("transcriptBox").classList.remove("hidden");
    setNotice("Transcript ready. Evaluating your answer…");
    const evaluation = await api("/api/evaluate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: sessionId,
        question: currentQuestion,
        transcript: transcript.transcript,
      }),
    });
    lastEvaluation = evaluation;
    renderEvaluation(evaluation);
    $("nextBtn").disabled = false;
    setNotice(
      "Evaluation saved. Listen to the feedback or move to the next question.",
    );
    loadHistory();
  } catch (e) {
    showError(e.message);
  } finally {
    $("submitBtn").textContent = "Transcribe & evaluate";
    $("submitBtn").disabled = false;
  }
}
function listInto(id, items) {
  const el = $(id);
  el.innerHTML = "";
  (items || []).forEach((item) => {
    const li = document.createElement("li");
    li.textContent = item;
    el.appendChild(li);
  });
  if (!items || !items.length) {
    const li = document.createElement("li");
    li.textContent = "No items returned.";
    el.appendChild(li);
  }
}
function renderEvaluation(e) {
  $("results").classList.remove("hidden");
  $("totalScore").textContent = Math.round(e.total_score ?? 0);
  const labels = [
    ["technical_correctness", "Technical accuracy", 30],
    ["relevance", "Relevance", 20],
    ["completeness", "Completeness", 20],
    ["clarity", "Clarity", 15],
    ["communication", "Communication", 15],
  ];
  $("scoreGrid").innerHTML = "";
  labels.forEach(([key, label, max]) => {
    const div = document.createElement("div");
    div.className = "score-item";
    const score = e.scores?.[key] ?? 0;
    div.innerHTML = `<strong>${score}<small style="font-size:10px;color:#8295b2">/${max}</small></strong><span>${label}</span>`;
    $("scoreGrid").appendChild(div);
  });
  listInto("strengths", e.strengths);
  listInto("weaknesses", e.weaknesses);
  listInto("suggestions", e.practical_suggestions);
  $("improvedAnswer").textContent =
    e.improved_answer || "No suggested answer returned.";
  $("feedbackAudio").classList.add("hidden");
  $("speakStatus").textContent =
    e.evaluation_mode === "fallback_demo"
      ? "Development fallback scoring is active; configure an LLM endpoint for semantic evaluation."
      : "";
  $("results").scrollIntoView({ behavior: "smooth", block: "start" });
}
async function speakFeedback() {
  if (!lastEvaluation) return;
  const text = `Your score is ${Math.round(lastEvaluation.total_score)} out of 100. Strengths: ${(lastEvaluation.strengths || []).join(". ")}. Areas to improve: ${(lastEvaluation.weaknesses || []).join(". ")}. Suggested answer: ${lastEvaluation.improved_answer || ""}`;
  const form = new FormData();
  form.append("text", text);
  form.append("language", $("language").value);
  $("speakStatus").textContent = "Generating voice feedback…";
  try {
    const response = await fetch("/api/speak", { method: "POST", body: form });
    if (!response.ok) {
      const d = await response.json().catch(() => ({}));
      throw new Error(d.detail || "Timbre request failed");
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    $("feedbackAudio").src = url;
    $("feedbackAudio").classList.remove("hidden");
    await $("feedbackAudio").play();
    $("speakStatus").textContent = "Powered by Gnani Timbre";
  } catch (e) {
    $("speakStatus").textContent = e.message;
  }
}
function nextQuestion() {
  if (questionIndex + 1 >= questions.length) {
    setNotice(
      "You completed this question set. Start another session to practise again.",
    );
    $("nextBtn").disabled = true;
    return;
  }
  questionIndex++;
  window.recordedWav = null;
  $("recTime").textContent = "00:00";
  $("submitBtn").disabled = true;
  $("nextBtn").disabled = true;
  $("recordLabel").textContent = "Start recording";
  renderQuestion();
  setNotice("Ready for your next answer.");
}
async function clearHistory() {
  const confirmed = confirm(
    "Are you sure you want to delete all interview history?",
  );

  if (!confirmed) return;

  try {
    const result = await api("/api/history", {
      method: "DELETE",
    });

    alert(`${result.message}\nDeleted sessions: ${result.deleted_sessions}`);

    await loadHistory();
  } catch (error) {
    console.error("Clear history error:", error);
    alert("Failed to clear interview history.");
  }
}

$("startBtn").addEventListener("click", startInterview);
$("recordBtn").addEventListener("click", () =>
  recording ? stopRecording() : startRecording(),
);
$("submitBtn").addEventListener("click", submitAnswer);
$("nextBtn").addEventListener("click", nextQuestion);
$("speakBtn").addEventListener("click", speakFeedback);
$("clearHistory").addEventListener("click", clearHistory);
checkHealth();
loadHistory();
