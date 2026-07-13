from apps.users.subsidiary_serial_helpers import get_serial, resolve_document_type


def get_serial_subsidiary_company(subsidiary_obj=None, company_rotation_obj=None, type_document=None):
    return get_serial(
        subsidiary_obj,
        company_rotation_obj,
        service_type='E',
        document_type=resolve_document_type('E', type_document or 'T'),
    )


def get_serial_manifest_and_commodity(subsidiary_obj=None, company_rotation_obj=None, type_document=None):
    return get_serial_subsidiary_company(
        subsidiary_obj=subsidiary_obj,
        company_rotation_obj=company_rotation_obj,
        type_document=type_document,
    )


def get_serial_manifest(subsidiary_obj=None, company_rotation_obj=None):
    serial_commodity = get_serial(subsidiary_obj, company_rotation_obj, 'E', 'T')
    serial_manifest = get_serial(subsidiary_obj, company_rotation_obj, 'P', 'T')
    return {
        'serial_commodity': serial_commodity,
        'serial_manifest_passenger': serial_manifest,
        'serial_commodity_voucher': get_serial(subsidiary_obj, company_rotation_obj, 'E', 'B'),
        'serial_commodity_invoice': get_serial(subsidiary_obj, company_rotation_obj, 'E', 'F'),
    }
