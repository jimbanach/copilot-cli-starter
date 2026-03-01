"""
compare.py — Compares local ~/.copilot/ against the copilot-cli-config repo.

Returns JSON with categorized results:
- new_in_repo: files in repo but not locally
- modified: files that differ between repo and local
- local_only: files locally but not in repo
- identical: files that match

Usage:
    python compare.py <repo_path> [--copilot-dir <path>] [--json] [--categories personas,skills,agents,scripts]
"""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path


def normalize_content(filepath):
    """Read file content and normalize line endings for comparison."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            return f.readlines()
    except Exception:
        # Binary file — fall back to byte comparison
        try:
            with open(filepath, 'rb') as f:
                return f.read()
        except Exception:
            return None


def files_are_identical(file_a, file_b):
    """Compare two files, tolerant of line ending differences."""
    content_a = normalize_content(file_a)
    content_b = normalize_content(file_b)

    if content_a is None or content_b is None:
        return content_a == content_b

    # If both are lists (text), compare line by line
    if isinstance(content_a, list) and isinstance(content_b, list):
        if len(content_a) != len(content_b):
            return False
        return all(a.rstrip('\r\n') == b.rstrip('\r\n') for a, b in zip(content_a, content_b))

    # Binary comparison
    return content_a == content_b


def get_dir_files(dirpath, exclude_patterns=None):
    """Recursively get all files in a directory, returning relative paths."""
    if exclude_patterns is None:
        exclude_patterns = ['__pycache__', '.pyc', '.pyo']

    files = {}
    dirpath = Path(dirpath)
    if not dirpath.exists():
        return files

    for filepath in dirpath.rglob('*'):
        if filepath.is_file():
            rel = str(filepath.relative_to(dirpath))
            # Skip excluded patterns
            skip = False
            for pattern in exclude_patterns:
                if pattern in str(filepath):
                    skip = True
                    break
            if not skip:
                files[rel] = str(filepath)
    return files


# Category definitions: how to discover items in repo vs local
CATEGORIES = {
    'personas': {
        'repo_subdir': 'personas',
        'local_subdir': 'personas',
        'item_type': 'directory',
        'key_file': 'AGENTS.md',
        'exclude_dirs': ['active'],
    },
    'skills': {
        'repo_subdir': 'skills',
        'local_subdir': 'skills',
        'item_type': 'directory',
        'key_file': 'SKILL.md',
        'exclude_dirs': [],
    },
    'agents': {
        'repo_subdir': 'agents',
        'local_subdir': 'agents',
        'item_type': 'file',
        'pattern': '*.agent.md',
        'exclude_dirs': [],
    },
    'scripts': {
        'repo_subdir': 'scripts',
        'local_subdir': '',  # scripts go to copilot root
        'item_type': 'file',
        'pattern': '*.ps1',
        'exclude_dirs': [],
    },
}


def compare_directory_items(repo_dir, local_dir, key_file, exclude_dirs):
    """Compare directory-based items (personas, skills)."""
    results = {'new_in_repo': [], 'modified': [], 'local_only': [], 'identical': []}

    repo_path = Path(repo_dir)
    local_path = Path(local_dir)

    # Get repo items
    repo_items = set()
    if repo_path.exists():
        for d in repo_path.iterdir():
            if d.is_dir() and d.name not in exclude_dirs and (d / key_file).exists():
                repo_items.add(d.name)

    # Get local items
    local_items = set()
    if local_path.exists():
        for d in local_path.iterdir():
            if d.is_dir() and d.name not in exclude_dirs and (d / key_file).exists():
                local_items.add(d.name)

    # Categorize
    for name in repo_items - local_items:
        results['new_in_repo'].append(name)

    for name in local_items - repo_items:
        results['local_only'].append(name)

    for name in repo_items & local_items:
        repo_item_dir = repo_path / name
        local_item_dir = local_path / name

        repo_files = get_dir_files(repo_item_dir)
        local_files = get_dir_files(local_item_dir)

        is_identical = True

        # Check all repo files exist locally and match
        for rel, repo_file in repo_files.items():
            local_file = local_item_dir / rel
            if not local_file.exists():
                is_identical = False
                break
            if not files_are_identical(repo_file, str(local_file)):
                is_identical = False
                break

        # Check for local-only files
        if is_identical:
            for rel in local_files:
                if rel not in repo_files:
                    is_identical = False
                    break

        if is_identical:
            results['identical'].append(name)
        else:
            # Find which files differ
            changed_files = []
            for rel, repo_file in repo_files.items():
                local_file = local_item_dir / rel
                if not local_file.exists():
                    changed_files.append({'file': rel, 'status': 'new_in_repo'})
                elif not files_are_identical(repo_file, str(local_file)):
                    changed_files.append({'file': rel, 'status': 'modified'})
            for rel in local_files:
                if rel not in repo_files:
                    changed_files.append({'file': rel, 'status': 'local_only'})

            results['modified'].append({'name': name, 'changed_files': changed_files})

    return results


def compare_file_items(repo_dir, local_dir, pattern):
    """Compare file-based items (agents, scripts)."""
    results = {'new_in_repo': [], 'modified': [], 'local_only': [], 'identical': []}

    repo_path = Path(repo_dir)
    local_path = Path(local_dir)

    repo_files = set()
    if repo_path.exists():
        repo_files = {f.name for f in repo_path.glob(pattern)}

    local_files = set()
    if local_path.exists():
        local_files = {f.name for f in local_path.glob(pattern)}

    for name in repo_files - local_files:
        results['new_in_repo'].append(name)

    for name in local_files - repo_files:
        results['local_only'].append(name)

    for name in repo_files & local_files:
        repo_file = repo_path / name
        local_file = local_path / name
        if files_are_identical(str(repo_file), str(local_file)):
            results['identical'].append(name)
        else:
            results['modified'].append(name)

    return results


def run_comparison(repo_path, copilot_dir, categories=None):
    """Run full comparison across all categories."""
    if categories is None:
        categories = list(CATEGORIES.keys())

    all_results = {}

    for cat_name in categories:
        if cat_name not in CATEGORIES:
            continue

        cat = CATEGORIES[cat_name]
        repo_dir = os.path.join(repo_path, cat['repo_subdir'])
        local_dir = os.path.join(copilot_dir, cat['local_subdir']) if cat['local_subdir'] else copilot_dir

        if cat['item_type'] == 'directory':
            results = compare_directory_items(
                repo_dir, local_dir,
                cat['key_file'],
                cat.get('exclude_dirs', [])
            )
        else:
            results = compare_file_items(
                repo_dir, local_dir,
                cat['pattern']
            )

        all_results[cat_name] = results

    return all_results


def print_summary(results):
    """Print human-readable summary."""
    print("\n📊 Config Sync — Comparison Results")
    print("━" * 40)

    total_new = 0
    total_modified = 0
    total_local = 0
    total_identical = 0

    for cat_name, cat_results in results.items():
        new_count = len(cat_results['new_in_repo'])
        mod_count = len(cat_results['modified'])
        local_count = len(cat_results['local_only'])
        ident_count = len(cat_results['identical'])

        total_new += new_count
        total_modified += mod_count
        total_local += local_count
        total_identical += ident_count

        print(f"\n📁 {cat_name.title()}")

        if new_count:
            for item in cat_results['new_in_repo']:
                name = item if isinstance(item, str) else item['name']
                print(f"   🆕 {name} (new in repo)")

        if mod_count:
            for item in cat_results['modified']:
                if isinstance(item, dict):
                    name = item['name']
                    changed = ', '.join(f['file'] for f in item.get('changed_files', [])[:3])
                    print(f"   ⚠️  {name} (differs: {changed})")
                else:
                    print(f"   ⚠️  {item} (differs from local)")

        if local_count:
            for item in cat_results['local_only']:
                print(f"   📁 {item} (local only)")

        if ident_count:
            print(f"   ✅ {ident_count} identical")

    print(f"\n{'━' * 40}")
    print(f"Total: {total_new} new, {total_modified} modified, {total_local} local-only, {total_identical} identical")


def show_diff(repo_path, copilot_dir, category, item_name):
    """Show detailed diff for a specific item."""
    if category not in CATEGORIES:
        print(f"Unknown category: {category}")
        return

    cat = CATEGORIES[category]
    repo_dir = os.path.join(repo_path, cat['repo_subdir'])
    local_dir = os.path.join(copilot_dir, cat['local_subdir']) if cat['local_subdir'] else copilot_dir

    if cat['item_type'] == 'directory':
        repo_item = os.path.join(repo_dir, item_name)
        local_item = os.path.join(local_dir, item_name)

        if not os.path.exists(local_item):
            print(f"\n🆕 {item_name} (new — doesn't exist locally)")
            key_file = os.path.join(repo_item, cat['key_file'])
            if os.path.exists(key_file):
                print(f"\n--- {cat['key_file']} ---")
                with open(key_file, 'r', encoding='utf-8', errors='replace') as f:
                    for line in f:
                        print(f"  + {line.rstrip()}")
            return

        # Show per-file diffs
        repo_dir_n = repo_item.rstrip(os.sep) + os.sep
        local_dir_n = local_item.rstrip(os.sep) + os.sep

        repo_files = get_dir_files(repo_item)
        local_files = get_dir_files(local_item)

        has_diff = False
        for rel, repo_file in repo_files.items():
            local_file = os.path.join(local_item, rel)
            if not os.path.exists(local_file):
                print(f"\n  + {rel} (new in repo)")
                has_diff = True
            elif not files_are_identical(repo_file, local_file):
                print(f"\n  ~ {rel} (differs)")
                _show_file_diff(repo_file, local_file)
                has_diff = True

        for rel in local_files:
            if rel not in repo_files:
                print(f"\n  - {rel} (local only)")
                has_diff = True

        if not has_diff:
            print(f"\n  ✅ {item_name} — files are identical")

    else:
        repo_file = os.path.join(repo_dir, item_name)
        local_file = os.path.join(local_dir, item_name)

        if not os.path.exists(local_file):
            print(f"\n🆕 {item_name} (new)")
            with open(repo_file, 'r', encoding='utf-8', errors='replace') as f:
                for line in f.readlines()[:30]:
                    print(f"  + {line.rstrip()}")
            return

        _show_file_diff(repo_file, local_file)


def _show_file_diff(repo_file, local_file):
    """Show line-by-line diff between two files."""
    try:
        with open(repo_file, 'r', encoding='utf-8', errors='replace') as f:
            repo_lines = [l.rstrip('\r\n') for l in f.readlines()]
        with open(local_file, 'r', encoding='utf-8', errors='replace') as f:
            local_lines = [l.rstrip('\r\n') for l in f.readlines()]

        import difflib
        diff = list(difflib.unified_diff(local_lines, repo_lines, lineterm='', n=2))
        if not diff:
            print("    (identical content — differences are whitespace/line-endings only)")
            return

        for line in diff[:40]:
            if line.startswith('+') and not line.startswith('+++'):
                print(f"    {line}")
            elif line.startswith('-') and not line.startswith('---'):
                print(f"    {line}")
            elif line.startswith('@@'):
                print(f"    {line}")
        if len(diff) > 40:
            print(f"    ... ({len(diff) - 40} more lines)")
    except Exception as e:
        print(f"    (cannot diff: {e})")


def main():
    parser = argparse.ArgumentParser(description='Compare local Copilot CLI config against repo')
    parser.add_argument('repo_path', help='Path to copilot-cli-config repo')
    parser.add_argument('--copilot-dir', default=os.path.expanduser('~/.copilot'),
                        help='Path to local ~/.copilot/ (default: ~/.copilot)')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--categories', default=None,
                        help='Comma-separated list of categories to compare')
    parser.add_argument('--diff', nargs=2, metavar=('CATEGORY', 'ITEM'),
                        help='Show detailed diff for a specific item (e.g., --diff skills research)')

    args = parser.parse_args()

    if args.diff:
        show_diff(args.repo_path, args.copilot_dir, args.diff[0], args.diff[1])
    else:
        categories = args.categories.split(',') if args.categories else None
        results = run_comparison(args.repo_path, args.copilot_dir, categories)

        if args.json:
            print(json.dumps(results, indent=2, default=str))
        else:
            print_summary(results)


if __name__ == '__main__':
    main()
