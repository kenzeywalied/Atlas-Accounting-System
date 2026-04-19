import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.database import get_conn, add_journal_entry, add_account

def reset_and_populate():
    conn = get_conn()
    
    # 1. Clear all existing journal entries to ensure ONLY Problem 3-1 data exists
    conn.execute("DELETE FROM journal_lines")
    conn.execute("DELETE FROM journal_entries")
    
    # Optional: Delete accounts that were part of seed data? 
    # Let's just keep them and add what's missing so the trial balance looks clean.
    conn.commit()
    conn.close()

    # 2. Add missing specific accounts from the assignment (ignoring errors if they already exist)
    add_account("1310", "Office Supplies", "Asset", "Current Asset", "Dr")
    add_account("1510", "Buildings", "Asset", "Non-Current Asset", "Dr")
    add_account("2210", "Notes Payable", "Liability", "Current Liability", "Cr")
    add_account("3010", "Capital", "Equity", "Paid-In Capital", "Cr")
    add_account("3300", "Drawings", "Equity", "Retained Earnings", "Dr")

    # Fetch updated accounts mapping
    conn = get_conn()
    accounts = conn.execute("SELECT id, code FROM accounts").fetchall()
    conn.close()
    code_to_id = {row['code']: row['id'] for row in accounts}

    # 3. Insert problem data
    entries = [
        {
            "date": "2026-01-01",
            "desc": "Deposit 75,000 in the bank as capital for the business",
            "ref": "P31-01",
            "lines": [{"code": "1000", "dr": 75000, "cr": 0}, {"code": "3010", "dr": 0, "cr": 75000}]
        },
        {
            "date": "2026-01-05",
            "desc": "borrowing 25,000 from Misr bank in cash",
            "ref": "P31-02",
            "lines": [{"code": "1000", "dr": 25000, "cr": 0}, {"code": "2200", "dr": 0, "cr": 25000}]
        },
        {
            "date": "2026-01-08",
            "desc": "Purchasing a building for 60,000. paid 25,000 in cash & sign a note payable for the remaining balance",
            "ref": "P31-03",
            "lines": [{"code": "1510", "dr": 60000, "cr": 0}, {"code": "1000", "dr": 0, "cr": 25000}, {"code": "2210", "dr": 0, "cr": 35000}]
        },
        {
            "date": "2026-01-09",
            "desc": "Purchase office supplies for 10,000 on credit",
            "ref": "P31-04",
            "lines": [{"code": "1310", "dr": 10000, "cr": 0}, {"code": "2000", "dr": 0, "cr": 10000}]
        },
        {
            "date": "2026-01-12",
            "desc": "paid rent for 4000 in cash",
            "ref": "P31-05",
            "lines": [{"code": "5200", "dr": 4000, "cr": 0}, {"code": "1000", "dr": 0, "cr": 4000}]
        },
        {
            "date": "2026-01-15",
            "desc": "provide services to customers for 12,000 in cash",
            "ref": "P31-06",
            "lines": [{"code": "1000", "dr": 12000, "cr": 0}, {"code": "4100", "dr": 0, "cr": 12000}]
        },
        {
            "date": "2026-01-18",
            "desc": "paid the amount due for office supplies",
            "ref": "P31-07",
            "lines": [{"code": "2000", "dr": 10000, "cr": 0}, {"code": "1000", "dr": 0, "cr": 10000}]
        },
        {
            "date": "2026-01-22",
            "desc": "provide services to customers for 10,000 on account",
            "ref": "P31-08",
            "lines": [{"code": "1100", "dr": 10000, "cr": 0}, {"code": "4100", "dr": 0, "cr": 10000}]
        },
        {
            "date": "2026-01-25",
            "desc": "paid salaries for 4000 in cash",
            "ref": "P31-09",
            "lines": [{"code": "5100", "dr": 4000, "cr": 0}, {"code": "1000", "dr": 0, "cr": 4000}]
        },
        {
            "date": "2026-01-28",
            "desc": "collect the amount due from customers on 22 in cash",
            "ref": "P31-10",
            "lines": [{"code": "1000", "dr": 10000, "cr": 0}, {"code": "1100", "dr": 0, "cr": 10000}]
        },
        {
            "date": "2026-01-31",
            "desc": "The owner withdrew 2000 in cash for personal use",
            "ref": "P31-11",
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
