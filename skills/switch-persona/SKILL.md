---
name: switch-persona
description: Switch Copilot's active persona mid-session without restarting. Use this when the user says "switch to [persona]", "change persona", "be more technical", "think like a marketer", or similar requests to change how Copilot behaves during the current session.
---

# Switch Persona

This skill allows mid-chat persona switching. When invoked:

## 1. Identify the Target Persona
- If the user specifies a persona name (e.g., "switch to marketing"), match it to an available persona
- If no persona is specified, list all available personas and ask which one to switch to

### Available Personas
**Always dynamically scan `~/.copilot/personas/` for subdirectories.** Each subdirectory containing a `persona.instructions.md` file (or legacy `AGENTS.md`) is an available persona. Do NOT rely on a hardcoded list — new personas may be added at any time.

**Discovery steps:**
1. List all subdirectories in `~/.copilot/personas/` (excluding `active/`)
2. For each subdirectory, check for `persona.instructions.md` (preferred) or `AGENTS.md` (legacy fallback)
3. Read the file to extract the persona name and a brief description (found in the `# Persona:` heading after any frontmatter)
4. Present the full list to the user

**Directory name → display name mapping:** Convert kebab-case directory names to title case for display (e.g., `hypervelocity-engineer` → `Hypervelocity Engineer`, `architect-marketer` → `Architect Marketer`).

## 2. Load the Persona
1. Read the target persona's file from `~/.copilot/personas/<name>/persona.instructions.md` (or `AGENTS.md` for legacy format)
2. Present the persona summary to the user for confirmation
3. Once confirmed, adopt the persona's:
   - **Tone & Style** — immediately adjust communication style
   - **Core Focus Areas** — shift domain expertise
   - **Behaviors** — follow the persona-specific behavioral rules

## 3. Persist the Change
After switching:
1. Run `~/.copilot/Switch-CopilotPersona.ps1 -Persona <name> -Target cli` to copy the persona file to `~/.copilot/personas/active/.github/instructions/persona.instructions.md` (Layer 3). This preserves Layer 1 (base instructions) and Layer 2 (instance rules).
2. Confirm the switch to the user:
   ```
   ✅ Switched to [persona name] persona.
   Tone, focus areas, and behaviors updated for this session.
   Next session will also start with this persona.
   ```

## 4. Handling Edge Cases
- **Fuzzy matching**: If the user says "be more technical", match to `deep-technical`. If they say "think like a PM", match to `program-manager`.
- **Unknown persona**: If no match is found, list available personas and ask the user to choose.
- **Same persona**: If already using the requested persona, confirm and continue.
- **Mid-task switch**: If switching during active work, acknowledge the switch and ask if the current task should be re-approached with the new persona's perspective.

## Important Notes
- The persona switch takes effect immediately in the current conversation
- Only **Layer 3 (active persona)** is changed — Layer 1 (base instructions) and Layer 2 (instance rules) are never modified
- Persistence is handled by `~/.copilot/Switch-CopilotPersona.ps1`, which copies the persona file to `~/.copilot/personas/active/.github/instructions/persona.instructions.md`
- Do NOT overwrite `~/.copilot/copilot-instructions.md` — that is the Layer 1 universal base
- This does NOT affect project-level instruction files — those remain project-specific
- Skills and agents remain available regardless of which persona is active
