#!/usr/bin/env python3
"""CLI entry point, so this still runs from a shell or `docker exec` the way
rename-playlists.py always did.

  python3 -m app.cli.playlist_folders              dry run
  python3 -m app.cli.playlist_folders --apply      rename
  python3 -m app.cli.playlist_folders --list       print every current playlist name
"""
import argparse
import sys

from app.core import navidrome_client as nd
from app.core.navidrome_client import NavidromeError
from app.modules.playlist_folders import service


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="rename (default is a dry run)")
    ap.add_argument("--list", action="store_true", help="print all playlist names and exit")
    a = ap.parse_args()

    if a.list:
        try:
            for p in sorted(nd.get_playlists(client="playlist-folders"), key=lambda p: p["name"].lower()):
                print(p["name"])
        except NavidromeError as e:
            print(f"STOP  {e}")
            return 1
        return 0

    result = service.run(dry_run=not a.apply)
    for line in result["log"]:
        print(line)
    return 1 if result.get("error") else 0


if __name__ == "__main__":
    sys.exit(main())
