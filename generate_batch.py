"""
CLI Script to generate batches of dialogue and audio for The Infinite Conversation.
Usage:
    python generate_batch.py --turns 6 --speaker werner
"""

import argparse
from backend.pipeline import ConversationPipeline

def main():
    parser = argparse.ArgumentParser(description="Generate conversation turns between Herzog and Žižek.")
    parser.add_argument("--turns", type=int, default=6, help="Number of turns to generate (default: 6)")
    parser.add_argument("--speaker", type=str, default="werner", choices=["werner", "slavoj"], help="Starting speaker")
    parser.add_argument("--batch-id", type=str, default=None, help="Custom batch ID (e.g. conversation_seed)")
    parser.add_argument("--prompt", type=str, default=None, help="Initial opening thought/prompt")
    parser.add_argument("--provider", type=str, default="auto", choices=["auto", "gemini", "openai", "fallback"], help="LLM provider")
    args = parser.parse_args()

    pipeline = ConversationPipeline(provider=args.provider)
    result = pipeline.generate_batch(
        batch_id=args.batch_id,
        num_turns=args.turns,
        starting_speaker=args.speaker,
        initial_prompt=args.prompt
    )
    print(f"\n[Success] Generated {result['turns_generated']} turns in '{result['batch_id']}'")
    print(f"Manifest written to: {result['manifest_path']}")

if __name__ == "__main__":
    main()
