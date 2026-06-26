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
