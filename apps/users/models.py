from django.db import models
from django.contrib.auth.models import User


class Company(models.Model):
    business_name = models.CharField('Razón social', max_length=200)
    short_name = models.CharField('Nombre corto', max_length=50)
    ruc = models.CharField('RUC', max_length=11, unique=True)
    address = models.CharField('Dirección', max_length=250, null=True, blank=True)
    phone = models.CharField('Teléfono', max_length=20, null=True, blank=True)
    is_enabled = models.BooleanField(default=True)

    def __str__(self):
        return self.short_name

    class Meta:
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'


class Subsidiary(models.Model):
    name = models.CharField('Nombre', max_length=100)
    short_name = models.CharField('Nombre corto', max_length=20)
    address = models.CharField('Dirección', max_length=250, null=True, blank=True)
    ubigeo = models.CharField('Ubigeo', max_length=6, blank=True, default='')
    color = models.CharField('Color', max_length=20, default='#0d3b66')
    phone = models.CharField('Teléfono', max_length=20, null=True, blank=True)
    is_enabled = models.BooleanField(default=True)

    def __str__(self):
        return self.short_name

    class Meta:
        verbose_name = 'Sede'
        verbose_name_plural = 'Sedes'


class SubsidiarySerial(models.Model):
    SERVICE_CHOICES = (
        ('E', 'Encomienda'),
        ('P', 'Programación'),
        ('R', 'Guía remitente'),
        ('T', 'Guía transportista'),
        ('A', 'Manifiesto de carga'),
    )
    DOCUMENT_TYPE_CHOICES = (
        ('T', 'Orden de servicio'),
        ('B', 'Boleta'),
        ('F', 'Factura'),
        ('G', 'Guía'),
    )
    subsidiary = models.ForeignKey(Subsidiary, on_delete=models.CASCADE, related_name='serials')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='serials')
    service_type = models.CharField(max_length=1, choices=SERVICE_CHOICES)
    document_type = models.CharField(max_length=1, choices=DOCUMENT_TYPE_CHOICES, default='T')
    serial = models.CharField(max_length=10, blank=True, default='')
    correlative = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)

    def __str__(self):
        return (
            f'{self.subsidiary.short_name} · {self.company.short_name} · '
            f'{self.get_service_type_display()} ({self.document_type})'
        )

    class Meta:
        unique_together = ('subsidiary', 'company', 'service_type', 'document_type')
        verbose_name = 'Serie por sede y servicio'
        verbose_name_plural = 'Series por sede y servicio'


class DocumentType(models.Model):
    id = models.CharField(primary_key=True, max_length=2)
    name = models.CharField(max_length=50)
    sunat_code = models.CharField(max_length=2, null=True, blank=True)

    @property
    def short_description(self):
        return self.name

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Tipo de documento'
        verbose_name_plural = 'Tipos de documento'


class Nationality(models.Model):
    id = models.CharField(primary_key=True, max_length=10)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Nacionalidad'
        verbose_name_plural = 'Nacionalidades'


class Department(models.Model):
    code = models.CharField(max_length=2, unique=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Province(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    code = models.CharField(max_length=4, unique=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class District(models.Model):
    province = models.ForeignKey(Province, on_delete=models.CASCADE)
    code = models.CharField(max_length=6, unique=True)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Employee(models.Model):
    LICENSE_CHOICES = (
        ('A', 'A-I'), ('A1', 'A-Ia'), ('A2', 'A-IIa'), ('A3', 'A-IIIa'),
        ('B', 'B-I'), ('C', 'C-I'), ('12', 'SIN LICENCIA'),
    )
    names = models.CharField(max_length=100)
    paternal_last_name = models.CharField(max_length=100, null=True, blank=True)
    maternal_last_name = models.CharField(max_length=100, null=True, blank=True)
    n_license = models.CharField(max_length=20, null=True, blank=True)
    license_type = models.CharField(max_length=5, choices=LICENSE_CHOICES, default='A')
    phone = models.CharField(max_length=15, null=True, blank=True)
    is_enabled = models.BooleanField(default=True)

    @property
    def full_name(self):
        return f'{self.names} {self.paternal_last_name or ""} {self.maternal_last_name or ""}'.strip()

    def __str__(self):
        return self.full_name

    class Meta:
        verbose_name = 'Empleado'
        verbose_name_plural = 'Empleados'


class Worker(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)

    def __str__(self):
        return self.employee.full_name

    class Meta:
        verbose_name = 'Trabajador'
        verbose_name_plural = 'Trabajadores'


class Establishment(models.Model):
    worker = models.ForeignKey(Worker, on_delete=models.CASCADE)
    subsidiary = models.ForeignKey(Subsidiary, on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.worker} - {self.subsidiary}'

    class Meta:
        verbose_name = 'Establecimiento'
        verbose_name_plural = 'Establecimientos'


class CompanyUser(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='companyuser')
    company_rotation = models.ForeignKey(Company, on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.user.username} - {self.company_rotation}'

    class Meta:
        verbose_name = 'Empresa del usuario'
        verbose_name_plural = 'Empresas del usuario'


class UserSubsidiary(models.Model):
    ROLE_CHOICES = (
        ('A', 'Administrador'),
        ('O', 'Operador'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    subsidiary = models.ForeignKey(Subsidiary, on_delete=models.CASCADE)
    rol = models.CharField(max_length=1, choices=ROLE_CHOICES, default='O')
    office = models.CharField(max_length=50, null=True, blank=True)
    printer = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return f'{self.user.username} - {self.subsidiary}'

    class Meta:
        unique_together = ('user', 'subsidiary')
        verbose_name = 'Usuario por sede'
        verbose_name_plural = 'Usuarios por sede'


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=15, null=True, blank=True)
    document_type = models.ForeignKey(DocumentType, on_delete=models.SET_NULL, null=True, blank=True)
    document_number = models.CharField(max_length=15, null=True, blank=True)
    subsidiary = models.ForeignKey(Subsidiary, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username

    class Meta:
        verbose_name = 'Perfil de usuario'
        verbose_name_plural = 'Perfiles de usuario'
