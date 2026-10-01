from django import forms
from django.forms import inlineformset_factory

from appointments.models import MedicalRecord
from .models import Invoice, Medicine, Prescription, Service


class PrescriptionForm(forms.ModelForm):
    class Meta:
        model = Prescription
        fields = ['medicine', 'quantity', 'dosage']
        widgets = {
            'medicine': forms.Select(attrs={'class': 'form-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'dosage': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ví dụ: Ngày 2 lần, mỗi lần 1 viên'}),
        }


PrescriptionFormSet = inlineformset_factory(
    MedicalRecord, Prescription,
    form=PrescriptionForm,
    extra=1,
    can_delete=True,
)


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ['services']
        widgets = {
            'services': forms.SelectMultiple(attrs={'class': 'form-select', 'size': 6}),
        }
        labels = {'services': 'Dịch vụ'}
