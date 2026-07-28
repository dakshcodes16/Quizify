"""
Quizify design system — injected into every page.

Token system:
  Color    -- near-black base (not flat purple), violet/blue dual accent,
              teal for mastery/success, coral for weak/alert states.
  Type     -- Space Grotesk (display), Inter (body/UI), JetBrains Mono
              (stats, scores, agent tags -- anything numeric or "system").
  Layout   -- "agent signature" tags (AGENT 01 · CONTENT) mark which of
              the four agents produced a given piece of UI, so the
              multi-agent architecture is visible in the product itself.
  Motion   -- a single signature animation (the gradient mesh orb) reused
              across hero / loading / status contexts rather than
              scattered one-off effects.
"""

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500;600;700&display=swap');

:root {
    --bg-base: #0B0A1A;
    --bg-elevated: #13112480;
    --surface: #1A1830;
    --surface-hover: #211D3D;
    --border: rgba(255,255,255,0.08);
    --border-strong: rgba(255,255,255,0.14);
    --violet: #7C5CFF;
    --blue: #4F7CFF;
    --teal: #26EBC4;
    --coral: #FF6B81;
    --amber: #FFB454;
    --text-primary: #F3F1FA;
    --text-secondary: #9D97C2;
    --text-muted: #6B6590;
    --font-display: 'Space Grotesk', sans-serif;
    --font-body: 'Inter', sans-serif;
    --font-mono: 'JetBrains Mono', monospace;
}

html, body, [class*="css"] { font-family: var(--font-body); }

.stApp {
    background:
        radial-gradient(ellipse 900px 600px at 15% -10%, rgba(124,92,255,0.16), transparent 60%),
        radial-gradient(ellipse 700px 500px at 110% 10%, rgba(79,124,255,0.12), transparent 55%),
        var(--bg-base);
    color: var(--text-primary);
}

#MainMenu, footer, header { visibility: hidden; }

h1, h2, h3, h4 {
    font-family: var(--font-display);
    letter-spacing: -0.01em;
}

/* ================= Sidebar ================= */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #15132A 0%, #0D0C1C 100%);
    border-right: 1px solid var(--border);
}
section[data-testid="stSidebar"] * { color: var(--text-primary); }
section[data-testid="stSidebar"] .stCaption, section[data-testid="stSidebar"] small {
    color: var(--text-muted) !important;
}

/* ================= Agent signature tag ================= */
.agent-tag {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    font-family: var(--font-mono);
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    color: var(--text-muted);
    padding: 0.3rem 0.7rem;
    border: 1px solid var(--border);
    border-radius: 999px;
    background: rgba(255,255,255,0.02);
    margin-bottom: 0.85rem;
}
.agent-tag .dot {
    width: 6px; height: 6px; border-radius: 50%;
    background: var(--violet);
    box-shadow: 0 0 8px var(--violet);
}
.agent-tag.tag-eval .dot { background: var(--blue); box-shadow: 0 0 8px var(--blue); }
.agent-tag.tag-adapt .dot { background: var(--teal); box-shadow: 0 0 8px var(--teal); }
.agent-tag.tag-analytics .dot { background: var(--amber); box-shadow: 0 0 8px var(--amber); }

/* ================= Cards ================= */
.glass-card {
    background: linear-gradient(160deg, rgba(255,255,255,0.05), rgba(255,255,255,0.015));
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 1.85rem;
    margin-bottom: 1.1rem;
    box-shadow: 0 1px 0 rgba(255,255,255,0.04) inset, 0 20px 40px -24px rgba(0,0,0,0.6);
    transition: border-color 0.2s ease, transform 0.2s ease;
}
.glass-card:hover { border-color: var(--border-strong); }

.glass-card-flat {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 1.5rem;
}

/* ================= Real bordered containers (st.container(border=True)) =================
   Used instead of hand-rolled open/close <div class="glass-card"> markdown pairs --
   those never actually nested Streamlit widgets inside them (each st.markdown() call
   produces its own isolated DOM node), so widgets rendered "inside" them visually
   escaped the card. st.container(border=True) is the real, working primitive: it
   emits one element that does wrap everything added to it. We re-skin its default
   grey border here to match the glass-card look. */
div[data-testid="stVerticalBlockBorderWrapper"] {
    border: 1px solid var(--border) !important;
    border-radius: 20px !important;
    background: linear-gradient(160deg, rgba(255,255,255,0.05), rgba(255,255,255,0.015));
    box-shadow: 0 1px 0 rgba(255,255,255,0.04) inset, 0 20px 40px -24px rgba(0,0,0,0.6);
    transition: border-color 0.2s ease;
}
div[data-testid="stVerticalBlockBorderWrapper"]:hover { border-color: var(--border-strong) !important; }
div[data-testid="stVerticalBlockBorderWrapper"] > div { background: transparent !important; }

/* ================= Headline gradient ================= */
.gradient-text {
    background: linear-gradient(100deg, #C9BCFF 0%, var(--violet) 45%, var(--blue) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-family: var(--font-display);
    font-weight: 700;
}

.hero-eyebrow {
    font-family: var(--font-mono);
    font-size: 0.74rem;
    font-weight: 600;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--teal);
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.9rem;
}
.hero-title {
    font-family: var(--font-display);
    font-size: clamp(2.4rem, 5vw, 3.6rem);
    font-weight: 700;
    line-height: 1.06;
    letter-spacing: -0.02em;
    margin-bottom: 0.9rem;
}
.hero-subtitle {
    font-size: 1.1rem;
    line-height: 1.6;
    color: var(--text-secondary);
    max-width: 600px;
    margin-bottom: 1.6rem;
}

/* ================= Pills / status ================= */
.pill {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.28rem 0.8rem;
    border-radius: 999px;
    font-size: 0.76rem;
    font-weight: 600;
    font-family: var(--font-mono);
    background: rgba(124,92,255,0.12);
    border: 1px solid rgba(124,92,255,0.3);
    color: #C9BCFF;
}
.pill-success { background: rgba(38,235,196,0.1); border-color: rgba(38,235,196,0.35); color: var(--teal); }
.pill-warning { background: rgba(255,180,84,0.1); border-color: rgba(255,180,84,0.35); color: var(--amber); }
.pill-danger  { background: rgba(255,107,129,0.1); border-color: rgba(255,107,129,0.35); color: var(--coral); }

/* ================= Metric cards ================= */
.metric-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 1.4rem 1.5rem;
    position: relative;
    overflow: hidden;
}
.metric-card::before {
    content: "";
    position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, var(--violet), var(--blue));
}
.metric-value {
    font-family: var(--font-mono);
    font-size: 2.3rem;
    font-weight: 700;
    color: var(--text-primary);
    line-height: 1;
}
.metric-label {
    font-size: 0.78rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-top: 0.5rem;
    font-weight: 600;
}

/* ================= Buttons ================= */
.stButton > button {
    background: linear-gradient(100deg, var(--violet), var(--blue));
    color: white;
    border: none;
    border-radius: 12px;
    padding: 0.65rem 1.5rem;
    font-weight: 600;
    font-family: var(--font-body);
    box-shadow: 0 8px 20px -8px rgba(124,92,255,0.55);
    transition: transform 0.15s ease, box-shadow 0.15s ease, filter 0.15s ease;
}
.stButton > button:hover {
    transform: translateY(-1px);
    filter: brightness(1.08);
    box-shadow: 0 10px 26px -8px rgba(124,92,255,0.7);
}
.stButton > button:active { transform: translateY(0); }
.stButton > button:disabled {
    background: var(--surface);
    box-shadow: none;
    color: var(--text-muted);
}

/* secondary button variant via container key */
div[data-testid="stButton"] button[kind="secondary"] {
    background: transparent;
    border: 1px solid var(--border-strong);
    box-shadow: none;
}

/* ================= Inputs ================= */
.stTextInput input, .stTextArea textarea, .stNumberInput input {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    color: var(--text-primary) !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: var(--violet) !important;
    box-shadow: 0 0 0 3px rgba(124,92,255,0.18) !important;
}
.stSelectbox > div > div {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
}
div[data-baseweb="radio"] label, div[data-baseweb="select"] { color: var(--text-primary); }

/* ================= Tabs ================= */
.stTabs [data-baseweb="tab-list"] { gap: 0.4rem; border-bottom: 1px solid var(--border); }
.stTabs [data-baseweb="tab"] {
    background: transparent;
    border-radius: 10px 10px 0 0;
    color: var(--text-muted);
    font-weight: 600;
    padding: 0.6rem 1.1rem;
}
.stTabs [aria-selected="true"] {
    color: var(--text-primary) !important;
    background: var(--surface) !important;
    border-bottom: 2px solid var(--violet) !important;
}

/* ================= Progress ================= */
.stProgress > div > div {
    background: linear-gradient(90deg, var(--violet), var(--blue)) !important;
    border-radius: 999px;
}
.stProgress > div { background: var(--surface) !important; border-radius: 999px; }

/* ================= Feature cards ================= */
.feature-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 1.6rem;
    height: 100%;
    transition: border-color 0.2s ease, transform 0.2s ease;
}
.feature-card:hover { border-color: rgba(124,92,255,0.4); transform: translateY(-2px); }
.feature-icon {
    width: 38px; height: 38px;
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    background: linear-gradient(135deg, rgba(124,92,255,0.18), rgba(79,124,255,0.12));
    font-size: 1.2rem;
    margin-bottom: 0.85rem;
}
.feature-title {
    font-family: var(--font-display);
    font-weight: 600;
    font-size: 1.05rem;
    margin-bottom: 0.4rem;
}
.feature-desc { color: var(--text-secondary); font-size: 0.89rem; line-height: 1.55; }

/* ================= Question card ================= */
.question-card {
    background: linear-gradient(135deg, rgba(255,255,255,0.04), rgba(255,255,255,0.015)) !important;
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    border: 1px solid var(--border-strong) !important;
    border-radius: 20px !important;
    padding: 1.85rem 2rem !important;
    margin-bottom: 1.5rem !important;
    box-shadow: 0 20px 40px -20px rgba(0,0,0,0.5) !important;
}
.question-number {
    display: inline-flex;
    align-items: center; justify-content: center;
    width: 26px; height: 26px;
    border-radius: 8px;
    background: linear-gradient(135deg, var(--violet), var(--blue));
    font-family: var(--font-mono);
    font-weight: 700;
    font-size: 0.78rem;
    color: white;
    margin-right: 0.55rem;
}

/* ================= Signature orb (motion) ================= */
@keyframes orb-breathe {
    0%, 100% { transform: scale(1) translate(0,0); opacity: 0.55; }
    50% { transform: scale(1.08) translate(6px,-6px); opacity: 0.8; }
}
.signature-orb {
    width: 100%; height: 100%;
    border-radius: 50%;
    background: conic-gradient(from 180deg, var(--violet), var(--blue), var(--teal), var(--violet));
    filter: blur(40px);
    animation: orb-breathe 6s ease-in-out infinite;
}

@media (prefers-reduced-motion: reduce) {
    .signature-orb { animation: none; }
}

/* ================= Misc ================= */
hr { border-color: var(--border); }
[data-testid="stDataFrame"] { border-radius: 14px; overflow: hidden; border: 1px solid var(--border); }
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-thumb { background: var(--border-strong); border-radius: 8px; }

/* keyboard focus visibility (accessibility) */
a:focus-visible, button:focus-visible, input:focus-visible {
    outline: 2px solid var(--violet);
    outline-offset: 2px;
}

/* ================= Premium Radio Card & Visual Enhancements ================= */
div[data-testid="stRadio"] label:not([data-testid="stWidgetLabel"]) {
    background: rgba(255, 255, 255, 0.02) !important;
    border: 1px solid var(--border) !important;
    border-radius: 14px !important;
    padding: 0.95rem 1.4rem !important;
    margin-bottom: 0.7rem !important;
    width: 100% !important;
    display: flex !important;
    align-items: center !important;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    cursor: pointer !important;
}
div[data-testid="stRadio"] label:not([data-testid="stWidgetLabel"]):hover {
    background: rgba(124, 92, 255, 0.05) !important;
    border-color: rgba(124, 92, 255, 0.3) !important;
    transform: translateX(3px);
}
div[data-testid="stRadio"] label:not([data-testid="stWidgetLabel"])[data-checked="true"] {
    background: rgba(124, 92, 255, 0.1) !important;
    border-color: var(--violet) !important;
    box-shadow: 0 0 14px rgba(124, 92, 255, 0.15) !important;
}
div[data-testid="stRadio"] label:not([data-testid="stWidgetLabel"]) p {
    font-size: 0.98rem !important;
    font-weight: 500 !important;
    color: var(--text-primary) !important;
}

@keyframes timer-pulse {
    0%, 100% { transform: scale(1); box-shadow: 0 0 0 rgba(255, 107, 129, 0); }
    50% { transform: scale(1.05); box-shadow: 0 0 12px rgba(255, 107, 129, 0.3); }
}
.timer-pulse-critical {
    animation: timer-pulse 1s infinite alternate ease-in-out !important;
    border-color: var(--coral) !important;
    color: var(--coral) !important;
    background: rgba(255, 107, 129, 0.1) !important;
}

/* ================= Premium Sidebar Profile & Glowing Active Tabs ================= */
.sidebar-profile {
    background: linear-gradient(135deg, rgba(124,92,255,0.1) 0%, rgba(79,124,255,0.03) 100%) !important;
    border: 1px solid rgba(124,92,255,0.2) !important;
    border-radius: 16px !important;
    padding: 1rem 1.1rem !important;
    margin-bottom: 1.5rem !important;
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2) !important;
}
div[data-testid="stSidebar"] button[kind="primary"] {
    background: linear-gradient(90deg, rgba(124,92,255,0.16) 0%, rgba(79,124,255,0.04) 100%) !important;
    border-left: 4px solid var(--violet) !important;
    border-radius: 0 12px 12px 0 !important;
    border-top: none !important;
    border-right: none !important;
    border-bottom: none !important;
    color: var(--text-primary) !important;
    font-weight: 700 !important;
    box-shadow: none !important;
}
div[data-testid="stSidebar"] button[kind="secondary"] {
    border: 1px solid transparent !important;
    background: transparent !important;
    color: var(--text-secondary) !important;
    transition: all 0.2s ease !important;
}
div[data-testid="stSidebar"] button[kind="secondary"]:hover {
    background: rgba(255,255,255,0.03) !important;
    color: var(--text-primary) !important;
}

/* ================= Capsule tag style ================= */
.concept-badge {
    display: inline-block !important;
    background: rgba(255,255,255,0.03) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    padding: 0.25rem 0.65rem !important;
    font-size: 0.8rem !important;
    margin: 0.2rem !important;
    color: var(--text-secondary) !important;
    transition: all 0.2s ease !important;
}
.concept-badge:hover {
    border-color: rgba(124,92,255,0.25) !important;
    color: var(--text-primary) !important;
}
</style>
"""


def inject_css(st):
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def agent_tag(label: str, variant: str = "content") -> str:
    """Renders the small monospace 'AGENT 0X · NAME' tag used to attribute
    UI sections to the agent that produced them."""
    cls = {
        "content": "",
        "eval": "tag-eval",
        "adapt": "tag-adapt",
        "analytics": "tag-analytics",
    }.get(variant, "")
    return f'<div class="agent-tag {cls}"><span class="dot"></span>{label}</div>'
