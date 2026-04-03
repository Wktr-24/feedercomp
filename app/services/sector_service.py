import sqlite3

from app.repositories import competitor_repo, venue_repo
from app.repositories import excluded_station_repo


class SectorService:
    def get_sector_for_station(self, conn: sqlite3.Connection, venue_id: int, station_number: int) -> str | None:
        return venue_repo.get_sector_for_station(conn, venue_id, station_number)

    def assign_station(self, conn: sqlite3.Connection, competitor_id: int, station_number: int, venue_id: int, competition_id: int | None = None):
        sector_name = venue_repo.get_sector_for_station(conn, venue_id, station_number)
        if sector_name is None:
            venue = venue_repo.get_by_id(conn, venue_id)
            total = venue.total_stations if venue else "?"
            raise ValueError(f"Stanowisko {station_number} nie istnieje (łowisko ma stanowiska 1-{total}).")
        if competition_id is not None and excluded_station_repo.is_excluded(conn, competition_id, station_number):
            raise ValueError(f"Stanowisko {station_number} jest wykluczone z losowania.")
        competitor_repo.update_station(conn, competitor_id, station_number, sector_name)
        conn.commit()

    def calculate_sector_places(self, conn: sqlite3.Connection, competition_id: int, sector_name: str):
        competitors = competitor_repo.get_by_sector(conn, competition_id, sector_name)
        total = len(competitors)
        if total == 0:
            return

        with_weight = [c for c in competitors if c.weight_grams > 0]
        zero_weight = [c for c in competitors if c.weight_grams == 0]

        with_weight.sort(key=lambda c: c.weight_grams, reverse=True)

        place = 0
        for i, c in enumerate(with_weight):
            if i == 0 or c.weight_grams != with_weight[i - 1].weight_grams:
                place = i + 1
            competitor_repo.update_rankings(conn, c.id, place, place, c.final_place)

        for c in zero_weight:
            competitor_repo.update_rankings(conn, c.id, total, total, c.final_place)
        conn.commit()

    def get_edge_stations(self, conn: sqlite3.Connection, venue_id: int, sector_name: str) -> list[int]:
        sectors = venue_repo.get_sectors(conn, venue_id)
        stations = sorted(s.station_number for s in sectors if s.sector_name == sector_name)
        if not stations:
            return []
        return [stations[0], stations[-1]]

    def propose_station_removals(
        self, conn: sqlite3.Connection, venue_id: int, competition_id: int, num_to_remove: int
    ) -> list[tuple[str, int]]:
        sector_names = venue_repo.get_sector_names(conn, venue_id)
        all_sectors = venue_repo.get_sectors(conn, venue_id)
        excluded = excluded_station_repo.get_excluded(conn, competition_id)
        excluded_numbers = {e["station_number"] for e in excluded}

        sector_stations: dict[str, list[int]] = {}
        for name in sector_names:
            sector_stations[name] = sorted(
                s.station_number for s in all_sectors if s.sector_name == name
            )

        sector_sizes: dict[str, int] = {}
        for name in sector_names:
            sector_sizes[name] = len([s for s in sector_stations[name] if s not in excluded_numbers])

        proposal: list[tuple[str, int]] = []
        proposed_numbers: set[int] = set()

        for _ in range(num_to_remove):
            max_size = max(sector_sizes.values())
            largest = [name for name in sector_names if sector_sizes[name] == max_size]
            picked_sector = largest[0]

            edges = self.get_edge_stations(conn, venue_id, picked_sector)
            chosen = None
            for station in edges:
                if station not in excluded_numbers and station not in proposed_numbers:
                    chosen = station
                    break

            if chosen is None:
                all_available = [
                    s for s in sector_stations[picked_sector]
                    if s not in excluded_numbers and s not in proposed_numbers
                ]
                if all_available:
                    chosen = all_available[0]

            if chosen is not None:
                proposal.append((picked_sector, chosen))
                proposed_numbers.add(chosen)
                sector_sizes[picked_sector] -= 1

        return proposal
