# from django.contrib.sites import requests
import requests
import html
from django.http import JsonResponse
from http import HTTPStatus

from .format_to_dates import utc_to_local
from .models import *
import math
from apps.users.models import Department, Province
from apps.users.subsidiary_serial_helpers import get_serial_record
from apps.comercial.models import Owner
from django.contrib.auth.models import User
import json
from django.core.serializers.json import DjangoJSONEncoder
from datetime import datetime
from django.db import DatabaseError, IntegrityError
from django.core import serializers
from django.views.decorators.csrf import csrf_exempt
from .number_to_letters import numero_a_moneda
from apps.comercial.models import Truck
from ..users.user_helpers import get_subsidiary_by_user


def send_bill(order_id):
    order_obj = Order.objects.get(id=int(order_id))
    details = OrderDetail.objects.filter(order=order_obj)
    client_obj = order_obj.client
    client_first_address = client_obj.clientaddress_set.first()
    client_document = client_obj.clienttype_set.filter(document_type_id='06').first()
    client_department = Department.objects.get(id=client_first_address.district[:2])
    register_date = datetime.now()
    formatdate = register_date.strftime("%Y-%m-%d")

    items = []
    index = 1
    sub_total = 0
    total = 0
    igv_total = 0
    for d in details:
        base_total = round(d.quantity_sold * d.price_unit)  # 5 * 20 = 100
        base_amount = round((base_total / 1.18), 2)  # 100 / 1.18 = 84.75
        igv = round((base_total - base_amount), 2)  # 100 - 84.75 = 15.25
        sub_total = round((sub_total + base_amount), 2)
        total = total + base_total
        igv_total = igv_total + igv
        # redondear a un decimal
        item = {
            "ITEM": index,
            "UNIDAD_MEDIDA": d.unit.name if d.unit_id else 'NIU',
            "CANTIDAD": d.quantity_sold,
            "PRECIO": float(d.price_unit),
            "IMPORTE": base_total,
            "PRECIO_TIPO_CODIGO": "01",  # 01--TABLA SUNAT = APLICA IGV
            "IGV": igv,
            "ISC": 0.0,
            "COD_TIPO_OPERACION": "10",  # 10--OPERACION ONEROSA
            "CODIGO": str(d.id).zfill(4),
            "DESCRIPCION": d.description or 'SERVICIO DE TRANSPORTE',
            "PRECIO_SIN_IMPUESTO": float(d.price_unit)

        }
        items.append(item)
        index = index + 1

    params = {
        "TIPO_OPERACION": "",
        "TOTAL_GRAVADAS": sub_total,
        "TOTAL_INAFECTA": 0.0,
        "TOTAL_EXONERADAS": 0.0,
        "TOTAL_GRATUITAS": 0.0,
        "TOTAL_PERCEPCIONES": 0.0,
        "TOTAL_RETENCIONES": 0.0,
        "TOTAL_DETRACCIONES": 0.0,
        "TOTAL_BONIFICACIONES": 0.0,
        "TOTAL_DESCUENTO": 0.0,
        "SUB_TOTAL": sub_total,
        "POR_IGV": 0.0,
        "TOTAL_IGV": igv_total,
        "TOTAL_ISC": 0.0,
        "TOTAL_EXPORTACION": 0.0,
        "TOTAL_OTR_IMP": 0.0,
        "TOTAL": total,
        "TOTAL_LETRAS": numero_a_moneda(total),
        "NRO_COMPROBANTE": "F001-0010",
        "FECHA_DOCUMENTO": formatdate,
        "COD_TIPO_DOCUMENTO": "01",  # 01=FACTURA, 03=BOLETA, 07=NOTA CREDITO, 08=NOTA DEBITO
        "COD_MONEDA": "PEN",
        "NRO_DOCUMENTO_CLIENTE": client_document.document_number,
        "RAZON_SOCIAL_CLIENTE": client_obj.names,
        "TIPO_DOCUMENTO_CLIENTE": "6",  # 1=DNI,6=RUC
        "DIRECCION_CLIENTE": client_first_address.address,
        "CIUDAD_CLIENTE": client_department,
        "COD_PAIS_CLIENTE": "PE",
        "NRO_DOCUMENTO_EMPRESA": "20434893217",
        "TIPO_DOCUMENTO_EMPRESA": "6",
        "NOMBRE_COMERCIAL_EMPRESA": "METALNOX EDMA S.R.L.",
        "CODIGO_UBIGEO_EMPRESA": "040112",
        "DIRECCION_EMPRESA": "VILLA JESUS MZA. E LOTE. 6 (FRENTE POSTA VILLA MEDICA VILLA JESUS)",
        "DEPARTAMENTO_EMPRESA": "AREQUIPA",
        "PROVINCIA_EMPRESA": "AREQUIPA",
        "DISTRITO_EMPRESA": "PAUCARPATA",
        "CODIGO_PAIS_EMPRESA": "PE",
        "RAZON_SOCIAL_EMPRESA": "METALNOX EDMA SOCIEDAD COMERCIAL DE RESPONSABILIDAD LIMITADA - METALNOX EDMA S.R.L.",
        "USUARIO_SOL_EMPRESA": "METALNOX",
        "PASS_SOL_EMPRESA": "Metalnox1",
        "CONTRA": "123456.",
        "TIPO_PROCESO": "3",
        "FLG_ANTICIPO": "0",
        "FLG_REGU_ANTICIPO": "0",
        "MONTO_REGU_ANTICIPO": "0",
        "PASS_FIRMA": "Ax123456789",
        "Detalle": items
    }

    url = 'http://www.facturacioncloud.com/cpesunatUBL21/CpeServlet?accion=WSSunatCPE_V2'
    headers = {'content-type': 'application/json'}
    response = requests.post(url, json=params, headers=headers)

    if response.status_code == 200:
        result = response.json()

        context = {
            'message': result.get("des_msj_sunat"),
            'params': params
        }
        return context


def query_dni(nro_dni, type_document):
    url = 'https://www.facturacionelectronica.us/facturacion/controller/ws_consulta_rucdni_v2.php'
    _user_marvisur = '20498189637'
    _pw_marvisur = 'marvisur.123.'
    _user_nikitus = '10465240861'
    _pw_nikitus = '123456.'
    params = {
        'usuario': _user_marvisur,
        'password': _pw_marvisur,
        'documento': type_document,
        'nro_documento': nro_dni
    }
    r = requests.get(url, params)

    if r.status_code == 200:
        result = r.json()

        if result.get('success') == "True":
            context = {
                'success': result.get('success'),
                'statusMessage': result.get('statusMessage'),
                'result': result.get('result'),
                'DNI': result.get('result').get('DNI'),
                'Nombre': result.get('result').get('Nombre'),
                'Paterno': result.get('result').get('Paterno'),
                'Materno': result.get('result').get('Materno'),
                'RazonSocial': result.get('result').get('RazonSocial'),
                'Direccion': result.get('result').get('Direccion'),
                'FechaNac': result.get('result').get('FechaNac')
            }
        else:
            context = {
                'success': result.get('success'),
                'statusMessage': result.get('statusMessage'),
                'result': result.get('result'),
            }
    else:
        result = r.json()
        context = {
            'errors': result.get("errors"),
            'codigo': result.get("codigo"),
        }
    return context


def query_api_free_dni(nro_dni, type_document):
    context = {}
    if type_document == 'DNI':
        url = 'https://dniruc.apisperu.com/api/v1/dni/{}'.format(nro_dni)
        params = {
            'token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJlbWFpbCI6Im1nbC5zdWFyZXoxQGdtYWlsLmNvbSJ9.JAdBpBl_qWivPcmVnEBfUlng8-TbNJZeoWmtVlHRooI',
        }
        r = requests.get(url, params)

        if r.status_code == 200:
            result = r.json()

            context = {
                'status': True,
                'DNI': result.get('dni'),
                'Nombre': html.unescape(result.get('nombres')),
                'Paterno': html.unescape(result.get('apellidoPaterno')),
                'Materno': html.unescape(result.get('apellidoMaterno')),
            }

        else:
            result = r.json()
            context = {
                'status': False,
                'errors': '400 Bad Request',
            }
    return context


def query_apis_quertium_free_dni(nro_dni, type_document):
    context = {}
    if type_document == 'DNI':
        url = 'http://quertium.com/api/v1/reniec/dni/{}'.format(nro_dni)
        params = {
            'token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.MTUxNQ.51Wx68RhZxNtzPZUpoIA61ySrETfmHeCSJNcRdrOL9Y',
        }
        r = requests.get(url, params)

        if r.status_code == 200:
            result = r.json()

            context = {
                'status': True,
                'DNI': result.get('dni'),
                'Nombre': html.unescape(result.get('primerNombre')),
                'Segundo': html.unescape(result.get('segundoNombre')),
                'Paterno': html.unescape(result.get('apellidoPaterno')),
                'Materno': html.unescape(result.get('apellidoMaterno')),
            }

        else:
            result = r.json()
            context = {
                'status': False,
                'errors': '400 Bad Request',
            }
    return context


def query_api_free_optimize_dni(nro_dni, type_document):
    context = {}
    if type_document == 'DNI':
        url = 'https://dni.optimizeperu.com/api/prod/persons/{}'.format(nro_dni)
        headers = {
            'authorization': 'token 48b5594ab9a37a8c3581e5e71ed89c7538a36f11',
        }
        r = requests.get(url, headers=headers)

        if r.status_code == 200:
            result = r.json()
            if len(result) != 0:
                context = {
                    'status': True,
                    'DNI': result.get('dni'),
                    'Nombre': html.unescape(result.get('name')),
                    'Paterno': html.unescape(result.get('first_name')),
                    'Materno': html.unescape(result.get('last_name')),
                }
            else:
                # result = r.json()
                context = {
                    'status': False,
                    'errors': '400 Bad Request',
                }
        else:
            # result = r.json()
            context = {
                'status': False,
                'errors': '400 Bad Request',
            }
    return context


def query_api_free_optimize_ruc(nro_dni, type_document):
    context = {}
    if type_document == 'RUC':
        url = 'https://dni.optimizeperu.com/api/prod/company/{}'.format(nro_dni)
        headers = {
            'authorization': 'token 48b5594ab9a37a8c3581e5e71ed89c7538a36f11',
        }
        r = requests.get(url, headers=headers)

        if r.status_code == 200:
            result = r.json()
            if len(result) != 0:
                context = {
                    'status': True,
                    'ruc': result.get('ruc'),
                    'razonSocial': html.unescape(result.get('razon_social')),
                    'direccion': html.unescape(result.get('domicilio_fiscal')),
                }
            else:
                # result = r.json()
                context = {
                    'status': False,
                    'errors': '400 Bad Request',
                }
        else:
            # result = r.json()
            context = {
                'status': False,
                'errors': '400 Bad Request',
            }
    return context


def query_api_free_ruc(nro_dni, type_document):
    context = {}
    if type_document == 'RUC':
        url = 'https://dniruc.apisperu.com/api/v1/ruc/{}'.format(nro_dni)
        params = {
            'token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJlbWFpbCI6Im1nbC5zdWFyZXoxQGdtYWlsLmNvbSJ9.JAdBpBl_qWivPcmVnEBfUlng8-TbNJZeoWmtVlHRooI',
        }
        r = requests.get(url, params)

        if r.status_code == 200:
            result = r.json()

            context = {
                'status': True,
                'ruc': result.get('ruc'),
                'razonSocial': html.unescape(result.get('razonSocial')),
                'direccion': html.unescape(result.get('direccion')),
            }

        else:
            result = r.json()
            context = {
                'status': False,
                'errors': '400 Bad Request',
            }
    return context


def query_api_amigo(nro_doc, type_document):
    context = {}
    if type_document == 'RUC':
        url = 'https://api.migo.pe/api/v1/ruc'
        params = {
            'token': 'GBk42s6qbluLcE2Jb2CFiainNpnqEDMRlio5nJjWrw5EVL1TrysTGfmdlV7k',
            'ruc': nro_doc,
        }
        headers = {
            "Accept": 'application/json',
        }
        r = requests.post(url, json=params, headers=headers)

        if r.status_code == 200:
            result = r.json()

            context = {
                'status': True,
                'ruc': result.get('ruc'),
                'razonSocial': html.unescape(result.get('nombre_o_razon_social')),
                'direccion': html.unescape(result.get('direccion')),
            }

        else:
            result = r.json()
            context = {
                'status': False,
                'errors': '400 Bad Request',
            }

    return context

# SEND_BILL_NUBEFACT


def query_api_peru(nro_doc, type_document):
    context = {}
    if type_document == 'DNI':
        url = 'https://apiperu.dev/api/dni/{}'.format(nro_doc)
        headers = {
            "Content-Type": 'application/json',
            'authorization': 'Bearer e757671523517ff9a2f015883d85bf9819079664eabf88632c8db9beed1d2e3b',
        }
        r = requests.get(url, headers=headers)

        if r.status_code == 200:
            result = r.json()
            success = result.get('success')
            if success:
                data = result.get('data')

                context = {
                    'success': True,
                    # 'data': result.get('data'),
                    # 'nombres': html.unescape(result.get('data').get('name')),
                    'nombres': data.get('nombres'),
                    'apellido_paterno': data.get('apellido_paterno'),
                    'apellido_materno': data.get('apellido_materno'),
                }
            else:
                context = {
                    'status': False,
                    'errors': result.get('message'),
                }
        else:
            result = r.json()
            context = {
                'status': False,
                'errors': '400 Bad Request',
            }

    if type_document == 'RUC':
        url = 'https://apiperu.dev/api/ruc/{}'.format(nro_doc)
        headers = {
            "Content-Type": 'application/json',
            'authorization': 'Bearer e757671523517ff9a2f015883d85bf9819079664eabf88632c8db9beed1d2e3b',
        }
        r = requests.get(url, headers=headers)

        if r.status_code == 200:
            result = r.json()
            data = result.get('data')

            context = {
                'success': True,
                # 'data': result.get('data'),
                'ruc': data.get('ruc'),
                'direccion': data.get('direccion'),
                'direccion_completa': data.get('direccion_completa'),
                'nombre_o_razon_social': data.get('nombre_o_razon_social'),
            }

        else:
            result = r.json()
            context = {
                'status': False,
                'errors': '400 Bad Request',
            }
    return context


def send_bill_nubefact(order_id, is_demo=False):  # Factura de encomienda
    order_obj = Order.objects.get(id=int(order_id))
    subsidiary = order_obj.subsidiary
    subsidiary_id = subsidiary.id
    serie = order_obj.serial
    n_receipt = order_obj.correlative_sale
    details = OrderDetail.objects.filter(order=order_obj)
    client_obj_sender = Client.objects.filter(orderaction__order=order_obj, orderaction__type='R').first()
    client_first_address = client_obj_sender.clientaddress_set.first()
    client_document = client_obj_sender.clienttype_set.filter(document_type_id='06').first()
    register_date = utc_to_local(order_obj.create_at)
    formatdate = register_date.strftime("%d-%m-%Y")

    items = []
    index = 1
    sub_total = 0
    total = 0
    igv_total = 0
    _base_total_v = 0
    _base_amount_v = 0
    _igv = 0
    for d in details:
        base_total = d.quantity * d.price_unit  # 3 * 10 = 30 | 1 * 20 = 20 ||
        base_amount = base_total / decimal.Decimal(1.1800)  # 100 / 1.18 = 84.75
        igv = base_total - base_amount  # 100 - 84.75 = 15.25
        _base_total_v = _base_total_v + base_total
        _base_amount_v = _base_amount_v + base_amount
        _igv = _base_total_v - _base_amount_v
        sub_total = sub_total + base_amount
        total = total + base_total
        igv_total = igv_total + igv
    item = {
        "item": index,  # index para los detalles
        "unidad_de_medida": 'ZZ',  # NIU viene del nubefact NIU=PRODUCTO
        "codigo": "",  # codigo del producto opcional
        "codigo_producto_sunat": "10000000",  # codigo del producto excel-sunat
        "descripcion": 'TRANPORTE DE CARGA POR CARRETERA A NIVEL REGIONAL Y NACIONAL',  # + d.description,
        "cantidad": '1',  # float(round(d.quantity)),
        "valor_unitario": float(round(_base_amount_v, 2)),  # valor unitario sin IGV
        "precio_unitario": float(round(_base_total_v, 2)),  # float(round(d.price_unit, 2)),
        "descuento": "",
        "subtotal": float(round(_base_amount_v, 2)),  # resultado del valor unitario por la cantidad menos el descuento
        "tipo_de_igv": 1,  # operacion onerosa
        "igv": float(round(_igv, 2)),
        "total": float(round(_base_total_v, 2)),
        "anticipo_regularizacion": 'false',
        "anticipo_documento_serie": "",
        "anticipo_documento_numero": "",
    }
    items.append(item)

    params = {
        "operacion": "generar_comprobante",
        "tipo_de_comprobante": 1,
        "serie": 'F' + serie[1:],
        "numero": n_receipt,
        "sunat_transaction": 1,
        "cliente_tipo_de_documento": 6,
        "cliente_numero_de_documento": client_document.document_number,
        "cliente_denominacion": client_obj_sender.names,
        "cliente_direccion": client_first_address.address,
        "cliente_email": client_obj_sender.email,
        "cliente_email_1": "",
        "cliente_email_2": "",
        "fecha_de_emision": formatdate,
        "fecha_de_vencimiento": "",
        "moneda": 1,
        "tipo_de_cambio": "",
        "porcentaje_de_igv": 18.00,
        "descuento_global": "",
        "total_descuento": "",
        "total_anticipo": "",
        "total_gravada": float(sub_total),
        "total_inafecta": "",
        "total_exonerada": "",
        "total_igv": float(igv_total),
        "total_gratuita": "",
        "total_otros_cargos": "",
        "total": float(total),
        "percepcion_tipo": "",
        "percepcion_base_imponible": "",
        "total_percepcion": "",
        "total_incluido_percepcion": "",
        "total_impuestos_bolsas": "",
        "detraccion": 'false',
        "observaciones": "",
        "documento_que_se_modifica_tipo": "",
        "documento_que_se_modifica_serie": "",
        "documento_que_se_modifica_numero": "",
        "tipo_de_nota_de_credito": "",
        "tipo_de_nota_de_debito": "",
        "enviar_automaticamente_a_la_sunat": 'true',
        "enviar_automaticamente_al_cliente": 'false',
        "condiciones_de_pago": "",
        "medio_de_pago": "",
        "placa_vehiculo": "",
        "orden_compra_servicio": "",
        "formato_de_pdf": "",
        "generado_por_contingencia": "",
        "bienes_region_selva": "",
        "servicios_region_selva": "",
        "items": items,
    }

    url = order_obj.company.url
    authorization = order_obj.company.token

    headers = {
        "Authorization": authorization,
        "Content-Type": 'application/json'
    }
    response = requests.post(url, json=params, headers=headers)

    if response.status_code == 200:
        result = response.json()

        context = {
            'tipo_de_comprobante': result.get("tipo_de_comprobante"),
            'serie': result.get("serie"),
            'numero': result.get("numero"),
            'aceptada_por_sunat': result.get("aceptada_por_sunat"),
            'sunat_description': result.get("sunat_description"),
            'enlace_del_pdf': result.get("enlace_del_pdf"),
            'cadena_para_codigo_qr': result.get("cadena_para_codigo_qr"),
            'codigo_hash': result.get("codigo_hash"),
            'params': params
        }
    else:
        result = response.json()
        context = {
            'errors': result.get("errors"),
            'codigo': result.get("codigo"),
        }
    return context


def send_receipt_nubefact(order_id, is_demo=False):  # boleta de encomienda
    order_obj = Order.objects.get(id=int(order_id))
    subsidiary = order_obj.subsidiary
    subsidiary_id = subsidiary.id
    serie = order_obj.serial
    n_receipt = order_obj.correlative_sale
    details = OrderDetail.objects.filter(order=order_obj)
    client_first_address = ""
    client_obj_sender = Client.objects.filter(orderaction__order=order_obj, orderaction__type='R').first()
    if client_obj_sender.clientaddress_set.first():
        client_first_address = client_obj_sender.clientaddress_set.first()
    # client_document = client_obj_sender.clienttype_set.filter(document_type_id='01').first()
    client_document_type_obj = client_obj_sender.clienttype_set.all().first()
    client_document = client_document_type_obj.document_number
    register_date = utc_to_local(order_obj.create_at)
    formatdate = register_date.strftime("%d-%m-%Y")

    items = []
    index = 1
    sub_total = 0
    total = 0
    igv_total = 0
    _base_total_v = 0
    _base_amount_v = 0
    _igv = 0
    for d in details:
        base_total = d.quantity * d.price_unit  # 3 * 10 = 30 | 1 * 20 = 20 ||
        base_amount = base_total / decimal.Decimal(1.1800)  # 100 / 1.18 = 84.75
        igv = base_total - base_amount  # 100 - 84.75 = 15.25
        _base_total_v = _base_total_v + base_total
        _base_amount_v = _base_amount_v + base_amount
        _igv = _base_total_v - _base_amount_v
        sub_total = sub_total + base_amount
        total = total + base_total
        igv_total = igv_total + igv

        # redondear a un decimal
    item = {
        "item": index,  # index para los detalles
        "unidad_de_medida": 'ZZ',  # NIU viene del nubefact NIU=PRODUCTO
        "codigo": "",  # codigo del producto opcional
        "codigo_producto_sunat": "10000000",  # codigo del producto excel-sunat
        "descripcion": 'TRANPORTE DE CARGA POR CARRETERA A NIVEL REGIONAL Y NACIONAL',  # + d.description,
        "cantidad": '1',  # float(round(d.quantity)),
        "valor_unitario": float(round(_base_amount_v, 2)),  # valor unitario sin IGV
        "precio_unitario": float(round(_base_total_v, 2)),  # float(round(d.price_unit, 2)),
        "descuento": "",
        "subtotal": float(round(_base_amount_v, 2)),  # resultado del valor unitario por la cantidad menos el descuento
        "tipo_de_igv": 1,  # operacion onerosa
        "igv": float(round(_igv, 2)),
        "total": float(round(_base_total_v, 2)),
        "anticipo_regularizacion": 'false',
        "anticipo_documento_serie": "",
        "anticipo_documento_numero": "",
    }
    items.append(item)

    params = {
        "operacion": "generar_comprobante",
        "tipo_de_comprobante": 2,
        "serie": 'B' + serie[1:],
        "numero": n_receipt,
        "sunat_transaction": 1,
        "cliente_tipo_de_documento": int(client_document_type_obj.document_type.id),
        "cliente_numero_de_documento": client_document,
        "cliente_denominacion": client_obj_sender.names,
        "cliente_direccion": client_first_address,
        "cliente_email": client_obj_sender.email,
        "cliente_email_1": "",
        "cliente_email_2": "",
        "fecha_de_emision": formatdate,
        "fecha_de_vencimiento": "",
        "moneda": 1,
        "tipo_de_cambio": "",
        "porcentaje_de_igv": 18.00,
        "descuento_global": "",
        "total_descuento": "",
        "total_anticipo": "",
        "total_gravada": float(round(sub_total, 2)),
        "total_inafecta": "",
        "total_exonerada": "",
        "total_igv": float(round(igv_total, 2)),
        "total_gratuita": "",
        "total_otros_cargos": "",
        "total": float(round(total, 2)),
        "percepcion_tipo": "",
        "percepcion_base_imponible": "",
        "total_percepcion": "",
        "total_incluido_percepcion": "",
        "total_impuestos_bolsas": "",
        "detraccion": 'false',
        "observaciones": "",
        "documento_que_se_modifica_tipo": "",
        "documento_que_se_modifica_serie": "",
        "documento_que_se_modifica_numero": "",
        "tipo_de_nota_de_credito": "",
        "tipo_de_nota_de_debito": "",
        "enviar_automaticamente_a_la_sunat": 'true',
        "enviar_automaticamente_al_cliente": 'false',
        "codigo_unico": "",
        "condiciones_de_pago": "",
        "medio_de_pago": "",
        "placa_vehiculo": "",
        "orden_compra_servicio": "",
        "tabla_personalizada_codigo": "",
        "formato_de_pdf": "",
        "items": items,
    }

    url = order_obj.company.url
    authorization = order_obj.company.token

    headers = {
        "Authorization": authorization,
        "Content-Type": 'application/json'
    }
    response = requests.post(url, json=params, headers=headers)

    if response.status_code == 200:
        result = response.json()

        context = {
            'tipo_de_comprobante': result.get("tipo_de_comprobante"),
            'serie': result.get("serie"),
            'numero': result.get("numero"),
            'aceptada_por_sunat': result.get("aceptada_por_sunat"),
            'sunat_description': result.get("sunat_description"),
            'enlace_del_pdf': result.get("enlace_del_pdf"),
            'cadena_para_codigo_qr': result.get("cadena_para_codigo_qr"),
            'codigo_hash': result.get("codigo_hash"),
            'params': params
        }
    else:
        result = response.json()
        context = {
            'errors': result.get("errors"),
            'codigo': result.get("codigo"),
        }
    return context


def get_correlative_invoice_voucher(order_id, _type):
    result = ''
    serial_sub_com = ''
    cod_type = ''
    serial = ''
    order_obj = Order.objects.get(id=int(order_id))
    document_type = 'B' if _type == 'B' else 'F'
    record = get_serial_record(order_obj.subsidiary, order_obj.company, 'E', document_type)
    if record:
        if _type == 'B':
            cod_type = '2'
            serial_sub_com = record.serial
            serial = record.serial
        else:
            cod_type = '1'
            serial_sub_com = record.serial[-3:] if record.serial else ''
            serial = 'B' + serial_sub_com
            
    order_bill_set = OrderBill.objects.filter(serial=serial, type=cod_type)
    if order_bill_set:
        n_receipt = order_bill_set.last().n_receipt
        new_n_receipt = n_receipt + 1
        return new_n_receipt
    else:
        return 1


def get_correlative(serial_receive, _type):
    serial_send = serial_receive[-3:]
    # c = Subsidiary.objects.filter(id=subsidiary_id).last()
    if _type == 'F':
        cod_type = '1'
        serie = 'F' + serial_send
    else:
        cod_type = '2'
        serie = 'B' + serial_send
    order_bill_set = OrderBill.objects.filter(serial=serie, type=cod_type)
    if order_bill_set:
        n_receipt = order_bill_set.last().n_receipt
        new_n_receipt = n_receipt + 1
        return new_n_receipt
    else:
        return 1


def send_bill_passenger(order_id, is_demo=False):  # Factura boleto de viaje
    order_obj = Order.objects.get(id=int(order_id))
    subsidiary = order_obj.subsidiary
    serie = order_obj.serial
    # route = order_obj.programming_seat.programming.path.name
    # n_receipt = get_correlative_invoice_voucher(order_id, 'B')
    n_receipt = order_obj.correlative_sale
    # n_receipt = get_correlative(order_obj.subsidiary.serial_two, 'F')
    # details = OrderDetail.objects.filter(order=order_obj)
    client_address = ""
    client_business_obj = Client.objects.filter(orderaction__order=order_obj, orderaction__type='E').first()
    client_passenger_obj = Client.objects.filter(orderaction__order=order_obj, orderaction__type='P').first()
    if client_business_obj.clientaddress_set.first():
        client_address = client_business_obj.clientaddress_set.first()
    client_document = client_business_obj.clienttype_set.filter(document_type_id='06').first()
    register_date = utc_to_local(order_obj.create_at)
    formatdate = register_date.strftime("%d-%m-%Y")
    date = order_obj.transfer_date.strftime("%d-%m-%Y")
    items = []
    index = 1
    base_amount = order_obj.total / decimal.Decimal(1.1800)
    igv = order_obj.total - base_amount
    total = base_amount + igv

    user_obj = order_obj.user
    _short_name_origin = order_obj.programming_seat.programming.path.get_first_point().short_name
    _short_name_destiny = order_obj.programming_seat.programming.path.get_last_point().short_name
    # subsidiary_origin_obj = get_subsidiary_by_user(user_obj)
    # company_rotation_obj = user_obj.companyuser.company_rotation
    #
    # subsidiary_company_origin_obj = SubsidiaryCompany.objects.filter(subsidiary=subsidiary_origin_obj,
    #                                                                  company=company_rotation_obj).last()
    # _short_name_origin = subsidiary_company_origin_obj.short_name
    #
    # subsidiary_destiny_obj = order_obj.programming_seat.programming.path.get_last_point()
    # subsidiary_company_destiny_obj = SubsidiaryCompany.objects.filter(subsidiary=subsidiary_destiny_obj,
    #                                                                   company=company_rotation_obj).last()
    #
    # _short_name_destiny = subsidiary_company_destiny_obj.short_name

    item = {
        "item": index,  # index para los detalles
        "unidad_de_medida": 'ZZ',  # NIU viene del nubefact NIU=PRODUCTO
        "codigo": "",  # codigo del producto opcional
        "codigo_producto_sunat": "10000000",  # codigo del producto excel-sunat
        "descripcion": 'SERVICIO DE TRANSPORTE RUTA: ' + _short_name_origin + ' - ' + _short_name_destiny + ' ASIENTO: ' + order_obj.programming_seat.plan_detail.name,
        # + d.description,        "cantidad": '1',  # float(round(d.quantity)),
        "cantidad": '1',  # float(round(d.quantity)),
        "valor_unitario": str(round(decimal.Decimal(total), 2)),  # valor unitario sin IGV
        "precio_unitario": str(round(decimal.Decimal(total), 2)),  # float(round(d.price_unit, 2)),
        "descuento": "",
        "subtotal": str(round(decimal.Decimal(total), 2)),  # resultado del valor unitario por la cantidad menos el descuento
        "tipo_de_igv": 8,  # operacion onerosa
        "igv": 0,
        "total": str(round(decimal.Decimal(total), 2)),
        "anticipo_regularizacion": 'false',
        "anticipo_documento_serie": "",
        "anticipo_documento_numero": "",
    }
    items.append(item)

    params = {
        "operacion": "generar_comprobante",
        "tipo_de_comprobante": 1,
        "serie": 'F' + serie[1:],
        "numero": n_receipt,
        "sunat_transaction": 1,
        "cliente_tipo_de_documento": 6,
        "cliente_numero_de_documento": client_document.document_number,
        "cliente_denominacion": client_business_obj.names,
        "cliente_direccion": client_address.address,
        "cliente_email": client_business_obj.email,
        "cliente_email_1": "",
        "cliente_email_2": "",
        "fecha_de_emision": date,
        "fecha_de_vencimiento": "",
        "moneda": 1,
        "tipo_de_cambio": "",
        "porcentaje_de_igv": 18.00,
        "descuento_global": "",
        "total_descuento": "",
        "total_anticipo": "",
        "total_gravada": "",
        "total_inafecta": "",
        "total_exonerada": str(round(decimal.Decimal(total))),
        "total_igv": "",
        "total_gratuita": "",
        "total_otros_cargos": "",
        "total": str(round(decimal.Decimal(total))),
        "percepcion_tipo": "",
        "percepcion_base_imponible": "",
        "total_percepcion": "",
        "total_incluido_percepcion": "",
        "total_impuestos_bolsas": "",
        "detraccion": 'false',
        "observaciones": "PASAJERO: " + client_passenger_obj.names,
        "documento_que_se_modifica_tipo": "",
        "documento_que_se_modifica_serie": "",
        "documento_que_se_modifica_numero": "",
        "tipo_de_nota_de_credito": "",
        "tipo_de_nota_de_debito": "",
        "enviar_automaticamente_a_la_sunat": 'true',
        "enviar_automaticamente_al_cliente": 'false',
        "codigo_unico": "",
        "condiciones_de_pago": "",
        "medio_de_pago": "",
        "placa_vehiculo": "",
        "orden_compra_servicio": "",
        "tabla_personalizada_codigo": "",
        "formato_de_pdf": "",
        "items": items,
    }

    url = order_obj.company.url
    authorization = order_obj.company.token

    headers = {
        "Authorization": authorization,
        "Content-Type": 'application/json'
    }
    response = requests.post(url, json=params, headers=headers)

    if response.status_code == 200:
        result = response.json()

        context = {
            'tipo_de_comprobante': result.get("tipo_de_comprobante"),
            'serie': result.get("serie"),
            'numero': result.get("numero"),
            'aceptada_por_sunat': result.get("aceptada_por_sunat"),
            'sunat_description': result.get("sunat_description"),
            'enlace_del_pdf': result.get("enlace_del_pdf"),
            'cadena_para_codigo_qr': result.get("cadena_para_codigo_qr"),
            'codigo_hash': result.get("codigo_hash"),
            'params': params
        }
    else:
        result = response.json()
        context = {
            'errors': result.get("errors"),
            'codigo': result.get("codigo"),
        }
    return context


def send_receipt_passenger(order_id, is_demo=False):  # BOLETA boleto de viaje
    order_obj = Order.objects.get(id=int(order_id))
    subsidiary = order_obj.subsidiary
    subsidiary_id = subsidiary.id
    origin = subsidiary.short_name
    serie = order_obj.serial
    # route = order_obj.programming_seat.programming.path.name
    # n_receipt = get_correlative_invoice_voucher(order_id, 'B')
    n_receipt = order_obj.correlative_sale
    client_first_address = ""
    client_passenger_obj = order_obj.client
    client_passenger_type_obj = client_passenger_obj.clienttype_set.all().first()
    if client_passenger_obj.clientaddress_set.first():
        client_first_address = client_passenger_obj.clientaddress_set.first()
    client_document = client_passenger_type_obj.document_number
    register_date = utc_to_local(order_obj.create_at)
    formatdate = register_date.strftime("%d-%m-%Y")

    items = []
    index = 1
    base_amount = order_obj.total / decimal.Decimal(1.1800)
    igv = order_obj.total - base_amount
    total = base_amount + igv

    user_obj = order_obj.user
    _short_name_origin = order_obj.programming_seat.programming.path.get_first_point().short_name
    _short_name_destiny = order_obj.programming_seat.programming.path.get_last_point().short_name
    # subsidiary_origin_obj = get_subsidiary_by_user(user_obj)
    # company_rotation_obj = user_obj.companyuser.company_rotation
    #
    # subsidiary_company_origin_obj = SubsidiaryCompany.objects.filter(subsidiary=subsidiary_origin_obj,
    #                                                                  company=company_rotation_obj).last()
    # _short_name_origin = subsidiary_company_origin_obj.short_name
    #
    # subsidiary_destiny_obj = order_obj.programming_seat.programming.path.get_last_point()
    # subsidiary_company_destiny_obj = SubsidiaryCompany.objects.filter(subsidiary=subsidiary_destiny_obj,
    #                                                                   company=company_rotation_obj).last()
    #
    # _short_name_destiny = subsidiary_company_destiny_obj.short_name

    item = {
        "item": index,  # index para los detalles
        "unidad_de_medida": 'ZZ',  # NIU viene del nubefact NIU=PRODUCTO
        "codigo": "",  # codigo del producto opcional
        "codigo_producto_sunat": "10000000",  # codigo del producto excel-sunat
        "descripcion": 'SERVICIO DE TRANSPORTE RUTA: ' + _short_name_origin + ' - ' + _short_name_destiny + ' ASIENTO: ' + order_obj.programming_seat.plan_detail.name,
        # + d.description,
        "cantidad": '1',  # float(round(d.quantity)),
        "valor_unitario": float(round(base_amount, 2)),  # valor unitario sin IGV
        "precio_unitario": float(round(total, 2)),  # float(round(d.price_unit, 2)),
        "descuento": "",
        "subtotal": float(round(base_amount, 2)),  # resultado del valor unitario por la cantidad menos el descuento
        "tipo_de_igv": 8,  # operacion exonerada
        "igv": 0,
        "total": float(round(total, 2)),
        "anticipo_regularizacion": 'false',
        "anticipo_documento_serie": "",
        "anticipo_documento_numero": "",
    }
    items.append(item)

    params = {
        "operacion": "generar_comprobante",
        "tipo_de_comprobante": 2,
        "serie": serie,
        "numero": n_receipt,
        "sunat_transaction": 1,
        "cliente_tipo_de_documento": int(client_passenger_type_obj.document_type.id),
        "cliente_numero_de_documento": client_document,
        "cliente_denominacion": client_passenger_obj.names,
        "cliente_direccion": client_first_address,
        "cliente_email": client_passenger_obj.email,
        "cliente_email_1": "",
        "cliente_email_2": "",
        "fecha_de_emision": formatdate,
        "fecha_de_vencimiento": "",
        "moneda": 1,
        "tipo_de_cambio": "",
        "porcentaje_de_igv": 18.00,
        "descuento_global": "",
        "total_descuento": "",
        "total_anticipo": "",
        "total_gravada": "",
        "total_inafecta": "",
        "total_exonerada": float(round(total, 2)),
        "total_igv": "",
        "total_gratuita": "",
        "total_otros_cargos": "",
        "total": float(round(total, 2)),
        "percepcion_tipo": "",
        "percepcion_base_imponible": "",
        "total_percepcion": "",
        "total_incluido_percepcion": "",
        "total_impuestos_bolsas": "",
        "detraccion": 'false',
        "observaciones": "",
        "documento_que_se_modifica_tipo": "",
        "documento_que_se_modifica_serie": "",
        "documento_que_se_modifica_numero": "",
        "tipo_de_nota_de_credito": "",
        "tipo_de_nota_de_debito": "",
        "enviar_automaticamente_a_la_sunat": 'true',
        "enviar_automaticamente_al_cliente": 'false',
        "codigo_unico": "",
        "condiciones_de_pago": "",
        "medio_de_pago": "",
        "placa_vehiculo": "",
        "orden_compra_servicio": "",
        "tabla_personalizada_codigo": "",
        "formato_de_pdf": "",
        "items": items,
    }

    url = order_obj.company.url
    authorization = order_obj.company.token

    headers = {
        "Authorization": authorization,
        "Content-Type": 'application/json'
    }
    response = requests.post(url, json=params, headers=headers)
    if response.status_code == 200:
        result = response.json()
        # print(result)

        context = {
            'tipo_de_comprobante': result.get("tipo_de_comprobante"),
            'serie': result.get("serie"),
            'numero': result.get("numero"),
            'aceptada_por_sunat': result.get("aceptada_por_sunat"),
            'sunat_description': result.get("sunat_description"),
            'enlace_del_pdf': result.get("enlace_del_pdf"),
            'cadena_para_codigo_qr': result.get("cadena_para_codigo_qr"),
            'codigo_hash': result.get("codigo_hash"),
            'params': params
        }
    else:
        result = response.json()
        context = {
            'errors': result.get("errors"),
            'codigo': result.get("codigo"),
        }
    return context


def send_voided_receipt(order_id, reason="ERROR DEL SISTEMA", is_demo=False):
    order_obj = Order.objects.get(id=int(order_id))
    order_bill_obj = OrderBill.objects.get(order=order_obj)
    serial = order_bill_obj.serial
    n_receipt = order_bill_obj.n_receipt

    params = {
        "operacion": "generar_anulacion",
        "tipo_de_comprobante": 2,
        "serie": serial,
        "numero": n_receipt,
        "motivo": reason,
        "codigo_unico": "",

    }

    if is_demo:
        _url = 'https://www.pse.pe/api/v1/91900d0da6424013b4cf9a8c4fdf8846b67addc7bbcb41328e137a9c93479e26'
        _authorization = 'eyJhbGciOiJIUzI1NiJ9.IjY1NTJmNDE1NGZhOTQ5ZGU4MjFjYTIwYmE4ZWM4ZDg1MzAxMDRlZmNlNGNjNDcyMGI0ZDU2MGE5ZGQwOGNhMmQi.GNzvsfMsCITQ-xwfK-yl_TQwcLd4F-264wYK19frMXE'
    else:
        _url = 'https://www.pse.pe/api/v1/830bd70339bd455fb7a50e99a940f9b03abaa578372f469b8833e45e89c1ee0f'
        _authorization = 'eyJhbGciOiJIUzI1NiJ9.Ijk4Mjk5MjBkZWE3NTRmNmQ5Y2RlNzY3YmY2ODg1OTYxZjkxMDczZDM2M2U2NGUyNTgyZDMzMTVkNmIxNDFkMmUi.t6on5vD56gMyJPH5H7PwHElb7u5qteJgFGuVhLYukXM'

    url = _url
    headers = {
        "Authorization": _authorization,
        "Content-Type": 'application/json'
    }
    response = requests.post(url, json=params, headers=headers)

    if response.status_code == 200:
        result = response.json()

        context = {
            'tipo_de_comprobante': result.get("tipo_de_comprobante"),
            'serie': result.get("serie"),
            'numero': result.get("numero"),
            'aceptada_por_sunat': result.get("aceptada_por_sunat"),
            'sunat_description': result.get("sunat_description"),
            'enlace_del_pdf': result.get("enlace_del_pdf"),
            'cadena_para_codigo_qr': result.get("cadena_para_codigo_qr"),
            'codigo_hash': result.get("codigo_hash"),
            'params': params
        }
    else:
        result = response.json()
        context = {
            'errors': result.get("errors"),
            'codigo': result.get("codigo"),
        }
    return context


def get_company(ruc=''):
    owner_obj = Owner.objects.get(ruc=ruc.strip())
    _url = ''
    _token = ''
    if ruc == '20539342348':  # SUPER
        _url = 'https://api.pse.pe/api/v1/bc4d4288a53c48adbd93d1af36e43280e5f1688fc5824cf6b13fc620b6eedc71'
        _token = 'eyJhbGciOiJIUzI1NiJ9.IjllM2U0ODE2ZDVjNjRiMTQ4OTRhM2Y0YTJiYWYzYzk2NGNjOTE3NjEzMjQ3NGQ4OGI5ODViYjQyMTk4OTdmMGIi.KyNlXrz7V3ZBDyb_G13_Kmylxu2hdCX2EpN6FEuBLWo'
    elif ruc == '20602745393':  # PLUS
        _url = 'https://api.pse.pe/api/v1/e35096465caa4ad786ad9271d6f6d26c079f5065cfe145578e9e74add07c9293'
        _token = 'eyJhbGciOiJIUzI1NiJ9.ImE1NzUwOGVkMTAwMjQ3Yzc5MDc5ZGM4MTViMWI1ODYwM2EzNDQyMTRhYTQ0NGFjYmE4ZDRhZmRmN2JjZTEzNWMi.NXWA-kXHVGZZdtokv78G3lU3o2oyg62zWG6zfB_y1c8'
    elif ruc == '20600787421':  # E&E
        _url = 'https://api.pse.pe/api/v1/907ab754c592407c818ade9a6b37a0291c636223e3444627ae888c179be40802'
        _token = 'eyJhbGciOiJIUzI1NiJ9.ImIxYjBhYjcxNzJjNTQwOTg5OTNkNTA4YmM4NzMxNTNmNjliZDI1NjQzMzNhNDViNDliOTU1MzlmZjZhZGViNTki.7JeIgRsfUkzNV5zW6FTPmjuZkKcSenDWy5h2HZRUVV8'
    context = {
        'url': _url,
        'token': _token,
        'address': owner_obj.address,
    }
    return context


def query_api_facturacioncloud(nro_doc, type_document):
    context = {}
    url = {}
    if type_document == 'DNI':
        url = 'http://www.facturaelectronicape.com/facturacion/controller/ws_consulta_rucdni_v2.php?usuario' \
              '=20498189637&password=marvisur.123.&documento=DNI&nro_documento=' + nro_doc
    elif type_document == 'RUC':
        url = 'http://www.facturaelectronicape.com/facturacion/controller/ws_consulta_rucdni_v2.php?usuario' \
              '=20498189637&password=marvisur.123.&documento=RUC&nro_documento=' + nro_doc

    headers = {
        "Content-Type": 'application/json'
    }
    try:
        response = requests.post(url, headers=headers, timeout=2.5)
        # print(response)
        # print(response.status_code)
        if response.status_code == 200:
            result = response.json()

            context = {
                'success': result.get("success"),
                'statusMessage': result.get("statusMessage"),
                'result': result.get('result'),
                'DNI': result.get('result').get('DNI'),
                'Nombre': result.get('result').get('Nombre'),
                'Paterno': result.get('result').get('Paterno'),
                'Materno': result.get('result').get('Materno'),
                'ruc': result.get('result').get('RUC'),
                'razonSocial': result.get('result').get('RazonSocial'),
                'direccion': result.get('result').get('Direccion'),
                'Estado': result.get('result').get('Estado'),
            }
        else:
            result = response.status_code
            context = {
                'errors': True
            }
    # except requests.exceptions.RequestException as e:
    #     context = {
    #         'errors': True
    #     }
    except requests.ReadTimeout:
        print("READ TIME OUT FACTURACION CLOUD")

        context = {
            'errors': True
        }
    return context


def query_apis_net_dni_ruc(nro_doc, type_document):
    context = {}
    url = {}
    if type_document == 'DNI':
        url = 'https://api.decolecta.com/v1/reniec/dni?numero=' + nro_doc

    if type_document == 'RUC':
        url = 'https://api.decolecta.com/v1/sunat/ruc?numero=' + nro_doc

    headers = {
        "Content-Type": 'application/json',
        "Authorization": 'Bearer apis-token-3244.1KWBKUSrgYq6HNht68arg8LNsId9vVLm'
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            result = response.json()
            # print(result)
            if type_document == 'DNI':
                context = {
                    # 'nombre': result.get("nombre"),
                    'fullName': result.get("full_name"),
                    # 'tipoDocumento': result.get("tipoDocumento"),
                    'numeroDocumento': result.get('document_number'),
                    'apellidoPaterno': result.get('first_last_name'),
                    'apellidoMaterno': result.get('second_last_name'),
                    'nombres': result.get('first_name'),
                    'direccion': result.get('direccion'),
                }
            else:
                context = {
                    'razonSocial': result.get("razon_social"),
                    'numeroDocumento': result.get('numero_documento'),
                    'direccion': result.get('direccion'),
                }
        else:
            result = response.status_code
            context = {
                'errors': True
            }
        # response = requests.get(url, headers=headers, timeout=2.5)
        #
        # if response.status_code == 200:
        #     result = response.json()
        #
        #     context = {
        #         'nombre': result.get("nombre"),
        #         'tipoDocumento': result.get("tipoDocumento"),
        #         'numeroDocumento': result.get('numeroDocumento'),
        #         'apellidoPaterno': result.get('apellidoPaterno'),
        #         'apellidoMaterno': result.get('apellidoMaterno'),
        #         'nombres': result.get('nombres'),
        #         'direccion': result.get('direccion'),
        #     }
        # else:
        #     result = response.status_code
        #     context = {
        #         'errors': True
        #     }

    except requests.ReadTimeout:
        print("READ TIME OUT APINET")
        context = {
            'errors': True
        }

    return context


def send_cancel_bill_nubefact(order_id, _motive):
    params = {}
    order_bill_obj = OrderBill.objects.get(order_id=int(order_id))
    order_obj = Order.objects.get(id=int(order_id))
    if order_bill_obj.type == '1':
        params = {
            "operacion": "generar_anulacion",
            "tipo_de_comprobante": "1",
            "serie": order_bill_obj.serial,
            "numero": order_bill_obj.n_receipt,
            "motivo": _motive,
            "codigo_unico": ""
        }
    elif order_bill_obj.type == '2':
        params = {
            "operacion": "generar_anulacion",
            "tipo_de_comprobante": "2",
            "serie": order_bill_obj.serial,
            "numero": order_bill_obj.n_receipt,
            "motivo": _motive,
            "codigo_unico": ""
        }

    url = order_obj.company.url
    authorization = order_obj.company.token

    headers = {
        "Authorization": authorization,
        "Content-Type": 'application/json'
    }
    response = requests.post(url, json=params, headers=headers)

    if response.status_code == 200:
        result = response.json()

        context = {
            'enlace': result.get("enlace"),
            'sunat_ticket_numero': result.get("sunat_ticket_numero"),
            'aceptada_por_sunat': result.get("aceptada_por_sunat"),
            'enlace_del_pdf': result.get("enlace_del_pdf"),
            'enlace_del_xml': result.get("enlace_del_xml"),
            'key': result.get("key"),
        }
    else:
        result = response.json()
        context = {
            'errors': result.get("errors"),
            'codigo': result.get("codigo"),
        }
    return context
