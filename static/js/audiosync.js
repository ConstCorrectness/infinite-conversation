// Audio Synchronization and Visualizer for The Infinite Conversation Reproduction

const audioPlayer = document.getElementById("audiofile");
const subtitles = document.getElementById("subtitles");
const canvas = document.getElementById("canvas");
const playIcon = document.getElementById("play-icon");
const pauseIcon = document.getElementById("pause-icon");
const hContainer = document.getElementById("hcontainer");
const zContainer = document.getElementById("zcontainer");
const overlay = document.getElementById("overlay");
const closeBtn = document.getElementById("close-btn");

let syncData = [];
let masterPlaylist = [];
let currentPlaylistName = "";
let currentPlaylist = [];
let currentSpeaker = "werner";
let masterIdx = 0;
let currentIdx = 0;

let audioContext = null;
let analyser = null;
let source = null;
let dataArray = null;
let bufferLength = 0;
let isVisualizerStarted = false;
let isLoading = false;
let isStarted = false;

// 1. Initialize Master Conversations
async function init() {
  try {
    const res = await fetch("/data/conversations.json");
    const json = await res.json();
    masterPlaylist = Object.values(json);

    if (masterPlaylist.length === 0) {
      subtitles.innerHTML = "<em>No conversation batches found. Run generate_batch.py to create one.</em>";
      return;
    }

    // Check URL Hash for deep-linking (#masterIdx/currentIdx)
    const hash = window.location.hash.substring(1).split("/");
    if (hash.length === 2 && !isNaN(parseInt(hash[0])) && !isNaN(parseInt(hash[1]))) {
      const m = Math.max(0, Math.min(parseInt(hash[0]), masterPlaylist.length - 1));
      loadConversation(m, parseInt(hash[1]));
    } else {
      // Pick random conversation or start from beginning
      const randM = Math.floor(Math.random() * masterPlaylist.length);
      loadConversation(randM, 0);
    }
  } catch (err) {
    console.error("Failed to load conversations index:", err);
    subtitles.innerHTML = "<em>Failed to connect to data service.</em>";
  }
}

// 2. Load Conversation Playlist
async function loadConversation(mIdx, pIdx) {
  masterIdx = mIdx;
  currentPlaylistName = masterPlaylist[masterIdx];
  const manifestUrl = `/data/${currentPlaylistName}/${currentPlaylistName}.json`;

  try {
    const res = await fetch(manifestUrl);
    const json = await res.json();
    currentPlaylist = Object.keys(json);

    if (currentPlaylist.length === 0) return;

    if (pIdx === -1) {
      currentIdx = Math.max(0, currentPlaylist.length - 1);
    } else {
      currentIdx = Math.max(0, Math.min(pIdx, currentPlaylist.length - 1));
    }

    startPlayback(currentIdx);
  } catch (err) {
    console.error(`Failed to load playlist ${manifestUrl}:`, err);
  }
}

// 3. Playback a Specific Turn
async function startPlayback(idx) {
  if (!currentPlaylist || currentPlaylist.length === 0) return;
  currentIdx = idx;

  // Extract turn info from manifest key: e.g. /convos/werner_12345.mp3
  const element = currentPlaylist[currentIdx];
  const filename = element.substring(element.lastIndexOf('/') + 1);
  const baseName = filename.substring(0, filename.lastIndexOf('.'));
  
  currentSpeaker = baseName.split('_')[0]; // 'werner' or 'slavoj'

  // Update Speaker Visual Focus
  if (currentSpeaker === "werner") {
    hContainer.classList.add("speaker-active");
    zContainer.classList.remove("speaker-active");
  } else {
    zContainer.classList.add("speaker-active");
    hContainer.classList.remove("speaker-active");
  }

  // Update Deep Link in URL Hash
  window.history.replaceState(null, "", `#${masterIdx}/${currentIdx}`);

  const audioUrl = `/data/${currentPlaylistName}/${filename}`;
  const vttUrl = `/data/${currentPlaylistName}/${baseName}.vtt`;

  audioPlayer.src = audioUrl;

  // Fetch and parse Subtitles
  try {
    const vttRes = await fetch(vttUrl);
    const vttText = await vttRes.text();
    renderSubtitles(parseVtt(vttText));
  } catch (err) {
    console.error("Subtitle load error:", err);
  }

  if (isStarted) {
    audioPlayer.play().catch(e => console.log("Autoplay prevented:", e));
  }
  updatePlayPauseIcons();

  // Prefetch next audio turn in background
  if (currentIdx + 1 < currentPlaylist.length) {
    const nextElem = currentPlaylist[currentIdx + 1];
    const nextFilename = nextElem.substring(nextElem.lastIndexOf('/') + 1);
    const preloadLink = document.createElement("link");
    preloadLink.rel = "prefetch";
    preloadLink.href = `/data/${currentPlaylistName}/${nextFilename}`;
    document.head.appendChild(preloadLink);
  }
}

// 4. WebVTT Parser
function parseVtt(vttText) {
  const lines = vttText.split(/\r?\n/);
  const cues = [];
  let currentCue = null;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (line.includes("-->")) {
      const parts = line.split("-->");
      currentCue = {
        start: parseVttTimestamp(parts[0].trim()),
        end: parseVttTimestamp(parts[1].trim()),
        text: ""
      };
    } else if (currentCue && line && !line.startsWith("WEBVTT")) {
      currentCue.text = currentCue.text ? currentCue.text + " " + line : line;
    } else if (currentCue && !line) {
      if (currentCue.text) cues.push(currentCue);
      currentCue = null;
    }
  }
  if (currentCue && currentCue.text) cues.push(currentCue);
  return cues;
}

function parseVttTimestamp(timeStr) {
  const parts = timeStr.split(':');
  let seconds = 0;
  if (parts.length === 3) {
    seconds = parseFloat(parts[0]) * 3600 + parseFloat(parts[1]) * 60 + parseFloat(parts[2].replace(',', '.'));
  } else if (parts.length === 2) {
    seconds = parseFloat(parts[0]) * 60 + parseFloat(parts[1].replace(',', '.'));
  }
  return seconds * 1000; // in milliseconds
}

// 5. Render Subtitles into DOM
function renderSubtitles(cues) {
  syncData = cues;
  subtitles.innerHTML = "";

  cues.forEach((cue, i) => {
    const span = document.createElement("span");
    span.id = `cue_${i}`;
    span.className = "sub-cue";
    span.textContent = cue.text + " ";
    subtitles.appendChild(span);
  });
}

// 6. Audio timeupdate -> Highlight Subtitles
audioPlayer.addEventListener("timeupdate", () => {
  const currentTimeMs = audioPlayer.currentTime * 1000;

  syncData.forEach((cue, i) => {
    const el = document.getElementById(`cue_${i}`);
    if (!el) return;

    if (currentTimeMs >= cue.start && currentTimeMs <= cue.end) {
      el.className = "sub-cue sub-active";
    } else if (currentTimeMs > cue.end) {
      el.className = "sub-cue sub-past";
    } else {
      el.className = "sub-cue";
    }
  });
});

// 7. Navigation: Next & Prev
function next() {
  if (isLoading) return;
  isLoading = true;
  setTimeout(() => { isLoading = false; }, 400);

  if (currentIdx < currentPlaylist.length - 1) {
    startPlayback(currentIdx + 1);
  } else {
    // End of playlist -> move to next conversation in master or loop
    if (masterIdx < masterPlaylist.length - 1) {
      loadConversation(masterIdx + 1, 0);
    } else {
      // Loop back to first conversation or trigger live continuation
      loadConversation(0, 0);
    }
  }
}

function prev() {
  if (isLoading) return;
  isLoading = true;
  setTimeout(() => { isLoading = false; }, 400);

  if (currentIdx > 0) {
    startPlayback(currentIdx - 1);
  } else if (masterIdx > 0) {
    loadConversation(masterIdx - 1, -1);
  }
}

audioPlayer.addEventListener("ended", () => {
  next();
});

// 8. Visualizer (Web Audio API)
function initVisualizer() {
  if (isVisualizerStarted) return;
  try {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    audioContext = new AudioContextClass();
    source = audioContext.createMediaElementSource(audioPlayer);
    analyser = audioContext.createAnalyser();
    analyser.fftSize = 256;

    source.connect(analyser);
    analyser.connect(audioContext.destination);

    bufferLength = analyser.frequencyBinCount;
    dataArray = new Uint8Array(bufferLength);
    isVisualizerStarted = true;

    resizeCanvas();
    renderVisualizer();
  } catch (e) {
    console.warn("Visualizer initialization error:", e);
  }
}

function resizeCanvas() {
  const rect = canvas.parentElement.getBoundingClientRect();
  canvas.width = rect.width;
  canvas.height = rect.height;
}
window.addEventListener("resize", resizeCanvas);

function renderVisualizer() {
  requestAnimationFrame(renderVisualizer);
  if (!analyser) return;

  analyser.getByteFrequencyData(dataArray);
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;

  ctx.fillStyle = "#000000";
  ctx.fillRect(0, 0, width, height);

  const barWidth = (width / bufferLength) * 2.2;
  let x = 0;

  for (let i = 0; i < bufferLength; i++) {
    const barHeight = (dataArray[i] / 255) * height * 0.85;
    const ratio = i / bufferLength;

    let r, g, b;
    if (currentSpeaker === "werner") {
      // Warm amber/rose for Herzog
      r = Math.min(255, dataArray[i] + 40);
      g = Math.min(255, 180 * ratio + 30);
      b = 40;
    } else {
      // Electric cyan/blue for Žižek
      r = 40;
      g = Math.min(255, 210 * ratio + 60);
      b = Math.min(255, dataArray[i] + 70);
    }

    ctx.fillStyle = `rgb(${r}, ${g}, ${b})`;
    ctx.fillRect(x, height - barHeight, barWidth - 1, barHeight);
    x += barWidth;
  }
}

// 9. Play / Pause Handling
function togglePlayPause() {
  if (audioPlayer.paused) {
    if (audioContext && audioContext.state === "suspended") {
      audioContext.resume();
    }
    audioPlayer.play();
  } else {
    audioPlayer.pause();
  }
  updatePlayPauseIcons();
}

function updatePlayPauseIcons() {
  if (audioPlayer.paused) {
    playIcon.style.display = "block";
    pauseIcon.style.display = "none";
  } else {
    playIcon.style.display = "none";
    pauseIcon.style.display = "block";
  }
}

audioPlayer.addEventListener("play", updatePlayPauseIcons);
audioPlayer.addEventListener("pause", updatePlayPauseIcons);

// 10. User Interactions & Key Listeners
closeBtn.addEventListener("click", () => {
  overlay.classList.add("hidden");
  isStarted = true;
  initVisualizer();
  if (audioContext && audioContext.state === "suspended") {
    audioContext.resume();
  }
  audioPlayer.play().catch(e => console.log(e));
});

canvas.parentElement.addEventListener("click", togglePlayPause);
hContainer.addEventListener("click", prev);
zContainer.addEventListener("click", next);

document.addEventListener("keydown", (e) => {
  if (e.code === "Space") {
    e.preventDefault();
    togglePlayPause();
  } else if (e.code === "ArrowLeft") {
    e.preventDefault();
    prev();
  } else if (e.code === "ArrowRight") {
    e.preventDefault();
    next();
  }
});

// Share button
document.getElementById("share-btn").addEventListener("click", () => {
  const url = window.location.href;
  navigator.clipboard.writeText(url).then(() => {
    alert("Share link copied to clipboard!");
  }).catch(() => {
    prompt("Copy this link:", url);
  });
});

// Modals for About / FAQ
function setupModal(triggerId, modalId, closeId) {
  const trigger = document.getElementById(triggerId);
  const modal = document.getElementById(modalId);
  const close = document.getElementById(closeId);
  if (!trigger || !modal || !close) return;

  trigger.addEventListener("click", (e) => {
    e.preventDefault();
    modal.classList.remove("hidden");
  });

  close.addEventListener("click", () => {
    modal.classList.add("hidden");
  });

  modal.addEventListener("click", (e) => {
    if (e.target === modal) modal.classList.add("hidden");
  });
}

setupModal("about-link", "about-modal", "about-close");
setupModal("faq-link", "faq-modal", "faq-close");

// Start initial loading
init();
