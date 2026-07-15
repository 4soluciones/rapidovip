from apps.users.models import SubsidiarySerial

SERVICE_TYPES = ('E', 'P', 'R', 'T', 'A')


def get_serial_record(subsidiary, company, service_type, document_type='T'):
    if not subsidiary or not company:
        return None
    return SubsidiarySerial.objects.filter(
        subsidiary=subsidiary,
        company=company,
        service_type=service_type,
        document_type=document_type,
        active=True,
    ).first()


def get_or_create_serial_record(
    subsidiary, company, service_type, document_type='T', default_serial='',
):
    record, _created = SubsidiarySerial.objects.get_or_create(
        subsidiary=subsidiary,
        company=company,
        service_type=service_type,
        document_type=document_type,
        defaults={
            'serial': default_serial or '',
            'correlative': 0,
            'active': True,
        },
    )
    return record


def get_serial(subsidiary, company, service_type, document_type='T'):
    record = get_serial_record(subsidiary, company, service_type, document_type)
    return record.serial if record else ''


def get_next_correlative(subsidiary, company, service_type, document_type='T'):
    record = get_serial_record(subsidiary, company, service_type, document_type)
    if record:
        return str(record.correlative + 1).zfill(6)
    return '000001'


def commit_correlative(subsidiary, company, service_type, correlative_value, document_type='T'):
    record = get_or_create_serial_record(subsidiary, company, service_type, document_type)
    record.correlative = int(correlative_value)
    record.save(update_fields=['correlative'])


def resolve_document_type(service_type, doc_type='T'):
    if service_type == 'E':
        return doc_type if doc_type in ('T', 'B', 'F') else 'T'
    if service_type in ('R', 'T', 'A'):
        return 'G' if doc_type in ('G', 'T') else doc_type
    return 'T'


def ensure_service_serials(subsidiary, company, serials_map=None):
    """Crea filas de serie para encomiendas, programación, guías y manifiesto."""
    serials_map = serials_map or {}
    created = []

    for service_type, document_type in (
        ('E', 'T'), ('E', 'B'), ('E', 'F'),
        ('P', 'T'),
        ('R', 'G'), ('T', 'G'), ('A', 'G'),
    ):
        default_serial = serials_map.get((service_type, document_type), '')
        record, was_created = SubsidiarySerial.objects.get_or_create(
            subsidiary=subsidiary,
            company=company,
            service_type=service_type,
            document_type=document_type,
            defaults={'serial': default_serial, 'correlative': 0, 'active': True},
        )
        if was_created:
            created.append(record)
        elif default_serial and record.serial != default_serial:
            record.serial = default_serial
            record.save(update_fields=['serial'])
    return created


def get_serials_for_subsidiary_company(subsidiary, company):
    rows = SubsidiarySerial.objects.filter(subsidiary=subsidiary, company=company)
    return {(row.service_type, row.document_type): row for row in rows}


SERVICE_SERIAL_GROUPS = (
    ('E', 'Encomienda', (
        ('T', 'Orden de servicio'),
        ('B', 'Boleta'),
        ('F', 'Factura'),
    )),
    ('R', 'Guía remitente', (('G', 'Serie'),)),
    ('T', 'Guía transportista', (('G', 'Serie'),)),
    ('A', 'Manifiesto de carga', (('G', 'Serie'),)),
    ('P', 'Programación', (('T', 'Serie'),)),
)


def serials_table_context(serial_map):
    """Agrupa series para tablas de sedes."""
    groups = []
    for service_type, service_label, doc_types in SERVICE_SERIAL_GROUPS:
        items = []
        for document_type, doc_label in doc_types:
            row = serial_map.get((service_type, document_type))
            items.append({
                'key': f'{service_type}_{document_type}',
                'doc_label': doc_label,
                'serial': row.serial if row else '',
                'correlative': row.correlative if row else 0,
            })
        groups.append({
            'service_type': service_type,
            'service_label': service_label,
            'items': items,
        })
    return groups


def serials_form_context(subsidiary, company):
    serials = get_serials_for_subsidiary_company(subsidiary, company)

    def _serial(service_type, document_type='T'):
        row = serials.get((service_type, document_type))
        return row.serial if row else ''

    return {
        'serial_ticket': _serial('E', 'T'),
        'serial_boleta': _serial('E', 'B'),
        'serial_factura': _serial('E', 'F'),
        'serial_sender_guide': _serial('R', 'G'),
        'serial_carrier_guide': _serial('T', 'G'),
        'serial_cargo_manifest': _serial('A', 'G'),
        'serial_manifiesto': _serial('P', 'T'),
    }
