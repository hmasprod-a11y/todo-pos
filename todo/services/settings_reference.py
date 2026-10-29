"""Database-backed reference lists used by settings screens.

No Tkinter dependencies: these functions can be reused by other frontends.
"""


def list_sellers():
    from database import connect
    with connect() as conn:
        rows = conn.execute(
            "SELECT id,name,active FROM sellers ORDER BY name COLLATE NOCASE"
        ).fetchall()
    return [dict(row) for row in rows]


def list_price_grids():
    from database import connect
    with connect() as conn:
        rows = conn.execute(
            "SELECT id,name,active FROM price_grids ORDER BY name COLLATE NOCASE"
        ).fetchall()
    return [dict(row) for row in rows]
