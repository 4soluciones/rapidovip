from decimal import Decimal
from datetime import date, datetime
from http import HTTPStatus

from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch, Q
from django.http import JsonResponse
from django.shortcuts import render
from django.template import loader

from apps.accounting.models import CashFlow
from apps.sales.api_FACT import (
    _commodity_product_description,
    annul_invoice,
    send_credit_note_fact,
)
from apps.sales.models import (
    CREDIT_NOTE_MOTIVE_CHOICES,
    Client,
    ClientType,
    Order,
    OrderBill,
    OrderCreditNote,
    OrderDetail,
)
from apps.users.user_helpers import get_subsidiary_by_user

ANNUL_DAYS_LIMIT = {'B': 5, 'F': 3}


def _emission_date(order_bill, order):
    if order_bill.created_at:
        return order_bill.created_at.date()
    if order.transfer_date:
        return order.transfer_date
    if order.create_at:
        return order.create_at.date()
    return date.today()


def _can_annul_voucher(order_bill, order):
    if order_bill.status != 'E' or order.status == 'A':
        return False, 'El comprobante no está vigente.'
    if order.type_document not in ANNUL_DAYS_LIMIT:
        return False, 'Tipo de comprobante no anulable.'
    emission = _emission_date(order_bill, order)
    days_elapsed = (date.today() - emission).days
    limit = ANNUL_DAYS_LIMIT[order.type_document]
    if days_elapsed > limit:
        return False, (
            f'Solo puede anular {"boletas" if order.type_document == "B" else "facturas"} '
            f'hasta {limit} días después de la emisión ({days_elapsed} días transcurridos).'
        )
    return True, None


def _can_issue_credit_note(order_bill, order):
    if order_bill.status != 'E' or order.status == 'A':
        return False
    if order.type_document not in ('B', 'F'):
        return False
    if order_bill.credit_notes.filter(status='E').exists():
        return False
    return True


def _client_display(order):
    client = order.client
    if client is None:
        client = Client.objects.filter(
            orderaction__order=order, orderaction__type='R',
        ).first()
    if not client:
        return {'names': '—', 'document': '—'}
    client_type = client.clienttype_set.select_related('document_type').first()
    doc_label = ''
    doc_number = ''
    if client_type:
        doc_label = getattr(client_type.document_type, 'description', '') or ''
        doc_number = client_type.document_number or ''
    return {
        'names': (client.names or '—').upper(),
        'document': f'{doc_label} {doc_number}'.strip() or '—',
    }


def _doc_type_label(doc_type):
    labels = {'B': 'Boleta', 'F': 'Factura', 'NC': 'Nota de crédito'}
    return labels.get(doc_type, doc_type)


def _build_voucher_rows(bills_qs, credit_notes_qs):
    rows = []

    for bill in bills_qs:
        order = bill.order
        client = _client_display(order)
        can_annul, annul_reason = _can_annul_voucher(bill, order)
        rows.append({
            'row_type': 'bill',
            'pk': bill.order_id,
            'order_id': order.id,
            'doc_type': order.type_document,
            'doc_type_label': _doc_type_label(order.type_document),
            'serial': bill.serial or order.serial or '',
            'number': str(bill.n_receipt).zfill(4),
            'full_number': f'{bill.serial or order.serial}-{str(bill.n_receipt).zfill(4)}',
            'client_names': client['names'],
            'client_document': client['document'],
            'total': order.total,
            'emission_date': _emission_date(bill, order),
            'status': bill.status,
            'status_label': 'Anulado' if bill.status == 'A' or order.status == 'A' else 'Emitido',
            'is_cancelled': bill.status == 'A' or order.status == 'A',
            'pdf_url': bill.sunat_enlace_pdf or '',
            'order_service': f'{order.order_serial or ""}-{order.order_correlative or ""}'.strip('-'),
            'user_name': (order.user.username if order.user_id else '').upper(),
            'can_annul': can_annul,
            'annul_reason': annul_reason or '',
            'can_credit_note': _can_issue_credit_note(bill, order),
            'related_doc': '',
        })

    for cn in credit_notes_qs:
        order = cn.order
        bill = cn.order_bill
        client = _client_display(order)
        related = ''
        if bill:
            related = f'{bill.serial or ""}-{str(bill.n_receipt).zfill(4)}'.strip('-')
        rows.append({
            'row_type': 'credit_note',
            'pk': cn.id,
            'order_id': order.id,
            'doc_type': 'NC',
            'doc_type_label': _doc_type_label('NC'),
            'serial': cn.serial,
            'number': str(cn.n_receipt).zfill(4),
            'full_number': f'{cn.serial}-{str(cn.n_receipt).zfill(4)}',
            'client_names': client['names'],
            'client_document': client['document'],
            'total': cn.total,
            'emission_date': cn.created_at.date() if cn.created_at else date.today(),
            'status': cn.status,
            'status_label': 'Anulado' if cn.status == 'A' else 'Emitido',
            'is_cancelled': cn.status == 'A',
            'pdf_url': cn.sunat_enlace_pdf or '',
            'order_service': f'{order.order_serial or ""}-{order.order_correlative or ""}'.strip('-'),
            'user_name': (cn.user.username if cn.user_id else '').upper(),
            'can_annul': False,
            'annul_reason': '',
            'can_credit_note': False,
            'related_doc': related,
            'motive_label': cn.get_motive_display(),
        })

    rows.sort(key=lambda r: (r['emission_date'], r['pk']), reverse=True)
    return rows


def _filter_voucher_querysets(subsidiary, start_date, end_date, doc_filter=''):
    bill_qs = OrderBill.objects.filter(
        order__subsidiary=subsidiary,
        order__type_document__in=('B', 'F'),
    ).select_related('order', 'order__client', 'order__user', 'order__company')

    cn_qs = OrderCreditNote.objects.filter(
        order__subsidiary=subsidiary,
    ).select_related('order', 'order__client', 'order__user', 'order_bill', 'user')

    if start_date and end_date:
        bill_qs = bill_qs.filter(
            Q(created_at__date__range=[start_date, end_date])
            | Q(order__transfer_date__range=[start_date, end_date])
            | Q(order__create_at__date__range=[start_date, end_date]),
        )
        cn_qs = cn_qs.filter(created_at__date__range=[start_date, end_date])

    doc_filter = (doc_filter or '').upper()
    if doc_filter == 'B':
        bill_qs = bill_qs.filter(order__type_document='B')
        cn_qs = cn_qs.none()
    elif doc_filter == 'F':
        bill_qs = bill_qs.filter(order__type_document='F')
        cn_qs = cn_qs.none()
    elif doc_filter == 'NC':
        bill_qs = OrderBill.objects.none()
    return bill_qs, cn_qs


def _render_voucher_grid(request, subsidiary, start_date, end_date, doc_filter=''):
    bill_qs, cn_qs = _filter_voucher_querysets(subsidiary, start_date, end_date, doc_filter)
    rows = _build_voucher_rows(bill_qs, cn_qs)
    total_amount = sum(
        (r['total'] for r in rows if not r['is_cancelled']),
        Decimal('0'),
    )
    tpl = loader.get_template('sales/electronic_voucher_grid.html')
    return tpl.render({
        'rows': rows,
        'count': len(rows),
        'f1': start_date,
        'f2': end_date,
        'total_amount': total_amount,
        'doc_filter': doc_filter,
    }, request)


@login_required
def electronic_voucher_report(request):
    subsidiary = get_subsidiary_by_user(request.user)
    date_now = datetime.now().strftime('%Y-%m-%d')

    if request.method == 'GET':
        return render(request, 'sales/electronic_voucher_report.html', {
            'date_now': date_now,
            'subsidiary': subsidiary,
            'doc_types': (
                ('', 'Todos'),
                ('B', 'Boletas'),
                ('F', 'Facturas'),
                ('NC', 'Notas de crédito'),
            ),
        })

    if request.method == 'POST':
        start_date = (request.POST.get('start-date') or '').strip()
        end_date = (request.POST.get('end-date') or '').strip()
        doc_filter = (request.POST.get('doc_type') or '').strip()

        if not start_date or not end_date:
            return JsonResponse({'error': 'Indique el rango de fechas.'}, status=HTTPStatus.BAD_REQUEST)

        grid_html = _render_voucher_grid(request, subsidiary, start_date, end_date, doc_filter)
        bill_qs, cn_qs = _filter_voucher_querysets(subsidiary, start_date, end_date, doc_filter)
        count = bill_qs.count() + cn_qs.count()

        if count == 0:
            return JsonResponse({
                'error': f'No hay comprobantes electrónicos del {start_date} al {end_date}.',
                'grid': (
                    '<div class="rv-report-empty"><i class="fas fa-inbox"></i>'
                    f'<p>No hay comprobantes electrónicos del <strong>{start_date}</strong> '
                    f'al <strong>{end_date}</strong>.</p></div>'
                ),
            }, status=HTTPStatus.OK)

        return JsonResponse({'grid': grid_html}, status=HTTPStatus.OK)

    return JsonResponse({'error': 'Método no permitido.'}, status=HTTPStatus.METHOD_NOT_ALLOWED)


@login_required
def annul_electronic_voucher(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido.'}, status=HTTPStatus.METHOD_NOT_ALLOWED)

    reason = (request.POST.get('reason') or '').strip()
    if not reason:
        return JsonResponse({'error': 'Debe indicar el motivo de anulación.'}, status=HTTPStatus.BAD_REQUEST)

    try:
        order_id = int(request.POST.get('pk', 0))
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Comprobante no válido.'}, status=HTTPStatus.BAD_REQUEST)

    subsidiary = get_subsidiary_by_user(request.user)
    try:
        order = Order.objects.get(pk=order_id, subsidiary=subsidiary, type_document__in=('B', 'F'))
        order_bill = OrderBill.objects.get(order=order)
    except (Order.DoesNotExist, OrderBill.DoesNotExist):
        return JsonResponse({'error': 'El comprobante no existe.'}, status=HTTPStatus.NOT_FOUND)

    can_annul, annul_msg = _can_annul_voucher(order_bill, order)
    if not can_annul:
        return JsonResponse({'error': annul_msg}, status=HTTPStatus.BAD_REQUEST)

    result = annul_invoice(order.id)
    if not result.get('success'):
        msg = result.get('message') or 'Error de anulación en SUNAT.'
        return JsonResponse({'error': msg}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    order_bill.status = 'A'
    order_bill.save(update_fields=['status'])
    order.status = 'A'
    order.cancel_motive = reason
    order.save(update_fields=['status', 'cancel_motive', 'update_at'])
    CashFlow.objects.filter(order=order).delete()

    start_date = (request.POST.get('start-date') or '').strip()
    end_date = (request.POST.get('end-date') or '').strip()
    doc_filter = (request.POST.get('doc_type') or '').strip()
    grid_html = _render_voucher_grid(request, subsidiary, start_date, end_date, doc_filter)

    return JsonResponse({
        'message': 'Comprobante anulado correctamente en SUNAT.',
        'grid': grid_html,
    }, status=HTTPStatus.OK)


@login_required
def credit_note_modal(request, order_id):
    subsidiary = get_subsidiary_by_user(request.user)
    try:
        order = Order.objects.prefetch_related(
            Prefetch('orderdetail_set', queryset=OrderDetail.objects.select_related('unit')),
            Prefetch(
                'client__clienttype_set',
                queryset=ClientType.objects.select_related('document_type'),
            ),
            Prefetch('client__clientaddress_set'),
        ).get(pk=order_id, subsidiary=subsidiary, type_document__in=('B', 'F'))
        order_bill = OrderBill.objects.get(order=order)
    except (Order.DoesNotExist, OrderBill.DoesNotExist):
        return JsonResponse({'error': 'Comprobante no encontrado.'}, status=HTTPStatus.NOT_FOUND)

    if not _can_issue_credit_note(order_bill, order):
        return JsonResponse({
            'error': 'No se puede emitir nota de crédito para este comprobante.',
        }, status=HTTPStatus.BAD_REQUEST)

    client = _client_display(order)
    order_details = list(order.orderdetail_set.all())
    service_description = _commodity_product_description(order_details)
    order_total = order.total or Decimal('0')
    sub_total = order_total / Decimal('1.18')
    igv_total = order_total - sub_total

    return render(request, 'sales/credit_note_modal.html', {
        'order': order,
        'order_bill': order_bill,
        'client': client,
        'service_description': service_description,
        'motives': CREDIT_NOTE_MOTIVE_CHOICES,
        'sub_total': sub_total,
        'igv_total': igv_total,
        'order_total': order_total,
        'full_number': f'{order_bill.serial or order.serial}-{str(order_bill.n_receipt).zfill(4)}',
        'doc_type_label': _doc_type_label(order.type_document),
    })


@login_required
def send_credit_note(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido.'}, status=HTTPStatus.METHOD_NOT_ALLOWED)

    try:
        order_id = int(request.POST.get('order_id', 0))
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Orden no válida.'}, status=HTTPStatus.BAD_REQUEST)

    motive = (request.POST.get('motive') or '01').strip()
    if not motive:
        return JsonResponse({'error': 'Seleccione el motivo de la nota de crédito.'}, status=HTTPStatus.BAD_REQUEST)

    subsidiary = get_subsidiary_by_user(request.user)
    try:
        order = Order.objects.get(pk=order_id, subsidiary=subsidiary, type_document__in=('B', 'F'))
        order_bill = OrderBill.objects.get(order=order)
    except (Order.DoesNotExist, OrderBill.DoesNotExist):
        return JsonResponse({'error': 'Comprobante no encontrado.'}, status=HTTPStatus.NOT_FOUND)

    if not _can_issue_credit_note(order_bill, order):
        return JsonResponse({
            'error': 'No se puede emitir nota de crédito para este comprobante.',
        }, status=HTTPStatus.BAD_REQUEST)

    result = send_credit_note_fact(order_id, [], motive, user=request.user)
    if not result.get('success'):
        msg = result.get('message') or result.get('error') or 'Error al emitir la nota de crédito.'
        return JsonResponse({'error': msg}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    if result.get('dry_run') and not OrderCreditNote.objects.filter(
        order=order, serial=result.get('serie'), n_receipt=int(result.get('numero') or 0),
    ).exists():
        OrderCreditNote.objects.create(
            order=order,
            order_bill=order_bill,
            serial=result.get('serie'),
            n_receipt=int(result.get('numero') or 0),
            motive=motive[:2],
            total=order.total,
            status='E',
            operation_id=int(result.get('operationId') or 0),
            sunat_enlace_pdf=result.get('enlace_del_pdf', ''),
            user=request.user,
            company=order.company,
        )

    start_date = (request.POST.get('start-date') or '').strip()
    end_date = (request.POST.get('end-date') or '').strip()
    doc_filter = (request.POST.get('doc_type') or '').strip()
    grid_html = _render_voucher_grid(request, subsidiary, start_date, end_date, doc_filter)

    return JsonResponse({
        'message': result.get('message') or 'Nota de crédito emitida correctamente.',
        'pdf_url': result.get('enlace_del_pdf', ''),
        'grid': grid_html,
    }, status=HTTPStatus.OK)
