# Enchan CLI

Enchan CLI is a local terminal chat interface for Enchan-backed and Ollama-backed GGUF runtimes.

This repository contains the CLI source and installer scripts. Native runtime binaries are distributed from this repository's GitHub Release and installed into `backend/bin/<platform>/`.

## Prerequisites

Required commands:

- Git: `git`
- Node.js/npm: `node`, `npm`
- Python: `python` on Windows or `python3` on macOS, or set `ENCHAN_PYTHON`
- macOS: `curl`, `unzip`, and Xcode Command Line Tools for runtime library inspection

## One-Command Install

### Windows PowerShell

```powershell
powershell -ExecutionPolicy Bypass -c "irm https://github.com/EnchanTheory/Enchan-CLI/raw/main/bootstrap/install.ps1 | iex"
```

### Apple Silicon macOS

```bash
curl -fsSL https://github.com/EnchanTheory/Enchan-CLI/raw/main/bootstrap/install.sh | sh
```

The bootstrap installer clones or updates Enchan CLI in `~/.enchan` and then runs the platform installer from that checkout.

## Manual Checkout Install

### Windows PowerShell

```powershell
git clone https://github.com/EnchanTheory/Enchan-CLI.git "$env:USERPROFILE\.enchan"
cd "$env:USERPROFILE\.enchan"
.\install.ps1
```

### Apple Silicon macOS

```bash
git clone https://github.com/EnchanTheory/Enchan-CLI.git ~/.enchan
cd ~/.enchan
chmod +x ./install.sh
./install.sh
```

The installer downloads the Enchan CLI runtime from this repository's release `llamacpp-b9840-enchan-20260703`, extracts it into `backend/bin/<platform>/`, installs Python UI dependencies into a local `.venv`, and registers the `enchan` command with `npm link`.

## Update

After installation, update the checkout and refresh the linked command with:

```bash
enchan update
```

This runs `git pull --ff-only` in the install directory. When new commits are applied, Enchan refreshes the installer-managed assets; when the checkout is already current, it exits without reinstalling. Normal `enchan` startup checks for updates in the background and prints a short notice when a newer commit is available.

To force a local asset repair without waiting for source changes, run `enchan update --repair`.

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

Runtime assets are published in the Enchan CLI release:

- Repo: `EnchanTheory/Enchan-CLI`
- Tag: `llamacpp-b9840-enchan-20260703`
- Windows asset: `enchan-cli-runtime-win-x64.zip`
- macOS asset: `enchan-cli-runtime-macos-arm64.zip`

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

Inside the interactive CLI, type `/` to see the following commands:

- `/resume`: List resumable sessions or resume a specific session
- `/compress`: Optimize older conversation turns
- `/model`: Switch the active model
- `/status`: Show model, history, context, and generation settings
- `/set`: Configure generation and early exit parameters
- `/help`: Show help menu and available commands
- `/license`: Show repository license terms
- `/new`: Start a new session (clears chat history and file context)
- `/exit`: Exit the CLI

You can also update the installation:
- `enchan update`: update the installed checkout and refresh the command

## License

Enchan CLI is distributed under the Enchan CLI Research & Evaluation License v1.0.
See [LICENSE](LICENSE) for the full terms. Commercial use, product integration,
hosted deployment, and derivative distribution require separate permission.

Native runtime packages also include third-party components such as llama.cpp/ggml and Ollama compatibility components. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Repository Scope

This repository intentionally excludes:

- native runtime build trees
- generated logs
- local/private memory contents
- development-only docs and tools
- machine-specific virtual environment paths
