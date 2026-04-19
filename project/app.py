import streamlit as st
import sys
import os

# Ensure imports work regardless of working directory
sys.path.insert(0, os.path.dirname(__file__))

import journal_enteries
from utils.database import init_db, seed_database
from utils.styles import THEME_CSS
import dashboard
import chart_of_accounts
import journal_entries
import ledger
import trial_balance
import income_statement
import balance_sheet

st.set_page_config(
    page_title="Atlas",
    page_icon="💠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Inject global CSS
st.markdown(THEME_CSS, unsafe_allow_html=True)

# Initialize database on first run
init_db()
seed_database()

# ── Sidebar Navigation ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="sidebar-logo">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
            <div style="width:32px;height:32px;background:linear-gradient(135deg,#6366F1,#4F46E5);border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:1rem">💠</div>
            <div>
                <div class="sidebar-logo-text">Atlas</div>
                <div class="sidebar-logo-sub">Accounting System</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div style="font-size:0.65rem;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;color:#334155;padding:0.5rem 0.25rem 0.25rem">Main Menu</div>', unsafe_allow_html=True)

    nav = st.radio(
        "Navigation",
        [
            "Dashboard",
            "Chart of Accounts",
            "Journal Entries",
            "General Ledger",
            "Trial Balance",
            "Income Statement",
            "Balance Sheet",
        ],
        label_visibility="collapsed",
    )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div style="font-size:0.65rem;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;color:#334155;padding:0.25rem">System</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Load Demos", use_container_width=True, help="Reset database and load 2024 demo data"):
            from utils.database import reset_db
            reset_db(include_entries=True)
            st.success("Demo data reloaded!")
            st.rerun()
    with col2:
        if st.button("Clear DB", use_container_width=True, help="Reset database and remove all entries"):
            from utils.database import reset_db
            reset_db(include_entries=False)
            st.success("Database cleared!")
            st.rerun()

    if st.button("Load Problem 3-1", use_container_width=True, help="Clear DB and populate with Problem 3-1 data"):
        import populate_problem_3_1_fixed
        populate_problem_3_1_fixed.reset_and_populate()
        st.success("Problem 3-1 data loaded successfully!")
        st.rerun()

    if st.button("Load Problem 3-7", use_container_width=True, help="Clear DB and populate with Problem 3-7 data"):
        import populate_problem_3_7
        populate_problem_3_7.reset_and_populate()
        st.success("Problem 3-7 data loaded successfully!")
        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    <div style="background:rgba(99,102,241,0.08);border:1px solid rgba(99,102,241,0.2);border-radius:10px;padding:0.75rem;font-size:0.72rem;color:#64748B">
        <div style="color:#818CF8;font-weight:700;margin-bottom:4px">💡 Quick Help</div>
        Start with <b style="color:#94A3B8">Journal Entries</b> to record transactions. 
        Reports auto-update from posted entries.
    </div>
    """, unsafe_allow_html=True)

# ── Page Router ───────────────────────────────────────────────────────────────
page_map = {
    "Dashboard":          dashboard.render,
    "Chart of Accounts":  chart_of_accounts.render,
    "Journal Entries":    journal_enteries.render,
    "General Ledger":     ledger.render,
    "Trial Balance":      trial_balance.render,
    "Income Statement":   income_statement.render,
    "Balance Sheet":      balance_sheet.render,
}

page_map[nav]()