"""Evergreen teal theme (light and dark via CSS variables) plus small HTML helpers. All text is escaped."""
import html

import streamlit as st

CSS = """
:root { --accent:#0E8A6D; --accent-soft:#E3F4EF; --surface:#FFFFFF; --surface2:#F5F7F6; --border:#E2E8E5;
        --text:#14201C; --muted:#5F6F69; --ok:#16A34A; --warn:#D97706; --bad:#DC2626; --info:#2563EB; }
@media (prefers-color-scheme: dark) {
  :root { --accent:#2BC29B; --accent-soft:#123A30; --surface:#16211E; --surface2:#1B2825; --border:#2A3A35;
          --text:#E8F1EE; --muted:#93A59E; --ok:#4ADE80; --warn:#FBBF24; --bad:#F87171; --info:#60A5FA; }
}
.block-container { max-width:1150px; padding-top:1.6rem; }
[data-testid="stVerticalBlockBorderWrapper"] { border-radius:14px; }
[data-testid="stBaseButton-primary"] { background:var(--accent) !important; border:none !important;
  color:#fff !important; border-radius:10px !important; font-weight:600; }
[data-testid="stBaseButton-secondary"] { border-radius:10px !important; }
.cc-hero h1 { font-size:2.4rem; font-weight:800; margin-bottom:.1rem; color:var(--accent); }
.cc-hero p { color:var(--muted); font-size:1.05rem; }
.cc-card { background:var(--surface); border:1px solid var(--border); border-radius:14px; padding:.9rem 1rem; }
.cc-card h4 { margin:0 0 .25rem 0; color:var(--text); }
.cc-card p { color:var(--muted); margin:0; }
.cc-chip { display:inline-block; padding:.15rem .65rem; border-radius:999px; font-size:.78rem; font-weight:600;
  border:1px solid currentColor; white-space:nowrap; }
.cc-metric { border-radius:14px; padding:.9rem 1rem; background:var(--surface); border:1px solid var(--border); }
.cc-metric .lbl { color:var(--muted); font-size:.85rem; }
.cc-metric .val { font-size:1.8rem; font-weight:700; color:var(--text); }
.cc-banner { border-radius:12px; padding:.7rem 1rem; margin-bottom:.8rem; font-weight:600; border:1px solid; }
.cc-banner.critical { background:rgba(220,38,38,.12); color:var(--bad); border-color:var(--bad); }
.cc-banner.hotspot { background:rgba(217,119,6,.12); color:var(--warn); border-color:var(--warn); }
.cc-banner.info { background:var(--accent-soft); color:var(--accent); border-color:var(--accent); }
.cc-steps { list-style:none; padding:0; margin:0; border-left:2px solid var(--border); }
.cc-steps li { position:relative; padding:0 0 .9rem 1.1rem; color:var(--text); }
.cc-steps li::before { content:""; position:absolute; left:-7px; top:.35rem; width:12px; height:12px;
  border-radius:50%; background:var(--accent); }
.cc-steps .when { color:var(--muted); font-size:.8rem; }
.cc-steps .detail { color:var(--muted); font-size:.92rem; }
.cc-brand { font-weight:800; font-size:1.25rem; color:var(--accent); margin-bottom:.4rem; }
.cc-user { border-top:1px solid var(--border); padding-top:.6rem; margin-top:.8rem; font-size:.9rem; }
.cc-user .role { color:var(--muted); font-size:.8rem; }
@media (max-width:640px) { .block-container { padding:1rem .75rem; } .cc-hero h1 { font-size:1.9rem; } }
"""

CHIP_COLORS = {
    "waiting": "#D97706", "assigned": "#2563EB", "in_progress": "#7C3AED", "resolved": "#16A34A",
    "self_resolved": "#16A34A", "critical": "#DC2626", "high": "#D97706", "normal": "#2563EB", "later": "#6B7280",
    "hotspot": "#D97706", "pending": "#D97706", "confirmed": "#16A34A", "separate": "#6B7280",
}


def esc(text: object) -> str:
    """HTML-escape any value for safe rendering."""
    return html.escape(str(text))


def inject_css() -> None:
    """Apply the theme. Call once per run from the entry script."""
    st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)


def chip(status: str, label: str | None = None) -> str:
    """HTML status/urgency pill. Use with st.markdown(..., unsafe_allow_html=True)."""
    color = CHIP_COLORS.get(status, "#6B7280")
    return f'<span class="cc-chip" style="color:{color}">{esc(label or status.replace("_", " "))}</span>'


def card(title: str, body: str = "") -> None:
    """Rounded card with an escaped title and body."""
    text = f"<p>{esc(body)}</p>" if body else ""
    st.markdown(f'<div class="cc-card"><h4>{esc(title)}</h4>{text}</div>', unsafe_allow_html=True)


def metric_card(label: str, value: object, accent: str = "info") -> None:
    """KPI tile. accent is one of: info, ok, warn, bad."""
    colors = {"info": "#2563EB", "ok": "#16A34A", "warn": "#D97706", "bad": "#DC2626"}
    st.markdown(
        f'<div class="cc-metric" style="border-left:4px solid {colors.get(accent, "#2563EB")}">'
        f'<div class="lbl">{esc(label)}</div><div class="val">{esc(value)}</div></div>',
        unsafe_allow_html=True,
    )


def banner(message: str, level: str = "info") -> None:
    """Full-width notice. level: critical, hotspot or info."""
    st.markdown(f'<div class="cc-banner {esc(level)}">{esc(message)}</div>', unsafe_allow_html=True)


def timeline(steps: list[dict]) -> None:
    """Stepper. Each step: {"label", "detail"(optional), "when"(optional)}."""
    items = "".join(
        f'<li><div>{esc(s["label"])}</div>'
        + (f'<div class="detail">{esc(s["detail"])}</div>' if s.get("detail") else "")
        + (f'<div class="when">{esc(s["when"])}</div>' if s.get("when") else "")
        + "</li>"
        for s in steps
    )
    st.markdown(f'<ul class="cc-steps">{items}</ul>', unsafe_allow_html=True)
