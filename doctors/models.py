from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


class Doctor(models.Model):
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='doctor', verbose_name='Tài khoản')
    full_name = models.CharField(max_length=100, verbose_name='Họ và tên')
    specialty = models.CharField(max_length=100, verbose_name='Chuyên khoa')
    phone = models.CharField(max_length=15, blank=True, verbose_name='Số điện thoại')
    is_active = models.BooleanField(default=True, verbose_name='Đang hoạt động')

    class Meta:
        verbose_name = 'Bác sĩ'
        verbose_name_plural = 'Bác sĩ'
        ordering = ['full_name']

    def __str__(self):
        return f"BS. {self.full_name} ({self.specialty})"


class DoctorSchedule(models.Model):
    WEEKDAY_CHOICES = [
        (0, 'Thứ 2'),
        (1, 'Thứ 3'),
        (2, 'Thứ 4'),
        (3, 'Thứ 5'),
        (4, 'Thứ 6'),
        (5, 'Thứ 7'),
        (6, 'Chủ nhật'),
    ]

    doctor = models.ForeignKey(
        Doctor, on_delete=models.CASCADE, related_name='schedules', verbose_name='Bác sĩ'
    )
    weekday = models.PositiveSmallIntegerField(choices=WEEKDAY_CHOICES, verbose_name='Thứ')
    start_time = models.TimeField(verbose_name='Giờ bắt đầu')
    end_time = models.TimeField(verbose_name='Giờ kết thúc')
    is_active = models.BooleanField(default=True, verbose_name='Đang hoạt động')

    class Meta:
        verbose_name = 'Lịch làm việc'
        verbose_name_plural = 'Lịch làm việc'
        ordering = ['doctor__full_name', 'weekday', 'start_time']

    def __str__(self):
        return (
            f'{self.doctor.full_name} - {self.get_weekday_display()} '
            f'{self.start_time:%H:%M}-{self.end_time:%H:%M}'
        )

    def clean(self):
        super().clean()
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValidationError({'end_time': 'Giờ kết thúc phải sau giờ bắt đầu.'})

        if not self.is_active or not self.doctor_id or not self.start_time or not self.end_time:
            return

        overlaps = DoctorSchedule.objects.filter(
            doctor_id=self.doctor_id,
            weekday=self.weekday,
            is_active=True,
            start_time__lt=self.end_time,
            end_time__gt=self.start_time,
        ).exclude(pk=self.pk)
        if overlaps.exists():
            raise ValidationError('Lịch làm việc bị trùng với ca khác của bác sĩ.')

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
