# Install

swift-pbi has two parts: the skills (instructions for your agent) and the
four command-line tools the skills run. The tools need a local shell and
[uv](https://docs.astral.sh/uv/):

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh      # macOS, Linux
winget install astral-sh.uv                           # Windows
uvx --from git+https://github.com/C-Kapsalis/tmdl-preflight@v1.1.0 tmdl-preflight --version
```

The last line prints `tmdl-preflight 1.1.0` when everything works. The four
tool repositories are public, so no GitHub credentials are needed.

## What I have tested

| Agent | Adapter | Status |
|---|---|---|
| Claude Code (CLI, Desktop Code tab) | `.claude-plugin/`, `skills/`, `hooks/` | `claude plugin validate` passes; the tools ran through uvx on macOS (see `benchmarks/demo/`). The skills have not been evaluated yet |
| Claude (web and Desktop chat) | `dist/swift-pbi-plugin.zip`, skill zips | Zip structure built locally; upload untested. No tool runs in chat |
| ChatGPT | `adapters/chatgpt/`, `dist/swift-pbi-chatgpt.zip` | Untested. No tool runs in ChatGPT |
| Codex | `.codex-plugin/plugin.json`, `.agents/plugins/marketplace.json` | Untested |
| GitHub Copilot (editor) | `.github/copilot-instructions.md` | Untested |
| Cursor | `.cursor/rules/swift-pbi.mdc` | Untested |
| Cline | `.clinerules/swift-pbi.md` | Untested |
| Kiro | `.kiro/steering/swift-pbi.md` | Untested |

If you try an untested route, please open an issue with what happened,
working or not.

## Claude Code

As two separate prompts:

```
/plugin marketplace add C-Kapsalis/swift-pbi
```
```
/plugin install swift-pbi@swift-pbi
```

The same commands work in the Code tab of Claude Desktop. A session hook
loads a short routing note and five rules; the skills load when you ask for
a model, a lint, a fleet check or chart styling.

## Claude (web and Desktop chat)

The tools cannot run here, so this route is for the conversation part:
interviewing, writing a spec, and explaining output you paste from a
terminal. Code execution must be on in Settings for skills to load.

1. Build the assets (`sh scripts/package.sh`) or download them from a release.
2. Either upload `swift-pbi-plugin.zip` in Customize > Plugins, or upload the
   skill zips you want in Customize > Skills (for example
   `swift-pbi-prototype-model-skill.zip`). Each skill zip holds one folder and
   carries a description under 200 characters.

## ChatGPT

Same limits as Claude chat: no tool runs. Upload the skill zips under
Plugins > Skills, or use `swift-pbi-chatgpt.zip` for the plugin directory
(see [PUBLISHING.md](PUBLISHING.md)). Fallback for any plan: a Project with
[`adapters/chatgpt/project-instructions.md`](adapters/chatgpt/project-instructions.md)
as instructions and the files in `adapters/chatgpt/knowledge/` attached.

## Codex

```sh
codex plugin marketplace add C-Kapsalis/swift-pbi
codex plugin add swift-pbi@swift-pbi
```

Codex also reads `AGENTS.md` from a project root, so copying it into the
project that holds your PBIP works without the plugin.

## Cursor, Copilot, Cline, Kiro

Copy the matching file into the same path in your project:
`.cursor/rules/swift-pbi.mdc`, `.github/copilot-instructions.md`,
`.clinerules/swift-pbi.md`, or `.kiro/steering/swift-pbi.md`. Each is a copy
of `AGENTS.md`. These agents can run the tools when they have terminal access.

## Any other agent

Copy [`AGENTS.md`](AGENTS.md) into its rules file, or install the folders in
`skills/` if it supports Agent Skills.

## Uninstall

| Host | How |
|---|---|
| Claude Code | `/plugin remove swift-pbi` |
| Claude chat | Customize > Plugins or Skills, then remove |
| ChatGPT | Remove the skills or the project |
| Codex | `codex plugin remove swift-pbi` |
| Rules files | Delete the copied file |

swift-pbi writes nothing outside the folders you point the tools at. uv keeps
its cache in its own folder (`uv cache clean` empties it).
