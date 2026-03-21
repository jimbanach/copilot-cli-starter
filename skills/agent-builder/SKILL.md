---
name: agent-builder
description: "Build agents for Copilot CLI (.agent.md) and VS Code Chat Participants (extensions). Guides users interactively through requirements gathering, environment scanning, agent generation, persona selection, testing, and iteration. Use when asked to create, build, scaffold, or design an agent."
---

# Agent Builder

## Overview

This skill helps you create agents for two platforms:
1. **Copilot CLI agents** -- `.agent.md` files that run as specialized sub-agents in the Copilot CLI terminal
2. **VS Code Chat Participants** -- Full VS Code extensions with `@mention` chat integration

The skill walks through requirements interactively, scans your environment for existing patterns, generates the agent, and validates it with testing.

---

## Workflow

Building an agent follows these steps:

1. **Detect agent type** (CLI or VS Code Chat Participant)
2. **Gather requirements** (purpose, capabilities, commands)
3. **Determine persona** (select existing or create new)
4. **Scan environment** (existing agents, tools, MCP servers)
5. **Generate agent files** (using scaffolding script + customization)
6. **Self-test** (automated validation)
7. **Interactive test** (guided test with user)
8. **Iterate** (refine based on test results)

---

## Step 1: Detect Agent Type

When activated, determine which type of agent the user wants:

**If the user specifies the type**, proceed directly.

**If unclear**, ask:

*"What type of agent would you like to build?"*

Offer these choices:
- **Copilot CLI agent** -- A `.agent.md` file that runs in the terminal. Best for personal/team workflows, file processing, code review, or any task-focused automation. No coding required -- just markdown instructions.
- **VS Code Chat Participant** -- A full VS Code extension with `@mention` support. Best for distributing via the Marketplace, deep VS Code integration, or custom UI elements. Requires TypeScript.

**Decision factors to help the user:**

| Factor | CLI Agent | VS Code Chat Participant |
|--------|-----------|--------------------------|
| Setup complexity | Zero -- just a markdown file | Full extension project (TypeScript, npm) |
| Distribution | Copy file or share via repo | VS Code Marketplace |
| VS Code API access | None | Full (workspace, debug, editor, etc.) |
| Custom UI | None (text only) | Buttons, file trees, progress, follow-ups |
| Tool access | Copilot CLI tools (read, edit, search, web, agent, mcp) | Language Model API + any VS Code API |
| Best for | Personal productivity, team workflows | Polished products, broad distribution |

Read `references/cli-agent-format.md` for CLI agent details.
Read `references/vscode-chat-participant.md` for VS Code extension details.

---

## Step 2: Gather Requirements

Ask the user these questions **one at a time** using the `ask_user` tool. Adapt the questions based on the agent type chosen in Step 1.

### For Both Types

1. **What should this agent do?**
   *"Describe what you want the agent to do. Be as specific as you can -- what's the core task it should handle?"*
   - Listen for: the primary use case, input/output expectations, domain expertise needed

2. **Who is the audience?**
   *"Who will use this agent? Just you, your team, or a broader audience?"*
   - This affects complexity, documentation depth, and error handling

3. **What should it be called?**
   *"What name should the agent have?"*
   - For CLI: suggest kebab-case (e.g., `terraform-reviewer`)
   - For VS Code: suggest lowercase for @mention name, Title Case for display name

### For CLI Agents

4. **What tools does it need?**
   *"What should the agent be able to do?"*
   Offer choices with explanations:
   - `read` -- Read files, search directories
   - `edit` -- Create and modify files
   - `search` -- Code search (grep, glob)
   - `web` -- Web search and fetch
   - `agent` -- Delegate to sub-agents
   - `mcp` -- Use MCP server tools
   
   Apply principle of least privilege -- only suggest tools the agent actually needs.

5. **Does it produce output files?**
   *"Should the agent create or modify files, or only report findings?"*
   - If report-only: suggest tools `[read, search]`
   - If creates files: add `edit` to tools

### For VS Code Chat Participants

4. **What slash commands should it have?**
   *"What quick-access commands should users be able to invoke with `/`? For example, `/analyze`, `/generate`, `/explain`."*

5. **Does it need VS Code workspace context?**
   *"Should the agent be aware of open files, workspace structure, or debug state?"*

6. **Publisher name?**
   *"What publisher ID should be used for the extension? (This is your VS Code Marketplace publisher name.)"*

---

## Step 3: Determine Persona

The agent's persona defines its communication style, tone, and personality.

Ask:
*"What kind of personality should this agent have? Think about tone and style."*

Offer choices:
- **Professional/Technical** -- Precise, concise, uses correct terminology
- **Friendly/Approachable** -- Warm, explains things clearly, encourages questions
- **Strict/Authoritative** -- Direct, opinionated, enforces standards
- **Educational/Teaching** -- Patient, provides context, explains "why"
- **Custom** -- Describe the persona you want

After the user chooses:

1. **Check for existing personas** -- Scan `~/.copilot/personas/` for matching personas
2. **If a match exists** -- Ask if they want to use or adapt it
3. **If no match** -- Invoke the **persona-creator** skill to guide the user through creating a new persona. The persona-creator handles requirements gathering, library analysis, generation, and review.
4. **Incorporate into agent instructions** -- Weave the persona characteristics into the agent's Role section and communication style

For CLI agents, the persona is embedded directly in the agent's instructions (Role section, tone guidance, response style).

For VS Code participants, the persona is encoded in the system prompt sent to the Language Model API.

---

## Step 4: Scan Environment

Before generating the agent, scan the user's environment to inform the design:

### Existing Agents
Scan `~/.copilot/agents/` and `.github/agents/` for existing `.agent.md` files:
- Read each agent's frontmatter and role description
- Note structural patterns, tool selections, and instruction styles
- Use these as **internal reference** for quality and consistency
- Do NOT reference them by name in the generated agent's instructions

### Available Tools and MCP Servers
Check what MCP servers and tools are available:
- Read the MCP configuration to identify available servers
- Note which tools are accessible (e.g., Playwright, Microsoft Docs, WorkIQ)
- Suggest relevant MCP tools the agent could leverage

### Available Skills
Scan `~/.copilot/skills/` for installed skills:
- Note complementary skills the agent could work alongside
- Suggest integration points if relevant

### Recommendations
After scanning, present a brief summary:

*"Here's what I found in your environment:"*
- **X existing agents** -- [list names and brief purposes]
- **Y MCP servers** -- [list available servers]
- **Z skills** -- [list relevant ones]
- **Recommendation:** [suggest any tools/MCP servers that would enhance the agent]

If new tools or MCP servers would benefit the agent, suggest them:
*"For this agent, you might also want to install [X] -- it provides [capability]. Want me to help set that up?"*

---

## Step 5: Generate Agent Files

### For CLI Agents

1. Run the scaffolding script:
   ```
   python scripts/init_agent.py cli <name> --path ~/.copilot/agents --tools "<tools>" --description "<description>"
   ```

2. Read the generated `.agent.md` file

3. Replace ALL TODO placeholders with the actual content gathered in Steps 2-4:
   - **Role** -- Write a clear, specific role description incorporating the persona
   - **Workflow** -- Define the step-by-step process based on the agent's purpose
   - **Output Format** -- Design the output structure appropriate for the task
   - **Rules** -- Add guardrails and boundaries
   - **Initial Response** -- Write the greeting message
   - **Interactive Elements** -- Add user interaction points where needed

4. Present the completed agent to the user for review before saving

### For VS Code Chat Participants

1. Run the scaffolding script:
   ```
   python scripts/init_agent.py vscode <name> --path <project-path> --publisher <publisher>
   ```

2. Customize the generated files:
   - **package.json** -- Update slash commands, description, disambiguation examples
   - **src/extension.ts** -- Implement command handlers, customize system prompt with persona
   - **README.md** -- Update documentation

3. Present the key files to the user for review

---

## Step 6: Self-Test

After generation, run automated validation:

### CLI Agent Self-Test

1. **Structure check** -- Verify the agent file has:
   - Valid YAML frontmatter with `description` and `tools` fields
   - A `# Title` heading
   - A `## Role` section
   - A `## Workflow` or process section
   - An `## Output Format` section
   - A `## Rules` section
   - No remaining `[TODO` placeholders

2. **Content quality check** -- Verify:
   - Description is informative (not generic placeholder text)
   - Role clearly states expertise and boundaries
   - Workflow has concrete, actionable steps
   - Tools list matches what the workflow requires
   - Rules include at least one boundary/guardrail

3. **Report results:**
   ```
   Self-Test Results:
   [PASS] Valid frontmatter
   [PASS] Required sections present
   [PASS] No TODO placeholders
   [PASS] Description is specific
   [WARN] Consider adding an "Initial Response" section
   ```

### VS Code Chat Participant Self-Test

1. **Structure check** -- Verify:
   - `package.json` has valid `chatParticipants` contribution
   - `src/extension.ts` compiles (run `npm run compile`)
   - All slash commands in `package.json` have handlers in code
   - `tsconfig.json` is valid

2. **Compile test** -- Run `npm install && npm run compile` and verify no errors

3. **Report results** the same way as CLI

---

## Step 7: Interactive Test

After self-test passes, guide the user through a live test:

### CLI Agent Interactive Test

1. Inform the user:
   *"The agent is created. Let's test it. I'll invoke it with a sample prompt -- watch the output and tell me if it behaves as expected."*

2. Construct a realistic test prompt based on the agent's purpose:
   - If it's a reviewer: provide a sample file to review
   - If it's a generator: ask it to generate something specific
   - If it's a Q&A agent: ask a representative question

3. Invoke the agent using the task tool with agent_type matching the new agent's name

4. After the agent responds, ask the user:
   *"How did that look? Any changes you'd like to make?"*

### VS Code Chat Participant Interactive Test

1. Guide the user to launch the Extension Development Host (F5)
2. Provide test prompts to type in chat:
   *"Try typing these in the Copilot Chat:"*
   - `@<name> /help`
   - `@<name> <sample prompt based on purpose>`
3. Ask for feedback

---

## Step 8: Iterate

Based on user feedback from testing:

1. **If changes are needed** -- Make targeted edits to the agent file(s)
2. **Re-run self-test** to verify changes don't break structure
3. **Offer another interactive test** round
4. **Repeat** until the user is satisfied

When the user confirms the agent is good:

*"Your agent is ready! Here's a summary:"*

| Field | Value |
|-------|-------|
| Type | [CLI / VS Code Chat Participant] |
| Name | [agent name] |
| Location | [file path] |
| Tools | [list] |
| Commands | [list, if VS Code] |
| Persona | [description] |

*"The agent is live and available in your next session. Want me to help with anything else?"*

---

## Express Mode

For experienced users who say things like "just build it" or "you know what I need":

1. Infer as much as possible from the user's description
2. Make reasonable defaults for all decisions
3. Generate the agent without asking intermediate questions
4. Present the completed agent with a summary of decisions made
5. Ask: *"I made these decisions automatically -- want to adjust anything?"*

Express mode should be offered (not forced) when:
- The user's initial request is very detailed
- The user has built agents before in this session
- The user explicitly asks for less interaction

---

## Error Handling

- **If scaffolding script fails**: Fall back to creating files manually with the create/edit tools
- **If compilation fails (VS Code)**: Read error output, fix the issue, and retry
- **If agent file already exists**: Ask if the user wants to overwrite, rename, or edit the existing one
- **If the user's request is too vague**: Ask targeted clarifying questions rather than guessing
