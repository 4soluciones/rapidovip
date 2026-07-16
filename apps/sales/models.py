import decimal
import random
import string

from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Min, Sum

from apps import users
from apps.users.models import Subsidiary, District, DocumentType
from apps.users.subsidiary_serial_helpers import get_serial_record
from apps.accounting.models import CashFlow


class Unit(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField('Nombre', max_length=5, unique=True)
    description = models.CharField('Descripcion', max_length=50, null=True, blank=True)
    is_enabled = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Unidad de medida'
        verbose_name_plural = 'Unidades de medida'


class Client(models.Model):
    id = models.AutoField(primary_key=True)
    names = models.CharField(max_length=100, null=True, blank=True, )
    phone = models.CharField('Telefono', max_length=9, null=True, blank=True)
    email = models.EmailField('Correo electronico', max_length=50, null=True, blank=True)
    birthday = models.DateField('Fecha de Nacimiento', null=True, blank=True)
    nationality = models.ForeignKey('users.Nationality', on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.names

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'


class ClientType(models.Model):
    client = models.ForeignKey('Client', on_delete=models.CASCADE, )
    document_type = models.ForeignKey(DocumentType, on_delete=models.CASCADE)
    document_number = models.CharField(max_length=15, null=True, blank=True)

    def __str__(self):
        return str(self.document_number)

    class Meta:
        unique_together = ('document_number', 'document_type',)
        verbose_name = 'Tipo de Cliente'
        verbose_name_plural = 'Tipos de Clientes'


class ClientAddress(models.Model):
    client = models.ForeignKey('Client', on_delete=models.CASCADE)
    address = models.CharField('Dirección', max_length=200, null=True, blank=True)
    district = models.ForeignKey(District, on_delete=models.SET_NULL, null=True, blank=True)
    reference = models.CharField('Referencia', max_length=400, null=True, blank=True)

    def __str__(self):
        return str(self.address)

    class Meta:
        verbose_name = 'Direccion de Cliente'
        verbose_name_plural = 'Direcciones del Clientes'


class OrderAction(models.Model):
    id = models.AutoField(primary_key=True)
    TYPE_CHOICES = (('R', 'REMITENTE'), ('D', 'DESTINATARIO'), ('E', 'ENTIDAD'))
    client = models.ForeignKey('Client', verbose_name='Cliente',
                               on_delete=models.SET_NULL, null=True, blank=True)
    order = models.ForeignKey('Order', on_delete=models.CASCADE, null=True, blank=True)
    type = models.CharField('Estado', max_length=1, choices=TYPE_CHOICES, default='R', )
    order_addressee = models.ForeignKey('OrderAddressee', on_delete=models.CASCADE, null=True, blank=True)


class OrderAddressee(models.Model):
    id = models.AutoField(primary_key=True)
    names = models.CharField(max_length=100, null=True, blank=True)
    phone = models.CharField('Telefono Remitente', max_length=9, null=True, blank=True)

    def __str__(self):
        return str(self.id)


STATUS_CHOICES = (
    ('P', 'PENDIENTE'),
    ('S', 'ASIGNADA'),
    ('T', 'EN TRÁNSITO'),
    ('C', 'COMPLETADO'),
    ('A', 'ANULADO'),
)
WAY_TO_PAY_CHOICES = (('C', 'AL CONTADO'), ('D', 'PAGO DESTINO'), ('S', 'SERVICIO'), ('O', 'Otro'))
TYPE_COMMODITY_CHOICES = (('S', 'SIN ENTREGAR'), ('E', 'ENTREGADO'), ('A', 'ANULADO'), ('I', 'INTERNADO'))
STATUS_TRANSPORT_CHOICES = (('O', 'EN ORIGEN'), ('T', 'EN TRÁNSITO'), ('D', 'EN DESTINO'), ('E', 'ENTREGADO'))
TYPE_DOCUMENT = (('T', 'ORDEN DE SERVICIO'), ('B', 'BOLETA'), ('F', 'FACTURA'))
GUIDE_TYPE_CHOICES = (('O', 'OFICINA'), ('R', 'REPARTO'))
SERVICE_TYPE_CHOICES = (
    ('E', 'ENCOMIENDAS'),
)
TYPE_ORDER_CHOICES = (('E', 'ENCOMIENDA'), ('P', 'PASSENGER'),)
DTG_CHOICES = (('GE', 'GUIA DE ENCOMIENDA'), ('DE', 'DOCUMENTO ELECTRONICO'),)
PAYMENT_METHOD_CHOICES = (
    ('E', 'Efectivo'),
    ('T', 'Tarjeta'),
)


class Order(models.Model):
    id = models.AutoField(primary_key=True)
    dtg = models.CharField('Tipo', max_length=2, choices=DTG_CHOICES, default='GE')
    type_order = models.CharField('Tipo Order', max_length=1, choices=TYPE_ORDER_CHOICES, default='E')
    type_document = models.CharField('Tipo Documento', max_length=1, choices=TYPE_DOCUMENT, default='T')
    subsidiary = models.ForeignKey(Subsidiary, on_delete=models.SET_NULL, null=True, blank=True)
    client = models.ForeignKey('Client', verbose_name='Cliente', on_delete=models.SET_NULL, null=True, blank=True)
    user = models.ForeignKey(User, verbose_name='Usuario', on_delete=models.CASCADE)
    truck = models.ForeignKey('comercial.Truck', on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField('Estado', max_length=1, choices=STATUS_CHOICES, default='P')
    transfer_date = models.DateField('Fecha de Traslado', null=True, blank=True)
    create_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    update_at = models.DateTimeField(auto_now=True)
    total = models.DecimalField('Total', max_digits=10, decimal_places=2, default=0)
    serial = models.CharField('Serie', max_length=5, null=True, blank=True)
    correlative_sale = models.CharField(verbose_name='Correlativo', max_length=45, null=True, blank=True)
    order_serial = models.CharField('Serie Orden de Servicio', max_length=10, null=True, blank=True)
    order_correlative = models.CharField('Correlativo Orden de Servicio', max_length=45, null=True, blank=True)
    way_to_pay = models.CharField('Forma de pago', max_length=1, choices=WAY_TO_PAY_CHOICES, default='C')
    company = models.ForeignKey('users.Company', on_delete=models.SET_NULL, null=True, blank=True)
    service_type = models.CharField('Tipo de servicio', max_length=1, choices=SERVICE_TYPE_CHOICES, default='E')
    observation = models.TextField('Observación', blank=True, default='')
    cancel_motive = models.CharField(max_length=500, null=True, blank=True)

    def __str__(self):
        return str(self.pk)

    def sum_total_details(self):
        total = self.orderdetail_set.aggregate(t=Sum('amount'))['t']
        if total is not None:
            return total
        return self.total or decimal.Decimal('0')

    @property
    def code_track(self):
        """Compatibilidad: el código de seguimiento vive en OrderCommodity."""
        try:
            return self.encomienda.code_track or ''
        except ObjectDoesNotExist:
            return ''

    class Meta:
        verbose_name = 'Orden'
        verbose_name_plural = 'Ordenes'


class OrderCommodity(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='encomienda')
    office_origin = models.ForeignKey(
        Subsidiary, related_name='origin_orders', on_delete=models.PROTECT, null=True, blank=True,
    )
    office_destination = models.ForeignKey(
        Subsidiary, related_name='destination_orders', on_delete=models.PROTECT, null=True, blank=True,
    )
    type_guide = models.CharField('Tipo de encomienda', max_length=1, choices=GUIDE_TYPE_CHOICES, default='O')
    arrival_time = models.TimeField('Hora de llegada', null=True, blank=True)
    address_delivery = models.CharField('Direccion de Reparto', max_length=250, blank=True, default='')
    code = models.CharField(max_length=4, blank=True, default='0000')
    type_commodity = models.CharField(
        'Tipo de envio de encomienda', max_length=1, choices=TYPE_COMMODITY_CHOICES, default='S',
    )
    status_transport = models.CharField(
        'Estado de encomienda', max_length=1, choices=STATUS_TRANSPORT_CHOICES, default='O',
    )
    code_track = models.CharField(max_length=4, blank=True, default='')

    def save(self, *args, **kwargs):
        if not self.code_track:
            characters = string.ascii_uppercase + string.digits
            self.code_track = ''.join(random.choices(characters, k=4))
        super().save(*args, **kwargs)

    def receiver_actions(self):
        return self.order.orderaction_set.filter(type='D').select_related('client', 'order_addressee')

    def receivers_display(self):
        names = []
        for action in self.receiver_actions():
            if action.client_id:
                names.append(action.client.names or '')
            elif action.order_addressee_id:
                names.append(action.order_addressee.names or '')
        return [n for n in names if n]

    class Meta:
        verbose_name = 'Encomienda'
        verbose_name_plural = 'Encomiendas'


class OrderTracking(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    status = models.CharField(max_length=1)
    subsidiary = models.ForeignKey(Subsidiary, on_delete=models.PROTECT)
    observation = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.PROTECT)

    class Meta:
        verbose_name = 'Seguimiento de orden'
        verbose_name_plural = 'Seguimientos de orden'


class OrderDetail(models.Model):
    STATUS_CHOICES = (('P', 'PENDIENTE'), ('E', 'EN PROCESO'),
                      ('C', 'COMPRADO'), ('V', 'VENDIDO'), ('A', 'ANULADO'),)
    order = models.ForeignKey('Order', on_delete=models.CASCADE, null=True, blank=True)
    quantity_sold = models.DecimalField('Cantidad vendida', max_digits=10, decimal_places=2, default=0)
    quantity_purchased = models.DecimalField('Cantidad comprada', max_digits=10, decimal_places=2, default=0)
    quantity_requested = models.DecimalField('Cantidad solicitada', max_digits=10, decimal_places=2, default=0)
    quantity = models.DecimalField('Cantidad', max_digits=10, decimal_places=2, default=0)
    price_unit = models.DecimalField('Precio unitario', max_digits=10, decimal_places=6, default=0)
    unit = models.ForeignKey('Unit', on_delete=models.SET_NULL, null=True, blank=True)
    commentary = models.CharField(max_length=200, null=True, blank=True)
    status = models.CharField('Estado', max_length=1, choices=STATUS_CHOICES, default='P', )
    description = models.CharField(max_length=500, null=True, blank=True)
    weight = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount = models.DecimalField('Importe', max_digits=10, decimal_places=6, default=0)

    def __str__(self):
        label = self.description or (self.unit.name if self.unit_id else 'Ítem')
        return f'{label} / {self.status}'

    def multiply(self):
        return self.quantity * self.price_unit

    class Meta:
        verbose_name = 'Detalle orden'
        verbose_name_plural = 'Detalles de orden'


class OrderBill(models.Model):
    STATUS_CHOICES = (('E', 'Emitido'), ('A', 'Anulado'),)
    TYPE_CHOICES = (('1', 'Factura'), ('2', 'Boleta'),)
    IS_DEMO_CHOICES = (('D', 'Demo'), ('P', 'Produccion'),)
    order = models.OneToOneField('Order', on_delete=models.CASCADE, primary_key=True)
    serial = models.CharField('Serie', max_length=5, null=True, blank=True)
    type = models.CharField('Tipo de Comprobante', max_length=2, choices=TYPE_CHOICES)
    n_receipt = models.IntegerField('Numero de Comprobante', default=0)
    sunat_status = models.CharField('Sunat Status', max_length=5, null=True, blank=True)
    sunat_description = models.CharField('Sunat descripcion', max_length=500, null=True, blank=True)
    user = models.ForeignKey(User, verbose_name='Usuario', on_delete=models.CASCADE)
    sunat_enlace_pdf = models.CharField('Sunat Enlace Pdf', max_length=500, null=True, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    code_qr = models.CharField('Codigo QR', max_length=500, null=True, blank=True)
    code_hash = models.CharField('Codigo Hash', max_length=500, null=True, blank=True)
    status = models.CharField('Estado', max_length=1, choices=STATUS_CHOICES)
    invoice_id = models.IntegerField(default=0)
    company = models.ForeignKey('users.Company', on_delete=models.SET_NULL, null=True, blank=True)
    link_xml = models.CharField('Enlace xml', max_length=900, null=True, blank=True)
    link_cdr = models.CharField('Enlace cdr', max_length=900, null=True, blank=True)

    def __str__(self):
        return str(self.order.id)

    class Meta:
        verbose_name = 'Registro de Comprobante'
        verbose_name_plural = 'Registros de Comprobantes'


class Manifest(models.Model):
    id = models.AutoField(primary_key=True)
    serial = models.CharField('Serie Manifiesto', max_length=5, null=True, blank=True)
    correlative = models.CharField(verbose_name='Correlativo Manifiesto', max_length=45, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, verbose_name='Usuario', on_delete=models.CASCADE)
    subsidiary = models.ForeignKey(Subsidiary, on_delete=models.SET_NULL, null=True, blank=True)
    company = models.ForeignKey('users.Company', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return str(self.id)

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):

        if self.pk is None:
            record = get_serial_record(self.subsidiary, self.company, service_type='P', document_type='T')
            if record:
                record.correlative = (record.correlative or 0) + 1
                record.save(update_fields=['correlative'])
                self.correlative = str(record.correlative).zfill(6)
        super(Manifest, self).save(force_insert, force_update, using, update_fields)
