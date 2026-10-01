from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from accounts.decorators import role_required
from .models import Patient
from .forms import PatientForm


@login_required
@role_required('admin', 'staff', 'doctor')
def patient_list(request):
    query = request.GET.get('q', '').strip()
    patients = Patient.objects.filter(is_active=True)
    if not request.user.is_superuser and request.user.profile.role == 'doctor':
        if not hasattr(request.user, 'doctor'):
            raise PermissionDenied
        patients = patients.filter(appointment__doctor=request.user.doctor).distinct()
    if query:
        patients = patients.filter(
            Q(full_name__icontains=query) | Q(phone__icontains=query)
        )
    paginator = Paginator(patients, 10)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'patients/patient_list.html', {
        'page_obj': page_obj, 'query': query, 'total': patients.count(),
    })


@login_required
@role_required('admin', 'staff')
def patient_create(request):
    if request.method == 'POST':
        form = PatientForm(request.POST)
        if form.is_valid():
            patient = form.save()
            messages.success(request, f'Đã thêm bệnh nhân {patient.full_name} thành công!')
            return redirect('patients:list')
    else:
        form = PatientForm()
    return render(request, 'patients/patient_form.html', {
        'form': form, 'title': 'Thêm Bệnh Nhân Mới',
        'button_text': 'Thêm bệnh nhân', 'is_update': False,
    })


@login_required
@role_required('admin', 'staff')
def patient_update(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    if request.method == 'POST':
        form = PatientForm(request.POST, instance=patient)
        if form.is_valid():
            form.save()
            messages.success(request, f'Đã cập nhật thông tin {patient.full_name}!')
            return redirect('patients:detail', pk=patient.pk)
    else:
        form = PatientForm(instance=patient)
    return render(request, 'patients/patient_form.html', {
        'form': form, 'patient': patient,
        'title': f'Sửa: {patient.full_name}',
        'button_text': 'Lưu thay đổi', 'is_update': True,
    })


@login_required
@role_required('admin')
def patient_delete(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    if request.method == 'POST':
        name = patient.full_name
        patient.is_active = False
        patient.save(update_fields=['is_active'])
        messages.success(request, f'Đã ngừng hoạt động bệnh nhân {name}.')
        return redirect('patients:list')
    return render(request, 'patients/patient_confirm_delete.html', {'patient': patient})


@login_required
@role_required('admin', 'staff', 'doctor')
def patient_detail(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    appointments = patient.appointment_set.select_related('doctor')
    if not request.user.is_superuser and request.user.profile.role == 'doctor':
        if not hasattr(request.user, 'doctor'):
            raise PermissionDenied
        appointments = appointments.filter(doctor=request.user.doctor)
        if not appointments.exists():
            raise PermissionDenied
    appointments = appointments.order_by('-date', '-start_time')
    return render(request, 'patients/patient_detail.html', {
        'patient': patient, 'appointments': appointments,
    })
