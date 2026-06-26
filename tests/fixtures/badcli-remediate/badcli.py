#!/usr/bin/env python3
"""A CLI for testing rate-my-cli (remediated for conformance checks)."""
import argparse, json, sys

VALID_VISIBILITY = ("public", "private")
DEFAULT_LIST_LIMIT = 20  # 5.1: bounded default

def emit(data, as_json):
    # 2.5: data -> stdout
    if as_json:
        print(json.dumps(data))
    else:
        print(data if isinstance(data, str) else json.dumps(data))

def cmd_get(args):            # 6.1: renamed from `info`
    record = {"id": args.id, "message": "hello", "visibility": args.visibility}
    if args.json:             # 2.1: JSON output
        emit(record, True)
    else:
        emit(f"post {args.id}: hello (visibility={args.visibility})", False)

def cmd_list(args):           # 6.1: renamed from `ls`
    limit = args.limit if args.limit is not None else DEFAULT_LIST_LIMIT  # 5.1
    posts = [f"post_{i}" for i in range(limit)]
    if args.json:             # 2.1
        emit({"posts": posts, "count": len(posts), "limit": limit}, True)
    else:
        for pid in posts:
            print(pid)

def cmd_delete(args):
    # 4.2: require an explicit, non-default --force before acting.
    # 1.1/1.2: only prompt when interactive AND not forced; --force bypasses.
    if not args.force:
        if sys.stdin.isatty():  # 1.2: guard prompt on TTY
            if input(f"Delete {args.id}? [y/N]: ").lower() != "y":
                print(json.dumps({"status": "aborted", "id": args.id}) if args.json
                      else "aborted")
                return
        else:
            # 1.1: non-interactive with no bypass -> fail clearly, don't block
            print("error: refusing to delete without --force in non-interactive mode "
                  "(re-run with --force)", file=sys.stderr)  # 3.4: corrective guidance
            sys.exit(2)         # 2.4: non-zero on failure
    # 4.4: return the affected id
    result = {"status": "deleted", "id": args.id}
    emit(result, args.json) if args.json else print(f"deleted {args.id}")

def cmd_create(args):
    if args.visibility not in VALID_VISIBILITY:
        # 3.3: enumerate valid set; 3.4: corrective guidance; 2.5: errors -> stderr
        print(f"error: invalid visibility '{args.visibility}'; "
              f"valid values are: {', '.join(VALID_VISIBILITY)}", file=sys.stderr)
        sys.exit(1)             # 2.4: non-zero exit on failure
    result = {"status": "created", "visibility": args.visibility}
    emit(result, args.json) if args.json else print(f"created with {args.visibility}")

def main():
    p = argparse.ArgumentParser(prog="badcli")
    sub = p.add_subparsers(required=True)

    a = sub.add_parser("get")            # 6.1
    a.add_argument("id")
    a.add_argument("--visibility", default="public", choices=VALID_VISIBILITY)
    a.add_argument("--json", action="store_true")  # 2.1
    a.set_defaults(f=cmd_get)

    b = sub.add_parser("list")           # 6.1
    b.add_argument("--limit", type=int, default=None,
                   help=f"max items (default {DEFAULT_LIST_LIMIT})")  # 5.1
    b.add_argument("--json", action="store_true")  # 2.1
    b.set_defaults(f=cmd_list)

    c = sub.add_parser("delete")
    c.add_argument("id")
    c.add_argument("--force", action="store_true",
                   help="required to delete non-interactively")  # 4.2 / 1.1
    c.add_argument("--json", action="store_true")  # 2.1
    c.set_defaults(f=cmd_delete)

    d = sub.add_parser("create")
    d.add_argument("--visibility", default="public", choices=VALID_VISIBILITY)
    d.add_argument("--json", action="store_true")  # 2.1
    d.set_defaults(f=cmd_create)

    args = p.parse_args()
    args.f(args)

if __name__ == "__main__":
    main()
