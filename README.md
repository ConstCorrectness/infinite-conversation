# The Infinite Conversation — Reproduction

An AI art reproduction of [The Infinite Conversation](https://infiniteconversation.com) by Giacomo Miceli (2022).

This project produces an automated, continuous philosophical dialogue between simulations of German filmmaker **Werner Herzog** and Slovenian philosopher **Slavoj Žižek**.

---

## Architecture Overview

```
infinite-conversation/
├── data/                                # Conversation storage & manifest
│   ├── conversations.json               # Master playlist index
│   └── conversation_seed/               # Batch directory
│       ├── conversation_seed.json       # Turn-to-audio mapping
│       ├── werner_<timestamp>.mp3       # Spoken audio
│       ├── werner_<timestamp>.vtt       # Millisecond-aligned WebVTT subtitles
│       └── ...
├── static/                              # Web frontend
│   ├── index.html                       # Responsive UI with Herzog/Žižek portraits
│   ├── css/infiniteconversation.css     # Dark mode, visualizer styling, dynamic CSS filters
│   ├── js/audiosync.js                  # Web Audio API visualizer & subtitle sync
│   └── assets/                          # Stylized illustrations and control icons
├── backend/                             # Core Python pipeline
│   ├── generator.py                     # Dialogue generation (Gemini / OpenAI / Fallback)
│   ├── tts.py                           # Neural TTS + WebVTT timestamp generation (edge-tts)
│   ├── pipeline.py                      # Batch generation & turn coordination
│   └── server.py                        # FastAPI web server and generation endpoints
├── generate_batch.py                    # CLI script to generate new batches
├── run.py                               # 1-click startup launcher
└── requirements.txt                     # Virtual environment dependencies
```

---

## Quick Start

### 1. Run the Web Server
Launch the server (which automatically loads the pre-generated seed conversation):

```powershell
.\.venv\Scripts\python.exe run.py
```

Then open **`http://127.0.0.1:8000`** in your browser.

- Click **"Play audio"** on the initial welcome modal to begin listening.
- Press **Spacebar** or click the bottom canvas to toggle **Play / Pause**.
- Press **Left Arrow** or click **Werner Herzog** to go to the previous turn.
- Press **Right Arrow** or click **Slavoj Žižek** to advance to the next turn.
- Click **Share** to copy a deep link to the current turn (`#<batchIdx>/<turnIdx>`).

---

## Generating New Dialogue Batches

You can generate additional conversation batches using the CLI:

```powershell
# Generate 6 turns starting with Werner Herzog (uses Gemini by default)
.\.venv\Scripts\python.exe generate_batch.py --turns 6 --speaker werner

# Generate with a custom opening prompt:
.\.venv\Scripts\python.exe generate_batch.py --turns 4 --speaker slavoj --prompt "Why do we fetishize artificial intelligence?"

# Specify a custom batch name:
.\.venv\Scripts\python.exe generate_batch.py --batch-id conversation_tech --turns 8
```

The web player will automatically register new batches in `data/conversations.json` and queue them for playback.

---

## How It Works

### 1. Dialogue Generation (`backend/generator.py`)
- Employs carefully tuned system prompts capturing:
  - **Werner Herzog**: Contemplative, existential Bavarian cadence, ecstatic truth, monumental indifference of nature, and solitude.
  - **Slavoj Žižek**: Rapid-fire, dialectical reversals, Lacanian psychoanalysis (*the Real*, *pure ideology*), vulgar jokes, and pop-culture analogies.
- Supports **Google Gemini (`gemini-2.5-flash`)**, **OpenAI (`gpt-4o-mini`)**, or an offline philosophical fallback engine.

### 2. Speech Synthesis & Alignment (`backend/tts.py`)
- Uses `edge-tts` to generate neural audio with accented speaker configurations:
  - **Herzog**: `de-DE-FlorianMultilingualNeural` (slowed down and pitched down for solemn gravity).
  - **Žižek**: `en-GB-RyanNeural` (sped up for animated, passionate tempo).
- Extracts sentence and word boundaries during stream synthesis to generate standard `.vtt` WebVTT subtitle files.

### 3. Frontend & Visualizer (`static/js/audiosync.js`)
- **Web Audio API**: Uses `AudioContext` and `AnalyserNode` connected to an HTML5 `<canvas>` to render audio frequency bars in real-time.
- **Dynamic Color Shifts**: Shifts visualizer palette to warm amber/rose when Werner speaks, and electric cyan/blue when Slavoj speaks.
- **Dynamic Speaker Focus**: Active speaker is illuminated while inactive speaker is desaturated using CSS filters (`sepia`, `hue-rotate`, `saturate`).
- **Karaoke Subtitles**: Highlights spoken cues as playback progresses via HTML5 `<audio>` `timeupdate` events.
