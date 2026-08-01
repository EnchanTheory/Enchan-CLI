# Enchan CLI

## Quick Install

Required commands: Git, Node.js/npm, and Python. Apple Silicon macOS also requires `curl`, `unzip`, and Xcode Command Line Tools.

### Windows PowerShell

```powershell
powershell -ExecutionPolicy Bypass -c "irm https://github.com/EnchanTheory/Enchan-CLI/raw/main/bootstrap/install.ps1 | iex"
```

### Apple Silicon macOS

```bash
curl -fsSL https://github.com/EnchanTheory/Enchan-CLI/raw/main/bootstrap/install.sh | sh
```

The installer places Enchan CLI in `~/.enchan` and registers the `enchan` command.

See [Enchan CLI Specification](docs/specification.md) for features, usage, settings, updates, manual installation, uninstallation, runtime assets, privacy, and license information.
