import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.database import get_conn, add_journal_entry, add_account

def reset_and_populate():
    conn = get_conn()
    
    # 1. Clear all existing journal entries and lines
    conn.execute("DELETE FROM journal_lines")
    conn.execute("DELETE FROM journal_entries")
    conn.commit()
    conn.close()

    # 2. Add specific accounts for Problem 3-7 if they don't exist
    add_account("1320", "Supplies", "Asset", "Current Asset", "Dr")
    add_account("1330", "Prepaid Insurance", "Asset", "Current Asset", "Dr")
    add_account("1520", "Land", "Asset", "Non-Current Asset", "Dr")
    add_account("1530", "Equipment", "Asset", "Non-Current Asset", "Dr")
    add_account("3010", "Capital", "Equity", "Paid-In Capital", "Cr")
    add_account("3300", "Drawings", "Equity", "Retained Earnings", "Dr")
    add_account("5110", "Wages Expense", "Expense", "Operating Expense", "Dr")

    # Fetch updated accounts mapping
    conn = get_conn()
    accounts = conn.execute("SELECT id, code FROM accounts").fetchall()
    conn.close()
    code_to_id = {row['code']: row['id'] for row in accounts}

    # 3. Insert problem data for October 2026
    entries = [
        {
            "date": "2026-10-01",
            "desc": "Invested $40,000 cash in the business.",
            "ref": "P37-01",
            "lines": [{"code": "1000", "dr": 40000, "cr": 0}, {"code": "3010", "dr": 0, "cr": 40000}]
        },
        {
            "date": "2026-10-02",
            "desc": "purchased land costing $28,000 for cash.",
            "ref": "P37-02",
            "lines": [{"code": "1520", "dr": 28000, "cr": 0}, {"code": "1000", "dr": 0, "cr": 28000}]
        },
        {
            "date": "2026-10-03",
            "desc": "purchased equipment costing $15,000 for $3000 cash and the remainder on credit.",
            "ref": "P37-03",
            "lines": [{"code": "1530", "dr": 15000, "cr": 0}, {"code": "1000", "dr": 0, "cr": 3000}, {"code": "2000", "dr": 0, "cr": 12000}]
        },
        {
            "date": "2026-10-04",
            "desc": "purchased supplies on account for $800.",
            "ref": "P37-04",
            "lines": [{"code": "1320", "dr": 800, "cr": 0}, {"code": "2000", "dr": 0, "cr": 800}]
        },
        {
            "date": "2026-10-05",
            "desc": "paid $1000 for a one-year insurance policy.",
            "ref": "P37-05",
            "lines": [{"code": "1330", "dr": 1000, "cr": 0}, {"code": "1000", "dr": 0, "cr": 1000}]
        },
        {
            "date": "2026-10-06",
            "desc": "Provided services for customers on account for $10,000.",
            "ref": "P37-06",
            "lines": [{"code": "1100", "dr": 10000, "cr": 0}, {"code": "4100", "dr": 0, "cr": 10000}]
        },
        {
            "date": "2026-10-07",
            "desc": "pay the amount due to the equipment supplier in cash.",
            "ref": "P37-07",
            "lines": [{"code": "2000", "dr": 12000, "cr": 0}, {"code": "1000", "dr": 0, "cr": 12000}]
        },
        {
            "date": "2026-10-08",
            "desc": "received $3000 cash from customers for the services previously provided.",
            "ref": "P37-08",
            "lines": [{"code": "1000", "dr": 3000, "cr": 0}, {"code": "1100", "dr": 0, "cr": 3000}]
        },
        {
            "date": "2026-10-09",
            "desc": "Paid wages to workers for $2500.",
            "ref": "P37-09",
            "lines": [{"code": "5110", "dr": 2500, "cr": 0}, {"code": "1000", "dr": 0, "cr": 2500}]
        },
        {
            "date": "2026-10-10",
            "desc": "withdrew $2000 cash from the business.",
            "ref": "P37-10",
            "lines": [{"code": "3300", "dr": 2000, "cr": 0}, {"code": "1000", "dr": 0, "cr": 2000}]
        }
    ]

    for e in entries:
        lines = []
        for l in e["lines"]:
            lines.append({
                "account_id": code_to_id[l["code"]],
                "debit": l["dr"],
                "credit": l["cr"],
                "description": ""
            })
        status, msg = add_journal_entry(e["date"], e["desc"], e["ref"], lines)
        if status:
            print(f"Success: {msg}")
        else:
            print(f"Error: {msg}")

if __name__ == '__main__':
    reset_and_populate()
