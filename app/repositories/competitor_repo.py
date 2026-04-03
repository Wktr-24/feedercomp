import sqlite3

from app.models.competitor import Competitor

_COLUMNS = (
    "id, competition_id, list_number, full_name, phone, payment_status, "
    "is_present, station_number, sector_name, weight_grams, "
    "sector_place, sector_points, final_place"
)


def _row_to_competitor(row: sqlite3.Row) -> Competitor:
    return Competitor(
        id=row["id"],
        competition_id=row["competition_id"],
        list_number=row["list_number"],
        full_name=row["full_name"],
        phone=row["phone"],
        payment_status=row["payment_status"],
        is_present=bool(row["is_present"]),
        station_number=row["station_number"],
        sector_name=row["sector_name"],
        weight_grams=row["weight_grams"],
        sector_place=row["sector_place"],
        sector_points=row["sector_points"],
        final_place=row["final_place"],
    )


def add(
    conn: sqlite3.Connection,
    competition_id: int,
    list_number: int,
    full_name: str,
    phone: str | None = None,
    payment_status: str = "unpaid",
) -> int:
    cursor = conn.execute(
        "INSERT INTO competitors (competition_id, list_number, full_name, phone, payment_status) "
        "VALUES (?, ?, ?, ?, ?)",
        (competition_id, list_number, full_name, phone, payment_status),
    )
    return cursor.lastrowid


def get_all(conn: sqlite3.Connection, competition_id: int) -> list[Competitor]:
    rows = conn.execute(
        f"SELECT {_COLUMNS} FROM competitors WHERE competition_id = ? ORDER BY list_number",
        (competition_id,),
    ).fetchall()
    return [_row_to_competitor(row) for row in rows]


def get_by_sector(conn: sqlite3.Connection, competition_id: int, sector_name: str) -> list[Competitor]:
    rows = conn.execute(
        f"SELECT {_COLUMNS} FROM competitors "
        "WHERE competition_id = ? AND sector_name = ? ORDER BY station_number",
        (competition_id, sector_name),
    ).fetchall()
    return [_row_to_competitor(row) for row in rows]


def get_by_id(conn: sqlite3.Connection, competitor_id: int) -> Competitor | None:
    row = conn.execute(
        f"SELECT {_COLUMNS} FROM competitors WHERE id = ?",
        (competitor_id,),
    ).fetchone()
    return _row_to_competitor(row) if row else None


def update_station(conn: sqlite3.Connection, competitor_id: int, station_number: int | None, sector_name: str | None) -> None:
    conn.execute(
        "UPDATE competitors SET station_number = ?, sector_name = ? WHERE id = ?",
        (station_number, sector_name, competitor_id),
    )


def update_weight(conn: sqlite3.Connection, competitor_id: int, weight_grams: int) -> None:
    conn.execute(
        "UPDATE competitors SET weight_grams = ? WHERE id = ?",
        (weight_grams, competitor_id),
    )


def update_presence(conn: sqlite3.Connection, competitor_id: int, is_present: bool) -> None:
    conn.execute(
        "UPDATE competitors SET is_present = ? WHERE id = ?",
        (int(is_present), competitor_id),
    )


def update_rankings(
    conn: sqlite3.Connection,
    competitor_id: int,
    sector_place: int | None,
    sector_points: int | None,
    final_place: int | None,
) -> None:
    conn.execute(
        "UPDATE competitors SET sector_place = ?, sector_points = ?, final_place = ? WHERE id = ?",
        (sector_place, sector_points, final_place, competitor_id),
    )


def search_by_name(conn: sqlite3.Connection, competition_id: int, query: str) -> list[Competitor]:
    rows = conn.execute(
        f"SELECT {_COLUMNS} FROM competitors "
        "WHERE competition_id = ? AND full_name LIKE ? ORDER BY list_number",
        (competition_id, f"%{query}%"),
    ).fetchall()
    return [_row_to_competitor(row) for row in rows]


def set_all_present(conn: sqlite3.Connection, competition_id: int, limit: int | None = None) -> None:
    if limit is not None:
        conn.execute("UPDATE competitors SET is_present = 0 WHERE competition_id = ? AND station_number IS NULL", (competition_id,))
        locked_present = conn.execute(
            "SELECT COUNT(*) FROM competitors WHERE competition_id = ? AND is_present = 1",
            (competition_id,),
        ).fetchone()[0]
        remaining = max(0, limit - locked_present)
        if remaining > 0:
            conn.execute(
                "UPDATE competitors SET is_present = 1 WHERE id IN ("
                "SELECT id FROM competitors WHERE competition_id = ? AND is_present = 0 "
                "ORDER BY list_number LIMIT ?)",
                (competition_id, remaining),
            )
    else:
        conn.execute("UPDATE competitors SET is_present = 1 WHERE competition_id = ?", (competition_id,))


def update_details(conn: sqlite3.Connection, competitor_id: int, phone: str | None, payment_status: str) -> None:
    conn.execute(
        "UPDATE competitors SET phone = ?, payment_status = ? WHERE id = ?",
        (phone, payment_status, competitor_id),
    )


def delete(conn: sqlite3.Connection, competitor_id: int) -> None:
    conn.execute("DELETE FROM competitors WHERE id = ?", (competitor_id,))
