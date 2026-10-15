import decimal

TWOPLACES = decimal.Decimal('0.01')
SIXPLACES = decimal.Decimal('0.000001')
IGV_FACTOR = decimal.Decimal('1.18')
MONEY_ROUNDING = decimal.ROUND_HALF_UP


def as_decimal(value):
    if value is None or value == '':
        return decimal.Decimal('0')
    if isinstance(value, decimal.Decimal):
        return value
    return decimal.Decimal(str(value))


def money(value):
    """Redondeo comercial a 2 decimales (0.005 -> 0.01)."""
    return as_decimal(value).quantize(TWOPLACES, rounding=MONEY_ROUNDING)


def money_str(value):
    return format(money(value), 'f')


def unit_price_from_amount(amount, quantity):
    """Precio unitario a 6 decimales a partir del importe cobrado."""
    qty = as_decimal(quantity)
    if qty == 0:
        return decimal.Decimal('0')
    return (as_decimal(amount) / qty).quantize(SIXPLACES, rounding=MONEY_ROUNDING)


def line_amount(detail):
    """Importe cobrado de la línea. `amount` es la fuente de verdad."""
    amount = as_decimal(getattr(detail, 'amount', 0) or 0)
    if amount != 0:
        return amount
    qty = as_decimal(getattr(detail, 'quantity', 0) or 0)
    price = as_decimal(getattr(detail, 'price_unit', 0) or 0)
    return qty * price


def igv_breakdown(total_with_igv):
    """Gravada, IGV y total desde un importe con IGV incluido."""
    total = as_decimal(total_with_igv)
    gravada = total / IGV_FACTOR
    igv = total - gravada
    return gravada, igv, total
