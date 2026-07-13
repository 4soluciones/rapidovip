from django.shortcuts import render

from django.contrib.auth.models import User

from apps.users.user_helpers import get_subsidiary_by_user

from apps.users.models import Subsidiary, UserSubsidiary

from django.template import loader

from django.http import JsonResponse

from http import HTTPStatus

from .models import *

from .cash_utils import (

    get_open_cash_for_subsidiary,

    get_other_open_cash_same_subsidiary,

    parse_date,

    get_cash_movements_for_day,

)

import decimal

from django.views.generic import TemplateView

from datetime import datetime

from django.db import DatabaseError

import json

from django.core import serializers
from django.db.models import Sum

from ..comercial.models import Programming


def _render_cash_grid(request, id_cash, start_date, user_type, user_obj=None):

    start_date = parse_date(start_date)

    cash_flow_set = get_cash_movements_for_day(

        id_cash,

        start_date,

        user_obj=user_obj,

        all_users=(str(user_type) == '1'),

    )

    opening_flow = CashFlow.objects.filter(

        transaction_date=start_date, cash__id=id_cash, type='A'

    ).first()

    cash_obj = Cash.objects.get(id=id_cash)

    tpl = loader.get_template('accounting/cash_grid_list.html')

    return tpl.render({

        'cash_flow_set': cash_flow_set,

        'has_rows': cash_flow_set.exists(),

        'opening_amount': opening_flow.total if opening_flow else decimal.Decimal('0'),

        'cash_name': cash_obj.name,

        'report_date_display': start_date.strftime('%d/%m/%Y'),

        'movement_count': cash_flow_set.count(),

    }, request)


def _render_expense_grid(request, id_cash, start_date, user_type, user_obj=None):

    start_date = parse_date(start_date)

    if str(user_type) == '2' and user_obj:

        cash_flow_set = CashFlow.objects.filter(

            transaction_date=start_date, cash__id=id_cash, user=user_obj, type='S'

        ).select_related('cash', 'order', 'user', 'programming', 'company')

    else:

        cash_flow_set = CashFlow.objects.filter(

            transaction_date=start_date, cash__id=id_cash, type='S'

        ).select_related('cash', 'order', 'user', 'programming', 'company')

    sum_total = cash_flow_set.aggregate(totals=Sum('total')).get('totals') or 0

    cash_obj = Cash.objects.get(id=id_cash)

    report_date_display = start_date.strftime('%d/%m/%Y')

    tpl = loader.get_template('accounting/expense_module_grid.html')

    return tpl.render({

        'cash_flow_set': cash_flow_set,

        'sum_total': sum_total,

        'has_rows': cash_flow_set.exists(),

        'report_date': start_date,

        'report_date_display': report_date_display,

        'cash_name': cash_obj.name,

    }, request)


class Home(TemplateView):

    template_name = 'home.html'


def get_cash_control_list(request):

    if request.method == 'GET':

        my_date = datetime.now()

        formatdate = my_date.strftime("%Y-%m-%d")

        user_id = request.user.id

        user_obj = User.objects.get(id=user_id)

        subsidiary_obj = get_subsidiary_by_user(user_obj)

        cash_set = Cash.objects.filter(subsidiary=subsidiary_obj, is_bank=False)

        only_cash_set = cash_set

        cash_all_set = Cash.objects.filter(is_bank=False).exclude(subsidiary=subsidiary_obj)

        accounts_banks_set = Cash.objects.filter(is_bank=True)

        return render(request, 'accounting/cash_list.html', {

            'formatdate': formatdate,

            'only_cash_set': only_cash_set,

            'cash_all_set': cash_all_set,

            'accounts_banks_set': accounts_banks_set,

            'choices_operation_types': CashFlow._meta.get_field('operation_type').choices,

            'user_subsidiary_set': UserSubsidiary.objects.filter(

                subsidiary=subsidiary_obj, rol__in=['A', 'O'], user__is_active=True

            ),

        })

    elif request.method == 'POST':

        id_cash = int(request.POST.get('cash'))

        start_date = parse_date(request.POST.get('start-date'))

        user_type = int(request.POST.get('user'))

        user_id = request.user.id

        user_obj = User.objects.get(id=user_id)

        grid = _render_cash_grid(request, id_cash, start_date, user_type, user_obj)

        return JsonResponse({'grid': grid}, status=HTTPStatus.OK)


def _parse_decimal_amount(value, default='0.00'):

    if value is None or str(value).strip() in ('', 'None'):

        return decimal.Decimal(default)

    try:

        return decimal.Decimal(str(value).strip().replace(',', ''))

    except decimal.InvalidOperation:

        return decimal.Decimal(default)


def _opening_amount_for_cash(cash_obj, amount_raw):

    """Saldo de apertura: 0.00 si es la primera apertura de la caja."""

    is_first_opening = not CashFlow.objects.filter(cash=cash_obj, type='A').exists()

    if is_first_opening:

        return decimal.Decimal('0.00')

    if amount_raw is not None and str(amount_raw).strip() not in ('', 'None'):

        try:

            return decimal.Decimal(str(amount_raw).strip().replace(',', ''))

        except decimal.InvalidOperation:

            pass

    last_close = cash_obj.cashflow_set.filter(type='C').order_by('transaction_date').last()

    if last_close:

        return last_close.total

    return _parse_decimal_amount(cash_obj.initial, '0.00')


def open_cash(request):

    if request.method == 'POST':

        _date = request.POST.get('cash-date')

        _amount = request.POST.get('cash-amount')

        _cash_id = request.POST.get('select-cash')

        user_obj = request.user

        cash_obj = Cash.objects.get(id=int(_cash_id))

        opening_total = _opening_amount_for_cash(cash_obj, _amount)

        opening_date = parse_date(_date)

        other_open = get_other_open_cash_same_subsidiary(cash_obj, opening_date, exclude_self=True)

        if other_open:

            data = {

                'error': f'Ya hay una caja abierta en esta sede ({other_open.name}). Solo puede haber una caja abierta por sede.',

            }

            response = JsonResponse(data)

            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR

            return response

        cash_flow_today_set = CashFlow.objects.filter(cash=cash_obj, transaction_date=opening_date, type='A')

        if cash_flow_today_set:

            data = {'error': "Ya existe una Apertura de Caja"}

            response = JsonResponse(data)

            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR

            return response

        last_cash_flow_opening_set = CashFlow.objects.filter(cash=cash_obj, type='A')

        if last_cash_flow_opening_set:

            cash_flow_opening_obj = last_cash_flow_opening_set.last()

            check_closed = CashFlow.objects.filter(

                type='C',

                cash=cash_obj,

                transaction_date=cash_flow_opening_obj.transaction_date,

            )

            if not check_closed:

                data = {'error': "Debes cerrar la caja " + str(cash_flow_opening_obj.transaction_date)}

                response = JsonResponse(data)

                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR

                return response

        cash_flow_obj = CashFlow(

            transaction_date=opening_date,

            cash=cash_obj,

            description='APERTURA',

            total=opening_total,

            type='A',

            user=user_obj,

        )

        cash_flow_obj.save()

        return JsonResponse({

            'message': 'Apertura de Caja exitosa.',

            'cash_id': cash_obj.id,

            'transaction_date': opening_date.strftime('%Y-%m-%d'),

        }, status=HTTPStatus.OK)

    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def close_cash(request):

    if request.method == 'GET':

        _pk = request.GET.get('pk')

        _date = request.GET.get('date')

        _status = request.GET.get('status')

        cash_flow_day_obj = CashFlow.objects.get(id=int(_pk))

        if _status == 'A':

            cash_flow_closed_obj = CashFlow.objects.get(

                cash=cash_flow_day_obj.cash,

                transaction_date=cash_flow_day_obj.transaction_date,

                type='C')

            last_cash_flow_closed_set = CashFlow.objects.filter(

                cash=cash_flow_day_obj.cash,

                type='C')

            if last_cash_flow_closed_set:

                last_cash_flow_closed_obj = last_cash_flow_closed_set.last()

                if last_cash_flow_closed_obj == cash_flow_closed_obj:

                    cash_flow_closed_obj.delete()

                else:

                    data = {'error': "Ya no puede aperturar esta Caja"}

                    response = JsonResponse(data)

                    response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR

                    return response

        else:

            cash_flow_obj = CashFlow(

                transaction_date=_date,

                cash=cash_flow_day_obj.cash,

                description='CIERRE',

                total=decimal.Decimal(cash_flow_day_obj.return_balance()),

                type='C')

            cash_flow_obj.save()

        return JsonResponse({

            'message': 'Cierre de Caja exitosa.',

        }, status=HTTPStatus.OK)

    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def get_cash_form(request):

    if request.method != 'GET':

        return JsonResponse({'error': True}, status=HTTPStatus.METHOD_NOT_ALLOWED)

    user_obj = User.objects.get(pk=request.user.id)

    subsidiary_obj = get_subsidiary_by_user(user_obj)

    tpl = loader.get_template('accounting/cash_modal_form.html')

    return JsonResponse({

        'success': True,

        'grid': tpl.render({

            'subsidiary_obj': subsidiary_obj,

        }, request),

    }, status=HTTPStatus.OK)


def new_entity(request):

    if request.method == 'POST':

        _entity_name = request.POST.get('entity-name', '')

        _entity_subsidiary = request.POST.get('entity-subsidiary', '')

        _entity_initial = request.POST.get('entity-initial', '')

        subsidiary_obj = Subsidiary.objects.get(id=int(_entity_subsidiary))

        try:

            cash_obj = Cash(

                name=str(_entity_name.upper()),

                subsidiary=subsidiary_obj,

                initial=decimal.Decimal(_entity_initial),

                cash_type='O',

                is_bank=False,

            )

            cash_obj.save()

        except DatabaseError as e:

            data = {'error': str(e)}

            response = JsonResponse(data)

            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR

            return response

        return JsonResponse({

            'message': 'Caja registrada correctamente.',

            'cash_id': cash_obj.id,

            'cash_name': cash_obj.name,

        }, status=HTTPStatus.OK)

    return JsonResponse({'error': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def get_entity(request):

    if request.method == 'GET':

        pk = request.GET.get('pk', '')

        cash_obj = Cash.objects.filter(id=pk)

        serialized_obj = serializers.serialize('json', cash_obj)

        return JsonResponse({'obj': serialized_obj}, status=HTTPStatus.OK)

    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def update_entity(request):

    if request.method == 'POST':

        _entity_id = request.POST.get('entity', '')

        _entity_name = request.POST.get('entity-name', '')

        cash_obj = Cash.objects.get(id=int(_entity_id))

        cash_obj.name = _entity_name.upper()

        cash_obj.save()

        return JsonResponse({

            'message': 'Cambios guardados con exito.',

        }, status=HTTPStatus.OK)

    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def get_initial_balance(request):

    if request.method == 'GET':

        id_cash = request.GET.get('cash', '')

        cash_obj = Cash.objects.get(id=int(id_cash))

        if not cash_obj.cashflow_set.filter(type='A').exists():

            initial_balance = decimal.Decimal('0.00')

        else:

            initial_set = cash_obj.cashflow_set.filter(type='C').order_by('transaction_date').last()

            if initial_set:

                initial_balance = initial_set.total

            else:

                initial_balance = cash_obj.initial or decimal.Decimal('0.00')

        return JsonResponse({

            'initial_balance': initial_balance,

            'message': 'Saldo recuperado.',

        }, status=HTTPStatus.OK)


def get_cash_date(request):

    if request.method == 'GET':

        my_date = datetime.now()

        formatdate = my_date.strftime("%Y-%m-%d")

        user_id = request.user.id

        user_obj = User.objects.get(id=user_id)

        subsidiary_obj = get_subsidiary_by_user(user_obj)

        open_cash = get_open_cash_for_subsidiary(subsidiary_obj, formatdate)

        if open_cash:

            return JsonResponse({

                'cash_date': formatdate,

                'cash_id': open_cash.id,

                'cash_name': open_cash.name,

                'message': 'Caja abierta',

            }, status=HTTPStatus.OK)

        pk = request.GET.get('cash_id', '')

        cash_obj = None

        if pk:

            cash_obj = Cash.objects.filter(id=int(pk), subsidiary=subsidiary_obj, is_bank=False).first()

        if cash_obj:

            last_opening = CashFlow.objects.filter(cash=cash_obj, type='A').order_by('transaction_date').last()

            if last_opening:

                last_date = last_opening.transaction_date.strftime('%Y-%m-%d')

                if last_date != formatdate and not CashFlow.objects.filter(

                    cash=cash_obj, transaction_date=last_opening.transaction_date, type='C'

                ).exists():

                    response = JsonResponse({

                        'error': 'Debe cerrar la caja del día ' + last_date,

                        '_date': last_date,

                    })

                    response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR

                    return response

        response = JsonResponse({

            'error': 'No hay caja abierta para hoy. Apertúrela en Finanzas → Caja y gastos.',

        })

        response.status_code = HTTPStatus.BAD_REQUEST

        return response

    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def get_last_cash_open(cash_id):

    cash_obj = Cash.objects.get(id=cash_id)

    last_cash = CashFlow.objects.filter(cash=cash_obj, type='A').last()

    return last_cash


def save_cash_flow(

        cash_obj=None,

        order_obj=None,

        user_obj=None,

        cash_flow_transact_date='',

        cash_flow_description='',

        cash_flow_type='',

        cash_flow_operation='',

        cash_flow_programming=None,

        cash_flow_total=0,

        document_type_attached=''

):

    cash_flow_obj = CashFlow(

        transaction_date=cash_flow_transact_date,

        document_type_attached=document_type_attached,

        description=cash_flow_description,

        order=order_obj,

        type=cash_flow_type,

        operation_code=cash_flow_operation,

        programming=cash_flow_programming,

        total=cash_flow_total,

        cash=cash_obj,

        user=user_obj

    )

    cash_flow_obj.save()


def expense_module(request):

    if request.method == 'GET':

        return get_cash_control_list(request)

    elif request.method == 'POST':

        id_cash = request.POST.get('cash')

        start_date = str(request.POST.get('date') or request.POST.get('start-date'))

        user = request.POST.get('user', 'T')

        user_type = '2' if user not in ('T', '1') else '1'

        user_obj = None

        if user_type == '2':

            user_obj = User.objects.get(id=user)

        grid = _render_cash_grid(request, id_cash, start_date, user_type, user_obj)

        return JsonResponse({'grid': grid}, status=HTTPStatus.OK)


def modal_expense(request):

    if request.method == 'GET':

        cash_id = request.GET.get('cash_id', '')

        my_date = datetime.now()

        formatdate = my_date.strftime("%Y-%m-%d")

        user_id = request.user.id

        user_obj = User.objects.get(id=user_id)

        subsidiary_obj = get_subsidiary_by_user(user_obj)

        user_subsidiary_set = UserSubsidiary.objects.filter(subsidiary=subsidiary_obj, rol__in=['A', 'O'],

                                                            user__is_active=True)

        cash_obj = Cash.objects.get(id=int(cash_id))

        tpl = loader.get_template('accounting/expense_modal_form.html')

        context = ({

            'cash_obj': cash_obj,

            'formatdate': formatdate,

            'subsidiary_obj': subsidiary_obj,

            'user_subsidiary_set': user_subsidiary_set,

            'cash_set': Cash.objects.filter(

                subsidiary=subsidiary_obj,

                is_bank=False,

            ),

        })

        return JsonResponse({

            'success': True,

            'grid': tpl.render(context, request),

        }, status=HTTPStatus.OK)


def new_expense(request):

    if request.method == 'POST':

        _cash = request.POST.get('cash')

        _user = request.POST.get('user')

        _operation_date = request.POST.get('operation_date')

        _description = request.POST.get('description')

        _total = request.POST.get('total', '')

        cash_obj = Cash.objects.get(id=int(_cash))

        user_obj = User.objects.get(id=_user)

        cash_flow_obj = CashFlow(

            transaction_date=_operation_date,

            cash=cash_obj,

            description=_description.upper(),

            total=decimal.Decimal(_total or 0),

            subtotal=decimal.Decimal('0'),

            igv=decimal.Decimal('0'),

            operation_type='0',

            document_type_attached='O',

            user=user_obj,

            type='S',

        )

        cash_flow_obj.save()

        cash_grid = _render_cash_grid(request, _cash, _operation_date, '1', None)

        return JsonResponse({

            'message': 'Operación registrada con exito.',

            'grid': cash_grid,

        }, status=HTTPStatus.OK)

    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)
