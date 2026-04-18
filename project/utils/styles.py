THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

/* ── Reset & Base ── */
*, *::before, *::after { box-sizing: border-box; }

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    background: #0F172A !important;
    color: #E2E8F0 !important;
}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer { visibility: hidden; }
header { background: transparent !important; }
.block-container { padding-top: 1.5rem !important; padding-bottom: 2rem !important; max-width: 1400px; }
[data-testid="stSidebar"] > div:first-child { padding-top: 1rem; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0F172A 0%, #1E293B 100%) !important;
    border-right: 1px solid rgba(148,163,184,0.1) !important;
}
[data-testid="stSidebar"] * { color: #CBD5E1 !important; }
[data-testid="stSidebar"] .stRadio label { 
    padding: 0.5rem 0.75rem !important;
    border-radius: 8px !important;
    transition: all 0.2s !important;
    display: block !important;
}
[data-testid="stSidebar"] .stRadio label:hover { background: rgba(99,102,241,0.15) !important; color: #A5B4FC !important; }

/* ── KPI Cards ── */
.kpi-grid { display: grid; grid-template-columns: repeat(4,1fr); gap: 1rem; margin-bottom: 1.5rem; }
.kpi-card {
    background: linear-gradient(135deg, #1E293B 0%, #162032 100%);
    border: 1px solid rgba(148,163,184,0.12);
    border-radius: 16px;
    padding: 1.25rem 1.5rem;
    position: relative;
    overflow: hidden;
    transition: transform 0.2s, box-shadow 0.2s;
}
.kpi-card:hover { transform: translateY(-2px); box-shadow: 0 8px 32px rgba(0,0,0,0.4); }
.kpi-card::before {
    content: '';
    position: absolute;
    top: 0; right: 0;
    width: 80px; height: 80px;
    border-radius: 50%;
    opacity: 0.08;
    transform: translate(20px,-20px);
}
.kpi-card.blue::before   { background: #6366F1; }
.kpi-card.green::before  { background: #10B981; }
.kpi-card.amber::before  { background: #F59E0B; }
.kpi-card.red::before    { background: #EF4444; }
.kpi-label { font-size: 0.72rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; color: #64748B; margin-bottom: 0.4rem; }
.kpi-value { font-size: 1.6rem; font-weight: 800; line-height: 1; margin-bottom: 0.25rem; }
.kpi-card.blue  .kpi-value { color: #818CF8; }
.kpi-card.green .kpi-value { color: #34D399; }
.kpi-card.amber .kpi-value { color: #FBBF24; }
.kpi-card.red   .kpi-value { color: #F87171; }
.kpi-sub { font-size: 0.75rem; color: #475569; font-weight: 500; }

/* ── Section card ── */
.section-card {
    background: #1E293B;
    border: 1px solid rgba(148,163,184,0.1);
    border-radius: 16px;
    padding: 1.5rem;
    margin-bottom: 1.25rem;
}
.section-title {
    font-size: 0.85rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: #64748B;
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
.section-title span { color: #6366F1; }

/* ── Page header ── */
.page-header {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-bottom: 1.5rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid rgba(148,163,184,0.1);
}
.page-header-icon {
    width: 44px; height: 44px;
    border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.4rem;
    background: rgba(99,102,241,0.15);
}
.page-header-title { font-size: 1.4rem; font-weight: 800; color: #F8FAFC; line-height: 1; }
.page-header-sub   { font-size: 0.8rem; color: #64748B; margin-top: 2px; }

/* ── Tables ── */
[data-testid="stDataFrame"] {
    border: 1px solid rgba(148,163,184,0.1) !important;
    border-radius: 12px !important;
    overflow: hidden !important;
}
.stDataFrame thead tr th {
    background: #0F172A !important;
    color: #FFFFFF !important;
    font-size: 0.72rem !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
    border-bottom: 1px solid rgba(148,163,184,0.15) !important;
}
.stDataFrame tbody tr:hover td { background: rgba(99,102,241,0.06) !important; }

/* ── Inputs ── */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stSelectbox > div > div,
.stDateInput > div > div > input {
    border: 1px solid rgba(148,163,184,0.2) !important;
    border-radius: 8px !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}
.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus {
    border-color: #6366F1 !important;
    box-shadow: 0 0 0 3px rgba(99,102,241,0.2) !important;
}

/* ── Buttons ── */
.stButton > button {
    background: linear-gradient(135deg, #6366F1 0%, #4F46E5 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    padding: 0.5rem 1.25rem !important;
    transition: all 0.2s !important;
}
.stButton > button:hover { transform: translateY(-1px); box-shadow: 0 4px 16px rgba(99,102,241,0.4) !important; }

/* ── Alerts / info boxes ── */
.stSuccess { background: rgba(16,185,129,0.1) !important; border-left: 3px solid #10B981 !important; border-radius: 8px !important; }
.stError   { background: rgba(239,68,68,0.1)  !important; border-left: 3px solid #EF4444  !important; border-radius: 8px !important; }
.stWarning { background: rgba(245,158,11,0.1) !important; border-left: 3px solid #F59E0B  !important; border-radius: 8px !important; }
.stInfo    { background: rgba(99,102,241,0.1) !important; border-left: 3px solid #6366F1  !important; border-radius: 8px !important; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: #0F172A !important;
    border-radius: 10px !important;
    padding: 0.25rem !important;
    gap: 0.25rem !important;
    border-bottom: none !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: #64748B !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.82rem !important;
    border: none !important;
    padding: 0.4rem 1rem !important;
}
.stTabs [aria-selected="true"] {
    background: #6366F1 !important;
    color: white !important;
}

/* ── Metric ── */
[data-testid="stMetricValue"] { font-weight: 800 !important; }
[data-testid="stMetricLabel"] { font-size: 0.75rem !important; }
[data-testid="stMetricDelta"] { font-size: 0.75rem !important; }

/* ── Tags / badges ── */
.badge {
    display: inline-flex; align-items: center;
    padding: 0.2rem 0.6rem;
    border-radius: 100px;
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.04em;
}
.badge-posted { background: rgba(16,185,129,0.15); color: #34D399; }
.badge-draft  { background: rgba(245,158,11,0.15); color: #FBBF24; }
.badge-void   { background: rgba(239,68,68,0.15);  color: #F87171; }

/* ── Divider ── */
hr { border-color: rgba(148,163,184,0.1) !important; margin: 1rem 0 !important; }

/* ── Sidebar logo area ── */
.sidebar-logo {
    padding: 0.75rem 1rem 1.25rem;
    border-bottom: 1px solid rgba(148,163,184,0.1);
    margin-bottom: 0.75rem;
}
.sidebar-logo-text { font-size: 1.2rem; font-weight: 800; color: #F1F5F9; letter-spacing: -0.02em; }
.sidebar-logo-sub  { font-size: 0.7rem; color: #475569; font-weight: 500; }
.sidebar-logo-dot  { display: inline-block; width: 8px; height: 8px; background: #6366F1; border-radius: 50%; margin-right: 6px; box-shadow: 0 0 8px #6366F1; }

/* ── Expander ── */
.streamlit-expanderHeader {
    background: #0F172A !important;
    border: 1px solid rgba(148,163,184,0.1) !important;
    border-radius: 8px !important;
    color: #CBD5E1 !important;
    font-weight: 600 !important;
}
.streamlit-expanderContent {
    background: #0F172A !important;
    border: 1px solid rgba(148,163,184,0.1) !important;
    border-top: none !important;
    border-radius: 0 0 8px 8px !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #475569; }

/* ── Mono font for numbers ── */
.mono { font-family: 'JetBrains Mono', monospace !important; }

/* ── Statement tables ── */
.stmt-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
.stmt-table th {
    background: #0F172A; color: #94A3B8;
    font-size: 0.7rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.07em;
    padding: 0.6rem 0.75rem;
    border-bottom: 1px solid rgba(148,163,184,0.15);
    text-align: right;
}
.stmt-table th:first-child, .stmt-table th:nth-child(2) { text-align: left; }
.stmt-table td { padding: 0.45rem 0.75rem; border-bottom: 1px solid rgba(148,163,184,0.06); }
.stmt-table tr:hover td { background: rgba(99,102,241,0.04); }
.stmt-table .section-hd td { background: rgba(99,102,241,0.1); font-weight: 700; color: #A5B4FC; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; }
.stmt-table .total-row td  { background: rgba(148,163,184,0.06); font-weight: 700; border-top: 1px solid rgba(148,163,184,0.2); }
.stmt-table .net-row td    { background: rgba(99,102,241,0.15); font-weight: 800; color: #A5B4FC; font-size: 0.9rem; border-top: 2px solid #6366F1; }
.num { text-align: right; font-family: 'JetBrains Mono', monospace; font-size: 0.82rem; }
.neg { color: #F87171; }
.pos { color: #34D399; }
</style>
"""


def fmt_currency(v):
    if v is None:
        return "-"
    if v < 0:
        return f'<span class="neg">({abs(v):,.2f})</span>'
    if v == 0:
        return '<span style="color:#475569">-</span>'
    return f"{v:,.2f}"


def page_header(icon, title, subtitle=""):
    return f"""
    <div class="page-header">
        <div class="page-header-icon">{icon}</div>
        <div>
            <div class="page-header-title">{title}</div>
            <div class="page-header-sub">{subtitle}</div>
        </div>
    </div>"""


def kpi_card(label, value, sub, color="blue"):
    return f"""<div class="kpi-card {color}">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-sub">{sub}</div>
    </div>"""