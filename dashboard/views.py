from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Sum
from django.utils import timezone
from accounts.decorators import role_required


@login_required
@role_required('admin', 'staff', 'doctor')
def dashboard_index(request):
    from datetime import timedelta

    from patients.models import Patient
    from doctors.models import Doctor
    from appointments.models import Appointment
    from billing.models import Invoice

    today = timezone.localdate()
    dashboard_role = 'admin' if request.user.is_superuser else request.user.profile.role

    appointments = Appointment.objects.all()
    invoices = Invoice.objects.all()

    if dashboard_role == 'doctor':
        if not hasattr(request.user, 'doctor'):
            raise PermissionDenied
        doctor = request.user.doctor
        appointments = appointments.filter(doctor=doctor)

        upcoming_filter = {
            'date__gt': today,
            'date__lte': today + timedelta(days=7),
            'status__in': ['pending', 'confirmed'],
        }
        stats = {
            'total_patients': Patient.objects.filter(
                is_active=True, appointment__doctor=doctor,
            ).distinct().count(),
            'appointments_today': appointments.filter(date=today).count(),
            'checked_in_count': appointments.filter(status='checked_in').count(),
            'done_total': appointments.filter(status='done').count(),
            'upcoming_count': appointments.filter(**upcoming_filter).count(),
        }
    elif dashboard_role == 'staff':
        stats = {
            'total_patients': Patient.objects.filter(is_active=True).count(),
            'appointments_today': appointments.filter(date=today).count(),
            'pending_count': appointments.filter(status='pending').count(),
            'confirmed_count': appointments.filter(status='confirmed').count(),
            'checked_in_count': appointments.filter(status='checked_in').count(),
            'pending_invoices': invoices.filter(status='Pending').count(),
        }
    else:
        stats = {
            'total_patients': Patient.objects.filter(is_active=True).count(),
            'active_doctors': Doctor.objects.filter(is_active=True).count(),
            'appointments_today': appointments.filter(date=today).count(),
            'pending_count': appointments.filter(status='pending').count(),
            'done_total': appointments.filter(status='done').count(),
            'paid_revenue': (
                invoices.filter(status='Paid').aggregate(total=Sum('total_amount'))['total']
                or 0
            ),
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
        'dashboard_role': dashboard_role,
        'stats': stats,
        'appointments_today': appointments_today,
        'upcoming': upcoming,
        'today': today,
    })
