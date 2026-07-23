from django.contrib import admin
from apps.sales import models


class UnitAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'is_enabled')
    list_editable = ('description', 'is_enabled')
    show_full_result_count = False


class DeliveryDestinationAdmin(admin.ModelAdmin):
    list_display = ('name', 'district', 'is_enabled')
    list_filter = ('is_enabled',)
    search_fields = ('name', 'district__description', 'district__id')
    show_full_result_count = False


admin.site.register(models.Unit, UnitAdmin)
admin.site.register(models.DeliveryDestination, DeliveryDestinationAdmin)
admin.site.register(models.Client)
