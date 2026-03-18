---
name: humanizer
description: Make AI-generated text sound natural and match Jim's writing voice. Use this skill ONLY when the user explicitly asks to humanize text — never auto-invoke. If output seems robotic, suggest running it but wait for confirmation. Triggers on explicit requests like "humanize," "make this sound natural," "this sounds like AI," "rewrite in my voice," or "clean up the tone." Combines algorithmic text processing (TextHumanize library) with a personal voice profile derived from the user's actual emails, chats, and documents.
---

# Humanizer

Rewrite AI-generated text to sound natural, using both algorithmic processing and a personal voice profile.

## Invocation Rules

**This skill must NEVER run automatically.** Even if output clearly sounds like AI, do NOT invoke the humanizer on your own. Instead, ask the user:

> *"This could benefit from a humanizer pass — want me to run it?"*

Only proceed after explicit user confirmation. The user triggers this skill by saying things like "humanize this," "run the humanizer," "make this sound natural," or "clean up the tone." If the user hasn't asked, don't run it — just suggest it.

## Workflow

1. **Read the voice profile** at `references/voice-profile.md` for Jim's tone, word choices, anti-patterns, and before/after examples
2. **Determine scope** — is this a full document, a section, or a quick rewrite?
3. **Run TextHumanize** for mechanical cleanup (formulaic connectors, uniform sentence length, bureaucratic vocabulary)
4. **Apply voice profile** for Jim-specific tone adjustments that the algorithm can't catch
5. **Present the result** with a brief summary of what changed

## Step 1: Algorithmic Processing

Run `scripts/humanize_text.py` for mechanical text cleanup:

```bash
# Process a file
python scripts/humanize_text.py input.txt --intensity 70 --output output.txt --metrics

# Process inline text
python scripts/humanize_text.py --text "However, it is important to note that..." --intensity 70
```

**Intensity guide:**
- `50` — Light touch. Fixes obvious AI markers only (connectors, filler phrases).
- `70` — Default. Good balance of natural flow without changing meaning.
- `90` — Heavy rewrite. Use for text that reads very robotic.

TextHumanize handles: formulaic connectors, bureaucratic vocabulary, uniform sentence length, perfect punctuation patterns, repetitive word choice.

## Step 2: Voice Profile Application

After algorithmic processing, apply Jim's voice profile (read `references/voice-profile.md`). Key rules:

**Kill these on sight:**
- "It's important to note that..." — just state it
- "Furthermore," / "Additionally," / "Moreover," — use "Also," or start a new sentence
- "In conclusion," — end with the next step or action
- "I hope this helps!" — close with action or invitation
- "Certainly!" / "Absolutely!" / "Great question!" — just answer
- "Let me break this down" — just break it down
- "Delve into" — say "dig into" or "look at"

**Apply these:**
- Front-load clarity: context first, then explanation, then next step
- Vary sentence length: mix 5-word punches with longer explanations
- Use operational vocabulary: guidance, assets, scope, triage, deliverables
- Keep qualifiers intentional, not defensive
- Match formality to context: lowercase for chat, standard for email, formal for documents

**Preserve:**
- Jim's collaborative invitations: "let me know," "any thoughts"
- Honest uncertainty: "I don't have direct knowledge on this one"
- Dry humor when contextually appropriate

## Scope Modes

**Full document rewrite:**
Process the entire document through both steps. Preserve all factual content, headings, tables, and structure. Only rewrite prose.

**Section rewrite:**
Process only the flagged section. Match the tone of surrounding content.

**Quick polish:**
Skip TextHumanize. Apply only the voice profile anti-pattern fixes. Use for text that's close but has a few AI tells.

## What NOT to Change

- Quoted speech from other people (in meeting notes, transcripts)
- Technical terms, product names, proper nouns
- Data, numbers, dates, table contents
- Code blocks or configuration
- Section headers (unless they sound AI-generated like "Key Insights and Takeaways")

