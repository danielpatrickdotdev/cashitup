from django import forms
from .models import RegisterTakings

class RegisterTakingsForm(forms.ModelForm):
    class Meta:
        model = RegisterTakings
        fields = ['cash_takings', 'card_takings', 'total_takings']
