from import_export.admin import ImportExportModelAdmin
from django.contrib import admin
from apps.comercial import models


class TruckBrandAdmin(ImportExportModelAdmin):
    list_display = ('name',)


admin.site.register(models.TruckBrand, TruckBrandAdmin)


class TruckModelAdmin(ImportExportModelAdmin):
    list_display = ('name', 'truck_brand')


admin.site.register(models.TruckModel, TruckModelAdmin)


class OwnerAdmin(ImportExportModelAdmin):
    list_display = ('name',)


admin.site.register(models.Owner, OwnerAdmin)


class TruckAdmin(ImportExportModelAdmin):
    list_display = ('license_plate', 'truck_model', 'drive_type', 'owner', 'is_active')
    list_filter = ('drive_type', 'is_active', 'fuel_type')
    search_fields = ('license_plate',)


admin.site.register(models.Truck, TruckAdmin)


class DriverAdmin(ImportExportModelAdmin):
    list_display = ('names', 'paternal_last_name', 'license_number', 'license_type', 'phone', 'is_active')
    list_filter = ('license_type', 'is_active')
    search_fields = ('names', 'paternal_last_name', 'maternal_last_name', 'license_number', 'phone')


admin.site.register(models.Driver, DriverAdmin)


class ProgrammingAdmin(ImportExportModelAdmin):
    list_display = ('id', 'departure_date', 'service_type', 'status', 'truck', 'subsidiary')
    list_filter = ('service_type', 'status', 'departure_date')
    search_fields = ('truck__license_plate', 'correlative', 'serial')


admin.site.register(models.Programming, ProgrammingAdmin)


class CargoManifestAdmin(ImportExportModelAdmin):
    list_display = (
        'id', 'serial', 'correlative', 'status', 'programming',
        'guides_count', 'total_weight', 'emit_date',
    )
    list_filter = ('status', 'emit_date')
    search_fields = ('serial', 'correlative', 'driver_name')


admin.site.register(models.CargoManifest, CargoManifestAdmin)


class SenderRemissionGuideAdmin(ImportExportModelAdmin):
    list_display = (
        'id', 'serial', 'correlative', 'status', 'order',
        'programming', 'cargo_manifest', 'emit_date',
    )
    list_filter = ('status', 'emit_date')
    search_fields = ('serial', 'correlative', 'order__id')


admin.site.register(models.SenderRemissionGuide, SenderRemissionGuideAdmin)


class CarrierRemissionGuideAdmin(ImportExportModelAdmin):
    list_display = (
        'id', 'serial', 'correlative', 'status', 'order',
        'programming', 'cargo_manifest', 'related_document', 'emit_date',
    )
    list_filter = ('status', 'emit_date')
    search_fields = ('serial', 'correlative', 'order__id', 'related_document', 'driver_name')


admin.site.register(models.CarrierRemissionGuide, CarrierRemissionGuideAdmin)
