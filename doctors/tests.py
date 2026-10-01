from datetime import timedelta, time

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from appointments.forms import AppointmentForm
from appointments.models import Appointment, MedicalRecord
from billing.models import Invoice, Medicine, Prescription
from patients.models import Patient

from .forms import DoctorScheduleForm
from .models import Doctor, DoctorSchedule


class DoctorScheduleModelTests(TestCase):
    def setUp(self):
        self.doctor = Doctor.objects.create(full_name='Doctor A', specialty='General')
        self.other_doctor = Doctor.objects.create(full_name='Doctor B', specialty='General')

    def test_create_valid_schedule(self):
        schedule = DoctorSchedule.objects.create(
            doctor=self.doctor, weekday=0,
            start_time=time(8), end_time=time(12),
        )

        self.assertTrue(schedule.is_active)

    def test_end_time_must_be_after_start_time(self):
        with self.assertRaisesMessage(ValidationError, 'Giờ kết thúc phải sau giờ bắt đầu.'):
            DoctorSchedule.objects.create(
                doctor=self.doctor, weekday=0,
                start_time=time(14), end_time=time(8),
            )

    def test_overlapping_schedules_are_rejected(self):
        DoctorSchedule.objects.create(
            doctor=self.doctor, weekday=0,
            start_time=time(8), end_time=time(12),
        )

        with self.assertRaisesMessage(
            ValidationError, 'Lịch làm việc bị trùng với ca khác của bác sĩ.'
        ):
            DoctorSchedule.objects.create(
                doctor=self.doctor, weekday=0,
                start_time=time(10), end_time=time(14),
            )

    def test_non_overlapping_schedules_are_allowed(self):
        DoctorSchedule.objects.create(
            doctor=self.doctor, weekday=0,
            start_time=time(8), end_time=time(12),
        )

        afternoon = DoctorSchedule.objects.create(
            doctor=self.doctor, weekday=0,
            start_time=time(13), end_time=time(17),
        )

        self.assertIsNotNone(afternoon.pk)

    def test_different_doctors_can_have_the_same_schedule(self):
        DoctorSchedule.objects.create(
            doctor=self.doctor, weekday=0,
            start_time=time(8), end_time=time(12),
        )

        schedule = DoctorSchedule.objects.create(
            doctor=self.other_doctor, weekday=0,
            start_time=time(8), end_time=time(12),
        )

        self.assertIsNotNone(schedule.pk)


class DoctorScheduleFormTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(username='schedule_form_staff')
        self.staff.profile.role = 'staff'
        self.staff.profile.save()
        self.active_doctor = Doctor.objects.create(
            full_name='Active Doctor', specialty='General'
        )
        self.inactive_doctor = Doctor.objects.create(
            full_name='Inactive Doctor', specialty='General', is_active=False
        )
        self.old_schedule = DoctorSchedule.objects.create(
            doctor=self.inactive_doctor, weekday=0,
            start_time=time(8), end_time=time(12),
        )

    def schedule_data(self, doctor):
        return {
            'doctor': doctor.pk,
            'weekday': 1,
            'start_time': '08:00',
            'end_time': '12:00',
            'is_active': 'on',
        }

    def test_active_doctor_is_valid_schedule_choice(self):
        form = DoctorScheduleForm(data=self.schedule_data(self.active_doctor))

        self.assertTrue(form.is_valid())

    def test_inactive_doctor_is_invalid_for_new_schedule(self):
        form = DoctorScheduleForm(data=self.schedule_data(self.inactive_doctor))

        self.assertFalse(form.is_valid())
        self.assertIn('doctor', form.errors)

    def test_manual_post_cannot_create_schedule_for_inactive_doctor(self):
        self.client.force_login(self.staff)

        response = self.client.post(
            reverse('doctors:schedule_create'),
            self.schedule_data(self.inactive_doctor),
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('doctor', response.context['form'].errors)
        self.assertEqual(
            DoctorSchedule.objects.filter(doctor=self.inactive_doctor).count(), 1
        )

    def test_old_schedule_keeps_inactive_doctor_when_edited(self):
        self.client.force_login(self.staff)
        list_response = self.client.get(reverse('doctors:schedule_list'))
        self.assertContains(list_response, self.inactive_doctor.full_name)

        data = self.schedule_data(self.inactive_doctor)
        data['weekday'] = 0
        data['start_time'] = '09:00'
        form = DoctorScheduleForm(data=data, instance=self.old_schedule)

        self.assertTrue(form.is_valid())
        schedule = form.save()
        self.assertEqual(schedule.doctor, self.inactive_doctor)


class DoctorSchedulePermissionTests(TestCase):
    def setUp(self):
        self.admin = self.make_user('admin', 'admin')
        self.staff = self.make_user('staff', 'staff')
        self.doctor_user = self.make_user('doctor_a', 'doctor')
        self.other_doctor_user = self.make_user('doctor_b', 'doctor')
        self.doctor = Doctor.objects.create(
            user=self.doctor_user, full_name='Doctor A', specialty='General'
        )
        self.other_doctor = Doctor.objects.create(
            user=self.other_doctor_user, full_name='Doctor B', specialty='General'
        )
        self.schedule = DoctorSchedule.objects.create(
            doctor=self.doctor, weekday=0,
            start_time=time(8), end_time=time(12),
        )
        self.other_schedule = DoctorSchedule.objects.create(
            doctor=self.other_doctor, weekday=0,
            start_time=time(13), end_time=time(17),
        )

    def make_user(self, username, role):
        user = User.objects.create_user(username=username)
        user.profile.role = role
        user.profile.save()
        return user

    def test_doctor_only_sees_own_schedule(self):
        self.client.force_login(self.doctor_user)

        response = self.client.get(reverse('doctors:schedule_list'))

        self.assertContains(response, self.doctor.full_name)
        self.assertNotContains(response, self.other_doctor.full_name)

    def test_doctor_cannot_update_another_doctors_schedule(self):
        self.client.force_login(self.doctor_user)
        url = reverse('doctors:schedule_update', args=[self.other_schedule.pk])

        get_response = self.client.get(url)
        post_response = self.client.post(url, {
            'doctor': self.other_doctor.pk,
            'weekday': 0,
            'start_time': '09:00',
            'end_time': '17:00',
            'is_active': 'on',
        })

        self.assertEqual(get_response.status_code, 302)
        self.assertEqual(post_response.status_code, 302)
        self.other_schedule.refresh_from_db()
        self.assertEqual(self.other_schedule.start_time, time(13))

    def test_admin_and_staff_can_manage_schedules(self):
        for weekday, user in enumerate([self.admin, self.staff], start=1):
            with self.subTest(role=user.profile.role):
                self.client.force_login(user)
                create_response = self.client.post(reverse('doctors:schedule_create'), {
                    'doctor': self.doctor.pk,
                    'weekday': weekday,
                    'start_time': '08:00',
                    'end_time': '12:00',
                    'is_active': 'on',
                })
                schedule = DoctorSchedule.objects.get(
                    doctor=self.doctor, weekday=weekday
                )
                update_response = self.client.post(
                    reverse('doctors:schedule_update', args=[schedule.pk]),
                    {
                        'doctor': self.doctor.pk,
                        'weekday': weekday,
                        'start_time': '09:00',
                        'end_time': '12:00',
                        'is_active': 'on',
                    },
                )
                deactivate_response = self.client.post(
                    reverse('doctors:schedule_deactivate', args=[schedule.pk])
                )

                self.assertEqual(create_response.status_code, 302)
                self.assertEqual(update_response.status_code, 302)
                self.assertEqual(deactivate_response.status_code, 302)
                schedule.refresh_from_db()
                self.assertFalse(schedule.is_active)


class DoctorDeactivateTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(username='staff')
        self.staff.profile.role = 'staff'
        self.staff.profile.save()
        self.doctor_user = User.objects.create_user(username='doctor')
        self.doctor_user.profile.role = 'doctor'
        self.doctor_user.profile.save()
        self.doctor = Doctor.objects.create(
            user=self.doctor_user, full_name='Doctor A', specialty='General'
        )
        self.patient = Patient.objects.create(
            full_name='Patient A', date_of_birth='1990-01-01',
            gender='M', phone='0900000001',
        )
        self.schedule = DoctorSchedule.objects.create(
            doctor=self.doctor, weekday=0,
            start_time=time(8), end_time=time(12),
        )
        today = timezone.localdate()
        self.done_appointment = Appointment.objects.create(
            patient=self.patient, doctor=self.doctor,
            date=today - timedelta(days=4),
            start_time=time(9), end_time=time(10), status='done',
        )
        self.cancelled_appointment = Appointment.objects.create(
            patient=self.patient, doctor=self.doctor,
            date=today - timedelta(days=3),
            start_time=time(9), end_time=time(10), status='cancelled',
        )
        self.pending_appointment = Appointment.objects.create(
            patient=self.patient, doctor=self.doctor,
            date=today - timedelta(days=2),
            start_time=time(9), end_time=time(10), status='pending',
        )
        self.confirmed_appointment = Appointment.objects.create(
            patient=self.patient, doctor=self.doctor,
            date=today - timedelta(days=1),
            start_time=time(9), end_time=time(10), status='confirmed',
        )
        self.record = MedicalRecord.objects.create(
            appointment=self.done_appointment, symptoms='A',
            diagnosis='Diagnosis A', treatment='Treatment A',
        )
        medicine = Medicine.objects.create(
            name='Medicine A', unit_price='10000', unit='Viên'
        )
        self.prescription = Prescription.objects.create(
            medical_record=self.record, medicine=medicine,
            quantity=2, dosage='Ngày 2 lần',
        )
        self.invoice = Invoice.objects.create(medical_record=self.record)

    def deactivate_doctor(self):
        self.client.force_login(self.staff)
        return self.client.post(reverse('doctors:delete', args=[self.doctor.pk]))

    def test_doctor_is_active_by_default(self):
        doctor = Doctor.objects.create(full_name='Doctor B', specialty='General')

        self.assertTrue(doctor.is_active)

    def test_deactivate_keeps_doctor_and_user_account(self):
        response = self.deactivate_doctor()

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Doctor.objects.filter(pk=self.doctor.pk).exists())
        self.doctor.refresh_from_db()
        self.doctor_user.refresh_from_db()
        self.assertFalse(self.doctor.is_active)
        self.assertTrue(User.objects.filter(pk=self.doctor_user.pk).exists())
        self.assertTrue(self.doctor_user.is_active)

    def test_deactivate_preserves_history_and_schedule(self):
        self.deactivate_doctor()

        self.assertTrue(Appointment.objects.filter(pk=self.done_appointment.pk).exists())
        self.assertTrue(Appointment.objects.filter(pk=self.cancelled_appointment.pk).exists())
        self.assertTrue(Appointment.objects.filter(pk=self.pending_appointment.pk).exists())
        self.assertTrue(Appointment.objects.filter(pk=self.confirmed_appointment.pk).exists())
        self.assertTrue(MedicalRecord.objects.filter(pk=self.record.pk).exists())
        self.assertTrue(Prescription.objects.filter(pk=self.prescription.pk).exists())
        self.assertTrue(Invoice.objects.filter(pk=self.invoice.pk).exists())
        self.schedule.refresh_from_db()
        self.assertTrue(self.schedule.is_active)

    def test_inactive_doctor_is_not_available_for_new_appointment(self):
        self.deactivate_doctor()

        form = AppointmentForm()

        self.assertNotIn(self.doctor, form.fields['doctor'].queryset)

    def test_old_appointment_of_inactive_doctor_is_visible(self):
        self.deactivate_doctor()

        response = self.client.get(
            reverse('appointments:detail', args=[self.done_appointment.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.doctor.full_name)
        self.assertContains(response, self.patient.full_name)
        self.assertContains(response, self.record.diagnosis)
        self.assertContains(response, 'Xem hóa đơn')

    def test_delete_doctor_with_appointments_is_protected(self):
        with self.assertRaises(ProtectedError):
            self.doctor.delete()
