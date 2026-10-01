from datetime import time

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

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
