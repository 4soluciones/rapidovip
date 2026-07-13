from django import template
import decimal
from apps.users.models import Company
from django.template.loader import get_template

register = template.Library()


@register.filter(name='get')
def get(d, k):
    return d.get(k, None)


@register.filter(name='zfill')
def zfill(d, k):
    res = str(d).zfill(int(k))
    return res


@register.filter
def intcomma(value):
    return value + 1


@register.filter(name='calculate_percent')
def calculate_percent(cs, ct):
    res = 0
    if cs > 0:
        res = round(cs * 100 / ct)
    return res


@register.filter(name='decimal_dot')
def decimal_dot(value, decimal_places=2):
    """Formatea número con punto como separador decimal (independiente del locale)."""
    if value is None or value == '':
        return ''
    try:
        d = decimal.Decimal(str(value))
    except (decimal.InvalidOperation, TypeError, ValueError):
        return value
    places = int(decimal_places) if decimal_places is not None else 2
    q = decimal.Decimal(10) ** -places
    return format(d.quantize(q), 'f')


@register.filter(name='replace_round_separator')
def replace_round_separator(value):
    if value is not None and value != '':
        value = float(value)
        decimal_part = value - int(value)
        decimal_str = f"{decimal_part:.3f}"[2:]
        if int(decimal_str[2]) > 0:
            rounded_value = round(value, 3)
        else:
            rounded_value = round(decimal.Decimal(value), 2)
        formatted_value = '{:,.{}f}'.format(rounded_value, 3 if int(decimal_str[2]) > 0 else 2).replace(',', 'X').replace('.', ',').replace('X', '.')
        return formatted_value
    return value