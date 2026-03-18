---
name: project-status
description: Summarize project status from files, todos, and recent activity. Generate status reports and progress updates. Use this when asked about project status, progress, or to create a status report.
---

# Project Status

When generating a project status report, follow this workflow:

## 1. Identify the Project
- Check if the user specified a project name
- If working in a CopilotWorkspace project folder, use that project's `project.json` for context
- If no project is specified, ask which project to report on (or offer to list active projects)

## 2. Gather Status Data
Collect from these sources:
- **project.json**: Metadata, persona, environment, status, tags
- **.github/copilot-instructions.md**: Project goals and context
- **Project files**: Recent changes, new artifacts, work in progress
- **Session history**: Recent Copilot CLI sessions in this project (use session store)
- **WorkIQ** (`ask_work_iq`): Related emails, meetings, or Teams messages if relevant

## 3. Status Report Structure

```markdown
# Project Status: [Name]
**Date**: [Today's date]
**Status**: 🟢 On Track / 🟡 At Risk / 🔴 Blocked
**Persona**: [Active persona for this project]

## Summary
[2-3 sentence executive summary]

## Completed This Period
- [Bullet list of accomplishments]

## In Progress
- [Bullet list of active work items]

## Upcoming / Next Steps
- [Bullet list of planned work]

## Risks & Blockers
- [Any issues that could delay progress]

## Key Decisions Needed
- [Decisions waiting on Jim or stakeholders]
```

## 4. Multi-Project Dashboard
When asked for a dashboard or overview of all projects:
- Scan `CopilotWorkspace\` for all project folders with `project.json`
- Present a summary table:

| Project | Status | Persona | Last Updated | Next Action |
|---------|--------|---------|-------------|-------------|
| ... | ... | ... | ... | ... |

## Output
- Save status reports to the project folder
- Offer to email or share via Teams if appropriate
