#!/usr/bin/env python3
"""CLI entry point, so this still runs from a shell or `docker exec` the way
clean-clusters.py always did.

  python3 -m app.cli.cluster_cleanup            dry run
  python3 -m app.cli.cluster_cleanup --apply     make the changes
"""
import argparse
import sys

from app.modules.cluster_cleanup import service


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="make the changes (default is a dry run)")
    a = ap.parse_args()
    result = service.run(dry_run=not a.apply)
    for line in result["log"]:
        print(line)
    return 1 if result.get("error") else 0


if __name__ == "__main__":
    sys.exit(main())
