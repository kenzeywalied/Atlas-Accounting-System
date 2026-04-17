import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date
from utils.database import get_ledger, get_accounts
from utils.styles import page_header


def render():
    st.markdown(page_header("📒", "General Ledger", "View auto-posted ledger entries and running balances per account"), unsafe_allow_html=True)

    accounts_df = get_accounts(active_only=True)
    if accounts_df.empty:
        st.warning("No accounts found.")
        return

    # Filters
    today = date.today()
    fc1, fc2, fc3, fc4 = st.columns([3, 2, 2, 1])
    acct_options = ["All Accounts"] + [f"{r.code} – {r.name}" for r in accounts_df.itertuples()]
    sel_acct   = fc1.selectbox("Account", acct_options, key="ledger_acct")
    start_date = fc2.date_input("From", value=date(today.year, 1, 1), key="ledger_start")
    end_date   = fc3.date_input("To",   value=today, key="ledger_end")

    acct_id = None
    if sel_acct != "All Accounts":
        code = sel_acct.split("–")[0].strip()
        match = accounts_df[accounts_df["code"] == code]
        if not match.empty:
            acct_id = int(match.iloc[0]["id"])

    df = get_ledger(account_id=acct_id, start_date=start_date, end_date=end_date)

    if df.empty:
        st.info("No ledger entries found for the selected filters.")
        return

    # If showing all accounts, group by account
    if acct_id is None:
        _render_all_accounts(df)
    else:
        _render_single_account(df, sel_acct)


def _render_all_accounts(df):
    st.markdown('<div class="section-title"><span>◆</span> Ledger Summary by Account</div>', unsafe_allow_html=True)

    summary = df.groupby(["code","account_name","account_type","normal_side"]).agg(
        total_debit=("debit","sum"),
        total_credit=("credit","sum"),
        transactions=("debit","count"),
    ).reset_index()

    summary["net_balance"] = summary.apply(
        lambda r: r["total_debit"] - r["total_credit"] if r["normal_side"] == "Dr"
                  else r["total_credit"] - r["total_debit"], axis=1)

    # Summary metrics
    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("Active Accounts", len(summary))
    mc2.metric("Total Debits",  f"${summary['total_debit'].sum():,.2f}")
    mc3.metric("Total Credits", f"${summary['total_credit'].sum():,.2f}")

    st.markdown("<br>", unsafe_allow_html=True)

    display = summary[["code","account_name","account_type","total_debit","total_credit","net_balance","transactions"]].copy()
    display.columns = ["Code","Account Name","Type","Total Dr","Total Cr","Net Balance","Txns"]
    display["Total Dr"]    = display["Total Dr"].map(lambda v: f"${v:,.2f}")
    display["Total Cr"]    = display["Total Cr"].map(lambda v: f"${v:,.2f}")
    display["Net Balance"] = display["Net Balance"].map(lambda v: f"${v:,.2f}")

    st.dataframe(display, use_container_width=True, hide_index=True)


def _render_single_account(df, acct_label):
    acct_type    = df.iloc[0]["account_type"]
    normal_side  = df.iloc[0]["normal_side"]

    # Compute running balance
    rows = []
    running_balance = 0.0
    for _, row in df.iterrows():
        if normal_side == "Dr":
            running_balance += row["debit"] - row["credit"]
        else:
            running_balance += row["credit"] - row["debit"]
        rows.append({
            "Date":        row["entry_date"],
            "Entry #":     row["entry_number"],
            "Description": row["entry_desc"],
            "Debit":       row["debit"],
            "Credit":      row["credit"],
            "Balance":     running_balance,
        })

    ledger_df = pd.DataFrame(rows)

    # Metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Transactions",  len(ledger_df))
    m2.metric("Total Debits",  f"${ledger_df['Debit'].sum():,.2f}")
    m3.metric("Total Credits", f"${ledger_df['Credit'].sum():,.2f}")
    m4.metric("Closing Balance", f"${ledger_df['Balance'].iloc[-1]:,.2f}")

    st.markdown("<br>", unsafe_allow_html=True)

    # Ledger table
    st.markdown('<div class="section-title"><span>◆</span> Ledger Transactions</div>', unsafe_allow_html=True)

    display = ledger_df.copy()
    display["Debit"]  = display["Debit"].map(lambda v: f"${v:,.2f}" if v > 0 else "")
    display["Credit"] = display["Credit"].map(lambda v: f"${v:,.2f}" if v > 0 else "")
    display["Balance"] = display["Balance"].map(lambda v: f"${v:,.2f}")

    st.dataframe(display, use_container_width=True, hide_index=True)

    # Balance chart
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-title"><span>◆</span> Balance Trend</div>', unsafe_allow_html=True)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=ledger_df["Date"],
        y=ledger_df["Balance"],
        mode="lines+markers",
        name="Running Balance",
        line=dict(color="#6366F1", width=2.5),
        marker=dict(size=6, color="#6366F1", symbol="circle"),
        fill="tozeroy",
        fillcolor="rgba(99,102,241,0.08)",
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Plus Jakarta Sans", color="#94A3B8"),
        margin=dict(l=10, r=10, t=20, b=10),
        xaxis=dict(gridcolor="rgba(148,163,184,0.08)"),
        yaxis=dict(gridcolor="rgba(148,163,184,0.08)"),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Dr/Cr bar chart
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(name="Debits",  x=ledger_df["Date"], y=ledger_df["Debit"].map(lambda v: float(v.replace("$","").replace(",","")) if v else 0),  marker_color="#6366F1"))
    fig2.add_trace(go.Bar(name="Credits", x=ledger_df["Date"], y=ledger_df["Credit"].map(lambda v: float(v.replace("$","").replace(",","")) if v else 0), marker_color="#F87171"))
    fig2.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Plus Jakarta Sans", color="#94A3B8"),
        margin=dict(l=10, r=10, t=20, b=10),
        barmode="group",
        xaxis=dict(gridcolor="rgba(148,163,184,0.08)"),
        yaxis=dict(gridcolor="rgba(148,163,184,0.08)"),
    )
    st.plotly_chart(fig2, use_container_width=True)