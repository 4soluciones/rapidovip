from django import forms
from .models import *


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
