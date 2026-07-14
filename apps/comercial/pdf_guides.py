"""Modulo unificado de PDFs de guias de remision y manifiesto de carga.

Consolida:
    - print_guide_format_tk: Guia de Remision Remitente (ticket termico).
    - print_guide_format_a4: Guia de Remision Transportista (A4).
    - print_cargo_manifest: Manifiesto de Carga (A4 horizontal).

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

    origin_route = order_obj.orderroute_set.filter(type='O').select_related('subsidiary').last()
    dest_route = order_obj.orderroute_set.filter(type='D').select_related('subsidiary').last()
    origin_label = (origin_route.subsidiary.short_name or origin_route.subsidiary.name) \
        if origin_route and origin_route.subsidiary else ''
    origin_address = (origin_route.subsidiary.address or '') if origin_route and origin_route.subsidiary else ''
    dest_label = (dest_route.subsidiary.short_name or dest_route.subsidiary.name) \
        if dest_route and dest_route.subsidiary else ''
    dest_address = (dest_route.subsidiary.address or '') if dest_route and dest_route.subsidiary else ''

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


def print_guide_format_a4(request, pk=None):  # Guia de Remision Transportista (A4)
    from .models import CarrierRemissionGuide, SenderRemissionGuide

    ml = 0.5 * inch
    mr = 0.5 * inch
    ms = 0.5 * inch
    mi = 0.5 * inch
    _bts = 8.27 * inch - ml - mr

    carrier_guide_obj = CarrierRemissionGuide.objects.select_related(
        'programming', 'programming__subsidiary', 'programming__company',
        'truck', 'truck__truck_model__truck_brand',
        'subsidiary', 'company', 'user',
    ).get(pk=pk)

    programming_obj = carrier_guide_obj.programming
    company_obj = carrier_guide_obj.company or (programming_obj.company if programming_obj else None)

    company_business_name = (company_obj.business_name if company_obj else 'RapidoVip') or 'RapidoVip'
    company_address = company_obj.address if company_obj else ''
    company_ruc = company_obj.ruc if company_obj else ''

    document_number = '{}-{}'.format(
        carrier_guide_obj.serial or '', str(carrier_guide_obj.correlative or '').zfill(6))

    emit_date = carrier_guide_obj.emit_date.strftime('%d/%m/%Y') if carrier_guide_obj.emit_date else '-'
    transfer_date = carrier_guide_obj.transfer_start_date.strftime('%d/%m/%Y') \
        if carrier_guide_obj.transfer_start_date else '-'
    total_weight = str(round(_safe_decimal(carrier_guide_obj.total_weight), 2))
    quantity_packages = str(int(round(_safe_decimal(carrier_guide_obj.quantity_packages))))
    observation = (carrier_guide_obj.observation or '').strip()

    truck_obj = carrier_guide_obj.truck or (programming_obj.truck if programming_obj else None)
    truck_plate = truck_obj.license_plate if truck_obj else '-'
    truck_brand = truck_obj.truck_model.truck_brand.name if truck_obj and truck_obj.truck_model_id else ''
    driver_name = carrier_guide_obj.driver_name or '-'
    driver_license = carrier_guide_obj.driver_license or '-'

    sender_guides_qs = list(carrier_guide_obj.sender_guides.select_related(
        'order', 'order__client').all())

    # Puntos de partida y llegada: sede de la programación y/o ruta de la primera guía remitente.
    origin_label = ''
    dest_label = ''
    if programming_obj and programming_obj.subsidiary:
        origin_label = programming_obj.subsidiary.short_name or programming_obj.subsidiary.name
    if sender_guides_qs:
        first_order = sender_guides_qs[0].order
        if not origin_label and first_order:
            first_origin_route = first_order.orderroute_set.filter(type='O').select_related('subsidiary').first()
            if first_origin_route and first_origin_route.subsidiary:
                origin_label = first_origin_route.subsidiary.short_name or first_origin_route.subsidiary.name
        if first_order:
            first_dest_route = first_order.orderroute_set.filter(type='D').select_related('subsidiary').first()
            if first_dest_route and first_dest_route.subsidiary:
                dest_label = first_dest_route.subsidiary.short_name or first_dest_route.subsidiary.name
    origin_label = origin_label or '-'
    dest_label = dest_label or '-'

    # Destinatario: si todas las guías comparten el mismo destinatario se muestra su nombre, sino "VARIOS".
    destination_names = set()
    for sender_guide_item in sender_guides_qs:
        order_item = sender_guide_item.order
        if not order_item:
            continue
        receiver_action = order_item.orderaction_set.filter(type='D').select_related(
            'client', 'order_addressee').last()
        if not receiver_action:
            continue
        if receiver_action.client:
            destination_names.add((receiver_action.client.names or '').upper())
        elif receiver_action.order_addressee:
            destination_names.add((receiver_action.order_addressee.names or '').upper())
    destination_names.discard('')
    if len(destination_names) == 1:
        destinatario_display = next(iter(destination_names))
    elif len(destination_names) > 1:
        destinatario_display = 'VARIOS'
    else:
        destinatario_display = '-'

    def _boxed_section(title, rows, col_widths):
        width_total = sum(col_widths)
        header_tbl = Table([[Paragraph(title, styles["Helvetica_Bold_Left_8"])]], colWidths=[width_total])
        header_tbl.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
            ('BOX', (0, 0), (-1, -1), 0.75, colors.black),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        body_tbl = Table(rows, colWidths=col_widths)
        body_tbl.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOX', (0, 0), (-1, -1), 0.75, colors.black),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        return [header_tbl, body_tbl]

    logo_image = _guide_logo_image(_bts * 18 / 100, 0.55 * inch)

    table_company_rows = [
        [Paragraph(company_business_name.upper(), styles["Helvetica_Bold_Left_8"])],
        [Paragraph(company_address or '', styles["Helvetica_Left_7"])],
        [Paragraph('RUC: {}'.format(company_ruc), styles["Helvetica_Left_7"])],
    ]
    table_company = Table(table_company_rows, colWidths=[_bts * 45 / 100])
    table_company.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
    ]))

    if logo_image:
        left_header_cell = Table([[logo_image, table_company]], colWidths=[_bts * 20 / 100, _bts * 45 / 100])
        left_header_cell.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ]))
    else:
        left_header_cell = table_company

    table_doc_title = Table([
        [Paragraph('RUC: {}'.format(company_ruc), styles["Helvetica_Bold_Center_8"])],
        [Paragraph('GUÍA DE REMISIÓN<br/>TRANSPORTISTA', styles["Helvetica_Bold_Center_10"])],
        [Paragraph(document_number, styles["Helvetica_Bold_Center_13"])],
    ], colWidths=[_bts * 35 / 100])
    table_doc_title.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('LINEBELOW', (0, 0), (-1, 0), 0.75, colors.black),
        ('LINEBELOW', (0, 1), (-1, 1), 0.75, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))

    table_header = Table([[left_header_cell, table_doc_title]], colWidths=[_bts * 65 / 100, _bts * 35 / 100])
    table_header.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')]))

    remitente_section = _boxed_section(
        'REMITENTE',
        [[Paragraph('RUC: {}&nbsp;&nbsp;-&nbsp;&nbsp;{}'.format(company_ruc, company_business_name.upper()),
                    styles["Helvetica_Left_8"])]],
        [_bts],
    )

    destinatario_section = _boxed_section(
        'DESTINATARIO',
        [[Paragraph(destinatario_display, styles["Helvetica_Left_8"])]],
        [_bts],
    )

    traslado_section = _boxed_section(
        'DATOS DEL TRASLADO',
        [[
            Paragraph('FECHA EMISIÓN: {}'.format(emit_date), styles["Helvetica_Left_8"]),
            Paragraph('FECHA INICIO DE TRASLADO: {}'.format(transfer_date), styles["Helvetica_Left_8"]),
        ], [
            Paragraph('PESO BRUTO TOTAL: {} KGM'.format(total_weight), styles["Helvetica_Left_8"]),
            Paragraph('NÚMERO DE BULTOS: {}'.format(quantity_packages), styles["Helvetica_Left_8"]),
        ]],
        [_bts * 50 / 100, _bts * 50 / 100],
    )

    transporte_section = _boxed_section(
        'DATOS DEL TRANSPORTE',
        [[
            Paragraph('PLACA: {}{}'.format(truck_plate, ' - ' + truck_brand if truck_brand else ''),
                      styles["Helvetica_Left_8"]),
            Paragraph('CONDUCTOR: {}'.format(driver_name), styles["Helvetica_Left_8"]),
            Paragraph('LICENCIA: {}'.format(driver_license), styles["Helvetica_Left_8"]),
        ]],
        [_bts * 34 / 100, _bts * 33 / 100, _bts * 33 / 100],
    )

    puntos_section = _boxed_section(
        'PUNTOS DE PARTIDA Y LLEGADA',
        [[
            Paragraph('PARTIDA: {}'.format(origin_label.upper()), styles["Helvetica_Left_8"]),
            Paragraph('LLEGADA: {}'.format(dest_label.upper()), styles["Helvetica_Left_8"]),
        ]],
        [_bts * 50 / 100, _bts * 50 / 100],
    )

    detail_rows = [('NRO.', 'CÓD', 'DESCRIPCIÓN', 'U/M', 'CANTIDAD')]
    related_docs = []
    for index, sender_guide_item in enumerate(sender_guides_qs, start=1):
        item_document_number = '{}-{}'.format(
            sender_guide_item.serial or '', str(sender_guide_item.correlative or '').zfill(6))
        related_docs.append('GUIA DE REMISION REMITENTE: {}'.format(item_document_number))
        cod = item_document_number if sender_guide_item.serial else str(
            sender_guide_item.order_id or sender_guide_item.pk)
        description = 'GRE {} | Remitente → Destinatario'.format(item_document_number)
        detail_rows.append((
            str(index),
            cod,
            Paragraph(description, styles["Helvetica_Left_7"]),
            'NIU',
            str(round(_safe_decimal(sender_guide_item.quantity_packages))),
        ))

    if len(detail_rows) == 1:
        detail_rows.append(('-', '-', 'SIN GUÍAS ASOCIADAS', '-', '-'))

    table_details = Table(detail_rows, colWidths=[
        _bts * 6 / 100, _bts * 18 / 100, _bts * 46 / 100, _bts * 10 / 100, _bts * 20 / 100,
    ])
    table_details.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('ALIGN', (0, 0), (1, -1), 'CENTER'),
        ('ALIGN', (3, 0), (4, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    observaciones_section = None
    if observation:
        observaciones_section = _boxed_section(
            'OBSERVACIONES',
            [[Paragraph(observation, styles["Helvetica_Justify_8"])]],
            [_bts],
        )

    documentos_section = _boxed_section(
        'DOCUMENTOS RELACIONADOS',
        [[Paragraph('<br/>'.join(related_docs) if related_docs else 'SIN GUÍAS ASOCIADAS',
                    styles["Helvetica_Left_7"])]],
        [_bts],
    )

    table_qr = Table([(qr_code(document_number), '')], colWidths=[_bts * 20 / 100, _bts * 80 / 100])
    table_qr.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))

    _dictionary = [
        table_header,
        Spacer(1, 10),
        *remitente_section,
        Spacer(1, 6),
        *destinatario_section,
        Spacer(1, 6),
        *traslado_section,
        Spacer(1, 6),
        *transporte_section,
        Spacer(1, 6),
        *puntos_section,
        Spacer(1, 10),
        Paragraph('DETALLE DE GUÍAS DE REMISIÓN REMITENTE INCLUIDAS', styles["Helvetica_Bold_Center_10"]),
        Spacer(1, 4),
        table_details,
        Spacer(1, 10),
    ]
    if observaciones_section:
        _dictionary.extend([*observaciones_section, Spacer(1, 6)])
    _dictionary.extend([*documentos_section, Spacer(1, 10)])
    _dictionary.append(Paragraph(
        'Representación impresa de la GUÍA DE REMISIÓN TRANSPORTISTA. '
        'Consulte la validez de este documento en el portal SUNAT.',
        styles["Helvetica_Justify_8"]))
    _dictionary.append(Spacer(1, 6))
    _dictionary.append(table_qr)

    buff = io.BytesIO()
    doc = SimpleDocTemplate(buff,
                            pagesize=A4,
                            rightMargin=mr,
                            leftMargin=ml,
                            topMargin=ms,
                            bottomMargin=mi,
                            title='GUIA DE REMISION TRANSPORTISTA-{}'.format(document_number)
                            )
    doc.build(_dictionary)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="GuiaRemisionTransportista_[{}].pdf"'.format(document_number)
    response.write(buff.getvalue())
    buff.close()
    return response


# ---------------------------------------------------------------------------
# Manifiesto de carga (nuevo)
# ---------------------------------------------------------------------------

def _order_document_number(order_obj):
    if order_obj and order_obj.serial and order_obj.correlative_sale:
        return '{}-{}'.format(order_obj.serial, order_obj.correlative_sale)
    return str(order_obj.id) if order_obj else '-'


def _order_detail_unit_name(order_obj):
    unit_names = [
        d.unit.name for d in order_obj.orderdetail_set.all() if d.unit_id
    ]
    if not unit_names:
        return 'UND'
    return Counter(unit_names).most_common(1)[0][0]


def _order_detail_quantity(order_obj, fallback_quantity):
    fallback_quantity = _safe_decimal(fallback_quantity)
    if fallback_quantity:
        return fallback_quantity
    total = order_obj.orderdetail_set.aggregate(s=Sum('quantity'))['s']
    return _safe_decimal(total)


def _guide_destination_label(order_obj, encomienda_obj):
    if encomienda_obj and encomienda_obj.office_destination_id:
        office = encomienda_obj.office_destination
        return office.short_name or office.name or '-'
    dest_route = order_obj.orderroute_set.filter(type='D').select_related('subsidiary').last()
    if dest_route and dest_route.subsidiary:
        return dest_route.subsidiary.short_name or dest_route.subsidiary.name or '-'
    return '-'


def _guide_destination_address(order_obj, encomienda_obj):
    if encomienda_obj and encomienda_obj.type_guide == 'R':
        return encomienda_obj.address_delivery or '-'
    if encomienda_obj and encomienda_obj.office_destination_id and encomienda_obj.office_destination.address:
        return encomienda_obj.office_destination.address
    dest_route = order_obj.orderroute_set.filter(type='D').select_related('subsidiary').last()
    if dest_route and dest_route.subsidiary and dest_route.subsidiary.address:
        return dest_route.subsidiary.address
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

    sender_guides_qs = list(
        cargo_manifest_obj.sender_guides.filter(status='I').select_related(
            'order', 'order__encomienda', 'order__encomienda__office_destination',
        ).prefetch_related(
            'order__orderdetail_set__unit',
            'order__orderaction_set__client',
            'order__orderaction_set__order_addressee',
            'order__orderroute_set__subsidiary',
        )
    )
    guides_count = cargo_manifest_obj.guides_count or len(sender_guides_qs)

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
                ('N° DE GUÍAS', guides_count),
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
        '', '', '', '', '', '', '',
        Paragraph('REMITENTE Y DESTINATARIO', styles['Helvetica_Bold_Center_8']),
        '',
    ]
    header_row_2 = [
        Paragraph(h, styles['Helvetica_Bold_Center_7']) for h in (
            '#', 'ORDEN', 'GUÍA', 'UNIDAD', 'CANT.', 'PESO', 'DESTINO', 'DIRECCIÓN',
            'REMITENTE', 'DESTINATARIO',
        )
    ]
    detail_rows = [header_row_1, header_row_2]

    for index, sender_guide_item in enumerate(sender_guides_qs, start=1):
        order_item = sender_guide_item.order
        encomienda_obj = getattr(order_item, 'encomienda', None) if order_item else None

        order_number = _order_document_number(order_item) if order_item else '-'
        guide_number = sender_guide_item.document_number()
        unit_name = _order_detail_unit_name(order_item) if order_item else 'UND'
        cantidad = _order_detail_quantity(order_item, sender_guide_item.quantity_packages) if order_item else \
            _safe_decimal(sender_guide_item.quantity_packages)
        peso = _safe_decimal(sender_guide_item.total_weight)
        destino = _guide_destination_label(order_item, encomienda_obj) if order_item else '-'
        direccion = _guide_destination_address(order_item, encomienda_obj) if order_item else '-'
        remitente = _guide_action_names(order_item, 'R') if order_item else '-'
        destinatario = _guide_action_names(order_item, 'D') if order_item else '-'

        detail_rows.append([
            str(index),
            order_number,
            guide_number,
            unit_name,
            str(cantidad.to_integral_value() if cantidad == cantidad.to_integral_value() else cantidad),
            str(round(peso, 2)),
            destino,
            Paragraph(direccion.upper(), style_l7),
            Paragraph(remitente, style_l7),
            Paragraph(destinatario, style_l7),
        ])

    if not sender_guides_qs:
        detail_rows.append(['-', '-', '-', '-', '-', '-', '-', 'SIN GUÍAS EMITIDAS', '-', '-'])

    # Más angostas: #, ORDEN, GUÍA, CANT, PESO, DESTINO | más anchas: UNIDAD, DIR, REM, DEST
    col_widths = [_bts * pct / 100 for pct in (3, 7, 9, 8, 5, 5, 8, 23, 16, 16)]
    table_detail = Table(detail_rows, colWidths=col_widths, repeatRows=2)
    table_detail.setStyle(TableStyle([
        ('SPAN', (0, 0), (7, 0)),
        ('SPAN', (8, 0), (9, 0)),
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
        Paragraph('DETALLE DE GUÍAS DE REMISIÓN REMITENTE INCLUIDAS', styles['Helvetica_Bold_Center_10']),
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
