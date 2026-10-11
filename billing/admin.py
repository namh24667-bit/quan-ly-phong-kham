from django.contrib import admin

from .models import Invoice, Medicine, Prescription, Service


@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display = ('name', 'unit', 'unit_price')
    search_fields = ('name',)


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ('medical_record', 'medicine', 'quantity', 'dosage', 'amount')
    list_filter = ('medicine',)
    search_fields = ('medicine__name', 'medical_record__appointment__patient__full_name')

    def has_add_permission(self, request):
        # Prescription changes must use the website workflow so the related
        # pending invoice is recalculated in the same transaction.
        return False

    def has_change_permission(self, request, obj=None):
        if obj is not None:
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'price')
    search_fields = ('name',)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient_name', 'total_amount', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('medical_record__appointment__patient__full_name',)
    filter_horizontal = ('services',)
    readonly_fields = (
        'status', 'medicine_total', 'service_total', 'total_amount', 'created_at',
    )

    def has_add_permission(self, request):
        # Invoice creation and service changes must use the website workflow,
        # which creates/recalculates totals transactionally.
        return False

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if obj is not None:
            fields.append('medical_record')
        return fields

    def has_change_permission(self, request, obj=None):
        if obj is not None:
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description='Bệnh nhân')
    def patient_name(self, obj):
        return obj.medical_record.appointment.patient.full_name
