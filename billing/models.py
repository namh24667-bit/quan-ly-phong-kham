from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from appointments.models import MedicalRecord


class Medicine(models.Model):
    name = models.CharField(max_length=150, unique=True, verbose_name='Tên thuốc')
    unit_price = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0)], verbose_name='Đơn giá',
    )
    unit = models.CharField(max_length=30, verbose_name='Đơn vị')

    class Meta:
        verbose_name = 'Thuốc'
        verbose_name_plural = 'Thuốc'
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.unit})'


class Prescription(models.Model):
    medical_record = models.ForeignKey(
        MedicalRecord, on_delete=models.CASCADE, related_name='prescriptions',
        verbose_name='Hồ sơ khám',
    )
    medicine = models.ForeignKey(Medicine, on_delete=models.PROTECT, verbose_name='Thuốc')
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)], verbose_name='Số lượng'
    )
    dosage = models.CharField(max_length=255, verbose_name='Liều dùng')

    class Meta:
        verbose_name = 'Đơn thuốc'
        verbose_name_plural = 'Đơn thuốc'

    def __str__(self):
        return f'{self.medicine.name} x {self.quantity}'

    @property
    def amount(self):
        return self.quantity * self.medicine.unit_price


class Service(models.Model):
    name = models.CharField(max_length=150, unique=True, verbose_name='Tên dịch vụ')
    price = models.DecimalField(
        max_digits=12, decimal_places=2,
        validators=[MinValueValidator(0)], verbose_name='Giá tiền',
    )

    class Meta:
        verbose_name = 'Dịch vụ'
        verbose_name_plural = 'Dịch vụ'
        ordering = ['name']

    def __str__(self):
        return self.name


class Invoice(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Chờ thanh toán'),
        ('Paid', 'Đã thanh toán'),
    ]
    medical_record = models.OneToOneField(
        MedicalRecord, on_delete=models.CASCADE, related_name='invoice',
        verbose_name='Hồ sơ khám',
    )
    services = models.ManyToManyField(Service, blank=True, related_name='invoices', verbose_name='Dịch vụ')
    medicine_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), verbose_name='Tiền thuốc')
    service_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), verbose_name='Tiền dịch vụ')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), verbose_name='Tổng tiền')
    status = models.CharField(max_length=7, choices=STATUS_CHOICES, default='Pending', verbose_name='Trạng thái')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Ngày tạo')

    class Meta:
        verbose_name = 'Hóa đơn'
        verbose_name_plural = 'Hóa đơn'
        ordering = ['-created_at']

    def __str__(self):
        return f'Hóa đơn #{self.pk} - {self.medical_record.appointment.patient.full_name}'

    def calculate_totals(self):
        medicine_total = sum(
            (prescription.amount for prescription in self.medical_record.prescriptions.select_related('medicine')),
            Decimal('0.00'),
        )
        service_total = sum((service.price for service in self.services.all()), Decimal('0.00'))
        return medicine_total, service_total, medicine_total + service_total

    def recalculate(self, save=True):
        self.medicine_total, self.service_total, self.total_amount = self.calculate_totals()
        if save:
            type(self).objects.filter(pk=self.pk).update(
                medicine_total=self.medicine_total,
                service_total=self.service_total,
                total_amount=self.total_amount,
            )
        return self.total_amount
