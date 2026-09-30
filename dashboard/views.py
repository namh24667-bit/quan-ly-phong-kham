from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from accounts.decorators import role_required


@login_required
@role_required('admin', 'staff', 'doctor')
def dashboard_index(request):
    from patients.models import Patient
    from doctors.models import Doctor
    from appointments.models import Appointment
    from billing.models import Invoice
    from django.db.models import Sum
    from datetime import timedelta

    today = timezone.localdate()

    patients = Patient.objects.all()
    doctors = Doctor.objects.filter(is_active=True)
    appointments = Appointment.objects.all()
    invoices = Invoice.objects.all()

    if not request.user.is_superuser and request.user.profile.role == 'doctor':
        if not hasattr(request.user, 'doctor'):
            raise PermissionDenied
        doctor = request.user.doctor
        patients = patients.filter(appointment__doctor=doctor).distinct()
        doctors = doctors.filter(pk=doctor.pk)
        appointments = appointments.filter(doctor=doctor)
        invoices = invoices.filter(medical_record__appointment__doctor=doctor)

    stats = {
        'total_patients':    patients.count(),
        'active_doctors':    doctors.count(),
        'appointments_today': appointments.filter(date=today).count(),
        'pending_count':     appointments.filter(status='pending').count(),
        'confirmed_today':   appointments.filter(date=today, status='confirmed').count(),
        'done_total':        appointments.filter(status='done').count(),
        'paid_revenue':      invoices.filter(status='Paid').aggregate(total=Sum('total_amount'))['total'] or 0,
    }

    appointments_today = appointments.filter(
        date=today
    ).select_related('patient', 'doctor').order_by('start_time')

    upcoming = appointments.filter(
        date__gt=today,
        date__lte=today + timedelta(days=7),
        status__in=['pending', 'confirmed'],
    ).select_related('patient', 'doctor').order_by('date', 'start_time')[:10]

    return render(request, 'dashboard/index.html', {
        'stats': stats,
        'appointments_today': appointments_today,
        'upcoming': upcoming,
        'today': today,
    })
