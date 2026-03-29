import customtkinter as ctk

from app.database import get_connection


class AppWindow(ctk.CTkFrame):
    def __init__(self, master, db_path):
        super().__init__(master)
        self.db_path = db_path
        self.competition_id = None
        self.venue_id = None

        self.nav_frame = ctk.CTkFrame(self)
        self.nav_frame.pack(fill="x", padx=5, pady=5)

        self.content_frame = ctk.CTkFrame(self)
        self.content_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.show_start_screen()

    def get_connection(self):
        return get_connection(self.db_path)

    def show_start_screen(self):
        self._clear_content()
        self._clear_nav()
        from app.ui.start_screen import StartScreen
        screen = StartScreen(self.content_frame, self)
        screen.pack(fill="both", expand=True)

    def show_competitors_screen(self):
        self._clear_content()
        self._setup_nav()
        from app.ui.competitors_screen import CompetitorsScreen
        screen = CompetitorsScreen(self.content_frame, self)
        screen.pack(fill="both", expand=True)

    def show_sectors_screen(self):
        self._clear_content()
        self._setup_nav()
        from app.ui.sectors_screen import SectorsScreen
        screen = SectorsScreen(self.content_frame, self)
        screen.pack(fill="both", expand=True)

    def show_results_screen(self):
        self._clear_content()
        self._setup_nav()
        from app.ui.results_screen import ResultsScreen
        screen = ResultsScreen(self.content_frame, self)
        screen.pack(fill="both", expand=True)

    def show_venue_editor(self, venue_id):
        self._clear_content()
        self._clear_nav()
        from app.ui.venue_editor import VenueEditor
        screen = VenueEditor(self.content_frame, self, venue_id)
        screen.pack(fill="both", expand=True)

    def on_competition_selected(self, competition_id, venue_id):
        self.competition_id = competition_id
        self.venue_id = venue_id
        self.show_competitors_screen()

    def _clear_content(self):
        for w in self.content_frame.winfo_children():
            w.destroy()

    def _clear_nav(self):
        for w in self.nav_frame.winfo_children():
            w.destroy()

    def _setup_nav(self):
        self._clear_nav()
        buttons = [
            ("Lista Zawodnik\u00f3w", self.show_competitors_screen),
            ("Sektory", self.show_sectors_screen),
            ("Wyniki", self.show_results_screen),
            ("\u2190 Powr\u00f3t", self.show_start_screen),
        ]
        for text, cmd in buttons:
            btn = ctk.CTkButton(self.nav_frame, text=text, command=cmd, width=150)
            btn.pack(side="left", padx=3)
