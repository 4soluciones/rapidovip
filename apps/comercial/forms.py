from django import forms
from .models import *


class FormDriver(forms.ModelForm):
    class Meta:
        model = Driver
        fields = [
            'names', 'paternal_last_name', 'maternal_last_name',
            'address', 'phone', 'license_number', 'license_type', 'is_active',
        ]
        labels = {
            'names': 'Nombres',
            'paternal_last_name': 'Apellido paterno',
            'maternal_last_name': 'Apellido materno',
            'address': 'Dirección',
            'phone': 'Teléfono',
            'license_number': 'N° licencia de conducir',
            'license_type': 'Tipo de licencia',
            'is_active': 'Conductor activo',
        }
        widgets = {
            'names': forms.TextInput(attrs={
                'class': 'rv-form-control rv-input-required',
                'placeholder': 'Ej: Juan Carlos',
                'autocomplete': 'off',
            }),
            'paternal_last_name': forms.TextInput(attrs={
                'class': 'rv-form-control rv-input-required',
                'placeholder': 'Apellido paterno',
                'autocomplete': 'off',
            }),
            'maternal_last_name': forms.TextInput(attrs={
                'class': 'rv-form-control',
                'placeholder': 'Apellido materno',
                'autocomplete': 'off',
            }),
            'address': forms.TextInput(attrs={
                'class': 'rv-form-control',
                'placeholder': 'Dirección completa',
                'autocomplete': 'off',
            }),
            'phone': forms.TextInput(attrs={
                'class': 'rv-form-control',
                'placeholder': 'Ej: 999 888 777',
                'autocomplete': 'off',
            }),
            'license_number': forms.TextInput(attrs={
                'class': 'rv-form-control rv-input-required',
                'placeholder': 'N° de licencia',
                'autocomplete': 'off',
            }),
            'license_type': forms.Select(attrs={
                'class': 'rv-form-control rv-input-required',
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'rv-checkbox'}),
        }


class FormTruck(forms.ModelForm):
    class Meta:
        model = Truck
        fields = ['license_plate', 'num_axle', 'year', 'truck_model', 'drive_type', 'contact_phone',
                  'certificate', 'engine', 'chassis', 'color', 'fuel_type', 'owner', 'condition_owner',
                  'technical_review_expiration_date', 'soat_expiration_date', 'capacidad_kg', 'capacidad_m3',
                  'is_active']
        labels = {
            'license_plate': 'Placa',
            'num_axle': 'N° de ejes',
            'year': 'Año de fabricación',
            'truck_model': 'Modelo',
            'drive_type': 'Tipo de unidad',
            'contact_phone': 'Teléfono de contacto',
            'certificate': 'Certificado M.T.C.',
            'engine': 'Motor',
            'chassis': 'Chasis',
            'color': 'Color',
            'fuel_type': 'Combustible',
            'owner': 'Propietario',
            'condition_owner': 'Condición de propiedad',
            'technical_review_expiration_date': 'Vencimiento revisión técnica',
            'soat_expiration_date': 'Vencimiento SOAT',
            'capacidad_kg': 'Capacidad (kg)',
            'capacidad_m3': 'Capacidad (m³)',
            'is_active': 'Unidad activa',
        }

        widgets = {
            'license_plate': forms.TextInput(
                attrs={
                    'class': 'rv-form-control rv-input-required',
                    'placeholder': 'Ej: ABC-123',
                    'autocomplete': 'off',
                }
            ),
            'num_axle': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Ingrese N de ejes',
                    'type': 'number',
                    'autocomplete': 'off',
                }
            ),
            'year': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Ingrese  Año',
                    'required': 'true',
                    'type': 'number',
                    'autocomplete': 'off',
                }
            ),
            'truck_model': forms.Select(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Selectione Modelo',
                    # 'aria-describedby': 'serieHelpInline',

                }
            ),
            'drive_type': forms.Select(
                attrs={
                    'class': 'rv-form-control rv-input-required',
                }
            ),
            'contact_phone': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Ingrese Telefono de contacto',
                    'autocomplete': 'off',
                }
            ),
            'certificate': forms.TextInput(
                attrs={
                    'class': 'rv-form-control',
                    'placeholder': 'Certificado M.T.C.',
                    'autocomplete': 'off',
                }
            ),
            'capacidad_kg': forms.NumberInput(
                attrs={
                    'class': 'rv-form-control',
                    'placeholder': '0.00',
                    'step': '0.01',
                    'min': '0',
                }
            ),
            'capacidad_m3': forms.NumberInput(
                attrs={
                    'class': 'rv-form-control',
                    'placeholder': '0.00',
                    'step': '0.01',
                    'min': '0',
                }
            ),
            'is_active': forms.CheckboxInput(
                attrs={'class': 'rv-checkbox'}
            ),

            'engine': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Numero  de motor',
                    'autocomplete': 'off',
                }
            ),
            'chassis': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Numero  de chasis',
                    'autocomplete': 'off',
                }
            ),
            'color': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Color',
                    'autocomplete': 'off',
                }
            ),
            'fuel_type': forms.Select(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Seleccione Tipo de Combustible',
                    # 'aria-describedby': 'serieHelpInline',

                }
            ),
            'owner': forms.Select(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Seleccione Dueño',
                    # 'aria-describedby': 'serieHelpInline',

                }
            ),
            'condition_owner': forms.Select(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Seleccione Condicions',
                    # 'aria-describedby': 'serieHelpInline',

                }
            ),
            'technical_review_expiration_date': forms.DateInput(
                format=('%Y-%m-%d'),
                attrs={
                    'class': 'form-control',
                    'type': 'date',
                }
            ),
            'soat_expiration_date': forms.DateInput(
                format=('%Y-%m-%d'),
                attrs={
                    'class': 'form-control',
                    'type': 'date',
                }
            ),
        }


class FormProgramming(forms.ModelForm):
    class Meta:
        model = Programming
        fields = [
            'departure_date', 'arrival_date', 'service_type', 'weight',
            'truck', 'subsidiary', 'observation', 'truck_exit', 'status',
        ]
        labels = {
            'departure_date': 'Fecha Programada',
            'arrival_date': 'Fecha de llegada',
            'service_type': 'Servicio',
            'weight': 'Peso',
            'truck': 'Tracto',
            'subsidiary': 'Sucursal',
            'observation': 'Observación',
            'truck_exit': 'Hora de salida',
            'status': 'Estado',
        }

        widgets = {
            'departure_date': forms.DateInput(
                format=('%Y-%m-%d'),
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Ingrese Fecha Programada',
                    'type': 'date',
                    'required': 'true',
                    'autocomplete': 'off',
                }
            ),
            'arrival_date': forms.DateInput(
                format=('%Y-%m-%d'),
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Ingrese Fecha de llegada',
                    'type': 'date',
                    'autocomplete': 'off',
                }
            ),
            'service_type': forms.Select(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Seleccione Servicio',
                }
            ),
            'weight': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Ingrese Peso',
                    'type': 'number',
                    'autocomplete': 'off',
                }
            ),
            'truck': forms.Select(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Seleccione Tracto',
                }
            ),
            'subsidiary': forms.Select(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Seleccione Sucursal',
                }
            ),
            'observation': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Ingrese Observación',
                    'autocomplete': 'off',
                }
            ),
            'truck_exit': forms.DateTimeInput(
                format='%Y-%m-%dT%H:%M',
                attrs={
                    'class': 'form-control',
                    'type': 'datetime-local',
                    'autocomplete': 'off',
                }
            ),
            'status': forms.Select(
                attrs={
                    'class': 'form-control',
                }
            ),
        }

