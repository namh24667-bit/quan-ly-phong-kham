from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone


@login_required
def dashboard_index(request):
    from patients.models import Patient
    from doctors.models import Doctor
    from appointments.models import Appointment
    from datetime import timedelta

    today = timezone.localdate()

    stats = {
        'total_patients':    Patient.objects.count(),
        'active_doctors':    Doctor.objects.filter(is_active=True).count(),
        'appointments_today': Appointment.objects.filter(date=today).count(),
        'pending_count':     Appointment.objects.filter(status='pending').count(),
        'confirmed_today':   Appointment.objects.filter(date=today, status='confirmed').count(),
        'done_total':        Appointment.objects.filter(status='done').count(),
    }

    appointments_today = Appointment.objects.filter(
        date=today
    ).select_related('patient', 'doctor').order_by('start_time')

    upcoming = Appointment.objects.filter(
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
