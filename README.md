# FeederComp — Program do obsługi zawodów wędkarskich

Program desktopowy do zarządzania zawodami wędkarskimi (spinning) dla klubu WKS Feederland.

## Co robi program

- Lista zawodników (dodawanie, opłaty, obecność)
- Rejestracja wylosowanych stanowisk → automatyczne przypisanie do sektora
- Wpisywanie wag ryb z wyszukiwaniem po nazwisku
- Automatyczna klasyfikacja (miejsca sektorowe → klasyfikacja końcowa)
- Generowanie PDF (klasyfikacja, lista zwycięzców, arkusze sektorów)
- Drukowanie wyników na przenośnej drukarce

## Wymagania

- Windows 10 lub 11
- Python 3.10 lub nowszy (pobrać z https://www.python.org/downloads/)
  - **Ważne:** przy instalacji zaznaczyć ✅ "Add Python to PATH"

## Instalacja i uruchomienie

```cmd
cd program-dla-taty
python -m venv .venv
.venv\Scripts\pip install customtkinter reportlab
.venv\Scripts\python -m app.main
```

## Budowanie pliku .exe (opcjonalne)

Aby stworzyć samodzielny plik `.exe`, który działa bez instalacji Pythona:

```cmd
.venv\Scripts\pip install pyinstaller
.venv\Scripts\pyinstaller --onefile --windowed --name=FeederComp app\main.py
```

Gotowy plik: `dist\FeederComp.exe` — skopiować na pulpit i kliknąć.

## Dane

Baza danych (SQLite) tworzy się automatycznie przy pierwszym uruchomieniu w folderze:
`%APPDATA%\FeederComp\data.db`

Predefiniowane łowiska: Stawy Siedleckie (50 stanowisk, 5 sektorów) i Lasomin (34 stanowiska).
