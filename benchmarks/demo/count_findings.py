"""Summarise a `tmdl-preflight check --json` report read from stdin.

Prints the summary counts and the number of findings per rule and severity.
Stdlib only: python3 count_findings.py < report.json
"""

import json
import sys
from collections import Counter

report = json.load(sys.stdin)
s = report["summary"]
print("summary: errors={errors} warnings={warnings} infos={infos} "
      "fixes_applied={fixes_applied}".format(**s))
print("findings: %d" % len(report["violations"]))
by_rule = Counter((v["rule"], v["severity"]) for v in report["violations"])
for (rule, sev), n in sorted(by_rule.items()):
    fixable = any(v["fixable"] for v in report["violations"] if v["rule"] == rule)
    print("  %-5s %-8s %d%s" % (rule, sev, n, "  (auto-fixable)" if fixable else ""))
