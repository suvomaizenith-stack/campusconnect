"""Priority score, tier and group level. Pure functions; thresholds come from config.py."""
import config
from ai.keywords import routing_guide

TIER_ORDER = ["critical", "high", "normal", "later"]


def level_for(report_count: int, max_severity: int = 1) -> str:
    """Group level: 'critical' (5+ reports or a severity-3 report), 'hotspot' (3+), else 'normal'."""
    if report_count >= config.CRITICAL_REPORTS or max_severity >= 3:
        return "critical"
    if report_count >= config.HOTSPOT_REPORTS:
        return "hotspot"
    return "normal"


def score(category: str, severity: int, report_count: int) -> int:
    """Priority score: category base + severity * 10 + reports * 5."""
    return routing_guide()[category]["base_priority"] + severity * 10 + report_count * 5


def tier(priority_score: int, level: str = "normal") -> str:
    """Tier from score; the group level can only raise it (critical group -> critical, hotspot -> at least high)."""
    if priority_score >= 100:
        base = "critical"
    elif priority_score >= 75:
        base = "high"
    elif priority_score >= 55:
        base = "normal"
    else:
        base = "later"
    floor = {"critical": "critical", "hotspot": "high"}.get(level)
    if floor and TIER_ORDER.index(floor) < TIER_ORDER.index(base):
        return floor
    return base


def effective_tier(computed: str, override: str | None) -> str:
    """A staff urgency override wins over the computed tier."""
    return override if override in TIER_ORDER else computed
