from django.contrib import admin
from apps.sales import models


class UnitAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'is_enabled')
    list_editable = ('description', 'is_enabled')
    show_full_result_count = False


admin.site.register(models.Unit, UnitAdmin)
admin.site.register(models.Client)
