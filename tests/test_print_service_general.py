from app.services.print_service import PrintService
from tests.test_general_classification_service import _setup_day


class TestGeneralClassificationPdf:
    def test_pdf_generated_nonempty(self, db):
        # Covers the full path end-to-end, including ex-aequo and the
        # zero-weight "-" row (fonts fall back to Helvetica off-Windows).
        day1, _ = _setup_day(db, "2026-09-05", "Finał", {
            "A": [(1, "Adam", 3000), (2, "Beata", 2000), (3, "Zenon", 0)],
            "B": [(6, "Darek", 3000), (7, "Ewa", 2000), (8, "Zofia", 0)],
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
