from django import forms
from .models import *
from apps.users.models import District, Province, Department


class FormClient(forms.ModelForm):
    class Meta:
        model = Client
        fields = ('names', 'phone', 'email')


class UnitForm(forms.ModelForm):
    class Meta:
        model = Unit
        fields = ('name', 'description', 'is_enabled')
        labels = {
            'name': 'Código',
            'description': 'Descripción',
            'is_enabled': 'Estado',
        }
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'rv-form-control text-uppercase',
                'maxlength': '5',
                'placeholder': 'Ej. UND, KG, BTO',
            }),
            'description': forms.TextInput(attrs={
                'class': 'rv-form-control',
                'maxlength': '50',
                'placeholder': 'Ej. Unidad, Kilogramo, Bulto',
            }),
            'is_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_name(self):
        name = (self.cleaned_data.get('name') or '').strip().upper()
        if not name:
            raise forms.ValidationError('Ingrese el código de la unidad.')
        return name


class DeliveryDestinationForm(forms.ModelForm):
    class Meta:
        model = DeliveryDestination
        fields = ('name', 'district', 'is_enabled')
        labels = {
            'name': 'Nombre del destino',
            'district': 'Distrito (ubigeo)',
            'is_enabled': 'Estado',
        }
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'rv-form-control text-uppercase',
                'maxlength': '150',
                'placeholder': 'Ej. CHACHAPOYAS CENTRO, BAGUA REPARTO',
            }),
            'district': forms.Select(attrs={
                'class': 'rv-form-control',
                'id': 'id_delivery_district',
            }),
            'is_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Solo el distrito actual (edición) para no cargar todo el catálogo;
        # Select2 AJAX completa el resto.
        qs = District.objects.none()
        if self.instance and self.instance.pk and self.instance.district_id:
            qs = District.objects.filter(pk=self.instance.district_id)
        elif self.data.get('district'):
            qs = District.objects.filter(pk=self.data.get('district'))
        self.fields['district'].queryset = qs
        self.fields['district'].empty_label = 'Buscar distrito...'

    def clean_name(self):
        name = (self.cleaned_data.get('name') or '').strip().upper()
        if not name:
            raise forms.ValidationError('Ingrese el nombre del destino.')
        return name


def district_autocomplete_label(district):
    """Etiqueta legible en mayúsculas: DISTRITO · PROVINCIA · DEPARTAMENTO (ubigeo)."""
    district_name = (district.description or '').strip().upper() or district.id
    province = Province.objects.filter(pk=district.id[:4]).first() if district.id else None
    department = Department.objects.filter(pk=district.id[:2]).first() if district.id else None
    province_name = (province.description or '').strip().upper() if province else ''
    department_name = (department.description or '').strip().upper() if department else ''
    parts = [district_name]
    if province_name:
        parts.append(province_name)
    if department_name:
        parts.append(department_name)
    return f'{" · ".join(parts)} ({district.id})'