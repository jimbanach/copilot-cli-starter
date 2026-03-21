---
name: persona-creator
description: "Create new Copilot CLI personas or evaluate/improve existing ones. Use when asked to create a persona, build a persona, make a new persona, review a persona, improve a persona, or evaluate a persona. Also triggers on 'what personas do I have' or 'help me design a persona'. Handles the full lifecycle: requirements gathering, library analysis, generation, review, and deployment."
---

# Persona Creator

Two modes: **Create** (build a new persona) and **Evaluate** (review and improve an existing one).

## Persona File Format

Persona files use the `.instructions.md` extension with `applyTo` frontmatter for auto-discovery:

```markdown
---
applyTo: "**"
---
# Persona: [Display Name]

[1-2 paragraph identity statement — who you are, what you specialize in, how you work]

## Tone & Style
- [3-6 bullets defining communication approach]

## Core Focus Areas
- [Domain expertise organized by area]
- [Use ### subsections for complex/framework-heavy personas]

## Behaviors
- [Actionable rules for how to operate]
- [Tool preferences, validation approaches, error handling]
- ✅ **Always:** [non-negotiable actions]
- ⚠️ **Ask first:** [actions requiring user confirmation]
- 🚫 **Never:** [hard constraints]
```

### Structural Guidelines

- **Minimal personas** (20-30 lines): Use the flat 3-section template. Good for focused, single-domain roles (e.g., "productivity coach", "security reviewer").
- **Deep personas** (50-200 lines): Add subsection hierarchies, numbered principles, methodology frameworks. Good for complex, multi-faceted roles (e.g., engineering methodologies, teaching frameworks).
- Depth should match complexity — don't pad simple roles or compress complex ones.

---

## Mode 1: Create

### Step 1: Gather Requirements

Ask these questions **one at a time** using the ask_user tool:

1. **Role name** — "What should this persona be called?" Suggest a display name and derive a `kebab-case` folder name (e.g., "Data Engineer" → `data-engineer`).

2. **Domain expertise** — "What area(s) does this persona specialize in?" Push for specificity: "Azure infrastructure with Bicep and Terraform" not "cloud stuff." Ask for technologies, versions, and frameworks.

3. **Target audience** — "Who will you interact with when using this persona?" (developers, executives, students, mixed technical/non-technical)

4. **Tone archetype** — Offer choices:
   - Professional/Technical — precise, shows work, uses correct terminology
   - Friendly/Approachable — warm, explains clearly, encourages questions
   - Strict/Authoritative — direct, opinionated, enforces standards
   - Educational/Teaching — patient, provides context, explains "why"
   - Action-Oriented — decisive, bias toward building and shipping
   - Custom — describe in their own words

5. **Depth** — "Should this be a minimal persona (20-30 lines, 3 sections) or a deep persona (50-200 lines, with sub-frameworks and methodology)?" Show the trade-off: minimal loads faster and uses less context; deep provides richer behavioral guidance.

6. **Boundaries** — "What should this persona always do? What should it ask before doing? What should it never do?" These become the three-tier boundaries in the Behaviors section.

### Step 2: Analyze Existing Library

Before generating, scan the persona directories:

1. **Scan `~/.copilot/personas/`** for deployed personas (subdirectories with persona files)
2. **Scan the repo `personas/` directory** if working in the config repo
3. **Check for overlap** — flag if the new persona's domain overlaps significantly (>50%) with an existing one. Suggest differentiation or confirm the user wants a distinct variation.
4. **Note structural patterns** — use neighboring personas as consistency references

### Step 3: Generate Draft

Produce a complete persona file following the format above. Key quality checks:

- **Specificity test:** Does it name exact technologies, versions, and domains? "Expert in React 18+ with TypeScript and Vite" not "frontend developer."
- **Identity test:** Does the opening paragraph create a distinct character? Could you tell this persona apart from others by reading just the first paragraph?
- **Actionability test:** Are Behaviors concrete and executable? "Always validate against Microsoft docs using microsoft_docs_search" not "be accurate."
- **Boundary test:** Are the Always/Ask/Never rules clear and non-overlapping?
- **Tone test:** Do the Tone & Style bullets create a voice distinct from other personas?

### Step 4: Review & Refine

Present the full draft to the user. Ask for feedback. Iterate until satisfied.

Common refinement patterns:
- "Too generic" → add more specific technologies, tools, or domain knowledge
- "Too verbose" → trim to essential bullets, move detail into subsections
- "Doesn't sound like what I want" → revisit tone archetype, adjust voice bullets
- "Missing something" → identify the gap (tools? boundaries? domain area?) and add it

### Step 5: Deploy

1. Create the persona directory: `personas/<kebab-name>/persona.instructions.md` (in the config repo if working there, otherwise `~/.copilot/personas/<kebab-name>/`)
2. Offer to deploy immediately using `Switch-CopilotPersona.ps1 -Persona <name>` (which deploys to `~/.copilot/personas/active/.github/instructions/persona.instructions.md`)
3. Suggest testing: "Start a new session and ask the persona to introduce itself — does the tone and focus match what you expected?"

---

## Mode 2: Evaluate & Improve

When the user asks to review, evaluate, or improve an existing persona:

### Step 1: Load the Persona

Read the persona file from the repo or deployed location. If the user doesn't specify which persona, list available ones and ask.

### Step 2: Score Against Best Practices

Evaluate on six dimensions (rate each as Strong / Adequate / Needs Work):

| Dimension | Strong | Needs Work |
|-----------|--------|------------|
| **Specificity** | Names exact technologies, versions, domains | Vague descriptors ("good at coding") |
| **Structure** | Follows standard template with clear sections | Missing sections, inconsistent formatting |
| **Boundaries** | Clear Always/Ask/Never rules | No constraints or overly broad rules |
| **Tone Clarity** | Distinct voice, consistent style bullets | Generic or indistinguishable from other personas |
| **Actionability** | Concrete, executable behaviors | Abstract or aspirational statements |
| **Length Fit** | Depth proportional to role complexity | Padded simple role or compressed complex one |

### Step 3: Compare to Library

- How does this persona differ from its neighbors?
- Any unintentional overlap with other personas?
- Is there a gap this persona could fill better?

### Step 4: Present Findings

Summarize strengths and specific improvement suggestions. Be concrete: "Add version numbers to the tech stack list" not "be more specific."

### Step 5: Apply Improvements

If the user agrees, generate an updated version. Preserve the user's voice and intent — improve structure and specificity without rewriting their personality choices.
