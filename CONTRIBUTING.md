# Contributing to Copilot CLI Starter

Thank you for improving this template! Your contributions help everyone who uses it.

## How to Contribute

### 1. Fork & Clone

If you haven't already:

<details>
<summary><b>GitHub CLI</b></summary>

```powershell
gh repo fork jimbanach/copilot-cli-starter --clone=true
cd copilot-cli-starter
```
</details>

<details>
<summary><b>VS Code</b></summary>

1. Open the Command Palette (`Ctrl+Shift+P`)
2. Run **Git: Clone**
3. Paste: `https://github.com/jimbanach/copilot-cli-starter.git`
4. Choose a local folder
5. Fork via GitHub web first (see below), then update your remote

</details>

<details>
<summary><b>GitHub Web</b></summary>

1. Go to https://github.com/jimbanach/copilot-cli-starter
2. Click **Fork** (top right)
3. Clone your fork:
   ```powershell
   git clone https://github.com/YOUR_USERNAME/copilot-cli-starter.git
   cd copilot-cli-starter
   ```
</details>

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

<details>
<summary><b>GitHub CLI / Terminal</b></summary>

```powershell
git add -A
git commit -m "Add [what you changed] — [why]"
git push origin main
```
</details>

<details>
<summary><b>VS Code</b></summary>

1. Open the **Source Control** panel (`Ctrl+Shift+G`)
2. Stage your changes (click `+` next to each file)
3. Type a commit message: `Add [what you changed] — [why]`
4. Click **Commit**, then **Sync Changes**

</details>

### 5. Submit a Pull Request

<details>
<summary><b>GitHub CLI</b></summary>

```powershell
gh pr create --repo jimbanach/copilot-cli-starter --title "Your improvement title" --body "Description of what you changed and why"
```
</details>

<details>
<summary><b>VS Code</b></summary>

1. Install the **GitHub Pull Requests** extension if not already
2. Open the Command Palette (`Ctrl+Shift+P`)
3. Run **GitHub Pull Requests: Create Pull Request**
4. Fill in the title and description

</details>

<details>
<summary><b>GitHub Web</b></summary>

1. Go to your fork: `https://github.com/YOUR_USERNAME/copilot-cli-starter`
2. Click **Contribute** → **Open pull request**
3. Fill in the title and description
4. Click **Create pull request**

</details>

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
