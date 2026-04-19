import streamlit as st
import pandas as pd
from datetime import date
from utils.database import (get_accounts, add_journal_entry, get_journal_entries,
                             get_entry_lines, void_journal_entry, next_entry_number)
from utils.styles import page_header, fmt_currency
from utils.export_utils import export_journal_entries


def render():
    st.markdown(page_header("📝", "Journal Entries", "Record double-entry transactions with automatic validation"), unsafe_allow_html=True)

    tabs = st.tabs(["📋  Entry Register", "➕  New Entry", "🔍  Entry Detail"])

    # ── Tab 1: Register ───────────────────────────────────────────────────────
    with tabs[0]:
        fc1, fc2, fc3, fc4 = st.columns([2, 2, 2, 1])
        today = date.today()
        start = fc1.date_input("From Date", value=date(today.year, 1, 1), key="je_list_start")
        end   = fc2.date_input("To Date",   value=date(2028, 12, 31), key="je_list_end")
        fstatus = fc3.selectbox("Status", ["All", "Posted", "Draft", "Void"], key="je_list_status")
        fc4.markdown("<div style='height:1.8rem'></div>", unsafe_allow_html=True)

        df = get_journal_entries(
            start_date=start, end_date=end,
            status=None if fstatus == "All" else fstatus
        )

        if not df.empty:
            # Summary row
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Entries", len(df))
            m2.metric("Total Debits",  f"${df['total_debit'].sum():,.2f}")
            m3.metric("Total Credits", f"${df['total_credit'].sum():,.2f}")
            balanced = abs(df['total_debit'].sum() - df['total_credit'].sum()) < 0.01
            m4.metric("Balanced", "Yes" if balanced else "No")

            st.markdown("<br>", unsafe_allow_html=True)

            # Export button
            exp_col1, exp_col2 = st.columns([6, 1])
            with exp_col2:
                xlsx_bytes = export_journal_entries(df, get_entry_lines)
                st.download_button("⬇ Excel", xlsx_bytes,
                                   file_name="journal_entries.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                   use_container_width=True)

            # Color-code status
            display = df[["entry_number","entry_date","description","reference","total_debit","total_credit","status"]].copy()
            display.columns = ["Entry #","Date","Description","Reference","Debit","Credit","Status"]
            display["Debit"]  = display["Debit"].map(lambda v: f"${v:,.2f}")
            display["Credit"] = display["Credit"].map(lambda v: f"${v:,.2f}")

            st.dataframe(display, use_container_width=True, hide_index=True,
                         column_config={
                             "Entry #": st.column_config.TextColumn(width="small"),
                             "Date":    st.column_config.TextColumn(width="small"),
                             "Status":  st.column_config.TextColumn(width="small"),
                         })
        else:
            st.info("No journal entries found for the selected filters.")

    # ── Tab 2: New Entry ──────────────────────────────────────────────────────
    with tabs[1]:
        accounts_df = get_accounts(active_only=True)
        if accounts_df.empty:
            st.warning("Please create accounts before adding journal entries.")
            return

        acct_map = {f"{r.code} – {r.name}": r.id for r in accounts_df.itertuples()}
        acct_options = list(acct_map.keys())

        st.markdown('<div class="section-title"><span>◆</span> Entry Header</div>', unsafe_allow_html=True)
        hc1, hc2, hc3 = st.columns([2, 2, 2])
        entry_date   = hc1.date_input("Date *", value=date.today(), key="je_date")
        reference    = hc2.text_input("Reference", placeholder="e.g. INV-001")
        description  = hc3.text_input("Description *", placeholder="Transaction description")
        status_opt   = st.selectbox("Status", ["Posted", "Draft"], key="je_status")

        st.markdown('<div class="section-title"><span>◆</span> Line Items</div>', unsafe_allow_html=True)

        # Session state for lines
        if "je_lines" not in st.session_state:
            st.session_state.je_lines = [
                {"account": acct_options[0], "debit": 0.0, "credit": 0.0, "desc": ""},
                {"account": acct_options[0], "debit": 0.0, "credit": 0.0, "desc": ""},
            ]

        col_add, col_clear = st.columns([1, 1])
        if col_add.button("➕  Add Line"):
            st.session_state.je_lines.append({"account": acct_options[0], "debit": 0.0, "credit": 0.0, "desc": ""})
        if col_clear.button("🗑  Clear All Lines"):
            st.session_state.je_lines = [
                {"account": acct_options[0], "debit": 0.0, "credit": 0.0, "desc": ""},
                {"account": acct_options[0], "debit": 0.0, "credit": 0.0, "desc": ""},
            ]

        # Header row
        header_cols = st.columns([3, 2, 2, 3, 0.7])
        for h, c in zip(["Account", "Debit", "Credit", "Description", ""], header_cols):
            c.markdown(f'<div style="font-size:0.7rem;font-weight:700;color:#64748B;text-transform:uppercase;letter-spacing:0.06em;padding:0.2rem 0">{h}</div>', unsafe_allow_html=True)

        lines_to_remove = []
        for i, line in enumerate(st.session_state.je_lines):
            lc = st.columns([3, 2, 2, 3, 0.7])
            line["account"] = lc[0].selectbox("Account", acct_options,
                                               index=acct_options.index(line["account"]) if line["account"] in acct_options else 0,
                                               key=f"je_acct_{i}", label_visibility="collapsed")
            line["debit"]   = lc[1].number_input("Dr", min_value=0.0, value=float(line["debit"]),
                                                  step=100.0, format="%.2f", key=f"je_dr_{i}",
                                                  label_visibility="collapsed")
            line["credit"]  = lc[2].number_input("Cr", min_value=0.0, value=float(line["credit"]),
                                                  step=100.0, format="%.2f", key=f"je_cr_{i}",
                                                  label_visibility="collapsed")
            line["desc"]    = lc[3].text_input("Desc", value=line["desc"],
                                               placeholder="Line description", key=f"je_ldesc_{i}",
                                               label_visibility="collapsed")
            if lc[4].button("✕", key=f"je_rm_{i}") and len(st.session_state.je_lines) > 1:
                lines_to_remove.append(i)

        for idx in reversed(lines_to_remove):
            st.session_state.je_lines.pop(idx) 
            st.rerun()

        # Running totals
        total_dr = sum(l["debit"] for l in st.session_state.je_lines)
        total_cr = sum(l["credit"] for l in st.session_state.je_lines)
        diff     = total_dr - total_cr

        st.markdown("<br>", unsafe_allow_html=True)
        tc1, tc2, tc3 = st.columns(3)
        tc1.metric("Total Debits",  f"${total_dr:,.2f}")
        tc2.metric("Total Credits", f"${total_cr:,.2f}")
        tc3.metric("Difference",    f"${abs(diff):,.2f}", delta="Balanced" if abs(diff) < 0.01 else f"Out by ${abs(diff):,.2f} ")

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Post Journal Entry", use_container_width=True, type="primary"):
            if not description.strip():
                st.error("Description is required.")
            elif abs(diff) > 0.005:
                st.error(f"Cannot post: Debits ({total_dr:,.2f}) ≠ Credits ({total_cr:,.2f}). Difference: {abs(diff):,.2f}")
            else:
                lines_payload = []
                for l in st.session_state.je_lines:
                    lines_payload.append({
                        "account_id": acct_map[l["account"]],
                        "debit": l["debit"],
                        "credit": l["credit"],
                        "description": l["desc"],
                    })
                ok, msg = add_journal_entry(entry_date, description, reference, lines_payload, status_opt)
                if ok:
                    st.success(msg)
                    st.session_state.je_lines = [
                        {"account": acct_options[0], "debit": 0.0, "credit": 0.0, "desc": ""},
                        {"account": acct_options[0], "debit": 0.0, "credit": 0.0, "desc": ""},
                    ]
                    st.rerun()
                else:
                    st.error(msg)

    # ── Tab 3: Entry Detail ───────────────────────────────────────────────────
    with tabs[2]:
        je_df = get_journal_entries()
        if je_df.empty:
            st.info("No journal entries available.")
            return

        options = {f"{r.entry_number}  |  {r.entry_date}  |  {r.description}": r.id
                   for r in je_df.itertuples()}
        sel = st.selectbox("Select Journal Entry", list(options.keys()), key="je_detail_sel")
        eid = options[sel]

        lines = get_entry_lines(eid)
        entry_info = je_df[je_df["id"] == eid].iloc[0]

        info_col1, info_col2, info_col3, info_col4 = st.columns(4)
        info_col1.metric("Entry #", entry_info.entry_number)
        info_col2.metric("Date",    entry_info.entry_date)
        info_col3.metric("Status",  entry_info.status)
        info_col4.metric("Total",   f"${entry_info.total_debit:,.2f}")

        st.markdown(f"**Description:** {entry_info.description}")
        if entry_info.get("reference"):
            st.markdown(f"**Reference:** {entry_info['reference']}")

        st.markdown("<br>", unsafe_allow_html=True)

        if not lines.empty:
            display = lines[["account_code","account_name","account_type","debit","credit","description"]].copy()
            display.columns = ["Code","Account","Type","Debit","Credit","Line Desc"]
            display["Debit"]  = display["Debit"].map(lambda v: f"${v:,.2f}" if v > 0 else "")
            display["Credit"] = display["Credit"].map(lambda v: f"${v:,.2f}" if v > 0 else "")
            st.dataframe(display, use_container_width=True, hide_index=True)

            # Totals
            tc1, tc2 = st.columns(2)
            tc1.metric("Total Debits",  f"${lines['debit'].sum():,.2f}")
            tc2.metric("Total Credits", f"${lines['credit'].sum():,.2f}")

        # Void option
        if entry_info.status == "Posted":
            st.markdown("<br>", unsafe_allow_html=True)
            with st.expander("Void this entry"):
                st.warning("Voiding removes this entry from all reports. This cannot be undone.")
                if st.button("Confirm Void Entry", key="void_btn"):
                    void_journal_entry(eid)
                    st.success("Entry voided.")
                    st.rerun()