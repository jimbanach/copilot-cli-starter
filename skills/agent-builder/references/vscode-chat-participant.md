# VS Code Chat Participant Reference

## Overview

VS Code Chat Participants are extensions that add specialized `@mention` assistants to GitHub Copilot Chat in VS Code. Users invoke them by typing `@participant-name` in the chat input. The participant owns the full conversation — receiving the user's prompt and returning a response.

## Architecture

```
User types: @my-agent explain this code
         |
         v
VS Code Chat UI --> Chat Participant Extension
                         |
                         +--> Request Handler (TypeScript)
                         |      |
                         |      +--> Language Model API (optional)
                         |      +--> VS Code Extension APIs
                         |      +--> External Services / MCP
                         |
                         +--> Response Stream (markdown, code, buttons)
```

## When to Use Chat Participants vs Other Options

| Approach | Best For | Distribution |
|----------|----------|-------------|
| **Chat Participant** | Domain-specific expertise that owns the conversation | VS Code Marketplace |
| **Language Model Tool** | Capabilities invoked automatically by Copilot during agentic sessions | VS Code Marketplace |
| **MCP Server** | External tool integration usable by any client | Standalone server |
| **Copilot CLI Agent** | Quick, file-based agents for personal/team use | `.agent.md` file |

Chat Participants are best when you want:
- Deep VS Code integration (debug context, workspace APIs, etc.)
- Distribution via the Marketplace
- Custom UI elements (buttons, follow-ups, progress indicators)
- Slash commands for quick-access features

## Project Structure

```
my-chat-participant/
  ├── package.json           # Extension manifest + chat participant registration
  ├── tsconfig.json          # TypeScript configuration
  ├── src/
  │   └── extension.ts       # Main extension code with request handler
  ├── .vscode/
  │   └── launch.json        # Debug configuration
  ├── .vscodeignore           # Files to exclude from package
  └── README.md              # Extension documentation
```

## package.json Schema

The `chatParticipants` contribution point registers the participant:

```json
{
  "name": "my-chat-participant",
  "displayName": "My Chat Participant",
  "description": "A chat participant that does X",
  "version": "0.0.1",
  "engines": {
    "vscode": "^1.93.0"
  },
  "categories": ["AI", "Chat"],
  "activationEvents": [],
  "main": "./out/extension.js",
  "contributes": {
    "chatParticipants": [
      {
        "id": "my-extension.my-participant",
        "name": "my-participant",
        "fullName": "My Participant",
        "description": "What can I help you with?",
        "isSticky": true,
        "commands": [
          {
            "name": "analyze",
            "description": "Analyze code for patterns"
          },
          {
            "name": "generate",
            "description": "Generate boilerplate code"
          }
        ]
      }
    ]
  },
  "dependencies": {
    "@types/vscode": "^1.93.0"
  },
  "devDependencies": {
    "typescript": "^5.4.0",
    "@vscode/vsce": "^3.0.0"
  },
  "scripts": {
    "compile": "tsc -p ./",
    "watch": "tsc -watch -p ./",
    "package": "vsce package"
  }
}
```

### Key Fields

| Field | Description |
|-------|-------------|
| `id` | Unique identifier: `<publisher>.<participant-name>` |
| `name` | Short name used for @-mention (lowercase recommended) |
| `fullName` | Display name shown in response header (Title Case) |
| `description` | Placeholder text in chat input when participant is active |
| `isSticky` | If `true`, participant stays selected after responding |
| `commands` | Array of slash commands (name + description) |

## Request Handler Pattern

```typescript
import * as vscode from 'vscode';

interface IParticipantResult extends vscode.ChatResult {
  metadata: {
    command?: string;
  };
}

export function activate(context: vscode.ExtensionContext) {
  const participant = vscode.chat.createChatParticipant(
    'my-extension.my-participant',
    handler
  );

  participant.iconPath = vscode.Uri.joinPath(
    context.extensionUri,
    'icon.png'
  );

  // Register follow-up provider
  participant.followupProvider = {
    provideFollowups(
      result: IParticipantResult,
      context: vscode.ChatContext,
      token: vscode.CancellationToken
    ) {
      return [
        {
          prompt: 'Tell me more',
          label: 'Learn more about this topic',
        },
      ];
    },
  };

  context.subscriptions.push(participant);
}

const handler: vscode.ChatRequestHandler = async (
  request: vscode.ChatRequest,
  context: vscode.ChatContext,
  stream: vscode.ChatResponseStream,
  token: vscode.CancellationToken
): Promise<IParticipantResult> => {
  // Handle slash commands
  if (request.command === 'analyze') {
    return handleAnalyze(request, context, stream, token);
  }

  if (request.command === 'generate') {
    return handleGenerate(request, context, stream, token);
  }

  // Default: handle free-form prompts
  return handleDefault(request, context, stream, token);
};

async function handleDefault(
  request: vscode.ChatRequest,
  context: vscode.ChatContext,
  stream: vscode.ChatResponseStream,
  token: vscode.CancellationToken
): Promise<IParticipantResult> {
  // Show progress
  stream.progress('Thinking...');

  // Use the language model
  const messages = [
    vscode.LanguageModelChatMessage.User(
      `You are an expert assistant. ${request.prompt}`
    ),
  ];

  const response = await request.model.sendRequest(messages, {}, token);

  // Stream the response
  for await (const fragment of response.text) {
    stream.markdown(fragment);
  }

  return { metadata: {} };
}

async function handleAnalyze(
  request: vscode.ChatRequest,
  context: vscode.ChatContext,
  stream: vscode.ChatResponseStream,
  token: vscode.CancellationToken
): Promise<IParticipantResult> {
  stream.progress('Analyzing...');

  // Example: use VS Code APIs to get workspace context
  const files = await vscode.workspace.findFiles('**/*.ts', '**/node_modules/**');

  stream.markdown(`Found **${files.length}** TypeScript files.\n\n`);

  // Process with LLM
  const messages = [
    vscode.LanguageModelChatMessage.User(
      `Analyze the following code context: ${request.prompt}`
    ),
  ];

  const response = await request.model.sendRequest(messages, {}, token);
  for await (const fragment of response.text) {
    stream.markdown(fragment);
  }

  return { metadata: { command: 'analyze' } };
}

async function handleGenerate(
  request: vscode.ChatRequest,
  context: vscode.ChatContext,
  stream: vscode.ChatResponseStream,
  token: vscode.CancellationToken
): Promise<IParticipantResult> {
  stream.progress('Generating...');

  // Example: add a button to the response
  stream.markdown('Here is your generated code:\n\n');
  stream.markdown('```typescript\nconsole.log("Hello!");\n```\n');

  stream.button({
    command: 'workbench.action.files.newUntitledFile',
    title: 'Open in New File',
    arguments: [],
  });

  return { metadata: { command: 'generate' } };
}

export function deactivate() {}
```

## Response Stream API

The `ChatResponseStream` supports these output types:

| Method | Description | Example |
|--------|-------------|---------|
| `stream.markdown(str)` | Markdown text (supports code blocks, links, etc.) | `stream.markdown('**Bold** text')` |
| `stream.progress(str)` | Progress indicator message | `stream.progress('Analyzing files...')` |
| `stream.button(cmd)` | Clickable button that invokes a VS Code command | See example above |
| `stream.reference(uri)` | Link to a file or resource | `stream.reference(fileUri)` |
| `stream.filetree(tree, uri)` | File tree visualization | Complex file structures |
| `stream.anchor(uri, title)` | Clickable link | `stream.anchor(uri, 'See docs')` |

## Participant Detection (Auto-routing)

VS Code can automatically route prompts to your participant based on descriptions and examples in `package.json`:

```json
"chatParticipants": [{
  "id": "my-extension.my-participant",
  "name": "my-participant",
  "disambiguation": [
    {
      "category": "code_analysis",
      "description": "The user wants to analyze code for patterns, complexity, or quality issues",
      "examples": [
        "Analyze this function for complexity",
        "Find code smells in this file",
        "What patterns does this codebase use?"
      ]
    }
  ]
}]
```

## Chat History Access

Access previous messages in the conversation:

```typescript
const handler: vscode.ChatRequestHandler = async (request, context, stream, token) => {
  // context.history contains previous turns
  const previousMessages = context.history;

  for (const turn of previousMessages) {
    if (turn instanceof vscode.ChatRequestTurn) {
      // User message
      console.log('User said:', turn.prompt);
    } else if (turn instanceof vscode.ChatResponseTurn) {
      // Assistant response
      console.log('Response from:', turn.participant);
    }
  }
};
```

## Publishing

1. **Package**: `npx @vscode/vsce package` creates a `.vsix` file
2. **Test locally**: `code --install-extension my-extension-0.0.1.vsix`
3. **Publish to Marketplace**: `npx @vscode/vsce publish` (requires publisher account)

## Naming Conventions

- **Participant name**: lowercase, no spaces (e.g., `terraform`, `docs-helper`)
- **Full name**: Title Case (e.g., `Terraform Reviewer`, `Docs Helper`)
- **Extension name**: kebab-case (e.g., `my-terraform-reviewer`)
- Some participant names are reserved by VS Code — if reserved, the fully qualified name (`extensionId.participantName`) is used

## Getting Started Resources

- [VS Code Chat Participant API Guide](https://code.visualstudio.com/api/extension-guides/chat)
- [Chat Sample Extension](https://github.com/microsoft/vscode-extension-samples/tree/main/chat-sample)
- [VS Code Extension API Reference](https://code.visualstudio.com/api/references/vscode-api#chat)
- [Language Model API](https://code.visualstudio.com/api/extension-guides/ai/language-model)
