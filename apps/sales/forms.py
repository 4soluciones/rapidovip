from django import forms
from .models import *


class FormClient(forms.ModelForm):
    class Meta:
        model = Client
        fields = ('names', 'phone', 'email')
