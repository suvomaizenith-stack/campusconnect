"""Campus Saathi look: near-black sidebar, yellow accent, Manrope + DM Sans, light/dark switch, Lucide icons.

All colours come from CSS variables on :root, so the light/dark switch only swaps a dict (see VARS). Widgets that
Streamlit themes itself are re-skinned here with !important so the switch works regardless of the OS theme.
Buttons and links get a Lucide icon from their key: key="i_<icon>__<anything>" (see ICON_BUTTONS).
Every dynamic value is escaped. No emoji: use ui.icons.icon().
"""
import html
from functools import lru_cache

import streamlit as st

from ui.icons import icon, mask_url

__all__ = ["esc", "icon", "inject_css", "mode", "theme_toggle", "chip", "category_chip", "card", "metric_card",
           "metric_row", "stat_row", "banner", "timeline", "page_header", "section_head", "empty_state", "meta",
           "issue_cards", "brand", "user_card", "hero_art", "auth_art", "kicker", "dash_head", "panel_head", "list_row"]

VARS = {
    "light": {
        "bg": "#f7f7f9", "paper": "#ffffff", "ink": "#19191c", "muted": "#85858e", "line": "#e9e8ed", "soft": "#f0eff3",
        "shadow": "0 12px 32px rgba(29,29,42,.10)", "btn-bg": "#19191c", "btn-fg": "#ffffff", "btn-hover": "#38383d",
        "focus": "#aaa6ff", "tab-on": "#ffffff", "feature-bg": "#202023", "feature-fg": "#ffffff",
        "amber": "#946a1d", "blue": "#3b5bb0", "violet": "#6d4fc2", "green": "#286c4e", "red": "#a83d36",
        "gray": "#6d6b75", "cyan": "#0e7490", "scheme": "light",
    },
    "dark": {
        "bg": "#131316", "paper": "#1e1e23", "ink": "#f2f2f4", "muted": "#aaa9b2", "line": "#34343b", "soft": "#303037",
        "shadow": "0 12px 30px rgba(0,0,0,.40)", "btn-bg": "#f3f05c", "btn-fg": "#19191c", "btn-hover": "#e2df4a",
        "focus": "#8f8bff", "tab-on": "#45454e", "feature-bg": "#2a2a30", "feature-fg": "#ffffff",
        "amber": "#efbd58", "blue": "#8fb0ff", "violet": "#b7a1ff", "green": "#7fc99b", "red": "#f19a93",
        "gray": "#b1b0ba", "cyan": "#67d4ea", "scheme": "dark",
    },
}

CHIP_COLORS = {
    "waiting": "amber", "assigned": "blue", "in_progress": "violet", "resolved": "green", "self_resolved": "green",
    "critical": "red", "high": "amber", "normal": "blue", "later": "gray", "hotspot": "amber", "pending": "amber",
    "confirmed": "green", "separate": "gray", "new": "blue", "needs_info": "amber", "overdue": "red",
    "duplicate": "gray", "open": "amber",
}
CATEGORY_STYLE = {
    "plumbing": ("droplets", "cyan"), "electricity": ("zap", "amber"),
    "cleanliness": ("brush-cleaning", "green"), "internet": ("wifi", "blue"),
}

# Icons usable from a button or nav-link key: key="i_<name>__<anything>". Keep this list to what the pages use.
ICON_BUTTONS = [
    "house", "file-pen-line", "ticket", "layout-dashboard", "map", "log-out", "sun", "moon", "send", "arrow-up-right",
    "user-check", "sparkles", "check", "circle-check", "undo-2", "refresh-cw", "x", "hand-heart", "bell", "sticky-note",
    "log-in", "user-plus", "arrow-right", "git-merge", "locate-fixed", "triangle-alert",
    "activity", "map-pinned", "wrench", "clock", "clipboard-list", "megaphone",
]

FONTS = "@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=Manrope:wght@500;600;700;800&display=swap');"

CSS = """
:root{--sidebar:#19191c;--yellow:#f3f05c;--hero-sub:#5e5e3b;--head:'Manrope','DM Sans',system-ui,sans-serif;--body:'DM Sans',system-ui,sans-serif}
html,body,.stApp,[data-testid="stAppViewContainer"],[data-testid="stMain"]{font-family:var(--body)}
.stApp,[data-testid="stAppViewContainer"],[data-testid="stMain"]{background:var(--bg)!important;color:var(--ink)}
[data-testid="stHeader"]{background:transparent!important}
.stAppDeployButton,[data-testid="stToolbarActions"],#MainMenu,footer{display:none!important}
.stMainBlockContainer,[data-testid="stMainBlockContainer"]{max-width:1400px;padding:1.4rem clamp(16px,3.5vw,48px) 3.5rem!important}
.stApp p,.stApp li,.stApp label,.stApp [data-testid="stMarkdownContainer"],.stApp [data-testid="stWidgetLabel"] p{color:var(--ink)}
.stApp h1,.stApp h2,.stApp h3,.stApp h4,.stApp h5{font-family:var(--head);color:var(--ink);letter-spacing:-.03em;font-weight:800}
.stApp [data-testid="stCaptionContainer"],.stApp [data-testid="stCaptionContainer"] p{color:var(--muted)}
.stApp a{color:var(--ink)}
.cc-i{flex:none;vertical-align:-.16em}
/* ---------- sidebar (always dark) ---------- */
[data-testid="stSidebar"]{background:var(--sidebar)!important;border-right:0}
[data-testid="stSidebar"] *{color:#c9c9d0}
[data-testid="stSidebarHeader"]{display:none}
[data-testid="stSidebarUserContent"]{padding:1.7rem 1rem 1rem!important}
.cc-logo{display:grid;grid-template-columns:max-content;font:800 34px/.8 var(--head);letter-spacing:-2.6px;margin:4px 0 38px 6px;color:#fff;position:relative}
.cc-logo span,.cc-logo b{color:#fff!important}.cc-logo b{margin-left:-2px}
.cc-logo small{position:absolute;left:calc(100% + 8px);bottom:0;font:700 6px/1.2 var(--body);letter-spacing:.6px;writing-mode:vertical-rl;color:#8d8d96!important}
.cc-side-label{font-size:10px;letter-spacing:1.8px;color:#777780!important;font-weight:800;margin:0 0 10px 11px}
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]{display:flex;align-items:center;gap:11px;border-radius:8px;padding:.7rem .75rem;color:#b5b5bd;transition:background .2s,color .2s,transform .2s;text-decoration:none}
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]:hover{background:rgba(255,255,255,.07);color:#fff;transform:translateX(2px)}
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] p{font-weight:700;font-size:13.5px;color:inherit}
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"][aria-current="page"],[data-testid="stSidebar"] [class*="__active"] [data-testid="stPageLink-NavLink"]{background:#2b2b30;color:#fff;box-shadow:inset 3px 0 var(--yellow)}
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"][aria-current="page"] p,[data-testid="stSidebar"] [class*="__active"] [data-testid="stPageLink-NavLink"] p{color:#fff}
.cc-side-note{border:1px solid #38383e;background:#222226;border-radius:10px;padding:14px;margin:1.6rem 0 .8rem}
.cc-side-note b{font-size:12px;color:#fff!important;display:flex;align-items:center;gap:7px}
.cc-side-note p{font-size:11px;line-height:1.7;color:#aaaab3!important;margin:.5rem 0 0}
.cc-user{display:flex;align-items:center;gap:10px;border-top:1px solid #34343a;padding-top:1rem;margin-top:.4rem}
.cc-avatar{width:34px;height:34px;border-radius:50%;display:grid;place-items:center;background:var(--yellow);color:#19191c!important;font:800 13px var(--head);flex:none}
.cc-user b{display:block;font-size:12.5px;color:#fff!important}.cc-user small{display:block;font-size:11px;color:#9a9aa3!important;margin-top:2px}
[data-testid="stSidebar"] [data-testid^="stBaseButton"]{background:transparent!important;border:1px solid #38383e!important;color:#d6d6dc!important;justify-content:flex-start}
[data-testid="stSidebar"] [data-testid^="stBaseButton"]:hover{background:rgba(255,255,255,.08)!important;color:#fff!important}
/* ---------- top bar ---------- */
.st-key-topbar{align-items:center!important;margin-bottom:.4rem}
.st-key-topbar>div:first-child{flex:1 1 auto}
.cc-crumb small{font-size:11px;letter-spacing:1.2px;color:var(--muted);font-weight:800}
.cc-crumb small b{color:var(--ink)}.cc-crumb p{margin:.35rem 0 0;font-size:13px;color:var(--muted)!important}
[class*="__theme"] button{width:38px!important;height:38px!important;min-height:38px!important;padding:0!important;border-radius:50%!important;font-size:0!important;justify-content:center!important;background:var(--paper)!important;border:1px solid var(--line)!important;color:var(--ink)!important}
[class*="__theme"] button:hover{transform:rotate(18deg) scale(1.06)!important}
[class*="__theme"] button::before{margin:0!important;width:18px!important;height:18px!important}
/* ---------- page intro ---------- */
.cc-kicker{display:block;color:var(--muted);font-size:10.5px;font-weight:800;letter-spacing:1.8px}
.cc-intro{margin:.4rem 0 1.4rem}.cc-intro h1{font-size:clamp(30px,4vw,44px)!important;line-height:1.08;margin:.55rem 0 .45rem!important;padding:0!important}
.cc-intro p{max-width:640px;color:var(--muted)!important;font-size:14px;line-height:1.7;margin:0}
.cc-section{display:flex;justify-content:space-between;align-items:flex-end;gap:12px;margin:1.8rem 0 .9rem}
.cc-section h2{font-size:21px!important;margin:.4rem 0 0!important;padding:0!important}.cc-section .right{color:var(--muted);font-size:12px;display:flex;align-items:center;gap:7px}
.cc-live{width:8px;height:8px;border-radius:50%;background:#7fc99b;display:inline-block;animation:ccPulse 2s infinite}
/* ---------- cards ---------- */
[data-testid="stVerticalBlockBorderWrapper"]{border-radius:12px!important;border:1px solid var(--line)!important;background:var(--paper);transition:border-color .2s,box-shadow .2s}
[data-testid="stVerticalBlockBorderWrapper"]:hover{box-shadow:var(--shadow)}
[data-testid="stExpander"]{border:1px solid var(--line)!important;border-radius:12px!important;background:var(--paper)}
[data-testid="stExpander"] summary:hover{background:transparent}
.cc-card{background:var(--paper);border:1px solid var(--line);border-radius:12px;padding:1rem 1.1rem}
.cc-card h4{margin:0 0 .25rem}.cc-card p{color:var(--muted)!important;margin:0}
.cc-grid{display:grid;gap:12px}.cc-grid.stats{grid-template-columns:repeat(auto-fit,minmax(190px,1fr))}.cc-grid.cards{grid-template-columns:repeat(auto-fill,minmax(280px,1fr))}
.cc-stat{position:relative;background:var(--paper);border:1px solid var(--line);border-radius:12px;padding:1.1rem 1.2rem;min-height:128px;transition:transform .25s,box-shadow .25s;animation:ccRise .45s both}
.cc-stat:hover{transform:translateY(-4px);box-shadow:var(--shadow)}
.cc-stat .lbl{display:flex;align-items:center;gap:7px;color:var(--muted);font-size:12px;font-weight:600}
.cc-stat .val{display:block;font:800 34px var(--head);letter-spacing:-1.2px;margin:.9rem 0 .25rem;color:var(--ink)}
.cc-stat .hint{font-size:11.5px;color:var(--muted)}
.cc-stat.featured{background:var(--feature-bg);border-color:var(--feature-bg)}.cc-stat.featured .lbl,.cc-stat.featured .hint{color:#c0c0c7}.cc-stat.featured .val{color:var(--feature-fg)}
.cc-stat .bar{position:absolute;left:0;top:18px;bottom:18px;width:3px;border-radius:0 3px 3px 0;background:var(--c,var(--blue))}
.cc-issue{position:relative;overflow:hidden;background:var(--paper);border:1px solid var(--line);border-radius:12px;padding:1rem 1.1rem;transition:transform .25s,border-color .25s,box-shadow .25s;animation:ccRise .45s both}
.cc-issue:hover{transform:translateY(-4px);box-shadow:var(--shadow)}
.cc-issue h3{font-size:15px!important;line-height:1.45;margin:.9rem 0 .4rem!important;padding:0!important;letter-spacing:-.2px!important;overflow-wrap:anywhere}
.cc-top{display:flex;justify-content:space-between;align-items:center;gap:6px;flex-wrap:wrap}
.cc-foot{display:flex;justify-content:space-between;align-items:center;gap:8px;border-top:1px solid var(--line);margin-top:.9rem;padding-top:.75rem;font-size:12px;color:var(--muted)}
.cc-foot span{display:inline-flex;align-items:center;gap:6px}
.cc-meta{display:flex;align-items:center;gap:8px;color:var(--muted);font-size:13px;margin:.2rem 0}.cc-meta b{color:var(--ink)}
.cc-chip{display:inline-flex;align-items:center;gap:5px;border-radius:5px;padding:.22rem .55rem;font-size:11px;font-weight:800;white-space:nowrap;color:var(--c,var(--gray));background:color-mix(in srgb,var(--c,var(--gray)) 14%,transparent)}
.cc-chip i{width:6px;height:6px;border-radius:50%;background:currentColor;display:inline-block}
.cc-empty{border:1px dashed var(--line);background:var(--paper);border-radius:14px;text-align:center;padding:2.4rem 1.2rem;margin:.8rem 0}
.cc-empty .ico{display:grid;place-items:center;width:46px;height:46px;border-radius:13px;background:var(--soft);color:var(--ink);margin:0 auto .8rem}
.cc-empty b{font:800 17px var(--head);color:var(--ink)}.cc-empty p{font-size:13px;color:var(--muted)!important;margin:.4rem 0 0}
.cc-banner{display:flex;align-items:center;gap:10px;border-radius:10px;padding:.7rem 1rem;margin:0 0 .7rem;font-weight:600;font-size:13.5px;border:1px solid;animation:ccRise .35s both}
.cc-banner.critical{background:color-mix(in srgb,var(--red) 12%,transparent);color:var(--red);border-color:color-mix(in srgb,var(--red) 45%,transparent)}
.cc-banner.hotspot{background:color-mix(in srgb,var(--amber) 12%,transparent);color:var(--amber);border-color:color-mix(in srgb,var(--amber) 45%,transparent)}
.cc-banner.info{background:var(--soft);color:var(--ink);border-color:var(--line)}
.cc-banner.critical svg{animation:ccPulse 1.6s infinite}
.cc-steps{list-style:none;padding:0;margin:.4rem 0 0;border-left:2px solid var(--line);margin-left:6px}
.cc-steps li{position:relative;padding:0 0 1rem 1.2rem;color:var(--ink);font-weight:600;font-size:14px}
.cc-steps li::before{content:"";position:absolute;left:-7px;top:.3rem;width:12px;height:12px;border-radius:50%;background:var(--ink);box-shadow:0 0 0 3px var(--paper)}
.cc-steps li:first-child::before{background:var(--yellow);box-shadow:0 0 0 3px var(--paper),0 0 0 4px var(--ink)}
.cc-steps .detail{color:var(--muted);font-size:13px;font-weight:400}.cc-steps .when{color:var(--muted);font-size:11.5px;font-weight:400}
.cc-steps li .lk{display:inline-flex;align-items:center;gap:5px}
/* ---------- hero (yellow) ---------- */
.st-key-hero{position:relative;overflow:hidden;background:var(--yellow);border-radius:14px;padding:2.3rem clamp(20px,4vw,46px)!important;min-height:290px;isolation:isolate;animation:ccRise .5s both}
.st-key-hero .stMarkdown,.st-key-hero p,.st-key-hero h1,.st-key-hero em{color:#19191c!important}
.st-key-hero .cc-kicker{color:#68682f}.st-key-hero h1{font-size:clamp(32px,4.4vw,52px)!important;line-height:1.04;letter-spacing:-2.5px!important;margin:.9rem 0!important;padding:0!important;max-width:520px}
.st-key-hero h1 em{font-style:normal}.st-key-hero .sub{max-width:410px;color:var(--hero-sub)!important;font-size:14px;line-height:1.75;margin:0 0 1rem}
.st-key-hero [data-testid="stElementContainer"]{position:relative;z-index:2}
.st-key-hero [data-testid="stElementContainer"]:has(.cc-hero-art){position:static;z-index:auto;height:0}
.st-key-hero a[data-testid="stPageLink-NavLink"]{background:#19191c;border-radius:9px;padding:.75rem 1.1rem;width:fit-content;transition:transform .2s,background .2s;text-decoration:none}
.st-key-hero a[data-testid="stPageLink-NavLink"]:hover{background:#38383d;transform:translateY(-2px)}
.st-key-hero a[data-testid="stPageLink-NavLink"] *{color:#fff!important;font-weight:700}
.cc-hero-art{position:absolute!important;right:0;top:0;width:46%;height:100%;z-index:1!important;pointer-events:none}
.cc-orbit{position:absolute;width:300px;height:300px;border:1px solid rgba(37,37,28,.22);border-radius:50%;right:6%;top:8%;box-shadow:0 0 0 38px rgba(34,34,34,.03),0 0 0 78px rgba(34,34,34,.025);animation:ccSpin 60s linear infinite}
.cc-sun{position:absolute;width:108px;height:108px;background:#1c1c1e;border-radius:50%;right:25%;top:22%;animation:ccBreathe 6s ease-in-out infinite}
.cc-float{position:absolute;background:#fff;border-radius:10px;padding:.8rem .95rem;display:grid;gap:4px;box-shadow:0 10px 25px rgba(68,68,28,.2);animation:ccFloat 5s ease-in-out infinite}
.cc-float b{font-size:12.5px;display:flex;align-items:center;gap:7px;color:#19191c!important}.cc-float small{font-size:11px;color:#8b8a91!important}
.cc-float.one{top:24%;right:34%}.cc-float.two{top:60%;right:5%;animation-delay:-2.5s}
/* ---------- auth split ---------- */
.cc-auth-art{position:relative;overflow:hidden;background:#19191c;color:#fff;border-radius:16px;padding:2.4rem clamp(24px,3.5vw,56px) 1.6rem;min-height:640px;display:flex;flex-direction:column;justify-content:space-between;animation:ccRise .5s both}
.cc-auth-art::after{content:"";position:absolute;width:420px;height:420px;border:1px solid rgba(255,255,255,.08);border-radius:50%;right:-170px;bottom:60px;box-shadow:0 0 0 50px rgba(255,255,255,.02),0 0 0 100px rgba(255,255,255,.015);animation:ccSpin 90s linear infinite}
.cc-auth-art .cc-logo{font-size:clamp(46px,6vw,72px);letter-spacing:-5px;margin:0}.cc-auth-art .cc-logo small{font-size:8px}
.cc-auth-art h1{font-size:clamp(36px,4.4vw,60px)!important;line-height:1.03;letter-spacing:-3px!important;margin:1rem 0!important;color:#fff!important}
.cc-auth-art h1 em{font-style:normal;color:var(--yellow)}.cc-auth-art p{max-width:360px;color:#b6b6bd!important;font-size:14px;line-height:1.8}
.cc-auth-art .cc-kicker{color:#8b8a93}.cc-auth-art .foot{position:relative;z-index:1;color:#c7c7cd;font-size:12px;display:flex;align-items:center;gap:8px}
.cc-auth-art>*{position:relative;z-index:1}
.cc-auth-form h2{font-size:30px!important;margin:.5rem 0 .3rem!important;padding:0!important}.cc-auth-form p{color:var(--muted)!important;font-size:13.5px}
.st-key-auth_card{background:var(--paper)!important;border:1px solid var(--line)!important;border-radius:20px!important;padding:2.1rem clamp(20px,3vw,44px) 2.3rem!important;box-shadow:0 24px 60px -20px rgba(0,0,0,.25);transform-origin:top center;animation:ccAuthPop .7s cubic-bezier(.16,1,.3,1) both}
.st-key-auth_card [data-testid="stForm"],.st-key-auth_card [data-baseweb="tab-panel"]{animation:ccAuthFields .5s ease-out .25s both}
/* ---------- widgets ---------- */
[data-baseweb="input"],[data-baseweb="textarea"],[data-baseweb="select"]>div{background:var(--paper)!important;border-color:var(--line)!important;border-radius:8px!important;color:var(--ink)!important}
[data-baseweb="input"] input,[data-baseweb="textarea"] textarea,[data-baseweb="select"] div,[data-baseweb="select"] input{color:var(--ink)!important;-webkit-text-fill-color:var(--ink)}
[data-baseweb="input"] input::placeholder,[data-baseweb="textarea"] textarea::placeholder{color:var(--muted)!important;-webkit-text-fill-color:var(--muted);opacity:.8}
[data-baseweb="input"]:focus-within,[data-baseweb="textarea"]:focus-within,[data-baseweb="select"]>div:focus-within{border-color:var(--focus)!important;box-shadow:0 0 0 3px color-mix(in srgb,var(--focus) 25%,transparent)!important}
[data-baseweb="popover"] [data-baseweb="menu"],[data-baseweb="popover"]>div{background:var(--paper)!important;color:var(--ink)!important;border:1px solid var(--line);border-radius:10px}
[data-baseweb="popover"] li,[data-baseweb="popover"] li *{color:var(--ink)!important;background:transparent}[data-baseweb="popover"] li:hover,[data-baseweb="popover"] li[aria-selected="true"]{background:var(--soft)!important}
[data-testid="stFileUploaderDropzone"]{background:var(--paper)!important;border:1px dashed var(--line)!important;border-radius:10px!important}
[data-testid="stFileUploaderDropzone"] *{color:var(--muted)!important}
[data-testid^="stBaseButton"]{border-radius:9px!important;font-weight:700;gap:.45rem;transition:transform .2s,background .2s,box-shadow .2s,border-color .2s}
[data-testid^="stBaseButton"]:not(:disabled):hover{transform:translateY(-2px)}
[data-testid="stBaseButton-secondary"],[data-testid="stBaseButton-secondaryFormSubmit"]{background:var(--paper)!important;color:var(--ink)!important;border:1px solid var(--line)!important}
[data-testid="stBaseButton-secondary"]:not(:disabled):hover,[data-testid="stBaseButton-secondaryFormSubmit"]:not(:disabled):hover{border-color:var(--focus)!important;box-shadow:var(--shadow)}
[data-testid="stBaseButton-primary"],[data-testid="stBaseButton-primaryFormSubmit"]{background:var(--btn-bg)!important;color:var(--btn-fg)!important;border:0!important}
[data-testid="stBaseButton-primary"]:not(:disabled):hover,[data-testid="stBaseButton-primaryFormSubmit"]:not(:disabled):hover{background:var(--btn-hover)!important}
[data-testid^="stBaseButton"] p,[data-testid^="stBaseButton"] div{color:inherit!important;font-weight:700}
[data-testid^="stBaseButton"]:disabled{opacity:.55}
[data-baseweb="tab-list"]{gap:3px;background:var(--soft);padding:4px;border-radius:10px;width:fit-content;max-width:100%;overflow:auto}
[data-baseweb="tab"]{border-radius:7px!important;height:auto!important;padding:.55rem .95rem!important;background:transparent!important}
[data-baseweb="tab"] p{color:var(--muted)!important;font-weight:700;font-size:13px}
[data-baseweb="tab"][aria-selected="true"]{background:var(--tab-on)!important;box-shadow:0 2px 8px rgba(0,0,0,.08)}
[data-baseweb="tab"][aria-selected="true"] p{color:var(--ink)!important}
[data-baseweb="tab-highlight"],[data-baseweb="tab-border"]{display:none!important}
[data-testid="stTabs"] [data-baseweb="tab-panel"]{padding-top:1rem}
[data-testid="stAlert"]{border-radius:10px!important;border:1px solid var(--line)}
[data-testid="stMetric"]{background:var(--soft);border-radius:10px;padding:.7rem .9rem}
[data-testid="stMetricLabel"] p{color:var(--muted)!important}[data-testid="stMetricValue"]{color:var(--ink)!important;font-family:var(--head);font-weight:800}
[data-testid="stChatMessage"]{background:var(--soft)!important;border-radius:12px;padding:.7rem .9rem}
[data-testid="stChatMessageAvatarUser"],[data-testid="stChatMessageAvatarAssistant"]{background:var(--yellow)!important;color:#19191c!important;border-radius:9px}
[data-testid="stToast"]{background:#202023!important;border-radius:10px}[data-testid="stToast"] *{color:#fff!important}
hr{border-color:var(--line)!important}
[data-testid="stImage"] img{border-radius:10px}
iframe[title*="campus_map"]{border-radius:14px;border:1px solid var(--line)}
/* ---------- Lucide icons on buttons and links ---------- */
[class*="st-key-i_"] button::before,[class*="st-key-i_"] a[data-testid="stPageLink-NavLink"]::before{content:"";display:inline-block;flex:none;width:1.1em;height:1.1em;background:currentColor;-webkit-mask:var(--ic) center/contain no-repeat;mask:var(--ic) center/contain no-repeat}
[class*="st-key-i_"] a[data-testid="stPageLink-NavLink"]::before{width:18px;height:18px}
/* ---------- motion ---------- */
@keyframes ccRise{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
@keyframes ccAuthPop{0%{opacity:0;transform:translateY(34px) scale(.95)}70%{opacity:1;transform:translateY(-4px) scale(1.005)}100%{opacity:1;transform:none}}
@keyframes ccAuthFields{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}
@keyframes ccFloat{50%{transform:translateY(-8px) rotate(1deg)}}
@keyframes ccPulse{0%,100%{opacity:1}50%{opacity:.45}}
@keyframes ccSpin{to{transform:rotate(360deg)}}
@keyframes ccBreathe{50%{transform:scale(1.06)}}
.cc-grid>*:nth-child(2){animation-delay:.05s}.cc-grid>*:nth-child(3){animation-delay:.1s}.cc-grid>*:nth-child(4){animation-delay:.15s}.cc-grid>*:nth-child(5){animation-delay:.2s}.cc-grid>*:nth-child(6){animation-delay:.25s}
.cc-intro,.cc-section{animation:ccRise .4s both}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
@media (max-width:900px){.cc-hero-art{opacity:.25}.cc-auth-art{min-height:auto}}
@media (max-width:640px){.cc-hero-art{opacity:.12;width:90%}.cc-stat .val{font-size:28px}}
/* ---------- dashboard panels, incident rows, register table ---------- */
.cc-panel-head h3{font-family:var(--head);font-size:18px;font-weight:800;color:var(--ink);margin:0}
.cc-panel-head p{color:var(--muted);font-size:13px;margin:.2rem 0 0}
.cc-row{display:flex;align-items:center;gap:14px;padding:.25rem 0}
.cc-row-ico{width:38px;height:38px;border-radius:10px;background:var(--soft);display:grid;place-items:center;flex:none;color:var(--ink)}
.cc-row-main{flex:1;min-width:0}
.cc-row-main b{display:block;color:var(--ink);font-family:var(--head);font-size:15px;font-weight:700}
.cc-row-main .sub{display:block;color:var(--muted);font-size:12.5px;margin-top:2px}
.cc-row-chips{display:flex;gap:6px;flex-wrap:wrap;margin-top:6px}
.cc-row-count{text-align:right;flex:none;padding-left:10px;border-left:1px solid var(--line)}
.cc-row-count b{display:block;font-family:var(--head);font-size:22px;font-weight:800;color:var(--c)}
.cc-row-count span{color:var(--muted);font-size:11.5px}
.cc-tablewrap{overflow-x:auto;border:1px solid var(--line);border-radius:12px}
.cc-table{width:100%;border-collapse:collapse;font-size:13px;color:var(--ink)}
.cc-table th{text-align:left;color:var(--muted);font-weight:700;font-size:11.5px;text-transform:uppercase;letter-spacing:.04em;padding:.6rem .8rem;background:var(--soft);white-space:nowrap}
.cc-table td{padding:.6rem .8rem;border-top:1px solid var(--line);vertical-align:middle}
.cc-table .mono{font-family:ui-monospace,Menlo,monospace;font-size:12px;white-space:nowrap}
.cc-table .title{font-weight:600;min-width:200px}
.cc-table .muted{color:var(--muted);white-space:nowrap}
[class*="__cta_"] a[data-testid="stPageLink-NavLink"]{background:var(--btn-bg);color:var(--btn-fg)!important;border-radius:9px;padding:.6rem 1rem;justify-content:center;font-weight:700;text-decoration:none}
[class*="__cta_"] a[data-testid="stPageLink-NavLink"] *{color:var(--btn-fg)!important}
"""


@lru_cache(maxsize=1)
def _icon_css() -> str:
    rules = "".join(f'[class*="st-key-i_{n}__"]{{--ic:{mask_url(n)}}}' for n in ICON_BUTTONS)
    return rules


def esc(text: object) -> str:
    """HTML-escape any value for safe rendering."""
    return html.escape(str(text))


def mode() -> str:
    """'light' or 'dark' for this browser session. Starts from the browser's own setting, then follows the switch."""
    chosen = st.session_state.get("theme")
    if chosen in VARS:
        return chosen
    try:
        seen = st.context.theme.type
    except Exception:
        seen = None
    return seen if seen in VARS else "light"


def inject_css() -> None:
    """Apply the theme for the current mode. Call once per run from the entry script."""
    v = VARS[mode()]
    root = ":root{" + "".join(f"--{k}:{val};" for k, val in v.items() if k != "scheme") + f"color-scheme:{v['scheme']}}}"
    st.markdown(f"<style>{FONTS}{root}{CSS}{_icon_css()}</style>", unsafe_allow_html=True)


def _flip_theme() -> None:
    st.session_state["theme"] = "light" if mode() == "dark" else "dark"


def theme_toggle() -> None:
    """Round sun/moon button that flips light and dark for this session only."""
    dark = mode() == "dark"
    st.button("Switch to light mode" if dark else "Switch to dark mode", key=f"i_{'sun' if dark else 'moon'}__theme",
              on_click=_flip_theme, help="Switch to light mode" if dark else "Switch to dark mode")


def kicker(text: str) -> str:
    return f'<span class="cc-kicker">{esc(text.upper())}</span>'


def chip(status: str, label: str | None = None) -> str:
    """HTML status or urgency pill, coloured by mode. Use with st.markdown(..., unsafe_allow_html=True)."""
    color = CHIP_COLORS.get(status, "gray")
    return f'<span class="cc-chip" style="--c:var(--{color})"><i></i>{esc(label or status.replace("_", " "))}</span>'


def category_chip(category: str) -> str:
    """Category pill with its Lucide icon (plumbing, electricity, cleanliness, internet)."""
    ico, color = CATEGORY_STYLE.get(category, ("tag", "gray"))
    return f'<span class="cc-chip" style="--c:var(--{color})">{icon(ico, 12)}{esc(category.title())}</span>'


def meta(ico: str, text: str, strong: str = "") -> str:
    """One icon + text line. text is escaped; strong is shown bold before it."""
    lead = f"<b>{esc(strong)}</b> " if strong else ""
    return f'<div class="cc-meta">{icon(ico, 15)}<span>{lead}{esc(text)}</span></div>'


def card(title: str, body: str = "") -> None:
    """Rounded card with an escaped title and body."""
    text = f"<p>{esc(body)}</p>" if body else ""
    st.markdown(f'<div class="cc-card"><h4>{esc(title)}</h4>{text}</div>', unsafe_allow_html=True)


def _stat(label: str, value: object, hint: str, featured: bool, ico: str | None, color: str | None) -> str:
    cls = "cc-stat featured" if featured else "cc-stat"
    bar = f'<span class="bar" style="--c:var(--{color})"></span>' if color and not featured else ""
    lead = icon(ico, 14) if ico else ""
    sub = f'<span class="hint">{esc(hint)}</span>' if hint else ""
    return f'<div class="{cls}">{bar}<span class="lbl">{lead}{esc(label)}</span><span class="val">{esc(value)}</span>{sub}</div>'


def stat_row(items: list[dict]) -> None:
    """Responsive KPI grid. Each item: label, value, hint, featured, icon, color (amber/blue/green/red...)."""
    html_ = "".join(_stat(i["label"], i["value"], i.get("hint", ""), i.get("featured", False), i.get("icon"), i.get("color"))
                    for i in items)
    st.markdown(f'<div class="cc-grid stats">{html_}</div>', unsafe_allow_html=True)


_ACCENT = {"info": "blue", "ok": "green", "warn": "amber", "bad": "red"}


def metric_card(label: str, value: object, accent: str = "info") -> None:
    """Single KPI tile. accent is one of: info, ok, warn, bad."""
    st.markdown(f'<div class="cc-grid stats">{_stat(label, value, "", False, None, _ACCENT.get(accent, "blue"))}</div>',
                unsafe_allow_html=True)


def metric_row(items: list[tuple[str, object, str]]) -> None:
    """Row of KPI tiles from (label, value, accent) tuples."""
    stat_row([{"label": a, "value": v, "color": _ACCENT.get(c, "blue")} for a, v, c in items])


def issue_cards(items: list[dict]) -> None:
    """Grid of issue cards. Each item: category, status, status_label, title, where, reports, when (all plain text)."""
    out = []
    for i in items:
        out.append(
            f'<article class="cc-issue"><div class="cc-top">{category_chip(i["category"])}'
            f'{chip(i["status"], i.get("status_label"))}</div><h3>{esc(i["title"])}</h3>'
            f'{meta("map-pin", i["where"])}<div class="cc-foot"><span>{icon("users", 14)}{esc(i["reports"])}</span>'
            f'<span>{icon("clock", 14)}{esc(i["when"])}</span></div></article>'
        )
    st.markdown(f'<div class="cc-grid cards">{"".join(out)}</div>', unsafe_allow_html=True)


def banner(message: str, level: str = "info") -> None:
    """Full-width notice. level: critical, hotspot or info."""
    ico = {"critical": "siren", "hotspot": "triangle-alert"}.get(level, "info")
    st.markdown(f'<div class="cc-banner {esc(level)}">{icon(ico, 18)}<span>{esc(message)}</span></div>', unsafe_allow_html=True)


def page_header(kick: str, title: str, sub: str = "") -> None:
    """Page intro: small uppercase label, big title, optional one-line description."""
    text = f"<p>{esc(sub)}</p>" if sub else ""
    st.markdown(f'<div class="cc-intro">{kicker(kick)}<h1>{esc(title)}</h1>{text}</div>', unsafe_allow_html=True)


def dash_head(kick: str, title: str, sub: str = "") -> None:
    page_header(kick, title, sub)


def panel_head(title: str, sub: str = "") -> None:
    text = f"<p>{esc(sub)}</p>" if sub else ""
    st.markdown(f'<div class="cc-panel-head"><h3>{esc(title)}</h3>{text}</div>', unsafe_allow_html=True)


def list_row(ico: str, title: str, sub: str, chips: str = "", right: tuple | None = None) -> str:
    count = ""
    if right:
        n, label, color = right
        count = f'<div class="cc-row-count" style="--c:var(--{color})"><b>{esc(n)}</b><span>{esc(label)}</span></div>'
    return (f'<div class="cc-row"><span class="cc-row-ico">{icon(ico, 18)}</span>'
            f'<div class="cc-row-main"><b>{esc(title)}</b><span class="sub">{esc(sub)}</span>'
            f'<div class="cc-row-chips">{chips}</div></div>{count}</div>')


def section_head(kick: str, title: str, right: str = "", live: bool = False) -> None:
    """Section heading with label; right is plain text shown on the far side, live adds a pulsing dot."""
    dot = '<i class="cc-live"></i>' if live else ""
    side = f'<span class="right">{dot}{esc(right)}</span>' if right else ""
    st.markdown(f'<div class="cc-section"><div>{kicker(kick)}<h2>{esc(title)}</h2></div>{side}</div>', unsafe_allow_html=True)


def empty_state(title: str, text: str = "", ico: str = "inbox") -> None:
    """Dashed empty-state box with an icon."""
    body = f"<p>{esc(text)}</p>" if text else ""
    st.markdown(f'<div class="cc-empty"><div class="ico">{icon(ico, 22)}</div><b>{esc(title)}</b>{body}</div>',
                unsafe_allow_html=True)


def timeline(steps: list[dict]) -> None:
    """Stepper. Each step: {"label", "detail"(optional), "when"(optional), "internal"(optional, shows a lock)}."""
    items = "".join(
        '<li><div class="lk">' + (icon("lock", 13) if s.get("internal") else "") + f'{esc(s["label"])}</div>'
        + (f'<div class="detail">{esc(s["detail"])}</div>' if s.get("detail") else "")
        + (f'<div class="when">{esc(s["when"])}</div>' if s.get("when") else "")
        + "</li>"
        for s in steps
    )
    st.markdown(f'<ul class="cc-steps">{items}</ul>', unsafe_allow_html=True)


def brand() -> str:
    return '<div class="cc-logo"><span>campus</span><b>saathi</b><small>KR MANGALAM</small></div>'


def user_card(name: str, role: str) -> str:
    initial = (name.strip()[:1] or "?").upper()
    return f'<div class="cc-user"><span class="cc-avatar">{esc(initial)}</span><div><b>{esc(name)}</b><small>{esc(role)}</small></div></div>'


def hero_art() -> str:
    """Decorative animated shapes for the yellow hero. Pure CSS."""
    return (
        f'<div class="cc-hero-art"><div class="cc-orbit"></div><div class="cc-sun"></div>'
        f'<div class="cc-float one"><b>{icon("sparkles", 14)}Spotted it.</b><small>Describe the problem</small></div>'
        f'<div class="cc-float two"><b>{icon("circle-check", 14)}Tracked.</b><small>Follow every step</small></div></div>'
    )


_ML_CYCLE_MS = 6000
_EASE_OUT = "animation-timing-function:cubic-bezier(.16,1,.3,1)"
_ML_BASE = (
    ".ml-wrap{position:relative;display:inline-block;padding:.04em .08em .12em 0}"
    ".ml-line{position:absolute;left:0;top:0;width:3px;height:100%;background:#fff;opacity:0;transform-origin:0 50%}"
    ".ml-l{display:inline-block;line-height:1em}"
    "@media (prefers-reduced-motion:reduce){.ml-line{animation:none!important;opacity:0}.ml-l{animation:none!important;opacity:1}}"
)


def _keyframes(name: str, frames: list[tuple[int, str]]) -> str:
    steps = "".join(f"{100 * ms / _ML_CYCLE_MS:.3f}%{{{css}}}" for ms, css in frames)
    return f"@keyframes {name}{{{steps}100%{{opacity:0}}}}"


def _moving_line(text: str, uid: str, start: int = 0) -> tuple[str, str]:
    """Letters fade in behind a sweeping line, looping. Returns (markup, css)."""
    line = f"{uid}line"
    hidden = "transform:scaleY(0);opacity:0;left:0"
    line_frames = [
        (0, hidden),
        (start, hidden + ";" + _EASE_OUT),
        (start + 700, "transform:scaleY(1);opacity:1;left:0"),
        (start + 800, "transform:scaleY(1);opacity:1;left:0;" + _EASE_OUT),
        (start + 1600, "transform:scaleY(1);opacity:1;left:calc(100% + 10px)"),
        (start + 4600, "transform:scaleY(1);opacity:1;left:calc(100% + 10px)"),
        (start + 5400, "transform:scaleY(1);opacity:0;left:calc(100% + 10px)"),
    ]
    spans, rules, k = [], [_keyframes(line, line_frames)], 0
    for ch in text:
        if ch == " ":
            spans.append(" ")
            continue
        name, rise = f"{uid}{k}", start + 900 + 70 * k
        rules.append(_keyframes(name, [
            (0, "opacity:0"),
            (rise, "opacity:0;" + _EASE_OUT),
            (rise + 600, "opacity:1"),
            (start + 4600, "opacity:1"),
            (start + 5400, "opacity:0"),
        ]))
        spans.append(f'<span class="ml-l" style="animation:{name} {_ML_CYCLE_MS}ms linear infinite">{esc(ch)}</span>')
        k += 1
    markup = (f'<span class="ml-wrap"><span class="ml-line" style="animation:{line} {_ML_CYCLE_MS}ms linear infinite">'
              f'</span>{"".join(spans)}</span>')
    return markup, "".join(rules)


def auth_art() -> str:
    """Dark left panel of the sign-in screen, with the tagline animated letter by letter."""
    one, css_one = _moving_line("Small voices.", "mla")
    two, css_two = _moving_line("Big change.", "mlb", start=400)
    return (
        f'<section class="cc-auth-art"><style>{_ML_BASE}{css_one}{css_two}</style>{brand()}'
        f'<div>{kicker("Your campus. Your voice.")}'
        f'<h1>{one}<br><em>{two}</em></h1>'
        f'<p>Tell us what is broken in plain words. We turn it into a ticket and keep you posted until it is fixed.</p></div>'
        f'<div class="foot"><i class="cc-live"></i>Plumbing, electricity, cleanliness and internet, one campus.</div></section>'
    )
