from django.urls import path
from django.contrib.auth.decorators import login_required
from apps.comercial.views import *
from apps.comercial.views_PDF import (
    print_ticket_order_commodity,
    print_ticket_order_passenger,
    print_bill_order_commodity,
    print_mock_up_passengers,
    print_manifest_comidity,
    print_ticket_old,
    print_manifest_passengers_old,
    print_report_commodity,
    print_guide_format_tk,
    print_guide_format_a4,
    print_cargo_manifest,
)

urlpatterns = [
    path('', login_required(Index.as_view()), name='index'),
    # truck
    path('truck_list/', login_required(TruckList.as_view()), name='truck_list'),
    path('truck_create/', login_required(TruckCreate.as_view()), name='truck_create'),
    path('get_truck_form/', login_required(get_truck_form), name='get_truck_form'),
    path('save_truck/', login_required(save_truck), name='save_truck'),
    path('get_truck/', login_required(get_truck), name='get_truck'),
    # programming
    path('programming_list/', login_required(ProgrammingList.as_view()), name='programming_list'),
    path('new_programming/', new_programming, name='new_programming'),
    path('get_programming_form/', login_required(get_programming_form), name='get_programming_form'),
    path('update_programming/', update_programming, name='update_programming'),
    # guide / orders
    path('new_guide/', new_guide, name='new_guide'),
    path('get_guide_document/', login_required(get_guide_document), name='get_guide_document'),
    path('create_order/', create_order, name='create_order'),
    path('get_address_subsidiary_by_id/', get_address_subsidiary_by_id, name='get_address_subsidiary_by_id'),
    # ReportLab PDFs
    path('print_ticket_order_commodity/<int:pk>/', print_ticket_order_commodity, name='print_ticket_order_commodity'),
    path('print_ticket_order_passenger/<int:pk>/', print_ticket_order_passenger, name='print_ticket_order_passenger'),
    path('print_bill_order_commodity/<int:pk>/', print_bill_order_commodity, name='print_bill_order_commodity'),
    path('print_mock_up_passengers/<int:pk>/', print_mock_up_passengers, name='print_mock_up_passengers'),
    path('print_manifest_comidity/<int:pk>/', print_manifest_comidity, name='print_manifest_comidity'),
    path('print_ticket_old/<int:pk>/', print_ticket_old, name='print_ticket_old'),
    path('print_manifest_passengers_old/<int:pk>/', print_manifest_passengers_old, name='print_manifest_passengers_old'),
    path('print_report_commodity/<str:start_date>/<str:end_date>/<str:user_selected>/<str:way_to_pay>/<str:destiny>', print_report_commodity, name='print_report_commodity'),
    # lookups
    path('get_name_business/', login_required(get_name_business), name='get_name_business'),
    path('get_phone_number_by_name_addressee/', login_required(get_phone_number_by_name_addressee), name='get_phone_number_by_name_addressee'),
    # programmings query
    path('get_programming_query_list/', login_required(get_programming_query_list), name='get_programming_query_list'),
    # commodity reports
    path('get_modal_change/', login_required(get_modal_change), name='get_modal_change'),
    path('change_destiny/', login_required(change_destiny), name='change_destiny'),
    path('report_comodity_grid/', login_required(report_comodity_grid), name='report_comodity_grid'),
    path('cancel_commodity/', login_required(cancel_commodity), name='cancel_commodity'),
    path('report_manifest_grid/', login_required(report_manifest_grid), name='report_manifest_grid'),
    path('get_modal_way_pay/', login_required(get_modal_way_pay), name='get_modal_way_pay'),
    path('change_way_to_pay/', login_required(change_way_to_pay), name='change_way_to_pay'),
    path('save_truck_exit/', login_required(save_truck_exit), name='save_truck_exit'),
    path('check_bill/', login_required(check_bill), name='check_bill'),
    path('get_all_programmings/', login_required(get_all_programmings), name='get_all_programmings'),
    path('get_trucks_programming_grid/', login_required(get_trucks_programming_grid), name='get_trucks_programming_grid'),
    # Remission guides
    path('guide_assignment/', login_required(GuideAssignmentView.as_view()), name='guide_assignment'),
    path('assign_order_guide/', login_required(assign_order_guide), name='assign_order_guide'),
    path('create_cargo_manifest/', login_required(create_cargo_manifest), name='create_cargo_manifest'),
    path('create_carrier_guide/', login_required(create_carrier_guide), name='create_carrier_guide'),
    path('unassign_order_guide/', login_required(unassign_order_guide), name='unassign_order_guide'),
    path('print_guide_format_tk/<int:pk>/', login_required(print_guide_format_tk), name='print_guide_format_tk'),
    path('print_guide_format_a4/<int:pk>/', login_required(print_guide_format_a4), name='print_guide_format_a4'),
    path('print_cargo_manifest/<int:pk>/', login_required(print_cargo_manifest), name='print_cargo_manifest'),
]
