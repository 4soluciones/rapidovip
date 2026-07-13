from django.shortcuts import render
from django.views.generic import TemplateView, View, CreateView, UpdateView
from django.views.decorators.csrf import csrf_exempt
from django.forms.models import model_to_dict
from django.http import JsonResponse
from http import HTTPStatus

from .models import *
from .forms import *
from apps.users.models import Subsidiary, District, DocumentType, Employee, Worker
from apps.comercial.models import Truck
from django.contrib.auth.models import User
from apps.users.user_helpers import get_subsidiary_by_user
from apps.accounting.views import Cash, CashFlow
import json
import decimal
import math
import random
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models.fields.files import ImageFieldFile
from django.template import loader
from datetime import datetime
from django.db import DatabaseError, IntegrityError
from django.core import serializers
from apps.sales.views_SUNAT import send_bill_nubefact, send_receipt_nubefact, send_bill_passenger, \
    send_receipt_passenger
from apps.sales.models import OrderBill
from apps.sales.number_to_letters import numero_a_moneda
from django.db.models import Min, Prefetch


PAYMENT_TYPE_CHOICES = (
    ('D', 'Deposito'),
    ('E', 'Efectivo'),
    ('F', 'FISE'),
)


class Home(TemplateView):
    """Redirige al listado de clientes (módulo ventas legacy)."""

    def get(self, request, *args, **kwargs):
        from django.shortcuts import redirect
        return redirect('sales:client_list')


class ExtendedEncoder(DjangoJSONEncoder):
    def default(self, o):
        if isinstance(o, ImageFieldFile):
            return str(o)
        else:
            return super().default(o)


def get_clients_values():
    client_set = Client.objects.prefetch_related(
        Prefetch(
          'clienttype_set', queryset=ClientType.objects.select_related('document_type')
        ),
        Prefetch(
          'clientaddress_set', queryset=ClientAddress.objects.select_related('district')
        ),
    ).all().values(
        'id',
        'names',
        'phone',
        'clienttype__document_type__description',
        'clienttype__document_number',
        'clientaddress__address',
        'clientaddress__district__description',
        'clientaddress__reference',
        'email'
    )[:10000]
    client_dict = {}
    for c in client_set:
        key = c['id']
        client_dict[key] = {
            'id': c['id'],
            'names': c['names'],
            'phone': c['phone'],
            'client_type': c['clienttype__document_type__description'],
            'client_document_number': c['clienttype__document_number'],
            'address': c['clientaddress__address'],
            'district': c['clientaddress__district__description'],
            'reference': ['clientaddress__reference'],
            'email': c['email'],
        }
    return client_dict


class ClientList(View):
    model = Client
    form_class = FormClient
    template_name = 'sales/client_list.html'

    def get_queryset(self):
        return self.model.objects.all().order_by('id')

    def get_context_data(self, **kwargs):
        contexto = {}
        contexto['clients'] = get_clients_values()
        contexto['form'] = self.form_class
        contexto['document_types'] = DocumentType.objects.all()
        contexto['districts'] = District.objects.all()
        return contexto

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, self.get_context_data())


@csrf_exempt
def new_client(request):
    data = dict()
    if request.method == 'POST':

        names = request.POST.get('names')
        phone = request.POST.get('phone', '')
        address = request.POST.get('address', '')
        email = request.POST.get('email', '')
        document_number = request.POST.get('document_number', '')
        document_type_id = request.POST.get('document_type', '')
        id_district = request.POST.get('id_district', '')
        reference = request.POST.get('reference', '')
        operation = request.POST.get('operation', '')
        client_id = int(request.POST.get('client_id', ''))

        if operation == 'N':

            if len(names) > 0:

                data_client = {
                    'names': names,
                    'phone': phone,
                    'email': email,
                }

                client = Client.objects.create(**data_client)
                client.save()

                if len(document_number) > 0:

                    try:
                        document_type = DocumentType.objects.get(id=document_type_id)
                    except DocumentType.DoesNotExist:
                        data['error'] = "Documento no existe!"
                        response = JsonResponse(data)
                        response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                        return response

                    data_client_type = {
                        'client': client,
                        'document_type': document_type,
                        'document_number': document_number,
                    }
                    client_type = ClientType.objects.create(**data_client_type)
                    client_type.save()

                    if len(address) > 0:

                        try:
                            district = District.objects.get(id=id_district)
                        except District.DoesNotExist:
                            data['error'] = "Distrito no existe!"
                            response = JsonResponse(data)
                            response.status_code = HTTPStatus.INTERNAL_SERVER_ERROR
                            return response

                        data_client_address = {
                            'client': client,
                            'address': address,
                            'district': district,
                            'reference': reference,
                        }
                        client_address = ClientAddress.objects.create(**data_client_address)
                        client_address.save()
                return JsonResponse({'success': True, 'message': 'El cliente se registro correctamente.'})
        else:

            client_obj = Client.objects.get(pk=client_id)
            client_obj.names = names
            client_obj.phone = phone
            client_obj.email = email
            client_obj.save()
            district = District.objects.get(id=id_district)
            document_type = DocumentType.objects.get(id=document_type_id)

            client_address_set = ClientAddress.objects.filter(client_id=client_id)
            if client_address_set:
                client_address_obj = client_address_set.first()

                client_address_obj.address = address
                client_address_obj.district = district
                client_address_obj.reference = reference
                client_address_obj.save()
            else:
                data_client_address = {
                    'client': client_obj,
                    'address': address,
                    'district': district,
                    'reference': reference,
                }
                client_address = ClientAddress.objects.create(**data_client_address)
                client_address.save()

            client_type_set = ClientType.objects.filter(client_id=client_id)
            if client_type_set:
                client_type_obj = client_type_set.first()
                client_type_obj.document_type = document_type
                client_type_obj.document_number = document_number
                client_type_obj.save()
            else:
                data_client_type = {
                    'client': client_obj,
                    'document_type': document_type,
                    'document_number': document_number,
                }
                client_type = ClientType.objects.create(**data_client_type)
                client_type.save()

            return JsonResponse({'success': True, 'message': 'El cliente se actualizo correctamente.'})
    return JsonResponse({'error': True, 'message': 'Error de peticion.'})


def get_client(request):
    if request.method == 'GET':
        pk = request.GET.get('pk', '')
        client_set = Client.objects.filter(id=pk)
        client_address_set = ClientAddress.objects.filter(client_id=pk)
        client_type_set = ClientType.objects.filter(client_id=pk)
        client_bill_set = OrderBill.objects.filter(order__client__id=client_set.first().id)
        client_serialized_data = serializers.serialize('json', client_set)
        client_serialized_data_address = serializers.serialize('json', client_address_set)
        client_serialized_data_type = serializers.serialize('json', client_type_set)
        client_bill = serializers.serialize('json', client_bill_set)

        return JsonResponse({
            'success': True,
            'client_names': client_set.first().names,
            'client_serialized': client_serialized_data,
            'client_serialized_data_address': client_serialized_data_address,
            'client_serialized_data_type': client_serialized_data_type,
            'client_bill': client_bill,
        })
    return JsonResponse({'error': True, 'message': 'Error de peticion.'})

