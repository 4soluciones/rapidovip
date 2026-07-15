import decimal
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
                           arrival_time=None, address_delivery='', code='0000'):
    """Persiste el detalle de encomienda."""
    return OrderCommodity.objects.create(
        order=order_obj,
        office_origin=subsidiary_origin,
        office_destination=subsidiary_destiny,
        type_guide=type_guide or 'O',
        arrival_time=_parse_time(arrival_time),
        address_delivery=address_delivery or '',
        code=(code or '0000').strip() or '0000',
    )


def get_service_destiny_label(order_obj):
    """Etiqueta de destino para el reporte de encomiendas."""
    encomienda = getattr(order_obj, 'encomienda', None)
    if encomienda and encomienda.office_destination_id:
        return encomienda.office_destination.short_name or encomienda.office_destination.name
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
    ).select_related('user', 'company', 'truck', 'encomienda')
