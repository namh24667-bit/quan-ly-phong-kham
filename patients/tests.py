from datetime import date, time

from django.contrib.auth.models import User
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.urls import reverse

from appointments.forms import AppointmentForm
from appointments.models import Appointment, MedicalRecord
from billing.models import Invoice
from doctors.models import Doctor

from .models import Patient


class PatientDeactivationTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='admin', email='admin@example.com', password='password',
        )
        self.patient = Patient.objects.create(
            full_name='Nguyen Van A', date_of_birth='1990-01-01',
            gender='M', phone='0900000000',
        )
        self.doctor = Doctor.objects.create(
            full_name='Doctor A', specialty='General', phone='0910000000',
        )
        self.appointment = Appointment.objects.create(
            patient=self.patient, doctor=self.doctor, date=date.today(),
            start_time=time(8, 0), end_time=time(8, 30), status='done',
        )
        self.record = MedicalRecord.objects.create(
            appointment=self.appointment, symptoms='Cough',
            diagnosis='Cold', treatment='Rest',
        )
        self.invoice = Invoice.objects.create(medical_record=self.record)

    def test_new_patient_is_active_by_default(self):
        patient = Patient.objects.create(
            full_name='Tran Thi B', date_of_birth='1995-01-01',
            gender='F', phone='0900000001',
        )

        self.assertTrue(patient.is_active)

    def test_deactivate_keeps_patient_and_medical_history(self):
        self.client.force_login(self.admin)

        response = self.client.post(reverse('patients:delete', args=[self.patient.pk]))

        self.assertRedirects(response, reverse('patients:list'))
        self.patient.refresh_from_db()
        self.assertFalse(self.patient.is_active)
        self.assertTrue(Patient.objects.filter(pk=self.patient.pk).exists())
        self.assertTrue(Appointment.objects.filter(pk=self.appointment.pk).exists())
        self.assertTrue(MedicalRecord.objects.filter(pk=self.record.pk).exists())
        self.assertTrue(Invoice.objects.filter(pk=self.invoice.pk).exists())

    def test_inactive_patient_is_hidden_from_patient_list_and_search(self):
        self.patient.is_active = False
        self.patient.save(update_fields=['is_active'])
        self.client.force_login(self.admin)

        list_response = self.client.get(reverse('patients:list'))
        search_response = self.client.get(reverse('patients:list'), {'q': 'Nguyen Van A'})

        self.assertNotContains(list_response, self.patient.full_name)
        self.assertEqual(search_response.context['total'], 0)
        self.assertQuerySetEqual(search_response.context['page_obj'].object_list, [])

    def test_inactive_patient_history_is_still_accessible(self):
        self.patient.is_active = False
        self.patient.save(update_fields=['is_active'])
        self.client.force_login(self.admin)

        response = self.client.get(reverse('appointments:detail', args=[self.appointment.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.patient.full_name)

    def test_inactive_patient_cannot_be_selected_for_new_appointment(self):
        self.patient.is_active = False
        self.patient.save(update_fields=['is_active'])

        form = AppointmentForm(data={
            'patient': self.patient.pk,
            'doctor': self.doctor.pk,
            'date': date.today(),
            'start_time': '09:00',
            'end_time': '09:30',
            'note': '',
        })

        self.assertNotIn(self.patient, form.fields['patient'].queryset)
        self.assertFalse(form.is_valid())
        self.assertIn('patient', form.errors)

    def test_existing_appointment_can_keep_inactive_patient(self):
        self.patient.is_active = False
        self.patient.save(update_fields=['is_active'])

        form = AppointmentForm(instance=self.appointment)

        self.assertIn(self.patient, form.fields['patient'].queryset)

    def test_patient_with_appointment_cannot_be_deleted(self):
        with self.assertRaises(ProtectedError):
            self.patient.delete()

        self.assertTrue(Patient.objects.filter(pk=self.patient.pk).exists())
