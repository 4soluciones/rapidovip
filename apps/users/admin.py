from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import (
    Company, Subsidiary, SubsidiarySerial, DocumentType, Nationality,
    Department, Province, District, Employee, Worker, Establishment,
    CompanyUser, UserSubsidiary, UserProfile,
)


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('short_name', 'ruc', 'business_name', 'is_enabled')


class SubsidiarySerialInline(admin.TabularInline):
    model = SubsidiarySerial
    extra = 0
    fields = ('company', 'service_type', 'document_type', 'serial', 'correlative', 'active')


@admin.register(Subsidiary)
class SubsidiaryAdmin(admin.ModelAdmin):
    list_display = ('short_name', 'name', 'ubigeo', 'phone', 'is_enabled')
    search_fields = ('name', 'short_name', 'ubigeo', 'address')
    inlines = [SubsidiarySerialInline]


@admin.register(SubsidiarySerial)
class SubsidiarySerialAdmin(admin.ModelAdmin):
    list_display = ('subsidiary', 'company', 'service_type', 'document_type', 'serial', 'correlative', 'active')
    list_filter = ('service_type', 'document_type', 'active')


admin.site.register(DocumentType)
admin.site.register(Nationality)
admin.site.register(Department)
admin.site.register(Province)
admin.site.register(District)
admin.site.register(Employee)
admin.site.register(Worker)
admin.site.register(Establishment)
admin.site.register(CompanyUser)
admin.site.register(UserSubsidiary)
admin.site.register(UserProfile)
