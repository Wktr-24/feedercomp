import sqlite3

from app.models.competition import Competition


def create(
    conn: sqlite3.Connection,
    venue_id: int,
    date: str,
    name: str | None = None,
    max_competitors: int = 50,
    winner_places: int = 3,
) -> int:
    cursor = conn.execute(
        "INSERT INTO competitions (venue_id, date, name, max_competitors, winner_places) "
        "VALUES (?, ?, ?, ?, ?)",
        (venue_id, date, name, max_competitors, winner_places),
    )
    return cursor.lastrowid


def get_all(conn: sqlite3.Connection) -> list[Competition]:
    rows = conn.execute(
        "SELECT id, venue_id, date, name, max_competitors, winner_places, created_at "
        "FROM competitions ORDER BY date DESC"
    ).fetchall()
    return [Competition(**row) for row in rows]


def get_by_id(conn: sqlite3.Connection, competition_id: int) -> Competition | None:
    row = conn.execute(
        "SELECT id, venue_id, date, name, max_competitors, winner_places, created_at "
        "FROM competitions WHERE id = ?",
        (competition_id,),
    ).fetchone()
    return Competition(**row) if row else None


def update_winner_places(conn: sqlite3.Connection, competition_id: int, winner_places: int) -> None:
    conn.execute(
        "UPDATE competitions SET winner_places = ? WHERE id = ?",
        (winner_places, competition_id),
    )


def delete(conn: sqlite3.Connection, competition_id: int) -> None:
    conn.execute("DELETE FROM competitions WHERE id = ?", (competition_id,))
