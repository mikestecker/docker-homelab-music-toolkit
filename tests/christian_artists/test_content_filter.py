import pytest

from app.core import config as cfg
from app.modules.christian_artists import service as svc

CSV_HEADER = "artist,genre,worship,tier,ambiguous,enabled,mbid,notes\n"


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "CONFIG_DIR", str(tmp_path))
    svc.save_artists_text(
        CSV_HEADER
        + "Hillsong UNITED,worship,yes,core,no,yes,,\n"
        + "MercyMe,ccm,no,core,no,yes,,\n"
    )
    return svc


def track(id_, title, artist, album=""):
    return {"id": id_, "title": title, "artist": artist, "album": album}


BASE_TRACKS = [
    track("1", "Oceans", "Hillsong UNITED"),
    track("2", "Changes", "David Bowie"),
    track("3", "Sail", "AWOLNATION"),
    track("4", "I Can Only Imagine", "MercyMe"),
]


def test_any_filter_keeps_everything(store):
    result = svc.apply_content_filter(BASE_TRACKS, "any")
    assert result["kept"] == BASE_TRACKS
    assert result["filtered_out"] == []
    assert result["short"] is False


def test_worship_only_drops_bowie_and_awolnation(store):
    result = svc.apply_content_filter(BASE_TRACKS, "worship")
    kept_artists = [t["artist"] for t in result["kept"]]
    assert kept_artists == ["Hillsong UNITED"]
    filtered_artists = {t["artist"] for t in result["filtered_out"]}
    assert filtered_artists == {"David Bowie", "AWOLNATION", "MercyMe"}


def test_christian_only_keeps_both_christian_artists(store):
    result = svc.apply_content_filter(BASE_TRACKS, "christian")
    kept_artists = {t["artist"] for t in result["kept"]}
    assert kept_artists == {"Hillsong UNITED", "MercyMe"}


def test_no_christian_keeps_only_secular(store):
    result = svc.apply_content_filter(BASE_TRACKS, "no_christian")
    kept_artists = {t["artist"] for t in result["kept"]}
    assert kept_artists == {"David Bowie", "AWOLNATION"}


def test_topup_requests_bigger_batch_and_merges_in_order(store):
    extra_worship = track("5", "What A Beautiful Name", "Hillsong UNITED")
    calls = []

    def fetch_more(n):
        calls.append(n)
        return BASE_TRACKS + [extra_worship]

    result = svc.apply_content_filter(BASE_TRACKS, "worship", goal=2, fetch_more=fetch_more)
    assert calls == [12]  # 4 base tracks * 3
    assert [t["id"] for t in result["kept"]] == ["1", "5"]
    assert result["short"] is False


def test_short_result_flag_when_topup_cannot_satisfy_goal(store):
    def fetch_more(n):
        return BASE_TRACKS  # no new matches, ever

    result = svc.apply_content_filter(BASE_TRACKS, "worship", goal=5, fetch_more=fetch_more)
    assert result["short"] is True
    assert [t["artist"] for t in result["kept"]] == ["Hillsong UNITED"]


def test_topup_stops_at_cap(store, monkeypatch):
    monkeypatch.setattr(svc, "TOPUP_CAP", 10)
    calls = []

    def fetch_more(n):
        calls.append(n)
        return []

    svc.apply_content_filter(BASE_TRACKS, "worship", goal=100, fetch_more=fetch_more)
    assert all(n <= 10 for n in calls)
    assert calls[-1] == 10
