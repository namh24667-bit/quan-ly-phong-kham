from django import forms
from .models import Doctor


class DoctorForm(forms.ModelForm):
    class Meta:
        model = Doctor
        fields = ['full_name', 'specialty', 'phone', 'is_active']
        widgets = {
            'full_name':  forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'BS. Nguyễn Văn A'}),
            'specialty':  forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nội khoa, Nhi khoa...'}),
            'phone':      forms.TextInput(attrs={'class': 'form-control', 'placeholder': '0901234567'}),
            'is_active':  forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'full_name': 'Họ và tên bác sĩ', 'specialty': 'Chuyên khoa',
            'phone': 'Số điện thoại', 'is_active': 'Đang hoạt động',
        }

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        if phone:
            if not phone.isdigit():
                raise forms.ValidationError('Số điện thoại chỉ được chứa chữ số.')
            if not (9 <= len(phone) <= 11):
                raise forms.ValidationError('Số điện thoại phải từ 9–11 chữ số.')
        return phone
