"""Offline checks for map geometry, location reading, quick replies and keyword helpers (no database)."""
import pytest

import config
from ai import keywords, kb
from logic import location, mapfile, priority, views


def test_landmarks_file_is_valid_and_complete():
    assert mapfile.validate() == []
    assert len([lm for lm in mapfile.landmarks() if lm["category"] != "road"]) == 23
    assert {s["id"] for s in mapfile.services()} >= {"helpdesk", "security"}


def test_hit_test_inside_polygon_and_road_and_snap():
    d = mapfile.by_id("d_block")
    hit = mapfile.hit_test(d["map_x"], d["map_y"])
    assert hit["kind"] == "landmark" and hit["landmark"]["id"] in {"d_block", "d_block_ground", "d_block_canteen"}
    road = mapfile.by_id("sohna_road")
    rx, ry = road["map_x"], road["map_y"]
    assert mapfile.hit_test(rx, ry)["landmark"]["category"] == "road"
    assert mapfile.hit_test(0.001, 0.001)["landmark"] is not None


def test_issue_dot_wins_and_reach_shrinks_with_zoom():
    d = mapfile.by_id("a_block")
    dot = {"id": 7, "map_x": d["map_x"] + 0.004, "map_y": d["map_y"]}  # 6.4 px away
    assert mapfile.hit_test(d["map_x"], d["map_y"], 1.0, [dot])["issue_id"] == 7
    assert mapfile.hit_test(d["map_x"], d["map_y"], 5.0, [dot])["kind"] != "issue"  # reach is 4 px at 5x zoom


def test_outside_campus_label_and_badge_anchor():
    assert mapfile.display_name(mapfile.by_id("sohna_road")).startswith("Outside campus")
    b = mapfile.by_id("b_block")
    x, y = mapfile.badge_anchor(b)
    assert x == max(p[0] for p in b["area"]) and y == min(p[1] for p in b["area"])


def test_index_order_places_roads_services():
    kinds = [e["kind"] for e in mapfile.index_entries()]
    assert kinds == sorted(kinds, key={"place": 0, "road": 1, "service": 2}.get)


def test_location_reads_block_floor_room_and_nearby():
    g = location.extract_location("tap near the water cooler in Block B 2nd floor room 204 is leaking")
    assert g["landmark"]["id"] == "b_block" and g["floor"] == "2nd" and g["room"] == "204"
    assert g["nearby"] == "water cooler"


def test_canteen_is_ambiguous_and_hindi_alias_works():
    g = location.match_landmark("fan not working in canteen")
    assert g["landmark"] is None and len(g["ambiguous"]) > 1
    assert location.match_landmark("बी ब्लॉक के दूसरे फ्लोर वॉशरूम में नल")["landmark"]["id"] == "b_block"


def test_ground_floor_does_not_pick_d_block_ground():
    assert location.match_landmark("light off in D block ground floor")["landmark"]["id"] == "d_block"


def test_pin_conflict_ignores_canteen_inside_block():
    assert location.pin_conflict(mapfile.by_id("a_block"), mapfile.by_id("b_block"))
    assert not location.pin_conflict(mapfile.by_id("a_block"), mapfile.by_id("a_block"))
    assert not location.pin_conflict(None, mapfile.by_id("a_block"))


def test_floors_come_from_the_file():
    assert location.extract_floor("5th floor", mapfile.by_id("main_gate")["floors"]) is None


def test_quick_replies_have_both_languages_and_fill_placeholders():
    replies = views.quick_replies("plumbing")
    assert replies and all(r["en"] and r["hi"] for r in replies)
    ticket = {"student_name": "Asha", "code": "CC-0007", "category": "plumbing", "eta_at": None}
    out = views.fill_reply("Hi {student_name}, {ticket_id} is with {department}. {unknown}", ticket, {"name": "Ravi"})
    assert "Asha" in out and "CC-0007" in out and "{unknown}" in out and "{student_name}" not in out


def test_urgency_labels_and_override():
    assert config.URGENCY_LABELS["critical"] == "Urgent" and config.URGENCY_LABELS["later"] == "Low"
    assert priority.effective_tier("normal", "critical") == "critical"
    assert priority.effective_tier("normal", None) == "normal"


def test_overdue_targets_match_the_mentor_spec():
    assert config.FIRST_RESPONSE_HOURS == {"plumbing": 2, "electricity": 1, "cleanliness": 2, "internet": 0.5}
    assert config.OVERDUE_HOURS["plumbing"] == 24 and config.OVERDUE_HOURS["electricity"] == 24


def test_hindi_text_is_detected_and_scored():
    assert keywords.language_of("बी ब्लॉक में नल से पानी टपक रहा है") == "hi"
    assert keywords.language_of("tap is leaking") == "en"
    scores = keywords.category_scores("नल से पानी टपक रहा है")
    assert max(scores, key=scores.get) == "plumbing"


def test_out_of_scope_and_no_general_category():
    assert keywords.out_of_scope_hit("when is the fee payment deadline")
    assert not keywords.out_of_scope_hit("tap is leaking")


def test_kb_contacts_are_flagged_as_placeholders():
    for key in ("helpdesk", "security", "medical", "it_support"):
        c = kb.contact(key)
        assert c and "PLACEHOLDER" in c["note"].upper()
