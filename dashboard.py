import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import date, timedelta
from utils.database import get_income_statement, get_balance_sheet, get_journal_entries, get_ledger
from utils.styles import page_header, kpi_card, fmt_currency

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Plus Jakarta Sans", color="#94A3B8", size=11),
    margin=dict(l=10, r=10, t=30, b=10),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
)


def render():
    st.markdown(page_header("📊", "Financial Dashboard", "Real-time overview of your accounting data"), unsafe_allow_html=True)

    # Date range
    today = date.today()
    col1, col2, col3 = st.columns([2, 2, 3])
    with col1:
        start = st.date_input("From", value=date(today.year, 1, 1), key="dash_start")
    with col2:
        end = st.date_input("To", value=today, key="dash_end")
    with col3:
        st.markdown("<div style='height:1.8rem'></div>", unsafe_allow_html=True)
        if st.button("⟳  Refresh Dashboard"):
            st.rerun()

    st.divider()

    # ── Data ──────────────────────────────────────────────────────────────────
    is_df  = get_income_statement(start, end)
    bs_df  = get_balance_sheet(end)
    je_df  = get_journal_entries(start, end, status="Posted")

    rev_total  = is_df[is_df["type"] == "Revenue"]["net"].sum()
    exp_total  = is_df[is_df["type"] == "Expense"]["net"].sum()
    net_income = rev_total - exp_total

    assets    = bs_df[bs_df["type"] == "Asset"]["balance"].sum()
    liab      = bs_df[bs_df["type"] == "Liability"]["balance"].sum()
    equity    = bs_df[bs_df["type"] == "Equity"]["balance"].sum()

    cash_id_row = bs_df[bs_df["code"].str.startswith("10")]
    cash_balance = cash_id_row["balance"].sum() if not cash_id_row.empty else 0

    # ── KPI Cards ─────────────────────────────────────────────────────────────
    kpis = [
        ("Total Revenue",  f"${rev_total:,.0f}",  f"{len(je_df)} journal entries", "blue"),
        ("Net Income",     f"${net_income:,.0f}", f"Margin: {(net_income/rev_total*100 if rev_total else 0):.1f}%", "green" if net_income >= 0 else "red"),
        ("Total Assets",   f"${assets:,.0f}",     f"Liabilities: ${liab:,.0f}", "amber"),
        ("Cash Balance",   f"${cash_balance:,.0f}", f"Equity: ${equity:,.0f}", "blue"),
    ]

    cards_html = '<div class="kpi-grid">' + "".join(kpi_card(*k) for k in kpis) + "</div>"
    st.markdown(cards_html, unsafe_allow_html=True)

    # ── Charts row 1 ─────────────────────────────────────────────────────────
    c1, c2 = st.columns(2)

    with c1:
        # Revenue vs Expenses bar
        fig = go.Figure()
        fig.add_trace(go.Bar(
            name="Revenue", x=["Financial Summary"], y=[rev_total],
            marker_color="#6366F1", width=0.3,
            text=[f"${rev_total:,.0f}"], textposition="outside",
        ))
        fig.add_trace(go.Bar(
            name="Expenses", x=["Financial Summary"], y=[exp_total],
            marker_color="#F87171", width=0.3,
            text=[f"${exp_total:,.0f}"], textposition="outside",
        ))
        fig.add_trace(go.Bar(
            name="Net Income", x=["Financial Summary"], y=[net_income],
            marker_color="#34D399" if net_income >= 0 else "#F87171", width=0.3,
            text=[f"${net_income:,.0f}"], textposition="outside",
        ))
        fig.update_layout(**PLOTLY_LAYOUT, title="Revenue vs Expenses vs Net Income",
                          barmode="group", yaxis=dict(gridcolor="rgba(148,163,184,0.08)"))
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        # Balance Sheet donut
        bs_vals = [max(assets, 0), max(liab, 0), max(equity, 0)]
        bs_labels = ["Assets", "Liabilities", "Equity"]
        fig2 = go.Figure(go.Pie(
            labels=bs_labels, values=bs_vals,
            hole=0.55,
            marker_colors=["#6366F1", "#F87171", "#FBBF24"],
            textfont_size=11,
        ))
        fig2.update_layout(**PLOTLY_LAYOUT, title="Balance Sheet Composition")
        st.plotly_chart(fig2, use_container_width=True)

    # ── Charts row 2 ─────────────────────────────────────────────────────────
    c3, c4 = st.columns(2)

    with c3:
        # Expense breakdown
        exp_df = is_df[is_df["type"] == "Expense"].copy()
        exp_df = exp_df[exp_df["net"] > 0].sort_values("net", ascending=True)
        if not exp_df.empty:
            fig3 = go.Figure(go.Bar(
                x=exp_df["net"], y=exp_df["name"],
                orientation="h",
                marker=dict(
                    color=exp_df["net"],
                    colorscale=[[0, "#312E81"], [1, "#F87171"]],
                    showscale=False,
                ),
                text=[f"${v:,.0f}" for v in exp_df["net"]],
                textposition="outside",
            ))
            fig3.update_layout(**PLOTLY_LAYOUT, title="Expense Breakdown",
                               xaxis=dict(gridcolor="rgba(148,163,184,0.08)"), showlegend=False)
            st.plotly_chart(fig3, use_container_width=True)

    with c4:
        # Account type distribution
        acct_types = bs_df.groupby("type")["balance"].sum().reset_index()
        acct_types = acct_types[acct_types["balance"].abs() > 0]
        if not acct_types.empty:
            colors = {"Asset": "#6366F1", "Liability": "#F87171", "Equity": "#FBBF24"}
            fig4 = go.Figure(go.Bar(
                x=acct_types["type"],
                y=acct_types["balance"].abs(),
                marker_color=[colors.get(t, "#94A3B8") for t in acct_types["type"]],
                text=[f"${v:,.0f}" for v in acct_types["balance"].abs()],
                textposition="outside",
            ))
            fig4.update_layout(**PLOTLY_LAYOUT, title="Balance by Account Category",
                               yaxis=dict(gridcolor="rgba(148,163,184,0.08)"), showlegend=False)
            st.plotly_chart(fig4, use_container_width=True)

    # ── Recent Entries ────────────────────────────────────────────────────────
    st.markdown('<div class="section-title"><span>◆</span> Recent Journal Entries</div>', unsafe_allow_html=True)
    if not je_df.empty:
        display = je_df.head(8)[["entry_number", "entry_date", "description", "total_debit", "status"]].copy()
        display.columns = ["Entry #", "Date", "Description", "Amount", "Status"]
        display["Amount"] = display["Amount"].map(lambda v: f"${v:,.2f}")
        st.dataframe(display, use_container_width=True, hide_index=True)
    else:
        st.info("No journal entries found for selected period.")