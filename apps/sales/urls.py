from django.urls import path
from django.contrib.auth.decorators import login_required
from apps.sales.views import *
from apps.sales.views_SUNAT import query_dni
from apps.sales.api_FACT import send_bill_commodity_fact, send_receipt_commodity_fact

urlpatterns = [
    path('', login_required(Home.as_view()), name='home'),
    path('client_list/', login_required(ClientList.as_view()), name='client_list'),

    path('new_client/', new_client, name='new_client'),
    path('get_client/', get_client, name='get_client'),

    path('query_dni/', query_dni, name='query_dni'),

    path('send_bill_commodity_fact/<int:order_id>/', login_required(send_bill_commodity_fact), name='send_bill_commodity_fact'),
    path('send_receipt_commodity_fact/<int:order_id>/', login_required(send_receipt_commodity_fact), name='send_receipt_commodity_fact'),
]
