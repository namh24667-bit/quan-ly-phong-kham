from datetime import date, time

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from appointments.models import Appointment, MedicalRecord
from billing.models import Invoice
from doctors.models import Doctor, DoctorSchedule
from patients.models import Patient


class DoctorAccountAccessTests(TestCase):
    password = 'testpass123'

    @classmethod
    def setUpTestData(cls):
        cls.active_user = cls.make_user('active_doctor', 'doctor')
        cls.inactive_user = cls.make_user('inactive_doctor', 'doctor')
        cls.missing_doctor_user = cls.make_user('missing_doctor', 'doctor')
        cls.staff = cls.make_user('staff', 'staff')
        cls.admin = cls.make_user('admin', 'admin')
        cls.superuser = User.objects.create_superuser(
            username='superuser', password=cls.password
        )

        cls.active_doctor = Doctor.objects.create(
            user=cls.active_user, full_name='Active Doctor', specialty='General'
        )
        cls.inactive_doctor = Doctor.objects.create(
            user=cls.inactive_user, full_name='Inactive Doctor',
            specialty='General', is_active=False,
        )
        cls.patient = Patient.objects.create(
            full_name='Patient A', date_of_birth='1990-01-01',
            gender='M', phone='0900000001',
        )
        cls.active_appointment = cls.make_appointment(cls.active_doctor)
        cls.inactive_appointment = cls.make_appointment(cls.inactive_doctor)
        cls.active_record = cls.make_record(cls.active_appointment, 'Active diagnosis')
        cls.inactive_record = cls.make_record(
            cls.inactive_appointment, 'Inactive diagnosis'
        )
        cls.active_invoice = Invoice.objects.create(
            medical_record=cls.active_record
        )
        cls.inactive_invoice = Invoice.objects.create(
            medical_record=cls.inactive_record
        )
        DoctorSchedule.objects.create(
            doctor=cls.active_doctor, weekday=0,
            start_time=time(8), end_time=time(12),
        )
        DoctorSchedule.objects.create(
            doctor=cls.inactive_doctor, weekday=0,
            start_time=time(8), end_time=time(12),
        )

    @classmethod
    def make_user(cls, username, role):
        user = User.objects.create_user(username=username, password=cls.password)
        user.profile.role = role
        user.profile.save()
        return user

    @classmethod
    def make_appointment(cls, doctor):
        return Appointment.objects.create(
            patient=cls.patient, doctor=doctor, date=date(2026, 10, 5),
            start_time=time(9), end_time=time(10), status='checked_in',
        )

    @classmethod
    def make_record(cls, appointment, diagnosis):
        return MedicalRecord.objects.create(
            appointment=appointment, symptoms='Symptoms',
            diagnosis=diagnosis, treatment='Treatment',
        )

    def login_data(self, user):
        return {'username': user.username, 'password': self.password}

    def test_active_doctor_can_log_in(self):
        response = self.client.post(
            reverse('accounts:login'), self.login_data(self.active_user)
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            int(self.client.session['_auth_user_id']), self.active_user.pk
        )

    def test_inactive_doctor_cannot_log_in_or_create_authenticated_session(self):
        response = self.client.post(
            reverse('accounts:login'), self.login_data(self.inactive_user)
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Tài khoản bác sĩ đã ngừng hoạt động.')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_inactive_doctor_keeps_active_user_account(self):
        self.inactive_user.refresh_from_db()

        self.assertFalse(self.inactive_doctor.is_active)
        self.assertTrue(self.inactive_user.is_active)

    def test_doctor_without_doctor_object_is_denied_safely(self):
        login_response = self.client.post(
            reverse('accounts:login'), self.login_data(self.missing_doctor_user)
        )
        self.assertEqual(login_response.status_code, 200)
        self.assertContains(login_response, 'Tài khoản bác sĩ chưa được liên kết.')
        self.assertNotIn('_auth_user_id', self.client.session)

        self.client.force_login(self.missing_doctor_user)
        self.assertEqual(
            self.client.get(reverse('dashboard:index')).status_code, 403
        )

    def test_inactive_doctor_old_session_is_blocked_from_role_views(self):
        self.client.force_login(self.inactive_user)
        urls = [
            reverse('dashboard:index'),
            reverse('appointments:list'),
            reverse('appointments:detail', args=[self.inactive_appointment.pk]),
            reverse('patients:detail', args=[self.patient.pk]),
            reverse('billing:detail', args=[self.inactive_invoice.pk]),
            reverse('doctors:schedule_list'),
        ]

        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)

    def test_inactive_doctor_cannot_finish_appointment(self):
        self.client.force_login(self.inactive_user)

        response = self.client.post(
            reverse('appointments:done', args=[self.inactive_appointment.pk])
        )

        self.assertEqual(response.status_code, 403)
        self.inactive_appointment.refresh_from_db()
        self.assertEqual(self.inactive_appointment.status, 'checked_in')

    def test_inactive_doctor_cannot_create_or_update_medical_record(self):
        self.client.force_login(self.inactive_user)

        create_response = self.client.get(
            reverse('appointments:medical_record_create')
        )
        update_response = self.client.get(
            reverse('appointments:medical_record_update', args=[self.inactive_record.pk])
        )

        self.assertEqual(create_response.status_code, 403)
        self.assertEqual(update_response.status_code, 403)

    def test_active_doctor_can_access_role_views(self):
        self.client.force_login(self.active_user)
        urls = [
            reverse('dashboard:index'),
            reverse('appointments:list'),
            reverse('appointments:detail', args=[self.active_appointment.pk]),
            reverse('patients:detail', args=[self.patient.pk]),
            reverse('billing:detail', args=[self.active_invoice.pk]),
            reverse('doctors:schedule_list'),
        ]

        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_staff_admin_and_superuser_are_not_affected(self):
        for user in [self.staff, self.admin, self.superuser]:
            with self.subTest(username=user.username):
                response = self.client.post(
                    reverse('accounts:login'), self.login_data(user)
                )
                self.assertEqual(response.status_code, 302)
                self.assertEqual(
                    self.client.get(reverse('dashboard:index')).status_code, 200
                )
                self.client.logout()

    def test_inactive_doctor_with_old_session_can_log_out(self):
        self.client.force_login(self.inactive_user)

        response = self.client.post(reverse('accounts:logout'))

        self.assertRedirects(response, reverse('accounts:login'))
        self.assertNotIn('_auth_user_id', self.client.session)
