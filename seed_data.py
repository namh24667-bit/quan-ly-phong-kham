"""
Script tạo dữ liệu mẫu cho ClinicMS.
Chạy: python seed_data.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinicms.settings')
django.setup()

from django.contrib.auth.models import User
from patients.models import Patient
from doctors.models import Doctor
from appointments.models import Appointment
from datetime import date, time, timedelta

print("Bắt đầu tạo dữ liệu mẫu...")

# ─── TÀI KHOẢN ────────────────────────────────────────────────────
def make_user(username, password, first_name, last_name, role):
    u, created = User.objects.get_or_create(username=username)
    if created:
        u.set_password(password)
        u.first_name = first_name
        u.last_name = last_name
        u.save()
    u.profile.role = role
    u.profile.save()
    return u, created

admin_u, _ = make_user('admin', 'admin123', 'Admin', 'ClinicMS', 'admin')
print(f"  Tài khoản admin: admin / admin123")

staff_u, _ = make_user('nhanvien', 'nhanvien123', 'Nhân viên', 'Lễ tân', 'staff')
print(f"  Tài khoản nhân viên: nhanvien / nhanvien123")

doc1_user, _ = make_user('bacsi_an', 'bacsi123', 'Văn An', 'Nguyễn', 'doctor')
doc2_user, _ = make_user('bacsi_binh', 'bacsi123', 'Thị Bình', 'Trần', 'doctor')
print(f"  Tài khoản bác sĩ: bacsi_an / bacsi123, bacsi_binh / bacsi123")

# ─── BÁC SĨ ───────────────────────────────────────────────────────
d1, _ = Doctor.objects.get_or_create(
    full_name='Nguyễn Văn An',
    defaults={'specialty': 'Nội khoa', 'phone': '0901111111', 'user': doc1_user}
)
d2, _ = Doctor.objects.get_or_create(
    full_name='Trần Thị Bình',
    defaults={'specialty': 'Nhi khoa', 'phone': '0902222222', 'user': doc2_user}
)
d3, _ = Doctor.objects.get_or_create(
    full_name='Lê Văn Cường',
    defaults={'specialty': 'Tim mạch', 'phone': '0903333333'}
)
print(f"  Đã tạo 3 bác sĩ")

# ─── BỆNH NHÂN ────────────────────────────────────────────────────
p1, _ = Patient.objects.get_or_create(phone='0901234567', defaults={
    'full_name': 'Phạm Thị Dung', 'date_of_birth': date(1985, 3, 15), 'gender': 'F',
    'address': '123 Nguyễn Huệ, Q.1, TP.HCM'
})
p2, _ = Patient.objects.get_or_create(phone='0902345678', defaults={
    'full_name': 'Hoàng Văn Em', 'date_of_birth': date(1990, 7, 22), 'gender': 'M',
    'address': '456 Lê Lợi, Q.3, TP.HCM'
})
p3, _ = Patient.objects.get_or_create(phone='0903456789', defaults={
    'full_name': 'Vũ Thị Phương', 'date_of_birth': date(1978, 11, 5), 'gender': 'F',
    'address': '789 Trần Hưng Đạo, Q.5, TP.HCM'
})
p4, _ = Patient.objects.get_or_create(phone='0904567890', defaults={
    'full_name': 'Đặng Văn Giang', 'date_of_birth': date(2000, 4, 18), 'gender': 'M',
    'address': '321 CMT8, Q.10, TP.HCM'
})
print(f"  Đã tạo 4 bệnh nhân")

# ─── LỊCH HẸN ─────────────────────────────────────────────────────
today = date.today()

appts = [
    # Hôm nay
    dict(patient=p1, doctor=d1, date=today, start_time=time(8,30), end_time=time(9,0), status='confirmed'),
    dict(patient=p2, doctor=d1, date=today, start_time=time(9,0), end_time=time(9,30), status='checked_in'),
    dict(patient=p3, doctor=d2, date=today, start_time=time(10,0), end_time=time(10,30), status='pending'),
    dict(patient=p4, doctor=d2, date=today, start_time=time(14,0), end_time=time(14,30), status='confirmed'),
    # Đã xong
    dict(patient=p1, doctor=d2, date=today-timedelta(days=1), start_time=time(9,0), end_time=time(9,30), status='done'),
    dict(patient=p2, doctor=d3, date=today-timedelta(days=3), start_time=time(11,0), end_time=time(11,30), status='done'),
    # Sắp tới
    dict(patient=p3, doctor=d1, date=today+timedelta(days=2), start_time=time(9,0), end_time=time(9,30), status='pending'),
    dict(patient=p4, doctor=d3, date=today+timedelta(days=3), start_time=time(14,0), end_time=time(15,0), status='confirmed'),
]

created_count = 0
for a in appts:
    obj, created = Appointment.objects.get_or_create(
        patient=a['patient'], doctor=a['doctor'],
        date=a['date'], start_time=a['start_time'],
        defaults={**a}
    )
    if created:
        created_count += 1

print(f"  Đã tạo {created_count} lịch hẹn mẫu")

print("\n✅ Hoàn thành! Chạy: python manage.py runserver")
print("\n📋 Tài khoản đăng nhập:")
print("   Admin     : admin / admin123")
print("   Nhân viên : nhanvien / nhanvien123")
print("   Bác sĩ An : bacsi_an / bacsi123")
