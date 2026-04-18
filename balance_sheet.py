import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date
from utils.database import get_balance_sheet, get_income_statement
from utils.styles import page_header, fmt_currency
from utils.export_utils import export_balance_sheet


def render():
    st.markdown(page_header("🏦", "Balance Sheet", "Assets, liabilities, and equity position at a given date"), unsafe_allow_html=True)

    today = date.today()
    c1, _ = st.columns([2, 4])
    as_of = c1.date_input("As-of Date", value=today, key="bs_asof")

    df = get_balance_sheet(as_of)
    assets_df   = df[df["type"] == "Asset"].copy()
    liab_df     = df[df["type"] == "Liability"].copy()
    equity_df   = df[df["type"] == "Equity"].copy()

    total_assets   = assets_df["balance"].sum()
    total_liab     = liab_df["balance"].sum()
    total_equity   = equity_df["balance"].sum()
    balanced       = abs(total_assets - (total_liab + total_equity)) < 0.5

    curr_assets     = assets_df[assets_df["subtype"] == "Current Asset"]["balance"].sum()
    non_curr_assets = assets_df[assets_df["subtype"] != "Current Asset"]["balance"].sum()
    curr_liab       = liab_df[liab_df["subtype"] == "Current Liability"]["balance"].sum()

    # KPIs
    mk1, mk2, mk3, mk4, mk5 = st.columns(5)
    mk1.metric("Total Assets",    f"${total_assets:,.2f}")
    mk2.metric("Total Liabilities", f"${total_liab:,.2f}")
    mk3.metric("Total Equity",    f"${total_equity:,.2f}")
    mk4.metric("Current Ratio",   f"{curr_assets/curr_liab:.2f}x" if curr_liab else "N/A")
    mk5.metric("Balanced?", "✅" if balanced else "❌",
               delta=f"Diff: ${abs(total_assets - total_liab - total_equity):,.2f}" if not balanced else None)

    st.markdown("<br>", unsafe_allow_html=True)

    # Export
    exp_col, _ = st.columns([2, 6])
    xlsx = export_balance_sheet(assets_df, liab_df, equity_df, as_of)
    exp_col.download_button("⬇ Export to Excel", xlsx,
                             file_name="balance_sheet.xlsx",
                             mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             use_container_width=True)

    # Layout: statement left, charts right
    stmt_col, chart_col = st.columns([1, 1])

    # ── Formal Statement ──────────────────────────────────────────────────────
    with stmt_col:
        st.markdown('<div class="section-title"><span>◆</span> Formal Statement</div>', unsafe_allow_html=True)

        def render_section(section_df, title, color, subtypes_order=None):
            rows = f'<tr class="section-hd"><td colspan="2" style="color:{color}">{title}</td><td></td></tr>'
            if subtypes_order:
                unique_subs = [s for s in subtypes_order if s in section_df["subtype"].values]
                remainder   = [s for s in section_df["subtype"].unique() if s not in subtypes_order]
                ordered = unique_subs + remainder
            else:
                ordered = section_df["subtype"].unique()

            for sub in ordered:
                sg = section_df[section_df["subtype"] == sub]
                if sg.empty:
                    continue
                rows += f'<tr><td colspan="3" style="padding:0.25rem 0.75rem 0.1rem;color:#94A3B8;font-size:0.68rem;font-weight:700;text-transform:uppercase;letter-spacing:0.05em">{sub}</td></tr>'
                for _, r in sg.iterrows():
                    bal = r["balance"]
                    rows += f'''<tr>
                        <td style="color:#64748B;font-family:JetBrains Mono,monospace;font-size:0.77rem;padding:0.35rem 0.75rem">{r["code"]}</td>
                        <td style="color:#CBD5E1;padding:0.35rem 0.75rem">{r["name"]}</td>
                        <td class="num" style="padding:0.35rem 0.75rem">{"("+f"{abs(bal):,.2f}"+")" if bal < 0 else f"{bal:,.2f}"}</td>
                    </tr>'''
            total = section_df["balance"].sum()
            rows += f'<tr class="total-row"><td colspan="2" style="padding:0.5rem 0.75rem;color:{color};font-weight:700">Total {title}</td><td class="num" style="color:{color};font-weight:700;padding:0.5rem 0.75rem">{total:,.2f}</td></tr>'
            rows += '<tr><td colspan="3" style="height:0.5rem;background:transparent;border:none"></td></tr>'
            return rows, total

        asset_rows, _  = render_section(assets_df, "ASSETS", "#6366F1",
                                        ["Current Asset","Non-Current Asset","Fixed Asset","Intangible Asset"])
        liab_rows, _   = render_section(liab_df, "LIABILITIES", "#F87171",
                                        ["Current Liability","Long-Term Liability"])
        equity_rows, _ = render_section(equity_df, "EQUITY", "#FBBF24",
                                        ["Paid-In Capital","Additional Paid-In Capital","Retained Earnings"])

        tl_color = "#34D399" if balanced else "#F87171"
        total_row = f'''<tr class="net-row">
            <td colspan="2" style="padding:0.65rem 0.75rem">TOTAL LIABILITIES & EQUITY</td>
            <td class="num" style="color:{tl_color};padding:0.65rem 0.75rem;font-size:1rem">{total_liab + total_equity:,.2f}</td>
        </tr>'''

        html = f"""
        <div style="border-radius:12px;border:1px solid rgba(148,163,184,0.12);overflow:hidden">
        <table class="stmt-table">
            <thead>
                <tr>
                    <th style="text-align:left;width:70px">Code</th>
                    <th style="text-align:left">Account</th>
                    <th style="width:130px">Balance</th>
                </tr>
            </thead>
            <tbody>
                {asset_rows}
                {liab_rows}
                {equity_rows}
                {total_row}
            </tbody>
        </table>
        </div>
        """
        st.markdown(html, unsafe_allow_html=True)

    # ── Charts ────────────────────────────────────────────────────────────────
    with chart_col:
        # Asset composition donut
        st.markdown('<div class="section-title"><span>◆</span> Asset Composition</div>', unsafe_allow_html=True)
        asset_sub = assets_df[assets_df["balance"] > 0].groupby("subtype")["balance"].sum()
        fig1 = go.Figure(go.Pie(
            labels=asset_sub.index, values=asset_sub.values,
            hole=0.55,
            marker_colors=["#6366F1","#818CF8","#A5B4FC","#C7D2FE"],
            textfont_size=10,
        ))
        fig1.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Plus Jakarta Sans", color="#94A3B8"),
            margin=dict(l=10, r=10, t=10, b=10),
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=9)),
        )
        st.plotly_chart(fig1, use_container_width=True)

        # Leverage bar
        st.markdown('<div class="section-title"><span>◆</span> Capital Structure</div>', unsafe_allow_html=True)
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(name="Liabilities", x=["Capital Structure"], y=[total_liab],
                              marker_color="#F87171", width=0.4, text=[f"${total_liab:,.0f}"], textposition="inside"))
        fig2.add_trace(go.Bar(name="Equity", x=["Capital Structure"], y=[total_equity],
                              marker_color="#FBBF24", width=0.4, text=[f"${total_equity:,.0f}"], textposition="inside"))
        fig2.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Plus Jakarta Sans", color="#94A3B8"),
            barmode="stack",
            margin=dict(l=10, r=10, t=10, b=10),
            yaxis=dict(gridcolor="rgba(148,163,184,0.08)"),
            legend=dict(bgcolor="rgba(0,0,0,0)"),
        )
        st.plotly_chart(fig2, use_container_width=True)

        # Financial ratios
        st.markdown('<div class="section-title"><span>◆</span> Key Financial Ratios</div>', unsafe_allow_html=True)

        non_curr_assets = assets_df[assets_df["subtype"].isin(["Non-Current Asset","Fixed Asset","Intangible Asset"])]["balance"].sum()
        long_term_liab  = liab_df[liab_df["subtype"] == "Long-Term Liability"]["balance"].sum()
        working_cap     = curr_assets - curr_liab
        debt_to_equity  = total_liab / total_equity if total_equity else 0
        asset_turnover  = total_assets / total_equity if total_equity else 0

        ratios = [
            ("Current Ratio",       f"{curr_assets/curr_liab:.2f}x"    if curr_liab else "N/A",     "Current Assets ÷ Current Liabilities"),
            ("Debt-to-Equity",      f"{debt_to_equity:.2f}x",           "Total Liabilities ÷ Equity"),
            ("Working Capital",     f"${working_cap:,.0f}",              "Current Assets − Current Liabilities"),
            ("Equity Multiplier",   f"{asset_turnover:.2f}x",           "Total Assets ÷ Equity"),
        ]

        for label, value, desc in ratios:
            st.markdown(f"""
            <div style="background:#0F172A;border:1px solid rgba(148,163,184,0.1);border-radius:8px;padding:0.6rem 0.85rem;margin-bottom:0.5rem;display:flex;justify-content:space-between;align-items:center">
                <div>
                    <div style="font-size:0.75rem;font-weight:700;color:#94A3B8">{label}</div>
                    <div style="font-size:0.65rem;color:#475569;margin-top:1px">{desc}</div>
                </div>
                <div style="font-family:'JetBrains Mono',monospace;font-size:1rem;font-weight:800;color:#818CF8">{value}</div>
            </div>
            """, unsafe_allow_html=True)