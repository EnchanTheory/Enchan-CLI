$ErrorActionPreference = "Stop"

$RuntimeRepo = "EnchanTheory/Enchan-CLI"
$RuntimeTag = "llamacpp-b10069-enchan-20260721"
$RuntimeAsset = "enchan-cli-runtime-win-x64.zip"
$RuntimeAssetUrl = "https://github.com/$RuntimeRepo/releases/download/$RuntimeTag/$RuntimeAsset"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BinDir = Join-Path $ScriptDir "backend\bin\win-x64"
$TmpDir = Join-Path $env:TEMP ("enchan-cli-install-" + [guid]::NewGuid().ToString("N"))
$ZipPath = Join-Path $TmpDir $RuntimeAsset
$RuntimeMarker = Join-Path $BinDir ".runtime-version"
$RuntimeManifest = Join-Path $BinDir ".runtime-manifest"
$RuntimeMarkerValue = "$RuntimeRepo $RuntimeTag $RuntimeAsset"
$RequirementsPath = Join-Path $ScriptDir "requirements.txt"
$VenvDir = Join-Path $ScriptDir ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$VenvHashPath = Join-Path $VenvDir ".requirements-sha256"

function Require-Command($Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $Name"
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

$BasePython = if ($env:ENCHAN_PYTHON) { $env:ENCHAN_PYTHON } else { "python" }
try {
    & $BasePython --version | Out-Host
} catch {
    throw "Python was not found. Install Python or set ENCHAN_PYTHON to the Python executable."
}

if ($env:ENCHAN_PYTHON) {
    try {
        & $BasePython -c "import prompt_toolkit, rich" | Out-Null
        Write-Host "Python UI dependencies already installed"
    } catch {
        Write-Host "Installing Python UI dependencies"
        & $BasePython -m pip install --user -r $RequirementsPath
    }
} else {
    $RequirementsHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $RequirementsPath).Hash
    $VenvReady = (Test-Path $VenvPython) -and (Test-Path $VenvHashPath) -and ((Get-Content -LiteralPath $VenvHashPath -Raw).Trim() -eq $RequirementsHash)
    if ($VenvReady) {
        Write-Host "Python environment already installed"
    } else {
        if (Test-Path $VenvDir) {
            Remove-Item -LiteralPath $VenvDir -Recurse -Force
        }
        Write-Host "Creating Python environment"
        & $BasePython -m venv $VenvDir
        & $VenvPython -m pip install -r $RequirementsPath
        Set-Content -LiteralPath $VenvHashPath -Value $RequirementsHash -Encoding UTF8
    }
}

Ensure-NpmLink

Write-Host "Enchan CLI installed. Try: enchan"
