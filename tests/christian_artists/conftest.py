import os
import sys

# Don't rely on tests/duplicate_finder/conftest.py having already inserted
# the repo root onto sys.path - that only happens once its directory is
# collected, and "christian_artists" sorts alphabetically before
# "duplicate_finder", so this directory's own tests would otherwise fail to
# `import app` under a bare `pytest` invocation (no cwd auto-insertion, unlike
# `python -m pytest`) depending on collection order alone. Self-sufficient,
# same pattern as tests/duplicate_finder/conftest.py.
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
