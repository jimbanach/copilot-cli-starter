---
name: content-drafting
description: Draft documents, briefs, presentations, and collateral with proper structure and audience awareness. Use this when asked to write, draft, or create content such as documents, briefs, one-pagers, decks, or written deliverables.
---

# Content Drafting

When drafting content, follow this workflow:

## 1. Clarify the Brief
Before writing, confirm:
- **Audience**: Who will read this? (internal team, partners, customers, executives)
- **Purpose**: Inform, persuade, enable, or document?
- **Format**: Document, one-pager, presentation outline, email, blog post?
- **Tone**: Technical, executive summary, marketing, casual?
- **Length**: Quick summary or comprehensive deep-dive?

If any of these are unclear, ask before drafting.

## 2. Structure First
Use the appropriate structure for the content type:

### Document / Brief
1. Executive Summary (2-3 sentences)
2. Background / Context
3. Key Points / Findings
4. Recommendations / Next Steps
5. Appendix (if needed)

### One-Pager / Solution Brief
1. Headline + value proposition (one sentence)
2. The challenge (customer pain point)
3. The solution (what we offer)
4. Key benefits (3-5 bullets)
5. Call to action

### Presentation Outline
1. Title slide + subtitle
2. Agenda / Overview
3. Content slides (one key message per slide)
4. Summary / Key takeaways
5. Next steps / Call to action

## 3. Writing Guidelines
- Use active voice and clear, direct language
- Lead with the most important information
- Use bullet points and tables for scannability
- Include specific data, examples, or references when available
- For Microsoft content, use official product names and terminology
- Check `_shared-resources\references\` for relevant frameworks or prior content

## 4. Visual Assets

AI-generated images are available via the `image-gen` MCP tools (`generate_image`, `edit_image`).

**⚠️ Propose, don't generate.** Image generation has real costs. During content drafting, **describe images you'd recommend — do not generate them.** Include inline descriptions like:

> *[Suggested image: Photorealistic aerial view of a modern data center at dusk, warm lighting, corporate feel — landscape format]*

This gives the user a clear picture of what you'd create, and lets them approve, adjust, or skip before any cost is incurred. The PPTX or DOCX skill handles actual generation and insertion during the build phase.

**Good candidates for AI-generated images:**
- Hero images for title slides or document covers
- Conceptual illustrations for abstract topics (e.g., "cloud security," "digital transformation")
- Icons or logos when none exist
- Visual metaphors that reinforce key points

**Do NOT suggest generating:**
- Official product screenshots (use real ones)
- Microsoft-branded photography (use official assets when available)
- Charts or data visualizations (use charting tools instead)
- Decorative images that don't add meaning

## 5. Review & Polish
- Check for consistency in terminology and formatting
- Ensure the call to action is clear
- Flag if legal/compliance review is needed (external-facing content)
- Verify visual aids strengthen the message — don't add images for decoration alone

## Output
Save drafts to the active project folder. Offer to save reusable templates to `CopilotWorkspace\_shared-resources\templates\`.
