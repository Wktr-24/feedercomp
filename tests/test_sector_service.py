from app.services.sector_service import SectorService


class TestGetSectorForStation:
    def setup_method(self):
        self.service = SectorService()

    def test_station_1_maps_to_sector_a(self, db):
        venue_id = db.execute("SELECT id FROM venues WHERE name = 'Stawy Siedleckie'").fetchone()["id"]
        assert self.service.get_sector_for_station(db, venue_id, 1) == "A"

    def test_station_45_maps_to_sector_b(self, db):
        venue_id = db.execute("SELECT id FROM venues WHERE name = 'Stawy Siedleckie'").fetchone()["id"]
        assert self.service.get_sector_for_station(db, venue_id, 45) == "B"

    def test_station_25_maps_to_sector_e(self, db):
        venue_id = db.execute("SELECT id FROM venues WHERE name = 'Stawy Siedleckie'").fetchone()["id"]
        assert self.service.get_sector_for_station(db, venue_id, 25) == "E"

    def test_station_999_returns_none(self, db):
        venue_id = db.execute("SELECT id FROM venues WHERE name = 'Stawy Siedleckie'").fetchone()["id"]
        assert self.service.get_sector_for_station(db, venue_id, 999) is None
