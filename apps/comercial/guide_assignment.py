"""Helpers: orden de servicio → GRT (1 por orden) → manifiesto de carga."""
import decimal
from datetime import date

from django.db import transaction
from django.db.models import Sum

from apps.users.models import Employee
from apps.users.subsidiary_serial_helpers import get_serial_record
from .models import (
    CargoManifest,
    CarrierRemissionGuide,
    Driver,
    Programming,
)


def _order_totals(order_obj):
    agg = order_obj.orderdetail_set.aggregate(
        weight=Sum('weight'),
        packages=Sum('quantity'),
    )
    weight = agg['weight'] or decimal.Decimal('0')
    packages = agg['packages'] or decimal.Decimal('0')
    return weight, packages


def _next_guide_serial(subsidiary, company, service_type):
    """Return (serial, correlative_str) and increment the serial record."""
    record = get_serial_record(subsidiary, company, service_type=service_type, document_type='G')
    if not record and service_type == 'A':
        record = get_serial_record(subsidiary, company, service_type=service_type, document_type='T')
    if not record:
        record = get_serial_record(subsidiary, company, service_type=service_type, document_type='T')
    if not record:
        prefixes = {'T': 'TR', 'R': 'GR', 'A': 'MC'}
        return prefixes.get(service_type, 'DOC'), '000001'
    record.correlative = (record.correlative or 0) + 1
    record.save(update_fields=['correlative'])
    prefixes = {'T': 'TR', 'R': 'GR', 'A': 'MC'}
    serial = (record.serial or '').strip() or prefixes.get(service_type, 'DOC')
    return serial, str(record.correlative).zfill(6)


def _employee_license_by_name(full_name):
    """Busca licencia primero en Driver, luego en Employee (compatibilidad)."""
    if not full_name:
        return ''
    name = str(full_name).strip()
    name_upper = name.upper()
    for driver in Driver.objects.filter(is_active=True):
        if driver.full_name.upper() == name_upper:
            return driver.license_number or ''
    token = name.split()[0] if name else ''
    if token:
        driver = Driver.objects.filter(names__icontains=token, is_active=True).first()
        if driver:
            return driver.license_number or ''
    first = name.split(',')[0].strip()
    employee = Employee.objects.filter(names__icontains=first.split()[0], is_enabled=True).first()
    if not employee:
        employee = Employee.objects.filter(names__icontains=first[:20], is_enabled=True).first()
    return (employee.n_license or '') if employee else ''


def related_document_for_order(order_obj):
    """Documento relacionado (factura/boleta) o vacío si es solo orden de servicio."""
    if not order_obj:
        return ''
    order_bill = getattr(order_obj, 'orderbill', None)
    if order_bill is None and hasattr(order_obj, 'orderbill_set'):
        order_bill = order_obj.orderbill_set.first()
    if order_bill:
        bill_type = str(getattr(order_bill, 'type', '') or '')
        serial = (order_bill.serial or order_obj.serial or '').strip()
        number = str(
            getattr(order_bill, 'n_receipt', None) or order_obj.correlative_sale or ''
        ).zfill(6)
        if bill_type in ('1', 'F', '01'):
            return f'FACTURA ELECTRÓNICA: {serial}-{number}'
        if bill_type in ('2', '3', 'B', '03'):
            return f'BOLETA ELECTRÓNICA: {serial}-{number}'
        return f'DOCUMENTO: {serial}-{number}'
    if order_obj.type_document == 'F':
        return f'FACTURA ELECTRÓNICA: {order_obj.serial or ""}-{order_obj.correlative_sale or ""}'
    if order_obj.type_document == 'B':
        return f'BOLETA ELECTRÓNICA: {order_obj.serial or ""}-{order_obj.correlative_sale or ""}'
    return ''


def _destination_label_for_guides(carrier_guides):
    labels = []
    for guide in carrier_guides:
        order = guide.order
        if not order:
            continue
        encomienda = getattr(order, 'encomienda', None)
        if encomienda and encomienda.office_destination_id:
            labels.append(
                encomienda.office_destination.short_name or encomienda.office_destination.name
            )
    unique = []
    for label in labels:
        if label and label not in unique:
            unique.append(label)
    if not unique:
        return '—'
    if len(unique) == 1:
        return unique[0]
    return 'VARIOS'


@transaction.atomic
def assign_order_to_programming(order_obj, programming_obj, user):
    """
    Asigna una orden de servicio a una programación y emite su GRT
    (tipo de traslado privado; documento relacionado = boleta/factura si existe).
    """
    if not programming_obj:
        raise ValueError('Debe existir una programación para generar la guía transportista.')

    weight, packages = _order_totals(order_obj)
    related_doc = related_document_for_order(order_obj)
    existing = getattr(order_obj, 'carrier_guide', None)

    if existing:
        if existing.cargo_manifest_id and existing.status == 'I':
            raise ValueError(
                'La orden ya está en un manifiesto de carga. '
                'No se puede reasignar hasta retirarla del manifiesto.'
            )
        if existing.status == 'I' and existing.programming_id == programming_obj.id:
            return existing
        existing.programming = programming_obj
        existing.status = 'I'
        existing.emit_date = existing.emit_date or date.today()
        existing.transfer_start_date = programming_obj.departure_date
        existing.total_weight = weight
        existing.quantity_packages = packages
        existing.related_document = related_doc
        existing.cargo_manifest = None
        if (order_obj.observation or '').strip() and not (existing.observation or '').strip():
            existing.observation = (order_obj.observation or '').strip()
        existing.driver_name = programming_obj.support_pilot or ''
        existing.driver_license = _employee_license_by_name(programming_obj.support_pilot or '')
        existing.truck = programming_obj.truck
        existing.subsidiary = order_obj.subsidiary or programming_obj.subsidiary
        existing.company = order_obj.company or programming_obj.company
        if user and not existing.user_id:
            existing.user = user
        existing.save()
        guide = existing
    else:
        serial, correlative = _next_guide_serial(
            order_obj.subsidiary or programming_obj.subsidiary,
            order_obj.company or programming_obj.company,
            'T',
        )
        guide = CarrierRemissionGuide.objects.create(
            order=order_obj,
            programming=programming_obj,
            serial=serial,
            correlative=correlative,
            status='I',
            emit_date=date.today(),
            transfer_start_date=programming_obj.departure_date,
            total_weight=weight,
            quantity_packages=packages,
            related_document=related_doc,
            observation=(order_obj.observation or '').strip(),
            driver_name=programming_obj.support_pilot or '',
            driver_license=_employee_license_by_name(programming_obj.support_pilot or ''),
            truck=programming_obj.truck,
            subsidiary=order_obj.subsidiary or programming_obj.subsidiary,
            company=order_obj.company or programming_obj.company,
            user=user,
        )

    if order_obj.truck_id != programming_obj.truck_id:
        order_obj.truck = programming_obj.truck
    order_obj.traslate_date = programming_obj.departure_date
    order_obj.status = 'S'
    order_obj.save(update_fields=['truck', 'traslate_date', 'status', 'update_at'])
    return guide


@transaction.atomic
def create_cargo_manifest_for_programming(programming_obj, user):
    """
    Emite/actualiza el manifiesto de carga agrupando las GRT de la programación.
    """
    carrier_guides = list(
        CarrierRemissionGuide.objects.filter(
            programming=programming_obj, status='I',
        ).select_related('order', 'order__encomienda')
    )
    if not carrier_guides:
        raise ValueError('No hay guías transportista emitidas para esta programación.')

    weight = sum((g.total_weight or 0) for g in carrier_guides)
    packages = sum((g.quantity_packages or 0) for g in carrier_guides)
    amount = sum((g.order.total or 0) for g in carrier_guides if g.order_id)
    destination = _destination_label_for_guides(carrier_guides)
    driver_name = programming_obj.support_pilot or ''
    co_pilot_name = programming_obj.support_copilot or ''

    manifest = getattr(programming_obj, 'cargo_manifest', None)
    if manifest and manifest.status != 'X':
        manifest.total_weight = weight
        manifest.quantity_packages = packages
        manifest.guides_count = len(carrier_guides)
        manifest.total_amount = amount
        manifest.destination_label = destination
        manifest.driver_name = driver_name
        manifest.driver_license = _employee_license_by_name(driver_name) or manifest.driver_license
        manifest.co_pilot_name = co_pilot_name
        manifest.co_pilot_license = _employee_license_by_name(co_pilot_name) or manifest.co_pilot_license
        manifest.truck = programming_obj.truck
        manifest.emit_date = manifest.emit_date or date.today()
        manifest.status = 'I'
        manifest.save()
    else:
        serial, correlative = _next_guide_serial(
            programming_obj.subsidiary,
            programming_obj.company,
            'A',
        )
        manifest = CargoManifest.objects.create(
            programming=programming_obj,
            serial=serial,
            correlative=correlative,
            status='I',
            emit_date=date.today(),
            total_weight=weight,
            quantity_packages=packages,
            guides_count=len(carrier_guides),
            total_amount=amount,
            destination_label=destination,
            driver_name=driver_name,
            driver_license=_employee_license_by_name(driver_name),
            co_pilot_name=co_pilot_name,
            co_pilot_license=_employee_license_by_name(co_pilot_name),
            truck=programming_obj.truck,
            subsidiary=programming_obj.subsidiary,
            company=programming_obj.company,
            user=user,
        )

    CarrierRemissionGuide.objects.filter(
        programming=programming_obj, status='I',
    ).update(cargo_manifest=manifest)

    for guide in carrier_guides:
        if guide.order_id and guide.order.status == 'S':
            guide.order.status = 'T'
            guide.order.save(update_fields=['status', 'update_at'])

    if programming_obj.status == 'P':
        programming_obj.status = 'R'
        programming_obj.save(update_fields=['status'])

    return manifest


@transaction.atomic
def unassign_carrier_guide(guide_obj):
    """
    Quita la orden de la programación (corrige asignación errónea).
    La orden vuelve a pendientes. No permite desasignar si ya está en un manifiesto.
    """
    if guide_obj.cargo_manifest_id:
        raise ValueError(
            'No se puede desasignar: la guía ya está en un manifiesto de carga.'
        )
    if guide_obj.status == 'X':
        return guide_obj

    order = guide_obj.order
    guide_obj.status = 'X'
    guide_obj.programming = None
    guide_obj.cargo_manifest = None
    guide_obj.save(update_fields=[
        'status', 'programming', 'cargo_manifest', 'updated_at',
    ])
    if order and order.status in ('S', 'T'):
        order.status = 'P'
        order.truck = None
        order.save(update_fields=['status', 'truck', 'update_at'])
    return guide_obj


# Compatibilidad con imports antiguos
def unassign_sender_guide(guide_obj):
    """Deprecated: usar unassign_carrier_guide."""
    if isinstance(guide_obj, CarrierRemissionGuide):
        return unassign_carrier_guide(guide_obj)
    raise ValueError('La guía remitente no se usa en este proceso. Desasigne la GRT.')


def create_carrier_guide_for_programming(programming_obj, user):
    """Deprecated: la GRT se emite al asignar cada orden."""
    raise ValueError(
        'La guía transportista se emite automáticamente al asignar cada orden de servicio.'
    )
