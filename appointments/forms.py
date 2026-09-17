from django import forms
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

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_time')
        end   = cleaned_data.get('end_time')
        if start and end and end <= start:
            raise forms.ValidationError(
                f'Giờ kết thúc ({end.strftime("%H:%M")}) phải sau giờ bắt đầu ({start.strftime("%H:%M")}).'
            )
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
        self.fields['appointment'].queryset = Appointment.objects.filter(
            doctor=doctor,
            medical_record__isnull=True,
        ).select_related('patient').order_by('-date', '-start_time')

    def clean_appointment(self):
        appointment = self.cleaned_data['appointment']
        if hasattr(appointment, 'medical_record'):
            raise forms.ValidationError('Lịch hẹn này đã có hồ sơ khám bệnh.')
        return appointment
