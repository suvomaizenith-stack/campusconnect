"""Building names ("C block") must not count as the plumbing keyword "blocked"."""
from ai import keywords, triage


def test_building_names_are_not_problem_keywords():
    assert keywords.category_scores("Fan not working in B block room 204")["plumbing"] == 0
    assert keywords.category_scores("Tap leaking in block-C washroom")["plumbing"] == 2  # tap + leak, not "block"


def test_real_blockage_still_counts_as_plumbing():
    assert triage.rules_analyse("a blocked drain near the canteen", {})["category"] == "plumbing"


def test_projector_flicker_in_a_block_is_electricity():
    assert triage.rules_analyse("Projector flickers in C block seminar hall", {})["category"] == "electricity"


def test_tie_is_sent_for_review():
    res = triage.rules_analyse("Dustbins overflowing in A block", {})
    assert res["confidence"] < 0.5
