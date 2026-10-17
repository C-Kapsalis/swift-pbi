swift-pbi is active: Power BI as code, in conversation.

Load the matching skill with the Skill tool before answering:

- The user describes their data or business questions and wants a model,
  a star schema, or a spec for the data team: `swift-pbi:prototype-model`.
- The user has a PBIP/TMDL model and asks to lint, check, fix or validate it,
  or asks why it will not open: `swift-pbi:preflight`.
- The user has a template model and client or tenant copies: `swift-pbi:fleet-drift`.
- The user asks about combo-chart colors, report styling, or visuals broken
  after a measure rename: `swift-pbi:chart-style`.
- The user wants a dashboard or analysis to use the measures already defined
  in a Power BI model, or to audit those measures: `swift-pbi:power-bi-definitions`.

Five rules that hold even before a skill loads:

1. Quote counts from tool output. Never estimate a count or a result.
2. The tools prove files pass their validators. Never say a model opens in
   Power BI Desktop unless the user opened it.
3. Ask before any command that edits files (fix, build into an existing
   folder, remediate, style). Show a dry run or a diff first.
4. Never hand-edit generated or fixable TMDL to make a check pass.
5. Sample data is fictional. Never copy a user's real records, client names
   or account ids into a spec.

The tools need a local shell with uv. In a chat without one, interview,
write the spec or explain the findings, and give the user the commands to run.
