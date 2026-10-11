from datetime import time
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from billing.models import Invoice, Medicine, Prescription, Service
from doctors.models import Doctor
from patients.models import Patient

from .models import Appointment, MedicalRecord


class AdminDataProtectionTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username='admin_protection',
            email='admin@example.com',
            password='testpass123',
        )
        self.client.force_login(self.superuser)
        self.patient = Patient.objects.create(
            full_name='Patient Admin', date_of_birth='1990-01-01',
            gender='M', phone='0900000101',
        )
        self.doctor = Doctor.objects.create(
            full_name='Doctor Admin', specialty='General', phone='0900000102',
        )
        self.medicine = Medicine.objects.create(
            name='Medicine Admin', unit_price='10000', unit='Viên',
        )
        self.service = Service.objects.create(
            name='Service Admin', price='50000',
        )

        self.pending_appointment = self.make_appointment('pending', 8)
        self.checked_in_appointment = self.make_appointment('checked_in', 9)
        self.done_appointment = self.make_appointment('done', 10)

        self.unlocked_record = self.make_record(
            self.checked_in_appointment, 'Unlocked diagnosis'
        )
        self.unlocked_prescription = Prescription.objects.create(
            medical_record=self.unlocked_record,
            medicine=self.medicine,
            quantity=1,
            dosage='Ngày 1 lần',
        )
        self.pending_invoice = Invoice.objects.create(
            medical_record=self.unlocked_record
        )
        self.pending_invoice.recalculate()

        self.locked_record = self.make_record(
            self.done_appointment, 'Locked diagnosis'
        )
        self.locked_prescription = Prescription.objects.create(
            medical_record=self.locked_record,
            medicine=self.medicine,
            quantity=2,
            dosage='Ngày 2 lần',
        )
        self.paid_invoice = Invoice.objects.create(
            medical_record=self.locked_record,
            medicine_total=Decimal('20000.00'),
            total_amount=Decimal('20000.00'),
            status='Paid',
        )
        self.paid_invoice.services.add(self.service)

    def make_appointment(self, status, hour):
        return Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            date=timezone.localdate(),
            start_time=time(hour),
            end_time=time(hour, 30),
            status=status,
        )

    @staticmethod
    def make_record(appointment, diagnosis):
        return MedicalRecord.objects.create(
            appointment=appointment,
            symptoms='Symptoms',
            diagnosis=diagnosis,
            treatment='Treatment',
        )

    def appointment_admin_data(self, appointment, **overrides):
        data = {
            'patient': appointment.patient_id,
            'doctor': appointment.doctor_id,
            'date': appointment.date.isoformat(),
            'start_time': appointment.start_time.strftime('%H:%M:%S'),
            'end_time': appointment.end_time.strftime('%H:%M:%S'),
            'note': appointment.note,
            '_save': 'Save',
        }
        data.update(overrides)
        return data

    def test_admin_cannot_mark_pending_invoice_paid_directly(self):
        old_total = self.pending_invoice.total_amount
        response = self.client.post(
            reverse('admin:billing_invoice_change', args=[self.pending_invoice.pk]),
            {
                'status': 'Paid',
                'services': [self.service.pk],
                '_save': 'Save',
            },
        )

        self.assertEqual(response.status_code, 403)
        self.pending_invoice.refresh_from_db()
        self.assertEqual(self.pending_invoice.status, 'Pending')
        self.assertEqual(self.pending_invoice.total_amount, old_total)
        self.assertEqual(list(self.pending_invoice.services.all()), [])

    def test_pending_invoice_is_view_only_and_cannot_be_created_in_admin(self):
        change_response = self.client.get(
            reverse('admin:billing_invoice_change', args=[self.pending_invoice.pk])
        )
        add_response = self.client.get(reverse('admin:billing_invoice_add'))

        self.assertEqual(change_response.status_code, 200)
        self.assertFalse(change_response.context['has_change_permission'])
        self.assertEqual(add_response.status_code, 403)

    def test_paid_invoice_is_view_only_and_cannot_be_deleted(self):
        old_total = self.paid_invoice.total_amount
        old_services = list(self.paid_invoice.services.all())
        change_url = reverse(
            'admin:billing_invoice_change', args=[self.paid_invoice.pk]
        )

        get_response = self.client.get(change_url)
        post_response = self.client.post(
            change_url,
            {'status': 'Pending', 'services': [], '_save': 'Save'},
        )
        delete_response = self.client.post(
            reverse('admin:billing_invoice_delete', args=[self.paid_invoice.pk]),
            {'post': 'yes'},
        )

        self.assertEqual(get_response.status_code, 200)
        self.assertFalse(get_response.context['has_change_permission'])
        self.assertEqual(post_response.status_code, 403)
        self.assertEqual(delete_response.status_code, 403)
        self.paid_invoice.refresh_from_db()
        self.assertEqual(self.paid_invoice.status, 'Paid')
        self.assertEqual(self.paid_invoice.total_amount, old_total)
        self.assertEqual(list(self.paid_invoice.services.all()), old_services)

    def test_existing_appointment_is_view_only_and_admin_post_keeps_data(self):
        inactive_patient = Patient.objects.create(
            full_name='Inactive Patient', date_of_birth='1991-01-01',
            gender='F', phone='0900000103', is_active=False,
        )
        inactive_doctor = Doctor.objects.create(
            full_name='Inactive Doctor', specialty='General', is_active=False,
        )
        original = (
            self.pending_appointment.patient_id,
            self.pending_appointment.doctor_id,
            self.pending_appointment.date,
            self.pending_appointment.start_time,
            self.pending_appointment.end_time,
            self.pending_appointment.status,
            self.pending_appointment.note,
        )
        change_url = reverse(
            'admin:appointments_appointment_change',
            args=[self.pending_appointment.pk],
        )

        get_response = self.client.get(change_url)
        post_response = self.client.post(
            change_url,
            self.appointment_admin_data(
                self.pending_appointment,
                patient=inactive_patient.pk,
                doctor=inactive_doctor.pk,
                date='2000-01-01',
                start_time='10:00:00',
                end_time='09:00:00',
                status='done',
                note='Must not change',
            ),
        )

        self.assertEqual(get_response.status_code, 200)
        self.assertFalse(get_response.context['has_change_permission'])
        self.assertEqual(post_response.status_code, 403)
        self.pending_appointment.refresh_from_db()
        self.assertEqual(
            (
                self.pending_appointment.patient_id,
                self.pending_appointment.doctor_id,
                self.pending_appointment.date,
                self.pending_appointment.start_time,
                self.pending_appointment.end_time,
                self.pending_appointment.status,
                self.pending_appointment.note,
            ),
            original,
        )

    def test_appointment_cannot_be_created_directly_in_admin(self):
        before_count = Appointment.objects.count()

        get_response = self.client.get(reverse('admin:appointments_appointment_add'))
        post_response = self.client.post(
            reverse('admin:appointments_appointment_add'),
            {
                'patient': self.patient.pk,
                'doctor': self.doctor.pk,
                'date': '2000-01-01',
                'start_time': '10:00:00',
                'end_time': '09:00:00',
                'status': 'done',
                'note': 'Invalid direct admin appointment',
                '_save': 'Save',
            },
        )

        self.assertEqual(get_response.status_code, 403)
        self.assertEqual(post_response.status_code, 403)
        self.assertEqual(Appointment.objects.count(), before_count)

    def test_admin_cannot_change_appointment_status_directly(self):
        response = self.client.post(
            reverse(
                'admin:appointments_appointment_change',
                args=[self.pending_appointment.pk],
            ),
            self.appointment_admin_data(
                self.pending_appointment,
                status='done',
                note='Allowed detail update',
            ),
        )

        self.assertEqual(response.status_code, 403)
        self.pending_appointment.refresh_from_db()
        self.assertEqual(self.pending_appointment.status, 'pending')
        self.assertEqual(self.pending_appointment.note, '')

    def test_locked_appointment_is_view_only_in_admin(self):
        old_note = self.done_appointment.note
        change_url = reverse(
            'admin:appointments_appointment_change',
            args=[self.done_appointment.pk],
        )

        get_response = self.client.get(change_url)
        post_response = self.client.post(
            change_url,
            self.appointment_admin_data(
                self.done_appointment,
                status='pending',
                note='Must not change',
            ),
        )

        self.assertEqual(get_response.status_code, 200)
        self.assertFalse(get_response.context['has_change_permission'])
        self.assertEqual(post_response.status_code, 403)
        self.done_appointment.refresh_from_db()
        self.assertEqual(self.done_appointment.status, 'done')
        self.assertEqual(self.done_appointment.note, old_note)

    def test_locked_medical_record_and_prescription_cannot_be_changed(self):
        record_response = self.client.post(
            reverse(
                'admin:appointments_medicalrecord_change',
                args=[self.locked_record.pk],
            ),
            {
                'appointment': self.done_appointment.pk,
                'symptoms': 'Changed',
                'diagnosis': 'Changed',
                'treatment': 'Changed',
                'notes': 'Changed',
                '_save': 'Save',
            },
        )
        prescription_response = self.client.post(
            reverse(
                'admin:billing_prescription_change',
                args=[self.locked_prescription.pk],
            ),
            {
                'medical_record': self.locked_record.pk,
                'medicine': self.medicine.pk,
                'quantity': 99,
                'dosage': 'Changed',
                '_save': 'Save',
            },
        )

        self.assertEqual(record_response.status_code, 403)
        self.assertEqual(prescription_response.status_code, 403)
        self.locked_record.refresh_from_db()
        self.locked_prescription.refresh_from_db()
        self.assertEqual(self.locked_record.diagnosis, 'Locked diagnosis')
        self.assertEqual(self.locked_prescription.quantity, 2)
        self.assertEqual(self.locked_prescription.dosage, 'Ngày 2 lần')

    def test_admin_cannot_delete_appointment_with_medical_record(self):
        response = self.client.post(
            reverse(
                'admin:appointments_appointment_delete',
                args=[self.checked_in_appointment.pk],
            ),
            {'post': 'yes'},
        )

        self.assertEqual(response.status_code, 403)
        self.assertTrue(
            Appointment.objects.filter(pk=self.checked_in_appointment.pk).exists()
        )
        self.assertTrue(
            MedicalRecord.objects.filter(pk=self.unlocked_record.pk).exists()
        )

    def test_admin_cannot_delete_medical_record_with_dependent_data(self):
        response = self.client.post(
            reverse(
                'admin:appointments_medicalrecord_delete',
                args=[self.unlocked_record.pk],
            ),
            {'post': 'yes'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            MedicalRecord.objects.filter(pk=self.unlocked_record.pk).exists()
        )
        self.assertTrue(
            Prescription.objects.filter(pk=self.unlocked_prescription.pk).exists()
        )
        self.assertTrue(Invoice.objects.filter(pk=self.pending_invoice.pk).exists())

    def test_prescription_is_view_only_and_keeps_pending_invoice_total(self):
        other_medicine = Medicine.objects.create(
            name='Other Medicine', unit_price='90000', unit='Viên',
        )
        old_total = self.pending_invoice.total_amount
        change_url = reverse(
            'admin:billing_prescription_change',
            args=[self.unlocked_prescription.pk],
        )

        get_response = self.client.get(change_url)
        post_response = self.client.post(
            change_url,
            {
                'medical_record': self.unlocked_record.pk,
                'medicine': other_medicine.pk,
                'quantity': 99,
                'dosage': 'Changed',
                '_save': 'Save',
            },
        )
        add_response = self.client.get(reverse('admin:billing_prescription_add'))

        self.assertEqual(get_response.status_code, 200)
        self.assertFalse(get_response.context['has_change_permission'])
        self.assertEqual(post_response.status_code, 403)
        self.assertEqual(add_response.status_code, 403)
        self.unlocked_prescription.refresh_from_db()
        self.pending_invoice.refresh_from_db()
        self.assertEqual(self.unlocked_prescription.medicine, self.medicine)
        self.assertEqual(self.unlocked_prescription.quantity, 1)
        self.assertEqual(self.pending_invoice.total_amount, old_total)

    def test_admin_still_manages_medicine_and_service(self):
        medicine_response = self.client.post(
            reverse('admin:billing_medicine_add'),
            {
                'name': 'New Medicine',
                'unit_price': '15000',
                'unit': 'Viên',
                '_save': 'Save',
            },
        )
        service_response = self.client.post(
            reverse('admin:billing_service_add'),
            {'name': 'New Service', 'price': '75000', '_save': 'Save'},
        )

        self.assertEqual(medicine_response.status_code, 302)
        self.assertEqual(service_response.status_code, 302)
        self.assertTrue(Medicine.objects.filter(name='New Medicine').exists())
        self.assertTrue(Service.objects.filter(name='New Service').exists())

    def test_valid_clinical_and_payment_workflow_still_succeeds(self):
        appointment = self.make_appointment('checked_in', 11)
        create_response = self.client.post(
            reverse('appointments:medical_record_create'),
            {
                'appointment': appointment.pk,
                'symptoms': 'Fever',
                'diagnosis': 'Flu',
                'treatment': 'Rest',
                'notes': '',
                'prescriptions-TOTAL_FORMS': '1',
                'prescriptions-INITIAL_FORMS': '0',
                'prescriptions-MIN_NUM_FORMS': '0',
                'prescriptions-MAX_NUM_FORMS': '1000',
                'prescriptions-0-medicine': self.medicine.pk,
                'prescriptions-0-quantity': '2',
                'prescriptions-0-dosage': 'Ngày 2 lần',
            },
        )

        self.assertEqual(create_response.status_code, 302)
        record = MedicalRecord.objects.get(appointment=appointment)
        invoice = Invoice.objects.get(medical_record=record)
        self.assertEqual(record.prescriptions.count(), 1)
        self.assertEqual(invoice.status, 'Pending')

        done_response = self.client.post(
            reverse('appointments:done', args=[appointment.pk])
        )
        paid_response = self.client.post(
            reverse('billing:mark_paid', args=[invoice.pk])
        )

        self.assertEqual(done_response.status_code, 302)
        self.assertEqual(paid_response.status_code, 302)
        appointment.refresh_from_db()
        invoice.refresh_from_db()
        self.assertEqual(appointment.status, 'done')
        self.assertEqual(invoice.status, 'Paid')

    def test_medical_record_cannot_be_created_directly_in_admin(self):
        response = self.client.get(reverse('admin:appointments_medicalrecord_add'))

        self.assertEqual(response.status_code, 403)
