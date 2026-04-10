"""
Lantico MVP — PDF generation view.
Endpoint: GET /api/result/<session_id>/pdf/

Uses reportlab (no external fonts needed — works with built-in Helvetica
plus manual Cyrillic fallback via DejaVuSans which ships with reportlab).
"""

import io
import math

from django.http import HttpResponse
from rest_framework.decorators import api_view
from rest_framework import status as http_status
from rest_framework.response import Response

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_LEFT

from .models import TestSession, Dimension, SITUATIONAL_NOTE

import os, glob

def _find_font(name):
    for d in ["/usr/share/fonts", "/usr/local/share/fonts"]:
        hits = glob.glob(f"{d}/**/{name}", recursive=True)
        if hits:
            return hits[0]
    return name

pdfmetrics.registerFont(TTFont("DejaVu", _find_font("DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DejaVu-Bold", _find_font("DejaVuSans-Bold.ttf")))
FONT = "DejaVu"
FONT_BOLD = "DejaVu-Bold"

# ── Colors ─────────────────────────────────────────────────
BG       = HexColor("#FFFFFF")
TEXT     = HexColor("#1A1A2E")
MUTED    = HexColor("#6B7280")
ACCENT   = HexColor("#7C3AED")
KIND_CLR = HexColor("#EC4899")
WILL_CLR = HexColor("#3B82F6")
IQ_CLR   = HexColor("#10B981")
HON_CLR  = HexColor("#F59E0B")
WARN_BG  = HexColor("#FEF3C7")
CARD_BG  = HexColor("#F9FAFB")
CARD_BRD = HexColor("#E5E7EB")

DIM_LABELS = {
    "KIND": ("Доброта", KIND_CLR),
    "WILL": ("Воля", WILL_CLR),
    "IQ":   ("Ум", IQ_CLR),
    "HON":  ("Честность", HON_CLR),
}

DIM_ORDER = ["KIND", "WILL", "IQ", "HON"]

W, H = A4  # 595 x 842 pts


def _score(dim: str, results: dict) -> float:
    r = results.get(dim, {})
    return r.get("average_score", 0) if dim == "IQ" else r.get("median", 0)


# ── Radar drawing ──────────────────────────────────────────

def _draw_radar(c: canvas.Canvas, cx: float, cy: float, radius: float, results: dict):
    """Draw a 4-axis radar polygon + grid."""
    angles = [90, 0, 270, 180]  # top, right, bottom, left
    scores = [_score(d, results) for d in DIM_ORDER]

    # concentric pentagons (grid)
    for level in (2, 4, 6, 8, 10):
        r = radius * level / 10
        c.setStrokeColor(CARD_BRD)
        c.setLineWidth(0.4)
        pts = []
        for ang in angles:
            rad = math.radians(ang)
            pts.append((cx + r * math.cos(rad), cy + r * math.sin(rad)))
        p = c.beginPath()
        p.moveTo(*pts[0])
        for pt in pts[1:]:
            p.lineTo(*pt)
        p.close()
        c.drawPath(p, stroke=1, fill=0)

    # axis lines
    for ang in angles:
        rad = math.radians(ang)
        c.setStrokeColor(CARD_BRD)
        c.setLineWidth(0.3)
        c.line(cx, cy, cx + radius * math.cos(rad), cy + radius * math.sin(rad))

    # data polygon
    pts = []
    for i, ang in enumerate(angles):
        rad = math.radians(ang)
        r = radius * scores[i] / 10
        pts.append((cx + r * math.cos(rad), cy + r * math.sin(rad)))

    c.setFillColor(HexColor("#7C3AED20"))
    c.setStrokeColor(ACCENT)
    c.setLineWidth(1.8)
    p = c.beginPath()
    p.moveTo(*pts[0])
    for pt in pts[1:]:
        p.lineTo(*pt)
    p.close()
    c.drawPath(p, stroke=1, fill=1)

    # dots + labels
    for i, (dim, ang) in enumerate(zip(DIM_ORDER, angles)):
        rad_a = math.radians(ang)
        r = radius * scores[i] / 10
        dx, dy = cx + r * math.cos(rad_a), cy + r * math.sin(rad_a)
        label_name, color = DIM_LABELS[dim]

        # dot
        c.setFillColor(color)
        c.circle(dx, dy, 3.5, stroke=0, fill=1)

        # label outside
        lr = radius + 16
        lx, ly = cx + lr * math.cos(rad_a), cy + lr * math.sin(rad_a)
        c.setFont(FONT_BOLD, 8)
        c.setFillColor(color)
        label_with_score = f"{label_name}: {scores[i]}"
        tw = pdfmetrics.stringWidth(label_with_score, FONT_BOLD, 8)
        # center label
        c.drawString(lx - tw / 2, ly - 3, label_with_score)


# ── Text wrapping ──────────────────────────────────────────

def _wrap(text: str, font: str, size: float, max_w: float) -> list[str]:
    words = text.split()
    lines, current = [], ""
    for w in words:
        test = f"{current} {w}".strip()
        if pdfmetrics.stringWidth(test, font, size) <= max_w:
            current = test
        else:
            if current:
                lines.append(current)
            current = w
    if current:
        lines.append(current)
    return lines


# ── Main PDF builder ───────────────────────────────────────

def build_pdf(session: TestSession) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)

    computed = session.compute_results()
    results = computed["results"]
    vector = computed["vector_signature"]

    y = H - 50 * mm

    # Title
    c.setFont(FONT_BOLD, 20)
    c.setFillColor(TEXT)
    c.drawCentredString(W / 2, y, "Лантико — Результаты")
    y -= 10 * mm

    # Vector signature
    sig = "  ".join(f"{d}:{vector.get(d, '?')}" for d in DIM_ORDER)
    c.setFont(FONT, 9)
    c.setFillColor(MUTED)
    c.drawCentredString(W / 2, y, sig)
    y -= 18 * mm

    # Radar
    radar_cx = W / 2
    radar_cy = y - 55 * mm
    _draw_radar(c, radar_cx, radar_cy, 50 * mm, results)
    y = radar_cy - 70 * mm

    # Interpretation cards
    margin_x = 30 * mm
    card_w = W - 2 * margin_x
    line_h = 13

    for dim in DIM_ORDER:
        r = results.get(dim)
        if not r:
            continue
        label_name, color = DIM_LABELS[dim]
        score = _score(dim, results)
        interp = r.get("interpretation", "")
        is_sit = r.get("is_situational", False)

        # estimate card height
        interp_lines = _wrap(interp, FONT, 9, card_w - 20 * mm)
        card_h = 12 * mm + len(interp_lines) * line_h
        if is_sit:
            sit_lines = _wrap(SITUATIONAL_NOTE, FONT, 8, card_w - 22 * mm)
            card_h += 8 * mm + len(sit_lines) * 11

        # page break if needed
        if y - card_h < 25 * mm:
            c.showPage()
            y = H - 30 * mm

        # card background
        c.setFillColor(CARD_BG)
        c.setStrokeColor(CARD_BRD)
        c.setLineWidth(0.5)
        c.roundRect(margin_x, y - card_h, card_w, card_h, 6, stroke=1, fill=1)

        # header line
        cy = y - 8 * mm
        c.setFont(FONT_BOLD, 11)
        c.setFillColor(color)
        c.drawString(margin_x + 5 * mm, cy, f"{label_name}")
        c.setFont(FONT, 11)
        c.setFillColor(TEXT)
        score_str = str(score)
        c.drawRightString(margin_x + card_w - 5 * mm, cy, score_str)

        # interpretation text
        cy -= 6 * mm
        c.setFont(FONT, 9)
        c.setFillColor(TEXT)
        for line in interp_lines:
            c.drawString(margin_x + 5 * mm, cy, line)
            cy -= line_h

        # situational warning
        if is_sit:
            cy -= 3 * mm
            warn_h = 5 * mm + len(sit_lines) * 11
            c.setFillColor(WARN_BG)
            c.roundRect(margin_x + 4 * mm, cy - warn_h + 4 * mm, card_w - 8 * mm, warn_h, 4, stroke=0, fill=1)
            c.setFont(FONT, 8)
            c.setFillColor(HexColor("#92400E"))
            for sl in sit_lines:
                c.drawString(margin_x + 7 * mm, cy, sl)
                cy -= 11

        y -= card_h + 6 * mm

    # footer
    c.setFont(FONT, 7)
    c.setFillColor(MUTED)
    c.drawCentredString(W / 2, 15 * mm, f"Сессия: {session.id}")

    c.save()
    return buf.getvalue()


# ── View ───────────────────────────────────────────────────

@api_view(["GET"])
def result_pdf(request, session_id):
    try:
        session = TestSession.objects.get(pk=session_id)
    except (TestSession.DoesNotExist, ValueError):
        return Response({"error": "Сессия не найдена"}, status=http_status.HTTP_404_NOT_FOUND)

    pdf_bytes = build_pdf(session)

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="lantico-{session_id}.pdf"'
    return response
