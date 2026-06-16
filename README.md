# SKYWATCH — Innowacje i Trendy Dronowe

Autonomiczny bot generujący tygodniowy raport PDF z branży dronowej
i wysyłający go e-mailem **w każdy wtorek rano** — w 100% automatycznie.

## Stack (Zero-Cost)

| Warstwa | Technologia | Koszt |
|---|---|---|
| Harmonogram | GitHub Actions (cron) | Darmowy |
| AI / analiza | Google Gemini Flash | Darmowy (1M tokenów/mies.) |
| Wysyłka e-mail | Resend.com API | Darmowy (3000 maili/mies.) |
| PDF + polskie znaki | fpdf2 + DejaVuSans (bundlowany) | Darmowy |

---

## Konfiguracja — jednorazowo, ~15 minut

### KROK 1 — Klucz Google Gemini API (darmowy)

1. Wejdź na **https://aistudio.google.com/app/apikey**
2. Zaloguj się kontem Google
3. Kliknij **Create API key**
4. Skopiuj klucz (zaczyna się od `AIza...`)

> Darmowy tier: 1 milion tokenów / miesiąc. Raport tygodniowy zużywa ok. 5000 tokenów.

---

### KROK 2 — Klucz Resend.com API (darmowy)

Resend to profesjonalna platforma e-mail — nie ląduje w spamie jak Gmail SMTP.

1. Wejdź na **https://resend.com** i utwórz darmowe konto
2. Po zalogowaniu kliknij **API Keys** → **Create API Key**
3. Skopiuj klucz (zaczyna się od `re_...`)

> Darmowy tier: 3000 maili / miesiąc, 100 / dzień. Bot wysyła 4-5 maili miesięcznie.

**Ważne — adres nadawcy:**
Na darmowym koncie Resend możesz wysyłać z adresu `onboarding@resend.dev`
(działa od razu, bez konfiguracji). Jeśli chcesz własny adres (np. `bot@twojafirma.pl`),
musisz zweryfikować domenę w panelu Resend — jest to darmowe, ale wymaga dostępu do DNS.

---

### KROK 3 — GitHub Secrets

W repozytorium: **Settings → Secrets and variables → Actions → New repository secret**

| Nazwa sekretu | Wartość | Wymagany? |
|---|---|---|
| `GEMINI_API_KEY` | Klucz z Kroku 1 (`AIza...`) | **TAK** |
| `RESEND_API_KEY` | Klucz z Kroku 2 (`re_...`) | **TAK** |
| `RECIPIENT_EMAILS` | Adresy odbiorców (przecinkami) | **TAK** |
| `SENDER_EMAIL` | Np. `SKYWATCH <onboarding@resend.dev>` | Opcjonalny* |

*Jeśli `SENDER_EMAIL` nie jest ustawiony, bot używa `onboarding@resend.dev` automatycznie.

**Przykład `RECIPIENT_EMAILS`:**
```
anna@firma.pl,jan@firma.pl,zosia.hoppel@gmail.com
```

---

### KROK 4 — Aktywuj GitHub Actions

1. Kliknij zakładkę **Actions** w repozytorium
2. Jeśli widzisz ostrzeżenie — kliknij **Enable workflows**
3. Gotowe! Bot uruchomi się **automatycznie w najbliższy wtorek**

---

## Test natychmiastowy

Nie czekaj do wtorku:

1. Zakładka **Actions** → **SKYWATCH — Weekly Drone Report**
2. **Run workflow** → **Run workflow**
3. Obserwuj logi — zajmuje ok. 60-90 sekund
4. Sprawdź skrzynkę mailową

---

## Struktura plików

```
├── report_bot.py                    # Główny skrypt bota
├── requirements.txt                 # Zależności Python
├── fonts/
│   ├── DejaVuSans.ttf               # Czcionka (Apache 2.0) — bundlowana w repo
│   └── DejaVuSans-Bold.ttf
├── .github/
│   └── workflows/
│       └── schedule.yml             # Cron: co wtorek 07:00 UTC
└── raporty/                         # Archiwum (commitowane automatycznie)
    ├── raport-tygodniowy-2026-06-16.md
    └── SKYWATCH_Raport_YYYY-MM-DD.md
```

---

## Dodawanie źródeł RSS

W `report_bot.py`, sekcja `RSS_SOURCES`:

```python
RSS_SOURCES = [
    {"name": "Świat Dronów", "url": "https://www.swiatdronow.pl/feed/"},
    # Dodaj nowe źródła tutaj:
    {"name": "Mój Portal", "url": "https://mojportal.pl/feed/"},
]
```

Większość portali ma RSS pod `/feed/`, `/rss/` lub `/feed.xml`.

---

## Rozwiązywanie problemów

| Problem | Rozwiązanie |
|---|---|
| Mail nie dochodzi (SPAM) | Zweryfikuj własną domenę w Resend → lepsza dostarczalność |
| `PERMISSION_DENIED` (Gemini) | Sprawdź `GEMINI_API_KEY` — musi być aktywny |
| `invalid_api_key` (Resend) | Sprawdź `RESEND_API_KEY` w panelu resend.com |
| `Brak pliku czcionki` | Upewnij się że folder `fonts/` jest w repo |
| Raport pusty | Sprawdź logi Actions — może RSS nie zwróciły wyników |

---

*SKYWATCH Bot — Zero-Cost Automation | GitHub Actions + Gemini Flash + Resend.com + fpdf2*
