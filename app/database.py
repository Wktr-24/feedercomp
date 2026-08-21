import json
import sqlite3
from pathlib import Path

from app.config import get_bundle_dir

_SCHEMA = """
CREATE TABLE IF NOT EXISTS venues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    total_stations INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS venue_sectors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    venue_id INTEGER NOT NULL REFERENCES venues(id) ON DELETE CASCADE,
    sector_name TEXT NOT NULL,
    station_number INTEGER NOT NULL,
    UNIQUE(venue_id, station_number)
);

CREATE TABLE IF NOT EXISTS competitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    venue_id INTEGER NOT NULL REFERENCES venues(id),
    date TEXT NOT NULL,
    name TEXT,
    max_competitors INTEGER DEFAULT 50,
    winner_places INTEGER DEFAULT 3,
    created_at TEXT DEFAULT (datetime('now')),
    linked_competition_id INTEGER REFERENCES competitions(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS competitors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    competition_id INTEGER NOT NULL REFERENCES competitions(id) ON DELETE CASCADE,
    list_number INTEGER NOT NULL,
    full_name TEXT NOT NULL,
    phone TEXT,
    payment_status TEXT DEFAULT 'unpaid' CHECK(payment_status IN ('paid', 'on_site', 'unpaid')),
    is_present INTEGER DEFAULT 0,
    station_number INTEGER,
    sector_name TEXT,
    weight_grams INTEGER DEFAULT 0,
    sector_place INTEGER,
    sector_points INTEGER,
    final_place INTEGER,
    UNIQUE(competition_id, list_number),
    UNIQUE(competition_id, station_number)
);

CREATE TABLE IF NOT EXISTS excluded_stations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    competition_id INTEGER NOT NULL REFERENCES competitions(id) ON DELETE CASCADE,
    venue_id INTEGER NOT NULL REFERENCES venues(id),
    station_number INTEGER NOT NULL,
    sector_name TEXT NOT NULL,
    UNIQUE(competition_id, station_number)
);

CREATE TABLE IF NOT EXISTS competition_sector_overrides (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    competition_id INTEGER NOT NULL REFERENCES competitions(id) ON DELETE CASCADE,
    station_number INTEGER NOT NULL,
    sector_name TEXT NOT NULL,
    UNIQUE(competition_id, station_number)
);
"""

_SEED_DATA_PATH = get_bundle_dir() / "seed_data" / "venues.json"

# Single point of change should the final venue ever be renamed
# (also referenced by tests/test_final_venue_seed.py).
_FINAL_VENUE_NAME = "Stawy Siedleckie — Finał"


def get_connection(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _create_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)


def _seed_default_venues(conn: sqlite3.Connection) -> None:
    count = conn.execute("SELECT COUNT(*) FROM venues").fetchone()[0]
    if count > 0:
        return

    with open(_SEED_DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)

    for venue_data in data["venues"]:
        cursor = conn.execute(
            "INSERT INTO venues (name, total_stations) VALUES (?, ?)",
            (venue_data["name"], venue_data["total_stations"]),
        )
        venue_id = cursor.lastrowid
        for sector_name, stations in venue_data.get("sectors", {}).items():
            for station in stations:
                conn.execute(
                    "INSERT INTO venue_sectors (venue_id, sector_name, station_number) VALUES (?, ?, ?)",
                    (venue_id, sector_name, station),
                )
    conn.commit()


def _migrate_lasomin_sectors(conn: sqlite3.Connection) -> None:
    # Migration: 2026-05 Lasomin sector seed.
    # Lasomin shipped in earlier versions with empty sectors; this fills them
    # in for production DBs that were created before the seed JSON was updated.
    # Idempotent — short-circuits when Lasomin already has any sectors.
    row = conn.execute("SELECT id FROM venues WHERE name = 'Lasomin'").fetchone()
    if not row:
        return
    venue_id = row["id"]
    has_sectors = conn.execute(
        "SELECT COUNT(*) FROM venue_sectors WHERE venue_id = ?", (venue_id,)
    ).fetchone()[0]
    if has_sectors > 0:
        return
    with open(_SEED_DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)
    lasomin = next((v for v in data["venues"] if v["name"] == "Lasomin"), None)
    if not lasomin:
        return
    for sector_name, stations in lasomin.get("sectors", {}).items():
        for station in stations:
            conn.execute(
                "INSERT INTO venue_sectors (venue_id, sector_name, station_number) VALUES (?, ?, ?)",
                (venue_id, sector_name, station),
            )
    conn.commit()


def _migrate_final_venue(conn: sqlite3.Connection) -> None:
    # Migration: 2026-08 six-sector final venue ("Stawy Siedleckie — Finał").
    # Production DBs created before this venue existed in the seed JSON never
    # re-read it (_seed_default_venues short-circuits when venues exist), so
    # insert the venue + its sectors here. Idempotent — short-circuits when
    # a venue with this name is already present.
    row = conn.execute(
        "SELECT id FROM venues WHERE name = ?", (_FINAL_VENUE_NAME,)
    ).fetchone()
    if row:
        return
    with open(_SEED_DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)
    venue_data = next(
        (v for v in data["venues"] if v["name"] == _FINAL_VENUE_NAME), None
    )
    if not venue_data:
        return
    cursor = conn.execute(
        "INSERT INTO venues (name, total_stations) VALUES (?, ?)",
        (venue_data["name"], venue_data["total_stations"]),
    )
    venue_id = cursor.lastrowid
    for sector_name, stations in venue_data.get("sectors", {}).items():
        for station in stations:
            conn.execute(
                "INSERT INTO venue_sectors (venue_id, sector_name, station_number) VALUES (?, ?, ?)",
                (venue_id, sector_name, station),
            )
    conn.commit()


def _migrate_linked_competition_column(conn: sqlite3.Connection) -> None:
    # Migration: 2026-08 two-day final — linked_competition_id column.
    # A day-2 competition points at its day-1 via this column; ON DELETE SET
    # NULL so deleting day-1 gracefully demotes day-2 to a regular
    # competition instead of failing the FK check. CREATE TABLE IF NOT
    # EXISTS never alters existing tables, so production DBs need this
    # ALTER. Idempotent — short-circuits when the column already exists.
    cols = {row[1] for row in conn.execute("PRAGMA table_info(competitions)")}
    if "linked_competition_id" in cols:
        return
    conn.execute(
        "ALTER TABLE competitions ADD COLUMN linked_competition_id INTEGER "
        "REFERENCES competitions(id) ON DELETE SET NULL"
    )
    conn.commit()


def init_db_with_connection(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA foreign_keys = ON")
    _create_tables(conn)
    _seed_default_venues(conn)
    _migrate_lasomin_sectors(conn)
    _migrate_final_venue(conn)
    _migrate_linked_competition_column(conn)


def init_db(db_path: Path) -> None:
    conn = get_connection(db_path)
    try:
        init_db_with_connection(conn)
    finally:
        conn.close()
