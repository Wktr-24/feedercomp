from app.repositories import competitor_repo
from app.services.ranking_service import RankingService
from app.services.sector_service import SectorService

SECTOR_DATA = {
    "A": [
        (1, "KOWALCZYK DAWID", 8060),
        (2, "KORCZAK WIKTOR", 6850),
        (3, "RUSAK JERZY", 1180),
        (4, "LEONTIEW BARTŁOMIEJ", 5250),
        (5, "BIEŃKO KRZYSZTOF", 0),
        (46, "WIŚNIEWSKI MARIUSZ", 31700),
        (47, "KOMAR JAKUB", 17490),
        (48, "CZAPLICKI PRZEMYSŁAW", 14050),
        (49, "DRABEK PAWEŁ", 12320),
        (50, "WIECZOREK JAROSŁAW", 0),
    ],
    "B": [
        (6, "CEPEK PAWEŁ", 9250),
        (7, "MARCINIAK MACIEJ", 25440),
        (8, "KUCHARSKI ARTUR", 10210),
        (9, "BORYSIAK MIROSŁAW", 0),
        (10, "PIENIEK WALDEMAR", 24600),
        (41, "SZUMIDŁO MARCIN", 38230),
        (42, "ORZECHOWSKI SYLWESTER", 15240),
        (43, "KALICKI SYLWESTER", 18010),
        (44, "JASTRZĘBSKI RADEK", 10280),
        (45, "JAWORSKI JAROSŁAW", 55790),
    ],
    "C": [
        (11, "POTRZEBOWSKI CEZARY", 9610),
        (12, "WILCZEK MARCIN", 61060),
        (13, "TROSHUPA JACEK", 4200),
        (14, "AKHTAROV YEVHENII", 3760),
        (15, "RUDZIŃSKI MICHAŁ", 4170),
        (36, "SZYMAŃSKI RAFAŁ", 12270),
        (37, "ZDZIARSTEK PAWEŁ", 5490),
        (38, "ROGIŃSKI ROBERT", 21650),
        (39, "PAVLENKO OLEKSANDR", 8740),
        (40, "MARINEC JURIJ", 29140),
    ],
    "D": [
        (16, "STEC PAWEŁ", 12260),
        (17, "ROSTKOWSKI PIOTR", 24190),
        (18, "RUDZIŃSKI PAWEŁ", 9600),
        (19, "JABŁOŃSKI JANUSZ", 3610),
        (20, "BRYL KRZYSZTOF", 23600),
        (31, "LEONTIEW KAMIL", 15140),
        (32, "OLEWIŃSKI JACEK", 0),
        (33, "PIENIEK KAROL", 32760),
        (34, "ORNOWSKI MARCIN", 0),
        (35, "DOMAGAŁA TOMASZ", 9690),
    ],
    "E": [
        (21, "GOMOŁA PIOTR", 19460),
        (22, "SUPRYN JAROSŁAW", 34330),
        (23, "DAWIDIUK RYSZARD", 31670),
        (24, "LECH GRZEGORZ", 9760),
        (25, "SOKULSKI FILIP", 6900),
        (26, "SZEWCZYK PAWEŁ", 16780),
        (27, "MIANOWSKI OSKAR", 15160),
        (28, "BINKIEWICZ JAN", 9400),
        (29, "MARCZAK TOMASZ", 10900),
        (30, "SZACHNOWSKI PAWEŁ", 14780),
    ],
}

EXPECTED_SECTOR_PLACES = {
    "A": {
        "WIŚNIEWSKI MARIUSZ": 1,
        "KOMAR JAKUB": 2,
        "CZAPLICKI PRZEMYSŁAW": 3,
        "DRABEK PAWEŁ": 4,
        "KOWALCZYK DAWID": 5,
        "KORCZAK WIKTOR": 6,
        "LEONTIEW BARTŁOMIEJ": 7,
        "RUSAK JERZY": 8,
        "BIEŃKO KRZYSZTOF": 10,
        "WIECZOREK JAROSŁAW": 10,
    },
    "B": {
        "JAWORSKI JAROSŁAW": 1,
        "SZUMIDŁO MARCIN": 2,
        "MARCINIAK MACIEJ": 3,
        "PIENIEK WALDEMAR": 4,
        "KALICKI SYLWESTER": 5,
        "ORZECHOWSKI SYLWESTER": 6,
        "JASTRZĘBSKI RADEK": 7,
        "KUCHARSKI ARTUR": 8,
        "CEPEK PAWEŁ": 9,
        "BORYSIAK MIROSŁAW": 10,
    },
    "C": {
        "WILCZEK MARCIN": 1,
        "MARINEC JURIJ": 2,
        "ROGIŃSKI ROBERT": 3,
        "SZYMAŃSKI RAFAŁ": 4,
        "POTRZEBOWSKI CEZARY": 5,
        "PAVLENKO OLEKSANDR": 6,
        "ZDZIARSTEK PAWEŁ": 7,
        "TROSHUPA JACEK": 8,
        "RUDZIŃSKI MICHAŁ": 9,
        "AKHTAROV YEVHENII": 10,
    },
    "D": {
        "PIENIEK KAROL": 1,
        "ROSTKOWSKI PIOTR": 2,
        "BRYL KRZYSZTOF": 3,
        "LEONTIEW KAMIL": 4,
        "STEC PAWEŁ": 5,
        "DOMAGAŁA TOMASZ": 6,
        "RUDZIŃSKI PAWEŁ": 7,
        "JABŁOŃSKI JANUSZ": 8,
        "OLEWIŃSKI JACEK": 10,
        "ORNOWSKI MARCIN": 10,
    },
    "E": {
        "SUPRYN JAROSŁAW": 1,
        "DAWIDIUK RYSZARD": 2,
        "GOMOŁA PIOTR": 3,
        "SZEWCZYK PAWEŁ": 4,
        "MIANOWSKI OSKAR": 5,
        "SZACHNOWSKI PAWEŁ": 6,
        "MARCZAK TOMASZ": 7,
        "LECH GRZEGORZ": 8,
        "BINKIEWICZ JAN": 9,
        "SOKULSKI FILIP": 10,
    },
}

EXPECTED_FINAL_CLASSIFICATION = [
    (1, "WILCZEK MARCIN", "C", 1, 61060),
    (2, "JAWORSKI JAROSŁAW", "B", 1, 55790),
    (3, "SUPRYN JAROSŁAW", "E", 1, 34330),
    (4, "PIENIEK KAROL", "D", 1, 32760),
    (5, "WIŚNIEWSKI MARIUSZ", "A", 1, 31700),
    (6, "SZUMIDŁO MARCIN", "B", 2, 38230),
    (7, "DAWIDIUK RYSZARD", "E", 2, 31670),
    (8, "MARINEC JURIJ", "C", 2, 29140),
    (9, "ROSTKOWSKI PIOTR", "D", 2, 24190),
    (10, "KOMAR JAKUB", "A", 2, 17490),
    (11, "MARCINIAK MACIEJ", "B", 3, 25440),
    (12, "BRYL KRZYSZTOF", "D", 3, 23600),
    (13, "ROGIŃSKI ROBERT", "C", 3, 21650),
    (14, "GOMOŁA PIOTR", "E", 3, 19460),
    (15, "CZAPLICKI PRZEMYSŁAW", "A", 3, 14050),
    (16, "PIENIEK WALDEMAR", "B", 4, 24600),
    (17, "SZEWCZYK PAWEŁ", "E", 4, 16780),
    (18, "LEONTIEW KAMIL", "D", 4, 15140),
    (19, "DRABEK PAWEŁ", "A", 4, 12320),
    (20, "SZYMAŃSKI RAFAŁ", "C", 4, 12270),
    (21, "KALICKI SYLWESTER", "B", 5, 18010),
    (22, "MIANOWSKI OSKAR", "E", 5, 15160),
    (23, "STEC PAWEŁ", "D", 5, 12260),
    (24, "POTRZEBOWSKI CEZARY", "C", 5, 9610),
    (25, "KOWALCZYK DAWID", "A", 5, 8060),
    (26, "ORZECHOWSKI SYLWESTER", "B", 6, 15240),
    (27, "SZACHNOWSKI PAWEŁ", "E", 6, 14780),
    (28, "DOMAGAŁA TOMASZ", "D", 6, 9690),
    (29, "PAVLENKO OLEKSANDR", "C", 6, 8740),
    (30, "KORCZAK WIKTOR", "A", 6, 6850),
    (31, "MARCZAK TOMASZ", "E", 7, 10900),
    (32, "JASTRZĘBSKI RADEK", "B", 7, 10280),
    (33, "RUDZIŃSKI PAWEŁ", "D", 7, 9600),
    (34, "ZDZIARSTEK PAWEŁ", "C", 7, 5490),
    (35, "LEONTIEW BARTŁOMIEJ", "A", 7, 5250),
    (36, "KUCHARSKI ARTUR", "B", 8, 10210),
    (37, "LECH GRZEGORZ", "E", 8, 9760),
    (38, "TROSHUPA JACEK", "C", 8, 4200),
    (39, "JABŁOŃSKI JANUSZ", "D", 8, 3610),
    (40, "RUSAK JERZY", "A", 8, 1180),
    (41, "BINKIEWICZ JAN", "E", 9, 9400),
    (42, "CEPEK PAWEŁ", "B", 9, 9250),
    (43, "RUDZIŃSKI MICHAŁ", "C", 9, 4170),
    (44, "SOKULSKI FILIP", "E", 10, 6900),
    (45, "AKHTAROV YEVHENII", "C", 10, 3760),
]

EXPECTED_NO_PLACE = [
    "BIEŃKO KRZYSZTOF",
    "WIECZOREK JAROSŁAW",
    "BORYSIAK MIROSŁAW",
    "OLEWIŃSKI JACEK",
    "ORNOWSKI MARCIN",
]


def _setup_competition(db):
    venue_id = db.execute("SELECT id FROM venues WHERE name = 'Stawy Siedleckie'").fetchone()["id"]
    cursor = db.execute(
        "INSERT INTO competitions (venue_id, date, name, winner_places) VALUES (?, ?, ?, ?)",
        (venue_id, "2025-09-28", "Zawody 28.09.2025", 3),
    )
    competition_id = cursor.lastrowid
    db.commit()

    list_number = 1
    for sector_name, entries in SECTOR_DATA.items():
        for station, name, weight in entries:
            comp_id = competitor_repo.add(db, competition_id, list_number, name)
            competitor_repo.update_station(db, comp_id, station, sector_name)
            competitor_repo.update_weight(db, comp_id, weight)
            list_number += 1

    return competition_id, venue_id


class TestFullRanking:
    def test_sector_places(self, db):
        competition_id, venue_id = _setup_competition(db)
        sector_service = SectorService()
        ranking_service = RankingService(sector_service)

        ranking_service.calculate_all(db, competition_id, venue_id)

        for sector_name, expected in EXPECTED_SECTOR_PLACES.items():
            competitors = competitor_repo.get_by_sector(db, competition_id, sector_name)
            actual = {c.full_name: c.sector_place for c in competitors}
            for name, expected_place in expected.items():
                assert actual[name] == expected_place, (
                    f"Sector {sector_name}: {name} expected place {expected_place}, got {actual[name]}"
                )

    def test_sector_points_equal_sector_place(self, db):
        competition_id, venue_id = _setup_competition(db)
        sector_service = SectorService()
        ranking_service = RankingService(sector_service)

        ranking_service.calculate_all(db, competition_id, venue_id)

        all_competitors = competitor_repo.get_all(db, competition_id)
        for c in all_competitors:
            assert c.sector_points == c.sector_place, (
                f"{c.full_name}: sector_points ({c.sector_points}) != sector_place ({c.sector_place})"
            )

    def test_final_classification(self, db):
        competition_id, venue_id = _setup_competition(db)
        sector_service = SectorService()
        ranking_service = RankingService(sector_service)

        ranking_service.calculate_all(db, competition_id, venue_id)

        all_competitors = competitor_repo.get_all(db, competition_id)
        by_name = {c.full_name: c for c in all_competitors}

        for expected_place, name, sector, points, weight in EXPECTED_FINAL_CLASSIFICATION:
            c = by_name[name]
            assert c.final_place == expected_place, (
                f"{name}: expected final_place {expected_place}, got {c.final_place}"
            )
            assert c.sector_name == sector, (
                f"{name}: expected sector {sector}, got {c.sector_name}"
            )
            assert c.sector_points == points, (
                f"{name}: expected sector_points {points}, got {c.sector_points}"
            )
            assert c.weight_grams == weight, (
                f"{name}: expected weight {weight}, got {c.weight_grams}"
            )

    def test_zero_weight_no_final_place(self, db):
        competition_id, venue_id = _setup_competition(db)
        sector_service = SectorService()
        ranking_service = RankingService(sector_service)

        ranking_service.calculate_all(db, competition_id, venue_id)

        all_competitors = competitor_repo.get_all(db, competition_id)
        by_name = {c.full_name: c for c in all_competitors}

        for name in EXPECTED_NO_PLACE:
            c = by_name[name]
            assert c.final_place is None, (
                f"{name}: expected final_place None, got {c.final_place}"
            )
            assert c.weight_grams == 0
            assert c.sector_points == 10

    def test_get_winners_returns_15_for_places_3(self, db):
        competition_id, venue_id = _setup_competition(db)
        sector_service = SectorService()
        ranking_service = RankingService(sector_service)

        ranking_service.calculate_all(db, competition_id, venue_id)

        winners = ranking_service.get_winners(db, competition_id, winner_places=3)
        assert len(winners) == 15

        winner_names = [w.full_name for w in winners]
        expected_winner_names = [name for _, name, _, _, _ in EXPECTED_FINAL_CLASSIFICATION[:15]]
        assert winner_names == expected_winner_names


class TestExAequo:
    def test_sector_places_with_weight_tie(self, db):
        """Two competitors with same weight get same sector place, next place is skipped."""
        venue_id = db.execute("SELECT id FROM venues WHERE name = 'Stawy Siedleckie'").fetchone()["id"]
        cursor = db.execute(
            "INSERT INTO competitions (venue_id, date, name) VALUES (?, ?, ?)",
            (venue_id, "2026-01-01", "Tie test"),
        )
        comp_id = cursor.lastrowid
        db.commit()

        entries = [
            (1, "FIRST", 10000),
            (2, "TIE_A", 8000),
            (3, "TIE_B", 8000),
            (4, "FOURTH", 5000),
            (5, "ZERO", 0),
        ]
        for station, name, weight in entries:
            cid = competitor_repo.add(db, comp_id, station, name)
            competitor_repo.update_station(db, cid, station, "A")
            competitor_repo.update_weight(db, cid, weight)

        service = SectorService()
        service.calculate_sector_places(db, comp_id, "A")

        competitors = competitor_repo.get_by_sector(db, comp_id, "A")
        by_name = {c.full_name: c.sector_place for c in competitors}

        assert by_name["FIRST"] == 1
        assert by_name["TIE_A"] == 2
        assert by_name["TIE_B"] == 2
        assert by_name["FOURTH"] == 4  # skipped 3
        assert by_name["ZERO"] == 5

    def test_final_classification_with_tie(self, db):
        """Two competitors with same sector_points and weight get same final place."""
        venue_id = db.execute("SELECT id FROM venues WHERE name = 'Stawy Siedleckie'").fetchone()["id"]
        cursor = db.execute(
            "INSERT INTO competitions (venue_id, date, name) VALUES (?, ?, ?)",
            (venue_id, "2026-01-02", "Final tie test"),
        )
        comp_id = cursor.lastrowid
        db.commit()

        # Sector A: two competitors with different weights
        for station, name, weight in [(1, "A_FIRST", 10000), (2, "A_SECOND", 5000)]:
            cid = competitor_repo.add(db, comp_id, station, name)
            competitor_repo.update_station(db, cid, station, "A")
            competitor_repo.update_weight(db, cid, weight)

        # Sector B: two competitors, first has same weight as A_FIRST
        for station, name, weight in [(6, "B_FIRST", 10000), (7, "B_SECOND", 5000)]:
            cid = competitor_repo.add(db, comp_id, station, name)
            competitor_repo.update_station(db, cid, station, "B")
            competitor_repo.update_weight(db, cid, weight)

        service = RankingService(SectorService())
        service.calculate_all(db, comp_id, venue_id)

        competitors = competitor_repo.get_all(db, comp_id)
        by_name = {c.full_name: c for c in competitors}

        # Both firsts have sector_points=1, weight=10000 -> same final place
        assert by_name["A_FIRST"].final_place == 1
        assert by_name["B_FIRST"].final_place == 1
        # Both seconds have sector_points=2, weight=5000 -> same final place
        assert by_name["A_SECOND"].final_place == 3  # skipped 2
        assert by_name["B_SECOND"].final_place == 3

    def test_three_way_tie_in_sector(self, db):
        """Three competitors with same weight get same sector place."""
        venue_id = db.execute("SELECT id FROM venues WHERE name = 'Stawy Siedleckie'").fetchone()["id"]
        cursor = db.execute(
            "INSERT INTO competitions (venue_id, date, name) VALUES (?, ?, ?)",
            (venue_id, "2026-01-03", "Three-way tie"),
        )
        comp_id = cursor.lastrowid
        db.commit()

        entries = [
            (1, "TIE_A", 8000),
            (2, "TIE_B", 8000),
            (3, "TIE_C", 8000),
            (4, "FOURTH", 5000),
        ]
        for station, name, weight in entries:
            cid = competitor_repo.add(db, comp_id, station, name)
            competitor_repo.update_station(db, cid, station, "A")
            competitor_repo.update_weight(db, cid, weight)

        service = SectorService()
        service.calculate_sector_places(db, comp_id, "A")

        competitors = competitor_repo.get_by_sector(db, comp_id, "A")
        by_name = {c.full_name: c.sector_place for c in competitors}

        assert by_name["TIE_A"] == 1
        assert by_name["TIE_B"] == 1
        assert by_name["TIE_C"] == 1
        assert by_name["FOURTH"] == 4

    def test_multiple_ties_in_sector(self, db):
        """Two independent ties in one sector."""
        venue_id = db.execute("SELECT id FROM venues WHERE name = 'Stawy Siedleckie'").fetchone()["id"]
        cursor = db.execute(
            "INSERT INTO competitions (venue_id, date, name) VALUES (?, ?, ?)",
            (venue_id, "2026-01-04", "Multiple ties"),
        )
        comp_id = cursor.lastrowid
        db.commit()

        entries = [
            (1, "FIRST", 10000),
            (2, "TIE_A1", 8000),
            (3, "TIE_A2", 8000),
            (4, "TIE_B1", 5000),
            (5, "TIE_B2", 5000),
            (46, "SIXTH", 3000),
        ]
        for station, name, weight in entries:
            cid = competitor_repo.add(db, comp_id, station, name)
            competitor_repo.update_station(db, cid, station, "A")
            competitor_repo.update_weight(db, cid, weight)

        service = SectorService()
        service.calculate_sector_places(db, comp_id, "A")

        competitors = competitor_repo.get_by_sector(db, comp_id, "A")
        by_name = {c.full_name: c.sector_place for c in competitors}

        assert by_name["FIRST"] == 1
        assert by_name["TIE_A1"] == 2
        assert by_name["TIE_A2"] == 2
        assert by_name["TIE_B1"] == 4
        assert by_name["TIE_B2"] == 4
        assert by_name["SIXTH"] == 6

    def test_tie_at_boundary_of_zero_weight(self, db):
        """Tie just above zero-weight group gets correct places."""
        venue_id = db.execute("SELECT id FROM venues WHERE name = 'Stawy Siedleckie'").fetchone()["id"]
        cursor = db.execute(
            "INSERT INTO competitions (venue_id, date, name) VALUES (?, ?, ?)",
            (venue_id, "2026-01-05", "Tie at zero boundary"),
        )
        comp_id = cursor.lastrowid
        db.commit()

        entries = [
            (1, "FIRST", 10000),
            (2, "TIE_A", 5000),
            (3, "TIE_B", 5000),
            (4, "ZERO_A", 0),
            (5, "ZERO_B", 0),
        ]
        for station, name, weight in entries:
            cid = competitor_repo.add(db, comp_id, station, name)
            competitor_repo.update_station(db, cid, station, "A")
            competitor_repo.update_weight(db, cid, weight)

        service = SectorService()
        service.calculate_sector_places(db, comp_id, "A")

        competitors = competitor_repo.get_by_sector(db, comp_id, "A")
        by_name = {c.full_name: c.sector_place for c in competitors}

        assert by_name["FIRST"] == 1
        assert by_name["TIE_A"] == 2
        assert by_name["TIE_B"] == 2
        assert by_name["ZERO_A"] == 5
        assert by_name["ZERO_B"] == 5

    def test_get_winners_with_ex_aequo(self, db):
        """With ex aequo in sector, get_winners returns correct results."""
        venue_id = db.execute("SELECT id FROM venues WHERE name = 'Stawy Siedleckie'").fetchone()["id"]
        cursor = db.execute(
            "INSERT INTO competitions (venue_id, date, name) VALUES (?, ?, ?)",
            (venue_id, "2026-01-06", "Winners ex aequo"),
        )
        comp_id = cursor.lastrowid
        db.commit()

        # Sector A: weights [10000, 10000, 5000] -> places 1, 1, 3
        for station, name, weight in [(1, "A1", 10000), (2, "A2", 10000), (3, "A3", 5000)]:
            cid = competitor_repo.add(db, comp_id, station, name)
            competitor_repo.update_station(db, cid, station, "A")
            competitor_repo.update_weight(db, cid, weight)

        # Sector B: weights [9000, 8000, 7000] -> places 1, 2, 3
        for station, name, weight in [(6, "B1", 9000), (7, "B2", 8000), (8, "B3", 7000)]:
            cid = competitor_repo.add(db, comp_id, station, name)
            competitor_repo.update_station(db, cid, station, "B")
            competitor_repo.update_weight(db, cid, weight)

        service = RankingService(SectorService())
        service.calculate_all(db, comp_id, venue_id)

        # winner_places=3: all 6 competitors qualify (all have sector_points <= 3)
        winners = service.get_winners(db, comp_id, winner_places=3)
        assert len(winners) == 6

        # winner_places=1: A has two with pkt=1, B has one with pkt=1
        winners = service.get_winners(db, comp_id, winner_places=1)
        assert len(winners) == 3
        winner_names = {w.full_name for w in winners}
        assert winner_names == {"A1", "A2", "B1"}

    def test_single_competitor_in_sector(self, db):
        """Single competitor gets place 1 (or total if zero weight)."""
        venue_id = db.execute("SELECT id FROM venues WHERE name = 'Stawy Siedleckie'").fetchone()["id"]

        # Competition 1: single competitor with weight > 0
        cursor = db.execute(
            "INSERT INTO competitions (venue_id, date, name) VALUES (?, ?, ?)",
            (venue_id, "2026-01-07", "Single with weight"),
        )
        comp_id1 = cursor.lastrowid
        db.commit()

        cid = competitor_repo.add(db, comp_id1, 1, "SOLO_WITH_WEIGHT")
        competitor_repo.update_station(db, cid, 1, "A")
        competitor_repo.update_weight(db, cid, 5000)

        service = SectorService()
        service.calculate_sector_places(db, comp_id1, "A")

        competitors = competitor_repo.get_by_sector(db, comp_id1, "A")
        assert competitors[0].sector_place == 1

        # Competition 2: single competitor with weight = 0
        cursor = db.execute(
            "INSERT INTO competitions (venue_id, date, name) VALUES (?, ?, ?)",
            (venue_id, "2026-01-08", "Single zero weight"),
        )
        comp_id2 = cursor.lastrowid
        db.commit()

        cid = competitor_repo.add(db, comp_id2, 1, "SOLO_ZERO")
        competitor_repo.update_station(db, cid, 1, "A")
        competitor_repo.update_weight(db, cid, 0)

        service.calculate_sector_places(db, comp_id2, "A")

        competitors = competitor_repo.get_by_sector(db, comp_id2, "A")
        assert competitors[0].sector_place == 1  # total = 1
