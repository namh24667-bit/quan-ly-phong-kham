from datetime import timedelta, time

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from billing.models import Invoice, Medicine, Prescription
from doctors.models import Doctor, DoctorSchedule
from patients.models import Patient

from .models import Appointment, MedicalRecord


class AppointmentScheduleTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(username='schedule_staff')
        self.staff.profile.role = 'staff'
        self.staff.profile.save()
        self.doctor = Doctor.objects.create(full_name='Doctor A', specialty='General')
        self.patient = Patient.objects.create(
            full_name='Patient A', date_of_birth='1990-01-01',
            gender='M', phone='0900000001',
        )
        self.schedule = DoctorSchedule.objects.create(
            doctor=self.doctor, weekday=0,
            start_time=time(8), end_time=time(12),
        )
        today = timezone.localdate()
        days_until_monday = (7 - today.weekday()) % 7 or 7
        self.monday = today + timedelta(days=days_until_monday)
        self.client.force_login(self.staff)

    def appointment_data(self, doctor=None, appointment_date=None,
                         start='09:00', end='10:00'):
        return {
            'patient': self.patient.pk,
            'doctor': (doctor or self.doctor).pk,
            'date': appointment_date or self.monday,
            'start_time': start,
            'end_time': end,
            'note': '',
        }

    def test_appointment_inside_schedule_is_created(self):
        response = self.client.post(
            reverse('appointments:create'), self.appointment_data()
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Appointment.objects.count(), 1)

    def test_appointment_on_yesterday_is_rejected(self):
        response = self.client.post(
            reverse('appointments:create'),
            self.appointment_data(
                appointment_date=timezone.localdate() - timedelta(days=1)
            ),
        )

        self.assertContains(response, 'Không thể đặt lịch khám trong quá khứ.')
        self.assertFalse(Appointment.objects.exists())

    def test_appointment_today_with_past_start_time_is_rejected(self):
        response = self.client.post(
            reverse('appointments:create'),
            self.appointment_data(
                appointment_date=timezone.localdate(),
                start='00:00', end='00:30',
            ),
        )

        self.assertContains(response, 'Không thể đặt lịch khám trong quá khứ.')
        self.assertFalse(Appointment.objects.exists())

    def test_appointment_starting_before_schedule_is_rejected(self):
        response = self.client.post(
            reverse('appointments:create'),
            self.appointment_data(start='07:30', end='09:00'),
        )

        self.assertContains(response, 'Lịch hẹn nằm ngoài giờ làm việc của bác sĩ.')
        self.assertFalse(Appointment.objects.exists())

    def test_appointment_ending_after_schedule_is_rejected(self):
        response = self.client.post(
            reverse('appointments:create'),
            self.appointment_data(start='11:30', end='12:30'),
        )

        self.assertContains(response, 'Lịch hẹn nằm ngoài giờ làm việc của bác sĩ.')
        self.assertFalse(Appointment.objects.exists())

    def test_appointment_on_day_without_schedule_is_rejected(self):
        response = self.client.post(
            reverse('appointments:create'),
            self.appointment_data(appointment_date=self.monday + timedelta(days=1)),
        )

        self.assertContains(response, 'Lịch hẹn nằm ngoài giờ làm việc của bác sĩ.')
        self.assertFalse(Appointment.objects.exists())

    def test_doctor_without_active_schedule_is_rejected(self):
        doctor = Doctor.objects.create(full_name='Doctor B', specialty='General')

        response = self.client.post(
            reverse('appointments:create'), self.appointment_data(doctor=doctor)
        )

        self.assertContains(response, 'Bác sĩ chưa có lịch làm việc.')
        self.assertFalse(Appointment.objects.exists())

    def test_inactive_schedule_is_not_used(self):
        self.schedule.is_active = False
        self.schedule.save(update_fields=['is_active'])

        response = self.client.post(
            reverse('appointments:create'), self.appointment_data()
        )

        self.assertContains(response, 'Bác sĩ chưa có lịch làm việc.')
        self.assertFalse(Appointment.objects.exists())

    def test_inactive_doctor_cannot_be_selected(self):
        doctor = Doctor.objects.create(
            full_name='Inactive Doctor', specialty='General', is_active=False
        )

        response = self.client.post(
            reverse('appointments:create'), self.appointment_data(doctor=doctor)
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('doctor', response.context['form'].errors)
        self.assertFalse(Appointment.objects.exists())

    def test_editing_appointment_outside_schedule_is_rejected(self):
        appointment = Appointment.objects.create(
            patient=self.patient, doctor=self.doctor, date=self.monday,
            start_time=time(9), end_time=time(10),
        )

        response = self.client.post(
            reverse('appointments:update', args=[appointment.pk]),
            self.appointment_data(start='13:00', end='14:00'),
        )

        self.assertContains(response, 'Lịch hẹn nằm ngoài giờ làm việc của bác sĩ.')
        appointment.refresh_from_db()
        self.assertEqual(appointment.start_time, time(9))

    def test_editing_pending_appointment_to_past_is_rejected(self):
        appointment = Appointment.objects.create(
            patient=self.patient, doctor=self.doctor, date=self.monday,
            start_time=time(9), end_time=time(10),
        )

        response = self.client.post(
            reverse('appointments:update', args=[appointment.pk]),
            self.appointment_data(
                appointment_date=timezone.localdate() - timedelta(days=1)
            ),
        )

        self.assertContains(response, 'Không thể đặt lịch khám trong quá khứ.')
        appointment.refresh_from_db()
        self.assertEqual(appointment.date, self.monday)

    def test_historical_appointment_still_has_detail_page(self):
        appointment = Appointment.objects.create(
            patient=self.patient, doctor=self.doctor,
            date=timezone.localdate() - timedelta(days=1),
            start_time=time(9), end_time=time(10), status='done',
        )

        response = self.client.get(
            reverse('appointments:detail', args=[appointment.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.patient.full_name)

    def test_old_appointment_remains_visible_after_doctor_and_schedule_deactivate(self):
        appointment = Appointment.objects.create(
            patient=self.patient, doctor=self.doctor, date=self.monday,
            start_time=time(9), end_time=time(10),
        )
        self.schedule.is_active = False
        self.schedule.save(update_fields=['is_active'])
        self.doctor.is_active = False
        self.doctor.save(update_fields=['is_active'])

        response = self.client.get(
            reverse('appointments:detail', args=[appointment.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.patient.full_name)


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
        user = User.objects.create_user(username=username)
        user.profile.role = role
        user.profile.save()
        return user

    def make_appointment(self, patient, doctor, status, hour):
        return Appointment.objects.create(
            patient=patient,
            doctor=doctor,
            date=timezone.localdate(),
            start_time=time(hour, 0),
            end_time=time(hour, 30),
            status=status,
        )

    def medical_record_data(self, appointment):
        return {
            'appointment': appointment.pk,
            'symptoms': 'Symptoms',
            'diagnosis': 'Diagnosis',
            'treatment': 'Treatment',
            'notes': '',
            'prescriptions-TOTAL_FORMS': '0',
            'prescriptions-INITIAL_FORMS': '0',
            'prescriptions-MIN_NUM_FORMS': '0',
            'prescriptions-MAX_NUM_FORMS': '1000',
        }

    def appointment_data(self, appointment, note='Updated note'):
        return {
            'patient': appointment.patient_id,
            'doctor': appointment.doctor_id,
            'date': appointment.date,
            'start_time': appointment.start_time,
            'end_time': appointment.end_time,
            'note': note,
        }

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
        self.appointment.status = 'checked_in'
        self.appointment.save(update_fields=['status'])
        self.client.force_login(self.doctor_user)

        own_response = self.client.get(reverse('appointments:medical_record_update', args=[self.record.pk]))
        other_response = self.client.get(
            reverse('appointments:medical_record_update', args=[self.other_record.pk])
        )

        self.assertEqual(own_response.status_code, 200)
        self.assertEqual(other_response.status_code, 403)

    def test_doctor_cannot_skip_appointment_workflow(self):
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
        self.appointment.status = 'checked_in'
        self.appointment.save(update_fields=['status'])
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

    def test_pending_cannot_change_directly_to_done(self):
        self.client.force_login(self.admin)

        response = self.client.post(reverse('appointments:done', args=[self.appointment.pk]))

        self.assertEqual(response.status_code, 302)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, 'pending')

    def test_confirmed_changes_to_checked_in_for_staff(self):
        appointment = self.make_appointment(self.patient, self.doctor, 'confirmed', 11)
        self.client.force_login(self.staff)

        response = self.client.post(reverse('appointments:checkin', args=[appointment.pk]))

        self.assertEqual(response.status_code, 302)
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, 'checked_in')

    def test_confirmed_cannot_change_directly_to_done(self):
        appointment = self.make_appointment(self.patient, self.doctor, 'confirmed', 12)
        self.client.force_login(self.admin)

        response = self.client.post(reverse('appointments:done', args=[appointment.pk]))

        self.assertEqual(response.status_code, 302)
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, 'confirmed')

    def test_doctor_finishes_own_checked_in_appointment(self):
        appointment = self.make_appointment(self.patient, self.doctor, 'checked_in', 13)
        MedicalRecord.objects.create(
            appointment=appointment, symptoms='A', diagnosis='A', treatment='A',
        )
        self.client.force_login(self.doctor_user)

        response = self.client.post(reverse('appointments:done', args=[appointment.pk]))

        self.assertEqual(response.status_code, 302)
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, 'done')

    def test_doctor_cannot_finish_checked_in_without_medical_record(self):
        appointment = self.make_appointment(self.patient, self.doctor, 'checked_in', 13)
        self.client.force_login(self.doctor_user)

        response = self.client.post(reverse('appointments:done', args=[appointment.pk]))

        self.assertEqual(response.status_code, 403)
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, 'checked_in')

    def test_staff_cannot_finish_checked_in_appointment(self):
        appointment = self.make_appointment(self.patient, self.doctor, 'checked_in', 13)
        MedicalRecord.objects.create(
            appointment=appointment, symptoms='A', diagnosis='A', treatment='A',
        )
        self.client.force_login(self.staff)

        response = self.client.post(reverse('appointments:done', args=[appointment.pk]))

        self.assertEqual(response.status_code, 302)
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, 'checked_in')

    def test_doctor_cannot_finish_another_doctors_appointment(self):
        appointment = self.make_appointment(
            self.other_patient, self.other_doctor, 'checked_in', 14,
        )
        self.client.force_login(self.doctor_user)

        response = self.client.post(reverse('appointments:done', args=[appointment.pk]))

        self.assertEqual(response.status_code, 403)
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, 'checked_in')

    def test_done_and_cancelled_appointments_cannot_change_status(self):
        self.client.force_login(self.admin)

        for status, hour in [('done', 15), ('cancelled', 16)]:
            with self.subTest(status=status):
                appointment = self.make_appointment(
                    self.patient, self.doctor, status, hour,
                )
                for name in ['confirm', 'checkin', 'done']:
                    response = self.client.post(
                        reverse(f'appointments:{name}', args=[appointment.pk])
                    )
                    self.assertEqual(response.status_code, 302)
                appointment.refresh_from_db()
                self.assertEqual(appointment.status, status)

    def test_staff_can_cancel_pending_and_confirmed_appointments(self):
        self.client.force_login(self.staff)

        for status, hour in [('pending', 19), ('confirmed', 20)]:
            with self.subTest(status=status):
                appointment = self.make_appointment(
                    self.patient, self.doctor, status, hour,
                )
                response = self.client.post(
                    reverse('appointments:cancel', args=[appointment.pk])
                )

                self.assertEqual(response.status_code, 302)
                appointment.refresh_from_db()
                self.assertEqual(appointment.status, 'cancelled')

    def test_staff_cannot_cancel_checked_in_done_or_cancelled_appointments(self):
        self.client.force_login(self.staff)

        for status, hour in [('checked_in', 21), ('done', 22), ('cancelled', 23)]:
            with self.subTest(status=status):
                appointment = self.make_appointment(
                    self.patient, self.doctor, status, hour,
                )
                response = self.client.post(
                    reverse('appointments:cancel', args=[appointment.pk])
                )

                self.assertEqual(response.status_code, 302)
                appointment.refresh_from_db()
                self.assertEqual(appointment.status, status)

    def test_only_checked_in_appointment_can_create_medical_record(self):
        pending = self.make_appointment(self.patient, self.doctor, 'pending', 16)
        checked_in = self.make_appointment(self.patient, self.doctor, 'checked_in', 17)
        self.client.force_login(self.doctor_user)

        denied_response = self.client.post(
            reverse('appointments:medical_record_create'),
            self.medical_record_data(pending),
        )
        success_response = self.client.post(
            reverse('appointments:medical_record_create'),
            self.medical_record_data(checked_in),
        )

        self.assertEqual(denied_response.status_code, 403)
        self.assertEqual(success_response.status_code, 302)
        self.assertFalse(MedicalRecord.objects.filter(appointment=pending).exists())
        self.assertTrue(MedicalRecord.objects.filter(appointment=checked_in).exists())
        checked_in.refresh_from_db()
        self.assertEqual(checked_in.status, 'checked_in')

    def test_appointment_actions_match_backend_roles(self):
        create_url = reverse('appointments:create')
        confirm_url = reverse('appointments:confirm', args=[self.appointment.pk])
        cancel_url = reverse('appointments:cancel', args=[self.appointment.pk])
        update_url = reverse('appointments:update', args=[self.appointment.pk])
        superuser = User.objects.create_superuser(username='superuser')

        self.client.force_login(self.doctor_user)
        list_response = self.client.get(reverse('appointments:list'))
        detail_response = self.client.get(
            reverse('appointments:detail', args=[self.appointment.pk])
        )
        self.assertNotContains(list_response, create_url)
        self.assertNotContains(detail_response, confirm_url)
        self.assertNotContains(detail_response, cancel_url)
        self.assertNotContains(detail_response, update_url)

        for user in [self.staff, self.admin, superuser]:
            with self.subTest(username=user.username):
                self.client.force_login(user)
                list_response = self.client.get(reverse('appointments:list'))
                detail_response = self.client.get(
                    reverse('appointments:detail', args=[self.appointment.pk])
                )
                self.assertContains(list_response, create_url)
                self.assertContains(detail_response, confirm_url)
                self.assertContains(detail_response, cancel_url)
                self.assertContains(detail_response, update_url)

    def test_done_action_requires_medical_record_and_backend_role(self):
        appointment = self.make_appointment(self.patient, self.doctor, 'checked_in', 17)
        detail_url = reverse('appointments:detail', args=[appointment.pk])
        done_url = reverse('appointments:done', args=[appointment.pk])

        self.client.force_login(self.doctor_user)
        self.assertNotContains(self.client.get(detail_url), done_url)

        MedicalRecord.objects.create(
            appointment=appointment, symptoms='A', diagnosis='A', treatment='A',
        )
        self.assertContains(self.client.get(detail_url), done_url)

        self.client.force_login(self.staff)
        self.assertNotContains(self.client.get(detail_url), done_url)

        superuser = User.objects.create_superuser(username='done_superuser')
        for user in [self.admin, superuser]:
            with self.subTest(username=user.username):
                self.client.force_login(user)
                self.assertContains(self.client.get(detail_url), done_url)

    def test_doctor_cannot_create_medical_record_for_another_doctor(self):
        appointment = self.make_appointment(
            self.other_patient, self.other_doctor, 'checked_in', 18,
        )
        self.client.force_login(self.doctor_user)

        response = self.client.post(
            reverse('appointments:medical_record_create'),
            self.medical_record_data(appointment),
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(MedicalRecord.objects.filter(appointment=appointment).exists())

    def test_appointment_cannot_have_second_medical_record(self):
        self.appointment.status = 'checked_in'
        self.appointment.save(update_fields=['status'])
        self.client.force_login(self.doctor_user)

        response = self.client.post(
            reverse('appointments:medical_record_create'),
            self.medical_record_data(self.appointment),
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(MedicalRecord.objects.filter(appointment=self.appointment).count(), 1)

    def test_staff_can_edit_pending_appointment(self):
        self.client.force_login(self.staff)

        response = self.client.post(
            reverse('appointments:update', args=[self.appointment.pk]),
            self.appointment_data(self.appointment),
        )

        self.assertEqual(response.status_code, 302)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.note, 'Updated note')

    def test_staff_can_edit_confirmed_appointment(self):
        appointment = self.make_appointment(self.patient, self.doctor, 'confirmed', 10)
        self.client.force_login(self.staff)

        response = self.client.post(
            reverse('appointments:update', args=[appointment.pk]),
            self.appointment_data(appointment),
        )

        self.assertEqual(response.status_code, 302)
        appointment.refresh_from_db()
        self.assertEqual(appointment.note, 'Updated note')

    def test_staff_cannot_edit_locked_appointments(self):
        self.client.force_login(self.staff)

        for status, hour in [('checked_in', 10), ('done', 11), ('cancelled', 12)]:
            with self.subTest(status=status):
                appointment = self.make_appointment(
                    self.patient, self.doctor, status, hour,
                )
                url = reverse('appointments:update', args=[appointment.pk])

                self.assertEqual(self.client.get(url).status_code, 403)
                response = self.client.post(
                    url, self.appointment_data(appointment, note='Changed'),
                )

                self.assertEqual(response.status_code, 403)
                appointment.refresh_from_db()
                self.assertEqual(appointment.note, '')

    def test_admin_cannot_edit_done_appointment(self):
        appointment = self.make_appointment(self.patient, self.doctor, 'done', 10)
        self.client.force_login(self.admin)
        url = reverse('appointments:update', args=[appointment.pk])

        get_response = self.client.get(url)
        post_response = self.client.post(url, self.appointment_data(appointment))

        self.assertEqual(get_response.status_code, 403)
        self.assertEqual(post_response.status_code, 403)
        appointment.refresh_from_db()
        self.assertEqual(appointment.note, '')

    def test_doctor_can_update_medical_record_while_checked_in(self):
        self.appointment.status = 'checked_in'
        self.appointment.save(update_fields=['status'])
        self.client.force_login(self.doctor_user)

        response = self.client.post(
            reverse('appointments:medical_record_update', args=[self.record.pk]),
            self.medical_record_data(self.appointment),
        )

        self.assertEqual(response.status_code, 302)
        self.record.refresh_from_db()
        self.assertEqual(self.record.diagnosis, 'Diagnosis')

    def test_paid_invoice_blocks_medical_record_and_prescription_update(self):
        medicine = Medicine.objects.create(
            name='Locked Medicine', unit_price='10000', unit='Viên'
        )
        prescription = Prescription.objects.create(
            medical_record=self.record, medicine=medicine,
            quantity=1, dosage='Ngày 1 lần',
        )
        self.appointment.status = 'checked_in'
        self.appointment.save(update_fields=['status'])
        self.invoice.recalculate()
        self.invoice.status = 'Paid'
        self.invoice.save(update_fields=['status'])
        old_total = self.invoice.total_amount
        self.client.force_login(self.doctor_user)
        url = reverse('appointments:medical_record_update', args=[self.record.pk])

        get_response = self.client.get(url)
        post_response = self.client.post(url, self.medical_record_data(self.appointment))

        self.assertEqual(get_response.status_code, 403)
        self.assertEqual(post_response.status_code, 403)
        prescription.refresh_from_db()
        self.invoice.refresh_from_db()
        self.assertEqual(prescription.quantity, 1)
        self.assertEqual(self.invoice.total_amount, old_total)

    def test_doctor_cannot_update_done_medical_record(self):
        self.appointment.status = 'done'
        self.appointment.save(update_fields=['status'])
        self.client.force_login(self.doctor_user)
        url = reverse('appointments:medical_record_update', args=[self.record.pk])

        get_response = self.client.get(url)
        post_response = self.client.post(url, self.medical_record_data(self.appointment))

        self.assertEqual(get_response.status_code, 403)
        self.assertEqual(post_response.status_code, 403)
        self.record.refresh_from_db()
        self.assertEqual(self.record.diagnosis, 'A')

    def test_done_medical_record_is_still_visible(self):
        self.appointment.status = 'done'
        self.appointment.save(update_fields=['status'])
        self.client.force_login(self.doctor_user)

        response = self.client.get(
            reverse('appointments:detail', args=[self.appointment.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.record.diagnosis)
        self.assertNotContains(response, 'Sửa hồ sơ và đơn thuốc')


class AppointmentListFilterTests(TestCase):
    def setUp(self):
        self.admin = self.make_user('filter_admin', 'admin')
        self.staff = self.make_user('filter_staff', 'staff')
        self.doctor_user = self.make_user('filter_doctor_a', 'doctor')
        self.other_doctor_user = self.make_user('filter_doctor_b', 'doctor')
        self.doctor = Doctor.objects.create(
            user=self.doctor_user, full_name='Bac Si An', specialty='General'
        )
        self.other_doctor = Doctor.objects.create(
            user=self.other_doctor_user, full_name='Bac Si Binh', specialty='General'
        )
        self.patient = Patient.objects.create(
            full_name='Nguyen Van An', date_of_birth='1990-01-01',
            gender='M', phone='0900000101',
        )
        self.other_patient = Patient.objects.create(
            full_name='Tran Van Binh', date_of_birth='1991-01-01',
            gender='M', phone='0900000102',
        )
        self.today = timezone.localdate()
        self.tomorrow = self.today + timedelta(days=1)
        self.own_appointment = self.make_appointment(
            self.patient, self.doctor, 'pending', self.today, 8
        )
        self.other_appointment = self.make_appointment(
            self.other_patient, self.other_doctor, 'confirmed', self.tomorrow, 9
        )

    def make_user(self, username, role):
        user = User.objects.create_user(username=username)
        user.profile.role = role
        user.profile.save()
        return user

    def make_appointment(self, patient, doctor, status, date, hour):
        return Appointment.objects.create(
            patient=patient, doctor=doctor, status=status, date=date,
            start_time=time(hour), end_time=time(hour, 30),
        )

    def page_appointments(self, response):
        return list(response.context['page_obj'].object_list)

    def test_appointment_list_is_paginated_by_ten(self):
        for index in range(10):
            self.make_appointment(
                self.patient, self.doctor, 'pending', self.today, 10 + index
            )
        self.client.force_login(self.admin)

        response = self.client.get(reverse('appointments:list'), {'page': 2})

        self.assertEqual(response.context['page_obj'].number, 2)
        self.assertEqual(len(response.context['page_obj']), 2)

    def test_search_matches_patient_name(self):
        self.client.force_login(self.staff)

        response = self.client.get(reverse('appointments:list'), {'q': 'Nguyen'})

        self.assertEqual(self.page_appointments(response), [self.own_appointment])

    def test_search_matches_doctor_name_for_admin_and_staff(self):
        for user in [self.admin, self.staff]:
            with self.subTest(role=user.profile.role):
                self.client.force_login(user)
                response = self.client.get(
                    reverse('appointments:list'), {'q': 'Bac Si Binh'}
                )
                self.assertEqual(
                    self.page_appointments(response), [self.other_appointment]
                )

    def test_status_filter_uses_valid_appointment_status(self):
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse('appointments:list'), {'status': 'confirmed'}
        )

        self.assertEqual(self.page_appointments(response), [self.other_appointment])

    def test_date_filter_uses_iso_date(self):
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse('appointments:list'), {'date': self.today.isoformat()}
        )

        self.assertEqual(self.page_appointments(response), [self.own_appointment])

    def test_search_status_and_date_filters_combine(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse('appointments:list'), {
            'q': 'Nguyen', 'status': 'pending', 'date': self.today.isoformat(),
        })

        self.assertEqual(self.page_appointments(response), [self.own_appointment])

    def test_doctor_filters_cannot_reveal_another_doctors_appointment(self):
        self.client.force_login(self.doctor_user)

        response = self.client.get(reverse('appointments:list'), {
            'q': 'Tran Van Binh',
            'status': 'confirmed',
            'date': self.tomorrow.isoformat(),
        })

        self.assertEqual(self.page_appointments(response), [])
        self.assertNotContains(
            response, reverse('appointments:detail', args=[self.other_appointment.pk])
        )

    def test_pagination_link_preserves_combined_filters(self):
        for index in range(10):
            self.make_appointment(
                self.patient, self.doctor, 'pending', self.today, 10 + index
            )
        self.client.force_login(self.admin)

        response = self.client.get(reverse('appointments:list'), {
            'q': 'Nguyen', 'status': 'pending', 'date': self.today.isoformat(),
        })

        expected_query = (
            f'q=Nguyen&amp;status=pending&amp;date={self.today.isoformat()}&amp;page=2'
        )
        self.assertContains(response, expected_query)

    def test_invalid_status_and_date_are_ignored(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse('appointments:list'), {
            'status': 'unknown', 'date': 'not-a-date',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total'], 2)
