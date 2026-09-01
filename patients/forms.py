from django import forms
from datetime import date
from .models import Patient


class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = ['full_name', 'date_of_birth', 'gender', 'phone', 'address']
        widgets = {
            'full_name':     forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nguyễn Văn A'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'gender':        forms.Select(attrs={'class': 'form-select'}),
            'phone':         forms.TextInput(attrs={'class': 'form-control', 'placeholder': '0901234567'}),
            'address':       forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'full_name': 'Họ và tên', 'date_of_birth': 'Ngày sinh',
            'gender': 'Giới tính', 'phone': 'Số điện thoại', 'address': 'Địa chỉ',
        }

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if not phone.isdigit():
            raise forms.ValidationError('Số điện thoại chỉ được chứa chữ số (0-9).')
        if not (9 <= len(phone) <= 11):
            raise forms.ValidationError(f'Số điện thoại phải từ 9–11 chữ số.')
        return phone

    def clean_date_of_birth(self):
        dob = self.cleaned_data.get('date_of_birth')
        if dob and dob > date.today():
            raise forms.ValidationError('Ngày sinh không thể là ngày trong tương lai.')
        return dob
