# wrappercli — expected verdicts

The point of this fixture: identity is upstream (auth via env), commands are
per-call. P9 must be N/A, not a Blocker fail.

- 9.1 na — auth-only persistent state; no recurring non-auth config bundle
- 9.2–9.5 na — no profiles needed
- P8 all na — no async API wrapped
- 6.1 pass — verbs are `get`/`list`
- 2.1 pass — `--json` present; output is JSON
- 3.3 na — no enum/choices inputs (corrective-guidance credit is 3.4, which passes)
- 3.4 pass — auth error names where to get a token
- Suspicious-N/A: P8 and P9 fully N/A is expected here, but the scorecard must
  still SHOW the warning so the reviewer can confirm it's legitimate.
