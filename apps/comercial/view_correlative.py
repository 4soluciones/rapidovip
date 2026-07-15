from apps.users.subsidiary_serial_helpers import (
    commit_correlative,
    get_next_correlative,
    resolve_document_type,
)


def get_correlative_electronic_passenger(subsidiary_obj=None, company_rotation_obj=None, doc_type=None):
    return get_next_correlative(
        subsidiary_obj,
        company_rotation_obj,
        service_type='E',
        document_type=resolve_document_type('E', doc_type or 'T'),
    )


def get_correlative_manifest(subsidiary_obj=None, company_rotation_obj=None):
    return get_next_correlative(subsidiary_obj, company_rotation_obj, service_type='P', document_type='T')


def get_correlative_commodity(subsidiary_obj=None, company_rotation_obj=None, doc_type=None):
    return get_next_correlative(
        subsidiary_obj,
        company_rotation_obj,
        service_type='E',
        document_type=resolve_document_type('E', doc_type or 'T'),
    )


def update_correlative_service_order(order_obj=None):
    """Confirma el correlativo de la orden de servicio (fila 'T' de la serie)."""
    if not order_obj or not order_obj.order_correlative:
        return
    commit_correlative(
        order_obj.subsidiary,
        order_obj.company,
        order_obj.service_type,
        order_obj.order_correlative,
        'T',
    )


def update_correlative_commodity(order_obj=None):
    if not order_obj:
        return
    commit_correlative(
        order_obj.subsidiary,
        order_obj.company,
        order_obj.service_type,
        order_obj.correlative_sale,
        resolve_document_type(order_obj.service_type, order_obj.type_document),
    )


def update_correlative_passenger(order_obj=None):
    if not order_obj:
        return
    commit_correlative(
        order_obj.subsidiary,
        order_obj.company,
        'E',
        order_obj.correlative_sale,
        resolve_document_type('E', order_obj.type_document),
    )


def update_correlative_manifest_passenger(programming_obj=None):
    if not programming_obj:
        return
    commit_correlative(
        programming_obj.subsidiary,
        programming_obj.company,
        'P',
        programming_obj.correlative,
        'T',
    )
