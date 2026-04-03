from tkinter import messagebox

import customtkinter as ctk

from app.repositories import excluded_station_repo, venue_repo
from app.services.sector_service import SectorService


class BalanceSectorsDialog(ctk.CTkToplevel):
    def __init__(self, master, app, competition_id, venue_id, on_confirm=None):
        super().__init__(master)
        self.app = app
        self.competition_id = competition_id
        self.venue_id = venue_id
        self.on_confirm = on_confirm
        self.sector_service = SectorService()
        self.selected_stations: set[tuple[str, int]] = set()
        self.station_buttons: dict[tuple[str, int], ctk.CTkButton] = {}

        self.title("Wyrównanie sektorów")
        self.geometry("700x550")
        self.resizable(False, False)

        conn = self.app.get_connection()
        try:
            self._load_data(conn)
            self._build_ui()
        finally:
            conn.close()

        self.transient(master)
        self.wait_visibility()
        self.grab_set()
        self.focus_set()

    def _load_data(self, conn):
        from app.repositories import competitor_repo
        competitors = competitor_repo.get_all(conn, self.competition_id)
        self.present_count = sum(1 for c in competitors if c.is_present)
        self.assigned_stations = {
            c.station_number for c in competitors if c.station_number is not None
        }

        self.already_excluded = excluded_station_repo.get_excluded(conn, self.competition_id)
        already_excluded_set = {
            (e["sector_name"], e["station_number"]) for e in self.already_excluded
        }

        all_sectors = venue_repo.get_sectors(conn, self.venue_id)
        sector_names = venue_repo.get_sector_names(conn, self.venue_id)

        self.total_stations = len(all_sectors)
        self.total_to_exclude = max(0, self.total_stations - self.present_count)
        self.sector_info: list[dict] = []
        for name in sector_names:
            stations = sorted(s.station_number for s in all_sectors if s.sector_name == name)
            self.sector_info.append({"name": name, "stations": stations})

        self.selected_stations = set(already_excluded_set)
        self.original_selection = set(self.selected_stations)

    def _build_ui(self):
        self.sector_labels: dict[str, ctk.CTkLabel] = {}

        header = ctk.CTkLabel(
            self,
            text=f"Obecnych: {self.present_count}    "
                 f"Stanowisk: {self.total_stations}    "
                 f"Do wykluczenia: {self.total_to_exclude}",
            font=("Segoe UI", 14, "bold"),
        )
        header.pack(padx=10, pady=(10, 5))

        scroll_frame = ctk.CTkScrollableFrame(self, width=660, height=370)
        scroll_frame.pack(padx=10, pady=5, fill="both", expand=True)

        for sector in self.sector_info:
            sector_frame = ctk.CTkFrame(scroll_frame)
            sector_frame.pack(fill="x", padx=5, pady=4)

            sector_excluded = sum(
                1 for s in sector["stations"]
                if (sector["name"], s) in self.selected_stations
            )
            effective = len(sector["stations"]) - sector_excluded
            label_text = f"Sektor {sector['name']} ({effective}/{len(sector['stations'])} stanowisk):"
            lbl = ctk.CTkLabel(
                sector_frame, text=label_text,
                font=("Segoe UI", 13, "bold"),
            )
            lbl.pack(anchor="w", padx=8, pady=(4, 2))
            self.sector_labels[sector["name"]] = lbl

            buttons_frame = ctk.CTkFrame(sector_frame, fg_color="transparent")
            buttons_frame.pack(fill="x", padx=8, pady=(0, 4))

            for station in sector["stations"]:
                key = (sector["name"], station)
                is_selected = key in self.selected_stations
                is_assigned = station in self.assigned_stations

                btn = ctk.CTkButton(
                    buttons_frame,
                    text=str(station),
                    width=45,
                    height=30,
                    font=("Segoe UI", 12),
                    command=lambda k=key: self._toggle_station(k),
                )
                btn.pack(side="left", padx=2, pady=2)
                self.station_buttons[key] = btn

                if is_assigned:
                    btn.configure(
                        fg_color="#5cb85c",
                        hover_color="#5cb85c",
                        state="disabled",
                    )
                elif is_selected:
                    btn.configure(fg_color="#d9534f", hover_color="#c9302c")

        self.counter_label = ctk.CTkLabel(
            self,
            text=self._counter_text(),
            font=("Segoe UI", 13, "bold"),
        )
        self.counter_label.pack(padx=10, pady=(5, 2))

        btn_frame = ctk.CTkFrame(self)
        btn_frame.pack(fill="x", padx=10, pady=(2, 10))

        self.confirm_btn = ctk.CTkButton(
            btn_frame, text="Zatwierdź", command=self._on_confirm, width=120,
        )
        self.confirm_btn.pack(side="left", padx=10)
        self._update_confirm_state()

        ctk.CTkButton(
            btn_frame, text="Anuluj", command=self.destroy, width=100,
        ).pack(side="left", padx=5)

        if self.selected_stations:
            ctk.CTkButton(
                btn_frame, text="Przywróć wszystkie", command=self._restore_all, width=160,
            ).pack(side="right", padx=10)

    def _toggle_station(self, key: tuple[str, int]):
        _, station_number = key
        if station_number in self.assigned_stations:
            return
        btn = self.station_buttons[key]
        if key in self.selected_stations:
            self.selected_stations.discard(key)
            btn.configure(fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"],
                          hover_color=ctk.ThemeManager.theme["CTkButton"]["hover_color"])
        else:
            if len(self.selected_stations) >= self.total_to_exclude:
                return
            self.selected_stations.add(key)
            btn.configure(fg_color="#d9534f", hover_color="#c9302c")
        self.counter_label.configure(text=self._counter_text())
        self._update_sector_label(key[0])
        self._update_confirm_state()

    def _update_sector_label(self, sector_name: str):
        sector = next(s for s in self.sector_info if s["name"] == sector_name)
        excluded_count = sum(
            1 for s in sector["stations"] if (sector_name, s) in self.selected_stations
        )
        effective = len(sector["stations"]) - excluded_count
        self.sector_labels[sector_name].configure(
            text=f"Sektor {sector_name} ({effective}/{len(sector['stations'])} stanowisk):"
        )

    def _update_confirm_state(self):
        changed = self.selected_stations != self.original_selection
        complete = len(self.selected_stations) >= self.total_to_exclude
        self.confirm_btn.configure(state="normal" if changed and complete else "disabled")

    def _counter_text(self) -> str:
        return f"Zaznaczono: {len(self.selected_stations)} / {self.total_to_exclude}"

    def _on_confirm(self):
        checked = list(self.selected_stations)

        if len(checked) < self.total_to_exclude:
            messagebox.showwarning(
                "Uwaga",
                f"Zaznacz {self.total_to_exclude} stanowisk do wykluczenia.",
                parent=self,
            )
            return

        sizes = list(self._compute_resulting_sizes(checked).values())
        diff = max(sizes) - min(sizes) if sizes else 0
        if diff > 1:
            msg = (
                f"Sektory nie będą równe (różnica: {diff}).\n\n"
                "Kontynuować?"
            )
            if not messagebox.askyesno("Uwaga", msg, parent=self):
                return

        conn = self.app.get_connection()
        try:
            excluded_station_repo.clear_excluded(conn, self.competition_id)
            for sector_name, station_number in checked:
                excluded_station_repo.add_excluded(
                    conn, self.competition_id, self.venue_id,
                    station_number, sector_name,
                )
            conn.commit()
        finally:
            conn.close()

        if self.on_confirm:
            self.on_confirm()
        self.destroy()

    def _compute_resulting_sizes(self, checked: list[tuple[str, int]]) -> dict[str, int]:
        checked_set = set(checked)
        sizes: dict[str, int] = {}
        for sector in self.sector_info:
            sizes[sector["name"]] = sum(
                1 for s in sector["stations"] if (sector["name"], s) not in checked_set
            )
        return sizes

    def _restore_all(self):
        conn = self.app.get_connection()
        try:
            excluded_station_repo.clear_excluded(conn, self.competition_id)
            conn.commit()
        finally:
            conn.close()

        if self.on_confirm:
            self.on_confirm()
        self.destroy()
