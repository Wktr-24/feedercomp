from tkinter import messagebox

import customtkinter as ctk

from app.repositories import venue_repo
from app.utils import normalize_whitespace


class VenueEditor(ctk.CTkFrame):
    def __init__(self, master, app, venue_id: int):
        super().__init__(master)
        self.app = app
        self.venue_id = venue_id
        self.sector_entries = {}
        self._build_ui()

    def _build_ui(self):
        conn = self.app.get_connection()
        try:
            venue = venue_repo.get_by_id(conn, self.venue_id)
            title = ctk.CTkLabel(self, text=f"Edytor łowiska: {venue.name}",
                                  font=("Segoe UI", 18, "bold"))
            title.pack(pady=10)

            info = ctk.CTkLabel(self, text="Wpisz numery stanowisk oddzielone przecinkami dla każdego sektora")
            info.pack(pady=5)

            sectors = venue_repo.get_sectors(conn, self.venue_id)
            sector_stations = {}
            for vs in sectors:
                sector_stations.setdefault(vs.sector_name, []).append(vs.station_number)

            form = ctk.CTkFrame(self)
            form.pack(fill="x", padx=20, pady=10)

            for sector_name in sorted(sector_stations.keys()):
                row = ctk.CTkFrame(form)
                row.pack(fill="x", pady=3)
                ctk.CTkLabel(row, text=f"Sektor {sector_name}:", width=100).pack(side="left")
                entry = ctk.CTkEntry(row, width=400)
                entry.pack(side="left", padx=5)
                stations_str = ", ".join(str(s) for s in sorted(sector_stations[sector_name]))
                entry.insert(0, stations_str)
                self.sector_entries[sector_name] = entry

            add_row = ctk.CTkFrame(form)
            add_row.pack(fill="x", pady=(10, 3))
            ctk.CTkLabel(add_row, text="Nowy sektor:").pack(side="left")
            self.new_sector_name = ctk.CTkEntry(add_row, width=50, placeholder_text="F")
            self.new_sector_name.pack(side="left", padx=5)
            self.new_sector_stations = ctk.CTkEntry(add_row, width=400, placeholder_text="51, 52, 53...")
            self.new_sector_stations.pack(side="left", padx=5)

            buttons = ctk.CTkFrame(self)
            buttons.pack(pady=10)
            ctk.CTkButton(buttons, text="Zapisz", command=self._save).pack(side="left", padx=5)
            ctk.CTkButton(buttons, text="Anuluj", command=self._cancel).pack(side="left", padx=5)
        finally:
            conn.close()

    def _save(self):
        sectors = {}
        for name, entry in self.sector_entries.items():
            text = entry.get().strip()
            if text:
                try:
                    stations = [int(s.strip()) for s in text.split(",") if s.strip()]
                    sectors[name] = stations
                except ValueError:
                    messagebox.showerror("Błąd", f"Nieprawidłowe numery stanowisk w sektorze {name}")
                    return

        new_name = normalize_whitespace(self.new_sector_name.get()).upper()
        new_stations_text = self.new_sector_stations.get().strip()
        if new_name and new_stations_text:
            try:
                sectors[new_name] = [int(s.strip()) for s in new_stations_text.split(",") if s.strip()]
            except ValueError:
                messagebox.showerror("Błąd", "Nieprawidłowe numery stanowisk w nowym sektorze")
                return

        all_stations = []
        for name, stations in sectors.items():
            for s in stations:
                if s in all_stations:
                    messagebox.showwarning("Błąd", f"Stanowisko {s} jest przypisane do więcej niż jednego sektora.")
                    return
                all_stations.append(s)

        conn = self.app.get_connection()
        try:
            venue_repo.update_sectors(conn, self.venue_id, sectors)
            total = sum(len(s) for s in sectors.values())
            conn.execute("UPDATE venues SET total_stations = ? WHERE id = ?", (total, self.venue_id))
            conn.commit()
            messagebox.showinfo("OK", "Konfiguracja sektorów zapisana")
            self.app.show_start_screen()
        finally:
            conn.close()

    def _cancel(self):
        self.app.show_start_screen()
