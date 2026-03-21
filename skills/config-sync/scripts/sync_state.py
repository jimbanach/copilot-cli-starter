"""
sync_state.py — Manages sync-state.json for tracking sync operations.

Provides functions to read, update, and query the sync state file.
The sync state tracks last pull/push timestamps, skipped items, and per-file status.

Usage:
    python sync_state.py <command> [options]

Commands:
    init        Create a new sync-state.json
    status      Show current sync state
    record-pull Record a pull operation timestamp
    record-push Record a push operation timestamp
    skip        Record a skipped item with reason
    unskip      Remove a skip decision (will be re-evaluated next sync)
    list-skips  Show all skipped items
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_SYNC_DIR = os.path.join(os.path.expanduser('~'), '.copilot', '.copilot-sync')
DEFAULT_STATE_FILE = os.path.join(DEFAULT_SYNC_DIR, 'sync-state.json')


def get_empty_state(instance='unknown', repo_path=''):
    """Return a new empty sync state."""
    return {
        'instance': instance,
        'repo_path': repo_path,
        'last_pull': None,
        'last_push': None,
        'last_publish': None,
        'skipped_items': [],
        'migrations_applied': [],
        'history': [],
    }


def load_state(state_file=None):
    """Load sync state from file, or return empty state if not found."""
    if state_file is None:
        state_file = DEFAULT_STATE_FILE

    if os.path.exists(state_file):
        with open(state_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    return get_empty_state()


def save_state(state, state_file=None):
    """Save sync state to file."""
    if state_file is None:
        state_file = DEFAULT_STATE_FILE

    os.makedirs(os.path.dirname(state_file), exist_ok=True)

    with open(state_file, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, default=str)


def now_iso():
    """Return current time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def record_pull(state):
    """Record a pull operation."""
    state['last_pull'] = now_iso()
    state['history'].append({
        'action': 'pull',
        'timestamp': state['last_pull'],
    })
    # Keep only last 50 history entries
    state['history'] = state['history'][-50:]
    return state


def record_push(state, files_pushed=None):
    """Record a push operation."""
    state['last_push'] = now_iso()
    entry = {
        'action': 'push',
        'timestamp': state['last_push'],
    }
    if files_pushed:
        entry['files'] = files_pushed
    state['history'].append(entry)
    state['history'] = state['history'][-50:]
    return state


def record_publish(state, target_repo=None):
    """Record a template publish operation."""
    state['last_publish'] = now_iso()
    entry = {
        'action': 'publish',
        'timestamp': state['last_publish'],
    }
    if target_repo:
        entry['target'] = target_repo
    state['history'].append(entry)
    state['history'] = state['history'][-50:]
    return state


def add_skip(state, path, reason=''):
    """Add a skipped item."""
    # Remove existing skip for this path if present
    state['skipped_items'] = [s for s in state['skipped_items'] if s['path'] != path]

    state['skipped_items'].append({
        'path': path,
        'reason': reason,
        'skipped_at': now_iso(),
    })
    return state


def remove_skip(state, path):
    """Remove a skip decision."""
    before = len(state['skipped_items'])
    state['skipped_items'] = [s for s in state['skipped_items'] if s['path'] != path]
    removed = before - len(state['skipped_items'])
    return state, removed


def is_skipped(state, path):
    """Check if an item is skipped."""
    return any(s['path'] == path for s in state['skipped_items'])


def record_migration(state, migration_id, description=''):
    """Record that a migration has been applied."""
    if 'migrations_applied' not in state:
        state['migrations_applied'] = []
    if not is_migration_applied(state, migration_id):
        state['migrations_applied'].append({
            'id': migration_id,
            'description': description,
            'applied_at': now_iso(),
        })
        state['history'].append({
            'action': 'migration',
            'migration_id': migration_id,
            'timestamp': now_iso(),
        })
        state['history'] = state['history'][-50:]
    return state


def is_migration_applied(state, migration_id):
    """Check if a migration has already been applied."""
    migrations = state.get('migrations_applied', [])
    return any(m['id'] == migration_id for m in migrations)


def print_status(state):
    """Print human-readable sync status."""
    print("\n📊 Sync State")
    print("━" * 35)
    print(f"   Instance:      {state.get('instance', 'unknown')}")
    print(f"   Repo:          {state.get('repo_path', 'not set')}")
    print(f"   Last pull:     {state.get('last_pull', 'never')}")
    print(f"   Last push:     {state.get('last_push', 'never')}")
    print(f"   Last publish:  {state.get('last_publish', 'never')}")

    skips = state.get('skipped_items', [])
    if skips:
        print(f"\n   ⏭️  Skipped items ({len(skips)}):")
        for s in skips:
            reason = f" — {s['reason']}" if s.get('reason') else ''
            print(f"      • {s['path']}{reason}")

    migrations = state.get('migrations_applied', [])
    if migrations:
        print(f"\n   🔄 Migrations applied ({len(migrations)}):")
        for m in migrations:
            desc = f" — {m['description']}" if m.get('description') else ''
            print(f"      • {m['id']}{desc} ({m.get('applied_at', '?')})")

    history = state.get('history', [])
    if history:
        print(f"\n   📜 Recent history (last 5):")
        for h in history[-5:]:
            action = h.get('action', '?')
            ts = h.get('timestamp', '?')
            files = h.get('files', [])
            extra = f" ({len(files)} files)" if files else ''
            print(f"      • {action}{extra} at {ts}")

    print()


def main():
    parser = argparse.ArgumentParser(description='Manage sync state')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # init
    init_parser = subparsers.add_parser('init', help='Create new sync state')
    init_parser.add_argument('--instance', default='work', help='Instance name')
    init_parser.add_argument('--repo-path', default='', help='Repo local path')

    # status
    subparsers.add_parser('status', help='Show sync state')

    # record-pull
    subparsers.add_parser('record-pull', help='Record a pull operation')

    # record-push
    push_parser = subparsers.add_parser('record-push', help='Record a push operation')
    push_parser.add_argument('--files', nargs='*', help='Files that were pushed')

    # skip
    skip_parser = subparsers.add_parser('skip', help='Skip an item')
    skip_parser.add_argument('path', help='Path of item to skip')
    skip_parser.add_argument('--reason', default='', help='Reason for skipping')

    # unskip
    unskip_parser = subparsers.add_parser('unskip', help='Remove a skip decision')
    unskip_parser.add_argument('path', help='Path of item to unskip')

    # list-skips
    subparsers.add_parser('list-skips', help='List all skipped items')

    # record-migration
    migrate_parser = subparsers.add_parser('record-migration', help='Record a migration')
    migrate_parser.add_argument('migration_id', help='Migration identifier')
    migrate_parser.add_argument('--description', default='', help='Migration description')

    # check-migration
    check_migrate_parser = subparsers.add_parser('check-migration', help='Check if migration applied')
    check_migrate_parser.add_argument('migration_id', help='Migration identifier')

    # Common options
    parser.add_argument('--state-file', default=None, help='Path to sync-state.json')
    parser.add_argument('--json', action='store_true', help='Output as JSON')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    state = load_state(args.state_file)

    if args.command == 'init':
        state = get_empty_state(args.instance, args.repo_path)
        save_state(state, args.state_file)
        print(f"✅ Sync state initialized for '{args.instance}'")

    elif args.command == 'status':
        if args.json:
            print(json.dumps(state, indent=2, default=str))
        else:
            print_status(state)

    elif args.command == 'record-pull':
        state = record_pull(state)
        save_state(state, args.state_file)
        print(f"✅ Pull recorded at {state['last_pull']}")

    elif args.command == 'record-push':
        state = record_push(state, args.files)
        save_state(state, args.state_file)
        print(f"✅ Push recorded at {state['last_push']}")

    elif args.command == 'skip':
        state = add_skip(state, args.path, args.reason)
        save_state(state, args.state_file)
        print(f"✅ Skipped: {args.path}")

    elif args.command == 'unskip':
        state, removed = remove_skip(state, args.path)
        save_state(state, args.state_file)
        if removed:
            print(f"✅ Removed skip for: {args.path}")
        else:
            print(f"⚠️  No skip found for: {args.path}")

    elif args.command == 'list-skips':
        skips = state.get('skipped_items', [])
        if skips:
            for s in skips:
                reason = f" — {s['reason']}" if s.get('reason') else ''
                print(f"   • {s['path']}{reason}")
        else:
            print("   No skipped items")

    elif args.command == 'record-migration':
        if is_migration_applied(state, args.migration_id):
            print(f"ℹ️  Migration '{args.migration_id}' already applied")
        else:
            state = record_migration(state, args.migration_id, args.description)
            save_state(state, args.state_file)
            print(f"✅ Migration recorded: {args.migration_id}")

    elif args.command == 'check-migration':
        if is_migration_applied(state, args.migration_id):
            print(f"✅ Migration '{args.migration_id}' has been applied")
            sys.exit(0)
        else:
            print(f"⚠️  Migration '{args.migration_id}' has NOT been applied")
            sys.exit(1)


if __name__ == '__main__':
    main()
