from django.urls import path
from django.contrib.auth.decorators import login_required
from apps.accounting.views import *

urlpatterns = [
    path('', login_required(Home.as_view()), name='home'),

    # cash
    path('get_cash_control_list/', login_required(get_cash_control_list), name='get_cash_control_list'),
    path('get_cash_form/', login_required(get_cash_form), name='get_cash_form'),
    path('open_cash/', login_required(open_cash), name='open_cash'),
    path('close_cash/', login_required(close_cash), name='close_cash'),
    path('get_initial_balance/', login_required(get_initial_balance), name='get_initial_balance'),
    path('get_cash_date/', login_required(get_cash_date), name='get_cash_date'),

    # entities (cash boxes)
    path('new_entity/', login_required(new_entity), name='new_entity'),
    path('get_entity/', login_required(get_entity), name='get_entity'),
    path('update_entity/', login_required(update_entity), name='update_entity'),

    # EXPENSE MODULE
    path('expense_module/', login_required(expense_module), name='expense_module'),
    path('modal_expense/', login_required(modal_expense), name='modal_expense'),
    path('new_expense/', login_required(new_expense), name='new_expense'),

]
