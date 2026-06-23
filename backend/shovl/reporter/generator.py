import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
)
from reportlab.lib.enums import TA_CENTER

# Colours ---------------------------------------------
ACCENT = colors.HexColor("#007a5e")
DARK = colors.black
MUTED = colors.HexColor("#444444")

SEVERITY_COLORS = {
    "CRITICAL": colors.HexColor("#ff4444"),
    "HIGH": colors.HexColor("#ff8800"),
    "MEDIUM": colors.HexColor("#ffcc00"),
    "LOW": colors.HexColor("#44bb44"),
    "PASS": colors.HexColor("#aaaaaa"),
    "ERROR": colors.HexColor("#cccccc")
}


# Styles --------------------------------------------
_base = getSampleStyleSheet()

title_style = ParagraphStyle("title", parent=_base["Normal"], fontName="Helvetica-Bold", fontSize=24, textColor=ACCENT, spaceAfter=4)

meta_style = ParagraphStyle("meta", parent=_base["Normal"], fontName="Helvetica", fontSize=10, textColor=MUTED, spaceAfter=16)

h2_style = ParagraphStyle("h2", parent=_base["Normal"], fontName="Helvetica-Bold", fontSize=13, textColor=DARK, spaceBefore=12, spaceAfter=6)

body_style = ParagraphStyle("body", parent=_base["Normal"], fontName="Helvetica", fontSize=12, textColor=DARK, spaceAfter=4, leading=16)

note_style = ParagraphStyle("note", parent=_base["Normal"], fontName="Helvetica-Oblique", fontSize=10, textColor=MUTED, spaceAfter=4, leftIndent=8)

raw_style = ParagraphStyle("raw", parent=_base["Normal"], fontName="Courier", fontSize=8, textColor=colors.HexColor("#333333"),
    backColor=colors.HexColor("#f0f0f0"),
    leftIndent=8, spaceAfter=4, leading=12)

footer_style = ParagraphStyle("footer", parent=_base["Normal"], fontName="Helvetica", fontSize=9, textColor=MUTED, alignment=TA_CENTER)



# Helpers --------------------------------------------
def _hr():
    return HRFlowable(
        width="100%",
        thickness=0.5,
        color=colors.HexColor("#cccccc"),
        spaceAfter=8, spaceBefore=4
    )

def _severity_badge(severity: str) -> Table:
    bg = SEVERITY_COLORS.get(severity, colors.grey)
    text_color = colors.black if severity == "MEDIUM" else colors.white
    t = Table([[severity]], colWidths=[40*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), bg),
        ("TEXTCOLOR",     (0, 0), (-1, -1), text_color),
        ("FONTNAME",      (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t



# Main -----------------------------------------
def generate_pdf(report: dict, output_path: str) -> str:
    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=20*mm, bottomMargin=20*mm,
    )

    meta     = report["meta"]
    summary  = report["summary"]
    findings = report["findings"]
    story    = []

    # Header ----------------------------------
    story.append(Paragraph("shovl", title_style))
    story.append(Paragraph("API Security Audit Report", meta_style))
    story.append(_hr())

    # Meta ----------------------------------
    story.append(Paragraph(f"Target:       {meta['target']}", body_style))
    story.append(Paragraph(f"Scanned:      {meta['scanned_at']}", body_style))
    story.append(Paragraph(f"Overall Risk: {meta['risk_score']}", body_style))
    story.append(Paragraph(f"Checks Run:   {meta['total_checks']}", body_style))
    story.append(Spacer(1, 12))

    #  Summary Table ----------------------------------
    story.append(Paragraph("Summary", h2_style))
    col_w = [30*mm] * len(summary)
    summary_table = Table(
        [list(summary.keys()), [str(v) for v in summary.values()]],
        colWidths=col_w
    )
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0),  ACCENT),
        ("TEXTCOLOR",  (0, 0), (-1, 0),  colors.white),
        ("FONTNAME",   (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, -1), 10),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f5f5f5")),
        ("TEXTCOLOR",  (0, 1), (-1, -1), DARK),
        ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
        ("GRID",       (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
        ("PADDING",    (0, 0), (-1, -1), 6),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 16))

    # Findings ----------------------------------
    story.append(Paragraph("Findings", h2_style))
    story.append(_hr())

    for finding in findings:
        # Title row with severity badge
        header = Table([[
            Paragraph(f"<b>{finding['id']} - {finding['check']}</b>", body_style),
            _severity_badge(finding['severity']),
        ]], colWidths=[120*mm, 40*mm])
        header.setStyle(TableStyle([
            ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING",  (0, 0), (0, -1),  0),
            ("RIGHTPADDING", (-1, 0), (-1, -1), 0),
        ]))
        story.append(header)

        # Detail items
        for item in finding["detail"]:
            story.append(Paragraph(f"&#8594; {item}", note_style))

        # Raw block (verbose mode only)
        if meta.get("verbose") and finding.get("raw"):
            story.append(Paragraph(str(finding["raw"]), raw_style))

        story.append(Spacer(1, 10))
        story.append(_hr())

    # Footer ----------------------------------
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        f"shovl &middot; {meta['scanned_at']} &middot; dig deeper",
        footer_style
    ))

    doc.build(story)
    return output_path

























# from jinja2 import Environment, FileSystemLoader
# from weasyprint import HTML
# import os

# # Path to the templates folder
# TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates", "reporter")

# def render_html(report: dict) -> str:
#     """Render the report dict into an HTML string."""
#     env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
#     template = env.get_template("report.html")
#     return template.render(report=report)

# # Passing the HTML string to be converted to PDF
# def generate_pdf(report: dict, output_path: str) -> str:
#     """Convert rendered HTML intoa PDF file. Returns the output path."""
#     html_string = render_html(report)
#     HTML(string=html_string).write_pdf(output_path)
#     return output_path
