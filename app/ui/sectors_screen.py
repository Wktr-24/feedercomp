from tkinter import messagebox, ttk

import customtkinter as ctk

from app.repositories import competitor_repo, venue_repo
from app.services.ranking_service import RankingService
from app.services.sector_service import SectorService


class SectorsScreen(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.tables = {}  # sector_name -> Treeview
        self._search_matches = []
        self._search_index = 0
        self._build_ui()
        self._refresh_all()

    def _build_ui(self):
        self._build_top()
        self._build_tabview()
        self._build_bottom()

    # -- Top: search + weight entry --

    def _build_top(self):
        top = ctk.CTkFrame(self)
        top.pack(fill="x", padx=5, pady=(5, 2))

        ctk.CTkLabel(top, text="Szukaj:", font=("Segoe UI", 14)).pack(side="left", padx=(10, 2))
        self.search_entry = ctk.CTkEntry(top, width=200, placeholder_text="wpisz nazwisko...")
        self.search_entry.pack(side="left", padx=2)
        self.search_entry.bind("<KeyRelease>", self._on_search_key)
        self.search_entry.bind("<Return>", lambda _: self._jump_to_next())
        self.search_counter = ctk.CTkLabel(top, text="", font=("Segoe UI", 12), width=60)
        self.search_counter.pack(side="left", padx=(2, 5))

        ctk.CTkLabel(top, text="Waga (g):", font=("Segoe UI", 14)).pack(side="left", padx=(20, 2))
        self.weight_entry = ctk.CTkEntry(top, width=100)
        self.weight_entry.pack(side="left", padx=2)
        self.weight_entry.bind("<Return>", lambda _: self._on_save_weight())

        ctk.CTkButton(top, text="Zapisz wagę", command=self._on_save_weight, width=120).pack(side="left", padx=(5, 10))

    # -- Tabview with sector tabs --

    def _build_tabview(self):
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=5, pady=2)

        conn = self.app.get_connection()
        try:
            sectors = venue_repo.get_sector_names(conn, self.app.venue_id)
        finally:
            conn.close()

        for sector_name in sectors:
            tab = self.tabview.add(f"Sektor {sector_name}")
            tree = self._create_table(tab)
            self.tables[sector_name] = tree

    def _create_table(self, parent):
        columns = ("station", "name", "weight_g", "weight_kg", "place")
        headings = ("Stanowisko", "Zawodnik", "Waga (g)", "Waga (kg)", "Miejsce")
        widths = (80, 250, 80, 100, 80)
        anchors = ("center", "w", "center", "center", "center")

        style = ttk.Style()
        style.configure("Treeview", font=("Segoe UI", 13), rowheight=28)
        style.configure("Treeview.Heading", font=("Segoe UI", 13, "bold"))

        tree = ttk.Treeview(parent, columns=columns, show="headings", selectmode="browse")
        for col, heading, width, anchor in zip(columns, headings, widths, anchors):
            tree.heading(col, text=heading)
            tree.column(col, width=width, minwidth=40, anchor=anchor)

        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)

        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        tree.tag_configure("even", background="#f0f0f0")
        tree.tag_configure("odd", background="#ffffff")

        tree.bind("<ButtonRelease-1>", self._on_row_click)
        tree.bind("<Double-1>", self._on_row_double_click)
        return tree

    # -- Bottom: action buttons --

    def _build_bottom(self):
        bottom = ctk.CTkFrame(self)
        bottom.pack(fill="x", padx=5, pady=(2, 5))

        ctk.CTkButton(bottom, text="Przelicz miejsca", command=self._recalculate, width=150).pack(side="left", padx=(10, 3))
        ctk.CTkButton(
            bottom, text="Przelicz i przejdź do wyników",
            command=self._recalculate_and_show_results, width=220,
        ).pack(side="left", padx=3)

    # -- Data operations --

    def _refresh_all(self):
        conn = self.app.get_connection()
        try:
            for sector_name, tree in self.tables.items():
                tree.delete(*tree.get_children())
                competitors = competitor_repo.get_by_sector(conn, self.app.competition_id, sector_name)
                competitors.sort(key=lambda c: c.station_number or 0)
                for i, c in enumerate(competitors):
                    tag = "even" if i % 2 == 0 else "odd"
                    place_str = str(c.sector_place) if c.sector_place is not None else ""
                    tree.insert("", "end", iid=str(c.id), tags=(tag,), values=(
                        c.station_number or "",
                        c.full_name,
                        c.weight_grams,
                        self._format_weight_kg(c.weight_grams),
                        place_str,
                    ))
        finally:
            conn.close()

    def _format_weight_kg(self, grams):
        if grams == 0:
            return "0"
        kg = grams / 1000
        return f"{kg:.3f}".replace(".", ",")

    # -- Events --

    def _on_row_click(self, event):
        tree = event.widget
        if tree.identify_row(event.y):
            self.weight_entry.focus_set()
            self.weight_entry.select_range(0, "end")

    def _on_row_double_click(self, event):
        tree = event.widget
        row_id = tree.identify_row(event.y)
        if not row_id:
            return
        values = tree.item(row_id, "values")
        weight_g = values[2]  # column "weight_g"
        self.weight_entry.delete(0, "end")
        self.weight_entry.insert(0, str(weight_g))
        self.weight_entry.focus_set()
        self.weight_entry.select_range(0, "end")

    def _on_search_key(self, event):
        if event.keysym == "Return":
            return
        query = self.search_entry.get().strip()
        if len(query) < 2:
            self._search_matches = []
            self._search_index = 0
            self.search_counter.configure(text="")
            return

        conn = self.app.get_connection()
        try:
            matches = competitor_repo.search_by_name(conn, self.app.competition_id, query)
        finally:
            conn.close()

        self._search_matches = [m for m in matches if m.sector_name and m.sector_name in self.tables]
        self._search_index = 0

        if not self._search_matches:
            self.search_counter.configure(text="0 / 0")
            return

        self._show_current_match()

    def _jump_to_next(self):
        if not self._search_matches:
            return
        self._search_index = (self._search_index + 1) % len(self._search_matches)
        self._show_current_match()

    def _show_current_match(self):
        match = self._search_matches[self._search_index]
        total = len(self._search_matches)
        self.search_counter.configure(text=f"{self._search_index + 1} / {total}")

        self.tabview.set(f"Sektor {match.sector_name}")
        tree = self.tables[match.sector_name]
        item_id = str(match.id)
        if tree.exists(item_id):
            tree.selection_set(item_id)
            tree.see(item_id)

    def _on_save_weight(self):
        selection, sector_name = self._get_current_selection()
        if not selection:
            messagebox.showwarning("Błąd", "Zaznacz zawodnika w tabeli.")
            return

        weight_str = self.weight_entry.get().strip()
        if not weight_str:
            messagebox.showwarning("Błąd", "Wpisz wagę w gramach.")
            return

        try:
            weight = int(weight_str)
        except ValueError:
            messagebox.showwarning("Błąd", "Waga musi być liczbą całkowitą.")
            return

        if weight < 0:
            messagebox.showwarning("Błąd", "Waga nie może być ujemna.")
            return

        competitor_id = int(selection)
        conn = self.app.get_connection()
        try:
            competitor_repo.update_weight(conn, competitor_id, weight)
        finally:
            conn.close()

        self.weight_entry.delete(0, "end")
        self._refresh_all()

        # Re-select and advance to next row
        if sector_name and sector_name in self.tables:
            tree = self.tables[sector_name]
            children = tree.get_children()
            if selection in children:
                idx = list(children).index(selection)
                if idx + 1 < len(children):
                    next_item = children[idx + 1]
                    tree.selection_set(next_item)
                    tree.see(next_item)
                    self.weight_entry.focus_set()

    def _get_current_selection(self):
        current_tab = self.tabview.get()
        for sector_name, tree in self.tables.items():
            if f"Sektor {sector_name}" == current_tab:
                sel = tree.selection()
                if sel:
                    return sel[0], sector_name
                return None, None
        return None, None

    def _recalculate(self):
        conn = self.app.get_connection()
        try:
            service = RankingService(SectorService())
            service.calculate_all(conn, self.app.competition_id, self.app.venue_id)
        finally:
            conn.close()
        self._refresh_all()

    def _recalculate_and_show_results(self):
        conn = self.app.get_connection()
        try:
            service = RankingService(SectorService())
            service.calculate_all(conn, self.app.competition_id, self.app.venue_id)
        finally:
            conn.close()
        self.app.show_results_screen()
