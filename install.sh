#!/usr/bin/env bash
set -euo pipefail

runtime_repo="EnchanTheory/Enchan-Llama"
runtime_tag="v0.1.0"
runtime_asset="enchan-llama-macos-arm64.zip"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bin_dir="$script_dir/backend/bin/macos-arm64"
tmp_dir="$(mktemp -d)"
zip_path="$tmp_dir/$runtime_asset"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Required command not found: $1" >&2
    exit 1
  fi
}

require_command gh
require_command node
require_command npm
require_command git
require_command unzip

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "install.sh currently supports macOS. Use install.ps1 on Windows." >&2
  exit 1
fi

if [[ "$(uname -m)" != "arm64" ]]; then
  echo "This installer expects Apple Silicon macOS arm64." >&2
  exit 1
fi

gh auth status >/dev/null || {
  echo "GitHub CLI is not authenticated. Run: gh auth login" >&2
  exit 1
}

mkdir -p "$bin_dir"

echo "Downloading Enchan Llama runtime: $runtime_asset"
gh release download "$runtime_tag" --repo "$runtime_repo" --pattern "$runtime_asset" --dir "$tmp_dir" --clobber

echo "Installing runtime to: $bin_dir"
unzip -o "$zip_path" -d "$bin_dir" >/dev/null
chmod +x "$bin_dir/llama-server" "$bin_dir/llama-cli" "$bin_dir/llama-quantize" 2>/dev/null || true

python_bin="${ENCHAN_PYTHON:-python3}"
if ! "$python_bin" --version >/dev/null 2>&1; then
  echo "Python was not found. Install Python 3 or set ENCHAN_PYTHON to the Python executable." >&2
fi

npm link

echo "Enchan CLI installed. Try: enchan --backend ollama"
echo "For Enchan runtime: enchan --backend enchan --gguf-model <path-to-model.gguf>"

