#!/usr/bin/env python3
"""
SKYWATCH — Autonomiczny Bot Raportów Dronowych
Uruchamiany automatycznie w każdy wtorek przez GitHub Actions.

Przepływ:
  1. Pobierz artykuły z kanałów RSS (ostatnie 7 dni)
  2. Wyślij do Claude API → uzyskaj zredagowany raport
  3. Zapisz raport w formacie Markdown do katalogu raporty/
  4. Wygeneruj PDF z obsługą polskich znaków (czcionka DejaVu)
  5. Wyślij PDF jako załącznik przez SMTP (Gmail)
"""

import html
import logging
import os
import re
import smtplib
import tempfile
from datetime import datetime, timedelta, timezone
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

import anthropic
import feedparser
from dateutil import parser as date_parser
from fpdf import FPDF

# ─── LOGGING ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("skywatch")

# ─── KONFIGURACJA ŹRÓDEŁ RSS ─────────────────────────────────────────────────
# Dodaj/usuń źródła według potrzeb. Każde musi mieć działający kanał RSS/Atom.

RSS_SOURCES = [
    {"name": "Świat Dronów",       "url": "https://www.swiatdronow.pl/feed/"},
    {"name": "dlapilota.pl",        "url": "https://dlapilota.pl/feed/"},
    {"name": "DroneXL",             "url": "https://dronexl.co/feed/"},
    {"name": "DroneDJ",             "url": "https://dronedj.com/feed/"},
    {"name": "Dronewatch Europe",   "url": "https://www.dronewatch.eu/feed/"},
    {"name": "Gramwzielone.pl",     "url": "https://www.gramwzielone.pl/rss/"},
    {"name": "WNP Energia",         "url": "https://www.wnp.pl/rss/energia.xml"},
    {"name": "nowa-energia.com.pl", "url": "https://nowa-energia.com.pl/feed/"},
    {"name": "infosecurity24.pl",   "url": "https://infosecurity24.pl/feed/"},
]

# Ścieżki do czcionek Unicode (instalowane przez apt w GitHub Actions)
_FONT_REGULAR = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
]
_FONT_BOLD = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
]

# ─── PROMPT SYSTEMOWY DLA CLAUDE ─────────────────────────────────────────────

SYSTEM_PROMPT = """
Jesteś redaktorem newslettera branżowego „SKYWATCH — Innowacje i Trendy Dronowe".
Otrzymujesz listę artykułów z ostatnich 7 dni (tytuł, opis, URL, data, źródło).

TWOJE ZADANIE:
Na podstawie dostarczonych artykułów stwórz raport tygodniowy zawierający WYŁĄCZNIE newsy
pasujące do jednego z czterech obszarów tematycznych podanych niżej.
Jeśli artykuł nie pasuje do żadnego obszaru — BEZWZGLĘDNIE go pomiń.

═══════════════════════════════════════════════════════════
DOZWOLONE OBSZARY TEMATYCZNE
═══════════════════════════════════════════════════════════

## 1. Zmiany Prawne i Operacyjne w Polsce i UE
Dotyczy: ULC, PAŻP/PANSA, EASA, CAA UK, FAA USA; regulacje lotnicze BSP; scenariusze
NSTS/STS; strefy CTR; aplikacja DroneTower; drony.gov.pl; rejestracja dronów;
ubezpieczenia OC BSP; strefy zakazu lotów i strefy przygraniczne (RSZ, wojsko).

## 2. Drony w Energetyce i Infrastrukturze Krytycznej
Dotyczy: inspekcje sieci elektroenergetycznych (PSE, PGE Dystrybucja); farmy wiatrowe
morskie i lądowe; fotowoltaika; ochrona elektrowni i kopalń przed dronami;
systemy antydronowe (C-UAS) przy obiektach strategicznych; drony do montażu czujników
na liniach wysokiego napięcia.

## 3. Zastosowania Samorządowe i Ratownictwo
Dotyczy: drony antysmogowe (inspekcja kominów, badanie dymu); monitoring termowizyjny
sieci ciepłowniczych; drony w TOPR/GOPR/PSP/straży miejskiej; stacje dokujące
(DJI Dock, autonomiczne systemy); dofinansowania dla OSP/PSP na drony.

## 4. Rynek Globalny i Cyberbezpieczeństwo
Dotyczy: zakazy i ograniczenia DJI (USA NDAA, FCC Covered List); etykieta
EU Trusted Drone Label; cyberbezpieczeństwo dronów; Remote ID; kluczowe
fuzje/przejęcia firm dronowych; nowe przepisy w UK, Niemczech, Szwecji.

═══════════════════════════════════════════════════════════
FORMAT KAŻDEGO NEWSA — stosuj go dokładnie:
═══════════════════════════════════════════════════════════

**[Tytuł newsa — po polsku jeśli możliwe, maksymalnie 10 słów]**
[Treść: 2-3 zdania prostym, konkretnym językiem bez korporacyjnego żargonu.
Co się stało? Dlaczego jest to ważne dla branży?]
[Źródło: Nazwa Portalu](URL_Z_DANYCH_WEJŚCIOWYCH)

═══════════════════════════════════════════════════════════
ZASADY BEZWZGLĘDNE — złamanie którejkolwiek dyskwalifikuje raport:
═══════════════════════════════════════════════════════════

1. ZAKAZ GENEROWANIA URL-ów: Używaj WYŁĄCZNIE adresów URL dostarczonych w danych
   wejściowych. Nie modyfikuj, nie skracaj, nie twórz własnych linków.
2. Artykuł bez URL w danych wejściowych = artykuł POMINIĘTY.
3. Ten sam news z dwóch źródeł = wybierz JEDNO, lepsze źródło.
4. Jeśli z jakiegoś obszaru nie ma newsów — pomiń tę sekcję (nie pisz "brak newsów").
5. Pisz po polsku. Nazwy własne (DJI, PAŻP, PSE, TOPR, DroneTower) — zachowaj oryginał.
6. Każdy news oddziel pustą linią od następnego.
7. Jeśli po filtracji masz MNIEJ NIŻ 3 newsy łącznie, napisz tylko:
   "W tym tygodniu brak wystarczającej liczby zweryfikowanych newsów spełniających kryteria."

═══════════════════════════════════════════════════════════
STRUKTURA RAPORTU (użyj dokładnie tych nagłówków):
═══════════════════════════════════════════════════════════

# SKYWATCH — Raport Tygodniowy
## [data z danych wejściowych]

## 1. Zmiany Prawne i Operacyjne
[newsy]

## 2. Drony w Energetyce i Infrastrukturze Krytycznej
[newsy]

## 3. Zastosowania Samorządowe i Ratownictwo
[newsy]

## 4. Rynek Globalny i Cyberbezpieczeństwo
[newsy]

---
*Raport wygenerowany automatycznie przez bota SKYWATCH na podstawie zweryfikowanych źródeł RSS.*
"""

# ─── ZBIERANIE ARTYKUŁÓW ─────────────────────────────────────────────────────


def _strip_html(text: str) -> str:
    """Usuwa tagi HTML i dekoduje encje HTML."""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def fetch_articles(sources: list[dict], days_back: int = 7) -> list[dict]:
    """Pobiera artykuły z kanałów RSS z ostatnich `days_back` dni."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    articles: list[dict] = []

    for source in sources:
        try:
            log.info("  RSS: %s", source["name"])
            feed = feedparser.parse(source["url"])

            if feed.bozo and not feed.entries:
                log.warning("  ✗ Nieprawidłowy feed: %s", source["name"])
                continue

            count = 0
            for entry in feed.entries:
                # Wyciągnij datę publikacji
                pub_date: Optional[datetime] = None
                for attr in ("published", "updated", "created"):
                    raw = getattr(entry, attr, None)
                    if raw:
                        try:
                            pub_date = date_parser.parse(raw)
                            if pub_date.tzinfo is None:
                                pub_date = pub_date.replace(tzinfo=timezone.utc)
                            break
                        except Exception:
                            continue

                # Jeśli data nieznana — użyj daty bieżącej
                if pub_date is None:
                    pub_date = datetime.now(timezone.utc)

                if pub_date < cutoff:
                    continue

                url = getattr(entry, "link", "").strip()
                if not url.startswith("http"):
                    continue  # Pomiń artykuły bez URL

                title = _strip_html(getattr(entry, "title", "Brak tytułu"))
                summary = _strip_html(getattr(entry, "summary", ""))[:700]

                articles.append(
                    {
                        "source": source["name"],
                        "date": pub_date.strftime("%Y-%m-%d"),
                        "title": title,
                        "url": url,
                        "desc": summary,
                    }
                )
                count += 1

            log.info("  ✓ %d artykułów z %s", count, source["name"])

        except Exception as exc:
            log.warning("  ✗ Błąd pobierania %s: %s", source["name"], exc)

    log.info("Łącznie artykułów: %d", len(articles))
    return articles


def _build_user_message(articles: list[dict], report_date: str) -> str:
    """Formatuje artykuły do wysłania do Claude jako wiadomość użytkownika."""
    if not articles:
        return f"Data raportu: {report_date}\n\nBrak artykułów zebranych w tym tygodniu."

    lines = [f"Data raportu: {report_date}\n", f"Zebrano {len(articles)} artykułów:\n"]
    for i, a in enumerate(articles, 1):
        lines.append(
            f"=== ARTYKUŁ {i} ===\n"
            f"Źródło: {a['source']}\n"
            f"Data: {a['date']}\n"
            f"Tytuł: {a['title']}\n"
            f"URL: {a['url']}\n"
            f"Opis: {a['desc']}\n"
        )
    return "\n".join(lines)


# ─── WYWOŁANIE CLAUDE API ─────────────────────────────────────────────────────


def call_claude(user_message: str, api_key: str) -> str:
    """Wysyła artykuły do Claude i zwraca zredagowany raport w formacie Markdown."""
    log.info("Wysyłanie do Claude API...")
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )
    report = response.content[0].text
    log.info("Odpowiedź Claude: %d znaków", len(report))
    return report


# ─── GENEROWANIE PDF ──────────────────────────────────────────────────────────


def _find_font(candidates: list[str]) -> Optional[str]:
    for path in candidates:
        if Path(path).exists():
            return path
    return None


class _SkywatchPDF(FPDF):
    """Klasa FPDF z nagłówkiem i stopką brandu SKYWATCH."""

    def __init__(self, font_regular: str, font_bold: Optional[str]):
        super().__init__()
        self._fr = font_regular
        self._fb = font_bold
        self._style_b = "B" if font_bold else ""
        self.set_margins(20, 30, 20)
        self.set_auto_page_break(True, margin=18)
        self.add_font("DV", "", font_regular)
        if font_bold:
            self.add_font("DV", "B", font_bold)

    def header(self) -> None:
        # Ciemny pasek nagłówkowy
        self.set_fill_color(15, 20, 40)
        self.rect(0, 0, 210, 23, "F")
        self.set_text_color(255, 255, 255)
        self.set_font("DV", self._style_b, 13)
        self.set_y(5)
        self.cell(0, 7, "SKYWATCH — Innowacje i Trendy Dronowe", align="C", ln=True)
        self.set_font("DV", "", 8)
        self.set_text_color(180, 190, 220)
        self.cell(0, 5, "Tygodniowy Przegląd Branży Dronowej", align="C", ln=True)
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def footer(self) -> None:
        self.set_y(-13)
        self.set_draw_color(200, 205, 220)
        self.line(20, self.get_y(), 190, self.get_y())
        self.ln(1)
        self.set_font("DV", "", 8)
        self.set_text_color(140, 140, 160)
        self.cell(0, 5, f"Strona {self.page_no()} | SKYWATCH Bot | skywatch.auto", align="C")
        self.set_text_color(0, 0, 0)


def render_pdf(report_text: str, output_path: str) -> None:
    """Konwertuje raport Markdown (z Claude) na plik PDF z obsługą polskich znaków."""
    font_regular = _find_font(_FONT_REGULAR)
    font_bold = _find_font(_FONT_BOLD)

    if not font_regular:
        raise RuntimeError(
            "Brak czcionki Unicode (DejaVuSans.ttf). "
            "Zainstaluj pakiet: sudo apt-get install fonts-dejavu-core"
        )

    pdf = _SkywatchPDF(font_regular, font_bold)
    pdf.add_page()

    sb = "B" if font_bold else ""  # styl bold (jeśli dostępny)

    for raw in report_text.splitlines():
        line = raw.rstrip()

        # ── Nagłówek H1: # Tekst ──────────────────────────────────────────
        if line.startswith("# "):
            pdf.set_font("DV", sb, 16)
            pdf.set_text_color(10, 15, 50)
            pdf.multi_cell(0, 9, line[2:])
            pdf.ln(1)

        # ── Nagłówek H2: ## Tekst ─────────────────────────────────────────
        elif line.startswith("## "):
            pdf.ln(5)
            pdf.set_fill_color(232, 237, 255)
            pdf.set_draw_color(60, 90, 200)
            pdf.set_font("DV", sb, 12)
            pdf.set_text_color(20, 30, 110)
            # Lewy kolorowy border via prostokąt
            x, y = pdf.get_x(), pdf.get_y()
            pdf.rect(20, y, 4, 9, "F")
            pdf.set_x(26)
            pdf.cell(0, 9, line[3:], fill=False, ln=True)
            pdf.set_text_color(0, 0, 0)
            pdf.set_draw_color(0, 0, 0)
            pdf.ln(3)

        # ── Pogrubiony tytuł newsa: **Tekst** ─────────────────────────────
        elif line.startswith("**") and line.endswith("**") and len(line) > 4:
            pdf.set_font("DV", sb, 11)
            pdf.set_text_color(5, 5, 5)
            pdf.multi_cell(0, 6, line[2:-2].strip())

        # ── Link źródłowy: [Tekst](URL) ───────────────────────────────────
        elif re.match(r"^\[.+?\]\(https?://", line):
            m = re.match(r"^\[([^\]]+)\]\((https?://[^)]+)\)", line)
            if m:
                label, url = m.group(1), m.group(2)
                pdf.set_font("DV", "", 9)
                pdf.set_text_color(10, 80, 200)
                pdf.cell(6, 5, "")         # małe wcięcie
                pdf.cell(0, 5, f"↗ {label}", link=url, ln=True)
                pdf.set_text_color(0, 0, 0)
            pdf.ln(5)

        # ── Linia pozioma: --- ────────────────────────────────────────────
        elif line.strip() in ("---", "***", "___"):
            pdf.ln(2)
            pdf.set_draw_color(190, 195, 210)
            pdf.line(20, pdf.get_y(), 190, pdf.get_y())
            pdf.set_draw_color(0, 0, 0)
            pdf.ln(4)

        # ── Kursywa / stopka: *Tekst* ─────────────────────────────────────
        elif (
            line.startswith("*")
            and line.endswith("*")
            and not line.startswith("**")
            and len(line) > 2
        ):
            pdf.set_font("DV", "", 8)
            pdf.set_text_color(110, 110, 130)
            pdf.multi_cell(0, 5, line[1:-1])
            pdf.set_text_color(0, 0, 0)

        # ── Pusta linia ───────────────────────────────────────────────────
        elif line.strip() == "":
            pdf.ln(2)

        # ── Zwykły akapit ─────────────────────────────────────────────────
        else:
            pdf.set_font("DV", "", 10)
            pdf.set_text_color(35, 35, 35)
            pdf.multi_cell(0, 5.5, line)

    pdf.output(output_path)
    size_kb = Path(output_path).stat().st_size // 1024
    log.info("PDF zapisany: %s (%d KB)", output_path, size_kb)


# ─── WYSYŁKA E-MAIL ───────────────────────────────────────────────────────────


def send_email(
    pdf_path: str,
    sender: str,
    password: str,
    recipients: list[str],
    report_date: str,
) -> None:
    """Wysyła PDF jako załącznik przez Gmail SMTP (SSL port 465)."""
    msg = MIMEMultipart()
    msg["From"] = f"SKYWATCH Bot <{sender}>"
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = f"SKYWATCH | Raport Dronowy | {report_date}"

    # Minimalistyczna treść maila (antyspam: brak zewnętrznych linków)
    body = (
        "Dzień dobry,\n\n"
        f"W załączniku przesyłam tygodniowy raport branżowy SKYWATCH za {report_date}.\n\n"
        "Raport obejmuje:\n"
        "  • Zmiany prawne i operacyjne (ULC, PAŻP, EASA)\n"
        "  • Drony w energetyce i infrastrukturze krytycznej\n"
        "  • Zastosowania samorządowe i ratownictwo\n"
        "  • Rynek globalny i cyberbezpieczeństwo\n\n"
        "Wszystkie źródła i klikalne linki dostępne są w pliku PDF.\n\n"
        "Z poważaniem,\n"
        "Bot SKYWATCH\n"
        "(wiadomość wygenerowana automatycznie)"
    )
    msg.attach(MIMEText(body, "plain", "utf-8"))

    # Dołącz PDF
    filename = f"SKYWATCH_Raport_{report_date.replace('.', '-')}.pdf"
    with open(pdf_path, "rb") as fh:
        part = MIMEBase("application", "pdf")
        part.set_payload(fh.read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
    msg.attach(part)

    log.info("Wysyłanie e-maila do: %s", recipients)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        server.sendmail(sender, recipients, msg.as_bytes())
    log.info("E-mail wysłany pomyślnie.")


# ─── MAIN ─────────────────────────────────────────────────────────────────────


def main() -> None:
    # Odczytaj konfigurację ze zmiennych środowiskowych (GitHub Secrets)
    api_key = os.environ["CLAUDE_API_KEY"]
    sender = os.environ["SENDER_EMAIL"]
    password = os.environ["EMAIL_PASSWORD"]
    recipients = [e.strip() for e in os.environ["RECIPIENT_EMAILS"].split(",") if e.strip()]

    report_date = datetime.now().strftime("%d.%m.%Y")

    log.info("=" * 55)
    log.info("SKYWATCH Bot — start | %s", report_date)
    log.info("=" * 55)

    # 1. Pobierz artykuły z RSS
    log.info("[1/4] Pobieranie artykułów RSS...")
    articles = fetch_articles(RSS_SOURCES)

    # 2. Przygotuj wiadomość dla Claude
    log.info("[2/4] Przygotowanie danych dla Claude...")
    user_message = _build_user_message(articles, report_date)

    # 3. Wygeneruj raport przez Claude API
    log.info("[3/4] Generowanie raportu (Claude API)...")
    report_text = call_claude(user_message, api_key)

    # Zapisz Markdown do archiwum w repo
    reports_dir = Path("raporty")
    reports_dir.mkdir(exist_ok=True)
    date_slug = datetime.now().strftime("%Y-%m-%d")
    md_path = reports_dir / f"SKYWATCH_Raport_{date_slug}.md"
    md_path.write_text(report_text, encoding="utf-8")
    log.info("Markdown zapisany: %s", md_path)

    # 4. Wygeneruj PDF i wyślij e-mail
    log.info("[4/4] Generowanie PDF i wysyłka e-maila...")
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        pdf_path = tmp.name

    try:
        render_pdf(report_text, pdf_path)
        send_email(pdf_path, sender, password, recipients, report_date)
    finally:
        Path(pdf_path).unlink(missing_ok=True)

    log.info("=" * 55)
    log.info("SKYWATCH Bot — zakończono pomyślnie!")
    log.info("=" * 55)


if __name__ == "__main__":
    main()
