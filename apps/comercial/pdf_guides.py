"""Modulo unificado de PDFs de guias de remision y manifiesto de carga.

Consolida:
    - print_guide_format_tk: Guia de Remision Remitente (reservada / no usada por ahora).
    - print_guide_format_a4: Guia de Remision Transportista (A4) — una por orden.
    - print_cargo_manifest: Manifiesto de Carga (A4 horizontal) — agrupa GRT.

Este modulo es autocontenido (no importa nada de views_PDF) para evitar
importaciones circulares, ya que views_PDF reexporta estas funciones.
"""
import decimal
import io
import os
from collections import Counter

from django.db.models import Sum
from django.http import HttpResponse
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, inch
from reportlab.platypus import HRFlowable, Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from rapidovip import settings

# ---------------------------------------------------------------------------
# Estilos locales (Helvetica). Se define un stylesheet propio para no
# depender de views_PDF y evitar el riesgo de import circular.
# ---------------------------------------------------------------------------
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='Helvetica_Bold_Center_15', alignment=TA_CENTER, leading=15,
                          fontName='Helvetica-Bold', fontSize=15, spaceBefore=6, spaceAfter=6))
styles.add(ParagraphStyle(name='Helvetica_Bold_Center_13', alignment=TA_CENTER, leading=13,
                          fontName='Helvetica-Bold', fontSize=13, spaceBefore=6, spaceAfter=6))
styles.add(ParagraphStyle(name='Helvetica_Bold_Center_12_leading', alignment=TA_CENTER, leading=8,
                          fontName='Helvetica-Bold', fontSize=12))
styles.add(ParagraphStyle(name='Helvetica_Bold_Center_10', alignment=TA_CENTER, leading=11,
                          fontName='Helvetica-Bold', fontSize=10))
styles.add(ParagraphStyle(name='Helvetica_Bold_Center_9', alignment=TA_CENTER, leading=10,
                          fontName='Helvetica-Bold', fontSize=9))
styles.add(ParagraphStyle(name='Helvetica_Bold_Center_8', alignment=TA_CENTER, leading=8,
                          fontName='Helvetica-Bold', fontSize=8))
styles.add(ParagraphStyle(name='Helvetica_Bold_Center_8_leading', alignment=TA_CENTER, leading=6,
                          fontName='Helvetica-Bold', fontSize=8))
styles.add(ParagraphStyle(name='Helvetica_Bold_Center_7', alignment=TA_CENTER, leading=8,
                          fontName='Helvetica-Bold', fontSize=7))
styles.add(ParagraphStyle(name='Helvetica_Bold_Left_9', alignment=TA_LEFT, leading=10,
                          fontName='Helvetica-Bold', fontSize=9))
styles.add(ParagraphStyle(name='Helvetica_Bold_Left_8', alignment=TA_LEFT, leading=8,
                          fontName='Helvetica-Bold', fontSize=7.4))
styles.add(ParagraphStyle(name='Helvetica_Bold_Left_7', alignment=TA_LEFT, leading=8,
                          fontName='Helvetica-Bold', fontSize=7))
styles.add(ParagraphStyle(name='Helvetica_Left_9', alignment=TA_LEFT, leading=10,
                          fontName='Helvetica', fontSize=9))
styles.add(ParagraphStyle(name='Helvetica_Left_8', alignment=TA_LEFT, leading=8,
                          fontName='Helvetica', fontSize=8))
styles.add(ParagraphStyle(name='Helvetica_Left_7', alignment=TA_LEFT, leading=8,
                          fontName='Helvetica', fontSize=7))
styles.add(ParagraphStyle(name='Helvetica_Center_8', alignment=TA_CENTER, leading=8,
                          fontName='Helvetica', fontSize=8))
styles.add(ParagraphStyle(name='Helvetica_Center_7', alignment=TA_CENTER, leading=8,
                          fontName='Helvetica', fontSize=7))
styles.add(ParagraphStyle(name='Helvetica_Justify_8', alignment=TA_JUSTIFY, leading=8,
                          fontName='Helvetica', fontSize=8))
styles.add(ParagraphStyle(name='Helvetica_Bold_Right_9', alignment=TA_RIGHT, leading=10,
                          fontName='Helvetica-Bold', fontSize=9))
styles.add(ParagraphStyle(name='Helvetica_Right_8', alignment=TA_RIGHT, leading=9,
                          fontName='Helvetica', fontSize=8))


def qr_code(table, size_cm=4.8, quiet_zone=1):
    """Genera un Drawing con el codigo QR (reescalado) para el texto dado."""
    qr_widget = qr.QrCodeWidget(table)
    qr_widget.barBorder = quiet_zone
    bounds = qr_widget.getBounds()
    width = bounds[2] - bounds[0]
    height = bounds[3] - bounds[1]
    side = size_cm * cm
    drawing = Drawing(
        side, side, transform=[side / width, 0, 0, side / height, 0, 0])
    drawing.add(qr_widget)
    return drawing


def _get_client_document_info(client_obj):
    """Devuelve (tipo_documento, numero_documento) de un cliente, de forma segura."""
    if not client_obj:
        return '', ''
    client_type_obj = client_obj.clienttype_set.first()
    if not client_type_obj:
        return '', ''
    document_type_label = ''
    if client_type_obj.document_type_id:
        document_type_label = client_type_obj.document_type.short_description or ''
    return document_type_label, client_type_obj.document_number or ''


def _safe_decimal(value):
    """Convierte valores None/float/Decimal a Decimal de forma segura."""
    if value is None:
        return decimal.Decimal('0')
    if isinstance(value, decimal.Decimal):
        return value
    return decimal.Decimal(str(value))


def _guide_logo_image(max_width, max_height):
    """Devuelve el logo centrable con proporción real (sin estirar)."""
    logo_path = os.path.join(str(settings.BASE_DIR), 'static', 'assets', 'rapidovip_logo.png')
    if not os.path.exists(logo_path):
        return None
    logo_image = Image(logo_path)
    natural_w = float(logo_image.imageWidth or 1)
    natural_h = float(logo_image.imageHeight or 1)
    aspect = natural_h / natural_w
    draw_w = float(max_width)
    draw_h = draw_w * aspect
    if draw_h > float(max_height):
        draw_h = float(max_height)
        draw_w = draw_h / aspect if aspect else float(max_width)
    logo_image.drawWidth = draw_w
    logo_image.drawHeight = draw_h
    logo_image.hAlign = 'CENTER'
    return logo_image


def _center_section_table(rows, width):
    """Tabla de una columna con textos centrados (título/fila fija en <b>)."""
    table = Table([[row] if not isinstance(row, list) else row for row in rows], colWidths=[width])
    table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
    ]))
    return table


def print_guide_format_tk(request, pk=None):  # Guia de Remision Remitente Electronica (ticket termico)
    from .models import SenderRemissionGuide

    sender_guide_obj = SenderRemissionGuide.objects.select_related(
        'order', 'order__client', 'order__subsidiary', 'order__company',
        'programming', 'programming__truck', 'programming__truck__truck_model__truck_brand',
        'carrier_guide', 'carrier_guide__company',
        'carrier_guide__truck', 'carrier_guide__truck__truck_model__truck_brand',
        'subsidiary', 'company', 'user',
    ).get(pk=pk)

    order_obj = sender_guide_obj.order
    company_obj = sender_guide_obj.company or order_obj.company

    page_width = 3.15 * inch
    _wt = page_width - 0.1 * inch

    document_number = '{}-{}'.format(
        sender_guide_obj.serial or '', str(sender_guide_obj.correlative or '').zfill(6))

    emit_date = sender_guide_obj.emit_date.strftime('%d/%m/%Y') if sender_guide_obj.emit_date else '-'
    transfer_date = sender_guide_obj.transfer_start_date.strftime('%d/%m/%Y') \
        if sender_guide_obj.transfer_start_date else '-'
    total_weight = str(round(_safe_decimal(sender_guide_obj.total_weight), 2))
    quantity_packages = str(int(round(_safe_decimal(sender_guide_obj.quantity_packages))))

    receiver_action = order_obj.orderaction_set.filter(type='D').select_related(
        'client', 'order_addressee').last()
    receiver_doc_type, receiver_doc_number, receiver_name = '', '', '-'
    if receiver_action and receiver_action.client:
        receiver_doc_type, receiver_doc_number = _get_client_document_info(receiver_action.client)
        receiver_name = (receiver_action.client.names or '').upper()
    elif receiver_action and receiver_action.order_addressee:
        receiver_name = (receiver_action.order_addressee.names or '').upper()

    _encomienda = getattr(order_obj, 'encomienda', None)
    _origin_office = _encomienda.office_origin if _encomienda else None
    _dest_office = _encomienda.office_destination if _encomienda else None
    origin_label = (_origin_office.short_name or _origin_office.name) if _origin_office else ''
    origin_address = (_origin_office.address or '') if _origin_office else ''
    if _encomienda and _encomienda.is_reparto:
        dest_label = 'REPARTO'
        dest_address = _encomienda.effective_destination_address()
        ubigeo_rep = _encomienda.effective_arrival_ubigeo()
        if ubigeo_rep:
            dest_address = f'{dest_address} (UBI {ubigeo_rep})'
    else:
        dest_label = (_dest_office.short_name or _dest_office.name) if _dest_office else ''
        dest_address = (_dest_office.address or '') if _dest_office else ''

    carrier_guide_obj = sender_guide_obj.carrier_guide
    transport_company_obj = (carrier_guide_obj.company if carrier_guide_obj else None) or company_obj
    truck_obj = None
    driver_name = ''
    driver_license = ''
    if carrier_guide_obj:
        truck_obj = carrier_guide_obj.truck
        driver_name = carrier_guide_obj.driver_name or ''
        driver_license = carrier_guide_obj.driver_license or ''
    elif sender_guide_obj.programming:
        truck_obj = sender_guide_obj.programming.truck
        driver_name = sender_guide_obj.programming.support_pilot or ''
    truck_plate = truck_obj.license_plate if truck_obj else ''
    truck_brand = truck_obj.truck_model.truck_brand.name if truck_obj and truck_obj.truck_model_id else ''

    separator = HRFlowable(width='100%', thickness=0.6, color=colors.grey, spaceBefore=3, spaceAfter=3)
    style_c7 = styles['Helvetica_Center_7']

    detail_rows = [
        [
            Paragraph('<b>#</b>', style_c7),
            Paragraph('<b>DETALLE</b>', style_c7),
            Paragraph('<b>CANT</b>', style_c7),
        ],
    ]
    for index, d in enumerate(order_obj.orderdetail_set.all(), start=1):
        detail_rows.append([
            Paragraph(str(index), style_c7),
            Paragraph((d.description or '').upper(), style_c7),
            Paragraph(str(_safe_decimal(d.quantity).to_integral_value()), style_c7),
        ])
    if len(detail_rows) == 1:
        detail_rows.append([
            Paragraph('-', style_c7),
            Paragraph('SIN DETALLE', style_c7),
            Paragraph('-', style_c7),
        ])

    style_details_table = [
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('BOX', (0, 0), (-1, 0), 1.2, colors.black),
        ('INNERGRID', (0, 0), (-1, 0), 0.6, colors.grey),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
    ]
    for idx in range(1, len(detail_rows) + 1):
        if idx % 2 == 0:
            style_details_table.append(('BACKGROUND', (0, idx), (-1, idx), colors.whitesmoke))
            style_details_table.append(('LINEABOVE', (0, idx), (-1, idx), 0.5, colors.grey))
            style_details_table.append(('LINEBELOW', (0, idx), (-1, idx), 0.5, colors.grey))

    table_details = Table(
        detail_rows,
        colWidths=[_wt * 10 / 100, _wt * 70 / 100, _wt * 20 / 100],
    )
    table_details.setStyle(TableStyle(style_details_table))

    # Solo boleta o factura; si no hay, no se muestra la sección.
    related_docs = []
    order_bill_obj = getattr(order_obj, 'orderbill', None)
    if order_bill_obj is None and hasattr(order_obj, 'orderbill_set'):
        order_bill_obj = order_obj.orderbill_set.first()
    if order_bill_obj:
        bill_type = getattr(order_bill_obj, 'type', None)
        if bill_type in ('1', 'F', '01'):
            bill_label = 'FACTURA ELECTRÓNICA'
            related_docs.append('{}: {}-{}'.format(
                bill_label,
                order_bill_obj.serial or '',
                str(getattr(order_bill_obj, 'n_receipt', None) or order_obj.correlative_sale or 0).zfill(6),
            ))
        elif bill_type in ('3', 'B', '03'):
            bill_label = 'BOLETA ELECTRÓNICA'
            related_docs.append('{}: {}-{}'.format(
                bill_label,
                order_bill_obj.serial or '',
                str(getattr(order_bill_obj, 'n_receipt', None) or order_obj.correlative_sale or 0).zfill(6),
            ))
    elif order_obj.type_document in ('B', 'F'):
        bill_label = 'FACTURA ELECTRÓNICA' if order_obj.type_document == 'F' else 'BOLETA ELECTRÓNICA'
        related_docs.append('{}: {}-{}'.format(
            bill_label, order_obj.serial or '', order_obj.correlative_sale or '',
        ))

    qr_size_cm = 4.2
    table_qr = Table(
        [[qr_code(document_number, size_cm=qr_size_cm, quiet_zone=1)]],
        colWidths=[qr_size_cm * cm + 8],
    )
    table_qr.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, colors.Color(0.4, 0.4, 0.4)),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    table_qr.hAlign = 'CENTER'

    destino_rows = [
        Paragraph('<b>DESTINATARIO</b>', style_c7),
    ]
    if receiver_doc_type or receiver_doc_number:
        destino_rows.append(Paragraph(
            '<b>{}:</b> {}'.format(receiver_doc_type, receiver_doc_number), style_c7,
        ))
    destino_rows.append(Paragraph(receiver_name, style_c7))

    traslado_rows = [
        Paragraph('<b>DATOS DEL TRASLADO</b>', style_c7),
        Paragraph('<b>FECHA EMISIÓN:</b> {}'.format(emit_date), style_c7),
        Paragraph(
            '<b>FECHA DE ENTREGA DE BIENES AL TRANSPORTISTA:</b> {}'.format(transfer_date),
            style_c7,
        ),
        Paragraph('<b>MOTIVO DE TRASLADO:</b> VENTA', style_c7),
        Paragraph('<b>MODALIDAD DE TRANSPORTE:</b> TRANSPORTE PRIVADO', style_c7),
        Paragraph('<b>PESO BRUTO TOTAL (KGM):</b> {}'.format(total_weight), style_c7),
        Paragraph('<b>NÚMERO DE BULTOS:</b> {}'.format(quantity_packages), style_c7),
    ]

    transport_name = ((transport_company_obj.business_name if transport_company_obj else '') or '').upper()
    transporte_rows = [Paragraph('<b>DATOS DEL TRANSPORTE</b>', style_c7)]
    if transport_name:
        transporte_rows.append(Paragraph(transport_name, style_c7))
    if truck_plate:
        vehicle_line = '<b>PLACA:</b> {}'.format(truck_plate)
        if truck_brand:
            vehicle_line += ' - {}'.format(truck_brand)
        transporte_rows.append(Paragraph(vehicle_line, style_c7))
    if driver_name:
        driver_line = '<b>CONDUCTOR:</b> {}'.format(driver_name)
        if driver_license:
            driver_line += ' - LIC. {}'.format(driver_license)
        transporte_rows.append(Paragraph(driver_line, style_c7))
    if not truck_plate and not driver_name:
        transporte_rows.append(Paragraph('<b>VEHÍCULO Y CONDUCTOR:</b> POR ASIGNAR', style_c7))

    partida_text = '{}{}'.format(
        (origin_label.upper() + ' - ') if origin_label else '',
        (origin_address or '-').upper(),
    )
    llegada_text = '{}{}'.format(
        (dest_label.upper() + ' - ') if dest_label else '',
        (dest_address or '-').upper(),
    )
    puntos_rows = [
        Paragraph('<b>PUNTO DE PARTIDA</b>', style_c7),
        Paragraph(partida_text, style_c7),
        Paragraph('<b>PUNTO DE LLEGADA</b>', style_c7),
        Paragraph(llegada_text, style_c7),
    ]

    _dictionary = []
    logo_image = _guide_logo_image(_wt * 0.55, _wt * 0.30)
    if logo_image:
        _dictionary.append(logo_image)
        # _dictionary.append(Spacer(1, 2))

    business_name = ((company_obj.business_name if company_obj else '') or '-').upper()
    _dictionary.append(Paragraph(business_name, styles['Helvetica_Bold_Center_8']))
    _dictionary.append(Spacer(1, 2))
    if company_obj and company_obj.address:
        _dictionary.append(Paragraph(company_obj.address, styles['Helvetica_Center_8']))
        _dictionary.append(Spacer(1, 2))
    if company_obj:
        _dictionary.append(Paragraph(
            'RUC {}'.format(company_obj.ruc or ''),
            styles['Helvetica_Bold_Center_8'],
        ))
    _dictionary.append(Spacer(1, 2))
    _dictionary.append(Paragraph(
        'GUIA DE REMISION REMITENTE ELECTRÓNICA',
        styles['Helvetica_Bold_Center_8_leading'],
    ))
    _dictionary.append(Spacer(1, 4))
    _dictionary.append(Paragraph(document_number, styles['Helvetica_Bold_Center_12_leading']))
    _dictionary.append(Spacer(1, 4))
    _dictionary.append(separator)

    _dictionary.append(_center_section_table(destino_rows, _wt))
    _dictionary.append(separator)
    _dictionary.append(_center_section_table(traslado_rows, _wt))
    _dictionary.append(separator)
    _dictionary.append(_center_section_table(transporte_rows, _wt))
    _dictionary.append(separator)
    _dictionary.append(_center_section_table(puntos_rows, _wt))
    _dictionary.append(Spacer(1, 4))
    _dictionary.append(table_details)
    _dictionary.append(Spacer(1, 4))
    _dictionary.append(Paragraph('<b>OBSERVACIONES</b>', style_c7))

    if related_docs:
        _dictionary.append(separator)
        related_rows = [Paragraph('<b>DOCUMENTOS RELACIONADOS</b>', style_c7)]
        related_rows.extend(Paragraph(doc_line, style_c7) for doc_line in related_docs)
        _dictionary.append(_center_section_table(related_rows, _wt))

    _dictionary.append(separator)
    _dictionary.append(Paragraph(
        'Representación impresa de la GUIA DE REMISIÓN<br/>'
        'REMITENTE ELECTRÓNICA, para ver el documento visita<br/>'
        '<b>https://www.tuf4ct.com/cpe</b>',
        style_c7,
    ))
    _dictionary.append(Spacer(1, 6))
    _dictionary.append(table_qr)

    buff = io.BytesIO()
    ml = 0.0 * inch
    mr = 0.0 * inch
    ms = 0.0 * inch
    mi = 0.039 * inch
    _details_count = max(order_obj.orderdetail_set.count(), 1)
    pz_termical = (page_width, 9.4 * inch + (_details_count * 0.18 * inch))

    doc = SimpleDocTemplate(
        buff,
        pagesize=pz_termical,
        rightMargin=mr,
        leftMargin=ml,
        topMargin=ms,
        bottomMargin=mi,
        title='GUIA DE REMISION REMITENTE-{}'.format(document_number),
    )
    doc.build(_dictionary)

    disposition = 'attachment' if request and request.GET.get('download') else 'inline'
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = '{}; filename="GuiaRemisionRemitente_[{}].pdf"'.format(
        disposition,
        document_number,
    )
    response.write(buff.getvalue())
    buff.close()
    return response


def _party_lines(order_obj, action_type):
    """Devuelve texto de remitente/destinatario con documento."""
    action = order_obj.orderaction_set.filter(type=action_type).select_related(
        'client', 'order_addressee',
    ).last()
    if not action:
        return '—'
    if action.client_id:
        name = (action.client.names or '—').upper()
        doc_type, doc_number = _get_client_document_info(action.client)
        phone = action.client.phone or ''
        lines = [name]
        if doc_type or doc_number:
            lines.append('{}: {}'.format(doc_type or 'DOC', doc_number or '—'))
        if phone:
            lines.append('TEL: {}'.format(phone))
        return '<br/>'.join(lines)
    if action.order_addressee_id:
        return (action.order_addressee.names or '—').upper()
    return '—'


def _related_document_lines(order_obj, carrier_guide_obj=None):
    """Documento relacionado (boleta/factura) + referencia a orden de servicio."""
    lines = ['ORDEN DE SERVICIO: OS-{}'.format(order_obj.id if order_obj else '—')]
    stored = ''
    if carrier_guide_obj:
        stored = (carrier_guide_obj.related_document or '').strip()
    if stored:
        lines.append(stored)
    elif order_obj:
        from .guide_assignment import related_document_for_order
        related = related_document_for_order(order_obj)
        if related:
            lines.append(related)
        else:
            lines.append('SIN COMPROBANTE (PAGO DESTINO / ORDEN DE SERVICIO)')
    return lines


def print_guide_format_a4(request, pk=None):  # Guia de Remision Transportista (A4)
    from .models import CarrierRemissionGuide

    ml = 0.45 * inch
    mr = 0.45 * inch
    ms = 0.4 * inch
    mi = 0.4 * inch
    _bts = 8.27 * inch - ml - mr

    soft_border = colors.Color(0.55, 0.55, 0.55)
    soft_fill = colors.Color(0.92, 0.92, 0.92)
    radius = [6, 6, 6, 6]

    carrier_guide_obj = CarrierRemissionGuide.objects.select_related(
        'order', 'order__company', 'order__subsidiary', 'order__orderbill',
        'programming', 'programming__subsidiary', 'programming__company',
        'programming__cargo_manifest',
        'cargo_manifest',
        'truck', 'truck__truck_model__truck_brand',
        'subsidiary', 'company', 'user',
    ).prefetch_related(
        'order__orderdetail_set__unit',
        'order__orderaction_set__client__clienttype_set__document_type',
        'order__orderaction_set__order_addressee',
        'order__encomienda__office_destination',
        'order__encomienda__office_origin',
    ).get(pk=pk)

    order_obj = carrier_guide_obj.order
    programming_obj = carrier_guide_obj.programming
    company_obj = (
        carrier_guide_obj.company
        or (order_obj.company if order_obj else None)
        or (programming_obj.company if programming_obj else None)
    )

    company_business_name = (company_obj.business_name if company_obj else 'RapidoVip') or 'RapidoVip'
    company_address = company_obj.address if company_obj else ''
    company_ruc = company_obj.ruc if company_obj else ''

    serial = (carrier_guide_obj.serial or '').strip()
    correlative = str(carrier_guide_obj.correlative or '').zfill(6)
    document_number = '{}-{}'.format(serial, correlative)
    document_number_display = 'Nº {}-{}'.format(serial, correlative)

    emit_date = carrier_guide_obj.emit_date.strftime('%d/%m/%Y') if carrier_guide_obj.emit_date else '-'
    transfer_date = carrier_guide_obj.transfer_start_date.strftime('%d/%m/%Y') \
        if carrier_guide_obj.transfer_start_date else '-'
    total_weight = str(round(_safe_decimal(carrier_guide_obj.total_weight), 2))
    quantity_packages = str(int(round(_safe_decimal(carrier_guide_obj.quantity_packages))))
    observation = (carrier_guide_obj.observation or '').strip()

    truck_obj = carrier_guide_obj.truck or (programming_obj.truck if programming_obj else None)
    truck_plate = truck_obj.license_plate if truck_obj else '-'

    driver_name = carrier_guide_obj.driver_name or '-'
    driver_license = carrier_guide_obj.driver_license or '-'

    def _route_label(route_type):
        if not order_obj:
            return '-'
        encomienda = getattr(order_obj, 'encomienda', None)
        if route_type == 'O' and encomienda and encomienda.office_origin_id:
            sub = encomienda.office_origin
            return '{} — {}'.format(
                sub.short_name or sub.name or '',
                sub.address or '',
            ).strip(' —')
        if route_type == 'D' and encomienda:
            if encomienda.is_reparto:
                address = encomienda.effective_destination_address()
                ubigeo = encomienda.effective_arrival_ubigeo()
                if ubigeo:
                    return 'REPARTO · {} (UBI {})'.format(address, ubigeo)
                return 'REPARTO · {}'.format(address or '-')
            if encomienda.office_destination_id:
                sub = encomienda.office_destination
                return '{} — {}'.format(
                    sub.short_name or sub.name or '',
                    sub.address or '',
                ).strip(' —')
        return '-'

    origin_label = _route_label('O')
    dest_label = _route_label('D')

    def _soft_boxed_section(title, rows, col_widths, min_body_height=None):
        width_total = sum(col_widths)
        header_tbl = Table([[Paragraph(title, styles["Helvetica_Bold_Left_8"])]], colWidths=[width_total])
        header_tbl.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), soft_fill),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        body_kwargs = {'colWidths': col_widths}
        if min_body_height:
            body_kwargs['rowHeights'] = [min_body_height] * len(rows)
        body_tbl = Table(rows, **body_kwargs)
        body_tbl.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('INNERGRID', (0, 0), (-1, -1), 0.35, soft_border),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        wrapped = Table([[header_tbl], [body_tbl]], colWidths=[width_total])
        wrapped.setStyle(TableStyle([
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('BOX', (0, 0), (-1, -1), 1.0, soft_border),
            ('ROUNDEDCORNERS', radius),
            ('LINEBELOW', (0, 0), (-1, 0), 0.5, soft_border),
        ]))
        return [wrapped]

    logo_image = _guide_logo_image(_bts * 21 / 100, 0.72 * inch)
    if logo_image:
        logo_image.hAlign = 'LEFT'

    company_text_width = _bts * 38 / 100
    table_company_rows = [
        [Paragraph(company_business_name.upper(), styles["Helvetica_Bold_Left_9"])],
        [Paragraph(company_address or '', styles["Helvetica_Left_7"])],
        [Paragraph('RUC: {}'.format(company_ruc), styles["Helvetica_Left_7"])],
    ]
    table_company = Table(table_company_rows, colWidths=[company_text_width])
    table_company.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
    ]))

    logo_col = _bts * 20 / 100
    if logo_image:
        left_header_cell = Table(
            [[logo_image, table_company]],
            colWidths=[logo_col, company_text_width],
        )
        left_header_cell.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('LEFTPADDING', (0, 0), (0, 0), 0),
            ('RIGHTPADDING', (0, 0), (0, 0), 6),
            ('LEFTPADDING', (1, 0), (1, 0), 4),
            ('RIGHTPADDING', (1, 0), (1, 0), 4),
        ]))
    else:
        left_header_cell = table_company

    title_box_width = _bts * 40 / 100
    table_doc_title = Table([
        [Paragraph('R.U.C. Nº {}'.format(company_ruc), styles["Helvetica_Bold_Center_9"])],
        [Paragraph('GUÍA DE REMISIÓN<br/>TRANSPORTISTA', styles["Helvetica_Bold_Center_10"])],
        [Paragraph(document_number_display, styles["Helvetica_Bold_Center_13"])],
    ], colWidths=[title_box_width])
    table_doc_title.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 2.0, colors.black),
        ('ROUNDEDCORNERS', [8, 8, 8, 8]),
        ('LINEBELOW', (0, 0), (-1, 0), 0.9, soft_border),
        ('LINEBELOW', (0, 1), (-1, 1), 0.9, soft_border),
        ('BACKGROUND', (0, 1), (-1, 1), soft_fill),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 1), (-1, 1), 7),
        ('BOTTOMPADDING', (0, 1), (-1, 1), 7),
    ]))

    left_header_width = _bts - title_box_width
    table_header = Table(
        [[left_header_cell, table_doc_title]],
        colWidths=[left_header_width, title_box_width],
    )
    table_header.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))

    # ------------------------------------------------------------------
    # Datos de remitente / destinatario (nombre, documento y teléfono).
    # ------------------------------------------------------------------
    def _party_info(action_type):
        info = {'name': '—', 'doc_label': '', 'doc_number': '', 'phone': ''}
        if not order_obj:
            return info
        action = order_obj.orderaction_set.filter(type=action_type).select_related(
            'client', 'order_addressee',
        ).last()
        if not action:
            return info
        if action.client_id:
            info['name'] = (action.client.names or '—').upper()
            doc_label, doc_number = _get_client_document_info(action.client)
            info['doc_label'] = (doc_label or '').upper()
            info['doc_number'] = doc_number or ''
            info['phone'] = action.client.phone or ''
        elif action.order_addressee_id:
            info['name'] = (action.order_addressee.names or '—').upper()
            info['phone'] = getattr(action.order_addressee, 'phone', '') or ''
        return info

    sender_info = _party_info('R')
    receiver_info = _party_info('D')

    def _party_display(info):
        text = info['name']
        if info['doc_label'] or info['doc_number']:
            text += ' - {} - {}'.format(
                info['doc_label'] or 'DOC', info['doc_number'] or '—')
        return text

    emit_time = ''
    if carrier_guide_obj.created_at:
        try:
            from apps.sales.format_to_dates import utc_to_local
            emit_time = utc_to_local(carrier_guide_obj.created_at).strftime('%H:%M:%S')
        except Exception:
            emit_time = carrier_guide_obj.created_at.strftime('%H:%M:%S')

    thin_line = colors.Color(0.75, 0.75, 0.75)

    def _label_value(label, value):
        return Paragraph(
            '<b>{}</b> {}'.format(label, value), styles["Helvetica_Left_8"])

    def _label_value_right(label, value):
        return Paragraph(
            '<b>{}</b> {}'.format(label, value), styles["Helvetica_Right_8"])

    # Nº de orden de servicio arriba, debajo del encabezado.
    if order_obj and (order_obj.order_serial or '').strip() and (order_obj.order_correlative or '').strip():
        order_service_number = '{}-{}'.format(order_obj.order_serial, order_obj.order_correlative)
    else:
        order_service_number = 'OS-{}'.format(order_obj.id) if order_obj else '—'
    order_service_line = Paragraph(
        '<b>ORDEN DE SERVICIO:</b> {}'.format(order_service_number),
        styles["Helvetica_Bold_Right_9"],
    )

    # Fechas (izquierda) y puntos de partida/llegada (derecha), sin recuadros.
    dates_points_tbl = Table(
        [
            [
                _label_value('FECHA DE EMISIÓN:', '{} {}'.format(emit_date, emit_time).strip()),
                _label_value('PUNTO DE PARTIDA:', origin_label),
            ],
            [
                _label_value('FECHA DE TRASLADO:', transfer_date),
                _label_value('PUNTO DE LLEGADA:', dest_label),
            ],
            [
                _label_value('PESO BRUTO TOTAL DE LA CARGA (KG):', total_weight),
                '',
            ],
        ],
        colWidths=[_bts * 47 / 100, _bts * 53 / 100],
    )
    dates_points_tbl.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
    ]))

    # Recuadros redondeados de remitente y destinatario, lado a lado.
    box_width = _bts * 49 / 100
    remitente_box = _soft_boxed_section(
        'DATOS DEL REMITENTE',
        [
            [Paragraph(_party_display(sender_info), styles["Helvetica_Left_8"])],
            [_label_value('TELÉFONO:', sender_info['phone'] or '—')],
        ],
        [box_width],
    )[0]
    destinatario_box = _soft_boxed_section(
        'DATOS DEL DESTINATARIO',
        [
            [Paragraph(_party_display(receiver_info), styles["Helvetica_Left_8"])],
            [_label_value('TELÉFONO:', receiver_info['phone'] or '—')],
        ],
        [box_width],
    )[0]
    parties_tbl = Table(
        [[remitente_box, destinatario_box]],
        colWidths=[_bts * 50 / 100, _bts * 50 / 100],
    )
    parties_tbl.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (0, 0), 0),
        ('RIGHTPADDING', (0, 0), (0, 0), 4),
        ('LEFTPADDING', (1, 0), (1, 0), 4),
        ('RIGHTPADDING', (1, 0), (1, 0), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))

    # Transportista (empresa) a la izquierda, RUC a la derecha.
    transportista_tbl = Table(
        [[
            _label_value('TRANSPORTISTA:', company_business_name.upper()),
            _label_value_right('RUC:', company_ruc),
        ]],
        colWidths=[_bts * 65 / 100, _bts * 35 / 100],
    )
    transportista_tbl.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LINEABOVE', (0, 0), (-1, 0), 0.6, thin_line),
        ('LINEBELOW', (0, 0), (-1, 0), 0.6, thin_line),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))

    # Pagador del flete: al contado paga el remitente; pago destino paga el destinatario.
    if order_obj and order_obj.way_to_pay == 'D':
        payer_info = receiver_info
        payer_indicator = 'DESTINATARIO'
    else:
        payer_info = sender_info
        payer_indicator = 'REMITENTE'
    payer_tbl = Table(
        [[
            _label_value('DATOS DE PAGADOR DE FLETE:', _party_display(payer_info)),
            _label_value_right(
                'INDICADOR DEL PAGADOR DEL FLETE:',
                '{} - {}'.format(payer_indicator, payer_info['doc_number'] or '—'),
            ),
        ]],
        colWidths=[_bts * 55 / 100, _bts * 45 / 100],
    )
    payer_tbl.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LINEBELOW', (0, 0), (-1, 0), 0.6, thin_line),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))

    # ------------------------------------------------------------------
    # Tabla de detalle: CANT. | UNIDAD | DESCRIPCIÓN | PESO (Kg) | FLETE
    # (con observación y T.G. dentro de la columna descripción).
    # ------------------------------------------------------------------
    detail_cols = [
        _bts * 9 / 100,
        _bts * 14 / 100,
        _bts * 47 / 100,
        _bts * 14 / 100,
        _bts * 16 / 100,
    ]
    detail_rows = [[
        Paragraph('CANT.', styles["Helvetica_Bold_Center_8"]),
        Paragraph('UNIDAD', styles["Helvetica_Bold_Center_8"]),
        Paragraph('DESCRIPCIÓN', styles["Helvetica_Bold_Left_8"]),
        Paragraph('PESO (KG)', styles["Helvetica_Bold_Center_8"]),
        Paragraph('FLETE', styles["Helvetica_Bold_Center_8"]),
    ]]
    details = list(order_obj.orderdetail_set.all()) if order_obj else []
    for detail in details:
        qty = _safe_decimal(detail.quantity)
        weight = _safe_decimal(detail.weight)
        amount = _safe_decimal(detail.amount)
        detail_rows.append([
            Paragraph(
                str(qty.to_integral_value() if qty == qty.to_integral_value() else qty),
                styles["Helvetica_Center_8"],
            ),
            Paragraph(
                (detail.unit.name if detail.unit_id else 'SIN UND').upper(),
                styles["Helvetica_Center_8"],
            ),
            Paragraph((detail.description or 'ENCOMIENDA').upper(), styles["Helvetica_Left_8"]),
            Paragraph(str(round(weight, 2)), styles["Helvetica_Center_8"]),
            Paragraph(str(round(amount, 2)), styles["Helvetica_Center_8"]),
        ])
    if len(detail_rows) == 1:
        detail_rows.append([
            Paragraph(quantity_packages, styles["Helvetica_Center_8"]),
            Paragraph('BULTO(S)', styles["Helvetica_Center_8"]),
            Paragraph('SIN DETALLE DE CARGA', styles["Helvetica_Left_8"]),
            Paragraph(total_weight, styles["Helvetica_Center_8"]),
            Paragraph('-', styles["Helvetica_Center_8"]),
        ])

    tg_label = 'FLETE DESTINO' if order_obj and order_obj.way_to_pay == 'D' else 'FLETE ORIGEN'
    detail_rows.append([
        '', '',
        Paragraph('<b>T.G.</b>&nbsp;&nbsp;&nbsp;{}'.format(tg_label), styles["Helvetica_Left_8"]),
        '', '',
    ])
    detail_rows.append([
        '', '',
        Paragraph(
            '<b>OBSERVACION:</b> {}'.format(observation.upper() if observation else ''),
            styles["Helvetica_Left_8"],
        ),
        '', '',
    ])

    row_heights = [None] * len(detail_rows)
    row_heights[-2] = 0.4 * inch
    row_heights[-1] = 0.5 * inch
    table_details = Table(detail_rows, colWidths=detail_cols, rowHeights=row_heights)
    table_details.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), soft_fill),
        ('BOX', (0, 0), (-1, -1), 1.0, soft_border),
        ('ROUNDEDCORNERS', radius),
        ('LINEBELOW', (0, 0), (-1, 0), 0.6, soft_border),
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
        ('VALIGN', (0, 1), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))

    # Documentos adjuntos: documento relacionado guardado en la guía (boleta/factura).
    related_document = (carrier_guide_obj.related_document or '').strip()
    attachments_tbl = Table(
        [[_label_value('DOCUMENTOS ADJUNTOS:', related_document.upper())]],
        colWidths=[_bts],
        rowHeights=[0.3 * inch],
    )
    attachments_tbl.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LINEBELOW', (0, 0), (-1, 0), 0.6, thin_line),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))

    # Datos de los vehículos y de los conductores.
    vehicles_title = Table(
        [[Paragraph('DATOS DE LOS VEHÍCULOS Y DE LOS CONDUCTORES', styles["Helvetica_Bold_Left_8"])]],
        colWidths=[_bts],
    )
    vehicles_title.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), soft_fill),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    vehicles_tbl = Table(
        [
            [
                _label_value('V. PRINCIPAL:', truck_plate),
                _label_value('TUC V. PRINCIPAL:', ''),
            ],
            [
                _label_value('C. PRINCIPAL:', driver_name.upper()),
                _label_value('LICENCIA C. PRINCIPAL:', driver_license),
            ],
        ],
        colWidths=[_bts * 50 / 100, _bts * 50 / 100],
    )
    vehicles_tbl.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))

    def _signature_block(label):
        block = Table(
            [
                [Paragraph(label, styles["Helvetica_Bold_Center_8"])],
                [Paragraph('&nbsp;<br/>&nbsp;', styles["Helvetica_Center_8"])],
                [HRFlowable(width='90%', thickness=0.8, color=soft_border, spaceBefore=2, spaceAfter=2)],
                [Paragraph('Firma', styles["Helvetica_Center_7"])],
            ],
            colWidths=[_bts * 26 / 100],
        )
        block.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (0, 0), (-1, -1), 0.8, soft_border),
            ('ROUNDEDCORNERS', radius),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]))
        return block

    table_qr_signatures = Table(
        [[
            qr_code(document_number, size_cm=3.2),
            _signature_block('FIRMA DE LA EMPRESA'),
            _signature_block('FIRMA DEL TRANSPORTISTA'),
            _signature_block('FIRMA DEL DESTINATARIO'),
        ]],
        colWidths=[_bts * 18 / 100, _bts * 27 / 100, _bts * 27.5 / 100, _bts * 27.5 / 100],
    )
    table_qr_signatures.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
    ]))

    _dictionary = [
        table_header,
        Spacer(1, 3),
        order_service_line,
        Spacer(1, 4),
        dates_points_tbl,
        Spacer(1, 3),
        parties_tbl,
        Spacer(1, 4),
        transportista_tbl,
        payer_tbl,
        Spacer(1, 4),
        table_details,
        Spacer(1, 4),
        attachments_tbl,
        Spacer(1, 4),
        vehicles_title,
        vehicles_tbl,
        Spacer(1, 5),
        Paragraph(
            'Representación impresa de la GUÍA DE REMISIÓN TRANSPORTISTA '
            '(traslado privado). Consulte la validez de este documento en el portal SUNAT.',
            styles["Helvetica_Justify_8"],
        ),
        Spacer(1, 4),
        table_qr_signatures,
    ]

    buff = io.BytesIO()
    doc = SimpleDocTemplate(
        buff,
        pagesize=A4,
        rightMargin=mr,
        leftMargin=ml,
        topMargin=ms,
        bottomMargin=mi,
        title='GUIA DE REMISION TRANSPORTISTA-{}'.format(document_number),
    )
    doc.build(_dictionary)

    disposition = 'attachment' if request and request.GET.get('download') else 'inline'
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = '{}; filename="GuiaRemisionTransportista_[{}].pdf"'.format(
        disposition, document_number,
    )
    response.write(buff.getvalue())
    buff.close()
    return response


# ---------------------------------------------------------------------------
# Manifiesto de carga (nuevo)
# ---------------------------------------------------------------------------

def _order_document_number(order_obj):
    """N° de orden de servicio = ID de la orden."""
    return 'OS-{}'.format(order_obj.id) if order_obj else '-'


def _order_detail_unit_name(order_obj):
    unit_names = [
        d.unit.name for d in order_obj.orderdetail_set.all() if d.unit_id
    ]
    if not unit_names:
        return 'SIN UND'
    return Counter(unit_names).most_common(1)[0][0]


def _order_detail_quantity(order_obj, fallback_quantity):
    fallback_quantity = _safe_decimal(fallback_quantity)
    if fallback_quantity:
        return fallback_quantity
    total = order_obj.orderdetail_set.aggregate(s=Sum('quantity'))['s']
    return _safe_decimal(total)


def _guide_destination_label(order_obj, encomienda_obj):
    if encomienda_obj:
        return encomienda_obj.effective_destination_label() or '-'
    return '-'


def _guide_destination_address(order_obj, encomienda_obj):
    if encomienda_obj:
        address = encomienda_obj.effective_destination_address()
        if address:
            return address
    return '-'


def _guide_action_names(order_obj, action_type):
    actions = order_obj.orderaction_set.filter(type=action_type).select_related('client', 'order_addressee')
    names = []
    for action in actions:
        if action.client_id:
            names.append((action.client.names or '').upper())
        elif action.order_addressee_id:
            names.append((action.order_addressee.names or '').upper())
    names = [n for n in names if n]
    return ', '.join(names) if names else '-'


def _manifest_section_title(title, width):
    tbl = Table([[Paragraph(title, styles["Helvetica_Bold_Center_9"])]], colWidths=[width])
    tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
        ('BOX', (0, 0), (-1, -1), 0.75, colors.black),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    return tbl


def _manifest_kv_grid(pairs, width):
    label_width = width * 0.42
    value_width = width - label_width
    rows = []
    for label, value in pairs:
        display_value = value if value not in (None, '') else '-'
        rows.append([
            Paragraph(label, styles["Helvetica_Bold_Left_7"]),
            Paragraph(str(display_value), styles["Helvetica_Left_7"]),
        ])
    tbl = Table(rows, colWidths=[label_width, value_width])
    tbl.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.75, colors.black),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    return tbl


def _manifest_titled_box(title, pairs, width):
    outer = Table(
        [[_manifest_section_title(title, width)], [_manifest_kv_grid(pairs, width)]],
        colWidths=[width],
    )
    outer.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    return outer


def print_cargo_manifest(request, pk=None):  # Manifiesto de Carga
    from .models import CargoManifest

    ml = 0.4 * inch
    mr = 0.4 * inch
    ms = 0.4 * inch
    mi = 0.4 * inch
    pagesize = landscape(A4)
    _bts = pagesize[0] - ml - mr
    soft_line = colors.Color(0.45, 0.45, 0.45)

    cargo_manifest_obj = CargoManifest.objects.select_related(
        'programming', 'programming__subsidiary', 'programming__company',
        'truck', 'truck__truck_model__truck_brand',
        'subsidiary', 'company', 'user',
    ).get(pk=pk)

    programming_obj = cargo_manifest_obj.programming
    company_obj = cargo_manifest_obj.company or (programming_obj.company if programming_obj else None)

    company_title = ((company_obj.short_name if company_obj else '') or
                      (company_obj.business_name if company_obj else '') or 'RapidoVip')
    company_business_name = (company_obj.business_name if company_obj else '') or ''
    company_ruc = (company_obj.ruc if company_obj else '') or ''

    document_number = cargo_manifest_obj.document_number()
    emit_date = cargo_manifest_obj.emit_date.strftime('%d/%m/%Y') if cargo_manifest_obj.emit_date else '-'
    total_weight = '{} KG'.format(str(round(_safe_decimal(cargo_manifest_obj.total_weight), 2)))
    quantity_packages = str(int(round(_safe_decimal(cargo_manifest_obj.quantity_packages))))
    total_amount = 'S/ {}'.format(str(round(_safe_decimal(cargo_manifest_obj.total_amount), 2)))

    truck_obj = cargo_manifest_obj.truck or (programming_obj.truck if programming_obj else None)
    truck_plate = truck_obj.license_plate if truck_obj else '-'
    truck_certificate = (getattr(truck_obj, 'certificate', None) if truck_obj else '') or '-'

    carrier_guides_qs = list(
        cargo_manifest_obj.carrier_guides.filter(status='I').select_related(
            'order', 'order__encomienda', 'order__encomienda__office_destination',
            'order__orderbill',
        ).prefetch_related(
            'order__orderdetail_set__unit',
            'order__orderaction_set__client',
            'order__orderaction_set__order_addressee',
            'order__encomienda__office_destination',
            'order__encomienda__office_origin',
        )
    )
    guides_count = cargo_manifest_obj.guides_count or len(carrier_guides_qs)

    # -------------------- Encabezado: 3 secciones en un solo cuadro --------------------
    left_width = _bts * 30 / 100
    box1_width = _bts * 36 / 100
    box2_width = _bts * 34 / 100
    style_l7 = styles['Helvetica_Left_7']
    style_l8 = styles['Helvetica_Left_8']

    def _soft_kv_grid(pairs, width):
        label_width = width * 0.42
        value_width = width - label_width
        rows = []
        for label, value in pairs:
            display_value = value if value not in (None, '') else '-'
            rows.append([
                Paragraph(label, styles['Helvetica_Bold_Left_7']),
                Paragraph(str(display_value), style_l7),
            ])
        tbl = Table(rows, colWidths=[label_width, value_width])
        tbl.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        return tbl

    logo_image = _guide_logo_image(left_width * 42 / 100, 0.72 * inch)
    left_lines = []
    if logo_image:
        logo_image.hAlign = 'LEFT'
        left_lines.append([logo_image])
    left_lines.append([Paragraph(company_title.upper(), styles['Helvetica_Bold_Left_9'])])
    if company_business_name and company_business_name.upper() != company_title.upper():
        left_lines.append([Paragraph(company_business_name.upper(), style_l8)])
    left_lines.append([Paragraph('<b>RUC:</b> {}'.format(company_ruc), style_l8)])
    left_cell = Table(left_lines, colWidths=[left_width - 8])
    left_cell.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
    ]))

    box1 = Table(
        [
            [Paragraph('<font size="12">MANIFIESTO DE CARGA</font>', styles['Helvetica_Bold_Left_9'])],
            [_soft_kv_grid([
                ('N° MANIFIESTO', document_number),
                ('PESO TOTAL', total_weight),
                ('FECHA MANIFIESTO', emit_date),
                ('BULTOS TOTAL', quantity_packages),
                ('N° DE GRT', guides_count),
                ('IMPORTE TOTAL', total_amount),
            ], box1_width - 8)],
        ],
        colWidths=[box1_width - 8],
    )
    box1.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, 0), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (0, 0), 2),
        ('BOTTOMPADDING', (0, 0), (0, 0), 4),
        ('TOPPADDING', (0, 1), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 0),
    ]))

    pilot_name = cargo_manifest_obj.driver_name or '-'
    pilot_license = cargo_manifest_obj.driver_license or '-'
    copilot_name = cargo_manifest_obj.co_pilot_name or '-'
    copilot_license = cargo_manifest_obj.co_pilot_license or '-'
    style_lb7 = styles['Helvetica_Bold_Left_7']
    viaje_w = box2_width - 8
    col_viaje = [viaje_w * 0.20, viaje_w * 0.30, viaje_w * 0.20, viaje_w * 0.30]

    box2 = Table([
        [
            Paragraph('<b>Destino:</b>', style_lb7),
            Paragraph(cargo_manifest_obj.destination_label or '-', style_l7),
            '',
            '',
        ],
        [
            Paragraph('<b>Vehículo:</b>', style_lb7),
            Paragraph(truck_plate, style_l7),
            Paragraph('<b>Certificado</b>', style_lb7),
            Paragraph(truck_certificate, style_l7),
        ],
        [
            Paragraph('<b>Conductor</b>', style_lb7),
            Paragraph(pilot_name, style_l7),
            Paragraph('<b>Licencia</b>', style_lb7),
            Paragraph(pilot_license, style_l7),
        ],
        [
            Paragraph('<b>Copiloto</b>', style_lb7),
            Paragraph(copilot_name, style_l7),
            Paragraph('<b>Licencia</b>', style_lb7),
            Paragraph(copilot_license, style_l7),
        ],
    ], colWidths=col_viaje)
    box2.setStyle(TableStyle([
        ('SPAN', (1, 0), (3, 0)),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))

    header_table = Table(
        [[left_cell, box1, box2]],
        colWidths=[left_width, box1_width, box2_width],
    )
    header_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, soft_line),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, soft_line),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))

    # -------------------- Detalle --------------------
    header_row_1 = [
        Paragraph('INFORMACIÓN DE LA CARGA', styles['Helvetica_Bold_Center_8']),
        '', '', '', '', '', '',
        Paragraph('PARTES Y DOCUMENTO', styles['Helvetica_Bold_Center_8']),
        '', '',
    ]
    header_row_2 = [
        Paragraph(h, styles['Helvetica_Bold_Center_7']) for h in (
            '#', 'N° OS', 'GRT', 'UNIDAD', 'CANT.', 'PESO', 'DESTINO',
            'REMITENTE', 'DESTINATARIO', 'DOC. RELACIONADO',
        )
    ]
    detail_rows = [header_row_1, header_row_2]

    for index, carrier_guide_item in enumerate(carrier_guides_qs, start=1):
        order_item = carrier_guide_item.order
        encomienda_obj = getattr(order_item, 'encomienda', None) if order_item else None

        order_number = _order_document_number(order_item) if order_item else '-'
        guide_number = carrier_guide_item.document_number()
        unit_name = _order_detail_unit_name(order_item) if order_item else 'UND'
        cantidad = _order_detail_quantity(order_item, carrier_guide_item.quantity_packages) if order_item else \
            _safe_decimal(carrier_guide_item.quantity_packages)
        peso = _safe_decimal(carrier_guide_item.total_weight)
        destino = _guide_destination_label(order_item, encomienda_obj) if order_item else '-'
        remitente = _guide_action_names(order_item, 'R') if order_item else '-'
        destinatario = _guide_action_names(order_item, 'D') if order_item else '-'
        related_doc = (carrier_guide_item.related_document or '').strip() or 'OS (sin comprobante)'

        detail_rows.append([
            str(index),
            order_number,
            guide_number,
            unit_name,
            str(cantidad.to_integral_value() if cantidad == cantidad.to_integral_value() else cantidad),
            str(round(peso, 2)),
            destino,
            Paragraph(remitente, style_l7),
            Paragraph(destinatario, style_l7),
            Paragraph(related_doc, style_l7),
        ])

    if not carrier_guides_qs:
        detail_rows.append(['-', '-', '-', '-', '-', '-', '-', 'SIN GRT EMITIDAS', '-', '-'])

    col_widths = [_bts * pct / 100 for pct in (3, 7, 10, 7, 5, 5, 10, 16, 16, 21)]
    table_detail = Table(detail_rows, colWidths=col_widths, repeatRows=2)
    table_detail.setStyle(TableStyle([
        ('SPAN', (0, 0), (6, 0)),
        ('SPAN', (7, 0), (9, 0)),
        ('BACKGROUND', (0, 0), (-1, 1), colors.lightgrey),
        ('FONTNAME', (0, 0), (-1, 1), 'Helvetica-Bold'),
        ('FONTNAME', (0, 2), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('ALIGN', (0, 0), (-1, 1), 'CENTER'),
        ('ALIGN', (0, 2), (6, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
    ]))

    _dictionary = [
        header_table,
        Spacer(1, 10),
        Paragraph('DETALLE DE GUÍAS DE REMISIÓN TRANSPORTISTA INCLUIDAS', styles['Helvetica_Bold_Center_10']),
        Spacer(1, 4),
        table_detail,
    ]

    buff = io.BytesIO()
    doc = SimpleDocTemplate(
        buff,
        pagesize=pagesize,
        rightMargin=mr,
        leftMargin=ml,
        topMargin=ms,
        bottomMargin=mi,
        title='MANIFIESTO DE CARGA-{}'.format(document_number),
    )
    doc.build(_dictionary)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="ManifiestoCarga_[{}].pdf"'.format(document_number)
    response.write(buff.getvalue())
    buff.close()
    return response
