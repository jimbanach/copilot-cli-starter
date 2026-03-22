# Effective New Project Prompts for Copilot CLI

How to write great "new project" prompts that give Copilot CLI everything it needs to hit the ground running.

---

## The Pattern: Full Context Handoff

When you tell Copilot CLI to start a new project, it needs to build a complete mental model — who's involved, where things live, and how to find information. The **Full Context Handoff** pattern gives it all of that in a single prompt.

> **Why it matters:** A vague prompt means Copilot has to ask 5–10 follow-up questions before it can do anything useful. A Full Context Handoff prompt lets it scaffold the project, load the right persona, and start working immediately.

---

## The 6 Core Elements

Every strong project prompt includes these six pieces:

| # | Element | What to Include | Example |
|---|---------|----------------|---------|
| 1 | **Action** | A clear verb — what you're asking Copilot to do | "startup a new project", "create a project for..." |
| 2 | **Name & Scope** | Project name + what's in scope (and what's adjacent but separate) | "Data Security Envisioning workshop — includes any Data Security activities rolled into ABS workshops" |
| 3 | **Data Locations** | Exact file paths with a note on what each folder contains | "Two OneDrive folders: `~/OneDrive/.../Workshop Materials` (slide decks, handouts) and `~/OneDrive/.../Planning` (timelines, notes)" |
| 4 | **Communication Channels** | Teams chats/meetings **by name AND type** (group chat, meeting, channel) | "Teams meeting: 'Data Security Weekly Sync'; Group chat: 'DS Workshop Planning'" |
| 5 | **People & Roles** | Who's involved, who owns what, and your influence level | "Francois owns the content; I'm a contributor/reviewer with strong influence on direction" |
| 6 | **Work Tracking** | ADO project, GitHub repo, Planner board, or whatever tracks tasks | "Tracked in the SCI-COE ADO project" |

> 💡 **Tip:** Don't say "check Teams." Say which Teams item, and whether it's a group chat, a meeting chat, or a channel. Copilot uses WorkIQ to search, and the item type changes how it queries.

---

## 4 Recommended Additions

These aren't required, but they save a round-trip every time:

| Addition | Why It Helps | Example |
|----------|-------------|---------|
| **Persona preference** | Copilot loads the right tone/expertise from the start | "Use the deep-technical persona" |
| **Current phase/status** | Tells Copilot where in the lifecycle you are — planning, executing, wrapping up | "We're in early planning — no content has been created yet" |
| **Key constraints** | Prevents Copilot from suggesting things you can't use | "Must use GA features only — no preview/beta services" |
| **Tool/source preferences** | Directs where Copilot should look for truth | "Use Microsoft Learn as source of truth for product capabilities; use WorkIQ for internal context and decisions" |

---

## Annotated Real-World Example

Here's an actual project prompt, broken down element by element:

---

> **[Action]** "we need to startup a new project."
>
> **[Name & Scope]** "This one is going to be the Data Security Envisioning workshop project. This is the project where i will collaborate with Francois van Hemert on the Data Security Envisioning workshop as well as any Data Security Activities that get incorporated into the ABS Copilot + Power Workshops."
>
> **[Data Locations]** "There are two folder paths in my one drive where the content is stored: `~/OneDrive - Microsoft/Documents/Workshops/Data Security Envisioning` (workshop decks and handouts) and `~/OneDrive - Microsoft/Documents/Planning/Data Security` (timelines, agendas, meeting notes)."
>
> **[Communication Channels]** "We also talk about this in meetings and chats so you will have to use WorkIQ. 4 Teams items to look at are: 'Data Security Envisioning Sync' (recurring meeting), 'DS Workshop Planning' (group chat), 'ABS Workshop Coordination' (group chat), and 'Data Security Updates' (Teams channel)."
>
> **[People & Roles]** "Francois is the primary owner of all of the workshop content and i am a contributer and reviewer but my feedback has strong weight."
>
> **[Work Tracking]** "We also track this work in the SCI-COE ADO project."

---

### What Makes This Good

✅ Clear action verb — no ambiguity about what's being asked
✅ Scope includes adjacent work (ABS workshops) so Copilot knows the boundary
✅ File paths are explicit — Copilot can load content immediately
✅ Teams items are named AND typed — WorkIQ can find them
✅ Influence level is stated — Copilot knows how to frame suggestions (direct vs. deferential)
✅ Work tracking system is named — Copilot can reference ADO for status

### What's Missing

The prompt above covers all 6 core elements but skips the 4 recommended additions. Here's the **Even Better** version:

---

> We need to startup a new project. This one is going to be the **Data Security Envisioning workshop** project. This is the project where I will collaborate with Francois van Hemert on the Data Security Envisioning workshop as well as any Data Security Activities that get incorporated into the ABS Copilot + Power Workshops.
>
> There are two folder paths in my OneDrive where the content is stored: `~/OneDrive - Microsoft/Documents/Workshops/Data Security Envisioning` (workshop decks and handouts) and `~/OneDrive - Microsoft/Documents/Planning/Data Security` (timelines, agendas, meeting notes).
>
> We also talk about this in meetings and chats so you will have to use WorkIQ. 4 Teams items to look at are: 'Data Security Envisioning Sync' (recurring meeting), 'DS Workshop Planning' (group chat), 'ABS Workshop Coordination' (group chat), and 'Data Security Updates' (Teams channel).
>
> Francois is the primary owner of all of the workshop content and I am a contributor and reviewer but my feedback has strong weight. We also track this work in the SCI-COE ADO project.
>
> **[Persona]** Use the **deep-technical** persona for this project.
>
> **[Current Phase]** We're in early planning — Francois has a draft deck but no content has been reviewed yet.
>
> **[Constraints]** All product references must use GA features only — nothing in preview or private preview.
>
> **[Tool/Source Preferences]** Use **Microsoft Learn** as the source of truth for product capabilities. Use **WorkIQ** for internal decisions, meeting context, and action items.

---

## Quick Reference Card

Copy this template and fill in the blanks:

```
We need to [ACTION] a new project. This one is [NAME] — it covers [SCOPE].

Data lives in: [PATH 1] ([description]) and [PATH 2] ([description]).

Teams items: '[NAME]' ([type: meeting/group chat/channel]), '[NAME]' ([type]).

People: [PERSON] owns [WHAT]. I am a [ROLE] with [INFLUENCE LEVEL] influence.

Work is tracked in [SYSTEM/PROJECT NAME].

Use the [PERSONA] persona. We're currently in [PHASE].
Constraints: [ANY LIMITS].
Prefer [TOOLS/SOURCES] for [PURPOSE].
```

---

## Common Mistakes

| Mistake | Why It Hurts | Fix |
|---------|-------------|-----|
| "Check Teams for context" | Copilot doesn't know which Teams item to search | Name each item and its type |
| "Files are in OneDrive" | Could be any of 50+ folders | Give the exact path(s) |
| "I work with the team on this" | No names, no roles, no ownership | Name people, state who owns what |
| Skipping work tracking | Copilot can't reference task status or priorities | Name the ADO project, GitHub repo, or board |
| No persona specified | Copilot uses whatever was loaded last | State which persona fits the work |
| No phase/status | Copilot doesn't know if you're planning or executing | One sentence: "We're in [phase]" |
