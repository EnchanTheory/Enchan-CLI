#!/usr/bin/env bash
set -euo pipefail

runtime_repo="EnchanTheory/Enchan-CLI"
runtime_tag="llamacpp-b10242-enchan-20260806"
runtime_asset="enchan-cli-runtime-macos-arm64.zip"
runtime_asset_url="https://github.com/$runtime_repo/releases/download/$runtime_tag/$runtime_asset"
lora_asset="enchan-lora-runtime-macos-arm64.zip"
lora_asset_url="https://github.com/$runtime_repo/releases/download/$runtime_tag/$lora_asset"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bin_dir="$script_dir/backend/bin/macos-arm64"
lora_bin_dir="$bin_dir/lora"
tmp_dir="$(mktemp -d)"
zip_path="$tmp_dir/$runtime_asset"
lora_zip_path="$tmp_dir/$lora_asset"
runtime_marker="$bin_dir/.runtime-version"
runtime_manifest="$bin_dir/.runtime-manifest"
runtime_marker_value="$runtime_repo $runtime_tag $runtime_asset"
lora_runtime_marker="$lora_bin_dir/.runtime-version"
lora_runtime_manifest="$lora_bin_dir/.runtime-manifest"
lora_runtime_marker_value="$runtime_repo $runtime_tag $lora_asset"
requirements_path="$script_dir/requirements.txt"
venv_dir="$script_dir/.venv"
venv_python="$venv_dir/bin/python"
venv_hash_path="$venv_dir/.requirements-sha256"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Required command not found: $1" >&2
    exit 1
  fi
}


download_runtime_asset() {
  if curl -fsSL "$runtime_asset_url" -o "$zip_path" && unzip -tq "$zip_path" >/dev/null 2>&1; then
    return 0
  fi
  rm -f "$zip_path"

  echo "Direct runtime download failed; trying GitHub CLI fallback" >&2
  require_command gh
  gh auth status >/dev/null || {
    echo "Runtime asset is not publicly downloadable and GitHub CLI is not authenticated. Run: gh auth login" >&2
    exit 1
  }
  gh release download "$runtime_tag" --repo "$runtime_repo" --pattern "$runtime_asset" --dir "$tmp_dir" --clobber
}
download_lora_asset() {
  if curl -fsSL "$lora_asset_url" -o "$lora_zip_path" && unzip -tq "$lora_zip_path" >/dev/null 2>&1; then
    return 0
  fi
  rm -f "$lora_zip_path"

  echo "Direct LoRA runtime download failed; trying GitHub CLI fallback" >&2
  require_command gh
  gh auth status >/dev/null || {
    echo "LoRA runtime asset is not publicly downloadable and GitHub CLI is not authenticated. Run: gh auth login" >&2
    exit 1
  }
  gh release download "$runtime_tag" --repo "$runtime_repo" --pattern "$lora_asset" --dir "$tmp_dir" --clobber
}
remove_runtime_manifest_files() {
  [[ -f "$runtime_manifest" ]] || return 0
  while IFS= read -r rel; do
    [[ -n "$rel" && "$rel" != .* ]] || continue
    target="$bin_dir/$rel"
    [[ -f "$target" || -L "$target" ]] && rm -f "$target"
  done < "$runtime_manifest"
}
remove_lora_runtime_manifest_files() {
  [[ -f "$lora_runtime_manifest" ]] || return 0
  while IFS= read -r rel; do
    [[ -n "$rel" && "$rel" != .* ]] || continue
    target="$lora_bin_dir/$rel"
    [[ -f "$target" || -L "$target" ]] && rm -f "$target"
  done < "$lora_runtime_manifest"
}

link_runtime_library_versions() {
  local runtime_dir="$1"
  local manifest="$2"
  if command -v otool >/dev/null 2>&1; then
    echo "Linking runtime library versions in: $runtime_dir"
    (
      cd "$runtime_dir"
      for lib in *.dylib; do
        [[ -f "$lib" && ! -L "$lib" ]] || continue
        id_name="$(basename "$(otool -D "$lib" 2>/dev/null | tail -n +2 | head -1)")"
        if [[ -n "$id_name" && "$id_name" != "$lib" ]]; then
          ln -sf "$lib" "$id_name"
          grep -qxF "$id_name" "$manifest" 2>/dev/null || printf '%s\n' "$id_name" >> "$manifest"
        fi
      done
    )
  else
    echo "[Warning] otool not found; skipping dylib version linking. If the engine fails to load, install Xcode Command Line Tools (xcode-select --install)." >&2
  fi
}

requirements_hash() {
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$requirements_path" | awk '{print $1}'
  else
    python3 - <<PY
import hashlib, pathlib
print(hashlib.sha256(pathlib.Path('$requirements_path').read_bytes()).hexdigest())
PY
  fi
}

enchan_linked() {
  global_root="$(npm root -g 2>/dev/null || true)"
  [[ -n "$global_root" ]] || return 1
  package_path="$global_root/enchan-cli"
  [[ -e "$package_path" ]] || return 1
  expected="$script_dir"
  resolved="$(python3 - <<PY
import os
print(os.path.realpath('$package_path'))
PY
)"
  [[ "$resolved" == "$expected" ]]
}

ensure_npm_link() {
  if enchan_linked; then
    echo "Enchan command already linked"
  else
    (cd "$script_dir" && npm link)
  fi
}
require_command curl
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


mkdir -p "$bin_dir" "$lora_bin_dir"

if [[ -x "$bin_dir/llama-server" && -f "$bin_dir/libenchan.dylib" && -f "$runtime_marker" && -f "$runtime_manifest" && "$(cat "$runtime_marker")" == "$runtime_marker_value" ]]; then
  echo "Enchan runtime already installed: $runtime_asset"
else
  echo "Downloading Enchan runtime: $runtime_asset"
  download_runtime_asset

  echo "Installing runtime to: $bin_dir"
  unzip -Z1 "$zip_path" > "$runtime_manifest.tmp"
  remove_runtime_manifest_files
  unzip -o "$zip_path" -d "$bin_dir" >/dev/null
  chmod +x "$bin_dir/llama-server" "$bin_dir/llama-cli" "$bin_dir/llama-quantize" 2>/dev/null || true
  mv "$runtime_manifest.tmp" "$runtime_manifest"
  printf '%s\n' "$runtime_marker_value" > "$runtime_marker"
fi

if [[ -x "$lora_bin_dir/enchan-lora-train" && -f "$lora_bin_dir/libenchan_lora.dylib" && -f "$lora_runtime_marker" && -f "$lora_runtime_manifest" && "$(cat "$lora_runtime_marker")" == "$lora_runtime_marker_value" ]]; then
  echo "Enchan LoRA runtime already installed: $lora_asset"
else
  echo "Downloading Enchan LoRA runtime: $lora_asset"
  download_lora_asset

  echo "Installing Enchan LoRA runtime to: $lora_bin_dir"
  unzip -Z1 "$lora_zip_path" > "$lora_runtime_manifest.tmp"
  remove_lora_runtime_manifest_files
  unzip -o "$lora_zip_path" -d "$lora_bin_dir" >/dev/null
  chmod +x "$lora_bin_dir/enchan-lora-train" 2>/dev/null || true
  mv "$lora_runtime_manifest.tmp" "$lora_runtime_manifest"
  printf '%s\n' "$lora_runtime_marker_value" > "$lora_runtime_marker"
fi

# Runtime archives do not preserve the versioned dylib symlinks required by dyld.
link_runtime_library_versions "$bin_dir" "$runtime_manifest"
link_runtime_library_versions "$lora_bin_dir" "$lora_runtime_manifest"

base_python="${ENCHAN_PYTHON:-python3}"
if ! "$base_python" --version >/dev/null 2>&1; then
  echo "Python was not found. Install Python 3 or set ENCHAN_PYTHON to the Python executable." >&2
  exit 1
fi

if [[ -n "${ENCHAN_PYTHON:-}" ]]; then
  if "$base_python" -c "import cryptography, prompt_toolkit, qrcode, rich" >/dev/null 2>&1; then
    echo "Python UI dependencies already installed"
  else
    echo "Installing Python UI dependencies"
    "$base_python" -m pip install --user -r "$requirements_path"
  fi
else
  req_hash="$(requirements_hash)"
  if [[ -x "$venv_python" ]] && "$venv_python" --version >/dev/null 2>&1; then
    if [[ -f "$venv_hash_path" && "$(cat "$venv_hash_path")" == "$req_hash" ]]; then
      echo "Python environment already installed"
    else
      echo "Updating Python environment"
      "$venv_python" -m pip install -r "$requirements_path"
      printf '%s\n' "$req_hash" > "$venv_hash_path"
    fi
  else
    rm -rf "$venv_dir"
    echo "Creating Python environment"
    "$base_python" -m venv "$venv_dir"
    "$venv_python" -m pip install -r "$requirements_path"
    printf '%s\n' "$req_hash" > "$venv_hash_path"
  fi
fi

ensure_npm_link

echo "Enchan CLI installed. Try: enchan"
