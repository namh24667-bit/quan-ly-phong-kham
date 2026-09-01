from django.contrib import admin
from .models import Doctor

@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display  = ['full_name', 'specialty', 'phone', 'is_active']
    list_filter   = ['specialty', 'is_active']
    search_fields = ['full_name', 'specialty']
    ordering      = ['full_name']
