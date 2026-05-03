import sqlite3


def get_overrides(conn: sqlite3.Connection, competition_id: int) -> dict[int, str]:
    rows = conn.execute(
        "SELECT station_number, sector_name FROM competition_sector_overrides "
        "WHERE competition_id = ?",
        (competition_id,),
    ).fetchall()
    return {row["station_number"]: row["sector_name"] for row in rows}


def get_override(
    conn: sqlite3.Connection, competition_id: int, station_number: int,
) -> str | None:
    row = conn.execute(
        "SELECT sector_name FROM competition_sector_overrides "
        "WHERE competition_id = ? AND station_number = ?",
        (competition_id, station_number),
    ).fetchone()
    return row["sector_name"] if row else None


def set_overrides(
    conn: sqlite3.Connection,
    competition_id: int,
    overrides: dict[int, str],
) -> None:
    conn.execute(
        "DELETE FROM competition_sector_overrides WHERE competition_id = ?",
        (competition_id,),
    )
    for station_number, sector_name in overrides.items():
        conn.execute(
            "INSERT INTO competition_sector_overrides "
            "(competition_id, station_number, sector_name) VALUES (?, ?, ?)",
            (competition_id, int(station_number), sector_name),
        )


def clear_overrides(conn: sqlite3.Connection, competition_id: int) -> None:
    conn.execute(
        "DELETE FROM competition_sector_overrides WHERE competition_id = ?",
        (competition_id,),
    )
