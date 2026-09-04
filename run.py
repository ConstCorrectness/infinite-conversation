"""
Launcher for The Infinite Conversation Reproduction.
Starts the server on http://127.0.0.1:8000
"""

import os
import sys
import uvicorn
from backend.pipeline import get_master_index, ConversationPipeline

def main():
    print("=" * 60)
    print("   THE INFINITE CONVERSATION - REPRODUCTION")
    print("=" * 60)

    # Check if there is at least one conversation batch in data/
    master = get_master_index()
    if not master:
        print("\n[*] No existing conversation batches found. Generating seed conversation...")
        pipeline = ConversationPipeline()
        pipeline.generate_batch(batch_id="conversation_seed", num_turns=6, starting_speaker="werner")
        print("[*] Seed conversation generated successfully!\n")

    port = 8000
    host = "127.0.0.1"
    url = f"http://{host}:{port}"
    print(f"\n[+] Server is starting at: {url}")
    print(f"[+] Open {url} in your browser to listen to the dialogue.")
    print("    Press Ctrl+C to stop the server.\n")

    uvicorn.run("backend.server:app", host=host, port=port, log_level="info")

if __name__ == "__main__":
    main()
