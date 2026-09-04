"""
Conversation Pipeline for The Infinite Conversation.
Coordinates generation of dialogue turns, audio files, WebVTT subtitles, and playlist manifests.
"""

import os
import json
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from backend.generator import DialogueGenerator
from backend.tts import synthesize_speech_sync

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
CONVERSATIONS_INDEX_FILE = os.path.join(DATA_DIR, "conversations.json")

def get_master_index() -> Dict[str, str]:
    """Load or initialize data/conversations.json"""
    if os.path.exists(CONVERSATIONS_INDEX_FILE):
        try:
            with open(CONVERSATIONS_INDEX_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_master_index(index_dict: Dict[str, str]):
    """Save data/conversations.json"""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CONVERSATIONS_INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index_dict, f, indent=2)

def register_conversation(conversation_id: str):
    """Register a conversation batch in the master index if not already present"""
    master = get_master_index()
    if conversation_id not in master.values():
        next_idx = str(len(master))
        master[next_idx] = conversation_id
        save_master_index(master)

class ConversationPipeline:
    def __init__(self, provider: str = "auto"):
        self.generator = DialogueGenerator(provider=provider)

    def generate_batch(
        self,
        batch_id: Optional[str] = None,
        num_turns: int = 6,
        starting_speaker: str = "werner",
        initial_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generates a batch of sequential dialogue turns, audio files, and WebVTT subtitles.
        """
        if not batch_id:
            now_str = datetime.now().strftime("%Y%m%d-%H%M")
            batch_id = f"conversation_{now_str}"

        batch_dir = os.path.join(DATA_DIR, batch_id)
        os.makedirs(batch_dir, exist_ok=True)
        manifest_path = os.path.join(batch_dir, f"{batch_id}.json")

        playlist_manifest = {}
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    playlist_manifest = json.load(f)
            except Exception:
                pass

        history = []
        current_speaker = starting_speaker

        # If batch already has turns, load history from existing manifest
        if playlist_manifest:
            for filepath, full_text in playlist_manifest.items():
                speaker = "werner" if "werner_" in filepath else "slavoj"
                clean_text = full_text.split(":", 1)[-1].strip()
                history.append({"speaker": speaker, "text": clean_text})
            if history:
                current_speaker = "slavoj" if history[-1]["speaker"] == "werner" else "werner"

        # If starting fresh and an initial prompt is provided
        if not history and initial_prompt:
            history.append({"speaker": "werner" if current_speaker == "slavoj" else "slavoj", "text": initial_prompt})

        print(f"Generating conversation batch '{batch_id}' ({num_turns} turns)...")

        for turn_i in range(num_turns):
            # 1. Generate text
            turn_text = self.generator.generate_next_turn(history, current_speaker)
            history.append({"speaker": current_speaker, "text": turn_text})

            # 2. File naming: <speaker>_<timestamp>.mp3 / .vtt
            ts = int(time.time() * 1000) + turn_i
            filename_base = f"{current_speaker}_{ts}"
            audio_filename = f"{filename_base}.mp3"
            vtt_filename = f"{filename_base}.vtt"
            
            audio_path = os.path.join(batch_dir, audio_filename)
            vtt_path = os.path.join(batch_dir, vtt_filename)

            # 3. Synthesize speech and subtitles
            print(f"[{turn_i+1}/{num_turns}] Synthesizing {current_speaker}: {turn_text[:50]}...")
            synthesize_speech_sync(turn_text, current_speaker, audio_path, vtt_path)

            # 4. Record in manifest: matches infiniteconversation schema
            speaker_display = "Werner Herzog" if current_speaker == "werner" else "Slavoj Žižek"
            manifest_key = f"/convos/{audio_filename}"
            playlist_manifest[manifest_key] = f"{speaker_display}: {turn_text}"

            # Save manifest after each turn
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(playlist_manifest, f, indent=2)

            # Alternate speaker
            current_speaker = "slavoj" if current_speaker == "werner" else "werner"

        # Register in master index
        register_conversation(batch_id)
        print(f"Batch '{batch_id}' completed successfully with {len(playlist_manifest)} turns.")
        return {
            "batch_id": batch_id,
            "turns_generated": num_turns,
            "manifest_path": manifest_path
        }
