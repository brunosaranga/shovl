"""
The downloadable PDF report: GET /api/scans/<id>/pdf/ (ScanPDFView in scans/views.py).

Built in memory from the scan's saved results every time someone downloads it, so nothing is
written to the server's disk (Render's free disk is wiped on every deploy). It follows the
report page: target and risk score, the counts, "since your last scan", then every finding,
worst first, with its fix when "suggest fix" was on. "verbose" adds the raw responses at the
end, cut short so one large response can't make a huge file.

Text that came from the scanned API (header values, field names, raw responses) is escaped
before it reaches ReportLab. ReportLab reads tags such as <img src="..."> in paragraph text,
and a hostile API could put one in its own responses.

Fonts are the site's own (Arbutus, Inter, JetBrains Mono), from reporter/fonts/ under the SIL
Open Font License (the licence files sit next to them; embedding in documents is allowed).
If they can't be loaded, Helvetica and Courier stand in.
"""
import io
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.platypus import (
    Flowable,
    KeepTogether,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

logger = logging.getLogger(__name__)

# ---- the site's design tokens (frontend/src/styles/tokens.css) -------------------------
INK = colors.HexColor("#0e0018")
WHITE = colors.white
NEON = colors.HexColor("#4aff00")
SOFT = colors.HexColor("#fafafa")
RAISED = colors.HexColor("#fcfcfc")
CHIP = colors.HexColor("#f1f1f1")
RULE_SOFT = colors.HexColor("#e5e4e7")

SEVERITY_FILL = {
    "CRITICAL": colors.HexColor("#ff0000"),
    "HIGH": colors.HexColor("#fd8c00"),
    "MEDIUM": colors.HexColor("#fdc500"),
    "LOW": colors.HexColor("#00ac46"),
    "PASS": colors.HexColor("#cccccc"),
    "ERROR": colors.HexColor("#8395a7"),
    "INCOMPLETE": colors.HexColor("#8395a7"),
}
# Text on a coloured fill: dark on the bright ones, white on red and slate (--on-fill, --on-dark-fill).
ON_DARK_FILL = {"CRITICAL", "ERROR", "INCOMPLETE"}

SEVERITY_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "PASS", "ERROR"]
SEVERITY_LABEL = {
    "CRITICAL": "CRITICAL",
    "HIGH": "HIGH",
    "MEDIUM": "MEDIUM",
    "LOW": "LOW",
    "PASS": "PASS",
    "ERROR": "COULD NOT RUN",
    "INCOMPLETE": "INCOMPLETE",
}

# Plain words for someone who isn't a developer (same wording as the FAQ).
SEVERITY_MEANING = [
    ("HIGH", "strong evidence of a real problem, like an invalid token getting through."),
    ("MEDIUM", "something is open to anyone, and shovl can't tell whether that's on purpose."),
    ("LOW", "something couldn't be verified or assessed."),
    ("PASS", "the check found nothing wrong."),
    ("ERROR", "the check didn't finish, which says nothing about the API."),
]

LIMITS_NOTE = (
    "shovl runs six automated checks from the outside. it is not a penetration test: "
    "business-logic flaws and anything behind complicated logins still need a person to look."
)

CHANGE_LABEL = {
    "fixed": "fixed",
    "new": "new problem",
    "better": "better",
    "worse": "worse",
    "same": "unchanged",
    "not_compared": "can't compare",
}

# "verbose" raw responses: at most this many lines per finding, each cut to this width.
RAW_MAX_LINES = 60
RAW_LINE_WIDTH = 92

PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN_X = 18 * mm
MARGIN_TOP = 16 * mm
MARGIN_BOTTOM = 22 * mm
CONTENT_WIDTH = PAGE_WIDTH - 2 * MARGIN_X
SHADOW = 4  # points: the hard offset shadow under every box


# ---- fonts -------------------------------------------------------------------------------
FONT_DIR = Path(__file__).resolve().parent / "fonts"
FONTS = {
    "display": ("Helvetica-Bold", "ShovlDisplay", "Arbutus-Regular.ttf"),
    "sans": ("Helvetica", "ShovlSans", "Inter-Regular.ttf"),
    "sans-bold": ("Helvetica-Bold", "ShovlSans-Bold", "Inter-Bold.ttf"),
    "mono": ("Courier", "ShovlMono", "JetBrainsMono-Regular.ttf"),
    "mono-bold": ("Courier-Bold", "ShovlMono-Bold", "JetBrainsMono-Bold.ttf"),
}


def _load_fonts():
    """{role: font name}. The site's fonts when they load, the built-in ones otherwise."""
    names = {}
    for role, (fallback, name, filename) in FONTS.items():
        try:
            if name not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(name, str(FONT_DIR / filename)))
            names[role] = name
        except Exception:
            logger.warning("PDF font %s could not be loaded; using %s", filename, fallback)
            names[role] = fallback
    return names


F = _load_fonts()


# ---- text helpers --------------------------------------------------------------------------
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


def clean(value):
    """Plain text: no control characters, never None."""
    if value is None:
        return ""
    return _CONTROL.sub("", str(value))


def esc(value):
    """Text that is safe inside a ReportLab paragraph: nothing in it is read as a tag."""
    return escape(clean(value))


def upper(value):
    return str(value or "").upper()


def format_time(value):
    """'18 Oct 2026, 02:11 UTC' from an ISO time, or the text as it is if it isn't one."""
    if not value:
        return "unknown"
    try:
        moment = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return clean(value)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).strftime("%d %b %Y, %H:%M UTC")


def _style(name, font, size, leading=None, color=INK, alignment=TA_LEFT, **extra):
    return ParagraphStyle(name, fontName=F[font], fontSize=size, leading=leading or size * 1.35,
                          textColor=color, alignment=alignment, **extra)


S = {
    "h2": _style("h2", "display", 17, 21, spaceBefore=4, spaceAfter=6),
    "lead": _style("lead", "mono", 8.5, 12),
    "label": _style("label", "mono-bold", 8, 11),
    "value": _style("value", "mono", 9, 12.5),
    "body": _style("body", "sans", 9.5, 13.5),
    "body-bold": _style("body-bold", "sans-bold", 9.5, 13.5),
    "name": _style("name", "sans-bold", 10.5, 13.5),
    "id": _style("id", "mono", 8.5, 11, alignment=2),
    "bullet": _style("bullet", "sans", 9.2, 13.2, leftIndent=10, bulletIndent=0, spaceAfter=2),
    "fix": _style("fix", "sans", 9.2, 13.2),
    "small": _style("small", "mono", 7.5, 10),
    "risk-word": _style("risk-word", "mono-bold", 21, 24),
    "risk-label": _style("risk-label", "mono-bold", 7.5, 10),
    "count": _style("count", "mono-bold", 18, 22, alignment=1),
    "count-label": _style("count-label", "mono-bold", 7, 9, alignment=1),
    "raw": _style("raw", "mono", 7, 9.2, color=WHITE),
    "raw-title": _style("raw-title", "mono-bold", 8, 11),
}


def _on_fill_style(base, severity):
    style = ParagraphStyle(f"{base.name}-{severity}", parent=base)
    style.textColor = WHITE if severity in ON_DARK_FILL else INK
    return style


# ---- boxes ---------------------------------------------------------------------------------
class BoxTable(Table):
    """A table drawn as the site's box: solid border and a hard offset shadow (also after a split)."""

    shadow = SHADOW

    def draw(self):
        c = self.canv
        c.saveState()
        c.setFillColor(INK)
        c.rect(self.shadow, -self.shadow, self._width, self._height, stroke=0, fill=1)
        c.setFillColor(WHITE)
        c.rect(0, 0, self._width, self._height, stroke=0, fill=1)
        c.restoreState()
        super().draw()


def box(rows, widths, extra_style=(), border=2):
    table = BoxTable(rows, colWidths=widths)
    table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), border, INK),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        *extra_style,
    ]))
    table.hAlign = "LEFT"
    return table


def badge(severity, size=7.5):
    """The coloured severity chip, as a one-cell table."""
    severity = upper(severity) or "ERROR"
    fill = SEVERITY_FILL.get(severity, SEVERITY_FILL["ERROR"])
    text = SEVERITY_LABEL.get(severity, severity)
    style = _on_fill_style(_style(f"badge-{size}", "mono-bold", size, size + 2.5), severity)
    width = pdfmetrics.stringWidth(text, style.fontName, size) + 10
    chip = Table([[Paragraph(esc(text), style)]], colWidths=[width])
    chip.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), fill),
        ("BOX", (0, 0), (-1, -1), 0.8, INK),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    chip.hAlign = "LEFT"
    return chip


class Masthead(Flowable):
    """'shovl' on the left, what this is on the right, a heavy rule underneath."""

    def __init__(self, right_lines):
        super().__init__()
        self.right_lines = right_lines
        self.height = 50

    def wrap(self, available_width, available_height):
        self.width = available_width
        return self.width, self.height

    def draw(self):
        c = self.canv
        c.setFillColor(INK)
        c.setFont(F["display"], 34)
        c.drawString(0, 16, "shovl")
        c.setFont(F["mono"], 8.5)
        y = 36
        for line in self.right_lines:
            c.drawRightString(self.width, y, line)
            y -= 11
        # the beta chip
        label = "BETA"
        chip_width = pdfmetrics.stringWidth(label, F["mono-bold"], 7) + 8
        c.setFillColor(NEON)
        c.setStrokeColor(INK)
        c.setLineWidth(0.8)
        word_width = pdfmetrics.stringWidth("shovl", F["display"], 34)
        c.rect(word_width + 6, 30, chip_width, 11, stroke=1, fill=1)
        c.setFillColor(INK)
        c.setFont(F["mono-bold"], 7)
        c.drawString(word_width + 10, 33, label)
        c.setLineWidth(3)
        c.line(0, 3, self.width, 3)


# ---- sections ------------------------------------------------------------------------------
def _checks_line(meta, findings):
    total = meta.get("total_checks", len(findings))
    failed = meta.get("checks_failed")
    if failed is None:
        failed = sum(1 for f in findings if upper(f.get("severity")) == "ERROR")
    ran = meta.get("checks_run", max(total - failed, 0))
    line = f"{ran} of {total} ran"
    if failed:
        line += f" ({failed} could not run)"
    return line


def _options_line(meta):
    def state(key, default=False):
        return "on" if meta.get(key, default) else "off"
    return (
        f"generate report: {state('generate_report', True)} · "
        f"suggest fix: {state('suggest_fix')} · verbose: {state('verbose')}"
    )


def target_box(meta, findings, target_url):
    label_width = 30 * mm
    rows = [
        [Paragraph("target", S["label"]), Paragraph(esc(meta.get("target") or target_url or "unknown"), S["value"])],
        [Paragraph("scanned", S["label"]), Paragraph(esc(format_time(meta.get("scanned_at"))), S["value"])],
        [Paragraph("checks", S["label"]), Paragraph(esc(_checks_line(meta, findings)), S["value"])],
        [Paragraph("options", S["label"]), Paragraph(esc(_options_line(meta)), S["value"])],
    ]
    return box(rows, [label_width, CONTENT_WIDTH - label_width - SHADOW], border=2.5, extra_style=[
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, 0), 9),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 9),
    ])


def risk_explanation(risk, summary):
    problems = sum(summary.get(level, 0) for level in ("CRITICAL", "HIGH", "MEDIUM", "LOW"))
    if risk in ("CRITICAL", "HIGH"):
        return "at least one check found strong evidence of a real problem. start with the high findings below."
    if risk == "MEDIUM":
        return ("the worst finding is something open to anyone, which may or may not be on purpose. "
                "go through the medium findings and decide which ones should be closed.")
    if risk == "LOW" and problems:
        return "nothing serious found. the low findings are things shovl couldn't fully verify."
    if risk == "LOW":
        return "every check that ran passed."
    if risk == "INCOMPLETE":
        return "no check could finish, so shovl can't say anything about this API yet. run the scan again."
    return "no overall score was saved for this scan."


def risk_box(risk, summary):
    risk = upper(risk) or "INCOMPLETE"
    fill = SEVERITY_FILL.get(risk, SEVERITY_FILL["INCOMPLETE"])
    left_width = 46 * mm
    left = [
        Paragraph("RISK SCORE", _on_fill_style(S["risk-label"], risk)),
        Paragraph(esc(SEVERITY_LABEL.get(risk, risk)), _on_fill_style(S["risk-word"], risk)),
    ]
    right = [Paragraph(esc(risk_explanation(risk, summary)), S["body"])]
    return box([[left, right]], [left_width, CONTENT_WIDTH - left_width - SHADOW], border=2.5, extra_style=[
        ("BACKGROUND", (0, 0), (0, 0), fill),
        ("LINEAFTER", (0, 0), (0, 0), 2, INK),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (1, 0), (1, 0), 12),
    ])


def counts_row(summary):
    levels = ["HIGH", "MEDIUM", "LOW", "PASS", "ERROR"]
    labels = {"PASS": "PASSED", "ERROR": "COULD NOT RUN"}
    gap = 6
    width = (CONTENT_WIDTH - SHADOW - gap * (len(levels) - 1)) / len(levels)
    cells = []
    for level in levels:
        cell = box(
            [[Paragraph(labels.get(level, level), _on_fill_style(S["count-label"], level))],
             [Paragraph(str(int(summary.get(level, 0) or 0)), S["count"])]],
            [width - SHADOW],
            extra_style=[
                ("BACKGROUND", (0, 0), (-1, 0), SEVERITY_FILL[level]),
                ("LINEBELOW", (0, 0), (-1, 0), 2, INK),
                ("TOPPADDING", (0, 0), (-1, 0), 4),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
                ("TOPPADDING", (0, 1), (-1, 1), 6),
                ("BOTTOMPADDING", (0, 1), (-1, 1), 8),
            ],
        )
        cells.append(cell)
    row = Table([cells], colWidths=[width + (gap if i < len(levels) - 1 else 0) for i in range(len(levels))])
    row.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), SHADOW),
    ]))
    row.hAlign = "LEFT"
    return row


def comparison_section(comparison):
    previous = comparison.get("previous") or {}
    risk = comparison.get("risk") or {}
    counts = comparison.get("counts") or {}
    checks = comparison.get("checks") or []

    parts = [Paragraph("since your last scan", S["h2"])]
    parts.append(Paragraph(
        esc(f"compared with scan #{previous.get('id', '?')} of the same address, "
            f"{format_time(previous.get('scanned_at'))}."),
        S["lead"],
    ))
    before, after = upper(risk.get("before")), upper(risk.get("after"))
    if before and after:
        verdict = "unchanged" if before == after else f"{SEVERITY_LABEL.get(before, before)} → {SEVERITY_LABEL.get(after, after)}"
        parts.append(Paragraph(esc(f"risk score: {verdict}"), S["lead"]))

    summary_bits = [
        f"{counts[key]} {CHANGE_LABEL[key]}"
        for key in ("fixed", "better", "new", "worse", "same", "not_compared")
        if counts.get(key)
    ]
    if summary_bits:
        parts.append(Paragraph(esc(" · ".join(summary_bits)), S["lead"]))
    parts.append(Spacer(1, 6))

    changed = [item for item in checks if item.get("change") != "same"]
    if not changed:
        parts.append(Paragraph("nothing changed: every check has the same result as last time.", S["body"]))
        return parts

    rows = []
    for item in changed:
        before_badge = badge(item.get("before") or "ERROR", 6.5)
        after_badge = badge(item.get("after") or "ERROR", 6.5)
        movement = Table([[before_badge, Paragraph("→", S["value"]), after_badge]])
        movement.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        movement.hAlign = "LEFT"
        rows.append([
            Paragraph(esc(item.get("check") or item.get("id")), S["body-bold"]),
            movement,
            Paragraph(esc(CHANGE_LABEL.get(item.get("change"), item.get("change"))), S["label"]),
        ])
    widths = [62 * mm, 70 * mm, CONTENT_WIDTH - SHADOW - 132 * mm]
    parts.append(box(rows, widths, extra_style=[
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, -2), 0.6, RULE_SOFT),
    ]))
    return parts


def _rank(finding):
    severity = upper(finding.get("severity"))
    return SEVERITY_ORDER.index(severity) if severity in SEVERITY_ORDER else len(SEVERITY_ORDER)


def finding_card(finding):
    severity = upper(finding.get("severity")) or "ERROR"
    details = finding.get("detail")
    if isinstance(details, str):
        details = [details]
    details = [d for d in (details or []) if clean(d).strip()]

    badge_width, id_width = 28 * mm, 18 * mm
    name_width = CONTENT_WIDTH - SHADOW - badge_width - id_width
    rows = [[badge(severity), Paragraph(esc(finding.get("check") or "check"), S["name"]),
             Paragraph(esc(finding.get("id") or ""), S["id"])]]
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), RAISED),
        ("LINEBELOW", (0, 0), (-1, 0), 1.5, INK),
        ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
    ]

    body = [Paragraph(esc(line), S["bullet"], bulletText="•") for line in details]
    if not body:
        body = [Paragraph("no additional detail.", S["body"])]
    rows.append([body, "", ""])
    style += [("SPAN", (0, 1), (-1, 1)), ("BACKGROUND", (0, 1), (-1, 1), SOFT)]

    if finding.get("remediation"):
        rows.append([[Paragraph("how to fix", S["label"]), Spacer(1, 2),
                      Paragraph(esc(finding["remediation"]), S["fix"])], "", ""])
        index = len(rows) - 1
        style += [
            ("SPAN", (0, index), (-1, index)),
            ("BACKGROUND", (0, index), (-1, index), SOFT),
            ("LINEBEFORE", (0, index), (0, index), 4, NEON),
            ("LINEABOVE", (0, index), (-1, index), 0.6, RULE_SOFT),
        ]

    return KeepTogether([box(rows, [badge_width, name_width, id_width], extra_style=style), Spacer(1, 12)])


def legend_box():
    rows = [[Paragraph("reading this report", S["label"]), ""]]
    for severity, meaning in SEVERITY_MEANING:
        rows.append([badge(severity, 6.5), Paragraph(esc(meaning), S["body"])])
    rows.append([Paragraph(esc(LIMITS_NOTE), S["body"]), ""])
    last = len(rows) - 1
    return box(rows, [34 * mm, CONTENT_WIDTH - SHADOW - 34 * mm], extra_style=[
        ("SPAN", (0, 0), (-1, 0)),
        ("SPAN", (0, last), (-1, last)),
        ("VALIGN", (0, 1), (-1, -1), "MIDDLE"),
        ("LINEABOVE", (0, last), (-1, last), 0.6, RULE_SOFT),
        ("TOPPADDING", (0, 1), (-1, last - 1), 3),
        ("BOTTOMPADDING", (0, 1), (-1, last - 1), 3),
        ("TOPPADDING", (0, last), (-1, last), 8),
    ])


def raw_lines(raw):
    """The raw data as wrapped lines, at most RAW_MAX_LINES, and whether it was cut."""
    try:
        text = json.dumps(raw, indent=2, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        text = str(raw)
    lines = []
    for line in clean(text).split("\n"):
        while len(line) > RAW_LINE_WIDTH:
            lines.append(line[:RAW_LINE_WIDTH])
            line = "  " + line[RAW_LINE_WIDTH:]
        lines.append(line)
    cut = len(lines) > RAW_MAX_LINES
    return lines[:RAW_MAX_LINES], cut


def raw_section(findings):
    with_raw = [f for f in findings if isinstance(f.get("raw"), dict) and f.get("raw")]
    if not with_raw:
        return []
    parts = [Paragraph("raw responses (verbose)", S["h2"]),
             Paragraph("what the API sent back to each check, cut short where it was long.", S["lead"]),
             Spacer(1, 8)]
    for finding in with_raw:
        lines, cut = raw_lines(finding["raw"])
        if cut:
            lines.append("… cut short here. the report page has all of it.")
        title = f"{clean(finding.get('id'))} · {clean(finding.get('check'))}"
        block = Table([[Preformatted("\n".join(lines), S["raw"])]], colWidths=[CONTENT_WIDTH - SHADOW])
        block.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), INK),
            ("LEFTPADDING", (0, 0), (-1, -1), 9),
            ("RIGHTPADDING", (0, 0), (-1, -1), 9),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        parts.append(KeepTogether([Paragraph(esc(title), S["raw-title"]), Spacer(1, 3), block]))
        parts.append(Spacer(1, 12))
    return parts


# ---- pages ---------------------------------------------------------------------------------
def _canvas_maker(footer_left, footer_right):
    """A canvas that writes 'page N of M' in the footer once it knows M."""

    class FooterCanvas(pdfcanvas.Canvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._pages = []

        def showPage(self):
            self._pages.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            total = len(self._pages)
            for number, state in enumerate(self._pages, start=1):
                self.__dict__.update(state)
                self._footer(number, total)
                super().showPage()
            super().save()

        def _footer(self, number, total):
            y = 12 * mm
            self.saveState()
            self.setStrokeColor(INK)
            self.setLineWidth(1.2)
            self.line(MARGIN_X, y + 9, PAGE_WIDTH - MARGIN_X, y + 9)
            self.setFillColor(NEON)
            self.rect(MARGIN_X, y - 0.5, 6, 6, stroke=0, fill=1)
            self.setFillColor(INK)
            self.setFont(F["mono"], 7.5)
            self.drawString(MARGIN_X + 10, y, footer_left)
            self.drawRightString(PAGE_WIDTH - MARGIN_X, y, f"{footer_right} · page {number} of {total}")
            self.restoreState()

    return FooterCanvas


def build_pdf(results, *, scan_id, target_url="", comparison=None, site="", generated_at=None):
    """
    The report as PDF bytes, from a complete scan's saved results (Scan.results).
    comparison: scans/compare.py's comparison_for(scan), or None.
    """
    results = results or {}
    meta = results.get("meta") or {}
    findings = [f for f in (results.get("findings") or []) if isinstance(f, dict)]
    summary = results.get("summary") or {}
    risk = upper(meta.get("risk_score"))
    generated_at = generated_at or datetime.now(timezone.utc)
    host = clean(meta.get("target") or target_url)

    story = [
        Masthead(["api security report", f"scan #{scan_id} · {format_time(meta.get('scanned_at'))}"]),
        Spacer(1, 14),
        target_box(meta, findings, target_url),
        Spacer(1, 12),
        risk_box(risk, summary),
        Spacer(1, 12),
        counts_row(summary),
        Spacer(1, 10),
    ]

    if comparison:
        story += comparison_section(comparison)
        story.append(Spacer(1, 12))

    ordered = sorted(enumerate(findings), key=lambda pair: (_rank(pair[1]), pair[0]))
    story.append(Paragraph("findings", S["h2"]))
    lead = "worst first."
    if meta.get("suggest_fix"):
        lead += " each problem comes with a fix."
    story += [Paragraph(lead, S["lead"]), Spacer(1, 8)]
    if ordered:
        story += [finding_card(finding) for _, finding in ordered]
    else:
        story.append(Paragraph("no findings were saved for this scan.", S["body"]))

    story += [Spacer(1, 4), KeepTogether([legend_box()]), Spacer(1, 14)]

    if meta.get("verbose"):
        story += raw_section(findings)

    footer_left = "made with shovl beta" + (f" · {clean(site)}" if site else "")
    footer_right = f"scan #{scan_id} · generated {format_time(generated_at.isoformat())}"

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=MARGIN_X,
        rightMargin=MARGIN_X,
        topMargin=MARGIN_TOP,
        bottomMargin=MARGIN_BOTTOM,
        title=f"shovl report: {host}"[:200],
        author="shovl",
        subject="API security report",
        creator="shovl beta",
    )
    doc.build(story, canvasmaker=_canvas_maker(footer_left, footer_right))
    return buffer.getvalue()


def generate_pdf(report, output_path, scan_id="local"):
    """Writes the PDF to a file. For local scripts only (test_scan.py); the API never writes to disk."""
    data = build_pdf(report, scan_id=scan_id)
    output = Path(output_path)
    if output.parent and not output.parent.exists():
        output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)
    return str(output)
