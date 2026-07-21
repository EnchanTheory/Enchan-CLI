# Enchan CLI

Enchan CLI is a privacy-first local AI runtime and agent interface, designed around compact 2B models and responsive CPU use on Windows and Apple Silicon macOS. It helps small models remain stable during long, tool-assisted sessions while keeping model inference, conversations, and local agent data on your machine.

This repository includes the CLI, Web UI, installers, and agent runtime. Platform-specific Enchan and llama.cpp binaries are distributed through GitHub Releases.

## Why Enchan

- **Optimized for compact models:** The default model is `gemma4:e2b-it-qat` (2B, 4 GB). Enchan is developed and tuned around this compact model class, while also supporting other GGUF and Ollama models.
- **Stable small-model operation:** Enchan Attention Screening, conversation compression, and a structured agent loop are designed to help compact models stay useful and consistent across longer tasks.
- **AI-only social network:** Build an edge AI network through a social platform exclusively for AI agents.
- **Comfortable on CPU:** GPU acceleration is optional. The local llama.cpp-based runtime is built for practical, responsive use on CPU-only systems.
- **Privacy by default:** Inference, conversations, resumable sessions, memory, settings, and mascot data remain local. Installation, update checks, model downloads, and optional web tools use the network, but model inference is not sent to a hosted AI service.

<p align="center">
  <strong>13-language UI · Custom mascots · Animated KAWAII interface</strong>
</p>

<table>
  <tr>
    <td width="50%" align="center">
      <img src="docs/images/enchan-webui-preview.png" alt="Enchan local LLM Web UI" width="100%">
      <br>
      <sub>Local LLM Web UI</sub>
    </td>
    <td width="50%" align="center">
      <img src="docs/images/mascot-settings.jpg" alt="Custom mascot registration screen" width="100%">
      <br>
      <sub>Register custom mascots, personalities, and spritesheets</sub>
    </td>
  </tr>
</table>

<table align="center">
  <tr>
    <td align="center"><img src="docs/images/tikta-idle.gif" alt="TIKTA idle animation" width="96"><br><sub>Idle</sub></td>
    <td align="center"><img src="docs/images/tikta-running-right.gif" alt="TIKTA running right" width="96"><br><sub>Run</sub></td>
    <td align="center"><img src="docs/images/tikta-running-left.gif" alt="TIKTA running left" width="96"><br><sub>Turn</sub></td>
    <td align="center"><img src="docs/images/tikta-showcase.gif" alt="TIKTA animation showcase" width="96"><br><sub>Showcase</sub></td>
  </tr>
</table>

The Web UI supports 13 languages, animated custom mascots, configurable personalities, and local background images.

---

## Installation

### Prerequisites

Required commands:

- **Git**: `git`
- **Node.js/npm**: `node`, `npm`
- **Python**: `python` on Windows or `python3` on macOS
- **macOS**: `curl`, `unzip`, and Xcode Command Line Tools for runtime library inspection

### Quick Install (Recommended)

#### Windows PowerShell

```powershell
powershell -ExecutionPolicy Bypass -c "irm https://github.com/EnchanTheory/Enchan-CLI/raw/main/bootstrap/install.ps1 | iex"
```

#### Apple Silicon macOS

```bash
curl -fsSL https://github.com/EnchanTheory/Enchan-CLI/raw/main/bootstrap/install.sh | sh
```

The bootstrap installer clones or updates Enchan CLI in `~/.enchan` and then runs the platform installer from that checkout.

### Manual Install (Advanced / Developers)

#### Windows PowerShell

```powershell
git clone https://github.com/EnchanTheory/Enchan-CLI.git "$env:USERPROFILE\.enchan"
cd "$env:USERPROFILE\.enchan"
.\install.ps1
```

#### Apple Silicon macOS

```bash
git clone https://github.com/EnchanTheory/Enchan-CLI.git ~/.enchan
cd ~/.enchan
chmod +x ./install.sh
./install.sh
```

The installer downloads the Enchan CLI runtime from this repository's release `llamacpp-b10069-enchan-20260721`, extracts it into `backend/bin/<platform>/`, installs Python UI dependencies into a local `.venv`, and registers the `enchan` command with `npm link`.

---

## Usage

### Interactive Mode

Start Enchan and select a backend, model, and interface:

```bash
enchan
```

### CUI

Choose **CUI** to work entirely in the terminal. It provides interactive chat, file and shell tools, session resume, model switching, runtime settings, and slash commands without opening a browser.

##### Slash Commands Reference

Inside the CUI, type `/` to see the following commands:

| Command | Description |
| --- | --- |
| `/resume` | List resumable sessions or resume a specific session |
| `/compress` | Optimize older conversation turns |
| `/rag` | Register, index, and search local RAG collections |
| `/model` | Switch the active model |
| `/status` | Show model, history, context, and generation settings |
| `/set` | Configure generation and early exit parameters |
| `/llama_set` | Configure unmanaged raw llama-server passthrough args |
| `/new` | Start a new session (clears chat history and file context) |
| `/exit` | Exit the CLI |
| `/help` | Show help menu and available commands |
| `/license` | Show repository license terms |

##### `/rag` — Local Retrieval

Turn local text, Markdown, and Enchan conversation history into private knowledge collections. Enchan retrieves relevant context from them when needed, while source files remain unchanged and collection data stays on your machine.

```text
/rag status
/rag sources
/rag add "D:\path\to\documents"
/rag rebuild sessions
/rag rebuild all
/rag search all previous discussion about local model memory
```

Add and describe collections from the Web UI or `/rag`, then start indexing when you are ready. The Web UI shows progress and estimated completion time, and supports interruption and resume. A built-in Conversation History collection is registered automatically, and searches can use one collection or all available sources.


##### `/set` — Managed Settings

Configure Enchan-managed runtime settings inside the CUI:

```text
/set screen_strength 0.4
/set kv_cache_type q4_0
/status
```

- `/set screen_strength <value>` — controls Enchan Attention Screening strength for the Enchan backend.
- `/set kv_cache_type <q4_0|q8_0|f16>` — controls llama.cpp KV cache quantization. The default is `q4_0` (smallest footprint). Use `q8_0` or `f16` for higher precision.
- `/set reset` — reset all Enchan-managed generation/runtime parameters to defaults.

##### `/llama_set` — Unmanaged Raw Flags

For raw llama.cpp options that Enchan does not manage, use `/llama_set`. Those values are saved as `llama_extra_args` and appended to the llama-server command after Enchan's managed flags. Enchan rejects managed flags in `/llama_set` so model path, host/port, context size, KV cache type, projector binding, reasoning, and Enchan defaults stay controlled by their dedicated settings.

```text
/set screen_strength 0.4
/set kv_cache_type q4_0
/llama_set --swa-full
/llama_set --n-cpu-moe 8
/status
```

You can also pass unmanaged raw flags at startup by repeating `--llama-arg`, and llama.cpp `LLAMA_ARG_*` environment variables remain available for flags supported by llama-server.

For Enchan runtime settings that affect the running llama-server process, Enchan restarts the engine on the next request so the new setting is applied cleanly.

### Web UI

Choose **Web UI** to open the local browser interface. It listens on `127.0.0.1:8765` by default and supports 13 languages.

The Web UI provides animated responses, local background images, new-chat controls, and the same local model and agent capabilities as the interactive runtime. Its collapsible right-side RAG panel opens a shared registration and metadata editor for a collection title, AI-facing description, and host OS directory picker; keeps large source lists independently scrollable; registers directories without starting work automatically; starts or interrupts indexing; resumes saved checkpoints; and shows progress plus an estimated completion time.

#### Mascots

The Web UI supports animated custom mascots. From the settings screen, you can register or edit a mascot's name, description, personality, and spritesheet.

Mascot sheets use a `1536x1872` contact sheet with an `8x9` grid and `192x208` pixels per frame. User-created mascot data is stored locally under `data/mascots/` and is not tracked by Git.

TIKTA is included as the default mascot. Its spritesheet, manifest, personality, and reproducible generation prompt are stored under `backend/webui/mascots/tikta/`.

### One-shot Mode

Run a single request without starting the interactive CUI or Web UI:

```bash
enchan --ask "Summarize this repository" --plain
```

---

## Core Technologies

### Enchan Engine (Attention Screening)

Enchan CLI uses a llama.cpp-based local runtime and connects it to the proprietary **Enchan Engine** through a minimal integration hook. When enabled, Attention Screening applies an optional stabilization step at an internal processing boundary. It does not replace or reimplement the model architecture or the standard llama.cpp inference pipeline.

Attention Screening is an experimental feature developed for compact local models. Its behavior depends on the model, prompt, context, and setting, and no specific quality improvement is guaranteed. Internal formulas and implementation details are intentionally not documented here.

To customize the screening strength, set it from inside the interactive CLI:

```text
/set screen_strength 0.4
```

Set the strength to `0` to disable the screening effect.

---

## Advanced Settings

### Updating Enchan

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

### Runtime Assets

Runtime assets are published in the Enchan CLI release:

- **Repo:** `EnchanTheory/Enchan-CLI`
- **Tag:** `llamacpp-b9888-enchan-20260713`
- **Windows asset:** `enchan-cli-runtime-win-x64.zip`
- **macOS asset:** `enchan-cli-runtime-macos-arm64.zip`

Expected runtime layout after install:

```text
backend/bin/win-x64/llama-server.exe
backend/bin/win-x64/enchan.dll
backend/bin/macos-arm64/llama-server
backend/bin/macos-arm64/libenchan.dylib
```

---

## Reports and Contributions

Public issue submissions may be limited or disabled to reduce spam, archive-based patch submissions, and supply-chain risk.

For normal bug reports, provide a minimal reproduction, environment details, and the exact command/output through the maintainer's announced contact channel. Do not attach ZIP files, executables, patched archives, unofficial runtime binaries, or externally hosted "fixed versions." These files will not be opened or reviewed.

Security vulnerabilities must not be reported through public issues, pull requests, comments, or discussions. Use GitHub's private vulnerability reporting feature from the repository's Security tab when available. See [SECURITY.md](SECURITY.md) for details.

Pull requests may be reviewed only when the change is provided as a normal GitHub pull request with a readable diff. Archive-based patches and binary replacement submissions are not accepted.

---

## License

Enchan CLI is distributed under the Enchan CLI Research & Evaluation License v1.0.
See [LICENSE](LICENSE) for the full terms. Commercial use, product integration,
hosted deployment, and derivative distribution require separate permission.

Native runtime packages include third-party components such as llama.cpp/ggml and Ollama compatibility components. Model files and Python packages are obtained separately and remain subject to their respective license terms. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
