# Windows and Power BI Desktop checklist

The macOS demo proves the files pass the validators. This run proves what
Power BI Desktop does with them. Only record what you saw.

Everything lives in one folder, `%USERPROFILE%\pbi-test`. Nothing is
installed: uv is a portable zip, Python and the tools are downloaded by uv
into that folder, and no git is needed. Step 5 deletes it all.

## 1. Set up (one PowerShell window, not as administrator)

Keep this one window open until step 5: the `$env:` settings only last
for this session.

```powershell
$Root = "$HOME\pbi-test"
New-Item -ItemType Directory -Force $Root | Out-Null
$env:UV_CACHE_DIR          = "$Root\uv-cache"
$env:UV_PYTHON_INSTALL_DIR = "$Root\uv-python"
$env:UV_TOOL_DIR           = "$Root\uv-tools"

# Portable uv (use uv-aarch64-pc-windows-msvc.zip on an ARM laptop)
Invoke-WebRequest -UseBasicParsing https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip -OutFile "$Root\uv.zip"
Expand-Archive -Force "$Root\uv.zip" "$Root\uv"
$env:PATH = "$Root\uv;$env:PATH"
uv --version

# swift-pbi itself
Invoke-WebRequest -UseBasicParsing https://github.com/C-Kapsalis/swift-pbi/archive/refs/heads/master.zip -OutFile "$Root\swift-pbi.zip"
Expand-Archive -Force "$Root\swift-pbi.zip" $Root
Set-Location "$Root\swift-pbi-master"
```

`$HOME\pbi-test` is used because Desktop and Documents are often synced to
OneDrive; the profile root is not.

## 2. Run the four tools

```powershell
powershell -ExecutionPolicy Bypass -File benchmarks\windows\run-windows.ps1 -Out "$Root\results"
```

It takes a few minutes the first time (uv downloads Python and the tools).
It writes `$Root\results\` with the tool output (`00`–`04*.txt`), a
`models\` folder and `open-in-desktop.txt`.

### Steps 1 and 2 in Git Bash instead

Same folder, same result. `unset HISTFILE` keeps this session out of
`~/.bash_history` from the start. uv is a Windows program, so its folders
are passed as Windows paths (`cygpath -w`), and Windows' own `tar.exe`
unpacks the zips.

```bash
unset HISTFILE
ROOT="$HOME/pbi-test"; mkdir -p "$ROOT"
export UV_CACHE_DIR="$(cygpath -w "$ROOT/uv-cache")"
export UV_PYTHON_INSTALL_DIR="$(cygpath -w "$ROOT/uv-python")"
export UV_TOOL_DIR="$(cygpath -w "$ROOT/uv-tools")"
UNZIP=/c/Windows/System32/tar.exe

curl -sSL -o "$ROOT/uv.zip" https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip
mkdir -p "$ROOT/uv" && "$UNZIP" -xf "$ROOT/uv.zip" -C "$ROOT/uv"
export PATH="$ROOT/uv:$PATH"; uv --version

curl -sSL -o "$ROOT/swift-pbi.zip" https://github.com/C-Kapsalis/swift-pbi/archive/refs/heads/master.zip
"$UNZIP" -xf "$ROOT/swift-pbi.zip" -C "$ROOT" && cd "$ROOT/swift-pbi-master"

powershell.exe -ExecutionPolicy Bypass -File benchmarks/windows/run-windows.ps1 -Out "$(cygpath -w "$ROOT/results")"
```

Steps 3 and 4 are the same. For step 5 in Git Bash, close Desktop, then:

```bash
cd ~ && rm -rf "$HOME/pbi-test"
find "$HOME/Pictures/Screenshots" -type f -newermt "-1 day" -print -delete 2>/dev/null
```

and do the "by hand" items below, plus the recent-item shortcuts (the
PowerShell block's item 3, or delete them in
`%APPDATA%\Microsoft\Windows\Recent`). Nothing reached `~/.bash_history`
because of `unset HISTFILE`; if you forgot it, run `history -c` and remove the
lines from `~/.bash_history` before closing the window.

## 3. Open each model in Desktop

If Desktop says it cannot read the project format, turn on File > Options >
Preview features > "Power BI Project (.pbip) save option" and "Store semantic
model using TMDL format", restart Desktop, and note that you had to.

Open each `.pbip` with File > Open, wait for it to finish loading, and fill in
the row. **Do not save** any model (close with "Don't save"), so the files
stay as the tools left them. Paste error text exactly.

| # | Model (under `results\models\`) | Expected | Opened? | Exact error, if any | Visuals render? | Refresh OK? |
|---|---|---|---|---|---|---|
| 1 | `01-bike-shop-broken` | refuses to open (M006: Stores not in the model) | | | | |
| 2 | `01-bike-shop-fixed` | opens, after 4 one-line fixes | | | | |
| 3 | `01-bike-shop-clean` | opens | | | | |
| 4 | `02-BikeRepair` | opens (built from a spec) | | | | |
| 5 | `03-spinouts-before\harbor-bikes` | field parameter broken (D002: deleted measure) | | | | |
| 6 | `03-fleet\clients\harbor-bikes` | opens, measure restored | | | | |
| 7 | `03-fleet\clients\north-cycles` | opens; Revenue per Store matches the template | | | | |
| 8 | `03-fleet\clients\summit-wheels` | opens; column and relationship restored | | | | |
| 9 | `03-fleet\clients\valley-spokes` | opens; its own extra measure still there | | | | |
| 10 | `04-roastery-before` | opens, default chart colours | | | | |
| 11 | `04-roastery-styled` | opens, styled lines and labels | | | | |

Also note the Power BI Desktop version (Help > About) and the Windows version.

**Screenshots.** Save every screenshot into `$Root\shots` (Snipping Tool >
Save as), not the default folder: Windows 11 also auto-saves snips to
`Pictures\Screenshots`, which step 5 cleans. Worth taking:

1. `win-01-broken-error.png`: the error when opening model 1.
2. `win-02-fixed-open.png`: model 2 open on its report page.
3. `win-03-fix-output.png`: the `fix` output in the terminal.
4. `win-04-roastery-before.png` and `win-05-roastery-styled.png`: same page, same size.
5. Optional `win-06-bikerepair-model.png`: model 4's model view.

Write anything that did not match "Expected" word for word in
`$Root\results\notes.txt`. A failure is as useful as a pass.

## 4. Take the results off the laptop

```powershell
Copy-Item "$Root\swift-pbi-master\benchmarks\windows\CHECKLIST.md" "$Root\results\"   # after filling it in
Compress-Archive -Force -Path "$Root\results\*.txt", "$Root\results\CHECKLIST.md", "$Root\shots" -DestinationPath "$Root\windows-results.zip"
```

Move `windows-results.zip` off the laptop the way you prefer (a USB stick
leaves no trace in cloud folders). The models themselves are not needed: the
script rebuilds them identically.

## 5. Remove every trace

Close Power BI Desktop first. Then, in the same PowerShell window:

```powershell
Set-Location $HOME

# 1. The working folder: uv, Python, tools, models, results, screenshots
Remove-Item -Recurse -Force $Root

# 2. Snips Windows auto-saved
Get-ChildItem "$HOME\Pictures\Screenshots" -ErrorAction SilentlyContinue |
  Where-Object LastWriteTime -gt (Get-Date).AddDays(-1) | Remove-Item -Confirm

# 3. Recent-item shortcuts that point into the folder
Get-ChildItem "$env:APPDATA\Microsoft\Windows\Recent" -Filter *.lnk |
  Where-Object { (New-Object -ComObject WScript.Shell).CreateShortcut($_.FullName).TargetPath -like "*pbi-test*" } |
  Remove-Item

# 4. This session's commands in PowerShell history
$h = (Get-PSReadLineOption).HistorySavePath
(Get-Content $h) | Where-Object { $_ -notmatch 'pbi-test|swift-pbi|uv-|UV_|C-Kapsalis' } | Set-Content $h
```

Then by hand:

- **Power BI Desktop's recent files.** On the start screen, remove each
  `pbi-test` model from the recent list (right-click it; the option's name
  varies by version). Right-click the Desktop icon in the taskbar and remove
  the same entries from its jump list.
- **Desktop's temporary model copies.** Desktop deletes them on a normal
  close. If it crashed, delete leftover folders under
  `%LOCALAPPDATA%\Microsoft\Power BI Desktop\AnalysisServicesWorkspaces`
  (installer version) or
  `%USERPROFILE%\Microsoft\Power BI Desktop Store App\AnalysisServicesWorkspaces`
  (Store version).
- **Close the PowerShell window.** The `$env:` settings disappear with it.

Check that nothing is left:

```powershell
Test-Path "$HOME\pbi-test"                                    # False
Select-String -Path (Get-PSReadLineOption).HistorySavePath -Pattern 'pbi-test' -Quiet   # False
```

What this cannot remove: anything recorded outside the laptop's files, such
as network proxy logs, endpoint security or device-management logs, and
Windows' own event logs. Those are not yours to clear.
