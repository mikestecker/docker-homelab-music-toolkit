import os

import pytest

from app.core import config as cfg
from app.modules.christian_artists import migration
from app.modules.christian_artists import service as svc

SHIPPED_ACTIVE_SAMPLE = migration._SHIPPED_ACTIVE[0]  # "Passion"
SHIPPED_GRAYAREA_SAMPLE = migration._SHIPPED_GRAYAREA[0]  # "Crowder"


@pytest.fixture
def config_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "CONFIG_DIR", str(tmp_path))
    return tmp_path


def _write_old_file(config_dir, text):
    (config_dir / "worship-artists.txt").write_text(text)


def test_no_edits_is_a_noop(config_dir):
    text = "\n".join(migration._SHIPPED_ACTIVE) + "\n" + \
           "\n".join(f"# {n}" for n in migration._SHIPPED_GRAYAREA) + "\n"
    _write_old_file(config_dir, text)
    svc.ensure_seeded()
    log = svc.migration_log()
    assert log["changed"] is False
    assert log["worship_enabled"] == []
    assert log["disabled"] == []
    assert os.path.exists(config_dir / "worship-artists.txt.migrated")
    assert not os.path.exists(config_dir / "worship-artists.txt")


def test_added_line_becomes_worship_yes_enabled_yes(config_dir):
    text = "\n".join(migration._SHIPPED_ACTIVE) + "\nMy Totally New Band\n"
    _write_old_file(config_dir, text)
    svc.ensure_seeded()
    log = svc.migration_log()
    assert "My Totally New Band" in log["worship_enabled"]
    row = next(r for r in svc.get_artist_rows() if r["artist"] == "My Totally New Band")
    assert row["worship"] == "yes" and row["enabled"] == "yes"


def test_removed_default_line_becomes_disabled(config_dir):
    kept = [n for n in migration._SHIPPED_ACTIVE if n != SHIPPED_ACTIVE_SAMPLE]
    _write_old_file(config_dir, "\n".join(kept) + "\n")
    svc.ensure_seeded()
    log = svc.migration_log()
    assert SHIPPED_ACTIVE_SAMPLE in log["disabled"]
    row = next((r for r in svc.get_artist_rows() if r["artist"] == SHIPPED_ACTIVE_SAMPLE), None)
    assert row is not None and row["enabled"] == "no"


def test_commented_out_default_line_becomes_disabled(config_dir):
    others = [n for n in migration._SHIPPED_ACTIVE if n != SHIPPED_ACTIVE_SAMPLE]
    text = "\n".join(others) + f"\n# {SHIPPED_ACTIVE_SAMPLE}\n"
    _write_old_file(config_dir, text)
    svc.ensure_seeded()
    log = svc.migration_log()
    assert SHIPPED_ACTIVE_SAMPLE in log["disabled"]


def test_uncommented_grayarea_line_becomes_worship_yes_enabled_yes(config_dir):
    text = "\n".join(migration._SHIPPED_ACTIVE) + f"\n{SHIPPED_GRAYAREA_SAMPLE}\n"
    _write_old_file(config_dir, text)
    svc.ensure_seeded()
    log = svc.migration_log()
    assert SHIPPED_GRAYAREA_SAMPLE in log["worship_enabled"]
    row = next(r for r in svc.get_artist_rows() if r["artist"].lower() == SHIPPED_GRAYAREA_SAMPLE.lower())
    assert row["worship"] == "yes" and row["enabled"] == "yes"


def test_untouched_grayarea_line_is_left_alone(config_dir):
    text = "\n".join(migration._SHIPPED_ACTIVE) + f"\n# {SHIPPED_GRAYAREA_SAMPLE}\n"
    _write_old_file(config_dir, text)
    svc.ensure_seeded()
    log = svc.migration_log()
    assert SHIPPED_GRAYAREA_SAMPLE not in log["worship_enabled"]
    assert SHIPPED_GRAYAREA_SAMPLE not in log["disabled"]


def test_runs_only_once(config_dir):
    _write_old_file(config_dir, "My Totally New Band\n")
    svc.ensure_seeded()
    first_log = svc.migration_log()
    # Someone hand-edits the .migrated file or re-creates the old file - the
    # marker file existing is what stops a second run, not file contents.
    _write_old_file(config_dir, "Someone Else Entirely\n")
    svc.ensure_seeded()
    assert svc.migration_log() == first_log
