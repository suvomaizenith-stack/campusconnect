"""Admin settings saved in the database. If the table or database is unavailable, config.py defaults apply."""
import streamlit as st

import config
from db import settings as sdb

HOTSPOT_RANGE = (2, config.CRITICAL_REPORTS - 1)
DEFAULTS = {"hotspot_reports": config.HOTSPOT_REPORTS, "recurring_banners": True, "latest_reports": True}


def _clamp_hotspot(value: int) -> int:
    lo, hi = HOTSPOT_RANGE
    return min(max(int(value), lo), hi)


def _parse(key: str, raw: str):
    if key == "hotspot_reports":
        try:
            return _clamp_hotspot(raw)
        except ValueError:
            return DEFAULTS[key]
    return raw == "true"


@st.cache_data(ttl=30)
def load() -> dict:
    try:
        stored = sdb.all_settings()
    except Exception:  # missing table or database trouble: keep the app running on defaults
        stored = {}
    return {key: _parse(key, stored[key]) if key in stored else default for key, default in DEFAULTS.items()}


def save(key: str, value, updated_by: str) -> None:
    if key not in DEFAULTS:
        raise ValueError(f"Unknown setting {key!r}.")
    if key == "hotspot_reports":
        text = str(_clamp_hotspot(value))
    else:
        text = "true" if value else "false"
    sdb.put_setting(key, text, updated_by)
    load.clear()
