"""Persistent first-run state, kept separate from shop data."""
from database import connect
_KEY="onboarding_completed"
def is_complete():
    with connect() as conn:
        row=conn.execute("SELECT value FROM commerce_state WHERE key=?",(_KEY,)).fetchone()
    return bool(row and row[0]=="1")
def mark_complete():
    with connect() as conn:
        conn.execute("INSERT INTO commerce_state(key,value) VALUES(?, '1') ON CONFLICT(key) DO UPDATE SET value='1',updated_at=CURRENT_TIMESTAMP",(_KEY,))
        conn.commit()
