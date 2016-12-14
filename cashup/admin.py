from django.contrib import admin
from .models import Outlet, Register, RegisterTakings, RegisterCashup

admin.site.register(Outlet)

admin.site.register(Register)

@admin.register(RegisterTakings)
class RegisterTakingsAdmin(admin.ModelAdmin):
    readonly_fields = ('register', 'register_open_time')

@admin.register(RegisterCashup)
class RegisterTakingsAdmin(admin.ModelAdmin):
    readonly_fields = ('register_takings', 'till_total', 'till_difference')