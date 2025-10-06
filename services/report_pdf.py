from __future__ import annotations

from typing import List
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle, PageBreak
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from PIL import Image as PILImage

from xpenseit.models import ReportHeader, ExpenseEntry
from datetime import date as _date


def build_pdf_report(header: ReportHeader, entries: List[ExpenseEntry], usd_to_mxn: float, logo_path: str | None) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=36, bottomMargin=36, leftMargin=36, rightMargin=36)
    styles = getSampleStyleSheet()
    cell_style = ParagraphStyle(
        "cell8",
        parent=styles["BodyText"],
        fontSize=8,
        leading=9,
        spaceAfter=0,
        spaceBefore=0,
    )
    flow = []

    # Header with logo
    if logo_path:
        try:
            img = RLImage(logo_path, width=1.6*inch, height=0.6*inch)
            flow.append(img)
        except Exception:
            pass
    flow.append(Paragraph("<b>Expense Report</b>", styles["Title"]))
    flow.append(Spacer(1, 6))

    page_w = doc.width
    meta_table = Table([
        ["Reporter", header.reporter_name or "", "Date", header.report_date.isoformat()],
        ["Trip Purpose", header.trip_purpose or "", "Client", header.client or ""],
        ["Visit Type", header.visit_type or "", "Base Currency", header.base_currency or ""],
        ["FX (1 USD)", f"{usd_to_mxn:.4f} MXN", "", ""],
    ], colWidths=[0.2*page_w, 0.3*page_w, 0.2*page_w, 0.3*page_w])
    meta_table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.25, colors.grey),
        ("BACKGROUND", (0,0), (-1,0), colors.whitesmoke),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))
    flow.append(meta_table)
    flow.append(Spacer(1, 12))

    # Expenses table with links (sorted by date ascending)
    table_data = [["Merchant", "Date", "Time", "Total", "Currency", "Payment", "Category", "Source"]]
    sorted_entries = sorted(
        entries,
        key=lambda e: (
            e.transaction_date or _date.max,
            e.transaction_time or "99:99",
        ),
    )
    for idx, e in enumerate(sorted_entries, start=1):
        link = f"<link href='#rec{idx}' color='blue'>{e.source_name or 'receipt'}</link>"
        table_data.append([
            Paragraph((e.merchant_name or ""), cell_style),
            e.transaction_date.isoformat() if e.transaction_date else "",
            e.transaction_time or "",
            f"{e.total_amount:.2f}" if e.total_amount is not None else "",
            e.currency_code,
            Paragraph((e.payment_method or ""), cell_style),
            Paragraph((e.category or ""), cell_style),
            Paragraph(link, cell_style),
        ])

    # Column widths as fractions of available width (sum to 1.0)
    col_fracs = [0.22, 0.12, 0.08, 0.09, 0.08, 0.14, 0.14, 0.13]
    expenses_table = Table(table_data, repeatRows=1, colWidths=[page_w*f for f in col_fracs])
    expenses_table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.25, colors.grey),
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("FONTSIZE", (0,0), (-1,-1), 8),
        ("ALIGN", (3,1), (3,-1), "RIGHT"),
        ("ALIGN", (0,0), (-1,0), "CENTER"),
    ]))
    flow.append(expenses_table)

    # Subtotals and totals
    usd_sub = sum((e.total_amount or 0.0) for e in entries if (e.currency_code or "").upper() == "USD")
    mxn_sub = sum((e.total_amount or 0.0) for e in entries if (e.currency_code or "").upper() == "MXN")
    total_usd = usd_sub + (mxn_sub / usd_to_mxn if usd_to_mxn else 0.0)
    total_mxn = mxn_sub + (usd_sub * usd_to_mxn)

    flow.append(Spacer(1, 8))
    totals = Table([
        ["Subtotal USD", f"{usd_sub:,.2f} USD", "Subtotal MXN", f"{mxn_sub:,.2f} MXN"],
        ["Total USD", f"{total_usd:,.2f} USD", "Total MXN", f"{total_mxn:,.2f} MXN"],
    ], colWidths=[0.25*page_w, 0.25*page_w, 0.25*page_w, 0.25*page_w])
    totals.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.25, colors.grey),
        ("BACKGROUND", (0,0), (-1,0), colors.whitesmoke),
    ]))
    flow.append(totals)

    # Receipts pages
    for idx, e in enumerate(sorted_entries, start=1):
        flow.append(PageBreak())
        flow.append(Paragraph(f"<a name='rec{idx}'/>Receipt {idx}: {e.source_name or ''}", styles["Heading2"]))
        if e._image_bytes:
            try:
                # Decode with PIL and re-encode as JPEG for ReportLab compatibility
                pil = PILImage.open(BytesIO(e._image_bytes))
                pil.load()
                if pil.mode in ("RGBA", "LA"):
                    bg = PILImage.new("RGB", pil.size, (255, 255, 255))
                    bg.paste(pil, mask=pil.split()[-1])
                    pil = bg
                elif pil.mode not in ("RGB", "L"):
                    pil = pil.convert("RGB")

                max_w = 7.3 * inch
                max_h = 9.0 * inch
                iw_px, ih_px = pil.size
                # scale from pixels to points to fit constraints
                scale = min(max_w / float(iw_px), max_h / float(ih_px))
                target_w = iw_px * scale
                target_h = ih_px * scale

                tmp = BytesIO()
                pil.save(tmp, format="JPEG", quality=85)
                tmp.seek(0)

                img = RLImage(tmp, width=target_w, height=target_h)
                flow.append(img)
            except Exception as ex:
                flow.append(Paragraph(f"[Unable to render image]", styles["BodyText"]))

    doc.build(flow)
    return buf.getvalue()


