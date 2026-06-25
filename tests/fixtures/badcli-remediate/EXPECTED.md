# badcli-remediate — expected POST-remediation state

This is the output of running `rate-my-cli` in **remediate** mode against a copy
of `badcli`. It documents the expected state *after* the conformance-fix loop,
not the original failing state (see `../badcli/EXPECTED.md` for the before).

## Conformance checks that must now PASS (auto-fixed by the loop)
- 1.1 — `delete` no longer blocks: prompt is bypassed by `--force` and guarded by isatty
- 1.2 — prompt guarded by `sys.stdin.isatty()`
- 2.1 — `--json` emits structured output on data commands
- 2.4 — failure paths exit non-zero (not `sys.exit(0)`)
- 2.5 — errors routed to stderr
- 3.3 — invalid `--visibility` enumerates the valid set
- 4.2 — `delete` requires an explicit non-default `--force`
- 4.4 — `delete` returns the affected id
- 5.1 — `list` has a bounded default limit (20)
- 6.1 — verbs renamed `info`→`get`, `ls`→`list`

## Feature checks that must remain (NOT built — proposals only)
- 7.1 — machine-readable introspection (`agent-context`): still absent
- 10.1 — `feedback` channel: still absent
- 5.2 / 6.4 / 7.3 — pagination, naming-policy CI, skill manifest: still absent

## Read-only post-conditions (no mutating commands run)
- `badcli.py --help` lists `get` and `list` (not `info`/`ls`)
- `badcli.py list --json | jq '.posts | length'` returns the bounded default (20)
- `badcli.py get <id> --json` emits JSON
- code shows `delete` requires `--force`, returns id, isatty-guarded prompt;
  `create` enumerates the valid set and exits non-zero on bad input
