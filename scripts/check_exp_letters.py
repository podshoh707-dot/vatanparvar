import json
import sqlite3
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

con = sqlite3.connect('db/database.sqlite')
cur = con.cursor()

cur.execute("""
    SELECT id, category, text, option_a, option_b, option_c, option_d, correct_option, explanation 
    FROM questions 
    ORDER BY id
""")
rows = cur.fetchall()

mismatches = []
for r in rows:
    qid, cat, text, oa, ob, oc, od, corr, exp = r
    if not exp:
        continue
    exp_low = exp.lower()
    
    # Check if explanation explicitly names a letter or an answer option
    # e.g., if explanation says "to'g'ri javob - B" or "A javob to'g'ri"
    m_let = re.search(r'(?:to[\'‘`]?g[\'‘`]?ri\s+javob|javob)[\s:\-]+([A-D])\b', exp, re.IGNORECASE)
    if m_let:
        exp_let = m_let.group(1).upper()
        if exp_let != corr:
            mismatches.append((qid, cat, text[:50], corr, exp_let, f"Explanation mentions {exp_let}"))

print(f"Total checked: {len(rows)}")
print(f"Explanation letter mismatches: {len(mismatches)}")
for m in mismatches:
    print(m)

con.close()
