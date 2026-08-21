from datetime import date, timedelta
from tkinter import messagebox

import customtkinter as ctk

from app.services.competition_service import Day2Error, create_day2
from app.ui.base_dialog import FeederCompDialog
from app.utils import normalize_whitespace

_DAY2_ERROR_MESSAGES = {
    "source_missing": "Zawody źródłowe nie istnieją.",
    "source_is_day2": "Te zawody są już dniem 2 — nie można tworzyć kolejnego dnia.",
    "already_has_day2": "Te zawody mają już utworzony dzień 2.",
}


def _default_day2_date(source_date: str) -> str:
    try:
        return (date.fromisoformat(source_date) + timedelta(days=1)).isoformat()
    except ValueError:
        return source_date


def _default_day2_name(source_name: str | None) -> str:
    return f"{source_name} — dzień 2" if source_name else ""


class CreateDay2Dialog(FeederCompDialog):
    """Create the day-2 competition of a two-day final, copying the roster
    from the source competition. Two editable fields; everything else
    (venue, winner_places, max_competitors, the link) comes from the source.
    """

    def __init__(self, master, app, source_competition, on_created=None):
        super().__init__(master, "Utwórz dzień 2", 400, 230)

        self.app = app
        self.source = source_competition
        self.on_created = on_created

        self._build_ui()
        self.show_modal()

    def _build_ui(self):
        ctk.CTkLabel(
            self,
            text=f"Dzień 2 dla: {self.source.name or 'Bez nazwy'} ({self.source.date})",
            font=("Segoe UI", 13),
        ).place(x=20, y=15)

        ctk.CTkLabel(self, text="Data (RRRR-MM-DD):", font=("Segoe UI", 14)).place(x=20, y=55)
        self.date_entry = ctk.CTkEntry(self, width=200)
        self.date_entry.place(x=180, y=55)
        self.date_entry.insert(0, _default_day2_date(self.source.date))

        ctk.CTkLabel(self, text="Nazwa zawodów:", font=("Segoe UI", 14)).place(x=20, y=100)
        self.name_entry = ctk.CTkEntry(self, width=200)
        self.name_entry.place(x=180, y=100)
        default_name = _default_day2_name(self.source.name)
        if default_name:
            self.name_entry.insert(0, default_name)

        ctk.CTkButton(
            self, text="Utwórz", command=self._on_create, width=110,
        ).place(x=75, y=165)
        ctk.CTkButton(
            self, text="Anuluj", command=self.destroy, width=110,
        ).place(x=215, y=165)

    def _on_create(self):
        from datetime import datetime
        comp_date = self.date_entry.get().strip()
        if not comp_date:
            messagebox.showwarning("Błąd", "Podaj datę.", parent=self)
            return
        try:
            datetime.strptime(comp_date, "%Y-%m-%d")
        except ValueError:
            messagebox.showwarning(
                "Błąd", "Nieprawidłowy format daty. Użyj RRRR-MM-DD.", parent=self,
            )
            return
        comp_name = normalize_whitespace(self.name_entry.get()) or None

        conn = self.app.get_connection()
        try:
            new_id, count = create_day2(conn, self.source.id, comp_date, comp_name)
        except Day2Error as e:
            messagebox.showwarning(
                "Błąd",
                _DAY2_ERROR_MESSAGES.get(e.reason, "Nie udało się utworzyć dnia 2."),
                parent=self,
            )
            return
        finally:
            conn.close()

        messagebox.showinfo(
            "Dzień 2",
            f"Utworzono dzień 2.\nSkopiowano {count} zawodników.",
            parent=self,
        )
        on_created = self.on_created
        venue_id = self.source.venue_id
        self.destroy()
        if on_created:
            on_created(new_id, venue_id)
