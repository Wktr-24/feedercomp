from app.repositories import competitor_repo


def _make_competition(db, venue_name="Stawy Siedleckie"):
    venue_id = db.execute("SELECT id FROM venues WHERE name = ?", (venue_name,)).fetchone()["id"]
    cursor = db.execute(
        "INSERT INTO competitions (venue_id, date, name) VALUES (?, ?, ?)",
        (venue_id, "2026-04-10", "Delete renumber test"),
    )
    db.commit()
    return cursor.lastrowid


def _numbers(db, competition_id):
    rows = db.execute(
        "SELECT list_number FROM competitors WHERE competition_id = ? ORDER BY list_number",
        (competition_id,),
    ).fetchall()
    return [r["list_number"] for r in rows]


class TestDeleteRenumber:
    def test_delete_middle_renumbers_remaining(self, db):
        comp_id = _make_competition(db)
        ids = []
        for i in range(1, 6):
            cid = competitor_repo.add(db, comp_id, i, f"Person {i}")
            ids.append(cid)
        db.commit()

        competitor_repo.delete(db, ids[2])  # delete list_number=3
        db.commit()

        assert _numbers(db, comp_id) == [1, 2, 3, 4]

        remaining = db.execute(
            "SELECT id, list_number, full_name FROM competitors WHERE competition_id = ? ORDER BY list_number",
            (comp_id,),
        ).fetchall()
        assert remaining[0]["full_name"] == "Person 1"
        assert remaining[1]["full_name"] == "Person 2"
        # Person 4 was shifted from 4 to 3
        assert remaining[2]["full_name"] == "Person 4"
        assert remaining[2]["list_number"] == 3
        assert remaining[3]["full_name"] == "Person 5"
        assert remaining[3]["list_number"] == 4

    def test_delete_first_renumbers_all(self, db):
        comp_id = _make_competition(db)
        ids = [competitor_repo.add(db, comp_id, i, f"Person {i}") for i in range(1, 6)]
        db.commit()

        competitor_repo.delete(db, ids[0])
        db.commit()

        assert _numbers(db, comp_id) == [1, 2, 3, 4]
        # Person 2 is now at list_number 1
        first = db.execute(
            "SELECT full_name FROM competitors WHERE competition_id = ? AND list_number = 1",
            (comp_id,),
        ).fetchone()
        assert first["full_name"] == "Person 2"

    def test_delete_last_does_not_renumber(self, db):
        comp_id = _make_competition(db)
        ids = [competitor_repo.add(db, comp_id, i, f"Person {i}") for i in range(1, 6)]
        db.commit()

        competitor_repo.delete(db, ids[4])
        db.commit()

        assert _numbers(db, comp_id) == [1, 2, 3, 4]

    def test_delete_preserves_presence_and_station(self, db):
        comp_id = _make_competition(db)
        ids = [competitor_repo.add(db, comp_id, i, f"Person {i}") for i in range(1, 6)]
        # Person 5 has presence + station + sector + weight
        competitor_repo.update_presence(db, ids[4], True)
        competitor_repo.update_station(db, ids[4], 10, "B")
        competitor_repo.update_weight(db, ids[4], 1234)
        db.commit()

        competitor_repo.delete(db, ids[1])  # delete list_number=2
        db.commit()

        # Person 5 should now have list_number=4, but all other fields preserved
        person5 = competitor_repo.get_by_id(db, ids[4])
        assert person5.list_number == 4
        assert person5.is_present is True
        assert person5.station_number == 10
        assert person5.sector_name == "B"
        assert person5.weight_grams == 1234

    def test_delete_multiple_in_sequence(self, db):
        comp_id = _make_competition(db)
        ids = [competitor_repo.add(db, comp_id, i, f"Person {i}") for i in range(1, 6)]
        db.commit()

        # Delete Person 2 (list_number=2). Remaining: 1, 3, 4, 5 → renumbered to 1, 2, 3, 4
        competitor_repo.delete(db, ids[1])
        db.commit()
        assert _numbers(db, comp_id) == [1, 2, 3, 4]

        # Now delete Person 4 (which had list_number=3 after first delete).
        competitor_repo.delete(db, ids[3])
        db.commit()
        assert _numbers(db, comp_id) == [1, 2, 3]

        remaining = db.execute(
            "SELECT full_name FROM competitors WHERE competition_id = ? ORDER BY list_number",
            (comp_id,),
        ).fetchall()
        assert [r["full_name"] for r in remaining] == ["Person 1", "Person 3", "Person 5"]

    def test_delete_reserve_promotes_next(self, db):
        comp_id = _make_competition(db)
        # 52 people: 1..50 main list, 51/52 reserve
        ids = [competitor_repo.add(db, comp_id, i, f"Person {i}") for i in range(1, 53)]
        db.commit()

        # Delete someone from main list
        competitor_repo.delete(db, ids[24])  # Person 25
        db.commit()

        numbers = _numbers(db, comp_id)
        assert numbers == list(range(1, 52))  # contiguous 1..51

        # Person 51 (was at list_number=51) is now at list_number=50
        person51 = competitor_repo.get_by_id(db, ids[50])
        assert person51.list_number == 50
        assert person51.full_name == "Person 51"

    def test_delete_competitor_with_assigned_station(self, db):
        comp_id = _make_competition(db)
        ids = [competitor_repo.add(db, comp_id, i, f"Person {i}") for i in range(1, 4)]
        # Person 2 has station + sector + weight
        competitor_repo.update_station(db, ids[1], 5, "A")
        competitor_repo.update_weight(db, ids[1], 500)
        db.commit()

        competitor_repo.delete(db, ids[1])
        db.commit()

        # Verify person 2 is gone (station 5 should be free again)
        assert _numbers(db, comp_id) == [1, 2]
        assert competitor_repo.get_by_id(db, ids[1]) is None

        # Person 3 should renumber to 2 and keep empty station
        person3 = competitor_repo.get_by_id(db, ids[2])
        assert person3.list_number == 2
        assert person3.station_number is None

        # Station 5 should be reusable: assign it to Person 3 without conflict
        competitor_repo.update_station(db, ids[2], 5, "A")
        db.commit()
        person3 = competitor_repo.get_by_id(db, ids[2])
        assert person3.station_number == 5

    def test_delete_nonexistent_is_noop(self, db):
        comp_id = _make_competition(db)
        competitor_repo.add(db, comp_id, 1, "Person 1")
        db.commit()

        competitor_repo.delete(db, 99999)
        db.commit()

        assert _numbers(db, comp_id) == [1]
