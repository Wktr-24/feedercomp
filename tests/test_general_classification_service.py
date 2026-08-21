from app.repositories import competition_repo, competitor_repo
from app.services.general_classification_service import calculate, resolve_linked_pair
from app.services.ranking_service import RankingService
from app.services.sector_service import SectorService


def _setup_day(db, comp_date, name, sector_data, venue_name="Stawy Siedleckie", linked_to=None):
    """Sibling of test_ranking_service._setup_competition, parameterized for
    two-day scenarios. sector_data: {sector: [(station, name, weight), ...]}.
    Runs the full per-day ranking so sector_points/final_place are real."""
    venue_id = db.execute(
        "SELECT id FROM venues WHERE name = ?", (venue_name,)
    ).fetchone()["id"]
    cursor = db.execute(
        "INSERT INTO competitions (venue_id, date, name, linked_competition_id) "
        "VALUES (?, ?, ?, ?)",
        (venue_id, comp_date, name, linked_to),
    )
    comp_id = cursor.lastrowid
    db.commit()

    list_number = 1
    for sector, entries in sector_data.items():
        for station, full_name, weight in entries:
            cid = competitor_repo.add(db, comp_id, list_number, full_name)
            competitor_repo.update_station(db, cid, station, sector)
            competitor_repo.update_weight(db, cid, weight)
            list_number += 1
    db.commit()

    RankingService(SectorService()).calculate_all(db, comp_id, venue_id)
    return comp_id, venue_id


class TestBasicTwoDay:
    """Hand-computed golden case: 6 competitors, 2 sectors of 3, both days.

    Day totals (points, weight):
      Adam   1+2=3 pts, 3000+1000=4000 g
      Beata  2+1=3 pts, 2000+4000=6000 g
      Celina 3+3=6 pts, 1000+500=1500 g
      Darek  1+1=2 pts, 5000+2000=7000 g
      Ewa    2+2=4 pts, 400+1500=1900 g
      Filip  3+3=6 pts, 300+100=400 g
    Order (pts ASC, weight DESC): Darek 1, Beata 2, Adam 3, Ewa 4, Celina 5, Filip 6.
    """

    def _build(self, db):
        day1, _ = _setup_day(db, "2026-09-05", "Finał", {
            "A": [(1, "Adam", 3000), (2, "Beata", 2000), (3, "Celina", 1000)],
            "B": [(6, "Darek", 5000), (7, "Ewa", 400), (8, "Filip", 300)],
        })
        day2, _ = _setup_day(db, "2026-09-06", "Finał — dzień 2", {
            "A": [(1, "Beata", 4000), (2, "Adam", 1000), (3, "Celina", 500)],
            "B": [(6, "Darek", 2000), (7, "Ewa", 1500), (8, "Filip", 100)],
        }, linked_to=day1)
        return day1, day2

    def test_order_and_places(self, db):
        day1, day2 = self._build(db)
        result = calculate(db, day1, day2)
        assert result.duplicate_names == []
        assert [(r.place, r.full_name) for r in result.rows] == [
            (1, "Darek"), (2, "Beata"), (3, "Adam"),
            (4, "Ewa"), (5, "Celina"), (6, "Filip"),
        ]

    def test_sums(self, db):
        day1, day2 = self._build(db)
        by_name = {r.full_name: r for r in calculate(db, day1, day2).rows}
        darek = by_name["Darek"]
        assert (darek.points_day1, darek.points_day2, darek.total_points) == (1, 1, 2)
        assert (darek.weight_day1, darek.weight_day2, darek.total_weight_grams) == (5000, 2000, 7000)
        beata = by_name["Beata"]
        assert (beata.points_day1, beata.points_day2, beata.total_points) == (2, 1, 3)
        assert beata.total_weight_grams == 6000


class TestExAequo:
    def test_full_tie_shares_place_competition_style(self, db):
        # X and Y: 3 pts / 3000 g each; Z and W: 3 pts / 900 g each
        # -> places 1, 1, 3, 3.
        day1, _ = _setup_day(db, "2026-09-05", None, {
            "A": [(1, "X", 2000), (2, "Y", 1000)],
            "B": [(6, "Z", 500), (7, "W", 400)],
        })
        day2, _ = _setup_day(db, "2026-09-06", None, {
            "A": [(1, "X", 1000), (2, "Y", 2000)],
            "B": [(6, "Z", 400), (7, "W", 500)],
        }, linked_to=day1)

        rows = calculate(db, day1, day2).rows
        places = {r.full_name: r.place for r in rows}
        assert places["X"] == 1
        assert places["Y"] == 1
        assert places["Z"] == 3
        assert places["W"] == 3


class TestZeroWeight:
    def test_zero_both_days_gets_no_place_at_bottom(self, db):
        day1, _ = _setup_day(db, "2026-09-05", None, {
            "A": [(1, "Adam", 3000), (2, "Zenon", 0)],
        })
        day2, _ = _setup_day(db, "2026-09-06", None, {
            "A": [(1, "Adam", 1000), (2, "Zenon", 0)],
        }, linked_to=day1)

        rows = calculate(db, day1, day2).rows
        assert [(r.full_name, r.place) for r in rows] == [("Adam", 1), ("Zenon", None)]

    def test_zero_single_day_ranked_normally(self, db):
        day1, _ = _setup_day(db, "2026-09-05", None, {
            "A": [(1, "Adam", 3000), (2, "Zenon", 0)],
        })
        day2, _ = _setup_day(db, "2026-09-06", None, {
            "A": [(1, "Zenon", 5000), (2, "Adam", 1000)],
        }, linked_to=day1)

        rows = calculate(db, day1, day2).rows
        by_name = {r.full_name: r for r in rows}
        # Zenon: day1 zero weight -> last place points (2), day2 winner (1) = 3 pts.
        # Adam: 1 + 2 = 3 pts. Tie on points -> weight decides: Zenon 5000 > Adam 4000.
        assert by_name["Zenon"].place == 1
        assert by_name["Adam"].place == 2


class TestParticipationFilter:
    def test_only_day1_participant_omitted(self, db):
        day1, _ = _setup_day(db, "2026-09-05", None, {
            "A": [(1, "Adam", 3000), (2, "Tylko Jeden Dzień", 9000)],
        })
        day2, _ = _setup_day(db, "2026-09-06", None, {
            "A": [(1, "Adam", 1000)],
        }, linked_to=day1)

        rows = calculate(db, day1, day2).rows
        assert [r.full_name for r in rows] == ["Adam"]

    def test_on_roster_but_no_station_counts_as_absent(self, db):
        day1, _ = _setup_day(db, "2026-09-05", None, {
            "A": [(1, "Adam", 3000), (2, "Bez Stanowiska", 2000)],
        })
        day2, _ = _setup_day(db, "2026-09-06", None, {
            "A": [(1, "Adam", 1000)],
        }, linked_to=day1)
        # Present on the day-2 roster but never drew a station.
        competitor_repo.add(db, day2, 2, "Bez Stanowiska")
        db.commit()

        rows = calculate(db, day1, day2).rows
        assert [r.full_name for r in rows] == ["Adam"]


class TestNameMatching:
    def test_whitespace_and_case_insensitive_pairing(self, db):
        day1, _ = _setup_day(db, "2026-09-05", None, {
            "A": [(1, "jan  kowalski", 3000)],
        })
        day2, _ = _setup_day(db, "2026-09-06", None, {
            "A": [(1, "JAN KOWALSKI", 1000)],
        }, linked_to=day1)

        rows = calculate(db, day1, day2).rows
        assert len(rows) == 1
        # Display name comes from day 1, original casing.
        assert rows[0].full_name == "jan  kowalski"
        assert rows[0].total_weight_grams == 4000

    def test_duplicate_names_excluded_with_warning(self, db):
        day1, _ = _setup_day(db, "2026-09-05", None, {
            "A": [(1, "Jan Kowalski", 3000), (2, "Jan Kowalski", 2000), (3, "Adam", 1000)],
        })
        day2, _ = _setup_day(db, "2026-09-06", None, {
            "A": [(1, "Jan Kowalski", 500), (2, "Adam", 700)],
        }, linked_to=day1)

        result = calculate(db, day1, day2)
        assert result.duplicate_names == ["Jan Kowalski"]
        assert [r.full_name for r in result.rows] == ["Adam"]


class TestResolveLinkedPair:
    def _pair(self, db):
        day1, _ = _setup_day(db, "2026-09-05", "D1", {"A": [(1, "Adam", 100)]})
        day2, _ = _setup_day(db, "2026-09-06", "D2", {"A": [(1, "Adam", 200)]}, linked_to=day1)
        return day1, day2

    def test_resolves_from_day1(self, db):
        day1, day2 = self._pair(db)
        pair = resolve_linked_pair(db, day1)
        assert pair is not None
        assert (pair[0].id, pair[1].id) == (day1, day2)

    def test_resolves_from_day2_same_order(self, db):
        day1, day2 = self._pair(db)
        pair = resolve_linked_pair(db, day2)
        assert pair is not None
        assert (pair[0].id, pair[1].id) == (day1, day2)

    def test_none_for_unlinked(self, db):
        day1, _ = _setup_day(db, "2026-09-05", None, {"A": [(1, "Adam", 100)]})
        assert resolve_linked_pair(db, day1) is None

    def test_none_after_day1_deleted(self, db):
        day1, day2 = self._pair(db)
        competition_repo.delete(db, day1)
        db.commit()
        # ON DELETE SET NULL cleared the link — day 2 is a regular competition now.
        assert resolve_linked_pair(db, day2) is None
