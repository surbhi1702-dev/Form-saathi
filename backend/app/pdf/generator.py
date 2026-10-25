"""PDF output: a filled-form draft, a cheque-writing guide, a rental agreement draft, or a deed details sheet.

PDFs are in English because official forms are filled in English block letters
(the extractor transliterates answers given in other scripts). Every page is
clearly marked as a draft prepared by Form Saathi - it is something to copy from
or take to a lawyer/office, never a substitute for the official form.
"""
from __future__ import annotations

import io
from datetime import date
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from ..forms import engine
from ..i18n import loc
from ..validators import amount_in_words, display_value, format_inr, shown_value

INK = colors.HexColor("#1f2a44")
ACCENT = colors.HexColor("#c2410c")
RULE = colors.HexColor("#d6d3d1")
PAPER = colors.HexColor("#fafaf9")

_ss = getSampleStyleSheet()
S = {
    "title": ParagraphStyle("t", parent=_ss["Title"], fontName="Helvetica-Bold", fontSize=17, textColor=INK, alignment=0, spaceAfter=2),
    "sub": ParagraphStyle("s", parent=_ss["Normal"], fontSize=9.5, textColor=colors.HexColor("#57534e"), spaceAfter=8),
    "h": ParagraphStyle("h", parent=_ss["Heading3"], fontName="Helvetica-Bold", fontSize=11.5, textColor=INK, spaceBefore=10, spaceAfter=4),
    "body": ParagraphStyle("b", parent=_ss["Normal"], fontSize=10, leading=14.5, textColor=INK),
    "cell": ParagraphStyle("c", parent=_ss["Normal"], fontSize=9.5, leading=12.5, textColor=INK),
    "cellb": ParagraphStyle("cb", parent=_ss["Normal"], fontName="Helvetica-Bold", fontSize=9.5, leading=12.5, textColor=INK),
    "warn": ParagraphStyle("w", parent=_ss["Normal"], fontSize=9.5, leading=13, textColor=ACCENT),
    "small": ParagraphStyle("sm", parent=_ss["Normal"], fontSize=8, leading=10, textColor=colors.HexColor("#78716c")),
    "clause": ParagraphStyle("cl", parent=_ss["Normal"], fontSize=10, leading=15, textColor=INK, spaceAfter=5, leftIndent=12, firstLineIndent=-12),
}


def _ordinal(n) -> str:
    n = int(n)
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _p(text, style="cell") -> Paragraph:
    return Paragraph(escape(str(text)).replace("\n", "<br/>"), S[style])


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#78716c"))
    canvas.drawString(18 * mm, 10 * mm, "DRAFT prepared with Form Saathi - copy onto the official form / verify before signing.")
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


def _table(rows, widths=(62 * mm, 112 * mm)):
    t = Table([[_p(a, "cellb"), _p(b)] for a, b in rows], colWidths=widths)
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, RULE),
        ("BACKGROUND", (0, 0), (0, -1), PAPER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


def _value(field, values, mask_sensitive):
    v = values.get(field["id"])
    return shown_value(field, v) if mask_sensitive else display_value(field, v)


def _header(story, form):
    story.append(Paragraph(escape(loc(form["title"], "en")), S["title"]))
    story.append(_p(f"{form.get('department', '')}  |  Prepared on {date.today().strftime('%d/%m/%Y')}", "sub"))


def _extras(story, form, values, notes):
    warnings = engine.run_checks(form, values)
    if warnings:
        story.append(Paragraph("Please double-check", S["h"]))
        for w in warnings:
            story.append(_p("! " + w, "warn"))
    if notes:
        story.append(Paragraph("Notes", S["h"]))
        for fid, note in notes.items():
            f = engine.field_by_id(form, fid)
            if f and fid in values:
                story.append(_p(f"{loc(f['label'], 'en')}: {note}", "body"))
    if form.get("documents"):
        story.append(Paragraph("Documents to carry", S["h"]))
        for d in form["documents"]:
            story.append(_p("[  ]  " + d, "body"))
    if form.get("submit_note"):
        story.append(Paragraph("Where and how to submit", S["h"]))
        story.append(_p(form["submit_note"], "body"))


def _signature(story, values):
    story.append(Spacer(1, 14 * mm))
    sig = Table([[_p(f"Place: {values.get('place', '')}"), _p("Signature of applicant: ______________________")],
                 [_p(f"Date: {date.today().strftime('%d/%m/%Y')}"), _p("")]], colWidths=(80 * mm, 94 * mm))
    story.append(sig)


def _form_story(form, values, notes, mask_sensitive):
    story = []
    _header(story, form)
    rows = [(loc(f["label"], "en"), _value(f, values, mask_sensitive))
            for f in engine.visible_fields(form, values) if f["id"] in values]
    rows += [(loc(c["label"], "en"), engine.computed_display(c)) for c in engine.compute_values(form, values)]
    story.append(Paragraph("Details to fill", S["h"]))
    story.append(_table(rows))
    _extras(story, form, values, notes)
    _signature(story, values)
    return story


def _cheque_story(form, values, notes, mask_sensitive):  # noqa: ARG001
    story = []
    _header(story, form)
    amount = values.get("amount", 0)
    crossed = values.get("account_payee") == "Yes"
    story.append(Paragraph("What to write where", S["h"]))
    story.append(_table([
        ("Date box (top right)", values.get("cheque_date", "").replace("/", " ")),
        ("Pay (line 1)", f"{values.get('payee_name', '')} -----------------"),
        ("Rupees (in words)", amount_in_words(amount) + " -----"),
        ("Rs. box (figures)", f"{format_inr(amount)}/-"),
        ("Top-left corner", "Draw two parallel lines and write 'A/c Payee' between them" if crossed
         else "Leave uncrossed (anyone holding it can encash it at the counter - not recommended)"),
        ("Signature (bottom right)", "Sign exactly as in the bank's records"),
    ]))
    story.append(Paragraph("Rules that prevent rejection", S["h"]))
    for tip in ["Use one pen for the whole cheque; do not overwrite or correct anything - use a new leaf instead.",
                "Draw a line after the payee name and after the amount in words so nothing can be added.",
                "Write the figures close to the Rs. symbol and end them with /-.",
                "The cheque is valid for 3 months from the date written on it.",
                "Note the cheque number, date, payee and amount in your cheque book counterfoil."]:
        story.append(_p("- " + tip, "body"))
    _extras(story, {**form, "documents": [], "submit_note": ""}, values, notes)
    return story


def _agreement_story(form, values, notes):  # noqa: ARG001
    v = values
    comp = {c["id"]: c for c in engine.compute_values(form, values)}
    story = [Paragraph(escape(f"{v.get('purpose', 'Residential').upper()} RENTAL AGREEMENT"), S["title"]),
             _p("Draft - print on stamp paper of the value required in your state, and have it reviewed before signing.", "sub")]
    end = comp.get("end_date", {}).get("value", "")
    rent, dep = v.get("monthly_rent", 0), v.get("security_deposit", 0)
    story.append(_p(
        f"This Rental Agreement is made at {v.get('place', '')} on {v.get('start_date', '')} between "
        f"{v.get('owner_name', '')}, S/o / D/o / W/o {v.get('owner_father', '')}, residing at {v.get('owner_address', '')} "
        f"(hereinafter called the OWNER) of the one part, and {v.get('tenant_name', '')}, S/o / D/o / W/o "
        f"{v.get('tenant_father', '')}, permanently residing at {v.get('tenant_permanent_address', '')} "
        "(hereinafter called the TENANT) of the other part.", "body"))
    story.append(Spacer(1, 4 * mm))
    story.append(_p(f"WHEREAS the Owner is the lawful owner of the {v.get('furnishing', '').lower()} premises at "
                    f"{v.get('property_address', '')} (the PREMISES), and has agreed to let it to the Tenant on the terms below:", "body"))
    clauses = [
        f"Term: The tenancy is for {v.get('duration_months', '')} months, from {v.get('start_date', '')} to {end}.",
        f"Rent: The Tenant shall pay a monthly rent of Rs. {format_inr(rent)} ({amount_in_words(rent)}) on or before "
        f"the {_ordinal(v.get('rent_due_day', 5))} day of each month.",
        f"Security deposit: The Tenant has paid a refundable, interest-free deposit of Rs. {format_inr(dep)} "
        f"({amount_in_words(dep)}), to be returned when the Tenant vacates, after deducting unpaid rent, charges or damages beyond normal wear and tear.",
        "Maintenance: Maintenance/society charges are " + ("included in the rent." if v.get("maintenance") == "Included in rent"
                                                            else "payable by the Tenant separately."),
        "Utilities: Electricity and water charges as per actual meter readings shall be paid by the Tenant.",
        f"Use: The premises shall be used only for {v.get('purpose', 'residential').lower()} purposes, and shall not be sub-let.",
        f"Notice: Either party may end this agreement by giving {v.get('notice_period_months', '')} month(s) written notice.",
        f"Renewal: The agreement may be renewed by mutual consent, with a rent increase of {v.get('rent_increase_percent', 0)}%.",
        "Repairs: Minor repairs are the Tenant's responsibility; structural and major repairs are the Owner's.",
        "Access: The Owner may inspect the premises at a reasonable time with prior notice.",
        "Handover: On expiry or termination, the Tenant shall hand over vacant possession in good condition.",
    ]
    story.append(Paragraph("Terms", S["h"]))
    for i, c in enumerate(clauses, 1):
        story.append(_p(f"{i}. {c}", "clause"))
    for w in engine.run_checks(form, values):
        story.append(_p("! " + w, "warn"))
    story.append(Spacer(1, 12 * mm))
    sig = Table([[_p("OWNER\n\n\n_______________________\n" + v.get("owner_name", "")),
                  _p("TENANT\n\n\n_______________________\n" + v.get("tenant_name", ""))],
                 [_p("WITNESS 1\n\n\n_______________________\nName & address:"),
                  _p("WITNESS 2\n\n\n_______________________\nName & address:")]],
                colWidths=(87 * mm, 87 * mm))
    sig.setStyle(TableStyle([("TOPPADDING", (0, 0), (-1, -1), 8)]))
    story.append(KeepTogether(sig))
    return story


def _deed_story(form, values, notes, mask_sensitive):
    story = _form_story(form, values, notes, mask_sensitive)
    story.insert(2, _p("This is a details sheet for your document writer or lawyer. It is not the deed itself. "
                       "Stamp duty and fee figures are estimates using configurable rates - confirm the current "
                       "rates with the Sub-Registrar office.", "warn"))
    return story


def build_pdf(form: dict, values: dict, notes: dict | None = None, mask_sensitive: bool = False) -> bytes:
    notes = notes or {}
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                            bottomMargin=18 * mm, title=loc(form["title"], "en"), author="Form Saathi")
    kind = form.get("output", "form")
    if kind == "cheque":
        story = _cheque_story(form, values, notes, mask_sensitive)
    elif kind == "agreement":
        story = _agreement_story(form, values, notes)
    elif kind == "deed":
        story = _deed_story(form, values, notes, mask_sensitive)
    else:
        story = _form_story(form, values, notes, mask_sensitive)
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()
