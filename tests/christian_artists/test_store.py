import pytest

from app.core import config as cfg
from app.modules.christian_artists import service as svc

CSV_HEADER = "artist,genre,worship,tier,ambiguous,enabled,mbid,notes,extra_future_col\n"


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "CONFIG_DIR", str(tmp_path))
    return svc


def seed(store, rows_text):
    store.save_artists_text(CSV_HEADER + rows_text)


def test_classify_christian_and_worship(store):
    seed(store, "Hillsong UNITED,worship,yes,core,no,yes,,,keepme\n"
                "MercyMe,ccm,no,core,no,yes,,,keepme\n")
    assert store.classify("Hillsong UNITED") == {"christian": True, "worship": True}
    assert store.classify("MercyMe") == {"christian": True, "worship": False}
    assert store.classify("David Bowie") == {"christian": False, "worship": False}


def test_classify_matches_any_split_credit_name():
    pass  # covered by test_artist_matcher.py + cluster_cleanup tests


def test_disabled_and_ambiguous_entries_do_not_match(store):
    seed(store, "Chris Brown,rnb,no,core,yes,no,,ambiguous with the R&B singer\n")
    assert store.classify("Chris Brown") == {"christian": False, "worship": False}


def test_crossover_ships_disabled_by_default(store):
    seed(store, "Switchfoot,rock,no,crossover,no,no,,ships disabled\n")
    assert store.classify("Switchfoot") == {"christian": False, "worship": False}


def test_mbid_takes_precedence_over_name_for_ambiguous_artists(store):
    # The real-world case: "Chris Brown" the R&B singer vs a Christian artist
    # confirmed by MusicBrainz id. Disabled by name, but matches by mbid.
    seed(store, "Chris Brown,worship,yes,core,yes,yes,mbid-xyz,confirmed by mbid\n")
    assert store.classify("Chris Brown") == {"christian": False, "worship": False}
    assert store.classify("Chris Brown", mbids={"mbid-xyz"}) == {"christian": True, "worship": True}


def test_worship_unknown_counts_as_not_worship(store):
    seed(store, "Some Band,unknown,unknown,core,no,yes,,needs research\n")
    assert store.classify("Some Band") == {"christian": True, "worship": False}


def test_override_track_beats_album_beats_artist_flag(store):
    seed(store, "for KING & COUNTRY,ccm,no,core,no,yes,,\n")
    store.save_overrides_text(
        "for KING & COUNTRY | Burn the Ships | Priceless\n"
        "for KING & COUNTRY | Relate\n"
    )
    # Track-level override wins for that one track.
    assert store.classify("for KING & COUNTRY", "Burn the Ships", "Priceless")["worship"] is True
    # Album-level override applies to any other track on that album.
    assert store.classify("for KING & COUNTRY", "Burn the Ships", "Other Song")["worship"] is False
    # Album-level override for a different album.
    assert store.classify("for KING & COUNTRY", "Relate", "Anything")["worship"] is True
    # No override at all: falls back to the artist's own flag (not worship).
    assert store.classify("for KING & COUNTRY", "Some Other Album", "X")["worship"] is False


def test_override_negation(store):
    seed(store, "Hillsong UNITED,worship,yes,core,no,yes,,\n")
    store.save_overrides_text("!Hillsong UNITED | Live Set\n")
    assert store.classify("Hillsong UNITED", "Live Set", "Anything")["worship"] is False
    assert store.classify("Hillsong UNITED", "Other Album", "X")["worship"] is True


def test_unknown_csv_columns_round_trip_untouched(store):
    seed(store, "Hillsong UNITED,worship,yes,core,no,yes,,,prov-value\n")
    rows = store.get_artist_rows()
    assert rows[0]["extra_future_col"] == "prov-value"
    store.update_artist("Hillsong UNITED", notes="edited")
    rows = store.get_artist_rows()
    assert rows[0]["extra_future_col"] == "prov-value"
    assert rows[0]["notes"] == "edited"


def test_add_update_delete_artist(store):
    seed(store, "")
    store.add_artist("New Band", genre="worship", worship="yes")
    assert store.classify("New Band")["worship"] is True
    with pytest.raises(ValueError):
        store.add_artist("New Band")  # duplicate
    store.update_artist("New Band", enabled="no")
    assert store.classify("New Band") == {"christian": False, "worship": False}
    store.delete_artist("New Band")
    with pytest.raises(KeyError):
        store.update_artist("New Band", enabled="yes")


def test_bulk_add_reports_duplicates(store):
    seed(store, "Existing Band,rock,no,core,no,yes,,\n")
    result = store.bulk_add(["Existing Band", "Brand New", "Brand New"])
    assert result["added"] == ["Brand New"]
    assert sorted(result["duplicates"]) == ["Brand New", "Existing Band"]


def test_scoped_name_keys_respects_scope(store):
    seed(store,
         "Hillsong UNITED,worship,yes,core,no,yes,,\n"
         "MercyMe,ccm,no,core,no,yes,,\n"
         "Switchfoot,rock,no,crossover,no,no,,\n")
    from app.core.artist_matcher import norm
    christian_keys = store.scoped_name_keys("christian")
    worship_keys = store.scoped_name_keys("worship")
    assert norm("Hillsong UNITED") in christian_keys and norm("MercyMe") in christian_keys
    assert norm("Switchfoot") not in christian_keys  # disabled (crossover)
    assert norm("Hillsong UNITED") in worship_keys
    assert norm("MercyMe") not in worship_keys  # christian but not worship


def test_reset_to_defaults_is_merge_only(store, tmp_path, monkeypatch):
    import os
    default_csv = tmp_path / "defaults.csv"
    default_csv.write_text(CSV_HEADER + "A Band,rock,no,core,no,yes,,\n"
                                          "B Band,rock,no,core,no,yes,,\n")
    monkeypatch.setattr(store, "_DEFAULT_CSV", str(default_csv))
    seed(store, "A Band,rock,no,core,no,yes,,user-edited-notes\n")
    result = store.reset_to_defaults()
    assert result["added"] == 1
    rows = {r["artist"]: r for r in store.get_artist_rows()}
    assert rows["A Band"]["notes"] == "user-edited-notes"  # untouched
    assert "B Band" in rows  # merged in
