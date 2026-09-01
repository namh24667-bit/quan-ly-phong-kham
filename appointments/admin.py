from django.contrib import admin
from .models import Appointment, MedicalRecord

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display  = ['patient', 'doctor', 'date', 'start_time', 'end_time', 'status']
    list_filter   = ['status', 'date', 'doctor']
    search_fields = ['patient__full_name', 'doctor__full_name']
    ordering      = ['-date', '-start_time']
    date_hierarchy = 'date'

@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    list_display  = ['appointment', 'created_at']
    search_fields = ['appointment__patient__full_name']
