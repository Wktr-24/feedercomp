import sqlite3

from app.repositories import competitor_repo, venue_repo
from app.services.sector_service import SectorService


class RankingService:
    def __init__(self, sector_service: SectorService):
        self.sector_service = sector_service

    def calculate_all(self, conn: sqlite3.Connection, competition_id: int, venue_id: int):
        sector_names = venue_repo.get_sector_names(conn, venue_id)
        for sector_name in sector_names:
            self.sector_service.calculate_sector_places(conn, competition_id, sector_name)
        self.calculate_final_classification(conn, competition_id)

    def calculate_final_classification(self, conn: sqlite3.Connection, competition_id: int):
        all_competitors = competitor_repo.get_all(conn, competition_id)

        with_weight = [c for c in all_competitors if c.weight_grams > 0 and c.sector_points is not None]
        zero_weight = [c for c in all_competitors if c.weight_grams == 0 or c.sector_points is None]

        with_weight.sort(key=lambda c: (c.sector_points, -c.weight_grams))

        for place, c in enumerate(with_weight, start=1):
            competitor_repo.update_rankings(conn, c.id, c.sector_place, c.sector_points, place)

        for c in zero_weight:
            competitor_repo.update_rankings(conn, c.id, c.sector_place, c.sector_points, None)

    def get_winners(self, conn: sqlite3.Connection, competition_id: int, winner_places: int) -> list:
        all_competitors = competitor_repo.get_all(conn, competition_id)
        winners = [c for c in all_competitors if c.sector_points is not None and c.sector_points <= winner_places]
        winners.sort(key=lambda c: (c.final_place is None, c.final_place or 0))
        return winners
