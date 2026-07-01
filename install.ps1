$ErrorActionPreference = "Stop"

$RuntimeRepo = "EnchanTheory/Enchan-Llama"
$RuntimeTag = "v0.1.0"
$RuntimeAsset = "enchan-llama-win-x64.zip"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BinDir = Join-Path $ScriptDir "backend\bin\win-x64"
$TmpDir = Join-Path $env:TEMP ("enchan-cli-install-" + [guid]::NewGuid().ToString("N"))
$ZipPath = Join-Path $TmpDir $RuntimeAsset

function Require-Command($Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $Name"
    }
}

Require-Command gh
Require-Command node
Require-Command npm
Require-Command git

try {
    gh auth status | Out-Null
} catch {
    throw "GitHub CLI is not authenticated. Run: gh auth login"
}

New-Item -ItemType Directory -Path $TmpDir -Force | Out-Null
New-Item -ItemType Directory -Path $BinDir -Force | Out-Null

Write-Host "Downloading Enchan Llama runtime: $RuntimeAsset"
gh release download $RuntimeTag --repo $RuntimeRepo --pattern $RuntimeAsset --dir $TmpDir --clobber

Write-Host "Installing runtime to: $BinDir"
Expand-Archive -LiteralPath $ZipPath -DestinationPath $BinDir -Force

$Python = if ($env:ENCHAN_PYTHON) { $env:ENCHAN_PYTHON } else { "python" }
try {
    & $Python --version | Out-Host
} catch {
    Write-Warning "Python was not found. Install Python or set ENCHAN_PYTHON to the Python executable."
}

npm link

Write-Host "Enchan CLI installed. Try: enchan --backend ollama"
Write-Host "For Enchan runtime: enchan --backend enchan --gguf-model <path-to-model.gguf>"

