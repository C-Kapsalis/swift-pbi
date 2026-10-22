# Publishing

How swift-pbi would get into public plugin directories. Nothing has been
submitted. Each step is done by hand by the maintainer; vendor requirements
change, so re-read their pages before submitting.

## Before any submission

1. The four tool repositories (tmdl-preflight, pbip-model-forge,
   tmdl-drift-doctor, pbi-plot-styler) are public, with tag `v1.2.0`. Until
   then `uvx --from git+https://...@v1.2.0` fails for anyone without access,
   and every skill fails with it.
2. This repository is public.
3. Validate the Claude plugin and the skills:
   ```sh
   claude plugin validate .
   claude plugin validate --strict .claude-plugin/plugin.json
   claude plugin validate --strict .claude-plugin/marketplace.json
   ```
4. Adapter copies are current: `python3 scripts/sync-adapters.py --check`.
5. Re-run the demo and compare with the README numbers:
   `sh benchmarks/demo/run-all.sh`, then `git diff benchmarks/demo/output/`
   (only UUIDs and dates should change).
6. Build the release assets and attach them to a GitHub Release:
   `sh scripts/package.sh` (writes `dist/`).
7. Re-read the README against the editorial checklist: every number traces to
   a file in `benchmarks/demo/output/`; no client or employer material; the
   "not affiliated" line is present.

## Claude plugin directory

Submit from claude.ai (directory management, plugin bundle) with the GitHub
repository as the source and the repo root as the plugin path. Data handling
answers for swift-pbi: it reads the model folders the user points it at,
stores nothing outside them, sends no data to any service except fetching
the pinned tool releases from GitHub through uv, and is not aimed at minors.

## ChatGPT plugin directory

Package: `dist/swift-pbi-chatgpt.zip` (a `plugin.json`, `skills/`, `LICENSE`,
no hooks). Say plainly in the listing that the tools need a local shell and
that in ChatGPT the skills interview, write specs and explain pasted output.

## Codex

The repository already works as a Codex marketplace
(`.agents/plugins/marketplace.json`); no submission is needed for
`codex plugin marketplace add C-Kapsalis/swift-pbi`.
