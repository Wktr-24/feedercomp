import os
from tkinter import messagebox, ttk

import customtkinter as ctk

from app.repositories import competitor_repo, competition_repo, venue_repo
from app.services.print_service import PrintService
from app.services.ranking_service import RankingService
from app.services.sector_service import SectorService
from app.utils import configure_treeview_style, format_weight_kg, get_treeview_tag_colors


class ResultsScreen(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self._build_ui()
        self._recalculate()
        self._refresh()

    def _build_ui(self):
        self._build_tabview()
        self._build_bottom()

    # -- Tabview --

    def _build_tabview(self):
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=5, pady=(5, 2))

        self._build_classification_tab()
        self._build_winners_tab()

    def _build_classification_tab(self):
        tab = self.tabview.add("Klasyfikacja końcowa")

        columns = ("place", "name", "sector", "points", "weight_g", "weight_kg")
        headings = ("Miejsce", "Imię i Nazwisko", "Sektor", "Pkt sekt.", "Waga (g)", "Waga (kg)")
        widths = (60, 250, 60, 80, 80, 100)
        anchors = ("center", "w", "center", "center", "center", "center")

        configure_treeview_style(dark_mode=self.app.dark_mode)

        self.class_tree = ttk.Treeview(tab, columns=columns, show="headings", selectmode="browse")
        for col, heading, width, anchor in zip(columns, headings, widths, anchors):
            self.class_tree.heading(col, text=heading)
            self.class_tree.column(col, width=width, minwidth=40, anchor=anchor)

        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=self.class_tree.yview)
        self.class_tree.configure(yscrollcommand=scrollbar.set)

        self.class_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        colors = get_treeview_tag_colors(self.app.dark_mode)
        self.class_tree.tag_configure("even", background=colors["even"])
        self.class_tree.tag_configure("odd", background=colors["odd"])

    def _build_winners_tab(self):
        tab = self.tabview.add("Lista zwycięzców")

        control_frame = ctk.CTkFrame(tab)
        control_frame.pack(fill="x", padx=5, pady=(5, 5))
        ctk.CTkLabel(control_frame, text="Liczba miejsc nagradzanych:", font=("Segoe UI", 13)).pack(side="left", padx=(5, 5))
        self.winner_places_entry = ctk.CTkEntry(control_frame, width=60)
        self.winner_places_entry.pack(side="left", padx=(0, 5))
        self.winner_places_entry.bind("<Return>", lambda e: self._on_apply_winner_places())
        ctk.CTkButton(
            control_frame, text="Zastosuj", width=90,
            command=self._on_apply_winner_places,
        ).pack(side="left")

        columns = ("place", "name", "weight_g", "weight_kg")
        headings = ("Miejsce", "Imię i Nazwisko", "Waga (g)", "Waga (kg)")
        widths = (60, 300, 100, 120)
        anchors = ("center", "w", "center", "center")

        self.winners_tree = ttk.Treeview(tab, columns=columns, show="headings", selectmode="browse")
        for col, heading, width, anchor in zip(columns, headings, widths, anchors):
            self.winners_tree.heading(col, text=heading)
            self.winners_tree.column(col, width=width, minwidth=40, anchor=anchor)

        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=self.winners_tree.yview)
        self.winners_tree.configure(yscrollcommand=scrollbar.set)

        self.winners_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        colors = get_treeview_tag_colors(self.app.dark_mode)
        self.winners_tree.tag_configure("even", background=colors["even"])
        self.winners_tree.tag_configure("odd", background=colors["odd"])

    def _apply_tag_colors(self):
        colors = get_treeview_tag_colors(self.app.dark_mode)
        self.class_tree.tag_configure("even", background=colors["even"])
        self.class_tree.tag_configure("odd", background=colors["odd"])
        self.winners_tree.tag_configure("even", background=colors["even"])
        self.winners_tree.tag_configure("odd", background=colors["odd"])

    # -- Bottom: action buttons --

    def _build_bottom(self):
        bottom = ctk.CTkFrame(self)
        bottom.pack(fill="x", padx=5, pady=(2, 5))

        ctk.CTkButton(bottom, text="Przelicz", command=self._on_recalculate, width=120).pack(side="left", padx=(10, 3))
        ctk.CTkButton(
            bottom, text="Drukuj klasyfikację (PDF)",
            command=self._print_classification, width=180,
        ).pack(side="left", padx=3)
        ctk.CTkButton(
            bottom, text="Drukuj zwycięzców (PDF)",
            command=self._print_winners, width=180,
        ).pack(side="left", padx=3)
        ctk.CTkButton(
            bottom, text="Drukuj sektory (PDF)",
            command=self._print_sectors, width=160,
        ).pack(side="left", padx=3)

    # -- Data operations --

    def _recalculate(self):
        conn = self.app.get_connection()
        try:
            service = RankingService(SectorService())
            service.calculate_all(conn, self.app.competition_id, self.app.venue_id)
        finally:
            conn.close()

    def _refresh(self):
        conn = self.app.get_connection()
        try:
            self._refresh_classification(conn)
            self._refresh_winners(conn)
        finally:
            conn.close()

    def _refresh_classification(self, conn):
        self.class_tree.delete(*self.class_tree.get_children())
        competitors = competitor_repo.get_all(conn, self.app.competition_id)
        competitors = [c for c in competitors if c.sector_name is not None]

        with_place = [c for c in competitors if c.final_place is not None]
        without_place = [c for c in competitors if c.final_place is None]
        with_place.sort(key=lambda c: c.final_place)
        without_place.sort(key=lambda c: (c.sector_name, c.list_number))

        for i, c in enumerate(with_place + without_place):
            tag = "even" if i % 2 == 0 else "odd"
            place_str = str(c.final_place) if c.final_place is not None else "-"
            self.class_tree.insert("", "end", tags=(tag,), values=(
                place_str,
                c.full_name,
                c.sector_name or "",
                str(c.sector_points) if c.sector_points is not None else "",
                c.weight_grams,
                format_weight_kg(c.weight_grams),
            ))

    def _refresh_winners(self, conn):
        self.winners_tree.delete(*self.winners_tree.get_children())
        comp = competition_repo.get_by_id(conn, self.app.competition_id)
        winner_places = comp.winner_places if comp else 3

        self.winner_places_entry.delete(0, "end")
        self.winner_places_entry.insert(0, str(winner_places))

        service = RankingService(SectorService())
        winners = service.get_winners(conn, self.app.competition_id, winner_places)

        for i, c in enumerate(winners):
            tag = "even" if i % 2 == 0 else "odd"
            self.winners_tree.insert("", "end", tags=(tag,), values=(
                str(c.final_place) if c.final_place is not None else "-",
                c.full_name,
                c.weight_grams,
                format_weight_kg(c.weight_grams),
            ))

    def _sync_winner_places_from_entry(self, conn) -> bool:
        """Save entry value to DB if it differs. Returns True on success, False if invalid."""
        entry_text = self.winner_places_entry.get().strip()
        try:
            new_value = int(entry_text)
        except ValueError:
            messagebox.showerror("Błąd", "Liczba miejsc nagradzanych musi być liczbą całkowitą")
            return False
        if new_value < 1:
            messagebox.showerror("Błąd", "Liczba miejsc nagradzanych musi być co najmniej 1")
            return False

        comp = competition_repo.get_by_id(conn, self.app.competition_id)
        if comp and comp.winner_places != new_value:
            competition_repo.update_winner_places(conn, self.app.competition_id, new_value)
            conn.commit()
        return True

    def _on_apply_winner_places(self):
        conn = self.app.get_connection()
        try:
            if self._sync_winner_places_from_entry(conn):
                self._refresh_winners(conn)
        finally:
            conn.close()

    def _get_comp_and_venue(self, conn):
        comp = competition_repo.get_by_id(conn, self.app.competition_id)
        venue = venue_repo.get_by_id(conn, self.app.venue_id)
        return comp, venue

    def _print_classification(self):
        conn = self.app.get_connection()
        try:
            comp, venue = self._get_comp_and_venue(conn)
            ps = PrintService()
            path = ps.generate_classification_pdf(
                conn, self.app.competition_id,
                venue.name, comp.date, comp.name,
            )
            ps.open_pdf(path)
        finally:
            conn.close()

    def _print_winners(self):
        conn = self.app.get_connection()
        try:
            comp, venue = self._get_comp_and_venue(conn)
            ps = PrintService()
            path = ps.generate_winners_pdf(
                conn, self.app.competition_id, comp.winner_places,
                venue.name, comp.date, comp.name,
            )
            ps.open_pdf(path)
        finally:
            conn.close()

    def _print_sectors(self):
        conn = self.app.get_connection()
        try:
            comp, venue = self._get_comp_and_venue(conn)
            sector_names = venue_repo.get_sector_names(conn, self.app.venue_id)
            ps = PrintService()
            paths = []
            for sector_name in sector_names:
                path = ps.generate_sector_pdf(
                    conn, self.app.competition_id, sector_name,
                    venue.name, comp.date, comp.name,
                )
                paths.append(path)
            if paths:
                folder = paths[0].parent
                messagebox.showinfo(
                    "PDF",
                    f"Wygenerowano {len(paths)} plików PDF w:\n{folder}",
                )
                if os.name == 'nt':
                    os.startfile(folder)
                else:
                    import subprocess
                    subprocess.Popen(['xdg-open', str(folder)])
            else:
                messagebox.showwarning("PDF", "Brak sektorów do wydruku.")
        finally:
            conn.close()

    def _on_recalculate(self):
        self._recalculate()
        self._refresh()
