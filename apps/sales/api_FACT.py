import requests

from .format_to_dates import utc_to_local
from .models import *
from apps.users.user_helpers import get_subsidiary_by_user

GRAPHQL_URL = "https://ng.tuf4ctur4.net.pe/graphql"
# GRAPHQL_URL = "http://192.168.1.80:9050/graphql"

# ---------------------------------------------------------------------------
# MODO PRUEBA LOCAL (no envía a 4FACT)
# ---------------------------------------------------------------------------
# Pruebas locales  -> FACT_DRY_RUN = True
# Producción       -> FACT_DRY_RUN = False
# ---------------------------------------------------------------------------
FACT_DRY_RUN = False


tokens = {
    "20559330818": "gAAAAABqTA0cJ5usLHk_6QxdRNsphXDcm_utYdSdMFagg2k2ww_-xFAaV7JoZw7b3_NpXxO25lXfxYUFR4Yewkm_zpFDTCkwzA==",
}


def _fact_dry_run_response(label, payload, success_data):
    """
    Imprime el payload GraphQL y simula respuesta exitosa.
    Usado solo cuando FACT_DRY_RUN = True.
    """
    print("=" * 72)
    print(f"[FACT_DRY_RUN] {label} — NO se envió a 4FACT")
    print("-" * 72)
    if isinstance(payload, dict):
        for key, value in payload.items():
            print(f"{key}:")
            print(value)
            print("-" * 40)
    else:
        print(payload)
    print("=" * 72)
    result = dict(success_data)
    result.setdefault("success", True)
    result.setdefault("message", f"[DRY RUN] {label} simulado correctamente")
    result.setdefault("dry_run", True)
    if "operationId" not in result:
        result["operationId"] = 999999
    return result


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

    # --- MODO PRUEBA: comentar este bloque al pasar a producción (o poner FACT_DRY_RUN = False) ---
    if FACT_DRY_RUN:
        return _fact_dry_run_response(
            "send_bill_commodity_fact (FACTURA)",
            graphql_query,
            {
                "serie": order_obj.serial,
                "numero": order_obj.correlative_sale,
                "tipo_de_comprobante": "1",
            },
        )
    # --- FIN MODO PRUEBA ---

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

    # --- MODO PRUEBA: comentar este bloque al pasar a producción (o poner FACT_DRY_RUN = False) ---
    if FACT_DRY_RUN:
        return _fact_dry_run_response(
            "send_receipt_commodity_fact (BOLETA)",
            graphql_query,
            {
                "serie": order_obj.serial,
                "numero": order_obj.correlative_sale,
                "tipo_de_comprobante": "2",
            },
        )
    # --- FIN MODO PRUEBA ---

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

    # --- MODO PRUEBA: comentar este bloque al pasar a producción (o poner FACT_DRY_RUN = False) ---
    if FACT_DRY_RUN:
        return _fact_dry_run_response(
            "annul_invoice (ANULACIÓN)",
            {"mutation": mutation, "variables": variables},
            {"message": "[DRY RUN] Anulación simulada correctamente"},
        )
    # --- FIN MODO PRUEBA ---

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

    # --- MODO PRUEBA: comentar este bloque al pasar a producción (o poner FACT_DRY_RUN = False) ---
    if FACT_DRY_RUN:
        return _fact_dry_run_response(
            "get_sale_by_id",
            {"query": query, "variables": variables},
            {
                "linkXml": "https://example.local/dry-run.xml",
                "linkCdr": "https://example.local/dry-run.cdr",
            },
        )
    # --- FIN MODO PRUEBA ---

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


def _gql_escape(value):
    """Escapa texto para insertarlo en literales GraphQL."""
    return str(value or "").replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").replace("\r", "")


def _client_document_info(client_obj):
    """Devuelve (codigo_tipo_entidad_int, numero_documento) del cliente."""
    if not client_obj:
        return None, ""
    client_type = client_obj.clienttype_set.select_related("document_type").first()
    if not client_type or not client_type.document_number:
        return None, ""
    doc_id = str(client_type.document_type_id or "").strip()
    # DocumentType.id suele ser '01', '06', etc. (SUNAT: 1=DNI, 6=RUC)
    try:
        codigo = int(doc_id)
    except (TypeError, ValueError):
        sunat = getattr(client_type.document_type, "sunat_code", None) if client_type.document_type else None
        try:
            codigo = int(sunat) if sunat is not None else None
        except (TypeError, ValueError):
            codigo = None
    return codigo, str(client_type.document_number).strip()


def _client_address_info(client_obj):
    """Devuelve (direccion, ubigeo) desde la última dirección del cliente."""
    if not client_obj:
        return "", ""
    address_obj = client_obj.clientaddress_set.select_related("district").last()
    if not address_obj:
        return "", ""
    address = (address_obj.address or "").strip()
    ubigeo = ""
    if address_obj.district_id and address_obj.district:
        ubigeo = (address_obj.district.code or "").strip()
    return address, ubigeo


def _route_point(order_obj, route_type):
    """Punto origen/destino desde OrderRoute: (dirección completa, dirección, ubigeo)."""
    route = order_obj.orderroute_set.filter(type=route_type).select_related("subsidiary").last()
    if not route or not route.subsidiary_id:
        return "", "", ""
    sub = route.subsidiary
    label = (sub.short_name or sub.name or "").strip()
    address = (sub.address or "").strip()
    ubigeo = (sub.ubigeo or "").strip()
    full_address = f"{label} - {address}".strip(" -") if label or address else ""
    return full_address, address, ubigeo


def _driver_from_employee_name(full_name):
    """Busca conductor/empleado por nombre y retorna (nombre, licencia)."""
    from apps.comercial.models import Driver
    from apps.users.models import Employee

    if not full_name:
        return "", ""
    name = str(full_name).strip()
    name_upper = name.upper()
    for driver in Driver.objects.filter(is_active=True):
        if driver.full_name.upper() == name_upper:
            return driver.full_name, (driver.license_number or "").strip()
    token = name.split()[0] if name else ""
    if token:
        driver = Driver.objects.filter(names__icontains=token, is_active=True).first()
        if driver:
            return driver.full_name, (driver.license_number or "").strip()
    first = name.split(",")[0].strip()
    employee = None
    if token:
        employee = Employee.objects.filter(names__icontains=token, is_enabled=True).first()
    if not employee and len(first) >= 3:
        employee = Employee.objects.filter(names__icontains=first[:20], is_enabled=True).first()
    if employee:
        return employee.full_name or name, (employee.n_license or "").strip()
    return name, ""


def send_guide_fact(guide_id):
    """
    Envía Guía de Remisión Remitente (GRE) a 4FACT vía mutation registerGuide.
    guide_id: pk de apps.comercial.models.SenderRemissionGuide
    """
    from apps.comercial.models import SenderRemissionGuide

    try:
        guide_obj = SenderRemissionGuide.objects.select_related(
            "order",
            "order__company",
            "order__subsidiary",
            "order__client",
            "programming",
            "programming__truck",
            "carrier_guide",
            "carrier_guide__truck",
            "carrier_guide__company",
            "subsidiary",
            "company",
        ).get(id=int(guide_id))
    except (SenderRemissionGuide.DoesNotExist, TypeError, ValueError):
        return {"success": False, "message": "Guía de remisión remitente no encontrada."}

    order_obj = guide_obj.order
    if not order_obj:
        return {"success": False, "message": "La guía no tiene una orden asociada."}

    errors = []

    if guide_obj.status != "I":
        errors.append("La guía debe estar emitida (estado I) para enviarse a facturación.")
    if not (guide_obj.serial or "").strip():
        errors.append("La guía no tiene serie.")
    if not (guide_obj.correlative or "").strip():
        errors.append("La guía no tiene correlativo.")
    if not guide_obj.emit_date:
        errors.append("La guía no tiene fecha de emisión.")
    if not guide_obj.transfer_start_date:
        errors.append("La guía no tiene fecha de inicio de traslado.")
    if not guide_obj.total_weight or guide_obj.total_weight <= 0:
        errors.append("El peso bruto total debe ser mayor a 0.")
    if not guide_obj.quantity_packages or guide_obj.quantity_packages <= 0:
        errors.append("La cantidad de bultos debe ser mayor a 0.")

    company_obj = guide_obj.company or order_obj.company
    if not company_obj or not (company_obj.ruc or "").strip():
        errors.append("No se encontró la empresa (RUC) asociada a la guía.")

    # Destinatario (GRE remitente): OrderAction tipo D; fallback a cliente de la orden.
    receiver_action = order_obj.orderaction_set.filter(type="D").select_related(
        "client", "order_addressee"
    ).last()
    client_obj = None
    if receiver_action and receiver_action.client_id:
        client_obj = receiver_action.client
    elif order_obj.client_id:
        client_obj = order_obj.client

    client_type_document, client_nro_document = _client_document_info(client_obj)
    client_names = ""
    client_phone = ""
    if client_obj:
        client_names = (client_obj.names or "").strip()
        client_phone = (client_obj.phone or "").strip()
    elif receiver_action and receiver_action.order_addressee_id:
        client_names = (receiver_action.order_addressee.names or "").strip()

    client_address, client_ubigeo = _client_address_info(client_obj)

    if not client_names:
        errors.append("Falta el nombre del destinatario.")
    if not client_nro_document:
        errors.append("Falta el documento del destinatario.")
    if client_type_document is None:
        errors.append("Falta el tipo de documento del destinatario.")

    # Puntos de partida / llegada
    origin_full, origin_address, origin_ubigeo = _route_point(order_obj, "O")
    destiny_full, destiny_address, arrival_ubigeo = _route_point(order_obj, "D")
    try:
        encomienda = order_obj.encomienda
    except ObjectDoesNotExist:
        encomienda = None
    if encomienda:
        if not origin_address and encomienda.office_origin_id:
            origin_sub = encomienda.office_origin
            origin_address = (origin_sub.address or "").strip()
            origin_label = (origin_sub.short_name or origin_sub.name or "").strip()
            origin_full = f"{origin_label} - {origin_address}".strip(" -")
            if not origin_ubigeo:
                origin_ubigeo = (origin_sub.ubigeo or "").strip()
        if not destiny_address and encomienda.office_destination_id:
            destiny_sub = encomienda.office_destination
            destiny_address = (destiny_sub.address or "").strip()
            destiny_label = (destiny_sub.short_name or destiny_sub.name or "").strip()
            destiny_full = f"{destiny_label} - {destiny_address}".strip(" -")
            if not arrival_ubigeo:
                arrival_ubigeo = (destiny_sub.ubigeo or "").strip()
        if encomienda.type_guide == "R" and (encomienda.address_delivery or "").strip():
            destiny_full = (encomienda.address_delivery or "").strip()
            destiny_address = destiny_full

    # Fallback: ubigeo desde dirección de clientes si la sede aún no lo tiene
    if not origin_ubigeo:
        remitter_action = order_obj.orderaction_set.filter(type="R").select_related("client").last()
        if remitter_action and remitter_action.client_id:
            _, origin_ubigeo = _client_address_info(remitter_action.client)
    if not arrival_ubigeo:
        arrival_ubigeo = client_ubigeo

    if not origin_full and not origin_address:
        errors.append("Falta la dirección del punto de partida (ruta origen).")
    if not destiny_full and not destiny_address:
        errors.append("Falta la dirección del punto de llegada (ruta destino).")
    if not origin_ubigeo:
        errors.append(
            "Falta el ubigeo del punto de partida "
            "(configurar ubigeo en la sede de origen)."
        )
    if not arrival_ubigeo:
        errors.append(
            "Falta el ubigeo del punto de llegada "
            "(configurar ubigeo en la sede de destino)."
        )

    # Modalidad privada / motivo venta (alineado al PDF de GRE remitente)
    guide_mode = "02"
    guide_reason = "01"

    carrier_guide = guide_obj.carrier_guide
    programming = guide_obj.programming
    truck_obj = None
    driver_name = ""
    driver_license = ""

    if carrier_guide:
        truck_obj = carrier_guide.truck
        driver_name = (carrier_guide.driver_name or "").strip()
        driver_license = (carrier_guide.driver_license or "").strip()
    if not truck_obj and programming:
        truck_obj = programming.truck
    if not driver_name and programming:
        driver_name = (programming.support_pilot or "").strip()
    if not driver_license and driver_name:
        resolved_name, resolved_license = _driver_from_employee_name(driver_name)
        driver_name = resolved_name or driver_name
        driver_license = resolved_license

    truck_plate = ((truck_obj.license_plate if truck_obj else "") or "").strip().upper()

    transport_company = (
        (carrier_guide.company if carrier_guide and carrier_guide.company_id else None)
        or company_obj
    )
    carrier_ruc = (transport_company.ruc if transport_company else "") or ""
    carrier_names = (transport_company.business_name if transport_company else "") or ""

    if not truck_plate:
        errors.append("Falta la placa del vehículo.")
    if not driver_name:
        errors.append("Falta el nombre del conductor.")
    if not driver_license:
        errors.append("Falta la licencia del conductor.")
    if not carrier_ruc or not carrier_names:
        errors.append("Faltan datos de la empresa de transporte (RUC / razón social).")

    details = list(order_obj.orderdetail_set.select_related("unit").all())
    if not details:
        errors.append("La orden no tiene detalles para la guía.")

    items = []
    for d in details:
        qty = d.quantity or d.quantity_sold or decimal.Decimal(0)
        if qty <= 0:
            continue
        unit_code = (d.unit.name if d.unit_id and d.unit else "NIU") or "NIU"
        description = str(d.description or "TRANSPORTE DE ENCOMIENDA").replace('"', "'")
        price_unit = d.price_unit or decimal.Decimal(0)
        base_amount = (
            (qty * price_unit) / decimal.Decimal("1.1800") if price_unit else decimal.Decimal(0)
        )
        precio_base = (base_amount / qty) if qty and price_unit else decimal.Decimal(0)
        items.append({
            "producto": description,
            "cantidad": float(qty),
            "precioBase": float(round(precio_base, 6)),
            "codigoSunat": "10000000",
            "codigoProducto": str(d.id).zfill(4),
            "codigoUnidad": unit_code,
            "tipoIgvCodigo": "10",
        })

    if not items:
        errors.append("No hay ítems con cantidad válida para enviar.")

    if errors:
        return {
            "success": False,
            "message": "Validación de guía fallida.",
            "errors": errors,
        }

    formatdate = guide_obj.emit_date.strftime("%Y-%m-%d")
    emit_dt = utc_to_local(guide_obj.created_at) if guide_obj.created_at else None
    formatdate_hour = emit_dt.strftime("%H:%M") if emit_dt else "00:00"
    formatdate_transfer = guide_obj.transfer_start_date.strftime("%Y-%m-%d")

    serial = (guide_obj.serial or "").strip()
    try:
        number = str(int(str(guide_obj.correlative).strip()))
    except (TypeError, ValueError):
        number = str(guide_obj.correlative).strip()

    items_graphql = ", ".join(
        f"""{{
               producto: "{_gql_escape(item['producto'])}",
               cantidad: {item['cantidad']},
               precioBase: {item['precioBase']},
               codigoSunat: "{item['codigoSunat']}",
               codigoProducto: "{item['codigoProducto']}",
               codigoUnidad: "{_gql_escape(item['codigoUnidad'])}",
               tipoIgvCodigo: "{item['tipoIgvCodigo']}"
        }}"""
        for item in items
    )
    items_graphql = f"[{items_graphql}]"

    related_documents_graphql = ""
    try:
        order_bill = order_obj.orderbill
    except ObjectDoesNotExist:
        order_bill = None
    if order_bill and order_bill.status == "E" and order_bill.n_receipt:
        bill_type = str(order_bill.type or "")
        if bill_type in ("1", "F", "01"):
            tipo_doc = "01"
        elif bill_type in ("2", "3", "B", "03"):
            tipo_doc = "03"
        else:
            tipo_doc = "01" if order_obj.type_document == "F" else "03"
        bill_date = order_bill.created_at or order_obj.create_at
        bill_fecha = utc_to_local(bill_date).strftime("%Y-%m-%d") if bill_date else formatdate
        related_documents_graphql = f""",
            relatedDocuments: {{
                tipoDocumentoCodigo: "{tipo_doc}",
                serie: "{_gql_escape(order_bill.serial or order_obj.serial or '')}",
                numero: "{int(order_bill.n_receipt)}",
                fechaEmision: "{bill_fecha}"
            }}"""

    observation = _gql_escape(guide_obj.observation or "")
    guide_origin_address = _gql_escape(origin_full or origin_address)
    guide_arrival_address = _gql_escape(destiny_full or destiny_address)

    graphql_query = f"""
    mutation RegisterGuide {{
        registerGuide(
            client: {{
                razonSocialNombres: "{_gql_escape(client_names.upper())}",
                numeroDocumento: "{_gql_escape(client_nro_document)}",
                codigoTipoEntidad: {int(client_type_document)},
                clienteDireccion: "{_gql_escape(client_address or guide_arrival_address)}",
                clienteTelefono: "{_gql_escape(client_phone)}"
            }},
            guide: {{
                serial: "{_gql_escape(serial)}",
                number: "{_gql_escape(number)}",
                guideModeTransfer: "{guide_mode}",
                guideReasonTransfer: "{guide_reason}",
                note: "{observation}",
                emitDate: "{formatdate}",
                emitHour: "{formatdate_hour}"
            }},
            transportation: {{
                transferDate: "{formatdate_transfer}",
                totalWeight: "{float(guide_obj.total_weight)}",
                quantityPackages: "{float(guide_obj.quantity_packages)}"
            }},
            points: {{
                guideOriginSerial: "",
                guideOriginAddress: "{guide_origin_address}",
                guideOriginDistrictId: "{_gql_escape(origin_ubigeo)}",
                guideArrivalSerial: "",
                guideArrivalAddress: "{guide_arrival_address}",
                guideArrivalDistrictId: "{_gql_escape(arrival_ubigeo)}"
            }},
            carrier: {{
                transportationCompanyDocumentType: "6",
                transportationCompanyDocumentNumber: "{_gql_escape(carrier_ruc)}",
                transportationCompanyNames: "{_gql_escape(carrier_names.upper())}",
                transportationCompanyMtcRegistrationNumber: "",
                mainDriverDocumentNumber: "",
                mainDriverNames: "{_gql_escape(driver_name.upper())}",
                mainDriverLicense: "{_gql_escape(driver_license.upper())}",
                mainVehicleLicensePlate: "{_gql_escape(truck_plate)}"
            }},
            items: {items_graphql}{related_documents_graphql}
        ) {{
            message
            error
            operationId
        }}
    }}
    """

    # --- MODO PRUEBA: comentar este bloque al pasar a producción (o poner FACT_DRY_RUN = False) ---
    if FACT_DRY_RUN:
        return _fact_dry_run_response(
            "send_guide_fact (GUÍA REMITENTE)",
            graphql_query,
            {
                "serie": serial,
                "numero": number,
            },
        )
    # --- FIN MODO PRUEBA ---

    token = tokens.get(company_obj.ruc, "ID no encontrado")
    if token == "ID no encontrado":
        return {
            "success": False,
            "message": f"No hay token de facturación configurado para el RUC {company_obj.ruc}.",
        }

    headers = {
        "Content-Type": "application/json",
        "token": token,
    }

    try:
        response = requests.post(GRAPHQL_URL, json={"query": graphql_query}, headers=headers)
        response.raise_for_status()
        result = response.json()

        if result.get("errors"):
            return {
                "success": False,
                "message": "Error GraphQL al registrar la guía.",
                "errors": result.get("errors"),
            }

        data = result.get("data", {}).get("registerGuide") or {}
        has_error = bool(data.get("error"))
        success = not has_error and bool(data.get("operationId") or data.get("message"))

        if success and not has_error:
            return {
                "success": True,
                "message": data.get("message"),
                "operationId": data.get("operationId"),
                "serie": serial,
                "numero": number,
            }

        return {
            "success": False,
            "message": data.get("message") or "La operación no fue exitosa",
            "error": data.get("error"),
        }

    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"Error en la solicitud: {str(e)}"}
    except ValueError:
        return {"success": False, "error": "La respuesta no es un JSON válido"}


def send_guide_transportation_fact(guide_id):
    """
    Envía Guía de Remisión Transportista (GRT) a 4FACT vía mutation
    registerGuideTransportation.
    guide_id: pk de apps.comercial.models.CarrierRemissionGuide
    """
    from apps.comercial.models import CarrierRemissionGuide, Driver

    try:
        guide_obj = CarrierRemissionGuide.objects.select_related(
            "order",
            "order__company",
            "order__subsidiary",
            "order__client",
            "programming",
            "programming__truck",
            "truck",
            "subsidiary",
            "company",
        ).get(id=int(guide_id))
    except (CarrierRemissionGuide.DoesNotExist, TypeError, ValueError):
        return {"success": False, "message": "Guía de remisión transportista no encontrada."}

    order_obj = guide_obj.order
    if not order_obj:
        return {"success": False, "message": "La guía no tiene una orden asociada."}

    errors = []

    if guide_obj.status not in ("I", "T"):
        errors.append("La guía debe estar emitida (estado I) para enviarse a facturación.")
    if not (guide_obj.serial or "").strip():
        errors.append("La guía no tiene serie.")
    if not (guide_obj.correlative or "").strip():
        errors.append("La guía no tiene correlativo.")
    if not guide_obj.emit_date:
        errors.append("La guía no tiene fecha de emisión.")
    if not guide_obj.transfer_start_date:
        errors.append("La guía no tiene fecha de inicio de traslado.")
    if not guide_obj.total_weight or guide_obj.total_weight <= 0:
        errors.append("El peso bruto total debe ser mayor a 0.")
    if not guide_obj.quantity_packages or guide_obj.quantity_packages <= 0:
        errors.append("La cantidad de bultos debe ser mayor a 0.")

    company_obj = guide_obj.company or order_obj.company
    if not company_obj or not (company_obj.ruc or "").strip():
        errors.append("No se encontró la empresa (RUC) asociada a la guía.")

    # Cliente (GRT): remitente que contrata el servicio (OrderAction tipo R).
    remitter_action = order_obj.orderaction_set.filter(type="R").select_related("client").last()
    client_obj = None
    if remitter_action and remitter_action.client_id:
        client_obj = remitter_action.client
    elif order_obj.client_id:
        client_obj = order_obj.client

    client_type_document, client_nro_document = _client_document_info(client_obj)
    client_names = (client_obj.names or "").strip() if client_obj else ""
    client_phone = (client_obj.phone or "").strip() if client_obj else ""
    client_address, client_ubigeo = _client_address_info(client_obj)

    if not client_names:
        errors.append("Falta el nombre del cliente (remitente).")
    if not client_nro_document:
        errors.append("Falta el documento del cliente (remitente).")
    if client_type_document is None:
        errors.append("Falta el tipo de documento del cliente (remitente).")

    # Destinatario (receiver): OrderAction tipo D; fallback al cliente de la orden.
    receiver_action = order_obj.orderaction_set.filter(type="D").select_related(
        "client", "order_addressee"
    ).last()
    receiver_obj = None
    if receiver_action and receiver_action.client_id:
        receiver_obj = receiver_action.client
    elif order_obj.client_id:
        receiver_obj = order_obj.client

    receiver_type_document, receiver_nro_document = _client_document_info(receiver_obj)
    receiver_names = (receiver_obj.names or "").strip() if receiver_obj else ""
    if not receiver_names and receiver_action and receiver_action.order_addressee_id:
        receiver_names = (receiver_action.order_addressee.names or "").strip()

    if not receiver_names:
        errors.append("Falta el nombre del destinatario.")
    if not receiver_nro_document:
        errors.append("Falta el documento del destinatario.")
    if receiver_type_document is None:
        errors.append("Falta el tipo de documento del destinatario.")

    # Puntos de partida / llegada
    origin_full, origin_address, origin_ubigeo = _route_point(order_obj, "O")
    destiny_full, destiny_address, arrival_ubigeo = _route_point(order_obj, "D")
    try:
        encomienda = order_obj.encomienda
    except ObjectDoesNotExist:
        encomienda = None
    if encomienda:
        if not origin_address and encomienda.office_origin_id:
            origin_sub = encomienda.office_origin
            origin_address = (origin_sub.address or "").strip()
            origin_label = (origin_sub.short_name or origin_sub.name or "").strip()
            origin_full = f"{origin_label} - {origin_address}".strip(" -")
            if not origin_ubigeo:
                origin_ubigeo = (origin_sub.ubigeo or "").strip()
        if not destiny_address and encomienda.office_destination_id:
            destiny_sub = encomienda.office_destination
            destiny_address = (destiny_sub.address or "").strip()
            destiny_label = (destiny_sub.short_name or destiny_sub.name or "").strip()
            destiny_full = f"{destiny_label} - {destiny_address}".strip(" -")
            if not arrival_ubigeo:
                arrival_ubigeo = (destiny_sub.ubigeo or "").strip()
        if encomienda.type_guide == "R" and (encomienda.address_delivery or "").strip():
            destiny_full = (encomienda.address_delivery or "").strip()
            destiny_address = destiny_full

    # Fallback: ubigeo desde direcciones de clientes si la sede no lo tiene
    if not origin_ubigeo:
        origin_ubigeo = client_ubigeo
    if not arrival_ubigeo:
        _, arrival_ubigeo = _client_address_info(receiver_obj)

    if not origin_full and not origin_address:
        errors.append("Falta la dirección del punto de partida (ruta origen).")
    if not destiny_full and not destiny_address:
        errors.append("Falta la dirección del punto de llegada (ruta destino).")
    if not origin_ubigeo:
        errors.append(
            "Falta el ubigeo del punto de partida "
            "(configurar ubigeo en la sede de origen)."
        )
    if not arrival_ubigeo:
        errors.append(
            "Falta el ubigeo del punto de llegada "
            "(configurar ubigeo en la sede de destino)."
        )

    # Vehículo y conductor
    programming = guide_obj.programming
    truck_obj = guide_obj.truck or (programming.truck if programming else None)
    truck_plate = ((truck_obj.license_plate if truck_obj else "") or "").strip().upper()

    driver_name = (guide_obj.driver_name or "").strip()
    driver_license = (guide_obj.driver_license or "").strip()
    if not driver_name and programming:
        driver_name = (programming.support_pilot or "").strip()
    if not driver_license and driver_name:
        resolved_name, resolved_license = _driver_from_employee_name(driver_name)
        driver_name = resolved_name or driver_name
        driver_license = resolved_license

    # DNI del conductor: dígitos de la licencia (ej. "Q-40567890" -> "40567890")
    driver_document = "".join(ch for ch in driver_license if ch.isdigit())
    if driver_name and not driver_document:
        driver_obj = Driver.objects.filter(is_active=True).filter(
            names__icontains=driver_name.split()[0]
        ).first()
        if driver_obj:
            driver_document = "".join(
                ch for ch in (driver_obj.license_number or "") if ch.isdigit()
            )

    if not truck_plate:
        errors.append("Falta la placa del vehículo.")
    if not driver_name:
        errors.append("Falta el nombre del conductor.")
    if not driver_license:
        errors.append("Falta la licencia del conductor.")
    if not driver_document:
        errors.append("Falta el documento (DNI) del conductor.")

    # Ítems desde el detalle de la orden
    details = list(order_obj.orderdetail_set.select_related("unit").all())
    if not details:
        errors.append("La orden no tiene detalles para la guía.")

    items = []
    for d in details:
        qty = d.quantity or d.quantity_sold or decimal.Decimal(0)
        if qty <= 0:
            continue
        unit_code = (d.unit.name if d.unit_id and d.unit else "NIU") or "NIU"
        description = str(d.description or "TRANSPORTE DE ENCOMIENDA").replace('"', "'")
        price_unit = d.price_unit or decimal.Decimal(0)
        base_amount = (
            (qty * price_unit) / decimal.Decimal("1.1800") if price_unit else decimal.Decimal(0)
        )
        precio_base = (base_amount / qty) if qty and price_unit else decimal.Decimal(0)
        items.append({
            "producto": description,
            "cantidad": float(qty),
            "precioBase": float(round(precio_base, 6)),
            "codigoSunat": "10000000",
            "codigoProducto": str(d.id).zfill(4),
            "codigoUnidad": unit_code,
            "tipoIgvCodigo": "10",
        })

    if not items:
        errors.append("No hay ítems con cantidad válida para enviar.")

    if errors:
        return {
            "success": False,
            "message": "Validación de guía transportista fallida.",
            "errors": errors,
        }

    formatdate = guide_obj.emit_date.strftime("%Y-%m-%d")
    emit_dt = utc_to_local(guide_obj.created_at) if guide_obj.created_at else None
    formatdate_hour = emit_dt.strftime("%H:%M:%S") if emit_dt else "00:00:00"
    formatdate_transfer = guide_obj.transfer_start_date.strftime("%Y-%m-%d")

    serial = (guide_obj.serial or "").strip()
    try:
        number = str(int(str(guide_obj.correlative).strip()))
    except (TypeError, ValueError):
        number = str(guide_obj.correlative).strip()

    # Motivo de traslado 01 = venta
    guide_reason = "01"

    items_graphql = ", ".join(
        f"""{{
               codigoUnidad: "{_gql_escape(item['codigoUnidad'])}",
               codigoProducto: "{item['codigoProducto']}",
               codigoSunat: "{item['codigoSunat']}",
               producto: "{_gql_escape(item['producto'])}",
               cantidad: {item['cantidad']},
               precioBase: {item['precioBase']},
               tipoIgvCodigo: "{item['tipoIgvCodigo']}"
        }}"""
        for item in items
    )
    items_graphql = f"[{items_graphql}]"

    related_documents_graphql = ""
    try:
        order_bill = order_obj.orderbill
    except ObjectDoesNotExist:
        order_bill = None
    if order_bill and order_bill.status == "E" and order_bill.n_receipt:
        bill_type = str(order_bill.type or "")
        if bill_type in ("1", "F", "01"):
            tipo_doc = "01"
        elif bill_type in ("2", "3", "B", "03"):
            tipo_doc = "03"
        else:
            tipo_doc = "01" if order_obj.type_document == "F" else "03"
        bill_date = order_bill.created_at or order_obj.create_at
        bill_fecha = utc_to_local(bill_date).strftime("%Y-%m-%d") if bill_date else formatdate
        related_documents_graphql = f""",
            relatedDocuments: {{
                tipoDocumentoCodigo: "{tipo_doc}",
                serie: "{_gql_escape(order_bill.serial or order_obj.serial or '')}",
                numero: "{int(order_bill.n_receipt)}",
                fechaEmision: "{bill_fecha}"
            }}"""

    observation = _gql_escape(guide_obj.observation or "")
    guide_origin_address = _gql_escape(origin_full or origin_address)
    guide_arrival_address = _gql_escape(destiny_full or destiny_address)

    graphql_query = f"""
    mutation RegisterGuideTransportation {{
        registerGuideTransportation(
            client: {{
                razonSocialNombres: "{_gql_escape(client_names.upper())}",
                numeroDocumento: "{_gql_escape(client_nro_document)}",
                codigoTipoEntidad: {int(client_type_document)},
                clienteDireccion: "{_gql_escape(client_address or guide_origin_address)}",
                clienteTelefono: "{_gql_escape(client_phone)}"
            }},
            guide: {{
                serial: "{_gql_escape(serial)}",
                number: "{_gql_escape(number)}",
                emitDate: "{formatdate}",
                emitHour: "{formatdate_hour}",
                guideReasonTransfer: "{guide_reason}",
                note: "{observation}"
            }},
            transportation: {{
                transferDate: "{formatdate_transfer}",
                totalWeight: "{float(guide_obj.total_weight)}",
                quantityPackages: "{float(guide_obj.quantity_packages)}",
                weightMeasurementUnit: "KGM"
            }},
            carrier: {{
                mainVehicleLicensePlate: "{_gql_escape(truck_plate)}",
                mainDriverDocumentNumber: "{_gql_escape(driver_document)}",
                mainDriverNames: "{_gql_escape(driver_name.upper())}",
                mainDriverLicense: "{_gql_escape(driver_license.upper())}"
            }},
            receiver: {{
                receiverDocumentType: "{int(receiver_type_document)}",
                receiverDocumentNumber: "{_gql_escape(receiver_nro_document)}",
                receiverNames: "{_gql_escape(receiver_names.upper())}"
            }},
            points: {{
                guideOriginDistrictId: "{_gql_escape(origin_ubigeo)}",
                guideOriginAddress: "{guide_origin_address}",
                guideOriginSerial: "",
                guideArrivalDistrictId: "{_gql_escape(arrival_ubigeo)}",
                guideArrivalAddress: "{guide_arrival_address}",
                guideArrivalSerial: ""
            }},
            items: {items_graphql}{related_documents_graphql}
        ) {{
            message
            error
            operationId
        }}
    }}
    """
    # print(graphql_query)
    # --- MODO PRUEBA: comentar este bloque al pasar a producción (o poner FACT_DRY_RUN = False) ---
    if FACT_DRY_RUN:
        return _fact_dry_run_response(
            "send_guide_transportation_fact (GUÍA TRANSPORTISTA)",
            graphql_query,
            {
                "serie": serial,
                "numero": number,
            },
        )
    # --- FIN MODO PRUEBA ---

    token = tokens.get(company_obj.ruc, "ID no encontrado")

    if token == "ID no encontrado":
        return {
            "success": False,
            "message": f"No hay token de facturación configurado para el RUC {company_obj.ruc}.",
        }

    headers = {
        "Content-Type": "application/json",
        "token": token,
    }

    try:
        response = requests.post(GRAPHQL_URL, json={"query": graphql_query}, headers=headers)
        response.raise_for_status()
        result = response.json()

        if result.get("errors"):
            return {
                "success": False,
                "message": "Error GraphQL al registrar la guía transportista.",
                "errors": result.get("errors"),
            }

        data = result.get("data", {}).get("registerGuideTransportation") or {}
        has_error = bool(data.get("error"))
        success = not has_error and bool(data.get("operationId") or data.get("message"))

        if success and not has_error:
            return {
                "success": True,
                "message": data.get("message"),
                "operationId": data.get("operationId"),
                "serie": serial,
                "numero": number,
            }

        return {
            "success": False,
            "message": data.get("message") or "La operación no fue exitosa",
            "error": data.get("error"),
        }

    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"Error en la solicitud: {str(e)}"}
    except ValueError:
        return {"success": False, "error": "La respuesta no es un JSON válido"}
