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
    readonly_fields = ('medicine_total', 'service_total', 'total_amount', 'created_at')

    @admin.display(description='Bệnh nhân')
    def patient_name(self, obj):
        return obj.medical_record.appointment.patient.full_name
