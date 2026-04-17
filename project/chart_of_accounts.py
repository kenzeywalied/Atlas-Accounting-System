import streamlit as st
import pandas as pd
from utils.database import get_accounts, add_account, update_account
from utils.styles import page_header, fmt_currency

ACCOUNT_TYPES  = ["Asset", "Liability", "Equity", "Revenue", "Expense"]
NORMAL_SIDES   = ["Dr", "Cr"]
SUBTYPES = {
    "Asset":     ["Current Asset", "Non-Current Asset", "Fixed Asset", "Intangible Asset"],
    "Liability": ["Current Liability", "Long-Term Liability"],
    "Equity":    ["Paid-In Capital", "Retained Earnings", "Other Equity"],
    "Revenue":   ["Operating Revenue", "Other Income"],
    "Expense":   ["COGS", "Operating Expense", "Finance Expense", "Tax Expense"],
}
TYPE_COLORS = {
    "Asset":     ("#DBEAFE", "#1D4ED8"),
    "Liability": ("#FEE2E2", "#B91C1C"),
    "Equity":    ("#FEF3C7", "#92400E"),
    "Revenue":   ("#D1FAE5", "#065F46"),
    "Expense":   ("#FCE7F3", "#9D174D"),
}


def render():
    st.markdown(page_header("📋", "Chart of Accounts", "Manage your account structure and classifications"), unsafe_allow_html=True)

    tabs = st.tabs(["📂  Account List", "➕  Add Account", "✏️  Edit Account"])

    # ── Tab 1: Account List ───────────────────────────────────────────────────
    with tabs[0]:
        col1, col2, col3 = st.columns([2, 2, 2])
        with col1:
            filter_type = st.selectbox("Filter by Type", ["All"] + ACCOUNT_TYPES, key="coa_filter_type")
        with col2:
            filter_status = st.selectbox("Filter by Status", ["Active", "All", "Inactive"], key="coa_filter_status")
        with col3:
            search = st.text_input("🔍  Search", placeholder="Name or code...", key="coa_search")

        df = get_accounts(active_only=False)
        if filter_type != "All":
            df = df[df["type"] == filter_type]
        if filter_status == "Active":
            df = df[df["is_active"] == 1]
        elif filter_status == "Inactive":
            df = df[df["is_active"] == 0]
        if search:
            mask = (df["name"].str.contains(search, case=False, na=False) |
                    df["code"].str.contains(search, case=False, na=False))
            df = df[mask]

        # Summary stats
        all_df = get_accounts(active_only=False)
        s_col = st.columns(5)
        for i, t in enumerate(ACCOUNT_TYPES):
            cnt = len(all_df[all_df["type"] == t])
            bg, fg = TYPE_COLORS[t]
            s_col[i].markdown(
                f'<div style="background:{bg};border-radius:10px;padding:0.6rem 0.8rem;text-align:center">'
                f'<div style="font-size:1.3rem;font-weight:800;color:{fg}">{cnt}</div>'
                f'<div style="font-size:0.68rem;font-weight:700;color:{fg};text-transform:uppercase;letter-spacing:0.05em">{t}</div></div>',
                unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        if df.empty:
            st.info("No accounts found with current filters.")
        else:
            # Render grouped
            for acct_type in ACCOUNT_TYPES:
                grp = df[df["type"] == acct_type]
                if grp.empty:
                    continue
                bg, fg = TYPE_COLORS[acct_type]
                st.markdown(
                    f'<div style="background:{bg}22;border-left:3px solid {fg};border-radius:6px;padding:0.4rem 0.75rem;margin:0.75rem 0 0.4rem;font-size:0.75rem;font-weight:700;color:{fg};text-transform:uppercase;letter-spacing:0.07em">{acct_type} ({len(grp)})</div>',
                    unsafe_allow_html=True)

                display = grp[["code", "name", "subtype", "normal_side", "is_active"]].copy()
                display["is_active"] = display["is_active"].map({1: "Active", 0: "Inactive"})
                display.columns = ["Code", "Account Name", "Sub-Type", "Normal Side", "Status"]
                st.dataframe(display, use_container_width=True, hide_index=True)

    # ── Tab 2: Add Account ────────────────────────────────────────────────────
    with tabs[1]:
        st.markdown('<div class="section-title"><span>◆</span> New Account</div>', unsafe_allow_html=True)
        with st.form("add_account_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            code = c1.text_input("Account Code *", placeholder="e.g. 1050")
            name = c2.text_input("Account Name *", placeholder="e.g. Bank Account")

            c3, c4, c5 = st.columns(3)
            acct_type   = c3.selectbox("Account Type *", ACCOUNT_TYPES)
            subtype     = c4.selectbox("Sub-Type", SUBTYPES.get(acct_type, [""]))
            normal_side = c5.selectbox("Normal Side *", NORMAL_SIDES,
                                       index=0 if acct_type in ["Asset","Expense"] else 1)
            description = st.text_area("Description", placeholder="Optional description", height=80)

            submitted = st.form_submit_button("Create Account", use_container_width=True)
            if submitted:
                if not code or not name:
                    st.error("Code and Name are required.")
                else:
                    ok, msg = add_account(code.strip(), name.strip(), acct_type, subtype, normal_side, description)
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)

    # ── Tab 3: Edit Account ───────────────────────────────────────────────────
    with tabs[2]:
        st.markdown('<div class="section-title"><span>◆</span> Edit Existing Account</div>', unsafe_allow_html=True)
        all_accts = get_accounts(active_only=False)
        if all_accts.empty:
            st.info("No accounts to edit.")
            return

        options = {f"{r.code} – {r.name}": r for r in all_accts.itertuples()}
        selected_label = st.selectbox("Select Account", list(options.keys()))
        acct = options[selected_label]

        with st.form("edit_account_form"):
            c1, c2 = st.columns(2)
            new_code = c1.text_input("Code", value=acct.code)
            new_name = c2.text_input("Name", value=acct.name)

            c3, c4, c5 = st.columns(3)
            new_type    = c3.selectbox("Type", ACCOUNT_TYPES, index=ACCOUNT_TYPES.index(acct.type))
            subs        = SUBTYPES.get(new_type, [""])
            idx         = subs.index(acct.subtype) if acct.subtype in subs else 0
            new_subtype = c4.selectbox("Sub-Type", subs, index=idx)
            new_ns      = c5.selectbox("Normal Side", NORMAL_SIDES,
                                       index=NORMAL_SIDES.index(acct.normal_side))
            new_desc    = st.text_area("Description", value=acct.description or "", height=80)
            new_active  = st.checkbox("Active", value=bool(acct.is_active))

            if st.form_submit_button("Save Changes", use_container_width=True):
                ok, msg = update_account(acct.id, new_code, new_name, new_type, new_subtype, new_ns, new_desc, int(new_active))
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)