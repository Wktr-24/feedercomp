import customtkinter as ctk

from app.database import get_connection
from app.utils import configure_treeview_style


class AppWindow(ctk.CTkFrame):
    def __init__(self, master, db_path):
        super().__init__(master)
        self.db_path = db_path
        self.competition_id = None
        self.venue_id = None
        self.dark_mode = True

        self.nav_frame = ctk.CTkFrame(self)
        self.nav_frame.pack(fill="x", padx=5, pady=5)

        self.theme_btn = ctk.CTkButton(
            self.nav_frame, text="\u2600", width=35, height=35,
            command=self._toggle_theme,
        )
        self.theme_btn.pack(side="right", padx=5)

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
            if w is self.theme_btn:
                continue
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

    def _toggle_theme(self):
        self.dark_mode = not self.dark_mode
        if self.dark_mode:
            ctk.set_appearance_mode("dark")
            self.theme_btn.configure(text="\u2600")
        else:
            ctk.set_appearance_mode("light")
            self.theme_btn.configure(text="\U0001f319")
        configure_treeview_style(dark_mode=self.dark_mode)
        self._refresh_current_screen()

    def _refresh_current_screen(self):
        children = self.content_frame.winfo_children()
        if not children:
            return
        screen = children[0]
        from app.ui.competitors_screen import CompetitorsScreen
        from app.ui.sectors_screen import SectorsScreen
        from app.ui.results_screen import ResultsScreen
        if isinstance(screen, CompetitorsScreen):
            screen._apply_tag_colors()
            screen._refresh_table()
        elif isinstance(screen, SectorsScreen):
            screen._apply_tag_colors()
            screen._refresh_all()
        elif isinstance(screen, ResultsScreen):
            screen._apply_tag_colors()
            screen._refresh()
