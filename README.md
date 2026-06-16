# SKYWATCH — Innowacje i Trendy Dronowe

Autonomiczny bot generujący tygodniowy raport PDF z branży dronowej
i wysyłający go e-mailem w każdy wtorek rano.

---

## Jak to działa?

```
[RSS: swiatdronow.pl, dlapilota.pl, dronedj.com ...]
            ↓  (feedparser — ostatnie 7 dni)
    [Python: report_bot.py]
            ↓  (Anthropic Claude API)
    [Raport zredagowany po polsku]
            ↓  (fpdf2 — PDF z polskimi znakami)
    [PDF jako załącznik e-mail]  →  odbiorca@firma.pl
            ↓
    [Markdown → commit do repo jako archiwum]
```

Całość uruchamia się automatycznie przez **GitHub Actions** (cron) — bezobsługowo, bezpłatnie.

---

## Konfiguracja jednorazowa (~20 minut)

### KROK 1 — Klucz API Anthropic (Claude)

1. Wejdź na **https://console.anthropic.com**
2. Utwórz konto i zaloguj się
3. Kliknij **API Keys** → **Create Key** → nadaj nazwę np. `skywatch-bot`
4. Skopiuj klucz (zaczyna się od `sk-ant-...`) — zapisz go bezpiecznie

> **Koszt:** Nowe konta Anthropic otrzymują darmowe kredyty. Każdy tygodniowy
> raport kosztuje ok. **$0.01–0.05** (zależnie od liczby artykułów).
> Miesięcznie: mniej niż $0.20.

---

### KROK 2 — Hasło do aplikacji Gmail (App Password)

Zwykłe hasło do Gmaila nie działa z SMTP. Musisz wygenerować specjalne
„Hasło do aplikacji":

1. Zaloguj się na konto Gmail, które będzie wysyłać raporty
2. Wejdź na **https://myaccount.google.com/security**
3. Upewnij się, że masz włączoną **Weryfikację dwuetapową** (2FA) — bez niej opcja nie jest dostępna
4. W wyszukiwarce ustawień wpisz **„Hasła do aplikacji"** i kliknij wynik
   - Alternatywna ścieżka: Bezpieczeństwo → Weryfikacja dwuetapowa → (przewiń na dół) → Hasła do aplikacji
5. W polu **Aplikacja** wpisz: `SKYWATCH Bot`
6. Kliknij **Utwórz**
7. Gmail wygeneruje **16-znakowe hasło** (np. `abcd efgh ijkl mnop`) — skopiuj je (spacje nie mają znaczenia)

> To hasło wkleisz jako sekret `EMAIL_PASSWORD` w następnym kroku.

---

### KROK 3 — Skonfiguruj GitHub Secrets

Tajne zmienne są przechowywane bezpiecznie w GitHubie i nigdy nie trafiają do kodu.

1. Wejdź na stronę tego repozytorium na GitHub
2. Kliknij zakładkę **Settings** (Ustawienia)
3. W lewym menu: **Secrets and variables** → **Actions**
4. Kliknij **New repository secret** i dodaj kolejno cztery sekrety:

| Nazwa sekretu      | Wartość                                      | Przykład                         |
|--------------------|----------------------------------------------|----------------------------------|
| `CLAUDE_API_KEY`   | Klucz API Anthropic z Kroku 1               | `sk-ant-api03-...`               |
| `SENDER_EMAIL`     | Adres Gmail wysyłającego                     | `skywatch.bot@gmail.com`         |
| `EMAIL_PASSWORD`   | 16-znakowe hasło z Kroku 2                  | `abcdefghijklmnop`               |
| `RECIPIENT_EMAILS` | Adresy odbiorców (przecinkami)              | `anna@firma.pl,jan@firma.pl`     |

---

### KROK 4 — Aktywuj GitHub Actions

1. W repozytorium kliknij zakładkę **Actions**
2. Jeśli widzisz komunikat *„Workflows aren't being run on this forked repository"*,
   kliknij **I understand my workflows, go ahead and enable them**
3. Gotowe! Bot uruchomi się automatycznie **w najbliższy wtorek o godz. 8:00–9:00 rano** (czas polski)

---

## Jak przetestować ręcznie?

Nie czekaj do wtorku — uruchom bota natychmiast:

1. W repozytorium kliknij zakładkę **Actions**
2. Wybierz workflow **SKYWATCH — Weekly Drone Report**
3. Kliknij **Run workflow** → **Run workflow** (zielony przycisk)
4. Odśwież stronę i obserwuj postęp — zajmuje ok. 1–2 minuty
5. Po zakończeniu sprawdź skrzynkę mailową odbiorcy

---

## Pliki w repozytorium

```
├── report_bot.py                        # Główny skrypt bota
├── requirements.txt                     # Zależności Python
├── .github/
│   └── workflows/
│       └── schedule.yml                 # Harmonogram GitHub Actions (cron)
└── raporty/                             # Archiwum raportów (Markdown)
    ├── raport-tygodniowy-2026-06-16.md  (ręcznie tworzony przykład)
    └── SKYWATCH_Raport_2026-06-23.md    (generowane automatycznie przez bota)
```

---

## Dodawanie/usuwanie źródeł RSS

Otwórz plik `report_bot.py` i znajdź sekcję `RSS_SOURCES`:

```python
RSS_SOURCES = [
    {"name": "Świat Dronów",  "url": "https://www.swiatdronow.pl/feed/"},
    # Dodaj nowe wpisy w tym formacie:
    {"name": "Nazwa Portalu", "url": "https://portal.pl/feed/"},
]
```

Większość portali udostępnia RSS pod adresem `/feed/`, `/rss/` lub `/feed.xml`.

---

## Zmiana harmonogramu

Edytuj plik `.github/workflows/schedule.yml`, linia:

```yaml
- cron: "0 7 * * 2"
```

Format: `minuta godzina(UTC) dzień miesiąc dzień_tygodnia`

| Zapis cron     | Znaczenie                                    |
|----------------|----------------------------------------------|
| `0 7 * * 2`    | Wtorek, 7:00 UTC (8:00 CET / 9:00 CEST)    |
| `0 7 * * 1`    | Poniedziałek, 7:00 UTC                       |
| `0 6 * * 1,4`  | Poniedziałek i czwartek, 6:00 UTC            |

---

## Rozwiązywanie problemów

| Problem                           | Rozwiązanie                                                    |
|-----------------------------------|----------------------------------------------------------------|
| Mail nie dochodzi                 | Sprawdź folder SPAM; upewnij się że Email Password jest poprawne |
| `RuntimeError: Brak czcionki`    | Workflow musi zawierać krok `apt-get install fonts-dejavu-core` |
| `AuthenticationError` (Claude)    | Sprawdź klucz `CLAUDE_API_KEY` — czy konto ma kredyty?       |
| `SMTPAuthenticationError`         | Wygeneruj nowe hasło aplikacji Gmail (stare wygasają)         |
| Raport pusty / brak newsów        | Sprawdź logi Actions — być może RSS nie zwróciły wyników      |

---

*Bot SKYWATCH — Zero-Cost Automation Stack | GitHub Actions + Anthropic Claude + fpdf2*
