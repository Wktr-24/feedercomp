from app.services.sector_service import load_venue_config
from app.ui.balance_sectors_dialog import split_stations_to_banks


class TestSplitStationsToBanksLasomin:
    """Lasomin has explicit `banks` config — top is 18-34 (L→R),
    bottom is 17-1 (L→R, descending because the pond wraps on the right)."""

    def setup_method(self):
        cfg = load_venue_config("Lasomin")
        assert cfg is not None
        self.banks = cfg["banks"]
        self.total = 34

    def test_sector_d_top_bottom(self):
        # D = [14, 15, 16, 17, 18, 19, 20, 21, 22]
        top, bot = split_stations_to_banks(
            [14, 15, 16, 17, 18, 19, 20, 21, 22], self.banks, self.total,
        )
        assert top == [18, 19, 20, 21, 22]
        assert bot == [17, 16, 15, 14]

    def test_sector_c_top_bottom(self):
        # C = [9, 10, 11, 12, 13, 23, 24, 25, 26]
        top, bot = split_stations_to_banks(
            [9, 10, 11, 12, 13, 23, 24, 25, 26], self.banks, self.total,
        )
        assert top == [23, 24, 25, 26]
        assert bot == [13, 12, 11, 10, 9]

    def test_sector_b_top_bottom(self):
        # B = [5, 6, 7, 8, 27, 28, 29, 30]
        top, bot = split_stations_to_banks(
            [5, 6, 7, 8, 27, 28, 29, 30], self.banks, self.total,
        )
        assert top == [27, 28, 29, 30]
        assert bot == [8, 7, 6, 5]

    def test_sector_a_top_bottom(self):
        # A = [1, 2, 3, 4, 31, 32, 33, 34]
        top, bot = split_stations_to_banks(
            [1, 2, 3, 4, 31, 32, 33, 34], self.banks, self.total,
        )
        assert top == [31, 32, 33, 34]
        assert bot == [4, 3, 2, 1]

    def test_lasomin_total_per_sector_matches_size(self):
        # Sanity: top + bottom for every sector covers all stations exactly.
        for stations in [
            [14, 15, 16, 17, 18, 19, 20, 21, 22],
            [9, 10, 11, 12, 13, 23, 24, 25, 26],
            [5, 6, 7, 8, 27, 28, 29, 30],
            [1, 2, 3, 4, 31, 32, 33, 34],
        ]:
            top, bot = split_stations_to_banks(stations, self.banks, self.total)
            assert sorted(top + bot) == sorted(stations)

    def test_excluded_station_18_drops_from_top(self):
        # If station 18 isn't in the sector's stations list (e.g. removed),
        # the helper just doesn't render it.
        top, bot = split_stations_to_banks(
            [14, 15, 16, 17, 19, 20, 21, 22], self.banks, self.total,
        )
        assert top == [19, 20, 21, 22]
        assert bot == [17, 16, 15, 14]


class TestSplitStationsToBanksStawyFallback:
    """Stawy has no `banks` config → falls back to the half-split heuristic.
    Behavior must match the dialog rendering before this refactor."""

    def test_sector_a_split(self):
        # A = [1..5, 46..50], total_stations = 50, half = 25
        top, bot = split_stations_to_banks(
            [1, 2, 3, 4, 5, 46, 47, 48, 49, 50], None, 50,
        )
        assert top == [5, 4, 3, 2, 1]
        assert bot == [46, 47, 48, 49, 50]

    def test_sector_e_contiguous(self):
        # E = [21..30], all on different sides of the half boundary
        top, bot = split_stations_to_banks(
            [21, 22, 23, 24, 25, 26, 27, 28, 29, 30], None, 50,
        )
        assert top == [25, 24, 23, 22, 21]
        assert bot == [26, 27, 28, 29, 30]

    def test_sector_c_split(self):
        # C = [11..15, 36..40]
        top, bot = split_stations_to_banks(
            [11, 12, 13, 14, 15, 36, 37, 38, 39, 40], None, 50,
        )
        assert top == [15, 14, 13, 12, 11]
        assert bot == [36, 37, 38, 39, 40]

    def test_total_per_sector_matches_size(self):
        for stations in [
            [1, 2, 3, 4, 5, 46, 47, 48, 49, 50],
            [21, 22, 23, 24, 25, 26, 27, 28, 29, 30],
            [11, 12, 13, 14, 15, 36, 37, 38, 39, 40],
        ]:
            top, bot = split_stations_to_banks(stations, None, 50)
            assert sorted(top + bot) == sorted(stations)
