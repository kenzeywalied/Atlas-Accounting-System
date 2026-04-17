import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date
from utils.database import get_income_statement
from utils.styles import page_header, fmt_currency
from utils.export_utils import export_income_statement


def render():
    st.markdown(page_header("📈", "Income Statement", "Profit & Loss statement with revenue, expenses, and net income"), unsafe_allow_html=True)

    today = date.today()
    c1, c2 = st.columns(2)
    start = c1.date_input("Period Start", value=date(today.year, 1, 1), key="is_start")
    end   = c2.date_input("Period End",   value=today, key="is_end")

    df = get_income_statement(start, end)

    rev_df = df[df["type"] == "Revenue"].copy()
    exp_df = df[df["type"] == "Expense"].copy()

    total_revenue = rev_df["net"].sum()
    total_expense = exp_df["net"].sum()
    gross_profit  = rev_df["net"].sum() - exp_df[exp_df["subtype"] == "COGS"]["net"].sum()
    net_income    = total_revenue - total_expense
    net_margin    = (net_income / total_revenue * 100) if total_revenue != 0 else 0

    # KPIs
    mk1, mk2, mk3, mk4 = st.columns(4)
    mk1.metric("Total Revenue",  f"${total_revenue:,.2f}")
    mk2.metric("Gross Profit",   f"${gross_profit:,.2f}",  delta=f"{gross_profit/total_revenue*100:.1f}%" if total_revenue else None)
    mk3.metric("Total Expenses", f"${total_expense:,.2f}")
    mk4.metric("Net Income",     f"${net_income:,.2f}",    delta=f"{net_margin:.1f}% margin")

    st.markdown("<br>", unsafe_allow_html=True)

    # Export
    exp_col1, _ = st.columns([2, 6])
    xlsx = export_income_statement(rev_df, exp_df, start, end)
    exp_col1.download_button("⬇ Export to Excel", xlsx,
                              file_name="income_statement.xlsx",
                              mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                              use_container_width=True)

    # Charts + Statement side by side
    chart_col, stmt_col = st.columns([1, 1])

    with chart_col:
        # Waterfall chart
        st.markdown('<div class="section-title"><span>◆</span> Profit Waterfall</div>', unsafe_allow_html=True)

        measure = ["absolute"]
        x_labels = ["Revenue"]
        y_vals = [total_revenue]
        text_vals = [f"${total_revenue:,.0f}"]

        for _, row in exp_df[exp_df["net"] > 0].iterrows():
            measure.append("relative")
            x_labels.append(row["name"][:22])
            y_vals.append(-row["net"])
            text_vals.append(f"-${row['net']:,.0f}")

        measure.append("total")
        x_labels.append("Net Income")
        y_vals.append(0)
        text_vals.append(f"${net_income:,.0f}")

        fig = go.Figure(go.Waterfall(
            name="P&L",
            orientation="v",
            measure=measure,
            x=x_labels,
            y=y_vals,
            text=text_vals,
            textposition="outside",
            connector=dict(line=dict(color="rgba(148,163,184,0.2)", width=1)),
            increasing=dict(marker_color="#34D399"),
            decreasing=dict(marker_color="#F87171"),
            totals=dict(marker_color="#6366F1"),
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Plus Jakarta Sans", color="#94A3B8", size=9),
            margin=dict(l=5, r=5, t=20, b=90),
            xaxis=dict(gridcolor="rgba(148,163,184,0.06)", tickangle=-40),
            yaxis=dict(gridcolor="rgba(148,163,184,0.06)"),
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

        # Revenue pie
        st.markdown('<div class="section-title"><span>◆</span> Revenue Mix</div>', unsafe_allow_html=True)
        rev_pie = rev_df[rev_df["net"] > 0]
        if not rev_pie.empty:
            fig2 = go.Figure(go.Pie(
                labels=rev_pie["name"], values=rev_pie["net"],
                hole=0.5, marker_colors=["#6366F1","#818CF8","#A5B4FC","#C7D2FE"],
            ))
            fig2.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Plus Jakarta Sans", color="#94A3B8"),
                margin=dict(l=5, r=5, t=10, b=5),
            )
            st.plotly_chart(fig2, use_container_width=True)

    with stmt_col:
        st.markdown('<div class="section-title"><span>◆</span> Formal Statement</div>', unsafe_allow_html=True)

        # Formal IS table
        def section_rows(section_df, label, color):
            rows = f'<tr class="section-hd"><td colspan="2" style="color:{color}">{label}</td><td></td></tr>'
            for _, r in section_df.iterrows():
                rows += f'<tr><td style="color:#64748B;font-family:JetBrains Mono,monospace;font-size:0.77rem;padding:0.4rem 0.75rem">{r["code"]}</td><td style="color:#CBD5E1;padding:0.4rem 0.75rem">{r["name"]}</td><td class="num" style="padding:0.4rem 0.75rem">{r["net"]:,.2f}</td></tr>'
            return rows

        rev_rows = section_rows(rev_df[rev_df["net"] > 0], "REVENUE", "#34D399")
        rev_total_row = f'<tr class="total-row"><td colspan="2" style="padding:0.5rem 0.75rem;color:#34D399;font-weight:700">Total Revenue</td><td class="num" style="color:#34D399;font-weight:700;padding:0.5rem 0.75rem">{total_revenue:,.2f}</td></tr>'

        # Group expenses by subtype
        exp_rows = ""
        for sub in exp_df["subtype"].unique():
            sg = exp_df[exp_df["subtype"] == sub]
            if sg.empty:
                continue
            exp_rows += f'<tr><td colspan="3" style="padding:0.3rem 0.75rem 0.1rem;color:#94A3B8;font-size:0.68rem;font-weight:700;text-transform:uppercase;letter-spacing:0.05em">{sub}</td></tr>'
            for _, r in sg.iterrows():
                exp_rows += f'<tr><td style="color:#64748B;font-family:JetBrains Mono,monospace;font-size:0.77rem;padding:0.3rem 0.75rem">{r["code"]}</td><td style="color:#CBD5E1;padding:0.3rem 0.75rem">{r["name"]}</td><td class="num" style="padding:0.3rem 0.75rem">({r["net"]:,.2f})</td></tr>'
        exp_section_hd = f'<tr class="section-hd"><td colspan="2" style="color:#F87171">EXPENSES</td><td></td></tr>'
        exp_total_row  = f'<tr class="total-row"><td colspan="2" style="padding:0.5rem 0.75rem;color:#F87171;font-weight:700">Total Expenses</td><td class="num" style="color:#F87171;font-weight:700;padding:0.5rem 0.75rem">({total_expense:,.2f})</td></tr>'

        ni_color = "#34D399" if net_income >= 0 else "#F87171"
        net_row = f'<tr class="net-row"><td colspan="2" style="padding:0.65rem 0.75rem">NET INCOME / (LOSS)</td><td class="num" style="color:{ni_color};padding:0.65rem 0.75rem;font-size:1rem">{net_income:,.2f}</td></tr>'
        margin_row = f'<tr><td colspan="2" style="color:#64748B;font-size:0.75rem;padding:0.3rem 0.75rem">Net Margin</td><td class="num" style="color:#64748B;font-size:0.75rem;padding:0.3rem 0.75rem">{net_margin:.1f}%</td></tr>'

        html = f"""
        <div style="border-radius:12px;border:1px solid rgba(148,163,184,0.12);overflow:hidden">
        <table class="stmt-table">
            <thead>
                <tr>
                    <th style="text-align:left;width:70px">Code</th>
                    <th style="text-align:left">Account</th>
                    <th style="width:120px">Amount</th>
                </tr>
            </thead>
            <tbody>
                {rev_rows}{rev_total_row}
                <tr><td colspan="3" style="height:0.4rem;background:transparent;border:none"></td></tr>
                {exp_section_hd}{exp_rows}{exp_total_row}
                <tr><td colspan="3" style="height:0.4rem;background:transparent;border:none"></td></tr>
                {net_row}{margin_row}
            </tbody>
        </table>
        </div>
        """
        st.markdown(html, unsafe_allow_html=True)

        # Expense breakdown bar
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-title"><span>◆</span> Expense Breakdown</div>', unsafe_allow_html=True)
        exp_chart = exp_df[exp_df["net"] > 0].sort_values("net", ascending=True)
        if not exp_chart.empty:
            fig3 = go.Figure(go.Bar(
                x=exp_chart["net"], y=exp_chart["name"],
                orientation="h",
                marker=dict(color=exp_chart["net"], colorscale=[[0,"#1e1b4b"],[1,"#F87171"]], showscale=False),
                text=[f"${v:,.0f}" for v in exp_chart["net"]],
                textposition="outside",
            ))
            fig3.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Plus Jakarta Sans", color="#94A3B8", size=9),
                margin=dict(l=5, r=60, t=10, b=5),
                xaxis=dict(gridcolor="rgba(148,163,184,0.06)"),
                showlegend=False,
            )
            st.plotly_chart(fig3, use_container_width=True)