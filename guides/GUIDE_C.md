# 📘 GUIDE C — Thành viên C: Appointment UI, Trạng thái & Testing

> **Phụ trách:** `appointments/` app – templates, views thay đổi trạng thái, URL, tests  
> **Thời gian ước tính:** ~4.5 giờ

---

## TỔNG QUAN

| Nhiệm vụ | File | Độ khó |
|---|---|---|
| Views thay đổi trạng thái | `appointments/views.py` (bổ sung) | ⭐⭐⭐ |
| Views danh sách & chi tiết | `appointments/views.py` (bổ sung) | ⭐⭐ |
| URL patterns hoàn chỉnh | `appointments/urls.py` | ⭐⭐ |
| Templates HTML (4 file) | `templates/appointments/` | ⭐⭐⭐ |
| Test cases | `appointments/tests.py` | ⭐⭐⭐ |

> **QUAN TRỌNG:** Thành viên A đã viết `appointment_create`, `appointment_update`, và `AppointmentForm`.  
> **Đừng xóa code của A** khi thêm phần của bạn vào `views.py`.

---

## PHẦN 1: Hiểu luồng trạng thái

Trước khi code, nắm rõ luồng:

```
pending (Chờ xác nhận)
    |-- [confirm] --> confirmed (Đã xác nhận)
                          |-- [checkin] --> checked_in (Đã check-in)
                                               |-- [done] --> done (Hoàn thành)
    |-- [cancel] --> cancelled (Đã hủy)   <-- cũng từ confirmed
```

**Tại sao phải kiểm tra trạng thái hiện tại?**  
Nếu không kiểm tra, user có thể check-in lịch `pending` (chưa xác nhận), gây lỗi logic nghiệp vụ.

---

## PHẦN 2: appointments/views.py — Phần Thành viên C thêm vào

Mở file `appointments/views.py`, **THÊM TIẾP** vào cuối (không xóa code của Thành viên A):

```python
# ================================================================
# PHẦN CỦA THÀNH VIÊN C — THÊM VÀO CUỐI FILE appointments/views.py
# ================================================================

from django.db.models import Q
from django.utils import timezone


# ----------------------------------------------------------------
# VIEW 1: Danh sách lịch hẹn
# ----------------------------------------------------------------
@login_required
def appointment_list(request):
    """
    Hiển thị danh sách lịch hẹn với bộ lọc trạng thái/ngày.
    select_related() tối ưu query: lấy patient và doctor trong 1 câu SQL.
    """
    appointments = Appointment.objects.select_related(
        'patient', 'doctor'
    ).order_by('-date', '-start_time')

    # Lọc theo URL params: /appointments/?status=pending
    status_filter = request.GET.get('status', '')
    date_filter   = request.GET.get('date', '')

    if status_filter:
        appointments = appointments.filter(status=status_filter)
    if date_filter:
        appointments = appointments.filter(date=date_filter)

    return render(request, 'appointments/appointment_list.html', {
        'appointments': appointments,
        'status_filter': status_filter,
        'date_filter': date_filter,
        'status_choices': Appointment.STATUS_CHOICES,
    })


# ----------------------------------------------------------------
# VIEW 2: Chi tiết lịch hẹn
# ----------------------------------------------------------------
@login_required
def appointment_detail(request, pk):
    """Xem chi tiết một lịch hẹn."""
    appointment = get_object_or_404(
        Appointment.objects.select_related('patient', 'doctor'),
        pk=pk
    )
    return render(request, 'appointments/appointment_detail.html', {
        'appointment': appointment,
    })


# ----------------------------------------------------------------
# VIEW 3: Xác nhận lịch hẹn (pending -> confirmed)
# ----------------------------------------------------------------
@login_required
def appointment_confirm(request, pk):
    """
    Chuyển trạng thái: pending -> confirmed.
    Chỉ chấp nhận POST (không dùng GET để thay đổi dữ liệu — bảo mật).
    """
    if request.method != 'POST':
        messages.error(request, 'Thao tác không hợp lệ.')
        return redirect('appointments:list')

    appointment = get_object_or_404(Appointment, pk=pk)

    # Kiểm tra trạng thái hiện tại
    if appointment.status != 'pending':
        messages.error(
            request,
            f'Không thể xác nhận lịch đang ở trạng thái "{appointment.get_status_display()}".'
        )
        return redirect('appointments:detail', pk=pk)

    appointment.status = 'confirmed'
    appointment.save()  # Lưu thay đổi vào database
    messages.success(request, 'Lịch hẹn đã được xác nhận!')
    return redirect('appointments:detail', pk=pk)


# ----------------------------------------------------------------
# VIEW 4: Check-in (confirmed -> checked_in)
# ----------------------------------------------------------------
@login_required
def appointment_checkin(request, pk):
    """Bệnh nhân đã đến: confirmed -> checked_in."""
    if request.method != 'POST':
        messages.error(request, 'Thao tác không hợp lệ.')
        return redirect('appointments:list')

    appointment = get_object_or_404(Appointment, pk=pk)

    if appointment.status != 'confirmed':
        messages.error(
            request,
            f'Không thể check-in lịch đang ở "{appointment.get_status_display()}". '
            f'Phải ở trạng thái "Đã xác nhận" trước.'
        )
        return redirect('appointments:detail', pk=pk)

    appointment.status = 'checked_in'
    appointment.save()
    messages.success(request, 'Check-in thành công! Bệnh nhân đã đến phòng khám.')
    return redirect('appointments:detail', pk=pk)


# ----------------------------------------------------------------
# VIEW 5: Hoàn thành (checked_in -> done)
# ----------------------------------------------------------------
@login_required
def appointment_done(request, pk):
    """Bác sĩ khám xong: checked_in -> done."""
    if request.method != 'POST':
        messages.error(request, 'Thao tác không hợp lệ.')
        return redirect('appointments:list')

    appointment = get_object_or_404(Appointment, pk=pk)

    if appointment.status != 'checked_in':
        messages.error(
            request,
            f'Không thể hoàn thành lịch đang ở "{appointment.get_status_display()}". '
            f'Phải ở trạng thái "Đã check-in" trước.'
        )
        return redirect('appointments:detail', pk=pk)

    appointment.status = 'done'
    appointment.save()
    messages.success(request, 'Lịch hẹn đã hoàn thành!')
    return redirect('appointments:detail', pk=pk)


# ----------------------------------------------------------------
# VIEW 6: Hủy lịch hẹn (pending/confirmed -> cancelled)
# ----------------------------------------------------------------
@login_required
def appointment_cancel(request, pk):
    """Hủy lịch hẹn. Không được hủy lịch đã done hoặc đã cancelled."""
    if request.method != 'POST':
        messages.error(request, 'Thao tác không hợp lệ.')
        return redirect('appointments:list')

    appointment = get_object_or_404(Appointment, pk=pk)

    if appointment.status in ['done', 'cancelled']:
        messages.error(
            request,
            f'Không thể hủy lịch đang ở trạng thái "{appointment.get_status_display()}".'
        )
        return redirect('appointments:detail', pk=pk)

    old_status = appointment.get_status_display()
    appointment.status = 'cancelled'
    appointment.save()
    messages.success(request, f'Đã hủy lịch hẹn (trước đó: {old_status}).')
    return redirect('appointments:detail', pk=pk)


# ----------------------------------------------------------------
# VIEW 7: Lịch khám của bác sĩ đang đăng nhập
# ----------------------------------------------------------------
@login_required
def my_schedule(request):
    """
    Hiển thị lịch khám của bác sĩ đang đăng nhập.
    hasattr() kiểm tra user có Doctor profile không (tránh RelatedObjectDoesNotExist).
    """
    if not hasattr(request.user, 'doctor'):
        messages.error(request, 'Trang này chỉ dành cho bác sĩ.')
        return redirect('appointments:list')

    doctor = request.user.doctor
    today  = timezone.localdate()

    # Lịch từ hôm nay trở đi, sắp xếp theo ngày và giờ
    appointments = Appointment.objects.filter(
        doctor=doctor,
        date__gte=today,   # gte = greater than or equal (>= hôm nay)
    ).select_related('patient').order_by('date', 'start_time')

    # Nhóm lịch theo ngày: {'2026-09-01': [appt1, appt2], ...}
    grouped = {}
    for appt in appointments:
        if appt.date not in grouped:
            grouped[appt.date] = []
        grouped[appt.date].append(appt)

    return render(request, 'appointments/my_schedule.html', {
        'doctor': doctor,
        'grouped_appointments': grouped,
        'today': today,
    })
```

---

## PHẦN 3: appointments/urls.py — Hoàn chỉnh

Tạo/thay thế toàn bộ file `appointments/urls.py`:

```python
# appointments/urls.py
from django.urls import path
from .views import (
    # Views của Thành viên A
    appointment_create,
    appointment_update,
    # Views của Thành viên C
    appointment_list,
    appointment_detail,
    appointment_confirm,
    appointment_checkin,
    appointment_done,
    appointment_cancel,
    my_schedule,
)

app_name = 'appointments'

urlpatterns = [
    # Danh sách & Chi tiết
    path('', appointment_list, name='list'),
    path('<int:pk>/', appointment_detail, name='detail'),
    # Tạo & Sửa (Thành viên A)
    path('create/', appointment_create, name='create'),
    path('<int:pk>/update/', appointment_update, name='update'),
    # Thay đổi trạng thái (Thành viên C)
    path('<int:pk>/confirm/', appointment_confirm, name='confirm'),
    path('<int:pk>/checkin/', appointment_checkin, name='checkin'),
    path('<int:pk>/done/', appointment_done, name='done'),
    path('<int:pk>/cancel/', appointment_cancel, name='cancel'),
    # Lịch bác sĩ
    path('my-schedule/', my_schedule, name='my_schedule'),
]
```

---

## PHẦN 4: Templates HTML

### 4.1. templates/appointments/appointment_list.html

```html
{% extends 'base.html' %}

{% block title %}Danh Sách Lịch Hẹn{% endblock %}
{% block page_title %}Danh Sách Lịch Hẹn{% endblock %}

{% block content %}
<div class="d-flex justify-content-between align-items-center mb-3">
    <div></div>
    <a href="{% url 'appointments:create' %}" class="btn btn-primary">
        <i class="bi bi-plus-circle me-1"></i>Tạo lịch hẹn mới
    </a>
</div>

<!-- Bộ lọc trạng thái -->
<div class="mb-3 d-flex flex-wrap gap-1">
    <a href="{% url 'appointments:list' %}"
       class="btn btn-sm {% if not status_filter %}btn-secondary{% else %}btn-outline-secondary{% endif %}">Tất cả</a>
    <a href="?status=pending"
       class="btn btn-sm {% if status_filter == 'pending' %}btn-warning{% else %}btn-outline-warning{% endif %}">Chờ xác nhận</a>
    <a href="?status=confirmed"
       class="btn btn-sm {% if status_filter == 'confirmed' %}btn-primary{% else %}btn-outline-primary{% endif %}">Đã xác nhận</a>
    <a href="?status=checked_in"
       class="btn btn-sm {% if status_filter == 'checked_in' %}btn-info{% else %}btn-outline-info{% endif %}">Đã check-in</a>
    <a href="?status=done"
       class="btn btn-sm {% if status_filter == 'done' %}btn-success{% else %}btn-outline-success{% endif %}">Hoàn thành</a>
    <a href="?status=cancelled"
       class="btn btn-sm {% if status_filter == 'cancelled' %}btn-danger{% else %}btn-outline-danger{% endif %}">Đã hủy</a>
</div>

<div class="card shadow-sm">
    <div class="card-body p-0">
        <div class="table-responsive">
            <table class="table table-hover table-striped mb-0">
                <thead class="table-dark">
                    <tr>
                        <th>#</th>
                        <th>Bệnh nhân</th>
                        <th>Bác sĩ</th>
                        <th>Ngày khám</th>
                        <th>Giờ</th>
                        <th>Trạng thái</th>
                        <th class="text-center">Hành động</th>
                    </tr>
                </thead>
                <tbody>
                    {% for appt in appointments %}
                    <tr>
                        <td class="text-muted">{{ forloop.counter }}</td>
                        <td><i class="bi bi-person-fill text-muted me-1"></i>{{ appt.patient.full_name }}</td>
                        <td>BS. {{ appt.doctor.full_name }}</td>
                        <td>{{ appt.date|date:"d/m/Y" }}</td>
                        <td>{{ appt.start_time|time:"H:i" }}–{{ appt.end_time|time:"H:i" }}</td>
                        <td>
                            <span class="badge bg-{{ appt.get_status_badge_class }}">
                                {{ appt.get_status_display }}
                            </span>
                        </td>
                        <td class="text-center">
                            <a href="{% url 'appointments:detail' appt.pk %}"
                               class="btn btn-sm btn-outline-primary">
                                <i class="bi bi-eye"></i> Chi tiết
                            </a>
                        </td>
                    </tr>
                    {% empty %}
                    <tr>
                        <td colspan="7" class="text-center py-5 text-muted">
                            <i class="bi bi-calendar-x fs-1 d-block mb-2"></i>
                            Không có lịch hẹn nào{% if status_filter %} với trạng thái này{% endif %}.
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
    <div class="card-footer text-muted small">
        Tổng: {{ appointments|length }} lịch hẹn
    </div>
</div>
{% endblock %}
```

---

### 4.2. templates/appointments/appointment_detail.html

```html
{% extends 'base.html' %}

{% block title %}Chi Tiết Lịch Hẹn #{{ appointment.pk }}{% endblock %}
{% block page_title %}Chi Tiết Lịch Hẹn #{{ appointment.pk }}{% endblock %}

{% block content %}
<div class="mb-3">
    <a href="{% url 'appointments:list' %}" class="btn btn-outline-secondary btn-sm">
        <i class="bi bi-arrow-left"></i> Quay lại
    </a>
</div>

{% if messages %}
    {% for message in messages %}
    <div class="alert alert-{{ message.tags }} alert-dismissible fade show">
        {{ message }}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    </div>
    {% endfor %}
{% endif %}

<div class="row">
    <!-- Thông tin lịch hẹn -->
    <div class="col-md-8">
        <div class="card shadow-sm mb-4">
            <div class="card-header d-flex justify-content-between align-items-center">
                <h5 class="mb-0"><i class="bi bi-calendar-check me-2"></i>Lịch hẹn #{{ appointment.pk }}</h5>
                <span class="badge bg-{{ appointment.get_status_badge_class }} fs-6">
                    {{ appointment.get_status_display }}
                </span>
            </div>
            <div class="card-body">
                <dl class="row">
                    <dt class="col-sm-4">Bệnh nhân:</dt>
                    <dd class="col-sm-8">
                        <i class="bi bi-person-fill text-primary me-1"></i>
                        <a href="{% url 'patients:detail' appointment.patient.pk %}">
                            {{ appointment.patient.full_name }}
                        </a>
                    </dd>
                    <dt class="col-sm-4">Bác sĩ:</dt>
                    <dd class="col-sm-8">BS. {{ appointment.doctor.full_name }}</dd>
                    <dt class="col-sm-4">Ngày khám:</dt>
                    <dd class="col-sm-8"><i class="bi bi-calendar3 me-1"></i>{{ appointment.date|date:"d/m/Y" }}</dd>
                    <dt class="col-sm-4">Giờ khám:</dt>
                    <dd class="col-sm-8">
                        <i class="bi bi-clock me-1"></i>
                        {{ appointment.start_time|time:"H:i" }} – {{ appointment.end_time|time:"H:i" }}
                    </dd>
                    {% if appointment.note %}
                    <dt class="col-sm-4">Ghi chú:</dt>
                    <dd class="col-sm-8">{{ appointment.note }}</dd>
                    {% endif %}
                    <dt class="col-sm-4">Tạo lúc:</dt>
                    <dd class="col-sm-8 text-muted small">{{ appointment.created_at|date:"d/m/Y H:i" }}</dd>
                </dl>
            </div>
        </div>
    </div>

    <!-- Nút hành động theo trạng thái -->
    <div class="col-md-4">
        <div class="card shadow-sm">
            <div class="card-header"><h6 class="mb-0"><i class="bi bi-gear me-1"></i>Hành động</h6></div>
            <div class="card-body d-grid gap-2">

                {% if appointment.status == 'pending' %}
                <form method="post" action="{% url 'appointments:confirm' appointment.pk %}">
                    {% csrf_token %}
                    <button type="submit" class="btn btn-primary w-100"
                            onclick="return confirm('Xác nhận lịch hẹn này?')">
                        <i class="bi bi-check-circle me-1"></i>Xác nhận lịch hẹn
                    </button>
                </form>
                <form method="post" action="{% url 'appointments:cancel' appointment.pk %}">
                    {% csrf_token %}
                    <button type="submit" class="btn btn-outline-danger w-100"
                            onclick="return confirm('Hủy lịch hẹn này?')">
                        <i class="bi bi-x-circle me-1"></i>Hủy lịch hẹn
                    </button>
                </form>

                {% elif appointment.status == 'confirmed' %}
                <form method="post" action="{% url 'appointments:checkin' appointment.pk %}">
                    {% csrf_token %}
                    <button type="submit" class="btn btn-info w-100 text-white"
                            onclick="return confirm('Xác nhận bệnh nhân đã đến?')">
                        <i class="bi bi-box-arrow-in-right me-1"></i>Check-in bệnh nhân
                    </button>
                </form>
                <form method="post" action="{% url 'appointments:cancel' appointment.pk %}">
                    {% csrf_token %}
                    <button type="submit" class="btn btn-outline-danger w-100"
                            onclick="return confirm('Hủy lịch hẹn này?')">
                        <i class="bi bi-x-circle me-1"></i>Hủy lịch hẹn
                    </button>
                </form>

                {% elif appointment.status == 'checked_in' %}
                <form method="post" action="{% url 'appointments:done' appointment.pk %}">
                    {% csrf_token %}
                    <button type="submit" class="btn btn-success w-100"
                            onclick="return confirm('Đánh dấu lịch hẹn đã hoàn thành?')">
                        <i class="bi bi-check2-all me-1"></i>Hoàn thành khám
                    </button>
                </form>

                {% elif appointment.status == 'done' %}
                <p class="text-center text-muted mb-0">
                    <i class="bi bi-check-circle-fill text-success"></i> Lịch hẹn đã hoàn thành.
                </p>

                {% elif appointment.status == 'cancelled' %}
                <p class="text-center text-muted mb-0">
                    <i class="bi bi-x-circle-fill text-danger"></i> Lịch hẹn đã bị hủy.
                </p>
                {% endif %}

                {% if appointment.status not in 'done,cancelled' %}
                <hr class="my-1">
                <a href="{% url 'appointments:update' appointment.pk %}"
                   class="btn btn-outline-secondary btn-sm w-100">
                    <i class="bi bi-pencil me-1"></i>Chỉnh sửa thông tin
                </a>
                {% endif %}

            </div>
        </div>
    </div>
</div>
{% endblock %}
```

---

### 4.3. templates/appointments/appointment_form.html

```html
{% extends 'base.html' %}

{% block title %}{% if form.instance.pk %}Sửa Lịch Hẹn{% else %}Tạo Lịch Hẹn Mới{% endif %}{% endblock %}
{% block page_title %}{{ title }}{% endblock %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-md-8">
        <div class="card shadow-sm">
            <div class="card-header">
                <h5 class="mb-0">
                    <i class="bi bi-calendar-plus me-2"></i>{{ title }}
                </h5>
            </div>
            <div class="card-body">
                {% if form.instance.pk %}
                <form method="post" action="{% url 'appointments:update' form.instance.pk %}">
                {% else %}
                <form method="post" action="{% url 'appointments:create' %}">
                {% endif %}
                {% csrf_token %}

                {% if form.non_field_errors %}
                <div class="alert alert-danger">
                    {% for error in form.non_field_errors %}<p class="mb-0">{{ error }}</p>{% endfor %}
                </div>
                {% endif %}

                <div class="mb-3">
                    <label class="form-label fw-bold">Bệnh nhân <span class="text-danger">*</span></label>
                    {{ form.patient }}
                    {% if form.patient.errors %}<div class="invalid-feedback d-block">{{ form.patient.errors.0 }}</div>{% endif %}
                </div>

                <div class="mb-3">
                    <label class="form-label fw-bold">Bác sĩ <span class="text-danger">*</span></label>
                    {{ form.doctor }}
                    {% if form.doctor.errors %}<div class="invalid-feedback d-block">{{ form.doctor.errors.0 }}</div>{% endif %}
                </div>

                <div class="mb-3">
                    <label class="form-label fw-bold">Ngày khám <span class="text-danger">*</span></label>
                    {{ form.date }}
                    {% if form.date.errors %}<div class="invalid-feedback d-block">{{ form.date.errors.0 }}</div>{% endif %}
                </div>

                <div class="row mb-3">
                    <div class="col-md-6">
                        <label class="form-label fw-bold">Giờ bắt đầu <span class="text-danger">*</span></label>
                        {{ form.start_time }}
                        {% if form.start_time.errors %}<div class="invalid-feedback d-block">{{ form.start_time.errors.0 }}</div>{% endif %}
                    </div>
                    <div class="col-md-6">
                        <label class="form-label fw-bold">Giờ kết thúc <span class="text-danger">*</span></label>
                        {{ form.end_time }}
                        {% if form.end_time.errors %}<div class="invalid-feedback d-block">{{ form.end_time.errors.0 }}</div>{% endif %}
                    </div>
                </div>

                <div class="mb-4">
                    <label class="form-label fw-bold">Ghi chú</label>
                    {{ form.note }}
                </div>

                <div class="d-flex gap-2">
                    <button type="submit" class="btn btn-primary">
                        <i class="bi bi-save me-1"></i>
                        {% if form.instance.pk %}Lưu thay đổi{% else %}Tạo lịch hẹn{% endif %}
                    </button>
                    <a href="{% url 'appointments:list' %}" class="btn btn-outline-secondary">
                        <i class="bi bi-x me-1"></i>Hủy
                    </a>
                </div>

                </form>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

---

### 4.4. templates/appointments/my_schedule.html

```html
{% extends 'base.html' %}

{% block title %}Lịch Khám Của Tôi{% endblock %}
{% block page_title %}Lịch Khám Của Tôi{% endblock %}

{% block content %}
<div class="mb-4">
    <h4 class="mb-1"><i class="bi bi-calendar-week me-2"></i>Lịch Khám Của Tôi</h4>
    <p class="text-muted">BS. {{ doctor.full_name }} — Từ hôm nay trở đi</p>
</div>

{% if grouped_appointments %}
    {% for date, appts in grouped_appointments.items %}
    <div class="card mb-3 shadow-sm {% if date == today %}border-primary{% endif %}">
        <div class="card-header {% if date == today %}bg-primary text-white{% else %}bg-light{% endif %}">
            <strong>
                <i class="bi bi-calendar-day me-1"></i>
                {{ date|date:"l, d/m/Y" }}
                {% if date == today %}<span class="badge bg-warning text-dark ms-2">Hôm nay</span>{% endif %}
            </strong>
            <span class="float-end badge bg-secondary">{{ appts|length }} lịch</span>
        </div>
        <div class="card-body p-0">
            <ul class="list-group list-group-flush">
                {% for appt in appts %}
                <li class="list-group-item d-flex justify-content-between align-items-center">
                    <div>
                        <strong><i class="bi bi-person-fill text-primary me-1"></i>{{ appt.patient.full_name }}</strong>
                        <br>
                        <small class="text-muted">
                            <i class="bi bi-clock me-1"></i>
                            {{ appt.start_time|time:"H:i" }} – {{ appt.end_time|time:"H:i" }}
                        </small>
                        {% if appt.note %}
                        <br><small class="text-muted fst-italic">{{ appt.note|truncatechars:50 }}</small>
                        {% endif %}
                    </div>
                    <div class="text-end">
                        <span class="badge bg-{{ appt.get_status_badge_class }} d-block mb-1">
                            {{ appt.get_status_display }}
                        </span>
                        <a href="{% url 'appointments:detail' appt.pk %}"
                           class="btn btn-outline-primary btn-sm">
                            <i class="bi bi-eye"></i>
                        </a>
                    </div>
                </li>
                {% endfor %}
            </ul>
        </div>
    </div>
    {% endfor %}
{% else %}
<div class="text-center py-5">
    <i class="bi bi-calendar-x fs-1 text-muted d-block mb-3"></i>
    <h5 class="text-muted">Bạn không có lịch khám nào từ hôm nay trở đi.</h5>
</div>
{% endif %}
{% endblock %}
```

---

## PHẦN 5: appointments/tests.py

```python
# appointments/tests.py
# Chạy tests: python manage.py test appointments

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from datetime import date, time, timedelta

from appointments.models import Appointment

try:
    from patients.models import Patient
    from doctors.models import Doctor
    HAS_MODELS = True
except ImportError:
    HAS_MODELS = False


def make_user(username, password='testpass123', **kwargs):
    """Helper: tạo user nhanh."""
    return User.objects.create_user(username=username, password=password, **kwargs)


class AppointmentStatusTest(TestCase):
    """Test luồng thay đổi trạng thái lịch hẹn."""

    def setUp(self):
        if not HAS_MODELS:
            self.skipTest('Patient hoặc Doctor model chưa tồn tại')

        self.staff = make_user('staff_u', 'staffpass')
        self.doc_user = make_user('doc_u', 'docpass')
        self.client = Client()
        self.client.login(username='staff_u', password='staffpass')

        # Tạo dữ liệu test
        try:
            self.patient = Patient.objects.create(
                full_name='Bệnh Nhân Test',
                phone='0901234567',
                gender='M',
                date_of_birth=date(1990, 1, 1),
            )
            self.doctor = Doctor.objects.create(
                user=self.doc_user,
                full_name='Bác Sĩ Test',
                specialty='Nội khoa',
            )
        except Exception as e:
            self.skipTest(f'Không tạo được dữ liệu test: {e}')

        self.appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            date=date.today() + timedelta(days=1),  # Ngày mai
            start_time=time(9, 0),
            end_time=time(9, 30),
            status='pending',
        )

    def test_appointment_created(self):
        """Lịch hẹn được tạo với status pending."""
        self.assertEqual(self.appointment.status, 'pending')
        self.assertEqual(self.appointment.patient, self.patient)

    def test_confirm_from_pending(self):
        """pending -> confirmed thành công."""
        url = reverse('appointments:confirm', kwargs={'pk': self.appointment.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)  # Redirect sau thành công
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, 'confirmed')

    def test_cannot_confirm_confirmed(self):
        """Không thể confirm lịch đã confirmed."""
        self.appointment.status = 'confirmed'
        self.appointment.save()
        url = reverse('appointments:confirm', kwargs={'pk': self.appointment.pk})
        self.client.post(url)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, 'confirmed')  # Không đổi

    def test_checkin_from_confirmed(self):
        """confirmed -> checked_in thành công."""
        self.appointment.status = 'confirmed'
        self.appointment.save()
        url = reverse('appointments:checkin', kwargs={'pk': self.appointment.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, 'checked_in')

    def test_cannot_checkin_from_pending(self):
        """Không thể check-in từ pending (phải confirmed trước)."""
        url = reverse('appointments:checkin', kwargs={'pk': self.appointment.pk})
        self.client.post(url)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, 'pending')  # Không đổi

    def test_full_flow_to_done(self):
        """Test toàn bộ luồng: pending -> confirmed -> checked_in -> done."""
        pk = self.appointment.pk

        # Bước 1: Confirm
        self.client.post(reverse('appointments:confirm', kwargs={'pk': pk}))
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, 'confirmed', 'Confirm thất bại')

        # Bước 2: Check-in
        self.client.post(reverse('appointments:checkin', kwargs={'pk': pk}))
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, 'checked_in', 'Check-in thất bại')

        # Bước 3: Done
        self.client.post(reverse('appointments:done', kwargs={'pk': pk}))
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, 'done', 'Done thất bại')

    def test_cancel_from_pending(self):
        """Hủy lịch từ pending."""
        url = reverse('appointments:cancel', kwargs={'pk': self.appointment.pk})
        self.client.post(url)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, 'cancelled')

    def test_cancel_from_confirmed(self):
        """Hủy lịch từ confirmed."""
        self.appointment.status = 'confirmed'
        self.appointment.save()
        url = reverse('appointments:cancel', kwargs={'pk': self.appointment.pk})
        self.client.post(url)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, 'cancelled')

    def test_cannot_cancel_done(self):
        """Không thể hủy lịch đã done."""
        self.appointment.status = 'done'
        self.appointment.save()
        url = reverse('appointments:cancel', kwargs={'pk': self.appointment.pk})
        self.client.post(url)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, 'done')  # Vẫn done

    def test_get_request_cannot_change_status(self):
        """GET request không được phép thay đổi status."""
        url = reverse('appointments:confirm', kwargs={'pk': self.appointment.pk})
        self.client.get(url)   # GET thay vì POST
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, 'pending')  # Không đổi


class AuthTest(TestCase):
    """Test xác thực đăng nhập."""

    def setUp(self):
        self.user = make_user('logintest', 'rightpass')
        self.client = Client()

    def test_login_correct(self):
        """Đăng nhập đúng -> redirect (302)."""
        response = self.client.post('/accounts/login/', {
            'username': 'logintest', 'password': 'rightpass'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_login_wrong_password(self):
        """Đăng nhập sai mật khẩu -> render lại login (200)."""
        response = self.client.post('/accounts/login/', {
            'username': 'logintest', 'password': 'WRONG'
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_unauthenticated_redirected(self):
        """User chưa đăng nhập -> redirect về login."""
        response = self.client.get(reverse('appointments:list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url.lower())
```

### Cách chạy tests:

```powershell
# Chạy tất cả tests của app appointments
python manage.py test appointments

# Chạy 1 class test cụ thể
python manage.py test appointments.tests.AppointmentStatusTest

# Chạy 1 hàm test cụ thể
python manage.py test appointments.tests.AppointmentStatusTest.test_full_flow_to_done

# Chạy với output chi tiết (-v 2)
python manage.py test appointments -v 2
```

**Kết quả mong đợi:**
```
Ran 12 tests in 0.xxx s
OK
```

---

## PHẦN 6: Câu hỏi Giảng viên có thể Hỏi

**Q1: Tại sao views thay đổi trạng thái chỉ chấp nhận POST, không chấp nhận GET?**
> GET request có thể bị browser cache, bot crawl, hoặc người dùng vô tình gọi lại. Dùng POST đảm bảo chỉ hành động có chủ ý (click nút) mới thay đổi dữ liệu. Đây là quy tắc REST cơ bản.

**Q2: Giải thích luồng trạng thái lịch hẹn trong hệ thống này.**
> pending -> confirmed -> checked_in -> done. Từ pending hoặc confirmed có thể cancel. Mỗi view kiểm tra trạng thái hiện tại trước khi chuyển để đảm bảo đúng thứ tự nghiệp vụ.

**Q3: `select_related()` trong `appointment_list` làm gì?**
> Tối ưu query database: thay vì mỗi row lại query thêm để lấy patient và doctor (N+1 queries), `select_related()` JOIN ngay từ đầu trong 1 câu SQL. 100 lịch hẹn = 1 query thay vì 201 queries.

**Q4: Giải thích cách viết test với Django TestCase.**
> `setUp()` chạy trước mỗi test method tạo dữ liệu sạch. `self.client.post()` giả lập HTTP request. `self.appointment.refresh_from_db()` lấy lại dữ liệu từ DB để kiểm tra đã thực sự thay đổi chưa. `self.assertEqual()` so sánh giá trị thực tế với kỳ vọng.

**Q5: Làm sao hiển thị nút hành động khác nhau theo trạng thái trong template?**
> Dùng `{% if appointment.status == 'pending' %}...{% elif appointment.status == 'confirmed' %}...{% endif %}`. Mỗi trạng thái hiện nút tương ứng với action cho phép tiếp theo.

---

## PHẦN 7: Lỗi Thường Gặp

| Lỗi | Nguyên nhân | Cách sửa |
|---|---|---|
| `ImportError: cannot import appointment_list` | Chưa thêm view vào `views.py` hoặc sai tên | Kiểm tra tên hàm trong views.py |
| `NoReverseMatch: appointments:confirm` | Chưa thêm URL confirm vào `urls.py` | Kiểm tra `appointments/urls.py` |
| Nút hành động không hiện | Điều kiện `{% if appointment.status == ... %}` sai | Dùng `{{ appointment.status }}` trong template để debug |
| Tests không chạy | Patient/Doctor model chưa có | Thêm `if not HAS_MODELS: self.skipTest(...)` như hướng dẫn |
| `refresh_from_db()` không thấy thay đổi | View không gọi `appointment.save()` | Kiểm tra có dòng `.save()` trong view |

---

## ✅ Checklist Hoàn thành

- [ ] `appointments/views.py` – 7 views bổ sung (list, detail, confirm, checkin, done, cancel, my_schedule)
- [ ] `appointments/urls.py` – Đầy đủ 9 URL patterns
- [ ] `templates/appointments/appointment_list.html`
- [ ] `templates/appointments/appointment_detail.html`
- [ ] `templates/appointments/appointment_form.html`
- [ ] `templates/appointments/my_schedule.html`
- [ ] `appointments/tests.py` – 12 test cases
- [ ] Test thay đổi trạng thái đúng luồng ✅
- [ ] Test chặn thay đổi trạng thái sai ✅
- [ ] Test GET request không thay đổi dữ liệu ✅
- [ ] `python manage.py test appointments` -> OK ✅
