from tkinter import TclError, messagebox

import customtkinter as ctk

from app.repositories import (
    competition_sector_overrides_repo,
    excluded_station_repo,
    venue_repo,
)
from app.services.sector_service import (
    SectorService,
    load_venue_config,
    match_variant_for_selection,
    reconcile_competitor_sectors,
)
from app.ui.base_dialog import FeederCompDialog


def compute_resulting_sizes(
    sector_info: list[dict],
    excluded_stations: set[int],
    overrides: dict[int, str] | None = None,
) -> dict[str, int]:
    """Compute the per-sector competitor count after exclusions and overrides.

    `excluded_stations` is the set of station numbers removed from the pond.
    `overrides` reassigns specific stations to a different sector (e.g. Lasomin
    variant 2 moves station 13 from C to D). Returns {sector_name: count}.
    """
    overrides = overrides or {}
    sizes: dict[str, int] = {sector["name"]: 0 for sector in sector_info}
    for sector in sector_info:
        for station in sector["stations"]:
            if station in excluded_stations:
                continue
            target = overrides.get(station, sector["name"])
            if target in sizes:
                sizes[target] += 1
    return sizes


def _format_distribution(sizes: dict[str, int], sector_order: list[str]) -> str:
    """Format sector sizes as compact 'D=8 C=8 B=8 A=8' string in given order."""
    return " ".join(f"{name}={sizes.get(name, 0)}" for name in sector_order)


def split_stations_to_banks(
    sector_stations: list[int],
    banks: dict | None,
    total_stations: int,
) -> tuple[list[int], list[int]]:
    """Split a sector's stations into (top, bottom) in left-to-right render order.

    With explicit `banks` config (per-venue): use the ordered lists in
    banks["top"] / banks["bottom"]. Without (e.g. Stawy): fall back to the
    half-split heuristic — low numbers on top (descending), high on bottom (ascending).
    """
    sector_set = set(sector_stations)
    if banks:
        top = [s for s in banks["top"] if s in sector_set]
        bot = [s for s in banks["bottom"] if s in sector_set]
        return top, bot
    half = total_stations // 2
    top = sorted([s for s in sector_stations if s <= half], reverse=True)
    bot = sorted([s for s in sector_stations if s > half])
    return top, bot


class BalanceSectorsDialog(FeederCompDialog):
    def __init__(self, master, app, competition_id, venue_id, on_confirm=None):
        super().__init__(master, "Wyrównanie sektorów", 1100, 500)

        self.app = app
        self.competition_id = competition_id
        self.venue_id = venue_id
        self.on_confirm = on_confirm
        self.sector_service = SectorService()
        self.selected_stations: set[tuple[str, int]] = set()
        self.station_buttons: dict[tuple[str, int], ctk.CTkButton] = {}
        self._hover_after_id = None
        self._hover_leave_after_id = None

        conn = self.app.get_connection()
        try:
            self._load_data(conn)
            self._build_ui()
        finally:
            conn.close()

        # Dynamically size dialog to fit actual content (prevents cutoff on DPI-scaled displays).
        # winfo_reqwidth() returns the physical size (already includes CTk widget_scaling
        # and DPI), but geometry() re-applies window_scaling on top. Divide by the
        # window scaling factor so we pass logical units to resize_to().
        self.update_idletasks()
        scaling = self._get_window_scaling()
        logical_req_w = int(self.winfo_reqwidth() / scaling) + 40
        logical_req_h = int(self.winfo_reqheight() / scaling) + 20
        req_width = max(self._dialog_width, logical_req_w)
        req_height = max(self._dialog_height, logical_req_h)
        # Never grow past the screen: the dialog is not resizable and has no
        # scrollbar, so an over-wide window would push the rightmost sector's
        # buttons off-screen (6 sectors + column padding on a small laptop).
        max_logical_w = int(self.winfo_screenwidth() / scaling) - 40
        req_width = min(req_width, max_logical_w)
        self.resize_to(req_width, req_height)

        self.show_modal()
        # Re-anchor separators after the window settles at its final size
        # (see _place_separators for why the <Configure> binding alone is
        # not enough).
        self._sep_after_id = self.after(100, self._place_separators)

    def _load_data(self, conn):
        from app.repositories import competitor_repo
        competitors = competitor_repo.get_all(conn, self.competition_id)
        self.present_count = sum(1 for c in competitors if c.is_present)
        self.assigned_stations_info = {
            c.station_number: c.full_name
            for c in competitors
            if c.station_number is not None
        }
        self.assigned_stations = set(self.assigned_stations_info.keys())

        self.already_excluded = excluded_station_repo.get_excluded(conn, self.competition_id)
        already_excluded_set = {
            (e["sector_name"], e["station_number"]) for e in self.already_excluded
        }

        all_sectors = venue_repo.get_sectors(conn, self.venue_id)
        sector_names = venue_repo.get_sector_names(conn, self.venue_id)
        venue = venue_repo.get_by_id(conn, self.venue_id)
        self.venue_name = venue.name if venue else ""
        venue_cfg = load_venue_config(self.venue_name)
        self._banks = venue_cfg.get("banks") if venue_cfg else None

        # Persisted overrides from a previous "Wyrównanie sektorów" save
        # (e.g. Lasomin variant 2: station 13 reassigned C → D for this competition).
        self._existing_overrides = competition_sector_overrides_repo.get_overrides(
            conn, self.competition_id,
        )

        self.total_stations = len(all_sectors)
        self.total_to_exclude = max(0, self.total_stations - self.present_count)
        self.sector_info: list[dict] = []
        for name in sector_names:
            stations = sorted(s.station_number for s in all_sectors if s.sector_name == name)
            self.sector_info.append({"name": name, "stations": stations})

        # Apply existing overrides to sector_info so the dialog renders the
        # competition's effective layout (moved stations, balanced sector sizes).
        for station, target_sector in self._existing_overrides.items():
            for sec in self.sector_info:
                if station in sec["stations"]:
                    sec["stations"].remove(station)
                    break
            for sec in self.sector_info:
                if sec["name"] == target_sector:
                    sec["stations"].append(station)
                    sec["stations"].sort()
                    break

        self.selected_stations = set(already_excluded_set)
        self.original_selection = set(self.selected_stations)

    def _build_ui(self):
        self.sector_labels: dict[str, ctk.CTkLabel] = {}
        sectors_lr = list(reversed(self.sector_info))
        sector_banks = {
            sector["name"]: split_stations_to_banks(
                sector["stations"], self._banks, self.total_stations,
            )
            for sector in self.sector_info
        }
        # Proportional column widths so a sector with more stations (e.g. D after
        # Lasomin variant 2: 10 stations vs 8 elsewhere) renders wider than its
        # neighbours.
        sector_weights = [len(s["stations"]) for s in sectors_lr]

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
        top_frame.pack(fill="x", padx=10, pady=(5, 0))
        for i, weight in enumerate(sector_weights):
            top_frame.grid_columnconfigure(i, weight=weight)

        self._top_inners: list[ctk.CTkFrame] = []
        for idx, sector in enumerate(sectors_lr):
            cell = ctk.CTkFrame(top_frame, fg_color="transparent")
            cell.grid(row=0, column=idx, sticky="nsew")
            # Inner frame centers buttons within the uniform-width cell
            inner = ctk.CTkFrame(cell, fg_color="transparent")
            inner.pack(expand=True)
            self._top_inners.append(inner)
            top_stations, _ = sector_banks[sector["name"]]
            for station in top_stations:
                key = (sector["name"], station)
                btn = self._create_station_button(inner, key)
                btn.pack(side="left", padx=2, pady=2)

        # --- pond rectangle ---
        pond_frame = ctk.CTkFrame(self, fg_color="#1a5276", height=80)
        pond_frame.pack(fill="x", padx=10, pady=0)
        pond_frame.pack_propagate(False)
        for i, weight in enumerate(sector_weights):
            pond_frame.grid_columnconfigure(i, weight=weight)
        pond_frame.grid_rowconfigure(0, weight=1)

        for idx, sector in enumerate(sectors_lr):
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
            lbl.grid(row=0, column=idx, sticky="nsew")
            self.sector_labels[sector["name"]] = lbl

        # Separators between sectors — placed at the MEASURED grid column
        # boundaries once the pond frame is laid out (see _place_separators).
        # Idealized cumulative fractions are not enough: grid distributes
        # only surplus space by weight, so a bank cell whose buttons exceed
        # the sector's proportional share (e.g. final venue: sector C has 5
        # top-bank buttons squeezed into a 9/50 column) pushes the real
        # column edges away from the ideal fractions.
        self._pond_frame = pond_frame
        self._separators = [
            ctk.CTkFrame(pond_frame, width=2, fg_color="#E74C3C")
            for _ in range(len(sectors_lr) - 1)
        ]
        pond_frame.bind("<Configure>", self._place_separators, add="+")

        # --- bottom bank ---
        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.pack(fill="x", padx=10, pady=(0, 5))
        for i, weight in enumerate(sector_weights):
            bottom_frame.grid_columnconfigure(i, weight=weight)

        self._bottom_inners: list[ctk.CTkFrame] = []
        for idx, sector in enumerate(sectors_lr):
            cell = ctk.CTkFrame(bottom_frame, fg_color="transparent")
            cell.grid(row=0, column=idx, sticky="nsew")
            # Inner frame centers buttons within the uniform-width cell
            inner = ctk.CTkFrame(cell, fg_color="transparent")
            inner.pack(expand=True)
            self._bottom_inners.append(inner)
            _, bot_stations = sector_banks[sector["name"]]
            for station in bot_stations:
                key = (sector["name"], station)
                btn = self._create_station_button(inner, key)
                btn.pack(side="left", padx=2, pady=2)

        self._sector_row_frames = (top_frame, pond_frame, bottom_frame)
        self._sync_sector_columns(sector_weights)

        # --- counter and action buttons ---
        self.counter_label = ctk.CTkLabel(
            self,
            text=self._counter_text(),
            font=("Segoe UI", 13, "bold"),
        )
        self.counter_label.pack(padx=10, pady=(5, 2))

        self.hover_status_label = ctk.CTkLabel(
            self, text="", font=("Segoe UI", 13),
            text_color=("gray40", "gray70"),
        )
        self.hover_status_label.pack(padx=10, pady=(0, 2))

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

    def _sync_sector_columns(self, sector_weights: list[int]) -> None:
        """Give all three rows (top bank, pond, bottom bank) identical grid
        columns. Each column's minimum width is the wider of its two bank
        cells, measured physically (DPI-safe). Without a shared minsize the
        top and bottom grids diverge whenever one bank holds more buttons
        than the sector's proportional share fits (final venue: sector C has
        5 top vs 4 bottom stations, F the reverse) — and then no single
        separator line can match both banks.

        The extra padding guarantees breathing room between a full cell's
        edge buttons and the sector separators — without it the fullest
        cell's buttons sit flush against the lines, which reads as the line
        "pointing at" a station tile.
        """
        self.update_idletasks()
        pad = int(round(18 * self._get_window_scaling()))
        for idx, weight in enumerate(sector_weights):
            minsize = pad + max(
                self._top_inners[idx].winfo_reqwidth(),
                self._bottom_inners[idx].winfo_reqwidth(),
            )
            for frame in self._sector_row_frames:
                frame.grid_columnconfigure(idx, weight=weight, minsize=minsize)

    def _place_separators(self, _event=None) -> None:
        # grid_bbox(col, 0)[0] is the real left edge of column `col` after
        # layout — i.e. the boundary between sectors col-1 and col (with
        # anchor="n" the 2px line deliberately straddles that edge by 1px,
        # centering on the boundary). Re-runs
        # on every <Configure> of the pond frame AND once shortly after the
        # dialog is shown (grid_bbox can be stale at the first <Configure>,
        # before Tk's idle-time grid pass ran for the final window size —
        # and the pond frame's fixed outer size means no later <Configure>
        # would arrive to correct it). Placing at the same coords is an
        # idempotent no-op.
        try:
            if not self.winfo_exists():
                return
            for idx, sep in enumerate(self._separators, start=1):
                bbox = self._pond_frame.grid_bbox(idx, 0)
                if not bbox or bbox[2] <= 0:
                    continue
                sep.place(x=bbox[0], y=0, relheight=1.0, anchor="n")
        except TclError:
            pass

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
            full_name = self.assigned_stations_info[station]
            btn.bind("<Enter>", lambda e, name=full_name: self._on_station_hover_enter(name))
            btn.bind("<Leave>", lambda e: self._on_station_hover_leave())
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

        # Build the venue-default sector_info (existing overrides reversed)
        # ONCE and use it for every size computation in this method, so the
        # popup distribution and the final diff>1 check both base their math
        # on the same canonical layout regardless of what overrides happened
        # to be applied previously.
        default_sector_info = self._default_sector_info_snapshot()

        # Detect a known balance variant for the current selection
        # (e.g. Lasomin variant 2: {17, 18} → suggest moving 13 from C to D).
        # Only triggers when the variant defines non-empty sector_overrides.
        excluded_stations = {station for _, station in checked}
        variant = match_variant_for_selection(self.venue_name, excluded_stations)
        pending_overrides: dict[int, str] = {}
        if variant and variant.get("sector_overrides"):
            override_map = {
                int(s): sec for s, sec in variant["sector_overrides"].items()
            }
            if self._existing_overrides == override_map:
                # Same selection + same variant already saved before — keep silently,
                # don't pester the user with the popup on every confirm.
                pending_overrides = override_map
            else:
                sector_order = [s["name"] for s in reversed(self.sector_info)]
                sizes_with = compute_resulting_sizes(
                    default_sector_info, excluded_stations, override_map,
                )
                sizes_without = compute_resulting_sizes(
                    default_sector_info, excluded_stations,
                )
                moves = ", ".join(
                    f"stanowisko {station} z sektora "
                    f"{self._venue_default_sector(station)} do sektora {new_sector}"
                    for station, new_sector in override_map.items()
                )
                msg = (
                    f"Zaznaczenie pasuje do wzorca wyrównywania Lasomin.\n\n"
                    f"Sugerowane przesunięcie: {moves}.\n\n"
                    f"Rozkład sektorów:\n"
                    f"  z przesunięciem: {_format_distribution(sizes_with, sector_order)}\n"
                    f"  bez przesunięcia: {_format_distribution(sizes_without, sector_order)}\n\n"
                    f"Zastosować przesunięcie?"
                )
                if messagebox.askyesno("Wariant Lasomin", msg, parent=self):
                    pending_overrides = override_map

        sizes = list(
            compute_resulting_sizes(
                default_sector_info, excluded_stations, pending_overrides or None,
            ).values()
        )
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
            competition_sector_overrides_repo.set_overrides(
                conn, self.competition_id, pending_overrides,
            )
            self._reconcile_competitor_sectors(conn)
            conn.commit()
        finally:
            conn.close()

        if self.on_confirm:
            self.on_confirm()
        self.destroy()

    def _venue_default_sector(self, station: int) -> str:
        """Look up the venue's canonical sector for a station, ignoring any
        overrides currently applied to self.sector_info."""
        cfg = load_venue_config(self.venue_name)
        if not cfg:
            return "?"
        for sector_name, stations in cfg.get("sectors", {}).items():
            if station in stations:
                return sector_name
        return "?"

    def _default_sector_info_snapshot(self) -> list[dict]:
        """Return a fresh copy of sector_info with self._existing_overrides
        reversed — i.e. the venue's canonical layout for this competition.

        Used for size computations that must be invariant to whatever
        overrides happen to be currently saved (so the popup display and
        the final diff>1 check don't double-apply prior overrides).
        """
        snapshot = [
            {"name": s["name"], "stations": list(s["stations"])}
            for s in self.sector_info
        ]
        for station in self._existing_overrides:
            for sec in snapshot:
                if station in sec["stations"]:
                    sec["stations"].remove(station)
                    break
            canonical = self._venue_default_sector(station)
            for sec in snapshot:
                if sec["name"] == canonical:
                    sec["stations"].append(station)
                    sec["stations"].sort()
                    break
        return snapshot

    def _reconcile_competitor_sectors(self, conn) -> None:
        reconcile_competitor_sectors(
            conn, self.competition_id, self.venue_id, self.sector_service,
        )

    def _restore_all(self):
        # "Przywróć wszystkie" must reset the competition's balancing state
        # in full — both station exclusions and any sector overrides applied
        # (e.g. Lasomin variant 2's 13 → D shift). Otherwise the dialog reopens
        # with stale overrides while the user expects a clean slate.
        # Reconcile competitor.sector_name for any already-assigned stations
        # so scoring doesn't keep using a sector that no longer applies.
        conn = self.app.get_connection()
        try:
            excluded_station_repo.clear_excluded(conn, self.competition_id)
            competition_sector_overrides_repo.clear_overrides(conn, self.competition_id)
            self._reconcile_competitor_sectors(conn)
            conn.commit()
        finally:
            conn.close()

        if self.on_confirm:
            self.on_confirm()
        self.destroy()

    def _on_station_hover_enter(self, full_name: str) -> None:
        # Cancel pending clear — we're still hovering (possibly over a sibling
        # child widget of the same button, which fires spurious Leave/Enter)
        if self._hover_leave_after_id is not None:
            self.after_cancel(self._hover_leave_after_id)
            self._hover_leave_after_id = None
        if self._hover_after_id is not None:
            self.after_cancel(self._hover_after_id)
        self._hover_after_id = self.after(150, lambda: self._show_hover_name(full_name))

    def _on_station_hover_leave(self) -> None:
        if self._hover_after_id is not None:
            self.after_cancel(self._hover_after_id)
            self._hover_after_id = None
        # Debounce clear — CTkButton bindings fire Leave/Enter when cursor
        # moves between internal _canvas and _text_label widgets of the same
        # button. Wait 50ms to see if Enter fires on any button before clearing.
        if self._hover_leave_after_id is not None:
            self.after_cancel(self._hover_leave_after_id)
        self._hover_leave_after_id = self.after(50, self._clear_hover_label)

    def _clear_hover_label(self) -> None:
        self._hover_leave_after_id = None
        if self.hover_status_label.winfo_exists():
            self.hover_status_label.configure(text="")

    def _show_hover_name(self, full_name: str) -> None:
        self._hover_after_id = None
        if not self.hover_status_label.winfo_exists():
            return
        self.hover_status_label.configure(text=full_name)

    def destroy(self):
        for attr in ('_hover_after_id', '_hover_leave_after_id', '_sep_after_id'):
            val = getattr(self, attr, None)
            if val is not None:
                try:
                    self.after_cancel(val)
                except Exception:
                    pass
                setattr(self, attr, None)
        super().destroy()
