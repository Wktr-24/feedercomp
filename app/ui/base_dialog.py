"""Base class for modal dialogs in FeederComp.

Encapsulates the full lifecycle of a CTkToplevel modal dialog:
  1. Hide window immediately after construction
  2. Apply title, sizing, icon
  3. Let subclass build its UI
  4. Center on master, make transient, show, grab focus

Subclasses should:
  - Call ``super().__init__(master, title, width, height)`` first
  - Build their UI (placing widgets)
  - Call ``self.show_modal()`` at the end of ``__init__``
"""
import tkinter

import customtkinter as ctk

from app.utils import set_window_icon


class FeederCompDialog(ctk.CTkToplevel):
    def __init__(self, master, title: str, width: int, height: int):
        super().__init__(master)
        self.withdraw()

        self._master_ref = master
        self._dialog_width = width
        self._dialog_height = height

        self.title(title)
        self.resizable(False, False)
        set_window_icon(self)

    def resizable(self, width=None, height=None):
        # Bypass CTkToplevel.resizable which schedules an after(10) callback
        # that triggers an extra withdraw/deiconify cycle ~10ms after the
        # dialog is shown, causing a visible flicker.
        # TODO: remove when CustomTkinter fixes the resizable() flicker
        # (bug present in 5.2.2).
        return tkinter.Toplevel.resizable(self, width, height)

    def show_modal(self) -> None:
        """Finalize the dialog lifecycle — call after UI is built."""
        self._center_on_master()
        self.transient(self._master_ref)
        self.update_idletasks()
        self.deiconify()
        self.grab_set()
        self.focus_set()

    def resize_to(self, width: int, height: int) -> None:
        """Update dialog target dimensions before show_modal() is called.

        Call this after building UI if the required size is only known
        after widgets are laid out (e.g., dynamic content).
        """
        self._dialog_width = width
        self._dialog_height = height

    def _center_on_master(self) -> None:
        # Center on the top-level window, not the immediate master frame —
        # the master is often a CTkFrame (e.g. CompetitorsScreen) which may
        # be narrower than the dialog, causing off-center placement.
        #
        # DPI note: winfo_width/rootx return already-scaled physical pixels,
        # while CTkToplevel.geometry() applies window_scaling to width/height
        # but NOT to x/y. Convert the logical dialog size to physical pixels
        # before computing offsets so centering holds on non-100% DPI.
        width = self._dialog_width
        height = self._dialog_height
        try:
            top = self._master_ref.winfo_toplevel()
            top.update_idletasks()
            mx = top.winfo_rootx()
            my = top.winfo_rooty()
            mw = top.winfo_width()
            mh = top.winfo_height()
            scaling = self._get_window_scaling()
        except tkinter.TclError:
            self.geometry(f"{width}x{height}")
            return
        phys_width = int(round(width * scaling))
        phys_height = int(round(height * scaling))
        x = mx + max(0, (mw - phys_width) // 2)
        y = my + max(0, (mh - phys_height) // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
