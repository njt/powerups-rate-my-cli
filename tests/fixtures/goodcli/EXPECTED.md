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
