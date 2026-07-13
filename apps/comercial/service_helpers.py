import decimal
from datetime import datetime, time

from django.db.models import Prefetch

from apps.sales.models import (
    Order,
    OrderAction,
    OrderCommodity,
    OrderCommodityAddressee,
    OrderDetail,
    OrderRoute,
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


def sync_commodity_addressees(commodity, addressee_actions):
    """Vincula destinatarios de OrderAction al modelo de encomienda."""
    if not commodity:
        return
    commodity.addressee_links.all().delete()
    for position, action in enumerate(addressee_actions):
        OrderCommodityAddressee.objects.create(
            commodity=commodity,
            client=action.client,
            order_addressee=action.order_addressee,
            position=position,
        )


def _parse_date(value):
    if not value:
        return None
    if hasattr(value, 'year'):
        return value
    try:
        return datetime.strptime(str(value), '%Y-%m-%d').date()
    except ValueError:
        return None


def save_service_for_order(order_obj, service_type, service_extra=None, *,
                           subsidiary_origin=None, subsidiary_destiny=None,
                           sender=None, type_guide='O',
                           arrival_time=None, address_delivery='', code='0000'):
    """Persiste el detalle de encomienda."""
    service_extra = service_extra or {}
    return OrderCommodity.objects.create(
        order=order_obj,
        sender=sender,
        office_origin=subsidiary_origin,
        office_destination=subsidiary_destiny,
        type_guide=type_guide or 'O',
        arrival_time=_parse_time(arrival_time),
        address_delivery=address_delivery or '',
        code=(code or '0000').strip() or '0000',
        addressee_name=service_extra.get('addressee_name', '') or '',
    )


def get_service_destiny_label(order_obj):
    """Etiqueta de destino para el reporte de encomiendas."""
    encomienda = getattr(order_obj, 'encomienda', None)
    if encomienda and encomienda.office_destination_id:
        return encomienda.office_destination.short_name or encomienda.office_destination.name
    for route in order_obj.orderroute_set.all():
        if route.type == 'D' and route.subsidiary_id:
            return route.subsidiary.name
    return '—'


def prefetch_orders_for_report(order_set):
    return order_set.prefetch_related(
        Prefetch(
            'orderdetail_set',
            queryset=OrderDetail.objects.select_related('unit'),
        ),
        Prefetch(
            'orderroute_set',
            queryset=OrderRoute.objects.filter(type='D').select_related('subsidiary'),
        ),
        Prefetch(
            'orderaction_set',
            queryset=OrderAction.objects.select_related('client', 'order_addressee'),
        ),
        'encomienda__office_destination',
        'encomienda__office_origin',
        'encomienda__addressee_links__client',
        'encomienda__addressee_links__order_addressee',
    ).select_related('user', 'company', 'truck', 'encomienda')
