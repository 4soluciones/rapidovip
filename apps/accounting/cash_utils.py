from datetime import datetime

from django.db.models import Case, When, IntegerField, Sum, Q

from apps.accounting.models import Cash, CashFlow


def parse_date(value):
    if isinstance(value, datetime):
        return value.date()
    if hasattr(value, 'year'):
        return value
    return datetime.strptime(str(value), '%Y-%m-%d').date()


def cash_is_open_on_date(cash_obj, target_date):
    target_date = parse_date(target_date)
    has_opening = CashFlow.objects.filter(
        cash=cash_obj, transaction_date=target_date, type='A'
    ).exists()
    has_closing = CashFlow.objects.filter(
        cash=cash_obj, transaction_date=target_date, type='C'
    ).exists()
    return has_opening and not has_closing


def get_open_cash_for_subsidiary(subsidiary_obj, target_date=None):
    target_date = parse_date(target_date or datetime.now().strftime('%Y-%m-%d'))
    for cash in Cash.objects.filter(subsidiary=subsidiary_obj, is_bank=False).order_by('id'):
        if cash_is_open_on_date(cash, target_date):
            return cash
    return None


def get_other_open_cash_same_subsidiary(cash_obj, target_date, exclude_self=True):
    target_date = parse_date(target_date)
    for cash in Cash.objects.filter(subsidiary=cash_obj.subsidiary, is_bank=False):
        if exclude_self and cash.id == cash_obj.id:
            continue
        if cash_is_open_on_date(cash, target_date):
            return cash
    return None


def order_cash_flows(queryset):
    return queryset.annotate(
        movement_sort=Case(
            When(type='A', then=0),
            When(type='E', then=1),
            When(type='S', then=2),
            When(type='C', then=3),
            default=4,
            output_field=IntegerField(),
        )
    ).order_by('movement_sort', 'id')


def get_cash_movements_for_day(cash_id, target_date, user_obj=None, all_users=True):
    """Movimientos del día; apertura y cierre siempre visibles."""
    target_date = parse_date(target_date)
    qs = CashFlow.objects.filter(
        transaction_date=target_date,
        cash__id=cash_id,
    ).select_related(
        'cash', 'order', 'user', 'programming', 'company'
    )
    if not all_users and user_obj:
        qs = qs.filter(Q(user=user_obj) | Q(type__in=['A', 'C']))
    return order_cash_flows(qs)
