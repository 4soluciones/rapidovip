import decimal
import os
import time
from http import HTTPStatus
# import pywintypes
import reportlab
# import cgi
# import tempfile
# import win32api
# import win32con
from django.http import HttpResponse
from reportlab.lib.pagesizes import landscape, A5, portrait, A6, A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, TableStyle, Spacer, Image, HRFlowable
from reportlab.platypus import Table
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.barcode import qr
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.lib import colors
from reportlab.lib.units import cm, inch
from reportlab.rl_settings import defaultPageSize
from rapidovip import settings
from apps.sales.format_to_dates import utc_to_local
from .models import Programming
from apps.sales.number_to_letters import numero_a_moneda
from apps.sales.models import Order, OrderAction, OrderBill, Manifest, OrderCommodity
import io
from .views import calculate_age
from .service_helpers import filter_report_orders


def _order_detail_unit_label(detail, use_description=False):
    if not detail.unit_id:
        return 'SIN UND'
    unit = detail.unit
    if use_description:
        return (unit.description or unit.name or 'SIN UND').upper()
    return (unit.name or unit.description or 'SIN UND').upper()
import datetime
from datetime import datetime, timedelta
# import win32
# import win32api
# import os, sys
# import win32print
from ..users.models import Subsidiary
from ..users.views import get_subsidiary_by_user
from django.contrib.auth.models import User

PAGE_HEIGHT = defaultPageSize[1]
PAGE_WIDTH = defaultPageSize[0]

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='Right', alignment=TA_RIGHT, leading=8, fontName='Square', fontSize=8))
styles.add(ParagraphStyle(name='Justify', alignment=TA_JUSTIFY, leading=8, fontName='Square', fontSize=8))
styles.add(ParagraphStyle(name='JustifyDesc', alignment=TA_JUSTIFY, leading=8, fontName='Square', fontSize=10))
styles.add(ParagraphStyle(name='JustifySquare', alignment=TA_JUSTIFY, leading=12, fontName='Square', fontSize=8))
styles.add(ParagraphStyle(name='LeftSquare', alignment=TA_LEFT, leading=12, fontName='Square', fontSize=13))
styles.add(ParagraphStyle(name='LeftSquareSmall', alignment=TA_LEFT, leading=9, fontName='Square', fontSize=10))
styles.add(ParagraphStyle(name='LeftSquareSmall2', alignment=TA_LEFT, leading=9, fontName='Square', fontSize=8))
styles.add(ParagraphStyle(name='Justify-Dotcirful', alignment=TA_JUSTIFY, leading=12, fontName='Dotcirful-Regular',
                          fontSize=10))
styles.add(
    ParagraphStyle(name='Justify-Dotcirful-table', alignment=TA_JUSTIFY, leading=12, fontName='Dotcirful-Regular',
                   fontSize=7))
styles.add(ParagraphStyle(name='Justify_Bold', alignment=TA_JUSTIFY, leading=8, fontName='Square-Bold', fontSize=8))
styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER, leading=8, fontName='Square', fontSize=8))
styles.add(ParagraphStyle(name='Center4', alignment=TA_CENTER, leading=10, fontName='Square-Bold',
                          fontSize=10, spaceBefore=6, spaceAfter=6))
styles.add(ParagraphStyle(name='Center5', alignment=TA_LEFT, leading=15, fontName='ticketing.regular',
                          fontSize=12))
styles.add(
    ParagraphStyle(name='Center-Dotcirful', alignment=TA_CENTER, leading=12, fontName='Dotcirful-Regular', fontSize=10))
styles.add(ParagraphStyle(name='Left', alignment=TA_LEFT, leading=8, fontName='Square', fontSize=8))
styles.add(ParagraphStyle(name='CenterTitle', alignment=TA_CENTER, leading=8, fontName='Square-Bold', fontSize=8))
styles.add(ParagraphStyle(name='CenterTitle-Dotcirful', alignment=TA_CENTER, leading=12, fontName='Dotcirful-Regular',
                          fontSize=10))
styles.add(ParagraphStyle(name='CenterTitle2', alignment=TA_CENTER, leading=8, fontName='Square-Bold', fontSize=12))
styles.add(ParagraphStyle(name='Center_Regular', alignment=TA_CENTER, leading=8, fontName='Ticketing', fontSize=10))
styles.add(ParagraphStyle(name='Center_Bold', alignment=TA_CENTER,
                          leading=8, fontName='Square-Bold', fontSize=12, spaceBefore=6, spaceAfter=6))
styles.add(ParagraphStyle(name='Center_Bold_title', alignment=TA_CENTER,
                          leading=35, fontName='Square-Bold', fontSize=55, spaceBefore=20, spaceAfter=20))
styles.add(ParagraphStyle(name='ticketing.regular', alignment=TA_CENTER,
                          leading=8, fontName='ticketing.regular', fontSize=14, spaceBefore=6, spaceAfter=6))
styles.add(ParagraphStyle(name='Center2', alignment=TA_CENTER, leading=8, fontName='Ticketing', fontSize=8))
styles.add(ParagraphStyle(name='Center3', alignment=TA_JUSTIFY, leading=8, fontName='Ticketing', fontSize=6))

styles.add(ParagraphStyle(name='Square_left', alignment=TA_LEFT, leading=8, fontName='Square', fontSize=8))
styles.add(ParagraphStyle(name='Square_right', alignment=TA_RIGHT, leading=8, fontName='Square', fontSize=8))
styles.add(ParagraphStyle(name='Square_left_2', alignment=TA_LEFT, leading=12, fontName='Square', fontSize=10))
styles.add(ParagraphStyle(name='Square_bold_left', alignment=TA_LEFT, leading=8, fontName='Square-Bold', fontSize=8))
styles.add(ParagraphStyle(name='JustifyArial', alignment=TA_JUSTIFY, leading=8, fontName='Arial_regular', fontSize=6))
styles.add(ParagraphStyle(name='title_enterprise', alignment=TA_CENTER, spaceBefore=15, spaceAfter=15,
                          leading=40, fontName='bauh', fontSize=55))
styles.add(
    ParagraphStyle(name='JustifyAllertaBig', alignment=TA_LEFT, leading=10, fontName='allerta_medium', fontSize=12))
styles.add(ParagraphStyle(name='Helvetica_Bold_Center_15', alignment=TA_CENTER, leading=15, fontName='Helvetica-Bold',
                          fontSize=15, spaceBefore=6, spaceAfter=6))
styles.add(ParagraphStyle(name='Helvetica_Bold_Center_16', alignment=TA_CENTER, leading=18, fontName='Helvetica-Bold',
                          fontSize=16, spaceBefore=6, spaceAfter=6))
styles.add(ParagraphStyle(name='Helvetica_Bold_Center_14', alignment=TA_CENTER, leading=14, fontName='Helvetica-Bold',
                          fontSize=14, spaceBefore=6, spaceAfter=6))
styles.add(ParagraphStyle(name='Helvetica_Bold_Center_13', alignment=TA_CENTER, leading=13, fontName='Helvetica-Bold',
                          fontSize=13, spaceBefore=6, spaceAfter=6))
styles.add(
    ParagraphStyle(name='Helvetica_Bold_Left_8', alignment=TA_LEFT, leading=8, fontName='Helvetica-Bold', fontSize=7.4))
styles.add(ParagraphStyle(name='Helvetica_Bold_Center_10', alignment=TA_CENTER, leading=11, fontName='Helvetica-Bold',
                          fontSize=10))
styles.add(ParagraphStyle(name='Helvetica_Bold_Left_7', alignment=TA_LEFT, leading=8, fontName='Helvetica-Bold', fontSize=7))
styles.add(ParagraphStyle(name='Helvetica_Bold_Right_8', alignment=TA_RIGHT, leading=8, fontName='Helvetica-Bold', fontSize=8))
styles.add(ParagraphStyle(name='Helvetica_Left_7', alignment=TA_LEFT, leading=8, fontName='Helvetica', fontSize=7))
styles.add(ParagraphStyle(name='Helvetica_Left_8', alignment=TA_LEFT, leading=8, fontName='Helvetica', fontSize=8))
styles.add(ParagraphStyle(name='Helvetica_Left_8_leading_10', alignment=TA_LEFT, leading=10, fontName='Helvetica', fontSize=8))
styles.add(ParagraphStyle(name='Helvetica_Center_7', alignment=TA_CENTER, leading=8, fontName='Helvetica', fontSize=7))
styles.add(ParagraphStyle(name='Helvetica_Center_8', alignment=TA_CENTER, leading=8, fontName='Helvetica', fontSize=8))
styles.add(ParagraphStyle(name='Helvetica_Justify_8', alignment=TA_JUSTIFY, leading=8, fontName='Helvetica', fontSize=8))
styles.add(ParagraphStyle(name='Helvetica_Bold_Center_7', alignment=TA_CENTER, leading=8, fontName='Helvetica-Bold', fontSize=7))
styles.add(ParagraphStyle(name='Helvetica_Bold_Center_8', alignment=TA_CENTER, leading=8, fontName='Helvetica-Bold', fontSize=8))
styles.add(ParagraphStyle(name='Helvetica_Bold_Center_8_leading', alignment=TA_CENTER, leading=6, fontName='Helvetica-Bold', fontSize=8))
styles.add(ParagraphStyle(name='Helvetica_Bold_Center_12', alignment=TA_CENTER, leading=12, fontName='Helvetica-Bold', fontSize=12))
styles.add(ParagraphStyle(name='Helvetica_Bold_Center_12_leading', alignment=TA_CENTER, leading=8, fontName='Helvetica-Bold', fontSize=12))
styles.add(ParagraphStyle(name='Helvetica_Bold_Center_13_bg', alignment=TA_CENTER, leading=13, fontName='Helvetica-Bold', fontSize=13))
styles.add(ParagraphStyle(name='Helvetica_Bold_Center_14_bg', alignment=TA_CENTER, leading=14, fontName='Helvetica-Bold', fontSize=14))
styles.add(ParagraphStyle(name='Helvetica_Bold_Center_15_bg', alignment=TA_CENTER, leading=15, fontName='Helvetica-Bold', fontSize=15))
styles.add(ParagraphStyle(name='Helvetica_Bold_Center_16_bg', alignment=TA_CENTER, leading=18, fontName='Helvetica-Bold', fontSize=16))
styles.add(ParagraphStyle(name='Helvetica_Bold_Left_8_bg', alignment=TA_LEFT, leading=8, fontName='Helvetica-Bold', fontSize=8))
styles.add(ParagraphStyle(name='Helvetica_Bold_Center_10_bg', alignment=TA_CENTER, leading=11, fontName='Helvetica-Bold', fontSize=10))

style = styles["Normal"]

reportlab.rl_config.TTFSearchPath.append(str(settings.BASE_DIR) + '/static/fonts')
pdfmetrics.registerFont(TTFont('Square', 'square-721-condensed-bt.ttf'))
pdfmetrics.registerFont(TTFont('Square-Bold', 'sqr721bc.ttf'))
pdfmetrics.registerFont(TTFont('Newgot', 'newgotbc.ttf'))
pdfmetrics.registerFont(TTFont('Ticketing', 'ticketing.regular.ttf'))
pdfmetrics.registerFont(TTFont('Lucida-Console', 'lucida-console.ttf'))
pdfmetrics.registerFont(TTFont('Square-Dot', 'square_dot_digital-7.ttf'))
pdfmetrics.registerFont(TTFont('Serif-Dot', 'serif_dot_digital-7.ttf'))
pdfmetrics.registerFont(TTFont('Enhanced-Dot-Digital', 'enhanced-dot-digital-7.regular.ttf'))
pdfmetrics.registerFont(TTFont('Merchant-Copy-Wide', 'MerchantCopyWide.ttf'))
pdfmetrics.registerFont(TTFont('Dot-Digital', 'dot_digital-7.ttf'))
pdfmetrics.registerFont(TTFont('Raleway-Dots-Regular', 'RalewayDotsRegular.ttf'))
pdfmetrics.registerFont(TTFont('Ordre-Depart', 'Ordre-de-Depart.ttf'))
pdfmetrics.registerFont(TTFont('Dotcirful-Regular', 'DotcirfulRegular.otf'))
pdfmetrics.registerFont(TTFont('Nationfd', 'Nationfd.ttf'))
pdfmetrics.registerFont(TTFont('Kg-Primary-Dots', 'KgPrimaryDots-Pl0E.ttf'))
pdfmetrics.registerFont(TTFont('Dot-line', 'Dotline-LA7g.ttf'))
pdfmetrics.registerFont(TTFont('Dot-line-Light', 'DotlineLight-XXeo.ttf'))
pdfmetrics.registerFont(TTFont('Jd-Lcd-Rounded', 'JdLcdRoundedRegular-vXwE.ttf'))
pdfmetrics.registerFont(TTFont('ticketing.regular', 'ticketing.regular.ttf'))
pdfmetrics.registerFont(TTFont('allerta_medium', 'allerta_medium.ttf'))
pdfmetrics.registerFont(TTFont('Arial_regular', 'allerta_medium.ttf'))
# pdfmetrics.registerFont(TTFont('bauhaus_regular', 'Bauhaus_93_Regular.ttf'))
pdfmetrics.registerFont(TTFont('bauh', 'BAUHS93.ttf'))
# pdfmetrics.registerFont(TTFont('Romanesque_Serif', 'Romanesque Serif.ttf'))

style_defs = [
    ('Helvetica_Bold_Center_15', 'Helvetica_Bold_Center_15_bg'),
    ('Helvetica_Bold_Center_16', 'Helvetica_Bold_Center_16_bg'),
    ('Helvetica_Bold_Center_14', 'Helvetica_Bold_Center_14_bg'),
    ('Helvetica_Bold_Center_13', 'Helvetica_Bold_Center_13_bg'),
    ('Helvetica_Bold_Left_8', 'Helvetica_Bold_Left_8_bg'),
    ('Helvetica_Bold_Center_10', 'Helvetica_Bold_Center_10_bg'),
]

logo = "static/assets/rapidovip_logo.png"

style_custom_left = ParagraphStyle(
    name='custom_left',
    fontName='Helvetica',
    fontSize=8,
    leading=10,
    alignment=TA_LEFT,
)
style_custom_right = ParagraphStyle(
    name='custom_right',
    fontName='Helvetica',
    fontSize=8,
    leading=10,
    alignment=TA_RIGHT,
)


def _programming_subsidiary_label(programming_obj):
    if programming_obj and programming_obj.subsidiary:
        return programming_obj.subsidiary.short_name or programming_obj.subsidiary.name
    return '—'


def _programming_pilot_name(programming_obj):
    if programming_obj and programming_obj.support_pilot:
        return programming_obj.support_pilot
    return '—'


def _passenger_pdf_unavailable():
    return HttpResponse(
        'La funcionalidad de pasajeros no está disponible.',
        status=410,
        content_type='text/plain',
    )


def _is_pending_destination_payment(order_obj):
    """Pago destino aún no cobrado en sede (sin OrderBill asociado)."""
    if order_obj.way_to_pay != 'D' or order_obj.status == 'A':
        return False
    if getattr(order_obj, 'orderbill', None) is not None:
        return False
    return not OrderBill.objects.filter(order_id=order_obj.pk).exists()


def _print_destination_delivery_ticket(request, order_obj, pk):
    """
    Constancia de entrega para encomiendas con pago pendiente en destino.
    Basada en la orden de servicio, simplificada para firma en recepción.
    """
    from .pdf_service_guides import _separator

    encomienda = getattr(order_obj, 'encomienda', None)
    _wt = 2.83 * inch - 4 * 0.05 * inch

    company_obj = order_obj.company
    company_name = 'RAPIDOVIP'
    if company_obj:
        company_name = (company_obj.business_name or company_obj.short_name or 'RAPIDOVIP').upper()

    carrier_guide = getattr(order_obj, 'carrier_guide', None)
    grt_number = carrier_guide.document_number() if carrier_guide else '—'

    _date_convert_zone = utc_to_local(order_obj.create_at)
    _formatdate = _date_convert_zone.strftime('%d/%m/%Y')
    _transfer_date_txt = (
        order_obj.transfer_date.strftime('%d/%m/%Y') if order_obj.transfer_date else '-'
    )
    _delivery_date_txt = '-'
    if carrier_guide and carrier_guide.programming_id and carrier_guide.programming:
        arrival = carrier_guide.programming.arrival_date
        if arrival:
            _delivery_date_txt = arrival.strftime('%d/%m/%Y')

    h_left = ParagraphStyle(
        name='DeliveryHelvLeft', fontName='Helvetica', fontSize=8, leading=10, alignment=TA_LEFT)
    h_company = ParagraphStyle(
        name='DeliveryHelvCompany', fontName='Helvetica', fontSize=6.5, leading=8, alignment=TA_CENTER)
    h_subsidiary = ParagraphStyle(
        name='DeliveryHelvSubsidiary', fontName='Helvetica-Bold', fontSize=9, leading=11, alignment=TA_LEFT)
    h_date = ParagraphStyle(
        name='DeliveryHelvDate', fontName='Helvetica', fontSize=6, leading=8, alignment=TA_LEFT)
    h_section = ParagraphStyle(
        name='DeliveryHelvSection', fontName='Helvetica-Bold', fontSize=7, leading=9, alignment=TA_LEFT)
    h_entrega = ParagraphStyle(
        name='DeliveryHelvEntrega', fontName='Helvetica', fontSize=6.5, leading=8, alignment=TA_LEFT)
    h_desc = ParagraphStyle(
        name='DeliveryHelvDesc', fontName='Helvetica', fontSize=6.5, leading=8, alignment=TA_LEFT)
    h_desc_right = ParagraphStyle(
        name='DeliveryHelvDescRight', fontName='Helvetica', fontSize=6.5, leading=8, alignment=TA_RIGHT)
    h_person = ParagraphStyle(
        name='DeliveryHelvPerson', fontName='Helvetica', fontSize=7, leading=9, alignment=TA_LEFT)
    h_person_right = ParagraphStyle(
        name='DeliveryHelvPersonRight', fontName='Helvetica', fontSize=7, leading=9, alignment=TA_RIGHT)
    h_grt = ParagraphStyle(
        name='DeliveryHelvGRT', fontName='Helvetica-Bold', fontSize=14, leading=16, alignment=TA_CENTER)
    h_sign = ParagraphStyle(
        name='DeliveryHelvSign', fontName='Helvetica', fontSize=7, leading=9, alignment=TA_CENTER)

    colwiths_table = [_wt * 50 / 100, _wt * 50 / 100]

    my_style_dates = [
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 0.3),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), -2),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
    ]
    my_style_section = [
        ('LEFTPADDING', (0, 0), (-1, -1), 0.3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]
    my_style_table = [
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), -4),
        ('ALIGNMENT', (1, 0), (1, 0), 'RIGHT'),
        ('LEFTPADDING', (0, 0), (0, -1), 0.3),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]
    my_style_person_sender = my_style_table + [('SPAN', (0, 0), (1, 0))]
    my_style_table2 = [
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('LEFTPADDING', (0, 0), (0, -1), 0.3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), -4),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]
    my_style_table3 = [
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 6.5),
        ('ALIGNMENT', (1, 0), (1, -1), 'CENTER'),
        ('ALIGNMENT', (2, 0), (2, -1), 'CENTER'),
        ('ALIGNMENT', (3, 0), (3, -1), 'CENTER'),
        ('ALIGNMENT', (4, 0), (4, -1), 'RIGHT'),
        ('LEFTPADDING', (0, 0), (0, -1), 0.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), -4),
        ('TOPPADDING', (0, 0), (-1, -1), -1),
        ('RIGHTPADDING', (4, 0), (4, -1), 0.5),
    ]
    my_style_table4 = [
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 6.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('LEFTPADDING', (0, 0), (0, -1), 0.3),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGNMENT', (1, 0), (1, -1), 'CENTER'),
        ('ALIGNMENT', (2, 0), (2, -1), 'CENTER'),
        ('ALIGNMENT', (3, 0), (3, -1), 'CENTER'),
        ('ALIGNMENT', (4, 0), (4, -1), 'RIGHT'),
        ('RIGHTPADDING', (4, 0), (4, -1), 0.5),
    ]
    my_style_table5 = [
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('FONTSIZE', (3, 0), (3, -1), 10),
        ('FONTNAME', (3, 0), (3, -1), 'Helvetica-Bold'),
        ('RIGHTPADDING', (2, 0), (2, -1), 6),
        ('ALIGNMENT', (2, 0), (2, -1), 'RIGHT'),
        ('RIGHTPADDING', (3, 0), (3, -1), 0.3),
        ('ALIGNMENT', (3, 0), (3, -1), 'RIGHT'),
        ('LEFTPADDING', (0, 0), (0, -1), 0.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), -6),
    ]

    ana_c1 = Table([
        [Paragraph('FECHA EMISIÓN: ' + str(_formatdate), h_date)],
        [Paragraph('FECHA TRASLADO: ' + str(_transfer_date_txt), h_date)],
        [Paragraph('FECHA ENTREGA: ' + str(_delivery_date_txt), h_date)],
    ], colWidths=[_wt])
    ana_c1.setStyle(TableStyle(my_style_dates))

    def _section_title(text):
        tbl = Table([[Paragraph(text, h_section)]], colWidths=[_wt])
        tbl.setStyle(TableStyle(my_style_section))
        return tbl

    _destination_office = encomienda.office_destination if encomienda else None
    subsidiary_address = '-'
    if _destination_office:
        subsidiary_address = (
            (_destination_office.address or _destination_office.short_name or '-').strip().upper()
        )
    ana_subsidiary = Table([[Paragraph(subsidiary_address, h_subsidiary)]], colWidths=[_wt])
    ana_subsidiary.setStyle(TableStyle(my_style_section))

    order_action_sender_obj = OrderAction.objects.get(order=order_obj, type='R')
    _sender_qr = ''
    _sender_document_qr = ''
    _sender_phone_qr = ''

    if order_action_sender_obj.client:
        document_sender = str(
            order_action_sender_obj.client.clienttype_set.first().document_type.short_description)
        _sender_document_qr = order_action_sender_obj.client.clienttype_set.first().document_number
        _sender_phone_qr = order_action_sender_obj.client.phone or ''
        _sender_qr = str(order_action_sender_obj.client.names)
        td_sender = (Paragraph('REMITENTE: ' + str(order_action_sender_obj.client.names), h_person), '')
        if order_action_sender_obj.client.phone:
            td_sender_document = (
                Paragraph(
                    document_sender + ': ' + str(
                        order_action_sender_obj.client.clienttype_set.first().document_number),
                    h_person),
                Paragraph('TELEFONO: ' + str(order_action_sender_obj.client.phone), h_person_right))
        else:
            td_sender_document = (
                Paragraph(
                    document_sender + ': ' + str(
                        order_action_sender_obj.client.clienttype_set.first().document_number),
                    h_person),
                '')
        ana_c3 = Table([td_sender] + [td_sender_document], colWidths=colwiths_table)
        ana_c3.setStyle(TableStyle(my_style_person_sender))
    else:
        _sender_qr = str(order_action_sender_obj.order_addressee.names.upper())
        _sender_phone_qr = str(order_action_sender_obj.order_addressee.phone or '')
        td_sender = (
            Paragraph('REMITENTE: ' + str(order_action_sender_obj.order_addressee.names.upper()), h_person),
            '')
        if order_action_sender_obj.order_addressee.phone:
            td_sender_document = (
                Paragraph('DNI: ', h_person),
                Paragraph(
                    'TELEFONO: ' + str(order_action_sender_obj.order_addressee.phone), h_person_right))
        else:
            td_sender_document = (Paragraph('DNI: ', h_person), '')
        ana_c3 = Table([td_sender] + [td_sender_document], colWidths=colwiths_table)
        ana_c3.setStyle(TableStyle(my_style_person_sender))

    recipients = OrderAction.objects.filter(order=order_obj, type='D')
    _rows = []
    _recipients_names_qr = []
    _recipients_phone_qr = []
    _recipients_nro_document_qr = []
    first_recipient_name = ''
    first_recipient_doc = ''
    for d in recipients:
        _phone = ''
        if d.client is None:
            _names = (d.order_addressee.names or '').upper()
            _phone = d.order_addressee.phone or ''
            _rows.append((Paragraph('DESTINATARIO: ' + _names, h_person), ''))
            if _phone:
                _rows.append((
                    Paragraph('DNI: ', h_person),
                    Paragraph('TELEFONO: ' + str(_phone), h_person_right)))
            else:
                _rows.append((Paragraph('DNI: ', h_person), ''))
            _recipients_names_qr.append(str(_names))
            _recipients_phone_qr.append(str(_phone))
            if not first_recipient_name:
                first_recipient_name = _names
                first_recipient_doc = 'DNI: —'
        else:
            if d.client.phone is not None:
                _phone = d.client.phone
            _names = (d.client.names or '').upper()
            _doc_type = d.client.clienttype_set.first().document_type.short_description
            _doc_number = d.client.clienttype_set.first().document_number
            _rows.append((Paragraph('DESTINATARIO: ' + _names, h_person), ''))
            if _phone:
                _rows.append((
                    Paragraph(_doc_type + ': ' + str(_doc_number), h_person),
                    Paragraph('TELEFONO: ' + str(_phone), h_person_right)))
            else:
                _rows.append((Paragraph(_doc_type + ': ' + str(_doc_number), h_person), ''))
            _recipients_names_qr.append(str(_names))
            _recipients_phone_qr.append(str(_phone))
            _recipients_nro_document_qr.append(str(_doc_number))
            if not first_recipient_name:
                first_recipient_name = _names
                first_recipient_doc = f'{_doc_type}: {_doc_number}'

    if not _rows:
        _rows = [(Paragraph('DESTINATARIO: -', h_person), '')]
        first_recipient_name = '-'
        first_recipient_doc = 'DNI: —'
    ana_c4 = Table(_rows, colWidths=colwiths_table)
    _name_row_spans = [('SPAN', (0, i), (1, i)) for i in range(0, len(_rows), 2)]
    ana_c4.setStyle(TableStyle(my_style_table + _name_row_spans))

    is_reparto = bool(
        encomienda
        and encomienda.type_guide == 'R'
        and (encomienda.address_delivery or '').strip()
    )
    delivery_address = (
        (encomienda.address_delivery or '').strip().upper()
        if is_reparto else 'ENTREGAR EN AGENCIA'
    )
    ana_entrega = Table([
        (Paragraph('<b>DIRECCIÓN:</b> ' + delivery_address, h_entrega),),
        (Paragraph('<b>DESTINATARIO:</b> ' + first_recipient_name, h_entrega),),
        (Paragraph(first_recipient_doc, h_entrega),),
    ], colWidths=[_wt])
    ana_entrega.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 0.3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    col_detail = [
        _wt * 38 / 100,
        _wt * 12 / 100,
        _wt * 12 / 100,
        _wt * 16 / 100,
        _wt * 22 / 100,
    ]
    ana_c6 = Table(
        [('DESCRIPCIÓN', 'CANT', 'UM', 'PESO', 'SUBTOTAL')], colWidths=col_detail)
    ana_c6.setStyle(TableStyle(my_style_table3))

    total = 0
    _rows_detail = []
    _details_q_qr = []
    _details_d_qr = []
    _detail_amount = ''
    for d in order_obj.orderdetail_set.all():
        P0 = Paragraph(d.description.upper(), h_desc)
        _weight = getattr(d, 'weight', None)
        weight_txt = str(round(_weight, 2)) if _weight not in (None, '') else '0'
        _rows_detail.append((
            P0,
            str(decimal.Decimal(round(d.quantity))),
            _order_detail_unit_label(d),
            weight_txt,
            Paragraph(str(round(d.amount, 2)), h_desc_right),
        ))
        base_total = d.quantity * d.price_unit
        total = total + base_total
        _details_q_qr.append(str(round(d.quantity)))
        _details_d_qr.append(d.description.upper())
        _detail_amount = str(round(d.amount, 2))

    ana_c7 = Table(_rows_detail, colWidths=col_detail, rowHeights=0.28 * inch)
    ana_c7.setStyle(TableStyle(my_style_table4))

    ana_c8 = Table(
        [('IMPORTE TOTAL', '', 'S/', str(decimal.Decimal(round(total, 2))))],
        colWidths=[_wt * 60 / 100, _wt * 10 / 100, _wt * 17 / 100, _wt * 13 / 100])
    ana_c8.setStyle(TableStyle(my_style_table5))

    current_time = datetime.now()
    _format_current_time = current_time.strftime('%d/%m/%Y %I:%M:%S %p')
    _formattime = _date_convert_zone.time().strftime('%I:%M:%S %p')
    _create_date = (
        (order_obj.transfer_date.strftime('%d/%m/%Y') if order_obj.transfer_date else _formatdate)
        + ' ' + str(_formattime)
    )
    correlative = order_obj.order_correlative or order_obj.correlative_sale or ''
    serie = order_obj.order_serial or order_obj.serial or ''
    _origin_office = encomienda.office_origin if encomienda else None
    origin = str(_origin_office.short_name if _origin_office else '-')
    destiny = str(_destination_office.short_name if _destination_office else '-')
    _user_qr = str(order_obj.user.username.upper()) if order_obj.user_id else ''
    datatable = (
        str(_format_current_time) + ',' + str(serie) + ',' + str(correlative) + ',' +
        str(_create_date) + ',' + str(_sender_qr) + ',' + str(_sender_phone_qr) + ',' +
        str(_sender_document_qr) + ',' +
        ', '.join(item.strip() for item in _recipients_names_qr) + ',' +
        ', '.join(item.strip() for item in _recipients_phone_qr) + ',' +
        ', '.join(item.strip() for item in _recipients_nro_document_qr) + ',' +
        ', '.join(item.strip() for item in _details_q_qr) + ',' +
        ', '.join(item.strip() for item in _details_d_qr) + ',' +
        'PAGO DESTINO,' + str(_detail_amount) + ',' + _user_qr + ',' + origin + ',' + destiny
    )

    _qr_widget = qr.QrCodeWidget(datatable)
    _qr_bounds = _qr_widget.getBounds()
    _qr_w = _qr_bounds[2] - _qr_bounds[0]
    _qr_h = _qr_bounds[3] - _qr_bounds[1]
    _qr_size = 2.2 * cm
    _qr_drawing = Drawing(
        _qr_size, _qr_size,
        transform=[_qr_size / _qr_w, 0, 0, _qr_size / _qr_h, 0, 0])
    _qr_drawing.add(_qr_widget)
    _qr_box = Table([[_qr_drawing]], colWidths=[_qr_size + 6])
    _qr_box.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.6, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    ana_c9 = Table([[_qr_box]], colWidths=[_wt])
    ana_c9.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    ana_firma = Table([
        [Paragraph('____________________', h_sign),
         Paragraph('____________________', h_sign)],
        [Paragraph('Firma', h_sign),
         Paragraph('Documento de identidad', h_sign)],
    ], colWidths=colwiths_table)
    ana_firma.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, 0), 28),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 2),
        ('TOPPADDING', (0, 1), (-1, 1), 2),
    ]))

    observation = (getattr(order_obj, 'observation', None) or '').strip()

    buff = io.BytesIO()
    doc = SimpleDocTemplate(
        buff,
        pagesize=(2.83 * inch, 11.6 * inch),
        rightMargin=0.0 * inch,
        leftMargin=0.0 * inch,
        topMargin=0.0 * inch,
        bottomMargin=0.039 * inch,
        title='CONSTANCIA DE ENTREGA',
    )

    dictionary = [
        Spacer(1, 10),
        Paragraph(company_name, h_company),
        Spacer(4, 4),
        Paragraph(str(grt_number), h_grt),
        Spacer(6, 6),
        ana_c1,
        Spacer(6, 6),
        Paragraph(subsidiary_address, h_subsidiary),
        Spacer(6, 6),
        _separator(_wt),
        Spacer(2, 2),
        _section_title('DATOS DEL REMITENTE'),
        Spacer(1, 1),
        ana_c3,
        Spacer(6, 6),
        _separator(_wt),
        Spacer(2, 2),
        _section_title('DATOS DEL DESTINATARIO'),
        Spacer(1, 1),
        ana_c4,
        Spacer(6, 6),
        _separator(_wt),
        Spacer(2, 2),
        _section_title('ENTREGA'),
        Spacer(2, 2),
        ana_entrega,
        Spacer(6, 6),
        _separator(_wt),
        Spacer(2, 2),
        ana_c6,
        Spacer(4, 4),
        _separator(_wt),
        Spacer(2, 2),
        ana_c7,
        Spacer(6, 6),
        _separator(_wt),
        Spacer(2, 2),
        ana_c8,
    ]
    if observation:
        dictionary.extend([
            Spacer(6, 6),
            _separator(_wt),
            Spacer(2, 2),
            _section_title('OBSERVACIÓN:'),
            Spacer(2, 2),
            Paragraph(observation.upper(), h_left),
        ])
    dictionary.extend([
        Spacer(8, 8),
        ana_c9,
        Spacer(10, 10),
        _separator(_wt),
        Spacer(2, 2),
        Paragraph('FIRMA Y DOCUMENTO DE IDENTIDAD', styles['Helvetica_Bold_Center_8']),
        Spacer(30, 30),
        ana_firma,
    ])

    doc.build(dictionary)

    response = HttpResponse(content_type='application/pdf')
    _disposition = 'attachment' if request.GET.get('download') else 'inline'
    response['Content-Disposition'] = '{}; filename="CONSTANCIA ENTREGA {}.pdf"'.format(
        _disposition, grt_number)
    tomorrow = datetime.now() + timedelta(days=1)
    tomorrow = tomorrow.replace(hour=0, minute=0, second=0)
    expires = datetime.strftime(tomorrow, '%a, %d-%b-%Y %H:%M:%S GMT')
    response.set_cookie('ware', value=pk, expires=expires)
    response.write(buff.getvalue())
    buff.close()
    return response


def print_ticket_order_commodity(request, pk=None):  # Ticket/Guia de encomienda
    order_obj = Order.objects.select_related(
        'encomienda',
        'encomienda__office_origin',
        'encomienda__office_destination',
        'company',
        'user',
        'orderbill',
        'carrier_guide',
        'carrier_guide__programming',
    ).get(pk=pk)
    encomienda = getattr(order_obj, 'encomienda', None)
    if order_obj.service_type != 'E':
        from .pdf_service_guides import build_ticket_for_service
        return build_ticket_for_service(order_obj, pk, request)

    force_delivery = (request.GET.get('delivery') or '').strip() in ('1', 'true', 'yes')
    if force_delivery or _is_pending_destination_payment(order_obj):
        return _print_destination_delivery_ticket(request, order_obj, pk)

    tbh_business_name_address = ''

    # _wt = 2.57 * inch - 5 * 0.05 * inch  #  TIKETERRA
    # _wt = 2.55 * inch - 4 * 0.05 * inch  # ticket normal
    _wt = 2.83 * inch - 4 * 0.05 * inch  # termical
    # _wt = 3.11 * inch

    order_action_sender_obj = OrderAction.objects.get(order=order_obj, type='R')

    company_obj = order_obj.company
    brand_title = 'RAPIDOVIP'
    if company_obj:
        brand_title = (company_obj.short_name or company_obj.business_name or 'RAPIDOVIP').upper()

    subsidiary_phones = []
    for sub in Subsidiary.objects.exclude(phone__isnull=True).exclude(phone='').order_by('name'):
        subsidiary_phones.append((sub.name, sub.phone))

    ruc_text = ''
    if company_obj:
        _address_line = (company_obj.address or '').strip()
        _company_lines = [company_obj.business_name or company_obj.short_name or '']
        if _address_line:
            _company_lines.append(_address_line)
        tbh_business_name_address = '\n'.join([_line for _line in _company_lines if _line])
        ruc_text = 'RUC: ' + (company_obj.ruc or '')

    name_document = 'ORDEN DE SERVICIO'
    # Preferir serie/correlativo de la orden de servicio (todas las encomiendas lo tienen).
    # En al contado, serial/correlative_sale corresponden a boleta/factura.
    serie = order_obj.order_serial or order_obj.serial or ''
    # colwiths_table = [2.57 / 2.2 * inch, 2.57 / 2.2 * inch]
    colwiths_table = [_wt * 50 / 100, _wt * 50 / 100]
    correlative = order_obj.order_correlative or order_obj.correlative_sale

    from .pdf_service_guides import _separator, _brand_logo
    logo_img = _brand_logo(_wt * 0.55, 0.6 * inch)
    date = order_obj.create_at.date()
    _date_convert_zone = utc_to_local(order_obj.create_at)
    date_hour = _date_convert_zone.time()
    _formatdate = _date_convert_zone.strftime("%d/%m/%Y")
    _formattime = date_hour.strftime("%I:%M:%S %p")

    # Estilos Helvetica exclusivos de este ticket
    h_left = ParagraphStyle(
        name='TicketHelvLeft', fontName='Helvetica', fontSize=8, leading=10, alignment=TA_LEFT)
    h_center = ParagraphStyle(
        name='TicketHelvCenter', fontName='Helvetica', fontSize=8, leading=10, alignment=TA_CENTER)
    h_center_7 = ParagraphStyle(
        name='TicketHelvCenter7', fontName='Helvetica', fontSize=7, leading=9, alignment=TA_CENTER)
    h_justify = ParagraphStyle(
        name='TicketHelvJustify', fontName='Helvetica', fontSize=8, leading=10, alignment=TA_JUSTIFY)
    h_desc = ParagraphStyle(
        name='TicketHelvDesc', fontName='Helvetica', fontSize=6.5, leading=8, alignment=TA_LEFT)
    h_desc_right = ParagraphStyle(
        name='TicketHelvDescRight', fontName='Helvetica', fontSize=6.5, leading=8, alignment=TA_RIGHT)
    h_person = ParagraphStyle(
        name='TicketHelvPerson', fontName='Helvetica', fontSize=7, leading=9, alignment=TA_LEFT)
    h_person_right = ParagraphStyle(
        name='TicketHelvPersonRight', fontName='Helvetica', fontSize=7, leading=9, alignment=TA_RIGHT)
    h_terms = ParagraphStyle(
        name='TicketHelvTerms', fontName='Helvetica', fontSize=6, leading=8, alignment=TA_JUSTIFY)
    h_serie = ParagraphStyle(
        name='TicketHelvSerie', fontName='Helvetica-Bold', fontSize=10, leading=11, alignment=TA_CENTER)

    rows = []

    if encomienda and encomienda.code_track:
        service_order_number = (
            str(order_obj.order_correlative).lstrip('0') or '0'
            if order_obj.order_correlative
            else str(order_obj.id)
        )
        td_code_track = (
            Paragraph('<b>NRO. ORDEN:</b> ' + service_order_number, style_custom_left),
            Paragraph('<b>CÓDIGO:</b> ' + str(encomienda.code_track), style_custom_right)
        )
        rows.append(td_code_track)

    td_date = ('FECHA EMISIÓN: ' + str(_formatdate), 'HORA: ' + str(_formattime))
    _transfer_date_txt = (
        order_obj.transfer_date.strftime("%d/%m/%Y") if order_obj.transfer_date else '-'
    )
    td_transfer = ('FECHA TRASLADO: ' + _transfer_date_txt, '')

    _date_row_idx = len(rows)  # fila de FECHA EMISIÓN (después del NRO. ORDEN si existe)
    rows.append(td_date)
    rows.append(td_transfer)
    ana_c1 = Table(rows, colWidths=colwiths_table)

    my_style_table_title = [
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('LEFTPADDING', (0, 0), (0, -1), 0.3),  # primera columna
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), -7),  # filas más pegadas entre sí
        ('TOPPADDING', (0, _date_row_idx), (-1, _date_row_idx), 8),  # separa FECHA EMISIÓN de la fila de arriba
        ('ALIGNMENT', (1, 0), (1, -1), 'RIGHT'),  # segunda columna
    ]
    my_style_table = [
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), -4),
        ('ALIGNMENT', (1, 1), (1, 1), 'RIGHT'),
        ('ALIGNMENT', (1, 0), (1, 0), 'RIGHT'),
        ('LEFTPADDING', (0, 0), (0, -1), 0.3),  # first column
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]
    # Las filas de nombre (remitente/destinatario) ocupan ambas columnas para
    # que el texto use todo el ancho y solo baje de línea cuando no entre.
    my_style_person_sender = my_style_table + [('SPAN', (0, 0), (1, 0))]

    my_style_table2 = [
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('LEFTPADDING', (0, 0), (0, -1), 0.3),  # first column
        ('BOTTOMPADDING', (0, 0), (-1, -1), -6),  # filas más pegadas
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]
    my_style_code = [
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (0, -1), 0.3),  # first column
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]
    my_style_hour_arrival = [
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('LEFTPADDING', (0, 0), (0, -1), 0.3),  # first column
        ('BOTTOMPADDING', (0, 0), (-1, -1), -2),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]
    # Columnas detalle: DESCRIPCIÓN | CANT | UM | PESO | SUBTOTAL
    my_style_table3 = [
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 6.5),
        ('ALIGNMENT', (1, 0), (1, -1), 'CENTER'),  # cant
        ('ALIGNMENT', (2, 0), (2, -1), 'CENTER'),  # um
        ('ALIGNMENT', (3, 0), (3, -1), 'CENTER'),  # peso
        ('ALIGNMENT', (4, 0), (4, -1), 'RIGHT'),  # subtotal
        ('LEFTPADDING', (0, 0), (0, -1), 0.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), -4),
        ('TOPPADDING', (0, 0), (-1, -1), -1),
        ('RIGHTPADDING', (4, 0), (4, -1), 0.5),
    ]
    my_style_table4 = [
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 6.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('LEFTPADDING', (0, 0), (0, -1), 0.3),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGNMENT', (1, 0), (1, -1), 'CENTER'),  # cant
        ('ALIGNMENT', (2, 0), (2, -1), 'CENTER'),  # um
        ('ALIGNMENT', (3, 0), (3, -1), 'CENTER'),  # peso
        ('ALIGNMENT', (4, 0), (4, -1), 'RIGHT'),  # subtotal
        ('RIGHTPADDING', (4, 0), (4, -1), 0.5),
    ]
    my_style_table5 = [
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('FONTSIZE', (3, 0), (3, -1), 10),
        ('FONTNAME', (3, 0), (3, -1), 'Helvetica-Bold'),
        ('RIGHTPADDING', (2, 0), (2, -1), 6),  # separa S/ del número
        ('ALIGNMENT', (2, 0), (2, -1), 'RIGHT'),  # third column
        ('RIGHTPADDING', (3, 0), (3, -1), 0.3),  # four column
        ('ALIGNMENT', (3, 0), (3, -1), 'RIGHT'),  # four column
        ('LEFTPADDING', (0, 0), (0, -1), 0.5),  # first column
        ('BOTTOMPADDING', (0, 0), (-1, -1), -6),
    ]

    ana_c1.setStyle(TableStyle(my_style_table_title))

    document_sender = ''
    _sender_qr = ''
    _sender_document_qr = ''
    _sender_phone_qr = ''
    if order_action_sender_obj.client:

        document_sender = str(order_action_sender_obj.client.clienttype_set.first().document_type.short_description)
        _sender_document_qr = order_action_sender_obj.client.clienttype_set.first().document_number
        _sender_phone_qr = order_action_sender_obj.client.phone
        td_client = ('NOMBRES: ' + str(order_action_sender_obj.client.names), '')
        _sender_qr = str(order_action_sender_obj.client.names)
        td_client_nro_documento = (
            document_sender + ': ' + str(order_action_sender_obj.client.clienttype_set.first().document_number), '')
        ana_c2 = Table([td_client] + [td_client_nro_documento], colWidths=colwiths_table)
        ana_c2.setStyle(TableStyle(my_style_table))

        # td_code = ('CÓDIGO DE RECOJO: ' + str(order_obj.code), '')
        # ana_code = Table([td_code], colWidths=colwiths_table)
        # ana_code.setStyle(TableStyle(my_style_code))

        _format_time_hour_arrival = (
            encomienda.arrival_time.strftime("%I:%M %p") if encomienda and encomienda.arrival_time else "-"
        )
        td_hour_arrival = ('HORA APROX. LLEGADA: ' + str(_format_time_hour_arrival), '')
        ana_hour_arrival = Table([td_hour_arrival], colWidths=colwiths_table)
        ana_hour_arrival.setStyle(TableStyle(my_style_hour_arrival))

        td_sender = (Paragraph('REMITENTE: ' + str(order_action_sender_obj.client.names), h_person), '')

        if order_action_sender_obj.client.phone:
            td_sender_document = (
                Paragraph(
                    document_sender + ': ' + str(order_action_sender_obj.client.clienttype_set.first().document_number),
                    h_person),
                Paragraph('TELEFONO: ' + str(order_action_sender_obj.client.phone), h_person_right))
            ana_c3 = Table([td_sender] + [td_sender_document], colWidths=colwiths_table)
            ana_c3.setStyle(TableStyle(my_style_person_sender))
        else:
            td_sender_document = (
                Paragraph(
                    document_sender + ': ' + str(order_action_sender_obj.client.clienttype_set.first().document_number),
                    h_person),
                '')
            ana_c3 = Table([td_sender] + [td_sender_document], colWidths=colwiths_table)
            ana_c3.setStyle(TableStyle(my_style_person_sender))

    else:

        td_client = ('NOMBRES: ' + str(order_action_sender_obj.order_addressee.names.upper()), '')
        _sender_qr = str(order_action_sender_obj.order_addressee.names.upper())
        td_client_nro_documento = (
            'DNI' + ': ' + '', '')
        _sender_document_qr = ''
        _sender_phone_qr = str(order_action_sender_obj.order_addressee.phone)
        ana_c2 = Table([td_client] + [td_client_nro_documento], colWidths=colwiths_table)
        ana_c2.setStyle(TableStyle(my_style_table))

        _format_time_hour_arrival = (
            encomienda.arrival_time.strftime("%I:%M %p") if encomienda and encomienda.arrival_time else "-"
        )
        td_hour_arrival = ('HORA APROX. LLEGADA: ' + str(_format_time_hour_arrival), '')
        ana_hour_arrival = Table([td_hour_arrival], colWidths=colwiths_table)
        ana_hour_arrival.setStyle(TableStyle(my_style_hour_arrival))

        td_sender = (
            Paragraph('REMITENTE: ' + str(order_action_sender_obj.order_addressee.names.upper()), h_person), '')

        if order_action_sender_obj.order_addressee.phone:
            td_sender_document = (
                Paragraph('DNI: ', h_person),
                Paragraph('TELEFONO: ' + str(order_action_sender_obj.order_addressee.phone), h_person_right))
            ana_c3 = Table([td_sender] + [td_sender_document], colWidths=colwiths_table)
            ana_c3.setStyle(TableStyle(my_style_person_sender))
        else:
            td_sender_document = (Paragraph('DNI: ', h_person), '')
            ana_c3 = Table([td_sender] + [td_sender_document], colWidths=colwiths_table)
            ana_c3.setStyle(TableStyle(my_style_person_sender))

    recipients = OrderAction.objects.filter(order=order_obj, type='D')
    _rows = []
    _recipients_names_qr = []
    _recipients_phone_qr = []
    _recipients_nro_document_qr = []
    for d in recipients:
        _phone = ''
        if d.client is None:
            _names = (d.order_addressee.names or '').upper()
            _phone = d.order_addressee.phone or ''
            _rows.append((Paragraph('DESTINATARIO: ' + _names, h_person), ''))
            if _phone:
                _rows.append((
                    Paragraph('DNI: ', h_person),
                    Paragraph('TELEFONO: ' + str(_phone), h_person_right)))
            else:
                _rows.append((Paragraph('DNI: ', h_person), ''))
            _recipients_names_qr.append(str(_names))
            _recipients_phone_qr.append(str(_phone))
        else:
            if d.client.phone is not None:
                _phone = d.client.phone
            _names = (d.client.names or '').upper()
            _doc_type = d.client.clienttype_set.first().document_type.short_description
            _doc_number = d.client.clienttype_set.first().document_number
            _rows.append((Paragraph('DESTINATARIO: ' + _names, h_person), ''))
            if _phone:
                _rows.append((
                    Paragraph(_doc_type + ': ' + str(_doc_number), h_person),
                    Paragraph('TELEFONO: ' + str(_phone), h_person_right)))
            else:
                _rows.append((Paragraph(_doc_type + ': ' + str(_doc_number), h_person), ''))
            _recipients_names_qr.append(str(_names))
            _recipients_phone_qr.append(str(_phone))
            _recipients_nro_document_qr.append(str(_doc_number))

    if not _rows:
        _rows = [(Paragraph('DESTINATARIO: -', h_person), '')]
    ana_c4 = Table(_rows, colWidths=colwiths_table)
    # Cada destinatario ocupa 2 filas: la del nombre (par) abarca ambas columnas
    _name_row_spans = [('SPAN', (0, i), (1, i)) for i in range(0, len(_rows), 2)]
    ana_c4.setStyle(TableStyle(my_style_table + _name_row_spans))

    encomienda = getattr(order_obj, 'encomienda', None)
    address_delivery = '-'

    if encomienda and encomienda.address_delivery:
        address_delivery = Paragraph(str(encomienda.address_delivery.upper()), h_justify)

    _origin_office = encomienda.office_origin if encomienda else None
    _destination_office = encomienda.office_destination if encomienda else None
    origin_address = (
        (_origin_office.address or _origin_office.short_name or '-').strip().upper()
        if _origin_office else '-'
    )
    destination_address = (
        (_destination_office.address or _destination_office.short_name or '-').strip().upper()
        if _destination_office else '-'
    )

    td_way_to_pay = ('FORMA DE PAGO', ': ' + str(order_obj.get_way_to_pay_display()))
    td_service = ('SERVICIO', ': ' + str(encomienda.get_type_guide_display() if encomienda else 'ENCOMIENDA'))
    td_address_delivery = ('DIR. REP.', address_delivery)

    if encomienda and encomienda.address_delivery:
        ana_c5 = Table(
            [td_way_to_pay] + [td_service] + [td_address_delivery],
            colWidths=[_wt * 28 / 100, _wt * 72 / 100])
    else:
        ana_c5 = Table([td_way_to_pay] + [td_service],
                       colWidths=[_wt * 28 / 100, _wt * 72 / 100])
    ana_c5.setStyle(TableStyle(my_style_table2))

    col_detail = [
        _wt * 38 / 100,  # descripción
        _wt * 12 / 100,  # cant
        _wt * 12 / 100,  # um
        _wt * 16 / 100,  # peso
        _wt * 22 / 100,  # subtotal
    ]
    td_description = ('DESCRIPCIÓN', 'CANT', 'UM', 'PESO', 'SUBTOTAL')
    ana_c6 = Table([td_description], colWidths=col_detail)
    ana_c6.setStyle(TableStyle(my_style_table3))

    sub_total = 0
    total = 0
    igv_total = 0
    _rows = []
    _counter = order_obj.orderdetail_set.count()
    _details_q_qr = []
    _details_d_qr = []
    _detail_amount = ''
    for d in order_obj.orderdetail_set.all():
        P0 = Paragraph(d.description.upper(), h_desc)
        _weight = getattr(d, 'weight', None)
        weight_txt = str(round(_weight, 2)) if _weight not in (None, '') else '0'
        _rows.append(
            (P0,
             str(decimal.Decimal(round(d.quantity))),
             _order_detail_unit_label(d),
             weight_txt,
             Paragraph(str(round(d.amount, 2)), h_desc_right)))
        base_total = d.quantity * d.price_unit
        base_amount = base_total / decimal.Decimal(1.1800)
        igv = base_total - base_amount
        sub_total = sub_total + base_amount
        total = total + base_total
        igv_total = igv_total + igv
        _details_q_qr.append(str(round(d.quantity)))
        _details_d_qr.append(d.description.upper())
        _detail_amount = str(round(d.amount, 2))

    ana_c7 = Table(_rows, colWidths=col_detail, rowHeights=0.28 * inch)
    ana_c7.setStyle(TableStyle(my_style_table4))

    td_importe_total = ('IMPORTE TOTAL', '', 'S/', str(decimal.Decimal(round(total, 2))))

    ana_c8 = Table([td_importe_total],
                   colWidths=[_wt * 60 / 100, _wt * 10 / 100, _wt * 17 / 100, _wt * 13 / 100])

    ana_c8.setStyle(TableStyle(my_style_table5))

    current_time = datetime.now()
    _format_current_time = current_time.strftime("%d/%m/%Y %I:%M:%S %p")
    _create_date = order_obj.transfer_date.strftime("%d/%m/%Y") + ' ' + str(_formattime)
    client_sender = str(_sender_qr)
    nro_document = str(_sender_document_qr)
    phone_sender = str(_sender_phone_qr)
    array_recipients_names_qr = ', '.join([item.strip() for item in _recipients_names_qr])
    array_recipients_phone_qr = ', '.join([item.strip() for item in _recipients_phone_qr])
    array_recipients_nro_document_qr = ', '.join([item.strip() for item in _recipients_nro_document_qr])

    str_details_q_qr = ', '.join([item.strip() for item in _details_q_qr])
    str_details_d_qr = ', '.join([item.strip() for item in _details_d_qr])
    # str_details_ic_qr = ', '.join([item.strip() for item in _details_ic_qr])
    # str_details_ix_qr = ', '.join([item.strip() for item in _details_ix_qr])

    _user_qr = str(order_obj.user.username.upper())
    origin = str(_origin_office.short_name if _origin_office else '-')
    destiny = str(_destination_office.short_name if _destination_office else '-')
    _way_to_pay_qr = str(order_obj.get_way_to_pay_display())

    datatable = str(_format_current_time) + ',' + str(order_obj.serial) + ',' + str(correlative) + ',' + str(
        _create_date) + ',' + client_sender + ',' + phone_sender + ',' + nro_document + ',' + str(
        array_recipients_names_qr) + ',' + str(
        array_recipients_phone_qr) + ',' + str(array_recipients_nro_document_qr) + ',' + str(
        str_details_q_qr) + ',' + str(str_details_d_qr) + ',' + str(_way_to_pay_qr) + ',' + str(
        _detail_amount) + ',' + _user_qr + ',' + origin + ',' + destiny
    # print(datatable)

    # QR más pequeño dentro de un cuadro
    _qr_widget = qr.QrCodeWidget(datatable)
    _qr_bounds = _qr_widget.getBounds()
    _qr_w = _qr_bounds[2] - _qr_bounds[0]
    _qr_h = _qr_bounds[3] - _qr_bounds[1]
    _qr_size = 3.4 * cm
    _qr_drawing = Drawing(
        _qr_size, _qr_size,
        transform=[_qr_size / _qr_w, 0, 0, _qr_size / _qr_h, 0, 0])
    _qr_drawing.add(_qr_widget)
    _qr_box = Table([[_qr_drawing]], colWidths=[_qr_size + 8])
    _qr_box.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.6, colors.HexColor('#d1d5db')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    ana_c9 = Table([[_qr_box]], colWidths=[_wt])
    ana_c9.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    observation = (getattr(order_obj, 'observation', None) or '').strip()

    buff = io.BytesIO()

    ml = 0.0 * inch
    mr = 0.0 * inch
    ms = 0.0 * inch
    mi = 0.039 * inch
    # pz_termical = (2.55 * inch, 11.6 * inch) # ticket normal
    pz_termical = (2.83 * inch, 11.6 * inch)

    doc = SimpleDocTemplate(buff,
                            pagesize=pz_termical,
                            rightMargin=mr,
                            leftMargin=ml,
                            topMargin=ms,
                            bottomMargin=mi,
                            title='ORDEN DE SERVICIO'
                            )
    dictionary = []
    dictionary.append(Spacer(1, 10))
    if logo_img:
        dictionary.append(logo_img)
    else:
        dictionary.append(Paragraph(brand_title, styles["Helvetica_Bold_Center_13"]))
    dictionary.append(Spacer(4, 4))
    if tbh_business_name_address:
        dictionary.append(Paragraph(tbh_business_name_address.replace("\n", "<br />"), styles["Helvetica_Center_7"]))
    if ruc_text:
        dictionary.append(Paragraph(ruc_text, styles["Helvetica_Bold_Center_7"]))
    dictionary.append(Spacer(2, 2))
    for sub_name, sub_phone in subsidiary_phones:
        dictionary.append(Paragraph(f"{sub_name}: {sub_phone}", h_center_7))
    dictionary.append(Spacer(6, 6))
    dictionary.append(_separator(_wt))
    dictionary.append(Spacer(2, 2))
    dictionary.append(Paragraph(name_document, styles["Helvetica_Bold_Center_10"]))
    dictionary.append(Spacer(4, 4))
    dictionary.append(Paragraph(f'{serie} - {correlative}', h_serie))
    dictionary.append(Spacer(1, 1))
    dictionary.append(ana_c1)
    dictionary.append(Spacer(6, 6))
    dictionary.append(_separator(_wt))
    dictionary.append(Spacer(2, 2))
    dictionary.append(Paragraph('<b>origen:</b> ' + origin_address, style_custom_left))
    dictionary.append(Spacer(2, 2))
    dictionary.append(Paragraph('<b>destino:</b> ' + destination_address, style_custom_left))
    dictionary.append(Spacer(6, 6))
    dictionary.append(_separator(_wt))
    dictionary.append(Spacer(2, 2))
    dictionary.append(Paragraph('DATOS DEL REMITENTE', styles["Helvetica_Bold_Left_7"]))
    dictionary.append(Spacer(1, 1))
    dictionary.append(ana_c3)
    dictionary.append(Spacer(6, 6))
    dictionary.append(_separator(_wt))
    dictionary.append(Spacer(2, 2))
    dictionary.append(Paragraph('DATOS DEL DESTINATARIO', styles["Helvetica_Bold_Left_7"]))
    dictionary.append(Spacer(1, 1))
    dictionary.append(ana_c4)
    dictionary.append(Spacer(6, 6))
    dictionary.append(_separator(_wt))
    dictionary.append(Spacer(2, 2))
    dictionary.append(ana_c5)
    dictionary.append(Spacer(6, 6))
    dictionary.append(_separator(_wt))
    dictionary.append(Spacer(2, 2))
    dictionary.append(ana_c6)
    dictionary.append(Spacer(6, 6))
    dictionary.append(_separator(_wt))
    dictionary.append(Spacer(2, 2))
    dictionary.append(ana_c7)
    dictionary.append(Spacer(6, 6))
    dictionary.append(_separator(_wt))
    dictionary.append(Spacer(2, 2))
    dictionary.append(ana_c8)
    if observation:
        dictionary.append(Spacer(6, 6))
        dictionary.append(_separator(_wt))
        dictionary.append(Spacer(2, 2))
        dictionary.append(Paragraph('OBSERVACIÓN:', styles["Helvetica_Bold_Left_7"]))
        dictionary.append(Spacer(2, 2))
        dictionary.append(Paragraph(observation.upper(), h_left))
    dictionary.append(Spacer(10, 10))
    dictionary.append(ana_c9)
    dictionary.append(Spacer(2, 2))
    dictionary.append(Paragraph(
        "TERMINOS Y CONDICIONES: <br/>"
        "1.    El remitente declara que la información y el contenido de la encomienda son veraces y de libre transporte. <br/>"
        "2.    La empresa no se responsabiliza por objetos de valor o contenido no declarado. <br/>"
        "3.    La entrega se realizará al destinatario o persona autorizada, previa identificación. <br/>"
        "4.    La empresa no será responsable por demoras ocasionadas por caso fortuito o fuerza mayor. <br/>"
        "5.    Al contratar el servicio, el cliente acepta los presentes términos y condiciones. <br/>",
        h_terms))
    dictionary.append(Spacer(6, 6))
    dictionary.append(_separator(_wt))
    dictionary.append(Spacer(2, 2))
    dictionary.append(Paragraph(
        "¡Gracias por confiar en nosotros!",
        h_center))

    doc.build(dictionary)

    response = HttpResponse(content_type='application/pdf')

    _os_serial = order_obj.order_serial or order_obj.serial or ''
    _os_correlative = order_obj.order_correlative or order_obj.correlative_sale or ''
    _disposition = 'attachment' if request.GET.get('download') else 'inline'
    response['Content-Disposition'] = '{}; filename="ORDEN DE SERVICIO {}-{}.pdf"'.format(
        _disposition, _os_serial, _os_correlative)

    tomorrow = datetime.now() + timedelta(days=1)
    tomorrow = tomorrow.replace(hour=0, minute=0, second=0)
    expires = datetime.strftime(tomorrow, "%a, %d-%b-%Y %H:%M:%S GMT")

    response.set_cookie('ware', value=pk, expires=expires)

    # doc.build(elements)
    # doc.build(Story)
    response.write(buff.getvalue())
    buff.close()
    return response


def print_ticket_order_passenger(request, pk=None):  # Boleto de viaje boleta / factura
    return _passenger_pdf_unavailable()
    # _wt = 2.83 * inch - 4 * 0.05 * inch  # termical

    tbh_business_name_address = ''
    # _wt = 2.57 * inch - 5 * 0.05 * inch # matricial

    order_obj = Order.objects.get(pk=pk)
    order_bill_obj = order_obj.orderbill
    passenger_name = ""
    passenger_document = ""
    client_document = ""
    client_name = ""
    client_address = ""

    if order_obj.company.id == 1:
        tbh_business_name_address = 'EMPRESA DE TRANSPORTES\n NALU S.R.L.\n RUC: 20455935173 '
    elif order_obj.company.id == 2:
        tbh_business_name_address = order_obj.company.business_name + '\n' + 'RUC: ' + order_obj.company.ruc

    date = order_obj.programming_seat.programming.departure_date
    _format_time = utc_to_local(order_obj.create_at).strftime("%H:%M %p")
    _format_date = date.strftime("%d/%m/%Y")

    if order_bill_obj.type == '1':
        tbn_document = 'FACTURA ELECTRÓNICA'
        passenger_set = order_obj.client
        company_set = order_obj.orderaction_set.filter(type='E')
        if passenger_set:
            passenger_name = passenger_set.names
            passenger_document = passenger_set.clienttype_set.first().document_number
        if company_set:
            client_document = company_set.first().client.clienttype_set.first().document_number
            client_name = company_set.first().client.names
            client_address = company_set.first().client.clientaddress_set.first().address
    elif order_bill_obj.type == '2':
        tbn_document = 'BOLETA DE VENTA ELECTRÓNICA'
        passenger_name = order_obj.client.names
        passenger_document = order_obj.client.clienttype_set.first().document_number
        client_name = passenger_name
        client_document = passenger_document
    line = '-----------------------------------------------------'

    I = Image(logo)
    I.drawHeight = 1.95 * inch / 2.9
    I.drawWidth = 7.4 * inch / 2.9

    style_table = [
        ('FONTNAME', (0, 0), (-1, -1), 'Square'),  # all columns
        # ('GRID', (0, 0), (-1, -1), 0.5, colors.black),  # all columns
        ('FONTSIZE', (0, 0), (-1, -1), 8),  # all columns
        ('FONTSIZE', (0, 0), (-1, -1), 8),  # all columns
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # all columns
        ('BOTTOMPADDING', (0, 0), (-1, -1), -2),  # all columns
        # ('BACKGROUND', (2, 3), (2, 4), colors.blue),
        ('LEFTPADDING', (0, 0), (0, -1), 0.5),  # first column
        ('ALIGNMENT', (1, 0), (1, -1), 'RIGHT'),  # second column
        ('RIGHTPADDING', (1, 0), (1, -1), 0.5),  # second column
    ]
    colwiths_table = [_wt * 30 / 100, _wt * 70 / 100]

    if order_bill_obj.type == '2':
        p0 = Paragraph(client_name, styles["Right"])
        ana_c1 = Table(
            [('CLIENTE: N DOC ', client_document)] +
            [('SR(A): ', p0)] +
            [('ATENDIDO POR: ', order_obj.user.username.upper() + " " + order_obj.subsidiary.name)],
            colWidths=colwiths_table)
    elif order_bill_obj.type == '1':
        p0 = Paragraph(client_name, styles["Justify"])
        p1 = Paragraph(client_address, styles["Justify"])
        ana_c1 = Table(
            [('RUC ', client_document)] +
            [('RAZÓN SOCIAL: ', p0)] +
            [('DIRECCIÓN: ', p1)] +
            [('ATENDIDO POR: ', order_obj.user.username.upper() + " " + order_obj.subsidiary.name)],
            colWidths=colwiths_table)

    ana_c1.setStyle(TableStyle(style_table))

    style_table = [
        ('FONTNAME', (0, 0), (-1, -1), 'Square'),  # all columns
        # ('GRID', (0, 0), (-1, -1), 0.5, colors.black),  # all columns
        ('FONTSIZE', (0, 0), (-1, -1), 8),  # all columns
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # all columns
        ('BOTTOMPADDING', (0, 0), (-1, -1), -2),  # all columns
        ('LEFTPADDING', (0, 0), (0, -1), 0.5),  # first column
        ('FONTNAME', (0, 0), (0, -1), 'Ticketing'),  # first column
        ('LEFTPADDING', (2, 0), (2, -1), 2),  # third column
        ('ALIGNMENT', (3, 0), (3, -1), 'RIGHT'),  # fourth column
        ('FONTSIZE', (3, 0), (3, -1), 10),  # fourth column
        ('FONTNAME', (3, 0), (3, -1), 'Ticketing'),  # fifth row [col 1:2]
        # ('BACKGROUND', (3, 0), (3, -1), colors.pink),

        ('FONTSIZE', (2, 3), (2, 4), 10),  # third column

        ('ALIGNMENT', (1, 2), (1, 4), 'LEFT'),  # second column [row 3:5]
        ('FONTNAME', (2, 3), (2, 4), 'Ticketing'),  # third column [row 4:5]
        # ('BACKGROUND', (2, 3), (2, 4), colors.blue),

        ('LEFTPADDING', (2, 3), (2, 4), 9),

        ('RIGHTPADDING', (3, 3), (3, 4), 0.5),  # fourth column [row 4:5]
        ('FONTNAME', (0, 4), (1, 4), 'Square-Bold'),  # fifth row [col 1:2]
        ('FONTSIZE', (0, 4), (1, 4), 12),  # fifth row [col 1:2]
        ('LEFTPADDING', (1, 0), (1, -1), 0.5),  # second column
        ('SPAN', (1, 0), (3, 0)),  # first row
        ('SPAN', (0, 1), (1, 1)),  # second row
        ('SPAN', (2, 1), (3, 1)),  # second row
    ]
    p10 = Paragraph('SR(A): ' + passenger_document + ' - ' + passenger_name, styles["Justify"])
    colwiths_table = [_wt * 25 / 100, _wt * 25 / 100, _wt * 25 / 100, _wt * 25 / 100]
    
    # Verificar si el origen es diferente a la sede
    if order_obj.origin and order_obj.origin.name != order_obj.subsidiary.name:
        # Si hay un origen seleccionado y es diferente a la sede, usar el nombre del origen
        _short_name_origin = order_obj.origin.name
    else:
        # Si no hay origen o es igual a la sede, usar la lógica original
        if getattr(order_obj, 'show_original_name', False):
            _short_name_origin = order_obj.subsidiary.short_name
        else:
            _short_name_origin = order_obj.subsidiary.short_name
    ana_c2 = Table(
        [('PASAJERO:', p10, '', '')] +
        [('AGENCIA DE EMBARQUE:', '', order_obj.subsidiary.name, '')] +
        [('ORIG:', _short_name_origin, '', '')] +
        [('DEST:', order_obj.destiny.name, 'FECHA:', str(_format_date))] +
        [('ASIENTO:', order_obj.programming_seat.plan_detail.name, 'HORA:', str(_format_time))],
        colWidths=colwiths_table)
    ana_c2.setStyle(TableStyle(style_table))

    my_style_table3 = [
        ('FONTNAME', (0, 0), (-1, -1), 'Square'),  # all columns
        # ('GRID', (0, 0), (-1, -1), 0.5, colors.pink),  # all columns
        ('FONTSIZE', (0, 0), (-1, -1), 8),  # all columns
        ('LEFTPADDING', (0, 0), (0, -1), 0.5),  # first column
        ('BOTTOMPADDING', (0, 0), (-1, -1), -6),  # all columns
        ('RIGHTPADDING', (1, 0), (1, -1), 0.5),  # second column
        ('ALIGNMENT', (1, 0), (1, -1), 'RIGHT'),  # second column
    ]
    colwiths_table = [_wt * 80 / 100, _wt * 20 / 100]
    ana_c6 = Table([('DESCRIPCIÓN', 'TOTAL')], colWidths=colwiths_table)
    ana_c6.setStyle(TableStyle(my_style_table3))

    sub_total = 0
    total = 0
    igv_total = 0

    P0 = Paragraph(
        'SER TRANSPORTE RUTA ' + order_obj.subsidiary.short_name + ' - ' + order_obj.destiny.name + '<br/> ASIENTO ' + order_obj.programming_seat.plan_detail.name + '.',
        styles["Justify"])
    P_TRUCK = Paragraph('PLACA: ' + order_obj.programming_seat.programming.truck.license_plate, styles["Justify_Bold"])

    base_total = 1 * 45
    base_amount = base_total / 1.1800
    igv = base_total - base_amount
    sub_total = sub_total + base_amount
    total = total + base_total
    igv_total = igv_total + igv
    ana_truck = Table([(P_TRUCK, '')], colWidths=[_wt * 80 / 100, _wt * 20 / 100])

    my_style_truck = [
        ('FONTNAME', (0, 0), (-1, -1), 'Square'),  # all columns
        # ('GRID', (0, 0), (-1, -1), 0.5, colors.pink),   # all columns
        ('FONTSIZE', (0, 0), (-1, -1), 8),  # all columns
        # ('BOTTOMPADDING', (0, 0), (-1, -1), 6),  # all columns
        ('TOPPADDING', (0, 0), (-1, -1), -3),  # all columns
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # all columns
        ('LEFTPADDING', (0, 0), (0, -1), 0.5),  # first column
        ('RIGHTPADDING', (1, 0), (1, -1), 0.5),  # second column
        ('ALIGNMENT', (1, 0), (1, -1), 'RIGHT'),  # second column
    ]
    my_style_table4 = [
        ('FONTNAME', (0, 0), (-1, -1), 'Square'),  # all columns
        # ('GRID', (0, 0), (-1, -1), 0.5, colors.pink),   # all columns
        ('FONTSIZE', (0, 0), (-1, -1), 8),  # all columns
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),  # all columns
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # all columns
        ('LEFTPADDING', (0, 0), (0, -1), 0.5),  # first column
        ('RIGHTPADDING', (1, 0), (1, -1), 0.5),  # second column
        ('ALIGNMENT', (1, 0), (1, -1), 'RIGHT'),  # second column
    ]
    ana_c7 = Table([(P0, 'S/ ' + str(decimal.Decimal(round(order_obj.total, 2))))],
                   colWidths=[_wt * 80 / 100, _wt * 20 / 100])
    ana_c7.setStyle(TableStyle(my_style_table4))
    ana_truck.setStyle(TableStyle(my_style_truck))

    my_style_table5 = [
        ('FONTNAME', (0, 0), (-1, -1), 'Square'),  # all columns

        # ('GRID', (0, 0), (-1, -1), 0.5, colors.pink),   # all columns
        ('FONTSIZE', (0, 0), (-1, -1), 8),  # all columns
        ('BOTTOMPADDING', (0, 0), (-1, -1), -6),  # all columns
        ('RIGHTPADDING', (2, 0), (2, -1), 0),  # third column
        ('ALIGNMENT', (2, 0), (2, -1), 'RIGHT'),  # third column
        ('RIGHTPADDING', (3, 0), (3, -1), 0.3),  # four column
        ('ALIGNMENT', (3, 0), (3, -1), 'RIGHT'),  # four column
        ('LEFTPADDING', (0, 0), (0, -1), 0.5),  # first column
        ('FONTNAME', (0, 2), (-1, 2), 'Square-Bold'),  # third row
        ('FONTSIZE', (0, 2), (-1, 2), 10),  # third row
    ]

    ana_c8 = Table(
        [('OP. NO GRAVADA', '', 'S/', str(decimal.Decimal(round(order_obj.total, 2))))] +
        [('I.G.V.  (18.00)', '', 'S/', '0.00')] +
        [('TOTAL', '', 'S/', str(decimal.Decimal(round(order_obj.total, 2))))],
        colWidths=[_wt * 60 / 100, _wt * 10 / 100, _wt * 10 / 100, _wt * 20 / 100]
    )
    ana_c8.setStyle(TableStyle(my_style_table5))
    footer = 'SON: ' + numero_a_moneda(order_obj.total)

    my_style_table6 = [
        # ('GRID', (0, 0), (-1, -1), 0.5, colors.blue),   # all columns
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # all columns
        ('ALIGNMENT', (0, 0), (0, -1), 'CENTER'),  # first column
        ('SPAN', (0, 0), (1, 0)),  # first row
    ]

    # datatable = order_bill_obj.code_qr
    datatable = 'https://www.tuf4ct.com/cpe/'
    ana_c9 = Table([(qr_code(datatable), '')], colWidths=[_wt * 99 / 100, _wt * 1 / 100])
    ana_c9.setStyle(TableStyle(my_style_table6))

    _dictionary = []
    # _dictionary.append(I)
    _dictionary.append(Spacer(1, 5))
    _dictionary.append(Paragraph(tbh_business_name_address.replace("\n", "<br />"), styles["Center4"]))
    _dictionary.append(Spacer(-4, -4))
    _dictionary.append(Paragraph(line, styles["Center2"]))
    _dictionary.append(Paragraph(tbn_document, styles["Center_Regular"]))
    _dictionary.append(
        Paragraph(order_bill_obj.serial + ' - ' + str(order_bill_obj.n_receipt).zfill(6), styles["Center_Bold"]))
    _dictionary.append(Spacer(-2, -2))
    _dictionary.append(ana_c1)
    _dictionary.append(Spacer(-4, -4))
    _dictionary.append(Paragraph(line, styles["Center2"]))
    _dictionary.append(Spacer(-2, -2))
    _dictionary.append(Spacer(1, 2))
    _dictionary.append(Paragraph('DATOS DE VIAJE ', styles["Center_Regular"]))
    _dictionary.append(Spacer(1, 1))
    _dictionary.append(ana_c2)
    _dictionary.append(Spacer(1, 1))
    _dictionary.append(Paragraph(line, styles["Center2"]))
    _dictionary.append(Spacer(-1, -1))
    _dictionary.append(ana_c6)
    _dictionary.append(Spacer(-1, -1))
    _dictionary.append(Paragraph(line, styles["Center2"]))
    _dictionary.append(Spacer(1, 1))
    _dictionary.append(ana_c7)
    _dictionary.append(ana_truck)
    _dictionary.append(Spacer(-7, -7))
    _dictionary.append(Paragraph(line, styles["Center2"]))
    _dictionary.append(ana_c8)
    _dictionary.append(Paragraph(line, styles["Center2"]))
    _dictionary.append(Paragraph(footer, styles["Center"]))
    _dictionary.append(Paragraph(line, styles["Center2"]))
    _dictionary.append(Spacer(1, 2))
    _dictionary.append(Paragraph(
        "Representación impresa de la " + str(
            tbn_document) + ", para ver el documento visita ", styles["Square_left"]))
    _dictionary.append(Paragraph("https://www.tuf4ct.com/cpe/" + order_obj.company.ruc, styles["Square_bold_left"]))
    _dictionary.append(Paragraph("Emitido mediante un PROVEEDOR Autorizado por la SUNAT", styles["Square_left"]), )
    # _dictionary.append(Paragraph("mediante Resolución de Intendencia No. 034-005- 0005315", styles["Square_left"]))
    _dictionary.append(Paragraph(line, styles["Center2"]))
    _dictionary.append(
        Paragraph("***CONSERVAR SU COMPROBANTE ANTE CUALQUIER EVENTUALIDAD***".replace('***', '"'), styles["Center2"]))
    _dictionary.append(Spacer(-4, -4))
    _dictionary.append(ana_c9)
    _dictionary.append(Spacer(-4, -4))
    _dictionary.append(Paragraph("TERMINOS Y CONDICIONES: <br/>"
                                "1.    El remitente declara que la información y el contenido de la encomienda son veraces y de libre transporte. <br/>"
                                "2.    La empresa no se responsabiliza por objetos de valor o contenido no declarado. <br/>"
                                "3.    La entrega se realizará al destinatario o persona autorizada, previa identificación. <br/>"
                                "4.    La empresa no será responsable por demoras ocasionadas por caso fortuito o fuerza mayor. <br/>"
                                "5.    Al contratar el servicio, el cliente acepta los presentes términos y condiciones. <br/>",
                                 styles["Center3"]))
    _dictionary.append(Spacer(-4, -4))
    _dictionary.append(Paragraph(line, styles["Center2"]))
    _dictionary.append(Spacer(-2, -2))
    _dictionary.append(Paragraph(
        "¡Gracias por viajar con nosotros!",
        styles["Center2"]))
    buff = io.BytesIO()

    ml = 0.0 * inch
    mr = 0.0 * inch
    ms = 0.039 * inch
    mi = 0.039 * inch

    pz_matricial = (2.57 * inch, 11.6 * inch)
    # pz_termical = (3.14961 * inch, 11.6 * inch)
    pz_termical = (2.83 * inch, 11.6 * inch)

    doc = SimpleDocTemplate(buff,
                            pagesize=pz_termical,
                            rightMargin=mr,
                            leftMargin=ml,
                            topMargin=ms,
                            bottomMargin=mi,
                            title='TICKET'
                            )
    doc.build(_dictionary)
    # doc.build(elements)
    # doc.build(Story)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="CE[{}].pdf"'.format(
        order_obj.serial + '-' + order_obj.correlative_sale)

    tomorrow = datetime.now() + timedelta(days=1)
    tomorrow = tomorrow.replace(hour=0, minute=0, second=0)
    expires = datetime.strftime(tomorrow, "%a, %d-%b-%Y %H:%M:%S GMT")

    response.set_cookie('bp', value=pk, expires=expires)

    response.write(buff.getvalue())

    buff.close()
    return response


def qr_code(table):
    # generate and rescale QR
    qr_code = qr.QrCodeWidget(table)
    bounds = qr_code.getBounds()
    width = bounds[2] - bounds[0]
    height = bounds[3] - bounds[1]
    drawing = Drawing(
        4.8 * cm, 4.8 * cm, transform=[4.8 * cm / width, 0, 0, 4.8 * cm / height, 0, 0])
    drawing.add(qr_code)

    return drawing


def print_bill_order_commodity(request, pk=None):  # Boleta / Factura Encomienda
    order_obj = Order.objects.select_related(
        'encomienda', 'company', 'subsidiary', 'user', 'orderbill', 'client',
    ).get(pk=pk)
    if order_obj.service_type != 'E':
        from .pdf_service_guides import build_ticket_for_service
        return build_ticket_for_service(order_obj, pk, request)

    from .pdf_service_guides import build_bill_encomienda
    return build_bill_encomienda(order_obj, pk, request)


def print_manifest_passengers(request, pk=None):  # Manifiesto de Pasajeros
    return _passenger_pdf_unavailable()
    _legal = (8.5 * inch, 14 * inch)

    ml = 0.75 * inch
    mr = 0.75 * inch
    ms = 0.75 * inch
    mi = 1.0 * inch

    _bts = 8.5 * inch - 0.5 * inch - 0.5 * inch
    programming_obj = Programming.objects.get(id=pk)

    buff = io.BytesIO()
    doc = SimpleDocTemplate(buff,
                            pagesize=(8.5 * inch, 14 * inch),
                            rightMargin=mr,
                            leftMargin=ml,
                            topMargin=ms,
                            bottomMargin=mi,
                            title='Manifiesto de pasajeros'
                            )
    response = HttpResponse(content_type='application/pdf')

    style_table = [
        ('FONTNAME', (0, 0), (-1, -1), 'Dotcirful-Regular'),  # all columns
        # ('GRID', (0, 0), (-1, -1), 0.5, colors.black),      # all columns
        ('FONTSIZE', (0, 0), (-1, -1), 10),  # all columns
        ('TOPPADDING', (0, 0), (-1, -1), 0),  # all columns
        ('LEFTPADDING', (0, 0), (-1, -1), 0),  # all columns
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),  # all columns
        ('BOTTOMPADDING', (0, 0), (-1, -1), -2),  # all columns
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),

        ('SPAN', (0, 0), (3, 0)),  # first row
        ('ALIGNMENT', (0, 0), (3, 0), 'LEFT'),  # first row

        ('SPAN', (4, 0), (4, 0)),  # first row
        ('ALIGNMENT', (4, 0), (4, 0), 'RIGHT'),  # first row

        ('SPAN', (0, 1), (3, 1)),  # second row
        ('ALIGNMENT', (0, 1), (2, 1), 'LEFT'),  # second row
        ('ALIGNMENT', (4, 1), (4, 1), 'RIGHT'),  # second row

        # ('SPAN', (3, 1), (4, 1)),  # second row

        # ('SPAN', (4, 1), (5, 1)),  # second row
        ('SPAN', (7, 1), (9, 1)),  # second row
        ('SPAN', (1, 2), (2, 2)),  # third row
        ('ALIGNMENT', (1, 2), (2, 2), 'RIGHT'),  # third row
        ('SPAN', (4, 2), (5, 2)),  # third row
        ('ALIGNMENT', (4, 2), (5, 2), 'CENTER'),  # third row
        ('SPAN', (7, 2), (9, 2)),  # third row
        ('SPAN', (1, 3), (2, 3)),  # fourth row
        ('ALIGNMENT', (1, 3), (2, 3), 'RIGHT'),  # fourth row
        ('TOPPADDING', (1, 3), (2, 3), -4),  # fourth row

        ('SPAN', (4, 3), (5, 3)),  # fourth row
        ('ALIGNMENT', (4, 3), (5, 3), 'CENTER'),  # fourth row
        ('TOPPADDING', (4, 3), (5, 3), -4),  # fourth row

        ('SPAN', (7, 3), (9, 3)),  # fourth row
        ('SPAN', (1, 4), (2, 4)),  # fifth row
        ('ALIGNMENT', (1, 4), (2, 4), 'RIGHT'),  # fifth row
        ('ALIGNMENT', (6, 4), (6, 4), 'RIGHT'),  # fifth row
        ('ALIGNMENT', (9, 4), (9, 4), 'RIGHT'),  # fifth row
    ]

    col_widths = [
        _bts * 5 / 100,  # destiny
        _bts * 10 / 100,
        _bts * 5 / 100,  # origin
        _bts * 10 / 100,

        _bts * 20 / 100,  # passengers
        _bts * 5 / 100,

        _bts * 10 / 100,  # date
        _bts * 10 / 100,
        _bts * 10 / 100,
        _bts * 15 / 100
    ]

    col_heights = [
        1 * inch / 8,
        1 * inch / 4,
        1 * inch / 4,
        1 * inch / 4,
        1 * inch / 8,
    ]

    _pilot = programming_obj.get_pilot()
    _copilot = programming_obj.get_copilot()

    _n_license_pilot = _pilot.n_license
    _n_license_copilot = ''
    _copilot_full_name = ''
    if _copilot:
        _copilot_full_name = _copilot.full_name()
        _n_license_copilot = _copilot.n_license

    _truck = programming_obj.truck
    _hour = programming_obj.get_turn_display()
    _date = str(programming_obj.departure_date.strftime("%d/%m/%y"))
    programming_seat_set = programming_obj.programmingseat_set.filter(status='4')  # sold

    p0 = Paragraph(_programming_subsidiary_label(programming_obj), styles["Justify-Dotcirful"])
    p1 = Paragraph(_programming_subsidiary_label(programming_obj), styles["Justify-Dotcirful"])
    p2 = Paragraph('Nº PASAJEROS EN LA RUTA', styles["Justify"])

    ana_c1 = Table(
        [(_pilot.full_name(), '', '', '', _n_license_pilot, '', '', '', '', '')] +
        [(_copilot_full_name, '', '', '', _n_license_copilot, '', '', '', '', '')] +
        [('', _truck.truck_model.truck_brand.name, '', '', _truck.license_plate, '', '', '', '', '')] +
        [('', _truck.certificate, '', '', _truck.nro_passengers, '', '', '', '', '')] +
        [('', p1, '', '', p0, '', programming_seat_set.count(), '', _date, _hour[0:8])], colWidths=col_widths,
        rowHeights=col_heights)
    ana_c1.setStyle(TableStyle(style_table))

    _rows = []

    for ps in programming_obj.programmingseat_set.filter(status='4'):
        order_obj = Order.objects.filter(programming_seat=ps).last()
        client_obj = order_obj.client
        client_type_obj = client_obj.clienttype_set.get(document_type_id__in=['01', '04', '07'])
        _birthday = 0
        _short_name = ''
        if order_obj.subsidiary.short_name:
            _short_name = order_obj.subsidiary.short_name
        if client_obj.birthday:
            _birthday = calculate_age(client_obj.birthday)
        _rows.append((
            order_obj.serial[1:4],
            order_obj.correlative_sale,
            client_obj.names,
            '',
            ps.plan_detail.name,
            client_type_obj.document_type.id,
            client_type_obj.document_number,
            _birthday,
            # client_obj.nationality,
            _short_name,
            order_obj.destiny.name,
            order_obj.total,
        ))

    style_table = [
        ('FONTNAME', (0, 0), (-1, -1), 'Dotcirful-Regular'),  # all columns
        # ('GRID', (0, 0), (-1, -1), 0.5, colors.black),  # all columns
        ('FONTSIZE', (0, 0), (-1, -1), 10),  # all columns
        ('TOPPADDING', (0, 0), (-1, -1), 0),  # all columns
        ('LEFTPADDING', (0, 0), (-1, -1), 0),  # all columns
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),  # all columns
        ('BOTTOMPADDING', (0, 0), (-1, -1), -2),  # all columns
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),

        ('ALIGNMENT', (0, 0), (0, -1), 'RIGHT'),  # first column
        ('ALIGNMENT', (1, 0), (1, -1), 'CENTER'),  # second column
        ('ALIGNMENT', (7, 0), (7, -1), 'CENTER'),  # eighth column
        ('ALIGNMENT', (10, 0), (10, -1), 'RIGHT'),  # eleventh column
    ]
    _bts2 = 8.5 * inch - 1.0 * inch
    col_widths = [
        _bts2 * 8 / 100,  # serial
        _bts2 * 10 / 100,  # correlative
        _bts2 * 32 / 100,  # names

        _bts2 * 8 / 100,  # void

        _bts2 * 3 / 100,  # seat
        _bts2 * 3 / 100,  # document type

        _bts2 * 9 / 100,  # document number
        _bts2 * 5 / 100,  # age

        _bts2 * 9 / 100,
        _bts2 * 9 / 100,
        _bts2 * 5 / 100,

    ]
    if len(_rows) == 0:
        _rows.append(('', '', '', '', '', '', '', '', '', '', '',))

    ana_c2 = Table(_rows, colWidths=col_widths)

    ana_c2.setStyle(TableStyle(style_table))

    _dictionary = []
    _dictionary.append(Spacer(1, 43))
    _dictionary.append(ana_c1)
    _dictionary.append(Spacer(1, 25))
    _dictionary.append(ana_c2)

    doc.build(_dictionary)
    response.write(buff.getvalue())
    buff.close()
    return response


def print_mock_up_passengers(request, pk=None):
    return _passenger_pdf_unavailable()
    _a4 = (8.3 * inch, 11.7 * inch)

    ml = 0.25 * inch
    mr = 0.25 * inch
    ms = 0.25 * inch
    mi = 0.25 * inch

    _bts = 8.3 * inch - 0.25 * inch - 0.25 * inch

    programming_obj = Programming.objects.get(id=pk)

    plan_obj = programming_obj.truck.plan

    rows = plan_obj.rows
    cols = plan_obj.columns

    first_floor_set = plan_obj.plandetail_set.filter(position='I')

    _data_first_floor = []
    _first_floor_style = []

    x_style = 1
    x2_style = 1
    for x in range(1, rows + 1):
        _row_first_floor = []
        _count_void_first_floor = 0
        for y in range(1, cols + 1):
            search_first_floor_seat = first_floor_set.filter(row=x, column=y)

            if search_first_floor_seat:
                _row_first_floor.append(search_first_floor_seat.last().name)
                _first_floor_style.append(('BOX', (y - 1, x_style - 1), (y - 1, x_style - 1), 1, colors.gray))
                _first_floor_style.append(('FONTNAME', (y - 1, x_style - 1), (y - 1, x_style - 1), 'Dotcirful-Regular'))
                _first_floor_style.append(('TOPPADDING', (y - 1, x_style - 1), (y - 1, x_style - 1), 0))
                _first_floor_style.append(('LEFTPADDING', (y - 1, x_style - 1), (y - 1, x_style - 1), 0))
                _first_floor_style.append(('VALIGN', (y - 1, x_style - 1), (y - 1, x_style - 1), 'TOP'))
            else:
                _row_first_floor.append('')
                _count_void_first_floor = _count_void_first_floor + 1

        if _count_void_first_floor != cols:
            _data_first_floor.append(_row_first_floor)
            x_style = x_style + 1

    # _first_floor_style.append(('BOX', (0, 0), (-1, -1), 1, colors.gray))
    square_width = 0.87 * inch
    square_height = 0.87 * inch
    first_floor = Table(_data_first_floor, colWidths=cols * [square_width], rowHeights=(x_style - 1) * [square_height])
    first_floor.setStyle(TableStyle(_first_floor_style))

    p0 = Paragraph('EMPRESA DE TRANSPORTES SUPER RAPIDO NUEVA FLECHA S.A. - CROQUIS DE CONTROL DE VIAJE',
                   styles["Justify-Dotcirful"])
    p1 = Paragraph(_programming_subsidiary_label(programming_obj), styles["Justify-Dotcirful"])
    p2 = Paragraph(_programming_subsidiary_label(programming_obj), styles["Justify-Dotcirful"])
    _pilot = programming_obj.get_pilot()
    _n_license = _pilot.n_license
    _truck = programming_obj.truck
    _hour = programming_obj.get_turn_display()
    _date = str(programming_obj.departure_date.strftime("%d/%m/%y"))

    labeled = [
        [p0, '', '', ''],
        ['BUS: ', _truck.license_plate, 'HORARIO:', _hour[0:8]],
        ['ORIGEN:', p1, '', ''],
        ['DESTINO:', p2, '', ''],
        ['PILOTO:', _pilot.full_name(), '', ''],
        ['COPILOTO:', '', '', ''],
        ['FECHA:', _date, '', ''],
    ]
    t_labeled = Table(labeled)
    t_labeled.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Dotcirful-Regular'),  # all columns
        # ('GRID', (0, 0), (-1, -1), 0.5, colors.black),      # all columns
        ('FONTSIZE', (0, 0), (-1, -1), 10),  # all columns
        ('TOPPADDING', (0, 0), (-1, -1), 0),  # all columns
        ('LEFTPADDING', (0, 0), (-1, -1), 0),  # all columns
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),  # all columns
        ('BOTTOMPADDING', (0, 0), (-1, -1), -2),  # all columns
        ('SPAN', (0, 0), (3, 0)),  # first row
        ('SPAN', (1, 2), (3, 2)),  # third row
        ('SPAN', (1, 3), (3, 3)),  # fourth row
        ('SPAN', (1, 4), (3, 4)),  # fifth row
        ('SPAN', (1, 5), (3, 5)),  # sixth row

    ]))
    bus = [
        [t_labeled, ''],
        ['', ''],
        ['', first_floor],
        ['DESPACHADO POR:...................', '']
    ]
    t = Table(bus)

    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Dotcirful-Regular'),  # all columns
        # ('GRID', (0, 0), (-1, -1), 0.5, colors.pink),      # all columns
        ('FONTSIZE', (0, 0), (-1, -1), 10),  # all columns
        ('TOPPADDING', (0, 0), (-1, -1), 0),  # all columns
        ('LEFTPADDING', (0, 0), (-1, -1), 0),  # all columns
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),  # all columns
        ('BOTTOMPADDING', (0, 0), (-1, -1), -2),  # all columns

        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (1, 0), (-1, -1), 'MIDDLE'),
        ('VALIGN', (0, 0), (0, 0), 'TOP'),
        ('SPAN', (0, 0), (0, 1)),  # first and second row
    ]))
    buff = io.BytesIO()
    doc = SimpleDocTemplate(buff,
                            pagesize=(8.3 * inch, 11.7 * inch),
                            rightMargin=mr,
                            leftMargin=ml,
                            topMargin=ms,
                            bottomMargin=mi,
                            title='Croquis de pasajeros'
                            )
    response = HttpResponse(content_type='application/pdf')

    _dictionary = []
    _dictionary.append(t)

    doc.build(_dictionary)
    response.write(buff.getvalue())
    buff.close()
    return response


def print_manifest_comidity(request, pk=None):  # Manifiesto de Encomiendas
    _a4 = (8.3 * inch, 11.7 * inch)

    ml = 0.25 * inch
    mr = 0.25 * inch
    ms = 0.25 * inch
    mi = 0.25 * inch

    _bts = 8.3 * inch - 0.25 * inch - 0.25 * inch

    manifest_obj = Manifest.objects.get(id=pk)
    order_qs = Order.objects.filter(
        subsidiary=manifest_obj.subsidiary,
        transfer_date=manifest_obj.created_at.date(),
        type_order='E',
    ).prefetch_related('orderdetail_set', 'orderbill_set', 'orderaction_set')
    programming_obj = Programming.objects.filter(
        subsidiary=manifest_obj.subsidiary,
        departure_date=manifest_obj.created_at.date(),
        truck__isnull=False,
    ).select_related('truck', 'subsidiary').first()
    if programming_obj is None:
        return HttpResponse(
            'No hay programación asociada al manifiesto.',
            status=HTTPStatus.NOT_FOUND,
            content_type='text/plain',
        )

    # I = Image(logo)
    # I.drawHeight = 2.00 * inch / 2.9
    # I.drawWidth = 5.4 * inch / 2.9

    tbh_business_name_address = ''

    if manifest_obj.company.id == 1:
        tbh_business_name_address = 'EMPRESA DE TRANSPORTES\n NALU S.R.L.\n RUC: 20455935173'
    elif manifest_obj.company.id == 2:
        tbh_business_name_address = 'EMPRESA DE TRANSPORTES\n NALU S.R.L.\n RUC: 20455935173'
    elif manifest_obj.company.id == 3:
        tbh_business_name_address = 'EMPRESA DE TRANSPORTES\n NALU S.R.L.\n RUC: 20455935173'

    # tbh_business_name_address = 'TURISMO MENDIVIL S.R.L <br/> CALLE JAVIER P. DE CUELLAR B-3 INT 105 TERM. TERRESTRE S/N INT. E1-E / URB. ARTURO IBAÑEZ HUNTER AREQUIPA <br/> RUC: 20442736759'
    ph = Paragraph(tbh_business_name_address.replace("\n", "<br />"), styles["Justify-Dotcirful-table"])
    tbn_name_document = 'MANIFIESTO DE ENCOMIENDAS'

    p0 = Paragraph('MANIFIESTO DE CARGA', styles["CenterTitle-Dotcirful"])

    _tbl_small = [
        [p0, ''],
        ['SERIE:', manifest_obj.serial],
        ['CORRELATIVO:', manifest_obj.correlative],
    ]

    ana_c_1 = Table(_tbl_small)

    _tbl_header = [
        [ph, '', ana_c_1],
    ]

    ana_c = Table(_tbl_header)

    # date = manifest_obj.create_at.date()
    _date_convert_zone = utc_to_local(manifest_obj.created_at)
    date_hour = _date_convert_zone.time()
    # date = datetime.now()
    _formatdate = _date_convert_zone.strftime("%d/%m/%Y")

    td_date = ('FECHA: ', _formatdate, 'TURNO: ', programming_obj.truck_exit)
    td_data_drive = ('PILOTO: ', _programming_pilot_name(programming_obj), 'ESTADO: ',
                     str(programming_obj.get_status_display()).upper())
    td_data_vehicle = (
        'PLACA: ', str(programming_obj.truck.license_plate), 'TIPO: ',
        str(programming_obj.truck.get_drive_type_display()))
    _route_label = _programming_subsidiary_label(programming_obj)
    td_route = ('ORIGEN: ', _route_label, 'DESTINO: ', _route_label)

    colwiths_table = [_bts * 10 / 100, _bts * 30 / 100, _bts * 10 / 100, _bts * 50 / 100]
    ana_c1 = Table([td_date] + [td_data_drive] + [td_data_vehicle] + [td_route], colWidths=colwiths_table)

    td_title = (
        '#', 'SERIE', 'NRO.', 'CANT.', 'UND.', 'PESO', 'DESCRIPCIÓN', 'DESTINATARIO', 'DESTINO', 'COND. PAGO', 'MONTO')
    colwiths_table_title = [_bts * 3 / 100,
                            _bts * 4 / 100,
                            _bts * 4 / 100,
                            _bts * 4 / 100,
                            _bts * 6 / 100,
                            _bts * 4 / 100,
                            _bts * 25 / 100,
                            _bts * 20 / 100,
                            _bts * 14 / 100,
                            _bts * 9 / 100,
                            _bts * 7 / 100]
    # ana_c2 = Table([td_title], colWidths=colwiths_table_title)
    detail_style = [
        ('FONTNAME', (0, 0), (-1, -1), 'Dotcirful-Regular'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('FONTNAME', (0, 0), (-1, 0), 'Dotcirful-Regular'),
        ('FONTNAME', (0, 0), (0, -1), 'Dotcirful-Regular'),
        ('FONTSIZE', (0, 0), (0, -1), 10),
        ('FONTSIZE', (0, 0), (-1, 0), 9)
    ]
    _rows = []

    _rows.append(td_title)
    _pi = 0
    _pf = 0
    _c2 = 1
    y = 8
    cont_counted = 0
    cont_destination_payment = 0
    serial_row = ''
    name_addreess = ''
    for order_obj in order_qs:
        _rows_recipients = []
        recipients = OrderAction.objects.filter(order=order_obj, type='D')
        for r in recipients:
            if r.client is None:
                _rows_recipients.append(str(r.order_addressee.names.upper()))
            else:
                _rows_recipients.append(str(r.client.names))
        name_addreess = str(_rows_recipients).replace(',', ' /').replace("'", '').replace(']', '').replace('[', '')
        number_details = order_obj.orderdetail_set.all().count()
        for d in order_obj.orderdetail_set.all():
            if order_obj and OrderBill.objects.filter(order=order_obj).count() > 0:
                serial_row = order_obj.orderbill.serial
            else:
                serial_row = 'G' + order_obj.serial[-3:]
            _rows.append((_c2,
                          # order_obj.id,
                          serial_row,
                          str(order_obj.correlative_sale[-4:]),
                          str(decimal.Decimal(round(d.quantity))),
                          _order_detail_unit_label(d, use_description=True),
                          str(decimal.Decimal(round(d.weight))) + ' KG',
                          Paragraph(d.description.upper(), styles["Justify-Dotcirful"]),
                          Paragraph(name_addreess, styles["Justify-Dotcirful"]),
                          (order_obj.get_destiny().short_name if order_obj.get_destiny() else ''),
                          # str(_programming_subsidiary_label(programming_obj)),
                          order_obj.get_way_to_pay_display(),
                          'S/. ' + str(decimal.Decimal(round(order_obj.total, 2)))))

        _pf = _pf + number_details
        _pi = _pf - (number_details - 1)
        detail_style.append(('SPAN', (y - 1, _pi), (y - 1, _pf)))
        detail_style.append(('SPAN', (y - 1 + 1, _pi), (y - 1 + 1, _pf)))
        detail_style.append(('SPAN', (y - 1 + 2, _pi), (y - 1 + 2, _pf)))
        detail_style.append(('SPAN', (y - 1 + 3, _pi), (y - 1 + 3, _pf)))
        detail_style.append(('SPAN', (y - 1 - 7, _pi), (y - 1 - 7, _pf)))
        detail_style.append(('SPAN', (y - 1 - 6, _pi), (y - 1 - 6, _pf)))
        detail_style.append(('SPAN', (y - 1 - 5, _pi), (y - 1 - 5, _pf)))
        if order_obj.way_to_pay == 'C':
            cont_counted = cont_counted + order_obj.total
        elif order_obj.way_to_pay == 'D':
            cont_destination_payment = cont_destination_payment + order_obj.total
        _c2 = _c2 + 1
    ana_c3 = Table(_rows, colWidths=colwiths_table_title)

    colwiths_table_totals = [_bts * 80 / 100, _bts * 10 / 100, _bts * 10 / 100]
    p4 = Paragraph('TOTALES ENCOMIENDAS', styles["CenterTitle-Dotcirful"])
    _tbl_totals = [
        ['', p4, ''],
        ['', 'TOTAL PAGO CONTADO:', 'S/. ' + str(decimal.Decimal(round(cont_counted, 2)))],
        ['', 'TOTAL PAGO DESTINO:', 'S/. ' + str(decimal.Decimal(round(cont_destination_payment, 2)))],
    ]
    ana_c4 = Table(_tbl_totals, colWidths=colwiths_table_totals)

    my_style_table = [
        ('FONTNAME', (0, 0), (-1, -1), 'Dotcirful-Regular'),
        # ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        # ('FONTNAME', (0, 1), (0, -1), 'Newgot'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('FONTNAME', (0, 0), (0, -1), 'Dotcirful-Regular'),
        ('FONTNAME', (2, 0), (2, -1), 'Dotcirful-Regular'),
        # ('BOTTOMPADDING', (0, 0), (-1, -1), -6),
        # ('ALIGNMENT', (1, 1), (1, 1), 'RIGHT'),
        # ('ALIGNMENT', (1, 0), (1, 0), 'RIGHT'),
        # ('TOPPADDING', (0, 0), (-1, -1), 1),
        # ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        # ('LINEBELOW', (0, 0), (-1, 0), 1, colors.darkblue),
        # ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey)
    ]
    ana_c1.setStyle(TableStyle(my_style_table))

    my_style_table_header_1 = [
        ('FONTNAME', (0, 0), (-1, -1), 'Dotcirful-Regular'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('SPAN', (0, 0), (1, 0)),
        ('VALIGN', (0, 0), (0, -1), 'MIDDLE')  # first column

    ]
    ana_c_1.setStyle(TableStyle(my_style_table_header_1))

    my_style_table_header = [
        ('FONTNAME', (0, 0), (-1, -1), 'Dotcirful-Regular'),
        # ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('VALIGN', (1, 0), (1, -1), 'MIDDLE')  # first column

    ]
    ana_c.setStyle(TableStyle(my_style_table_header))

    my_style_table_totals = [
        ('FONTNAME', (0, 0), (-1, -1), 'Dotcirful-Regular'),
        # ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('VALIGN', (1, 0), (1, -1), 'MIDDLE'),  # first column
        ('SPAN', (1, 0), (2, 0)),  # first row
        ('ALIGNMENT', (1, 0), (2, -1), 'RIGHT'),  # second column
    ]
    ana_c4.setStyle(TableStyle(my_style_table_totals))

    ana_c3.setStyle(TableStyle(detail_style))

    buff = io.BytesIO()
    doc = SimpleDocTemplate(buff,
                            pagesize=(8.3 * inch, 11.7 * inch),
                            rightMargin=mr,
                            leftMargin=ml,
                            topMargin=ms,
                            bottomMargin=mi,
                            title='Manifiesto de Encomiendas'
                            )
    dictionary = []
    dictionary.append(ana_c)
    dictionary.append(Spacer(1, 5))
    # dictionary.append(Paragraph(tbh_business_name_address.replace("\n", "<br />"), styles["Left"]))
    dictionary.append(Spacer(1, 5))
    dictionary.append(Paragraph(tbn_name_document, styles["CenterTitle-Dotcirful"]))
    dictionary.append(Spacer(20, 20))
    dictionary.append(ana_c1)
    dictionary.append(Spacer(10, 10))
    # dictionary.append(ana_c2)
    dictionary.append(ana_c3)
    dictionary.append(Spacer(10, 10))
    dictionary.append(ana_c4)

    response = HttpResponse(content_type='application/pdf')
    doc.build(dictionary)

    response['Content-Disposition'] = 'attachment; filename="Manifiesto-Encomienda_[{}].pdf"'.format(manifest_obj.id)
    # doc.build(elements)
    # doc.build(Story)
    response.write(buff.getvalue())
    buff.close()
    return response


def print_guide_comidity(request, pk=None):  # Guia Remision Transportista
    _a5 = (5.8 * inch, 8.3 * inch)

    ml = 0.25 * inch
    mr = 0.25 * inch
    ms = 0.25 * inch
    mi = 0.25 * inch

    _bts = 5.8 * inch - 0.25 * inch - 0.25 * inch
    # _bts2 = 8.3 * inch - 0.25 * inch - 0.25 * inch
    colwiths_table = [_bts * 10 / 100, _bts * 30 / 100, _bts * 10 / 100, _bts * 50 / 100]
    order_obj = Order.objects.get(pk=pk)
    encomienda = getattr(order_obj, 'encomienda', None)
    programming_obj = Programming.objects.filter(
        truck=order_obj.truck,
        departure_date=order_obj.transfer_date,
    ).select_related('truck').first()
    date = datetime.now()
    _formatdate = date.strftime("%d/%m/%Y")

    td_dates_1 = _formatdate
    td_dates_2 = _formatdate
    td_serial_guide = (order_obj.serial or '') + ' - '
    td_nro_guide = order_obj.correlative_sale or (encomienda.code if encomienda else '') or ''

    _tbl_header = [
        ['', td_serial_guide, td_nro_guide],
        ['', td_dates_1, td_dates_2],

    ]
    ana_c = Table(_tbl_header, colWidths=[_bts * 10 / 100, _bts * 35 / 100, _bts * 55 / 100],
                  rowHeights=[_bts * 10 / 100, _bts * 10 / 100])

    my_style_table_header = [
        ('FONTNAME', (0, 0), (-1, -1), 'Dotcirful-Regular'),
        # ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (2, 0), (2, 0), 180),
        ('LEFTPADDING', (1, 0), (1, 0), 291),
        ('BOTTOMPADDING', (0, 0), (3, 0), -20),
        # ('BACKGROUND',  (0, 0), (3, 0), colors.pink)
        # ('VALIGN', (1, 0), (1, -1), 'MIDDLE')  # first column
    ]
    ana_c.setStyle(TableStyle(my_style_table_header))

    td_subsidiary_origin = encomienda.office_origin.address \
        if encomienda and encomienda.office_origin_id else ''
    td_subsidiary_destiny = encomienda.office_destination.address \
        if encomienda and encomienda.office_destination_id else ''

    _tbl_subsidiarys = [
        ['', '', td_subsidiary_origin],
        ['', '', td_subsidiary_destiny],
    ]
    ana_c1 = Table(_tbl_subsidiarys, colWidths=[_bts * 10 / 100, _bts * 5 / 100, _bts * 85 / 100])

    my_style_table_subsidiary = [
        ('FONTNAME', (0, 0), (-1, -1), 'Dotcirful-Regular'),
        # ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (3, 0), -6),  # first row
        ('TOPPADDING', (0, 1), (3, 1), 2),  # second row
        # ('BACKGROUND',  (0, 1), (3, 1), colors.pink),
    ]
    ana_c1.setStyle(TableStyle(my_style_table_subsidiary))

    td_client_sender = order_obj.orderaction_set.filter(type='R').last().client.names.upper()
    td_client_addreesse = order_obj.orderaction_set.filter(type='D').last().client.names.upper()
    td_client_sender_type_document = order_obj.orderaction_set.filter(
        type='R').last().client.clienttype_set.first().document_type.short_description + ':'
    td_client_sender_document = order_obj.orderaction_set.filter(
        type='R').last().client.clienttype_set.first().document_number
    td_client_addreesse_type_document = order_obj.orderaction_set.filter(
        type='D').last().client.clienttype_set.first().document_type.short_description + ':'
    td_client_addreesse_document = order_obj.orderaction_set.filter(
        type='D').last().client.clienttype_set.first().document_number

    _tbl_clients = [
        ['', '', td_client_sender] + [td_client_sender_type_document] + [td_client_sender_document],
        ['', '', td_client_addreesse] + [td_client_addreesse_type_document] + [td_client_addreesse_document],
    ]
    ana_c2 = Table(_tbl_clients,
                   colWidths=[_bts * 5 / 100, _bts * 4 / 100, _bts * 79 / 100, _bts * 5 / 100, _bts * 7 / 100])

    my_style_table_client = [
        ('FONTNAME', (0, 0), (-1, -1), 'Dotcirful-Regular'),
        # ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('FONTSIZE', (3, 0), (4, -1), 6),
        ('LEFTPADDING', (3, 0), (3, -1), 21),
        ('LEFTPADDING', (4, 0), (4, -1), 12),
        ('TOPPADDING', (0, 0), (4, 0), -1),  # first row
        ('TOPPADDING', (0, 1), (4, 1), 3),  # second row
    ]
    ana_c2.setStyle(TableStyle(my_style_table_client))

    colwiths_table_title = [_bts * 10 / 100,
                            _bts * 65 / 100,
                            _bts * 9 / 100,
                            _bts * 9 / 100,
                            _bts * 7 / 100]

    _rows = []
    _counter = 1
    _c2 = 1
    for d in order_obj.orderdetail_set.all():
        _rows.append((_c2,
                      Paragraph(d.description.upper(), styles["Justify-Dotcirful-table"]),
                      _order_detail_unit_label(d, use_description=True),
                      str(decimal.Decimal(round(d.quantity))),
                      str(decimal.Decimal(round(d.weight))) + ' KG'))
        _c2 = _c2 + 1

    ana_c3 = Table(_rows, colWidths=colwiths_table_title)

    detail_style = [
        ('FONTNAME', (0, 0), (-1, -1), 'Dotcirful-Regular'),
        # ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGNMENT', (4, 0), (4, -1), 'RIGHT'),  # four column
        ('RIGHTPADDING', (4, 0), (4, -1), -4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), -5),  # all columns
        # ('BACKGROUND', (4, 0), (4, -1), colors.lightgrey),
        ('FONTNAME', (0, 0), (-1, 0), 'Dotcirful-Regular'),
        ('FONTNAME', (0, 0), (0, -1), 'Dotcirful-Regular'),
        ('FONTSIZE', (0, 0), (0, -1), 7),
        ('FONTSIZE', (0, 0), (-1, 0), 7)
    ]
    ana_c3.setStyle(TableStyle(detail_style))

    truck = order_obj.truck or (programming_obj.truck if programming_obj else None)
    if truck is None:
        return HttpResponse(
            'Unidad no asociada a la orden.',
            status=HTTPStatus.NOT_FOUND,
            content_type='text/plain',
        )

    td_truck = truck.truck_model.truck_brand.name if truck.truck_model else ''
    td_plate = truck.license_plate
    td_certificate = truck.certificate or ''
    td_license_nro = ''

    _tbl_truck_data = [
        ['', td_truck],
        ['', td_plate],
        ['', ''],
        ['', td_certificate],
        ['', td_license_nro]
    ]
    ana_c4 = Table(_tbl_truck_data, colWidths=[_bts * 23 / 100, _bts * 77 / 100])

    my_style_table_truck_data = [
        ('FONTNAME', (0, 0), (-1, -1), 'Dotcirful-Regular'),
        # ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), -5),  # all columns
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # all columns
        ('TOPPADDING', (0, 0), (1, 0), -1),  # first row
        ('TOPPADDING', (0, 1), (2, 1), 3),  # second row
        ('TOPPADDING', (0, 2), (2, 2), -1),  # third row
        ('BOTTOMPADDING', (0, 3), (3, 3), -10),  # fourth row
        ('BOTTOMPADDING', (0, 4), (4, 4), -14),  # fourth row
    ]
    ana_c4.setStyle(TableStyle(my_style_table_truck_data))

    buff = io.BytesIO()
    doc = SimpleDocTemplate(buff,
                            pagesize=A5,
                            rightMargin=mr,
                            leftMargin=ml,
                            topMargin=ms,
                            bottomMargin=mi,
                            title='Manifiesto de Encomiendas'
                            )
    dictionary = []
    dictionary.append(ana_c)
    dictionary.append(Spacer(1, 5))
    dictionary.append(ana_c1)
    dictionary.append(Spacer(1, 5))
    dictionary.append(ana_c2)
    dictionary.append(Spacer(4, 10))
    dictionary.append(ana_c3)
    dictionary.append(Spacer(54, 54))
    dictionary.append(ana_c4)

    response = HttpResponse(content_type='application/pdf')
    doc.build(dictionary)
    response['Content-Disposition'] = 'attachment; filename="GuiaRemisionTransportista_[{}].pdf"'.format(
        order_obj.id)
    # doc.build(elements)
    # doc.build(Story)
    response.write(buff.getvalue())
    buff.close()
    return response


# ---------------------------------------------------------------------------------------------------------------


def print_ticket_old(request, pk=None):  # TICKET PASSENGER OLD
    return _passenger_pdf_unavailable()

    _wt = 2.83 * inch - 4 * 0.05 * inch  # termical
    tbh_business_name_address = ''
    ml = 0.0 * inch
    mr = 0.0 * inch
    ms = 0.039 * inch
    mi = 0.039 * inch
    order_obj = Order.objects.get(pk=pk)
    passenger_name = ""
    passenger_document = ""
    client_document = ""
    client_name = ""
    client_address = ""

    passenger_set = order_obj.client
    passenger_name = passenger_set.names
    passenger_document = passenger_set.clienttype_set.first().document_number

    entity_set = order_obj.orderaction_set.filter(type='E')
    if entity_set.exists():
        client_document = entity_set.first().client.clienttype_set.first().document_number
        client_name = entity_set.first().client.names
        client_address = entity_set.first().client.clientaddress_set.first().address

    if order_obj.company.id == 1:
        tbh_business_name_address = 'EMPRESA DE TRANSPORTES\n NALU S.R.L.\n RUC: 20455935173'
    elif order_obj.company.id == 2:
        tbh_business_name_address = order_obj.company.business_name + '\n' + 'RUC: ' + order_obj.company.ruc
        # tbh_business_name_address = 'EMPRESA DE TRANSPORTES\n NALU S.R.L.\n RUC: 20455935173'

    date = order_obj.programming_seat.programming.departure_date
    _format_time = utc_to_local(order_obj.create_at).strftime("%H:%M %p")
    _format_date = date.strftime("%d/%m/%Y")

    line = '-----------------------------------------------------'

    I = Image(logo)
    I.drawHeight = 1.95 * inch / 2.9
    I.drawWidth = 7.4 * inch / 2.9

    style_table = [
        ('FONTNAME', (0, 0), (-1, -1), 'Square'),  # all columns
        # ('GRID', (0, 0), (-1, -1), 0.5, colors.black),  # all columns
        ('FONTSIZE', (0, 0), (-1, -1), 8),  # all columns
        ('FONTSIZE', (0, 0), (-1, -1), 8),  # all columns
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # all columns
        ('BOTTOMPADDING', (0, 0), (-1, -1), -2),  # all columns
        # ('BACKGROUND', (1, 0), (3, 0), colors.blue),
        ('LEFTPADDING', (0, 0), (0, -1), 0.5),  # first column
        ('ALIGNMENT', (1, 0), (1, -1), 'RIGHT'),  # second column
        ('RIGHTPADDING', (1, 0), (1, -1), 0.5),  # second column
        ('SPAN', (1, 0), (3, 0)),

    ]
    colwiths_table = [_wt * 30 / 100, _wt * 70 / 100]

    # p0 = Paragraph(client_name, styles["Right"])
    # ana_c1 = Table(
    #     [('CLIENTE: N DOC ', client_document)] +
    #     [('SR(A): ', p0)] +
    #     [('ATENDIDO POR: ', order_obj.user.username.upper() + " " + order_obj.subsidiary.name)],
    #     colWidths=colwiths_table)
    #
    # ana_c1.setStyle(TableStyle(style_table))

    p10 = Paragraph('SR(A): ' + passenger_document + ' - ' + passenger_name, styles["Justify"])
    colwiths_table = [_wt * 25 / 100, _wt * 25 / 100, _wt * 25 / 100, _wt * 25 / 100]
    if getattr(order_obj, 'show_original_name', False):
        _short_name_origin = order_obj.subsidiary.short_name
    else:
        _short_name_origin = order_obj.subsidiary.short_name

    ana_c2 = Table(
        [('PASAJERO:', p10, '', '')] +
        [('AGENCIA DE EMBARQUE:', '', order_obj.subsidiary.name, '')] +
        [('ORIG:', _short_name_origin, '', '')] +
        [('DEST:', order_obj.destiny.name, 'FECHA:', str(_format_date))] +
        [('ASIENTO:', order_obj.programming_seat.plan_detail.name, 'HORA:', str(_format_time))] +
        [('ATENDIDO POR: ', '', order_obj.user.username.upper() + " " + order_obj.subsidiary.name)],
        colWidths=colwiths_table)
    ana_c2.setStyle(TableStyle(style_table))

    my_style_table3 = [
        ('FONTNAME', (0, 0), (-1, -1), 'Square'),  # all columns
        # ('GRID', (0, 0), (-1, -1), 0.5, colors.pink),  # all columns
        ('FONTSIZE', (0, 0), (-1, -1), 8),  # all columns
        ('LEFTPADDING', (0, 0), (0, -1), 0.5),  # first column
        ('BOTTOMPADDING', (0, 0), (-1, -1), -6),  # all columns
        ('RIGHTPADDING', (1, 0), (1, -1), 0.5),  # second column
        ('ALIGNMENT', (1, 0), (1, -1), 'RIGHT'),  # second column
    ]
    colwiths_table = [_wt * 80 / 100, _wt * 20 / 100]
    ana_c6 = Table([('DESCRIPCIÓN', 'TOTAL')], colWidths=colwiths_table)
    ana_c6.setStyle(TableStyle(my_style_table3))

    sub_total = 0
    total = 0
    igv_total = 0

    P0 = Paragraph(
        'SER TRANSPORTE RUTA ' + order_obj.subsidiary.short_name + ' - ' + order_obj.destiny.name + '<br/> ASIENTO ' + order_obj.programming_seat.plan_detail.name + '.',
        styles["Justify"])
    P_TRUCK = Paragraph('PLACA: ' + order_obj.programming_seat.programming.truck.license_plate, styles["Justify_Bold"])

    base_total = 1 * 45
    base_amount = base_total / 1.1800
    igv = base_total - base_amount
    sub_total = sub_total + base_amount
    total = total + base_total
    igv_total = igv_total + igv
    ana_truck = Table([(P_TRUCK, '')], colWidths=[_wt * 80 / 100, _wt * 20 / 100])

    my_style_truck = [
        ('FONTNAME', (0, 0), (-1, -1), 'Square'),  # all columns
        # ('GRID', (0, 0), (-1, -1), 0.5, colors.pink),   # all columns
        ('FONTSIZE', (0, 0), (-1, -1), 8),  # all columns
        # ('BOTTOMPADDING', (0, 0), (-1, -1), 6),  # all columns
        ('TOPPADDING', (0, 0), (-1, -1), -3),  # all columns
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # all columns
        ('LEFTPADDING', (0, 0), (0, -1), 0.5),  # first column
        ('RIGHTPADDING', (1, 0), (1, -1), 0.5),  # second column
        ('ALIGNMENT', (1, 0), (1, -1), 'RIGHT'),  # second column
    ]
    my_style_table4 = [
        ('FONTNAME', (0, 0), (-1, -1), 'Square'),  # all columns
        # ('GRID', (0, 0), (-1, -1), 0.5, colors.pink),   # all columns
        ('FONTSIZE', (0, 0), (-1, -1), 8),  # all columns
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),  # all columns
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # all columns
        ('LEFTPADDING', (0, 0), (0, -1), 0.5),  # first column
        ('RIGHTPADDING', (1, 0), (1, -1), 0.5),  # second column
        ('ALIGNMENT', (1, 0), (1, -1), 'RIGHT'),  # second column
    ]
    ana_c7 = Table([(P0, 'S/ ' + str(decimal.Decimal(round(order_obj.total, 2))))],
                   colWidths=[_wt * 80 / 100, _wt * 20 / 100])
    ana_c7.setStyle(TableStyle(my_style_table4))
    ana_truck.setStyle(TableStyle(my_style_truck))

    my_style_table5 = [
        ('FONTNAME', (0, 0), (-1, -1), 'Square'),  # all columns

        # ('GRID', (0, 0), (-1, -1), 0.5, colors.pink),   # all columns
        ('FONTSIZE', (0, 0), (-1, -1), 8),  # all columns
        ('BOTTOMPADDING', (0, 0), (-1, -1), -6),  # all columns
        ('RIGHTPADDING', (2, 0), (2, -1), 0),  # third column
        ('ALIGNMENT', (2, 0), (2, -1), 'RIGHT'),  # third column
        ('RIGHTPADDING', (3, 0), (3, -1), 0.3),  # four column
        ('ALIGNMENT', (3, 0), (3, -1), 'RIGHT'),  # four column
        ('LEFTPADDING', (0, 0), (0, -1), 0.5),  # first column
        ('FONTNAME', (0, 2), (-1, 2), 'Square-Bold'),  # third row
        ('FONTSIZE', (0, 2), (-1, 2), 10),  # third row
    ]

    ana_c8 = Table(
        [('OP. NO GRAVADA', '', 'S/', str(decimal.Decimal(round(order_obj.total, 2))))] +
        [('I.G.V.  (18.00)', '', 'S/', '0.00')] +
        [('TOTAL', '', 'S/', str(decimal.Decimal(round(order_obj.total, 2))))],
        colWidths=[_wt * 60 / 100, _wt * 10 / 100, _wt * 10 / 100, _wt * 20 / 100]
    )
    ana_c8.setStyle(TableStyle(my_style_table5))
    footer = 'SON: ' + numero_a_moneda(order_obj.total)

    my_style_table6 = [
        # ('GRID', (0, 0), (-1, -1), 0.5, colors.blue),   # all columns
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # all columns
        ('ALIGNMENT', (0, 0), (0, -1), 'CENTER'),  # first column
        ('SPAN', (0, 0), (1, 0)),  # first row
    ]

    datatable = order_obj.correlative_sale
    ana_c9 = Table([(qr_code(datatable), '')], colWidths=[_wt * 99 / 100, _wt * 1 / 100])
    ana_c9.setStyle(TableStyle(my_style_table6))

    _dictionary = []
    # _dictionary.append(I)
    _dictionary.append(Spacer(1, 5))
    _dictionary.append(Paragraph(tbh_business_name_address.replace("\n", "<br />"), styles["Center4"]))
    _dictionary.append(Spacer(-4, -4))
    _dictionary.append(Paragraph(line, styles["Center2"]))
    _dictionary.append(Paragraph('TICKET', styles["Center_Regular"]))
    _dictionary.append(
        Paragraph(order_obj.serial + ' - ' + str(order_obj.correlative_sale).zfill(6), styles["Center_Bold"]))
    _dictionary.append(Spacer(-2, -2))
    # _dictionary.append(ana_c1)
    # _dictionary.append(Spacer(-4, -4))
    _dictionary.append(Paragraph(line, styles["Center2"]))
    _dictionary.append(Spacer(-2, -2))
    _dictionary.append(Spacer(1, 2))
    _dictionary.append(Paragraph('DATOS DE VIAJE ', styles["Center_Regular"]))
    _dictionary.append(Spacer(1, 1))
    _dictionary.append(ana_c2)
    _dictionary.append(Spacer(1, 1))
    _dictionary.append(Paragraph(line, styles["Center2"]))
    _dictionary.append(Spacer(-1, -1))
    _dictionary.append(ana_c6)
    _dictionary.append(Spacer(-1, -1))
    _dictionary.append(Paragraph(line, styles["Center2"]))
    _dictionary.append(Spacer(1, 1))
    _dictionary.append(ana_c7)
    _dictionary.append(ana_truck)
    _dictionary.append(Spacer(-7, -7))
    _dictionary.append(Paragraph(line, styles["Center2"]))
    _dictionary.append(ana_c8)
    _dictionary.append(Paragraph(line, styles["Center2"]))
    _dictionary.append(Paragraph(footer, styles["Center"]))
    _dictionary.append(Paragraph(line, styles["Center2"]))
    _dictionary.append(
        Paragraph("***COMPROBANTE NO TRIBUTARIO.***".replace('***', '"'), styles["Center2"]))
    _dictionary.append(Spacer(-4, -4))
    _dictionary.append(ana_c9)
    _dictionary.append(Spacer(-4, -4))
    _dictionary.append(Paragraph("DE LAS CONDICIONES PARA EL SERVICIO DE TRANSPORTE: "
                                 "1. EL BOLETO DE VIAJE ES PERSONAL, TRANSFERIBLE Y/O PO5TERGABLE. "
                                 "2. EL PASAJERO SE PRESENTARÁ 30 MIN ANTES DE LA HORA DE VIAJE, DEBIENDO PRESENTAR SU BOLETO DE VIAJE Y DNI. "
                                 "3. LOS MENORES DE EDAD VIAJAN CON SUS PADRES O EN SU DEFECTO DEBEN PRESENTAR PERMISO NOTARIAL DE SUS PADRES, MAYORES DE 5 AÑOS PAGAN SU PASAJE. "
                                 "4. EN CASO DE ACCIDENTES EL PASAJERO VIAJA  ASEGURADO CON SOAT DE LA COMPANIA RIMAC SEGUROS. "
                                 "5. EL PASAJERO TIENE DERECHO A TRANSPORTAR 20 KILOS DE EQUIPAJE, SOLO ARTICULOS DE USO PERSONAL (NO CARGA).  EL EXCESO SERÁ ADMITIDO CUANDO LA CAPACIDAD DEL BUS LO PERMITA, PREVIO PAGO DE LA TARIFA. "
                                 "6. LA EMPRESA NO SE RESPONSABILIZA POR FALLAS AJENAS AL MISMO SERVICIO DE TRANSPORTE (WIFI, TOMACORRIENTES, PANTALLAS, AUDIO Y OTRAS SIMILARES) PUES ESTOS SERVICIOS SON OFRECIDOS EN CALIDAD DE CORTESIA. "
                                 "7. LAS DEVOLUCIONES DE BOLETOS PAGADOS CON VISA SE EFECTUARÁ SEGÚN LOS PLAZOS, PROCEDIMIENTOS Y CANALES ESTABLECIDOS POR VISA, EN NINGUN CASO SE EFECTUARÁ DEVOLUCIÓN EN EFECTIVO.",
                                 styles["Center3"]))
    _dictionary.append(Spacer(-4, -4))
    _dictionary.append(Paragraph(line, styles["Center2"]))
    _dictionary.append(Spacer(-2, -2))
    _dictionary.append(Paragraph(
        "¡Gracias por viajar con nosotros!",
        styles["Center2"]))
    buff = io.BytesIO()

    pz_matricial = (2.57 * inch, 11.6 * inch)
    # pz_termical = (3.14961 * inch, 11.6 * inch)
    pz_termical = (2.83 * inch, 11.6 * inch)

    doc = SimpleDocTemplate(buff,
                            pagesize=pz_termical,
                            rightMargin=mr,
                            leftMargin=ml,
                            topMargin=ms,
                            bottomMargin=mi,
                            title='TICKET'
                            )
    doc.build(_dictionary)
    # doc.build(elements)
    # doc.build(Story)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="CE[{}-{}].pdf"'.format(
        order_obj.serial, order_obj.correlative_sale)

    tomorrow = datetime.now() + timedelta(days=1)
    tomorrow = tomorrow.replace(hour=0, minute=0, second=0)
    expires = datetime.strftime(tomorrow, "%a, %d-%b-%Y %H:%M:%S GMT")

    response.set_cookie('bp', value=pk, expires=expires)

    response.write(buff.getvalue())

    buff.close()
    return response


def print_manifest_passengers_old(request, pk=None):  # Manifiesto de Pasajeros antiguo matricial
    return _passenger_pdf_unavailable()
    # _legal = (8.5 * inch, 14 * inch)
    _a6 = 8.27 * inch - 0.5 * inch
    _custom_a5 = (8.27 * inch, 5.75 * inch)

    ml = 0.00 * inch
    mr = 0.00 * inch
    ms = 0.00 * inch
    mi = 0.00 * inch

    # _bts = 8.5 * inch - 0.5 * inch - 0.5 * inch

    style_table0 = [
        ('FONTNAME', (0, 0), (-1, -1), 'Dotcirful-Regular'),  # all columns
        ('GRID', (0, 0), (-1, -1), 0.5, colors.blue),  # all columns
        ('FONTSIZE', (0, 0), (-1, -1), 12),  # all columns
        # ('TOPPADDING', (0, 0), (-1, -1), -3),  # all columns
    ]
    style_table = [
        ('FONTNAME', (0, 0), (-1, -1), 'Dotcirful-Regular'),  # all columns
        ('GRID', (0, 0), (-1, -1), 0.5, colors.green),  # all columns
        ('FONTSIZE', (0, 0), (-1, -1), 12),  # all columns
        ('TOPPADDING', (0, 0), (-1, -1), -3),  # all columns
    ]
    style_table2 = [
        ('FONTNAME', (0, 0), (-1, -1), 'Dotcirful-Regular'),  # all columns
        ('GRID', (0, 0), (-1, -1), 0.5, colors.red),  # all columns
        ('FONTSIZE', (0, 0), (-1, -1), 12),  # all columns
        ('TOPPADDING', (0, 0), (-1, -1), -3),  # all columns
    ]
    style_table3 = [
        ('FONTNAME', (0, 0), (-1, -1), 'Dotcirful-Regular'),  # all columns
        ('GRID', (0, 0), (-1, -1), 0.5, colors.yellow),  # all columns
        ('FONTSIZE', (0, 0), (-1, -1), 10),  # all columns
        ('TOPPADDING', (0, 0), (-1, -1), -3),  # all columns
    ]

    style_table4 = [
        ('FONTNAME', (0, 0), (-1, -1), 'Square'),  # all columns
        ('GRID', (0, 0), (-1, -1), 0.5, colors.fuchsia),  # all columns
        ('FONTSIZE', (0, 0), (-1, -1), 9),  # all columns
        # ('TOPPADDING', (0, 0), (-1, -1), -3),  # all columns
    ]

    colwiths_table0 = [_a6 * 75 / 100, _a6 * 25 / 100]
    colwiths_table = [_a6 * 20 / 100, _a6 * 25 / 100, _a6 * 25 / 100, _a6 * 15 / 100, _a6 * 15 / 100]
    colwiths_table2 = [_a6 * 45 / 100, _a6 * 15 / 100, _a6 * 20 / 100, _a6 * 20 / 100]
    colwiths_table3 = [_a6 * 10 / 100, _a6 * 30 / 100, _a6 * 7 / 100, _a6 * 27 / 100, _a6 * 13 / 100, _a6 * 13 / 100]
    colwiths_table4 = [_a6 * 5 / 100, _a6 * 15 / 100, _a6 * 45 / 100, _a6 * 15 / 100, _a6 * 10 / 100, _a6 * 10 / 100]

    programming_obj = Programming.objects.get(id=pk)

    _pilot = programming_obj.get_pilot()
    _copilot = programming_obj.get_copilot()
    _n_license_pilot = _pilot.n_license
    if _copilot:
        _copilot_full_name = _copilot.full_name()
        _n_license_copilot = _copilot.n_licens

    _serial_correlative = str(programming_obj.serial + '-' + programming_obj.correlative.zfill(6))
    _truck = programming_obj.truck
    _driver = _pilot.full_name()
    _brand = _truck.truck_model.truck_brand.name
    # _hour = programming_obj.get_turn_display()
    _date = str(programming_obj.departure_date.strftime("%d/%m/%y"))
    # _hour = str(programming_obj.departure_date.strftime("%I:%M:%S %p"))
    my_date = datetime.now()
    _hour = str(my_date.strftime("%I:%M %p"))

    if programming_obj.truck_exit is None:
        programming_obj.truck_exit = my_date

    user_id = request.user.id
    user_obj = User.objects.get(pk=int(user_id))
    subsidiary_origin_obj = get_subsidiary_by_user(user_obj)
    company_rotation_obj = user_obj.companyuser.company_rotation

    _short_name_origin = subsidiary_origin_obj.short_name

    subsidiary_destiny_obj = programming_obj.path.get_last_point()
    _short_name_destiny = subsidiary_destiny_obj.short_name

    p0 = Paragraph(_short_name_origin, styles["Justify-Dotcirful"])
    p1 = Paragraph(_short_name_destiny, styles["Justify-Dotcirful"])

    ana_c0 = Table([('', _serial_correlative)], colWidths=colwiths_table0)
    ana_c0.setStyle(TableStyle(style_table0))

    ana_c1 = Table([('', '', _brand, _hour, _date)], colWidths=colwiths_table)
    ana_c1.setStyle(TableStyle(style_table))

    ana_c2 = Table([(_pilot.full_name(), _truck, _n_license_pilot, _pilot.document_number)], colWidths=colwiths_table2)
    ana_c2.setStyle(TableStyle(style_table2))

    arr_ps_set = ProgrammingSeat.objects.filter(programming=programming_obj.id).values_list('plan_detail__name',
                                                                                            flat=True)
    arr_ps_strings = list(map(int, arr_ps_set))
    arr_ps_strings.sort()
    _rows = []
    for element in arr_ps_strings:
        ps = ProgrammingSeat.objects.get(programming=programming_obj, plan_detail__name=str(element))
        name = ''
        document = ''
        serial_correlative = ''
        price = ''
        if ps.status == '4':
            order_obj = Order.objects.filter(programming_seat=ps, status='C').last()
            name = order_obj.client.names
            price = str(order_obj.total)
            document = order_obj.client.clienttype_set.first().document_number
            serial_correlative = str(order_obj.serial + '-' + order_obj.correlative_sale.zfill(6))
        # _rows.append((ps.plan_detail.name, name, document, serial_correlative))
        _rows.append(('', serial_correlative, name, document, price, ''))

    ana_c4 = Table(_rows, colWidths=colwiths_table4, rowHeights=0.22 * inch)
    ana_c4.setStyle(TableStyle(style_table4))

    programming_obj.status = 'E'
    programming_obj.save()

    '''
        printer_name = 'EPSON FX-890 (PLUS)'
    
        p = win32print.OpenPrinter(printer_name)
        job = win32print.StartDocPrinter(p, 1, ("test of raw data", None, "RAW"))
        win32print.StartPagePrinter(p)
        win32print.WritePrinter(p, "data to print")
        win32print.EndPagePrinter(p)
    '''

    buff = io.BytesIO()
    doc = SimpleDocTemplate(buff,
                            pagesize=_custom_a5,
                            rightMargin=mr,
                            leftMargin=ml,
                            topMargin=ms,
                            bottomMargin=mi,
                            title='Manifiesto de pasajeros'
                            )
    response = HttpResponse(content_type='application/pdf')

    # response['Content-Disposition'] = 'attachment; filename="MPE_{}_{}.pdf"'.format(
    #     programming_obj.serial, programming_obj.correlative)

    # Wait for 5 seconds
    # time.sleep(8)

    tomorrow = datetime.now() + timedelta(days=1)
    tomorrow = tomorrow.replace(hour=0, minute=0, second=0)
    expires = datetime.strftime(tomorrow, "%a, %d-%b-%Y %H:%M:%S GMT")

    response.set_cookie('mpe', value=pk, expires=expires)

    _dictionary = []
    _dictionary.append(Spacer(53, 53))  # antes estaba en 100, 100
    _dictionary.append(ana_c0)
    _dictionary.append(Spacer(15, 15))
    _dictionary.append(ana_c1)
    _dictionary.append(Spacer(5, 5))
    _dictionary.append(ana_c2)
    _dictionary.append(Spacer(15, 15))
    _dictionary.append(ana_c4)

    doc.build(_dictionary)

    response.write(buff.getvalue())
    buff.close()
    return response


def print_report_commodity(request, start_date=None, end_date=None, user_selected=None, way_to_pay=None,
                           destiny=None):  # reporte de encomiendas

    _a5 = (5.8 * inch, 8.3 * inch)

    date_start_date = datetime.strptime(start_date, '%Y-%m-%d')
    date_end_date = datetime.strptime(end_date, '%Y-%m-%d')

    ml = 0.25 * inch
    mr = 0.25 * inch
    ms = 0.25 * inch
    mi = 0.25 * inch

    _bts = 5.8 * inch - 0.25 * inch - 0.25 * inch

    date = datetime.now()
    _formatdate = date.strftime("%d/%m/%Y")

    user_obj = request.user
    subsidiary_obj = get_subsidiary_by_user(user_obj)

    order_set = filter_report_orders(
        subsidiary_obj, start_date, end_date,
        user_selected=user_selected,
        way_to_pay=way_to_pay,
        destiny=destiny,
    ).order_by('id')

    _tbl_header = ('REPORTE DE ENCOMIENDAS',)

    ana_c = Table([_tbl_header], colWidths=[_bts * 100 / 100])

    my_style_table_header = [
        ('FONTNAME', (0, 0), (-1, -1), 'Square'),
        # ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('ALIGNMENT', (0, 0), (-1, -1), 'CENTER'),  # third column
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')  # first column
        # ('LEFTPADDING', (2, 0), (2, 0), 180),
        # ('LEFTPADDING', (1, 0), (1, 0), 291),
        # ('BOTTOMPADDING', (0, 0), (3, 0), -20),
        # ('BACKGROUND',  (0, 0), (3, 0), colors.pink)
    ]
    ana_c.setStyle(TableStyle(my_style_table_header))

    td_title = (
        'FECHA',
        'SERIE\nOS',
        'NRO.\nOS',
        'COMPROB.',
        'PAGO\nCONTADO',
        'PAGO\nDESTINO',
        'DESTINO',
        'USUARIO',
    )
    # Ancho útil A5 ≈ 5.3"; proporciones ajustadas a 8 columnas
    colwiths_table_title = [
        _bts * 12 / 100,  # fecha
        _bts * 10 / 100,  # serie OS
        _bts * 10 / 100,  # nro OS
        _bts * 14 / 100,  # comprobante B/F
        _bts * 11 / 100,  # contado
        _bts * 11 / 100,  # destino $
        _bts * 16 / 100,  # destino sede
        _bts * 16 / 100,  # usuario
    ]
    _rows = []
    _rows.append(td_title)
    cont_counted = decimal.Decimal('0.00')
    cont_destination_payment = decimal.Decimal('0.00')

    for o in order_set:
        _total_pay_counted = decimal.Decimal('0.00')
        _total_pay_destiny = decimal.Decimal('0.00')
        amount = decimal.Decimal(str(o.sum_total_details() or o.total or 0)).quantize(
            decimal.Decimal('0.00'), rounding=decimal.ROUND_HALF_EVEN,
        )

        if o.status != 'A':
            if o.way_to_pay == 'C':
                _total_pay_counted = amount
                cont_counted += amount
            elif o.way_to_pay == 'D':
                _total_pay_destiny = amount
                cont_destination_payment += amount

        encomienda = getattr(o, 'encomienda', None)
        if encomienda and encomienda.office_destination_id:
            destiny_obj = encomienda.office_destination.short_name or '—'
        else:
            destiny_obj = '—'

        user_label = o.user.username if o.user_id else '—'
        worker = o.user.worker_set.last() if o.user_id else None
        if worker and getattr(worker, 'employee_id', None):
            user_label = worker.employee.names or user_label

        os_serial = (o.order_serial or '').strip() or '—'
        os_corr = (o.order_correlative or '').strip()
        os_nro = os_corr.zfill(4) if os_corr else '—'
        if o.type_document in ('B', 'F') and (o.serial or '').strip() and (o.correlative_sale or '').strip():
            bill_label = f'{o.serial}-{str(o.correlative_sale).strip().zfill(4)}'
        else:
            bill_label = '—'

        _rows.append((
            o.transfer_date.strftime('%d/%m/%Y') if o.transfer_date else '—',
            os_serial,
            os_nro,
            bill_label,
            f'{_total_pay_counted:.2f}' if _total_pay_counted else '0.00',
            f'{_total_pay_destiny:.2f}' if _total_pay_destiny else '0.00',
            destiny_obj,
            user_label,
        ))

    ana_c3 = Table(_rows, colWidths=colwiths_table_title)

    colwiths_table_totals = [_bts * 55 / 100, _bts * 25 / 100, _bts * 20 / 100]
    p4 = Paragraph('TOTALES ENCOMIENDAS', styles["Center"])
    _tbl_totals = [
        ['', p4, ''],
        ['', 'TOTAL PAGO CONTADO:', 'S/. ' + str(cont_counted)],
        ['', 'TOTAL PAGO DESTINO:', 'S/. ' + str(cont_destination_payment)],
        ['', 'TOTAL GENERAL:', 'S/. ' + str(cont_counted + cont_destination_payment)],
    ]
    ana_c4 = Table(_tbl_totals, colWidths=colwiths_table_totals)

    detail_style = [
        ('FONTNAME', (0, 0), (-1, -1), 'Square'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 0), (-1, -1), 6.5),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('FONTNAME', (0, 0), (-1, 0), 'Square'),
        ('FONTSIZE', (0, 0), (-1, 0), 6.5),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]
    ana_c3.setStyle(TableStyle(detail_style))

    my_style_table_totals = [
        ('FONTNAME', (0, 0), (-1, -1), 'Square'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('VALIGN', (1, 0), (1, -1), 'MIDDLE'),
        ('SPAN', (1, 0), (2, 0)),
        ('ALIGNMENT', (1, 0), (2, -1), 'RIGHT'),
        ('FONTNAME', (1, -1), (2, -1), 'Square-Bold'),
    ]
    ana_c4.setStyle(TableStyle(my_style_table_totals))

    buff = io.BytesIO()
    doc = SimpleDocTemplate(buff,
                            pagesize=A5,
                            rightMargin=mr,
                            leftMargin=ml,
                            topMargin=ms,
                            bottomMargin=mi,
                            title='Reporte de Encomiendas'
                            )
    dictionary = []
    dictionary.append(ana_c)
    dictionary.append(Spacer(10, 10))
    dictionary.append(ana_c3)
    dictionary.append(Spacer(10, 10))
    dictionary.append(ana_c4)

    response = HttpResponse(content_type='application/pdf')
    doc.build(dictionary)
    response['Content-Disposition'] = 'attachment; filename="ReporteDeEncomiendas_[{}].pdf"'.format(_formatdate)
    # doc.build(elements)
    # doc.build(Story)
    response.write(buff.getvalue())
    buff.close()
    return response


# ---------------------------------------------------------------------------------------------------------------
# Guias de remision (remitente / transportista) y manifiesto de carga
# Estas funciones viven en pdf_guides.py (modulo unificado) y se reexportan aqui
# para no romper los imports existentes (urls.py, views.py, etc.).
# ---------------------------------------------------------------------------------------------------------------
from apps.comercial.pdf_guides import (  # noqa: E402
    print_guide_format_tk,
    print_guide_format_a4,
    print_cargo_manifest,
)
