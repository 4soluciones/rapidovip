from django.db import models
from django.contrib.auth.models import User
from django.db.models import Sum
from apps.users.models import Subsidiary


class Owner(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField('Nombre', max_length=100)
    associated = models.CharField('Asociado', max_length=100, null=True, blank=True)
    ruc = models.CharField(max_length=11)
    address = models.CharField('Dirección', max_length=100, null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Propietario'
        verbose_name_plural = 'Propietarios'


class TruckBrand(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField('Nombre', max_length=45, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Marca de tracto'
        verbose_name_plural = 'Marcas de tractos'


class TruckModel(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField('Nombre', max_length=45, unique=True)
    truck_brand = models.ForeignKey('TruckBrand', on_delete=models.CASCADE)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Modelo de tracto'
        verbose_name_plural = 'Modelos de tractos'


class Truck(models.Model):
    DRIVE_TYPE_CHOICES = (('C', 'FURGON'), ('S', 'SEMITRAILER'), ('A', 'CAMION'),)
    FUEL_TYPE_CHOICES = (('1', 'DIESEL'), ('2', 'GASOLINA'), ('3', 'GAS'),)
    CONDITION_OWNER_CHOICES = (('P', 'PROPIO'), ('A', 'APOYO'),)
    id = models.AutoField(primary_key=True)
    license_plate = models.CharField('Placa', max_length=10)
    num_axle = models.IntegerField('Numero de Ejes', null=True, default=0)
    year = models.CharField('Fabricación', max_length=4, null=True, blank=True)
    truck_model = models.ForeignKey('TruckModel', on_delete=models.SET_NULL, null=True, blank=True)
    drive_type = models.CharField('Tipo de Unidad', max_length=2,
                                  choices=DRIVE_TYPE_CHOICES, default='A')
    contact_phone = models.CharField(max_length=45, null=True, blank=True)
    certificate = models.CharField(max_length=15, null=True, blank=True)
    nro_passengers = models.CharField(max_length=2, null=True, blank=True)
    engine = models.CharField('Motor', max_length=100, null=True, blank=True)
    chassis = models.CharField('Chasis', max_length=100, null=True, blank=True)
    color = models.CharField(max_length=45, null=True, blank=True)
    fuel_type = models.CharField('Tipo de Combustible', max_length=1,
                                 choices=FUEL_TYPE_CHOICES, default='1')
    owner = models.ForeignKey('Owner', on_delete=models.SET_NULL, null=True, blank=True)
    condition_owner = models.CharField('Condicion', max_length=1,
                                       choices=CONDITION_OWNER_CHOICES, default='P')
    technical_review_expiration_date = models.DateField('Fecha de expiracion de revisión técnica', null=True,
                                                        blank=True)
    soat_expiration_date = models.DateField('Fecha de expiracion del soat', null=True, blank=True)
    capacidad_kg = models.DecimalField('Capacidad (kg)', max_digits=10, decimal_places=2, default=0)
    capacidad_m3 = models.DecimalField('Capacidad (m³)', max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField('Activo', default=True)

    def __str__(self):
        return self.license_plate

    class Meta:
        verbose_name = 'Unidad'
        verbose_name_plural = 'Unidades'


class Driver(models.Model):
    """Conductor operativo (no es usuario del sistema)."""
    LICENSE_TYPE_CHOICES = (
        ('A1', 'A-I'),
        ('A2a', 'A-IIa'),
        ('A2b', 'A-IIb'),
        ('A3a', 'A-IIIa'),
        ('A3b', 'A-IIIb'),
        ('A3c', 'A-IIIc'),
        ('B1', 'B-I'),
        ('B2a', 'B-IIa'),
        ('B2b', 'B-IIb'),
        ('B2c', 'B-IIc'),
    )
    id = models.AutoField(primary_key=True)
    names = models.CharField('Nombres', max_length=100)
    paternal_last_name = models.CharField('Apellido paterno', max_length=100)
    maternal_last_name = models.CharField('Apellido materno', max_length=100, blank=True, default='')
    address = models.CharField('Dirección', max_length=250, blank=True, default='')
    phone = models.CharField('Teléfono', max_length=20, blank=True, default='')
    license_number = models.CharField('N° licencia', max_length=30)
    license_type = models.CharField(
        'Tipo de licencia', max_length=5, choices=LICENSE_TYPE_CHOICES, default='A3b',
    )
    is_active = models.BooleanField('Activo', default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def full_name(self):
        parts = [self.names, self.paternal_last_name, self.maternal_last_name or '']
        return ' '.join(p.strip() for p in parts if p and p.strip())

    def __str__(self):
        return self.full_name

    class Meta:
        verbose_name = 'Conductor'
        verbose_name_plural = 'Conductores'
        ordering = ['paternal_last_name', 'names']


class Programming(models.Model):
    SERVICE_TYPE_CHOICES = (
        ('E', 'Encomiendas'),
    )
    STATUS_CHOICES = (
        ('P', 'Programado'),
        ('R', 'En ruta'),
        ('E', 'Entregado'),
        ('C', 'Cancelado'),
    )
    id = models.AutoField(primary_key=True)
    departure_date = models.DateField('Fecha Salida', null=True, blank=True)
    arrival_date = models.DateField('Fecha Llegada', null=True, blank=True)
    service_type = models.CharField('Servicio', max_length=1, choices=SERVICE_TYPE_CHOICES, default='E')
    status = models.CharField('Estado', max_length=1, choices=STATUS_CHOICES, default='P')
    weight = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    truck = models.ForeignKey('Truck', verbose_name='Tracto',
                              on_delete=models.SET_NULL, null=True, blank=True)
    subsidiary = models.ForeignKey(Subsidiary, verbose_name='Sede',
                                   on_delete=models.SET_NULL, null=True, blank=True)
    observation = models.CharField(max_length=200, null=True, blank=True)
    km_initial = models.CharField('km inicial', max_length=6, null=True, blank=True)
    km_ending = models.CharField('km inicial', max_length=6, null=True, blank=True)
    correlative = models.CharField(verbose_name='Correlativo', max_length=45, null=True, blank=True)
    serial = models.CharField(verbose_name='Serie', max_length=4, null=True, blank=True)
    company = models.ForeignKey('users.Company', on_delete=models.SET_NULL, null=True, blank=True)
    truck_exit = models.DateTimeField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    support_pilot = models.CharField(max_length=500, null=True, blank=True)
    support_copilot = models.CharField(max_length=500, null=True, blank=True)

    def __str__(self):
        return str(self.id)

    def get_exit_time_display(self):
        """Hora de salida formateada desde truck_exit."""
        if self.truck_exit:
            return self.truck_exit.strftime('%H:%M')
        return ''

    def get_turn_display(self):
        """Compatibilidad con plantillas que usaban el antiguo campo turn."""
        return self.get_exit_time_display() or '—'

    class Meta:
        verbose_name = 'Programación'
        verbose_name_plural = 'Programaciones'


class CargoManifest(models.Model):
    """Manifiesto de carga: agrupa las guías de remisión transportista de una programación."""

    STATUS_CHOICES = (
        ('D', 'Borrador'),
        ('I', 'Emitido'),
        ('T', 'En tránsito'),
        ('C', 'Completado'),
        ('X', 'Anulado'),
    )
    programming = models.OneToOneField(
        Programming, on_delete=models.PROTECT, related_name='cargo_manifest',
    )
    serial = models.CharField(max_length=10, blank=True, default='')
    correlative = models.CharField(max_length=20, blank=True, default='')
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default='D')
    emit_date = models.DateField(null=True, blank=True)
    total_weight = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    quantity_packages = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    guides_count = models.PositiveIntegerField(default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    destination_label = models.CharField(max_length=200, blank=True, default='')
    driver_name = models.CharField(max_length=200, blank=True, default='')
    driver_license = models.CharField(max_length=30, blank=True, default='')
    co_pilot_name = models.CharField(max_length=200, blank=True, default='')
    co_pilot_license = models.CharField(max_length=30, blank=True, default='')
    observation = models.TextField(blank=True, default='')
    truck = models.ForeignKey(
        'Truck', on_delete=models.SET_NULL, null=True, blank=True, related_name='cargo_manifests',
    )
    subsidiary = models.ForeignKey(
        Subsidiary, on_delete=models.SET_NULL, null=True, blank=True,
    )
    company = models.ForeignKey(
        'users.Company', on_delete=models.SET_NULL, null=True, blank=True,
    )
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.serial}-{self.correlative}' if self.serial else str(self.pk)

    def document_number(self):
        if self.serial and self.correlative:
            return f'{self.serial}-{str(self.correlative).zfill(6)}'
        return str(self.pk)

    class Meta:
        verbose_name = 'Manifiesto de carga'
        verbose_name_plural = 'Manifiestos de carga'
        ordering = ['-created_at']


class CarrierRemissionGuide(models.Model):
    """Guía de remisión transportista: una por orden de servicio al asignarla a una programación."""

    STATUS_CHOICES = (
        ('D', 'Borrador'),
        ('I', 'Emitida'),
        ('T', 'En tránsito'),
        ('C', 'Completada'),
        ('X', 'Anulada'),
    )
    order = models.OneToOneField(
        'sales.Order', on_delete=models.PROTECT, related_name='carrier_guide',
    )
    programming = models.ForeignKey(
        Programming, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='carrier_guides',
    )
    cargo_manifest = models.ForeignKey(
        CargoManifest, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='carrier_guides',
    )
    serial = models.CharField(max_length=10, blank=True, default='')
    correlative = models.CharField(max_length=20, blank=True, default='')
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default='D')
    emit_date = models.DateField(null=True, blank=True)
    transfer_start_date = models.DateField(null=True, blank=True)
    total_weight = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    quantity_packages = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    observation = models.TextField(blank=True, default='')
    related_document = models.CharField(max_length=120, blank=True, default='')
    driver_name = models.CharField(max_length=200, blank=True, default='')
    driver_license = models.CharField(max_length=30, blank=True, default='')
    truck = models.ForeignKey(
        'Truck', on_delete=models.SET_NULL, null=True, blank=True, related_name='carrier_guides',
    )
    subsidiary = models.ForeignKey(
        Subsidiary, on_delete=models.SET_NULL, null=True, blank=True,
    )
    company = models.ForeignKey(
        'users.Company', on_delete=models.SET_NULL, null=True, blank=True,
    )
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.serial}-{self.correlative}' if self.serial else str(self.pk)

    def document_number(self):
        if self.serial and self.correlative:
            return f'{self.serial}-{str(self.correlative).zfill(6)}'
        return str(self.pk)

    def recalculate_totals(self):
        if not self.order_id:
            return
        agg = self.order.orderdetail_set.aggregate(
            w=Sum('weight'), p=Sum('quantity'),
        )
        self.total_weight = agg['w'] or 0
        self.quantity_packages = agg['p'] or 0
        self.save(update_fields=['total_weight', 'quantity_packages', 'updated_at'])

    class Meta:
        verbose_name = 'Guía de remisión transportista'
        verbose_name_plural = 'Guías de remisión transportista'
        ordering = ['-created_at']


class SenderRemissionGuide(models.Model):
    """Guía de remisión remitente (reservada; proceso actual usa GRT por orden)."""

    STATUS_CHOICES = (
        ('D', 'Borrador'),
        ('I', 'Emitida'),
        ('C', 'Anulada'),
    )
    order = models.OneToOneField(
        'sales.Order', on_delete=models.PROTECT, related_name='sender_guide',
    )
    programming = models.ForeignKey(
        Programming, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sender_guides',
    )
    cargo_manifest = models.ForeignKey(
        CargoManifest, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sender_guides',
    )
    carrier_guide = models.ForeignKey(
        CarrierRemissionGuide, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sender_guides',
    )
    serial = models.CharField(max_length=10, blank=True, default='')
    correlative = models.CharField(max_length=20, blank=True, default='')
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default='D')
    emit_date = models.DateField(null=True, blank=True)
    transfer_start_date = models.DateField(null=True, blank=True)
    total_weight = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    quantity_packages = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    observation = models.TextField(blank=True, default='')
    subsidiary = models.ForeignKey(
        Subsidiary, on_delete=models.SET_NULL, null=True, blank=True,
    )
    company = models.ForeignKey(
        'users.Company', on_delete=models.SET_NULL, null=True, blank=True,
    )
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.serial}-{self.correlative}' if self.serial else str(self.pk)

    def document_number(self):
        if self.serial and self.correlative:
            return f'{self.serial}-{str(self.correlative).zfill(6)}'
        return str(self.pk)

    class Meta:
        verbose_name = 'Guía de remisión remitente'
        verbose_name_plural = 'Guías de remisión remitente'
        ordering = ['-created_at']
