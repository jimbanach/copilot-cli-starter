# Copilot CLI Agent Format Reference

## Overview

Copilot CLI agents are specialized sub-agents defined as `.agent.md` files. They run in separate context windows with restricted tool access, giving them focused expertise on specific tasks.

## File Location

Agents are stored as individual markdown files:
- **User-level**: `~/.copilot/agents/<name>.agent.md`
- **Project-level**: `.github/agents/<name>.agent.md` (within a repo)

User-level agents are available in all sessions. Project-level agents are available only when working in that repository.

## File Format

An agent file is a markdown document with YAML frontmatter:

```markdown
---
description: 'One-line description of what the agent does and when to use it. This appears in the agent selection UI and is used for routing decisions.'
tools: [read, edit, search, web, agent]
---

# Agent Name

## Role
You are a [role description]. You [primary capability].

## Workflow
1. Step one
2. Step two
3. Step three

## Output Format
[Define expected output structure]

## Rules
- Rule 1
- Rule 2
```

## Frontmatter Fields

| Field | Required | Description |
|-------|----------|-------------|
| `description` | Yes | A complete, informative description of what the agent does. This is shown in the UI and used to determine when to invoke the agent. Include trigger phrases and use cases. |
| `tools` | Yes | Array of tool categories the agent can access. Controls what the agent can do. |

## Available Tools

| Tool Name | Description | Use When |
|-----------|-------------|----------|
| `read` | Read files, view directories, glob/grep search | Agent needs to examine existing content |
| `edit` | Create and modify files | Agent produces or modifies files |
| `search` | Code search (grep, glob, code intelligence) | Agent needs to find code patterns |
| `web` | Web search and fetch | Agent needs external/current information |
| `agent` | Launch sub-agents (task tool) | Agent needs to delegate specialized work |
| `mcp` | Access MCP server tools | Agent needs external tool integrations |

**Principle of least privilege**: Only grant the tools the agent actually needs. A review-only agent should not have `edit`. A local-only agent should not have `web`.

## Agent Instruction Best Practices

### 1. Clear Role Definition
Start with a concise role statement that establishes expertise and boundaries:
```markdown
## Role
You are a Terraform configuration reviewer. You analyze .tf files for security misconfigurations, best practice violations, and cost optimization opportunities. You do NOT modify files — you only report findings.
```

### 2. Structured Workflow
Define the step-by-step process the agent follows:
```markdown
## Workflow
1. **Scan** — Find all relevant files (e.g., `*.tf`, `*.tfvars`)
2. **Analyze** — Check each file against the rules below
3. **Report** — Present findings in the output format
```

### 3. Explicit Output Format
Define exactly what the agent's output should look like:
```markdown
## Output Format
For each finding:
| Severity | File | Line | Issue | Recommendation |
|----------|------|------|-------|----------------|
| HIGH | main.tf | 42 | S3 bucket has no encryption | Add `server_side_encryption_configuration` block |
```

### 4. Guardrails and Boundaries
State what the agent should NOT do:
```markdown
## Rules
- Never modify files directly — report findings only
- If a file cannot be read, skip it and note the error
- Do not make assumptions about infrastructure intent — flag ambiguity for the user
- Limit findings to actionable items — no style-only comments
```

### 5. Interactive Elements
If the agent needs user input at certain points:
```markdown
## User Interaction
- If the scan finds more than 50 files, ask the user which directories to prioritize
- If a finding has multiple valid fixes, present options and ask which approach the user prefers
```

### 6. Initial Response
Define what the agent says when first invoked:
```markdown
## Initial Response
When activated, say:
*"I'm the Terraform Reviewer. Point me at a directory or specific .tf files and I'll analyze them for security, best practices, and cost optimization. What would you like me to review?"*
```

## Example: Complete Agent File

```markdown
---
description: 'Documentation Validator — Reviews markdown documentation for accuracy, completeness, broken links, and consistency. Reports issues without modifying files. Use when asked to review docs, validate documentation, or check for broken links.'
tools: [read, search, web]
---

# Documentation Validator

## Role
You are a documentation quality analyst. You review markdown files for accuracy, completeness, consistency, and broken links.

## Workflow
1. **Discover** — Scan the specified directory for `.md` files
2. **Analyze each file** for:
   - Broken internal links (references to files/anchors that don't exist)
   - Outdated information (version numbers, deprecated APIs)
   - Inconsistent terminology
   - Missing sections (no examples, no prerequisites, etc.)
   - Grammar and clarity issues
3. **Cross-reference** — Check links between documents
4. **Report** — Present findings grouped by severity

## Output Format

### Summary
- Files scanned: X
- Issues found: X (Y high, Z medium, W low)

### Findings
| Severity | File | Issue | Details |
|----------|------|-------|---------|
| HIGH | README.md | Broken link | Link to `docs/setup.md` — file does not exist |

## Rules
- Do not modify any files
- Verify external links only if the user explicitly asks (they may be rate-limited)
- Flag files with no content or placeholder text
- If a directory has no .md files, report that clearly

## Initial Response
*"I'm the Documentation Validator. Give me a directory path and I'll review all markdown files for quality issues. What docs should I check?"*
```

## Naming Conventions

- File name: `kebab-case.agent.md` (e.g., `terraform-reviewer.agent.md`)
- Use descriptive names that indicate the agent's purpose
- Avoid generic names like `helper.agent.md` or `assistant.agent.md`

## Testing an Agent

After creating an agent:
1. Start a new Copilot CLI session (or reload)
2. The agent appears in the task tool's custom agents list
3. Invoke it via the task tool: select the agent type matching your agent name
4. Test with a representative prompt that exercises the main workflow
5. Verify output format matches the specification
6. Test edge cases (empty input, large input, ambiguous requests)
