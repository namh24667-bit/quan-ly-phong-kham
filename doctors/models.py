from django.db import models
from django.contrib.auth.models import User


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
