# Contributing

Thanks for reading this far. The most useful contributions, in order:

1. **A model where a tool is wrong.** A TMDL file that tmdl-preflight flags
   but Power BI Desktop opens, or one it passes that Desktop refuses; a drift
   finding that is not drift; a spec the forge accepts that builds a broken
   model. Open an issue on the tool's own repository with a minimal,
   fictional reproduction.
2. **A case where a skill misleads.** The agent claimed something the tool
   output did not say, skipped a consent step, or put real data in a spec.
   Open an issue here with the conversation (remove anything private), the
   host and the model.
3. **A report from another agent.** Most adapters are untested (see
   [INSTALL.md](INSTALL.md)).
4. **A Windows run of the demo.** `benchmarks/demo/` has only been run on
   macOS. Output from Git Bash or WSL, with the exact versions, helps.

## Rules for examples and fixtures

Use fictional businesses, people and ids, and `.example` domains. Never add a
model, a screenshot or a number from a client or an employer, even
"anonymised".

## Before you open a pull request

- Edit `AGENTS.md` and the skills, not the generated copies, then run
  `python3 scripts/sync-adapters.py` (`--check` to verify).
- Keep each `SKILL.md` under about 250 lines, with numbered steps and exact
  commands, so smaller models can follow it.
- Run `claude plugin validate .`.
- If you change a number in the README, re-run `sh benchmarks/demo/run-all.sh`
  and commit the new output with it.
- Plain writing: short sentences, no em-dashes, no hype words.

## Disagreeing

If you think a number or a comparison in the README is wrong, say so in an
issue with the evidence. I will try to reproduce it and update the README
either way.
