# Enchan CLI

Enchan CLI is a local terminal chat interface for Enchan-backed and Ollama-backed GGUF runtimes.

This publish tree contains only the CLI source and lightweight runtime scaffolding. Native runtime binaries are not committed here; install or attach platform artifacts under `backend/bin/<platform>/`.

## Supported runtime folders

- Windows x64: `backend/bin/win-x64/`
- Apple Silicon macOS: `backend/bin/macos-arm64/`

For `--backend enchan`, the runtime folder must contain the Enchan Llama executable and its required native libraries:

- Windows: `llama-server.exe`, `enchan.dll`, and required DLLs
- macOS arm64: `llama-server`, `libenchan.dylib`, and required dylibs

## Python

The `enchan` command is a Node.js launcher for the Python backend.

Set `ENCHAN_PYTHON` if you want to use a specific Python executable:

```powershell
$env:ENCHAN_PYTHON = "C:\path\to\python.exe"
enchan --backend ollama
```

On macOS/Linux, the launcher uses `python3` when `ENCHAN_PYTHON` is not set. On Windows, it uses `python`.

## Usage

```bash
enchan
```

Select a backend at startup, or pass one explicitly:

```bash
enchan --backend ollama
enchan --backend enchan --gguf-model /path/to/model.gguf
```

Useful one-shot mode:

```bash
enchan --backend ollama --ask "Summarize this repository" --plain
```

## Runtime Notes

- `ollama` backend calls a local Ollama API and can start `ollama serve` when allowed.
- `enchan` backend starts the packaged Enchan Llama runtime from `backend/bin/<platform>/`.
- Local memory is loaded from `memory/guidelines/` and `memory/knowledge/`.
- Session logs are written under `logs/sessions/`; logs are ignored by git.

## Commands

Inside the interactive CLI:

- `/help`: show commands
- `/status`: show current backend/model/session status
- `/model`: select local model
- `/resume`: resume a prior session log
- `/clear`: clear current chat context
- `/exit`: exit cleanly

## Repository Scope

This repository intentionally excludes:

- native runtime build trees
- generated logs
- local/private memory contents
- development-only docs and tools
- machine-specific virtual environment paths
