import sqlite3

import pytest

from app.database import _create_tables, _migrate_lasomin_sectors, init_db_with_connection


@pytest.fixture
def lasomin_venue_id(db):
    return db.execute("SELECT id FROM venues WHERE name = 'Lasomin'").fetchone()["id"]


def _stations_per_sector(conn, venue_id):
    rows = conn.execute(
        "SELECT sector_name, COUNT(*) AS n FROM venue_sectors WHERE venue_id = ? GROUP BY sector_name",
        (venue_id,),
    ).fetchall()
    return {row["sector_name"]: row["n"] for row in rows}


class TestLasominSeed:
    def test_lasomin_sectors_seeded_correctly(self, db, lasomin_venue_id):
        sizes = _stations_per_sector(db, lasomin_venue_id)
        assert sizes == {"A": 8, "B": 8, "C": 9, "D": 9}

    def test_lasomin_total_stations_is_34(self, db, lasomin_venue_id):
        total = db.execute(
            "SELECT COUNT(*) FROM venue_sectors WHERE venue_id = ?",
            (lasomin_venue_id,),
        ).fetchone()[0]
        assert total == 34

    def test_lasomin_station_13_is_in_sector_C_by_default(self, db, lasomin_venue_id):
        sector = db.execute(
            "SELECT sector_name FROM venue_sectors WHERE venue_id = ? AND station_number = 13",
            (lasomin_venue_id,),
        ).fetchone()["sector_name"]
        assert sector == "C"

    def test_lasomin_station_22_is_in_sector_D(self, db, lasomin_venue_id):
        sector = db.execute(
            "SELECT sector_name FROM venue_sectors WHERE venue_id = ? AND station_number = 22",
            (lasomin_venue_id,),
        ).fetchone()["sector_name"]
        assert sector == "D"


class TestLasominBanksConfig:
    """Verify the per-venue bank layout in seed_data/venues.json matches the
    physical pond geometry described in wymagania-lasomin.md §2.1 and IMG_1150.jpg."""

    def setup_method(self):
        from app.services.sector_service import load_venue_config
        self.cfg = load_venue_config("Lasomin")

    def test_banks_field_present(self):
        assert self.cfg is not None
        assert "banks" in self.cfg

    def test_top_bank_is_stations_18_to_34_left_to_right(self):
        assert self.cfg["banks"]["top"] == list(range(18, 35))

    def test_bottom_bank_is_stations_17_to_1_left_to_right(self):
        # Pond wraps on the right side: station 17 is the leftmost on the bottom,
        # station 1 is the rightmost (geometrically adjacent to station 34 on top).
        assert self.cfg["banks"]["bottom"] == list(range(17, 0, -1))

    def test_banks_partition_all_34_stations_uniquely(self):
        top = set(self.cfg["banks"]["top"])
        bot = set(self.cfg["banks"]["bottom"])
        assert top.isdisjoint(bot)
        assert top | bot == set(range(1, 35))

    def test_stawy_has_no_banks_config(self):
        from app.services.sector_service import load_venue_config
        cfg = load_venue_config("Stawy Siedleckie")
        assert cfg is not None
        assert "banks" not in cfg


class TestLasominMigration:
    def test_idempotent_when_called_twice(self, db, lasomin_venue_id):
        _migrate_lasomin_sectors(db)
        sizes = _stations_per_sector(db, lasomin_venue_id)
        assert sizes == {"A": 8, "B": 8, "C": 9, "D": 9}

    def test_seeds_empty_lasomin_on_legacy_db(self):
        # Simulate a production DB created before the JSON had Lasomin sectors:
        # schema is in place and Lasomin venue row exists, but venue_sectors is empty.
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        _create_tables(conn)
        cursor = conn.execute(
            "INSERT INTO venues (name, total_stations) VALUES ('Lasomin', 34)"
        )
        venue_id = cursor.lastrowid
        conn.commit()
        assert _stations_per_sector(conn, venue_id) == {}

        _migrate_lasomin_sectors(conn)

        assert _stations_per_sector(conn, venue_id) == {"A": 8, "B": 8, "C": 9, "D": 9}
        conn.close()

    def test_skips_when_lasomin_already_has_any_sectors(self):
        # If a single sector row exists, migration must short-circuit
        # (does not append the remaining 33 stations).
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        _create_tables(conn)
        cursor = conn.execute(
            "INSERT INTO venues (name, total_stations) VALUES ('Lasomin', 34)"
        )
        venue_id = cursor.lastrowid
        conn.execute(
            "INSERT INTO venue_sectors (venue_id, sector_name, station_number) VALUES (?, 'A', 1)",
            (venue_id,),
        )
        conn.commit()

        _migrate_lasomin_sectors(conn)

        total = conn.execute(
            "SELECT COUNT(*) FROM venue_sectors WHERE venue_id = ?", (venue_id,)
        ).fetchone()[0]
        assert total == 1
        conn.close()

    def test_no_op_when_lasomin_venue_missing(self):
        # Schema in place, no venues at all — migration should be a no-op, not raise.
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        _create_tables(conn)
        _migrate_lasomin_sectors(conn)
        venue_count = conn.execute("SELECT COUNT(*) FROM venues").fetchone()[0]
        assert venue_count == 0
        conn.close()

    def test_init_db_runs_migration(self):
        # Smoke: a fully fresh init_db_with_connection on a blank DB ends with
        # Lasomin populated, regardless of order between seed and migration.
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        init_db_with_connection(conn)
        venue_id = conn.execute(
            "SELECT id FROM venues WHERE name = 'Lasomin'"
        ).fetchone()["id"]
        assert _stations_per_sector(conn, venue_id) == {"A": 8, "B": 8, "C": 9, "D": 9}
        conn.close()


class TestCompetitionSectorOverridesTable:
    def test_table_exists_and_is_empty(self, db):
        rows = db.execute("SELECT * FROM competition_sector_overrides").fetchall()
        assert rows == []

    def test_unique_constraint_per_competition_and_station(self, db):
        # Set up a competition row to satisfy the FK.
        venue_id = db.execute(
            "SELECT id FROM venues WHERE name = 'Lasomin'"
        ).fetchone()["id"]
        cursor = db.execute(
            "INSERT INTO competitions (venue_id, date, name) VALUES (?, '2026-06-01', 'Test')",
            (venue_id,),
        )
        comp_id = cursor.lastrowid
        db.execute(
            "INSERT INTO competition_sector_overrides (competition_id, station_number, sector_name) VALUES (?, 13, 'D')",
            (comp_id,),
        )
        db.commit()
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO competition_sector_overrides (competition_id, station_number, sector_name) VALUES (?, 13, 'C')",
                (comp_id,),
            )
            db.commit()

    def test_foreign_key_cascade_on_competition_delete(self, db):
        venue_id = db.execute(
            "SELECT id FROM venues WHERE name = 'Lasomin'"
        ).fetchone()["id"]
        cursor = db.execute(
            "INSERT INTO competitions (venue_id, date, name) VALUES (?, '2026-06-01', 'Test')",
            (venue_id,),
        )
        comp_id = cursor.lastrowid
        db.execute(
            "INSERT INTO competition_sector_overrides (competition_id, station_number, sector_name) VALUES (?, 13, 'D')",
            (comp_id,),
        )
        db.commit()

        db.execute("DELETE FROM competitions WHERE id = ?", (comp_id,))
        db.commit()

        rows = db.execute(
            "SELECT * FROM competition_sector_overrides WHERE competition_id = ?", (comp_id,)
        ).fetchall()
        assert rows == []
