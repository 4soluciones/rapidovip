import decimal
import json
import random
import string
from datetime import date, datetime, timedelta
from http import HTTPStatus

from django.contrib.auth.models import User
from django.core import serializers
from django.db.models import Prefetch
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.template import loader
from django.urls import reverse_lazy
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View, TemplateView, UpdateView, CreateView

from apps.accounting.cash_utils import get_open_cash_for_subsidiary
from apps.accounting.views import Cash, CashFlow, save_cash_flow
from apps.comercial.guide_helpers import get_serial_service, get_correlative_service
from apps.comercial.service_helpers import (
    get_service_destiny_label,
    prefetch_orders_for_report,
    save_service_for_order,
    sync_commodity_addressees,
)
from apps.comercial.serial_helpers import (
    get_serial_manifest,
    get_serial_manifest_and_commodity,
    get_serial_subsidiary_company,
)
from apps.comercial.view_correlative import (
    get_correlative_commodity,
    get_correlative_manifest,
    update_correlative_commodity,
    update_correlative_manifest_passenger,
)
from apps.sales.api_FACT import (
    annul_invoice,
    get_sale_by_id,
    send_bill_commodity_fact,
    send_receipt_commodity_fact,
)
from apps.sales.models import (
    Order,
    OrderAction,
    OrderAddressee,
    OrderBill,
    OrderCommodity,
    OrderDetail,
    OrderRoute,
    SERVICE_TYPE_CHOICES,
    Unit,
    WAY_TO_PAY_CHOICES,
)
from apps.sales.views import Client, ClientAddress, ClientType, Manifest
from apps.sales.views_SUNAT import (
    query_api_facturacioncloud,
    query_apis_net_dni_ruc,
)
from apps.users.models import DocumentType, Employee, Nationality, Subsidiary, UserSubsidiary
from apps.users.subsidiary_serial_helpers import get_serial
from apps.users.roles import user_is_administrator
from apps.users.views import CompanyUser, get_subsidiary_by_user
from .forms import FormDriver, FormProgramming, FormTruck
from .guide_assignment import (
    assign_order_to_programming,
    create_cargo_manifest_for_programming,
    create_carrier_guide_for_programming,
    unassign_sender_guide,
)
from .models import (
    CargoManifest,
    CarrierRemissionGuide,
    Driver,
    Owner,
    Programming,
    SenderRemissionGuide,
    Truck,
    TruckBrand,
    TruckModel,
)

class Index(TemplateView):
    # template_name = 'dashboard.html'
    # template_name = 'vetstore/home.html'
    template_name = 'dashboard.html'


# ---------------------------------------Truck-----------------------------------
class TruckList(View):
    model = Truck
    form_class = FormTruck
    template_name = 'comercial/truck_list.html'

    def get_queryset(self):
        return self.model.objects.all()

    def get_context_data(self, **kwargs):
        user_obj = self.request.user
        company = user_obj.companyuser.company_rotation
        context = {
            'trucks': self.get_queryset(),
            'form': self.form_class,
            'employee_set': Employee.objects.all(),
            'subsidiary_set': Subsidiary.objects.all(),
            'company': company,
        }
        return context

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self.get_context_data())


class TruckCreate(CreateView):
    model = Truck
    form_class = FormTruck

    def get(self, request, *args, **kwargs):
        return redirect('comercial:truck_list')


def get_company_owner(company):
    owner, _ = Owner.objects.get_or_create(
        ruc=company.ruc,
        defaults={
            'name': company.business_name,
            'address': company.address or '',
        },
    )
    if owner.name != company.business_name:
        owner.name = company.business_name
        owner.save(update_fields=['name'])
    return owner


def get_truck_form(request):
    if request.method != 'GET':
        return JsonResponse({'error': True, 'message': 'Método no permitido.'}, status=405)

    pk = request.GET.get('pk', '')
    user_obj = User.objects.get(pk=request.user.id)
    company = user_obj.companyuser.company_rotation
    default_owner = get_company_owner(company)

    truck_obj = None
    if pk:
        truck_obj = Truck.objects.get(pk=int(pk))
        form = FormTruck(instance=truck_obj)
    else:
        form = FormTruck(initial={'owner': default_owner.pk, 'is_active': True})

    tpl = loader.get_template('comercial/truck_modal_form.html')
    context = {
        'form': form,
        'brands': TruckBrand.objects.all(),
        'models': TruckModel.objects.all(),
        'company': company,
        'default_owner': default_owner,
        'truck_obj': truck_obj,
        'truck_id': pk,
    }
    return JsonResponse({'success': True, 'grid': tpl.render(context, request)})


@csrf_exempt
def save_truck(request):
    if request.method != 'POST':
        return JsonResponse({'error': True, 'message': 'Método no permitido.'}, status=405)

    user_obj = User.objects.get(pk=request.user.id)
    default_owner = get_company_owner(user_obj.companyuser.company_rotation)
    pk = request.POST.get('truck_id', '')

    post_data = request.POST.copy()
    post_data['owner'] = str(default_owner.pk)

    truck_obj = None
    if pk:
        truck_obj = Truck.objects.get(pk=int(pk))

    form = FormTruck(post_data, instance=truck_obj)
    if not form.is_valid():
        errors = '; '.join(
            f'{field}: {", ".join(msg_list)}' for field, msg_list in form.errors.items()
        )
        return JsonResponse({'error': True, 'message': errors or 'Datos inválidos.'}, status=400)

    truck = form.save()
    truck_model_id = request.POST.get('truck_model')
    if truck_model_id:
        truck.truck_model_id = int(truck_model_id)
        truck.save(update_fields=['truck_model'])

    return JsonResponse({
        'success': True,
        'message': 'Unidad guardada correctamente.',
    })


class TruckUpdate(UpdateView):
    model = Truck
    form_class = FormTruck

    def get(self, request, *args, **kwargs):
        return redirect('comercial:truck_list')


# ---------------------------------------Driver-----------------------------------


class DriverList(View):
    model = Driver
    form_class = FormDriver
    template_name = 'comercial/driver_list.html'

    def get(self, request, *args, **kwargs):
        drivers = self.model.objects.all()
        return render(request, self.template_name, {
            'drivers': drivers,
            'form': self.form_class,
            'drivers_active_count': drivers.filter(is_active=True).count(),
            'drivers_total_count': drivers.count(),
        })


def get_driver_form(request):
    if request.method != 'GET':
        return JsonResponse({'error': True, 'message': 'Método no permitido.'}, status=405)

    pk = request.GET.get('pk', '')
    driver_obj = None
    if pk:
        driver_obj = Driver.objects.get(pk=int(pk))
        form = FormDriver(instance=driver_obj)
    else:
        form = FormDriver(initial={'is_active': True, 'license_type': 'A3b'})

    tpl = loader.get_template('comercial/driver_modal_form.html')
    context = {
        'form': form,
        'driver_obj': driver_obj,
        'driver_id': pk,
    }
    return JsonResponse({'success': True, 'grid': tpl.render(context, request)})


@csrf_exempt
def save_driver(request):
    if request.method != 'POST':
        return JsonResponse({'error': True, 'message': 'Método no permitido.'}, status=405)

    pk = request.POST.get('driver_id', '')
    driver_obj = None
    if pk:
        driver_obj = Driver.objects.get(pk=int(pk))

    form = FormDriver(request.POST, instance=driver_obj)
    if not form.is_valid():
        errors = '; '.join(
            f'{field}: {", ".join(msg_list)}' for field, msg_list in form.errors.items()
        )
        return JsonResponse({'error': True, 'message': errors or 'Datos inválidos.'}, status=400)

    form.save()
    return JsonResponse({
        'success': True,
        'message': 'Conductor guardado correctamente.',
    })


# ----------------------------------------Programming-------------------------------


class ProgrammingCreate(CreateView):
    model = Programming
    form_class = FormProgramming
    template_name = 'comercial/programming_list.html'
    success_url = reverse_lazy('comercial:programming_list')


class ProgrammingList(View):
    model = Programming
    form_class = FormProgramming
    template_name = 'comercial/programming_module.html'

    def get_context_data(self, **kwargs):
        user_id = self.request.user.id
        user_obj = User.objects.get(pk=int(user_id))
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        company_rotation_obj = user_obj.companyuser.company_rotation
        company_obj = company_rotation_obj
        serial_manifest = get_serial(subsidiary_obj, company_rotation_obj, 'P', 'T')
        correlative_manifest = get_correlative_manifest(
            subsidiary_obj=subsidiary_obj, company_rotation_obj=company_rotation_obj
        ) or ''

        my_date = datetime.now()
        formatdate = my_date.strftime("%Y-%m-%d")
        context = {
            'drivers': Driver.objects.filter(is_active=True),
            'trucks': Truck.objects.filter(
                is_active=True,
                owner__ruc=company_obj.ruc
            ),
            'choices_status': Programming.STATUS_CHOICES,
            'service_types': Programming.SERVICE_TYPE_CHOICES,
            'current_date': formatdate,
            'formatdate': formatdate,
            'subsidiary_origin': subsidiary_obj,
            'subsidiary_set': Subsidiary.objects.filter(is_enabled=True),
            'programmings': get_programmings(
                need_rendering=False,
                subsidiary_obj=subsidiary_obj,
                company_obj=company_obj,
                show_edit=False, show_plan=False, show_lp=False
            ),
            'show_edit': True,
            'show_plan': False,
            'show_lp': False,
            'serial': serial_manifest,
            'correlative': correlative_manifest,
        }
        return context

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self.get_context_data())


@csrf_exempt
def new_programming(request):
    if request.method == 'POST':

        truck = request.POST.get('truck', '')
        departure_date = request.POST.get('departure_date')
        arrival_date = request.POST.get('arrival_date') or None
        subsidiary_origin = request.POST.get('origin', '')
        status = request.POST.get('status', 'P')
        service_type = request.POST.get('service_type', 'E')

        user_id = request.user.id
        user_obj = User.objects.get(pk=int(user_id))
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        company_obj = user_obj.companyuser.company_rotation

        pilot = request.POST.get('pilot', '')
        copilot = request.POST.get('copilot', '')

        serial = request.POST.get('serial', '')
        correlative = request.POST.get('correlative', '')
        price = request.POST.get('price', '0.00')
        subsidiary_origin_obj = Subsidiary.objects.get(id=subsidiary_origin)

        if not pilot or not truck:
            return JsonResponse({'error': True, 'message': 'Seleccione vehículo y conductor.'})

        try:
            pilot_obj = Driver.objects.get(pk=int(pilot), is_active=True)
        except (Driver.DoesNotExist, ValueError, TypeError):
            return JsonResponse({'error': True, 'message': 'Conductor no válido.'})

        truck_obj = Truck.objects.get(id=truck)
        copilot_name = ''
        if copilot:
            try:
                copilot_name = Driver.objects.get(pk=int(copilot), is_active=True).full_name
            except (Driver.DoesNotExist, ValueError, TypeError):
                return JsonResponse({'error': True, 'message': 'Copiloto no válido.'})

        data_programming = {
            'departure_date': departure_date,
            'arrival_date': arrival_date,
            'service_type': service_type,
            'truck': truck_obj,
            'subsidiary': subsidiary_origin_obj,
            'status': status,
            'serial': serial,
            'correlative': correlative,
            'company': company_obj,
            'price': price,
            'support_pilot': pilot_obj.full_name,
            'support_copilot': copilot_name or None,
        }
        programming_obj = Programming.objects.create(**data_programming)

        update_correlative_manifest_passenger(programming_obj=programming_obj)

        return JsonResponse({
            'success': True,
            'message': 'Programación registrada correctamente.',
            'grid': get_programmings(
                need_rendering=True,
                subsidiary_obj=subsidiary_obj,
                company_obj=company_obj,
                show_edit=True, show_plan=False),
            })
    return JsonResponse({'error': True, 'message': 'Error de peticion.'})


def _match_driver_by_stored_name(full_name):
    """Resuelve un Driver a partir del nombre guardado en Programming."""
    if not full_name:
        return None
    name = str(full_name).strip()
    if not name:
        return None
    drivers = Driver.objects.filter(is_active=True)
    name_upper = name.upper()
    for driver in drivers:
        if driver.full_name.upper() == name_upper:
            return driver
    token = name.split()[0]
    if token:
        match = drivers.filter(names__icontains=token).first()
        if match:
            return match
        match = drivers.filter(paternal_last_name__icontains=token).first()
        if match:
            return match
    return None


def _programming_form_context(user_obj, programming_obj=None):
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    company_ruc = user_obj.companyuser.company_rotation.ruc
    company_rotation_obj = user_obj.companyuser.company_rotation
    serial_manifest = get_serial(subsidiary_obj, company_rotation_obj, 'P', 'T')
    correlative_manifest = get_correlative_manifest(
        subsidiary_obj=subsidiary_obj, company_rotation_obj=company_rotation_obj
    ) or ''
    if programming_obj and programming_obj.serial:
        serial_manifest = programming_obj.serial
    if programming_obj and programming_obj.correlative:
        correlative_manifest = programming_obj.correlative
    my_date = datetime.now()
    drivers = Driver.objects.filter(is_active=True).order_by('paternal_last_name', 'names')
    selected_pilot_id = None
    selected_copilot_id = None
    selected_pilot_license = ''
    selected_copilot_license = ''
    if programming_obj and programming_obj.support_pilot:
        pilot_match = _match_driver_by_stored_name(programming_obj.support_pilot)
        if pilot_match:
            selected_pilot_id = pilot_match.id
            selected_pilot_license = pilot_match.license_number
    if programming_obj and programming_obj.support_copilot:
        copilot_match = _match_driver_by_stored_name(programming_obj.support_copilot)
        if copilot_match:
            selected_copilot_id = copilot_match.id
            selected_copilot_license = copilot_match.license_number
    return {
        'programming_obj': programming_obj,
        'selected_pilot_id': selected_pilot_id,
        'selected_copilot_id': selected_copilot_id,
        'selected_pilot_license': selected_pilot_license,
        'selected_copilot_license': selected_copilot_license,
        'drivers': drivers,
        'subsidiary_origin': subsidiary_obj,
        'trucks': Truck.objects.filter(is_active=True, owner__ruc=company_ruc),
        'choices_status': Programming.STATUS_CHOICES,
        'service_types': Programming.SERVICE_TYPE_CHOICES,
        'current_date': my_date.strftime('%Y-%m-%d'),
        'serial': serial_manifest,
        'correlative': correlative_manifest,
    }


def get_programming_form(request):
    if request.method != 'GET':
        return JsonResponse({'error': True}, status=405)
    pk = request.GET.get('programming', '')
    user_obj = User.objects.get(pk=request.user.id)
    programming_obj = None
    if pk:
        programming_obj = Programming.objects.get(pk=int(pk))
    tpl = loader.get_template('comercial/programming_modal_form.html')
    ctx = _programming_form_context(user_obj, programming_obj)
    ctx['is_edit'] = bool(pk)
    return JsonResponse({'success': True, 'grid': tpl.render(ctx, request)})


def update_programming(request):
    if request.method == 'POST':
        id_programming = request.POST.get('programming', '')
        programming_obj = Programming.objects.get(id=int(id_programming))

        id_subsidiary_origin = request.POST.get('origin', '')
        id_pilot = request.POST.get('pilot', '')
        id_copilot = request.POST.get('copilot', '')
        id_truck = request.POST.get('truck', '')
        departure_date = request.POST.get('departure_date', '')
        arrival_date = request.POST.get('arrival_date', '') or None
        status = request.POST.get('status', '')
        service_type = request.POST.get('service_type', 'E')
        serial = request.POST.get('serial', '')
        correlative = request.POST.get('correlative', '')
        price = request.POST.get('price', '0.00')

        if id_pilot:
            try:
                pilot_obj = Driver.objects.get(pk=int(id_pilot))
                programming_obj.support_pilot = pilot_obj.full_name
            except (Driver.DoesNotExist, ValueError, TypeError):
                return JsonResponse({'error': True, 'message': 'Conductor no válido.'})

        if id_copilot:
            try:
                programming_obj.support_copilot = Driver.objects.get(pk=int(id_copilot)).full_name
            except (Driver.DoesNotExist, ValueError, TypeError):
                return JsonResponse({'error': True, 'message': 'Copiloto no válido.'})
        else:
            programming_obj.support_copilot = None

        if len(id_truck) > 0:
            truck_obj = Truck.objects.get(id=int(id_truck))
            programming_obj.truck = truck_obj

        if len(id_subsidiary_origin) > 0:
            programming_obj.subsidiary = Subsidiary.objects.get(pk=int(id_subsidiary_origin))

        programming_obj.status = status
        programming_obj.service_type = service_type
        programming_obj.departure_date = departure_date
        programming_obj.arrival_date = arrival_date
        programming_obj.serial = serial
        programming_obj.correlative = correlative
        programming_obj.price = price
        programming_obj.save()

        user_id = request.user.id
        user_obj = User.objects.get(pk=int(user_id))
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        company_obj = user_obj.companyuser.company_rotation
        return JsonResponse({
            'success': True,
            'message': 'La Programacion se guardo correctamente.',
            'grid': get_programmings(
                need_rendering=True,
                subsidiary_obj=subsidiary_obj,
                company_obj=company_obj,
                show_edit=True,
                show_plan=False),
        })
    return JsonResponse({'error': True, 'message': 'Error de peticion.'})


def get_programmings(need_rendering, subsidiary_obj=None, company_obj=None, show_edit=False, show_plan=False,
                     show_lp=False):
    my_date = datetime.now()
    formatdate = my_date.strftime("%Y-%m-%d")
    if subsidiary_obj is None:
        programmings = Programming.objects.filter(
            departure_date__gte=formatdate, truck__owner__ruc=company_obj.ruc,
            status__in=['P', 'R']
        ).order_by('departure_date')
    else:
        programmings = Programming.objects.filter(
            subsidiary=subsidiary_obj, truck__owner__ruc=company_obj.ruc,
            departure_date__gte=formatdate,
            status__in=['P', 'R']
        ).order_by('departure_date')
    if need_rendering:
        tpl = loader.get_template('comercial/programming_list.html')
        context = ({'programmings': programmings, 'show_edit': show_edit, 'show_plan': show_plan, 'show_lp': show_lp, })
        return tpl.render(context)
    return programmings


# ----------------------------------------Guide------------------------------------

def new_guide(request):
    user_id = request.user.id
    user_obj = User.objects.get(id=user_id)
    company_rotation_obj = user_obj.companyuser.company_rotation
    subsidiary_obj = get_subsidiary_by_user(user_obj)
    company_user_set = CompanyUser.objects.filter(user=user_obj)
    user_subsidiary_set = UserSubsidiary.objects.filter(subsidiary=subsidiary_obj, rol__in=['A', 'O'],
                                                        user__is_active=True)

    if company_user_set.exists():
        company_user_obj = company_user_set.last()
        company_user_obj.company_rotation = company_rotation_obj
        company_user_obj.save()

    document_types = DocumentType.objects.all()
    mydate = datetime.now()
    formatdate = mydate.strftime("%Y-%m-%d")
    formattime = mydate.strftime("%H:%M")

    cash_set = Cash.objects.filter(subsidiary=subsidiary_obj, is_bank=False)
    open_cash = get_open_cash_for_subsidiary(subsidiary_obj, formatdate)
    service_type = 'E'
    service_docs = {'E': {}}
    for doc_type in ('T', 'B', 'F'):
        service_docs['E'][doc_type] = {
            'serial': get_serial_service(subsidiary_obj, company_rotation_obj, 'E', doc_type) or '',
            'correlative': get_correlative_service(subsidiary_obj, company_rotation_obj, 'E', doc_type) or '',
        }
    return render(request, 'comercial/guide.html', {
        'document_types': document_types,
        'subsidiaries': Subsidiary.objects.all().order_by('id'),
        'subsidiary_origin': subsidiary_obj,
        'choices_type_payments': Order._meta.get_field('way_to_pay').choices,
        'choices_type_guide': OrderCommodity._meta.get_field('type_guide').choices,
        'cash_set': cash_set,
        'open_cash_id': open_cash.id if open_cash else None,
        'date': formatdate,
        'time': formattime,
        'user_subsidiary_set': user_subsidiary_set,
        'service_type': service_type,
        'service_docs': service_docs,
        'service_docs_json': json.dumps(service_docs),
    })


def get_guide_document(request):
    if request.method == 'GET':
        service_type = request.GET.get('service_type', 'E')
        doc_type = request.GET.get('document_type', 'T')
        user_obj = User.objects.get(id=request.user.id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        company_obj = user_obj.companyuser.company_rotation
        return JsonResponse({
            'serial': get_serial_service(subsidiary_obj, company_obj, service_type, doc_type) or '',
            'correlative': get_correlative_service(subsidiary_obj, company_obj, service_type, doc_type) or '',
        }, status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def create_order(request):
    if request.method == 'GET':
        orders_request = request.GET.get('orders', '')
        data_orders = json.loads(orders_request)
        # print(data_orders)
        user_id = request.user.id
        user_obj = User.objects.get(pk=int(user_id))
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        company_obj = user_obj.companyuser.company_rotation
        _document_type = 'G'
        serial = str(data_orders["Serial"])
        correlative = str(data_orders["Correlative"])
        client_obj_addressee = None
        client_obj_sender = None
        client_obj_addressee_obj = None
        client_sender_addressee_obj = None
        client_addressee_name = str(data_orders["Client_Address_Sender"])
        client_sender_name = str(data_orders["Client_Sender"])
        client_sender_phone = str(data_orders["Client_Sender_phone"])
        subsidiary_origin = str(data_orders["Subsidiary_origin"])
        subsidiary_destiny = str(data_orders["Subsidiary_destiny"])
        service_type = 'E'
        service_extra = data_orders.get('Service_Extra') or {}
        way_to_pay = str(data_orders.get('Way_to_pay') or data_orders.get('Way_to_Pay') or 'C')
        type_document = str(data_orders.get('Type') or 'T')
        if way_to_pay == 'C' and type_document == 'T':
            return JsonResponse({
                'message': 'Al contado solo se permite boleta o factura.',
            }, status=HTTPStatus.BAD_REQUEST)
        if way_to_pay == 'D' and type_document != 'T':
            return JsonResponse({
                'message': 'Pago destino solo permite ticket de encomienda.',
            }, status=HTTPStatus.BAD_REQUEST)

        if subsidiary_origin in ('0', '', 'None') or subsidiary_destiny in ('0', '', 'None'):
            subsidiary_origin_obj = subsidiary_obj
            subsidiary_destiny_obj = subsidiary_obj
        else:
            subsidiary_origin_obj = Subsidiary.objects.get(id=subsidiary_origin)
            subsidiary_destiny_obj = Subsidiary.objects.get(id=subsidiary_destiny)
        client_sender_nro_document = str(data_orders["Client_Sender_nro_document"])
        code = str(data_orders.get("Code") or "").strip() or "0000"
        type_document = str(data_orders["Type"])

        arrival_time = str(data_orders["Arrival_Time"])
        user = int(data_orders["User"])
        type_guide = str(data_orders["Type_Guide"])
        address_delivery = str(data_orders["Address_Delivery"])

        user_selected_obj = User.objects.get(pk=int(user))

        user_subsidiary_set = UserSubsidiary.objects.filter(user=user_selected_obj)

        user_subsidiary_subsidiary = None
        user_subsidiary_office = None
        user_subsidiary_printer = None
        if user_subsidiary_set.exists():
            user_subsidiary_obj = user_subsidiary_set.last()
            user_subsidiary_subsidiary = str(user_subsidiary_obj.subsidiary.id)
            user_subsidiary_office = user_subsidiary_obj.office
            user_subsidiary_printer = user_subsidiary_obj.printer

        new_correlative = get_correlative_service(
            subsidiary_obj=subsidiary_obj,
            company_obj=company_obj,
            service_type=service_type,
            doc_type=type_document,
        )

        search_commodity_set = Order.objects.filter(
            serial=serial, correlative_sale=new_correlative, type_order='E',
            company=company_obj, subsidiary=subsidiary_obj,
            type_document=type_document, service_type=service_type,
        )
        if search_commodity_set.exists():
            data = {'error': "Servicio ya registrado con esta serie y correlativo"}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        if client_sender_nro_document != '':
            client_sender_set = Client.objects.filter(clienttype__document_number=client_sender_nro_document)
            if client_sender_set:
                client_obj_sender = client_sender_set.first()
                client_obj_sender.phone = client_sender_phone
                if client_obj_sender.names != client_sender_name:
                    client_obj_sender.names = client_sender_name
                client_obj_sender.save()

            else:
                client_sender_type = str(data_orders["Client_Sender_type"])
                nationality_obj = None
                if client_sender_type == '01':
                    nationality = '9589'
                    nationality_obj = Nationality.objects.get(id=nationality)
                client_obj_sender = Client(
                    names=client_sender_name.upper(),
                    nationality=nationality_obj,
                    phone=client_sender_phone
                )
                client_obj_sender.save()
                client_type_sender_obj = ClientType(
                    client=client_obj_sender,
                    document_number=client_sender_nro_document.upper(),
                    document_type=get_document_type(client_sender_type),
                )
                client_type_sender_obj.save()
                client_sender_address = str(data_orders["Client_Address_Sender"])
                if client_sender_address:
                    client_address_sender_obj = ClientAddress(
                        address=client_sender_address,
                        client=client_obj_sender,
                    )
                    client_address_sender_obj.save()

        else:
            client_sender_addressee_obj = OrderAddressee(
                names=client_sender_name.upper(),
                phone=client_sender_phone
            )
            client_sender_addressee_obj.save()

        _type = str(data_orders["Type"])
        traslate_date = str(data_orders["Date_traslate"])
        way_to_pay = str(data_orders["Way_to_pay"])
        igv = str(data_orders["Igv"])
        sub_total = str(data_orders["Sub_total"])
        total = str(data_orders["Total"])
        is_demo = bool(int(data_orders["Demo"]))
        msg_sunat = ''
        sunat_pdf = ''

        value_is_demo = ''
        if is_demo:
            value_is_demo = 'D'
        else:
            value_is_demo = 'P'

        _dtg = ''
        if _type == 'T':
            _dtg = 'GE'
        else:
            _dtg = 'DE'

        # Guardando la cabecera Orden
        order_obj = Order(
            traslate_date=traslate_date,
            way_to_pay=way_to_pay,
            correlative_sale=new_correlative,
            serial=serial,
            user=user_selected_obj,
            subsidiary=subsidiary_obj,
            type_order='E',
            type_document=type_document,
            dtg=_dtg,
            total=total,
            company=company_obj,
            service_type=service_type,
        )
        order_obj.save()

        update_correlative_commodity(order_obj=order_obj)

        addressee_actions = []

        for data_addressee in data_orders['Addressees']:
            document_type_addressee = str(data_addressee['DocumentType'])
            document_number_addressee = str(data_addressee['DocumentNumber'])
            name_addressee = str(data_addressee['Name'])
            phone_addressee = str(data_addressee['Phone'])
            if document_number_addressee:
                client_obj_addressee_set = Client.objects.filter(clienttype__document_number=document_number_addressee)
                if client_obj_addressee_set.exists():
                    client_obj_addressee_obj = client_obj_addressee_set.first()
                    if client_obj_addressee_obj.names != name_addressee:
                        client_obj_addressee_obj.names = name_addressee
                    # if client_obj_addressee.phone is None:
                    client_obj_addressee_obj.phone = phone_addressee
                    client_obj_addressee_obj.save()
                else:
                    nationality_obj = None
                    if document_type_addressee == '01':
                        nationality = '9589'
                        nationality_obj = Nationality.objects.get(id=nationality)
                    client_obj_addressee_obj = Client(
                        names=name_addressee.upper(),
                        nationality=nationality_obj,
                        phone=phone_addressee
                    )
                    client_obj_addressee_obj.save()
                    client_type_addressee_obj = ClientType(
                        client=client_obj_addressee_obj,
                        document_number=document_number_addressee.upper(),
                        document_type=get_document_type(document_type_addressee),
                    )
                    client_type_addressee_obj.save()

                order_action_addressee_obj = OrderAction(
                    client=client_obj_addressee_obj,
                    order=order_obj,
                    type='D'
                )
                order_action_addressee_obj.save()
                addressee_actions.append(order_action_addressee_obj)

            else:
                client_addressee_obj = OrderAddressee(
                    names=name_addressee,
                    phone=phone_addressee
                )
                client_addressee_obj.save()

                order_action_addressee_obj = OrderAction(
                    order=order_obj,
                    type='D',
                    order_addressee=client_addressee_obj
                )
                order_action_addressee_obj.save()
                addressee_actions.append(order_action_addressee_obj)

        if service_type == 'E':
            commodity = save_service_for_order(
                order_obj,
                service_type,
                service_extra,
                subsidiary_origin=subsidiary_origin_obj,
                subsidiary_destiny=subsidiary_destiny_obj,
                sender=client_obj_sender,
                type_guide=type_guide,
                arrival_time=arrival_time,
                address_delivery=address_delivery,
                code=code,
            )
            commodity.addressee_name = client_addressee_name.upper()
            commodity.save(update_fields=['addressee_name', 'code_track'])
            sync_commodity_addressees(commodity, addressee_actions)

        # Guardando la orden route
        order_route_origin_obj = OrderRoute(
            order=order_obj,
            subsidiary=subsidiary_origin_obj,
            type='O'
        )
        order_route_origin_obj.save()

        order_route_destiny_obj = OrderRoute(
            order=order_obj,
            subsidiary=subsidiary_destiny_obj,
            type='D'
        )
        order_route_destiny_obj.save()

        # Guardando el orden action

        if client_sender_nro_document:
            order_action_sender_obj = OrderAction(
                client=client_obj_sender,
                order=order_obj,
                type='R'
            )
            order_action_sender_obj.save()

        else:
            order_action_sender_obj = OrderAction(
                order=order_obj,
                type='R',
                order_addressee=client_sender_addressee_obj,
            )
            order_action_sender_obj.save()

        # Guardando el detalle de la orden
        for detail in data_orders['Details']:
            quantity = decimal.Decimal(detail['Quantity'])
            price_unit = decimal.Decimal(detail['Price_unit'])
            description = str(detail['Description'])
            amount = decimal.Decimal(detail['Amount'])
            raw_weight = detail.get('Weight', '')
            try:
                weight = decimal.Decimal(str(raw_weight).strip() or '0')
            except (decimal.InvalidOperation, TypeError, ValueError):
                weight = decimal.Decimal('0')
            unit_obj = resolve_order_unit(detail.get('Unit'))

            new_item_order = OrderDetail(
                order=order_obj,
                quantity=quantity,
                price_unit=price_unit,
                description=description,
                amount=amount,
                weight=weight,
                unit=unit_obj,
            )
            new_item_order.save()

        plate = str(data_orders.get("Plate", "")).strip()
        if plate:
            truck_obj = Truck.objects.filter(license_plate=plate).last()
            if truck_obj:
                order_obj.truck = truck_obj
                order_obj.save(update_fields=['truck'])

        if _type == 'F':
            r = send_bill_commodity_fact(request, order_obj.id)
            _document_type = 'F'
            if r.get('success'):
                order_bill_obj = OrderBill(order=order_obj,
                                           serial=r.get('serie'),
                                           type=r.get('tipo_de_comprobante'),
                                           user=user_obj,
                                           n_receipt=r.get('numero'),
                                           status='E',
                                           created_at=order_obj.create_at,
                                           invoice_id=r.get('operationId'),
                                           company=order_obj.company
                                           )
                order_bill_obj.save()
            else:
                objects_to_delete = OrderDetail.objects.filter(order=order_obj)
                objects_to_delete.delete()
                order_obj.delete()
                if r.get('errors'):
                    data = {'error': str(r.get('errors'))}
                elif r.get('error'):
                    data = {'error': str(r.get('error'))}
                response = JsonResponse(data)
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response

        elif _type == 'B':
            r = send_receipt_commodity_fact(request, order_obj.id)
            _document_type = 'B'
            if r.get('success'):
                order_bill_obj = OrderBill(order=order_obj,
                                           serial=r.get('serie'),
                                           type=r.get('tipo_de_comprobante'),
                                           user=user_obj,
                                           n_receipt=r.get('numero'),
                                           status='E',
                                           created_at=order_obj.create_at,
                                           invoice_id=r.get('operationId'),
                                           company=order_obj.company
                                           )
                order_bill_obj.save()
            else:
                objects_to_delete = OrderDetail.objects.filter(order=order_obj)
                objects_to_delete.delete()
                order_obj.delete()
                if r.get('errors'):
                    data = {'error': str(r.get('errors'))}
                elif r.get('error'):
                    data = {'error': str(r.get('error'))}
                response = JsonResponse(data)
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response


        open_cash = get_open_cash_for_subsidiary(subsidiary_obj, traslate_date)
        if not open_cash:
            data = {'error': "No existe una Apertura de Caja"}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        cash_obj = open_cash

        serial_description_cash = 'PAGO DE LA ENCOMIENDA {}-{}'.format(order_obj.serial,
                                                                       order_obj.correlative_sale.zfill(6))

        if way_to_pay == 'C':
            save_cash_flow(cash_obj=cash_obj, order_obj=order_obj, user_obj=user_obj,
                           cash_flow_transact_date=traslate_date,
                           cash_flow_description=str(serial_description_cash),
                           cash_flow_type='E',
                           cash_flow_total=total)

        return JsonResponse({
            'message': 'Cambios guardados con exito.',
            'msg_sunat': msg_sunat,
            'document_type': _document_type,
            'sunat_pdf': sunat_pdf,
            'order_id': order_obj.id,
            'serial': order_obj.serial,
            'correlative': order_obj.correlative_sale,
            'userSubsidiary': user_subsidiary_subsidiary,
            'userOffice': user_subsidiary_office,
            'userPrinter': user_subsidiary_printer,
        }, status=HTTPStatus.OK)

    return JsonResponse({
        'message': 'Se guardo la guia correctamente.',
    }, status=HTTPStatus.OK)


def generate_code():
    character = string.ascii_uppercase + string.digits
    return ''.join(random.choices(character, k=4))


def get_address_subsidiary_by_id(request):
    if request.method == 'GET':
        pk = request.GET.get('subsidiary_id', '')
        subsidiary_obj = Subsidiary.objects.get(id=pk)
        address_subsidiary = subsidiary_obj.address

        return JsonResponse({'address_subsidiary': address_subsidiary, 'color': subsidiary_obj.color},
                            status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def calculate_age(birthdate):
    today = date.today()
    age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
    return age
    # # Driver code
    # print(calculateAge(date(1997, 2, 3)), "years")


DOCUMENT_TYPE_SUNAT = {
    '01': 'DNI',
    '04': 'C. EXTRANJERÍA',
    '06': 'RUC',
    '07': 'PASAPORTE',
}


def get_document_type(doc_code):
    """Resuelve el tipo de documento por código SUNAT (ej. 01, 06)."""
    doc_code = str(doc_code).strip()
    document_type = (
        DocumentType.objects.filter(id=doc_code).first()
        or DocumentType.objects.filter(sunat_code=doc_code).first()
    )
    if document_type is None:
        name = DOCUMENT_TYPE_SUNAT.get(doc_code, f'Documento {doc_code}')
        document_type, _ = DocumentType.objects.get_or_create(
            id=doc_code,
            defaults={'name': name, 'sunat_code': doc_code},
        )
    return document_type


def get_default_unit():
    """Unidad genérica para detalles de encomienda/servicio cuando no hay catálogo cargado."""
    unit, _ = Unit.objects.get_or_create(
        name='UN',
        defaults={'description': 'Unidad', 'is_enabled': True},
    )
    return unit


def resolve_order_unit(unit_value):
    if unit_value in (None, ''):
        return get_default_unit()
    try:
        unit_id = int(unit_value)
    except (TypeError, ValueError):
        return get_default_unit()
    return Unit.objects.filter(id=unit_id).first() or get_default_unit()


def get_name_business(request):
    if request.method == 'GET':
        nro_document = request.GET.get('nro_document', '')
        type_document = str(request.GET.get('type', ''))
        result = ''
        address = ''
        age = ''
        phone = ''
        client_obj_search = Client.objects.filter(clienttype__document_number=nro_document)

        if client_obj_search.exists():
            if type_document == '01':
                names = client_obj_search.first().names
                birthday = client_obj_search.first().birthday
                phone = client_obj_search.first().phone
                if birthday is not None:
                    age = calculate_age(birthday)
                return JsonResponse({'result': names, 'address': address, 'age': age, 'phone': phone},
                                    status=HTTPStatus.OK)

            elif type_document == '06':
                client_obj = client_obj_search.first()
                address_search = ClientAddress.objects.filter(client=client_obj).first()
                names = client_obj.names
                address = address_search.address if address_search else ''
                return JsonResponse({'result': names, 'address': address}, status=HTTPStatus.OK)

            elif type_document == '04' or type_document == '07':
                names = client_obj_search.first().names
                nationality = client_obj_search.first().nationality.id
                phone = client_obj_search.first().phone
                return JsonResponse({'result': names, 'nationality': nationality, 'phone': phone}, status=HTTPStatus.OK)

            else:
                data = {
                    'error': 'PROBLEMAS CON LA CONSULTA A LA RENIEC, FAVOR DE INTENTAR MAS TARDE O REGISTRE MANUALMENTE'}
                response = JsonResponse(data)
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response
        else:
            if type_document == '01':
                type_name = 'DNI'
                r = query_apis_net_dni_ruc(nro_document, type_name)
                name = r.get('nombres')
                paternal_name = r.get('apellidoPaterno')
                maternal_name = r.get('apellidoMaterno')

                if paternal_name is not None and len(paternal_name) > 0:
                    # print('client find in query_apis_net_dni_ruc')
                    result = name + ' ' + paternal_name + ' ' + maternal_name

                    if len(result.strip()) != 0:
                        client_obj = Client(
                            names=result,
                        )
                        client_obj.save()

                        client_type_obj = ClientType(
                            document_number=nro_document,
                            client=client_obj,
                            document_type=get_document_type(type_document),
                        )
                        client_type_obj.save()

                    else:
                        data = {'error': 'NO EXISTE DNI. REGISTRE MANUALMENTE'}
                        response = JsonResponse(data)
                        response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                        return response

                else:
                    data = {
                        'error': 'NO EXISTE DNI. REGISTRE MANUALMENTE / FALLO RENIEC'}
                    response = JsonResponse(data)
                    response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                    return response
            elif type_document == '06':

                type_name = 'RUC'

                r = query_apis_net_dni_ruc(nro_document, type_name)

                if r.get('numeroDocumento') == nro_document:
                    business_name = r.get('razonSocial')
                    address_business = r.get('direccion')
                    result = business_name
                    address = address_business

                    client_obj = Client(
                        names=result,
                    )
                    client_obj.save()

                    client_type_obj = ClientType(
                        document_number=nro_document,
                        client=client_obj,
                        document_type=get_document_type(type_document),
                    )
                    client_type_obj.save()

                    client_address_obj = ClientAddress(
                        address=address,
                        client=client_obj
                    )
                    client_address_obj.save()

                else:

                    # r = query_api_free_optimize_ruc(nro_document, type_name)
                    r = query_api_facturacioncloud(nro_document, type_name)
                    # if r.get('statusMessage') != 'SERVICIO SE VENCIO' and r.get('razonSocial') is not None:
                    if r.get('statusMessage') != 'SERVICIO SE VENCIO' and r.get('errors') is None:

                        if r.get('ruc') == nro_document:
                            business_name = r.get('razonSocial')
                            address_business = r.get('direccion')
                            result = business_name
                            address = address_business

                            client_obj = Client(
                                names=result,
                            )
                            client_obj.save()

                            client_type_obj = ClientType(
                                document_number=nro_document,
                                client=client_obj,
                                document_type=get_document_type(type_document),
                            )
                            client_type_obj.save()

                            client_address_obj = ClientAddress(
                                address=address,
                                client=client_obj
                            )
                            client_address_obj.save()
                    else:

                        data = {'error': 'NO EXISTE RUC. REGISTRE MANUAL O CORREGIRLO'}
                        response = JsonResponse(data)
                        response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                        return response
            else:
                data = {
                    'error': 'No esta registrado en la Base de Datos, favor de registrar manualmente'}
                response = JsonResponse(data)
                response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                return response

        return JsonResponse({'result': result, 'address': address, 'age': age}, status=HTTPStatus.OK)
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def get_phone_number_by_name_addressee(request):
    if request.method == 'GET':
        name_addressee = str(request.GET.get('name_addressee', ''))
        client_obj_search = OrderAddressee.objects.filter(names=name_addressee)
        if client_obj_search.exists():
            phone = client_obj_search.first().phone
            return JsonResponse({'phone': phone},
                                status=HTTPStatus.OK)
        else:
            data = {
                'error': 'No tiene telefono registrado'}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response
    return JsonResponse({'message': 'Error de peticion.'}, status=HTTPStatus.BAD_REQUEST)


def get_programming_query_list(request):
    if request.method == 'GET':
        return redirect('comercial:programming_list')
    elif request.method == 'POST':
        id_subsidiary = int(request.POST.get('subsidiary'))
        start_date = str(request.POST.get('start-date'))
        end_date = str(request.POST.get('end-date'))
        service_type = request.POST.get('service_type', '')
        status_filter = request.POST.get('status', '')

        programming_set = Programming.objects.filter(subsidiary__id=id_subsidiary)
        if start_date == end_date:
            programming_set = programming_set.filter(departure_date=start_date)
        else:
            programming_set = programming_set.filter(departure_date__range=[start_date, end_date])
        if service_type:
            programming_set = programming_set.filter(service_type=service_type)
        if status_filter:
            programming_set = programming_set.filter(status=status_filter)
        programming_set = programming_set.order_by('-departure_date', 'id')

        if not programming_set.exists():
            return JsonResponse({'error': 'No hay programaciones en el rango seleccionado.'},
                                status=HTTPStatus.INTERNAL_SERVER_ERROR)

        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)

        tpl = loader.get_template('comercial/programming_list.html')
        context = {
            'programmings': programming_set,
            'show_edit': True,
            'show_plan': False,
            'show_lp': False,
            'subsidiary_obj': subsidiary_obj,
        }

        return JsonResponse({
            'grid': tpl.render(context, request),
            'message': f'{programming_set.count()} programación(es) encontrada(s).',
        }, status=HTTPStatus.OK)


def report_comodity_grid(request):
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        date_now = datetime.now().strftime("%Y-%m-%d")
        subsidiaries_set = Subsidiary.objects.all().exclude(id=subsidiary_obj.id)
        user_set = UserSubsidiary.objects.filter(
            subsidiary=subsidiary_obj, rol__in=['A', 'O'], user__is_active=True
        ).select_related('user')

        return render(request, 'comercial/report_services.html', {
            'date_now': date_now,
            'subsidiaries_set': subsidiaries_set,
            'user_set': user_set,
            'subsidiary': subsidiary_obj,
            'service_types': SERVICE_TYPE_CHOICES,
            'way_to_pay_choices': WAY_TO_PAY_CHOICES,
            'user_log_perm': user_is_administrator(user_obj),
        })

    elif request.method == 'POST':
        start_date = str(request.POST.get('start-date'))
        end_date = str(request.POST.get('end-date'))
        user_selected = str(request.POST.get('user'))
        way_to_pay = str(request.POST.get('way_to_pay'))
        destiny = request.POST.get('destiny')
        service_type = request.POST.get('service_type', 'T')
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        user_select_obj = None

        order_set = Order.objects.filter(
            subsidiary=subsidiary_obj, type_order='E',
            traslate_date__range=[start_date, end_date])

        if service_type != 'T':
            order_set = order_set.filter(service_type=service_type)

        if user_selected != 'T':
            user_select_obj = User.objects.get(id=int(user_selected))

        if destiny == 'T' and way_to_pay == 'T':
            if user_selected != 'T':
                order_set = order_set.filter(user=user_select_obj)
        if destiny == 'T' and way_to_pay == 'C':
            if user_selected == 'T':
                order_set = order_set.filter(way_to_pay='C')
            elif user_selected != 'T':
                order_set = order_set.filter(user=user_select_obj, way_to_pay='C')
        if destiny == 'T' and way_to_pay == 'D':
            if user_selected == 'T':
                order_set = order_set.filter(way_to_pay='D')
            elif user_selected != 'T':
                order_set = order_set.filter(user=user_select_obj, way_to_pay='D')

        if destiny != 'T' and way_to_pay == 'T':
            if user_selected == 'T':
                order_set = order_set.filter(orderroute__type='D', orderroute__subsidiary__id=destiny)
            elif user_selected != 'T':
                order_set = order_set.filter(user=user_select_obj, orderroute__type='D',
                                             orderroute__subsidiary__id=destiny)
        if destiny != 'T' and way_to_pay == 'C':
            if user_selected == 'T':
                order_set = order_set.filter(orderroute__type='D', orderroute__subsidiary__id=destiny, way_to_pay='C')
            elif user_selected != 'T':
                order_set = order_set.filter(user=user_select_obj, orderroute__type='D',
                                             orderroute__subsidiary__id=destiny, way_to_pay='C')
        if destiny != 'T' and way_to_pay == 'D':
            if user_selected == 'T':
                order_set = order_set.filter(orderroute__type='D', orderroute__subsidiary__id=destiny, way_to_pay='D')
            elif user_selected != 'T':
                order_set = order_set.filter(user=user_select_obj, orderroute__type='D',
                                             orderroute__subsidiary__id=destiny,
                                             way_to_pay='D')

        order_set = prefetch_orders_for_report(order_set).order_by('-traslate_date', '-id')

        if not order_set.exists():
            return JsonResponse({'error': 'No hay servicios registrados en el rango seleccionado.'},
                                status=HTTPStatus.INTERNAL_SERVER_ERROR)

        order_dict = get_order_comodity_values(order_set=order_set)
        tpl = loader.get_template('comercial/report_services_grid.html')
        context = {
            'order_set': order_dict,
            'count': len(order_dict),
            'subsidiary': subsidiary_obj,
            'f1': start_date,
            'f2': end_date,
            't': user_selected,
            'w': way_to_pay,
            'd': destiny,
            'user_log_perm': user_is_administrator(user_obj),
        }
        return JsonResponse({'grid': tpl.render(context, request)}, status=HTTPStatus.OK)


def check_commodity_destiny(o):
    type_commodity_destiny = False
    for oa in o.orderaction_set.all():
        if oa.type == 'D':
            if oa.client is None and oa.order_addressee.names == '':
                type_commodity_destiny = True
    return type_commodity_destiny


def get_order_comodity_values(order_set=None):
    order_dict = []
    # cont_counted = 0
    for o in order_set:

        type_commodity_destiny = False

        item_detail_order = []
        item_route_destiny = []
        item_action_addressee = []
        item_action_sender = []
        item_set_employee = []

        for od in o.orderdetail_set.all():
            item_detail = {
                'id': od.id,
                'quantity': od.quantity,
                'unit_id': od.unit.id,
                'weight': od.weight,
                'unit_description': od.unit.description,
                'description': od.description
            }

            item_detail_order.append(item_detail)

        for ort in o.orderroute_set.all():
            item_route_d = {
                'id': ort.id,
                'type': ort.type,
                'subsidiary': ort.subsidiary.name if ort.subsidiary_id else '—',
            }
            item_route_destiny.append(item_route_d)

        destiny_label = get_service_destiny_label(o)
        if destiny_label != '—' and not item_route_destiny:
            item_route_destiny.append({'id': 0, 'type': 'D', 'subsidiary': destiny_label})

        for oa in o.orderaction_set.all():

            if oa.type == 'D':
                _client_names = ''
                if oa.client is None and oa.order_addressee.names == '':
                    type_commodity_destiny = True
                    _client_names = 'CANJE DE ENCOMIENDA'
                else:
                    if oa.client is None:
                        _client_names = oa.order_addressee.names
                    else:
                        _client_names = oa.client.names

                item_action_a = {
                    'id': oa.id,
                    'client_names': _client_names
                }
                item_action_addressee.append(item_action_a)

            elif oa.type == 'R':

                _client_sender_names = ''

                if oa.client is None:
                    _client_sender_names = oa.order_addressee.names
                else:
                    _client_sender_names = oa.client.names
                item_action_s = {
                    'id': oa.id,
                    'client_names': _client_sender_names
                }
                item_action_sender.append(item_action_s)

        if o.truck_id:
            item_set_employee.append({
                'id': o.truck_id,
                'names': o.truck.license_plate,
            })

        order_item = {
            'id': o.id,
            'company': o.company.short_name,
            'traslate_date': o.traslate_date,
            'type_document': o.type_document,
            'type_document_label': o.get_type_document_display(),
            'service_type': o.service_type,
            'service_type_label': o.get_service_type_display(),
            'serial': o.serial,
            'correlative_sale': o.correlative_sale,
            'total': decimal.Decimal(o.sum_total_details()).quantize(decimal.Decimal('0.00'),
                                                                     rounding=decimal.ROUND_HALF_EVEN),
            'way_to_pay': o.way_to_pay,
            'way_to_pay_label': o.get_way_to_pay_display(),
            'status': o.status,
            'status_label': o.get_status_display(),
            'status_transport': (
                o.encomienda.get_status_transport_display()
                if getattr(o, 'encomienda', None)
                else '—'
            ),
            'destiny_label': destiny_label,
            'user': o.user.username,
            'item_detail_order': item_detail_order,
            'item_route_destiny': item_route_destiny,
            'item_action_addressee': item_action_addressee,
            'item_action_sender': item_action_sender,
            'item_set_employee': item_set_employee,
            'type_commodity_destiny': type_commodity_destiny,
        }
        order_dict.append(order_item)

    return order_dict


def report_manifest_grid(request):
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        company_rotation_obj = user_obj.companyuser.company_rotation
        date_now = datetime.now().strftime("%Y-%m-%d")
        serials = get_serial_subsidiary_company(subsidiary_obj=subsidiary_obj,
                                                company_rotation_obj=company_rotation_obj)
        serial_commodity = serials.get('serial_commodity')
        programmings = get_programmings(False, subsidiary_obj=subsidiary_obj, company_obj=company_rotation_obj)
        # programmings = Programming.objects.filter(status__in=['P'], subsidiary=subsidiary_obj, departure_date=date_now).order_by('id')
        return render(request, 'comercial/report_manifest.html', {
            'date_now': date_now,
            'programmings': programmings,
            'serial': serial_commodity
        })

    elif request.method == 'POST':
        start_date = str(request.POST.get('start-date'))
        end_date = str(request.POST.get('end-date'))
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)

        if start_date == end_date:
            # op_set = OrderProgramming.objects.filter(manifest__subsidiary=subsidiary_obj, manifest__created_at__date=start_date, manifest__isnull=False).annotate(Sum('manifest_id')).first()
            manifest_set = Manifest.objects.filter(subsidiary=subsidiary_obj, created_at__date=start_date)
        else:
            manifest_set = Manifest.objects.filter(subsidiary=subsidiary_obj,
                                                   created_at__date__range=[start_date, end_date])
            # op_set = OrderProgramming.objects.filter(manifest__subsidiary=subsidiary_obj, manifest__created_at__date__range=[start_date, end_date], manifest__isnull=False).annotate(Sum('manifest_id')).first()

        has_rows = False
        if manifest_set:
            has_rows = True
        else:
            data = {'error': "No hay manifiestos registradas"}
            response = JsonResponse(data)
            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
            return response

        tpl = loader.get_template('comercial/report_manifest_grid.html')
        context = ({
            'manifest_set': manifest_set,
            'has_rows': has_rows
        })
        return JsonResponse({
            'grid': tpl.render(context, request),
        }, status=HTTPStatus.OK)


def get_truck(request):
    if request.method == 'GET':
        pk = request.GET.get('pk', '')

        truck_set = Truck.objects.filter(id=pk)
        truck_serialized_data = serializers.serialize('json', truck_set)
        return JsonResponse({
            'success': True,
            'truck_serialized': truck_serialized_data,
        })
    return JsonResponse({'error': True, 'message': 'Error de peticion.'})


def cancel_commodity(request):
    if request.method == 'GET':
        start_date = str(request.GET.get('start-date'))
        end_date = str(request.GET.get('end-date'))
        order_id = int(request.GET.get('pk', ''))
        user_selected = str(request.GET.get('user'))
        way_to_pay = str(request.GET.get('way_to_pay'))
        destiny = request.GET.get('destiny')

        order_obj = Order.objects.get(pk=order_id)

        type_order = order_obj.type_order
        type_document = order_obj.type_document

        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)

        user_select_obj = None

        message = ''

        if type_order == 'E':
            _motive = request.GET.get('reason')
            if type_document == 'T':
                order_obj.status = 'A'
                order_obj.cancel_motive = _motive
                order_obj.save()
                cash_obj = CashFlow.objects.filter(order=order_obj)
                cash_obj.delete()

            elif type_document == 'F' or type_document == 'B':
                order_bill_set = OrderBill.objects.filter(order=order_id)
                if order_bill_set.exists():
                    # r = send_cancel_bill_nubefact(order_id, _motive)
                    # enlace = r.get('enlace')
                    r = annul_invoice(order_id)
                    enlace = r.get('success')
                    if enlace:
                        order_obj.status = 'A'
                        order_obj.save()
                        cash_obj = CashFlow.objects.filter(order=order_obj)
                        cash_obj.delete()
                    else:
                        data = {'error': "Error de anulación en sunat, "
                                         "Actualice o vuelva a intentarlo"}
                        response = JsonResponse(data)
                        response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                        return response

            # elif type_document == 'B':
            #     order_bill_set = OrderBill.objects.filter(order=order_id)
            #     if order_bill_set.exists():
            #         r = send_cancel_bill_nubefact(order_id, _motive)
            #         enlace = r.get('enlace')
            #         if enlace:
            #             message = "Encomienda anulada correctamente en SUNAT"
            #         else:
            #             message = "Encomienda anulada Internamente, REVISAR ANULACION EN SUNAT"
            #         order_obj.status = 'A'
            #         order_obj.save()
            #         cash_obj = CashFlow.objects.filter(order=order_obj)
            #         cash_obj.delete()

        order_set = Order.objects.filter(
            subsidiary=subsidiary_obj, type_order='E', traslate_date__range=[start_date, end_date])

        if user_selected != 'T':
            user_select_obj = User.objects.get(id=int(user_selected))

            order_set = order_set

        if destiny == 'T' and way_to_pay == 'T':
            if user_selected == 'T':
                order_set = order_set
            elif user_selected != 'T':
                order_set = order_set.filter(user=user_select_obj)
        if destiny == 'T' and way_to_pay == 'C':
            if user_selected == 'T':
                order_set = order_set.filter(way_to_pay='C')
            elif user_selected != 'T':
                order_set = order_set.filter(user=user_select_obj, way_to_pay='C')
        if destiny == 'T' and way_to_pay == 'D':
            if user_selected == 'T':
                order_set = order_set.filter(way_to_pay='D')
            elif user_selected != 'T':
                order_set = order_set.filter(user=user_select_obj, way_to_pay='D')

        if destiny != 'T' and way_to_pay == 'T':
            if user_selected == 'T':
                order_set = order_set.filter(orderroute__type='D', orderroute__subsidiary__id=destiny)
            elif user_selected != 'T':
                order_set = order_set.filter(user=user_select_obj, orderroute__type='D',
                                             orderroute__subsidiary__id=destiny)
        if destiny != 'T' and way_to_pay == 'C':
            if user_selected == 'T':
                order_set = order_set.filter(orderroute__type='D', orderroute__subsidiary__id=destiny, way_to_pay='C')
            elif user_selected != 'T':
                order_set = order_set.filter(user=user_select_obj, orderroute__type='D',
                                             orderroute__subsidiary__id=destiny, way_to_pay='C')
        if destiny != 'T' and way_to_pay == 'D':
            if user_selected == 'T':
                order_set = order_set.filter(orderroute__type='D', orderroute__subsidiary__id=destiny, way_to_pay='D')
            elif user_selected != 'T':
                order_set = order_set.filter(user=user_select_obj, orderroute__type='D',
                                             orderroute__subsidiary__id=destiny,
                                             way_to_pay='D')

        order_set = prefetch_orders_for_report(order_set).order_by('-traslate_date', '-id')

        order_dict = get_order_comodity_values(order_set=order_set)

        tpl = loader.get_template('comercial/report_services_grid.html')
        context = {
            'order_set': order_dict,
            'count': len(order_dict),
            'subsidiary': subsidiary_obj,
            'f1': start_date,
            'f2': end_date,
            't': user_selected,
            'w': way_to_pay,
            'd': destiny,
            'user_log_perm': user_is_administrator(user_obj),
        }
        return JsonResponse({
            'message': message,
            'grid': tpl.render(context, request)
        }, status=HTTPStatus.OK)


def get_modal_change(request):
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        _subsidiary_origin = request.GET.get('_subsidiary_origin', '')
        _order_id = request.GET.get('_order_id', '')
        subsidiary_set = ''
        # if subsidiary_obj.id == 1:

        subsidiary_set = Subsidiary.objects.all().exclude(id=subsidiary_obj.id)

        tpl = loader.get_template('comercial/new_destiny_comodity.html')
        context = ({
            'subsidiary_set': subsidiary_set,
            'subsidiary_origin': _subsidiary_origin,
            'order_id': _order_id,
        })
        return JsonResponse({
            'grid': tpl.render(context, request),
        }, status=HTTPStatus.OK)


def change_destiny(request):
    if request.method == 'POST':
        order_id = request.POST.get('orden', '')
        new_destiny = int(request.POST.get('new_destiny', ''))
        new_subsidiary_destiny_obj = Subsidiary.objects.get(id=new_destiny)
        order_obj = Order.objects.get(id=int(order_id))
        order_route_obj = OrderRoute.objects.filter(order=order_obj, type='D').first()
        order_route_obj.subsidiary = new_subsidiary_destiny_obj
        order_route_obj.save()
        # serialized_new_subsidiary_destiny = serializers.serialize('json', new_subsidiary_destiny_obj)

        return JsonResponse({
            'message': 'Sucursal actualizada correctamente',
            'destiny': new_subsidiary_destiny_obj.name,
        }, status=HTTPStatus.OK)


def get_modal_way_pay(request):
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        way_to_pay = request.GET.get('way_to_pay', '')
        _order_id = request.GET.get('_order_id', '')
        tpl = loader.get_template('comercial/new_way_to_pay_modal.html')

        context = ({
            'choices_type_payments': Order._meta.get_field('way_to_pay').choices,
            'order_id': _order_id,
        })
        return JsonResponse({
            'grid': tpl.render(context, request),
        }, status=HTTPStatus.OK)


def change_way_to_pay(request):
    if request.method == 'POST':
        order_id = request.POST.get('orden', '')
        way_to_pay = str(request.POST.get('way_to_pay', ''))
        order_obj = Order.objects.get(id=int(order_id))
        order_obj.way_to_pay = way_to_pay
        order_obj.save()
        return JsonResponse({
            'message': 'Cambio actualizado correctamente',
            'way_to_pay': way_to_pay,
            'total': order_obj.total,
        }, status=HTTPStatus.OK)


def save_truck_exit(request):
    if request.method == 'GET':
        programming_id = request.GET.get('programming_id', '')
        truck_exit = request.GET.get('truck_exit', '')
        programming_obj = Programming.objects.get(id=int(programming_id))
        programming_obj.truck_exit = truck_exit
        programming_obj.save()

        return JsonResponse({
            'success': True,
        })
    return JsonResponse({'error': True, 'message': 'Error de peticion.'})


def check_bill(request):
    if request.method == 'GET':
        order_id = request.GET.get('order_id', '')
        try:
            order_bill = OrderBill.objects.get(order_id=order_id)
        except OrderBill.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Orden no encontrada.'}, status=HTTPStatus.NOT_FOUND)

        if not (order_bill.link_xml and order_bill.link_cdr):
            result = get_sale_by_id(order_bill.invoice_id)
            if not result.get('success'):
                return JsonResponse({'success': False, 'message': 'Orden sin comprobante electrónico'},
                                    status=HTTPStatus.OK)

            order_bill.link_xml = result.get('linkXml')
            order_bill.link_cdr = result.get('linkCdr')
            order_bill.save()

        return JsonResponse({
            'success': True,
            'linkXml': order_bill.link_xml,
            'linkCdr': order_bill.link_cdr,
        }, status=HTTPStatus.OK)
    return JsonResponse({'error': True, 'message': 'Error de peticion.'})


def get_all_programmings(request):
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        my_date = datetime.now()
        formatdate = my_date.strftime("%Y-%m-%d")
        
        # Obtener fecha de la URL si se proporciona
        date_param = request.GET.get('date', formatdate)
        
        # Convertir la fecha a objeto datetime
        try:
            search_date = datetime.strptime(date_param, "%Y-%m-%d").date()
        except ValueError:
            search_date = my_date.date()
        
        # Obtener todas las programaciones SOLO de trucks para la fecha especificada
        programmings = Programming.objects.filter(
            departure_date=search_date,
            truck__isnull=False
        ).select_related('truck', 'subsidiary')
        
        # Agrupar por placa
        trucks_programmings = {}
        for programming in programmings:
            license_plate = programming.truck.license_plate
            if license_plate not in trucks_programmings:
                trucks_programmings[license_plate] = {
                    'truck': programming.truck,
                    'programmings': []
                }
            trucks_programmings[license_plate]['programmings'].append(programming)

        return render(request, 'comercial/get_trucks_programmings.html', {
            'subsidiary_obj': subsidiary_obj,
            'user_obj': user_obj,
            'date_now': formatdate,
            'search_date': search_date,
            'trucks_programmings': trucks_programmings,
        })


def get_trucks_programming_grid(request):
    if request.method == 'GET':
        user_id = request.user.id
        user_obj = User.objects.get(id=user_id)
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        my_date = datetime.now()
        formatdate = my_date.strftime("%Y-%m-%d")
        
        # Obtener parámetros de la URL
        date_param = request.GET.get('date', formatdate)
        license_plate = request.GET.get('plate', '')
        
        # Convertir la fecha a objeto datetime
        try:
            search_date = datetime.strptime(date_param, "%Y-%m-%d").date()
        except ValueError:
            search_date = my_date.date()
        
        # Obtener programaciones para la placa y fecha específicas
        programmings = Programming.objects.filter(
            departure_date=search_date
        ).select_related('truck', 'subsidiary')

        if license_plate:
            programmings = programmings.filter(truck__license_plate=license_plate)

        vehicle_info = None
        if license_plate:
            truck = Truck.objects.filter(license_plate=license_plate).first()
            if truck:
                vehicle_info = {'truck': truck}

        return render(request, 'comercial/get_trucks_programming_grid.html', {
            'subsidiary_obj': subsidiary_obj,
            'user_obj': user_obj,
            'date_now': formatdate,
            'search_date': search_date,
            'license_plate': license_plate,
            'vehicle_info': vehicle_info,
            'programmings': programmings,
        })


# ----------------------- Remission guides assignment -----------------------

class GuideAssignmentView(TemplateView):
    """Módulo para asignar encomiendas a programación y emitir guías."""
    template_name = 'comercial/guide_assignment.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_obj = self.request.user
        subsidiary_obj = get_subsidiary_by_user(user_obj)
        today = date.today()
        date_param = self.request.GET.get('date') or today.strftime('%Y-%m-%d')
        try:
            search_date = datetime.strptime(date_param, '%Y-%m-%d').date()
        except ValueError:
            search_date = today

        programmings = Programming.objects.filter(
            departure_date=search_date,
            status__in=['P', 'R'],
        ).select_related(
            'truck', 'subsidiary', 'company', 'cargo_manifest', 'carrier_guide',
        ).order_by('turn', 'id')

        pending_orders = Order.objects.filter(
            status='P',
            type_order='E',
            service_type='E',
        ).exclude(
            sender_guide__status='I',
        ).select_related(
            'encomienda__office_destination',
            'client',
            'user',
        ).prefetch_related(
            'orderaction_set__client',
            'orderdetail_set',
        ).order_by('-id')[:200]

        assigned_guides = SenderRemissionGuide.objects.filter(
            status='I',
            programming__departure_date=search_date,
        ).select_related(
            'order', 'programming', 'programming__truck', 'carrier_guide', 'cargo_manifest',
        ).order_by('-id')

        cargo_manifests = CargoManifest.objects.filter(
            programming__departure_date=search_date,
        ).exclude(status='X').select_related(
            'programming', 'truck',
        ).prefetch_related('sender_guides')

        carrier_guides = CarrierRemissionGuide.objects.filter(
            programming__departure_date=search_date,
        ).exclude(status='X').select_related(
            'programming', 'truck',
        ).prefetch_related('sender_guides')

        context.update({
            'search_date': search_date,
            'programmings': programmings,
            'pending_orders': pending_orders,
            'assigned_guides': assigned_guides,
            'cargo_manifests': cargo_manifests,
            'carrier_guides': carrier_guides,
            'subsidiary': subsidiary_obj,
        })
        return context


def assign_order_guide(request):
    """POST: asigna una orden a una programación y crea guía remitente."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=HTTPStatus.BAD_REQUEST)
    try:
        order_id = int(request.POST.get('order_id') or 0)
        programming_id = int(request.POST.get('programming_id') or 0)
        order_obj = Order.objects.select_related('encomienda').get(pk=order_id)
        programming_obj = Programming.objects.select_related('truck').get(pk=programming_id)
        if not programming_obj.support_pilot:
            return JsonResponse({
                'success': False,
                'message': 'La programación no tiene conductor asignado.',
            }, status=HTTPStatus.BAD_REQUEST)
        guide = assign_order_to_programming(order_obj, programming_obj, request.user)
        return JsonResponse({
            'success': True,
            'message': 'Asignado.',
            'guide_id': guide.id,
            'document_number': guide.document_number(),
        }, status=HTTPStatus.OK)
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Orden no encontrada.'}, status=HTTPStatus.NOT_FOUND)
    except Programming.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Programación no encontrada.'}, status=HTTPStatus.NOT_FOUND)
    except Exception as exc:
        return JsonResponse({'success': False, 'message': str(exc)}, status=HTTPStatus.BAD_REQUEST)


def create_cargo_manifest(request):
    """POST: genera el manifiesto de carga obligatorio de una programación."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=HTTPStatus.BAD_REQUEST)
    try:
        programming_id = int(request.POST.get('programming_id') or 0)
        programming_obj = Programming.objects.select_related('truck', 'subsidiary', 'company').get(
            pk=programming_id,
        )
        manifest = create_cargo_manifest_for_programming(programming_obj, request.user)
        return JsonResponse({
            'success': True,
            'message': f'Manifiesto de carga {manifest.document_number()} emitido.',
            'manifest_id': manifest.id,
            'document_number': manifest.document_number(),
            'print_url': f'/comercial/print_cargo_manifest/{manifest.id}/',
            'guides_count': manifest.guides_count,
        }, status=HTTPStatus.OK)
    except Programming.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Programación no encontrada.'}, status=HTTPStatus.NOT_FOUND)
    except ValueError as exc:
        return JsonResponse({'success': False, 'message': str(exc)}, status=HTTPStatus.BAD_REQUEST)
    except Exception as exc:
        return JsonResponse({'success': False, 'message': str(exc)}, status=HTTPStatus.BAD_REQUEST)


def create_carrier_guide(request):
    """POST: genera la guía transportista opcional de una programación."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=HTTPStatus.BAD_REQUEST)
    try:
        programming_id = int(request.POST.get('programming_id') or 0)
        programming_obj = Programming.objects.select_related('truck', 'subsidiary', 'company').get(
            pk=programming_id,
        )
        try:
            manifest = programming_obj.cargo_manifest
        except CargoManifest.DoesNotExist:
            manifest = None
        if not manifest or manifest.status == 'X':
            return JsonResponse({
                'success': False,
                'message': 'Primero debe emitir el manifiesto de carga.',
            }, status=HTTPStatus.BAD_REQUEST)
        carrier = create_carrier_guide_for_programming(programming_obj, request.user)
        return JsonResponse({
            'success': True,
            'message': f'Guía transportista {carrier.document_number()} emitida.',
            'guide_id': carrier.id,
            'document_number': carrier.document_number(),
            'print_url': f'/comercial/print_guide_format_a4/{carrier.id}/',
            'guides_count': carrier.sender_guides.count(),
        }, status=HTTPStatus.OK)
    except Programming.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Programación no encontrada.'}, status=HTTPStatus.NOT_FOUND)
    except ValueError as exc:
        return JsonResponse({'success': False, 'message': str(exc)}, status=HTTPStatus.BAD_REQUEST)
    except Exception as exc:
        return JsonResponse({'success': False, 'message': str(exc)}, status=HTTPStatus.BAD_REQUEST)


def unassign_order_guide(request):
    """POST: anula la asignación de una guía remitente."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=HTTPStatus.BAD_REQUEST)
    try:
        guide_id = int(request.POST.get('guide_id') or 0)
        guide = SenderRemissionGuide.objects.select_related('order').get(pk=guide_id)
        unassign_sender_guide(guide)
        return JsonResponse({'success': True, 'message': 'Asignación anulada.'}, status=HTTPStatus.OK)
    except SenderRemissionGuide.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Guía no encontrada.'}, status=HTTPStatus.NOT_FOUND)
    except Exception as exc:
        return JsonResponse({'success': False, 'message': str(exc)}, status=HTTPStatus.BAD_REQUEST)

