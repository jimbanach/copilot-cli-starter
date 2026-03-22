---
name: meeting-processing
description: Process meeting recordings and transcripts into structured notes. Orchestrates WorkIQ context gathering, transcript acquisition, and the meeting-transcript-processor agent. Use when the user shares a meeting recording URL, asks to "process a meeting", mentions a transcript to summarize, or references a recent meeting they want notes for. Do NOT use for meeting preparation (that's the meeting-prep skill).
---

# Meeting Processing

When the user wants to process a meeting recording or transcript into structured notes, follow this workflow. Your job is to **gather context and delegate** — never extract transcripts yourself.

## Trigger Detection

Activate this skill when the user:
- Shares a Stream/SharePoint recording URL
- Says "process this meeting", "summarize this recording", "create meeting notes from..."
- Shares a VTT or transcript file
- Asks you to process a meeting they just attended
- References a Teams meeting and wants notes from it

**Do NOT activate for:**
- Meeting preparation (upcoming meetings) → use `meeting-prep` skill instead
- Questions about existing meeting notes → answer directly from files in `meeting-notes/`

---

## Workflow

### Step 1 — Identify What You Have

Determine which inputs are available:

| Input | How to detect |
|-------|--------------|
| **Stream URL** | User shared a `sharepoint.com/...stream.aspx` or `*.mp4` link |
| **Local transcript file** | User referenced a `.vtt`, `.txt` file path |
| **Meeting name/time** | User mentioned a meeting by name or said "the meeting that just ended" |
| **Nothing specific** | User said "process the meeting" without details → ask which one |

If you don't have enough to identify the meeting, ask the user. **One question at a time.**

### Step 2 — Gather Context from WorkIQ

**Before calling the agent**, pull supplementary data from WorkIQ. This enriches the output significantly.

Make these WorkIQ queries (in parallel if possible):

1. **Meeting details + chat:**
   > "Get me the full meeting chat log from [meeting name] on [date]. Show every chat message with sender name and text."

2. **Copilot recap:**
   > "Get me the AI-generated meeting recap for [meeting name] on [date]. Show all topics discussed, action items, and follow-ups."

3. **Attendee details** (if not already known):
   > "Who attended [meeting name] on [date]? Include their titles and roles."

**Compile the results** into a `workiq_context` block to pass to the agent. Format:

```
## WorkIQ Context

### Attendees
- Name 1 — Title
- Name 2 — Title

### Meeting Chat
[full chat log]

### Copilot Recap
[topics, action items, follow-ups]
```

**If WorkIQ fails or returns incomplete data**, proceed anyway — the agent handles degradation. Note what was and wasn't available.

### Step 3 — Extract Transcript (if Stream URL provided)

**⚠️ CRITICAL: The sub-agent CANNOT use Playwright.** Playwright MCP tools only exist in the main session context and are not forwarded to sub-agents launched via the `task` tool. If you have a Stream URL, YOU (the main session) must extract the transcript before calling the agent.

**If the user provided a local transcript file** → skip this step entirely.

**If the user provided a Stream URL** → extract the VTT yourself using the waterfall below. **⚠️ ALWAYS follow the method order strictly: 1 → 2 → 3. Do NOT skip ahead to a later method for convenience or speed — Method 1 produces the best output (VTT with speaker names) and avoids the extra DOM-scraping step that Methods 2 and 3 require. Only proceed to the next method when the current one actually fails.**

#### Playwright Lock

Before any browser work, acquire the lock:
```
pwsh C:\Users\{{YOUR_NAME}}banach\.copilot/scripts/playwright-lock.ps1 check
pwsh C:\Users\{{YOUR_NAME}}banach\.copilot/scripts/playwright-lock.ps1 acquire
```
If the lock is held, tell the user and offer to retry later. **Release the lock as soon as browser work is done** — don't hold it during agent processing.

#### Navigate to the Stream Page

```
playwright-browser_navigate → [Stream URL]
```
Wait for page to load (5–8 seconds).

#### Method 1 — Download Button (Best: VTT with speaker names)

1. Take a `browser_snapshot`
2. Look for the **Transcript** panel (click "Transcript" tab in the enhancements menu if needed)
3. Look for a **Download** button in the transcript panel
4. **If Download is enabled:**
   - Click it → a `.vtt` file downloads to the Playwright temp output folder
   - This VTT typically includes `<v SpeakerName>` tags — full speaker attribution
   - Copy the file to the project's `reference/` folder
   - **Done** — skip Methods 2 and 3
5. **If Download is disabled** (permission message) → proceed to Method 2

#### Method 2 — Transcript API via Performance Entries (Fast: VTT without speakers)

1. Search the browser's performance entries for the transcript metadata API:
   ```javascript
   () => {
     const entries = performance.getEntriesByType('resource');
     const metadataUrl = entries.find(e =>
       e.name.includes('_api/v2.1/drives') && e.name.includes('transcripts') &&
       !e.name.includes('cdnmedia') && !e.name.includes('streamContent')
     );
     if (!metadataUrl) return JSON.stringify({ error: 'No metadata URL found' });
     return fetch(metadataUrl.name).then(r => r.json()).then(data => JSON.stringify(data, null, 2));
   }
   ```

2. If the metadata response contains a `media.transcripts` array with a `temporaryDownloadUrl`:
   ```javascript
   () => {
     return fetch('<TEMPORARY_DOWNLOAD_URL>').then(r => r.text()).then(text => {
       window.__fullTranscript = text;
       return JSON.stringify({ length: text.length, preview: text.substring(0, 100) });
     });
   }
   ```

3. Extract in chunks (15K chars at a time) and save to a local VTT file:
   ```javascript
   () => { return window.__fullTranscript.substring(0, 15000); }
   () => { return window.__fullTranscript.substring(15000, 30000); }
   // ... continue until all content extracted
   ```
   Save as: `reference/meeting-name-YYYYMMDD.vtt`

4. **⚠️ This VTT has NO speaker names** — only segment IDs and timestamped text. Get speaker attribution from the transcript panel DOM (see Speaker Attribution below).

5. **If no metadata URL found, or fetch fails** → proceed to Method 3

#### Method 3 — DOM Scraping (Slowest: gets speakers + text directly)

If both Methods 1 and 2 fail, scrape the transcript directly from the Stream UI:

1. Click the "Transcript" tab in the enhancements menu (if not already open)
2. Find the scrollable transcript container:
   ```javascript
   () => {
     const complementary = document.querySelector('[role="complementary"][aria-label="Transcript"]');
     const allDivs = complementary.querySelectorAll('div');
     let scrollEl = null;
     for (const d of allDivs) {
       const style = window.getComputedStyle(d);
       if ((style.overflowY === 'auto' || style.overflowY === 'scroll') && d.scrollHeight > 100) {
         if (!scrollEl || d.scrollHeight > scrollEl.scrollHeight) scrollEl = d;
       }
     }
     return scrollEl ? 'Found: height=' + scrollEl.scrollHeight : 'Not found';
   }
   ```

3. Scroll and extract in a single pass (the panel virtualizes — only ~20-30 entries exist in DOM at once):
   ```javascript
   async () => {
     scrollEl.scrollTop = 0;
     await new Promise(r => setTimeout(r, 500));
     const allEntries = new Map();
     const step = 800;
     let pos = 0;
     const maxScroll = scrollEl.scrollHeight;
     while (pos <= maxScroll + step) {
       scrollEl.scrollTop = pos;
       await new Promise(r => setTimeout(r, 250));
       const groups = complementary.querySelectorAll('[role="group"]');
       for (const g of groups) {
         const label = (g.getAttribute('aria-label') || '').trim();
         if (!label || label === ' ' || label.includes('Suggested') ||
             label.includes('Transcript') || label.includes('started transcription')) continue;
         const listItem = g.querySelector('[role="listitem"]');
         const text = listItem ? listItem.textContent.trim() : '';
         if (text && label) allEntries.set(label, text);
       }
       pos += step;
     }
     // Convert Map to array and return as JSON
     return JSON.stringify(Array.from(allEntries.entries()));
   }
   ```

4. Each aria-label has format: `"Speaker Name X minutes Y seconds"` — parse for speaker name and timestamp. Sort by timestamp.

5. Save as a speaker-attributed text file:
   ```
   Speaker Name [M:SS]
   Transcript text for this segment
   ---
   ```

6. **This method gives you BOTH text and speaker names** — no separate speaker attribution needed.

7. **If DOM scraping also fails** → release lock, proceed without transcript (agent will produce Tier 3 from WorkIQ).

#### Speaker Attribution (for Method 2 only)

When Method 2 succeeds, the VTT lacks speaker names. Before releasing Playwright, grab speaker mappings from the transcript panel DOM:

1. Click the "Transcript" tab (if not already visible)
2. Extract visible entries (these include speaker names in the aria-labels):
   ```javascript
   () => {
     const groups = document.querySelectorAll('[role="group"]');
     let speakers = [];
     groups.forEach(g => {
       const label = (g.getAttribute('aria-label') || '').trim();
       if (label && !label.includes('started transcription') && !label.includes('Suggested')) {
         speakers.push(label);
       }
     });
     return JSON.stringify(speakers);
   }
   ```
3. Scroll through the panel to collect ALL speaker entries (same scrolling technique as Method 3, but just collecting aria-labels, not full text).
4. Parse each label into `{ speaker, timestamp }` pairs.
5. Pass these as **Speaker Identification** data to the agent alongside the VTT.

#### Release Playwright Lock

```
pwsh C:\Users\{{YOUR_NAME}}banach\.copilot/scripts/playwright-lock.ps1 release
```

**Always release the lock after browser work — even if extraction failed.** Do not hold the lock while the agent processes the transcript.

#### Summary of Methods

| Method | Speed | Speaker Names | When to Use |
|--------|-------|---------------|------------|
| 1 — Download button | ⚡ Fast | ✅ Yes (in VTT) | Always try first |
| 2 — API + temporaryDownloadUrl | ⚡ Fast | ❌ No (need DOM supplement) | Download disabled |
| 3 — DOM scraping | 🐢 Slow | ✅ Yes (from aria-labels) | Both above failed |
| None — skip to agent | — | Via WorkIQ only | All Playwright methods failed |

**After extraction**, you have a local VTT/text file. Pass this as `transcript_path` (NOT `stream_url`) to the agent.

### Step 4 — Determine Output Path

Follow the active project's conventions:
- If working in a project with a `meeting-notes/` folder, use: `meeting-notes/YYYY-MM-DD-<short-description>.md`
- If no project context, ask the user where to save
- Use kebab-case, date-prefixed naming

### Step 5 — Call the Agent

Launch `meeting-transcript-processor` as a **background task** with the local transcript and all gathered context:

```
task: meeting-transcript-processor
mode: background
prompt:
  Process this meeting transcript into structured notes.

  Transcript file: [local path to VTT or text file]
  Output path: [path]
  Meeting title: [title]
  Meeting date: [YYYY-MM-DD]
  Attendees: [list]

  ## Speaker Identification
  [speaker-to-timestamp mappings extracted from DOM, if available]

  ## WorkIQ Context
  [paste the compiled WorkIQ context here]

  ## Project Context
  [any relevant project-specific guidance]
```

**Key rules:**
- **ALWAYS pass `transcript_path` (a local file), NOT `stream_url`.** You already extracted the transcript in Step 3 — the agent doesn't need Playwright.
- **If transcript extraction failed**, pass only WorkIQ context and no transcript_path. The agent will produce Tier 3 output.
- **DO include speaker identification** from the DOM scrape — the raw VTT typically lacks speaker names.
- **DO include WorkIQ context** — it dramatically improves output quality.
- **DO include project context** if relevant.

### Step 6 — Handle the Result

When the agent completes, read its output:

**On success:**
- Open the output file for the user (or confirm it's saved)
- Briefly summarize: "Meeting notes saved — X discussion points, Y action items, Z quotes."
- Note the processing tier if it wasn't Tier 1

**On partial success (Tier 3-4):**
- Tell the user what data was available and what was missing
- Offer alternatives: "The full transcript wasn't available. I produced notes from the Copilot recap and chat. Want me to retry if you can share the VTT directly?"

**On failure (Tier 5):**
- Read the error report the agent produced
- Surface the specific failure reasons and suggested actions to the user
- Offer to help with the suggested actions (e.g., "Should I try a different URL?" or "Can you download the VTT manually?")

**Playwright lock safety check:**
After the agent completes (success or failure), run a safety check:
```
pwsh C:\Users\{{YOUR_NAME}}banach\.copilot/scripts/playwright-lock.ps1 check
```
If the lock is still held (and the agent should have released it), release it:
```
pwsh C:\Users\{{YOUR_NAME}}banach\.copilot/scripts/playwright-lock.ps1 release
```

---

## Common Scenarios

### Scenario 1: User shares a Stream URL
```
User: "process this meeting: [Stream URL]"
You:
  1. Query WorkIQ for chat + recap + attendees (parallel)
  2. Acquire Playwright lock → navigate → extract VTT → get speakers → release lock
  3. Determine output path from project conventions
  4. Call agent with transcript_path (local VTT) + speaker IDs + workiq_context
  5. Surface result
```

### Scenario 2: User references a recent meeting by name
```
User: "process the pre-day sync from today"
You:
  1. Query WorkIQ: "Find my meeting today about pre-day sync. 
     Give me the recording URL, attendees, chat, and recap."
  2. Extract VTT from the recording URL (Playwright)
  3. Call agent with transcript_path + workiq_context
  4. Surface result
```

### Scenario 3: User provides a local VTT file
```
User: "process reference/meeting.vtt"
You:
  1. Still query WorkIQ for supplementary context (chat, recap)
  2. Call agent with transcript_path + workiq_context
  3. Surface result
  NOTE: No Playwright needed — skip Step 3 entirely
```

### Scenario 4: User asks after a meeting ends
```
User: "that meeting just ended, can you process it?"
You:
  1. Query WorkIQ for the most recent meeting that just ended
  2. Get recording URL, chat, recap, attendees
  3. NOTE: Recording may still be processing — if WorkIQ says 
     "not yet available", tell user and offer to retry in 5-10 min
  4. Once recording available, extract VTT via Playwright
  5. Call agent with transcript_path + workiq_context
```

### Scenario 5: Playwright extraction fails
```
You:
  1. WorkIQ context gathered successfully
  2. Playwright lock acquired, but VTT extraction fails 
     (e.g., no transcript on recording, permissions blocked)
  3. Release Playwright lock immediately
  4. Call agent with ONLY workiq_context (no transcript_path)
  5. Agent produces Tier 3 output
  6. Tell user: "Full transcript wasn't available — produced notes 
     from Copilot recap and chat. To upgrade, you could download 
     the VTT manually from Stream."
```

---

## What This Skill Does NOT Do

- **Does not process transcripts** — that's the agent's job (parsing, summarizing, extracting action items)
- **Does not process video frames** — video analysis is a separate workflow (currently disabled)
- **Does not replace meeting-prep** — that skill handles upcoming meeting preparation

## Architecture Note: Why the Skill Extracts Transcripts

The `meeting-transcript-processor` agent has Playwright-based acquisition paths (B2 and B) documented in its spec. However, **Playwright MCP tools are only available in the main CLI session** — they are NOT forwarded to sub-agents launched via the `task` tool. Since the agent primarily runs as a background sub-agent, those paths are unreachable.

To solve this, **this skill handles Playwright-based transcript extraction** (Step 3) in the main session, then passes a local VTT file to the agent. The agent's Playwright paths remain in its spec for the rare case of interactive/direct use, but the expected production path is: **Skill extracts → Agent processes.**
