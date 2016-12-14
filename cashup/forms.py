from django import forms
from .models import RegisterTakings, RegisterCashup

class RegisterTakingsForm(forms.ModelForm):
    class Meta:
        model = RegisterTakings
        fields = ['cash_takings', 'card_takings', 'total_takings']

class RegisterCashupForm(forms.ModelForm):
    class Meta:
        model = RegisterCashup
        fields = ['note_GBP50', 'note_GBP20', 'note_GBP10', 'note_GBP5',
                  'coin_GBP2', 'coin_GBP1', 'coin_50p', 'coin_20p',
                  'coin_10p', 'coin_5p', 'coin_2p', 'coin_1p', 'till_float']
