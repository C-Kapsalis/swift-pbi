# Windows and Power BI Desktop checklist

The macOS demo proves the files pass the validators. This run proves what
Power BI Desktop does with them. Only record what you saw.

## 1. Run the script

```powershell
git clone https://github.com/C-Kapsalis/swift-pbi; cd swift-pbi
winget install astral-sh.uv          # if uv is missing; reopen the terminal after
powershell -ExecutionPolicy Bypass -File benchmarks\windows\run-windows.ps1
```

It writes `windows-run-<date>\` with the tool output (`00`–`04*.txt`), a
`models\` folder and `open-in-desktop.txt`. Copy the whole folder back.

## 2. Open each model in Desktop

If Desktop says it cannot read the project format, turn on File > Options >
Preview features > "Power BI Project (.pbip) save option" and "Store semantic
model using TMDL format", restart Desktop, and note that you had to.

For each row: open the `.pbip` (File > Open), wait for it to finish loading,
then fill in the columns. Paste error text exactly, or screenshot it.

| # | Model (under `models\`) | Expected | Opened? | Exact error, if any | Visuals render? | Refresh OK? |
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

Also note: the Power BI Desktop version (Help > About), Windows version.

## 3. Screenshots for the README and launch

1. The error dialog when opening `01-bike-shop-broken`.
2. `01-bike-shop-fixed` open on its report page.
3. The terminal output of `fix` on the broken copy (from `01-preflight.txt` is fine).
4. `04-roastery-before` and `04-roastery-styled`, same page, same size.
5. Optional: `02-BikeRepair` model view, showing the star schema.

Name them `win-01-broken-error.png`, `win-02-fixed-open.png`, and so on.

## 4. Anything unexpected

Write down anything that did not match the "Expected" column, word for word.
A failure is as useful as a pass: it becomes a fix or a documented limit.
