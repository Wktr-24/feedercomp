import sqlite3

from app.database import _FINAL_VENUE_NAME, _create_tables, _migrate_final_venue, init_db_with_connection
from app.repositories import competitor_repo
from app.services.ranking_service import RankingService
from app.services.sector_service import SectorService, load_venue_config

EXPECTED_SECTORS = {
    "A": [1, 2, 3, 4, 47, 48, 49, 50],
    "B": [5, 6, 7, 8, 43, 44, 45, 46],
    "C": [9, 10, 11, 12, 13, 39, 40, 41, 42],
    "D": [14, 15, 16, 17, 35, 36, 37, 38],
    "E": [18, 19, 20, 21, 31, 32, 33, 34],
    "F": [22, 23, 24, 25, 26, 27, 28, 29, 30],
}


def _venue_id(conn):
    row = conn.execute(
        "SELECT id FROM venues WHERE name = ?", (_FINAL_VENUE_NAME,)
    ).fetchone()
    return row["id"] if row else None


def _stations_per_sector(conn, venue_id):
    rows = conn.execute(
        "SELECT sector_name, station_number FROM venue_sectors WHERE venue_id = ? "
        "ORDER BY sector_name, station_number",
        (venue_id,),
    ).fetchall()
    result: dict[str, list[int]] = {}
    for row in rows:
        result.setdefault(row["sector_name"], []).append(row["station_number"])
    return result


class TestFinalVenueSeed:
    def test_seeded_on_fresh_init(self, db):
        venue_id = _venue_id(db)
        assert venue_id is not None

    def test_sector_layout_exact(self, db):
        assert _stations_per_sector(db, _venue_id(db)) == EXPECTED_SECTORS

    def test_sector_sizes(self, db):
        sizes = {s: len(st) for s, st in _stations_per_sector(db, _venue_id(db)).items()}
        assert sizes == {"A": 8, "B": 8, "C": 9, "D": 8, "E": 8, "F": 9}

    def test_total_stations_is_50(self, db):
        venue = db.execute(
            "SELECT total_stations FROM venues WHERE id = ?", (_venue_id(db),)
        ).fetchone()
        assert venue["total_stations"] == 50
        total = db.execute(
            "SELECT COUNT(*) FROM venue_sectors WHERE venue_id = ?", (_venue_id(db),)
        ).fetchone()[0]
        assert total == 50

    def test_boundary_stations(self, db):
        service = SectorService()
        venue_id = _venue_id(db)
        for station, expected in [(26, "F"), (13, "C"), (42, "C"), (38, "D"), (34, "E"), (47, "A")]:
            assert service.get_sector_for_station(db, venue_id, station) == expected

    def test_no_banks_no_balance_variants(self):
        cfg = load_venue_config(_FINAL_VENUE_NAME)
        assert cfg is not None
        assert "banks" not in cfg
        assert "balance_variants" not in cfg

    def test_old_stawy_untouched(self, db):
        old_id = db.execute(
            "SELECT id FROM venues WHERE name = 'Stawy Siedleckie'"
        ).fetchone()["id"]
        sectors = _stations_per_sector(db, old_id)
        assert len(sectors) == 5
        assert sectors["A"] == [1, 2, 3, 4, 5, 46, 47, 48, 49, 50]
        assert sectors["E"] == [21, 22, 23, 24, 25, 26, 27, 28, 29, 30]


class TestFinalVenueMigration:
    def test_idempotent_when_called_twice(self, db):
        _migrate_final_venue(db)
        assert _stations_per_sector(db, _venue_id(db)) == EXPECTED_SECTORS
        count = db.execute("SELECT COUNT(*) FROM venues WHERE name = ?", (_FINAL_VENUE_NAME,)).fetchone()[0]
        assert count == 1

    def test_seeds_when_missing_on_legacy_db(self, db):
        # Simulate a production DB from before this venue existed:
        # delete it (venue_sectors cascade) and re-run the migration.
        db.execute("DELETE FROM venues WHERE name = ?", (_FINAL_VENUE_NAME,))
        db.commit()
        assert _venue_id(db) is None

        _migrate_final_venue(db)

        assert _stations_per_sector(db, _venue_id(db)) == EXPECTED_SECTORS

    def test_short_circuits_when_venue_exists(self, db):
        # A venue row with this name (even without sectors) must block re-seeding —
        # never risk duplicating or overwriting a user-edited layout.
        db.execute("DELETE FROM venue_sectors WHERE venue_id = ?", (_venue_id(db),))
        db.commit()

        _migrate_final_venue(db)

        total = db.execute(
            "SELECT COUNT(*) FROM venue_sectors WHERE venue_id = ?", (_venue_id(db),)
        ).fetchone()[0]
        assert total == 0

    def test_no_op_on_bare_db_without_any_venues(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        _create_tables(conn)

        _migrate_final_venue(conn)

        # Migration inserts the final venue even on an empty DB — by design:
        # its guard is name-presence, not venues-count.
        assert _venue_id(conn) is not None
        conn.close()

    def test_init_db_runs_migration_on_legacy_db(self):
        # Full legacy path: DB that has only the two old venues (as production
        # did before v0.4.0), then a normal app start.
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        _create_tables(conn)
        conn.execute("INSERT INTO venues (name, total_stations) VALUES ('Stawy Siedleckie', 50)")
        conn.execute("INSERT INTO venues (name, total_stations) VALUES ('Lasomin', 34)")
        conn.commit()

        init_db_with_connection(conn)

        assert _stations_per_sector(conn, _venue_id(conn)) == EXPECTED_SECTORS
        conn.close()


class TestSixSectorRankingSmoke:
    """Guard the 'sector-count agnostic' claim with a real end-to-end assertion:
    6 sectors of 2 competitors each -> the six sector winners take final places 1-6."""

    def test_six_sector_final_classification(self, db):
        venue_id = _venue_id(db)
        cursor = db.execute(
            "INSERT INTO competitions (venue_id, date, name, max_competitors, winner_places) "
            "VALUES (?, '2026-09-05', 'Final smoke', 50, 3)",
            (venue_id,),
        )
        comp_id = cursor.lastrowid
        db.commit()

        # One competitor on each bank half of every sector; sector winners get
        # strictly descending weights A>B>C>D>E>F so the final order is fixed.
        setup = [
            ("A", 1, "Winner A", 6000), ("A", 47, "Loser A", 600),
            ("B", 5, "Winner B", 5000), ("B", 43, "Loser B", 500),
            ("C", 9, "Winner C", 4000), ("C", 39, "Loser C", 400),
            ("D", 14, "Winner D", 3000), ("D", 35, "Loser D", 300),
            ("E", 18, "Winner E", 2000), ("E", 31, "Loser E", 200),
            ("F", 22, "Winner F", 1000), ("F", 26, "Loser F", 100),
        ]
        for i, (sector, station, name, weight) in enumerate(setup, start=1):
            cid = competitor_repo.add(db, comp_id, i, name)
            competitor_repo.update_station(db, cid, station, sector)
            competitor_repo.update_weight(db, cid, weight)
        db.commit()

        RankingService(SectorService()).calculate_all(db, comp_id, venue_id)

        by_name = {c.full_name: c for c in competitor_repo.get_all(db, comp_id)}
        for expected_place, name in enumerate(
            ["Winner A", "Winner B", "Winner C", "Winner D", "Winner E", "Winner F"],
            start=1,
        ):
            assert by_name[name].final_place == expected_place, (
                f"{name}: expected final_place {expected_place}, got {by_name[name].final_place}"
            )
        for name in ["Loser A", "Loser B", "Loser C", "Loser D", "Loser E", "Loser F"]:
            assert by_name[name].sector_points == 2
        assert by_name["Loser A"].final_place == 7
        assert by_name["Loser F"].final_place == 12
