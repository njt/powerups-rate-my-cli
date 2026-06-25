# rate-my-cli Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Claude Code skill, `rate-my-cli`, that statically assesses a CLI codebase against the 10 agent-native-CLI principles and drives a conformance-fix loop, validated against fixture CLIs with known expected verdicts.

**Architecture:** A prose skill (`SKILL.md`) orchestrates three read-only subagent stages — recon (map the CLI once), fan-out (one evaluator per principle against `rubric.md`), synthesize (`SCORECARD.md` from `report-template.md`) — plus a remediate loop that auto-fixes failing `conformance` checks and proposes failing `feature` checks. Validation is e2e: fixture CLIs each ship an `EXPECTED.md` of per-check verdicts; the skill is run against them and its scorecard diffed against expectations.

**Tech Stack:** Markdown skill files; Python 3 (`argparse`) single-file fixture CLIs; `git` for per-task commits. No runtime dependencies beyond a system Python 3 and `jq` (already installed) for the read-only verification commands.

**Source of truth for the rubric:** `docs/superpowers/specs/2026-06-25-rate-my-cli-design.md` Appendix A (10 principles, ~46 checks, with Sev/Kind/Absence columns). The plan ports that table into `rubric.md` and enriches each row with a concrete static-detection hint.

---

## File structure

```
skills/rate-my-cli/
  SKILL.md            # frontmatter + orchestration (modes, stages, loop)
  rubric.md           # ~46 checks: id, assertion, Sev, Kind, Absence, Detection
  report-template.md  # SCORECARD.md skeleton with placeholders

tests/
  VERIFY.md           # how to run the e2e validation and diff verdicts
  fixtures/
    badcli/           # fails many Tier-1 conformance checks
      badcli.py
      EXPECTED.md     # expected verdict per check id
    wrappercli/       # thin upstream-API wrapper: P8 & P9 should score N/A
      wrappercli.py
      EXPECTED.md
    goodcli/          # conformant CLI: most checks pass
      goodcli.py
      EXPECTED.md
```

`SKILL.md`, `rubric.md`, `report-template.md` each have one responsibility and stay small enough to hold in context. Fixtures live with their `EXPECTED.md` (files that change together live together).

---

## Task 1: Scaffold the skill directory and SKILL.md frontmatter

**Files:**
- Create: `skills/rate-my-cli/SKILL.md`

- [ ] **Step 1: Create SKILL.md with frontmatter and a stub body**

```markdown
---
name: rate-my-cli
description: Use when asked to assess, rate, audit, or remediate a CLI codebase against agent-native CLI principles (Trevin Chow's 10 principles). Statically scores ~46 pass/fail checks across 10 principles and can drive a conformance-fix loop. Read-only assessment; never runs the target CLI's mutating commands.
---

# rate-my-cli

(Orchestration added in Tasks 4–5. Rubric in `rubric.md`. Report shape in `report-template.md`.)
```

- [ ] **Step 2: Verify the file exists and frontmatter parses**

Run: `head -5 skills/rate-my-cli/SKILL.md`
Expected: the three frontmatter lines (`name`, `description`) between `---` fences.

- [ ] **Step 3: Commit**

```bash
git add skills/rate-my-cli/SKILL.md
git commit -m "scaffold rate-my-cli skill with frontmatter"
```

---

## Task 2: Write rubric.md (the ~46 checks)

**Files:**
- Create: `skills/rate-my-cli/rubric.md`

**What to do:** Port every row of Appendix A from the spec verbatim (id, Assertion, Sev, Kind, Absence) and add one new column, **Detection** — a concrete static signal an evaluator greps/reads for. Cover all 46 ids; no row may be omitted. Keep the principle headers and the P8/P9 scope notes from the spec.

- [ ] **Step 1: Write the rubric header and legends**

```markdown
# rate-my-cli rubric

Severity: **B**=Blocker, **F**=Friction, **T**=Target.
Kind: **C**=conformance (localized edit → auto-fixable), **Ft**=feature (subsystem → propose-only).
Absence: resolution when the thing a check looks for is absent — PASS, N/A, or FAIL@severity.
Detection: how to confirm statically. Evaluators read source only; they never run the target CLI.

Verdict per check: `pass | fail | na`. Report every pass-by-absence and every N/A with its
one-line reason. Exclude N/A from the score denominator.
```

- [ ] **Step 2: Write the Tier-1 tables (P1–P5) with the Detection column**

Port P1–P5 rows from spec Appendix A; add Detection. Use this exact pattern (full P1 shown as the worked example — replicate the column shape for every principle):

```markdown
## Tier 1 — Table Stakes

### P1. Non-interactive by default

| id | Assertion | Sev | Kind | Absence | Detection |
|----|-----------|-----|------|---------|-----------|
| 1.1 | No command can block on an interactive prompt without a bypass | B | C | PASS (no prompts ⇒ non-interactive) | Grep for prompt calls: `input(`, `readline`, `inquirer`, `prompt(`, `Scanf`, `survey.`, `click.confirm`, `click.prompt`. For each, check a bypass flag (`--force`/`--yes`/`--no-input`) short-circuits it. |
| 1.2 | TTY detection treats non-TTY stdin as headless | B | C | PASS | Look for `isatty`/`sys.stdin.isatty()`/`process.stdin.isTTY` guarding any prompt. A prompt with no TTY guard fails. |
| 1.3 | A confirmation-bypass flag exists for destructive ops | F | C | N/A (no destructive ops) | Find delete/destroy/prune/reset commands; check each defines `--force`/`--yes`. |
| 1.4 | Interactive menus have a structured flag/file equivalent | F | C | PASS (no menus) | Find select/menu prompts; check a flag/file can supply the value non-interactively. |
| 1.5 | Bypass convention is consistent across subcommands (one flag name) | F | C | N/A (0–1 bypass flag) | Collect all bypass flag names; fail if mixed (`--force` here, `--yes` there). |
```

Then do P2, P3, P4, P5 the same way, porting Sev/Kind/Absence from Appendix A and writing a Detection cell for each. Detection hints to use:
- **2.1** grep for a `--json`/`json.dumps`/`JSON.stringify` path on any data command. **2.2** count data commands vs those wiring `--json`. **2.3** grep flag names: fail if `--format`/`--output`/`-o json` coexist with `--json`. **2.4** inspect exit paths: `sys.exit`/`os.Exit`/`process.exit` — fail@B if all exits are 0. **2.5** check data prints to stdout and errors/logs to stderr (`sys.stderr`, `console.error`, `fmt.Fprintln(os.Stderr,...)`). **2.6** grep for color libs (`colorama`, `chalk`, ANSI escapes) guarded by an isatty/`NO_COLOR` check.
- **3.1** error paths print a message (not bare traceback/`panic`); **3.2** validation occurs before any write/network side effect in the handler; **3.3** enum/choices rejections include the allowed set in the message (look at `choices=` / switch defaults); **3.4** error text includes a corrective example/usage.
- **4.1** create handlers accept an idempotency key or use a natural key (often N/A — note when create is the upstream API's job); **4.2** destructive handlers require a non-default flag before acting; **4.3** consequential handlers honor `--dry-run`; **4.4** mutation responses include the affected id.
- **5.1** list handlers apply a default limit/page size; **5.2** list handlers accept filter + cursor/page; **5.3** truncated responses set a `truncated` flag + narrowing hint; **5.4** if an MCP server/tool-description surface exists, each description is short and budget-audited (else N/A).

- [ ] **Step 3: Write the Tier-2 tables (P6–P10) with the Detection column**

Port P6–P10 rows from Appendix A (including the P8 "entire principle N/A if no async API" note and the P9 non-auth-scope note). Detection hints:
- **6.1** scan command/verb names for banned verbs (`info`,`ls`,`rm`,`new`,`show` where `get`/`list`/`delete`/`create` is conventional); **6.2** scan flag names for `--skip-*`, `--format=json`, `--no-confirm` aliases; **6.3** compare naming across subcommands for internal drift; **6.4** look for a documented naming policy + a CI/lint check enforcing it.
- **7.1** look for a machine introspection command (`agent-context`, `--schema`, `dump-schema`) emitting structured command/flag JSON; **7.2** that output carries a `schema_version`; **7.3** a long-form `SKILL.md`/skills dir teaches workflows; **7.4** introspection is generated from / validated against the real command tree (codegen, test).
- **8.1** async-submitting commands (return a job id / `status: queued`) offer `--wait`; **8.2** poll loop uses exponential backoff + jitter; **8.3** a persistent job ledger file is written; **8.4** a `jobs` command exposes `list`/`get`/`prune`. All N/A if no async API is wrapped.
- **9.1** detect a recurring **non-auth** flag cluster across commands with no persistence (profiles/named config); N/A if only auth/credentials persist or there's no recurring non-auth config; **9.2** `profile save/use/list/show/delete` subcommands; **9.3** `--profile` root flag + precedence flag>env>profile>default; **9.4** profiles appear in machine introspection; **9.5** stable documented storage path.
- **10.1** a `feedback <text>` command writing local JSONL; **10.2** optional upstream POST gated on a configured endpoint, discoverable; **10.3** artifact-producing commands support `--deliver` (stdout/file/webhook); **10.4** file sinks write atomically + unknown schemes get a structured refusal; **10.5** deliver+feedback appear in machine introspection.

- [ ] **Step 4: Self-check coverage — all 46 ids present**

Run: `grep -oE '^\| [0-9]+\.[0-9]+ ' skills/rate-my-cli/rubric.md | wc -l`
Expected: `46` (the count in spec Appendix A "Totals").

- [ ] **Step 5: Commit**

```bash
git add skills/rate-my-cli/rubric.md
git commit -m "add rate-my-cli rubric: 46 checks with static detection hints"
```

---

## Task 3: Write report-template.md

**Files:**
- Create: `skills/rate-my-cli/report-template.md`

- [ ] **Step 1: Write the template**

```markdown
# CLI Agent-Nativeness Scorecard

**Target:** {{target_path}}
**Date:** {{date}}
**Score:** {{passes}} / {{applicable}} applicable checks ({{percent}}%)
**Failing gaps:** {{n_blocker}} Blocker · {{n_friction}} Friction · {{n_target}} Target
{{suspicious_na_warning}}   <!-- present only if a whole principle returned N/A -->

## Per-principle results

<!-- One block per principle P1..P10 -->
### {{principle_id}}. {{principle_name}}

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| {{id}} {{assertion}} | {{pass/fail/na}} | {{sev_if_fail}} | {{kind}} | {{file:line or absence reason}} |

## Remediation plan

### Auto-fixable now (failing `conformance` checks, Blockers first)
- [ ] {{id}} — {{fix_hint}}  ({{file:line}})

### Friction (conformance, lower priority)
- [ ] {{id}} — {{fix_hint}}

### Proposals — features, not auto-built (failing `feature` checks)
- {{id}} — {{what it would take}}; requires your go-ahead.
```

- [ ] **Step 2: Commit**

```bash
git add skills/rate-my-cli/report-template.md
git commit -m "add rate-my-cli scorecard template"
```

---

## Task 4: Write SKILL.md — assess mode (recon → fan-out → synthesize)

**Files:**
- Modify: `skills/rate-my-cli/SKILL.md`

- [ ] **Step 1: Replace the stub body with the assess-mode orchestration**

Append after the frontmatter (replace the stub line). Use this content:

````markdown
# rate-my-cli

Assess a CLI codebase against the 10 agent-native principles, and optionally
remediate. **Two modes:** `assess` (default, read-only) and `remediate` (loop).

## Hard constraints
- Assessment is **static only** — never run the target CLI during assessment.
- The recon agent and all evaluators are **read-only**: dispatch them as the
  `Explore` agent type.
- Score = passes / (passes + fails), **excluding N/A**.

## Mode: assess

### Stage 1 — Recon (one read-only agent)
Dispatch one `Explore` agent to map the CLI once and return a recon map:
entry point & arg-parsing framework; command/subcommand tree; where flags are
declared; where output is serialized; where errors are built; config/profile
storage; async/job code; MCP wrapper (if any); build/codegen/schema layer;
whether the CLI is a thin upstream-API wrapper (auth-only state).
If no CLI entry point is found, STOP and report that — do not produce a scorecard.

### Stage 2 — Fan-out (10 read-only agents, parallel)
Dispatch one `Explore` agent per principle (P1–P10) in a single message so they
run concurrently. Give each: the recon map + that principle's section of
`rubric.md`. Each returns a JSON array of findings, one per check id:
`{check_id, verdict: pass|fail|na, severity, kind, evidence, fix_hint}`.
Evaluators apply the Absence column mechanically and always include a one-line
reason for pass-by-absence and N/A.

### Stage 3 — Synthesize
Collect all findings. Render `report-template.md` → write `SCORECARD.md` in the
target repo root. Compute score excluding N/A. If any whole principle is entirely
N/A, set the suspicious-N/A warning. Group the remediation plan by kind then
severity exactly as the template lays out.
````

- [ ] **Step 2: Verify the section renders and references resolve**

Run: `grep -c 'Stage [123]' skills/rate-my-cli/SKILL.md`
Expected: `3`

- [ ] **Step 3: Commit**

```bash
git add skills/rate-my-cli/SKILL.md
git commit -m "add assess mode orchestration to rate-my-cli SKILL"
```

---

## Task 5: Write SKILL.md — remediate mode (the loop)

**Files:**
- Modify: `skills/rate-my-cli/SKILL.md`

- [ ] **Step 1: Append the remediate-mode section**

````markdown
## Mode: remediate

A loop that closes conformance gaps and proposes feature gaps. Gate on **kind**,
not severity.

1. Run `assess` to get the current scorecard.
2. **Auto-fix every failing `conformance` check**, Blockers first. These are
   localized source edits only — add `--json`, add `--force`/`--yes`, add an
   `isatty` guard, enumerate the valid set in an enum error, route data→stdout /
   diagnostics→stderr, rename off-convention verbs/flags. One fix per commit.
   **Never** auto-fix a `feature` check.
3. **Verify each fix by running read-only commands ONLY** — `--help`, `list`,
   `get`, anything with `--json` or `--dry-run`. Never run a mutating/destructive
   command. If a fix can't be verified read-only, re-read the code to confirm.
4. Re-assess to confirm the check cleared and catch regressions.
5. Repeat until no failing `conformance` checks remain.
6. **Stop. Present every failing `feature` check as a proposal** (profile system,
   async ledger + `--wait`, `agent-context`, skill manifest, `feedback`,
   `--deliver`, naming-policy CI check), ordered by severity. Do not build these
   without explicit go-ahead.
````

- [ ] **Step 2: Verify both modes are present**

Run: `grep -E '^## Mode:' skills/rate-my-cli/SKILL.md`
Expected: two lines — `## Mode: assess` and `## Mode: remediate`.

- [ ] **Step 3: Commit**

```bash
git add skills/rate-my-cli/SKILL.md
git commit -m "add remediate loop to rate-my-cli SKILL"
```

---

## Task 6: Build the `badcli` fixture + expected verdicts (the failing test)

**Files:**
- Create: `tests/fixtures/badcli/badcli.py`
- Create: `tests/fixtures/badcli/EXPECTED.md`

**Purpose:** A CLI that deliberately fails many Tier-1 conformance checks so we can confirm the assessor catches them.

- [ ] **Step 1: Write badcli.py**

```python
#!/usr/bin/env python3
"""A deliberately non-agent-native CLI for testing rate-my-cli."""
import argparse, sys

def cmd_info(args):           # 6.1: should be `get`
    print(f"post {args.id}: hello (visibility={args.visibility})")  # 2.1: no JSON; 2.5: to stdout only

def cmd_ls(args):             # 6.1: should be `list`
    for i in range(100):      # 5.1: unbounded, no default limit
        print(f"post_{i}")

def cmd_delete(args):
    # 1.1: interactive prompt with no bypass flag, no isatty guard (1.2)
    if input(f"Delete {args.id}? [y/N]: ").lower() != "y":
        return
    print("deleted")          # 4.4: no id returned; 4.2: no required force flag

def cmd_create(args):
    if args.visibility not in ("public", "private"):
        print("error: invalid visibility")  # 3.3: no valid set enumerated
        sys.exit(0)           # 2.4: exit 0 on failure
    print(f"created with {args.visibility}")

def main():
    p = argparse.ArgumentParser(prog="badcli")
    sub = p.add_subparsers(required=True)
    a = sub.add_parser("info"); a.add_argument("id"); a.add_argument("--visibility", default="public"); a.set_defaults(f=cmd_info)
    b = sub.add_parser("ls"); b.set_defaults(f=cmd_ls)
    c = sub.add_parser("delete"); c.add_argument("id"); c.set_defaults(f=cmd_delete)
    d = sub.add_parser("create"); d.add_argument("--visibility", default="public"); d.set_defaults(f=cmd_create)
    args = p.parse_args(); args.f(args)

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Write EXPECTED.md (the assertion this fixture is the test for)**

```markdown
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
```

- [ ] **Step 3: Sanity-check the fixture runs (read-only command only)**

Run: `python3 tests/fixtures/badcli/badcli.py ls | head -3`
Expected: `post_0` / `post_1` / `post_2`.

- [ ] **Step 4: Commit**

```bash
git add tests/fixtures/badcli/
git commit -m "add badcli fixture and expected verdicts"
```

---

## Task 7: Build the `wrappercli` fixture + expected verdicts

**Files:**
- Create: `tests/fixtures/wrappercli/wrappercli.py`
- Create: `tests/fixtures/wrappercli/EXPECTED.md`

**Purpose:** A thin upstream-API wrapper whose only persistent state is auth — must score **P9 N/A** (not Blocker) and **P8 N/A**, confirming the D9 rescope works.

- [ ] **Step 1: Write wrappercli.py**

```python
#!/usr/bin/env python3
"""Thin wrapper over an upstream API. Auth via env; everything else per-call.
Conformant on Tier-1 basics so P9/P8 N/A is the interesting signal."""
import argparse, json, os, sys

def _client():
    token = os.environ.get("UPSTREAM_TOKEN")
    if not token:
        print("error: set UPSTREAM_TOKEN (get one at https://upstream.example/tokens)", file=sys.stderr)
        sys.exit(2)
    return token

def cmd_get(args):
    _client(); print(json.dumps({"id": args.id, "title": "demo"}))

def cmd_list(args):
    _client(); print(json.dumps({"items": [{"id": "t1"}, {"id": "t2"}], "truncated": False}))

def main():
    p = argparse.ArgumentParser(prog="wrappercli")
    sub = p.add_subparsers(required=True)
    g = sub.add_parser("get"); g.add_argument("id"); g.add_argument("--json", action="store_true"); g.set_defaults(f=cmd_get)
    l = sub.add_parser("list"); l.add_argument("--limit", type=int, default=20); l.add_argument("--json", action="store_true"); l.set_defaults(f=cmd_list)
    args = p.parse_args(); args.f(args)

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Write EXPECTED.md**

```markdown
# wrappercli — expected verdicts

The point of this fixture: identity is upstream (auth via env), commands are
per-call. P9 must be N/A, not a Blocker fail.

- 9.1 na — auth-only persistent state; no recurring non-auth config bundle
- 9.2–9.5 na — no profiles needed
- P8 all na — no async API wrapped
- 6.1 pass — verbs are `get`/`list`
- 2.1 pass — `--json` present; output is JSON
- 3.3 pass-by-absence or pass — auth error names where to get a token (3.4)
- Suspicious-N/A: P8 and P9 fully N/A is expected here, but the scorecard must
  still SHOW the warning so the reviewer can confirm it's legitimate.
```

- [ ] **Step 3: Sanity-check (read-only command)**

Run: `UPSTREAM_TOKEN=x python3 tests/fixtures/wrappercli/wrappercli.py list --json | jq '.items[0].id'`
Expected: `"t1"`

- [ ] **Step 4: Commit**

```bash
git add tests/fixtures/wrappercli/
git commit -m "add wrappercli fixture (P9/P8 N/A case)"
```

---

## Task 8: Build the `goodcli` fixture + expected verdicts

**Files:**
- Create: `tests/fixtures/goodcli/goodcli.py`
- Create: `tests/fixtures/goodcli/EXPECTED.md`

**Purpose:** A conformant CLI so we confirm the assessor reports passes, not just failures (guards against an over-eager evaluator that fails everything).

- [ ] **Step 1: Write goodcli.py**

```python
#!/usr/bin/env python3
"""A conformant agent-native CLI fixture."""
import argparse, json, sys

VIS = ("public", "private", "unlisted")

def cmd_get(args):
    print(json.dumps({"id": args.id, "visibility": "public"}))

def cmd_list(args):
    items = [{"id": f"post_{i}"} for i in range(args.limit)]
    print(json.dumps({"posts": items, "truncated": True, "hint": "use --limit / --cursor"}))

def cmd_create(args):
    if args.visibility not in VIS:
        print(f"error: --visibility must be one of: {', '.join(VIS)} (got: {args.visibility!r})", file=sys.stderr)
        sys.exit(4)
    print(json.dumps({"id": "post_8f2a", "existing": False}))

def cmd_delete(args):
    if not args.force:
        print("error: refusing to delete without --force", file=sys.stderr); sys.exit(3)
    if args.dry_run:
        print(json.dumps({"would_delete": args.id, "status": "dry_run"})); return
    print(json.dumps({"deleted": args.id}))

def main():
    p = argparse.ArgumentParser(prog="goodcli")
    sub = p.add_subparsers(required=True)
    g = sub.add_parser("get"); g.add_argument("id"); g.add_argument("--json", action="store_true"); g.set_defaults(f=cmd_get)
    l = sub.add_parser("list"); l.add_argument("--limit", type=int, default=20); l.add_argument("--cursor"); l.add_argument("--json", action="store_true"); l.set_defaults(f=cmd_list)
    c = sub.add_parser("create"); c.add_argument("--visibility", default="public"); c.add_argument("--json", action="store_true"); c.set_defaults(f=cmd_create)
    d = sub.add_parser("delete"); d.add_argument("id"); d.add_argument("--force", action="store_true"); d.add_argument("--dry-run", action="store_true"); d.add_argument("--json", action="store_true"); d.set_defaults(f=cmd_delete)
    args = p.parse_args(); args.f(args)

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Write EXPECTED.md**

```markdown
# goodcli — expected verdicts

Mostly passes on Tier 1. Remaining gaps are Tier-2 features.
- 1.1 pass-by-absence — no prompts (delete gated by --force)
- 2.1 pass · 2.4 pass (exit 3/4 on failure) · 2.5 pass (errors→stderr)
- 3.3 pass — create enumerates the valid set
- 4.2 pass (--force required) · 4.3 pass (--dry-run) · 4.4 pass (id returned)
- 5.1 pass (default limit) · 5.3 pass (truncated + hint)
- 6.1 pass · 6.2 pass
- 7.1 fail B Ft — no agent-context (feature → proposal, not auto-fixed)
- 9.1 na — no recurring non-auth config; 10.1 fail B Ft — no feedback channel (feature)
```

- [ ] **Step 3: Sanity-check (read-only commands)**

Run: `python3 tests/fixtures/goodcli/goodcli.py create --visibility=secret; echo "exit=$?"`
Expected: stderr line naming `public, private, unlisted` and `exit=4`.

- [ ] **Step 4: Commit**

```bash
git add tests/fixtures/goodcli/
git commit -m "add goodcli fixture (conformant baseline)"
```

---

## Task 9: Write tests/VERIFY.md (the validation procedure)

**Files:**
- Create: `tests/VERIFY.md`

- [ ] **Step 1: Write the procedure**

```markdown
# Verifying rate-my-cli

For each fixture (`badcli`, `wrappercli`, `goodcli`):

1. Invoke the `rate-my-cli` skill in `assess` mode against the fixture directory.
2. Open the generated `SCORECARD.md`.
3. Diff its verdicts against the fixture's `EXPECTED.md`:
   - Every "MUST report (fail)" line in EXPECTED appears as a `fail` with matching
     severity and kind.
   - Every "expected N/A" line appears as `na` with a reason.
   - Every "pass-by-absence" line appears as a pass with a reason.
   - For wrappercli: P9 is N/A (NOT a Blocker fail) and the suspicious-N/A warning
     is present.
4. A fixture passes validation when there are no mismatches. If there are,
   fix `rubric.md` (detection hint) or `SKILL.md` (orchestration), re-run, repeat.

Remediate-loop check (Task 13): run `remediate` against a COPY of badcli and
confirm only `conformance` checks were edited, `feature` checks were only
proposed, and verification used read-only commands only (check the transcript:
no `delete`/`create`/`prune` invocations against the fixture).
```

- [ ] **Step 2: Commit**

```bash
git add tests/VERIFY.md
git commit -m "add e2e verification procedure for rate-my-cli"
```

---

## Task 10: E2E validation run — badcli

**Files:** none created; this exercises the skill and may drive fixes to `rubric.md` / `SKILL.md`.

- [ ] **Step 1: Run assess on badcli**

Invoke the `rate-my-cli` skill, `assess` mode, target `tests/fixtures/badcli`. It writes `tests/fixtures/badcli/SCORECARD.md`.

- [ ] **Step 2: Diff against EXPECTED.md**

Per `tests/VERIFY.md` step 3. Expected: every MUST-fail check in `badcli/EXPECTED.md` is reported as `fail` with matching Sev/Kind; P8 + 9.1 + 5.4 are N/A; 1.4 is pass-by-absence.

- [ ] **Step 3: If mismatches, fix and re-run**

Edit the offending Detection hint in `rubric.md` or orchestration in `SKILL.md`, commit the fix, re-run Step 1. Loop until zero mismatches.

- [ ] **Step 4: Commit the validated scorecard as a golden reference**

```bash
git add tests/fixtures/badcli/SCORECARD.md skills/rate-my-cli/
git commit -m "validate rate-my-cli against badcli; golden scorecard"
```

---

## Task 11: E2E validation run — wrappercli

**Files:** none created (may drive fixes).

- [ ] **Step 1: Run assess on wrappercli** (target `tests/fixtures/wrappercli`).

- [ ] **Step 2: Diff against EXPECTED.md**, focusing on the P9-N/A behavior.
Expected: 9.1 is `na` with reason "auth-only state"; P8 all `na`; the suspicious-N/A warning is present; verbs pass 6.1.

- [ ] **Step 3: If P9 came back as a Blocker fail**, the rubric's 9.1 detection/absence handling is wrong — fix `rubric.md` so auth-only state resolves to N/A, commit, re-run.

- [ ] **Step 4: Commit the validated scorecard**

```bash
git add tests/fixtures/wrappercli/SCORECARD.md skills/rate-my-cli/
git commit -m "validate rate-my-cli against wrappercli (P9 N/A)"
```

---

## Task 12: E2E validation run — goodcli

**Files:** none created (may drive fixes).

- [ ] **Step 1: Run assess on goodcli** (target `tests/fixtures/goodcli`).

- [ ] **Step 2: Diff against EXPECTED.md.** Expected: Tier-1 checks pass; 7.1 and 10.1 are `fail` with kind `Ft`; the remediation plan lists 7.1/10.1 under **Proposals**, not under auto-fixable.

- [ ] **Step 3: If a passing check was reported as fail** (over-eager evaluator), tighten the Detection hint in `rubric.md`, commit, re-run.

- [ ] **Step 4: Commit the validated scorecard**

```bash
git add tests/fixtures/goodcli/SCORECARD.md skills/rate-my-cli/
git commit -m "validate rate-my-cli against goodcli (conformant baseline)"
```

---

## Task 13: E2E validation — remediate loop on a badcli copy

**Files:**
- Create: `tests/fixtures/badcli-remediate/` (copy of badcli)

- [ ] **Step 1: Copy the fixture**

```bash
cp -r tests/fixtures/badcli tests/fixtures/badcli-remediate
rm -f tests/fixtures/badcli-remediate/SCORECARD.md
```

- [ ] **Step 2: Run remediate mode** against `tests/fixtures/badcli-remediate`.

- [ ] **Step 3: Verify loop behavior against the EXPECTED contract**

Confirm:
- Conformance fails (1.1, 1.2, 2.1, 2.4, 3.3, 4.2, 4.4, 5.1, 6.1) were **edited** in `badcli.py` (e.g. `--json` added, `ls`→`list`, `info`→`get`, `--force` required, `input()` guarded/bypassed, exit non-zero on failure).
- Any `feature` check was **only proposed**, not built.
- Verification ran **read-only commands only** — inspect the session transcript and confirm no `delete`/`create` invocation hit the fixture (a final `list --json`/`--help` is fine).

Run (after loop): `python3 tests/fixtures/badcli-remediate/badcli.py list --json | jq '.posts | length'`
Expected: a bounded number (the default limit), proving 5.1 + 2.1 + 6.1 were fixed.

- [ ] **Step 4: Commit**

```bash
git add tests/fixtures/badcli-remediate/
git commit -m "validate rate-my-cli remediate loop (conformance-only auto-fix)"
```

---

## Task 14: README and final self-review

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write a short README** documenting: what the skill does, the two modes, the read-only/static safety guarantees, how to install the skill, and how to run the fixtures (`tests/VERIFY.md`).

- [ ] **Step 2: Spec-coverage self-review** — confirm every spec section maps to a task: D1 static (Task 4 hard constraints), D2 scoring (Task 2/3), D3 deliverable (Task 3), D4 architecture (Task 4), D5 absence (Task 2), D6/D8 kind gate (Task 5), D7 read-only verify (Task 5/13), D9 P9 scope (Task 2/7/11). Note any gap and add a task.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "add README and complete rate-my-cli skill"
```

---

## Notes for the implementer
- **Do not run the target CLI's mutating commands at any point.** Read-only commands (`--help`, `list`, `get`, `--json`, `--dry-run`) are the only execution allowed, and only during remediate verification — never during assessment.
- Fixtures are intentionally tiny single-file Python CLIs so verdicts are easy to eyeball against `EXPECTED.md`.
- The rubric's master copy is the spec's Appendix A; if you change a Sev/Kind/Absence value, update the spec too so they don't drift.
- Per Nat's workflow: commit after every task; run `/roborev-fix` after Tasks 5 and 14.
