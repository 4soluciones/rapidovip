from datetime import datetime, time

from django.db.models import Prefetch

from apps.sales.models import (
    Order,
    OrderAction,
    OrderCommodity,
    OrderDetail,
)


def _parse_time(value):
    if not value or value in ('00:00', 'None'):
        return None
    if isinstance(value, time):
        return value
    try:
        return datetime.strptime(str(value), '%H:%M').time()
    except ValueError:
        try:
            return datetime.strptime(str(value), '%H:%M:%S').time()
        except ValueError:
            return None


def _parse_date(value):
    if not value:
        return None
    if hasattr(value, 'year'):
        return value
    try:
        return datetime.strptime(str(value), '%Y-%m-%d').date()
    except ValueError:
        return None


def save_service_for_order(order_obj, service_type, *,
                           subsidiary_origin=None, subsidiary_destiny=None,
                           type_guide='O',
                           arrival_time=None, address_delivery='',
                           ubigeo_delivery='', code='0000'):
    """Persiste el detalle de encomienda."""
    return OrderCommodity.objects.create(
        order=order_obj,
        office_origin=subsidiary_origin,
        office_destination=subsidiary_destiny,
        type_guide=type_guide or 'O',
        arrival_time=_parse_time(arrival_time),
        address_delivery=address_delivery or '',
        ubigeo_delivery=(ubigeo_delivery or '').strip(),
        code=(code or '0000').strip() or '0000',
    )


def get_service_destiny_label(order_obj):
    """Etiqueta de destino para el reporte de encomiendas."""
    encomienda = getattr(order_obj, 'encomienda', None)
    if encomienda:
        return encomienda.effective_destination_label()
    return '—'


def prefetch_orders_for_report(order_set):
    return order_set.prefetch_related(
        Prefetch(
            'orderdetail_set',
            queryset=OrderDetail.objects.select_related('unit'),
        ),
        Prefetch(
            'orderaction_set',
            queryset=OrderAction.objects.select_related('client', 'order_addressee'),
        ),
        'encomienda__office_destination',
        'encomienda__office_origin',
    ).select_related('user', 'company', 'truck', 'encomienda', 'orderbill')


def _is_all_filter(value):
    """True cuando el filtro significa 'todos' (sin restricción)."""
    if value is None:
        return True
    return str(value).strip().upper() in ('', 'ALL', 'T', 'NONE', 'NULL')


def normalize_report_filter(value):
    """Devuelve None si el filtro es 'todos'; si no, el valor limpio."""
    if _is_all_filter(value):
        return None
    return str(value).strip()


def report_filter_url_value(value):
    """Valor seguro para URLs del PDF: ALL cuando no hay filtro."""
    normalized = normalize_report_filter(value)
    return normalized if normalized else 'ALL'


def filter_report_orders(subsidiary_obj, start_date, end_date,
                         service_type=None, user_selected=None, way_to_pay=None, destiny=None):
    """
    Encomiendas emitidas en la sede.
    Vacío / T / ALL = sin filtro en ese campo (no busca service_type='T').
    """
    service_type = (service_type or '').strip()
    user_selected = (user_selected or '').strip()
    way_to_pay = (way_to_pay or '').strip()
    destiny = (destiny or '').strip()

    order_set = Order.objects.filter(
        subsidiary=subsidiary_obj,
        type_order='E',
        transfer_date__range=[start_date, end_date],
    )
    if service_type and service_type.upper() not in ('T', 'ALL'):
        order_set = order_set.filter(service_type=service_type)
    if user_selected.isdigit():
        order_set = order_set.filter(user_id=int(user_selected))
    if way_to_pay and way_to_pay.upper() not in ('T', 'ALL'):
        order_set = order_set.filter(way_to_pay=way_to_pay)
    if destiny.isdigit():
        order_set = order_set.filter(encomienda__office_destination_id=int(destiny))
    return prefetch_orders_for_report(order_set).order_by('-transfer_date', '-id')
