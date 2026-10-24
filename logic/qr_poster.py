"""Printable QR posters: one A6 card per spot, and A4 sheets with four cards each (cut along the dashed lines).

Used by the staff Locations page and scripts/make_qr_codes.py. Needs Pillow (comes with Streamlit) and qrcode.
"""
import io
from functools import lru_cache
from pathlib import Path

import qrcode
from PIL import Image, ImageDraw, ImageFont
from qrcode.constants import ERROR_CORRECT_Q

from logic import qr

DPI = 300
CARD = (1240, 1748)        # A6 portrait at 300 dpi
SHEET = (2480, 3508)       # A4 portrait at 300 dpi, 2 x 2 cards
INK, YELLOW, PAPER, MUTED, BAND = "#19191c", "#f3f05c", "#ffffff", "#6d6b75", "#19191c"

_BOLD = ["Manrope-Bold.ttf", "Manrope-ExtraBold.ttf", "DMSans-Bold.ttf", "Inter-Bold.otf", "Poppins-Bold.ttf",
         "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf", "arialbd.ttf", "Arial Bold.ttf", "Arial-BoldMT.ttf"]
_REGULAR = ["DMSans-Regular.ttf", "Manrope-Medium.ttf", "Inter-Regular.otf", "Poppins-Regular.ttf",
            "DejaVuSans.ttf", "LiberationSans-Regular.ttf", "arial.ttf", "Arial.ttf"]
_FONT_DIRS = [Path(__file__).resolve().parent.parent / "data" / "fonts", Path("/usr/share/fonts"),
              Path("/Library/Fonts"), Path("/System/Library/Fonts"), Path("C:/Windows/Fonts"),
              Path.home() / ".fonts", Path.home() / "Library" / "Fonts"]


@lru_cache(maxsize=4)
def _font_path(bold: bool) -> str | None:
    """First installed font from the list (searching the usual Linux, macOS and Windows font folders)."""
    for name in _BOLD if bold else _REGULAR:
        for d in _FONT_DIRS:
            hit = next(d.rglob(name), None) if d.is_dir() else None
            if hit:
                return str(hit)
    return None  # Pillow's built-in font is used instead


@lru_cache(maxsize=64)
def _font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    path = _font_path(bold)
    return ImageFont.truetype(path, size) if path else ImageFont.load_default(size)


def _fit(draw: ImageDraw.ImageDraw, text: str, size: int, width: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    """Largest font up to size that fits text into width."""
    while size > 18 and draw.textlength(text, font=_font(size, bold)) > width:
        size -= 2
    return _font(size, bold)


def _center(draw: ImageDraw.ImageDraw, y: int, text: str, font, fill: str, spacing: float = 0) -> None:
    if spacing:
        w = sum(draw.textlength(ch, font=font) for ch in text) + spacing * (len(text) - 1)
        x = (CARD[0] - w) / 2
        for ch in text:
            draw.text((x, y), ch, font=font, fill=fill)
            x += draw.textlength(ch, font=font) + spacing
        return
    draw.text(((CARD[0] - draw.textlength(text, font=font)) / 2, y), text, font=font, fill=fill)


def _qr_image(url: str, size: int) -> Image.Image:
    """QR with whole-pixel modules (no resampling, so every module is the same size and scans reliably)."""
    code = qrcode.QRCode(error_correction=ERROR_CORRECT_Q, box_size=1, border=2)
    code.add_data(url)
    code.make(fit=True)
    modules = len(code.get_matrix())  # includes the border
    code.box_size = max(1, size // modules)
    img = code.make_image(fill_color=INK, back_color=PAPER).convert("RGB")
    out = Image.new("RGB", (size, size), PAPER)
    out.paste(img, ((size - img.width) // 2, (size - img.height) // 2))
    return out


def _sparkle(draw: ImageDraw.ImageDraw, cx: float, cy: float, r: float) -> None:
    """Four-point star like the app's brand mark."""
    k = r * 0.28
    draw.polygon([(cx, cy - r), (cx + k, cy - k), (cx + r, cy), (cx + k, cy + k), (cx, cy + r), (cx - k, cy + k),
                  (cx - r, cy), (cx - k, cy - k)], fill=INK)


def card(spot: dict, base_url: str | None = None) -> Image.Image:
    """One A6 poster for a spot. Raises ValueError when no app link is configured."""
    url = qr.link(spot["code"], base_url)
    img = Image.new("RGB", CARD, PAPER)
    d = ImageDraw.Draw(img)
    w, _ = CARD

    d.rectangle([0, 0, w, 250], fill=BAND)
    d.rounded_rectangle([80, 65, 200, 185], radius=30, fill=YELLOW)
    _sparkle(d, 140, 125, 40)
    d.text((232, 70), "Campus Saathi", font=_font(62), fill=PAPER)
    d.text((234, 148), "K.R. Mangalam University", font=_font(34, False), fill="#a9a9b2")

    _center(d, 300, "SPOTTED A PROBLEM HERE?", _font(34), MUTED, spacing=5)
    _center(d, 350, "Scan to report it", _fit(d, "Scan to report it", 96, w - 160), INK)

    d.rounded_rectangle([150, 500, w - 150, 1440], radius=48, fill=YELLOW)
    img.paste(_qr_image(url, 820), ((w - 820) // 2, 560))

    floor = f"{spot['floor']} floor" if spot.get("floor") else ""
    line2 = " · ".join(p for p in (floor, spot.get("spot")) if p)
    _center(d, 1475, spot["name"], _fit(d, spot["name"], 76, w - 140), INK)
    if line2:
        _center(d, 1570, line2, _fit(d, line2, 48, w - 140, False), INK)

    note = "The place is filled in for you. Just describe it."
    _center(d, 1650, note, _fit(d, note, 30, w - 160, False), MUTED)
    d.text((60, CARD[1] - 52), spot["code"], font=_font(24, False), fill="#a9a9b2")
    return img


def png_bytes(image: Image.Image) -> bytes:
    """PNG bytes of a poster, tagged with the print DPI."""
    buf = io.BytesIO()
    image.save(buf, format="PNG", dpi=(DPI, DPI))
    return buf.getvalue()


def sheets(spot_list: list[dict], base_url: str | None = None) -> list[Image.Image]:
    """A4 pages, four cards per page, with dashed cut lines."""
    pages = []
    for i in range(0, len(spot_list), 4):
        page = Image.new("RGB", SHEET, PAPER)
        for j, spot in enumerate(spot_list[i:i + 4]):
            page.paste(card(spot, base_url), ((j % 2) * CARD[0], (j // 2) * CARD[1]))
        d = ImageDraw.Draw(page)
        for y in range(0, SHEET[1], 40):
            d.line([(CARD[0], y), (CARD[0], y + 20)], fill="#bbbbbb", width=3)
        for x in range(0, SHEET[0], 40):
            d.line([(x, CARD[1]), (x + 20, CARD[1])], fill="#bbbbbb", width=3)
        pages.append(page)
    return pages


def pdf_bytes(spot_list: list[dict], base_url: str | None = None) -> bytes:
    """All cards as a printable A4 PDF (four per page)."""
    pages = sheets(spot_list, base_url)
    buf = io.BytesIO()
    pages[0].save(buf, format="PDF", save_all=True, append_images=pages[1:], resolution=DPI)
    return buf.getvalue()
