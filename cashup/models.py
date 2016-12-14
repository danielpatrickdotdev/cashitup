from django.db import models
from social_django.models import UserSocialAuth

class Outlet(models.Model):
    id = models.UUIDField(primary_key=True, editable=False)

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
    register = models.ForeignKey(Register, on_delete=models.SET_NULL,
                                    null=True, editable=False)
    register_open_time = models.DateTimeField(editable=False)
    updated = models.DateTimeField(auto_now=True)
    cash_takings = models.DecimalField(max_digits=12, decimal_places=2)
    card_takings = models.DecimalField(max_digits=12, decimal_places=2)
    total_takings = models.DecimalField(max_digits=12, decimal_places=2)
