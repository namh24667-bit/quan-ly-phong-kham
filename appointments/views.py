from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone
from accounts.decorators import role_required
from .models import Appointment, MedicalRecord
from .forms import AppointmentForm, MedicalRecordForm
from .utils import check_appointment_conflict
from billing.forms import PrescriptionFormSet
from billing.models import Invoice


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
    if appointment.status not in ['pending', 'confirmed']:
        raise PermissionDenied
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
@role_required('admin', 'staff', 'doctor')
def appointment_list(request):
    appointments = Appointment.objects.select_related('patient', 'doctor').order_by('-date', '-start_time')
    if not request.user.is_superuser and request.user.profile.role == 'doctor':
        if not hasattr(request.user, 'doctor'):
            raise PermissionDenied
        appointments = appointments.filter(doctor=request.user.doctor)
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
@role_required('admin', 'staff', 'doctor')
def appointment_detail(request, pk):
    appointment = get_object_or_404(
        Appointment.objects.select_related('patient', 'doctor'), pk=pk
    )
    if (not request.user.is_superuser
            and request.user.profile.role == 'doctor'
            and appointment.doctor.user != request.user):
        raise PermissionDenied
    return render(request, 'appointments/appointment_detail.html', {'appointment': appointment})


# ─── XÁC NHẬN (pending -> confirmed) ─────────────────────────────
@login_required
@role_required('admin', 'staff')
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
@role_required('admin', 'staff')
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
@role_required('admin', 'doctor')
def appointment_done(request, pk):
    if request.method != 'POST':
        return redirect('appointments:list')
    appointment = get_object_or_404(Appointment, pk=pk)
    if (not request.user.is_superuser
            and request.user.profile.role == 'doctor'
            and appointment.doctor.user != request.user):
        raise PermissionDenied
    if appointment.status != 'checked_in':
        messages.error(request, f'Phải ở trạng thái "Đã check-in" mới hoàn thành được.')
        return redirect('appointments:detail', pk=pk)
    appointment.status = 'done'
    appointment.save()
    messages.success(request, 'Lịch hẹn đã hoàn thành!')
    return redirect('appointments:detail', pk=pk)


# ─── HỦY LỊCH ────────────────────────────────────────────────────
@login_required
@role_required('admin', 'staff')
def appointment_cancel(request, pk):
    if request.method != 'POST':
        return redirect('appointments:list')
    appointment = get_object_or_404(Appointment, pk=pk)
    if appointment.status not in ['pending', 'confirmed']:
        messages.error(request, f'Không thể hủy lịch đang ở "{appointment.get_status_display()}".')
        return redirect('appointments:detail', pk=pk)
    old = appointment.get_status_display()
    appointment.status = 'cancelled'
    appointment.save()
    messages.success(request, f'Đã hủy lịch hẹn (trước đó: {old}).')
    return redirect('appointments:detail', pk=pk)


# ─── LỊCH CỦA BÁC SĨ ĐANG ĐĂNG NHẬP ─────────────────────────────
@login_required
@role_required('doctor')
def my_schedule(request):
    if not hasattr(request.user, 'doctor'):
        raise PermissionDenied
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


# ─── TẠO HỒ SƠ KHÁM BỆNH ────────────────────────────────────────
@login_required
@role_required('admin', 'doctor')
def create_medical_record(request):
    doctor = None
    if not request.user.is_superuser and request.user.profile.role == 'doctor':
        if not hasattr(request.user, 'doctor'):
            raise PermissionDenied
        doctor = request.user.doctor
    if request.method == 'POST':
        try:
            appointment = Appointment.objects.filter(
                pk=request.POST.get('appointment')
            ).first()
        except (TypeError, ValueError):
            appointment = None
        if appointment is not None:
            if doctor is not None and appointment.doctor != doctor:
                raise PermissionDenied
            if (appointment.status != 'checked_in'
                    or MedicalRecord.objects.filter(appointment=appointment).exists()):
                raise PermissionDenied
        form = MedicalRecordForm(request.POST, doctor=doctor)
        prescription_formset = PrescriptionFormSet(request.POST)
        if form.is_valid() and prescription_formset.is_valid():
            appointment = form.cleaned_data['appointment']
            if doctor is not None and appointment.doctor != doctor:
                raise PermissionDenied
            if (appointment.status != 'checked_in'
                    or MedicalRecord.objects.filter(appointment=appointment).exists()):
                raise PermissionDenied
            with transaction.atomic():
                record = form.save()
                prescription_formset.instance = record
                prescription_formset.save()
                Invoice.objects.create(medical_record=record).recalculate()
            messages.success(request, f'Đã tạo hồ sơ khám cho {record.appointment.patient.full_name}.')
            return redirect('appointments:detail', pk=record.appointment.pk)
    else:
        form = MedicalRecordForm(doctor=doctor)
        prescription_formset = PrescriptionFormSet()

    return render(request, 'appointments/create_medical_record.html', {
        'form': form,
        'prescription_formset': prescription_formset,
        'title': 'Tạo hồ sơ khám bệnh',
    })


@login_required
@role_required('admin', 'doctor')
def update_medical_record(request, pk):
    record = get_object_or_404(MedicalRecord.objects.select_related('appointment__doctor'), pk=pk)
    doctor = None
    if not request.user.is_superuser and request.user.profile.role == 'doctor':
        if not hasattr(request.user, 'doctor'):
            raise PermissionDenied
        doctor = request.user.doctor
        if record.appointment.doctor != doctor:
            raise PermissionDenied
    if record.appointment.status != 'checked_in':
        raise PermissionDenied
    if hasattr(record, 'invoice') and record.invoice.status == 'Paid':
        raise PermissionDenied
    if request.method == 'POST':
        form = MedicalRecordForm(request.POST, instance=record, doctor=doctor)
        prescription_formset = PrescriptionFormSet(request.POST, instance=record)
        if form.is_valid() and prescription_formset.is_valid():
            with transaction.atomic():
                form.save()
                prescription_formset.save()
                Invoice.objects.get_or_create(medical_record=record)
                record.invoice.recalculate()
            messages.success(request, 'Đã cập nhật hồ sơ và đơn thuốc.')
            return redirect('appointments:detail', pk=record.appointment.pk)
    else:
        form = MedicalRecordForm(instance=record, doctor=doctor)
        prescription_formset = PrescriptionFormSet(instance=record)
    return render(request, 'appointments/create_medical_record.html', {
        'form': form, 'prescription_formset': prescription_formset,
        'title': 'Chỉnh sửa hồ sơ khám bệnh', 'record': record,
    })
