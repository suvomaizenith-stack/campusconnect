from datetime import date, time, timezone

import config
from logic import safety, settings
from logic.timeutil import from_ist


def test_safety_report_detects_injury_text():
    assert safety.is_safety_report("a student fainted near the lab")


def test_safety_report_ignores_plain_text():
    assert not safety.is_safety_report("the tap in block a is leaking slightly")


def test_from_ist_converts_to_utc():
    got = from_ist(date(2026, 10, 24), time(11, 0))
    assert got.tzinfo == timezone.utc
    assert (got.hour, got.minute) == (5, 30)


def test_hotspot_is_clamped_into_range():
    lo, hi = settings.HOTSPOT_RANGE
    assert settings._clamp_hotspot(0) == lo
    assert settings._clamp_hotspot(999) == hi
    assert settings._clamp_hotspot(config.HOTSPOT_REPORTS) == config.HOTSPOT_REPORTS


def test_parse_falls_back_to_default_for_bad_hotspot():
    assert settings._parse("hotspot_reports", "not a number") == settings.DEFAULTS["hotspot_reports"]


def test_parse_reads_booleans():
    assert settings._parse("latest_reports", "true") is True
    assert settings._parse("latest_reports", "false") is False
