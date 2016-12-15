from django.db import models
from django.urls import reverse
from social_django.models import UserSocialAuth
import decimal

class Outlet(models.Model):
    id = models.UUIDField(primary_key=True, editable=False)
    name = models.CharField(max_length=256)

class Register(models.Model):
    id = models.UUIDField(primary_key=True, editable=False)
    vend_user = models.ForeignKey(UserSocialAuth, on_delete=models.CASCADE)
    name = models.CharField(max_length=256)
    outlet = models.ForeignKey(Outlet, on_delete=models.CASCADE)
    is_open = models.BooleanField(default=False)
    open_time = models.DateTimeField(blank=True, null=True)
    close_time = models.DateTimeField(blank=True, null=True)
    updated = models.DateTimeField(auto_now=True)

class RegisterTakings(models.Model):
    register = models.ForeignKey(Register, on_delete=models.CASCADE,
                                    editable=False)
    register_open_time = models.DateTimeField(editable=False)
    updated = models.DateTimeField(auto_now=True)
    cash_takings = models.DecimalField(max_digits=12, decimal_places=2)
    card_takings = models.DecimalField(max_digits=12, decimal_places=2)
    total_takings = models.DecimalField(max_digits=12, decimal_places=2)

class RegisterCashup(models.Model):
    register_takings = models.ForeignKey(RegisterTakings, on_delete=models.CASCADE,
                                    editable=False)
    note_GBP50 = models.PositiveIntegerField("£50 notes", default=0)
    note_GBP20 = models.PositiveIntegerField("£20 notes", default=0)
    note_GBP10 = models.PositiveIntegerField("£10 notes", default=0)
    note_GBP5 = models.PositiveIntegerField("£5 notes", default=0)
    coin_GBP2 = models.PositiveIntegerField("£2 coins", default=0)
    coin_GBP1 = models.PositiveIntegerField("£1 coins", default=0)
    coin_50p = models.PositiveIntegerField("50p coins", default=0)
    coin_20p = models.PositiveIntegerField("20p coins", default=0)
    coin_10p = models.PositiveIntegerField("10p coins", default=0)
    coin_5p = models.PositiveIntegerField("5p coins", default=0)
    coin_2p = models.PositiveIntegerField("2p coins", default=0)
    coin_1p = models.PositiveIntegerField("1p coins", default=0)
    till_float = models.DecimalField(max_digits=12, decimal_places=2,
                                default=decimal.Decimal('225.00'))
    till_total = models.DecimalField(max_digits=12, decimal_places=2,
                                blank=True,  null=True, editable=False)
    till_difference = models.DecimalField(max_digits=12, decimal_places=2,
                                blank=True,  null=True, editable=False)
