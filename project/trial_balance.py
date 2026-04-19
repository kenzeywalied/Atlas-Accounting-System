import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.graph_objects as go
from datetime import date
from utils.database import get_trial_balance
from utils.styles import page_header, fmt_currency
from utils.export_utils import export_trial_balance


def render():
    st.markdown(page_header("⚖️", "Trial Balance", "Advanced trial balance with beginning balances, movements, and closing figures"), unsafe_allow_html=True)

    # Controls
    today = date.today()
    c1, c2, c3 = st.columns(3)
    as_of_date  = c1.date_input("As-of Date (Period End)", value=date(2028, 12, 31), key="tb_end")
    period_start = c2.date_input("Period Start (for movements)", value=date(today.year, 1, 1), key="tb_start")
    show_zero   = c3.checkbox("Show zero-balance accounts", value=False, key="tb_zero")

    show_type = st.multiselect(
        "Filter by Account Type",
        ["Asset","Liability","Equity","Revenue","Expense"],
        default=["Asset","Liability","Equity","Revenue","Expense"],
        key="tb_types"
    )

    df = get_trial_balance(
        start_date=period_start,
        end_date=as_of_date,
        period_start=period_start
    )

    # Filter
    if not show_zero:
        df = df[(df["end_bal_dr"] > 0) | (df["end_bal_cr"] > 0)]
    if show_type:
        df = df[df["type"].isin(show_type)]

    if df.empty:
        st.info("No data for selected filters.")
        return

    # Summary cards
    total_beg_dr = df["beg_bal_dr"].sum()
    total_beg_cr = df["beg_bal_cr"].sum()
    total_mv_dr  = df["mv_dr"].sum()
    total_mv_cr  = df["mv_cr"].sum()
    total_end_dr = df["end_bal_dr"].sum()
    total_end_cr = df["end_bal_cr"].sum()
    balanced = abs(total_end_dr - total_end_cr) < 0.01

    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("Beg Dr Balance", f"${total_beg_dr:,.2f}")
    mc2.metric("Period Debits",  f"${total_mv_dr:,.2f}")
    mc3.metric("Ending Dr",      f"${total_end_dr:,.2f}")
    mc4.metric("Balanced?", "✅ Yes" if balanced else "❌ No",
               delta=f"Diff: ${abs(total_end_dr - total_end_cr):,.2f}" if not balanced else None)

    st.markdown("<br>", unsafe_allow_html=True)

    # Export
    exp_col1, exp_col2, _ = st.columns([2, 2, 4])
    xlsx = export_trial_balance(df, f"Trial Balance — {period_start} to {as_of_date}")
    exp_col1.download_button("⬇ Export to Excel", xlsx,
                              file_name="trial_balance.xlsx",
                              mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                              use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Render trial balance table
    st.markdown('<div class="section-title"><span>◆</span> Trial Balance Detail</div>', unsafe_allow_html=True)

    def _num(v):
        if v == 0:
            return '<td class="num" style="color:#334155">—</td>'
        return f'<td class="num">{v:,.2f}</td>'

    TYPE_COLORS = {
        "Asset":     "#818CF8",
        "Liability": "#F87171",
        "Equity":    "#FBBF24",
        "Revenue":   "#34D399",
        "Expense":   "#FB923C",
    }

    rows_html = ""
    for acct_type in ["Asset","Liability","Equity","Revenue","Expense"]:
        grp = df[df["type"] == acct_type]
        if grp.empty:
            continue
        color = TYPE_COLORS.get(acct_type, "#94A3B8")
        rows_html += f"""
        <tr class="section-hd">
            <td colspan="2" style="color:{color};font-size:0.72rem;font-weight:800;text-transform:uppercase;letter-spacing:0.07em;padding:0.6rem 0.75rem">
                {acct_type}
            </td>
            <td class="num" style="color:{color}66">Beg Dr</td>
            <td class="num" style="color:{color}66">Beg Cr</td>
            <td class="num" style="color:{color}66">Mvt Dr</td>
            <td class="num" style="color:{color}66">Mvt Cr</td>
            <td class="num" style="color:{color}">End Dr</td>
            <td class="num" style="color:{color}">End Cr</td>
        </tr>
        """
        for _, row in grp.iterrows():
            rows_html += f"""
            <tr>
                <td style="color:#64748B;font-family:'JetBrains Mono',monospace;font-size:0.78rem;padding:0.45rem 0.75rem">{row['code']}</td>
                <td style="color:#CBD5E1;padding:0.45rem 0.75rem">{row['name']}</td>
                {_num(row['beg_bal_dr'])}
                {_num(row['beg_bal_cr'])}
                {_num(row['mv_dr'])}
                {_num(row['mv_cr'])}
                {_num(row['end_bal_dr'])}
                {_num(row['end_bal_cr'])}
            </tr>
            """

        # Subtotals per type
        rows_html += f"""
        <tr class="total-row">
            <td colspan="2" style="padding:0.5rem 0.75rem;color:{color};font-size:0.75rem;font-weight:700">
                Subtotal {acct_type}
            </td>
            <td class="num" style="color:{color};font-weight:700">{grp['beg_bal_dr'].sum():,.2f}</td>
            <td class="num" style="color:{color};font-weight:700">{grp['beg_bal_cr'].sum():,.2f}</td>
            <td class="num" style="color:{color};font-weight:700">{grp['mv_dr'].sum():,.2f}</td>
            <td class="num" style="color:{color};font-weight:700">{grp['mv_cr'].sum():,.2f}</td>
            <td class="num" style="color:{color};font-weight:700">{grp['end_bal_dr'].sum():,.2f}</td>
            <td class="num" style="color:{color};font-weight:700">{grp['end_bal_cr'].sum():,.2f}</td>
        </tr>
        <tr class="spacer"><td colspan="8"></td></tr>
        """

    # Grand totals
    grand_balanced_color = "#34D399" if balanced else "#F87171"
    rows_html += f"""
    <tr class="net-row">
        <td colspan="2" style="padding:0.6rem 0.75rem;font-size:0.85rem;font-weight:800">GRAND TOTAL</td>
        <td class="num">{total_beg_dr:,.2f}</td>
        <td class="num">{total_beg_cr:,.2f}</td>
        <td class="num">{total_mv_dr:,.2f}</td>
        <td class="num">{total_mv_cr:,.2f}</td>
        <td class="num" style="color:{grand_balanced_color}">{total_end_dr:,.2f}</td>
        <td class="num" style="color:{grand_balanced_color}">{total_end_cr:,.2f}</td>
    </tr>
    """

    # Estimate row count to set iframe height dynamically
    num_rows = len(df) + (len(df["type"].unique()) * 3)   # data + subtotal + spacer rows
    iframe_height = max(400, num_rows * 36 + 80)

    table_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
      * {{ box-sizing: border-box; margin: 0; padding: 0; }}
      body {{
        background: transparent;
        font-family: 'Plus Jakarta Sans', sans-serif;
        color: #CBD5E1;
      }}
      .wrap {{
        overflow-x: auto;
        border-radius: 12px;
        border: 1px solid rgba(148,163,184,0.12);
      }}
      table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 0.84rem;
        background: #1E293B;
      }}
      thead th {{
        background: #0F172A;
        color: #94A3B8;
        font-size: 0.68rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.07em;
        padding: 0.6rem 0.75rem;
        border-bottom: 1px solid rgba(148,163,184,0.15);
        text-align: right;
        white-space: nowrap;
      }}
      thead th:first-child, thead th:nth-child(2) {{ text-align: left; }}
      tbody tr {{ border-bottom: 1px solid rgba(148,163,184,0.06); }}
      tbody tr:hover td {{ background: rgba(99,102,241,0.05); }}
      td {{ padding: 0.42rem 0.75rem; }}
      .num {{
        text-align: right;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.8rem;
        white-space: nowrap;
      }}
      .section-hd td {{
        background: rgba(99,102,241,0.08);
        font-size: 0.72rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.07em;
        padding: 0.55rem 0.75rem;
      }}
      .total-row td {{
        background: rgba(148,163,184,0.06);
        font-weight: 700;
        border-top: 1px solid rgba(148,163,184,0.18);
        font-size: 0.78rem;
      }}
      .net-row td {{
        background: rgba(99,102,241,0.14);
        font-weight: 800;
        font-size: 0.88rem;
        border-top: 2px solid #6366F1;
        color: #A5B4FC;
        padding: 0.62rem 0.75rem;
      }}
      .spacer td {{ background: transparent !important; border: none !important; height: 0.5rem; }}
    </style>
    </head>
    <body>
    <div class="wrap">
    <table>
      <thead>
        <tr>
          <th style="text-align:left;width:90px">Code</th>
          <th style="text-align:left">Account Name</th>
          <th>Beg. Dr</th>
          <th>Beg. Cr</th>
          <th>Period Dr</th>
          <th>Period Cr</th>
          <th>End Dr</th>
          <th>End Cr</th>
        </tr>
      </thead>
      <tbody>
        {rows_html}
      </tbody>
    </table>
    </div>
    </body>
    </html>
    """
    components.html(table_html, height=iframe_height, scrolling=True)

    # Chart: Ending balances
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-title"><span>◆</span> Ending Balance Distribution</div>', unsafe_allow_html=True)

    chart_df = df[(df["end_bal_dr"] > 0) | (df["end_bal_cr"] > 0)].copy()
    chart_df["ending"] = chart_df["end_bal_dr"] - chart_df["end_bal_cr"]
    chart_df = chart_df.sort_values("ending", key=abs, ascending=False).head(15)

    colors_map = {
        "Asset":     "#6366F1",
        "Liability": "#F87171",
        "Equity":    "#FBBF24",
        "Revenue":   "#34D399",
        "Expense":   "#FB923C",
    }

    fig = go.Figure(go.Bar(
        x=chart_df["name"],
        y=chart_df["ending"].abs(),
        marker_color=[colors_map.get(t, "#94A3B8") for t in chart_df["type"]],
        text=[f"${v:,.0f}" for v in chart_df["ending"].abs()],
        textposition="outside",
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Plus Jakarta Sans", color="#94A3B8", size=10),
        margin=dict(l=10, r=10, t=20, b=80),
        xaxis=dict(gridcolor="rgba(148,163,184,0.06)", tickangle=-35),
        yaxis=dict(gridcolor="rgba(148,163,184,0.08)"),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)