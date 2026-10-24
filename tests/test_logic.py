"""Logic tests. Pure functions only; no DB or AI calls."""
import pytest

import config
from ai import llm
from ai.keywords import issue_tokens, jaccard
from ai.triage import rules_analyse
from logic import auth, priority
from logic.assignment import choose_staff
from logic.tickets import validate_category


def test_password_round_trip_and_salt():
    stored = auth.hash_password("s3cret")
    assert auth.verify_password("s3cret", stored)
    assert not auth.verify_password("wrong", stored)
    assert auth.hash_password("same") != auth.hash_password("same")


def test_access_key_format():
    key = auth.generate_access_key()
    assert len(key) == 14 and key.count("-") == 2


def test_clean_student_trims_and_uppercases_roll():
    assert auth.clean_student("  Asha Rao ", " cs2401 ") == ("Asha Rao", "CS2401")


@pytest.mark.parametrize("name, roll", [("", "CS2401"), ("Asha", ""), ("Asha", "bad roll!")])
def test_clean_student_rejects_bad_input(name, roll):
    with pytest.raises(ValueError):
        auth.clean_student(name, roll)


def test_assignment_picks_fewest_open_then_lowest_id():
    staff = [{"id": 3}, {"id": 1}, {"id": 2}]
    assert choose_staff(staff, {1: 4, 2: 1, 3: 1})["id"] == 2
    assert choose_staff(staff, {})["id"] == 1
    assert choose_staff([], {}) is None


def test_group_levels_follow_thresholds():
    assert priority.level_for(config.HOTSPOT_REPORTS - 1) == "normal"
    assert priority.level_for(config.HOTSPOT_REPORTS) == "hotspot"
    assert priority.level_for(config.CRITICAL_REPORTS) == "critical"
    assert priority.level_for(1, max_severity=3) == "critical"


def test_tier_and_group_level_floor():
    assert priority.tier(40) == "later"
    assert priority.tier(60) == "normal"
    assert priority.tier(80) == "high"
    assert priority.tier(110) == "critical"
    assert priority.tier(40, "hotspot") == "high"
    assert priority.tier(40, "critical") == "critical"


def test_duplicate_reports_match_and_different_ones_do_not():
    a = issue_tokens("wifi not working on the 2nd floor")
    b = issue_tokens("internet is down on second floor, no network")
    c = issue_tokens("water leaking from the washroom tap")
    assert jaccard(a, b) >= config.CACHE_MATCH_THRESHOLD
    assert jaccard(a, c) < config.CACHE_MATCH_THRESHOLD


def test_category_validation_has_no_general():
    for c in ("plumbing", "electricity", "cleanliness", "internet"):
        assert validate_category(c) == c
    for bad in ("General", "", "other"):
        with pytest.raises(ValueError):
            validate_category(bad)


def test_rules_triage_always_returns_valid_category():
    out = rules_analyse("the thing is broken somehow", {})
    assert out["category"] in config.CATEGORIES
    out = rules_analyse("tap leaking in washroom", {})
    assert out["category"] == "plumbing"


def test_llm_breaker_opens_after_repeated_failures(monkeypatch):
    llm.reset_state()
    monkeypatch.setattr(llm, "_chain", lambda: ["gemini"])

    def boom(*a, **k):
        raise llm.LLMError("down")

    monkeypatch.setattr(llm, "_try_provider", boom)
    for _ in range(config.BREAKER_FAILURES):
        with pytest.raises(llm.LLMError):
            llm.chat([{"role": "user", "content": "hi"}], "sys")
    assert llm.get_ai_status() == "degraded"
    llm.reset_state()
