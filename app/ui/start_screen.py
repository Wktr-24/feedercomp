from datetime import date, datetime
from tkinter import messagebox

import customtkinter as ctk

from app.repositories import venue_repo, competition_repo


class StartScreen(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self._build_ui()

    def _build_ui(self):
        title = ctk.CTkLabel(self, text="FeederComp", font=("Segoe UI", 32, "bold"))
        title.pack(pady=(30, 5))

        subtitle = ctk.CTkLabel(self, text="Zawody W\u0119dkarskie", font=("Segoe UI", 16))
        subtitle.pack(pady=(0, 30))

        columns = ctk.CTkFrame(self)
        columns.pack(fill="both", expand=True, padx=40)
        columns.columnconfigure(0, weight=1)
        columns.columnconfigure(1, weight=1)

        self._build_new_competition(columns)
        self._build_resume_competition(columns)

    def _build_new_competition(self, parent):
        frame = ctk.CTkFrame(parent)
        frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=5)

        ctk.CTkLabel(frame, text="Nowe zawody", font=("Segoe UI", 18, "bold")).pack(pady=(15, 10))

        conn = self.app.get_connection()
        try:
            venues = venue_repo.get_all(conn)
        finally:
            conn.close()

        self.venue_map = {v.name: v for v in venues}
        venue_names = [v.name for v in venues]

        ctk.CTkLabel(frame, text="\u0141owisko:", font=("Segoe UI", 14)).pack(padx=15, anchor="w")
        self.venue_var = ctk.StringVar(value=venue_names[0] if venue_names else "")
        venue_row = ctk.CTkFrame(frame)
        venue_row.pack(fill="x", padx=15, pady=(0, 8))
        venue_menu = ctk.CTkOptionMenu(venue_row, variable=self.venue_var, values=venue_names, width=220)
        venue_menu.pack(side="left")
        ctk.CTkButton(
            venue_row, text="Edytuj łowisko", width=100,
            command=self._edit_venue,
        ).pack(side="left", padx=(5, 0))

        ctk.CTkLabel(frame, text="Data (RRRR-MM-DD):", font=("Segoe UI", 14)).pack(padx=15, anchor="w")
        self.date_entry = ctk.CTkEntry(frame, width=280)
        self.date_entry.insert(0, date.today().isoformat())
        self.date_entry.pack(padx=15, pady=(0, 8))

        ctk.CTkLabel(frame, text="Nazwa zawod\u00f3w:", font=("Segoe UI", 14)).pack(padx=15, anchor="w")
        self.name_entry = ctk.CTkEntry(frame, width=280)
        self.name_entry.pack(padx=15, pady=(0, 8))

        limits_row = ctk.CTkFrame(frame)
        limits_row.pack(fill="x", padx=15, pady=(0, 15))
        ctk.CTkLabel(limits_row, text="Miejsc nagrodzonych:", font=("Segoe UI", 14)).pack(side="left")
        self.winner_places_entry = ctk.CTkEntry(limits_row, width=60)
        self.winner_places_entry.insert(0, "3")
        self.winner_places_entry.pack(side="left", padx=(2, 0))

        ctk.CTkButton(frame, text="Utw\u00f3rz", command=self._create_competition, width=200).pack(pady=(0, 20))

    def _build_resume_competition(self, parent):
        frame = ctk.CTkFrame(parent)
        frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=5)

        ctk.CTkLabel(frame, text="Wzn\u00f3w zawody", font=("Segoe UI", 18, "bold")).pack(pady=(15, 10))

        self.competitions_frame = ctk.CTkScrollableFrame(frame)
        self.competitions_frame.pack(fill="both", expand=True, padx=10, pady=(0, 15))

        self._refresh_competitions_list()

    def _refresh_competitions_list(self):
        for w in self.competitions_frame.winfo_children():
            w.destroy()

        conn = self.app.get_connection()
        try:
            competitions = competition_repo.get_all(conn)
            venues = {v.id: v.name for v in venue_repo.get_all(conn)}
        finally:
            conn.close()

        if not competitions:
            ctk.CTkLabel(
                self.competitions_frame,
                text="Brak zapisanych zawod\u00f3w",
                font=("Segoe UI", 13),
                text_color="gray",
            ).pack(pady=20)
            return

        for comp in competitions:
            row = ctk.CTkFrame(self.competitions_frame)
            row.pack(fill="x", pady=2)

            venue_name = venues.get(comp.venue_id, "?")
            label_text = f"{comp.date} \u2013 {comp.name or 'Bez nazwy'} ({venue_name})"
            ctk.CTkLabel(row, text=label_text, font=("Segoe UI", 13)).pack(side="left", padx=5)

            btn = ctk.CTkButton(
                row,
                text="Otw\u00f3rz",
                width=80,
                command=lambda c=comp: self._open_competition(c),
            )
            btn.pack(side="right", padx=5, pady=2)

    def _create_competition(self):
        venue_name = self.venue_var.get()
        if not venue_name or venue_name not in self.venue_map:
            messagebox.showwarning("B\u0142\u0105d", "Wybierz \u0142owisko.")
            return

        comp_date = self.date_entry.get().strip()
        if not comp_date:
            messagebox.showwarning("Błąd", "Podaj datę.")
            return
        try:
            datetime.strptime(comp_date, "%Y-%m-%d")
        except ValueError:
            messagebox.showwarning("Błąd", "Nieprawidłowy format daty. Użyj RRRR-MM-DD.")
            return

        try:
            winner_places = int(self.winner_places_entry.get().strip())
            if winner_places < 1:
                raise ValueError
        except ValueError:
            messagebox.showwarning("B\u0142\u0105d", "Miejsc nagrodzonych musi by\u0107 liczb\u0105 dodatni\u0105.")
            return

        comp_name = self.name_entry.get().strip() or None
        venue = self.venue_map[venue_name]

        conn = self.app.get_connection()
        try:
            comp_id = competition_repo.create(
                conn, venue.id, comp_date, comp_name,
                max_competitors=venue.total_stations, winner_places=winner_places,
            )
        finally:
            conn.close()

        self.app.on_competition_selected(comp_id, venue.id)

    def _edit_venue(self):
        venue_name = self.venue_var.get()
        if not venue_name or venue_name not in self.venue_map:
            messagebox.showwarning("Błąd", "Wybierz łowisko.")
            return
        venue = self.venue_map[venue_name]
        self.app.show_venue_editor(venue.id)

    def _open_competition(self, competition):
        self.app.on_competition_selected(competition.id, competition.venue_id)
