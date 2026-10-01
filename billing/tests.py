from decimal import Decimal
from datetime import date, time

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

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


class InvoiceLockTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = cls.make_user('admin', 'admin')
        cls.staff = cls.make_user('staff', 'staff')
        cls.doctor_user = cls.make_user('doctor', 'doctor')
        cls.doctor = Doctor.objects.create(
            user=cls.doctor_user, full_name='Doctor A', specialty='General'
        )
        cls.patient = Patient.objects.create(
            full_name='Patient A', date_of_birth='1990-01-01',
            gender='M', phone='0900000001',
        )
        cls.service_a = Service.objects.create(name='Service A', price='100000')
        cls.service_b = Service.objects.create(name='Service B', price='200000')
        cls.pending_invoice = cls.make_invoice('Pending', 8)
        cls.paid_invoice = cls.make_invoice('Paid', 9)
        cls.admin_payment_invoice = cls.make_invoice('Pending', 10)
        cls.staff_payment_invoice = cls.make_invoice('Pending', 11)
        cls.pending_invoice.services.add(cls.service_a)
        cls.pending_invoice.recalculate()
        cls.paid_invoice.services.add(cls.service_a)
        cls.paid_invoice.recalculate()

    @classmethod
    def make_user(cls, username, role):
        user = User.objects.create_user(username=username)
        user.profile.role = role
        user.profile.save()
        return user

    @classmethod
    def make_invoice(cls, status, hour):
        appointment = Appointment.objects.create(
            patient=cls.patient, doctor=cls.doctor, date=date(2026, 10, 5),
            start_time=time(hour), end_time=time(hour, 30), status='done',
        )
        record = MedicalRecord.objects.create(
            appointment=appointment, symptoms='A', diagnosis='A', treatment='A'
        )
        return Invoice.objects.create(medical_record=record, status=status)

    def test_staff_and_admin_can_edit_pending_invoice(self):
        cases = [
            (self.staff, [self.service_b]),
            (self.admin, [self.service_a, self.service_b]),
        ]
        for user, services in cases:
            with self.subTest(role=user.profile.role):
                self.client.force_login(user)
                response = self.client.post(
                    reverse('billing:update', args=[self.pending_invoice.pk]),
                    {
                        'services': [service.pk for service in services],
                        'status': 'Paid',
                    },
                )

                self.assertEqual(response.status_code, 302)
                self.pending_invoice.refresh_from_db()
                self.assertEqual(self.pending_invoice.status, 'Pending')
                self.assertEqual(
                    set(self.pending_invoice.services.all()), set(services)
                )

    def test_paid_invoice_update_get_is_blocked(self):
        self.client.force_login(self.staff)

        response = self.client.get(
            reverse('billing:update', args=[self.paid_invoice.pk])
        )

        self.assertEqual(response.status_code, 403)

    def test_paid_invoice_update_post_keeps_status_services_and_total(self):
        self.client.force_login(self.admin)
        old_total = self.paid_invoice.total_amount

        response = self.client.post(
            reverse('billing:update', args=[self.paid_invoice.pk]),
            {'services': [self.service_b.pk], 'status': 'Pending'},
        )

        self.assertEqual(response.status_code, 403)
        self.paid_invoice.refresh_from_db()
        self.assertEqual(self.paid_invoice.status, 'Paid')
        self.assertEqual(list(self.paid_invoice.services.all()), [self.service_a])
        self.assertEqual(self.paid_invoice.total_amount, old_total)

    def test_staff_and_admin_can_mark_pending_invoice_paid(self):
        cases = [
            (self.staff, self.staff_payment_invoice),
            (self.admin, self.admin_payment_invoice),
        ]
        for user, invoice in cases:
            with self.subTest(role=user.profile.role):
                self.client.force_login(user)
                response = self.client.post(
                    reverse('billing:mark_paid', args=[invoice.pk])
                )

                self.assertEqual(response.status_code, 302)
                invoice.refresh_from_db()
                self.assertEqual(invoice.status, 'Paid')

    def test_paid_invoice_cannot_be_marked_paid_again(self):
        self.client.force_login(self.staff)

        response = self.client.post(
            reverse('billing:mark_paid', args=[self.paid_invoice.pk])
        )

        self.assertEqual(response.status_code, 403)
        self.paid_invoice.refresh_from_db()
        self.assertEqual(self.paid_invoice.status, 'Paid')

    def test_doctor_cannot_edit_or_mark_invoice_paid(self):
        self.client.force_login(self.doctor_user)

        edit_response = self.client.post(
            reverse('billing:update', args=[self.pending_invoice.pk]),
            {'services': [self.service_b.pk]},
        )
        paid_response = self.client.post(
            reverse('billing:mark_paid', args=[self.pending_invoice.pk])
        )

        self.assertEqual(edit_response.status_code, 302)
        self.assertEqual(paid_response.status_code, 302)
        self.pending_invoice.refresh_from_db()
        self.assertEqual(self.pending_invoice.status, 'Pending')
        self.assertEqual(list(self.pending_invoice.services.all()), [self.service_a])

    def test_paid_invoice_detail_remains_visible(self):
        for user in [self.staff, self.doctor_user]:
            with self.subTest(role=user.profile.role):
                self.client.force_login(user)
                response = self.client.get(
                    reverse('billing:detail', args=[self.paid_invoice.pk])
                )

                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'Đã thanh toán')
