#!/usr/bin/env python3
"""
Agent Initializer - Scaffolds a new agent (CLI or VS Code Chat Participant)

Usage:
    init_agent.py cli <agent-name> --path <path> [--tools <tools>] [--description <desc>]
    init_agent.py vscode <agent-name> --path <path> [--publisher <publisher>]

Examples:
    init_agent.py cli terraform-reviewer --path ~/.copilot/agents --tools "read,search" --description "Reviews Terraform configs"
    init_agent.py vscode docs-helper --path ~/projects --publisher my-publisher
"""

import sys
import json
import os
from pathlib import Path
from datetime import datetime


def create_cli_agent(name: str, path: str, tools: str = "read,search", description: str = "") -> Path:
    """Create a Copilot CLI .agent.md file."""
    agent_dir = Path(path).expanduser().resolve()
    agent_dir.mkdir(parents=True, exist_ok=True)

    agent_file = agent_dir / f"{name}.agent.md"
    if agent_file.exists():
        print(f"Error: Agent file already exists: {agent_file}")
        return None

    tool_list = [t.strip() for t in tools.split(",")]
    tools_yaml = "[" + ", ".join(tool_list) + "]"

    title = " ".join(word.capitalize() for word in name.split("-"))
    desc = description or f"{title} - [TODO: Add description]"

    content = f"""---
description: '{desc}'
tools: {tools_yaml}
---

# {title}

## Role
You are a [TODO: describe role]. You [TODO: describe primary capability].

**Core principle:** [TODO: Add the agent's guiding principle]

---

## Workflow

1. **[Step 1]** - [TODO: What happens first]
2. **[Step 2]** - [TODO: What happens next]
3. **[Step 3]** - [TODO: Final step]

---

## Output Format

[TODO: Define expected output structure]

---

## Rules
- [TODO: Add guardrails]
- [TODO: Define boundaries]

---

## Initial Response

When activated, say:

*"I'm the {title}. [TODO: Brief intro and ask what the user wants to do]"*
"""

    agent_file.write_text(content, encoding="utf-8")
    print(f"Created CLI agent: {agent_file}")
    return agent_file


def create_vscode_participant(name: str, path: str, publisher: str = "my-publisher") -> Path:
    """Create a VS Code Chat Participant extension scaffold."""
    project_dir = Path(path).expanduser().resolve() / name
    if project_dir.exists():
        print(f"Error: Directory already exists: {project_dir}")
        return None

    title = " ".join(word.capitalize() for word in name.split("-"))
    participant_id = f"{publisher}.{name}"

    # Create directories
    (project_dir / "src").mkdir(parents=True)
    (project_dir / ".vscode").mkdir(parents=True)

    # package.json
    package = {
        "name": name,
        "displayName": title,
        "description": f"A VS Code Chat Participant: {title}",
        "version": "0.0.1",
        "publisher": publisher,
        "engines": {"vscode": "^1.93.0"},
        "categories": ["AI", "Chat"],
        "activationEvents": [],
        "main": "./out/extension.js",
        "contributes": {
            "chatParticipants": [
                {
                    "id": participant_id,
                    "name": name,
                    "fullName": title,
                    "description": f"What can {title} help you with?",
                    "isSticky": True,
                    "commands": [
                        {"name": "help", "description": f"Get help using {title}"}
                    ],
                }
            ]
        },
        "scripts": {
            "compile": "tsc -p ./",
            "watch": "tsc -watch -p ./",
            "package": "npx @vscode/vsce package",
        },
        "devDependencies": {
            "@types/vscode": "^1.93.0",
            "typescript": "^5.4.0",
            "@vscode/vsce": "^3.0.0",
        },
    }
    (project_dir / "package.json").write_text(
        json.dumps(package, indent=2), encoding="utf-8"
    )

    # tsconfig.json
    tsconfig = {
        "compilerOptions": {
            "module": "commonjs",
            "target": "ES2022",
            "lib": ["ES2022"],
            "outDir": "out",
            "rootDir": "src",
            "sourceMap": True,
            "strict": True,
            "esModuleInterop": True,
        },
        "exclude": ["node_modules", ".vscode-test"],
    }
    (project_dir / "tsconfig.json").write_text(
        json.dumps(tsconfig, indent=2), encoding="utf-8"
    )

    # .vscode/launch.json
    launch = {
        "version": "0.2.0",
        "configurations": [
            {
                "name": "Run Extension",
                "type": "extensionHost",
                "request": "launch",
                "args": ["--extensionDevelopmentPath=${workspaceFolder}"],
                "outFiles": ["${workspaceFolder}/out/**/*.js"],
                "preLaunchTask": "${defaultBuildTask}",
            }
        ],
    }
    (project_dir / ".vscode" / "launch.json").write_text(
        json.dumps(launch, indent=2), encoding="utf-8"
    )

    # src/extension.ts
    extension_ts = f"""import * as vscode from 'vscode';

interface IParticipantResult extends vscode.ChatResult {{
  metadata: {{
    command?: string;
  }};
}}

export function activate(context: vscode.ExtensionContext) {{
  const participant = vscode.chat.createChatParticipant(
    '{participant_id}',
    handler
  );

  participant.iconPath = vscode.Uri.joinPath(context.extensionUri, 'icon.png');

  participant.followupProvider = {{
    provideFollowups(
      result: IParticipantResult,
      _context: vscode.ChatContext,
      _token: vscode.CancellationToken
    ) {{
      return [
        {{ prompt: 'What else can you do?', label: 'See more capabilities' }},
      ];
    }},
  }};

  context.subscriptions.push(participant);
}}

const handler: vscode.ChatRequestHandler = async (
  request: vscode.ChatRequest,
  context: vscode.ChatContext,
  stream: vscode.ChatResponseStream,
  token: vscode.CancellationToken
): Promise<IParticipantResult> => {{
  // Handle slash commands
  if (request.command === 'help') {{
    stream.markdown('# {title}\\n\\n');
    stream.markdown('Available commands:\\n');
    stream.markdown('- `/help` - Show this help message\\n');
    stream.markdown('\\nOr just ask me anything!\\n');
    return {{ metadata: {{ command: 'help' }} }};
  }}

  // Default: handle free-form prompts
  stream.progress('Thinking...');

  const messages = [
    vscode.LanguageModelChatMessage.User(
      // TODO: Customize the system prompt for your participant
      `You are {title}, a helpful assistant. ${{request.prompt}}`
    ),
  ];

  const response = await request.model.sendRequest(messages, {{}}, token);

  for await (const fragment of response.text) {{
    stream.markdown(fragment);
  }}

  return {{ metadata: {{}} }};
}};

export function deactivate() {{}}
"""
    (project_dir / "src" / "extension.ts").write_text(extension_ts, encoding="utf-8")

    # .vscodeignore
    vscodeignore = """
.vscode/**
.vscode-test/**
src/**
**/*.ts
**/*.map
node_modules/**
tsconfig.json
""".strip()
    (project_dir / ".vscodeignore").write_text(vscodeignore, encoding="utf-8")

    # README.md
    readme = f"""# {title}

A VS Code Chat Participant extension.

## Usage

Type `@{name}` in GitHub Copilot Chat to invoke this participant.

### Available Commands
- `@{name} /help` - Show help

## Development

```bash
npm install
npm run compile
```

Press F5 in VS Code to launch the Extension Development Host.

## Packaging

```bash
npm run package
```
"""
    (project_dir / "README.md").write_text(readme, encoding="utf-8")

    print(f"Created VS Code Chat Participant: {project_dir}")
    return project_dir


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)

    agent_type = sys.argv[1]
    agent_name = sys.argv[2]

    # Parse remaining args
    args = sys.argv[3:]
    params = {}
    i = 0
    while i < len(args):
        if args[i].startswith("--") and i + 1 < len(args):
            params[args[i][2:]] = args[i + 1]
            i += 2
        else:
            i += 1

    if "path" not in params:
        print("Error: --path is required")
        sys.exit(1)

    if agent_type == "cli":
        result = create_cli_agent(
            agent_name,
            params["path"],
            tools=params.get("tools", "read,search"),
            description=params.get("description", ""),
        )
    elif agent_type == "vscode":
        result = create_vscode_participant(
            agent_name,
            params["path"],
            publisher=params.get("publisher", "my-publisher"),
        )
    else:
        print(f"Error: Unknown agent type '{agent_type}'. Use 'cli' or 'vscode'.")
        sys.exit(1)

    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
