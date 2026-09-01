from django.db import models
from datetime import date


class Patient(models.Model):
    GENDER_CHOICES = [
        ('M', 'Nam'),
        ('F', 'Nữ'),
        ('O', 'Khác'),
    ]
    full_name = models.CharField(max_length=100, verbose_name='Họ và tên')
    date_of_birth = models.DateField(verbose_name='Ngày sinh')
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, verbose_name='Giới tính')
    phone = models.CharField(max_length=15, verbose_name='Số điện thoại')
    address = models.TextField(blank=True, verbose_name='Địa chỉ')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Ngày tạo')

    class Meta:
        verbose_name = 'Bệnh nhân'
        verbose_name_plural = 'Bệnh nhân'
        ordering = ['-created_at']

    def __str__(self):
        return self.full_name

    def get_age(self):
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )
