"""
UI helpers — JRG Trading
CSS, HTML templates, and styling utilities for landing, auth, and dashboard pages.
"""

import streamlit as st

# ──────────────────────────────────────────────────────────────
#  Design tokens
# ──────────────────────────────────────────────────────────────
PRIMARY      = "#0D5C6A"
PRIMARY_DARK = "#094858"
PRIMARY_GLOW = "rgba(13, 92, 106, 0.15)"
BG           = "#F5F7F9"
WHITE        = "#FFFFFF"
TEXT         = "#0C1A2E"
TEXT_MUTED   = "#5A7080"
BORDER       = "#DDE5ED"


# ──────────────────────────────────────────────────────────────
#  Global CSS
# ──────────────────────────────────────────────────────────────
_GLOBAL_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,600;0,700;1,400&family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600&display=swap');

/* ── HIDE STREAMLIT CHROME ── */
#MainMenu                    {{ visibility: hidden; }}
footer                       {{ visibility: hidden; }}
[data-testid="stToolbar"]    {{ display: none; }}
[data-testid="stDecoration"] {{ display: none; }}

/* ── APP BASE ── */
.stApp {{
    background: {BG};
    font-family: 'DM Sans', system-ui, -apple-system, sans-serif;
}}

.main .block-container {{
    padding-top: 0 !important;
    padding-left: 0 !important;
    padding-right: 0 !important;
    max-width: 100% !important;
}}

/* ── HEADINGS ── */
h1, h2, h3, h4 {{
    font-family: 'Playfair Display', Georgia, serif;
    color: {TEXT};
    letter-spacing: -0.015em;
}}

/* ── TEXT INPUTS ── */
div[data-baseweb="input"] > div {{
    border: 1.5px solid {BORDER} !important;
    border-radius: 10px !important;
    background: {WHITE} !important;
    min-height: 44px !important;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
}}

div[data-baseweb="input"] > div:focus-within {{
    border-color: {PRIMARY} !important;
    box-shadow: 0 0 0 3px {PRIMARY_GLOW} !important;
}}

div[data-baseweb="input"] input {{
    font-family: 'DM Sans', sans-serif !important;
    font-size: 15px !important;
    color: {TEXT} !important;
    padding: 4px 8px !important;
}}

div[data-baseweb="input"] input::placeholder {{
    color: #9AABB8 !important;
    font-weight: 300 !important;
}}

/* Input labels */
.stTextInput label,
.stTextInput > div > label {{
    font-family: 'DM Sans', sans-serif !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    color: {TEXT_MUTED} !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    margin-bottom: 4px !important;
}}

/* ── CAPTION / HINT TEXT ── */
.stCaption, .stCaption p,
div[data-testid="stCaptionContainer"] {{
    font-family: 'DM Sans', sans-serif !important;
    font-size: 12px !important;
    color: #9AABB8 !important;
    line-height: 1.45 !important;
    margin-top: 2px !important;
}}

/* ── FORM SUBMIT (primary) ── */
div[data-testid="stFormSubmitButton"] > button {{
    background: {PRIMARY} !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 15px !important;
    font-weight: 500 !important;
    letter-spacing: 0.01em !important;
    padding: 0.68rem 1.5rem !important;
    width: 100% !important;
    transition: background 0.2s ease, box-shadow 0.2s ease, transform 0.15s ease !important;
}}

div[data-testid="stFormSubmitButton"] > button:hover {{
    background: {PRIMARY_DARK} !important;
    box-shadow: 0 4px 16px {PRIMARY_GLOW} !important;
    transform: translateY(-1px) !important;
}}

/* ── PRIMARY BUTTON ── */
div[data-testid="stButton"] > button[kind="primary"] {{
    background: {PRIMARY} !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 15px !important;
    font-weight: 500 !important;
    transition: background 0.2s ease, box-shadow 0.2s ease, transform 0.15s ease !important;
}}

div[data-testid="stButton"] > button[kind="primary"]:hover {{
    background: {PRIMARY_DARK} !important;
    box-shadow: 0 4px 16px {PRIMARY_GLOW} !important;
    transform: translateY(-1px) !important;
}}

/* ── SECONDARY / NAV BUTTONS (text-link style) ── */
div[data-testid="stButton"] > button[kind="secondary"],
div[data-testid="stButton"] > button:not([kind]) {{
    background: transparent !important;
    color: {PRIMARY} !important;
    border: none !important;
    border-radius: 6px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 14px !important;
    font-weight: 400 !important;
    padding: 0.35rem 0.6rem !important;
    box-shadow: none !important;
    transition: color 0.15s ease, background 0.15s ease !important;
    text-decoration: underline !important;
    text-underline-offset: 2px !important;
    text-decoration-color: rgba(13,92,106,0.35) !important;
}}

div[data-testid="stButton"] > button[kind="secondary"]:hover,
div[data-testid="stButton"] > button:not([kind]):hover {{
    color: {PRIMARY_DARK} !important;
    background: rgba(13,92,106,0.05) !important;
    transform: none !important;
    box-shadow: none !important;
    text-decoration-color: {PRIMARY} !important;
}}

/* ── FORM CARD ── */
div[data-testid="stForm"] {{
    background: {WHITE} !important;
    border-radius: 18px !important;
    padding: 36px 36px 28px !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05), 0 12px 40px rgba(0,0,0,0.07) !important;
    border: 1px solid rgba(0,0,0,0.05) !important;
}}

/* ── ALERTS ── */
div[data-testid="stAlert"] {{
    border-radius: 10px !important;
    font-family: 'DM Sans', sans-serif !important;
    border: none !important;
    font-size: 14px !important;
    line-height: 1.5 !important;
}}

/* ── CHECKBOX (terms) ── */
.stCheckbox label {{
    font-family: 'DM Sans', sans-serif !important;
    font-size: 14px !important;
    color: {TEXT_MUTED} !important;
}}

.stCheckbox > label > div[data-baseweb="checkbox"] > div:first-child {{
    border-color: {BORDER} !important;
    border-radius: 5px !important;
}}

/* ── DIVIDERS ── */
hr {{ border-color: #E8EEF4 !important; }}

/* ── MOBILE ── */
@media (max-width: 768px) {{
    div[data-testid="stForm"] {{
        padding: 24px 20px 20px !important;
        border-radius: 14px !important;
    }}
}}
</style>
"""


# ──────────────────────────────────────────────────────────────
#  Dashboard-wide CSS (tabs, metrics, tables, cards)
# ──────────────────────────────────────────────────────────────
_DASHBOARD_CSS = f"""
<style>
.main .block-container {{
    padding: 1.5rem 2rem 3rem !important;
    max-width: 100% !important;
}}

/* ── TABS ── */
.stTabs [data-baseweb="tab-list"] {{
    gap: 4px;
    border-bottom: 1.5px solid {BORDER} !important;
}}

.stTabs [data-baseweb="tab"] {{
    font-family: 'DM Sans', sans-serif !important;
    font-size: 14.5px !important;
    font-weight: 500 !important;
    color: {TEXT_MUTED} !important;
    padding: 10px 18px !important;
}}

.stTabs [aria-selected="true"] {{
    color: {PRIMARY} !important;
}}

.stTabs [data-baseweb="tab-highlight"] {{
    background-color: {PRIMARY} !important;
    height: 2.5px !important;
}}

/* ── METRICS ── */
div[data-testid="stMetric"] {{
    background: {WHITE} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 12px !important;
    padding: 16px 20px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
}}

div[data-testid="stMetricValue"] {{
    font-family: 'Playfair Display', Georgia, serif !important;
    color: {PRIMARY} !important;
    font-weight: 700 !important;
}}

div[data-testid="stMetricLabel"] {{
    font-family: 'DM Sans', sans-serif !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    color: {TEXT_MUTED} !important;
}}

/* ── DATAFRAMES / TABLES ── */
div[data-testid="stDataFrame"] {{
    border: 1px solid {BORDER} !important;
    border-radius: 10px !important;
    overflow: hidden !important;
}}

/* ── EXPANDERS ── */
div[data-testid="stExpander"] {{
    background: {WHITE} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 12px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
}}

div[data-testid="stExpander"] summary {{
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 500 !important;
    color: {TEXT} !important;
}}

/* ── BORDERED CONTAINERS (st.container(border=True)) ── */
div[data-testid="stVerticalBlockBorderWrapper"] > div {{
    border-color: {BORDER} !important;
    border-radius: 12px !important;
}}

/* ── DEFAULT BUTTONS (Add / Remove / actions outside forms) ── */
div[data-testid="stButton"] > button[kind="secondary"] {{
    background: {WHITE} !important;
    color: {PRIMARY} !important;
    border: 1.5px solid {PRIMARY} !important;
    border-radius: 8px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 500 !important;
    text-decoration: none !important;
    padding: 0.5rem 1.1rem !important;
}}

div[data-testid="stButton"] > button[kind="secondary"]:hover {{
    background: rgba(13,92,106,0.06) !important;
    color: {PRIMARY_DARK} !important;
    border-color: {PRIMARY_DARK} !important;
}}

/* ── SLIDERS ── */
div[data-testid="stSlider"] [role="slider"] {{
    background-color: {PRIMARY} !important;
}}

/* ── SELECTBOX / NUMBER INPUT ── */
div[data-baseweb="select"] > div,
div[data-testid="stNumberInput"] input {{
    border-radius: 10px !important;
    border-color: {BORDER} !important;
}}
</style>
"""


def inject_global_styles() -> None:
    st.markdown(_GLOBAL_CSS, unsafe_allow_html=True)


def inject_dashboard_styles() -> None:
    """Apply the Simple Elegance design system to the authenticated dashboard pages."""
    st.markdown(_GLOBAL_CSS, unsafe_allow_html=True)
    st.markdown(_DASHBOARD_CSS, unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────
#  Dashboard HTML helpers
# ──────────────────────────────────────────────────────────────

def app_header_html(username: str) -> str:
    """Top brand bar for the authenticated dashboard."""
    return f"""
<div style="
    display:flex;align-items:center;justify-content:space-between;
    padding:4px 0 20px;border-bottom:1px solid {BORDER};margin-bottom:20px;
">
    <div style="display:flex;align-items:center;gap:12px;">
        <span style="font-size:24px;">📈</span>
        <div>
            <div style="font-family:'Playfair Display',Georgia,serif;font-size:22px;
                font-weight:700;color:{TEXT};letter-spacing:-0.01em;line-height:1.2;">
                JRG Trading</div>
            <div style="font-family:'DM Sans',sans-serif;font-size:12.5px;color:{TEXT_MUTED};">
                Welcome back, {username}</div>
        </div>
    </div>
</div>
"""


def section_header_html(eyebrow: str, title: str, subtitle: str = "") -> str:
    """Small uppercase eyebrow + serif title used to open each dashboard tab."""
    subtitle_html = (
        f'<p style="font-family:\'DM Sans\',sans-serif;font-size:14px;'
        f'color:{TEXT_MUTED};margin:6px 0 0;font-weight:300;">{subtitle}</p>'
        if subtitle else ""
    )
    return f"""
<div style="margin:4px 0 20px;">
    <p style="font-family:'DM Sans',sans-serif;font-size:11px;font-weight:600;
        letter-spacing:0.12em;text-transform:uppercase;color:{PRIMARY};margin:0 0 4px;">
        {eyebrow}</p>
    <h2 style="font-family:'Playfair Display',Georgia,serif;font-size:26px;
        font-weight:700;color:{TEXT};margin:0;letter-spacing:-0.01em;">{title}</h2>
    {subtitle_html}
</div>
"""


def status_badge_html(status: str) -> str:
    """Small pill badge for notification status: 'active' | 'triggered' | 'inactive'."""
    styles = {
        "active":    ("#10B981", "rgba(16,185,129,0.1)",  "Active"),
        "triggered": ("#EF4444", "rgba(239,68,68,0.1)",   "Triggered"),
        "inactive":  (TEXT_MUTED, "rgba(90,112,128,0.08)", "Inactive"),
    }
    color, bg, label = styles.get(status, styles["inactive"])
    return (
        f'<span style="display:inline-block;padding:3px 12px;border-radius:100px;'
        f'background:{bg};color:{color};font-family:\'DM Sans\',sans-serif;'
        f'font-size:12px;font-weight:600;">{label}</span>'
    )


def news_card_html(title: str, url: str, source: str, date_str: str, description: str, ticker: str = "") -> str:
    """Clean card layout for a single news article."""
    ticker_tag = (
        f'<span style="display:inline-block;margin-bottom:8px;padding:2px 10px;'
        f'border-radius:100px;background:{PRIMARY_GLOW};color:{PRIMARY};'
        f'font-family:\'DM Sans\',sans-serif;font-size:11px;font-weight:600;">{ticker}</span>'
        if ticker else ""
    )
    return f"""
<div style="
    background:{WHITE};border:1px solid {BORDER};border-radius:12px;
    padding:18px 20px;margin-bottom:12px;box-shadow:0 1px 3px rgba(0,0,0,0.04);
">
    {ticker_tag}
    <a href="{url}" target="_blank" style="
        display:block;font-family:'Playfair Display',Georgia,serif;font-size:17px;
        font-weight:600;color:{TEXT};text-decoration:none;margin:0 0 6px;line-height:1.35;
    ">{title}</a>
    <p style="font-family:'DM Sans',sans-serif;font-size:13px;color:{TEXT_MUTED};
        margin:0 0 8px;">{source} · {date_str}</p>
    <p style="font-family:'DM Sans',sans-serif;font-size:14px;color:{TEXT};
        margin:0;line-height:1.6;font-weight:300;">{description}</p>
</div>
"""


def empty_state_html(icon: str, title: str, text: str) -> str:
    """Friendly empty-state card for sections with no data yet."""
    return f"""
<div style="
    background:{WHITE};border:1px solid {BORDER};border-radius:14px;
    padding:48px 24px;text-align:center;
">
    <div style="font-size:36px;margin-bottom:12px;">{icon}</div>
    <h3 style="font-family:'Playfair Display',Georgia,serif;font-size:19px;
        font-weight:600;color:{TEXT};margin:0 0 6px;">{title}</h3>
    <p style="font-family:'DM Sans',sans-serif;font-size:14px;color:{TEXT_MUTED};
        margin:0;font-weight:300;">{text}</p>
</div>
"""


# ──────────────────────────────────────────────────────────────
#  Small HTML helpers
# ──────────────────────────────────────────────────────────────

def field_hint_html(text: str) -> str:
    return (
        f'<p style="margin:2px 0 12px;font-family:\'DM Sans\',sans-serif;'
        f'font-size:12px;color:#9AABB8;line-height:1.45;">{text}</p>'
    )


def password_strength_html(password: str) -> str:
    """Returns an HTML strength bar + label for the given password."""
    if not password:
        return ""

    score = 0
    if len(password) >= 8:                                        score += 1
    if len(password) >= 12:                                       score += 1
    if any(c.isupper() for c in password):                        score += 1
    if any(c.isdigit() for c in password):                        score += 1
    if any(c in "!@#$%^&*()_+-=[]{}|;'\",./<>?" for c in password): score += 1

    if score <= 1:
        label, color, filled = "Weak",   "#EF4444", 1
    elif score == 2:
        label, color, filled = "Fair",   "#F59E0B", 2
    elif score == 3:
        label, color, filled = "Good",   "#3B82F6", 3
    else:
        label, color, filled = "Strong", "#10B981", 4

    segments = []
    for i in range(4):
        bg = color if i < filled else "#E8EEF4"
        segments.append(f'<div style="flex:1;height:3px;border-radius:3px;background:{bg};"></div>')
    bars = "".join(segments)

    return (
        f'<div style="margin:4px 0 12px;">'
        f'<div style="display:flex;gap:4px;margin-bottom:5px;">{bars}</div>'
        f'<span style="font-family:\'DM Sans\',sans-serif;font-size:12px;'
        f'color:{color};font-weight:500;">{label}</span>'
        f'<span style="font-family:\'DM Sans\',sans-serif;font-size:12px;'
        f'color:#9AABB8;"> strength</span>'
        f'</div>'
    )


def inline_error_html(text: str) -> str:
    return (
        f'<p style="margin:2px 0 10px;font-family:\'DM Sans\',sans-serif;'
        f'font-size:12px;color:#EF4444;font-weight:500;">{text}</p>'
    )


def auth_switch_html(message: str) -> str:
    return (
        f'<div style="text-align:center;margin:16px 0 4px;'
        f'font-family:\'DM Sans\',sans-serif;font-size:14px;color:#8A9FAD;">'
        f'{message}</div>'
    )


# ──────────────────────────────────────────────────────────────
#  Landing page HTML
# ──────────────────────────────────────────────────────────────

LANDING_HERO_HTML = """
<div style="
    background: linear-gradient(160deg, #072E38 0%, #0D5C6A 55%, #147A8A 100%);
    padding: 88px 24px 72px;
    text-align: center;
    position: relative;
    overflow: hidden;
">
    <div style="position:absolute;top:-80px;right:-80px;width:380px;height:380px;
        background:rgba(255,255,255,0.025);border-radius:50%;pointer-events:none;"></div>
    <div style="position:absolute;bottom:-100px;left:-60px;width:280px;height:280px;
        background:rgba(255,255,255,0.02);border-radius:50%;pointer-events:none;"></div>

    <!-- Brand pill -->
    <div style="
        display:inline-flex;align-items:center;gap:10px;
        background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.14);
        border-radius:12px;padding:10px 20px;margin-bottom:40px;
        backdrop-filter:blur(6px);
    ">
        <span style="font-size:18px;">📈</span>
        <span style="
            font-family:'DM Sans',sans-serif;font-size:13px;font-weight:600;
            letter-spacing:0.1em;color:rgba(255,255,255,0.8);text-transform:uppercase;
        ">JRG Trading</span>
    </div>

    <h1 style="
        font-family:'Playfair Display',Georgia,serif;
        font-size:clamp(40px,6vw,68px);font-weight:700;color:#FFFFFF;
        line-height:1.1;margin:0 auto 18px;max-width:700px;letter-spacing:-0.025em;
    ">JRG Trading</h1>

    <p style="
        font-family:'Playfair Display',Georgia,serif;
        font-size:clamp(18px,2.5vw,26px);font-weight:400;font-style:italic;
        color:rgba(255,255,255,0.6);margin:0 0 24px;
    ">Your portfolio, your pace.</p>

    <p style="
        font-family:'DM Sans',sans-serif;font-size:clamp(14px,1.8vw,17px);
        color:rgba(255,255,255,0.58);max-width:440px;margin:0 auto 52px;
        line-height:1.75;font-weight:300;
    ">Track stocks, analyze performance, read market news, and build your investment
    knowledge — all in one elegant dashboard built for beginners.</p>

    <!-- Feature chips -->
    <div style="display:flex;flex-wrap:wrap;gap:10px;justify-content:center;">
        <span style="background:rgba(255,255,255,0.09);color:rgba(255,255,255,0.85);
            padding:8px 18px;border-radius:100px;font-size:13px;font-family:'DM Sans';
            border:1px solid rgba(255,255,255,0.11);">📊 Portfolio tracking</span>
        <span style="background:rgba(255,255,255,0.09);color:rgba(255,255,255,0.85);
            padding:8px 18px;border-radius:100px;font-size:13px;font-family:'DM Sans';
            border:1px solid rgba(255,255,255,0.11);">📈 Live charts</span>
        <span style="background:rgba(255,255,255,0.09);color:rgba(255,255,255,0.85);
            padding:8px 18px;border-radius:100px;font-size:13px;font-family:'DM Sans';
            border:1px solid rgba(255,255,255,0.11);">📰 Market news</span>
        <span style="background:rgba(255,255,255,0.09);color:rgba(255,255,255,0.85);
            padding:8px 18px;border-radius:100px;font-size:13px;font-family:'DM Sans';
            border:1px solid rgba(255,255,255,0.11);">📚 Learn to invest</span>
        <span style="background:rgba(255,255,255,0.09);color:rgba(255,255,255,0.85);
            padding:8px 18px;border-radius:100px;font-size:13px;font-family:'DM Sans';
            border:1px solid rgba(255,255,255,0.11);">🔔 Price alerts</span>
    </div>
</div>

<!-- CTA bridge -->
<div style="
    background:#F5F7F9;padding:52px 24px 24px;text-align:center;
    border-bottom:1px solid #E2EAF0;
">
    <p style="
        font-family:'DM Sans',sans-serif;font-size:11px;font-weight:600;
        letter-spacing:0.12em;text-transform:uppercase;color:#7A95A8;margin:0 0 12px;
    ">Get started — it's free</p>
    <h2 style="
        font-family:'Playfair Display',Georgia,serif;
        font-size:clamp(20px,3vw,28px);font-weight:600;color:#0C1A2E;margin:0 0 8px;
    ">Ready to take control of your investments?</h2>
    <p style="
        font-family:'DM Sans',sans-serif;font-size:15px;color:#5A7080;
        margin:0 0 32px;font-weight:300;
    ">Create a free account or sign in below.</p>
</div>
"""

FEATURES_HTML = """
<div style="background:#F5F7F9;padding:60px 24px 72px;">
    <div style="max-width:960px;margin:0 auto;">
        <p style="
            text-align:center;font-family:'DM Sans',sans-serif;font-size:11px;
            font-weight:600;letter-spacing:0.12em;text-transform:uppercase;
            color:#7A95A8;margin:0 0 12px;
        ">What you can do</p>
        <h2 style="
            text-align:center;font-family:'Playfair Display',Georgia,serif;
            font-size:clamp(22px,3vw,32px);font-weight:600;color:#0C1A2E;
            margin:0 auto 48px;max-width:480px;
        ">Everything a first-time investor needs</h2>

        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:24px;">
            <div style="background:white;border-radius:16px;padding:32px 28px;
                border:1px solid #E8EFF5;box-shadow:0 1px 4px rgba(0,0,0,0.04);">
                <div style="font-size:28px;margin-bottom:16px;">📊</div>
                <h3 style="font-family:'Playfair Display',Georgia,serif;font-size:18px;
                    font-weight:600;color:#0C1A2E;margin:0 0 8px;letter-spacing:-0.01em;">
                    Portfolio Tracking</h3>
                <p style="font-family:'DM Sans',sans-serif;font-size:14px;color:#6B8090;
                    line-height:1.65;margin:0;font-weight:300;">
                    Add your stocks and watch live prices auto-refresh every 60 seconds.</p>
            </div>
            <div style="background:white;border-radius:16px;padding:32px 28px;
                border:1px solid #E8EFF5;box-shadow:0 1px 4px rgba(0,0,0,0.04);">
                <div style="font-size:28px;margin-bottom:16px;">📈</div>
                <h3 style="font-family:'Playfair Display',Georgia,serif;font-size:18px;
                    font-weight:600;color:#0C1A2E;margin:0 0 8px;letter-spacing:-0.01em;">
                    Interactive Charts</h3>
                <p style="font-family:'DM Sans',sans-serif;font-size:14px;color:#6B8090;
                    line-height:1.65;margin:0;font-weight:300;">
                    Compare your holdings against the S&amp;P 500 with 30-day performance charts.</p>
            </div>
            <div style="background:white;border-radius:16px;padding:32px 28px;
                border:1px solid #E8EFF5;box-shadow:0 1px 4px rgba(0,0,0,0.04);">
                <div style="font-size:28px;margin-bottom:16px;">📰</div>
                <h3 style="font-family:'Playfair Display',Georgia,serif;font-size:18px;
                    font-weight:600;color:#0C1A2E;margin:0 0 8px;letter-spacing:-0.01em;">
                    Market News</h3>
                <p style="font-family:'DM Sans',sans-serif;font-size:14px;color:#6B8090;
                    line-height:1.65;margin:0;font-weight:300;">
                    Curated financial news for your portfolio and the broader market.</p>
            </div>
            <div style="background:white;border-radius:16px;padding:32px 28px;
                border:1px solid #E8EFF5;box-shadow:0 1px 4px rgba(0,0,0,0.04);">
                <div style="font-size:28px;margin-bottom:16px;">📚</div>
                <h3 style="font-family:'Playfair Display',Georgia,serif;font-size:18px;
                    font-weight:600;color:#0C1A2E;margin:0 0 8px;letter-spacing:-0.01em;">
                    Learn to Invest</h3>
                <p style="font-family:'DM Sans',sans-serif;font-size:14px;color:#6B8090;
                    line-height:1.65;margin:0;font-weight:300;">
                    Built-in lessons teach you investing fundamentals at your own pace.</p>
            </div>
        </div>
    </div>
</div>

<div style="background:#072E38;padding:28px 24px;text-align:center;">
    <p style="font-family:'DM Sans',sans-serif;font-size:12px;
        color:rgba(255,255,255,0.3);margin:0;font-weight:300;">
        © 2025 JRG Trading · For portfolio tracking only — not a brokerage</p>
</div>
"""


# ──────────────────────────────────────────────────────────────
#  Auth page header
# ──────────────────────────────────────────────────────────────

def auth_page_header_html(title: str, subtitle: str) -> str:
    return f"""
<div style="
    background: linear-gradient(160deg, #072E38 0%, #0D5C6A 55%, #147A8A 100%);
    padding: 56px 24px 80px;
    text-align: center;
    position: relative;
    overflow: hidden;
">
    <div style="position:absolute;top:-60px;right:-60px;width:300px;height:300px;
        background:rgba(255,255,255,0.025);border-radius:50%;pointer-events:none;"></div>

    <div style="
        display:inline-flex;align-items:center;gap:8px;
        background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.14);
        border-radius:10px;padding:8px 16px;margin-bottom:36px;
    ">
        <span style="font-size:16px;">📈</span>
        <span style="font-family:'DM Sans',sans-serif;font-size:12px;font-weight:600;
            letter-spacing:0.09em;color:rgba(255,255,255,0.75);text-transform:uppercase;">
            JRG Trading</span>
    </div>

    <h1 style="font-family:'Playfair Display',Georgia,serif;
        font-size:clamp(28px,4vw,40px);font-weight:700;color:white;
        margin:0 0 12px;letter-spacing:-0.02em;">{title}</h1>
    <p style="font-family:'DM Sans',sans-serif;font-size:16px;
        color:rgba(255,255,255,0.55);margin:0;font-weight:300;">{subtitle}</p>
</div>
"""
