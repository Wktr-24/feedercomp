import sqlite3

from app.models.venue import Venue, VenueSector


def get_all(conn: sqlite3.Connection) -> list[Venue]:
    rows = conn.execute("SELECT id, name, total_stations FROM venues ORDER BY id").fetchall()
    return [Venue(**row) for row in rows]


def get_by_id(conn: sqlite3.Connection, venue_id: int) -> Venue | None:
    row = conn.execute(
        "SELECT id, name, total_stations FROM venues WHERE id = ?", (venue_id,)
    ).fetchone()
    return Venue(**row) if row else None


def get_sectors(conn: sqlite3.Connection, venue_id: int) -> list[VenueSector]:
    rows = conn.execute(
        "SELECT id, venue_id, sector_name, station_number FROM venue_sectors "
        "WHERE venue_id = ? ORDER BY sector_name, station_number",
        (venue_id,),
    ).fetchall()
    return [VenueSector(**row) for row in rows]


def get_sector_names(conn: sqlite3.Connection, venue_id: int) -> list[str]:
    rows = conn.execute(
        "SELECT DISTINCT sector_name FROM venue_sectors "
        "WHERE venue_id = ? ORDER BY sector_name",
        (venue_id,),
    ).fetchall()
    return [row["sector_name"] for row in rows]


def get_sector_for_station(conn: sqlite3.Connection, venue_id: int, station_number: int) -> str | None:
    row = conn.execute(
        "SELECT sector_name FROM venue_sectors WHERE venue_id = ? AND station_number = ?",
        (venue_id, station_number),
    ).fetchone()
    return row["sector_name"] if row else None


def update_sectors(conn: sqlite3.Connection, venue_id: int, sectors: dict[str, list[int]]) -> None:
    conn.execute("DELETE FROM venue_sectors WHERE venue_id = ?", (venue_id,))
    for sector_name, stations in sectors.items():
        for station in stations:
            conn.execute(
                "INSERT INTO venue_sectors (venue_id, sector_name, station_number) VALUES (?, ?, ?)",
                (venue_id, sector_name, station),
            )


def create(conn: sqlite3.Connection, name: str, total_stations: int) -> int:
    cursor = conn.execute(
        "INSERT INTO venues (name, total_stations) VALUES (?, ?)",
        (name, total_stations),
    )
    return cursor.lastrowid
