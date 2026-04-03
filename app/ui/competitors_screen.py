import sqlite3
from tkinter import messagebox, ttk

import customtkinter as ctk

from app.repositories import competitor_repo, competition_repo
from app.services.sector_service import SectorService

_PAYMENT_LABELS = {
    "paid": "TAK",
    "on_site": "Na miejscu",
}

_PAYMENT_VALUES = ["paid", "on_site"]
_PAYMENT_DISPLAY = ["TAK", "Na miejscu"]

_COLUMNS = ("nr", "name", "phone", "payment", "present", "station", "sector")
_HEADINGS = ("Nr", "Imi\u0119 i Nazwisko", "Telefon", "Op\u0142ata", "Obecny", "Stanowisko", "Sektor")
_WIDTHS = (50, 220, 120, 90, 70, 90, 70)


class CompetitorsScreen(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.sector_service = SectorService()
        conn = self.app.get_connection()
        try:
            competition = competition_repo.get_by_id(conn, self.app.competition_id)
        finally:
            conn.close()
        self.max_competitors = competition.max_competitors if competition else 50
        self._build_ui()
        self._refresh_table()

    def _build_ui(self):
        self._build_add_form()
        self._build_search()
        self._build_table()
        self._build_actions()

    # -- Add form --

    def _build_add_form(self):
        form = ctk.CTkFrame(self)
        form.pack(fill="x", padx=5, pady=(5, 2))

        ctk.CTkLabel(form, text="Imi\u0119 i Nazwisko:", font=("Segoe UI", 14)).pack(side="left", padx=(10, 2))
        self.name_entry = ctk.CTkEntry(form, width=200)
        self.name_entry.pack(side="left", padx=2)

        ctk.CTkLabel(form, text="Telefon:", font=("Segoe UI", 14)).pack(side="left", padx=(10, 2))
        self.phone_entry = ctk.CTkEntry(form, width=120)
        self.phone_entry.pack(side="left", padx=2)

        ctk.CTkLabel(form, text="Op\u0142ata:", font=("Segoe UI", 14)).pack(side="left", padx=(10, 2))
        self.payment_var = ctk.StringVar(value=_PAYMENT_DISPLAY[0])
        payment_menu = ctk.CTkOptionMenu(
            form, variable=self.payment_var, values=_PAYMENT_DISPLAY, width=120,
        )
        payment_menu.pack(side="left", padx=2)

        ctk.CTkButton(form, text="Dodaj", command=self._add_competitor, width=80).pack(side="left", padx=(15, 10))

    # -- Search --

    def _build_search(self):
        search_frame = ctk.CTkFrame(self)
        search_frame.pack(fill="x", padx=5, pady=2)

        self.counter_label = ctk.CTkLabel(
            search_frame, text="", font=("Segoe UI", 14, "bold"),
        )
        self.counter_label.pack(side="right", padx=(10, 10))

        ctk.CTkLabel(search_frame, text="Szukaj:", font=("Segoe UI", 14)).pack(side="left", padx=(10, 2))
        self.search_entry = ctk.CTkEntry(search_frame, width=250, placeholder_text="wpisz nazwisko...")
        self.search_entry.pack(side="left", padx=2)
        self.search_entry.bind("<KeyRelease>", lambda _: self._refresh_table())
        self.clear_btn = ctk.CTkButton(
            search_frame, text="✕", width=30, height=28,
            command=self._clear_search,
        )
        self.clear_btn.pack(side="left", padx=2)

    # -- Table --

    def _clear_search(self):
        self.search_entry.delete(0, "end")
        self._refresh_table()

    def _build_table(self):
        table_frame = ctk.CTkFrame(self)
        table_frame.pack(fill="both", expand=True, padx=5, pady=2)

        style = ttk.Style()
        style.configure("Treeview", font=("Segoe UI", 13), rowheight=28)
        style.configure("Treeview.Heading", font=("Segoe UI", 13, "bold"))

        self.tree = ttk.Treeview(
            table_frame,
            columns=_COLUMNS,
            show="headings",
            selectmode="browse",
        )

        for col, heading, width in zip(_COLUMNS, _HEADINGS, _WIDTHS):
            self.tree.heading(col, text=heading)
            anchor = "center" if col in ("nr", "phone", "payment", "present", "station", "sector") else "w"
            self.tree.column(col, width=width, minwidth=40, anchor=anchor)

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.tag_configure("even", background="#f0f0f0")
        self.tree.tag_configure("odd", background="#ffffff")
        self.tree.tag_configure("reserve", background="#fff3cd")

        self.tree.bind("<Double-1>", self._on_double_click)

    # -- Actions --

    def _build_actions(self):
        actions = ctk.CTkFrame(self)
        actions.pack(fill="x", padx=5, pady=(2, 5))

        ctk.CTkButton(
            actions, text="Wszyscy obecni", command=self._set_all_present, width=140,
        ).pack(side="left", padx=(10, 5))

        ctk.CTkButton(
            actions, text="Przełącz obecność", command=self._toggle_presence, width=150,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            actions, text="Wyrównaj sektory", command=self._balance_sectors, width=150,
        ).pack(side="left", padx=5)

        ctk.CTkLabel(actions, text="Stanowisko:", font=("Segoe UI", 14)).pack(side="left", padx=(15, 2))
        self.station_entry = ctk.CTkEntry(actions, width=60)
        self.station_entry.pack(side="left", padx=2)
        ctk.CTkButton(
            actions, text="Przypisz", command=self._assign_station, width=100,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            actions, text="Usu\u0144 zaznaczonego", command=self._delete_selected, width=150,
            fg_color="#d9534f", hover_color="#c9302c",
        ).pack(side="right", padx=10)

    # -- Data operations --

    def _refresh_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        query = self.search_entry.get().strip() if hasattr(self, "search_entry") else ""

        conn = self.app.get_connection()
        try:
            if len(query) >= 2:
                competitors = competitor_repo.search_by_name(conn, self.app.competition_id, query)
            else:
                competitors = competitor_repo.get_all(conn, self.app.competition_id)
        finally:
            conn.close()

        if not query and hasattr(self, "counter_label"):
            reserve_list = competitors[self.max_competitors:]
            total_present = sum(1 for c in competitors if c.is_present)
            counter_text = f"Obecnych: {total_present} / {self.max_competitors}"
            reserve_on_site = sum(1 for c in reserve_list if c.is_present)
            if reserve_on_site > 0:
                counter_text += f"  |  Rezerwa: {reserve_on_site}"
            self.counter_label.configure(text=counter_text)

        for i, c in enumerate(competitors):
            is_reserve = not query and i >= self.max_competitors
            if is_reserve:
                tag = "reserve"
            else:
                tag = "even" if i % 2 == 0 else "odd"
            self.tree.insert("", "end", iid=str(c.id), tags=(tag,), values=(
                c.list_number,
                c.full_name,
                c.phone or "",
                _PAYMENT_LABELS.get(c.payment_status, c.payment_status),
                "Tak" if c.is_present else "Nie",
                "" if c.station_number is None else c.station_number,
                "" if c.sector_name is None else c.sector_name,
            ))

    def _add_competitor(self):
        name = self.name_entry.get().strip()

        if not name:
            messagebox.showwarning("Błąd", "Imię i nazwisko jest wymagane.")
            return

        phone = self.phone_entry.get().strip() or None
        if phone and (len(phone) != 9 or not phone.isdigit()):
            messagebox.showwarning("Błąd", "Numer telefonu musi mieć dokładnie 9 cyfr.")
            return
        display_payment = self.payment_var.get()
        idx = _PAYMENT_DISPLAY.index(display_payment) if display_payment in _PAYMENT_DISPLAY else 0
        payment_status = _PAYMENT_VALUES[idx]

        conn = self.app.get_connection()
        try:
            competitors = competitor_repo.get_all(conn, self.app.competition_id)
            list_number = max((c.list_number for c in competitors), default=0) + 1
        finally:
            conn.close()

        if len(competitors) >= self.max_competitors:
            messagebox.showinfo(
                "Lista rezerwowa",
                f"Zawodnik zostanie dodany na listę rezerwową (limit: {self.max_competitors}).",
            )

        conn = self.app.get_connection()
        try:
            competitor_repo.add(conn, self.app.competition_id, list_number, name, phone, payment_status)
        finally:
            conn.close()

        self.name_entry.delete(0, "end")
        self.phone_entry.delete(0, "end")
        self.payment_var.set(_PAYMENT_DISPLAY[0])
        self._refresh_table()

    def _toggle_presence(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Błąd", "Zaznacz zawodnika.")
            return

        competitor_id = int(selection[0])
        conn = self.app.get_connection()
        try:
            competitor = competitor_repo.get_by_id(conn, competitor_id)
            if not competitor:
                return
            if not competitor.is_present:
                present_count = sum(
                    1 for c in competitor_repo.get_all(conn, self.app.competition_id)
                    if c.is_present
                )
                if present_count >= self.max_competitors:
                    messagebox.showwarning(
                        "Błąd",
                        f"Osiągnięto limit obecnych ({self.max_competitors}). "
                        "Odznacz kogoś innego, aby zwolnić miejsce.",
                    )
                    return
            else:
                if competitor.station_number is not None:
                    if not messagebox.askyesno(
                        "Potwierdzenie",
                        f"Zawodnik ma przypisane stanowisko {competitor.station_number}. "
                        "Usunąć przypisanie?",
                    ):
                        return
                    competitor_repo.update_station(conn, competitor_id, None, None)
            competitor_repo.update_presence(conn, competitor_id, not competitor.is_present)
        finally:
            conn.close()
        self._refresh_table()

    def _set_all_present(self):
        if not messagebox.askyesno(
            "Potwierdzenie",
            f"Oznaczyć pierwszych {self.max_competitors} zawodników jako obecnych?",
        ):
            return

        conn = self.app.get_connection()
        try:
            competitor_repo.set_all_present(conn, self.app.competition_id, limit=self.max_competitors)
        finally:
            conn.close()
        self._refresh_table()

    def _assign_station(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("B\u0142\u0105d", "Zaznacz zawodnika w tabeli.")
            return

        station_str = self.station_entry.get().strip()
        if not station_str:
            messagebox.showwarning("B\u0142\u0105d", "Wpisz numer stanowiska.")
            return

        try:
            station_number = int(station_str)
        except ValueError:
            messagebox.showwarning("B\u0142\u0105d", "Numer stanowiska musi by\u0107 liczb\u0105.")
            return

        competitor_id = int(selection[0])
        conn = self.app.get_connection()
        try:
            competitor = competitor_repo.get_by_id(conn, competitor_id)
            if competitor and not competitor.is_present:
                messagebox.showwarning("Błąd", "Nie można przypisać stanowiska nieobecnemu zawodnikowi.")
                return
            self.sector_service.assign_station(conn, competitor_id, station_number, self.app.venue_id, self.app.competition_id)
        except ValueError as e:
            messagebox.showwarning("Błąd", str(e))
            return
        except sqlite3.IntegrityError:
            messagebox.showwarning("B\u0142\u0105d", f"Stanowisko {station_number} jest ju\u017c zaj\u0119te.")
            return
        finally:
            conn.close()

        self.station_entry.delete(0, "end")
        self._refresh_table()

    def _delete_selected(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("B\u0142\u0105d", "Zaznacz zawodnika do usuni\u0119cia.")
            return

        competitor_id = int(selection[0])
        conn = self.app.get_connection()
        try:
            competitor = competitor_repo.get_by_id(conn, competitor_id)
            if not competitor:
                return
        finally:
            conn.close()

        if not messagebox.askyesno("Potwierdzenie", f"Usun\u0105\u0107 zawodnika {competitor.full_name}?"):
            return

        conn = self.app.get_connection()
        try:
            competitor_repo.delete(conn, competitor_id)
        finally:
            conn.close()

        self._refresh_table()

    def _on_double_click(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return

        competitor_id = int(item)
        conn = self.app.get_connection()
        try:
            competitor = competitor_repo.get_by_id(conn, competitor_id)
        finally:
            conn.close()

        if not competitor:
            return

        from app.ui.edit_competitor_dialog import EditCompetitorDialog
        EditCompetitorDialog(self, self.app, competitor, on_save=self._refresh_table)

    def _balance_sectors(self):
        from app.ui.balance_sectors_dialog import BalanceSectorsDialog
        BalanceSectorsDialog(
            self, self.app, self.app.competition_id, self.app.venue_id,
            on_confirm=self._refresh_table,
        )
