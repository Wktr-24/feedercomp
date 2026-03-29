import sqlite3

from app.repositories import competitor_repo, venue_repo


class SectorService:
    def get_sector_for_station(self, conn: sqlite3.Connection, venue_id: int, station_number: int) -> str | None:
        return venue_repo.get_sector_for_station(conn, venue_id, station_number)

    def assign_station(self, conn: sqlite3.Connection, competitor_id: int, station_number: int, venue_id: int):
        sector_name = venue_repo.get_sector_for_station(conn, venue_id, station_number)
        competitor_repo.update_station(conn, competitor_id, station_number, sector_name)

    def calculate_sector_places(self, conn: sqlite3.Connection, competition_id: int, sector_name: str):
        competitors = competitor_repo.get_by_sector(conn, competition_id, sector_name)
        total = len(competitors)
        if total == 0:
            return

        with_weight = [c for c in competitors if c.weight_grams > 0]
        zero_weight = [c for c in competitors if c.weight_grams == 0]

        with_weight.sort(key=lambda c: c.weight_grams, reverse=True)

        for place, c in enumerate(with_weight, start=1):
            competitor_repo.update_rankings(conn, c.id, place, place, c.final_place)

        for c in zero_weight:
            competitor_repo.update_rankings(conn, c.id, total, total, c.final_place)
