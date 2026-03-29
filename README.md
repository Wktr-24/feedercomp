# FeederComp — Program do obsługi zawodów wędkarskich

Program desktopowy do zarządzania zawodami wędkarskimi (spinning) dla klubu WKS Feederland.

## Co robi program

- Lista zawodników (dodawanie, opłaty, obecność)
- Rejestracja wylosowanych stanowisk → automatyczne przypisanie do sektora
- Wpisywanie wag ryb z wyszukiwaniem po nazwisku
- Automatyczna klasyfikacja (miejsca sektorowe → klasyfikacja końcowa)
- Generowanie PDF (klasyfikacja, lista zwycięzców, arkusze sektorów)
- Drukowanie wyników na przenośnej drukarce

## Dla taty — uruchamianie

Plik `FeederComp.exe` — kliknij dwukrotnie. Nie wymaga instalacji.

Dane zapisują się automatycznie w `%APPDATA%\FeederComp\data.db` — przetrwają aktualizację programu.

Predefiniowane łowiska: Stawy Siedleckie (50 stanowisk, 5 sektorów) i Lasomin (34 stanowiska).

## Dla developera — budowanie .exe

### Wymagania

- Windows 10/11
- Python 3.10+ (https://www.python.org/downloads/) — przy instalacji zaznaczyć "Add Python to PATH"

### Szybkie budowanie

Kliknij dwukrotnie `build.bat` — zbuduje `dist\FeederComp.exe`.

### Ręczne budowanie

```cmd
python -m venv .venv
.venv\Scripts\pip install customtkinter reportlab pyinstaller
.venv\Scripts\pyinstaller --onefile --windowed --name=FeederComp --add-data "seed_data;seed_data" --collect-all customtkinter app\main.py
```

### Uruchamianie w trybie developerskim (bez budowania .exe)

```cmd
.venv\Scripts\pip install customtkinter reportlab
.venv\Scripts\python -m app.main
```

### Testy

```cmd
.venv\Scripts\pip install pytest
.venv\Scripts\pytest tests/ -v
```
