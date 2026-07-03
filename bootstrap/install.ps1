$ErrorActionPreference = "Stop"

$Repo = if ($env:ENCHAN_CLI_REPO) { $env:ENCHAN_CLI_REPO } else { "https://github.com/EnchanTheory/Enchan-CLI.git" }
$InstallDir = if ($env:ENCHAN_INSTALL_DIR) { $env:ENCHAN_INSTALL_DIR } else { Join-Path $HOME ".enchan" }

function Require-Command($Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $Name"
    }
}

Require-Command git

if (Test-Path $InstallDir) {
    if (-not (Test-Path (Join-Path $InstallDir ".git"))) {
        throw "Install directory exists but is not a Git checkout: $InstallDir"
    }
    git -C $InstallDir pull --ff-only
} else {
    git clone $Repo $InstallDir
}

$Installer = Join-Path $InstallDir "install.ps1"
if (-not (Test-Path $Installer)) {
    throw "Installer not found after clone: $Installer"
}

& $Installer
