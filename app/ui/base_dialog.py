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
import time
import tkinter

import customtkinter as ctk

from app.utils import UNMAP_GRACE_SECONDS, set_window_icon


class FeederCompDialog(ctk.CTkToplevel):
    def __init__(self, master, title: str, width: int, height: int):
        super().__init__(master)
        self.withdraw()

        # Establish owner relationship BEFORE touching window styles or icon.
        # On Win32, calling resizable() / wm_iconbitmap() before transient()
        # leaves WS_THICKFRAME / WS_MAXIMIZEBOX styles and the owner-chain
        # out of sync (Tk does SetParent(GWL_HWNDPARENT) at transient time
        # without re-running SWP_FRAMECHANGED). The corrupted owner-chain is
        # what makes the root window un-restorable from the taskbar after
        # Win+D / Show Desktop while a modal is open.
        self.transient(master)

        self._master_ref = master
        self._dialog_width = width
        self._dialog_height = height

        self.title(title)
        self.resizable(False, False)
        set_window_icon(self)

        # Track last <Unmap> timestamp to distinguish Win+D side-effects
        # from user-initiated restore clicks (see _restore_if_unmapped).
        # Initialise far in the past so the first <FocusIn> after start is
        # never treated as a Win+D race.
        self._last_unmap_time = float("-inf")
        self.bind("<Unmap>", self._on_unmap, add="+")

    def iconbitmap(self, bitmap=None, default=None):
        # CTkToplevel.__init__ schedules an unconditional ``after(200)``
        # lambda that calls ``self.iconbitmap(<CTk default ico>)`` and
        # bypasses our ``wm_iconbitmap`` override. Once the user-supplied
        # icon has been set (set_window_icon → _user_icon_set=True), we
        # turn this method into a no-op so the late CTk callback can't
        # overwrite the Feederland icon ~200 ms after the dialog appears.
        if getattr(self, "_user_icon_set", False):
            return None
        return tkinter.Toplevel.wm_iconbitmap(self, bitmap, default)

    def resizable(self, width=None, height=None):
        # Bypass CTkToplevel.resizable which schedules an after(10) callback
        # that triggers an extra withdraw/deiconify cycle ~10ms after the
        # dialog is shown, causing a visible flicker.
        # TODO: remove when CustomTkinter fixes the resizable() flicker
        # (bug present in 5.2.2).
        return tkinter.Toplevel.resizable(self, width, height)

    def show_modal(self) -> None:
        """Finalize the dialog lifecycle — call after UI is built."""
        # Order: deiconify → focus_set → grab_set. transient() is already
        # established in __init__ (must precede style changes — see above).
        # focus_set BEFORE grab_set per CPython issue #114422 advice — the
        # reverse order leaves the root window un-restorable from the
        # taskbar after Win+D / Show Desktop on Windows.
        self._center_on_master()
        self.deiconify()
        self.focus_set()
        self.grab_set()
        # Workaround for Tk bug ed6c3a787d / CPython #114422 (still open
        # in Tk 9.0.3, Nov 2025): after Win+D / Show Desktop with a modal
        # open, Tk's internal "mapped" flag desyncs from the actual WS_MINIMIZE
        # bit and the WM never gets a deiconify when the user clicks the
        # taskbar to restore. Bind <FocusIn> — Windows still delivers focus
        # events even in the broken state — and reconcile via deiconify()
        # whenever Tk says we're not mapped. (Aivar Annamaa, author of Thonny
        # IDE; confirmed by reporter on the official CPython issue.)
        self.bind("<FocusIn>", self._restore_if_unmapped, add="+")

    def _on_unmap(self, _event) -> None:
        self._last_unmap_time = time.monotonic()

    def _restore_if_unmapped(self, _event) -> None:
        # Two-window restoration after the Tk modal-restore bug
        # (CPython #114422 / Tk ed6c3a787d). When the user Alt+Tabs to the
        # modal, only the modal gets <FocusIn>; the root stays hidden, so
        # we restore root first, then self, then lift self.
        #
        # Don't fight intentional Win+D: Tk fires a transient <FocusIn>
        # while the window is being iconified by the WM. If <FocusIn>
        # arrives within UNMAP_GRACE_SECONDS of our last <Unmap>, treat
        # it as that race and skip restoration. Real user-initiated taskbar
        # clicks happen well after this grace window.
        # Known fragility: relies on Tk dispatching <Unmap> before the
        # transient <FocusIn> during a WM iconify. If that ordering ever
        # inverts (no Tk guarantee), Win+D would briefly restore — flag for
        # follow-up if ever observed in the wild.
        now = time.monotonic()
        if now - self._last_unmap_time < UNMAP_GRACE_SECONDS:
            return

        root_restored = False
        try:
            root = self._master_ref.winfo_toplevel()
            root_unmap_time = getattr(root, "_last_unmap_time", float("-inf"))
            if (
                not root.winfo_ismapped()
                and now - root_unmap_time >= UNMAP_GRACE_SECONDS
            ):
                root.deiconify()
                root_restored = True
        except Exception:
            # Best-effort recovery path — never crash the focus handler.
            pass

        if not self.winfo_ismapped():
            try:
                focused = self.focus_get()
                self.deiconify()
                if focused is not None:
                    focused.focus_set()
            except Exception:
                pass

        if root_restored:
            try:
                self.lift()
            except Exception:
                pass

    def destroy(self):
        # Release the grab before destroying — leaving a dangling grab on a
        # destroyed Toplevel desyncs Tk's WM state on Windows and contributes
        # to the "minimize then can't restore from taskbar" bug.
        try:
            self.grab_release()
        except tkinter.TclError:
            pass
        super().destroy()

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
