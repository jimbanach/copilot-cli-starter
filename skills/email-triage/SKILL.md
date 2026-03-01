---
name: email-triage
description: Summarize and prioritize emails, surface action items, flag urgent threads, and draft replies. Use this when asked to check email, triage inbox, summarize messages, or draft a reply.
---

# Email Triage

When triaging email or messages, follow this workflow:

## 1. Gather Messages
- Use the **WorkIQ** tool (`ask_work_iq`) to pull recent emails or search for specific threads
- If the user asks about a specific sender, topic, or time range, filter accordingly
- Default to unread or recent messages if no filter is specified

## 2. Triage & Prioritize
Categorize each message into:

| Priority | Criteria | Action |
|----------|----------|--------|
| 🔴 **Urgent** | Requires response today, escalation, or blocking issue | Flag immediately |
| 🟡 **Action needed** | Requires response or task, but not time-critical | Add to action list |
| 🔵 **FYI** | Informational, no action needed | Summarize briefly |
| ⚪ **Low priority** | Newsletters, automated notifications, CC-only | Skip or batch |

## 3. Summarize
For each message, provide:
- **From**: sender name
- **Subject**: one-line summary
- **Action needed**: what {{YOUR_NAME}} needs to do (if anything)
- **Deadline**: if any is mentioned or implied

Lead with action items and decisions, not narrative recaps.

## 4. Draft Replies
When asked to draft a reply:
- Match the tone of the original thread
- Keep it concise — aim for 3-5 sentences unless complexity requires more
- Include specific answers to questions asked
- End with a clear next step or call to action
- Offer to attach relevant documents from OneDrive if appropriate

## Output Format
Present as a prioritized table, then detail the urgent/action items below.


## Tip
- Flag emails from your manager or skip-level as high priority by default
