"""Aurora dark theme: global CSS plus small HTML helpers. All text is escaped."""
import html

import streamlit as st

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Poppins:wght@600;700;800&display=swap');
:root { --card:#141B34; --violet:#7C5CFF; --pink:#FF6BCB; --cyan:#22D3EE;
        --ok:#34D399; --warn:#FBBF24; --bad:#FB7185; --muted:#A9B4D0; }
html, body, .stApp, p, label, input, textarea, button { font-family:'Inter', sans-serif; }
h1, h2, h3, h4 { font-family:'Poppins', sans-serif !important; }
.stApp { background:#0B1020; overflow-x:hidden; }
[data-testid="stHeader"] { background:transparent; }
[data-testid="stSidebar"] { background:#0F1630; }
.block-container { max-width:1100px; padding-top:2rem; }
[data-testid="stVerticalBlockBorderWrapper"] {
  background:var(--card); border-radius:16px; border:1px solid rgba(124,92,255,.28);
  transition:box-shadow .2s ease; }
[data-testid="stVerticalBlockBorderWrapper"]:hover { box-shadow:0 0 24px rgba(124,92,255,.35); }
[data-testid="stBaseButton-primary"], button[kind="primary"] {
  background:linear-gradient(90deg,var(--violet),var(--pink)) !important; border:none !important;
  color:#fff !important; border-radius:12px !important; font-weight:600; }
[data-testid="stBaseButton-primary"]:hover { box-shadow:0 0 18px rgba(255,107,203,.45); }
[data-testid="stBaseButton-secondary"] { border-radius:12px !important; }
.cc-hero h1 { font-size:2.8rem; font-weight:800; margin-bottom:.2rem;
  background:linear-gradient(90deg,var(--violet),var(--pink)); -webkit-background-clip:text;
  background-clip:text; color:transparent; }
.cc-hero p { color:var(--muted); font-size:1.05rem; }
.cc-card h4 { margin:0 0 .3rem 0; color:#F1F5FF; }
.cc-card p { color:var(--muted); margin:0; }
.cc-chip { display:inline-block; padding:.18rem .65rem; border-radius:999px; font-size:.78rem;
  font-weight:600; border:1px solid currentColor; white-space:nowrap; }
.cc-metric { border-radius:16px; padding:1rem; background:var(--card);
  border:1px solid rgba(255,255,255,.08); }
.cc-metric .lbl { color:var(--muted); font-size:.85rem; }
.cc-metric .val { font-family:'Poppins',sans-serif; font-size:1.9rem; font-weight:700; }
.cc-steps { list-style:none; padding:0; margin:0; border-left:2px solid rgba(124,92,255,.4); }
.cc-steps li { position:relative; padding:0 0 1rem 1.1rem; color:#E6EBFA; }
.cc-steps li::before { content:""; position:absolute; left:-7px; top:.35rem; width:12px; height:12px;
  border-radius:50%; background:linear-gradient(90deg,var(--violet),var(--pink)); }
.cc-steps .when { color:var(--muted); font-size:.8rem; }
.cc-steps .detail { color:var(--muted); font-size:.92rem; }
@media (max-width:640px) {
  .block-container { padding:1rem .75rem; }
  .cc-hero h1 { font-size:2.1rem; }
}
"""

# status or urgency name -> accent colour
CHIP_COLORS = {
    "open": "#22D3EE", "assigned": "#22D3EE", "in_progress": "#7C5CFF",
    "waiting": "#FBBF24", "resolved": "#34D399", "closed": "#34D399",
    "critical": "#FB7185", "high": "#FBBF24", "normal": "#22D3EE", "later": "#A9B4D0",
}


def esc(text: object) -> str:
    """HTML-escape any value for safe rendering."""
    return html.escape(str(text))


def inject_css() -> None:
    """Apply the Aurora theme. Call once per run from the entry script."""
    st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)


def chip(status: str) -> str:
    """Return an HTML status/urgency chip. Use with st.markdown(..., unsafe_allow_html=True)."""
    color = CHIP_COLORS.get(status, "#A9B4D0")
    return f'<span class="cc-chip" style="color:{color}">{esc(status.replace("_", " "))}</span>'


def card(title: str, body: str = "") -> None:
    """Render a rounded card with an escaped title and body."""
    text = f"<p>{esc(body)}</p>" if body else ""
    st.markdown(f'<div class="cc-card"><h4>{esc(title)}</h4>{text}</div>', unsafe_allow_html=True)


def metric_card(label: str, value: object, accent: str = "cyan") -> None:
    """Render a KPI tile. accent is one of: cyan, violet, ok, warn, bad."""
    colors = {"cyan": "#22D3EE", "violet": "#7C5CFF", "ok": "#34D399", "warn": "#FBBF24", "bad": "#FB7185"}
    st.markdown(
        f'<div class="cc-metric" style="border-left:4px solid {colors.get(accent, "#22D3EE")}">'
        f'<div class="lbl">{esc(label)}</div><div class="val">{esc(value)}</div></div>',
        unsafe_allow_html=True,
    )


def timeline(steps: list[dict]) -> None:
    """Render a stepper. Each step: {"label", "detail"(optional), "when"(optional)}."""
    items = "".join(
        f'<li><div>{esc(s["label"])}</div>'
        + (f'<div class="detail">{esc(s["detail"])}</div>' if s.get("detail") else "")
        + (f'<div class="when">{esc(s["when"])}</div>' if s.get("when") else "")
        + "</li>"
        for s in steps
    )
    st.markdown(f'<ul class="cc-steps">{items}</ul>', unsafe_allow_html=True)
