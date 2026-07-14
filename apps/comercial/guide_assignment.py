"""Helpers for sender guides, cargo manifest and optional carrier guide."""
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
    SenderRemissionGuide,
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


def _destination_label_for_guides(sender_guides):
    labels = []
    for guide in sender_guides:
        order = guide.order
        if not order:
            continue
        encomienda = getattr(order, 'encomienda', None)
        if encomienda and encomienda.office_destination_id:
            labels.append(
                encomienda.office_destination.short_name or encomienda.office_destination.name
            )
        else:
            route = order.orderroute_set.filter(type='D').select_related('subsidiary').last()
            if route and route.subsidiary_id:
                labels.append(route.subsidiary.short_name or route.subsidiary.name)
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
    Assign an encomienda order to a programming and issue a SenderRemissionGuide.
    Requires an existing programming.
    """
    if not programming_obj:
        raise ValueError('Debe existir una programación para generar la guía de remisión.')

    if getattr(order_obj, 'sender_guide', None) and order_obj.sender_guide.status != 'C':
        guide = order_obj.sender_guide
        guide.programming = programming_obj
        guide.status = 'I'
        guide.transfer_start_date = programming_obj.departure_date
        guide.save(update_fields=[
            'programming', 'status', 'transfer_start_date', 'updated_at',
        ])
    else:
        weight, packages = _order_totals(order_obj)
        serial, correlative = _next_guide_serial(
            order_obj.subsidiary or programming_obj.subsidiary,
            order_obj.company or programming_obj.company,
            'R',
        )
        guide = SenderRemissionGuide.objects.create(
            order=order_obj,
            programming=programming_obj,
            serial=serial,
            correlative=correlative,
            status='I',
            emit_date=date.today(),
            transfer_start_date=programming_obj.departure_date,
            total_weight=weight,
            quantity_packages=packages,
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
    Create/refresh the mandatory CargoManifest for a programming.
    Groups all issued sender guides of that programming.
    """
    sender_guides = list(
        SenderRemissionGuide.objects.filter(
            programming=programming_obj, status='I',
        ).select_related('order', 'order__encomienda')
    )
    if not sender_guides:
        raise ValueError('No hay guías de remisión remitente emitidas para esta programación.')

    weight = sum((g.total_weight or 0) for g in sender_guides)
    packages = sum((g.quantity_packages or 0) for g in sender_guides)
    amount = sum((g.order.total or 0) for g in sender_guides if g.order_id)
    destination = _destination_label_for_guides(sender_guides)
    driver_name = programming_obj.support_pilot or ''
    co_pilot_name = programming_obj.support_copilot or ''

    manifest = getattr(programming_obj, 'cargo_manifest', None)
    if manifest and manifest.status != 'X':
        manifest.total_weight = weight
        manifest.quantity_packages = packages
        manifest.guides_count = len(sender_guides)
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
            guides_count=len(sender_guides),
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

    SenderRemissionGuide.objects.filter(
        programming=programming_obj, status='I',
    ).update(cargo_manifest=manifest)

    for guide in sender_guides:
        if guide.order_id and guide.order.status == 'S':
            guide.order.status = 'T'
            guide.order.save(update_fields=['status', 'update_at'])

    if programming_obj.status == 'P':
        programming_obj.status = 'R'
        programming_obj.save(update_fields=['status'])

    return manifest


@transaction.atomic
def create_carrier_guide_for_programming(programming_obj, user):
    """
    Optional CarrierRemissionGuide for a programming.
    Requires at least one issued sender guide (preferably already in a cargo manifest).
    """
    sender_guides = list(
        SenderRemissionGuide.objects.filter(
            programming=programming_obj, status='I',
        ).select_related('order')
    )
    if not sender_guides:
        raise ValueError('No hay guías de remisión remitente emitidas para esta programación.')

    weight = sum((g.total_weight or 0) for g in sender_guides)
    packages = sum((g.quantity_packages or 0) for g in sender_guides)

    carrier = getattr(programming_obj, 'carrier_guide', None)
    if carrier and carrier.status != 'X':
        carrier.total_weight = weight
        carrier.quantity_packages = packages
        carrier.driver_name = programming_obj.support_pilot or carrier.driver_name
        carrier.driver_license = _employee_license_by_name(carrier.driver_name) or carrier.driver_license
        carrier.truck = programming_obj.truck
        carrier.transfer_start_date = programming_obj.departure_date
        carrier.status = 'I'
        carrier.save()
    else:
        serial, correlative = _next_guide_serial(
            programming_obj.subsidiary,
            programming_obj.company,
            'T',
        )
        carrier = CarrierRemissionGuide.objects.create(
            programming=programming_obj,
            serial=serial,
            correlative=correlative,
            status='I',
            emit_date=date.today(),
            transfer_start_date=programming_obj.departure_date,
            total_weight=weight,
            quantity_packages=packages,
            driver_name=programming_obj.support_pilot or '',
            driver_license=_employee_license_by_name(programming_obj.support_pilot or ''),
            truck=programming_obj.truck,
            subsidiary=programming_obj.subsidiary,
            company=programming_obj.company,
            user=user,
        )

    SenderRemissionGuide.objects.filter(
        programming=programming_obj, status='I',
    ).update(carrier_guide=carrier)
    return carrier


def unassign_sender_guide(guide_obj):
    """Detach a sender guide from programming (cancel assignment)."""
    order = guide_obj.order
    guide_obj.status = 'C'
    guide_obj.programming = None
    guide_obj.carrier_guide = None
    guide_obj.cargo_manifest = None
    guide_obj.save(update_fields=[
        'status', 'programming', 'carrier_guide', 'cargo_manifest', 'updated_at',
    ])
    if order and order.status in ('S', 'T'):
        order.status = 'P'
        order.truck = None
        order.save(update_fields=['status', 'truck', 'update_at'])
