#!/usr/bin/env python3
"""
SKYWATCH — Autonomiczny Bot Raportów Dronowych
Uruchamiany automatycznie w każdy wtorek przez GitHub Actions.

Stack (Zero-Cost):
  - AI:    Groq API / Llama 3.3 70B   (darmowy tier, brak limitu regionalnego)
  - Email: Resend.com                  (darmowy tier: 3000 maili/miesiąc)
  - Infra: GitHub Actions              (darmowy tier: 2000 min/miesiąc)
  - Fonts: DejaVuSans.ttf bundlowany w repo (licencja Apache 2.0)

Przepływ:
  1. Pobierz artykuły z 9 kanałów RSS (ostatnie 7 dni)
  2. Wyślij do Groq (Llama 3.3 70B) → uzyskaj zredagowany raport po polsku
  3. Zapisz Markdown do raporty/ (archiwum w repo)
  4. Wygeneruj PDF z polskimi znakami (fpdf2 + DejaVuSans.ttf)
  5. Wyślij PDF przez Resend.com API
"""

import base64
import html
import logging
import os
import re
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import feedparser
import resend
from groq import Groq
from dateutil import parser as date_parser
from fpdf import FPDF

# ─── LOGGING ──────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("skywatch")

# ─── ŚCIEŻKI ─────────────────────────────────────────────────────────────────

SCRIPT_DIR  = Path(__file__).parent
FONTS_DIR   = SCRIPT_DIR / "fonts"
FONT_REG    = FONTS_DIR / "DejaVuSans.ttf"
FONT_BOLD   = FONTS_DIR / "DejaVuSans-Bold.ttf"
REPORTS_DIR = SCRIPT_DIR / "raporty"

# ─── ŹRÓDŁA RSS ──────────────────────────────────────────────────────────────

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

# ─── PROMPT SYSTEMOWY ─────────────────────────────────────────────────────────

SYSTEM_PROMPT = """
Jesteś redaktorem newslettera branżowego „SKYWATCH — Innowacje i Trendy Dronowe".
Otrzymujesz listę artykułów z ostatnich 7 dni (tytuł, opis, URL, data, źródło).

TWOJE ZADANIE:
Na podstawie dostarczonych artykułów stwórz raport tygodniowy zawierający WYŁĄCZNIE
newsy pasujące do jednego z czterech obszarów tematycznych. Jeśli artykuł nie pasuje
do żadnego z nich — BEZWZGLĘDNIE go pomiń.

═══════════════════════════════════════════
DOZWOLONE OBSZARY TEMATYCZNE
═══════════════════════════════════════════

## 1. Zmiany Prawne i Operacyjne w Polsce i UE
ULC, PAŻP/PANSA, EASA, CAA UK, FAA USA; regulacje BSP; scenariusze NSTS/STS;
strefy CTR; DroneTower; rejestracja dronów; ubezpieczenia OC; strefy przygraniczne.

## 2. Drony w Energetyce i Infrastrukturze Krytycznej
Inspekcje sieci elektroenergetycznych (PSE, PGE); farmy wiatrowe; fotowoltaika;
ochrona elektrowni i kopalń; systemy antydronowe (C-UAS) przy obiektach strategicznych.

## 3. Zastosowania Samorządowe i Ratownictwo
Drony antysmogowe (inspekcja kominów); monitoring termowizyjny sieci ciepłowniczych;
drony w TOPR/GOPR/PSP/straży miejskiej; stacje dokujące DJI Dock; dofinansowania OSP/PSP.

## 4. Rynek Globalny i Cyberbezpieczeństwo
Zakazy DJI (USA NDAA, FCC Covered List); EU Trusted Drone Label; cyberbezpieczeństwo;
Remote ID; fuzje/przejęcia; nowe przepisy UK, Niemcy, Szwecja.

═══════════════════════════════════════════
FORMAT KAŻDEGO NEWSA (stosuj dokładnie):
═══════════════════════════════════════════

**[Tytuł — po polsku, maks. 10 słów]**
[2-3 zdania: co się stało i dlaczego to ważne. Prosty, ludzki język, zero żargonu.]
[Źródło: Nazwa Portalu](URL_Z_DANYCH_WEJŚCIOWYCH)

═══════════════════════════════════════════
ZASADY BEZWZGLĘDNE:
═══════════════════════════════════════════

1. ZAKAZ generowania URL-ów. Używaj WYŁĄCZNIE adresów z danych wejściowych.
2. Artykuł bez URL = pominięty.
3. Ten sam news z 2 źródeł = wybierz 1 (lepsze).
4. Sekcja bez newsów = pomiń ją.
5. Pisz po polsku; nazwy własne (DJI, PAŻP, PSE) zachowaj.
6. Newsy rozdzielaj pustą linią.
7. Jeśli łącznie mniej niż 3 newsy — napisz TYLKO:
   "W tym tygodniu brak zweryfikowanych newsów spełniających kryteria tematyczne."

STRUKTURA RAPORTU:

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

# ─── ZBIERANIE ARTYKUŁÓW RSS ─────────────────────────────────────────────────


def _clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def fetch_articles(days_back: int = 7) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    articles: list[dict] = []

    for src in RSS_SOURCES:
        try:
            log.info("  RSS: %s", src["name"])
            feed = feedparser.parse(src["url"])

            if feed.bozo and not feed.entries:
                log.warning("  ✗ Nieprawidłowy feed: %s", src["name"])
                continue

            count = 0
            for entry in feed.entries:
                pub: Optional[datetime] = None
                for attr in ("published", "updated", "created"):
                    raw = getattr(entry, attr, None)
                    if raw:
                        try:
                            pub = date_parser.parse(raw)
                            if pub.tzinfo is None:
                                pub = pub.replace(tzinfo=timezone.utc)
                            break
                        except Exception:
                            continue
                if pub is None:
                    pub = datetime.now(timezone.utc)
                if pub < cutoff:
                    continue

                url = getattr(entry, "link", "").strip()
                if not url.startswith("http"):
                    continue

                articles.append({
                    "source": src["name"],
                    "date":   pub.strftime("%Y-%m-%d"),
                    "title":  _clean(getattr(entry, "title", "")),
                    "url":    url,
                    "desc":   _clean(getattr(entry, "summary", ""))[:600],
                })
                count += 1

            log.info("  ✓ %d artykułów z %s", count, src["name"])
        except Exception as exc:
            log.warning("  ✗ Błąd %s: %s", src["name"], exc)

    log.info("Łącznie: %d artykułów", len(articles))
    return articles


def _build_message(articles: list[dict], report_date: str) -> str:
    if not articles:
        return f"Data raportu: {report_date}\n\nBrak artykułów w tym tygodniu."
    lines = [f"Data raportu: {report_date}\n", f"Zebrano {len(articles)} artykułów:\n"]
    for i, a in enumerate(articles, 1):
        lines.append(
            f"=== ARTYKUŁ {i} ===\n"
            f"Źródło: {a['source']}\nData: {a['date']}\n"
            f"Tytuł: {a['title']}\nURL: {a['url']}\nOpis: {a['desc']}\n"
        )
    return "\n".join(lines)


# ─── GROQ API ────────────────────────────────────────────────────────────────


def call_groq(user_message: str, api_key: str) -> str:
    log.info("Wysyłanie do Groq API (Llama 3.3 70B)...")
    client = Groq(api_key=api_key)
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_message},
        ],
        max_tokens=4096,
        temperature=0.2,
    )
    text = completion.choices[0].message.content
    log.info("Odpowiedź Groq: %d znaków", len(text))
    return text


# ─── GENEROWANIE PDF ──────────────────────────────────────────────────────────


class _PDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_margins(20, 30, 20)
        self.set_auto_page_break(True, margin=18)
        self.add_font("DV",  "",  str(FONT_REG))
        self.add_font("DV",  "B", str(FONT_BOLD))

    def header(self) -> None:
        self.set_fill_color(15, 20, 40)
        self.rect(0, 0, 210, 23, "F")
        self.set_text_color(255, 255, 255)
        self.set_font("DV", "B", 13)
        self.set_y(5)
        self.cell(0, 7, "SKYWATCH — Innowacje i Trendy Dronowe", align="C", ln=True)
        self.set_font("DV", "", 8)
        self.set_text_color(170, 185, 225)
        self.cell(0, 5, "Tygodniowy Przegląd Branży Dronowej", align="C", ln=True)
        self.set_text_color(0, 0, 0)

    def footer(self) -> None:
        self.set_y(-13)
        self.set_draw_color(200, 205, 220)
        self.line(20, self.get_y(), 190, self.get_y())
        self.set_font("DV", "", 8)
        self.set_text_color(140, 140, 160)
        self.cell(0, 6, f"Strona {self.page_no()}", align="C")
        self.set_text_color(0, 0, 0)


def render_pdf(report_text: str, output_path: str) -> None:
    if not FONT_REG.exists():
        raise RuntimeError(f"Brak pliku czcionki: {FONT_REG}")

    pdf = _PDF()
    pdf.add_page()

    for raw in report_text.splitlines():
        line = raw.rstrip()

        if line.startswith("# "):
            pdf.set_font("DV", "B", 16)
            pdf.set_text_color(10, 15, 50)
            pdf.multi_cell(0, 9, line[2:])
            pdf.ln(1)

        elif line.startswith("## "):
            pdf.ln(5)
            x, y = pdf.get_x(), pdf.get_y()
            pdf.set_fill_color(60, 90, 200)
            pdf.rect(20, y, 4, 9, "F")
            pdf.set_fill_color(232, 237, 255)
            pdf.rect(24, y, 166, 9, "F")
            pdf.set_font("DV", "B", 12)
            pdf.set_text_color(20, 30, 110)
            pdf.set_x(27)
            pdf.cell(0, 9, line[3:], ln=True)
            pdf.set_text_color(0, 0, 0)
            pdf.ln(3)

        elif line.startswith("**") and line.endswith("**") and len(line) > 4:
            pdf.set_font("DV", "B", 11)
            pdf.set_text_color(5, 5, 5)
            pdf.multi_cell(0, 6, line[2:-2].strip())

        elif re.match(r"^\[.+?\]\(https?://", line):
            m = re.match(r"^\[([^\]]+)\]\((https?://[^)]+)\)", line)
            if m:
                label, url = m.group(1), m.group(2)
                pdf.set_font("DV", "", 9)
                pdf.set_text_color(10, 80, 200)
                pdf.cell(6, 5, "")
                pdf.cell(0, 5, f"↗ {label}", link=url, ln=True)
                pdf.set_text_color(0, 0, 0)
            pdf.ln(5)

        elif line.strip() in ("---", "***"):
            pdf.ln(2)
            pdf.set_draw_color(190, 195, 210)
            pdf.line(20, pdf.get_y(), 190, pdf.get_y())
            pdf.set_draw_color(0, 0, 0)
            pdf.ln(4)

        elif line.startswith("*") and line.endswith("*") and not line.startswith("**"):
            pdf.set_font("DV", "", 8)
            pdf.set_text_color(110, 110, 130)
            pdf.multi_cell(0, 5, line[1:-1])
            pdf.set_text_color(0, 0, 0)

        elif line.strip() == "":
            pdf.ln(2)

        else:
            pdf.set_font("DV", "", 10)
            pdf.set_text_color(35, 35, 35)
            pdf.multi_cell(0, 5.5, line)

    pdf.output(output_path)
    size_kb = Path(output_path).stat().st_size // 1024
    log.info("PDF: %s (%d KB)", output_path, size_kb)


# ─── WYSYŁKA PRZEZ RESEND ─────────────────────────────────────────────────────


def send_via_resend(
    pdf_path: str,
    api_key: str,
    sender: str,
    recipients: list[str],
    report_date: str,
) -> None:
    resend.api_key = api_key

    filename = f"SKYWATCH_Raport_{report_date.replace('.', '-')}.pdf"
    with open(pdf_path, "rb") as fh:
        pdf_bytes = fh.read()

    body = (
        f"Dzień dobry,\n\n"
        f"W załączniku przesyłam tygodniowy raport branżowy SKYWATCH za {report_date}.\n\n"
        "Raport obejmuje:\n"
        "  • Zmiany prawne i operacyjne (ULC, PAŻP, EASA)\n"
        "  • Drony w energetyce i infrastrukturze krytycznej\n"
        "  • Zastosowania samorządowe i ratownictwo\n"
        "  • Rynek globalny i cyberbezpieczeństwo\n\n"
        "Wszystkie źródła i klikalne linki znajdują się w załączonym pliku PDF.\n\n"
        "Z poważaniem,\nBot SKYWATCH\n(wiadomość wygenerowana automatycznie)"
    )

    params: resend.Emails.SendParams = {
        "from": sender,
        "to": recipients,
        "subject": f"SKYWATCH | Raport Dronowy | {report_date}",
        "text": body,
        "attachments": [
            {
                "filename": filename,
                "content": list(pdf_bytes),
            }
        ],
    }

    result = resend.Emails.send(params)
    log.info("Resend: e-mail wysłany, id=%s", result.get("id", "?"))


# ─── MAIN ─────────────────────────────────────────────────────────────────────


def main() -> None:
    groq_key     = os.environ["GROQ_API_KEY"]
    resend_key   = os.environ["RESEND_API_KEY"]
    recipients   = [e.strip() for e in os.environ["RECIPIENT_EMAILS"].split(",") if e.strip()]
    sender       = os.environ.get("SENDER_EMAIL", "SKYWATCH Bot <onboarding@resend.dev>")
    report_date  = datetime.now().strftime("%d.%m.%Y")

    log.info("=" * 55)
    log.info("SKYWATCH Bot — %s", report_date)
    log.info("=" * 55)

    log.info("[1/4] Pobieranie artykułów RSS...")
    articles = fetch_articles()

    log.info("[2/4] Budowanie promptu...")
    user_msg = _build_message(articles, report_date)

    log.info("[3/4] Generowanie raportu (Groq / Llama 3.3 70B)...")
    report_text = call_groq(user_msg, groq_key)

    # Zapis Markdown do archiwum
    REPORTS_DIR.mkdir(exist_ok=True)
    date_slug = datetime.now().strftime("%Y-%m-%d")
    md_path = REPORTS_DIR / f"SKYWATCH_Raport_{date_slug}.md"
    md_path.write_text(report_text, encoding="utf-8")
    log.info("Markdown: %s", md_path)

    log.info("[4/4] Generowanie PDF i wysyłka e-maila...")
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        pdf_path = tmp.name

    try:
        render_pdf(report_text, pdf_path)
        send_via_resend(pdf_path, resend_key, sender, recipients, report_date)
    finally:
        Path(pdf_path).unlink(missing_ok=True)

    log.info("=" * 55)
    log.info("SKYWATCH Bot — zakończono pomyślnie!")
    log.info("=" * 55)


if __name__ == "__main__":
    main()
