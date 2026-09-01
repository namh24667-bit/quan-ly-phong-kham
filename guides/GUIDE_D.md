# 📘 GUIDE D — Thành viên D: Quản lý Bác sĩ & Dashboard Thống kê

> **Phụ trách:** `doctors/` app (toàn bộ) + `dashboard/` app  
> **Thời gian ước tính:** ~4 giờ

---

## TỔNG QUAN

| Nhiệm vụ | File | Độ khó |
|---|---|---|
| Form bác sĩ | `doctors/forms.py` | ⭐⭐ |
| Views CRUD bác sĩ | `doctors/views.py` | ⭐⭐⭐ |
| URL routing | `doctors/urls.py` | ⭐ |
| Templates bác sĩ | `templates/doctors/` (4 file) | ⭐⭐⭐ |
| Dashboard thống kê | `dashboard/views.py` | ⭐⭐⭐ |
| Dashboard template | `templates/dashboard/index.html` | ⭐⭐ |

### File cần tạo:
```
doctors/
├── forms.py
├── views.py
├── urls.py
└── templates/doctors/
    ├── doctor_list.html
    ├── doctor_form.html
    ├── doctor_detail.html
    └── doctor_confirm_delete.html

dashboard/
├── views.py
├── urls.py
└── templates/dashboard/
    └── index.html
```

### Phụ thuộc:
| Từ ai | Cung cấp gì | Cách dùng |
|---|---|---|
| Thành viên A | `accounts.decorators.role_required` | Import trong views.py |
| GUIDE_CHUNG | Model `Doctor` và `Appointment` đã có | Dùng trực tiếp |

---

## PHẦN 1: doctors App

### 1.1. doctors/forms.py

```python
# doctors/forms.py
from django import forms
from .models import Doctor


class DoctorForm(forms.ModelForm):
    """Form tạo/sửa bác sĩ."""

    class Meta:
        model = Doctor
        # user không bắt buộc (blank=True trong model)
        fields = ['full_name', 'specialty', 'phone', 'is_active']
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'BS. Nguyễn Văn A',
            }),
            'specialty': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nội khoa, Nhi khoa, Tim mạch...',
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '0901234567',
                'type': 'tel',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }
        labels = {
            'full_name': 'Họ và tên bác sĩ',
            'specialty': 'Chuyên khoa',
            'phone': 'Số điện thoại',
            'is_active': 'Đang hoạt động',
        }
        error_messages = {
            'full_name': {'required': 'Vui lòng nhập tên bác sĩ.'},
            'specialty': {'required': 'Vui lòng nhập chuyên khoa.'},
        }

    def clean_phone(self):
        """Validate số điện thoại (tương tự PatientForm)."""
        phone = self.cleaned_data.get('phone', '').strip()
        if phone:   # phone không bắt buộc với bác sĩ
            if not phone.isdigit():
                raise forms.ValidationError('Số điện thoại chỉ được chứa chữ số.')
            if not (9 <= len(phone) <= 11):
                raise forms.ValidationError(
                    f'Số điện thoại phải từ 9–11 chữ số. Bạn nhập {len(phone)} chữ số.'
                )
        return phone
```

---

### 1.2. doctors/views.py

```python
# doctors/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from accounts.decorators import role_required   # Từ Thành viên A
from .models import Doctor
from .forms import DoctorForm


@login_required
@role_required('admin', 'staff')
def doctor_list(request):
    """Danh sách tất cả bác sĩ, có tìm kiếm theo tên/chuyên khoa."""
    query = request.GET.get('q', '').strip()

    doctors = Doctor.objects.all()

    if query:
        doctors = doctors.filter(
            Q(full_name__icontains=query) |
            Q(specialty__icontains=query)
        )

    # Annotate: đếm số lịch hẹn của mỗi bác sĩ
    # appointment_set là reverse FK từ Appointment -> Doctor
    doctors = doctors.annotate(
        appointment_count=Count('appointment')
    ).order_by('full_name')

    return render(request, 'doctors/doctor_list.html', {
        'doctors': doctors,
        'query': query,
        'total': doctors.count(),
    })


@login_required
@role_required('admin')   # Chỉ admin tạo bác sĩ mới
def doctor_create(request):
    """Thêm bác sĩ mới."""
    if request.method == 'POST':
        form = DoctorForm(request.POST)
        if form.is_valid():
            doctor = form.save()
            messages.success(request, f'Đã thêm bác sĩ {doctor.full_name} thành công!')
            return redirect('doctors:list')
    else:
        form = DoctorForm()

    return render(request, 'doctors/doctor_form.html', {
        'form': form,
        'title': 'Thêm Bác Sĩ Mới',
        'button_text': 'Thêm bác sĩ',
        'is_update': False,
    })


@login_required
@role_required('admin')
def doctor_update(request, pk):
    """Sửa thông tin bác sĩ."""
    doctor = get_object_or_404(Doctor, pk=pk)

    if request.method == 'POST':
        form = DoctorForm(request.POST, instance=doctor)
        if form.is_valid():
            form.save()
            messages.success(request, f'Đã cập nhật thông tin BS. {doctor.full_name}!')
            return redirect('doctors:detail', pk=doctor.pk)
    else:
        form = DoctorForm(instance=doctor)

    return render(request, 'doctors/doctor_form.html', {
        'form': form,
        'doctor': doctor,
        'title': f'Sửa: {doctor.full_name}',
        'button_text': 'Lưu thay đổi',
        'is_update': True,
    })


@login_required
@role_required('admin')
def doctor_delete(request, pk):
    """Xóa bác sĩ — hiện cảnh báo nếu còn lịch hẹn."""
    doctor = get_object_or_404(Doctor, pk=pk)

    if request.method == 'POST':
        # Kiểm tra còn lịch hẹn active không
        active_appts = doctor.appointment_set.filter(
            status__in=['pending', 'confirmed', 'checked_in']
        ).count()

        if active_appts > 0:
            messages.error(
                request,
                f'Không thể xóa! BS. {doctor.full_name} còn {active_appts} lịch hẹn đang hoạt động.'
            )
            return redirect('doctors:detail', pk=pk)

        name = doctor.full_name
        doctor.delete()
        messages.success(request, f'Đã xóa bác sĩ {name}.')
        return redirect('doctors:list')

    # GET: đếm lịch hẹn để hiển thị cảnh báo
    active_count = doctor.appointment_set.filter(
        status__in=['pending', 'confirmed', 'checked_in']
    ).count()

    return render(request, 'doctors/doctor_confirm_delete.html', {
        'doctor': doctor,
        'active_count': active_count,
    })


@login_required
@role_required('admin', 'staff', 'doctor')
def doctor_detail(request, pk):
    """Chi tiết bác sĩ + danh sách lịch hẹn sắp tới."""
    doctor = get_object_or_404(Doctor, pk=pk)

    # Lấy lịch hẹn của bác sĩ (sắp xếp theo ngày mới nhất)
    try:
        from appointments.models import Appointment
        appointments = Appointment.objects.filter(
            doctor=doctor
        ).select_related('patient').order_by('-date', '-start_time')[:20]  # 20 lịch gần nhất
    except Exception:
        appointments = []

    return render(request, 'doctors/doctor_detail.html', {
        'doctor': doctor,
        'appointments': appointments,
    })
```

> **Tại sao dùng `annotate(appointment_count=Count('appointment'))`?**  
> Thay vì loop qua từng bác sĩ và đếm thủ công (N+1 queries), `annotate()` đếm ngay trong câu SQL. 50 bác sĩ = 1 query thay vì 51 queries.

---

### 1.3. doctors/urls.py

```python
# doctors/urls.py
from django.urls import path
from . import views

app_name = 'doctors'

urlpatterns = [
    path('', views.doctor_list, name='list'),                    # /doctors/
    path('create/', views.doctor_create, name='create'),         # /doctors/create/
    path('<int:pk>/', views.doctor_detail, name='detail'),       # /doctors/5/
    path('<int:pk>/update/', views.doctor_update, name='update'),# /doctors/5/update/
    path('<int:pk>/delete/', views.doctor_delete, name='delete'),# /doctors/5/delete/
]
```

Đảm bảo `clinicms/urls.py` đã có:
```python
path('doctors/', include('doctors.urls')),
```

---

## PHẦN 2: Templates Bác sĩ

### 2.1. templates/doctors/doctor_list.html

```html
{% extends 'base.html' %}

{% block title %}Danh Sách Bác Sĩ{% endblock %}
{% block page_title %}Danh Sách Bác Sĩ{% endblock %}

{% block content %}
<div class="d-flex justify-content-between align-items-center mb-3">
    <p class="text-muted mb-0">
        {% if query %}Tìm thấy {{ total }} kết quả{% else %}Tổng: {{ total }} bác sĩ{% endif %}
    </p>
    <a href="{% url 'doctors:create' %}" class="btn btn-primary">
        <i class="bi bi-plus-circle me-1"></i>Thêm Bác Sĩ
    </a>
</div>

<!-- Tìm kiếm -->
<div class="card mb-3 shadow-sm">
    <div class="card-body py-2">
        <form method="GET" action="{% url 'doctors:list' %}">
            <div class="input-group">
                <input type="text" name="q" class="form-control"
                       placeholder="Tìm theo tên hoặc chuyên khoa..."
                       value="{{ query }}">
                <button type="submit" class="btn btn-outline-primary">
                    <i class="bi bi-search"></i>
                </button>
                {% if query %}
                <a href="{% url 'doctors:list' %}" class="btn btn-outline-secondary">
                    <i class="bi bi-x-lg"></i>
                </a>
                {% endif %}
            </div>
        </form>
    </div>
</div>

<!-- Bảng danh sách -->
<div class="card shadow-sm">
    <div class="card-body p-0">
        <div class="table-responsive">
            <table class="table table-hover table-striped mb-0">
                <thead class="table-dark">
                    <tr>
                        <th>#</th>
                        <th>Họ tên</th>
                        <th>Chuyên khoa</th>
                        <th>SĐT</th>
                        <th>Trạng thái</th>
                        <th class="text-center">Lịch hẹn</th>
                        <th class="text-center">Hành động</th>
                    </tr>
                </thead>
                <tbody>
                    {% for doctor in doctors %}
                    <tr>
                        <td class="text-muted">{{ forloop.counter }}</td>
                        <td>
                            <a href="{% url 'doctors:detail' pk=doctor.pk %}"
                               class="text-decoration-none fw-semibold">
                                BS. {{ doctor.full_name }}
                            </a>
                        </td>
                        <td>
                            <span class="badge bg-info text-dark">{{ doctor.specialty }}</span>
                        </td>
                        <td>{{ doctor.phone|default:"—" }}</td>
                        <td>
                            {% if doctor.is_active %}
                            <span class="badge bg-success">Đang làm việc</span>
                            {% else %}
                            <span class="badge bg-secondary">Nghỉ</span>
                            {% endif %}
                        </td>
                        <td class="text-center">
                            <span class="badge bg-primary rounded-pill">
                                {{ doctor.appointment_count }}
                            </span>
                        </td>
                        <td class="text-center">
                            <a href="{% url 'doctors:detail' pk=doctor.pk %}"
                               class="btn btn-sm btn-outline-info" title="Xem">
                                <i class="bi bi-eye"></i>
                            </a>
                            <a href="{% url 'doctors:update' pk=doctor.pk %}"
                               class="btn btn-sm btn-outline-warning" title="Sửa">
                                <i class="bi bi-pencil"></i>
                            </a>
                            <a href="{% url 'doctors:delete' pk=doctor.pk %}"
                               class="btn btn-sm btn-outline-danger" title="Xóa">
                                <i class="bi bi-trash"></i>
                            </a>
                        </td>
                    </tr>
                    {% empty %}
                    <tr>
                        <td colspan="7" class="text-center py-5 text-muted">
                            <i class="bi bi-person-x fs-1 d-block mb-2"></i>
                            Chưa có bác sĩ nào.
                            <a href="{% url 'doctors:create' %}">Thêm ngay</a>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</div>
{% endblock %}
```

---

### 2.2. templates/doctors/doctor_form.html

```html
{% extends 'base.html' %}

{% block title %}{{ title }}{% endblock %}
{% block page_title %}{{ title }}{% endblock %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-md-7">
        <div class="card shadow">
            <div class="card-header bg-success text-white">
                <h5 class="mb-0">
                    <i class="bi bi-person-badge me-2"></i>{{ title }}
                </h5>
            </div>
            <div class="card-body p-4">
                <form method="post" action="" novalidate>
                    {% csrf_token %}

                    {% if form.non_field_errors %}
                    <div class="alert alert-danger">
                        {% for e in form.non_field_errors %}<p class="mb-0">{{ e }}</p>{% endfor %}
                    </div>
                    {% endif %}

                    <div class="mb-3">
                        <label class="form-label fw-semibold">Họ và tên <span class="text-danger">*</span></label>
                        {{ form.full_name }}
                        {% if form.full_name.errors %}<div class="invalid-feedback d-block">{{ form.full_name.errors.0 }}</div>{% endif %}
                    </div>

                    <div class="mb-3">
                        <label class="form-label fw-semibold">Chuyên khoa <span class="text-danger">*</span></label>
                        {{ form.specialty }}
                        {% if form.specialty.errors %}<div class="invalid-feedback d-block">{{ form.specialty.errors.0 }}</div>{% endif %}
                    </div>

                    <div class="mb-3">
                        <label class="form-label fw-semibold">Số điện thoại</label>
                        {{ form.phone }}
                        {% if form.phone.errors %}<div class="invalid-feedback d-block">{{ form.phone.errors.0 }}</div>{% endif %}
                    </div>

                    <div class="mb-4">
                        <div class="form-check">
                            {{ form.is_active }}
                            <label class="form-check-label fw-semibold">Đang hoạt động</label>
                        </div>
                        <div class="form-text">Bỏ tick nếu bác sĩ tạm nghỉ (sẽ không hiện khi đặt lịch).</div>
                    </div>

                    <div class="d-flex gap-2">
                        <button type="submit" class="btn btn-success">
                            <i class="bi bi-save me-1"></i>{{ button_text }}
                        </button>
                        {% if is_update %}
                        <a href="{% url 'doctors:detail' pk=doctor.pk %}" class="btn btn-outline-secondary">Hủy</a>
                        {% else %}
                        <a href="{% url 'doctors:list' %}" class="btn btn-outline-secondary">Hủy</a>
                        {% endif %}
                    </div>
                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

---

### 2.3. templates/doctors/doctor_detail.html

```html
{% extends 'base.html' %}

{% block title %}{{ doctor.full_name }}{% endblock %}
{% block page_title %}Chi Tiết Bác Sĩ{% endblock %}

{% block content %}
<div class="mb-3">
    <a href="{% url 'doctors:list' %}" class="btn btn-outline-secondary btn-sm">
        <i class="bi bi-arrow-left"></i> Quay lại
    </a>
</div>

<div class="row g-4">
    <!-- Thông tin bác sĩ -->
    <div class="col-md-4">
        <div class="card shadow h-100">
            <div class="card-header bg-success text-white">
                <h5 class="mb-0"><i class="bi bi-person-badge me-2"></i>Thông Tin</h5>
            </div>
            <div class="card-body">
                <div class="text-center mb-3">
                    <div class="rounded-circle bg-success d-inline-flex align-items-center justify-content-center text-white"
                         style="width:80px;height:80px;font-size:2rem;">
                        <i class="bi bi-person-badge"></i>
                    </div>
                    <h5 class="mt-2 mb-0">BS. {{ doctor.full_name }}</h5>
                    <p class="text-muted">{{ doctor.specialty }}</p>
                </div>
                <table class="table table-borderless">
                    <tr>
                        <th class="text-muted" style="width:40%">SĐT:</th>
                        <td>{{ doctor.phone|default:"—" }}</td>
                    </tr>
                    <tr>
                        <th class="text-muted">Trạng thái:</th>
                        <td>
                            {% if doctor.is_active %}
                            <span class="badge bg-success">Đang làm việc</span>
                            {% else %}
                            <span class="badge bg-secondary">Tạm nghỉ</span>
                            {% endif %}
                        </td>
                    </tr>
                </table>
            </div>
            <div class="card-footer bg-transparent">
                <div class="d-flex gap-2">
                    <a href="{% url 'doctors:update' pk=doctor.pk %}" class="btn btn-warning btn-sm">
                        <i class="bi bi-pencil me-1"></i>Sửa
                    </a>
                    <a href="{% url 'doctors:delete' pk=doctor.pk %}" class="btn btn-danger btn-sm">
                        <i class="bi bi-trash me-1"></i>Xóa
                    </a>
                </div>
            </div>
        </div>
    </div>

    <!-- Lịch hẹn -->
    <div class="col-md-8">
        <div class="card shadow h-100">
            <div class="card-header bg-primary text-white">
                <h5 class="mb-0"><i class="bi bi-calendar3 me-2"></i>Lịch Hẹn Gần Đây</h5>
            </div>
            <div class="card-body p-0">
                {% if appointments %}
                <table class="table table-hover mb-0">
                    <thead class="table-light">
                        <tr><th>Ngày</th><th>Giờ</th><th>Bệnh nhân</th><th>Trạng thái</th></tr>
                    </thead>
                    <tbody>
                        {% for appt in appointments %}
                        <tr>
                            <td>{{ appt.date|date:"d/m/Y" }}</td>
                            <td>{{ appt.start_time|time:"H:i" }}</td>
                            <td>{{ appt.patient.full_name }}</td>
                            <td>
                                <span class="badge bg-{{ appt.get_status_badge_class }}">
                                    {{ appt.get_status_display }}
                                </span>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                {% else %}
                <div class="text-center py-4">
                    <i class="bi bi-calendar-x fs-1 text-muted"></i>
                    <p class="text-muted mt-2">Chưa có lịch hẹn nào.</p>
                </div>
                {% endif %}
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

---

### 2.4. templates/doctors/doctor_confirm_delete.html

```html
{% extends 'base.html' %}

{% block title %}Xác Nhận Xóa Bác Sĩ{% endblock %}
{% block page_title %}Xác Nhận Xóa{% endblock %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-md-6">
        <div class="card shadow border-danger">
            <div class="card-header bg-danger text-white">
                <h4 class="mb-0"><i class="bi bi-exclamation-triangle-fill me-2"></i>Xác Nhận Xóa</h4>
            </div>
            <div class="card-body text-center py-4">
                <h5>Xóa bác sĩ: <strong>{{ doctor.full_name }}</strong>?</h5>
                <p class="text-muted">Chuyên khoa: {{ doctor.specialty }}</p>

                {% if active_count > 0 %}
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle-fill me-1"></i>
                    <strong>Không thể xóa!</strong><br>
                    Bác sĩ này còn <strong>{{ active_count }}</strong> lịch hẹn đang hoạt động.
                    Hãy hủy tất cả lịch hẹn trước khi xóa.
                </div>
                <a href="{% url 'doctors:detail' pk=doctor.pk %}" class="btn btn-secondary btn-lg">
                    <i class="bi bi-arrow-left me-1"></i>Quay lại
                </a>
                {% else %}
                <div class="alert alert-warning">
                    <strong>Hành động này không thể hoàn tác!</strong>
                </div>
                <div class="d-flex gap-3 justify-content-center">
                    <a href="{% url 'doctors:detail' pk=doctor.pk %}" class="btn btn-secondary btn-lg">
                        <i class="bi bi-x-circle me-1"></i>Hủy
                    </a>
                    <form method="post" action="{% url 'doctors:delete' pk=doctor.pk %}">
                        {% csrf_token %}
                        <button type="submit" class="btn btn-danger btn-lg">
                            <i class="bi bi-trash me-1"></i>Xóa vĩnh viễn
                        </button>
                    </form>
                </div>
                {% endif %}
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

---

## PHẦN 3: dashboard App

### 3.1. dashboard/views.py

```python
# dashboard/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone


@login_required
def dashboard_index(request):
    """
    Trang chủ dashboard — hiển thị thống kê tổng quan.
    Dùng import bên trong hàm để tránh circular import.
    """
    from patients.models import Patient
    from doctors.models import Doctor
    from appointments.models import Appointment

    today = timezone.localdate()

    # === THỐNG KÊ TỔNG QUAN ===
    stats = {
        # Tổng số bệnh nhân trong hệ thống
        'total_patients': Patient.objects.count(),

        # Bác sĩ đang hoạt động
        'active_doctors': Doctor.objects.filter(is_active=True).count(),

        # Lịch hẹn hôm nay
        'appointments_today': Appointment.objects.filter(date=today).count(),

        # Lịch hẹn chờ xác nhận
        'pending_count': Appointment.objects.filter(status='pending').count(),

        # Lịch hẹn đã xác nhận hôm nay (cần check-in)
        'confirmed_today': Appointment.objects.filter(
            date=today, status='confirmed'
        ).count(),

        # Tổng lịch hẹn đã hoàn thành
        'done_total': Appointment.objects.filter(status='done').count(),
    }

    # === LỊCH HẸN HÔM NAY ===
    # select_related() để tránh N+1 queries
    appointments_today = Appointment.objects.filter(
        date=today
    ).select_related('patient', 'doctor').order_by('start_time')

    # === LỊCH HẸN SẮP TỚI (7 ngày tới, không tính hôm nay) ===
    from datetime import timedelta
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
```

---

### 3.2. dashboard/urls.py

```python
# dashboard/urls.py
from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_index, name='index'),   # /dashboard/ hoặc /
]
```

Đảm bảo `clinicms/urls.py` đã có:
```python
path('dashboard/', include('dashboard.urls')),
path('', include('dashboard.urls')),   # Trang chủ -> dashboard
```

---

### 3.3. templates/dashboard/index.html

```html
{% extends 'base.html' %}

{% block title %}Dashboard – ClinicMS{% endblock %}
{% block page_title %}Dashboard Tổng Quan{% endblock %}

{% block content %}

<!-- ===== HÀNG THỐNG KÊ TỔNG QUAN ===== -->
<div class="row g-3 mb-4">

    <!-- Tổng bệnh nhân -->
    <div class="col-md-6 col-xl-3">
        <div class="card shadow-sm border-0 text-white" style="background: linear-gradient(135deg, #0d6efd, #0a58ca);">
            <div class="card-body d-flex align-items-center">
                <div class="flex-grow-1">
                    <p class="card-text mb-1 opacity-75">Tổng Bệnh Nhân</p>
                    <h2 class="fw-bold mb-0">{{ stats.total_patients }}</h2>
                </div>
                <i class="bi bi-people-fill fs-1 opacity-50"></i>
            </div>
            <div class="card-footer bg-transparent border-0 pt-0 pb-2">
                <a href="{% url 'patients:list' %}" class="text-white-50 small text-decoration-none">
                    Xem danh sách <i class="bi bi-arrow-right"></i>
                </a>
            </div>
        </div>
    </div>

    <!-- Bác sĩ hoạt động -->
    <div class="col-md-6 col-xl-3">
        <div class="card shadow-sm border-0 text-white" style="background: linear-gradient(135deg, #198754, #146c43);">
            <div class="card-body d-flex align-items-center">
                <div class="flex-grow-1">
                    <p class="card-text mb-1 opacity-75">Bác Sĩ Hoạt Động</p>
                    <h2 class="fw-bold mb-0">{{ stats.active_doctors }}</h2>
                </div>
                <i class="bi bi-person-badge-fill fs-1 opacity-50"></i>
            </div>
            <div class="card-footer bg-transparent border-0 pt-0 pb-2">
                <a href="{% url 'doctors:list' %}" class="text-white-50 small text-decoration-none">
                    Xem danh sách <i class="bi bi-arrow-right"></i>
                </a>
            </div>
        </div>
    </div>

    <!-- Lịch hẹn hôm nay -->
    <div class="col-md-6 col-xl-3">
        <div class="card shadow-sm border-0 text-white" style="background: linear-gradient(135deg, #0dcaf0, #0aa2c0);">
            <div class="card-body d-flex align-items-center">
                <div class="flex-grow-1">
                    <p class="card-text mb-1 opacity-75">Lịch Hẹn Hôm Nay</p>
                    <h2 class="fw-bold mb-0">{{ stats.appointments_today }}</h2>
                </div>
                <i class="bi bi-calendar-check-fill fs-1 opacity-50"></i>
            </div>
            <div class="card-footer bg-transparent border-0 pt-0 pb-2">
                <a href="{% url 'appointments:list' %}?date={{ today|date:'Y-m-d' }}"
                   class="text-white-50 small text-decoration-none">
                    Xem hôm nay <i class="bi bi-arrow-right"></i>
                </a>
            </div>
        </div>
    </div>

    <!-- Chờ xác nhận -->
    <div class="col-md-6 col-xl-3">
        <div class="card shadow-sm border-0 text-dark" style="background: linear-gradient(135deg, #ffc107, #d39e00);">
            <div class="card-body d-flex align-items-center">
                <div class="flex-grow-1">
                    <p class="card-text mb-1 opacity-75">Chờ Xác Nhận</p>
                    <h2 class="fw-bold mb-0">{{ stats.pending_count }}</h2>
                </div>
                <i class="bi bi-hourglass-split fs-1 opacity-50"></i>
            </div>
            <div class="card-footer bg-transparent border-0 pt-0 pb-2">
                <a href="{% url 'appointments:list' %}?status=pending"
                   class="text-dark-50 small text-decoration-none opacity-75">
                    Xem và xác nhận <i class="bi bi-arrow-right"></i>
                </a>
            </div>
        </div>
    </div>

</div>

<!-- ===== NỘI DUNG CHÍNH ===== -->
<div class="row g-4">

    <!-- Lịch hẹn hôm nay -->
    <div class="col-lg-7">
        <div class="card shadow-sm h-100">
            <div class="card-header d-flex justify-content-between align-items-center">
                <h5 class="mb-0">
                    <i class="bi bi-calendar-day me-2 text-primary"></i>
                    Lịch Hẹn Hôm Nay
                    <small class="text-muted fs-6">({{ today|date:"d/m/Y" }})</small>
                </h5>
                <a href="{% url 'appointments:create' %}" class="btn btn-sm btn-primary">
                    <i class="bi bi-plus"></i> Tạo mới
                </a>
            </div>
            <div class="card-body p-0">
                {% if appointments_today %}
                <div class="table-responsive">
                    <table class="table table-hover mb-0">
                        <thead class="table-light">
                            <tr>
                                <th>Giờ</th>
                                <th>Bệnh nhân</th>
                                <th>Bác sĩ</th>
                                <th>Trạng thái</th>
                                <th></th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for appt in appointments_today %}
                            <tr>
                                <td class="fw-semibold">{{ appt.start_time|time:"H:i" }}</td>
                                <td>{{ appt.patient.full_name }}</td>
                                <td>BS. {{ appt.doctor.full_name }}</td>
                                <td>
                                    <span class="badge bg-{{ appt.get_status_badge_class }}">
                                        {{ appt.get_status_display }}
                                    </span>
                                </td>
                                <td>
                                    <a href="{% url 'appointments:detail' appt.pk %}"
                                       class="btn btn-sm btn-outline-primary">
                                        <i class="bi bi-eye"></i>
                                    </a>
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
                {% else %}
                <div class="text-center py-4 text-muted">
                    <i class="bi bi-calendar-x fs-1 d-block mb-2"></i>
                    Không có lịch hẹn nào hôm nay.
                </div>
                {% endif %}
            </div>
        </div>
    </div>

    <!-- Lịch sắp tới -->
    <div class="col-lg-5">
        <div class="card shadow-sm h-100">
            <div class="card-header">
                <h5 class="mb-0">
                    <i class="bi bi-calendar-week me-2 text-success"></i>
                    Sắp Tới (7 ngày)
                </h5>
            </div>
            <div class="card-body p-0">
                {% if upcoming %}
                <ul class="list-group list-group-flush">
                    {% for appt in upcoming %}
                    <li class="list-group-item">
                        <div class="d-flex justify-content-between align-items-start">
                            <div>
                                <strong>{{ appt.patient.full_name }}</strong>
                                <br>
                                <small class="text-muted">
                                    <i class="bi bi-calendar3 me-1"></i>{{ appt.date|date:"d/m" }}
                                    <i class="bi bi-clock ms-2 me-1"></i>{{ appt.start_time|time:"H:i" }}
                                    — BS. {{ appt.doctor.full_name }}
                                </small>
                            </div>
                            <span class="badge bg-{{ appt.get_status_badge_class }}">
                                {{ appt.get_status_display }}
                            </span>
                        </div>
                    </li>
                    {% endfor %}
                </ul>
                {% else %}
                <div class="text-center py-4 text-muted">
                    <i class="bi bi-calendar-check fs-1 d-block mb-2"></i>
                    Không có lịch hẹn sắp tới.
                </div>
                {% endif %}
            </div>
            {% if upcoming %}
            <div class="card-footer">
                <a href="{% url 'appointments:list' %}" class="btn btn-outline-success btn-sm w-100">
                    Xem tất cả lịch hẹn <i class="bi bi-arrow-right"></i>
                </a>
            </div>
            {% endif %}
        </div>
    </div>

</div>
{% endblock %}
```

---

## PHẦN 4: Test Nhanh

### Tạo dữ liệu mẫu (chạy trong Django shell)

```powershell
python manage.py shell
```
```python
from doctors.models import Doctor
from patients.models import Patient
from appointments.models import Appointment
from datetime import date, time, timedelta

# Tạo bác sĩ
d1 = Doctor.objects.create(full_name='Nguyễn Văn An', specialty='Nội khoa', phone='0901111111')
d2 = Doctor.objects.create(full_name='Trần Thị Bình', specialty='Nhi khoa', phone='0902222222')

# Tạo bệnh nhân
p1 = Patient.objects.create(full_name='Lê Văn Cường', phone='0903333333', gender='M', date_of_birth=date(1985, 5, 15))
p2 = Patient.objects.create(full_name='Phạm Thị Dung', phone='0904444444', gender='F', date_of_birth=date(1990, 3, 20))

# Tạo lịch hẹn
today = date.today()
Appointment.objects.create(patient=p1, doctor=d1, date=today,
                           start_time=time(9,0), end_time=time(9,30), status='confirmed')
Appointment.objects.create(patient=p2, doctor=d1, date=today,
                           start_time=time(10,0), end_time=time(10,30), status='pending')
Appointment.objects.create(patient=p1, doctor=d2, date=today+timedelta(days=2),
                           start_time=time(14,0), end_time=time(14,30), status='pending')

print("Tạo dữ liệu mẫu thành công!")
exit()
```

### Checklist test:

| # | Thao tác | Kết quả mong đợi |
|---|---|---|
| 1 | Vào `/dashboard/` | Thấy 4 ô thống kê + bảng lịch hôm nay |
| 2 | Thêm bác sĩ mới | Lưu thành công, về danh sách |
| 3 | Tìm bác sĩ theo chuyên khoa | Hiện đúng kết quả |
| 4 | Xem chi tiết bác sĩ | Thấy thông tin + lịch hẹn |
| 5 | Xóa bác sĩ có lịch active | Hiện lỗi "Không thể xóa!" |
| 6 | Xóa bác sĩ không có lịch | Xóa thành công |

---

## PHẦN 5: Câu hỏi Giảng viên có thể Hỏi

**Q1: `annotate(appointment_count=Count('appointment'))` làm gì?**
> Đếm số lịch hẹn của mỗi bác sĩ ngay trong câu SQL. Thay vì loop từng bác sĩ và đếm thủ công (N+1 queries), annotate dùng SQL `COUNT()` — 50 bác sĩ = 1 query thay vì 51.

**Q2: Tại sao import model trong hàm view thay vì ở đầu file?**
> Tránh **circular import**: `dashboard/views.py` import từ `patients`, `doctors`, `appointments`. Nếu ở đầu file và các app đó cũng import từ dashboard, Python sẽ bị vòng lặp import. Import bên trong hàm giải quyết vấn đề này.

**Q3: `select_related()` trong dashboard_index dùng để làm gì?**
> Tối ưu database: lấy dữ liệu liên quan (patient, doctor) trong 1 câu SQL JOIN thay vì nhiều câu. 10 lịch hẹn = 1 query thay vì 21 queries (1 + 10 cho patient + 10 cho doctor).

**Q4: Giải thích tại sao xóa bác sĩ phải kiểm tra lịch hẹn active trước.**
> Nếu xóa bác sĩ còn lịch pending/confirmed/checked_in, bệnh nhân đó mất lịch khám mà không được thông báo. Kiểm tra trước và yêu cầu hủy lịch trước khi xóa bảo vệ tính toàn vẹn dữ liệu.

**Q5: `date__gt=today` và `date__lte=today + timedelta(days=7)` có nghĩa gì?**
> `__gt` = greater than (lớn hơn, tức là sau hôm nay).  
> `__lte` = less than or equal (nhỏ hơn hoặc bằng, tức là không vượt quá 7 ngày tới).  
> Kết hợp: lọc lịch hẹn trong khoảng từ ngày mai đến 7 ngày tới.

---

## PHẦN 6: Lỗi Thường Gặp

| Lỗi | Nguyên nhân | Cách sửa |
|---|---|---|
| Dashboard hiện 0 ở tất cả thống kê | Chưa có dữ liệu mẫu | Chạy script tạo dữ liệu trong shell |
| `ImportError: cannot import 'Patient'` | Thứ tự migrate sai | `python manage.py makemigrations && python manage.py migrate` |
| `circular import` khi mở dashboard | Import model ở đầu file | Chuyển import vào bên trong hàm view |
| `FieldError: Cannot resolve 'appointment'` | Tên reverse FK sai | Kiểm tra `related_name` trong Appointment model |
| Bảng lịch hôm nay trống dù có dữ liệu | Date filter sai timezone | Dùng `timezone.localdate()` thay vì `date.today()` |
| Không tìm thấy template dashboard | Chưa tạo thư mục `templates/dashboard/` | Tạo đúng cấu trúc thư mục |

---

## ✅ Checklist Hoàn thành

- [ ] `doctors/forms.py` – DoctorForm với validation phone
- [ ] `doctors/views.py` – 5 views (list, create, update, delete, detail)
- [ ] `doctors/urls.py` – 5 URL patterns với namespace `doctors`
- [ ] `templates/doctors/doctor_list.html` – bảng + tìm kiếm + annotate count
- [ ] `templates/doctors/doctor_form.html` – form tạo/sửa
- [ ] `templates/doctors/doctor_detail.html` – chi tiết + lịch hẹn
- [ ] `templates/doctors/doctor_confirm_delete.html` – có cảnh báo lịch active
- [ ] `dashboard/views.py` – 6 thống kê + lịch hôm nay + lịch sắp tới
- [ ] `dashboard/urls.py` – namespace `dashboard`
- [ ] `templates/dashboard/index.html` – 4 stat cards + 2 bảng
- [ ] Test dashboard hiện đúng số liệu ✅
- [ ] Test thêm/sửa/xóa bác sĩ ✅
- [ ] Test chặn xóa bác sĩ có lịch active ✅
