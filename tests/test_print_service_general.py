from app.services import print_service
from app.services.print_service import PrintService
from tests.test_general_classification_service import _setup_day


class TestGeneralClassificationPdf:
    def test_pdf_generated_nonempty(self, db):
        # Covers the full path end-to-end, including ex-aequo, the
        # zero-weight "-" row and a DYSKWALIFIKACJA row for a one-day
        # participant (fonts fall back to Helvetica off-Windows).
        day1, _ = _setup_day(db, "2026-09-05", "Finał", {
            "A": [(1, "Adam", 3000), (2, "Beata", 2000), (3, "Zenon", 0)],
            "B": [(6, "Darek", 3000), (7, "Ewa", 2000), (8, "Zofia", 0),
                  (9, "Tylko Jeden Dzień", 500)],
        })
        day2, _ = _setup_day(db, "2026-09-06", "Finał — dzień 2", {
            "A": [(1, "Adam", 1000), (2, "Beata", 1000), (3, "Zenon", 0)],
            "B": [(6, "Darek", 1000), (7, "Ewa", 1000), (8, "Zofia", 0)],
        }, linked_to=day1)

        ps = PrintService()
        path = ps.generate_general_classification_pdf(
            db, day1, day2, "Stawy Siedleckie — Finał",
            "2026-09-05", "2026-09-06", "Finał",
        )

        assert path.exists()
        assert path.stat().st_size > 0
        # Dated filename: archive per print + no PermissionError when a
        # viewer still holds a previous file open.
        assert path.name.startswith("Klasyfikacja_generalna_")
        assert path.name.endswith(".pdf")

    def test_dq_row_content_reaches_the_table(self, db, monkeypatch):
        # The service tests pin WHO is disqualified; this pins that the
        # PDF actually renders the row — below the zero-weight "-" rows,
        # with the fished day's points, "-" for the missing day, the
        # duplicated total and the kg-formatted weight. No PDF parsing:
        # spy on the Table data matrix instead.
        day1, _ = _setup_day(db, "2026-09-05", "Finał", {
            "A": [(1, "Adam", 3000), (2, "Zenon", 0)],
            "B": [(6, "Darek", 3000), (7, "Ewa", 2000),
                  (8, "Tylko Jeden Dzień", 500)],
        })
        day2, _ = _setup_day(db, "2026-09-06", "Finał — dzień 2", {
            "A": [(1, "Adam", 1000), (2, "Zenon", 0)],
            "B": [(6, "Darek", 1000), (7, "Ewa", 900)],
        }, linked_to=day1)

        captured = {}
        real_table = print_service.Table

        def spy_table(data, **kwargs):
            captured["data"] = data
            return real_table(data, **kwargs)

        monkeypatch.setattr(print_service, "Table", spy_table)
        PrintService().generate_general_classification_pdf(
            db, day1, day2, "Stawy Siedleckie — Finał",
            "2026-09-05", "2026-09-06", "Finał",
        )

        data = captured["data"]
        # 500 g was 3rd of 3 in day-1 sector B -> 3 pts on the day fished.
        assert data[-1] == [
            "DYSKWALIFIKACJA", "Tylko Jeden Dzień", "3", "-", "3", "0,500",
        ]
        # The DQ block sits below the zero-weight "-" row (Zenon).
        assert data[-2][0] == "-"
