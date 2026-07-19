#!/usr/bin/env python3
"""Manage posts."""
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
    cmd = sys.argv[1] if len(sys.argv) > 1 else None
    if cmd not in ("get", "list", "create", "delete"):
        print(f"error: unknown command {cmd!r}; valid commands: get, list, create, delete", file=sys.stderr)
        sys.exit(2)
    p = argparse.ArgumentParser(prog=f"helptrapcli {cmd}", add_help=False)
    if cmd == "get":
        p.add_argument("id"); p.add_argument("--json", action="store_true"); handler = cmd_get
    elif cmd == "list":
        p.add_argument("--limit", type=int, default=20); p.add_argument("--cursor"); p.add_argument("--json", action="store_true"); handler = cmd_list
    elif cmd == "create":
        p.add_argument("--visibility", default="public"); p.add_argument("--json", action="store_true"); handler = cmd_create
    else:
        p.add_argument("id"); p.add_argument("--force", action="store_true"); p.add_argument("--dry-run", action="store_true"); p.add_argument("--json", action="store_true"); handler = cmd_delete
    args, _extra = p.parse_known_args(sys.argv[2:])
    handler(args)

if __name__ == "__main__":
    main()
