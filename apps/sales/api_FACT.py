import requests

from .format_to_dates import utc_to_local
from .models import *
from apps.users.user_helpers import get_subsidiary_by_user

GRAPHQL_URL = "https://ng.tuf4ctur4.net.pe/graphql"
# GRAPHQL_URL = "http://192.168.1.80:9050/graphql"

tokens = {
    "20616147375": "gAAAAABqTA0cJ5usLHk_6QxdRNsphXDcm_utYdSdMFagg2k2ww_-xFAaV7JoZw7b3_NpXxO25lXfxYUFR4Yewkm_zpFDTCkwzA==",
}


def send_bill_commodity_fact(request, order_id):  # FACTURA DE ENCOMIENDA 4FACT
    order_obj = Order.objects.get(id=int(order_id))
    serial = order_obj.serial
    correlative = order_obj.correlative_sale
    details = OrderDetail.objects.filter(order=order_obj)
    client_obj_sender = Client.objects.filter(orderaction__order=order_obj, orderaction__type='R').first()
    client_obj_sender_name = str(client_obj_sender.names).replace('"', "'")
    client_first_address = client_obj_sender.clientaddress_set.first()
    client_first_address_address = str(client_first_address).replace('"', "'")
    client_document = client_obj_sender.clienttype_set.filter(document_type_id='06').first()
    register_date = utc_to_local(order_obj.create_at)
    formatdate = order_obj.traslate_date.strftime("%Y-%m-%d")
    hour_date = register_date.strftime("%H:%M:%S")

    items = []
    index = 1
    sub_total = 0
    total = 0
    igv_total = 0
    for d in details:
        base_total = d.quantity * d.price_unit
        base_amount = base_total / decimal.Decimal(1.1800)
        igv = base_total - base_amount
        qty = d.quantity or decimal.Decimal(0)
        precio_base_unitario = (base_amount / qty) if qty else decimal.Decimal(0)
        sub_total = sub_total + base_amount
        total = total + base_total
        igv_total = igv_total + igv

        item = {
            "index": str(index),
            "codigoUnidad": "ZZ",
            "codigoProducto": "0000",
            "codigoSunat": "10000000",
            "producto": "TRANSPORTE DE CARGA POR CARRETERA A NIVEL REGIONAL Y NACIONAL",
            "cantidad": float(d.quantity),
            "precioBase": float(round(precio_base_unitario, 6)),
            "tipoIgvCodigo": "10"
        }
        items.append(item)
        index += 1

    items_graphql = ", ".join(
        f"""{{  
               producto: "{item['producto']}", 
               cantidad: {item['cantidad']}, 
               precioBase: {item['precioBase']}, 
               codigoSunat: "{item['codigoSunat']}",
               codigoProducto: "{item['codigoProducto']}",
               codigoUnidad: "{item['codigoUnidad']}",                                            
               tipoIgvCodigo: "{item['tipoIgvCodigo']}" 
        }}"""
        for item in items
    )

    items_graphql = f"[{items_graphql}]"

    graphql_query = f"""
    mutation RegisterSale  {{
        registerSale(            
            cliente: {{
                razonSocialNombres: "{client_obj_sender_name}",
                numeroDocumento: "{client_document.document_number}",
                codigoTipoEntidad: 6,
                clienteDireccion: "{client_first_address_address}"
            }},
            venta: {{
                serie: "F{serial[1:]}",
                numero: "{int(correlative)}",
                fechaEmision: "{formatdate}",
                horaEmision: "{hour_date}",
                fechaVencimiento: "",
                monedaId: 1,                
                formaPagoId: 1,
                totalGravada: {float(sub_total)},
                totalDescuentoGlobalPorcentaje: 0,
                totalDescuentoGlobal: 0,
                totalIgv: {float(igv_total)},
                totalExonerada: 0,
                totalInafecta: 0,
                totalImporte: {float(round(total, 2))},
                totalAPagar: {float(round(total, 2))},
                tipoDocumentoCodigo: "01",
                nota: " "
            }},
            items: {items_graphql}
        ) {{
            message
            success
            operationId
        }}
    }}
    """
    # print(graphql_query)

    token = tokens.get(order_obj.company.ruc, "ID no encontrado")

    HEADERS = {
        "Content-Type": "application/json",
        "token": token
    }

    try:
        response = requests.post(GRAPHQL_URL, json={"query": graphql_query}, headers=HEADERS)
        response.raise_for_status()

        result = response.json()

        success = result.get("data", {}).get("registerSale", {}).get("success")

        if success:
            return {
                "success": success,
                "message": result.get("data", {}).get("registerSale", {}).get("message"),
                "operationId": result.get("data", {}).get("registerSale", {}).get("operationId"),
                "serie": order_obj.serial,
                "numero": order_obj.correlative_sale,
                "tipo_de_comprobante": "1",
            }
        else:
            # Maneja el caso en que la operación no fue exitosa
            return {
                "success": False,
                "message": "La operación no fue exitosa",
            }

    except requests.exceptions.RequestException as e:
        return {"error": f"Error en la solicitud: {str(e)}"}
    except ValueError:
        return {"error": "La respuesta no es un JSON válido"}


def send_receipt_commodity_fact(request, order_id):  # BOLETA DE ENCOMIENDA 4FACT
    order_obj = Order.objects.get(id=int(order_id))
    subsidiary = order_obj.subsidiary
    subsidiary_id = subsidiary.id
    # serie = subsidiary.serial
    serial = order_obj.serial
    # n_receipt = get_correlative(order_obj, 'B')
    correlative = order_obj.correlative_sale
    details = OrderDetail.objects.filter(order=order_obj)
    client_first_address = ""
    client_obj_sender = Client.objects.filter(orderaction__order=order_obj, orderaction__type='R').first()
    if client_obj_sender.clientaddress_set.first():
        client_first_address = client_obj_sender.clientaddress_set.first()
    # client_document = client_obj_sender.clienttype_set.filter(document_type_id='01').first()
    client_document_type_obj = client_obj_sender.clienttype_set.all().first()
    client_document = client_document_type_obj.document_number
    register_date = utc_to_local(order_obj.create_at)
    formatdate = register_date.strftime("%Y-%m-%d")
    hour_date = register_date.strftime("%H:%M:%S")

    items = []
    index = 1
    sub_total = 0
    total = 0
    igv_total = 0
    for d in details:
        base_total = d.quantity * d.price_unit
        base_amount = base_total / decimal.Decimal(1.1800)
        igv = base_total - base_amount
        qty = d.quantity or decimal.Decimal(0)
        precio_base_unitario = (base_amount / qty) if qty else decimal.Decimal(0)
        sub_total = sub_total + base_amount
        total = total + base_total
        igv_total = igv_total + igv

        item = {
            "index": str(index),
            "codigoUnidad": "ZZ",
            "codigoProducto": "0000",
            "codigoSunat": "10000000",
            "producto": "TRANSPORTE DE CARGA POR CARRETERA A NIVEL REGIONAL Y NACIONAL",
            "cantidad": float(d.quantity),
            "precioBase": float(round(precio_base_unitario, 6)),
            "tipoIgvCodigo": "10"
        }
        items.append(item)
        index += 1

    items_graphql = ", ".join(
        f"""{{                     
                codigoUnidad: "{item['codigoUnidad']}", 
                codigoProducto: "{item['codigoProducto']}", 
                codigoSunat: "{item['codigoSunat']}", 
                producto: "{item['producto']}", 
                cantidad: {item['cantidad']}, 
                precioBase: {item['precioBase']}, 
                tipoIgvCodigo: "{item['tipoIgvCodigo']}" 
            }}"""
        for item in items
    )

    graphql_query = f"""
        mutation RegisterSale  {{
            registerSale(            
                cliente: {{
                    razonSocialNombres: "{client_obj_sender.names}",
                    numeroDocumento: "{client_document}",
                    codigoTipoEntidad: {int(client_document_type_obj.document_type.id)},
                    clienteDireccion: "{client_first_address}"
                }},
                venta: {{
                    serie: "B{serial[1:]}",
                    numero: "{int(correlative)}",
                    fechaEmision: "{formatdate}",
                    horaEmision: "{hour_date}",
                    fechaVencimiento: "",
                    monedaId: 1,                
                    formaPagoId: 1,
                    totalGravada: {float(sub_total)},
                    totalDescuentoGlobalPorcentaje: 0,
                    totalDescuentoGlobal: 0,
                    totalIgv: {float(igv_total)},
                    totalExonerada: 0,
                    totalInafecta: 0,
                    totalImporte: {float(round(total, 2))},
                    totalAPagar: {float(round(total, 2))},
                    tipoDocumentoCodigo: "03",
                    nota: " "
                }},
                items: {items_graphql}
            ) {{
                message
                success
                operationId
            }}
        }}
        """

    # print(graphql_query)

    token = tokens.get(order_obj.company.ruc, "ID no encontrado")

    HEADERS = {
        "Content-Type": "application/json",
        "token": token
    }

    try:
        response = requests.post(GRAPHQL_URL, json={"query": graphql_query}, headers=HEADERS)
        response.raise_for_status()

        result = response.json()

        success = result.get("data", {}).get("registerSale", {}).get("success")

        if success:
            return {
                "success": success,
                "message": result.get("data", {}).get("registerSale", {}).get("message"),
                "operationId": result.get("data", {}).get("registerSale", {}).get("operationId"),
                "serie": order_obj.serial,
                "numero": order_obj.correlative_sale,
                "tipo_de_comprobante": "2",
            }
        else:
            # Maneja el caso en que la operación no fue exitosa
            return {
                "success": False,
                "message": "La operación no fue exitosa",
            }

    except requests.exceptions.RequestException as e:
        return {"error": f"Error en la solicitud: {str(e)}"}
    except ValueError:
        return {"error": "La respuesta no es un JSON válido"}


def annul_invoice(order_id):
    order_bill_obj = OrderBill.objects.get(order_id=int(order_id))
    correlative = order_bill_obj.n_receipt
    serial = order_bill_obj.serial

    variables = {
        "correlative": correlative,
        "serial": serial
    }

    mutation = """
    mutation AnnulInvoice($correlative: Int!, $serial: String!) {
        annulInvoice(correlative: $correlative, serial: $serial) {
            message
            success
        }
    }
    """

    token = tokens.get(order_bill_obj.order.company.ruc, "ID no encontrado")

    HEADERS = {
        "Content-Type": "application/json",
        "token": token
    }

    # print("Enviando mutación GraphQL:")
    # print("Query:", mutation)
    # print("Variables:", variables)
    # print("Headers:", HEADERS)

    try:
        response = requests.post(
            GRAPHQL_URL,
            json={"query": mutation, "variables": variables},
            headers=HEADERS
        )
        response.raise_for_status()

        result = response.json()

        data = result.get("data", {}).get("annulInvoice")

        if data and data.get("success"):
            return {
                "success": True,
                "message": data.get("message"),
            }
        else:
            return {
                "success": False,
                "message": data.get("message") if data else "No se obtuvo respuesta del servidor.",
            }

    except requests.exceptions.RequestException as e:
        return {"success": False, "message": f"Error en la solicitud: {str(e)}"}
    except ValueError:
        return {"success": False, "message": "La respuesta no es un JSON válido"}


def get_sale_by_id(pk):

    HEADERS = {
        "Content-Type": "application/json",
    }

    query = """
    query GetSale($pk: ID!) {
      getSaleById(pk: $pk) {
        linkXml
        linkCdr
      }
    }
    """

    variables = {"pk": str(pk)}


    try:
        response = requests.post(
            GRAPHQL_URL,
            json={"query": query, "variables": variables},
            headers=HEADERS
        )

        # print("Response:", response.status_code)
        # print("Response Text:", response.text)

        response.raise_for_status()

        result = response.json()

        data = result.get("data", {}).get("getSaleById")

        if data:
            return {
                "success": True,
                "linkXml": data.get("linkXml"),
                "linkCdr": data.get("linkCdr"),
            }
        else:
            return {
                "success": False,
                "message": "No se encontró información para el ID proporcionado.",
            }

    except requests.RequestException as e:
        return {
            "success": False,
            "message": f"Error de red o servidor: {str(e)}"
        }