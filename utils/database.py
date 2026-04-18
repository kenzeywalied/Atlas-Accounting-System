import sqlite3
import pandas as pd
from datetime import datetime, date
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "accounting.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.executescript("""
        CREATE TABLE IF NOT EXISTS accounts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            code        TEXT    NOT NULL UNIQUE,
            name        TEXT    NOT NULL,
            type        TEXT    NOT NULL,   -- Asset, Liability, Equity, Revenue, Expense
            subtype     TEXT,
            normal_side TEXT    NOT NULL,   -- Dr or Cr
            is_active   INTEGER DEFAULT 1,
            description TEXT,
            created_at  TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS journal_entries (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_number TEXT    NOT NULL UNIQUE,
            entry_date   TEXT    NOT NULL,
            description  TEXT    NOT NULL,
            reference    TEXT,
            status       TEXT    DEFAULT 'Posted',  -- Draft, Posted, Void
            created_by   TEXT    DEFAULT 'System',
            created_at   TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS journal_lines (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_id    INTEGER NOT NULL REFERENCES journal_entries(id) ON DELETE CASCADE,
            account_id  INTEGER NOT NULL REFERENCES accounts(id),
            debit       REAL    DEFAULT 0,
            credit      REAL    DEFAULT 0,
            description TEXT,
            line_order  INTEGER DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS idx_lines_entry   ON journal_lines(entry_id);
        CREATE INDEX IF NOT EXISTS idx_lines_account ON journal_lines(account_id);
        CREATE INDEX IF NOT EXISTS idx_entries_date  ON journal_entries(entry_date);
    """)
    conn.commit()
    conn.close()


# ─── Accounts ───────────────────────────────────────────────────────────────

def get_accounts(active_only=True):
    conn = get_conn()
    q = "SELECT * FROM accounts"
    if active_only:
        q += " WHERE is_active=1"
    q += " ORDER BY code"
    df = pd.read_sql_query(q, conn)
    conn.close()
    return df


def add_account(code, name, acct_type, subtype, normal_side, description=""):
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO accounts (code,name,type,subtype,normal_side,description) VALUES (?,?,?,?,?,?)",
            (code, name, acct_type, subtype, normal_side, description)
        )
        conn.commit()
        return True, "Account created successfully."
    except sqlite3.IntegrityError:
        return False, f"Account code '{code}' already exists."
    finally:
        conn.close()


def update_account(account_id, code, name, acct_type, subtype, normal_side, description, is_active):
    conn = get_conn()
    try:
        conn.execute(
            """UPDATE accounts SET code=?,name=?,type=?,subtype=?,normal_side=?,
               description=?,is_active=? WHERE id=?""",
            (code, name, acct_type, subtype, normal_side, description, is_active, account_id)
        )
        conn.commit()
        return True, "Account updated."
    except sqlite3.IntegrityError:
        return False, f"Code '{code}' is already used by another account."
    finally:
        conn.close()


# ─── Journal Entries ─────────────────────────────────────────────────────────

def next_entry_number():
    conn = get_conn()
    row = conn.execute("SELECT COUNT(*) as cnt FROM journal_entries").fetchone()
    n = (row["cnt"] or 0) + 1
    conn.close()
    return f"JE-{n:05d}"


def add_journal_entry(entry_date, description, reference, lines, status="Posted"):
    """
    lines: list of dicts {account_id, debit, credit, description}
    """
    total_dr = sum(l["debit"] for l in lines)
    total_cr = sum(l["credit"] for l in lines)
    if abs(total_dr - total_cr) > 0.005:
        return False, f"Debits ({total_dr:,.2f}) ≠ Credits ({total_cr:,.2f}). Entry not saved."

    conn = get_conn()
    try:
        entry_num = next_entry_number()
        cur = conn.execute(
            "INSERT INTO journal_entries (entry_number,entry_date,description,reference,status) VALUES (?,?,?,?,?)",
            (entry_num, str(entry_date), description, reference, status)
        )
        eid = cur.lastrowid
        for i, l in enumerate(lines):
            conn.execute(
                "INSERT INTO journal_lines (entry_id,account_id,debit,credit,description,line_order) VALUES (?,?,?,?,?,?)",
                (eid, l["account_id"], l.get("debit", 0), l.get("credit", 0), l.get("description", ""), i)
            )
        conn.commit()
        return True, f"Journal entry {entry_num} posted successfully."
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


def void_journal_entry(entry_id):
    conn = get_conn()
    conn.execute("UPDATE journal_entries SET status='Void' WHERE id=?", (entry_id,))
    conn.commit()
    conn.close()


def get_journal_entries(start_date=None, end_date=None, status=None):
    conn = get_conn()
    q = """
        SELECT je.id, je.entry_number, je.entry_date, je.description, je.reference,
               je.status, je.created_at,
               SUM(jl.debit) as total_debit, SUM(jl.credit) as total_credit
        FROM journal_entries je
        LEFT JOIN journal_lines jl ON je.id = jl.entry_id
        WHERE 1=1
    """
    params = []
    if start_date:
        q += " AND je.entry_date >= ?"
        params.append(str(start_date))
    if end_date:
        q += " AND je.entry_date <= ?"
        params.append(str(end_date))
    if status:
        q += " AND je.status = ?"
        params.append(status)
    q += " GROUP BY je.id ORDER BY je.entry_date DESC, je.id DESC"
    df = pd.read_sql_query(q, conn, params=params)
    conn.close()
    return df


def get_entry_lines(entry_id):
    conn = get_conn()
    df = pd.read_sql_query("""
        SELECT jl.*, a.code as account_code, a.name as account_name, a.type as account_type
        FROM journal_lines jl
        JOIN accounts a ON jl.account_id = a.id
        WHERE jl.entry_id = ?
        ORDER BY jl.line_order
    """, conn, params=[entry_id])
    conn.close()
    return df


# ─── Ledger ──────────────────────────────────────────────────────────────────

def get_ledger(account_id=None, start_date=None, end_date=None):
    conn = get_conn()
    q = """
        SELECT je.entry_date, je.entry_number, je.description as entry_desc,
               jl.description as line_desc,
               a.code, a.name as account_name, a.type as account_type, a.normal_side,
               jl.debit, jl.credit, a.id as account_id
        FROM journal_lines jl
        JOIN journal_entries je ON jl.entry_id = je.id
        JOIN accounts a ON jl.account_id = a.id
        WHERE je.status = 'Posted'
    """
    params = []
    if account_id:
        q += " AND a.id = ?"
        params.append(account_id)
    if start_date:
        q += " AND je.entry_date >= ?"
        params.append(str(start_date))
    if end_date:
        q += " AND je.entry_date <= ?"
        params.append(str(end_date))
    q += " ORDER BY a.code, je.entry_date, je.id"
    df = pd.read_sql_query(q, conn, params=params)
    conn.close()
    return df


# ─── Trial Balance ────────────────────────────────────────────────────────────

def get_trial_balance(start_date=None, end_date=None, period_start=None):
    """
    Returns a trial balance DataFrame with:
    - Beginning balance (Dr/Cr) before period_start
    - Period movements (Dr/Cr) between period_start and end_date
    - Ending balance (Dr/Cr)
    """
    conn = get_conn()

    # All activity up to end_date
    def fetch_balances(from_date, to_date):
        q = """
            SELECT a.id, a.code, a.name, a.type, a.normal_side,
                   COALESCE(SUM(jl.debit),0)  as total_dr,
                   COALESCE(SUM(jl.credit),0) as total_cr
            FROM accounts a
            LEFT JOIN journal_lines jl ON a.id = jl.account_id
            LEFT JOIN journal_entries je ON jl.entry_id = je.id AND je.status='Posted'
        """
        params = []
        conditions = []
        if from_date:
            conditions.append("je.entry_date >= ?")
            params.append(str(from_date))
        if to_date:
            conditions.append("je.entry_date <= ?")
            params.append(str(to_date))
        if conditions:
            q += " AND " + " AND ".join(conditions)
        q += " GROUP BY a.id ORDER BY a.code"
        return pd.read_sql_query(q, conn, params=params)

    if period_start and start_date:
        beg = fetch_balances(None, str(date.fromisoformat(str(start_date)) - pd.Timedelta(days=1)))
        mv  = fetch_balances(start_date, end_date)
    else:
        beg = fetch_balances(None, None)
        beg["total_dr"] = 0
        beg["total_cr"] = 0
        mv  = fetch_balances(start_date, end_date)

    conn.close()

    # Merge
    df = mv.copy()
    df = df.rename(columns={"total_dr": "mv_dr", "total_cr": "mv_cr"})

    if period_start and start_date:
        beg = beg.rename(columns={"total_dr": "beg_dr", "total_cr": "beg_cr"})
        df = df.merge(beg[["id", "beg_dr", "beg_cr"]], on="id", how="left")
        df["beg_dr"] = df["beg_dr"].fillna(0)
        df["beg_cr"] = df["beg_cr"].fillna(0)
    else:
        df["beg_dr"] = 0
        df["beg_cr"] = 0

    # Compute net beginning balance (Dr side or Cr side)
    def net_balance(row, dr_col, cr_col):
        net = row[dr_col] - row[cr_col]
        if row["normal_side"] == "Dr":
            return max(net, 0), max(-net, 0)
        else:
            return max(-net, 0), max(net, 0)   # (showing_as_dr, showing_as_cr)

    df[["beg_bal_dr", "beg_bal_cr"]] = df.apply(
        lambda r: pd.Series(net_balance(r, "beg_dr", "beg_cr")), axis=1)

    df["end_dr"] = df["beg_dr"] + df["mv_dr"]
    df["end_cr"] = df["beg_cr"] + df["mv_cr"]

    df[["end_bal_dr", "end_bal_cr"]] = df.apply(
        lambda r: pd.Series(net_balance(r, "end_dr", "end_cr")), axis=1)

    return df


# ─── Financial Statements ────────────────────────────────────────────────────

def get_income_statement(start_date=None, end_date=None):
    conn = get_conn()
    q = """
        SELECT a.code, a.name, a.type, a.subtype, a.normal_side,
               COALESCE(SUM(jl.debit),0)  as total_dr,
               COALESCE(SUM(jl.credit),0) as total_cr
        FROM accounts a
        LEFT JOIN journal_lines jl ON a.id = jl.account_id
        LEFT JOIN journal_entries je ON jl.entry_id = je.id AND je.status='Posted'
        WHERE a.type IN ('Revenue','Expense')
    """
    params = []
    if start_date:
        q += " AND (je.entry_date >= ? OR je.entry_date IS NULL)"
        params.append(str(start_date))
    if end_date:
        q += " AND (je.entry_date <= ? OR je.entry_date IS NULL)"
        params.append(str(end_date))
    q += " GROUP BY a.id ORDER BY a.type DESC, a.code"
    df = pd.read_sql_query(q, conn, params=params)
    conn.close()

    df["net"] = df.apply(
        lambda r: r["total_cr"] - r["total_dr"] if r["type"] == "Revenue"
                  else r["total_dr"] - r["total_cr"], axis=1)
    return df


def get_balance_sheet(as_of_date=None):
    conn = get_conn()
    q = """
        SELECT a.code, a.name, a.type, a.subtype, a.normal_side,
               COALESCE(SUM(jl.debit),0)  as total_dr,
               COALESCE(SUM(jl.credit),0) as total_cr
        FROM accounts a
        LEFT JOIN journal_lines jl ON a.id = jl.account_id
        LEFT JOIN journal_entries je ON jl.entry_id = je.id AND je.status='Posted'
        WHERE a.type IN ('Asset','Liability','Equity')
    """
    params = []
    if as_of_date:
        q += " AND (je.entry_date <= ? OR je.entry_date IS NULL)"
        params.append(str(as_of_date))
    q += " GROUP BY a.id ORDER BY a.type, a.code"
    df = pd.read_sql_query(q, conn, params=params)
    conn.close()

    def bs_balance(row):
        net = row["total_dr"] - row["total_cr"]
        if row["type"] == "Asset":
            return net
        else:
            return -net

    df["balance"] = df.apply(bs_balance, axis=1)
    return df


# ─── Seed Data ───────────────────────────────────────────────────────────────

SEED_ACCOUNTS = [
    # Assets
    ("1000", "Cash & Cash Equivalents",      "Asset",     "Current Asset",    "Dr"),
    ("1010", "Petty Cash",                    "Asset",     "Current Asset",    "Dr"),
    ("1100", "Accounts Receivable",           "Asset",     "Current Asset",    "Dr"),
    ("1200", "Inventory",                     "Asset",     "Current Asset",    "Dr"),
    ("1300", "Prepaid Expenses",              "Asset",     "Current Asset",    "Dr"),
    ("1500", "Property, Plant & Equipment",   "Asset",     "Non-Current Asset","Dr"),
    ("1600", "Accumulated Depreciation",      "Asset",     "Non-Current Asset","Cr"),
    ("1700", "Intangible Assets",             "Asset",     "Non-Current Asset","Dr"),
    # Liabilities
    ("2000", "Accounts Payable",              "Liability", "Current Liability","Cr"),
    ("2100", "Accrued Liabilities",           "Liability", "Current Liability","Cr"),
    ("2200", "Short-Term Loans",              "Liability", "Current Liability","Cr"),
    ("2300", "Taxes Payable",                 "Liability", "Current Liability","Cr"),
    ("2500", "Long-Term Debt",                "Liability", "Long-Term Liability","Cr"),
    # Equity
    ("3000", "Share Capital",                 "Equity",    "Paid-In Capital",  "Cr"),
    ("3100", "Retained Earnings",             "Equity",    "Retained Earnings","Cr"),
    ("3200", "Additional Paid-In Capital",    "Equity",    "Paid-In Capital",  "Cr"),
    # Revenue
    ("4000", "Sales Revenue",                 "Revenue",   "Operating Revenue","Cr"),
    ("4100", "Service Revenue",               "Revenue",   "Operating Revenue","Cr"),
    ("4200", "Interest Income",               "Revenue",   "Other Income",     "Cr"),
    ("4300", "Other Income",                  "Revenue",   "Other Income",     "Cr"),
    # Expenses
    ("5000", "Cost of Goods Sold",            "Expense",   "COGS",             "Dr"),
    ("5100", "Salaries & Wages",              "Expense",   "Operating Expense","Dr"),
    ("5200", "Rent Expense",                  "Expense",   "Operating Expense","Dr"),
    ("5300", "Utilities Expense",             "Expense",   "Operating Expense","Dr"),
    ("5400", "Marketing & Advertising",       "Expense",   "Operating Expense","Dr"),
    ("5500", "Depreciation Expense",          "Expense",   "Operating Expense","Dr"),
    ("5600", "Insurance Expense",             "Expense",   "Operating Expense","Dr"),
    ("5700", "Interest Expense",              "Expense",   "Finance Expense",  "Dr"),
    ("5800", "Income Tax Expense",            "Expense",   "Tax Expense",      "Dr"),
    ("5900", "Miscellaneous Expense",         "Expense",   "Operating Expense","Dr"),
]

import sqlite3
import pandas as pd
from datetime import datetime, date
import os

# ✅ FIX 1: DB_PATH كان بياخد dirname مرتين فكان بيدور على الـ DB
#    في مكان غلط — دلوقتي بيحط الـ DB جنب database.py مباشرة
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "accounting.db")
DB_PATH = os.path.normpath(DB_PATH)


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS accounts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            code        TEXT    NOT NULL UNIQUE,
            name        TEXT    NOT NULL,
            type        TEXT    NOT NULL,
            subtype     TEXT,
            normal_side TEXT    NOT NULL,
            is_active   INTEGER DEFAULT 1,
            description TEXT,
            created_at  TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS journal_entries (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_number TEXT    NOT NULL UNIQUE,
            entry_date   TEXT    NOT NULL,
            description  TEXT    NOT NULL,
            reference    TEXT,
            status       TEXT    DEFAULT 'Posted',
            created_by   TEXT    DEFAULT 'System',
            created_at   TEXT    DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS journal_lines (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_id    INTEGER NOT NULL REFERENCES journal_entries(id) ON DELETE CASCADE,
            account_id  INTEGER NOT NULL REFERENCES accounts(id),
            debit       REAL    DEFAULT 0,
            credit      REAL    DEFAULT 0,
            description TEXT,
            line_order  INTEGER DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS idx_lines_entry   ON journal_lines(entry_id);
        CREATE INDEX IF NOT EXISTS idx_lines_account ON journal_lines(account_id);
        CREATE INDEX IF NOT EXISTS idx_entries_date  ON journal_entries(entry_date);
    """)
    conn.commit()
    conn.close()


# ─── Accounts ────────────────────────────────────────────────────────────────

def get_accounts(active_only=True):
    conn = get_conn()
    q = "SELECT * FROM accounts"
    if active_only:
        q += " WHERE is_active=1"
    q += " ORDER BY code"
    df = pd.read_sql_query(q, conn)
    conn.close()
    return df


def add_account(code, name, acct_type, subtype, normal_side, description=""):
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO accounts (code,name,type,subtype,normal_side,description) VALUES (?,?,?,?,?,?)",
            (code, name, acct_type, subtype, normal_side, description)
        )
        conn.commit()
        return True, "Account created successfully."
    except sqlite3.IntegrityError:
        return False, f"Account code '{code}' already exists."
    finally:
        conn.close()


def update_account(account_id, code, name, acct_type, subtype, normal_side, description, is_active):
    conn = get_conn()
    try:
        conn.execute(
            """UPDATE accounts SET code=?,name=?,type=?,subtype=?,normal_side=?,
               description=?,is_active=? WHERE id=?""",
            (code, name, acct_type, subtype, normal_side, description, is_active, account_id)
        )
        conn.commit()
        return True, "Account updated."
    except sqlite3.IntegrityError:
        return False, f"Code '{code}' is already used by another account."
    finally:
        conn.close()


# ─── Journal Entries ─────────────────────────────────────────────────────────

def next_entry_number():
    conn = get_conn()
    row = conn.execute("SELECT COUNT(*) as cnt FROM journal_entries").fetchone()
    n = (row["cnt"] or 0) + 1
    conn.close()
    return f"JE-{n:05d}"


def add_journal_entry(entry_date, description, reference, lines, status="Posted"):
    total_dr = sum(l["debit"] for l in lines)
    total_cr = sum(l["credit"] for l in lines)
    if abs(total_dr - total_cr) > 0.005:
        return False, f"Debits ({total_dr:,.2f}) ≠ Credits ({total_cr:,.2f}). Entry not saved."

    conn = get_conn()
    try:
        entry_num = next_entry_number()
        cur = conn.execute(
            "INSERT INTO journal_entries (entry_number,entry_date,description,reference,status) VALUES (?,?,?,?,?)",
            (entry_num, str(entry_date), description, reference, status)
        )
        eid = cur.lastrowid
        for i, l in enumerate(lines):
            conn.execute(
                "INSERT INTO journal_lines (entry_id,account_id,debit,credit,description,line_order) VALUES (?,?,?,?,?,?)",
                (eid, l["account_id"], l.get("debit", 0), l.get("credit", 0), l.get("description", ""), i)
            )
        conn.commit()
        return True, f"Journal entry {entry_num} posted successfully."
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


def void_journal_entry(entry_id):
    conn = get_conn()
    conn.execute("UPDATE journal_entries SET status='Void' WHERE id=?", (entry_id,))
    conn.commit()
    conn.close()


def get_journal_entries(start_date=None, end_date=None, status=None):
    conn = get_conn()
    q = """
        SELECT je.id, je.entry_number, je.entry_date, je.description, je.reference,
               je.status, je.created_at,
               COALESCE(SUM(jl.debit),0)  as total_debit,
               COALESCE(SUM(jl.credit),0) as total_credit
        FROM journal_entries je
        LEFT JOIN journal_lines jl ON je.id = jl.entry_id
        WHERE 1=1
    """
    params = []
    if start_date:
        q += " AND je.entry_date >= ?"
        params.append(str(start_date))
    if end_date:
        q += " AND je.entry_date <= ?"
        params.append(str(end_date))
    if status:
        q += " AND je.status = ?"
        params.append(status)
    q += " GROUP BY je.id ORDER BY je.entry_date DESC, je.id DESC"
    df = pd.read_sql_query(q, conn, params=params)
    conn.close()
    return df


def get_entry_lines(entry_id):
    conn = get_conn()
    df = pd.read_sql_query("""
        SELECT jl.*, a.code as account_code, a.name as account_name, a.type as account_type
        FROM journal_lines jl
        JOIN accounts a ON jl.account_id = a.id
        WHERE jl.entry_id = ?
        ORDER BY jl.line_order
    """, conn, params=[entry_id])
    conn.close()
    return df


# ─── Ledger ──────────────────────────────────────────────────────────────────

def get_ledger(account_id=None, start_date=None, end_date=None):
    conn = get_conn()
    q = """
        SELECT je.entry_date, je.entry_number, je.description as entry_desc,
               jl.description as line_desc,
               a.code, a.name as account_name, a.type as account_type, a.normal_side,
               jl.debit, jl.credit, a.id as account_id
        FROM journal_lines jl
        JOIN journal_entries je ON jl.entry_id = je.id
        JOIN accounts a ON jl.account_id = a.id
        WHERE je.status = 'Posted'
    """
    params = []
    if account_id:
        q += " AND a.id = ?"
        params.append(account_id)
    if start_date:
        q += " AND je.entry_date >= ?"
        params.append(str(start_date))
    if end_date:
        q += " AND je.entry_date <= ?"
        params.append(str(end_date))
    q += " ORDER BY a.code, je.entry_date, je.id"
    df = pd.read_sql_query(q, conn, params=params)
    conn.close()
    return df


# ─── Trial Balance ────────────────────────────────────────────────────────────

def get_trial_balance(start_date=None, end_date=None, period_start=None):
    conn = get_conn()

    def fetch_balances(from_date, to_date):
        q = """
            SELECT a.id, a.code, a.name, a.type, a.normal_side,
                   COALESCE(SUM(jl.debit),0)  as total_dr,
                   COALESCE(SUM(jl.credit),0) as total_cr
            FROM accounts a
            LEFT JOIN journal_lines jl ON a.id = jl.account_id
            LEFT JOIN journal_entries je ON jl.entry_id = je.id AND je.status='Posted'
        """
        params = []
        conditions = []
        if from_date:
            conditions.append("je.entry_date >= ?")
            params.append(str(from_date))
        if to_date:
            conditions.append("je.entry_date <= ?")
            params.append(str(to_date))
        if conditions:
            q += " AND " + " AND ".join(conditions)
        q += " GROUP BY a.id ORDER BY a.code"
        return pd.read_sql_query(q, conn, params=params)

    if period_start and start_date:
        beg_end = str(date.fromisoformat(str(start_date)) - pd.Timedelta(days=1))
        beg = fetch_balances(None, beg_end)
        mv  = fetch_balances(start_date, end_date)
    else:
        beg = fetch_balances(None, None)
        beg["total_dr"] = 0
        beg["total_cr"] = 0
        mv  = fetch_balances(start_date, end_date)

    conn.close()

    df = mv.copy()
    df = df.rename(columns={"total_dr": "mv_dr", "total_cr": "mv_cr"})

    if period_start and start_date:
        beg = beg.rename(columns={"total_dr": "beg_dr", "total_cr": "beg_cr"})
        df = df.merge(beg[["id", "beg_dr", "beg_cr"]], on="id", how="left")
        df["beg_dr"] = df["beg_dr"].fillna(0)
        df["beg_cr"] = df["beg_cr"].fillna(0)
    else:
        df["beg_dr"] = 0
        df["beg_cr"] = 0

    def net_balance(row, dr_col, cr_col):
        net = row[dr_col] - row[cr_col]
        if row["normal_side"] == "Dr":
            return max(net, 0), max(-net, 0)
        else:
            return max(-net, 0), max(net, 0)

    df[["beg_bal_dr", "beg_bal_cr"]] = df.apply(
        lambda r: pd.Series(net_balance(r, "beg_dr", "beg_cr")), axis=1)

    df["end_dr"] = df["beg_dr"] + df["mv_dr"]
    df["end_cr"] = df["beg_cr"] + df["mv_cr"]

    df[["end_bal_dr", "end_bal_cr"]] = df.apply(
        lambda r: pd.Series(net_balance(r, "end_dr", "end_cr")), axis=1)

    return df


# ─── Financial Statements ────────────────────────────────────────────────────

def get_income_statement(start_date=None, end_date=None):
    conn = get_conn()
    q = """
        SELECT a.code, a.name, a.type, a.subtype, a.normal_side,
               COALESCE(SUM(jl.debit),0)  as total_dr,
               COALESCE(SUM(jl.credit),0) as total_cr
        FROM accounts a
        LEFT JOIN journal_lines jl ON a.id = jl.account_id
        LEFT JOIN journal_entries je ON jl.entry_id = je.id AND je.status='Posted'
        WHERE a.type IN ('Revenue','Expense')
    """
    params = []
    if start_date:
        q += " AND (je.entry_date >= ? OR je.entry_date IS NULL)"
        params.append(str(start_date))
    if end_date:
        q += " AND (je.entry_date <= ? OR je.entry_date IS NULL)"
        params.append(str(end_date))
    q += " GROUP BY a.id ORDER BY a.type DESC, a.code"
    df = pd.read_sql_query(q, conn, params=params)
    conn.close()

    df["net"] = df.apply(
        lambda r: r["total_cr"] - r["total_dr"] if r["type"] == "Revenue"
                  else r["total_dr"] - r["total_cr"], axis=1)
    return df


def get_balance_sheet(as_of_date=None):
    conn = get_conn()
    q = """
        SELECT a.code, a.name, a.type, a.subtype, a.normal_side,
               COALESCE(SUM(jl.debit),0)  as total_dr,
               COALESCE(SUM(jl.credit),0) as total_cr
        FROM accounts a
        LEFT JOIN journal_lines jl ON a.id = jl.account_id
        LEFT JOIN journal_entries je ON jl.entry_id = je.id AND je.status='Posted'
        WHERE a.type IN ('Asset','Liability','Equity')
    """
    params = []
    if as_of_date:
        q += " AND (je.entry_date <= ? OR je.entry_date IS NULL)"
        params.append(str(as_of_date))
    q += " GROUP BY a.id ORDER BY a.type, a.code"
    df = pd.read_sql_query(q, conn, params=params)
    conn.close()

    def bs_balance(row):
        net = row["total_dr"] - row["total_cr"]
        return net if row["type"] == "Asset" else -net

    df["balance"] = df.apply(bs_balance, axis=1)
    return df


# ─── Seed Data ───────────────────────────────────────────────────────────────

SEED_ACCOUNTS = [
    # Assets
    ("1000", "Cash & Cash Equivalents",      "Asset",     "Current Asset",     "Dr"),
    ("1010", "Petty Cash",                   "Asset",     "Current Asset",     "Dr"),
    ("1100", "Accounts Receivable",          "Asset",     "Current Asset",     "Dr"),
    ("1200", "Inventory",                    "Asset",     "Current Asset",     "Dr"),
    ("1300", "Prepaid Expenses",             "Asset",     "Current Asset",     "Dr"),
    ("1500", "Property, Plant & Equipment",  "Asset",     "Non-Current Asset", "Dr"),
    ("1600", "Accumulated Depreciation",     "Asset",     "Non-Current Asset", "Cr"),
    ("1700", "Intangible Assets",            "Asset",     "Non-Current Asset", "Dr"),
    # Liabilities
    ("2000", "Accounts Payable",             "Liability", "Current Liability",  "Cr"),
    ("2100", "Accrued Liabilities",          "Liability", "Current Liability",  "Cr"),
    ("2200", "Short-Term Loans",             "Liability", "Current Liability",  "Cr"),
    ("2300", "Taxes Payable",                "Liability", "Current Liability",  "Cr"),
    ("2500", "Long-Term Debt",               "Liability", "Long-Term Liability","Cr"),
    # Equity
    ("3000", "Share Capital",                "Equity",    "Paid-In Capital",   "Cr"),
    ("3100", "Retained Earnings",            "Equity",    "Retained Earnings", "Cr"),
    ("3200", "Additional Paid-In Capital",   "Equity",    "Paid-In Capital",   "Cr"),
    # Revenue
    ("4000", "Sales Revenue",                "Revenue",   "Operating Revenue", "Cr"),
    ("4100", "Service Revenue",              "Revenue",   "Operating Revenue", "Cr"),
    ("4200", "Interest Income",              "Revenue",   "Other Income",      "Cr"),
    ("4300", "Other Income",                 "Revenue",   "Other Income",      "Cr"),
    # Expenses
    ("5000", "Cost of Goods Sold",           "Expense",   "COGS",              "Dr"),
    ("5100", "Salaries & Wages",             "Expense",   "Operating Expense", "Dr"),
    ("5200", "Rent Expense",                 "Expense",   "Operating Expense", "Dr"),
    ("5300", "Utilities Expense",            "Expense",   "Operating Expense", "Dr"),
    ("5400", "Marketing & Advertising",      "Expense",   "Operating Expense", "Dr"),
    ("5500", "Depreciation Expense",         "Expense",   "Operating Expense", "Dr"),
    ("5600", "Insurance Expense",            "Expense",   "Operating Expense", "Dr"),
    ("5700", "Interest Expense",             "Expense",   "Finance Expense",   "Dr"),
    ("5800", "Income Tax Expense",           "Expense",   "Tax Expense",       "Dr"),
    ("5900", "Miscellaneous Expense",        "Expense",   "Operating Expense", "Dr"),
]

# 1. خلي القائمة دي فاضية تماماً
SEED_ENTRIES = []

def seed_database():
    """Insert demo accounts and journal entries — only runs on empty DB."""
    conn = get_conn()
    count = conn.execute("SELECT COUNT(*) as c FROM accounts").fetchone()["c"]
    conn.close()
    
    if count > 0:
        return  

    # البرنامج هيدخل أسماء الحسابات بس (Cash, Revenue, etc.) بدون مبالغ
    code_to_id = {}
    conn = get_conn()
    for code, name, atype, subtype, ns in SEED_ACCOUNTS:
        cur = conn.execute(
            "INSERT INTO accounts (code,name,type,subtype,normal_side) VALUES (?,?,?,?,?)",
            (code, name, atype, subtype, ns)
        )
        code_to_id[code] = cur.lastrowid
    conn.commit()
    conn.close()

    # وبما إن SEED_ENTRIES فاضية، اللوب اللي تحت دي مش هتعمل حاجة
    for e in SEED_ENTRIES:
        # لن يتم إدخال أي مبالغ مالية
        pass