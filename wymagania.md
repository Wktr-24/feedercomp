# Wymagania: Program do obsługi zawodów wędkarskich

## Kontekst

Program do zarządzania zawodami wędkarskimi (spinning) organizowanymi przez klub WKS Feederland. Obecny workflow jest w pełni ręczny — listy w Excelu, ręczne wpisywanie nazwisk do arkuszy sektorowych, ręczne sortowanie wyników. Organizator chce zautomatyzować cały proces, żeby zaoszczędzić czas w dniu zawodów.

**Środowisko pracy:** laptop w terenie, bez internetu, na baterii. Przenośna drukarka USB.

---

## Wymagania funkcjonalne

### A. Zarządzanie listą zawodników (przed zawodami)

- Wprowadzanie listy zawodników (w domu, 1-2 dni wcześniej)
  - Dane: numer na liście, imię i nazwisko, numer telefonu, status opłaty
- Limit uczestników: typowo 50 osób
- Lista rezerwowa: osoby powyżej limitu
- Status opłaty: TAK / na miejscu / nieopłacone
- Odhaczyć obecność w dniu zawodów

### B. Konfiguracja łowiska i sektorów

- Wiele łowisk (profile):
  - **Stawy Siedleckie** — 50 stanowisk, 5 sektorów (A-E)
  - **Lasomin** — 34 stanowiska, 4 sektory
- Mapowanie numerów stanowisk do sektorów (stałe dla łowiska, ale edytowalne):
  - Przykład Stawy Siedleckie:
    - Sektor A: 1-5 i 46-50
    - Sektor B: 6-10 i 41-45
    - Sektor C: 11-15 i 36-40
    - Sektor D: 16-20 i 31-35
    - Sektor E: 21-30
  - Stanowiska NIE są ciągłe — otaczają zbiornik wodny
- Tryb edycji sektorów z wyraźnym "zatwierdź" / "wyjdź z edycji"

### C. Losowanie stanowisk

- Fizyczne losowanie z worka (krążki drewniane) — program tylko rejestruje wynik
- Przy nazwisku zawodnika wpisuje się wylosowany numer stanowiska
- Po wpisaniu numeru → automatyczne przypisanie do odpowiedniego sektora

### D. Rejestrowanie wyników (wag)

- Wpisywanie wagi dla każdego zawodnika po zakończeniu zawodów
- **Waga w gramach** (np. 61060 = 61,060 kg) — potwierdzone z Exceli
- Wyszukiwanie zawodnika po 2-3 pierwszych literach nazwiska (auto-complete)
- Waga zero dla zawodników, którzy nic nie złowili

### E. Obliczanie wyników i klasyfikacji

- **Sortowanie wewnątrz sektora**: malejąco po wadze
- **Punkty sektorowe**: miejsce w sektorze = liczba punktów (1. miejsce = 1 pkt, 2. = 2 pkt, itd.)
- **Klasyfikacja końcowa** — algorytm:
  1. Najpierw wszystkie jedynki sektorowe (5 zawodników) — sortowane wg wagi malejąco
  2. Potem wszystkie dwójki sektorowe — sortowane wg wagi malejąco
  3. Potem trójki, czwórki, itd.
  4. W ramach tych samych punktów sektorowych — ten z większą wagą jest wyżej
- **Zawodnicy z wagą 0**: dzielą ostatnie miejsce w sektorze, pośrednie pozycje pomijane (np. dwóch z wagą 0 → obaj miejsce 10, brak miejsca 9). W klasyfikacji końcowej nie dostają numeru miejsca (wyświetlane jako „-"), listowani na końcu
- **Lista zwycięzców**: konfigurowalny podzbiór (jedynki+dwójki lub jedynki+dwójki+trójki) — w danych z 28.09.2025: nagrodzono 15 osób (jedynki+dwójki+trójki)

### F. Obsługa nieobecności

- Gdy ktoś nie dojedzie — usunięcie stanowisk skrajnych z sektora
- Cel: zachowanie równej liczby zawodników między sektorami
- **Zawsze robione ręcznie** — organizator sam decyduje które stanowiska usunąć
- Program może proponować, ale organizator musi mieć pełną kontrolę

**Szczegóły z transkrypcji (cytaty organizatora):**

Algorytm ręczny:
> "Jeżeli tylko jeden wypadnie, to odrzucamy jedynki. Jeżeli wypadnie na przykład dwóch, to odrzucamy jedynki z tej strony i z tej strony."

Konkretne przykłady stanowisk do odrzucenia (wskazywane na diagramie łowiska):
> "Tu odrzucę jedynkę. I tutaj odrzucę na przykład dwudziestą piątkę. Albo odrzucimy jedynkę i tutaj odrzucimy dwudziestą szóstą."

Zasada ogólna:
> "Raczej skrajne odrzucamy."

Kluczowe — musi być ręcznie:
> "Muszę mieć możliwość manualnego, manualnej zmiany."
> "To zawsze będzie, będzie manualnie robione."

Cel:
> "Nie chcemy zrobić, że tutaj będzie zawodników dziesięciu, a tu ośmiu. To też jest niesprawiedliwe."

### G. Wydruki / eksport

- Drukowanie wyników na przenośnej drukarce USB
- Eksport do PDF (do wrzucenia na Facebooka)
- Format nagłówka (z Exceli): `WKS FEEDERLAND` / `ZAWODY DD.MM.YYYY` / `Łowisko NAZWA`
- Wydruki: klasyfikacja końcowa, lista zwycięzców, arkusze sektorów

### H. Cykl zawodów

- Sezon = ok. 6 zawodów (4× Stawy Siedleckie, 2× Lasomin)
- Finał dwudniowy we wrześniu

---

## Encje danych

### Łowisko
- Nazwa
- Liczba stanowisk
- Liczba sektorów
- Mapowanie: numer stanowiska → sektor

### Zawody
- Data
- Łowisko (referencja)
- Nazwa / edycja
- Maksymalna liczba zawodników

### Zawodnik (w ramach zawodów)
- Numer na liście (kolejność zapisu)
- Imię i nazwisko
- Numer telefonu (opcjonalny)
- Status opłaty
- Obecność (TAK/NIE)
- Numer stanowiska (wylosowany)
- Sektor (automatycznie)
- Waga (w gramach)
- Miejsce w sektorze (obliczone)
- Punkty sektorowe (= miejsce w sektorze)
- Miejsce w klasyfikacji końcowej (obliczone)

---

## Reguły biznesowe

1. Numery stanowisk w sektorach są stałe dla danego łowiska, ale edytowalne
2. Po wpisaniu numeru stanowiska → automatyczne przypisanie do sektora
3. Sortowanie w sektorze: waga malejąco
4. Punkty sektorowe = miejsce w sektorze
5. Klasyfikacja końcowa: sortuj wg punktów sektorowych (rosnąco), potem wg wagi (malejąco) — zweryfikowane na danych z 28.09.2025
6. Zawodnicy z wagą 0: dzielą ostatnie miejsce w sektorze (pozycje pomiędzy są pomijane). W klasyfikacji końcowej wyświetlani z „-" zamiast numeru miejsca
7. Jedynka sektorowa ZAWSZE jest wyżej niż dwójka sektorowa (niezależnie od wagi)
8. Wagi przechowywane w gramach (liczby całkowite)

---

## Preferencje UI/UX

- Praca na laptopie, offline, na baterii
- Kilka ekranów/plansz:
  - Lista zawodników (wpisywanie, losowanie)
  - Sektory (automatycznie wypełniane, potem wagi)
  - Klasyfikacja końcowa (generowana automatycznie)
- Szybkość — kluczowa (organizator chce łowić, nie siedzieć przy laptopie)
- Auto-complete przy wyszukiwaniu po nazwisku
- Przycisk "posortuj" lub sortowanie w locie
- Wybór łowiska na starcie aplikacji

---

## Rozstrzygnięte pytania

1. ~~**Jednostka wagi**~~ → gramy (liczby całkowite, np. 61060)
2. ~~**Ile miejsc nagradzanych**~~ → konfigurowalne per zawody (w danych: 15 = jedynki+dwójki+trójki)
3. ~~**Remisy wagowe (waga 0)**~~ → dzielą ostatnie miejsce, wyświetlani z „-" w klasyfikacji końcowej
4. ~~**Remisy wagowe (waga > 0)**~~ → scenariusz nieosiągalny w praktyce, nie obsługujemy
5. ~~**Aplikacja offline**~~ → tak, desktopowa offline
6. ~~**Platforma**~~ → Windows 10 i Windows 11, maksymalna kompatybilność i prostota
7. ~~**Klasyfikacja roczna**~~ → nie istnieje (brak w danych i transkrypcji)

## Odroczone pytania

1. **Finał dwudniowy**: Jak agregować wyniki z dwóch dni? Nie jest priorytetem — pierwsze zawody będą jednodniowe. Informacje zostaną dostarczone później.

---

## Istniejące pliki referencyjne

Katalog `zawody-Wiktor/` zawiera dane z prawdziwych zawodów (28.09.2025, Stawy Siedleckie, 50 zawodników, 5 sektorów):

| Plik | Opis | Struktura kolumn |
|------|------|------------------|
| `FINAL-..._lista-zawodnikow.xlsx` | Lista startowa | Numer \| Imię i Nazwisko \| Numer telefonu \| Opłacone \| Nr stanowiska |
| `Sektor-A-_...xls` ... `Sektor-E_...` | Arkusze sektorów (po 10 zawodników) | STANOWISKO \| ZAWODNIK \| WAGA \| MIEJSCE |
| `Klasyfikacja-koncowa_...xls` | Klasyfikacja końcowa (50 zawodników) | Nazwisko \| Miejsce \| Sektor \| Punkty sektorowe \| Waga |
| `Lista-zwyciezcow_...xls` | Lista zwycięzców (15 nagrodzonych) | Imię Nazwisko \| Miejsce \| Waga |

> **Uwaga:** Znaleziona rozbieżność w danych — Czaplicki ma wagę 14320 w arkuszu Sektora A, ale 14050 w klasyfikacji końcowej. Prawdopodobnie błąd ręcznego przepisywania — potwierdza potrzebę automatyzacji.
