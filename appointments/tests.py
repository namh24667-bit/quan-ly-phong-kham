from datetime import date, time

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from billing.models import Invoice
from doctors.models import Doctor
from patients.models import Patient

from .models import Appointment, MedicalRecord


class BackendPermissionTests(TestCase):
    def setUp(self):
        self.admin = self.make_user('admin', 'admin')
        self.staff = self.make_user('staff', 'staff')
        self.doctor_user = self.make_user('doctor_a', 'doctor')
        self.other_doctor_user = self.make_user('doctor_b', 'doctor')

        self.doctor = Doctor.objects.create(
            user=self.doctor_user, full_name='Doctor A', specialty='General',
        )
        self.other_doctor = Doctor.objects.create(
            user=self.other_doctor_user, full_name='Doctor B', specialty='General',
        )
        self.patient = Patient.objects.create(
            full_name='Patient A', date_of_birth='1990-01-01', gender='M', phone='0900000001',
        )
        self.other_patient = Patient.objects.create(
            full_name='Patient B', date_of_birth='1991-01-01', gender='F', phone='0900000002',
        )
        self.appointment = self.make_appointment(self.patient, self.doctor, 'pending', 8)
        self.other_appointment = self.make_appointment(
            self.other_patient, self.other_doctor, 'checked_in', 9,
        )
        self.record = MedicalRecord.objects.create(
            appointment=self.appointment, symptoms='A', diagnosis='A', treatment='A',
        )
        self.other_record = MedicalRecord.objects.create(
            appointment=self.other_appointment, symptoms='B', diagnosis='B', treatment='B',
        )
        self.invoice = Invoice.objects.create(medical_record=self.record)
        self.other_invoice = Invoice.objects.create(medical_record=self.other_record)

    def make_user(self, username, role):
        user = User.objects.create_user(username=username, password='password')
        user.profile.role = role
        user.profile.save()
        return user

    def make_appointment(self, patient, doctor, status, hour):
        return Appointment.objects.create(
            patient=patient,
            doctor=doctor,
            date=date.today(),
            start_time=time(hour, 0),
            end_time=time(hour, 30),
            status=status,
        )

    def test_doctor_only_sees_own_appointments(self):
        self.client.force_login(self.doctor_user)

        response = self.client.get(reverse('appointments:list'))

        self.assertContains(response, self.patient.full_name)
        self.assertNotContains(response, self.other_patient.full_name)
        response = self.client.get(reverse('appointments:detail', args=[self.other_appointment.pk]))
        self.assertEqual(response.status_code, 403)

    def test_doctor_only_sees_related_patients_and_own_history(self):
        self.make_appointment(self.patient, self.other_doctor, 'pending', 10)
        self.client.force_login(self.doctor_user)

        response = self.client.get(reverse('patients:list'))
        self.assertContains(response, self.patient.full_name)
        self.assertNotContains(response, self.other_patient.full_name)
        response = self.client.get(reverse('patients:detail', args=[self.patient.pk]))
        self.assertQuerySetEqual(response.context['appointments'], [self.appointment])
        response = self.client.get(reverse('patients:detail', args=[self.other_patient.pk]))
        self.assertEqual(response.status_code, 403)

    def test_doctor_cannot_view_another_doctor(self):
        self.client.force_login(self.doctor_user)

        response = self.client.get(reverse('doctors:detail', args=[self.other_doctor.pk]))

        self.assertEqual(response.status_code, 403)

    def test_doctor_only_updates_own_medical_record(self):
        self.client.force_login(self.doctor_user)

        own_response = self.client.get(reverse('appointments:medical_record_update', args=[self.record.pk]))
        other_response = self.client.get(
            reverse('appointments:medical_record_update', args=[self.other_record.pk])
        )

        self.assertEqual(own_response.status_code, 200)
        self.assertEqual(other_response.status_code, 403)

    def test_doctor_cannot_change_appointment_status(self):
        self.client.force_login(self.doctor_user)

        for name in ['confirm', 'checkin', 'done', 'cancel']:
            response = self.client.post(reverse(f'appointments:{name}', args=[self.appointment.pk]))
            self.assertEqual(response.status_code, 302)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, 'pending')

    def test_staff_manages_reception_work_but_not_medical_records(self):
        self.client.force_login(self.staff)

        response = self.client.post(reverse('appointments:confirm', args=[self.appointment.pk]))
        self.assertEqual(response.status_code, 302)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, 'confirmed')
        response = self.client.get(reverse('appointments:medical_record_update', args=[self.record.pk]))
        self.assertEqual(response.status_code, 302)

    def test_admin_role_can_manage_medical_records_and_finish_appointments(self):
        self.client.force_login(self.admin)

        create_response = self.client.get(reverse('appointments:medical_record_create'))
        update_response = self.client.get(
            reverse('appointments:medical_record_update', args=[self.record.pk])
        )
        done_response = self.client.post(
            reverse('appointments:done', args=[self.other_appointment.pk])
        )

        self.assertEqual(create_response.status_code, 200)
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(done_response.status_code, 302)
        self.other_appointment.refresh_from_db()
        self.assertEqual(self.other_appointment.status, 'done')

    def test_doctor_only_sees_own_invoices_and_cannot_mark_paid(self):
        self.client.force_login(self.doctor_user)

        response = self.client.get(reverse('billing:list'))
        self.assertQuerySetEqual(response.context['invoices'], [self.invoice])
        response = self.client.get(reverse('billing:detail', args=[self.other_invoice.pk]))
        self.assertEqual(response.status_code, 403)
        response = self.client.post(reverse('billing:mark_paid', args=[self.invoice.pk]))
        self.assertEqual(response.status_code, 302)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, 'Pending')

    def test_doctor_dashboard_only_uses_own_data(self):
        self.client.force_login(self.doctor_user)

        response = self.client.get(reverse('dashboard:index'))

        self.assertEqual(response.context['stats']['total_patients'], 1)
        self.assertEqual(response.context['stats']['appointments_today'], 1)
        self.assertQuerySetEqual(response.context['appointments_today'], [self.appointment])
