from datetime import time, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from appointments.models import Appointment, MedicalRecord
from billing.models import Invoice
from doctors.models import Doctor
from patients.models import Patient


def make_user(username, role):
    user = User.objects.create_user(username=username)
    user.profile.role = role
    user.profile.save()
    return user


class RoleAwareDashboardTests(TestCase):
    def setUp(self):
        self.admin = make_user('dashboard_admin', 'admin')
        self.staff = make_user('dashboard_staff', 'staff')
        self.doctor_user = make_user('dashboard_doctor', 'doctor')
        self.other_doctor_user = make_user('dashboard_other_doctor', 'doctor')
        self.superuser = User.objects.create_superuser(username='dashboard_superuser')

        self.doctor = Doctor.objects.create(
            user=self.doctor_user, full_name='Doctor Dashboard', specialty='General',
        )
        self.other_doctor = Doctor.objects.create(
            user=self.other_doctor_user, full_name='Other Doctor', specialty='General',
        )
        self.patient = Patient.objects.create(
            full_name='Own Patient', date_of_birth='1990-01-01',
            gender='M', phone='0900000001',
        )
        self.other_patient = Patient.objects.create(
            full_name='Other Patient', date_of_birth='1991-01-01',
            gender='F', phone='0900000002',
        )
        Patient.objects.create(
            full_name='Inactive Patient', date_of_birth='1992-01-01',
            gender='M', phone='0900000003', is_active=False,
        )

        today = timezone.localdate()
        self.own_today = self.make_appointment(
            self.patient, self.doctor, today, 'checked_in', 8,
        )
        self.other_today = self.make_appointment(
            self.other_patient, self.other_doctor, today, 'pending', 9,
        )
        self.own_done = self.make_appointment(
            self.patient, self.doctor, today - timedelta(days=1), 'done', 10,
        )
        self.other_done = self.make_appointment(
            self.other_patient, self.other_doctor,
            today - timedelta(days=1), 'done', 11,
        )
        self.own_upcoming = self.make_appointment(
            self.patient, self.doctor, today + timedelta(days=1), 'confirmed', 12,
        )

        pending_record = self.make_record(self.own_today)
        own_done_record = self.make_record(self.own_done)
        other_done_record = self.make_record(self.other_done)
        Invoice.objects.create(medical_record=pending_record)
        Invoice.objects.create(
            medical_record=own_done_record, total_amount=Decimal('100000'), status='Paid',
        )
        Invoice.objects.create(
            medical_record=other_done_record, total_amount=Decimal('200000'), status='Paid',
        )

    def make_appointment(self, patient, doctor, day, status, hour):
        return Appointment.objects.create(
            patient=patient, doctor=doctor, date=day,
            start_time=time(hour), end_time=time(hour, 30), status=status,
        )

    def make_record(self, appointment):
        return MedicalRecord.objects.create(
            appointment=appointment, symptoms='Symptoms',
            diagnosis='Diagnosis', treatment='Treatment',
        )

    def get_dashboard(self, user):
        self.client.force_login(user)
        return self.client.get(reverse('dashboard:index'))

    def test_admin_dashboard_has_system_metrics(self):
        response = self.get_dashboard(self.admin)

        self.assertEqual(response.context['dashboard_role'], 'admin')
        self.assertEqual(response.context['stats'], {
            'total_patients': 2,
            'active_doctors': 2,
            'appointments_today': 2,
            'pending_count': 1,
            'done_total': 2,
            'paid_revenue': Decimal('300000'),
        })

    def test_staff_dashboard_has_operational_metrics(self):
        response = self.get_dashboard(self.staff)

        self.assertEqual(response.context['dashboard_role'], 'staff')
        self.assertEqual(response.context['stats'], {
            'total_patients': 2,
            'appointments_today': 2,
            'pending_count': 1,
            'confirmed_count': 1,
            'checked_in_count': 1,
            'pending_invoices': 1,
        })
        self.assertNotContains(response, 'Doanh Thu Đã Thanh Toán')

    def test_doctor_dashboard_uses_only_own_appointments(self):
        response = self.get_dashboard(self.doctor_user)

        self.assertEqual(response.context['dashboard_role'], 'doctor')
        self.assertEqual(response.context['stats'], {
            'total_patients': 1,
            'appointments_today': 1,
            'checked_in_count': 1,
            'done_total': 1,
            'upcoming_count': 1,
        })
        self.assertQuerySetEqual(response.context['appointments_today'], [self.own_today])
        self.assertQuerySetEqual(response.context['upcoming'], [self.own_upcoming])

    def test_doctor_dashboard_excludes_other_doctors_data(self):
        response = self.get_dashboard(self.doctor_user)

        self.assertNotContains(response, self.other_patient.full_name)
        self.assertNotContains(response, self.other_doctor.full_name)
        self.assertNotIn(self.other_today, response.context['appointments_today'])

    def test_doctor_dashboard_does_not_show_system_revenue(self):
        response = self.get_dashboard(self.doctor_user)

        self.assertNotIn('paid_revenue', response.context['stats'])
        self.assertNotContains(response, 'Doanh Thu Đã Thanh Toán')

    def test_superuser_uses_admin_dashboard(self):
        response = self.get_dashboard(self.superuser)

        self.assertEqual(response.context['dashboard_role'], 'admin')
        self.assertContains(response, 'Bác Sĩ Đang Hoạt Động')
        self.assertContains(response, 'Doanh Thu Đã Thanh Toán')

    def test_doctor_dashboard_has_no_create_appointment_action(self):
        response = self.get_dashboard(self.doctor_user)

        self.assertNotContains(response, reverse('appointments:create'))


class RoleAwareTemplateTests(TestCase):
    def setUp(self):
        self.admin = make_user('ui_admin', 'admin')
        self.staff = make_user('ui_staff', 'staff')
        self.doctor_user = make_user('ui_doctor', 'doctor')
        self.doctor = Doctor.objects.create(
            user=self.doctor_user, full_name='UI Doctor', specialty='General',
        )
        self.patient = Patient.objects.create(
            full_name='UI Patient', date_of_birth='1990-01-01',
            gender='M', phone='0910000001',
        )
        Appointment.objects.create(
            patient=self.patient, doctor=self.doctor, date=timezone.localdate(),
            start_time=time(8), end_time=time(8, 30), status='pending',
        )

    def responses_for(self, user, list_name, detail_name, pk):
        self.client.force_login(user)
        return (
            self.client.get(reverse(list_name)),
            self.client.get(reverse(detail_name, args=[pk])),
        )

    def test_doctor_patient_pages_hide_management_actions(self):
        list_response, detail_response = self.responses_for(
            self.doctor_user, 'patients:list', 'patients:detail', self.patient.pk,
        )

        for response in [list_response, detail_response]:
            self.assertNotContains(response, reverse('patients:create'))
            self.assertNotContains(response, reverse('patients:update', args=[self.patient.pk]))
            self.assertNotContains(response, reverse('patients:delete', args=[self.patient.pk]))

    def test_staff_patient_pages_hide_deactivate_action(self):
        list_response, detail_response = self.responses_for(
            self.staff, 'patients:list', 'patients:detail', self.patient.pk,
        )

        for response in [list_response, detail_response]:
            self.assertContains(response, reverse('patients:update', args=[self.patient.pk]))
            self.assertNotContains(response, reverse('patients:delete', args=[self.patient.pk]))
        self.assertContains(list_response, reverse('patients:create'))

    def test_admin_patient_pages_show_management_actions(self):
        list_response, detail_response = self.responses_for(
            self.admin, 'patients:list', 'patients:detail', self.patient.pk,
        )

        for response in [list_response, detail_response]:
            self.assertContains(response, reverse('patients:update', args=[self.patient.pk]))
            self.assertContains(response, reverse('patients:delete', args=[self.patient.pk]))
        self.assertContains(list_response, reverse('patients:create'))

    def test_staff_doctor_pages_hide_create_and_update_but_show_deactivate(self):
        list_response, detail_response = self.responses_for(
            self.staff, 'doctors:list', 'doctors:detail', self.doctor.pk,
        )

        for response in [list_response, detail_response]:
            self.assertNotContains(response, reverse('doctors:create'))
            self.assertNotContains(response, reverse('doctors:update', args=[self.doctor.pk]))
            self.assertContains(response, reverse('doctors:delete', args=[self.doctor.pk]))

    def test_admin_doctor_pages_show_management_actions(self):
        list_response, detail_response = self.responses_for(
            self.admin, 'doctors:list', 'doctors:detail', self.doctor.pk,
        )

        self.assertContains(list_response, reverse('doctors:create'))
        for response in [list_response, detail_response]:
            self.assertContains(response, reverse('doctors:update', args=[self.doctor.pk]))
            self.assertContains(response, reverse('doctors:delete', args=[self.doctor.pk]))

    def test_doctor_navigation_has_only_allowed_shortcuts(self):
        self.client.force_login(self.doctor_user)
        response = self.client.get(reverse('dashboard:index'))

        self.assertContains(response, 'Lịch sử lịch khám')
        self.assertNotContains(response, 'Tất cả lịch hẹn')
        self.assertNotContains(response, reverse('appointments:create'))
        self.assertNotContains(response, reverse('patients:create'))
        self.assertNotContains(response, reverse('doctors:create'))
