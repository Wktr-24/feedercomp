import pytest

from app.repositories import competition_sector_overrides_repo, competitor_repo
from app.services.sector_service import (
    SectorService,
    get_balance_variant,
    match_variant_for_selection,
    reconcile_competitor_sectors,
)


@pytest.fixture
def service():
    return SectorService()


@pytest.fixture
def lasomin_venue_id(db):
    return db.execute("SELECT id FROM venues WHERE name = 'Lasomin'").fetchone()["id"]


@pytest.fixture
def lasomin_comp(db, lasomin_venue_id):
    cursor = db.execute(
        "INSERT INTO competitions (venue_id, date, name) VALUES (?, '2026-06-01', 'Lasomin Test')",
        (lasomin_venue_id,),
    )
    db.commit()
    return cursor.lastrowid


@pytest.fixture
def second_lasomin_comp(db, lasomin_venue_id):
    cursor = db.execute(
        "INSERT INTO competitions (venue_id, date, name) VALUES (?, '2026-07-01', 'Lasomin Test 2')",
        (lasomin_venue_id,),
    )
    db.commit()
    return cursor.lastrowid


def _add_competitor(db, comp_id, list_number=1, name="Test Competitor"):
    return competitor_repo.add(db, comp_id, list_number, name)


class TestGetSectorForStationDefault:
    def test_station_13_default_is_C(self, db, service, lasomin_venue_id):
        # No competition_id passed → falls back to venue default mapping.
        assert service.get_sector_for_station(db, lasomin_venue_id, 13) == "C"

    def test_station_22_default_is_D(self, db, service, lasomin_venue_id):
        assert service.get_sector_for_station(db, lasomin_venue_id, 22) == "D"

    def test_station_18_default_is_D(self, db, service, lasomin_venue_id):
        assert service.get_sector_for_station(db, lasomin_venue_id, 18) == "D"

    def test_station_1_default_is_A(self, db, service, lasomin_venue_id):
        assert service.get_sector_for_station(db, lasomin_venue_id, 1) == "A"

    def test_unknown_station_returns_none(self, db, service, lasomin_venue_id):
        assert service.get_sector_for_station(db, lasomin_venue_id, 99) is None


class TestGetSectorForStationWithOverride:
    def test_station_13_resolves_to_D_with_override(
        self, db, service, lasomin_venue_id, lasomin_comp,
    ):
        competition_sector_overrides_repo.set_overrides(db, lasomin_comp, {13: "D"})
        db.commit()
        assert service.get_sector_for_station(
            db, lasomin_venue_id, 13, lasomin_comp,
        ) == "D"

    def test_station_13_resolves_to_C_without_override(
        self, db, service, lasomin_venue_id, lasomin_comp,
    ):
        # Fresh competition, no override row → still uses venue default.
        assert service.get_sector_for_station(
            db, lasomin_venue_id, 13, lasomin_comp,
        ) == "C"

    def test_overrides_isolated_per_competition(
        self, db, service, lasomin_venue_id, lasomin_comp, second_lasomin_comp,
    ):
        competition_sector_overrides_repo.set_overrides(db, lasomin_comp, {13: "D"})
        db.commit()
        # First competition sees the override; second one doesn't.
        assert service.get_sector_for_station(
            db, lasomin_venue_id, 13, lasomin_comp,
        ) == "D"
        assert service.get_sector_for_station(
            db, lasomin_venue_id, 13, second_lasomin_comp,
        ) == "C"

    def test_other_stations_unaffected_by_override(
        self, db, service, lasomin_venue_id, lasomin_comp,
    ):
        competition_sector_overrides_repo.set_overrides(db, lasomin_comp, {13: "D"})
        db.commit()
        assert service.get_sector_for_station(db, lasomin_venue_id, 22, lasomin_comp) == "D"
        assert service.get_sector_for_station(db, lasomin_venue_id, 1, lasomin_comp) == "A"


class TestAssignStationWithOverride:
    def test_assign_station_13_writes_D_when_override_active(
        self, db, service, lasomin_venue_id, lasomin_comp,
    ):
        competition_sector_overrides_repo.set_overrides(db, lasomin_comp, {13: "D"})
        db.commit()
        cid = _add_competitor(db, lasomin_comp)
        competitor_repo.update_presence(db, cid, True)
        db.commit()

        service.assign_station(db, cid, 13, lasomin_venue_id, lasomin_comp)
        db.commit()

        c = competitor_repo.get_by_id(db, cid)
        assert c.station_number == 13
        assert c.sector_name == "D"

    def test_assign_station_13_writes_C_without_override(
        self, db, service, lasomin_venue_id, lasomin_comp,
    ):
        cid = _add_competitor(db, lasomin_comp)
        competitor_repo.update_presence(db, cid, True)
        db.commit()

        service.assign_station(db, cid, 13, lasomin_venue_id, lasomin_comp)
        db.commit()

        c = competitor_repo.get_by_id(db, cid)
        assert c.sector_name == "C"

    def test_two_competitions_can_assign_station_13_to_different_sectors(
        self, db, service, lasomin_venue_id, lasomin_comp, second_lasomin_comp,
    ):
        competition_sector_overrides_repo.set_overrides(db, lasomin_comp, {13: "D"})
        db.commit()

        cid1 = _add_competitor(db, lasomin_comp, list_number=1, name="Person A")
        cid2 = _add_competitor(db, second_lasomin_comp, list_number=1, name="Person B")
        competitor_repo.update_presence(db, cid1, True)
        competitor_repo.update_presence(db, cid2, True)
        db.commit()

        service.assign_station(db, cid1, 13, lasomin_venue_id, lasomin_comp)
        service.assign_station(db, cid2, 13, lasomin_venue_id, second_lasomin_comp)
        db.commit()

        assert competitor_repo.get_by_id(db, cid1).sector_name == "D"
        assert competitor_repo.get_by_id(db, cid2).sector_name == "C"


class TestAssignStationRegression:
    """Regression: changes to assign_station must not break Stawy or generic flow."""

    def test_assign_to_stawy_works_unchanged(self, db, service):
        venue_id = db.execute(
            "SELECT id FROM venues WHERE name = 'Stawy Siedleckie'"
        ).fetchone()["id"]
        cursor = db.execute(
            "INSERT INTO competitions (venue_id, date, name) VALUES (?, '2026-04-01', 'Stawy Test')",
            (venue_id,),
        )
        comp_id = cursor.lastrowid
        cid = _add_competitor(db, comp_id, list_number=1)
        competitor_repo.update_presence(db, cid, True)
        db.commit()

        service.assign_station(db, cid, 25, venue_id, comp_id)
        db.commit()
        assert competitor_repo.get_by_id(db, cid).sector_name == "E"

    def test_assign_unknown_station_raises(self, db, service, lasomin_venue_id, lasomin_comp):
        cid = _add_competitor(db, lasomin_comp)
        competitor_repo.update_presence(db, cid, True)
        db.commit()
        with pytest.raises(ValueError, match="nie istnieje"):
            service.assign_station(db, cid, 99, lasomin_venue_id, lasomin_comp)

    def test_assign_excluded_station_raises(
        self, db, service, lasomin_venue_id, lasomin_comp,
    ):
        from app.repositories import excluded_station_repo
        excluded_station_repo.add_excluded(db, lasomin_comp, lasomin_venue_id, 18, "D")
        db.commit()
        cid = _add_competitor(db, lasomin_comp)
        competitor_repo.update_presence(db, cid, True)
        db.commit()
        with pytest.raises(ValueError, match="wykluczone"):
            service.assign_station(db, cid, 18, lasomin_venue_id, lasomin_comp)


class TestGetBalanceVariant:
    def test_variant_1_for_lasomin(self):
        v = get_balance_variant("Lasomin", 1)
        assert v == {"excluded": [18], "sector_overrides": {}}

    def test_variant_2_for_lasomin(self):
        v = get_balance_variant("Lasomin", 2)
        assert v == {"excluded": [17, 18], "sector_overrides": {"13": "D"}}

    def test_variant_3_for_lasomin(self):
        v = get_balance_variant("Lasomin", 3)
        assert v == {"excluded": [17, 18, 1], "sector_overrides": {"13": "D"}}

    def test_variant_0_returns_none(self):
        assert get_balance_variant("Lasomin", 0) is None

    def test_variant_4_returns_none_manual_fallback(self):
        # Lasomin spec doesn't define variant ≥4 — caller should treat as manual flow.
        assert get_balance_variant("Lasomin", 4) is None

    def test_stawy_has_no_variants(self):
        assert get_balance_variant("Stawy Siedleckie", 1) is None
        assert get_balance_variant("Stawy Siedleckie", 2) is None

    def test_unknown_venue_returns_none(self):
        assert get_balance_variant("Nieistniejące Łowisko", 1) is None


class TestReconcileCompetitorSectors:
    """Regression tests for the sector divergence flagged by architect/code review:
    after overrides change, already-assigned competitors must be re-stamped with
    the current effective sector_name so ranking uses the right sector."""

    def test_assign_then_add_override_reconciles_to_overridden_sector(
        self, db, service, lasomin_venue_id, lasomin_comp,
    ):
        cid = _add_competitor(db, lasomin_comp)
        competitor_repo.update_presence(db, cid, True)
        db.commit()

        # Assign first WITHOUT override → station 13 lands in C (venue default).
        service.assign_station(db, cid, 13, lasomin_venue_id, lasomin_comp)
        db.commit()
        assert competitor_repo.get_by_id(db, cid).sector_name == "C"

        # Now add override (Lasomin variant 2) and reconcile.
        competition_sector_overrides_repo.set_overrides(db, lasomin_comp, {13: "D"})
        db.commit()
        reconcile_competitor_sectors(db, lasomin_comp, lasomin_venue_id, service)
        db.commit()

        # Stored sector_name should track the override.
        assert competitor_repo.get_by_id(db, cid).sector_name == "D"

    def test_assign_with_override_then_clear_reconciles_to_default(
        self, db, service, lasomin_venue_id, lasomin_comp,
    ):
        cid = _add_competitor(db, lasomin_comp)
        competitor_repo.update_presence(db, cid, True)
        competition_sector_overrides_repo.set_overrides(db, lasomin_comp, {13: "D"})
        db.commit()

        service.assign_station(db, cid, 13, lasomin_venue_id, lasomin_comp)
        db.commit()
        assert competitor_repo.get_by_id(db, cid).sector_name == "D"

        # Clear override (e.g. user clicked "Przywróć wszystkie") and reconcile.
        competition_sector_overrides_repo.clear_overrides(db, lasomin_comp)
        db.commit()
        reconcile_competitor_sectors(db, lasomin_comp, lasomin_venue_id, service)
        db.commit()

        assert competitor_repo.get_by_id(db, cid).sector_name == "C"

    def test_reconcile_is_noop_for_unassigned_competitors(
        self, db, service, lasomin_venue_id, lasomin_comp,
    ):
        cid = _add_competitor(db, lasomin_comp)
        competitor_repo.update_presence(db, cid, True)
        db.commit()

        reconcile_competitor_sectors(db, lasomin_comp, lasomin_venue_id, service)
        db.commit()

        c = competitor_repo.get_by_id(db, cid)
        assert c.station_number is None
        assert c.sector_name is None

    def test_reconcile_does_not_touch_already_correct_assignments(
        self, db, service, lasomin_venue_id, lasomin_comp,
    ):
        cid = _add_competitor(db, lasomin_comp)
        competitor_repo.update_presence(db, cid, True)
        db.commit()

        service.assign_station(db, cid, 22, lasomin_venue_id, lasomin_comp)
        db.commit()
        assert competitor_repo.get_by_id(db, cid).sector_name == "D"

        reconcile_competitor_sectors(db, lasomin_comp, lasomin_venue_id, service)
        db.commit()

        # Station 22 has no override; should remain D.
        assert competitor_repo.get_by_id(db, cid).sector_name == "D"

    def test_reconcile_default_service_when_none_passed(
        self, db, lasomin_venue_id, lasomin_comp,
    ):
        # Smoke test: reconcile should construct its own SectorService when not given.
        cid = _add_competitor(db, lasomin_comp)
        competitor_repo.update_presence(db, cid, True)
        SectorService().assign_station(db, cid, 13, lasomin_venue_id, lasomin_comp)
        competition_sector_overrides_repo.set_overrides(db, lasomin_comp, {13: "D"})
        db.commit()

        reconcile_competitor_sectors(db, lasomin_comp, lasomin_venue_id)
        db.commit()

        assert competitor_repo.get_by_id(db, cid).sector_name == "D"


class TestMatchVariantForSelection:
    def test_exact_match_returns_variant_2(self):
        v = match_variant_for_selection("Lasomin", {17, 18})
        assert v is not None
        assert v["sector_overrides"] == {"13": "D"}

    def test_exact_match_returns_variant_3(self):
        v = match_variant_for_selection("Lasomin", {17, 18, 1})
        assert v is not None
        assert v["excluded"] == [17, 18, 1]
        assert v["sector_overrides"] == {"13": "D"}

    def test_no_match_for_random_selection(self):
        assert match_variant_for_selection("Lasomin", {17, 18, 5}) is None

    def test_no_match_for_empty_selection(self):
        assert match_variant_for_selection("Lasomin", set()) is None

    def test_skips_variants_without_overrides(self):
        # Variant 1 has empty sector_overrides → no UI prompt needed.
        # Even though selection {18} matches variant 1.excluded, return None.
        assert match_variant_for_selection("Lasomin", {18}) is None

    def test_stawy_never_matches(self):
        assert match_variant_for_selection("Stawy Siedleckie", {1, 2, 3}) is None

    def test_subset_does_not_match(self):
        # Selection must match `excluded` exactly (not subset/superset).
        assert match_variant_for_selection("Lasomin", {17}) is None
        assert match_variant_for_selection("Lasomin", {17, 18, 1, 5}) is None
