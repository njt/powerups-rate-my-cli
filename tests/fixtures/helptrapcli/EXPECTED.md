# helptrapcli — expected verdicts

The point of this fixture: **7.6 must FAIL**. It mirrors goodcli's surface
(get/list/create/delete, `--json`, `--force`, `--dry-run`, bounded list) and
even its handlers, but the dispatch is hand-rolled: root command lookup with no
help path, and per-command argparse parsers built with `add_help=False` and
consumed via `parse_known_args`. Every other verdict matches goodcli's, so an
evaluator that rubber-stamps "argparse ⇒ pass" on 7.6 has exactly one place to
be wrong — this is the under-eager guard, the counterpart to goodcli's
over-eager guard.

Key failing check the assessor MUST report:
- 7.6 fail B C — root dispatch never checks `-h`/`--help` (`helptrapcli --help`
  ⇒ "unknown command", exit 2, no usage); every subcommand parser sets
  `add_help=False` and parses via `parse_known_args` (helptrapcli.py:32,41), so
  `--help` is silently discarded into the extras and the action executes —
  `helptrapcli delete X --force --help` deletes (verified live). Two of the
  rubric row's named argparse suppression tells, plus the catastrophic
  never-executes violation.

Other expected fails (same as goodcli — features → proposals, not auto-fixed):
- 7.1 fail B Ft — no agent-context
- 10.1 fail B Ft — no feedback channel
- 7.5 fail F Ft — no `version` command
- 6.4 fail T Ft — no naming-policy CI; 7.3 fail T Ft — no skill manifest

Expected pass (guard against over-eager failing): 1.1–1.4 (no prompts; `--force`
gates delete), 2.1–2.7 (`--json` everywhere, exit 2/3/4 on failure,
errors→stderr, no secret-shaped fields), 3.1–3.4 (create enumerates the valid
set; unknown-command error names the valid commands), 4.1–4.4, 5.1–5.3, 6.1–6.3.

Expected N/A (with reason): 1.5 (one bypass flag), 3.3 is a PASS not N/A (enum
exists), 5.4 (no MCP wrapper), 7.2/7.4 (7.1 fails), P8 all (no async API),
P9 all (no persistent config), 10.2–10.5 (10.1 fails / no artifacts).
Suspicious-N/A warning for P8/P9 must still be shown.

Remediate note: 7.6 is **conformance** — the loop must auto-fix it (restore real
argparse subparsers, or drop `add_help=False`/`parse_known_args` and route
`-h`/`--help` to help before dispatch), unlike the feature proposals above.
