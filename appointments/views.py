from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from accounts.decorators import role_required
from .models import Appointment
from .forms import AppointmentForm
from .utils import check_appointment_conflict


# ─── TẠO LỊCH HẸN ────────────────────────────────────────────────
@login_required
@role_required('admin', 'staff')
def appointment_create(request):
    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        if form.is_valid():
            doctor     = form.cleaned_data['doctor']
            date       = form.cleaned_data['date']
            start_time = form.cleaned_data['start_time']
            end_time   = form.cleaned_data['end_time']
            conflict = check_appointment_conflict(doctor, date, start_time, end_time)
            if conflict:
                messages.error(request,
                    f'Trùng lịch! Bác sĩ {doctor.full_name} đã có lịch '
                    f'{conflict.start_time.strftime("%H:%M")}–{conflict.end_time.strftime("%H:%M")} '
                    f'với {conflict.patient.full_name}.')
            else:
                appt = form.save()
                messages.success(request, f'Đã tạo lịch hẹn cho {appt.patient.full_name}!')
                return redirect('appointments:list')
    else:
        form = AppointmentForm()
    return render(request, 'appointments/appointment_form.html', {
        'form': form, 'action': 'Tạo mới', 'title': 'Tạo lịch hẹn mới'
    })


# ─── SỬA LỊCH HẸN ────────────────────────────────────────────────
@login_required
@role_required('admin', 'staff')
def appointment_update(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)
    if request.method == 'POST':
        form = AppointmentForm(request.POST, instance=appointment)
        if form.is_valid():
            doctor     = form.cleaned_data['doctor']
            date       = form.cleaned_data['date']
            start_time = form.cleaned_data['start_time']
            end_time   = form.cleaned_data['end_time']
            conflict = check_appointment_conflict(doctor, date, start_time, end_time,
                                                  exclude_id=appointment.pk)
            if conflict:
                messages.error(request,
                    f'Trùng lịch! Bác sĩ {doctor.full_name} đã có lịch '
                    f'{conflict.start_time.strftime("%H:%M")}–{conflict.end_time.strftime("%H:%M")}.')
            else:
                form.save()
                messages.success(request, 'Đã cập nhật lịch hẹn!')
                return redirect('appointments:list')
    else:
        form = AppointmentForm(instance=appointment)
    return render(request, 'appointments/appointment_form.html', {
        'form': form, 'appointment': appointment,
        'action': 'Cập nhật', 'title': f'Chỉnh sửa lịch hẹn #{pk}'
    })


# ─── DANH SÁCH LỊCH HẸN ──────────────────────────────────────────
@login_required
def appointment_list(request):
    appointments = Appointment.objects.select_related('patient', 'doctor').order_by('-date', '-start_time')
    status_filter = request.GET.get('status', '')
    date_filter   = request.GET.get('date', '')
    if status_filter:
        appointments = appointments.filter(status=status_filter)
    if date_filter:
        appointments = appointments.filter(date=date_filter)
    return render(request, 'appointments/appointment_list.html', {
        'appointments': appointments,
        'status_filter': status_filter,
        'date_filter': date_filter,
        'status_choices': Appointment.STATUS_CHOICES,
    })


# ─── CHI TIẾT LỊCH HẸN ───────────────────────────────────────────
@login_required
def appointment_detail(request, pk):
    appointment = get_object_or_404(
        Appointment.objects.select_related('patient', 'doctor'), pk=pk
    )
    return render(request, 'appointments/appointment_detail.html', {'appointment': appointment})


# ─── XÁC NHẬN (pending -> confirmed) ─────────────────────────────
@login_required
def appointment_confirm(request, pk):
    if request.method != 'POST':
        return redirect('appointments:list')
    appointment = get_object_or_404(Appointment, pk=pk)
    if appointment.status != 'pending':
        messages.error(request, f'Không thể xác nhận lịch đang ở "{appointment.get_status_display()}".')
        return redirect('appointments:detail', pk=pk)
    appointment.status = 'confirmed'
    appointment.save()
    messages.success(request, 'Lịch hẹn đã được xác nhận!')
    return redirect('appointments:detail', pk=pk)


# ─── CHECK-IN (confirmed -> checked_in) ──────────────────────────
@login_required
def appointment_checkin(request, pk):
    if request.method != 'POST':
        return redirect('appointments:list')
    appointment = get_object_or_404(Appointment, pk=pk)
    if appointment.status != 'confirmed':
        messages.error(request, f'Phải ở trạng thái "Đã xác nhận" mới check-in được.')
        return redirect('appointments:detail', pk=pk)
    appointment.status = 'checked_in'
    appointment.save()
    messages.success(request, 'Check-in thành công!')
    return redirect('appointments:detail', pk=pk)


# ─── HOÀN THÀNH (checked_in -> done) ─────────────────────────────
@login_required
def appointment_done(request, pk):
    if request.method != 'POST':
        return redirect('appointments:list')
    appointment = get_object_or_404(Appointment, pk=pk)
    if appointment.status != 'checked_in':
        messages.error(request, f'Phải ở trạng thái "Đã check-in" mới hoàn thành được.')
        return redirect('appointments:detail', pk=pk)
    appointment.status = 'done'
    appointment.save()
    messages.success(request, 'Lịch hẹn đã hoàn thành!')
    return redirect('appointments:detail', pk=pk)


# ─── HỦY LỊCH ────────────────────────────────────────────────────
@login_required
def appointment_cancel(request, pk):
    if request.method != 'POST':
        return redirect('appointments:list')
    appointment = get_object_or_404(Appointment, pk=pk)
    if appointment.status in ['done', 'cancelled']:
        messages.error(request, f'Không thể hủy lịch đang ở "{appointment.get_status_display()}".')
        return redirect('appointments:detail', pk=pk)
    old = appointment.get_status_display()
    appointment.status = 'cancelled'
    appointment.save()
    messages.success(request, f'Đã hủy lịch hẹn (trước đó: {old}).')
    return redirect('appointments:detail', pk=pk)


# ─── LỊCH CỦA BÁC SĨ ĐANG ĐĂNG NHẬP ─────────────────────────────
@login_required
def my_schedule(request):
    if not hasattr(request.user, 'doctor'):
        messages.error(request, 'Trang này chỉ dành cho bác sĩ.')
        return redirect('appointments:list')
    doctor = request.user.doctor
    today  = timezone.localdate()
    appointments = Appointment.objects.filter(
        doctor=doctor, date__gte=today,
    ).select_related('patient').order_by('date', 'start_time')
    grouped = {}
    for appt in appointments:
        if appt.date not in grouped:
            grouped[appt.date] = []
        grouped[appt.date].append(appt)
    return render(request, 'appointments/my_schedule.html', {
        'doctor': doctor, 'grouped_appointments': grouped, 'today': today,
    })
