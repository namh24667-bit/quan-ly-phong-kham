from django.contrib import admin

from .models import Appointment, MedicalRecord


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display  = ['patient', 'doctor', 'date', 'start_time', 'end_time', 'status']
    list_filter   = ['status', 'date', 'doctor']
    search_fields = ['patient__full_name', 'doctor__full_name']
    ordering      = ['-date', '-start_time']
    date_hierarchy = 'date'
    readonly_fields = ('status', 'created_at')

    def has_add_permission(self, request):
        # Appointment creation must use the website workflow so schedule,
        # active-patient/doctor, date, and conflict checks are applied.
        return False

    def has_change_permission(self, request, obj=None):
        if obj is not None:
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
    list_display  = ['appointment', 'created_at']
    search_fields = ['appointment__patient__full_name']
    readonly_fields = ('created_at',)

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if obj is not None:
            fields.append('appointment')
        return fields

    def has_add_permission(self, request):
        # Medical records must be created by the application workflow, which
        # also creates the pending invoice in the same transaction.
        return False

    def has_change_permission(self, request, obj=None):
        if obj is not None and self._is_locked(obj):
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj is not None and self._is_locked(obj):
            return False
        return super().has_delete_permission(request, obj)

    @staticmethod
    def _is_locked(record):
        if record.appointment.status != 'checked_in':
            return True
        return hasattr(record, 'invoice') and record.invoice.status == 'Paid'
