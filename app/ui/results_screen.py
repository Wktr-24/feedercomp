import os
from tkinter import font as tkfont
from tkinter import messagebox, ttk

import customtkinter as ctk

from app.repositories import competitor_repo, competition_repo, venue_repo
from app.services import general_classification_service
from app.services.print_service import PrintService
from app.services.ranking_service import RankingService
from app.services.sector_service import SectorService
from app.utils import (
    configure_treeview_style,
    format_weight_kg,
    get_treeview_tag_colors,
    normalize_whitespace,
)


class ResultsScreen(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self._db_name = ""
        self._db_winner_places = None
        self.general_tree = None
        # Two-day final: resolved once — the pair can only change from the
        # start screen, and navigating back rebuilds this screen anyway.
        conn = self.app.get_connection()
        try:
            self._linked_pair = general_classification_service.resolve_linked_pair(
                conn, self.app.competition_id,
            )
        finally:
            conn.close()
        self._build_ui()
        self._recalculate()
        self._refresh()

    def _build_ui(self):
        self._build_name_bar()
        self._build_tabview()
        self._build_bottom()

    def _build_name_bar(self):
        name_frame = ctk.CTkFrame(self)
        name_frame.pack(fill="x", padx=5, pady=(5, 2))
        ctk.CTkLabel(
            name_frame, text="Nazwa zawodów:", font=("Segoe UI", 13),
        ).pack(side="left", padx=(10, 5))
        self.name_entry = ctk.CTkEntry(name_frame, width=300)
        self.name_entry.pack(side="left", padx=(0, 5))
        self.name_entry.bind("<Return>", lambda e: self._on_apply_name())
        self.name_entry.bind("<KeyRelease>", lambda e: self._check_changes())
        self.apply_name_btn = ctk.CTkButton(
            name_frame, text="Zastosuj", width=110,
            command=self._on_apply_name, state="disabled",
        )
        self.apply_name_btn.pack(side="left")

    # -- Tabview --

    def _build_tabview(self):
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=5, pady=(5, 2))

        self._build_classification_tab()
        self._build_winners_tab()
        if self._linked_pair:
            self._build_general_tab()

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
        self.winner_places_entry.bind("<KeyRelease>", lambda e: self._check_changes())
        self.apply_winner_places_btn = ctk.CTkButton(
            control_frame, text="Zastosuj", width=90,
            command=self._on_apply_winner_places, state="disabled",
        )
        self.apply_winner_places_btn.pack(side="left")

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

    def _build_general_tab(self):
        tab = self.tabview.add("Klasyfikacja generalna")

        day1, day2 = self._linked_pair
        ctk.CTkLabel(
            tab,
            text=f"Suma z dwóch dni: {day1.date} + {day2.date}",
            font=("Segoe UI", 13),
        ).pack(fill="x", padx=5, pady=(5, 0))

        # Classified/per-day counts — lets the organizer eyeball at a glance
        # that nobody silently fell out of the pairing.
        self.general_info = ctk.CTkLabel(
            tab, text="", font=("Segoe UI", 13),
            text_color=("gray40", "gray70"),
        )
        self.general_info.pack(fill="x", padx=5, pady=(0, 0))

        # Populated when ambiguous (duplicated) names had to be excluded
        # from the classification. wraplength + left anchor: a long name
        # list must wrap, not get center-truncated on both sides.
        self.general_warning = ctk.CTkLabel(
            tab, text="", font=("Segoe UI", 13, "bold"), text_color="#C0392B",
            anchor="w", justify="left", wraplength=850,
        )
        self.general_warning.pack(fill="x", padx=5, pady=(0, 2))

        columns = ("place", "name", "pts1", "pts2", "pts_sum", "weight_kg")
        headings = ("Miejsce", "Imię i Nazwisko", "Pkt dzień 1", "Pkt dzień 2", "Suma pkt", "Waga (kg)")
        # The place column must hold the literal "DYSKWALIFIKACJA" at the
        # actual Treeview font, and every other column must hold its
        # heading at the bold heading font (pixel sizes depend on DPI).
        # Treeview clips overflowing text, and stretch can shrink a column
        # below its configured width at small window sizes — measure and
        # pin minwidths so any deficit lands on the name column (widest,
        # left-anchored data), never on the headings or the DQ label.
        cell_font = tkfont.Font(font=ttk.Style().lookup("Treeview", "font"))
        heading_font = tkfont.Font(font=ttk.Style().lookup("Treeview.Heading", "font"))
        place_width = cell_font.measure("DYSKWALIFIKACJA") + 24
        widths = (place_width, 250, 90, 90, 80, 100)
        anchors = ("center", "w", "center", "center", "center", "center")

        self.general_tree = ttk.Treeview(tab, columns=columns, show="headings", selectmode="browse")
        for col, heading, width, anchor in zip(columns, headings, widths, anchors):
            self.general_tree.heading(col, text=heading)
            min_w = heading_font.measure(heading) + 12
            self.general_tree.column(col, width=max(width, min_w), minwidth=min_w, anchor=anchor)
        self.general_tree.column("place", minwidth=place_width)

        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=self.general_tree.yview)
        self.general_tree.configure(yscrollcommand=scrollbar.set)

        self.general_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        colors = get_treeview_tag_colors(self.app.dark_mode)
        self.general_tree.tag_configure("even", background=colors["even"])
        self.general_tree.tag_configure("odd", background=colors["odd"])

    def _apply_tag_colors(self):
        colors = get_treeview_tag_colors(self.app.dark_mode)
        self.class_tree.tag_configure("even", background=colors["even"])
        self.class_tree.tag_configure("odd", background=colors["odd"])
        self.winners_tree.tag_configure("even", background=colors["even"])
        self.winners_tree.tag_configure("odd", background=colors["odd"])
        if self.general_tree is not None:
            self.general_tree.tag_configure("even", background=colors["even"])
            self.general_tree.tag_configure("odd", background=colors["odd"])

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
        if self._linked_pair:
            ctk.CTkButton(
                bottom, text="Drukuj generalną (PDF)",
                command=self._print_general, width=170,
            ).pack(side="left", padx=3)

    # -- Data operations --

    def _recalculate(self):
        conn = self.app.get_connection()
        try:
            service = RankingService(SectorService())
            if self._linked_pair:
                # Keep BOTH days' persisted points fresh before the general
                # classification aggregates them (day-1 weights may have
                # been edited after that day was last recalculated).
                day1, day2 = self._linked_pair
                service.calculate_all(conn, day1.id, day1.venue_id)
                service.calculate_all(conn, day2.id, day2.venue_id)
            else:
                service.calculate_all(conn, self.app.competition_id, self.app.venue_id)
        finally:
            conn.close()

    def _refresh(self):
        conn = self.app.get_connection()
        try:
            self._refresh_name(conn)
            self._refresh_classification(conn)
            self._refresh_winners(conn)
            if self.general_tree is not None:
                self._refresh_general(conn)
        finally:
            conn.close()

    def _refresh_general(self, conn):
        self.general_tree.delete(*self.general_tree.get_children())
        day1, day2 = self._linked_pair
        result = general_classification_service.calculate(conn, day1.id, day2.id)

        self.general_info.configure(
            text=f"Sklasyfikowani: {len(result.rows)}    "
                 f"(dzień 1: {result.day1_count}, dzień 2: {result.day2_count})",
        )

        if result.duplicate_names:
            self.general_warning.configure(
                text="Powtarzające się nazwiska pominięte w klasyfikacji: "
                + ", ".join(result.duplicate_names)
            )
        else:
            self.general_warning.configure(text="")

        for i, row in enumerate(result.rows):
            tag = "even" if i % 2 == 0 else "odd"
            self.general_tree.insert("", "end", tags=(tag,), values=(
                str(row.place) if row.place is not None else "-",
                row.full_name,
                str(row.points_day1),
                str(row.points_day2),
                str(row.total_points),
                format_weight_kg(row.total_weight_grams),
            ))
        for i, row in enumerate(result.disqualified, start=len(result.rows)):
            tag = "even" if i % 2 == 0 else "odd"
            self.general_tree.insert("", "end", tags=(tag,), values=(
                "DYSKWALIFIKACJA",
                row.full_name,
                str(row.points_day1) if row.points_day1 is not None else "-",
                str(row.points_day2) if row.points_day2 is not None else "-",
                str(row.total_points),
                format_weight_kg(row.weight_grams),
            ))

    def _refresh_name(self, conn):
        comp = competition_repo.get_by_id(conn, self.app.competition_id)
        raw_db_name = comp.name if comp and comp.name else ""
        new_db_name = normalize_whitespace(raw_db_name)

        current_entry = normalize_whitespace(self.name_entry.get())
        was_dirty = current_entry != (self._db_name or "")

        self._db_name = new_db_name

        if not was_dirty:
            self.name_entry.delete(0, "end")
            if new_db_name:
                self.name_entry.insert(0, new_db_name)

        self._check_changes()

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
        comp = competition_repo.get_by_id(conn, self.app.competition_id)
        new_db_winner_places = comp.winner_places if comp else 3

        if self._db_winner_places is None:
            was_dirty = False
        else:
            current_entry = self.winner_places_entry.get().strip()
            was_dirty = current_entry != str(self._db_winner_places)

        self._db_winner_places = new_db_winner_places

        if not was_dirty:
            self.winner_places_entry.delete(0, "end")
            self.winner_places_entry.insert(0, str(new_db_winner_places))

        self._check_changes()

        self._refresh_winners_tree(conn, new_db_winner_places)

    def _refresh_winners_tree(self, conn, winner_places):
        self.winners_tree.delete(*self.winners_tree.get_children())
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

    def _check_changes(self):
        name_now = normalize_whitespace(self.name_entry.get())
        name_db = self._db_name or ""
        name_dirty = name_now != name_db
        self.apply_name_btn.configure(state="normal" if name_dirty else "disabled")

        if self._db_winner_places is None:
            wp_dirty = False
        else:
            wp_now = self.winner_places_entry.get().strip()
            wp_dirty = wp_now != str(self._db_winner_places)
        self.apply_winner_places_btn.configure(state="normal" if wp_dirty else "disabled")

    def _has_unsaved_changes(self) -> bool:
        name_dirty = normalize_whitespace(self.name_entry.get()) != (self._db_name or "")
        if self._db_winner_places is None:
            wp_dirty = False
        else:
            wp_dirty = self.winner_places_entry.get().strip() != str(self._db_winner_places)
        return name_dirty or wp_dirty

    def _warn_unsaved_changes(self):
        messagebox.showwarning(
            "Niezapisane zmiany",
            "Masz niezapisane zmiany w polach ekranu.\n\n"
            "Przed wydrukiem kliknij przycisk 'Zastosuj' przy zmienionym polu, "
            "aby zapisać zmiany, albo przywróć pierwotne wartości ręcznie.",
            parent=self,
        )

    def _sync_winner_places_from_entry(self, conn) -> bool:
        """Save entry value to DB if it differs. Returns True on success, False if invalid."""
        entry_text = self.winner_places_entry.get().strip()
        try:
            new_value = int(entry_text)
        except ValueError:
            messagebox.showerror("Błąd", "Liczba miejsc nagradzanych musi być liczbą całkowitą", parent=self)
            return False
        if new_value < 1:
            messagebox.showerror("Błąd", "Liczba miejsc nagradzanych musi być co najmniej 1", parent=self)
            return False

        comp = competition_repo.get_by_id(conn, self.app.competition_id)
        if comp and comp.winner_places != new_value:
            competition_repo.update_winner_places(conn, self.app.competition_id, new_value)
            conn.commit()
            self._db_winner_places = new_value
            self.apply_winner_places_btn.configure(text="\u2713 Zapisano")
            self.after(1500, lambda: self.apply_winner_places_btn.configure(text="Zastosuj"))

        self.winner_places_entry.delete(0, "end")
        self.winner_places_entry.insert(0, str(new_value))
        self._check_changes()
        return True

    def _on_apply_winner_places(self):
        conn = self.app.get_connection()
        try:
            if self._sync_winner_places_from_entry(conn):
                self._refresh_winners_tree(conn, self._db_winner_places)
                self._check_changes()
        finally:
            conn.close()

    def _on_apply_name(self):
        new_name = normalize_whitespace(self.name_entry.get()) or None
        conn = self.app.get_connection()
        try:
            comp = competition_repo.get_by_id(conn, self.app.competition_id)
            if comp and comp.name != new_name:
                competition_repo.update_name(conn, self.app.competition_id, new_name)
                conn.commit()
                self._db_name = new_name or ""
                self.name_entry.delete(0, "end")
                if new_name:
                    self.name_entry.insert(0, new_name)
                self.apply_name_btn.configure(text="\u2713 Zapisano")
                self.after(1500, lambda: self.apply_name_btn.configure(text="Zastosuj"))
                self._check_changes()
        finally:
            conn.close()

    def _get_comp_and_venue(self, conn):
        comp = competition_repo.get_by_id(conn, self.app.competition_id)
        venue = venue_repo.get_by_id(conn, self.app.venue_id)
        return comp, venue

    def _print_classification(self):
        if self._has_unsaved_changes():
            self._warn_unsaved_changes()
            return
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
        if self._has_unsaved_changes():
            self._warn_unsaved_changes()
            return
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
        if self._has_unsaved_changes():
            self._warn_unsaved_changes()
            return
        conn = self.app.get_connection()
        try:
            comp, venue = self._get_comp_and_venue(conn)
            sector_names = venue_repo.get_sector_names(conn, self.app.venue_id)
            ps = PrintService()
            run_dir = ps.new_print_run_dir("Sektory")
            paths = []
            for sector_name in sector_names:
                path = ps.generate_sector_pdf(
                    conn, self.app.competition_id, sector_name,
                    venue.name, comp.date, comp.name,
                    run_dir=run_dir,
                )
                paths.append(path)
            if paths:
                folder = paths[0].parent
                messagebox.showinfo(
                    "PDF",
                    f"Wygenerowano {len(paths)} plików PDF w:\n{folder}",
                    parent=self,
                )
                if os.name == 'nt':
                    os.startfile(folder)
                else:
                    import subprocess
                    subprocess.Popen(['xdg-open', str(folder)])
            else:
                messagebox.showwarning("PDF", "Brak sektorów do wydruku.", parent=self)
        finally:
            conn.close()

    def _print_general(self):
        if self._has_unsaved_changes():
            self._warn_unsaved_changes()
            return
        conn = self.app.get_connection()
        try:
            # Re-read both days from the DB — the __init__ snapshot's name can
            # be stale after a rename applied on this very screen (ids are
            # stable, names are not).
            day1 = competition_repo.get_by_id(conn, self._linked_pair[0].id)
            day2 = competition_repo.get_by_id(conn, self._linked_pair[1].id)
            venue = venue_repo.get_by_id(conn, day1.venue_id)
            result = general_classification_service.calculate(conn, day1.id, day2.id)
            if result.duplicate_names:
                messagebox.showwarning(
                    "Uwaga",
                    "Powtarzające się nazwiska pominięte w klasyfikacji: "
                    + ", ".join(result.duplicate_names),
                    parent=self,
                )
            ps = PrintService()
            # day1.name is the natural competition name (without " — dzień 2").
            path = ps.generate_general_classification_pdf(
                conn, day1.id, day2.id, venue.name, day1.date, day2.date, day1.name,
            )
            ps.open_pdf(path)
        finally:
            conn.close()

    def _on_recalculate(self):
        self._recalculate()
        self._refresh()
