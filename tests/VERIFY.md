# Verifying rate-my-cli

For each fixture (`badcli`, `wrappercli`, `goodcli`):

1. Invoke the `rate-my-cli` skill in `assess` mode against the fixture directory.
2. Open the generated `SCORECARD.md`.
3. Diff its verdicts against the fixture's `EXPECTED.md`:
   - Every "MUST report (fail)" line in EXPECTED appears as a `fail` with matching severity and kind.
   - Every "expected N/A" line appears as `na` with a reason.
   - Every "pass-by-absence" line appears as a pass with a reason.
   - For wrappercli: P9 is N/A (NOT a Blocker fail) and the suspicious-N/A warning is present.
4. A fixture passes validation when there are no mismatches. If there are, fix `rubric.md` (detection hint) or `SKILL.md` (orchestration), re-run, repeat.

Remediate-loop check: run `remediate` against a COPY of badcli and confirm only `conformance` checks were edited, `feature` checks were only proposed, and verification used read-only commands only (check the transcript: no `delete`/`create`/`prune` invocations against the fixture).
