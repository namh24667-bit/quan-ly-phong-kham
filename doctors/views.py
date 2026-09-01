from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from accounts.decorators import role_required
from .models import Doctor
from .forms import DoctorForm


@login_required
@role_required('admin', 'staff')
def doctor_list(request):
    query = request.GET.get('q', '').strip()
    doctors = Doctor.objects.all()
    if query:
        doctors = doctors.filter(
            Q(full_name__icontains=query) | Q(specialty__icontains=query)
        )
    doctors = doctors.annotate(appointment_count=Count('appointment')).order_by('full_name')
    return render(request, 'doctors/doctor_list.html', {
        'doctors': doctors, 'query': query, 'total': doctors.count(),
    })


@login_required
@role_required('admin')
def doctor_create(request):
    if request.method == 'POST':
        form = DoctorForm(request.POST)
        if form.is_valid():
            doctor = form.save()
            messages.success(request, f'Đã thêm bác sĩ {doctor.full_name}!')
            return redirect('doctors:list')
    else:
        form = DoctorForm()
    return render(request, 'doctors/doctor_form.html', {
        'form': form, 'title': 'Thêm Bác Sĩ Mới',
        'button_text': 'Thêm bác sĩ', 'is_update': False,
    })


@login_required
@role_required('admin')
def doctor_update(request, pk):
    doctor = get_object_or_404(Doctor, pk=pk)
    if request.method == 'POST':
        form = DoctorForm(request.POST, instance=doctor)
        if form.is_valid():
            form.save()
            messages.success(request, f'Đã cập nhật thông tin BS. {doctor.full_name}!')
            return redirect('doctors:detail', pk=doctor.pk)
    else:
        form = DoctorForm(instance=doctor)
    return render(request, 'doctors/doctor_form.html', {
        'form': form, 'doctor': doctor,
        'title': f'Sửa: {doctor.full_name}',
        'button_text': 'Lưu thay đổi', 'is_update': True,
    })


@login_required
@role_required('admin')
def doctor_delete(request, pk):
    doctor = get_object_or_404(Doctor, pk=pk)
    active_count = doctor.appointment_set.filter(
        status__in=['pending', 'confirmed', 'checked_in']
    ).count()

    if request.method == 'POST':
        if active_count > 0:
            messages.error(request, f'Không thể xóa! BS. {doctor.full_name} còn {active_count} lịch hẹn đang hoạt động.')
            return redirect('doctors:detail', pk=pk)
        name = doctor.full_name
        doctor.delete()
        messages.success(request, f'Đã xóa bác sĩ {name}.')
        return redirect('doctors:list')

    return render(request, 'doctors/doctor_confirm_delete.html', {
        'doctor': doctor, 'active_count': active_count,
    })


@login_required
@role_required('admin', 'staff', 'doctor')
def doctor_detail(request, pk):
    doctor = get_object_or_404(Doctor, pk=pk)
    try:
        from appointments.models import Appointment
        appointments = Appointment.objects.filter(
            doctor=doctor
        ).select_related('patient').order_by('-date', '-start_time')[:20]
    except Exception:
        appointments = []
    return render(request, 'doctors/doctor_detail.html', {
        'doctor': doctor, 'appointments': appointments,
    })
