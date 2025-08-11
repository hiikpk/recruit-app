import os, sqlite3, sys

DBS = [
    os.path.join(os.getcwd(), 'recruiting.db'),
    os.path.join(os.getcwd(), 'instance', 'recruiting.db'),
]

def inspect(db):
    print(f"\n=== {db} ===")
    if not os.path.exists(db):
        print("missing")
        return
    conn = sqlite3.connect(db)
    cur = conn.cursor()
    def q(sql, params=()):
        cur.execute(sql, params)
        return cur.fetchall()
    try:
        print('candidates:', q('select id,name,coalesce(org_id,0) from candidates order by id'))
        print('applications:', q('select id,candidate_id,coalesce(org_id,0) from applications order by id'))
        print('interviews:', q('select id,application_id,coalesce(org_id,0) from interviews order by id'))
        print('recordings:', q('select id,interview_id from recordings order by id'))
        # Candidate 1 linkage
        print('applications for candidate 1:', q('select id,candidate_id from applications where candidate_id=? order by id', (1,)))
        print('interviews for candidate 1 (via join):', q('select i.id,i.application_id from interviews i join applications a on a.id=i.application_id where a.candidate_id=? order by i.id', (1,)))
    except Exception as e:
        print('error:', e)
    finally:
        conn.close()

if __name__ == '__main__':
    for db in DBS:
        inspect(db)
    print('\nDone.')
