from django.db import models
from patients.models import Patient
from doctors.models import Doctor


class Appointment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Chờ xác nhận'),
        ('confirmed', 'Đã xác nhận'),
        ('checked_in', 'Đã check-in'),
        ('done', 'Hoàn thành'),
        ('cancelled', 'Đã hủy'),
    ]
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, verbose_name='Bệnh nhân')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, verbose_name='Bác sĩ')
    date = models.DateField(verbose_name='Ngày khám')
    start_time = models.TimeField(verbose_name='Giờ bắt đầu')
    end_time = models.TimeField(verbose_name='Giờ kết thúc')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending',
                              verbose_name='Trạng thái')
    note = models.TextField(blank=True, verbose_name='Ghi chú')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Ngày tạo')

    class Meta:
        verbose_name = 'Lịch hẹn'
        verbose_name_plural = 'Lịch hẹn'
        ordering = ['-date', '-start_time']

    def __str__(self):
        return f"{self.patient} - {self.doctor} - {self.date} {self.start_time}"

    def get_status_badge_class(self):
        return {
            'pending': 'warning',
            'confirmed': 'primary',
            'checked_in': 'info',
            'done': 'success',
            'cancelled': 'danger',
        }.get(self.status, 'secondary')


class MedicalRecord(models.Model):
    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE,
                                       related_name='medical_record')
    symptoms = models.TextField(verbose_name='Triệu chứng')
    diagnosis = models.TextField(verbose_name='Chẩn đoán')
    treatment = models.TextField(verbose_name='Hướng điều trị')
    notes = models.TextField(blank=True, verbose_name='Ghi chú thêm')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Hồ sơ bệnh án'
        verbose_name_plural = 'Hồ sơ bệnh án'

    def __str__(self):
        return f"Bệnh án - {self.appointment}"
