import re
from datetime import datetime
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from appointments.models import MedicalRecord


def _snapshot_money(value):
    if not isinstance(value, str) or re.fullmatch(r'(?:0|[1-9][0-9]{0,9})(?:\.[0-9]{1,2})?', value) is None:
        raise ValueError('Snapshot amount must be a non-negative decimal string with at most two decimal places.')
    return Decimal(value)


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
        MedicalRecord, on_delete=models.PROTECT, related_name='prescriptions',
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
        MedicalRecord, on_delete=models.PROTECT, related_name='invoice',
        verbose_name='Hồ sơ khám',
    )
    services = models.ManyToManyField(Service, blank=True, related_name='invoices', verbose_name='Dịch vụ')
    medicine_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), verbose_name='Tiền thuốc')
    service_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), verbose_name='Tiền dịch vụ')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), verbose_name='Tổng tiền')
    status = models.CharField(max_length=7, choices=STATUS_CHOICES, default='Pending', verbose_name='Trạng thái')
    paid_snapshot = models.JSONField(null=True, blank=True)
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
        if self.status == 'Paid':
            return self.total_amount
        self.medicine_total, self.service_total, self.total_amount = self.calculate_totals()
        if save:
            type(self).objects.filter(pk=self.pk).update(
                medicine_total=self.medicine_total,
                service_total=self.service_total,
                total_amount=self.total_amount,
            )
        return self.total_amount

    def build_paid_snapshot(self):
        if self.status != 'Pending' or self.paid_snapshot is not None:
            raise ValueError('Only an unsnapshotted pending invoice can be captured.')

        medicines = []
        for prescription in self.medical_record.prescriptions.select_related('medicine').order_by('pk'):
            unit_price = prescription.medicine.unit_price
            medicines.append({
                'prescription_id': prescription.pk,
                'medicine_id': prescription.medicine_id,
                'name': prescription.medicine.name,
                'unit': prescription.medicine.unit,
                'quantity': prescription.quantity,
                'dosage': prescription.dosage,
                'unit_price': str(unit_price),
                'line_total': str(prescription.quantity * unit_price),
            })

        services = []
        for service in self.services.all().order_by('pk'):
            services.append({
                'service_id': service.pk,
                'name': service.name,
                'unit_price': str(service.price),
                'line_total': str(service.price),
            })

        snapshot = {
            'schema_version': 1,
            'captured_at': timezone.now().isoformat(),
            'source': 'captured_at_payment',
            'medicines': medicines,
            'services': services,
            'totals': {
                'medicine_total': str(self.medicine_total),
                'service_total': str(self.service_total),
                'total_amount': str(self.total_amount),
            },
        }
        return self.validate_paid_snapshot(snapshot)

    def validate_paid_snapshot(self, snapshot):
        """Return a usable snapshot, or reject incomplete and inconsistent data."""
        if not isinstance(snapshot, dict) or type(snapshot.get('schema_version')) is not int:
            raise ValueError('Snapshot structure is invalid.')
        if snapshot['schema_version'] != 1:
            raise ValueError('Snapshot version is not supported.')
        if snapshot.get('source') != 'captured_at_payment':
            raise ValueError('Snapshot source is invalid.')
        captured_at = snapshot.get('captured_at')
        if not isinstance(captured_at, str):
            raise ValueError('Snapshot capture time is invalid.')
        try:
            datetime.fromisoformat(captured_at)
        except ValueError as exc:
            raise ValueError('Snapshot capture time is invalid.') from exc

        medicines = snapshot.get('medicines')
        services = snapshot.get('services')
        totals = snapshot.get('totals')
        if not isinstance(medicines, list) or not isinstance(services, list) or not isinstance(totals, dict):
            raise ValueError('Snapshot lines or totals are missing.')

        medicine_total = Decimal('0.00')
        for item in medicines:
            if not isinstance(item, dict):
                raise ValueError('Snapshot medicine line is invalid.')
            if any(type(item.get(key)) is not int or item[key] < 1 for key in
                   ('prescription_id', 'medicine_id', 'quantity')):
                raise ValueError('Snapshot medicine identifiers or quantity are invalid.')
            if any(not isinstance(item.get(key), str) for key in ('name', 'unit', 'dosage')):
                raise ValueError('Snapshot medicine description is invalid.')
            unit_price = _snapshot_money(item.get('unit_price'))
            line_total = _snapshot_money(item.get('line_total'))
            if line_total != unit_price * item['quantity']:
                raise ValueError('Snapshot medicine line total does not match.')
            medicine_total += line_total

        service_total = Decimal('0.00')
        for item in services:
            if not isinstance(item, dict):
                raise ValueError('Snapshot service line is invalid.')
            if type(item.get('service_id')) is not int or item['service_id'] < 1:
                raise ValueError('Snapshot service identifier is invalid.')
            if not isinstance(item.get('name'), str):
                raise ValueError('Snapshot service name is invalid.')
            unit_price = _snapshot_money(item.get('unit_price'))
            line_total = _snapshot_money(item.get('line_total'))
            if line_total != unit_price:
                raise ValueError('Snapshot service line total does not match.')
            service_total += line_total

        if (medicine_total != _snapshot_money(totals.get('medicine_total'))
                or service_total != _snapshot_money(totals.get('service_total'))
                or medicine_total + service_total != _snapshot_money(totals.get('total_amount'))
                or medicine_total != self.medicine_total
                or service_total != self.service_total
                or medicine_total + service_total != self.total_amount):
            raise ValueError('Snapshot totals do not match the invoice.')
        return snapshot
