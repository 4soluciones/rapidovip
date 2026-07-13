from apps.users.subsidiary_serial_helpers import get_next_correlative, get_serial, resolve_document_type


def get_serial_service(subsidiary_obj, company_obj, service_type, doc_type='T'):
    document_type = resolve_document_type(service_type, doc_type)
    serial = get_serial(subsidiary_obj, company_obj, service_type, document_type)
    return serial or 'G001'


def get_correlative_service(subsidiary_obj, company_obj, service_type, doc_type='T'):
    document_type = resolve_document_type(service_type, doc_type)
    return get_next_correlative(subsidiary_obj, company_obj, service_type, document_type)
