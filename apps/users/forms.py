from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User

from .models import Subsidiary, Company, UserSubsidiary


class FormLogin(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'id': 'id_username',
            'class': 'rv-auth-input',
            'placeholder': 'Usuario',
            'autocomplete': 'username',
        })
        self.fields['password'].widget.attrs.update({
            'id': 'id_password',
            'class': 'rv-auth-input',
            'placeholder': 'Contraseña',
            'autocomplete': 'current-password',
        })


class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'rv-form-control'}))
    password_confirm = forms.CharField(
        label='Confirmar contraseña',
        widget=forms.PasswordInput(attrs={'class': 'rv-form-control'}),
    )
    full_name = forms.CharField(
        label='Nombre completo',
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'rv-form-control'}),
    )
    phone = forms.CharField(
        label='Teléfono',
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={'class': 'rv-form-control'}),
    )
    subsidiary = forms.ModelChoiceField(
        queryset=Subsidiary.objects.filter(is_enabled=True),
        widget=forms.Select(attrs={'class': 'rv-form-control'}),
    )
    company = forms.ModelChoiceField(
        queryset=Company.objects.filter(is_enabled=True),
        widget=forms.Select(attrs={'class': 'rv-form-control'}),
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'rv-form-control'}),
            'email': forms.EmailInput(attrs={'class': 'rv-form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'rv-form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'rv-form-control'}),
        }

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('password') != cleaned.get('password_confirm'):
            raise forms.ValidationError('Las contraseñas no coinciden.')
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class AdminUserCreateForm(forms.ModelForm):
    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={'class': 'rv-form-control'}),
    )
    password_confirm = forms.CharField(
        label='Confirmar contraseña',
        widget=forms.PasswordInput(attrs={'class': 'rv-form-control'}),
    )
    full_name = forms.CharField(
        label='Nombre completo',
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'rv-form-control'}),
    )
    phone = forms.CharField(
        label='Teléfono',
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={'class': 'rv-form-control'}),
    )
    subsidiary = forms.ModelChoiceField(
        label='Sede',
        queryset=Subsidiary.objects.filter(is_enabled=True),
        widget=forms.Select(attrs={'class': 'rv-form-control'}),
    )
    company = forms.ModelChoiceField(
        label='Empresa',
        queryset=Company.objects.filter(is_enabled=True),
        widget=forms.Select(attrs={'class': 'rv-form-control'}),
    )
    rol = forms.ChoiceField(
        label='Rol en sede',
        choices=UserSubsidiary.ROLE_CHOICES,
        initial='O',
        widget=forms.Select(attrs={'class': 'rv-form-control'}),
    )

    class Meta:
        model = User
        fields = ('username', 'email')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'rv-form-control'}),
            'email': forms.EmailInput(attrs={'class': 'rv-form-control'}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.is_staff = self.cleaned_data.get('rol') == 'A'
        if commit:
            user.save()
        return user

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('password') != cleaned.get('password_confirm'):
            raise forms.ValidationError('Las contraseñas no coinciden.')
        if not Subsidiary.objects.filter(is_enabled=True).exists():
            raise forms.ValidationError('Debe crear al menos una sede antes de registrar usuarios.')
        if not Company.objects.filter(is_enabled=True).exists():
            raise forms.ValidationError('Debe crear al menos una empresa antes de registrar usuarios.')
        return cleaned


class AdminUserEditForm(forms.ModelForm):
    password = forms.CharField(
        label='Nueva contraseña',
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'rv-form-control',
            'placeholder': 'Dejar en blanco para no cambiar',
        }),
    )
    password_confirm = forms.CharField(
        label='Confirmar contraseña',
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'rv-form-control',
            'placeholder': 'Repetir solo si cambia la contraseña',
        }),
    )
    full_name = forms.CharField(
        label='Nombre completo',
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'rv-form-control'}),
    )
    phone = forms.CharField(
        label='Teléfono',
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={'class': 'rv-form-control'}),
    )
    subsidiary = forms.ModelChoiceField(
        label='Sede',
        queryset=Subsidiary.objects.filter(is_enabled=True),
        widget=forms.Select(attrs={'class': 'rv-form-control'}),
    )
    company = forms.ModelChoiceField(
        label='Empresa',
        queryset=Company.objects.filter(is_enabled=True),
        widget=forms.Select(attrs={'class': 'rv-form-control'}),
    )
    rol = forms.ChoiceField(
        label='Rol en sede',
        choices=UserSubsidiary.ROLE_CHOICES,
        widget=forms.Select(attrs={'class': 'rv-form-control'}),
    )
    is_active = forms.BooleanField(
        label='Usuario activo',
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'rv-checkbox'}),
    )

    class Meta:
        model = User
        fields = ('username', 'email')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'rv-form-control'}),
            'email': forms.EmailInput(attrs={'class': 'rv-form-control'}),
        }

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get('password')
        password_confirm = cleaned.get('password_confirm')
        if password or password_confirm:
            if password != password_confirm:
                raise forms.ValidationError('Las contraseñas no coinciden.')
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        user.is_staff = self.cleaned_data.get('rol') == 'A'
        if commit:
            user.save()
        return user


class SubsidiaryForm(forms.ModelForm):
    class Meta:
        model = Subsidiary
        fields = ('name', 'short_name', 'address', 'ubigeo', 'color', 'phone')
        labels = {
            'name': 'Nombre de la sede',
            'short_name': 'Código corto',
            'address': 'Dirección',
            'ubigeo': 'Ubigeo',
            'color': 'Color identificador',
            'phone': 'Teléfono',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'rv-form-control', 'placeholder': 'Ej: Sede Lima Centro'}),
            'short_name': forms.TextInput(attrs={'class': 'rv-form-control', 'placeholder': 'Ej: LIM'}),
            'address': forms.TextInput(attrs={'class': 'rv-form-control'}),
            'ubigeo': forms.TextInput(attrs={
                'class': 'rv-form-control',
                'placeholder': 'Ej: 150101',
                'maxlength': '6',
                'pattern': '[0-9]{6}',
                'title': 'Código ubigeo SUNAT de 6 dígitos',
            }),
            'color': forms.TextInput(attrs={'class': 'rv-form-control', 'type': 'color'}),
            'phone': forms.TextInput(attrs={'class': 'rv-form-control'}),
        }

    def clean_ubigeo(self):
        ubigeo = (self.cleaned_data.get('ubigeo') or '').strip()
        if ubigeo and (not ubigeo.isdigit() or len(ubigeo) != 6):
            raise forms.ValidationError('El ubigeo debe tener exactamente 6 dígitos numéricos.')
        return ubigeo


class SubsidiarySeriesForm(forms.Form):
    company = forms.ModelChoiceField(
        label='Empresa',
        queryset=Company.objects.filter(is_enabled=True),
        widget=forms.Select(attrs={'class': 'rv-form-control'}),
    )
    serial_ticket = forms.CharField(
        label='Serie tickets encomienda',
        max_length=10,
        required=False,
        widget=forms.TextInput(attrs={'class': 'rv-form-control', 'placeholder': 'Ej: T001'}),
    )
    serial_boleta = forms.CharField(
        label='Serie boletas',
        max_length=10,
        required=False,
        widget=forms.TextInput(attrs={'class': 'rv-form-control', 'placeholder': 'Ej: B001'}),
    )
    serial_factura = forms.CharField(
        label='Serie facturas',
        max_length=10,
        required=False,
        widget=forms.TextInput(attrs={'class': 'rv-form-control', 'placeholder': 'Ej: F001'}),
    )
    serial_manifiesto = forms.CharField(
        label='Serie programación',
        max_length=10,
        required=False,
        widget=forms.TextInput(attrs={'class': 'rv-form-control', 'placeholder': 'Ej: MF01'}),
    )
    serial_sender_guide = forms.CharField(
        label='Serie guía remitente',
        max_length=10,
        required=False,
        widget=forms.TextInput(attrs={'class': 'rv-form-control', 'placeholder': 'Ej: GR01'}),
    )
    serial_carrier_guide = forms.CharField(
        label='Serie guía transportista',
        max_length=10,
        required=False,
        widget=forms.TextInput(attrs={'class': 'rv-form-control', 'placeholder': 'Ej: GT01'}),
    )
    serial_cargo_manifest = forms.CharField(
        label='Serie manifiesto de carga',
        max_length=10,
        required=False,
        widget=forms.TextInput(attrs={'class': 'rv-form-control', 'placeholder': 'Ej: MC01'}),
    )


class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ('business_name', 'short_name', 'ruc', 'address', 'phone')
        labels = {
            'business_name': 'Razón social',
            'short_name': 'Nombre corto',
            'ruc': 'RUC',
            'address': 'Dirección',
            'phone': 'Teléfono',
        }
        widgets = {
            'business_name': forms.TextInput(attrs={
                'class': 'rv-form-control',
                'placeholder': 'Ej: Transportes Unidos S.A.C.',
            }),
            'short_name': forms.TextInput(attrs={
                'class': 'rv-form-control',
                'placeholder': 'Ej: TUNI',
            }),
            'ruc': forms.TextInput(attrs={
                'class': 'rv-form-control',
                'maxlength': '11',
                'placeholder': '11 dígitos',
            }),
            'address': forms.TextInput(attrs={'class': 'rv-form-control'}),
            'phone': forms.TextInput(attrs={'class': 'rv-form-control'}),
        }


class CompanyEditForm(CompanyForm):
    class Meta(CompanyForm.Meta):
        fields = ('business_name', 'short_name', 'ruc', 'address', 'phone', 'is_enabled')
        labels = {
            **CompanyForm.Meta.labels,
            'is_enabled': 'Empresa activa',
        }
        widgets = {
            **CompanyForm.Meta.widgets,
            'is_enabled': forms.CheckboxInput(attrs={'class': 'rv-checkbox'}),
        }
