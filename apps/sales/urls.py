from django.urls import path
from django.contrib.auth.decorators import login_required
from apps.sales.views import *
from apps.sales.views_SUNAT import query_dni
from apps.sales.api_FACT import send_bill_commodity_fact, send_receipt_commodity_fact

urlpatterns = [
    path('', login_required(Home.as_view()), name='home'),
    path('client_list/', login_required(ClientList.as_view()), name='client_list'),
    path('units/', login_required(UnitListView.as_view()), name='unit_list'),
    path('units/form/', login_required(get_unit_form), name='get_unit_form'),
    path('units/save/', login_required(save_unit), name='save_unit'),
    path('units/<int:unit_id>/form/', login_required(get_unit_edit_form), name='get_unit_edit_form'),
    path('units/<int:unit_id>/save/', login_required(save_unit_edit), name='save_unit_edit'),

    path('delivery-destinations/', login_required(DeliveryDestinationListView.as_view()), name='delivery_destination_list'),
    path('delivery-destinations/form/', login_required(get_delivery_destination_form), name='get_delivery_destination_form'),
    path('delivery-destinations/save/', login_required(save_delivery_destination), name='save_delivery_destination'),
    path(
        'delivery-destinations/search/',
        login_required(search_delivery_destinations),
        name='search_delivery_destinations',
    ),
    path(
        'delivery-destinations/<int:destination_id>/form/',
        login_required(get_delivery_destination_edit_form),
        name='get_delivery_destination_edit_form',
    ),
    path(
        'delivery-destinations/<int:destination_id>/save/',
        login_required(save_delivery_destination_edit),
        name='save_delivery_destination_edit',
    ),
    path('districts/search/', login_required(search_districts), name='search_districts'),

    path('new_client/', new_client, name='new_client'),
    path('get_client/', get_client, name='get_client'),

    path('query_dni/', query_dni, name='query_dni'),

    path('send_bill_commodity_fact/<int:order_id>/', login_required(send_bill_commodity_fact), name='send_bill_commodity_fact'),
    path('send_receipt_commodity_fact/<int:order_id>/', login_required(send_receipt_commodity_fact), name='send_receipt_commodity_fact'),
]
