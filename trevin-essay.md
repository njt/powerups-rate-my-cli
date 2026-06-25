# 10 Principles for Agent-Native CLIs

**Trevin Chow** ([@trevin](https://x.com/trevin)) · May 5, 2026

---

Last month I wrote 7 Principles for Agent-Friendly CLIs. Since then I've been deep in CLI work, watching agents use them, and seeing them break in interesting ways.

Mid-April, [@Cloudflare](https://x.com/Cloudflare) published *The CLI for all of Cloudflare*, describing how they rebuilt Wrangler around a TypeScript schema that generates the CLI, the SDKs, the Terraform provider, and the MCP server from one source. Their Code Mode MCP serves their entire ~3,000-operation API in under 1,000 tokens. They added `/cdn-cgi/explorer/api`, an OpenAPI-shaped runtime endpoint for agents. And they enforce naming rules across the entire CLI surface: always `get`, never `info`; always `--force`, never `--skip-confirmations`; always `--json`. Their framing for why: "manually enforcing consistency through reviews is Swiss cheese."

Shortly after, [@HeyGen](https://x.com/HeyGen) launched their CLI, and I've been using it heavily since. Generating videos through agents, polling jobs, routing artifacts to webhooks. The practical experience is what earned it a spot here. Plenty of companies ship CLIs; this one's been the most agent-pleasant I've used.

The original 7 principles I wrote about were defensive: the things a CLI has to get right, or agents pay for it on every call. Don't hang on a TTY check, return JSON, make errors actionable, bound the output. That layer is still necessary but not enough.

The next layer is about compounding instead of not breaking. The CLI gets more useful the more agents use it, because agents come with persistent identity, asynchronous workflows, output that has to land somewhere, and friction that maintainers should hear about.

The 10 principles below come from my own CLI work (new project coming soon!) alongside what Cloudflare and HeyGen have published. Organized into 2 tiers. Five condense the original seven and five are new.

---

## Tier 1: Table Stakes

> Don't break the agent. Agents are good at figuring things out, but when these aren't met, the deck is stacked against them. Every gap costs more tokens, more retries, and more failure modes that don't surface until production.

### 1. Non-interactive by default

Commands have to run without interactive prompts when an agent invokes them. When a subagent spawns a background process, there's nothing answering the prompt. The command hangs.

```bash
# Hangs forever waiting for a confirmation that will never come
$ mycli post delete post_8f2a < /dev/null
Are you sure you want to delete post_8f2a? [y/N]: ^C

# With --force: bypasses the prompt, agent gets through cleanly
$ mycli post delete post_8f2a --force
{"deleted":"post_8f2a"}
```

**What good looks like:** `--no-input` or equivalent on every command that might prompt; honest TTY detection that treats non-TTY as headless; `--yes` for confirmation bypass; structured input via flags or files for anything you used to collect through interactive menus. Cloudflare standardizes on `--force` for destructive bypass and explicitly bans `--skip-confirmations`. Pick the convention, then enforce it.

- **Blocker:** Silent hanging on a prompt
- **Friction:** Inconsistent prompt-bypass behavior across subcommands
- **Target:** A comprehensive non-interactive mode the agent can rely on without per-command lookups

---

### 2. Structured, parseable output

A nicely aligned table with ANSI colors is for humans. An agent extracting a post ID needs JSON.

```bash
# Data on stdout, parseable directly with jq
$ mycli post list --json | jq '.posts[0].id'
"post_8f2a"

# Errors go to stderr, exit codes signal failure class
$ mycli post get post_does_not_exist --json
$ echo $?
4
# stderr → "error: post not found: post_does_not_exist"
```

**What good looks like:** `--json` on every data-returning command; exit code `0` for success, non-zero for failure with a stable taxonomy; results to stdout, diagnostics to stderr; ANSI suppressed when output isn't a terminal. From Cloudflare: pick one flag — always `--json`, not `--format=json` for some commands and `--output json` for others.

- **Blocker:** No structured output at all
- **Friction:** Coverage gaps where some commands are JSON-capable and others aren't
- **Target:** Uniform `--json` across the CLI with clean stdout/stderr separation and a documented exit code taxonomy

---

### 3. Errors that teach, and enumerate

The original principle was "fail fast with actionable errors." That still holds, with one refinement. When the failure is "you passed an invalid value for X," the error should include the valid set.

```bash
# Unhelpful: agent has to read --help, parse, guess, retry
$ mycli post create --json --visibility=secret --content="hi"
error: invalid visibility

# Better: error names the valid set, agent self-corrects in one retry
$ mycli post create --json --visibility=secret --content="hi"
error: --visibility must be one of: public, private, unlisted (got: "secret")
```

HeyGen's CLI applies this consistently: pass an unknown delivery scheme and you get a structured refusal naming what is supported.

The pattern generalizes. Any time your CLI rejects user input against an enum, an enum-shaped resource list, or a schema, surface the enumeration in the error. Errors are the highest-signal context an agent gets, because they fire exactly when the agent doesn't know what to do next.

**What good looks like:** errors validated early, before side effects; correct invocation syntax in the error text; valid values enumerated when an enum is the cause; concrete examples instead of stack traces.

- **Blocker:** Silent or vague failures
- **Friction:** Errors that name the problem but not the solution
- **Target:** Errors that include the valid set and a working invocation

---

### 4. Safe retries and explicit mutation boundaries

Agents retry. Humans glance at a duplicate row and notice; agents don't.

```bash
# Idempotent create — second call returns the existing resource, not a duplicate
$ mycli post create --json --content="hello world"
{"id":"post_8f2a","existing":false}
$ mycli post create --json --content="hello world"
{"id":"post_8f2a","existing":true}

# Destructive ops require an explicit flag; --dry-run shows what would happen
$ mycli post delete post_8f2a --dry-run
{"would_delete":"post_8f2a","status":"dry_run"}
```

**What good looks like:** idempotency tokens or natural keys for create operations; `--dry-run` for anything consequential; explicit, non-default flags for destructive operations; identifiers returned in every mutation response.

Retries on a long-running operation aren't just about idempotency at submission — they're about idempotency across the whole submit-poll-collect arc. A persistent job ledger solves this.

- **Blocker:** Silent duplication or state corruption on retry
- **Friction:** Destructive commands that are scriptable without preview
- **Target:** Idempotent mutations, durable job state, and explicit destructive flags

---

### 5. Bounded responses, at every layer

Tokens cost money and context. Big outputs are sometimes justified, but the default should be narrow.

```bash
# Default page size is bounded; truncation tells the agent how to narrow
$ mycli post list --json
{"posts":[...20 items...],"truncated":true,"hint":"add --limit=N or --filter=author:..."}

# Cursor for explicit continuation
$ mycli post list --json --cursor=abc123
{"posts":[...],"next":null}
```

The original principle covered runtime output. Cloudflare added a layer the original missed: the tool description surface itself costs tokens. Their Code Mode MCP serves over 3,000 operations in under 1,000 tokens. Most MCP servers burn 1,000 tokens on a single tool's description.

**What good looks like:** filtering, pagination, and limits on every list-style command; concise vs. detailed modes; truncation messages that teach the agent how to narrow the next query; summary-before-detail responses. For MCP wrappers: a budget per tool description, audited at build time.

- **Blocker:** Routine commands dumping unbounded output
- **Friction:** Broad defaults with available narrowing
- **Target:** Bounded defaults that guide better queries, plus an MCP surface where each tool's description fits in a tweet

---

## Tier 2: Compounding

> Empower the agent. Tier 1 keeps you in the game. Tier 2 makes the CLI better the more it gets used.

### 6. Cross-CLI vocabulary consistency

Agents don't memorize one CLI at a time. They build a generalized model of what CLIs do, drawn from every CLI they've seen. When your tool uses `info` for what every other tool calls `get`, the agent doesn't fail; it succeeds slowly, with extra retries, after burning tokens on `--help`.

```bash
# Conforming to the convention — agents recognize these immediately
$ wrangler kv namespace list --json
$ heygen videos list --json
$ mycli posts list --json

# Off-convention versions an agent has to relearn for each tool
$ mycli posts ls                        # use list, not ls
$ mycli posts info abc                  # use get, not info
$ mycli post delete abc \
  --skip-confirmations                  # use --force, not --skip-*
$ mycli post list \
  --format=json                         # use --json, not --format=json
```

Cloudflare made this explicit with schema-layer rules:
- Always `get`, never `info`
- Always `list`, never `ls`
- Always `--force`, never `--skip-confirmations`
- Always `--json`, never `--format=json`

Their framing: "manually enforcing consistency through reviews is Swiss cheese." Vocabulary consistency has to be enforced mechanically, at the codegen or schema layer.

**What good looks like:** a documented naming policy; a static check in CI that fails on banned verbs and flag aliases; canonical names that match the dominant convention in your language community.

- **Blocker:** Verbs and flags that contradict universal conventions (`info` instead of `get`, `--skip-confirmations` instead of `--force`)
- **Friction:** Internal inconsistency between your own subcommands
- **Target:** Schema-enforced vocabulary that an agent trained on neighboring CLIs recognizes on first encounter

---

### 7. Three-layer introspection

The original principle was "progressive help discovery." That's still the bottom layer of a three-layer stack. Each layer answers a different question.

```bash
# Layer 1 — what does this command do? (human-shaped text)
$ mycli --help
mycli  Manage posts and accounts.

USAGE: mycli <command> [flags]

COMMANDS:
  post      Manage posts
  account   Manage accounts
  jobs      Inspect async jobs
  profile   Manage saved configurations
  feedback  Send feedback upstream

# Layer 2 — what's the shape of everything? (structured, versioned)
$ mycli agent-context | jq '.schema_version, (.commands | keys)'
"1"
["account","feedback","jobs","post","profile"]

$ mycli agent-context | jq '.commands.post.subcommands.create.flags'
{
  "--content":    {"type":"string","required":true},
  "--visibility": {"type":"enum","values":["public","private","unlisted"]},
  "--json":       {"type":"bool","default":false},
  "--dry-run":    {"type":"bool","default":false}
}

# Layer 3 — when would I use this? (long-form skill manifest)
$ cat $(mycli skill-path)/SKILL.md
# Publishing a post end-to-end
1. Save a profile for your default audience.
2. Create the post with --wait so the artifact returns synchronously.
3. Use --deliver=webhook:... to ship it downstream.
```

- `--help` is for humans (and some agents that hit it first)
- `agent-context` is the machine-readable, versioned JSON shape — Cloudflare's `/cdn-cgi/explorer/api` is the runtime version of this idea
- The **skill manifest** is long-form prose teaching the agent how to compose operations into useful workflows. HeyGen ships a skills repo of `SKILL.md` files alongside their CLI.

**What good looks like:** all three layers present, each versioned, each kept in sync with the implementation by the same generation step.

- **Blocker:** A CLI with only `--help` and nothing structured
- **Friction:** An `agent-context` that exists but isn't versioned, or skill manifests that drift from the actual command surface
- **Target:** Three layers, schema-versioned, machine-validated against the real implementation

---

### 8. Async-aware execution

Most CLIs treat async APIs the way the underlying HTTP endpoint does: submit returns a job ID, poll returns a status, that's the agent's problem. Either the agent writes its own poll loop (wasting tokens and getting it subtly wrong), or the workflow fails because the result wasn't ready when the next step ran.

The fix is `--wait`.

```bash
# Without --wait: the agent has to write its own polling loop
$ mycli video render --script=story.txt
{"job_id":"job_8f2a","status":"queued"}
$ mycli video status job_8f2a
{"job_id":"job_8f2a","status":"running","progress":0.34}
$ mycli video status job_8f2a
{"job_id":"job_8f2a","status":"running","progress":0.71}
$ mycli video status job_8f2a
{"job_id":"job_8f2a","status":"complete","url":"https://.../out.mp4"}

# With --wait: same workflow, one command, no polling logic
$ mycli video render --script=story.txt --wait
{"job_id":"job_8f2a","status":"complete","url":"https://.../out.mp4"}

# The job ledger survives across invocations
$ mycli jobs list
JOB_ID    STATUS    KIND          STARTED                DURATION
job_8f2a  complete  video.render  2026-04-30T18:22:11    37s
job_7c14  running   video.render  2026-04-30T18:24:02    12s
```

`--wait` blocks until completion. Behind it, the CLI runs a poll loop with backoff and writes job state to a local ledger. A `jobs` command exposes the ledger: `jobs list`, `jobs get <id>`, `jobs prune`.

**What good looks like:** `--wait` on every submitting command that wraps an async API; a polling implementation with exponential backoff and jitter; a persistent job ledger (`~/.<cli>/jobs.jsonl` is fine); a `jobs` parent command exposing `list`/`get`/`prune`.

- **Blocker:** Async commands that return a job ID and stop, forcing the agent to write a polling loop
- **Friction:** `--wait` that exists but doesn't survive disconnect, or no way to inspect or recover in-flight jobs
- **Target:** `--wait` on every async submission with a durable, recoverable ledger

---

### 9. Persistent identity through profiles

Agents don't show up once. They show up tomorrow, and the day after, and a week from now, in a different shell, with the same underlying intent and a different specific input. Stateless leaf-shaped CLIs make every invocation re-specify the same eight flags.

The fix is a profile system.

```bash
# Save a named bundle of configuration once
$ mycli profile save my-podcast \
    --avatar=lila \
    --voice=warm-en \
    --webhook=https://podcast.example.com/hook
profile saved: my-podcast

# Reuse it on every subsequent invocation
$ mycli video create --profile=my-podcast --script=ep_42.txt
{"job_id":"job_8f2a","using_profile":"my-podcast"}

# Explicit flags win over profile values
$ mycli video create --profile=my-podcast --voice=energetic --script=...
{"job_id":"job_a91","using_profile":"my-podcast","voice":"energetic"}

# Surfaced through introspection so agents discover available identities
$ mycli agent-context | jq '.available_profiles'
["my-podcast","client-demo","weekly-recap"]
```

Recommended precedence: **explicit flag > environment variable > profile > default**. Surfacing available profile names in `agent-context` is how an introspecting agent discovers which identities exist without parsing a config file.

**What good looks like:** `profile save / use / list / show / delete` subcommands; `--profile <name>` as a persistent root flag; profile contents shown in `agent-context`; a stable storage location like `~/.<cli>/profiles.json`.

- **Blocker:** No way to persist configuration
- **Friction:** Profiles that exist but aren't discoverable via introspection
- **Target:** Named profiles with clean precedence, surfaced through `agent-context`

---

### 10. Two-way I/O

The original principle covered stdin/stdout pipelining. But agents don't only consume CLIs through pipes, and the CLI doesn't only emit through stdout. Two new mechanisms matter: a way for the CLI to emit artifacts where the agent actually needs them, and a way for the agent to report friction back.

```bash
# --deliver routes the artifact to where it's actually needed
$ mycli video create --script=story.txt --deliver=stdout
{"video_url":"https://.../out.mp4","duration_s":47}

$ mycli video create --script=story.txt --deliver=file:./out.mp4
{"delivered_to":"file:./out.mp4","bytes":4823091}

$ mycli video create --script=story.txt \
    --deliver=webhook:https://example.com/hook
{"delivered_to":"webhook:https://example.com/hook","status":201}

# Unknown schemes get a structured refusal naming what's supported
$ mycli video create --script=... --deliver=s3:bucket/key
error: --deliver scheme must be one of: stdout, file:<path>, webhook:<url>

# feedback closes the loop in the other direction
$ mycli feedback "the --tier flag rejects 'enterprise' but the docs list it as valid"
feedback recorded locally (1 entry)

$ mycli feedback list
2026-04-30T18:31:02  the --tier flag rejects 'enterprise' but the docs list it as valid

# Optional upstream POST when configured
$ MYCLI_FEEDBACK_ENDPOINT=https://maintainers.example.com/cli-feedback \
  mycli feedback "race condition in --wait when job completes during the first poll"
feedback recorded locally and sent upstream (status: 200)
```

`--deliver` routes the artifact directly: stdout, a file path, or a webhook URL. File sinks write atomically; webhook sinks POST and surface HTTP status; unknown schemes return a structured refusal. HeyGen's framing: "fewer steps between agent output and a finished artifact."

`feedback` runs the other way. Agents hit friction constantly — flags rejected for the wrong reason, race conditions in async paths, error messages that don't enumerate. Most of it never gets reported because there's no channel. `<cli> feedback "..."` writes locally by default; with an endpoint configured, the entry POSTs upstream too.

**What good looks like:** `--deliver` with stdout/file/webhook sinks and structured refusal on unknown schemes; `feedback <text>` with local JSONL by default and configurable upstream POST; both surfaced in `agent-context`.

- **Blocker:** Output that is stdout-only with no way to report friction
- **Friction:** Output sinks that exist but aren't atomic, or feedback that exists but the upstream channel isn't discoverable
- **Target:** Structured delivery and discoverable feedback, both versioned in introspection

---

## A note on the architecture beneath these

Most of Tier 2 is hard to apply by hand and easy to apply mechanically. Cross-CLI vocabulary, three-layer introspection, async detection, profile precedence, delivery routing — every one of them is the kind of thing you'd be inconsistent about across a dozen subcommands if you wrote them by hand, and trivially consistent about if a schema or codegen pipeline writes them.

That's why Cloudflare's TypeScript schema is the load-bearing detail of their post, not a side note. Generating the CLI, the SDKs, the Terraform provider, and the MCP server from one source is what makes ten principles hold across thousands of operations without drift.

If you're maintaining a hand-written CLI of any size, the consistency bar will keep rising, and the only way to keep up is to move enforcement out of code review and into the schema or the build.

---

## Design for agents first

Every principle here makes the CLI better for humans too. None of these are concessions to agents. They're good CLI design we used to be able to skip because humans worked around the gaps.

The classic *Command Line Interface Guidelines* treat a human at a terminal as the primary user, with agents as a tolerated secondary audience. That's no longer the right default. Cloudflare puts it directly: "Increasingly, agents are the primary customer of our APIs." HeyGen launched their CLI with "agent" in the marketing copy.

Design for agents first, and humans benefit. Designing for humans first and bolting on agent support is what produces the inconsistent, prompt-prone, stdout-only CLIs the first five principles exist to correct.

---

*These 10 are what I'm currently designing against. They'll keep evolving — I had to replace the original 7 a few weeks after publishing them, and the same thing will probably happen here.*

*Also published at [trevinsays.com](https://trevinsays.com).*

*This framework comes from three places: the CLIs I've been building and generating in the last several weeks, Cloudflare's [The CLI for all of Cloudflare](https://blog.cloudflare.com) (2026-04-13), and HeyGen's CLI launch and accompanying skills repo. The original seven principles are still online; treat this post as their replacement, not a sequel.*