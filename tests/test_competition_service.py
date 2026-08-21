import pytest

from app.repositories import (
    competition_repo,
    competition_sector_overrides_repo,
    competitor_repo,
    excluded_station_repo,
)
from app.services.competition_service import Day2Error, create_day2


@pytest.fixture
def venue_id(db):
    return db.execute(
        "SELECT id FROM venues WHERE name = 'Stawy Siedleckie — Finał'"
    ).fetchone()["id"]


@pytest.fixture
def day1_id(db, venue_id):
    comp_id = competition_repo.create(
        db, venue_id, "2026-09-05", "Finał", max_competitors=50, winner_places=4,
    )
    competitor_repo.add(db, comp_id, 1, "Jan Kowalski", "123456789", "paid")
    competitor_repo.add(db, comp_id, 2, "Anna Nowak", None, "on_site")
    competitor_repo.add(db, comp_id, 3, "Piotr Wiśniewski", None, "unpaid")
    db.commit()
    return comp_id


class TestCreateDay2HappyPath:
    def test_copies_roster_fields_in_order(self, db, day1_id):
        result = create_day2(db, day1_id, "2026-09-06", "Finał — dzień 2")
        assert result.copied_count == 3
        assert result.duplicate_names == []

        copied = competitor_repo.get_all(db, result.competition_id)
        source = competitor_repo.get_all(db, day1_id)
        assert [(c.list_number, c.full_name, c.phone, c.payment_status) for c in copied] == [
            (c.list_number, c.full_name, c.phone, c.payment_status) for c in source
        ]

    def test_copied_competitors_start_clean(self, db, venue_id, day1_id):
        # Give day-1 competitors state that must NOT carry over.
        source = competitor_repo.get_all(db, day1_id)
        competitor_repo.update_presence(db, source[0].id, True)
        competitor_repo.update_station(db, source[0].id, 1, "A")
        competitor_repo.update_weight(db, source[0].id, 12345)
        competitor_repo.update_rankings(db, source[0].id, 1, 1, 1)
        db.commit()

        result = create_day2(db, day1_id, "2026-09-06", None)

        for c in competitor_repo.get_all(db, result.competition_id):
            assert c.is_present is False
            assert c.station_number is None
            assert c.sector_name is None
            assert c.weight_grams == 0
            assert c.sector_place is None
            assert c.sector_points is None
            assert c.final_place is None

    def test_competition_fields_copied_and_linked(self, db, venue_id, day1_id):
        result = create_day2(db, day1_id, "2026-09-06", "Finał — dzień 2")
        day2 = competition_repo.get_by_id(db, result.competition_id)
        assert day2.venue_id == venue_id
        assert day2.date == "2026-09-06"
        assert day2.name == "Finał — dzień 2"
        assert day2.max_competitors == 50
        assert day2.winner_places == 4
        assert day2.linked_competition_id == day1_id

    def test_exclusions_and_overrides_not_copied(self, db, venue_id, day1_id):
        excluded_station_repo.add_excluded(db, day1_id, venue_id, 22, "F")
        competition_sector_overrides_repo.set_overrides(db, day1_id, {13: "D"})
        db.commit()

        result = create_day2(db, day1_id, "2026-09-06", None)

        assert excluded_station_repo.get_excluded(db, result.competition_id) == []
        assert competition_sector_overrides_repo.get_overrides(db, result.competition_id) == {}

    def test_empty_roster_returns_zero(self, db, venue_id):
        empty_id = competition_repo.create(db, venue_id, "2026-09-05")
        db.commit()
        result = create_day2(db, empty_id, "2026-09-06", None)
        assert result.copied_count == 0
        assert competitor_repo.get_all(db, result.competition_id) == []

    def test_source_untouched(self, db, day1_id):
        before = [(c.id, c.list_number, c.full_name) for c in competitor_repo.get_all(db, day1_id)]
        create_day2(db, day1_id, "2026-09-06", None)
        after = [(c.id, c.list_number, c.full_name) for c in competitor_repo.get_all(db, day1_id)]
        assert before == after


class TestCreateDay2Guards:
    def test_source_missing(self, db):
        with pytest.raises(Day2Error) as exc:
            create_day2(db, 99999, "2026-09-06", None)
        assert exc.value.reason == "source_missing"

    def test_source_is_day2(self, db, day1_id):
        result = create_day2(db, day1_id, "2026-09-06", None)
        with pytest.raises(Day2Error) as exc:
            create_day2(db, result.competition_id, "2026-09-07", None)
        assert exc.value.reason == "source_is_day2"

    def test_already_has_day2(self, db, day1_id):
        create_day2(db, day1_id, "2026-09-06", None)
        with pytest.raises(Day2Error) as exc:
            create_day2(db, day1_id, "2026-09-07", None)
        assert exc.value.reason == "already_has_day2"

    def test_guard_failure_persists_nothing(self, db, day1_id):
        create_day2(db, day1_id, "2026-09-06", None)
        count_before = db.execute("SELECT COUNT(*) FROM competitions").fetchone()[0]
        with pytest.raises(Day2Error):
            create_day2(db, day1_id, "2026-09-07", None)
        count_after = db.execute("SELECT COUNT(*) FROM competitions").fetchone()[0]
        assert count_after == count_before


class TestCreateDay2DuplicateReport:
    def test_legacy_duplicates_copied_and_reported(self, db, venue_id):
        # Rosters entered before the duplicate guard existed can hold the
        # same name twice; the copy must stay faithful and report it.
        comp_id = competition_repo.create(db, venue_id, "2026-09-05")
        competitor_repo.add(db, comp_id, 1, "Jan Kowalski")
        competitor_repo.add(db, comp_id, 2, "JAN KOWALSKI")
        competitor_repo.add(db, comp_id, 3, "Adam Nowak")
        db.commit()

        result = create_day2(db, comp_id, "2026-09-06", None)

        assert result.copied_count == 3
        assert result.duplicate_names == ["Jan Kowalski"]
        assert len(competitor_repo.get_all(db, result.competition_id)) == 3
