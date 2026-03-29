import json
import sqlite3
from pathlib import Path

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
    created_at TEXT DEFAULT (datetime('now'))
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
"""

_SEED_DATA_PATH = Path(__file__).resolve().parent.parent / "seed_data" / "venues.json"


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

    with open(_SEED_DATA_PATH) as f:
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


def init_db_with_connection(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA foreign_keys = ON")
    _create_tables(conn)
    _seed_default_venues(conn)


def init_db(db_path: Path) -> None:
    conn = get_connection(db_path)
    try:
        init_db_with_connection(conn)
    finally:
        conn.close()
