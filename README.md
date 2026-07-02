# Enchan CLI

Enchan CLI is a local terminal chat interface for Enchan-backed and Ollama-backed GGUF runtimes.

This repository contains the CLI source and installer scripts. Native Enchan Llama runtime binaries are distributed from the private `EnchanTheory/Enchan-Llama` GitHub Release and installed into `backend/bin/<platform>/`.

## Prerequisites

Because the repositories are private, install requires an authenticated GitHub CLI session.

```bash
gh auth login
```

Required commands:

- GitHub CLI: `gh`
- Git: `git`
- Node.js/npm: `node`, `npm`
- Python: `python` on Windows or `python3` on macOS, or set `ENCHAN_PYTHON`

## One-Command Install

### Windows PowerShell

```powershell
gh repo clone EnchanTheory/Enchan-CLI "$env:USERPROFILE\.enchan"; cd "$env:USERPROFILE\.enchan"; .\install.ps1
```

The installer downloads `enchan-llama-win-x64.zip` from `EnchanTheory/Enchan-Llama` release `v0.1.0`, extracts it to `backend/bin/win-x64/`, and registers the `enchan` command with `npm link`.

### Apple Silicon macOS

```bash
gh repo clone EnchanTheory/Enchan-CLI ~/.enchan && cd ~/.enchan && chmod +x ./install.sh && ./install.sh
```

The installer downloads `enchan-llama-macos-arm64.zip` from `EnchanTheory/Enchan-Llama` release `v0.1.0`, extracts it to `backend/bin/macos-arm64/`, marks runtime executables executable, and registers the `enchan` command with `npm link`.

## Update

After installation, update the checkout and refresh the linked command with:

```bash
enchan update
```

This runs `git pull --ff-only` in the install directory, then reruns the platform installer. Normal `enchan` startup checks for updates in the background and prints a short notice when a newer commit is available.

The installer keeps Python dependencies in a local `.venv`, recreates that environment when `requirements.txt` changes, and tracks native runtime files with a manifest so obsolete runtime files can be pruned when the runtime asset changes.

If the installed command is older and does not yet support `enchan update`, update once manually from the install directory:

```powershell
cd "$env:USERPROFILE\.enchan"
git pull --ff-only
.\install.ps1
```

```bash
cd ~/.enchan
git pull --ff-only
./install.sh
```

## Runtime Assets

Runtime assets are published in the private Enchan Llama release:

- Repo: `EnchanTheory/Enchan-Llama`
- Tag: `v0.1.0`
- Windows asset: `enchan-llama-win-x64.zip`
- macOS asset: `enchan-llama-macos-arm64.zip`

Expected runtime layout after install:

```text
backend/bin/win-x64/llama-server.exe
backend/bin/win-x64/enchan.dll
backend/bin/macos-arm64/llama-server
backend/bin/macos-arm64/libenchan.dylib
```

## Usage

Start the interactive CLI:

```bash
enchan
```

Select a backend at startup:

```bash
enchan
```

One-shot mode:

```bash
enchan --ask "Summarize this repository" --plain
```

## Python Selection

The `enchan` command is a Node.js launcher for the Python backend.

Set `ENCHAN_PYTHON` to force a specific Python executable:

```powershell
$env:ENCHAN_PYTHON = "C:\path\to\python.exe"
enchan
```

```bash
export ENCHAN_PYTHON=/opt/homebrew/bin/python3
enchan
```

If `ENCHAN_PYTHON` is not set, the launcher uses `python` on Windows and `python3` on macOS/Linux.

## Commands

Inside the interactive CLI:

- `/help`: show commands
- `/status`: show current backend/model/session status
- `/model`: select local model
- `/resume`: resume a prior session log
- `/clear`: clear current chat context
- `/exit`: exit cleanly
- `enchan update`: update the installed checkout and refresh the command

## Repository Scope

This repository intentionally excludes:

- native runtime build trees
- generated logs
- local/private memory contents
- development-only docs and tools
- machine-specific virtual environment paths
