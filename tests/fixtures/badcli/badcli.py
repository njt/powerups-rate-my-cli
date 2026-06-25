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
