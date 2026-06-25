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
