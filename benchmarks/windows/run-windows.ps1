<#
Windows run of the swift-pbi demo, with the models kept for Power BI Desktop.

Runs the same steps as benchmarks/demo/*.sh, saves every tool's output under
-Out, and leaves each model in place so you can open it in Desktop and fill in
benchmarks/windows/CHECKLIST.md.

  powershell -ExecutionPolicy Bypass -File benchmarks\windows\run-windows.ps1

Needs only uv (it also provides Python). No git: the tools and the styler
example are downloaded as release zips from GitHub. To keep every file
inside one folder, set UV_CACHE_DIR, UV_PYTHON_INSTALL_DIR and UV_TOOL_DIR
before running (see benchmarks/windows/CHECKLIST.md).
#>
param(
    [string]$Tag = "v1.1.0",
    [string]$Out = (Join-Path $PWD ("windows-run-" + (Get-Date -Format "yyyy-MM-dd")))
)
$ErrorActionPreference = "Continue"
$Repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$GH = "https://github.com/C-Kapsalis"
New-Item -ItemType Directory -Force -Path $Out | Out-Null
$Models = Join-Path $Out "models"
New-Item -ItemType Directory -Force -Path $Models | Out-Null

function Tool([string]$repo, [string]$cmd) { @("-q", "--from", "$GH/$repo/archive/refs/tags/$Tag.zip", $cmd) }
$PREFLIGHT = Tool "tmdl-preflight" "tmdl-preflight"
$FORGE = Tool "pbip-model-forge" "pbip-forge"
$DRIFT = Tool "tmdl-drift-doctor" "drift-doctor"
$STYLER = Tool "pbi-plot-styler" "pbi-plot-styler"

# Windows PowerShell 5.1's Tee-Object writes UTF-16, so every line goes
# through Log, which prints it and appends it as UTF-8.
$script:Log = $null
function Log($lines) {
    foreach ($line in @($lines)) {
        $text = "$line"
        Write-Host $text
        Add-Content -Path $script:Log -Value $text -Encoding utf8
    }
}
function Note([string]$text) { Log "`n# $text" }
function Run([string[]]$tool, [string[]]$arguments) {
    Log "`n> uvx $($tool -join ' ') $($arguments -join ' ')"
    Log (& uvx @tool @arguments 2>&1)
    Log "[exit $LASTEXITCODE]"
}

# --- 00 environment -----------------------------------------------------------
$script:Log = Join-Path $Out "00-environment.txt"
@(
    "date: $((Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mmZ'))"
    "os: $((Get-CimInstance Win32_OperatingSystem).Caption) $([Environment]::OSVersion.Version)"
    "powershell: $($PSVersionTable.PSVersion)"
    "uv: $(uv --version)"
    "tag: $Tag"
) | Set-Content $script:Log -Encoding utf8
$desktop = Get-AppxPackage -Name "Microsoft.MicrosoftPowerBIDesktop" -ErrorAction SilentlyContinue
if ($desktop) { "power bi desktop (store): $($desktop.Version)" | Add-Content $script:Log -Encoding utf8 }
$exe = Get-ChildItem "C:\Program Files\Microsoft Power BI Desktop\bin\PBIDesktop.exe" -ErrorAction SilentlyContinue
if ($exe) { "power bi desktop (installer): $($exe.VersionInfo.ProductVersion)" | Add-Content $script:Log -Encoding utf8 }
if (-not ($desktop -or $exe)) { "power bi desktop: not found" | Add-Content $script:Log -Encoding utf8 }

# --- 01 tmdl-preflight ----------------------------------------------------------
$script:Log = Join-Path $Out "01-preflight.txt"; Set-Content $script:Log "" -Encoding utf8
Copy-Item -Recurse -Force (Join-Path $Repo "examples\bike-shop-clean") (Join-Path $Models "01-bike-shop-clean")
Copy-Item -Recurse -Force (Join-Path $Repo "examples\bike-shop-broken") (Join-Path $Models "01-bike-shop-broken")
Copy-Item -Recurse -Force (Join-Path $Repo "examples\bike-shop-broken") (Join-Path $Models "01-bike-shop-fixed")
Note "Tool version"; Run $PREFLIGHT @("--version")
Note "Check the clean copy"; Run $PREFLIGHT @("check", (Join-Path $Models "01-bike-shop-clean"))
Note "Check the broken copy (read-only)"; Run $PREFLIGHT @("check", (Join-Path $Models "01-bike-shop-broken"))
Note "Fix a copy, then the tool re-checks from disk"; Run $PREFLIGHT @("fix", (Join-Path $Models "01-bike-shop-fixed"))
Note "Independent re-check of the fixed copy"; Run $PREFLIGHT @("check", (Join-Path $Models "01-bike-shop-fixed"))
Note "Second fix run: should apply nothing"; Run $PREFLIGHT @("fix", (Join-Path $Models "01-bike-shop-fixed"))

# --- 02 pbip-model-forge --------------------------------------------------------
$script:Log = Join-Path $Out "02-forge.txt"; Set-Content $script:Log "" -Encoding utf8
$specs = Join-Path $Repo "benchmarks\demo\specs"
Note "Tool version"; Run $FORGE @("--version")
Note "Gate 1 on the first draft"; Run $FORGE @("check", (Join-Path $specs "bike-repair-draft.json"), "--profile", "handoff")
Note "Gate 1 on the corrected spec"; Run $FORGE @("check", (Join-Path $specs "bike-repair.json"), "--profile", "handoff")
Note "Build"; Run $FORGE @("build", (Join-Path $specs "bike-repair.json"), (Join-Path $Models "02-BikeRepair"), "--check", "--profile", "handoff")
Note "Gate 2: structural validation"; Run $PREFLIGHT @("check", (Join-Path $Models "02-BikeRepair"))

# --- 03 tmdl-drift-doctor -------------------------------------------------------
$script:Log = Join-Path $Out "03-drift.txt"; Set-Content $script:Log "" -Encoding utf8
$fleet = Join-Path $Models "03-fleet"
Log (& uv run -q --no-project --python 3.12 python -I (Join-Path $Repo "benchmarks\demo\make_fleet.py") (Join-Path $Repo "examples\bike-shop-clean") $fleet 2>&1)
# Keep a copy of each spinout before remediation, for opening in Desktop.
Copy-Item -Recurse -Force (Join-Path $fleet "clients") (Join-Path $Models "03-spinouts-before")
Push-Location $fleet
Note "Tool version"; Run $DRIFT @("--version")
Note "Before: tmdl-preflight per spinout"
foreach ($c in "north-cycles", "harbor-bikes", "summit-wheels", "valley-spokes") { Run $PREFLIGHT @("check", "clients\$c") }
Note "Capture"; Run $DRIFT @("capture")
Note "Detect"; Run $DRIFT @("detect")
Note "Remediate dry run"; Run $DRIFT @("remediate", "--dry-run")
Note "Remediate"; Run $DRIFT @("remediate")
Note "Detect again"; Run $DRIFT @("detect")
Note "After: tmdl-preflight per spinout"
foreach ($c in "north-cycles", "harbor-bikes", "summit-wheels", "valley-spokes") { Run $PREFLIGHT @("check", "clients\$c") }
Pop-Location

# --- 04 pbi-plot-styler ---------------------------------------------------------
$script:Log = Join-Path $Out "04-plot-styler.txt"; Set-Content $script:Log "" -Encoding utf8
$zip = Join-Path $Out "pbi-plot-styler.zip"
Invoke-WebRequest -UseBasicParsing -Uri "$GH/pbi-plot-styler/archive/refs/tags/$Tag.zip" -OutFile $zip
Expand-Archive -Force -Path $zip -DestinationPath (Join-Path $Out "styler-src")
$src = (Get-ChildItem (Join-Path $Out "styler-src") -Directory | Select-Object -First 1).FullName
Copy-Item -Recurse -Force (Join-Path $src "examples\coffee-roastery") (Join-Path $Models "04-roastery-before")
Copy-Item -Recurse -Force (Join-Path $src "examples\coffee-roastery") (Join-Path $Models "04-roastery-styled")
Push-Location (Join-Path $Models "04-roastery-styled")
Note "Tool version"; Run $STYLER @("--version")
Note "Integrity check"; Run $STYLER @("check", "Roastery.Report")
Note "Style"; Run $STYLER @("Roastery.Report")
Note "Style again: nothing should change"; Run $STYLER @("Roastery.Report")
Note "Integrity check after styling"; Run $STYLER @("check", "Roastery.Report")
Pop-Location

# --- what to open ---------------------------------------------------------------
$list = Join-Path $Out "open-in-desktop.txt"
Get-ChildItem -Path $Models -Recurse -Filter *.pbip | ForEach-Object { $_.FullName } | Set-Content $list
Write-Host "`nDone. Outputs in $Out"
Write-Host "Open each .pbip listed in $list and fill in benchmarks\windows\CHECKLIST.md"
