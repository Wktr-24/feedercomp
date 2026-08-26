# FeederComp — Program do obsługi zawodów wędkarskich

Program desktopowy do zarządzania zawodami wędkarskimi (spinning) dla klubu WKS Feederland.

## Co robi program

- Lista zawodników (dodawanie, opłaty, obecność)
- Rejestracja wylosowanych stanowisk → automatyczne przypisanie do sektora
- Wpisywanie wag ryb z wyszukiwaniem po nazwisku
- Automatyczna klasyfikacja (miejsca sektorowe → klasyfikacja końcowa)
- Finał dwudniowy — utworzenie dnia 2 z kopiowaniem listy zawodników i klasyfikacja generalna z sumy dwóch dni
- Generowanie PDF (klasyfikacja, lista zwycięzców, arkusze sektorów, klasyfikacja generalna)
- Drukowanie wyników na przenośnej drukarce

## Dla taty — uruchamianie

Plik `FeederComp.exe` — kliknij dwukrotnie. Nie wymaga instalacji.

Dane zapisują się automatycznie w `%APPDATA%\FeederComp\data.db` — przetrwają aktualizację programu.

**Kopie zapasowe:** przy każdym uruchomieniu program robi kopię bazy do `%APPDATA%\FeederComp\backups\` (trzymane jest 20 ostatnich). Żeby przywrócić dane po pomyłce: zamknij program, skopiuj wybrany plik `backups\data-<data>-<godzina>.db` w miejsce `data.db`, uruchom ponownie.

**Błędy:** jeśli program pokaże okno "Błąd programu", szczegóły są dopisywane do `%APPDATA%\FeederComp\error.log` — ten plik wystarczy wysłać do autora.

**Wydruki PDF** trafiają do folderu `FeederComp` w katalogu tymczasowym (`%TEMP%\FeederComp`), z datą i godziną w nazwie pliku; arkusze sektorów z jednego wydruku lądują w osobnym podfolderze.

Predefiniowane łowiska: Stawy Siedleckie (50 stanowisk, 5 sektorów), Lasomin (34 stanowiska) i Stawy Siedleckie — Finał (50 stanowisk, 6 sektorów — układ na finał dwudniowy).

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
