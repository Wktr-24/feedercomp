import sqlite3

import customtkinter as ctk

from app.constants import PAYMENT_DISPLAY, PAYMENT_LABELS, PAYMENT_REVERSE
from app.repositories import competitor_repo
from app.services.sector_service import SectorService


class EditCompetitorDialog(ctk.CTkToplevel):
    def __init__(self, master, app, competitor, on_save=None):
        super().__init__(master)
        self.withdraw()

        self.app = app
        self.competitor = competitor
        self.on_save = on_save
        self.sector_service = SectorService()

        self.original_phone = competitor.phone or ""
        self.original_payment = PAYMENT_LABELS.get(competitor.payment_status, PAYMENT_DISPLAY[0])
        self.original_station = str(competitor.station_number) if competitor.station_number else ""

        self.title(f"Edycja \u2014 {competitor.full_name}")
        self.geometry("350x240")
        self.resizable(False, False)

        self._build_ui()

        self.transient(master)
        self.update_idletasks()
        self.deiconify()
        self.grab_set()
        self.focus_set()

    def _build_ui(self):
        ctk.CTkLabel(self, text="Telefon:", font=("Segoe UI", 14)).place(x=20, y=20)
        self.phone_entry = ctk.CTkEntry(self, width=200)
        self.phone_entry.place(x=120, y=20)
        if self.original_phone:
            self.phone_entry.insert(0, self.original_phone)
        self.phone_entry.bind("<KeyRelease>", lambda _: self._check_changes())

        ctk.CTkLabel(self, text="Op\u0142ata:", font=("Segoe UI", 14)).place(x=20, y=65)
        self.payment_var = ctk.StringVar(value=self.original_payment)
        self.payment_var.trace_add("write", lambda *_: self._check_changes())
        ctk.CTkOptionMenu(
            self, variable=self.payment_var, values=PAYMENT_DISPLAY, width=200,
        ).place(x=120, y=65)

        ctk.CTkLabel(self, text="Stanowisko:", font=("Segoe UI", 14)).place(x=20, y=110)
        self.station_entry = ctk.CTkEntry(self, width=200)
        self.station_entry.place(x=120, y=110)
        if self.original_station:
            self.station_entry.insert(0, self.original_station)
        self.station_entry.bind("<KeyRelease>", lambda _: self._check_changes())

        self.save_btn = ctk.CTkButton(
            self, text="Zapisz", command=self._on_save, width=100, state="disabled",
        )
        self.save_btn.place(x=60, y=185)
        ctk.CTkButton(
            self, text="Anuluj", command=self.destroy, width=100,
        ).place(x=190, y=185)

    def _check_changes(self):
        phone_now = self.phone_entry.get().strip()
        payment_now = self.payment_var.get()
        station_now = self.station_entry.get().strip()
        changed = (
            phone_now != self.original_phone
            or payment_now != self.original_payment
            or station_now != self.original_station
        )
        self.save_btn.configure(state="normal" if changed else "disabled")

    def _on_save(self):
        from tkinter import messagebox
        phone = self.phone_entry.get().strip() or None
        if phone and (len(phone) != 9 or not phone.isdigit()):
            messagebox.showwarning("Błąd", "Numer telefonu musi mieć dokładnie 9 cyfr.", parent=self)
            return
        payment_status = PAYMENT_REVERSE.get(self.payment_var.get(), "paid")

        station_str = self.station_entry.get().strip()
        station_changed = station_str != self.original_station

        if station_changed:
            if station_str == "":
                # Clear station assignment
                conn = self.app.get_connection()
                try:
                    competitor_repo.update_station(conn, self.competitor.id, None, None)
                    competitor_repo.update_details(conn, self.competitor.id, phone, payment_status)
                    conn.commit()
                finally:
                    conn.close()
            else:
                if not self.competitor.is_present:
                    messagebox.showwarning("Błąd", "Nie można przypisać stanowiska nieobecnemu zawodnikowi.", parent=self)
                    return

                try:
                    station_number = int(station_str)
                except ValueError:
                    messagebox.showwarning("Błąd", "Numer stanowiska musi być liczbą.", parent=self)
                    return

                conn = self.app.get_connection()
                try:
                    self.sector_service.assign_station(
                        conn, self.competitor.id, station_number,
                        self.app.venue_id, self.app.competition_id,
                    )
                    competitor_repo.update_details(conn, self.competitor.id, phone, payment_status)
                    conn.commit()
                except ValueError as e:
                    messagebox.showwarning("Błąd", str(e), parent=self)
                    return
                except sqlite3.IntegrityError:
                    messagebox.showwarning("Błąd", f"Stanowisko {station_number} jest już zajęte.", parent=self)
                    return
                finally:
                    conn.close()
        else:
            conn = self.app.get_connection()
            try:
                competitor_repo.update_details(conn, self.competitor.id, phone, payment_status)
                conn.commit()
            finally:
                conn.close()

        if self.on_save:
            self.on_save()
        self.destroy()
