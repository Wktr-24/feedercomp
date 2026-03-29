import sqlite3
from tkinter import messagebox, ttk

import customtkinter as ctk

from app.repositories import competitor_repo
from app.services.sector_service import SectorService

_PAYMENT_LABELS = {
    "paid": "TAK",
    "on_site": "Na miejscu",
    "unpaid": "Nie",
}

_PAYMENT_VALUES = ["unpaid", "on_site", "paid"]
_PAYMENT_DISPLAY = ["Nie", "Na miejscu", "TAK"]

_COLUMNS = ("nr", "name", "phone", "payment", "present", "station", "sector")
_HEADINGS = ("Nr", "Imi\u0119 i Nazwisko", "Telefon", "Op\u0142ata", "Obecny", "Stanowisko", "Sektor")
_WIDTHS = (50, 220, 120, 90, 70, 90, 70)


class CompetitorsScreen(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.sector_service = SectorService()
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

        ctk.CTkLabel(form, text="Numer:", font=("Segoe UI", 14)).pack(side="left", padx=(10, 2))
        self.number_entry = ctk.CTkEntry(form, width=60)
        self.number_entry.pack(side="left", padx=2)

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

        ctk.CTkLabel(search_frame, text="Szukaj:", font=("Segoe UI", 14)).pack(side="left", padx=(10, 2))
        self.search_entry = ctk.CTkEntry(search_frame, width=250, placeholder_text="wpisz nazwisko...")
        self.search_entry.pack(side="left", padx=2)
        self.search_entry.bind("<KeyRelease>", lambda _: self._refresh_table())

    # -- Table --

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
            anchor = "center" if col in ("nr", "payment", "present", "station", "sector") else "w"
            self.tree.column(col, width=width, minwidth=40, anchor=anchor)

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.tag_configure("even", background="#f0f0f0")
        self.tree.tag_configure("odd", background="#ffffff")

        self.tree.bind("<Double-1>", self._on_double_click)

    # -- Actions --

    def _build_actions(self):
        actions = ctk.CTkFrame(self)
        actions.pack(fill="x", padx=5, pady=(2, 5))

        ctk.CTkLabel(actions, text="Stanowisko:", font=("Segoe UI", 14)).pack(side="left", padx=(10, 2))
        self.station_entry = ctk.CTkEntry(actions, width=60)
        self.station_entry.pack(side="left", padx=2)
        ctk.CTkButton(
            actions, text="Przypisz stanowisko", command=self._assign_station, width=160,
        ).pack(side="left", padx=(5, 20))

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
            if query:
                competitors = competitor_repo.search_by_name(conn, self.app.competition_id, query)
            else:
                competitors = competitor_repo.get_all(conn, self.app.competition_id)
        finally:
            conn.close()

        for i, c in enumerate(competitors):
            tag = "even" if i % 2 == 0 else "odd"
            self.tree.insert("", "end", iid=str(c.id), tags=(tag,), values=(
                c.list_number,
                c.full_name,
                c.phone or "",
                _PAYMENT_LABELS.get(c.payment_status, c.payment_status),
                "Tak" if c.is_present else "Nie",
                c.station_number or "",
                c.sector_name or "",
            ))

    def _add_competitor(self):
        num_str = self.number_entry.get().strip()
        name = self.name_entry.get().strip()

        if not num_str or not name:
            messagebox.showwarning("B\u0142\u0105d", "Numer i nazwisko s\u0105 wymagane.")
            return

        try:
            list_number = int(num_str)
        except ValueError:
            messagebox.showwarning("B\u0142\u0105d", "Numer musi by\u0107 liczb\u0105.")
            return

        phone = self.phone_entry.get().strip() or None
        display_payment = self.payment_var.get()
        idx = _PAYMENT_DISPLAY.index(display_payment) if display_payment in _PAYMENT_DISPLAY else 0
        payment_status = _PAYMENT_VALUES[idx]

        conn = self.app.get_connection()
        try:
            competitor_repo.add(conn, self.app.competition_id, list_number, name, phone, payment_status)
        except sqlite3.IntegrityError:
            messagebox.showwarning("B\u0142\u0105d", f"Numer {list_number} jest ju\u017c zaj\u0119ty.")
            return
        finally:
            conn.close()

        self.number_entry.delete(0, "end")
        self.name_entry.delete(0, "end")
        self.phone_entry.delete(0, "end")
        self.payment_var.set(_PAYMENT_DISPLAY[0])
        self._refresh_table()

    def _on_double_click(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return

        competitor_id = int(item)
        conn = self.app.get_connection()
        try:
            competitor = competitor_repo.get_by_id(conn, competitor_id)
            if competitor:
                competitor_repo.update_presence(conn, competitor_id, not competitor.is_present)
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
            self.sector_service.assign_station(conn, competitor_id, station_number, self.app.venue_id)
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
