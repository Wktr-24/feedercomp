# Lasomin — specyfikacja sektorów i wyrównywania

> **Dla kogo:** instancja Claude Code pracująca w Windows nad implementacją FeederComp.
> **Cel:** dodać pełną obsługę łowiska **Lasomin** (drugiego venue obok Stawów Siedleckich).
> **Najważniejszy haczyk:** algorytm wyrównywania sektorów **różni się** od Stawów —
> przy braku ≥2 zawodników nie wystarczy wykluczyć skrajne stanowiska, trzeba też
> **przesunąć granicę między sektorami C i D**.
>
> **Źródło:** demo z organizatorem zawodów (Janusz, tata Wiktora) z dnia 2026-05-03.
> Rozmowa nagrana (`nagranie-4.m4a`, 49 min, transkrypcja w `nagrania/`), tata
> ręcznie narysował schemat łowiska na kartce (`IMG_1150.jpg` w katalogu projektu).
> Cała wiedza ze schematu i nagrania jest przepisana niżej — nie potrzeba sięgać
> do tych źródeł.

---

## 1. Stan obecny w kodzie

- `seed_data/venues.json`: Lasomin istnieje jako venue z `total_stations=34`,
  ale `sectors: {}` (puste). Trzeba uzupełnić.
- `app/services/sector_service.py`: wyrównywanie obsłużone tylko dla Stawów
  (proste wykluczanie skrajnych stanowisk).
- `app/ui/balance_sectors_dialog.py`: dialog z układem "stawu" (zrefaktorowany pod
  Stawy Siedleckie). Trzeba rozszerzyć, by wizualizował **przesunięcie granicy
  sektora** dla Lasomina.
- Komentarz w `CLAUDE.md` mówi obecnie: *"Konfiguracja sektorów Lasomina (brak danych
  — venue istnieje, sektory puste)"*. Po implementacji można skreślić — i ewentualnie
  podlinkować ten dokument.

---

## 2. Specyfikacja venue: Lasomin

- **Łączna liczba stanowisk:** 34
- **Liczba sektorów:** 4 (`A`, `B`, `C`, `D`)
- **Konwencja układu:** sektory **od prawej do lewej**: `A` najbardziej po prawej,
  `D` najbardziej po lewej (analogicznie jak na Stawach Siedleckich, gdzie A jest
  po prawej, E po lewej).
- **Asymetryczny rozkład stanowisk:** **9-9-8-8** (D-C-B-A) — 34 nie dzieli się
  równo na 4, więc dwa środkowe sektory mają po jednym dodatkowym stanowisku.
- **Topologia:** wąski staw, stanowiska na dwóch brzegach:
  - Górny brzeg: stanowiska 18–34 (numerowane od lewej do prawej).
  - Dolny brzeg: stanowiska 1–17 (numerowane od prawej do lewej — staw "się zawija",
    czyli 1 jest skrajnym prawym stanowiskiem dolnego brzegu, sąsiadującym
    geometrycznie ze stanowiskiem 34 z górnego brzegu).

### 2.1 Schemat (tekstowy odpowiednik rysunku taty)

```
                                 GÓRNY BRZEG
       18  19  20  21  22 │ 23  24  25  26 │ 27  28  29  30 │ 31  32  33  34
      ┌──────────────────────────────────────────────────────────────────────┐
      │       D  (9)       │     C  (9)     │     B  (8)     │     A  (8)    │
      └──────────────────────────────────────────────────────────────────────┘
       17  16  15  14    │ 13  12  11  10  9 │ 8   7   6   5  │ 4   3   2   1
                                 DOLNY BRZEG
```

Granice sektorów (przerywane linie pionowe na rysunku) przebiegają:

| Granica | Górny brzeg | Dolny brzeg |
|---------|-------------|-------------|
| D / C   | między 22 a 23 | między 14 a 13 |
| C / B   | między 26 a 27 | między 9 a 8   |
| B / A   | między 30 a 31 | między 5 a 4   |

### 2.2 Konfiguracja sektorów (komplet, do `seed_data/venues.json`)

```json
{
  "name": "Lasomin",
  "total_stations": 34,
  "sectors": {
    "A": [1, 2, 3, 4, 31, 32, 33, 34],
    "B": [5, 6, 7, 8, 27, 28, 29, 30],
    "C": [9, 10, 11, 12, 13, 23, 24, 25, 26],
    "D": [14, 15, 16, 17, 18, 19, 20, 21, 22]
  }
}
```

Suma: `8 + 8 + 9 + 9 = 34` ✓.

---

## 3. Reguła wyrównywania sektorów (KLUCZOWE — różnica vs. Stawy)

### 3.1 Tło

Na **Stawach Siedleckich** (50 stanowisk, 5 sektorów po 10) algorytm jest prosty:
gdy brakuje N zawodników, użytkownik klika N **skrajnych** stanowisk w dialogu
"Wyrównaj sektory", wykluczone stanowiska podświetlają się na czerwono, sektory
tylko się kurczą (np. z 10 robi się 9 lub 8). Granice sektorów się **nie ruszają**.

Na **Lasominie** dla N≥2 trzeba zrobić **dodatkowo przesunięcie granicy między
sektorami C i D**, bo bez tego rozkład robi się jeszcze bardziej nierówny.

### 3.2 Warianty (zweryfikowane z tatą na rysunku)

#### Wariant 0: komplet (34 osoby)

- Konfiguracja standardowa z §2.2.
- Rozkład: **9 - 9 - 8 - 8** (D-C-B-A).
- Granice sektorów: standardowe (D/C między 14 i 13).

#### Wariant 1: brak 1 osoby (33 osób)

- Wyklucz stanowisko **18** (skrajne lewe górne).
- Sektor D zmniejsza się do 8: `[14, 15, 16, 17, 19, 20, 21, 22]`.
- Pozostałe sektory bez zmian.
- Rozkład: **8 - 9 - 8 - 8**.
- Granice sektorów: **bez zmian**.

#### Wariant 2: brak 2 osób (32 osób) — ⚠️ TUTAJ PRZESUWAMY GRANICĘ

- Wyklucz stanowiska **17 i 18** (oba skrajne lewe).
- **Przesuń granicę D/C**: stanowisko **13** przechodzi z sektora C do D.
- Nowe składy:
  - **D**: `[13, 14, 15, 16, 19, 20, 21, 22]` (8 stanowisk)
  - **C**: `[9, 10, 11, 12, 23, 24, 25, 26]` (8 stanowisk)
  - **B**: bez zmian (8)
  - **A**: bez zmian (8)
- Rozkład: **8 - 8 - 8 - 8** (idealnie równe).
- Nowa granica D/C: na dolnym brzegu między 12 a 13 (zamiast między 14 a 13).

> Cytat z taty: *"odpada osiemnastka i (...) siedemnastka. Te dwie wypadają. (...)
> ale muszę przesunąć wtedy linię sektorową i jeszcze zahaczyć tą trzynastkę,
> żeby tutaj było cztery, cztery i tutaj zrobi się cztery i cztery. I wtedy są
> równe sektory po ośmiu."*

#### Wariant 3: brak 3 osób (31 osób)

- Konfiguracja **jak w wariancie 2** (17, 18 wykluczone, 13 w D).
- **Dodatkowo wyklucz stanowisko 1** (sektor A).
  - **Uwaga**: stanowisko 1 nie jest "skrajne" w sensie geometrycznym —
    tata kieruje się tutaj wiedzą wędkarską, że *"jedynka jest najsłabiej
    łowiąca na tym łowisku"* (najgorsze pod względem ryb).
- Sektor A zmniejsza się do 7: `[2, 3, 4, 31, 32, 33, 34]`.
- Rozkład: **8 - 8 - 8 - 7** (asymetria w sektorze A).

> Cytat z taty: *"jak nie przyjedzie trzech. To zostaje, yy, ten sam układ co
> przy, przy dwóch. Ale wypada jedynka, bo ona jest najsłabiej łowiąca na tym
> łowisku."*

⚠️ **Uwaga**: tata przeszedł nad tym płynnie i **nie potwierdził wprost**, że
8-8-8-7 jest akceptowalne. Bezpiecznie potwierdzić u taty, zanim zrobimy to
automatycznie. Może preferowalne jest, żeby algorytm **podpowiadał** wykluczenie
1, ale finalnie tata sam klika (tak jak na Stawach).

#### Wariant 4+: brak ≥4 osób

**Nie omówione w nagraniu.** Należy dopytać tatę przed implementacją.
Możliwe podejście: zostawić jako manual fallback (algorytm nic nie robi, tata
sam wybiera stanowiska do wykluczenia z dialogu).

### 3.3 Tabela podsumowująca

| N brakujących | Wykluczone stanowiska | Przesunięcie granicy | Rozkład (D-C-B-A) |
|---------------|----------------------|----------------------|-------------------|
| 0             | —                    | —                    | 9-9-8-8           |
| 1             | 18                   | —                    | 8-9-8-8           |
| 2             | 17, 18               | 13: C → D            | 8-8-8-8           |
| 3             | 17, 18, 1            | 13: C → D            | 8-8-8-7           |
| ≥4            | (do uzgodnienia)     | (do uzgodnienia)     | ?                 |

---

## 4. Implementacja — sugerowana ścieżka

### 4.1 `seed_data/venues.json`

Wpisz Lasomina jak w §2.2. **Pamiętaj**: aplikacja seeduje bazę przy pierwszym
starcie (przez `app/database.py`). Lokalna `data.db` (`%APPDATA%/FeederComp/data.db`)
nie zostanie zaktualizowana automatycznie — trzeba ją skasować (utrata historycznych
zawodów) lub dodać migrację seedu. Decyzja zależy od tego, czy są już jakieś
historyczne dane w `%APPDATA%`.

### 4.2 `app/services/sector_service.py` (lub odpowiednik)

Logika wyrównywania musi rozpoznawać venue. **Odradzam** rozsiewanie
`if venue_name == "Lasomin"` po kodzie — lepiej:

- **Opcja A (preferowana, deklaratywna)**: dodać w `venues.json` pole
  `balance_variants` z mapą `{N_missing: {excluded: [...], sector_overrides: {...}}}`
  i niech serwis czyta po prostu konfigurację. Logika wykonawcza staje się jedna,
  niezależna od venue.
- **Opcja B (krótsza, mniej elastyczna)**: hardkoduj warianty Lasomina w
  `sector_service.py`, ale wyizoluj je do osobnej funkcji/klasy, np. 
  `LasominBalancer`, którą serwis wybiera po nazwie venue.

Zachowaj wstecz kompatybilność — Stawy Siedleckie muszą działać jak dotychczas
(istniejące testy nie powinny się zepsuć).

### 4.3 `app/ui/balance_sectors_dialog.py`

Dialog aktualnie pokazuje wykluczone stanowiska na czerwono. Dla Lasomina trzeba
też **wizualizować przesunięcie granicy**. Tata na kartce narysował to dwiema
przerywanymi liniami oznaczonymi `I` (oryginalna granica D/C między 14 a 13)
i `II (gdy brakuje 2-ch)` (nowa granica między 13 a 12). Analogiczna wizualizacja
na ekranie:

- Stanowiska 17 i 18: czerwone (wykluczone).
- Stanowisko 13: zmienia kolor sektora (z C na D) — pokazać wizualnie, np.
  obwódka w kolorze sektora D albo strzałka.
- Linia separatora D/C: przesuwa się wizualnie, lub rysujemy obie linie
  (oryginalną na szaro, nową na zielono).

Do wymyślenia konkretny UX — najprostsze: po prostu redrawing diagramu z nowym
podziałem po kliknięciu "Zatwierdź".

### 4.4 Testy

`tests/test_sector_service.py`:

- Test wariantu 0 (Lasomin, 34 osoby): rozkład 9-9-8-8.
- Test wariantu 1 (Lasomin, brak 1): exclude 18 → 8-9-8-8.
- Test wariantu 2 (Lasomin, brak 2): exclude 17, 18 + shift 13 z C do D → 8-8-8-8.
- Test wariantu 3 (Lasomin, brak 3): exclude 17, 18, 1 → 8-8-8-7.
- Regresje: wszystkie istniejące testy Stawów muszą nadal przechodzić.

---

## 5. Otwarte pytania (do potwierdzenia z tatą)

1. **Wariant 3 (brak 3 osób)** — czy 8-8-8-7 jest akceptowalne, czy lepiej
   wykluczyć też np. stanowisko 34 dla symetrii?
2. **Wariant 4+ (brak 4 i więcej osób)** — co robimy?
3. **Reguła "wypada jedynka, bo najsłabiej łowi"** — czy to jest property tylko
   Lasomina (specyficzna wiedza wędkarska o tym łowisku), czy ogólny wzorzec
   ("każde łowisko ma wskazaną najsłabszą pozycję")? Jeśli ogólne — dorzucić
   konfigurację per-venue.
4. **UX dialogu** — czy automat (kliknięcie "Wyrównaj sektory" robi wszystko od
   razu wg liczby brakujących i venue), czy podpowiedzi (algorytm sugeruje, tata
   sam klika, jak na Stawach)?

---

## 6. Materiały źródłowe (informacyjnie — wszystko istotne jest w tym pliku)

- `nagrania/nagranie-4.m4a` (~49 min) — rozmowa z tatą, demo + tłumaczenie reguł.
  Pliki audio i transkrypty są w `.gitignore`, więc niedostępne w repo Windows.
- `nagrania/nagranie-4.txt` — pełna transkrypcja, kluczowe fragmenty: linie ~166–290
  (Lasomin + warianty wyrównywania) i ~644–648 (UI ostrzeżenia o nierównych sektorach).
- `IMG_1150.jpg` — schemat narysowany ręcznie przez tatę (w katalogu projektu;
  nie jest w `.gitignore`, więc warto zacommitować dla wygody — można też pominąć,
  bo całość jest odwzorowana w §2.1).

---

## 7. Status

- **Spec napisana:** 2026-05-03 (Linux Claude Code, na bazie demo z 2026-05-03).
- **Implementacja:** TODO (Windows Claude Code).
- **Weryfikacja na żywo:** zaplanowana na pierwsze zawody na Lasominie
  (data nieznana — tata ma najpierw eliminacje na Stawach).
- **Sugestia commit-owa:** zacommituj ten plik (i opcjonalnie `IMG_1150.jpg`)
  do repo, żeby zsync'ować z Windowsową instancją. Nie wymaga aktualizacji
  `wymagania.md`, ale warto skreślić wzmiankę "Konfiguracja sektorów Lasomina
  (brak danych...)" w `CLAUDE.md` po implementacji.
