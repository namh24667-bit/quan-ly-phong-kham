# Generated manually because Django is not installed in this environment.
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('appointments', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Medicine',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150, unique=True, verbose_name='Tên thuốc')),
                ('unit_price', models.DecimalField(decimal_places=2, max_digits=12, verbose_name='Đơn giá')),
                ('unit', models.CharField(max_length=30, verbose_name='Đơn vị')),
            ],
            options={'ordering': ['name'], 'verbose_name': 'Thuốc', 'verbose_name_plural': 'Thuốc'},
        ),
        migrations.CreateModel(
            name='Service',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150, unique=True, verbose_name='Tên dịch vụ')),
                ('price', models.DecimalField(decimal_places=2, max_digits=12, verbose_name='Giá tiền')),
            ],
            options={'ordering': ['name'], 'verbose_name': 'Dịch vụ', 'verbose_name_plural': 'Dịch vụ'},
        ),
        migrations.CreateModel(
            name='Prescription',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField(verbose_name='Số lượng')),
                ('dosage', models.CharField(max_length=255, verbose_name='Liều dùng')),
                ('medical_record', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='prescriptions', to='appointments.medicalrecord', verbose_name='Hồ sơ khám')),
                ('medicine', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='billing.medicine', verbose_name='Thuốc')),
            ],
            options={'verbose_name': 'Đơn thuốc', 'verbose_name_plural': 'Đơn thuốc'},
        ),
        migrations.CreateModel(
            name='Invoice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('medicine_total', models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='Tiền thuốc')),
                ('service_total', models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='Tiền dịch vụ')),
                ('total_amount', models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='Tổng tiền')),
                ('status', models.CharField(choices=[('Pending', 'Chờ thanh toán'), ('Paid', 'Đã thanh toán')], default='Pending', max_length=7, verbose_name='Trạng thái')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Ngày tạo')),
                ('medical_record', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='invoice', to='appointments.medicalrecord', verbose_name='Hồ sơ khám')),
                ('services', models.ManyToManyField(blank=True, related_name='invoices', to='billing.service', verbose_name='Dịch vụ')),
            ],
            options={'ordering': ['-created_at'], 'verbose_name': 'Hóa đơn', 'verbose_name_plural': 'Hóa đơn'},
        ),
    ]
