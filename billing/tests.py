from decimal import Decimal

from django.test import TestCase

from appointments.models import Appointment, MedicalRecord
from doctors.models import Doctor
from patients.models import Patient

from .models import Invoice, Medicine, Prescription, Service


class InvoiceTotalTests(TestCase):
    def setUp(self):
        patient = Patient.objects.create(
            full_name='Nguyen Van A', date_of_birth='1990-01-01', gender='M', phone='0900000000',
        )
        doctor = Doctor.objects.create(
            full_name='Dr. Test', specialty='General', phone='0910000000',
        )
        appointment = Appointment.objects.create(
            patient=patient, doctor=doctor, date='2026-09-22',
            start_time='09:00', end_time='09:30', status='done',
        )
        self.record = MedicalRecord.objects.create(
            appointment=appointment, symptoms='Cough', diagnosis='Cold', treatment='Rest',
        )

    def test_total_is_medicine_quantity_times_price_plus_services(self):
        medicine = Medicine.objects.create(name='Medicine A', unit_price='12500.00', unit='vien')
        Prescription.objects.create(
            medical_record=self.record, medicine=medicine, quantity=3, dosage='1 vien/ngay',
        )
        service = Service.objects.create(name='Consultation', price='50000.00')
        invoice = Invoice.objects.create(medical_record=self.record)
        invoice.services.add(service)

        self.assertEqual(invoice.recalculate(), Decimal('87500.00'))
        invoice.refresh_from_db()
        self.assertEqual(invoice.medicine_total, Decimal('37500.00'))
        self.assertEqual(invoice.service_total, Decimal('50000.00'))
        self.assertEqual(invoice.total_amount, Decimal('87500.00'))