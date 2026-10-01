"""Tạo dữ liệu demo cho ClinicMS. Chạy bằng: python seed_data.py"""

import os
from datetime import date, time, timedelta

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'clinicms.settings')
django.setup()

from django.contrib.auth.models import User
from django.utils import timezone

from appointments.models import Appointment, MedicalRecord
from billing.models import Invoice, Medicine, Prescription, Service
from doctors.models import Doctor, DoctorSchedule
from patients.models import Patient


def make_user(username, password, first_name, last_name, role):
    user, _ = User.objects.get_or_create(username=username)
    user.first_name = first_name
    user.last_name = last_name
    user.is_active = True
    user.set_password(password)
    user.save()
    user.profile.role = role
    user.profile.save(update_fields=['role'])
    return user


def next_workday(day):
    day += timedelta(days=1)
    while day.weekday() > 4:
        day += timedelta(days=1)
    return day


def previous_workday(day):
    day -= timedelta(days=1)
    while day.weekday() > 4:
        day -= timedelta(days=1)
    return day


print('Creating demo data...')

make_user('admin', 'admin123', 'Admin', 'ClinicMS', 'admin')
make_user('nhanvien', 'nhanvien123', 'Nhan vien', 'Le tan', 'staff')
doctor_an_user = make_user('bacsi_an', 'bacsi123', 'Van An', 'Nguyen', 'doctor')
doctor_binh_user = make_user('bacsi_binh', 'bacsi123', 'Thi Binh', 'Tran', 'doctor')

doctor_an, _ = Doctor.objects.update_or_create(
    full_name='Nguyễn Văn An',
    defaults={
        'user': doctor_an_user,
        'specialty': 'Nội khoa',
        'phone': '0901111111',
        'is_active': True,
    },
)
doctor_binh, _ = Doctor.objects.update_or_create(
    full_name='Trần Thị Bình',
    defaults={
        'user': doctor_binh_user,
        'specialty': 'Nhi khoa',
        'phone': '0902222222',
        'is_active': True,
    },
)

for doctor in [doctor_an, doctor_binh]:
    for weekday in range(5):
        DoctorSchedule.objects.update_or_create(
            doctor=doctor,
            weekday=weekday,
            start_time=time(8),
            end_time=time(17),
            defaults={'is_active': True},
        )

patient_dung, _ = Patient.objects.get_or_create(
    phone='0901234567',
    defaults={
        'full_name': 'Phạm Thị Dung',
        'date_of_birth': date(1985, 3, 15),
        'gender': 'F',
        'address': '123 Nguyễn Huệ, Quận 1, TP.HCM',
    },
)
patient_em, _ = Patient.objects.get_or_create(
    phone='0902345678',
    defaults={
        'full_name': 'Hoàng Văn Em',
        'date_of_birth': date(1990, 7, 22),
        'gender': 'M',
        'address': '456 Lê Lợi, Quận 3, TP.HCM',
    },
)
patient_phuong, _ = Patient.objects.get_or_create(
    phone='0903456789',
    defaults={
        'full_name': 'Vũ Thị Phương',
        'date_of_birth': date(1978, 11, 5),
        'gender': 'F',
        'address': '789 Trần Hưng Đạo, Quận 5, TP.HCM',
    },
)

today = timezone.localdate()
future_date = next_workday(today)
done_date = previous_workday(today)

Appointment.objects.update_or_create(
    patient=patient_dung,
    doctor=doctor_an,
    note='Dữ liệu demo - chờ xác nhận',
    defaults={
        'date': future_date,
        'start_time': time(10),
        'end_time': time(10, 30),
        'status': 'pending',
    },
)
Appointment.objects.update_or_create(
    patient=patient_em,
    doctor=doctor_binh,
    note='Dữ liệu demo - đã xác nhận',
    defaults={
        'date': future_date,
        'start_time': time(11),
        'end_time': time(11, 30),
        'status': 'confirmed',
    },
)
done_appointment, _ = Appointment.objects.update_or_create(
    patient=patient_phuong,
    doctor=doctor_an,
    note='Dữ liệu demo - đã hoàn thành',
    defaults={
        'date': done_date,
        'start_time': time(15),
        'end_time': time(15, 30),
        'status': 'done',
    },
)

record, _ = MedicalRecord.objects.update_or_create(
    appointment=done_appointment,
    defaults={
        'symptoms': 'Đau đầu nhẹ',
        'diagnosis': 'Theo dõi sức khỏe',
        'treatment': 'Nghỉ ngơi và dùng thuốc theo hướng dẫn',
        'notes': 'Hồ sơ demo',
    },
)

medicine, _ = Medicine.objects.get_or_create(
    name='Paracetamol 500mg',
    defaults={'unit_price': '2000', 'unit': 'Viên'},
)
Prescription.objects.update_or_create(
    medical_record=record,
    medicine=medicine,
    defaults={'quantity': 5, 'dosage': 'Ngày 1 viên sau ăn'},
)

general_service, _ = Service.objects.get_or_create(
    name='Khám tổng quát', defaults={'price': '150000'},
)
Service.objects.get_or_create(
    name='Xét nghiệm cơ bản', defaults={'price': '100000'},
)

invoice, _ = Invoice.objects.get_or_create(medical_record=record)
if invoice.status == 'Pending':
    invoice.services.set([general_service])
    invoice.recalculate()

print('Demo data is ready.')
print('Admin: admin / admin123')
print('Staff: nhanvien / nhanvien123')
print('Doctors: bacsi_an / bacsi123, bacsi_binh / bacsi123')
