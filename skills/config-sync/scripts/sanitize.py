"""
sanitize.py — Sanitizes copilot-cli-config content for the peer template repo.

Replaces user-specific names, paths, and sensitive content with {{variables}}.
Blanks the humanizer voice profile. Scans for potentially confidential patterns.

Usage:
    python sanitize.py <source_dir> <output_dir> [--user-name "{{YOUR_NAME}}"] [--workspace-path "..."] [--dry-run] [--json]
"""

import argparse
import json
import os
import re
import shutil
from pathlib import Path


# Patterns to replace (order matters — more specific first)
DEFAULT_REPLACEMENTS = {
    'user_patterns': [],      # Populated from --user-name
    'path_patterns': [],      # Populated from --workspace-path
}

# Files/dirs to exclude from the template entirely
EXCLUDE_FROM_TEMPLATE = [
    'instance-config.json',
    '.copilot-sync',
    'sync-state.json',
    '__pycache__',
    '.git',
]

# Files to blank/replace with templates
TEMPLATE_OVERRIDES = {
    'skills/humanizer/references/voice-profile.md': 'VOICE_PROFILE_TEMPLATE',
}

VOICE_PROFILE_TEMPLATE = """# Voice Profile — Template

Build your own voice profile to make the humanizer skill match your writing style.

## How to Create Your Voice Profile

1. **Gather samples** — collect 10-15 examples of your writing: emails, documents, chat messages, blog posts
2. **Analyze patterns** — ask Copilot to analyze your samples:
   ```
   Analyze these writing samples and create a voice profile. Identify:
   - Tone blend (e.g., formal + casual, technical + accessible)
   - Signature patterns (structure, transitions, emphasis)
   - Word choice preferences and anti-patterns
   - Sentence length and rhythm
   ```
3. **Save the profile** — paste the analysis into this file
4. **Test it** — run the humanizer on some AI-generated text and compare against your natural writing
5. **Iterate** — refine the profile based on results

## Tone Blend

*[Describe your tone here — e.g., "Pragmatic + informal + strategic"]*

## Signature Patterns

### Structure
*[How do you typically organize your writing?]*

### Word Choice
*[Words you prefer, words you avoid]*

### Anti-Patterns
*[AI-isms to eliminate — e.g., "utilize" → "use"]*

## Before/After Examples

*[Add 2-3 examples of AI text → your voice]*
"""

# Patterns that might indicate confidential content
CONFIDENTIAL_PATTERNS = [
    r'(?i)NDA\b',
    r'(?i)confidential\b',
    r'(?i)internal[\s-]only',
    r'(?i)do not share',
    r'(?i)customer[\s:]',
    # Specific financial/engagement patterns
    r'\$[\d,]+[MBK]?\b',
    r'(?i)revenue\b',
    r'(?i)engagement\s+\d',
]


def build_replacements(user_name, workspace_path, github_account=None):
    """Build the replacement patterns from user-specific values."""
    replacements = []

    if user_name:
        # Replace full name references
        replacements.append((user_name, '{{YOUR_NAME}}'))
        # Also try lowercase
        replacements.append((user_name.lower(), '{{YOUR_NAME}}'))

    if workspace_path:
        # Normalize path separators for matching
        workspace_norm = workspace_path.replace('/', '\\')
        workspace_fwd = workspace_path.replace('\\', '/')
        replacements.append((workspace_norm, '{{WORKSPACE_PATH}}'))
        replacements.append((workspace_fwd, '{{WORKSPACE_PATH}}'))
        # Also match with ~ prefix
        replacements.append(('{{WORKSPACE_PATH}}', '{{WORKSPACE_PATH}}'))

    if github_account:
        replacements.append((github_account, '{{GITHUB_ACCOUNT}}'))

    return replacements


def sanitize_content(content, replacements):
    """Apply replacements to file content."""
    for pattern, replacement in replacements:
        content = content.replace(pattern, replacement)
    return content


def scan_for_confidential(content, filepath):
    """Scan content for potentially confidential patterns."""
    findings = []
    lines = content.split('\n')
    for i, line in enumerate(lines):
        for pattern in CONFIDENTIAL_PATTERNS:
            if re.search(pattern, line):
                findings.append({
                    'file': filepath,
                    'line': i + 1,
                    'pattern': pattern,
                    'text': line.strip()[:100],
                })
    return findings


def sanitize_directory(source_dir, output_dir, replacements, dry_run=False):
    """Sanitize an entire directory tree."""
    source = Path(source_dir)
    output = Path(output_dir)

    results = {
        'copied': [],
        'sanitized': [],
        'templated': [],
        'excluded': [],
        'confidential_warnings': [],
    }

    for filepath in source.rglob('*'):
        if filepath.is_dir():
            continue

        rel = str(filepath.relative_to(source))

        # Check exclusions
        skip = False
        for excl in EXCLUDE_FROM_TEMPLATE:
            if excl in rel:
                skip = True
                break
        if skip:
            results['excluded'].append(rel)
            continue

        # Check for template overrides
        rel_fwd = rel.replace('\\', '/')
        if rel_fwd in TEMPLATE_OVERRIDES:
            template_name = TEMPLATE_OVERRIDES[rel_fwd]
            template_content = globals().get(template_name, f'# Template for {rel}\n')
            dest = output / rel
            if not dry_run:
                dest.parent.mkdir(parents=True, exist_ok=True)
                with open(dest, 'w', encoding='utf-8') as f:
                    f.write(template_content)
            results['templated'].append(rel)
            continue

        # Read and sanitize text files
        dest = output / rel
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            sanitized = sanitize_content(content, replacements)

            # Scan for confidential patterns
            warnings = scan_for_confidential(sanitized, rel)
            if warnings:
                results['confidential_warnings'].extend(warnings)

            if sanitized != content:
                results['sanitized'].append(rel)
            else:
                results['copied'].append(rel)

            if not dry_run:
                dest.parent.mkdir(parents=True, exist_ok=True)
                with open(dest, 'w', encoding='utf-8') as f:
                    f.write(sanitized)

        except (UnicodeDecodeError, PermissionError):
            # Binary file — copy as-is
            results['copied'].append(rel)
            if not dry_run:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(filepath, dest)

    return results


def print_summary(results):
    """Print human-readable summary."""
    print("\n📊 Sanitization Results")
    print("━" * 40)
    print(f"   ✅ Copied as-is:    {len(results['copied'])}")
    print(f"   🔄 Sanitized:      {len(results['sanitized'])}")
    print(f"   📄 Templated:      {len(results['templated'])}")
    print(f"   ⏭️  Excluded:       {len(results['excluded'])}")

    if results['sanitized']:
        print("\n   Sanitized files:")
        for f in results['sanitized']:
            print(f"      • {f}")

    if results['templated']:
        print("\n   Templated files:")
        for f in results['templated']:
            print(f"      • {f}")

    if results['confidential_warnings']:
        print(f"\n   ⚠️  Confidential content warnings ({len(results['confidential_warnings'])}):")
        for w in results['confidential_warnings']:
            print(f"      • {w['file']}:{w['line']} — {w['text']}")

    print()


def main():
    parser = argparse.ArgumentParser(description='Sanitize config for peer template')
    parser.add_argument('source_dir', help='Path to source (repo main branch content)')
    parser.add_argument('output_dir', help='Path to output (template repo)')
    parser.add_argument('--user-name', default='{{YOUR_NAME}}', help='User name to replace')
    parser.add_argument('--workspace-path',
                        default=os.path.expanduser('{{WORKSPACE_PATH}}'),
                        help='Workspace path to replace')
    parser.add_argument('--github-account', default=None, help='GitHub account to replace')
    parser.add_argument('--dry-run', action='store_true', help='Preview without writing files')
    parser.add_argument('--json', action='store_true', help='Output as JSON')

    args = parser.parse_args()

    replacements = build_replacements(args.user_name, args.workspace_path, args.github_account)
    results = sanitize_directory(args.source_dir, args.output_dir, replacements, args.dry_run)

    if args.json:
        print(json.dumps(results, indent=2, default=str))
    else:
        print_summary(results)


if __name__ == '__main__':
    main()
