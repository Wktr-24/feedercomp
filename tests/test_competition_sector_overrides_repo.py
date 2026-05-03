import pytest

from app.repositories import competition_sector_overrides_repo as repo


@pytest.fixture
def lasomin_competition_id(db):
    venue_id = db.execute(
        "SELECT id FROM venues WHERE name = 'Lasomin'"
    ).fetchone()["id"]
    cursor = db.execute(
        "INSERT INTO competitions (venue_id, date, name) VALUES (?, '2026-06-01', 'Test')",
        (venue_id,),
    )
    db.commit()
    return cursor.lastrowid


@pytest.fixture
def second_competition_id(db):
    venue_id = db.execute(
        "SELECT id FROM venues WHERE name = 'Lasomin'"
    ).fetchone()["id"]
    cursor = db.execute(
        "INSERT INTO competitions (venue_id, date, name) VALUES (?, '2026-07-01', 'Test 2')",
        (venue_id,),
    )
    db.commit()
    return cursor.lastrowid


class TestGetOverrides:
    def test_returns_empty_dict_when_none(self, db, lasomin_competition_id):
        assert repo.get_overrides(db, lasomin_competition_id) == {}

    def test_returns_all_overrides_keyed_by_station(self, db, lasomin_competition_id):
        repo.set_overrides(db, lasomin_competition_id, {13: "D", 5: "C"})
        db.commit()
        result = repo.get_overrides(db, lasomin_competition_id)
        assert result == {13: "D", 5: "C"}


class TestGetOverride:
    def test_returns_none_when_missing(self, db, lasomin_competition_id):
        assert repo.get_override(db, lasomin_competition_id, 13) is None

    def test_returns_sector_when_present(self, db, lasomin_competition_id):
        repo.set_overrides(db, lasomin_competition_id, {13: "D"})
        db.commit()
        assert repo.get_override(db, lasomin_competition_id, 13) == "D"

    def test_returns_none_for_other_competition(
        self, db, lasomin_competition_id, second_competition_id,
    ):
        repo.set_overrides(db, lasomin_competition_id, {13: "D"})
        db.commit()
        assert repo.get_override(db, second_competition_id, 13) is None


class TestSetOverrides:
    def test_inserts_all_entries(self, db, lasomin_competition_id):
        repo.set_overrides(db, lasomin_competition_id, {13: "D", 1: "B"})
        db.commit()
        assert repo.get_overrides(db, lasomin_competition_id) == {13: "D", 1: "B"}

    def test_replaces_existing_overrides(self, db, lasomin_competition_id):
        repo.set_overrides(db, lasomin_competition_id, {13: "D", 5: "C"})
        db.commit()
        repo.set_overrides(db, lasomin_competition_id, {7: "A"})
        db.commit()
        assert repo.get_overrides(db, lasomin_competition_id) == {7: "A"}

    def test_empty_dict_clears_existing(self, db, lasomin_competition_id):
        repo.set_overrides(db, lasomin_competition_id, {13: "D"})
        db.commit()
        repo.set_overrides(db, lasomin_competition_id, {})
        db.commit()
        assert repo.get_overrides(db, lasomin_competition_id) == {}

    def test_accepts_string_keys_as_well_as_int(self, db, lasomin_competition_id):
        # JSON in venues.json stores variant.sector_overrides keys as strings
        # (JSON forbids non-string object keys). Repo must coerce.
        repo.set_overrides(db, lasomin_competition_id, {"13": "D"})
        db.commit()
        # Stored as int in DB; lookup by int works.
        assert repo.get_override(db, lasomin_competition_id, 13) == "D"
        assert repo.get_overrides(db, lasomin_competition_id) == {13: "D"}


class TestClearOverrides:
    def test_removes_all_for_competition(self, db, lasomin_competition_id):
        repo.set_overrides(db, lasomin_competition_id, {13: "D", 5: "C"})
        db.commit()
        repo.clear_overrides(db, lasomin_competition_id)
        db.commit()
        assert repo.get_overrides(db, lasomin_competition_id) == {}

    def test_leaves_other_competitions_untouched(
        self, db, lasomin_competition_id, second_competition_id,
    ):
        repo.set_overrides(db, lasomin_competition_id, {13: "D"})
        repo.set_overrides(db, second_competition_id, {5: "C"})
        db.commit()

        repo.clear_overrides(db, lasomin_competition_id)
        db.commit()

        assert repo.get_overrides(db, lasomin_competition_id) == {}
        assert repo.get_overrides(db, second_competition_id) == {5: "C"}


class TestPerCompetitionIsolation:
    def test_same_station_can_have_different_overrides_in_different_competitions(
        self, db, lasomin_competition_id, second_competition_id,
    ):
        repo.set_overrides(db, lasomin_competition_id, {13: "D"})
        repo.set_overrides(db, second_competition_id, {13: "C"})
        db.commit()

        assert repo.get_override(db, lasomin_competition_id, 13) == "D"
        assert repo.get_override(db, second_competition_id, 13) == "C"
