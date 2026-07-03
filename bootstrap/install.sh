#!/usr/bin/env bash
set -euo pipefail

repo="${ENCHAN_CLI_REPO:-https://github.com/EnchanTheory/Enchan-CLI.git}"
install_dir="${ENCHAN_INSTALL_DIR:-$HOME/.enchan}"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Required command not found: $1" >&2
    exit 1
  fi
}

require_command git

if [[ -e "$install_dir" ]]; then
  if [[ ! -d "$install_dir/.git" ]]; then
    echo "Install directory exists but is not a Git checkout: $install_dir" >&2
    exit 1
  fi
  git -C "$install_dir" pull --ff-only
else
  git clone "$repo" "$install_dir"
fi

installer="$install_dir/install.sh"
if [[ ! -f "$installer" ]]; then
  echo "Installer not found after clone: $installer" >&2
  exit 1
fi

chmod +x "$installer"
"$installer"
