from decimal import Decimal
from datetime import time

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from appointments.models import Appointment, MedicalRecord
from doctors.models import Doctor
from patients.models import Patient

from .forms import PrescriptionForm
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
            patient=patient, doctor=doctor, date=timezone.localdate(),
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
        cls.paid_invoice = cls.make_invoice('Pending', 9)
        cls.admin_payment_invoice = cls.make_invoice('Pending', 10)
        cls.staff_payment_invoice = cls.make_invoice('Pending', 11)
        cls.pending_invoice.services.add(cls.service_a)
        cls.pending_invoice.recalculate()
        cls.paid_invoice.services.add(cls.service_a)
        cls.paid_invoice.recalculate()
        cls.paid_invoice.status = 'Paid'
        cls.paid_invoice.save(update_fields=['status'])

    @classmethod
    def make_user(cls, username, role):
        user = User.objects.create_user(username=username)
        user.profile.role = role
        user.profile.save()
        return user

    @classmethod
    def make_invoice(cls, status, hour, appointment_status='done'):
        appointment = Appointment.objects.create(
            patient=cls.patient, doctor=cls.doctor, date=timezone.localdate(),
            start_time=time(hour), end_time=time(hour, 30),
            status=appointment_status,
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
                invoice.services.add(self.service_a)
                self.client.force_login(user)
                response = self.client.post(
                    reverse('billing:mark_paid', args=[invoice.pk])
                )

                self.assertEqual(response.status_code, 302)
                invoice.refresh_from_db()
                self.assertEqual(invoice.status, 'Paid')
                self.assertEqual(invoice.total_amount, Decimal('100000.00'))

    def test_non_done_appointments_cannot_be_marked_paid(self):
        self.client.force_login(self.staff)

        for hour, status in enumerate(
                ['pending', 'confirmed', 'checked_in', 'cancelled'], start=12):
            with self.subTest(status=status):
                invoice = self.make_invoice('Pending', hour, status)
                response = self.client.post(
                    reverse('billing:mark_paid', args=[invoice.pk])
                )

                self.assertEqual(response.status_code, 403)
                invoice.refresh_from_db()
                self.assertEqual(invoice.status, 'Pending')

    def test_paid_invoice_recalculate_keeps_existing_totals(self):
        old_medicine_total = self.paid_invoice.medicine_total
        old_service_total = self.paid_invoice.service_total
        old_total = self.paid_invoice.total_amount
        self.paid_invoice.services.add(self.service_b)

        result = self.paid_invoice.recalculate()

        self.paid_invoice.refresh_from_db()
        self.assertEqual(result, old_total)
        self.assertEqual(self.paid_invoice.medicine_total, old_medicine_total)
        self.assertEqual(self.paid_invoice.service_total, old_service_total)
        self.assertEqual(self.paid_invoice.total_amount, old_total)

    def test_mark_paid_button_only_shows_for_done_appointment(self):
        checked_in_invoice = self.make_invoice('Pending', 16, 'checked_in')
        self.client.force_login(self.staff)

        checked_in_response = self.client.get(
            reverse('billing:detail', args=[checked_in_invoice.pk])
        )
        done_response = self.client.get(
            reverse('billing:detail', args=[self.pending_invoice.pk])
        )

        self.assertNotContains(checked_in_response, 'Đánh dấu đã thanh toán')
        self.assertContains(done_response, 'Đánh dấu đã thanh toán')

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

    def test_authorized_users_see_invoice_print_action(self):
        for user in [self.admin, self.staff, self.doctor_user]:
            with self.subTest(role=user.profile.role):
                self.client.force_login(user)

                response = self.client.get(
                    reverse('billing:detail', args=[self.pending_invoice.pk])
                )

                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'In hóa đơn')
                self.assertContains(response, 'onclick="window.print()"')


class BillingValueValidationTests(TestCase):
    def setUp(self):
        patient = Patient.objects.create(
            full_name='Patient Validation', date_of_birth='1990-01-01',
            gender='M', phone='0900000002',
        )
        doctor = Doctor.objects.create(
            full_name='Doctor Validation', specialty='General'
        )
        appointment = Appointment.objects.create(
            patient=patient, doctor=doctor, date=timezone.localdate(),
            start_time=time(9), end_time=time(10), status='checked_in',
        )
        self.record = MedicalRecord.objects.create(
            appointment=appointment, symptoms='A', diagnosis='A', treatment='A'
        )
        self.medicine = Medicine.objects.create(
            name='Valid Medicine', unit_price='10000', unit='Viên'
        )

    def test_negative_medicine_price_is_invalid(self):
        medicine = Medicine(name='Negative Medicine', unit_price='-1', unit='Viên')

        with self.assertRaises(ValidationError):
            medicine.full_clean()

    def test_zero_medicine_price_is_valid(self):
        medicine = Medicine(name='Free Medicine', unit_price='0', unit='Viên')

        medicine.full_clean()

    def test_negative_service_price_is_invalid(self):
        service = Service(name='Negative Service', price='-1')

        with self.assertRaises(ValidationError):
            service.full_clean()

    def test_zero_service_price_is_valid(self):
        service = Service(name='Free Service', price='0')

        service.full_clean()

    def test_zero_prescription_quantity_is_invalid(self):
        form = PrescriptionForm(data={
            'medicine': self.medicine.pk,
            'quantity': 0,
            'dosage': 'Ngày 1 lần',
        })

        self.assertFalse(form.is_valid())
        self.assertIn('quantity', form.errors)

    def test_negative_prescription_quantity_is_invalid(self):
        form = PrescriptionForm(data={
            'medicine': self.medicine.pk,
            'quantity': -1,
            'dosage': 'Ngày 1 lần',
        })

        self.assertFalse(form.is_valid())
        self.assertIn('quantity', form.errors)

    def test_positive_prescription_quantity_is_valid(self):
        form = PrescriptionForm(data={
            'medicine': self.medicine.pk,
            'quantity': 1,
            'dosage': 'Ngày 1 lần',
        })

        self.assertTrue(form.is_valid())


class BillingListFilterTests(TestCase):
    def setUp(self):
        self.admin = self.make_user('billing_list_admin', 'admin')
        self.doctor_user = self.make_user('billing_list_doctor_a', 'doctor')
        self.other_doctor_user = self.make_user('billing_list_doctor_b', 'doctor')
        self.doctor = Doctor.objects.create(
            user=self.doctor_user, full_name='Invoice Doctor A', specialty='General'
        )
        self.other_doctor = Doctor.objects.create(
            user=self.other_doctor_user, full_name='Invoice Doctor B', specialty='General'
        )
        self.patient = Patient.objects.create(
            full_name='Invoice Patient An', date_of_birth='1990-01-01',
            gender='M', phone='0900000201',
        )
        self.other_patient = Patient.objects.create(
            full_name='Invoice Patient Binh', date_of_birth='1991-01-01',
            gender='M', phone='0900000202',
        )
        self.pending_invoice = self.make_invoice(
            self.patient, self.doctor, 'Pending', 8
        )
        self.paid_invoice = self.make_invoice(
            self.other_patient, self.other_doctor, 'Paid', 9
        )

    def make_user(self, username, role):
        user = User.objects.create_user(username=username)
        user.profile.role = role
        user.profile.save()
        return user

    def make_invoice(self, patient, doctor, status, hour):
        appointment = Appointment.objects.create(
            patient=patient, doctor=doctor, date=timezone.localdate(),
            start_time=time(hour), end_time=time(hour, 30), status='done',
        )
        record = MedicalRecord.objects.create(
            appointment=appointment, symptoms='A', diagnosis='A', treatment='A'
        )
        return Invoice.objects.create(medical_record=record, status=status)

    def page_invoices(self, response):
        return list(response.context['page_obj'].object_list)

    def test_invoice_list_is_paginated_by_ten(self):
        for index in range(10):
            self.make_invoice(
                self.patient, self.doctor, 'Pending', 10 + index
            )
        self.client.force_login(self.admin)

        response = self.client.get(reverse('billing:list'), {'page': 2})

        self.assertEqual(response.context['page_obj'].number, 2)
        self.assertEqual(len(response.context['page_obj']), 2)

    def test_invoice_search_matches_patient_name(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse('billing:list'), {'q': 'Patient An'})

        self.assertEqual(self.page_invoices(response), [self.pending_invoice])

    def test_pending_and_paid_status_filters(self):
        self.client.force_login(self.admin)

        pending_response = self.client.get(
            reverse('billing:list'), {'status': 'Pending'}
        )
        paid_response = self.client.get(
            reverse('billing:list'), {'status': 'Paid'}
        )

        self.assertEqual(self.page_invoices(pending_response), [self.pending_invoice])
        self.assertEqual(self.page_invoices(paid_response), [self.paid_invoice])

    def test_doctor_only_sees_own_invoices(self):
        self.client.force_login(self.doctor_user)

        response = self.client.get(reverse('billing:list'))

        self.assertEqual(self.page_invoices(response), [self.pending_invoice])
        self.assertNotContains(response, self.other_patient.full_name)

    def test_invoice_search_and_filter_cannot_bypass_doctor_permission(self):
        self.client.force_login(self.doctor_user)

        response = self.client.get(reverse('billing:list'), {
            'q': 'Patient Binh', 'status': 'Paid',
        })

        self.assertEqual(self.page_invoices(response), [])
        self.assertNotContains(response, self.other_patient.full_name)

    def test_invoice_pagination_link_preserves_search_and_status(self):
        for index in range(10):
            self.make_invoice(
                self.patient, self.doctor, 'Pending', 10 + index
            )
        self.client.force_login(self.admin)

        response = self.client.get(reverse('billing:list'), {
            'q': 'Patient An', 'status': 'Pending',
        })

        self.assertContains(
            response, 'q=Patient+An&amp;status=Pending&amp;page=2'
        )
