---
applyTo: "**"
---
# Instance Configuration: Work Machine

## Identity
- This is {{YOUR_NAME}}'s **work machine** instance
- Workspace root: {{WORKSPACE_PATH}}/
- GitHub account: {{YOUR_NAME}}banach_microsoft

## Confidentiality Rules
- Before including information that may be confidential or highly confidential in any output that will be stored outside the current project folder (e.g., committed to a repo, shared in a document, exported, or synced), ask for user confirmation first
- Examples of potentially confidential content: customer names, partner-specific strategies, NDA-protected materials, internal org structures, unreleased roadmap details, specific revenue or engagement data
- Content that is NOT confidential: publicly documented Microsoft product names and features, general role descriptions, publicly available frameworks and methodologies, Microsoft Learn content
- When in doubt, flag it and ask: "This may contain confidential information. Should I include it?"
- This does NOT apply to content that stays within the local project folder or session

## Work-Specific Tools
- WorkIQ is available for email and calendar access via the workiq MCP server
- OneDrive - Microsoft is available for file storage and sharing

## WorkIQ Proactive Usage
WorkIQ connects to Microsoft 365 via the `ask_work_iq` tool. **Use it proactively** — don't wait for explicit requests.

### When to use WorkIQ
- **Context enrichment:** When a task involves people, meetings, decisions, or timelines, query WorkIQ for relevant emails, threads, or calendar context before proceeding. Example: preparing an agenda → check for recent emails about that meeting's topic.
- **Information gap filling:** When local files, the web, and GitHub don't have what's needed, try WorkIQ as a fallback for internal information. Example: "What did we decide about the timeline?" → search recent threads.
- **People context:** When a task references colleagues, stakeholders, or teams, use WorkIQ to surface org context, recent interactions, or shared documents.
- **Meeting and email workflows:** Proactively support meeting-prep, email-triage, content-drafting, and project-status skills by pulling M365 data as input.

### When NOT to use WorkIQ
- Purely technical/coding tasks with no people or organizational context
- When a project's `project.json` contains `"workiq_enabled": false` — only use when explicitly asked
- Don't over-query: one or two targeted questions per task, not a barrage

### Transparency
When presenting information gathered from WorkIQ, mark it with **📧 WorkIQ** so the source is clear. Example: "📧 WorkIQ: Sarah sent an email on March 12 confirming the revised timeline."

### Productivity Plugin (when installed)
The `workiq-productivity` plugin adds read-only insights beyond basic queries:
- **Email triage analysis** — priority scoring and action item extraction
- **Meeting cost analysis** — time investment across recurring meetings
- **Org charts** — reporting structures and team relationships
- **Channel audits** — Teams channel activity and engagement patterns

These tools appear as additional MCP tools when the plugin is installed (`/plugin install workiq-productivity@work-iq`). Use them to enrich status reports, meeting prep, and stakeholder analysis.

## Known Folder Paths
When saving files to user-facing locations, use these resolved paths (OneDrive Known Folder Move may redirect them):
- **Desktop:** `C:\Users\{{YOUR_NAME}}banach\OneDrive - Microsoft\Desktop`
- **Documents:** `C:\Users\{{YOUR_NAME}}banach\OneDrive - Microsoft\Documents`
