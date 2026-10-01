from django import forms
from django.db.models import Q
from django.utils import timezone

from doctors.models import Doctor, DoctorSchedule
from patients.models import Patient

from .models import Appointment, MedicalRecord


class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ['patient', 'doctor', 'date', 'start_time', 'end_time', 'note']
        widgets = {
            'date':       forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'end_time':   forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'patient':    forms.Select(attrs={'class': 'form-select'}),
            'doctor':     forms.Select(attrs={'class': 'form-select'}),
            'note':       forms.Textarea(attrs={'class': 'form-control', 'rows': 3,
                                                'placeholder': 'Ghi chú (không bắt buộc)...'}),
        }
        labels = {
            'patient': 'Bệnh nhân', 'doctor': 'Bác sĩ',
            'date': 'Ngày khám', 'start_time': 'Giờ bắt đầu',
            'end_time': 'Giờ kết thúc', 'note': 'Ghi chú',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        patients = Patient.objects.filter(is_active=True)
        if self.instance.pk and self.instance.patient_id:
            patients = Patient.objects.filter(
                Q(is_active=True) | Q(pk=self.instance.patient_id)
            )
        self.fields['patient'].queryset = patients

        doctors = Doctor.objects.filter(is_active=True)
        if self.instance.pk and self.instance.doctor_id:
            doctors = Doctor.objects.filter(
                Q(is_active=True) | Q(pk=self.instance.doctor_id)
            )
        self.fields['doctor'].queryset = doctors

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_time')
        end   = cleaned_data.get('end_time')
        if start and end and end <= start:
            raise forms.ValidationError(
                f'Giờ kết thúc ({end.strftime("%H:%M")}) phải sau giờ bắt đầu ({start.strftime("%H:%M")}).'
            )

        date = cleaned_data.get('date')
        time_fields = {'date', 'start_time'}
        check_time = not self.instance.pk or bool(time_fields.intersection(self.changed_data))
        if check_time and date and start:
            now = timezone.localtime()
            if date < now.date() or (date == now.date() and start <= now.time()):
                raise forms.ValidationError('Không thể đặt lịch khám trong quá khứ.')

        schedule_fields = {'doctor', 'date', 'start_time', 'end_time'}
        check_schedule = not self.instance.pk or bool(schedule_fields.intersection(self.changed_data))
        doctor = cleaned_data.get('doctor')
        if check_schedule and doctor and date and start and end:
            if not doctor.is_active:
                raise forms.ValidationError('Bác sĩ đang ngừng hoạt động.')

            schedules = DoctorSchedule.objects.filter(doctor=doctor, is_active=True)
            if not schedules.exists():
                raise forms.ValidationError('Bác sĩ chưa có lịch làm việc.')

            is_in_schedule = schedules.filter(
                weekday=date.weekday(),
                start_time__lte=start,
                end_time__gte=end,
            ).exists()
            if not is_in_schedule:
                raise forms.ValidationError('Lịch hẹn nằm ngoài giờ làm việc của bác sĩ.')
        return cleaned_data


class MedicalRecordForm(forms.ModelForm):
    class Meta:
        model = MedicalRecord
        fields = ['appointment', 'symptoms', 'diagnosis', 'treatment', 'notes']
        widgets = {
            'appointment': forms.Select(attrs={'class': 'form-select'}),
            'symptoms': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'diagnosis': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'treatment': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'appointment': 'Lịch hẹn',
            'symptoms': 'Triệu chứng',
            'diagnosis': 'Chẩn đoán',
            'treatment': 'Hướng điều trị',
            'notes': 'Ghi chú thêm',
        }

    def __init__(self, *args, doctor=None, **kwargs):
        super().__init__(*args, **kwargs)
        queryset = Appointment.objects.select_related('patient')
        if doctor is not None:
            queryset = queryset.filter(doctor=doctor)
        if self.instance.pk:
            queryset = queryset.filter(pk=self.instance.appointment_id)
        else:
            queryset = queryset.filter(
                status='checked_in', medical_record__isnull=True,
            )
        self.fields['appointment'].queryset = queryset.order_by('-date', '-start_time')

    def clean_appointment(self):
        appointment = self.cleaned_data['appointment']
        if hasattr(appointment, 'medical_record') and appointment.medical_record != self.instance:
            raise forms.ValidationError('Lịch hẹn này đã có hồ sơ khám bệnh.')
        return appointment
