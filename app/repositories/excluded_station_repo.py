import sqlite3


def get_excluded(conn: sqlite3.Connection, competition_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT station_number, sector_name FROM excluded_stations "
        "WHERE competition_id = ? ORDER BY station_number",
        (competition_id,),
    ).fetchall()
    return [{"station_number": row["station_number"], "sector_name": row["sector_name"]} for row in rows]


def add_excluded(
    conn: sqlite3.Connection,
    competition_id: int,
    venue_id: int,
    station_number: int,
    sector_name: str,
) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO excluded_stations (competition_id, venue_id, station_number, sector_name) "
        "VALUES (?, ?, ?, ?)",
        (competition_id, venue_id, station_number, sector_name),
    )


def remove_excluded(conn: sqlite3.Connection, competition_id: int, station_number: int) -> None:
    conn.execute(
        "DELETE FROM excluded_stations WHERE competition_id = ? AND station_number = ?",
        (competition_id, station_number),
    )


def clear_excluded(conn: sqlite3.Connection, competition_id: int) -> None:
    conn.execute("DELETE FROM excluded_stations WHERE competition_id = ?", (competition_id,))


def is_excluded(conn: sqlite3.Connection, competition_id: int, station_number: int) -> bool:
    row = conn.execute(
        "SELECT 1 FROM excluded_stations WHERE competition_id = ? AND station_number = ?",
        (competition_id, station_number),
    ).fetchone()
    return row is not None
