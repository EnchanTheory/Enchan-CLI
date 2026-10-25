$ErrorActionPreference = "Stop"

$RuntimeRepo = "EnchanTheory/Enchan-CLI"
$RuntimeTag = "llamacpp-b11521-enchan-20261012"
$LoraRuntimeTag = "llamacpp-b10760-enchan-20260903"
$RuntimeAsset = "enchan-cli-runtime-win-x64.zip"
$RuntimeAssetUrl = "https://github.com/$RuntimeRepo/releases/download/$RuntimeTag/$RuntimeAsset"
$LoraAsset = "enchan-lora-runtime-win-x64.zip"
$LoraAssetUrl = "https://github.com/$RuntimeRepo/releases/download/$LoraRuntimeTag/$LoraAsset"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BinDir = Join-Path $ScriptDir "backend\bin\win-x64"
$LoraBinDir = Join-Path $BinDir "lora"
$TmpDir = Join-Path $env:TEMP ("enchan-cli-install-" + [guid]::NewGuid().ToString("N"))
$ZipPath = Join-Path $TmpDir $RuntimeAsset
$LoraZipPath = Join-Path $TmpDir $LoraAsset
$RuntimeMarker = Join-Path $BinDir ".runtime-version"
$RuntimeManifest = Join-Path $BinDir ".runtime-manifest"
$RuntimeMarkerValue = "$RuntimeRepo $RuntimeTag $RuntimeAsset"
$LoraMarker = Join-Path $LoraBinDir ".runtime-version"
$LoraManifest = Join-Path $LoraBinDir ".runtime-manifest"
$LoraMarkerValue = "$RuntimeRepo $LoraRuntimeTag $LoraAsset"
$RequirementsPath = Join-Path $ScriptDir "requirements.txt"
$VenvDir = Join-Path $ScriptDir ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$VenvHashPath = Join-Path $VenvDir ".requirements-sha256"
$SecurePipRequirement = "pip @ https://files.pythonhosted.org/packages/3f/06/3e4420302363fbb71be3c7f35ce042f54bfca330e3e66b3a2e3c4cca579f/pip-26.2.2-py3-none-any.whl#sha256=fd7f4dfa8190e014013b9f08f3e973f4e4c26ffd179a204895533a7254813a70"

function Require-Command($Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $Name"
    }
}

function Test-PythonSupported($PythonExe) {
    & $PythonExe -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" 2>$null
    return $LASTEXITCODE -eq 0
}

function Test-PipSecurityBaseline($PythonExe) {
    $Code = @'
import importlib.metadata as m
import re
import sys

def version_tuple(value):
    return tuple(int(x) for x in re.findall(r"\d+", value))

try:
    current = m.version("pip")
except m.PackageNotFoundError:
    raise SystemExit(1)
raise SystemExit(0 if version_tuple(current) >= version_tuple("26.2.2") else 1)
'@
    & $PythonExe -c $Code 2>$null
    return $LASTEXITCODE -eq 0
}

function Ensure-PipSecurityBaseline($PythonExe, [switch]$UserInstall) {
    if (Test-PipSecurityBaseline $PythonExe) {
        return
    }
    Write-Host "Updating pip security baseline to 26.2.2"
    $PipArgs = @("-m", "pip", "install")
    if ($UserInstall) {
        $PipArgs += "--user"
    }
    $PipArgs += $SecurePipRequirement
    & $PythonExe @PipArgs
    if ($LASTEXITCODE -ne 0 -or -not (Test-PipSecurityBaseline $PythonExe)) {
        throw "Failed to establish the secure pip 26.2.2 baseline"
    }
}

function Test-PythonDependencySecurityBaseline($PythonExe) {
    $Code = @'
import importlib.metadata as m
import re

def version_tuple(value):
    return tuple(int(x) for x in re.findall(r"\d+", value))

minimums = {
    "certifi": "2026.10.19",
    "Pillow": "13.0.0",
    "Brotli": "1.2.1",
}
for package, minimum in minimums.items():
    try:
        current = m.version(package)
    except m.PackageNotFoundError:
        raise SystemExit(1)
    if version_tuple(current) < version_tuple(minimum):
        raise SystemExit(1)

try:
    current = m.version("brotlicffi")
except m.PackageNotFoundError:
    pass
else:
    if version_tuple(current) < version_tuple("1.2.1.0"):
        raise SystemExit(1)
raise SystemExit(0)
'@
    & $PythonExe -c $Code 2>$null
    return $LASTEXITCODE -eq 0
}

function Ensure-OptionalBrotliCffiSecurityBaseline($PythonExe, [switch]$UserInstall) {
    & $PythonExe -c "import importlib.metadata as m; m.version('brotlicffi')" 2>$null
    if ($LASTEXITCODE -ne 0) {
        return
    }
    $Code = "import importlib.metadata as m, re; p=lambda v: tuple(int(x) for x in re.findall(r'\d+', v)); raise SystemExit(0 if p(m.version('brotlicffi')) >= p('1.2.1.0') else 1)"
    & $PythonExe -c $Code 2>$null
    if ($LASTEXITCODE -eq 0) {
        return
    }
    Write-Host "Updating brotlicffi security baseline to 1.2.1.0"
    $PipArgs = @("-m", "pip", "install", "--upgrade")
    if ($UserInstall) {
        $PipArgs += "--user"
    }
    $PipArgs += "brotlicffi>=1.2.1.0"
    & $PythonExe @PipArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to update brotlicffi security baseline"
    }
}

function Download-RuntimeAsset {
    $oldProgress = $ProgressPreference
    try {
        $ProgressPreference = 'SilentlyContinue'
        Invoke-WebRequest -Uri $RuntimeAssetUrl -OutFile $ZipPath -UseBasicParsing -ErrorAction Stop
        $ProgressPreference = $oldProgress
        $Magic = [System.IO.File]::ReadAllBytes($ZipPath)
        if ($Magic.Length -ge 2 -and $Magic[0] -eq 0x50 -and $Magic[1] -eq 0x4b) {
            return
        }
        Write-Host "Direct runtime download did not return a zip; trying GitHub CLI fallback"
    } catch {
        $ProgressPreference = $oldProgress
        Write-Host "Direct runtime download failed; trying GitHub CLI fallback"
    }

    Require-Command gh
    try {
        gh auth status | Out-Null
    } catch {
        throw "Runtime asset is not publicly downloadable and GitHub CLI is not authenticated. Run: gh auth login"
    }
    gh release download $RuntimeTag --repo $RuntimeRepo --pattern $RuntimeAsset --dir $TmpDir --clobber
}
function Download-LoraAsset {
    $oldProgress = $ProgressPreference
    try {
        $ProgressPreference = 'SilentlyContinue'
        Invoke-WebRequest -Uri $LoraAssetUrl -OutFile $LoraZipPath -UseBasicParsing -ErrorAction Stop
        $ProgressPreference = $oldProgress
        $Magic = [System.IO.File]::ReadAllBytes($LoraZipPath)
        if ($Magic.Length -ge 2 -and $Magic[0] -eq 0x50 -and $Magic[1] -eq 0x4b) {
            return
        }
        Write-Host "Direct LoRA runtime download did not return a zip; trying GitHub CLI fallback"
    } catch {
        $ProgressPreference = $oldProgress
        Write-Host "Direct LoRA runtime download failed; trying GitHub CLI fallback"
    }

    Require-Command gh
    try {
        gh auth status | Out-Null
    } catch {
        throw "LoRA runtime asset is not publicly downloadable and GitHub CLI is not authenticated. Run: gh auth login"
    }
    gh release download $LoraRuntimeTag --repo $RuntimeRepo --pattern $LoraAsset --dir $TmpDir --clobber
}
function Remove-RuntimeManifestFiles {
    if (-not (Test-Path $RuntimeManifest)) {
        return
    }
    $Root = [System.IO.Path]::GetFullPath($BinDir)
    Get-Content -LiteralPath $RuntimeManifest | ForEach-Object {
        $Rel = $_.Trim()
        if (-not $Rel -or $Rel.StartsWith(".")) {
            return
        }
        $Target = [System.IO.Path]::GetFullPath((Join-Path $BinDir $Rel))
        if ($Target.StartsWith($Root, [System.StringComparison]::OrdinalIgnoreCase) -and (Test-Path $Target -PathType Leaf)) {
            Remove-Item -LiteralPath $Target -Force
        }
    }
}
function Remove-LoraManifestFiles {
    if (-not (Test-Path $LoraManifest)) {
        return
    }
    $Root = [System.IO.Path]::GetFullPath($LoraBinDir)
    Get-Content -LiteralPath $LoraManifest | ForEach-Object {
        $Rel = $_.Trim()
        if (-not $Rel -or $Rel.StartsWith(".")) {
            return
        }
        $Target = [System.IO.Path]::GetFullPath((Join-Path $LoraBinDir $Rel))
        if ($Target.StartsWith($Root, [System.StringComparison]::OrdinalIgnoreCase) -and (Test-Path $Target -PathType Leaf)) {
            Remove-Item -LiteralPath $Target -Force
        }
    }
}

function Get-ZipFileList($ZipFile) {
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $Zip = [System.IO.Compression.ZipFile]::OpenRead($ZipFile)
    try {
        return @($Zip.Entries | Where-Object { $_.Name } | ForEach-Object { $_.FullName })
    } finally {
        $Zip.Dispose()
    }
}

function Test-EnchanLinked {
    $GlobalRoot = (& npm root -g 2>$null).Trim()
    if (-not $GlobalRoot) {
        return $false
    }
    $PackagePath = Join-Path $GlobalRoot "enchan-cli"
    if (-not (Test-Path $PackagePath)) {
        return $false
    }
    $Item = Get-Item -LiteralPath $PackagePath -Force
    $Target = if ($Item.Target) { [string]$Item.Target } else { $Item.FullName }
    $ResolvedTarget = [System.IO.Path]::GetFullPath($Target).TrimEnd("\", "/")
    $Expected = [System.IO.Path]::GetFullPath($ScriptDir).TrimEnd("\", "/")
    return $ResolvedTarget.Equals($Expected, [System.StringComparison]::OrdinalIgnoreCase)
}

function Ensure-NpmLink {
    if (Test-EnchanLinked) {
        Write-Host "Enchan command already linked"
    } else {
        Push-Location $ScriptDir
        try {
            npm link
            if ($LASTEXITCODE -ne 0) {
                throw "npm link failed with exit code $LASTEXITCODE"
            }
        } finally {
            Pop-Location
        }
    }
}
Require-Command node
Require-Command npm
Require-Command git

New-Item -ItemType Directory -Path $TmpDir -Force | Out-Null
New-Item -ItemType Directory -Path $BinDir -Force | Out-Null
New-Item -ItemType Directory -Path $LoraBinDir -Force | Out-Null

$RuntimeReady = (Test-Path (Join-Path $BinDir "llama-server.exe")) -and (Test-Path (Join-Path $BinDir "enchan.dll")) -and (Test-Path $RuntimeMarker) -and (Test-Path $RuntimeManifest) -and ((Get-Content -LiteralPath $RuntimeMarker -Raw).Trim() -eq $RuntimeMarkerValue)
if ($RuntimeReady) {
    Write-Host "Enchan runtime already installed: $RuntimeAsset"
} else {
    Write-Host "Downloading Enchan runtime: $RuntimeAsset"
    Download-RuntimeAsset

    Write-Host "Installing runtime to: $BinDir"
    $ManifestEntries = Get-ZipFileList $ZipPath
    Remove-RuntimeManifestFiles
    Expand-Archive -LiteralPath $ZipPath -DestinationPath $BinDir -Force
    Set-Content -LiteralPath $RuntimeManifest -Value $ManifestEntries -Encoding UTF8
    Set-Content -LiteralPath $RuntimeMarker -Value $RuntimeMarkerValue -Encoding UTF8
}

$LoraReady = (Test-Path (Join-Path $LoraBinDir "enchan-lora-train.exe")) -and (Test-Path (Join-Path $LoraBinDir "enchan_lora.dll")) -and (Test-Path $LoraMarker) -and (Test-Path $LoraManifest) -and ((Get-Content -LiteralPath $LoraMarker -Raw).Trim() -eq $LoraMarkerValue)
if ($LoraReady) {
    Write-Host "Enchan LoRA runtime already installed: $LoraAsset"
} else {
    Write-Host "Downloading Enchan LoRA runtime: $LoraAsset"
    Download-LoraAsset

    Write-Host "Installing Enchan LoRA runtime to: $LoraBinDir"
    $LoraManifestEntries = Get-ZipFileList $LoraZipPath
    Remove-LoraManifestFiles
    Expand-Archive -LiteralPath $LoraZipPath -DestinationPath $LoraBinDir -Force
    Set-Content -LiteralPath $LoraManifest -Value $LoraManifestEntries -Encoding UTF8
    Set-Content -LiteralPath $LoraMarker -Value $LoraMarkerValue -Encoding UTF8
}

$BasePython = if ($env:ENCHAN_PYTHON) { $env:ENCHAN_PYTHON } else { "python" }
try {
    & $BasePython --version | Out-Host
} catch {
    throw "Python was not found. Install Python 3.11 or newer, or set ENCHAN_PYTHON to the Python executable."
}
if (-not (Test-PythonSupported $BasePython)) {
    throw "Enchan CLI requires Python 3.11 or newer because the supported Pillow security baseline requires Python 3.11+."
}

if ($env:ENCHAN_PYTHON) {
    Ensure-PipSecurityBaseline $BasePython -UserInstall
    Write-Host "Ensuring Python UI dependencies and security baselines"
    & $BasePython -m pip install --user -r $RequirementsPath
    if ($LASTEXITCODE -ne 0) {
        throw "Python dependency update failed"
    }
    Ensure-OptionalBrotliCffiSecurityBaseline $BasePython -UserInstall
    if (-not (Test-PythonDependencySecurityBaseline $BasePython)) {
        throw "Python dependency security baseline verification failed"
    }
} else {
    $RequirementsHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $RequirementsPath).Hash
    $VenvUsable = Test-Path $VenvPython
    if ($VenvUsable) {
        & $VenvPython --version 2>$null | Out-Null
        $VenvUsable = $LASTEXITCODE -eq 0 -and (Test-PythonSupported $VenvPython)
    }
    if (-not $VenvUsable -and (Test-Path $VenvDir)) {
        Remove-Item -LiteralPath $VenvDir -Recurse -Force
    }

    if (-not $VenvUsable) {
        Write-Host "Creating Python environment"
        & $BasePython -m venv $VenvDir
        if ($LASTEXITCODE -ne 0) {
            throw "Python environment creation failed"
        }
    }

    Ensure-PipSecurityBaseline $VenvPython
    $RequirementsCurrent = $VenvUsable -and (Test-Path $VenvHashPath) -and ((Get-Content -LiteralPath $VenvHashPath -Raw).Trim() -eq $RequirementsHash) -and (Test-PythonDependencySecurityBaseline $VenvPython)
    if ($RequirementsCurrent) {
        Write-Host "Python environment already installed and security baseline verified"
    } else {
        Write-Host "Updating Python environment"
        & $VenvPython -m pip install -r $RequirementsPath
        if ($LASTEXITCODE -ne 0) {
            throw "Python dependency update failed"
        }
        Ensure-OptionalBrotliCffiSecurityBaseline $VenvPython
        if (-not (Test-PythonDependencySecurityBaseline $VenvPython)) {
            throw "Python dependency security baseline verification failed"
        }
        Set-Content -LiteralPath $VenvHashPath -Value $RequirementsHash -Encoding UTF8
    }

    & $VenvPython -m pip check
    if ($LASTEXITCODE -ne 0) {
        throw "Python dependency consistency check failed"
    }
}

Ensure-NpmLink

Write-Host "Enchan CLI installed. Try: enchan"
