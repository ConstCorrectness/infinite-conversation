"""
TTS and WebVTT Alignment Module for The Infinite Conversation.
Uses edge-tts to generate voice audio and synchronized WebVTT subtitles.
"""

import asyncio
import os
from typing import Dict, Any

# Voice settings tailored to capture speech characteristics:
# - Werner Herzog: Deep, measured, contemplative Bavarian cadence (-10% rate, -4Hz pitch)
# - Slavoj Žižek: Energetic, rapid-fire, idiosyncratic cadence (+10% rate)
VOICE_CONFIG = {
    "werner": {
        "voice": "de-DE-FlorianMultilingualNeural",
        "rate": "-10%",
        "pitch": "-4Hz",
    },
    "slavoj": {
        "voice": "en-GB-RyanNeural",
        "rate": "+12%",
        "pitch": "+2Hz",
    }
}

def format_vtt_time(ms: float) -> str:
    """Format milliseconds into WebVTT timestamp format: 00:00.000 or 00:00:00.000"""
    total_seconds = ms / 1000.0
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    millis = int((total_seconds - int(total_seconds)) * 1000)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{millis:03d}"
    return f"{minutes:02d}:{seconds:02d}.{millis:03d}"

async def synthesize_speech(text: str, speaker: str, audio_path: str, vtt_path: str) -> Dict[str, Any]:
    """
    Synthesizes speech for the given speaker and generates synchronized WebVTT subtitle file.
    speaker: 'werner' or 'slavoj'
    """
    import edge_tts
    
    config = VOICE_CONFIG.get(speaker, VOICE_CONFIG["werner"])
    communicate = edge_tts.Communicate(
        text=text,
        voice=config["voice"],
        rate=config["rate"],
        pitch=config["pitch"]
    )

    audio_bytes = bytearray()
    cues = []

    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_bytes.extend(chunk["data"])
        elif chunk["type"] in ("SentenceBoundary", "WordBoundary"):
            # offset and duration are in 100-nanosecond intervals (1 ms = 10,000 units)
            start_ms = chunk["offset"] / 10000.0
            end_ms = (chunk["offset"] + chunk["duration"]) / 10000.0
            cue_text = chunk["text"].strip()
            if cue_text:
                cues.append({
                    "start": start_ms,
                    "end": end_ms,
                    "text": cue_text
                })

    # Write MP3 audio file
    os.makedirs(os.path.dirname(os.path.abspath(audio_path)), exist_ok=True)
    with open(audio_path, "wb") as f:
        f.write(audio_bytes)

    # Generate WebVTT content
    vtt_lines = ["WEBVTT", ""]
    if cues:
        for cue in cues:
            start_str = format_vtt_time(cue["start"])
            end_str = format_vtt_time(cue["end"])
            vtt_lines.append(f"{start_str} --> {end_str}")
            vtt_lines.append(cue["text"])
            vtt_lines.append("")
    else:
        # Fallback if no boundaries received: assign full duration estimate (~1 sec per 3 words)
        words = len(text.split())
        est_duration_ms = max(2000, words * 350)
        vtt_lines.append(f"00:00.000 --> {format_vtt_time(est_duration_ms)}")
        vtt_lines.append(text)
        vtt_lines.append("")

    with open(vtt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(vtt_lines))

    return {
        "speaker": speaker,
        "text": text,
        "audio_path": audio_path,
        "vtt_path": vtt_path,
        "cues_count": len(cues)
    }

def synthesize_speech_sync(text: str, speaker: str, audio_path: str, vtt_path: str) -> Dict[str, Any]:
    return asyncio.run(synthesize_speech(text, speaker, audio_path, vtt_path))
