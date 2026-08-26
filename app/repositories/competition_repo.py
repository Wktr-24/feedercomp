import sqlite3

from app.models.competition import Competition


_COLUMNS = (
    "id, venue_id, date, name, max_competitors, winner_places, created_at, "
    "linked_competition_id"
)


def create(
    conn: sqlite3.Connection,
    venue_id: int,
    date: str,
    name: str | None = None,
    max_competitors: int = 50,
    winner_places: int = 3,
    linked_competition_id: int | None = None,
) -> int:
    cursor = conn.execute(
        "INSERT INTO competitions "
        "(venue_id, date, name, max_competitors, winner_places, linked_competition_id) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (venue_id, date, name, max_competitors, winner_places, linked_competition_id),
    )
    return cursor.lastrowid


def get_all(conn: sqlite3.Connection) -> list[Competition]:
    rows = conn.execute(
        # Secondary id key: keeps same-date rows (day 1 + day 2 of a final
        # after the user accepted an equal-date warning) in a stable order.
        f"SELECT {_COLUMNS} FROM competitions ORDER BY date DESC, id DESC"
    ).fetchall()
    return [Competition(**row) for row in rows]


def get_by_id(conn: sqlite3.Connection, competition_id: int) -> Competition | None:
    row = conn.execute(
        f"SELECT {_COLUMNS} FROM competitions WHERE id = ?",
        (competition_id,),
    ).fetchone()
    return Competition(**row) if row else None


def get_day2_of(conn: sqlite3.Connection, competition_id: int) -> Competition | None:
    """Return the competition whose linked_competition_id points at the given
    one (i.e. its day 2), or None. 1:1 by construction — competition_service
    refuses to create a second day 2 for the same source."""
    row = conn.execute(
        f"SELECT {_COLUMNS} FROM competitions WHERE linked_competition_id = ? "
        "ORDER BY id LIMIT 1",
        (competition_id,),
    ).fetchone()
    return Competition(**row) if row else None


def update_winner_places(conn: sqlite3.Connection, competition_id: int, winner_places: int) -> None:
    conn.execute(
        "UPDATE competitions SET winner_places = ? WHERE id = ?",
        (winner_places, competition_id),
    )


def update_name(conn: sqlite3.Connection, competition_id: int, name: str | None) -> None:
    conn.execute(
        "UPDATE competitions SET name = ? WHERE id = ?",
        (name, competition_id),
    )


def delete(conn: sqlite3.Connection, competition_id: int) -> None:
    conn.execute("DELETE FROM competitions WHERE id = ?", (competition_id,))
