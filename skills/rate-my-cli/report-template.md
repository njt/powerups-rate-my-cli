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
