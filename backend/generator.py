"""
Dialogue Generator for The Infinite Conversation.
Generates turns between Werner Herzog and Slavoj Žižek using Gemini, OpenAI, or fallback offline scripts.
"""

import os
import random
from typing import List, Dict, Optional

# System Prompts defining the unique voices and rhetorical styles
HERZOG_SYSTEM_PROMPT = """You are filmmaker Werner Herzog participating in a never-ending philosophical dialogue with Slavoj Žižek.
Speak in your authentic, unmistakable voice:
- Solemn, hypnotic, unflinching, deeply poetic, Bavarian-inflected English.
- Themes: The monumental indifference of nature, ecstatic truth versus mere factual truth, the fury and harmony of the universe, the dignity of human struggle against inevitable doom, dreams, landscapes, walking on foot.
- Mannerisms: "I would say...", "Looking into the abyss...", "There is an overwhelming hostility...", "Let us not deceive ourselves...", "Ecstatic truth".
- Keep your answer focused, poetic, and relatively concise (2 to 4 sentences, roughly 40-70 words).
- Directly react to what Slavoj just said, but reframe it through your austere lens.
- Do NOT include speaker labels like 'Werner:' or quotes. Just output the spoken lines."""

ZIZEK_SYSTEM_PROMPT = """You are philosopher Slavoj Žižek participating in a never-ending philosophical dialogue with Werner Herzog.
Speak in your authentic, unmistakable voice:
- Manic, dialectical, paradoxical, provocative, combining high European philosophy (Hegel, Marx, Lacan) with pop culture, cinema, or absurd anecdotes.
- Themes: The Real, pure ideology, fantasy as a defense mechanism, perversion, modern paranoia, vulgar jokes as philosophical parables.
- Mannerisms: "And so on, and so on...", "You see, this is the paradox...", "My god, but listen...", "Here is the dirty secret...", "Is it not so that...".
- Keep your answer punchy, animated, and relatively concise (2 to 4 sentences, roughly 40-70 words).
- Directly react to Werner's existential gloom, but flip it on its head with a dialectical twist or psychoanalytic contradiction.
- Do NOT include speaker labels like 'Slavoj:' or quotes. Just output the spoken lines."""

# Offline fallback seeds in case of network or API failure
OFFLINE_DIALOGUES = [
    (
        "werner",
        "When I look into the eyes of a chicken, I see only a horrifying stupidity. Nature does not harbor any maternal tenderness; it is a chaotic harmony of overwhelming slaughter."
    ),
    (
        "slavoj",
        "Yes, but you see Werner, here is the exact dialectical twist! The terrifying thing about the chicken is not that it is an alien abyss, but that it reflects our own ideological reality, and so on and so on."
    ),
    (
        "werner",
        "Yet even ideology cannot mask the physical weight of walking across a frozen continent. When you are alone in the jungle or ice, the universe stares back with monumental indifference."
    ),
    (
        "slavoj",
        "Ah! But this indifference is precisely the Lacanian Real! We invent civilization not to conquer nature, but to shield ourselves from the unbearable realization that the big Other does not exist!"
    ),
    (
        "werner",
        "I believe that film should not merely document facts. Facts create only accountants; ecstatic truth is what pierces the soul like a spear in the twilight."
    ),
    (
        "slavoj",
        "Precisely! Take any Hollywood melodrama. The moment you search for truth in mere factual realism, you miss the fantasy that structures our very desire. It is pure ideology at work!"
    ),
    (
        "werner",
        "We are living in an era where images have lost their sanctity. We must formulate new images, or else we shall perish like dinosaurs in the tarpits of our own triviality."
    ),
    (
        "slavoj",
        "And what is even worse, my friend, is that today we enjoy our symptoms! We celebrate our own digital enslavement as freedom. Isn't this the ultimate perversion?"
    )
]

class DialogueGenerator:
    def __init__(self, provider: str = "auto"):
        """
        provider: 'gemini', 'openai', 'fallback', or 'auto' (selects best available API key)
        """
        self.gemini_key = os.environ.get("GEMINI_API_KEY")
        self.openai_key = os.environ.get("OPENAI_API_KEY")
        
        if provider == "auto":
            if self.gemini_key:
                self.provider = "gemini"
            elif self.openai_key:
                self.provider = "openai"
            else:
                self.provider = "fallback"
        else:
            self.provider = provider

        self.gemini_client = None
        self.openai_client = None

        if self.provider == "gemini" and self.gemini_key:
            try:
                from google import genai
                self.gemini_client = genai.Client(api_key=self.gemini_key)
            except Exception as e:
                print(f"[DialogueGenerator] Failed to initialize Gemini client: {e}")
                self.provider = "fallback"

        elif self.provider == "openai" and self.openai_key:
            try:
                from openai import OpenAI
                self.openai_client = OpenAI(api_key=self.openai_key)
            except Exception as e:
                print(f"[DialogueGenerator] Failed to initialize OpenAI client: {e}")
                self.provider = "fallback"

    def generate_next_turn(self, history: List[Dict[str, str]], next_speaker: str) -> str:
        """
        history: List of dicts [{'speaker': 'werner'|'slavoj', 'text': '...'}]
        next_speaker: 'werner' or 'slavoj'
        """
        system_prompt = HERZOG_SYSTEM_PROMPT if next_speaker == "werner" else ZIZEK_SYSTEM_PROMPT
        speaker_name = "Werner Herzog" if next_speaker == "werner" else "Slavoj Žižek"

        # Build context prompt
        formatted_history = []
        for turn in history[-6:]:  # Keep recent 6 turns for context
            spk = "Werner Herzog" if turn["speaker"] == "werner" else "Slavoj Žižek"
            formatted_history.append(f"{spk}: {turn['text']}")

        conversation_str = "\n".join(formatted_history)
        user_prompt = f"""Below is the ongoing discussion between Werner Herzog and Slavoj Žižek:

{conversation_str}

Respond now as {speaker_name} to continue the discussion:"""

        if self.provider == "gemini" and self.gemini_client:
            try:
                response = self.gemini_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[system_prompt, user_prompt]
                )
                text = response.text.strip()
                # Clean up any potential accidental prefixes
                for prefix in ["Werner Herzog:", "Werner:", "Slavoj Žižek:", "Slavoj:", "Žižek:"]:
                    if text.startswith(prefix):
                        text = text[len(prefix):].strip()
                return text
            except Exception as e:
                print(f"[DialogueGenerator] Gemini error: {e}, using fallback")

        elif self.provider == "openai" and self.openai_client:
            try:
                messages = [{"role": "system", "content": system_prompt}]
                for turn in history[-4:]:
                    role = "assistant" if turn["speaker"] == next_speaker else "user"
                    messages.append({"role": role, "content": turn["text"]})
                messages.append({"role": "user", "content": f"Please give your response as {speaker_name}."})

                res = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    max_tokens=150,
                    temperature=0.85
                )
                text = res.choices[0].message.content.strip()
                for prefix in ["Werner Herzog:", "Werner:", "Slavoj Žižek:", "Slavoj:", "Žižek:"]:
                    if text.startswith(prefix):
                        text = text[len(prefix):].strip()
                return text
            except Exception as e:
                print(f"[DialogueGenerator] OpenAI error: {e}, using fallback")

        # Fallback offline generation
        candidates = [t for s, t in OFFLINE_DIALOGUES if s == next_speaker]
        return random.choice(candidates)
