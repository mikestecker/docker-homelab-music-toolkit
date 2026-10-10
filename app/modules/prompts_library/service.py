"""Prompts library: the Apple Playlist Prompts page, Playlist recipes and
New library recipes, served as data for the frontend to search and filter
(the same job the original single HTML page did client-side). Data files are
ported verbatim from prompts-tool/data/ - this module only reads them.

"Run in AudioMuse" and playlist creation go through app.core.audiomuse_client.
"""
import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
_cache = {}


def _load(name):
    if name not in _cache:
        with open(os.path.join(DATA_DIR, f"{name}.json"), encoding="utf-8") as fh:
            _cache[name] = json.load(fh)
    return _cache[name]


def seedprompts():
    return _load("seedprompts")


def recipes():
    return _load("recipes_v2")


def newlib():
    return _load("newlib")


def concepts():
    return _load("concepts")


def profile():
    return _load("profile")
