from .models import Appointment


def check_appointment_conflict(doctor, date, start_time, end_time, exclude_id=None):
    """
    Kiểm tra xem lịch hẹn có bị trùng giờ không.
    Logic: Hai khoảng [A_start,A_end] và [B_start,B_end] trùng khi:
           A_start < B_end  VÀ  A_end > B_start
    """
    conflicts = Appointment.objects.filter(
        doctor=doctor,
        date=date,
        status__in=['pending', 'confirmed', 'checked_in'],
        start_time__lt=end_time,
        end_time__gt=start_time,
    )
    if exclude_id is not None:
        conflicts = conflicts.exclude(id=exclude_id)
    return conflicts.first()
