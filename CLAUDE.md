# FeederComp — kontekst projektu

## O projekcie

Desktopowa aplikacja offline (Windows 10/11) do zarządzania zawodami wędkarskimi (spinning) dla klubu WKS Feederland. Program zastępuje ręczny workflow w Excelu — listy zawodników, arkusze sektorów, sortowanie wyników. Docelowy użytkownik to organizator zawodów (tata Wiktora), który nie jest informatykiem — UX musi być prosty i szybki.

Pełne wymagania: `wymagania.md`
Dane referencyjne z prawdziwych zawodów: `zawody-Wiktor/` (nie w repozytorium, .gitignore)

## Stack

- **Python 3.10+** z CustomTkinter (GUI) + ttk.Treeview (tabele)
- **SQLite** — baza danych w `%APPDATA%/FeederComp/data.db`
- **ReportLab** — generowanie PDF
- **PyInstaller** — budowanie do pojedynczego `FeederComp.exe`

## Architektura

Trzy warstwy: UI → Services → Repositories. Brak frameworka, brak ORM.

```
app/
  main.py              — entry point
  config.py            — ścieżki, obsługa sys._MEIPASS (PyInstaller)
  database.py          — SQLite schema, seed danych
  models/              — dataclasses (Venue, Competition, Competitor)
  repositories/        — CRUD (venue_repo, competition_repo, competitor_repo,
                         excluded_station_repo, competition_sector_overrides_repo)
  services/
    sector_service.py  — mapowanie stanowisko→sektor, miejsca w sektorze
    ranking_service.py — klasyfikacja końcowa (KLUCZOWY algorytm)
    competition_service.py — tworzenie dnia 2 finału (kopiowanie listy + link)
    general_classification_service.py — klasyfikacja generalna z 2 dni (finał)
    print_service.py   — generowanie PDF (4 szablony)
  ui/
    app_window.py      — główne okno z nawigacją
    start_screen.py    — wybór łowiska, tworzenie/wznowienie zawodów, "Dzień 2"
    competitors_screen.py — lista zawodników, losowanie stanowisk
    sectors_screen.py  — zakładki sektorów, wpisywanie wag
    results_screen.py  — klasyfikacja końcowa + generalna (2 dni), PDF
    venue_editor.py    — edytor konfiguracji sektorów
    create_day2_dialog.py — dialog tworzenia dnia 2 finału
```

Łowiska: Stawy Siedleckie (5×10), Lasomin (4 sektory, warianty wyrównywania —
`wymagania-lasomin.md`), Stawy Siedleckie — Finał (6 sektorów 8/8/9/8/8/9,
tylko finał dwudniowy — `wymagania.md` §I).

## Kluczowy algorytm: klasyfikacja końcowa

1. Wewnątrz sektora: sortuj po wadze malejąco, przypisz miejsca 1, 2, 3...
2. Waga = 0 → wszyscy dzielą ostatnie miejsce (= liczba zawodników w sektorze)
3. Klasyfikacja końcowa: sortuj po punktach sektorowych ASC, potem wadze DESC
4. Waga = 0 → brak miejsca końcowego (wyświetlane jako „-")
5. Zweryfikowane na danych z 28.09.2025 (50 zawodników, 5 sektorów)

## Finał dwudniowy (klasyfikacja generalna)

1. Dzień 1 i 2 = dwie konkurencje połączone `competitions.linked_competition_id`
   (dzień 2 → dzień 1); dzień 2 tworzony przyciskiem z kopią listy zawodników
2. Klasyfikacja generalna (in-memory, nic nie persystowane): tylko zawodnicy
   z przydzielonym stanowiskiem w OBU dniach; parowanie po `utils.name_key`
   (normalize + casefold); suma pkt sektorowych ASC → suma wag DESC;
   ex aequo 1, 2, 2, 4; suma wag 0 → „-" na końcu
3. Obecny jeden dzień → całkowicie pomijany (decyzja organizatora)
4. Duplikaty nazwisk w ramach zawodów są blokowane przy dodawaniu/edycji
   (`competitor_repo.name_exists`); ewentualne historyczne duplikaty generalka
   wyklucza z ostrzeżeniem

## Polecenia

```bash
# Uruchomienie
.venv\Scripts\python -m app.main

# Testy
.venv\Scripts\pytest tests/ -v

# Lint
.venv\Scripts\ruff check app/ tests/

# Budowanie .exe
build.bat
```

## Konwencje

- Język UI: polski
- Commity i PR-y: angielski, Conventional Commits
- Waga: przechowywana w gramach (int), wyświetlana w kg z polskim formatem (przecinek)
- Status opłaty w bazie: 'paid', 'on_site', 'unpaid' — w UI: TAK, Na miejscu, Nie
- Brak obsługi remisów wagowych przy wadze > 0 (scenariusz uznany za nieosiągalny)
- `config.get_bundle_dir()` — używać zamiast `__file__` do lokalizacji plików (kompatybilność z PyInstaller)

## Co jeszcze nie zrobione

- (nic odroczonego — finał dwudniowy i Lasomin zaimplementowane; migracja na
  `schema_migrations` table dopiero przy trzeciej migracji w `database.py`)
