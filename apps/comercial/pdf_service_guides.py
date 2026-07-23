"""Generación de tickets y comprobantes PDF por tipo de servicio (E/M/D/C)."""
import decimal
import io
import os
from datetime import datetime, timedelta

from django.http import HttpResponse
from rapidovip import settings
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm, inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from apps.sales.format_to_dates import utc_to_local
from apps.sales.models import Order, OrderAction, PAYMENT_METHOD_CHOICES
from apps.sales.number_to_letters import numero_a_moneda


def _pdf_assets():
    from .views_PDF import styles
    return styles


def _ensure_brand_font():
    import reportlab.rl_config
    reportlab.rl_config.TTFSearchPath.append(str(settings.BASE_DIR) + '/static/fonts')
    for name, filename in (
        ('bauh', 'BAUHS93.ttf'),
        ('Square', 'square-721-condensed-bt.ttf'),
        ('Square-Bold', 'sqr721bc.ttf'),
        ('Newgot', 'newgotbc.ttf'),
    ):
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, filename))


def _brand_logo(max_width, max_height):
    """Logo de la empresa con proporción real; None si no existe el archivo."""
    logo_path = os.path.join(str(settings.BASE_DIR), 'static', 'assets', 'rapidovip_logo.png')
    if not os.path.exists(logo_path):
        return None
    img = Image(logo_path)
    natural_w = float(img.imageWidth or 1)
    natural_h = float(img.imageHeight or 1)
    aspect = natural_h / natural_w
    draw_w = float(max_width)
    draw_h = draw_w * aspect
    if draw_h > float(max_height):
        draw_h = float(max_height)
        draw_w = draw_h / aspect if aspect else float(max_width)
    img.drawWidth = draw_w
    img.drawHeight = draw_h
    img.hAlign = 'CENTER'
    return img


def _qr_code(data):
    widget = qr.QrCodeWidget(data)
    bounds = widget.getBounds()
    width = bounds[2] - bounds[0]
    height = bounds[3] - bounds[1]
    drawing = Drawing(
        4.8 * cm, 4.8 * cm, transform=[4.8 * cm / width, 0, 0, 4.8 * cm / height, 0, 0])
    drawing.add(widget)
    return drawing


THERMAL_WT = 2.83 * inch - 4 * 0.05 * inch
THERMAL_PAGE = (2.83 * inch, 11.6 * inch)
# Ancho útil real del frame de boleta: página - márgenes (0.05 + 0.055) - padding
# interno del Frame (6 pt por lado). Así las tablas ocupan el mismo ancho que los
# párrafos (remitente/destinatario).
BILL_WT = 3.14961 * inch - 0.105 * inch - 12

SERVICE_TITLES = {
    'E': 'ORDEN DE SERVICIO',
}


def _local_styles():
    """Estilos compactos usando Newgot (solo negro)."""
    return {
        'enterprise': ParagraphStyle(
            name='SvcEnterprise',
            alignment=TA_CENTER,
            leading=14,
            fontName='Newgot',
            fontSize=14,
            spaceBefore=1,
            spaceAfter=1,
            textColor=colors.black,
        ),
        'brand_title': ParagraphStyle(
            name='SvcBrandTitle',
            alignment=TA_CENTER,
            leading=42,
            fontName='bauh',
            fontSize=52,
            spaceBefore=8,
            spaceAfter=8,
            textColor=colors.black,
        ),
        'center': ParagraphStyle(
            name='SvcCenter',
            alignment=TA_CENTER,
            leading=7,
            fontName='Newgot',
            fontSize=8,
            spaceBefore=0,
            spaceAfter=0,
            textColor=colors.black,
        ),
        'center_small': ParagraphStyle(
            name='SvcCenterSmall',
            alignment=TA_CENTER,
            leading=6,
            fontName='Newgot',
            fontSize=7,
            spaceBefore=0,
            spaceAfter=0,
            textColor=colors.black,
        ),
        'left': ParagraphStyle(
            name='SvcLeft',
            alignment=TA_LEFT,
            leading=7,
            fontName='Newgot',
            fontSize=8,
            spaceBefore=0,
            spaceAfter=0,
            textColor=colors.black,
        ),
        'left_pad': ParagraphStyle(
            name='SvcLeftPad',
            alignment=TA_LEFT,
            leading=8,
            fontName='Newgot',
            fontSize=8,
            spaceBefore=1,
            spaceAfter=1,
            leftIndent=2,
            textColor=colors.black,
        ),
        'justify': ParagraphStyle(
            name='SvcJustify',
            alignment=TA_JUSTIFY,
            leading=7,
            fontName='Newgot',
            fontSize=8,
            spaceBefore=0,
            spaceAfter=0,
            textColor=colors.black,
        ),
        'value': ParagraphStyle(
            name='SvcValue',
            alignment=TA_LEFT,
            leading=7,
            fontName='Square',
            fontSize=8,
            spaceBefore=0,
            spaceAfter=0,
            textColor=colors.black,
        ),
        'desc': ParagraphStyle(
            name='SvcDesc',
            alignment=TA_JUSTIFY,
            leading=7,
            fontName='Newgot',
            fontSize=9,
            spaceBefore=0,
            spaceAfter=0,
            textColor=colors.black,
        ),
        'docno': ParagraphStyle(
            name='SvcDocNo',
            alignment=TA_CENTER,
            leading=9,
            fontName='Newgot',
            fontSize=11,
            spaceBefore=1,
            spaceAfter=1,
            textColor=colors.black,
        ),
        'docname': ParagraphStyle(
            name='SvcDocName',
            alignment=TA_CENTER,
            leading=7,
            fontName='Newgot',
            fontSize=8,
            spaceBefore=0,
            spaceAfter=0,
            textColor=colors.black,
        ),
        'tiny': ParagraphStyle(
            name='SvcTiny',
            alignment=TA_JUSTIFY,
            leading=6,
            fontName='Newgot',
            fontSize=6,
            spaceBefore=0,
            spaceAfter=0,
            textColor=colors.black,
        ),
        'terms_body': ParagraphStyle(
            name='SvcTermsBody',
            alignment=TA_JUSTIFY,
            leading=6,
            fontName='Square',
            fontSize=6,
            spaceBefore=0,
            spaceAfter=0,
            textColor=colors.black,
        ),
        'terms_title': ParagraphStyle(
            name='SvcTermsTitle',
            alignment=TA_CENTER,
            leading=7,
            fontName='Newgot',
            fontSize=6,
            spaceBefore=0,
            spaceAfter=2,
            textColor=colors.black,
        ),
        'right': ParagraphStyle(
            name='SvcRight',
            alignment=TA_RIGHT,
            leading=7,
            fontName='Square',
            fontSize=8,
            spaceBefore=0,
            spaceAfter=0,
            textColor=colors.black,
        ),
    }


def _mix(label, value, value_font='Square'):
    """
    Texto fijo en Newgot, valor dinámico en otra fuente (por defecto Square).
    """
    label = (label or '').upper()
    v = '' if value is None else str(value).strip()
    v = v.upper()
    return Paragraph(
        f'<font name="Newgot">{label}</font> <font name="{value_font}">{v}</font>',
        _local_styles()['left'],
    )


def _meta_two_cols(order_obj, width):
    """
    Bloque en 2 columnas:
    CÓDIGO ...     NRO ORDEN ...
    FECHA ...      HORA ...
    SUCURSAL ...   ATENDIDO ...
    """
    date_str, time_str = _order_datetime(order_obj)
    left1 = _mix('CÓDIGO:', order_obj.code_track or '-')
    right1 = _mix('NRO ORDEN:', _service_order_number(order_obj))
    left2 = _mix('FECHA:', date_str)
    right2 = _mix('HORA:', time_str)
    left3 = _mix('SUCURSAL:', order_obj.subsidiary.name if order_obj.subsidiary else '-')
    right3 = _mix('ATENDIDO:', order_obj.user.username if order_obj.user else '-')

    tbl = Table(
        [[left1, right1], [left2, right2], [left3, right3]],
        colWidths=[width * 0.5, width * 0.5],
    )
    tbl.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    return tbl


def _meta_encomienda(order_obj, width):
    """Bloque de metadatos estilo comprobante: fecha, hora, atendido y sede."""
    s = _local_styles()
    date_str, time_str = _order_datetime(order_obj)
    attended = (order_obj.user.username if order_obj.user else '-').upper()
    subsidiary = (order_obj.subsidiary.name if order_obj.subsidiary else '-').upper()
    pad = TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ])
    row1 = Table([[_mix('FECHA DE EMISIÓN:', date_str)]], colWidths=[width])
    row2 = Table([[_mix('HORA EMISIÓN:', time_str)]], colWidths=[width])
    sede = Paragraph(
        f'<font name="Newgot">SEDE</font> <font name="Square">{subsidiary}</font>',
        s['right'],
    )
    row3 = Table(
        [[_mix('ATENDIDO POR:', attended), sede]],
        colWidths=[width * 0.58, width * 0.42],
    )
    for tbl in (row1, row2, row3):
        tbl.setStyle(pad)
    rows = [row1, row2, row3]
    if order_obj.code_track:
        row4 = Table([[_mix('CÓDIGO:', order_obj.code_track)]], colWidths=[width])
        row4.setStyle(pad)
        rows.append(row4)
    return rows


def _service_order_number(order_obj):
    """Número de orden de servicio (serie-correlativo); todas las encomiendas lo llevan."""
    if order_obj.order_serial and order_obj.order_correlative:
        return f'{order_obj.order_serial}-{order_obj.order_correlative}'
    return str(order_obj.id)


def _header_encomienda(order_obj, title, width=None, top_gap=None):
    """Encabezado de encomienda al estilo comprobante térmico."""
    _ensure_brand_font()
    wt = width or THERMAL_WT
    s = _local_styles()
    brand = _company_short_name(order_obj)
    logo = _brand_logo(wt * 0.55, 0.6 * inch)
    # Nombre/dirección de la empresa sin negrita; solo el RUC va en negrita
    company_lines = _company_block(order_obj).split('\n')
    ruc_line = (
        company_lines.pop()
        if company_lines and company_lines[-1].upper().startswith('RUC')
        else None
    )
    company_flowables = [
        Paragraph(
            '<font name="Square">' + '<br />'.join(company_lines) + '</font>',
            s['center_small'],
        ),
    ]
    if ruc_line:
        company_flowables.extend([
            Spacer(2, 3),
            Paragraph(ruc_line, s['center_small']),
        ])
    elements = [
        Spacer(1, top_gap) if top_gap is not None else Spacer(-12, -12),
        logo if logo else Paragraph(brand.upper(), s['enterprise']),
        Spacer(4, 4),
        *company_flowables,
        Spacer(4, 4),
        _separator(wt),
        Spacer(4, 4),
        Paragraph(title, s['docname']),
        Paragraph(
            (
                f'<b>N° ORDEN DE SERVICIO: {_service_order_number(order_obj)}</b>'
                if order_obj.type_document == 'T'
                else f'<b>SERIE: {order_obj.serial} - {order_obj.correlative_sale}</b>'
            ),
            s['docno'],
        ),
    ]
    if order_obj.type_document != 'T' and order_obj.order_correlative:
        elements.append(
            Paragraph(f'ORDEN DE SERVICIO: {_service_order_number(order_obj)}', s['docno'])
        )
    elements.extend([
        Spacer(4, 4),
        _separator(wt),
        Spacer(4, 4),
    ])
    elements.extend(_meta_encomienda(order_obj, wt))
    return elements


def _get_encomienda(order_obj):
    return getattr(order_obj, 'encomienda', None)


def _route_block_encomienda(order_obj, width=None):
    """Bloque de ruta con destino resaltado y condición de pago en negrita."""
    s = _local_styles()
    wt = width or THERMAL_WT
    encomienda = _get_encomienda(order_obj)
    origin = encomienda.office_origin.short_name \
        if encomienda and encomienda.office_origin_id else '-'
    if encomienda and encomienda.is_reparto:
        # En OS: DESTINO = solo la dirección de reparto (sin ubigeo ni etiqueta DIR. REP.)
        dest = (encomienda.address_delivery or '').strip() or '-'
    else:
        dest = encomienda.office_destination.short_name \
            if encomienda and encomienda.office_destination_id else '-'
    payment = order_obj.get_way_to_pay_display()
    service = encomienda.get_type_guide_display() if encomienda else 'ENCOMIENDA'

    lines = [
        _mix('TIPO:', 'ENCOMIENDA'),
        _mix('ORIGEN:', origin),
        Paragraph(
            f'<font name="Newgot">DESTINO:</font> '
            f'<font name="Square-Bold" size="12">{dest.upper()}</font>',
            s['left'],
        ),
        Paragraph(
            f'<font name="Newgot">COND. PAGO:</font> '
            f'<font name="Square-Bold">{payment.upper()}</font>',
            s['left'],
        ),
        _mix('SERVICIO:', service),
    ]

    data = [[line] for line in lines]
    tbl = Table(data, colWidths=[wt])
    tbl.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        # Separa la fila de DESTINO (fuente grande) de la siguiente
        ('BOTTOMPADDING', (0, 2), (0, 2), 9),
    ]))
    return tbl


def _encomienda_shipping_block(order_obj, width=None, include_client=False):
    """Datos de envío: cliente (opcional), remitente, destinatarios y ruta."""
    wt = width or THERMAL_WT
    s = _local_styles()
    # Alinea los párrafos con las tablas (2pt) y separa un poco las líneas
    s['left'] = s['left_pad']
    elements = []

    sender = OrderAction.objects.filter(order=order_obj, type='R').first()

    if include_client and sender and sender.client:
        doc = sender.client.clienttype_set.first()
        # Razón social y dirección en Paragraph para que hagan salto de línea
        # y no se pierdan cuando el texto es largo (p. ej. facturas)
        name_tbl = _kv_table(
            [('CLIENTE', Paragraph((sender.client.names or '').upper(), s['value']))],
            label_pct=28, width=wt,
        )
        client_rows = [
            (doc.document_type.short_description if doc else 'RUC', doc.document_number if doc else ''),
        ]
        if sender.client.phone:
            client_rows.append(('TELÉFONO', sender.client.phone))
        addr = sender.client.clientaddress_set.first()
        if addr and addr.address:
            client_rows.append(('DIRECCIÓN', Paragraph(addr.address.upper(), s['value'])))
        client_tbl = _kv_table(client_rows, label_pct=28, width=wt)
        if name_tbl:
            # Separa el nombre/razón social del número de documento
            elements.extend([name_tbl, Spacer(1, 3)])
        if client_tbl:
            elements.append(client_tbl)
        if name_tbl or client_tbl:
            elements.extend([Spacer(2, 2), _separator(wt)])

    elements.extend([_section('Datos de envío'), _separator(wt), Spacer(2, 2)])

    if sender and sender.client:
        doc_type = sender.client.clienttype_set.first()
        doc_label = doc_type.document_type.short_description if doc_type else 'DOC'
        doc_num = doc_type.document_number if doc_type else ''
        elements.append(Paragraph('<font name="Newgot">REMITENTE:</font>', s['left']))
        elements.append(Paragraph(f'<font name="Square">{sender.client.names.upper()}</font>', s['left']))
        if doc_num:
            elements.append(Paragraph(
                f'<font name="Newgot">{doc_label}:</font> <font name="Square">{doc_num}</font>',
                s['left'],
            ))
        if sender.client.phone:
            elements.append(Paragraph(
                f'<font name="Newgot">TELÉFONO:</font> <font name="Square">{sender.client.phone}</font>',
                s['left'],
            ))
    elif sender and sender.order_addressee:
        elements.append(Paragraph('<font name="Newgot">REMITENTE:</font>', s['left']))
        elements.append(Paragraph(
            f'<font name="Square">{sender.order_addressee.names.upper()}</font>',
            s['left'],
        ))
        if sender.order_addressee.phone:
            elements.append(Paragraph(
                f'<font name="Newgot">TELÉFONO:</font> <font name="Square">{sender.order_addressee.phone}</font>',
                s['left'],
            ))

    recipients = OrderAction.objects.filter(order=order_obj, type='D')
    if recipients.exists():
        elements.extend([Spacer(2, 2), _separator(wt), Spacer(2, 2)])
        elements.append(Paragraph('<font name="Newgot">DESTINATARIO(S)</font>', s['left']))
        elements.append(Spacer(2, 2))
        for rec in recipients:
            if rec.client:
                doc = rec.client.clienttype_set.first()
                elements.append(Paragraph(
                    f'<font name="Newgot">NOMBRES:</font> <font name="Square">{rec.client.names.upper()}</font>',
                    s['left'],
                ))
                if rec.client.phone:
                    elements.append(Paragraph(
                        f'<font name="Newgot">CEL:</font> <font name="Square">{rec.client.phone}</font>',
                        s['left'],
                    ))
                if doc and doc.document_number:
                    elements.append(Paragraph(
                        f'<font name="Newgot">{doc.document_type.short_description}:</font> '
                        f'<font name="Square">{doc.document_number}</font>',
                        s['left'],
                    ))
            elif rec.order_addressee:
                elements.append(Paragraph(
                    f'<font name="Newgot">NOMBRES:</font> '
                    f'<font name="Square">{rec.order_addressee.names.upper()}</font>',
                    s['left'],
                ))
                if rec.order_addressee.phone:
                    elements.append(Paragraph(
                        f'<font name="Newgot">CEL:</font> <font name="Square">{rec.order_addressee.phone}</font>',
                        s['left'],
                    ))

    elements.extend([Spacer(2, 2), _separator(wt), Spacer(2, 2), _route_block_encomienda(order_obj, width=wt)])
    return elements


def _encomienda_details_table(order_obj, use_base=False, width=None):
    """Tabla de detalle estilo comprobante: DESCRIPCIÓN | CANT. | TOTAL."""
    s = _local_styles()
    wt = width or THERMAL_WT
    col_w = [wt * 0.58, wt * 0.12, wt * 0.30]
    head = Table([('DESCRIPCIÓN', 'CANT.', 'TOTAL')], colWidths=col_w)
    head.setStyle(TableStyle(ENCOMIENDA_DETAIL_HEAD_STYLE))

    detail_rows = []
    for detail in order_obj.orderdetail_set.all():
        qty = str(decimal.Decimal(round(detail.quantity)))
        desc_text = (detail.description or '').upper()
        desc = Paragraph(desc_text, s['value']) if len(desc_text) > 32 else desc_text
        if use_base:
            base_total = detail.quantity * detail.price_unit
            amount_val = base_total / decimal.Decimal('1.18')
            amount = str(round(amount_val, 2))
        else:
            amount = str(round(detail.amount, 2))
        detail_rows.append((desc, qty, amount))

    if not detail_rows:
        return None

    body = Table(detail_rows, colWidths=col_w)
    body.setStyle(TableStyle(ENCOMIENDA_DETAIL_ROW_STYLE))
    return [head, Spacer(0, 0), body]


def _bill_amounts(order_obj):
    """Calcula subtotal (gravada), IGV y total de la boleta/factura."""
    sub_total = decimal.Decimal('0')
    total = decimal.Decimal('0')
    igv_total = decimal.Decimal('0')
    for detail in order_obj.orderdetail_set.all():
        base_total = detail.quantity * detail.price_unit
        base_amount = base_total / decimal.Decimal('1.18')
        igv = base_total - base_amount
        sub_total += base_amount
        total += base_total
        igv_total += igv

    if total == 0 and order_obj.total:
        total = decimal.Decimal(str(order_obj.total))
        sub_total = total / decimal.Decimal('1.18')
        igv_total = total - sub_total
    return sub_total, igv_total, total


def _bill_totals_table(order_obj, width=None):
    """Totales de boleta/factura (sin OP. INAFECTA / OP. EXONERADA)."""
    wt = width or BILL_WT
    sub_total, igv_total, total = _bill_amounts(order_obj)
    rows = [
        ('OP. GRAVADA', sub_total),
        ('I.G.V. (18.00)', igv_total),
        ('IMPORTE TOTAL', total),
    ]
    data = [(label, '', 'S/', str(round(value, 2))) for label, value in rows]
    tbl = Table(data, colWidths=[wt * 0.61, wt * 0.02, wt * 0.12, wt * 0.25])
    tbl.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -2), 'Helvetica'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGNMENT', (0, 0), (-1, -1), 'RIGHT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
    ]))
    return tbl, total


SECTION_STYLE = ParagraphStyle(
    name='PdfSection',
    alignment=TA_CENTER,
    leading=7,
    fontName='Newgot',
    fontSize=8,
    spaceBefore=2,
    spaceAfter=2,
    textColor=colors.black,
)

KV_STYLE = [
    ('FONTNAME', (0, 0), (-1, -1), 'Square'),
    ('FONTSIZE', (0, 0), (-1, -1), 8),
    ('LEFTPADDING', (0, 0), (0, -1), 2),
    ('LEFTPADDING', (1, 0), (1, -1), 4),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ('TOPPADDING', (0, 0), (-1, -1), 0),
    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ('FONTNAME', (0, 0), (0, -1), 'Newgot'),   # etiquetas fijas
    ('FONTNAME', (1, 0), (1, -1), 'Square'),  # valores dinámicos sin negrita
    ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
]

DETAIL_HEAD_STYLE = [
    ('FONTNAME', (0, 0), (-1, -1), 'Newgot'),
    ('FONTSIZE', (0, 0), (-1, -1), 8),
    ('BACKGROUND', (0, 0), (-1, -1), colors.white),
    ('LEFTPADDING', (0, 0), (-1, -1), 3),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ('TOPPADDING', (0, 0), (-1, -1), 2),
    ('ALIGNMENT', (0, 0), (0, -1), 'CENTER'),
    ('ALIGNMENT', (1, 0), (1, -1), 'LEFT'),
    ('ALIGNMENT', (2, 0), (2, -1), 'RIGHT'),
]

DETAIL_ROW_STYLE = [
    ('FONTNAME', (0, 0), (-1, -1), 'Square'),
    ('FONTSIZE', (0, 0), (-1, -1), 8),
    ('LEFTPADDING', (0, 0), (-1, -1), 3),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
    ('TOPPADDING', (0, 0), (-1, -1), 1),
    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ('ALIGNMENT', (0, 0), (0, -1), 'CENTER'),
    ('ALIGNMENT', (1, 0), (1, -1), 'LEFT'),
    ('ALIGNMENT', (2, 0), (2, -1), 'RIGHT'),
]

ENCOMIENDA_DETAIL_HEAD_STYLE = [
    ('FONTNAME', (0, 0), (-1, -1), 'Newgot'),
    ('FONTSIZE', (0, 0), (-1, -1), 8),
    ('LEFTPADDING', (0, 0), (-1, -1), 2),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ('TOPPADDING', (0, 0), (-1, -1), 2),
    ('ALIGNMENT', (0, 0), (0, -1), 'LEFT'),
    ('ALIGNMENT', (1, 0), (1, -1), 'CENTER'),
    ('ALIGNMENT', (2, 0), (2, -1), 'RIGHT'),
]

ENCOMIENDA_DETAIL_ROW_STYLE = [
    ('FONTNAME', (0, 0), (-1, -1), 'Square'),
    ('FONTSIZE', (0, 0), (-1, -1), 8),
    ('LEFTPADDING', (0, 0), (-1, -1), 2),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
    ('TOPPADDING', (0, 0), (-1, -1), 1),
    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ('ALIGNMENT', (0, 0), (0, -1), 'LEFT'),
    ('ALIGNMENT', (1, 0), (1, -1), 'CENTER'),
    ('ALIGNMENT', (2, 0), (2, -1), 'RIGHT'),
]

TOTAL_STYLE = [
    ('FONTNAME', (0, 0), (-1, -1), 'Square'),
    ('FONTSIZE', (0, 0), (-1, -1), 8),
    ('ALIGNMENT', (2, 0), (3, -1), 'RIGHT'),
    ('LEFTPADDING', (0, 0), (-1, -1), 2),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
    ('TOPPADDING', (0, 0), (-1, -1), 1),
]

INVENTORY_HEAD_STYLE = [
    ('FONTNAME', (0, 0), (-1, -1), 'Newgot'),
    ('FONTSIZE', (0, 0), (-1, -1), 9),
    ('LEFTPADDING', (0, 0), (-1, -1), 3),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ('TOPPADDING', (0, 0), (-1, -1), 2),
    ('ALIGNMENT', (0, 0), (0, -1), 'CENTER'),
    ('ALIGNMENT', (1, 0), (1, -1), 'CENTER'),
]

INVENTORY_ROW_STYLE = [
    ('FONTNAME', (0, 0), (-1, -1), 'Square'),
    ('FONTSIZE', (0, 0), (-1, -1), 9),
    ('LEFTPADDING', (0, 0), (-1, -1), 3),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
    ('TOPPADDING', (0, 0), (-1, -1), 1),
    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ('ALIGNMENT', (0, 0), (0, -1), 'CENTER'),
    ('ALIGNMENT', (1, 0), (1, -1), 'LEFT'),
]

SOFT_LINE = colors.HexColor('#d1d5db')


def _separator(width=None):
    wt = width or THERMAL_WT
    line = Table([['']], colWidths=[wt], rowHeights=[1])
    line.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (-1, -1), 0.6, SOFT_LINE),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    return line


def _section(title):
    return Paragraph(title.upper(), SECTION_STYLE)


def _company_block(order_obj):
    company = getattr(order_obj, 'company', None)
    if not company:
        return 'EMPRESA'
    lines = [(company.business_name or company.short_name or 'EMPRESA').strip()]
    if company.address:
        lines.append(company.address.strip())
    if company.phone:
        lines.append(f'TEL: {company.phone.strip()}')
    if company.ruc:
        lines.append(f'RUC: {company.ruc}')
    return '\n'.join(lines)


def _company_short_name(order_obj):
    company = getattr(order_obj, 'company', None)
    if not company:
        return 'EMPRESA'
    return (company.short_name or company.business_name or 'EMPRESA').strip()


def _thanks_message(order_obj):
    brand = _company_short_name(order_obj).upper()
    return f'¡Gracias por enviar con {brand}!'


def _property_label(code):
    return code or '-'


def _payment_label(code):
    return dict(PAYMENT_METHOD_CHOICES).get(code or '', code or '-')


def _order_datetime(order_obj):
    local_dt = utc_to_local(order_obj.create_at)
    return local_dt.strftime('%d/%m/%Y'), local_dt.strftime('%I:%M:%S %p')


def _kv_table(rows, label_pct=30, width=None):
    s = _local_styles()
    wt = width or THERMAL_WT
    label_w = wt * label_pct / 100
    value_w = wt - label_w
    data = []
    for label, value in rows:
        if value is None:
            continue
        if isinstance(value, str) and not str(value).strip():
            continue
        if isinstance(value, Paragraph):
            val = value
        elif isinstance(value, str):
            val = Paragraph(value.upper(), s['value']) if len(value) > 45 else value.upper()
        else:
            val = str(value).upper()
        data.append((label.upper(), val))
    if not data:
        return None
    tbl = Table(data, colWidths=[label_w, value_w])
    tbl.setStyle(TableStyle(KV_STYLE))
    return tbl


def _header_block(order_obj, title):
    s = _local_styles()
    brand = _company_short_name(order_obj)
    elements = [
        Spacer(-12, -12),
        Paragraph(brand.upper(), s['enterprise']),
        Paragraph(_company_block(order_obj).replace('\n', '<br />'), s['center_small']),
        Spacer(2, 2),
        Paragraph(title, s['docname']),
        Paragraph(f'SERIE: {order_obj.serial} - {order_obj.correlative_sale}', s['docno']),
        Spacer(5, 5),
        _separator(), Spacer(5, 5), _meta_two_cols(order_obj, THERMAL_WT),
    ]
    return elements


def _header_service_block(order_obj, title):
    """Encabezado de servicio con marca dinámica y tipografía compacta."""
    _ensure_brand_font()
    s = _local_styles()
    short_name = _company_short_name(order_obj).upper()
    elements = [
        Spacer(1, 8),
        Paragraph(short_name, s['enterprise']),
        Spacer(2, 2),
        Paragraph(_company_block(order_obj).replace('\n', '<br />'), s['center_small']),
        Spacer(2, 2),
        Paragraph(title, s['docname']),
        Paragraph(f'SERIE: {order_obj.serial} - {order_obj.correlative_sale}', s['docno']),
        Spacer(5, 5),
        _separator(),
        Spacer(5, 5),
        _meta_two_cols(order_obj, THERMAL_WT),
    ]
    return elements


def _details_table(order_obj, qty_header='CNT.', desc_header='ARTÍCULO', amount_header='IMPORTE',
                   use_base=False, width=None):
    s = _local_styles()
    wt = width or THERMAL_WT
    col_w = [wt * 0.12, wt * 0.55, wt * 0.33]
    head = Table([(qty_header, desc_header, amount_header)], colWidths=col_w)
    head.setStyle(TableStyle(DETAIL_HEAD_STYLE))

    detail_rows = []
    for detail in order_obj.orderdetail_set.all():
        qty = str(decimal.Decimal(round(detail.quantity)))
        desc_text = (detail.description or '').upper()
        desc = Paragraph(desc_text, s['value']) if len(desc_text) > 35 else desc_text
        if use_base:
            base_total = detail.quantity * detail.price_unit
            amount_val = base_total / decimal.Decimal('1.18')
            amount = str(round(amount_val, 2))
        else:
            amount = str(round(detail.amount, 2))
        detail_rows.append((qty, desc, amount))

    if not detail_rows:
        return None

    body = Table(detail_rows, colWidths=col_w)
    body.setStyle(TableStyle(DETAIL_ROW_STYLE))
    return [head, Spacer(0, 0), body]


def _inventory_table(order_obj, width=None):
    """Inventario mudanza: solo cantidad y artículo (sin importe por línea)."""
    s = _local_styles()
    wt = width or THERMAL_WT
    col_w = [wt * 0.18, wt * 0.82]
    head = Table([('CANTIDAD', 'ARTÍCULO')], colWidths=col_w)
    head.setStyle(TableStyle(INVENTORY_HEAD_STYLE))

    inv_rows = []
    for detail in order_obj.orderdetail_set.all():
        qty = str(decimal.Decimal(round(detail.quantity)))
        desc_text = (detail.description or '').upper()
        desc = Paragraph(desc_text, s['value']) if len(desc_text) > 40 else desc_text
        inv_rows.append((qty, desc))

    if not inv_rows:
        return None

    body = Table(inv_rows, colWidths=col_w)
    body.setStyle(TableStyle(INVENTORY_ROW_STYLE))
    return [head, Spacer(0, 0), body]


def _totals_table(order_obj, show_igv=False, width=None, font_size=8):
    wt = width or THERMAL_WT
    sub_total = decimal.Decimal('0')
    total = decimal.Decimal('0')
    igv_total = decimal.Decimal('0')
    for detail in order_obj.orderdetail_set.all():
        base_total = detail.quantity * detail.price_unit
        base_amount = base_total / decimal.Decimal('1.18')
        igv = base_total - base_amount
        sub_total += base_amount
        total += base_total
        igv_total += igv

    if total == 0 and order_obj.total:
        total = decimal.Decimal(str(order_obj.total))
        sub_total = total

    rows = []
    if show_igv:
        rows.extend([
            ('OP. GRAVADA', 'S/', str(round(sub_total, 2))),
            ('I.G.V. 18%', 'S/', str(round(igv_total, 2))),
        ])
    rows.append(('TOTAL', 'S/', str(round(total, 2))))

    if not show_igv:
        tbl = Table([['', f'TOTAL S/ {round(total, 2)}']], colWidths=[wt * 0.35, wt * 0.65])
        tbl.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Square'),
            ('FONTSIZE', (0, 0), (-1, -1), font_size),
            ('ALIGNMENT', (1, 0), (1, -1), 'RIGHT'),
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
        ]))
        return tbl, total

    data = [(label, '', symbol, value) for label, symbol, value in rows]
    tbl = Table(data, colWidths=[wt * 0.55, wt * 0.08, wt * 0.12, wt * 0.25])
    total_style = list(TOTAL_STYLE)
    total_style[1] = ('FONTSIZE', (0, 0), (-1, -1), font_size)
    tbl.setStyle(TableStyle(total_style))
    return tbl, total


def _bill_client_doc_sunat_code(client_obj):
    """Código SUNAT del documento del cliente: 6=RUC, 1=DNI, etc."""
    if not client_obj:
        return ''
    client_type = client_obj.clienttype_set.select_related('document_type').first()
    if not client_type:
        return ''
    doc = client_type.document_type
    raw = (getattr(doc, 'sunat_code', None) or getattr(doc, 'id', None) or '')
    raw = str(raw).strip()
    if not raw:
        return ''
    try:
        return str(int(raw))
    except (TypeError, ValueError):
        return raw.lstrip('0') or raw


def _bill_qr_payload(order_obj, igv_total, total):
    """
    QR SUNAT:
    RUC|01/03|serie|correlativo|igv|total|fecha|tipo_doc_cliente||
    """
    company = getattr(order_obj, 'company', None)
    ruc = (company.ruc if company and company.ruc else '') or ''
    order_bill = getattr(order_obj, 'orderbill', None)
    bill_type = str(getattr(order_bill, 'type', '') or '')
    if bill_type in ('1', 'F', '01') or order_obj.type_document == 'F':
        tipo_cpe = '01'
    else:
        tipo_cpe = '03'
    serie = order_obj.serial or getattr(order_bill, 'serial', None) or ''
    correlativo = order_obj.correlative_sale or ''
    if not correlativo and getattr(order_bill, 'n_receipt', None):
        correlativo = str(order_bill.n_receipt)
    bill_created_at = getattr(order_bill, 'created_at', None)
    local_dt = utc_to_local(bill_created_at or order_obj.create_at)
    fecha_qr = local_dt.strftime('%Y-%m-%d')
    client_obj = _bill_client_obj(order_obj)
    tipo_doc_cliente = _bill_client_doc_sunat_code(client_obj)
    return '|'.join([
        str(ruc),
        tipo_cpe,
        str(serie),
        str(correlativo),
        f'{round(igv_total, 2):.2f}',
        f'{round(total, 2):.2f}',
        fecha_qr,
        str(tipo_doc_cliente),
        '',
        '',
    ])


def _bill_client_obj(order_obj):
    # En cobros realizados en destino, Order.client guarda al destinatario facturado.
    billing_client = getattr(order_obj, 'client', None)
    if billing_client:
        return billing_client
    sender = OrderAction.objects.filter(order=order_obj, type='R').select_related('client').first()
    if sender and sender.client_id:
        return sender.client
    return None


def _qr_block(order_obj, width=None, igv_total=None, total=None):
    wt = width or THERMAL_WT
    if igv_total is None or total is None:
        _, igv_total, total = _bill_amounts(order_obj)
    datatable = _bill_qr_payload(order_obj, igv_total, total)
    tbl = Table([(_qr_code(datatable), '')], colWidths=[wt * 0.99, wt * 0.01])
    tbl.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGNMENT', (0, 0), (0, -1), 'CENTER'),
        ('SPAN', (0, 0), (1, 0)),
    ]))
    return tbl


def _footer_terms_flowables(service_type='E'):
    _ensure_brand_font()
    s = _local_styles()
    if service_type == 'M':
        return [
            Paragraph('CONDICIONES DEL SERVICIO DE MUDANZA:', s['terms_title']),
            Paragraph(
                '1. El inventario es referencial y debe ser verificado al inicio del servicio.<br/>'
                '2. Objetos frágiles o de valor deben ser declarados previamente.<br/>'
                '3. La empresa no se responsabiliza por daños no reportados antes del traslado.',
                s['terms_body'],
            ),
        ]
    if service_type == 'E':
        text = (
            'CONDICIONES DE CONTRATACIÓN:<br/>'
            '• El remitente declara que la información y el contenido de la encomienda son veraces y de libre transporte.<br/>'
            '• La empresa no se responsabiliza por objetos de valor o contenido no declarado.<br/>'
            '• La entrega se realizará al destinatario o persona autorizada, previa identificación.<br/>'
            '• La empresa no será responsable por demoras ocasionadas por caso fortuito o fuerza mayor.<br/>'
            '• Al contratar el servicio, el cliente acepta los presentes términos y condiciones.'
        )
    elif service_type == 'D':
        text = (
            'CONDICIONES DEL SERVICIO DELIVERY:<br/>'
            '1. Verifique el contenido del envío al momento de la entrega.<br/>'
            '2. Reclamos por deterioro deben reportarse el mismo día del servicio.<br/>'
            '3. La empresa no transporta sustancias prohibidas o peligrosas.'
        )
    else:
        text = (
            'CONDICIONES DEL SERVICIO DE CARGA:<br/>'
            '1. La mercancía debe estar correctamente embalada y rotulada.<br/>'
            '2. El cliente declara el contenido y peso aproximado de la carga.<br/>'
            '3. Reclamos por daños deben presentarse dentro de las 48 horas.'
        )
    return [Paragraph(text, s['terms_body'])]


def _pdf_http_response(buff, order_obj, pk, request=None, filename=None):
    response = HttpResponse(content_type='application/pdf')
    if not filename:
        filename = f'WARE[{order_obj.serial}-{order_obj.correlative_sale}].pdf'
    disposition = 'attachment' if request and request.GET.get('download') else 'inline'
    response['Content-Disposition'] = f'{disposition}; filename="{filename}"'
    tomorrow = datetime.now() + timedelta(days=1)
    tomorrow = tomorrow.replace(hour=0, minute=0, second=0)
    expires = datetime.strftime(tomorrow, '%a, %d-%b-%Y %H:%M:%S GMT')
    response.set_cookie('ware', value=pk, expires=expires)
    response.write(buff.getvalue())
    buff.close()
    return response


def _build_ticket_doc(elements, order_obj):
    buff = io.BytesIO()
    doc = SimpleDocTemplate(
        buff,
        pagesize=THERMAL_PAGE,
        rightMargin=0,
        leftMargin=0.039 * inch,
        topMargin=0,
        bottomMargin=0.039 * inch,
        title=SERVICE_TITLES.get(order_obj.service_type, 'GUÍA DE SERVICIO'),
    )
    doc.build(elements)
    return buff


def _finish_ticket(elements, order_obj, pk, service_type, total_font_size=8, request=None):
    s = _local_styles()
    total_tbl, _ = _totals_table(order_obj, font_size=total_font_size)
    elements.extend([
        Spacer(1, 1),
        total_tbl,
        Spacer(1, 1),
        *_footer_terms_flowables(service_type),
        Spacer(1, 1),
        _separator(),
        Paragraph(_thanks_message(order_obj), s['center_small']),
    ])
    buff = _build_ticket_doc(elements, order_obj)
    return _pdf_http_response(buff, order_obj, pk, request)


def build_ticket_encomienda(order_obj, pk, request=None):
    s = _local_styles()
    elements = _header_encomienda(order_obj, SERVICE_TITLES['E'])
    elements.extend([Spacer(2, 2), *_encomienda_shipping_block(order_obj)])
    elements.extend([Spacer(2, 2), _separator(), Spacer(2, 2)])
    details = _encomienda_details_table(order_obj)
    if details:
        elements.extend(details)
    observation = (getattr(order_obj, 'observation', None) or '').strip()
    if observation:
        elements.extend([
            Spacer(2, 2),
            _separator(),
            Spacer(2, 2),
            Paragraph('<font name="Newgot">OBSERVACIÓN:</font>', s['left']),
            Paragraph(f'<font name="Square">{observation.upper()}</font>', s['left']),
        ])
    return _finish_ticket(elements, order_obj, pk, 'E', request=request)


def build_ticket_mudanza(order_obj, pk, request=None):
    moving = getattr(order_obj, 'moving', None)
    elements = _header_service_block(order_obj, SERVICE_TITLES['M'])

    # SPACER_ORIGEN_ANTES: espacio entre encabezado y la línea de "Origen" (ajusta el 2)
    elements.extend([
        Spacer(2, 2),
        _separator(),
        _section('Origen'),
    ])
    if moving:
        elements.append(Spacer(2, 3))  # entre título "Origen" y DIRECCIÓN (ajusta el 3)
        elements.append(_kv_table([
            ('DIRECCIÓN:', moving.origin_address),
            ('INMUEBLE:', _property_label(moving.origin_property_type)),
            ('PISOS:', str(moving.origin_floors or 0)),
        ]))

    # SPACER_ORIGEN_DESPUES: espacio entre datos de Origen y la línea de "Destino" (ajusta el 2)
    elements.append(Spacer(2, 2))
    elements.extend([_separator(), _section('Destino')])
    if moving:
        elements.append(Spacer(2, 3))  # entre título "Destino" y DIRECCIÓN (ajusta el 3)
        elements.append(_kv_table([
            ('DIRECCIÓN:', moving.destination_address),
            ('INMUEBLE:', _property_label(moving.dest_property_type)),
            ('PISOS:', str(moving.dest_floors or 0)),
        ]))
        sched = []
        if moving.service_date:
            sched.append(('FECHA:', moving.service_date.strftime('%d/%m/%Y')))
        if moving.service_time:
            sched.append(('HORA:', moving.service_time.strftime('%I:%M %p')))
        sched.append(('AYUDANTES:', str(moving.helpers_count or 0)))
        sched.append(('PAGO:', _payment_label(moving.payment_method)))
        elements.extend([Spacer(2, 2), _separator(), _section('Programación')])
        elements.append(Spacer(2, 3))  # entre título "Programación" y FECHA (ajusta el 3)
        elements.append(_kv_table(sched))

    elements.extend([Spacer(5, 2), _separator(), _section('Inventario')])
    inventory = _inventory_table(order_obj)
    if inventory:
        elements.extend(inventory)

    return _finish_ticket(elements, order_obj, pk, 'M', total_font_size=9, request=request)


def build_ticket_delivery(order_obj, pk, request=None):
    delivery = getattr(order_obj, 'delivery', None)
    elements = _header_service_block(order_obj, SERVICE_TITLES['D'])
    elements.extend([_separator(), _section('Recojo')])
    if delivery:
        elements.append(_kv_table([('DIRECCIÓN', delivery.pickup_address)]))

    elements.extend([Spacer(2, 2), _separator(), _section('Entrega')])
    if delivery:
        elements.append(_kv_table([
            ('CLIENTE', delivery.receiver_name),
            ('TELÉFONO', delivery.receiver_phone),
            ('DIRECCIÓN', delivery.delivery_address),
            ('REFERENCIA', delivery.dest_reference or '-'),
            ('PAGO', _payment_label(delivery.payment_method)),
        ]))

    elements.extend([Spacer(2, 2), _separator(), _section('Detalle del envío')])
    details = _details_table(order_obj)
    if details:
        elements.extend(details)

    return _finish_ticket(elements, order_obj, pk, 'D', request=request)


def build_ticket_carga(order_obj, pk, request=None):
    cargo = getattr(order_obj, 'cargo', None)
    elements = _header_service_block(order_obj, SERVICE_TITLES['C'])

    if cargo:
        elements.extend([_separator(), _section('Cliente')])
        elements.append(_kv_table([
            ('RUC', cargo.client_ruc),
            ('RAZÓN SOC.', cargo.client_name),
        ]))
        # Sin línea inmediatamente debajo de RUC (solo espacio)
        elements.extend([Spacer(1, 1), _section('Origen')])
        elements.append(_kv_table([
            ('DIRECCIÓN', cargo.origin_address),
            ('CONTACTO', cargo.origin_contact or '-'),
            ('TELÉFONO', cargo.origin_phone or '-'),
        ]))
        elements.extend([Spacer(1, 1), _separator(), _section('Destino')])
        elements.append(_kv_table([
            ('DIRECCIÓN', cargo.dest_address),
            ('CONTACTO', cargo.dest_contact or '-'),
            ('TELÉFONO', cargo.dest_phone or '-'),
            ('PAGO', _payment_label(cargo.payment_method)),
        ]))

    elements.extend([Spacer(2, 2), _separator(), _section('Mercancía')])
    details = _details_table(order_obj)
    if details:
        elements.extend(details)

    return _finish_ticket(elements, order_obj, pk, 'C', request=request)


def build_ticket_for_service(order_obj, pk, request=None):
    return build_ticket_encomienda(order_obj, pk, request)


def _bill_header(order_obj, doc_title):
    s = _local_styles()
    brand = _company_short_name(order_obj)
    elements = [Spacer(-20, -20), Paragraph(brand.upper(), s['enterprise']),
                Paragraph(_company_block(order_obj).replace('\n', '<br />'), s['center']), Spacer(2, 2),
                Table([['']], colWidths=[BILL_WT], rowHeights=[1], style=TableStyle([
                    ('LINEBELOW', (0, 0), (-1, -1), 0.6, SOFT_LINE),
                    ('TOPPADDING', (0, 0), (-1, -1), 0),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                    ('LEFTPADDING', (0, 0), (-1, -1), 0),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ])), Paragraph(doc_title, s['docname']),
                Paragraph(f'SERIE: {order_obj.serial} - {order_obj.correlative_sale}', s['docno']), Spacer(2, 2),
                Table([['']], colWidths=[BILL_WT], rowHeights=[1], style=TableStyle([
                    ('LINEBELOW', (0, 0), (-1, -1), 0.6, SOFT_LINE),
                    ('TOPPADDING', (0, 0), (-1, -1), 0),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                    ('LEFTPADDING', (0, 0), (-1, -1), 0),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ])), Spacer(1, 1), _meta_two_cols(order_obj, BILL_WT)]
    return elements


def _bill_helvetica_styles():
    """Estilos Helvetica exclusivos de boleta/factura encomienda."""
    return {
        'center': ParagraphStyle(
            name='BillHelvCenter', fontName='Helvetica', fontSize=8, leading=10,
            alignment=TA_CENTER, spaceBefore=0, spaceAfter=0, textColor=colors.black,
        ),
        'center_small': ParagraphStyle(
            name='BillHelvCenterSmall', fontName='Helvetica', fontSize=7, leading=9,
            alignment=TA_CENTER, spaceBefore=0, spaceAfter=0, textColor=colors.black,
        ),
        'center_bold': ParagraphStyle(
            name='BillHelvCenterBold', fontName='Helvetica-Bold', fontSize=9, leading=11,
            alignment=TA_CENTER, spaceBefore=0, spaceAfter=0, textColor=colors.black,
        ),
        'center_docno': ParagraphStyle(
            name='BillHelvDocNo', fontName='Helvetica-Bold', fontSize=11, leading=12,
            alignment=TA_CENTER, spaceBefore=1, spaceAfter=1, textColor=colors.black,
        ),
        'left': ParagraphStyle(
            name='BillHelvLeft', fontName='Helvetica', fontSize=8, leading=10,
            alignment=TA_LEFT, spaceBefore=0, spaceAfter=0, leftIndent=2, textColor=colors.black,
        ),
        'left_bold': ParagraphStyle(
            name='BillHelvLeftBold', fontName='Helvetica-Bold', fontSize=8, leading=10,
            alignment=TA_LEFT, spaceBefore=0, spaceAfter=0, leftIndent=2, textColor=colors.black,
        ),
        'detail': ParagraphStyle(
            name='BillHelvDetail', fontName='Helvetica', fontSize=7, leading=9,
            alignment=TA_LEFT, spaceBefore=0, spaceAfter=0, textColor=colors.black,
        ),
        'detail_center': ParagraphStyle(
            name='BillHelvDetailCenter', fontName='Helvetica', fontSize=7, leading=9,
            alignment=TA_CENTER, spaceBefore=0, spaceAfter=0, textColor=colors.black,
        ),
        'detail_right': ParagraphStyle(
            name='BillHelvDetailRight', fontName='Helvetica', fontSize=7, leading=9,
            alignment=TA_RIGHT, spaceBefore=0, spaceAfter=0, textColor=colors.black,
        ),
        'head': ParagraphStyle(
            name='BillHelvHead', fontName='Helvetica-Bold', fontSize=7, leading=9,
            alignment=TA_LEFT, spaceBefore=0, spaceAfter=0, textColor=colors.black,
        ),
        'head_center': ParagraphStyle(
            name='BillHelvHeadCenter', fontName='Helvetica-Bold', fontSize=7, leading=9,
            alignment=TA_CENTER, spaceBefore=0, spaceAfter=0, textColor=colors.black,
        ),
        'head_right': ParagraphStyle(
            name='BillHelvHeadRight', fontName='Helvetica-Bold', fontSize=7, leading=9,
            alignment=TA_RIGHT, spaceBefore=0, spaceAfter=0, textColor=colors.black,
        ),
    }


def _header_bill_encomienda(order_obj, title, width=None, top_gap=10):
    """Encabezado de boleta/factura (Helvetica, sin ORDEN DE SERVICIO)."""
    wt = width or BILL_WT
    s = _bill_helvetica_styles()
    brand = _company_short_name(order_obj)
    logo = _brand_logo(wt * 0.55, 0.6 * inch)
    company_lines = _company_block(order_obj).split('\n')
    ruc_line = (
        company_lines.pop()
        if company_lines and company_lines[-1].upper().startswith('RUC')
        else None
    )
    company_text = '<br />'.join(company_lines) if company_lines else brand
    company_flowables = [Paragraph(company_text, s['center_small'])]
    if ruc_line:
        company_flowables.extend([
            Spacer(2, 2),
            Paragraph(f'<b>{ruc_line}</b>', s['center_small']),
        ])
    elements = [
        Spacer(1, top_gap),
        logo if logo else Paragraph(brand.upper(), s['center_bold']),
        Spacer(4, 4),
        *company_flowables,
        Spacer(4, 4),
        _separator(wt),
        Spacer(4, 4),
        Paragraph(title, s['center_bold']),
        Paragraph(f'{order_obj.serial} - {order_obj.correlative_sale}', s['center_docno']),
        Spacer(4, 4),
        _separator(wt),
        Spacer(4, 4),
    ]
    return elements


def _bill_client_block(order_obj, width=None):
    """
    Bloque CLIENTE:
    - DNI/RUC + número
    - razón social / nombre
    - dirección (opcional)
    Todo con Paragraph.
    """
    s = _bill_helvetica_styles()
    client = _bill_client_obj(order_obj)
    elements = [Paragraph('CLIENTE', s['left_bold'])]

    doc_label = 'DOC'
    doc_number = ''
    names = ''
    address = ''
    if client:
        names = (client.names or '').strip().upper()
        client_type = client.clienttype_set.select_related('document_type').first()
        if client_type:
            if client_type.document_type_id:
                # Preferir etiqueta corta: RUC / DNI
                raw_id = str(client_type.document_type_id).strip()
                try:
                    code = int(raw_id)
                except (TypeError, ValueError):
                    code = None
                if code == 6:
                    doc_label = 'RUC'
                elif code == 1:
                    doc_label = 'DNI'
                else:
                    doc_label = (client_type.document_type.short_description or 'DOC').upper()
            doc_number = (client_type.document_number or '').strip()
        addr = client.clientaddress_set.first()
        if addr and addr.address:
            address = addr.address.strip().upper()

    elements.append(Paragraph(f'{doc_label} {doc_number}'.strip(), s['left']))
    elements.append(Paragraph(names or '-', s['left']))
    if address:
        elements.append(Paragraph(address, s['left']))
    return elements


def _bill_emission_meta_block(order_obj, width=None):
    """FECHA DE EMISION / VENC / MONEDA / IGV."""
    s = _bill_helvetica_styles()
    order_bill = getattr(order_obj, 'orderbill', None)
    bill_created_at = getattr(order_bill, 'created_at', None)
    if bill_created_at:
        date_str = utc_to_local(bill_created_at).strftime('%d/%m/%Y')
    else:
        date_str, _ = _order_datetime(order_obj)
    return [
        Paragraph(f'<b>FECHA EMISIÓN:</b> {date_str}', s['left']),
        Paragraph(f'<b>FECHA DE VENC:</b> {date_str}', s['left']),
        Paragraph('<b>MONEDA:</b> SOLES', s['left']),
        Paragraph('<b>IGV:</b> 18.00 %', s['left']),
    ]


def _bill_details_table(order_obj, width=None):
    """Detalle: [CANT.] | DESCRIPCION | P/U | TOTAL."""
    wt = width or BILL_WT
    s = _bill_helvetica_styles()
    col_w = [wt * 0.14, wt * 0.50, wt * 0.18, wt * 0.18]
    head = Table([[
        Paragraph('[CANT.]', s['head']),
        Paragraph('DESCRIPCION', s['head']),
        Paragraph('P/U', s['head_right']),
        Paragraph('TOTAL', s['head_right']),
    ]], colWidths=col_w)
    head.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 1),
        ('RIGHTPADDING', (0, 0), (-1, -1), 1),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))

    detail_rows = []
    for detail in order_obj.orderdetail_set.all():
        qty = detail.quantity or decimal.Decimal('0')
        qty_display = str(int(qty)) if qty == qty.to_integral_value() else str(round(qty, 2))
        unit_name = 'ZZ'
        if detail.unit_id and detail.unit and detail.unit.description:
            unit_name = detail.unit.description.strip().upper()
        desc = f'ZZ SERVICIO DE TRANSPORTE {qty_display} {unit_name}'
        price = str(round(detail.price_unit or 0, 2))
        amount = str(round(detail.amount or (detail.quantity * detail.price_unit), 2))
        detail_rows.append([
            Paragraph(f'[ {qty_display} ]', s['detail_center']),
            Paragraph(desc, s['detail']),
            Paragraph(price, s['detail_right']),
            Paragraph(amount, s['detail_right']),
        ])

    if not detail_rows:
        return None

    body = Table(detail_rows, colWidths=col_w)
    body.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 1),
        ('RIGHTPADDING', (0, 0), (-1, -1), 1),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
    ]))
    return [head, Spacer(0, 0), body]


def _bill_payment_label(order_obj):
    if order_obj.way_to_pay == 'C':
        return 'CONTADO'
    return (order_obj.get_way_to_pay_display() or 'CONTADO').upper().replace('AL ', '')


def build_bill_encomienda(order_obj, pk, request=None):
    s = _bill_helvetica_styles()
    order_bill = getattr(order_obj, 'orderbill', None)
    bill_type = str(getattr(order_bill, 'type', '') or '')
    if bill_type in ('1', 'F', '01') or order_obj.type_document == 'F':
        doc_title = 'FACTURA ELECTRÓNICA'
        file_label = 'FACTURA ELECTRONICA'
    else:
        doc_title = 'BOLETA DE VENTA ELECTRÓNICA'
        file_label = 'BOLETA ELECTRONICA'

    brand = _company_short_name(order_obj)
    elements = _header_bill_encomienda(order_obj, doc_title, width=BILL_WT, top_gap=10)
    elements.extend(_bill_client_block(order_obj, width=BILL_WT))
    elements.extend([Spacer(2, 3), *_bill_emission_meta_block(order_obj, width=BILL_WT)])
    elements.extend([Spacer(2, 2), _separator(BILL_WT), Spacer(2, 2)])

    details = _bill_details_table(order_obj, width=BILL_WT)
    if details:
        elements.extend(details)

    total_tbl, total = _bill_totals_table(order_obj, width=BILL_WT)
    _, igv_total, _ = _bill_amounts(order_obj)
    payment = _bill_payment_label(order_obj)
    elements.extend([
        Spacer(1, 6),
        _separator(BILL_WT),
        Spacer(1, 6),
        total_tbl,
        Spacer(1, 6),
        _separator(BILL_WT),
        Spacer(1, 6),
        Paragraph(f'<b>IMPORTE EN LETRAS:</b> {numero_a_moneda(total)}', s['left']),
        Spacer(1, 4),
        Paragraph(f'<b>FORMA DE PAGO:</b> [{payment}]', s['left']),
        Spacer(1, 7),
        Paragraph(
            'Representación impresa del comprobante electrónico. Consulte en https://www.tuf4ct.com/cpe/',
            s['center'],
        ),
        Paragraph('Emitido mediante PROVEEDOR autorizado por la SUNAT', s['center']),
        Spacer(1, 1),
        _qr_block(order_obj, width=BILL_WT, igv_total=igv_total, total=total),
    ])

    counter = max(order_obj.orderdetail_set.count(), 1)
    buff = io.BytesIO()
    doc = SimpleDocTemplate(
        buff,
        pagesize=(3.14961 * inch, 13.6 * inch + (counter * 0.13 * inch)),
        rightMargin=0.055 * inch,
        leftMargin=0.05 * inch,
        topMargin=0.039 * inch,
        bottomMargin=0.039 * inch,
        title=f'{doc_title}',
    )
    doc.build(elements)
    return _pdf_http_response(buff, order_obj, pk, request)
