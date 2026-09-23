import json
from datetime import datetime
from http import HTTPStatus

from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch, Q
from django.http import JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.views.decorators.http import require_GET, require_POST


from apps.sales.models import (
    CREDIT_NOTE_MOTIVE_CHOICES,
    Order,
    OrderAction,
    OrderBill,
    OrderCreditNote,
)
from apps.users.user_helpers import get_subsidiary_by_user


def _parse_date(value):
    value = (value or '').strip()
    if not value:
        return None
    return datetime.strptime(value, '%Y-%m-%d').date()


@login_required
@require_GET
def electronic_vouchers_report(request):
    subsidiary = get_subsidiary_by_user(request.user)
    return render(request, 'sales/electronic_vouchers_report.html', {
        'subsidiary': subsidiary,
        'date_now': datetime.now().strftime('%Y-%m-%d'),
        'motive_choices': CREDIT_NOTE_MOTIVE_CHOICES,
    })


@login_required
@require_POST
def electronic_vouchers_grid(request):
    subsidiary = get_subsidiary_by_user(request.user)
    start_date = _parse_date(request.POST.get('start-date'))
    end_date = _parse_date(request.POST.get('end-date'))
    doc_type = (request.POST.get('doc_type') or 'B').strip().upper()

    if not start_date or not end_date:
        return JsonResponse({'error': 'Indique un rango de fechas válido.'}, status=HTTPStatus.BAD_REQUEST)
    if start_date > end_date:
        return JsonResponse(
            {'error': 'La fecha inicial no puede ser mayor que la final.'},
            status=HTTPStatus.BAD_REQUEST,
        )
    if doc_type not in ('B', 'F', 'N'):
        return JsonResponse({'error': 'Tipo de comprobante no válido.'}, status=HTTPStatus.BAD_REQUEST)

    rows = []
    total_amount = 0.0

    if doc_type == 'N':
        notes = (
            OrderCreditNote.objects.filter(
                status='E',
                created_at__date__range=[start_date, end_date],
                order__subsidiary=subsidiary,
            )
            .select_related('order', 'order__client', 'order__user', 'order_bill', 'user')
            .order_by('-created_at', '-id')
        )
        for note in notes:
            order = note.order
            related = '—'
            if note.order_bill_id:
                related = f'{note.order_bill.serial}-{str(note.order_bill.n_receipt).zfill(8)}'
            elif order:
                related = f'{order.serial or ""}-{order.correlative_sale or ""}'
            client_name = (order.client.names if order and order.client_id else None) or '—'
            rows.append({
                'order_id': order.id if order else None,
                'date': note.created_at,
                'document_number': note.full_number,
                'related_document': related,
                'client_name': client_name,
                'total': note.total,
                'status_label': note.get_status_display(),
                'motive_label': note.motive_label,
                'user': note.user.username if note.user_id else '—',
                'pdf_url': note.sunat_enlace_pdf or '',
                'has_credit_note': True,
                'can_credit_note': False,
                'credit_note_number': '',
            })
            total_amount += float(note.total or 0)
        type_label = 'Notas de crédito'
    else:
        orders = (
            Order.objects.filter(
                subsidiary=subsidiary,
                type_document=doc_type,
                orderbill__status='E',
            )
            .filter(
                Q(orderbill__created_at__date__range=[start_date, end_date])
                | Q(orderbill__created_at__isnull=True, create_at__date__range=[start_date, end_date])
            )
            .select_related('client', 'user', 'orderbill')
            .prefetch_related(
                Prefetch(
                    'orderaction_set',
                    queryset=OrderAction.objects.filter(type='R').select_related('client'),
                    to_attr='sender_actions',
                ),
                Prefetch(
                    'credit_notes',
                    queryset=OrderCreditNote.objects.filter(status='E'),
                    to_attr='active_credit_notes',
                ),
            )
            .order_by('-create_at', '-id')
        )
        for order in orders:
            bill = getattr(order, 'orderbill', None)
            if bill is None:
                continue
            active_notes = getattr(order, 'active_credit_notes', []) or []
            has_nc = bool(active_notes)
            client_name = (order.client.names if order.client_id else '') or ''
            if not client_name and getattr(order, 'sender_actions', None):
                sender = order.sender_actions[0]
                if sender.client_id:
                    client_name = sender.client.names or ''
            rows.append({
                'order_id': order.id,
                'date': bill.created_at or order.create_at,
                'document_number': f'{bill.serial or order.serial or ""}-{str(bill.n_receipt).zfill(8)}',
                'related_document': '',
                'client_name': client_name or '—',
                'total': order.total,
                'status_label': 'Con NC' if has_nc else bill.get_status_display(),
                'motive_label': '',
                'user': order.user.username if order.user_id else '—',
                'pdf_url': bill.sunat_enlace_pdf or '',
                'has_credit_note': has_nc,
                'can_credit_note': (not has_nc) and bill.status == 'E',
                'credit_note_number': active_notes[0].full_number if has_nc else '',
            })
            total_amount += float(order.total or 0)
        type_label = 'Boletas' if doc_type == 'B' else 'Facturas'

    count = len(rows)
    grid = render_to_string('sales/electronic_vouchers_grid.html', {
        'rows': rows,
        'count': count,
        'total_amount': f'{total_amount:,.2f}',
        'f1': start_date.strftime('%d/%m/%Y'),
        'f2': end_date.strftime('%d/%m/%Y'),
        'doc_type': doc_type,
        'type_label': type_label,
    }, request=request)

    return JsonResponse({
        'grid': grid,
        'count': count,
        'error': None if count else 'No se encontraron comprobantes para los filtros seleccionados.',
    })


@login_required
@require_GET
def electronic_voucher_credit_note_data(request, order_id):
    subsidiary = get_subsidiary_by_user(request.user)
    try:
        order = (
            Order.objects.select_related('client', 'orderbill')
            .prefetch_related('orderdetail_set__unit')
            .get(id=int(order_id), subsidiary=subsidiary)
        )
    except Order.DoesNotExist:
        return JsonResponse({'error': 'Orden no encontrada.'}, status=HTTPStatus.NOT_FOUND)

    if order.type_document not in ('B', 'F'):
        return JsonResponse(
            {'error': 'Solo boletas o facturas admiten nota de crédito.'},
            status=HTTPStatus.BAD_REQUEST,
        )

    try:
        bill = order.orderbill
    except OrderBill.DoesNotExist:
        bill = None
    if bill is None or bill.status != 'E':
        return JsonResponse(
            {'error': 'No hay comprobante electrónico emitido.'},
            status=HTTPStatus.BAD_REQUEST,
        )
    if OrderCreditNote.objects.filter(order=order, status='E').exists():
        return JsonResponse(
            {'error': 'Esta orden ya tiene una nota de crédito emitida.'},
            status=HTTPStatus.BAD_REQUEST,
        )

    details = []
    for d in order.orderdetail_set.all():
        qty = d.quantity or 0
        price = d.price_unit or 0
        details.append({
            'id': d.id,
            'description': (d.description or 'TRANSPORTE DE CARGA').upper(),
            'quantity': float(qty),
            'price_unit': float(price),
            'amount': float(d.amount or (qty * price)),
            'unit': d.unit.name if d.unit_id else 'ZZ',
        })

    return JsonResponse({
        'order_id': order.id,
        'document_type': order.type_document,
        'document_type_label': 'Factura' if order.type_document == 'F' else 'Boleta',
        'document_number': f'{bill.serial}-{str(bill.n_receipt).zfill(8)}',
        'client_name': (order.client.names if order.client_id else '—') or '—',
        'total': float(order.total or 0),
        'details': details,
        'motives': [{'code': c, 'label': l} for c, l in CREDIT_NOTE_MOTIVE_CHOICES],
    })


@login_required
@require_POST
def electronic_voucher_generate_credit_note(request):
    subsidiary = get_subsidiary_by_user(request.user)
    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except (json.JSONDecodeError, UnicodeDecodeError):
        payload = request.POST

    try:
        order = Order.objects.get(id=int(payload.get('order_id')), subsidiary=subsidiary)
    except (Order.DoesNotExist, TypeError, ValueError):
        return JsonResponse({'error': 'Orden no válida.'}, status=HTTPStatus.BAD_REQUEST)

    if order.type_document not in ('B', 'F'):
        return JsonResponse(
            {'error': 'Solo se puede generar NC sobre boletas o facturas.'},
            status=HTTPStatus.BAD_REQUEST,
        )

    result = send_credit_note_fact(
        order.id,
        payload.get('motive') or '01',
        details=payload.get('details'),
        fees=None,
        user=request.user,
        motive_description=(payload.get('motive_description') or '').strip(),
    )

    if not result.get('success'):
        return JsonResponse(
            {
                'error': result.get('message') or result.get('error') or 'No se pudo emitir la NC.',
                'detail': result.get('error'),
            },
            status=HTTPStatus.BAD_GATEWAY,
        )

    return JsonResponse({
        'message': result.get('message') or 'Nota de crédito emitida correctamente.',
        'serie': result.get('serie'),
        'numero': result.get('numero'),
        'full_number': result.get('full_number'),
        'pdf_url': result.get('enlace_del_pdf') or '',
        'credit_note_id': result.get('credit_note_id'),
    })
