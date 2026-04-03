import pytest

from app.repositories import excluded_station_repo
from app.services.sector_service import SectorService


@pytest.fixture
def venue_id(db):
    return db.execute("SELECT id FROM venues WHERE name = 'Stawy Siedleckie'").fetchone()["id"]


@pytest.fixture
def competition_id(db, venue_id):
    cursor = db.execute(
        "INSERT INTO competitions (venue_id, date, name) VALUES (?, '2026-04-01', 'Test')",
        (venue_id,),
    )
    db.commit()
    return cursor.lastrowid


class TestGetEdgeStations:
    def setup_method(self):
        self.service = SectorService()

    def test_split_sector(self, db, venue_id):
        edges = self.service.get_edge_stations(db, venue_id, "A")
        assert edges == [1, 50]

    def test_contiguous_sector(self, db, venue_id):
        edges = self.service.get_edge_stations(db, venue_id, "E")
        assert edges == [21, 30]

    def test_sector_b(self, db, venue_id):
        edges = self.service.get_edge_stations(db, venue_id, "B")
        assert edges == [6, 45]

    def test_sector_c(self, db, venue_id):
        edges = self.service.get_edge_stations(db, venue_id, "C")
        assert edges == [11, 40]

    def test_sector_d(self, db, venue_id):
        edges = self.service.get_edge_stations(db, venue_id, "D")
        assert edges == [16, 35]


class TestProposeRemovals:
    def setup_method(self):
        self.service = SectorService()

    def test_distributes_evenly(self, db, venue_id, competition_id):
        proposals = self.service.propose_station_removals(db, venue_id, competition_id, 3)
        assert len(proposals) == 3
        sectors_hit = [s for s, _ in proposals]
        assert len(set(sectors_hit)) == 3

    def test_targets_largest_first(self, db, venue_id, competition_id):
        excluded_station_repo.add_excluded(db, competition_id, venue_id, 1, "A")
        excluded_station_repo.add_excluded(db, competition_id, venue_id, 50, "A")

        proposals = self.service.propose_station_removals(db, venue_id, competition_id, 1)
        assert len(proposals) == 1
        sector, _ = proposals[0]
        assert sector != "A"

    def test_returns_correct_count(self, db, venue_id, competition_id):
        proposals = self.service.propose_station_removals(db, venue_id, competition_id, 5)
        assert len(proposals) == 5


class TestAssignStationRejectsExcluded:
    def setup_method(self):
        self.service = SectorService()

    def test_raises_for_excluded(self, db, venue_id, competition_id):
        competitor_id = db.execute(
            "INSERT INTO competitors (competition_id, list_number, full_name) VALUES (?, 1, 'Jan Kowalski')",
            (competition_id,),
        ).lastrowid
        db.commit()

        excluded_station_repo.add_excluded(db, competition_id, venue_id, 5, "A")

        with pytest.raises(ValueError, match="Stanowisko 5 jest wykluczone"):
            self.service.assign_station(db, competitor_id, 5, venue_id, competition_id)

    def test_allows_non_excluded(self, db, venue_id, competition_id):
        competitor_id = db.execute(
            "INSERT INTO competitors (competition_id, list_number, full_name) VALUES (?, 1, 'Jan Kowalski')",
            (competition_id,),
        ).lastrowid
        db.commit()

        self.service.assign_station(db, competitor_id, 1, venue_id, competition_id)

    def test_allows_without_competition_id(self, db, venue_id, competition_id):
        competitor_id = db.execute(
            "INSERT INTO competitors (competition_id, list_number, full_name) VALUES (?, 1, 'Jan Kowalski')",
            (competition_id,),
        ).lastrowid
        db.commit()

        excluded_station_repo.add_excluded(db, competition_id, venue_id, 5, "A")
        self.service.assign_station(db, competitor_id, 5, venue_id)


class TestExcludedRepoCrud:
    def test_add_and_check(self, db, venue_id, competition_id):
        assert not excluded_station_repo.is_excluded(db, competition_id, 5)
        excluded_station_repo.add_excluded(db, competition_id, venue_id, 5, "A")
        assert excluded_station_repo.is_excluded(db, competition_id, 5)

    def test_get_excluded(self, db, venue_id, competition_id):
        excluded_station_repo.add_excluded(db, competition_id, venue_id, 5, "A")
        excluded_station_repo.add_excluded(db, competition_id, venue_id, 46, "A")
        result = excluded_station_repo.get_excluded(db, competition_id)
        assert len(result) == 2
        assert result[0]["station_number"] == 5
        assert result[0]["sector_name"] == "A"

    def test_remove(self, db, venue_id, competition_id):
        excluded_station_repo.add_excluded(db, competition_id, venue_id, 5, "A")
        excluded_station_repo.remove_excluded(db, competition_id, 5)
        assert not excluded_station_repo.is_excluded(db, competition_id, 5)

    def test_clear(self, db, venue_id, competition_id):
        excluded_station_repo.add_excluded(db, competition_id, venue_id, 5, "A")
        excluded_station_repo.add_excluded(db, competition_id, venue_id, 46, "A")
        excluded_station_repo.clear_excluded(db, competition_id)
        assert len(excluded_station_repo.get_excluded(db, competition_id)) == 0
