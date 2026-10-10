"""Small helpers for the editable data files each module keeps under
CONFIG_DIR: worship-artists.txt, playlist-folders.txt, job schedules, run
history. Seeds defaults from config-defaults/ on first boot, never overwrites
an existing file.
"""
import json
import os
import shutil


def seed_if_missing(dest_path, default_path):
    if not os.path.exists(dest_path) and os.path.exists(default_path):
        os.makedirs(os.path.dirname(dest_path) or ".", exist_ok=True)
        shutil.copy2(default_path, dest_path)


def load_text(path, default=""):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except FileNotFoundError:
        return default


def save_text(path, text):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.replace(tmp, path)


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1)
    os.replace(tmp, path)
