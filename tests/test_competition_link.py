import sqlite3

from app.database import _migrate_linked_competition_column
from app.repositories import competition_repo


def _columns(conn) -> set[str]:
    return {row[1] for row in conn.execute("PRAGMA table_info(competitions)")}


def _stawy_venue_id(db) -> int:
    return db.execute("SELECT id FROM venues WHERE name = 'Stawy Siedleckie'").fetchone()["id"]


# Pre-v0.4.0 shape of the competitions table, for legacy-migration tests.
_LEGACY_DDL = """
CREATE TABLE venues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    total_stations INTEGER NOT NULL
);
CREATE TABLE competitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    venue_id INTEGER NOT NULL REFERENCES venues(id),
    date TEXT NOT NULL,
    name TEXT,
    max_competitors INTEGER DEFAULT 50,
    winner_places INTEGER DEFAULT 3,
    created_at TEXT DEFAULT (datetime('now'))
);
"""


class TestSchemaAndMigration:
    def test_fresh_schema_has_column(self, db):
        assert "linked_competition_id" in _columns(db)

    def test_legacy_db_gets_column_via_migration(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(_LEGACY_DDL)
        assert "linked_competition_id" not in _columns(conn)

        _migrate_linked_competition_column(conn)

        assert "linked_competition_id" in _columns(conn)
        conn.close()

    def test_migration_idempotent(self, db):
        _migrate_linked_competition_column(db)
        _migrate_linked_competition_column(db)
        # Exactly one column with this name (a duplicate ALTER would raise anyway).
        names = [row[1] for row in db.execute("PRAGMA table_info(competitions)")]
        assert names.count("linked_competition_id") == 1


class TestRepoLinkRoundtrip:
    def test_create_without_link_defaults_to_none(self, db):
        comp_id = competition_repo.create(db, _stawy_venue_id(db), "2026-09-05", "Dzień 1")
        db.commit()
        comp = competition_repo.get_by_id(db, comp_id)
        assert comp.linked_competition_id is None

    def test_create_with_link_and_get_by_id(self, db):
        venue_id = _stawy_venue_id(db)
        day1 = competition_repo.create(db, venue_id, "2026-09-05", "Dzień 1")
        day2 = competition_repo.create(
            db, venue_id, "2026-09-06", "Dzień 2", linked_competition_id=day1,
        )
        db.commit()
        assert competition_repo.get_by_id(db, day2).linked_competition_id == day1

    def test_get_all_populates_link(self, db):
        venue_id = _stawy_venue_id(db)
        day1 = competition_repo.create(db, venue_id, "2026-09-05")
        day2 = competition_repo.create(db, venue_id, "2026-09-06", linked_competition_id=day1)
        db.commit()
        by_id = {c.id: c for c in competition_repo.get_all(db)}
        assert by_id[day2].linked_competition_id == day1
        assert by_id[day1].linked_competition_id is None

    def test_get_day2_of_found(self, db):
        venue_id = _stawy_venue_id(db)
        day1 = competition_repo.create(db, venue_id, "2026-09-05")
        day2 = competition_repo.create(db, venue_id, "2026-09-06", linked_competition_id=day1)
        db.commit()
        found = competition_repo.get_day2_of(db, day1)
        assert found is not None
        assert found.id == day2

    def test_get_day2_of_none_for_unlinked(self, db):
        comp_id = competition_repo.create(db, _stawy_venue_id(db), "2026-09-05")
        db.commit()
        assert competition_repo.get_day2_of(db, comp_id) is None


class TestOnDeleteSetNull:
    def test_deleting_day1_demotes_day2_to_regular(self, db):
        venue_id = _stawy_venue_id(db)
        day1 = competition_repo.create(db, venue_id, "2026-09-05")
        day2 = competition_repo.create(db, venue_id, "2026-09-06", linked_competition_id=day1)
        db.commit()

        # Must not raise FOREIGN KEY constraint failed (foreign_keys is ON
        # in the fixture) — ON DELETE SET NULL handles the dangling link.
        competition_repo.delete(db, day1)
        db.commit()

        day2_after = competition_repo.get_by_id(db, day2)
        assert day2_after is not None
        assert day2_after.linked_competition_id is None
