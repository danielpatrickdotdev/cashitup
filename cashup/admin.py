from django.contrib import admin
from .models import Outlet, Register, RegisterTakings

admin.site.register(Outlet)

admin.site.register(Register)

@admin.register(RegisterTakings)
class RegisterTakingsAdmin(admin.ModelAdmin):
    readonly_fields = ('register', 'register_open_time')
