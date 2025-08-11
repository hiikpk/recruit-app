import os, sqlite3

DB = os.path.join(os.getcwd(), 'instance', 'recruiting.db')

if not os.path.exists(DB):
    print('DB not found:', DB)
    raise SystemExit(1)

conn = sqlite3.connect(DB)
cur = conn.cursor()

# Ensure tables exist
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='applications'")
if not cur.fetchone():
    print('applications table not found')
    conn.close()
    raise SystemExit(1)

# Find missing application ids referenced by interviews
cur.execute("SELECT DISTINCT application_id FROM interviews")
interview_app_ids = [row[0] for row in cur.fetchall()]
cur.execute("SELECT id FROM applications")
existing_app_ids = {row[0] for row in cur.fetchall()}
missing = [aid for aid in interview_app_ids if aid not in existing_app_ids]

# If no missing, nothing to do
if not missing:
    print('No missing applications referenced by interviews.')
    conn.close()
    raise SystemExit(0)

# Strategy: If there is a candidate with id=1, attach missing app ids to candidate 1 (org_id = candidate.org_id)
# Otherwise attach to the first candidate we find.
cur.execute("SELECT id, coalesce(org_id, 1) FROM candidates ORDER BY id")
rows = cur.fetchall()
if not rows:
    print('No candidates found; cannot repair.')
    conn.close()
    raise SystemExit(1)

cand_id, cand_org = None, None
for cid, org in rows:
    if cid == 1:
        cand_id, cand_org = cid, org
        break
if cand_id is None:
    cand_id, cand_org = rows[0]

print(f'Will create Applications for candidate_id={cand_id}, org_id={cand_org}:', missing)

for aid in missing:
    cur.execute(
        "INSERT INTO applications (id, candidate_id, org_id, status, stage) VALUES (?, ?, ?, 'screening', 'document')",
        (aid, cand_id, cand_org)
    )

conn.commit()
conn.close()
print('Repair done.')
