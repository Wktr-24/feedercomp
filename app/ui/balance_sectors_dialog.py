from tkinter import messagebox

import customtkinter as ctk

from app.repositories import excluded_station_repo, venue_repo
from app.services.sector_service import SectorService


class BalanceSectorsDialog(ctk.CTkToplevel):
    def __init__(self, master, app, competition_id, venue_id, on_confirm=None):
        super().__init__(master)
        self.withdraw()

        self.app = app
        self.competition_id = competition_id
        self.venue_id = venue_id
        self.on_confirm = on_confirm
        self.sector_service = SectorService()
        self.selected_stations: set[tuple[str, int]] = set()
        self.station_buttons: dict[tuple[str, int], ctk.CTkButton] = {}

        self.title("Wyrównanie sektorów")
        self.geometry("1100x500")
        self.resizable(False, False)

        conn = self.app.get_connection()
        try:
            self._load_data(conn)
            self._build_ui()
        finally:
            conn.close()

        self.transient(master)
        self.update_idletasks()
        self.deiconify()
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
        half = self.total_stations // 2
        sectors_lr = list(reversed(self.sector_info))

        header = ctk.CTkLabel(
            self,
            text=f"Obecnych: {self.present_count}    "
                 f"Stanowisk: {self.total_stations}    "
                 f"Do wykluczenia: {self.total_to_exclude}",
            font=("Segoe UI", 14, "bold"),
        )
        header.pack(padx=10, pady=(10, 5))

        # --- top bank ---
        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.pack(padx=10, pady=(5, 0))

        for idx, sector in enumerate(sectors_lr):
            sector_top_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
            sector_top_frame.pack(side="left", padx=(0 if idx == 0 else 6, 0))
            top_stations = sorted(
                [s for s in sector["stations"] if s <= half], reverse=True,
            )
            for station in top_stations:
                key = (sector["name"], station)
                btn = self._create_station_button(sector_top_frame, key)
                btn.pack(side="left", padx=2, pady=2)

        # --- pond rectangle ---
        pond_frame = ctk.CTkFrame(self, fg_color="#1a5276", height=80)
        pond_frame.pack(fill="x", padx=10, pady=0)
        pond_frame.pack_propagate(False)

        for idx, sector in enumerate(sectors_lr):
            if idx > 0:
                sep = ctk.CTkFrame(pond_frame, width=2, fg_color="#E74C3C")
                sep.pack(side="left", fill="y")
            sector_excluded = sum(
                1 for s in sector["stations"]
                if (sector["name"], s) in self.selected_stations
            )
            effective = len(sector["stations"]) - sector_excluded
            lbl = ctk.CTkLabel(
                pond_frame,
                text=f"Sektor {sector['name']}\n({effective}/{len(sector['stations'])})",
                font=("Segoe UI", 14, "bold"),
                text_color="#FFFFFF",
            )
            lbl.pack(side="left", expand=True, fill="both")
            self.sector_labels[sector["name"]] = lbl

        # --- bottom bank ---
        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.pack(padx=10, pady=(0, 5))

        for idx, sector in enumerate(sectors_lr):
            sector_bot_frame = ctk.CTkFrame(bottom_frame, fg_color="transparent")
            sector_bot_frame.pack(side="left", padx=(0 if idx == 0 else 6, 0))
            bot_stations = sorted(
                [s for s in sector["stations"] if s > half],
            )
            for station in bot_stations:
                key = (sector["name"], station)
                btn = self._create_station_button(sector_bot_frame, key)
                btn.pack(side="left", padx=2, pady=2)

        # --- counter and action buttons ---
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
            text_color_disabled="#555555",
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

    def _create_station_button(self, parent, key: tuple[str, int]) -> ctk.CTkButton:
        _, station = key
        is_selected = key in self.selected_stations
        is_assigned = station in self.assigned_stations

        btn = ctk.CTkButton(
            parent,
            text=str(station),
            width=38,
            height=30,
            font=("Segoe UI", 12),
            command=lambda k=key: self._toggle_station(k),
        )
        self.station_buttons[key] = btn

        if is_assigned:
            btn.configure(
                fg_color="#3D8B3D",
                hover_color="#3D8B3D",
                text_color="#FFFFFF",
                text_color_disabled="#FFFFFF",
                state="disabled",
            )
        elif is_selected:
            btn.configure(fg_color="#922B21", hover_color="#7B241C", text_color="#FFFFFF")

        return btn

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
            btn.configure(fg_color="#922B21", hover_color="#7B241C", text_color="#FFFFFF")
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
            text=f"Sektor {sector_name}\n({effective}/{len(sector['stations'])})"
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
