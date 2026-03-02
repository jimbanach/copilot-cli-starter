# Contributing to Copilot CLI Starter

Thank you for improving this template! Your contributions help everyone who uses it.

## How to Contribute

### 1. Fork & Clone

If you haven't already:
```powershell
gh repo fork jimbanach/copilot-cli-starter --clone=true
cd copilot-cli-starter
```

### 2. Make Your Improvement

Common contributions:
- **New persona** — add a directory under `personas/` with an `AGENTS.md`
- **Improved persona** — edit an existing `personas/*/AGENTS.md`
- **New skill** — add a directory under `skills/` with a `SKILL.md`
- **Bug fix** — fix an issue in a script, skill, or agent
- **Documentation** — improve README, add examples, clarify instructions

### 3. Test Your Change

Before submitting:
- Run `.\init.ps1` to deploy your changes locally
- Launch Copilot CLI and verify the change works as expected
- If you modified a persona, switch to it and test
- If you modified a skill, trigger it and verify behavior

### 4. Commit with a Clear Message

```powershell
git add -A
git commit -m "Add [what you changed] — [why]"
git push origin main
```

### 5. Submit a Pull Request

```powershell
gh pr create --repo jimbanach/copilot-cli-starter --title "Your improvement title" --body "Description of what you changed and why"
```

Or create the PR on GitHub at: https://github.com/jimbanach/copilot-cli-starter/compare

## What Makes a Good Contribution

- **Solves a real problem** — something you ran into while using the template
- **Stays generic** — avoid adding content specific to your role or projects; keep it useful for everyone
- **Doesn't break existing setup** — test that init.ps1 still works after your change
- **Includes context** — your PR description explains what changed and why

## What NOT to Contribute

- Personal voice profiles (these are unique to each user)
- Instance-specific rules (work paths, account names)
- Confidential or NDA content
- Large binary files

## Review Process

1. You submit a PR to `jimbanach/copilot-cli-starter`
2. The maintainer reviews your change
3. If approved, it's merged into `main`
4. All peers benefit on their next `check for starter updates`

## Questions?

Open an issue at https://github.com/jimbanach/copilot-cli-starter/issues
