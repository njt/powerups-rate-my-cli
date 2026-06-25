# badcli — expected verdicts

Key failing checks the assessor MUST report (verdict: fail):
- 1.1 fail B C — `delete` prompts via `input()` with no bypass (badcli.py: cmd_delete)
- 1.2 fail B C — no isatty guard on the prompt
- 2.1 fail B C — no `--json` anywhere
- 2.4 fail B C(→B) — `sys.exit(0)` on the create error path
- 3.3 fail F C — "invalid visibility" without the valid set
- 4.2 fail B C — `delete` acts without a required `--force`
- 4.4 fail F C — `delete` returns no id
- 5.1 fail B C — `ls` dumps 100 rows, no default limit
- 6.1 fail B C — verbs `info` (→get) and `ls` (→list)

Expected N/A (with reason):
- P8 all — no async API wrapped
- P9 9.1 — no recurring non-auth config (no profiles needed)
- 5.4 — no MCP wrapper

Expected pass-by-absence:
- 1.4 — no interactive menus
