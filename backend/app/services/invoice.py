import os
import io
import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from app.models.booking import Booking
from app.services.availability import utc_to_ist

INVOICE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "uploads", "invoices"))
os.makedirs(INVOICE_DIR, exist_ok=True)

def generate_invoice_pdf(booking: Booking) -> str:
    filename = f"invoice_{booking.booking_code.replace('#', '')}.pdf"
    file_path = os.path.join(INVOICE_DIR, filename)

    doc = SimpleDocTemplate(
        file_path,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'InvoiceTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1E293B')
    )
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#64748B')
    )
    h2_style = ParagraphStyle(
        'H2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#0F172A')
    )
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#334155')
    )
    bold_style = ParagraphStyle(
        'BodyBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#0F172A')
    )

    elements = []

    # Header banner
    header_data = [
        [
            Paragraph("<b>SpotMyShoot</b><br/><font color='#64748B'>India's Premier Location Marketplace</font>", title_style),
            Paragraph(f"<b>TAX INVOICE</b><br/>Invoice #: {booking.booking_code}<br/>Date: {datetime.datetime.utcnow().strftime('%d %b %Y')}<br/>Status: <b>PAID</b>", subtitle_style)
        ]
    ]
    header_table = Table(header_data, colWidths=[300, 240])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (1,0), (1,0), 'RIGHT')
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 15))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#E2E8F0'), spaceAfter=15))

    # Customer & Shoot Details
    start_ist = utc_to_ist(booking.start_datetime)
    end_ist = utc_to_ist(booking.end_datetime)

    prop_name = booking.property.name if booking.property else "Location"
    prop_addr = booking.property.address if booking.property else "Location Address"
    cust_name = booking.customer.name if booking.customer else "Creator"
    cust_email = booking.customer.email if booking.customer else ""
    cust_phone = booking.customer.phone or "N/A"

    info_data = [
        [
            Paragraph("<b>Billed To:</b>", h2_style),
            Paragraph("<b>Shoot Location Details:</b>", h2_style)
        ],
        [
            Paragraph(f"{cust_name}<br/>{cust_email}<br/>Phone: {cust_phone}", body_style),
            Paragraph(f"<b>{prop_name}</b><br/>{prop_addr}<br/>Date: {start_ist.strftime('%d %b %Y')}<br/>Timing: {start_ist.strftime('%I:%M %p')} - {end_ist.strftime('%I:%M %p')} ({booking.duration_hours} hrs)<br/>Category: {booking.shoot_category}", body_style)
        ]
    ]
    info_table = Table(info_data, colWidths=[270, 270])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8)
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 15))

    # Financial Breakdown Table
    cgst = booking.gst_amount // 2
    sgst = booking.gst_amount - cgst

    breakdown_data = [
        [Paragraph("Description", bold_style), Paragraph("Qty / Hours", bold_style), Paragraph("Rate / Hr", bold_style), Paragraph("Amount (INR)", bold_style)],
        [Paragraph(f"Location Booking: {prop_name}", body_style), Paragraph(f"{booking.duration_hours} hrs", body_style), Paragraph(f"Rs. {booking.property.hourly_price}", body_style), Paragraph(f"Rs. {booking.subtotal:,}", body_style)],
        [Paragraph("Platform Convenience & Protection Fee", body_style), Paragraph("1", body_style), Paragraph("-", body_style), Paragraph(f"Rs. {booking.platform_fee:,}", body_style)],
        [Paragraph("CGST (9%)", body_style), Paragraph("-", body_style), Paragraph("9%", body_style), Paragraph(f"Rs. {cgst:,}", body_style)],
        [Paragraph("SGST (9%)", body_style), Paragraph("-", body_style), Paragraph("9%", body_style), Paragraph(f"Rs. {sgst:,}", body_style)],
        [Paragraph("<b>Total Amount Paid (Inclusive of GST)</b>", bold_style), "", "", Paragraph(f"<b>Rs. {booking.total_amount:,}</b>", bold_style)]
    ]

    breakdown_table = Table(breakdown_data, colWidths=[240, 90, 90, 120])
    breakdown_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F8FAFC')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#1E293B')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
        ('ALIGN', (0,0), (0,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 6),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#F1F5F9'))
    ]))
    elements.append(breakdown_table)
    elements.append(Spacer(1, 20))

    # Notes & Cancellation Policy
    cancellation_text = f"Cancellation Policy: {booking.property.cancellation_policy.capitalize()} Policy applies. Refer to terms for refund eligibility."
    elements.append(Paragraph("<b>Terms & Conditions:</b>", h2_style))
    elements.append(Paragraph(f"1. {cancellation_text}<br/>2. Overtime will be billed directly by the property owner at 1.5x hourly rate.<br/>3. This invoice is digitally generated and valid without a physical signature.<br/>4. SpotMyShoot acts as a marketplace facilitator connecting creators and property owners.", subtitle_style))

    doc.build(elements)
    return file_path
