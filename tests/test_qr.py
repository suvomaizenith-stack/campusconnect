"""QR spots: the spot list is valid, codes resolve safely, links and posters are built correctly."""
import pytest

from logic import mapfile, qr


def test_spot_list_is_valid():
    assert qr.problems() == []
    assert len(qr.spots()) >= 50


def test_every_spot_points_at_a_real_place_and_floor():
    for s in qr.spots().values():
        lm = mapfile.by_id(s["landmark"])
        assert lm and (s["floor"] is None or s["floor"] in lm["floors"]) and s["spot"]


def test_lookup_is_case_insensitive_and_rejects_junk():
    s = qr.get(" BH-2-WR ")
    assert s and s["name"] == "Boys Hostel" and s["floor"] == "2nd" and s["spot"] == "Washroom"
    assert qr.label(s) == "Boys Hostel · 2nd floor · Washroom"
    for junk in (None, 5, "", "nope", "bh-9-wr", "<script>", "bh-2-wr; drop table"):
        assert qr.get(junk) is None


def test_link_needs_a_real_base_url():
    assert qr.link("bh-2-wr", "https://x.streamlit.app/") == "https://x.streamlit.app/?qr=bh-2-wr"
    with pytest.raises(ValueError):
        qr.link("bh-2-wr", "")


def test_poster_and_sheet_render():
    qr_poster = pytest.importorskip("logic.qr_poster")
    spot = qr.get("bh-2-wr")
    card = qr_poster.card(spot, "https://x.streamlit.app")
    assert card.size == qr_poster.CARD
    pages = qr_poster.sheets([spot] * 5, "https://x.streamlit.app")
    assert len(pages) == 2 and pages[0].size == qr_poster.SHEET


def test_hostel_pins_do_not_land_on_the_mess():
    for code, place in (("bh-2-wr", "boys_hostel"), ("gh-g-wc", "girls_hostel"), ("a-1-wr", "a_block")):
        x, y = qr.pin_point(qr.get(code))
        assert mapfile.hit_test(x, y, scale=100.0)["landmark"]["id"] == place
