---
name: image-generation
description: Generate, edit, and manage AI images using the image-gen MCP server. Handles prompt crafting, model selection, output management, and image workflows for presentations, documents, social media, and creative projects. WHEN asked to create an image, generate a picture, make a graphic, edit a photo, create a logo, design an icon, illustrate something, create visual content, or produce any kind of image asset.
---

# Image Generation Skill

This skill orchestrates the `image-gen` MCP server tools to produce AI-generated images. It handles prompt engineering, model selection, and output management.

## Available MCP Tools

### `generate_image`
Generate images from text prompts. Auto-selects the best available model if none specified.
- **prompt** (required): Descriptive text for the image
- **model** (optional): Specific model ID — omit for auto-selection
- **quality**: `medium` (default via env), `high`, `low`, `auto` — only use `high` if the user explicitly requests it
- **size**: `1024x1024` (default), `1536x1024`, `1024x1536`
- **n**: Number of images (1-10)
- **background**: `transparent`, `opaque`, `auto`
- **output_format**: `png` (default), `jpeg`, `webp`
- **output_dir**: Override the default save directory

### `edit_image`
Edit an existing image using AI (requires Azure OpenAI GPT-Image-1.5 or GPT-Image-1).
- **image** (required): Absolute file path to source image
- **prompt** (required): Description of the desired edit
- **mask** (optional): Absolute file path to a mask image (transparent areas = edit zones)
- **model**: Defaults to `gpt-image-1.5`
- **quality**, **size**, **n**, **output_dir**: Same as generate_image

### `recommend_model`
Get ranked model recommendations for a task before generating.
- **task_description** (required): Describe what you want to create
- **prefer_cost**, **prefer_speed**, **prefer_quality**: Boolean toggles to weight recommendations

## Workflow

### 1. Understand the Request
Before generating, clarify:
- **Subject**: What is the image of?
- **Style**: Photorealistic, illustration, digital art, cartoon, minimalist, icon?
- **Dimensions**: Square (1024x1024), landscape (1536x1024), portrait (1024x1536)?
- **Purpose**: Presentation slide, document figure, social media, logo, icon?
- **Background**: Does it need transparency (logos, icons)?

If the request is clear enough, proceed directly. If ambiguous, ask one clarifying question.

### 2. Craft an Effective Prompt
Write detailed, descriptive prompts. The quality of the output depends heavily on prompt quality.

**Good prompt patterns:**
- Lead with the subject and style: "A photorealistic product photo of..."
- Include composition details: "centered, with soft lighting, shallow depth of field"
- Specify colors and mood: "warm tones, professional, clean"
- For text in images: Quote the exact text to render: 'with the text "Welcome" in bold serif font'

**Prompt tips by use case:**
| Use Case | Prompt Strategy |
|----------|----------------|
| Presentation slides | "Professional, clean, corporate style, simple composition, [subject]" |
| Document figures | "Technical diagram style, clear labels, white background, [subject]" |
| Social media | "Eye-catching, vibrant colors, modern design, [subject]" |
| Logos/icons | "Minimalist [subject] icon, flat design, transparent background" |
| Realistic photos | "Photorealistic [subject], natural lighting, high detail, 8K quality" |

### 3. Choose the Right Parameters
- **Logos, icons, stickers** → `background: "transparent"`, `output_format: "png"`
- **Presentation slides** → `size: "1536x1024"` (landscape) — medium quality is fine for slides
- **Portrait/headshot** → `size: "1024x1536"`
- **Quick drafts** → `quality: "medium"` to save cost
- **Multiple options** → `n: 3` to generate variants

### 4. Generate and Deliver
1. Call `generate_image` with the crafted prompt and parameters
2. Report the file path(s) to the user
3. If the user wants to see the image, use the `view` tool on the file path
4. If the result needs tweaking, refine the prompt and regenerate

### 5. Iterative Refinement
If the user isn't happy with the result:
- Ask what specifically to change (composition, colors, style, subject)
- Adjust the prompt — don't start from scratch, iterate on what worked
- If editing an existing image, use `edit_image` with the generated file path

## Model Availability
The MCP auto-discovers available models from configured providers:
- **Azure AI Foundry**: FLUX.2 Flex — good all-rounder, strong photorealism and text. This will be our default in most scenarios due to its balance of quality and cost. It's a great choice for general image generation needs.
- **Azure OpenAI**: GPT-Image-1.5 (preferred) / GPT-Image-1 — best for editing, text rendering, and complex compositions. More expensive than FLUX, so we recommend using it when you need its specific strengths. For general image generation, FLUX.2 Flex is often sufficient and more cost-effective. You should never use this on a first pass, only if a user specifies it specifially or says they really don't like the other generation.


If no model is specified, the MCP auto-selects the best match based on the prompt content. Use `recommend_model` when the user wants to compare options.

## Cost Awareness

Every generation incurs cost. Treat image generation as a deliberate action, not a convenience.

- **Don't generate speculatively.** Only call `generate_image` when you have a clear, confirmed intent. If you're unsure what the user wants, describe the image you'd create and ask first.
- **One at a time.** Generate a single image and confirm it meets the need before generating more. Don't batch-generate "just in case."
- **Use `n: 1` (default).** Only generate multiple variants (`n: 2+`) if the user explicitly asks for options.
- **Default to `quality: "medium"`.** The MCP server is configured to default to medium quality via `IMAGE_DEFAULT_QUALITY`. This is sufficient for the vast majority of use cases — presentations, social media posts, documents, and drafts. Only use `quality: "high"` when the user **explicitly requests** high quality, print-resolution output, or a polished final asset where the extra detail matters. The cost difference is significant (~$0.04 vs ~$0.17+ per image) and the quality difference is invisible in most delivery formats (PowerPoint slides, Facebook posts, Teams messages, etc.).
- **Don't regenerate for minor tweaks.** If the user asks to change text overlaid on an image, adjust the text — don't regenerate the image. Use `edit_image` for targeted changes to existing images.
- **When invoked by other skills** (PPTX, DOCX, content-drafting): those skills are responsible for proposing images and getting user approval before calling generation. Respect their workflow.

## Output Management
- **Do NOT pass `output_dir`** unless the user explicitly requests a specific save location. The MCP server's `IMAGE_OUTPUT_DIR` environment variable handles the default path automatically (`Pictures/ai-generated`). Passing `output_dir` overrides this default.
- Filenames follow `{timestamp}-{prompt-slug}.{ext}` format
- Generated images are not committed to git — they're working artifacts

## Examples

**Simple generation:**
> "Create an image of a mountain landscape at sunrise"
→ Call `generate_image` with a detailed prompt, default settings

**Presentation asset:**
> "I need a hero image for my presentation about cloud security"
→ `generate_image` with landscape size, professional style prompt, high quality

**Logo creation:**
> "Generate a minimalist logo for my project"
→ `generate_image` with transparent background, png format, square size

**Image editing:**
> "Remove the background from this photo" (with file path)
→ `edit_image` with the file path and edit prompt

**Model comparison:**
> "What's the best model for generating product photos?"
→ `recommend_model` with task description
