"""Content filter wiring in Playlist Studio and Prompts Library, against a
fake AudioMuse (monkeypatched chat_playlist/alchemy, same style tests/
conftest.py uses for app.core.navidrome_client: patch the names each
consuming module already imported into its own namespace)."""
import pytest

from app.core import config as cfg
from app.modules.christian_artists import service as christian_artists
from app.modules.playlist_studio import service as studio
from app.modules.prompts_library import router as prompts_router

CSV_HEADER = "artist,genre,worship,tier,ambiguous,enabled,mbid,notes\n"


def song(id_, title, artist, album=""):
    return {"id": id_, "title": title, "artist": artist, "album": album}


BASE = [
    song("1", "Oceans", "Hillsong UNITED"),
    song("2", "Changes", "David Bowie"),
    song("3", "Sail", "AWOLNATION"),
]


@pytest.fixture
def artists(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "CONFIG_DIR", str(tmp_path))
    christian_artists.save_artists_text(
        CSV_HEADER + "Hillsong UNITED,worship,yes,core,no,yes,,\n")


def test_instant_mode_applies_worship_filter(artists, monkeypatch):
    calls = []

    def fake_chat_playlist(prompt):
        calls.append(prompt)
        return {"songs": BASE, "raw_response": {}}

    monkeypatch.setattr(studio, "chat_playlist", fake_chat_playlist)
    session_id, entry = studio.generate_instant("worship music", content_filter="worship")
    assert [t["artist"] for t in entry["tracks"]] == ["Hillsong UNITED"]
    assert entry["filtered_out"][0]["artist"] in {"David Bowie", "AWOLNATION"}
    # Filtering left fewer tracks than we started with (1 of 3), so top-up
    # fired (and found nothing new, since the fake always returns the same
    # three songs) - that's reported via "short", not a missing top-up call.
    assert calls[0] == "worship music"
    assert entry["short"] is True


def test_instant_mode_tops_up_with_a_nudged_prompt_when_short(artists, monkeypatch):
    extra = song("4", "What A Beautiful Name", "Hillsong UNITED")
    calls = []

    def fake_chat_playlist(prompt):
        calls.append(prompt)
        if "give me at least" in prompt:
            return {"songs": BASE + [extra], "raw_response": {}}
        return {"songs": [song("2", "Changes", "David Bowie")], "raw_response": {}}

    monkeypatch.setattr(studio, "chat_playlist", fake_chat_playlist)
    _, entry = studio.generate_instant("worship music", content_filter="worship")
    assert any("give me at least" in c for c in calls)
    assert [t["id"] for t in entry["tracks"]] == ["1", "4"]


def test_alchemy_mode_tops_up_with_a_bigger_n(artists, monkeypatch):
    extra = song("4", "What A Beautiful Name", "Hillsong UNITED")
    calls = []

    def fake_alchemy(items, n=None, temperature=None, subtract_distance=None):
        calls.append(n)
        if n and n > 3:
            return {"songs": BASE + [extra], "raw_response": {}}
        return {"songs": BASE, "raw_response": {}}

    monkeypatch.setattr(studio, "alchemy", fake_alchemy)
    anchor = {"id": "1", "title": "Oceans", "artist": "Hillsong UNITED"}
    _, entry = studio.generate_alchemy([anchor], [], size=2, content_filter="worship")
    assert calls[0] == 2
    assert calls[1] > 2  # top-up asked for more than the original size
    assert len(entry["tracks"]) <= 2
    assert all(t["artist"] == "Hillsong UNITED" for t in entry["tracks"])


def test_refine_diff_includes_filtered_out(artists, monkeypatch):
    def fake_chat_playlist(prompt):
        return {"songs": BASE, "raw_response": {}}

    monkeypatch.setattr(studio, "chat_playlist", fake_chat_playlist)
    session_id, first = studio.generate_instant("anything", content_filter="any")
    entry, diff = studio.refine(session_id, "more upbeat", content_filter="worship")
    assert diff["filtered_out"]
    assert {t["artist"] for t in diff["filtered_out"]} <= {"David Bowie", "AWOLNATION"}


def test_prompts_library_run_applies_filter_and_reports_short(artists, monkeypatch):
    def fake_chat_playlist(prompt):
        return {"songs": BASE, "raw_response": {"debug": True}}

    monkeypatch.setattr(prompts_router, "chat_playlist", fake_chat_playlist)
    result = prompts_router.run_prompt(prompts_router.RunReq(prompt="worship", content_filter="worship"))
    assert [t["artist"] for t in result["songs"]] == ["Hillsong UNITED"]
    assert result["short"] is True  # no fetch_more improvement available here
    assert result["raw_response"] == {"debug": True}


def test_suggest_content_filter_from_prompt_text():
    assert christian_artists.suggest_content_filter("gimme some worship songs") == "worship"
    assert christian_artists.suggest_content_filter("Christian hip hop please") == "christian"
    assert christian_artists.suggest_content_filter("upbeat road trip music") is None


def test_suggest_from_anchors_all_worship(artists):
    assert christian_artists.suggest_from_anchors(["Hillsong UNITED"]) == "worship"
    assert christian_artists.suggest_from_anchors(["Hillsong UNITED", "David Bowie"]) is None
