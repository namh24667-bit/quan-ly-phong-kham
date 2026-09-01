# 📘 GUIDE B — Thành viên B: Quản lý Bệnh nhân (patients app)

> **Phụ trách:** `patients/` app hoàn chỉnh  
> **Thời gian ước tính:** ~4 giờ

---

## TỔNG QUAN

Bạn phụ trách toàn bộ **patients app** — trái tim của hệ thống phòng khám.

### File cần tạo:
```
patients/
├── forms.py          <- bạn viết
├── views.py          <- bạn viết
├── urls.py           <- bạn viết
└── templates/patients/
    ├── patient_list.html
    ├── patient_form.html
    ├── patient_detail.html
    └── patient_confirm_delete.html
```

### Phụ thuộc:
| Từ ai | Cung cấp gì | Cách dùng |
|---|---|---|
| Thành viên A | `accounts.decorators.role_required` | Import trong views.py |
| GUIDE_CHUNG | Model `Patient` đã có sẵn | Dùng trực tiếp, không viết lại |

---

## PHẦN 1: patients/forms.py

```python
# patients/forms.py
from django import forms
from datetime import date
from .models import Patient


class PatientForm(forms.ModelForm):
    """
    ModelForm tự động tạo field từ model Patient.
    Chỉ cần khai báo một lần, Django tự sinh HTML + validate + lưu DB.
    """

    class Meta:
        model = Patient
        fields = ['full_name', 'date_of_birth', 'gender', 'phone', 'address']
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nguyễn Văn A',
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',  # Trình duyệt hiện date picker
            }),
            'gender': forms.Select(attrs={
                'class': 'form-select',
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '0901234567',
                'type': 'tel',
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Số nhà, đường, phường/xã, quận/huyện, tỉnh/thành phố',
            }),
        }
        labels = {
            'full_name': 'Họ và tên',
            'date_of_birth': 'Ngày sinh',
            'gender': 'Giới tính',
            'phone': 'Số điện thoại',
            'address': 'Địa chỉ',
        }
        error_messages = {
            'full_name': {'required': 'Vui lòng nhập họ tên bệnh nhân.'},
            'date_of_birth': {'required': 'Vui lòng nhập ngày sinh.'},
            'gender': {'required': 'Vui lòng chọn giới tính.'},
            'phone': {'required': 'Vui lòng nhập số điện thoại.'},
        }

    def clean_phone(self):
        """Validate số điện thoại: chỉ số, 9-11 ký tự."""
        phone = self.cleaned_data.get('phone', '').strip()
        if not phone.isdigit():
            raise forms.ValidationError('Số điện thoại chỉ được chứa chữ số (0-9).')
        if not (9 <= len(phone) <= 11):
            raise forms.ValidationError(
                f'Số điện thoại phải từ 9–11 chữ số. Bạn đang nhập {len(phone)} chữ số.'
            )
        return phone  # QUAN TRỌNG: phải return giá trị đã validate

    def clean_date_of_birth(self):
        """Validate ngày sinh: không được là ngày tương lai."""
        dob = self.cleaned_data.get('date_of_birth')
        if dob and dob > date.today():
            raise forms.ValidationError('Ngày sinh không thể là ngày trong tương lai.')
        return dob
```

> **Tại sao dùng `clean_<fieldname>()`?**  
> Django validation có 2 tầng: (1) Django tự kiểm tra kiểu dữ liệu, (2) bạn viết `clean_<tên>` để thêm rule riêng. Hàm phải **return** giá trị đã validate, hoặc `raise ValidationError` nếu lỗi.

---

## PHẦN 2: patients/views.py

```python
# patients/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from accounts.decorators import role_required   # Từ Thành viên A
from .models import Patient
from .forms import PatientForm


@login_required
@role_required('admin', 'staff')
def patient_list(request):
    """
    Danh sách bệnh nhân với tìm kiếm (Q object) và phân trang (Paginator).
    """
    # Lấy từ khóa tìm kiếm từ URL: /patients/?q=nguyen
    query = request.GET.get('q', '').strip()

    patients = Patient.objects.all()

    if query:
        # Q object cho phép dùng OR (|): tìm theo tên HOẶC SĐT
        # icontains = không phân biệt hoa thường
        patients = patients.filter(
            Q(full_name__icontains=query) |
            Q(phone__icontains=query)
        )

    # Phân trang: 10 bệnh nhân/trang
    paginator = Paginator(patients, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)  # get_page() an toàn, không crash

    return render(request, 'patients/patient_list.html', {
        'page_obj': page_obj,
        'query': query,
        'total': patients.count(),
    })


@login_required
@role_required('admin', 'staff')
def patient_create(request):
    """
    Thêm bệnh nhân mới.
    GET  -> form trống
    POST -> validate, lưu DB, redirect (PRG pattern)
    """
    if request.method == 'POST':
        form = PatientForm(request.POST)
        if form.is_valid():
            patient = form.save()
            messages.success(request, f'Đã thêm bệnh nhân {patient.full_name} thành công!')
            return redirect('patients:list')
        # form.is_valid() = False -> render lại form với lỗi
    else:
        form = PatientForm()  # Form trống

    return render(request, 'patients/patient_form.html', {
        'form': form,
        'title': 'Thêm Bệnh Nhân Mới',
        'button_text': 'Thêm bệnh nhân',
        'is_update': False,
    })


@login_required
@role_required('admin', 'staff')
def patient_update(request, pk):
    """Sửa thông tin bệnh nhân."""
    # get_object_or_404: tìm Patient có pk=pk, nếu không có -> tự trả 404
    patient = get_object_or_404(Patient, pk=pk)

    if request.method == 'POST':
        # instance=patient -> Django biết đây là UPDATE, không phải INSERT mới
        form = PatientForm(request.POST, instance=patient)
        if form.is_valid():
            form.save()
            messages.success(request, f'Đã cập nhật thông tin {patient.full_name}!')
            return redirect('patients:detail', pk=patient.pk)
    else:
        # GET: điền sẵn dữ liệu hiện tại vào form
        form = PatientForm(instance=patient)

    return render(request, 'patients/patient_form.html', {
        'form': form,
        'patient': patient,
        'title': f'Sửa: {patient.full_name}',
        'button_text': 'Lưu thay đổi',
        'is_update': True,
    })


@login_required
@role_required('admin')   # Chỉ admin được xóa
def patient_delete(request, pk):
    """Xóa bệnh nhân: GET -> trang xác nhận, POST -> thực sự xóa."""
    patient = get_object_or_404(Patient, pk=pk)

    if request.method == 'POST':
        name = patient.full_name
        patient.delete()
        messages.success(request, f'Đã xóa bệnh nhân {name}.')
        return redirect('patients:list')

    # GET: hiện trang xác nhận
    return render(request, 'patients/patient_confirm_delete.html', {'patient': patient})


@login_required
@role_required('admin', 'staff', 'doctor')
def patient_detail(request, pk):
    """Chi tiết bệnh nhân + lịch sử khám."""
    patient = get_object_or_404(Patient, pk=pk)

    # Lấy lịch sử khám (khi Thành viên A và C đã tạo Appointment)
    try:
        appointments = patient.appointment_set.select_related(
            'doctor'
        ).order_by('-date', '-start_time')
    except Exception:
        appointments = []  # Nếu Appointment chưa sẵn sàng

    return render(request, 'patients/patient_detail.html', {
        'patient': patient,
        'appointments': appointments,
    })
```

> **Tại sao sau POST thành công dùng `redirect()` thay vì `render()`?**  
> Đây là **PRG pattern (Post/Redirect/Get)**. Nếu dùng `render()` sau POST, người dùng ấn F5 sẽ gửi form lại -> tạo bản ghi trùng! `redirect()` chuyển sang GET request, F5 chỉ load lại trang.

---

## PHẦN 3: patients/urls.py

```python
# patients/urls.py
from django.urls import path
from . import views

app_name = 'patients'   # Namespace: gọi bằng 'patients:list', 'patients:detail' v.v.

urlpatterns = [
    path('', views.patient_list, name='list'),                    # /patients/
    path('create/', views.patient_create, name='create'),         # /patients/create/
    path('<int:pk>/', views.patient_detail, name='detail'),       # /patients/5/
    path('<int:pk>/update/', views.patient_update, name='update'),# /patients/5/update/
    path('<int:pk>/delete/', views.patient_delete, name='delete'),# /patients/5/delete/
]
```

Đảm bảo `clinicms/urls.py` đã có:
```python
path('patients/', include('patients.urls')),
```

> **Tại sao dùng tên URL thay vì hardcode `/patients/`?**  
> Dùng `{% url 'patients:list' %}` trong template: nếu đổi URL, chỉ sửa 1 chỗ trong `urls.py`. Hardcode phải sửa hàng chục nơi.

---

## PHẦN 4: Templates HTML

### 4.1. templates/patients/patient_list.html

```html
{% extends 'base.html' %}

{% block title %}Danh Sách Bệnh Nhân{% endblock %}
{% block page_title %}Danh Sách Bệnh Nhân{% endblock %}

{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
    <div>
        <h4 class="mb-0"><i class="bi bi-people-fill text-primary me-2"></i>Bệnh Nhân</h4>
        <small class="text-muted">
            {% if query %}Tìm thấy {{ total }} kết quả cho "{{ query }}"
            {% else %}Tổng cộng {{ total }} bệnh nhân{% endif %}
        </small>
    </div>
    <a href="{% url 'patients:create' %}" class="btn btn-primary">
        <i class="bi bi-plus-circle me-1"></i>Thêm Bệnh Nhân
    </a>
</div>

<!-- Thanh tìm kiếm -->
<div class="card mb-3 shadow-sm">
    <div class="card-body py-2">
        <form method="GET" action="{% url 'patients:list' %}">
            <div class="input-group">
                <input type="text" name="q" class="form-control"
                       placeholder="Tìm theo tên hoặc số điện thoại..."
                       value="{{ query }}">
                <button type="submit" class="btn btn-outline-primary">
                    <i class="bi bi-search"></i> Tìm
                </button>
                {% if query %}
                <a href="{% url 'patients:list' %}" class="btn btn-outline-secondary">
                    <i class="bi bi-x-lg"></i> Xóa
                </a>
                {% endif %}
            </div>
        </form>
    </div>
</div>

<!-- Bảng danh sách -->
<div class="card shadow-sm">
    <div class="card-body p-0">
        {% if page_obj %}
        <div class="table-responsive">
            <table class="table table-hover table-striped mb-0">
                <thead class="table-dark">
                    <tr>
                        <th>#</th>
                        <th>Họ tên</th>
                        <th>Tuổi</th>
                        <th>Giới tính</th>
                        <th>SĐT</th>
                        <th>Ngày tạo</th>
                        <th class="text-center">Hành động</th>
                    </tr>
                </thead>
                <tbody>
                    {% for patient in page_obj %}
                    <tr>
                        <td class="text-muted">{{ page_obj.start_index|add:forloop.counter0 }}</td>
                        <td>
                            <a href="{% url 'patients:detail' pk=patient.pk %}"
                               class="text-decoration-none fw-semibold">
                                {{ patient.full_name }}
                            </a>
                        </td>
                        <td>{{ patient.get_age }}</td>
                        <td>
                            {% if patient.gender == 'M' %}<span class="badge bg-primary">Nam</span>
                            {% elif patient.gender == 'F' %}<span class="badge bg-danger">Nữ</span>
                            {% else %}<span class="badge bg-secondary">Khác</span>{% endif %}
                        </td>
                        <td>{{ patient.phone }}</td>
                        <td><small>{{ patient.created_at|date:"d/m/Y" }}</small></td>
                        <td class="text-center">
                            <a href="{% url 'patients:detail' pk=patient.pk %}"
                               class="btn btn-sm btn-outline-info" title="Xem">
                                <i class="bi bi-eye"></i>
                            </a>
                            <a href="{% url 'patients:update' pk=patient.pk %}"
                               class="btn btn-sm btn-outline-warning" title="Sửa">
                                <i class="bi bi-pencil"></i>
                            </a>
                            <a href="{% url 'patients:delete' pk=patient.pk %}"
                               class="btn btn-sm btn-outline-danger" title="Xóa">
                                <i class="bi bi-trash"></i>
                            </a>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <!-- Phân trang -->
        {% if page_obj.has_other_pages %}
        <div class="d-flex justify-content-center py-3">
            <nav>
                <ul class="pagination mb-0">
                    {% if page_obj.has_previous %}
                    <li class="page-item">
                        <a class="page-link" href="?page=1{% if query %}&q={{ query }}{% endif %}">«</a>
                    </li>
                    <li class="page-item">
                        <a class="page-link"
                           href="?page={{ page_obj.previous_page_number }}{% if query %}&q={{ query }}{% endif %}">‹</a>
                    </li>
                    {% endif %}
                    <li class="page-item active">
                        <span class="page-link">{{ page_obj.number }} / {{ page_obj.paginator.num_pages }}</span>
                    </li>
                    {% if page_obj.has_next %}
                    <li class="page-item">
                        <a class="page-link"
                           href="?page={{ page_obj.next_page_number }}{% if query %}&q={{ query }}{% endif %}">›</a>
                    </li>
                    <li class="page-item">
                        <a class="page-link"
                           href="?page={{ page_obj.paginator.num_pages }}{% if query %}&q={{ query }}{% endif %}">»</a>
                    </li>
                    {% endif %}
                </ul>
            </nav>
        </div>
        {% endif %}

        {% else %}
        <div class="text-center py-5">
            <i class="bi bi-inbox display-1 text-muted"></i>
            <p class="text-muted mt-3 fs-5">
                {% if query %}Không tìm thấy bệnh nhân nào với "{{ query }}".
                {% else %}Chưa có bệnh nhân nào. <a href="{% url 'patients:create' %}">Thêm ngay</a>{% endif %}
            </p>
        </div>
        {% endif %}
    </div>
</div>
{% endblock %}
```

---

### 4.2. templates/patients/patient_form.html

```html
{% extends 'base.html' %}

{% block title %}{{ title }}{% endblock %}
{% block page_title %}{{ title }}{% endblock %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-md-8 col-lg-7">
        <div class="card shadow">
            <div class="card-header bg-primary text-white">
                <h5 class="mb-0">
                    <i class="bi bi-{% if is_update %}pencil-square{% else %}person-plus{% endif %} me-2"></i>
                    {{ title }}
                </h5>
            </div>
            <div class="card-body p-4">
                <form method="post" action="" novalidate>
                    {% csrf_token %}

                    {% if form.non_field_errors %}
                    <div class="alert alert-danger">
                        {% for error in form.non_field_errors %}<p class="mb-0">{{ error }}</p>{% endfor %}
                    </div>
                    {% endif %}

                    <!-- Họ tên -->
                    <div class="mb-3">
                        <label class="form-label fw-semibold">Họ và tên <span class="text-danger">*</span></label>
                        {{ form.full_name }}
                        {% if form.full_name.errors %}
                        <div class="invalid-feedback d-block">{{ form.full_name.errors.0 }}</div>
                        {% endif %}
                    </div>

                    <!-- Ngày sinh + Giới tính -->
                    <div class="row">
                        <div class="col-md-6 mb-3">
                            <label class="form-label fw-semibold">Ngày sinh <span class="text-danger">*</span></label>
                            {{ form.date_of_birth }}
                            {% if form.date_of_birth.errors %}
                            <div class="invalid-feedback d-block">{{ form.date_of_birth.errors.0 }}</div>
                            {% endif %}
                        </div>
                        <div class="col-md-6 mb-3">
                            <label class="form-label fw-semibold">Giới tính <span class="text-danger">*</span></label>
                            {{ form.gender }}
                            {% if form.gender.errors %}
                            <div class="invalid-feedback d-block">{{ form.gender.errors.0 }}</div>
                            {% endif %}
                        </div>
                    </div>

                    <!-- Số điện thoại -->
                    <div class="mb-3">
                        <label class="form-label fw-semibold">Số điện thoại <span class="text-danger">*</span></label>
                        {{ form.phone }}
                        {% if form.phone.errors %}
                        <div class="invalid-feedback d-block">{{ form.phone.errors.0 }}</div>
                        {% endif %}
                        <div class="form-text">Nhập 9–11 chữ số, không dùng dấu cách.</div>
                    </div>

                    <!-- Địa chỉ -->
                    <div class="mb-4">
                        <label class="form-label fw-semibold">Địa chỉ</label>
                        {{ form.address }}
                        {% if form.address.errors %}
                        <div class="invalid-feedback d-block">{{ form.address.errors.0 }}</div>
                        {% endif %}
                    </div>

                    <div class="d-flex gap-2">
                        <button type="submit" class="btn btn-primary">
                            <i class="bi bi-save me-1"></i>{{ button_text }}
                        </button>
                        {% if is_update %}
                        <a href="{% url 'patients:detail' pk=patient.pk %}" class="btn btn-outline-secondary">
                            <i class="bi bi-x-circle me-1"></i>Hủy
                        </a>
                        {% else %}
                        <a href="{% url 'patients:list' %}" class="btn btn-outline-secondary">
                            <i class="bi bi-x-circle me-1"></i>Hủy
                        </a>
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

### 4.3. templates/patients/patient_detail.html

```html
{% extends 'base.html' %}

{% block title %}{{ patient.full_name }} – Chi Tiết{% endblock %}
{% block page_title %}Chi Tiết Bệnh Nhân{% endblock %}

{% block content %}
<div class="mb-3">
    <a href="{% url 'patients:list' %}" class="btn btn-outline-secondary btn-sm">
        <i class="bi bi-arrow-left"></i> Quay lại
    </a>
</div>

<div class="row g-4">
    <!-- Thông tin bệnh nhân -->
    <div class="col-md-5">
        <div class="card shadow h-100">
            <div class="card-header bg-primary text-white">
                <h5 class="mb-0"><i class="bi bi-person-circle me-2"></i>Thông Tin</h5>
            </div>
            <div class="card-body">
                <table class="table table-borderless">
                    <tr><th class="text-muted" style="width:40%">Họ tên:</th>
                        <td class="fw-semibold">{{ patient.full_name }}</td></tr>
                    <tr><th class="text-muted">Ngày sinh:</th>
                        <td>{{ patient.date_of_birth|date:"d/m/Y" }}</td></tr>
                    <tr><th class="text-muted">Tuổi:</th>
                        <td>{{ patient.get_age }} tuổi</td></tr>
                    <tr><th class="text-muted">Giới tính:</th>
                        <td>{{ patient.get_gender_display }}</td></tr>
                    <tr><th class="text-muted">SĐT:</th>
                        <td><a href="tel:{{ patient.phone }}">{{ patient.phone }}</a></td></tr>
                    <tr><th class="text-muted">Địa chỉ:</th>
                        <td>{{ patient.address|default:"Chưa cập nhật" }}</td></tr>
                    <tr><th class="text-muted">Ngày tạo:</th>
                        <td><small class="text-muted">{{ patient.created_at|date:"d/m/Y H:i" }}</small></td></tr>
                </table>
            </div>
            <div class="card-footer bg-transparent">
                <div class="d-flex gap-2">
                    <a href="{% url 'patients:update' pk=patient.pk %}" class="btn btn-warning btn-sm">
                        <i class="bi bi-pencil me-1"></i>Sửa
                    </a>
                    <a href="{% url 'patients:delete' pk=patient.pk %}" class="btn btn-danger btn-sm">
                        <i class="bi bi-trash me-1"></i>Xóa
                    </a>
                </div>
            </div>
        </div>
    </div>

    <!-- Lịch sử khám -->
    <div class="col-md-7">
        <div class="card shadow h-100">
            <div class="card-header bg-success text-white">
                <h5 class="mb-0"><i class="bi bi-calendar2-check me-2"></i>Lịch Sử Khám</h5>
            </div>
            <div class="card-body p-0">
                {% if appointments %}
                <table class="table table-hover mb-0">
                    <thead class="table-light">
                        <tr><th>#</th><th>Ngày khám</th><th>Giờ</th><th>Bác sĩ</th><th>Trạng thái</th></tr>
                    </thead>
                    <tbody>
                        {% for appt in appointments %}
                        <tr>
                            <td>{{ forloop.counter }}</td>
                            <td>{{ appt.date|date:"d/m/Y" }}</td>
                            <td>{{ appt.start_time|time:"H:i" }}</td>
                            <td>BS. {{ appt.doctor.full_name }}</td>
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
                <div class="text-center py-5">
                    <i class="bi bi-calendar-x display-4 text-muted"></i>
                    <p class="text-muted mt-2">Bệnh nhân chưa có lịch khám nào.</p>
                </div>
                {% endif %}
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

---

### 4.4. templates/patients/patient_confirm_delete.html

```html
{% extends 'base.html' %}

{% block title %}Xác Nhận Xóa{% endblock %}
{% block page_title %}Xác Nhận Xóa Bệnh Nhân{% endblock %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-md-6">
        <div class="card shadow border-danger">
            <div class="card-header bg-danger text-white">
                <h4 class="mb-0"><i class="bi bi-exclamation-triangle-fill me-2"></i>Xác Nhận Xóa</h4>
            </div>
            <div class="card-body text-center py-4">
                <div class="fs-1 mb-3">⚠️</div>
                <h5>Bạn có chắc muốn xóa bệnh nhân này không?</h5>
                <div class="alert alert-warning mt-3">
                    <strong>{{ patient.full_name }}</strong><br>
                    <small class="text-muted">SĐT: {{ patient.phone }} | Ngày sinh: {{ patient.date_of_birth|date:"d/m/Y" }}</small>
                </div>
                <p class="text-danger">
                    <strong>Hành động này không thể hoàn tác!</strong>
                </p>
            </div>
            <div class="card-footer bg-transparent">
                <div class="d-flex gap-3 justify-content-center">
                    <a href="{% url 'patients:detail' pk=patient.pk %}" class="btn btn-secondary btn-lg">
                        <i class="bi bi-x-circle me-1"></i>Hủy, giữ lại
                    </a>
                    <form method="post" action="{% url 'patients:delete' pk=patient.pk %}">
                        {% csrf_token %}
                        <button type="submit" class="btn btn-danger btn-lg">
                            <i class="bi bi-trash me-1"></i>Xóa vĩnh viễn
                        </button>
                    </form>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

---

## PHẦN 5: Giải thích Q Object và Paginator

### Q Object (tìm kiếm phức tạp)

```python
from django.db.models import Q

# Cách thông thường chỉ dùng được AND
Patient.objects.filter(full_name__icontains='An', phone__icontains='090')
# WHERE full_name LIKE '%An%' AND phone LIKE '%090%'

# Q object dùng được OR (|)
Patient.objects.filter(
    Q(full_name__icontains='An') | Q(phone__icontains='090')
)
# WHERE full_name LIKE '%An%' OR phone LIKE '%090%'
```

| Ký hiệu | Ý nghĩa | Ví dụ |
|---|---|---|
| `\|` | OR (hoặc) | `Q(tên=A) \| Q(sdt=B)` |
| `&` | AND (và) | `Q(tên=A) & Q(tuoi=25)` |
| `~` | NOT (phủ định) | `~Q(tên='Ẩn danh')` |

### Paginator

```python
from django.core.paginator import Paginator

paginator = Paginator(patients, 10)      # 10 bản ghi/trang
page_number = request.GET.get('page', 1)
page_obj = paginator.get_page(page_number)  # an toàn, không crash dù page=999
```

**Các thuộc tính trong template:**
```
{{ page_obj.number }}                  -> số trang hiện tại
{{ page_obj.paginator.num_pages }}     -> tổng số trang
{{ page_obj.has_previous }}            -> True/False
{{ page_obj.has_next }}                -> True/False
{{ page_obj.previous_page_number }}    -> số trang trước
{{ page_obj.next_page_number }}        -> số trang sau
```

**Lưu ý khi kết hợp tìm kiếm + phân trang:**
```html
<!-- ĐÚNG: giữ lại ?q=... khi chuyển trang -->
<a href="?page={{ page_obj.next_page_number }}{% if query %}&q={{ query }}{% endif %}">Trang sau</a>

<!-- SAI: mất từ khóa tìm kiếm khi chuyển trang -->
<a href="?page={{ page_obj.next_page_number }}">Trang sau</a>
```

---

## PHẦN 6: Test Nhanh

| # | Thao tác | Kết quả mong đợi |
|---|---|---|
| 1 | Vào `/patients/create/`, điền đúng | Lưu thành công, về danh sách |
| 2 | Nhập SĐT = "abc123" | Lỗi "chỉ được chứa chữ số" |
| 3 | Nhập ngày sinh = ngày mai | Lỗi "không thể là ngày tương lai" |
| 4 | Để trống Họ tên | Lỗi "Vui lòng nhập họ tên" |
| 5 | Tìm theo tên | Chỉ hiện bệnh nhân có tên khớp |
| 6 | Tìm theo SĐT | Chỉ hiện bệnh nhân có SĐT khớp |
| 7 | Sửa SĐT | Lưu thành công, về trang chi tiết |
| 8 | Xóa bệnh nhân | Hiện trang xác nhận, sau đó xóa |
| 9 | Xem chi tiết | Thấy thông tin + bảng lịch sử khám |

---

## PHẦN 7: Câu hỏi Giảng viên có thể Hỏi

**Q1: Tại sao dùng `ModelForm` thay vì form HTML thủ công?**
> `ModelForm` tự tạo fields từ model, tự validate, tự lưu DB qua `form.save()`. Nếu viết thủ công phải làm hết từng bước: tạo `<input>`, lấy `request.POST[...]`, validate, tạo object, gọi `.save()`. ModelForm tiết kiệm code và ít lỗi hơn.

**Q2: `{% csrf_token %}` dùng để làm gì?**
> Bảo vệ chống CSRF — ngăn website khác giả mạo request. Nếu thiếu Django trả 403 Forbidden.

**Q3: Tại sao sau POST thành công dùng `redirect()` không dùng `render()`?**
> PRG pattern. Dùng `render()` sau POST, F5 sẽ submit form lại -> bản ghi trùng. `redirect()` chuyển sang GET, F5 chỉ load lại trang.

**Q4: Q object dùng `|` để làm gì?**
> `|` là OR — tìm bệnh nhân có TÊN khớp HOẶC SĐT khớp. Dùng `.filter()` bình thường là AND — phải khớp cả hai cùng lúc.

**Q5: `get_object_or_404()` khác `Patient.objects.get(pk=pk)` thế nào?**
> `.get()` raise `DoesNotExist` exception -> lỗi 500. `get_object_or_404()` tự trả về trang 404 — hành vi đúng khi user nhập URL với ID không tồn tại.

**Q6: Tại sao view sửa bệnh nhân truyền `instance=patient` vào form?**
> Không có `instance`, form sẽ tạo bệnh nhân MỚI thay vì cập nhật. `instance=patient` báo Django đây là UPDATE record đã có.

**Q7: Tại sao chỉ admin mới được xóa (`@role_required('admin')`), còn staff thì không?**
> Xóa là hành động không thể hoàn tác, có thể ảnh hưởng dữ liệu lịch sử. Admin có trách nhiệm và quyền cao hơn mới được thực hiện các thao tác nguy hiểm.

---

## PHẦN 8: Lỗi Thường Gặp

| Lỗi | Nguyên nhân | Cách sửa |
|---|---|---|
| `NoReverseMatch: patients:list` | Thiếu `app_name = 'patients'` hoặc chưa include URL | Kiểm tra `patients/urls.py` và `clinicms/urls.py` |
| Form không hiện lỗi | Dùng `{{ form.as_p }}` nhưng widget có class riêng | Hiển thị từng field riêng như hướng dẫn |
| SĐT validation không chạy | Tên hàm sai, phải là `clean_phone` (có `clean_` prefix) | Kiểm tra tên hàm trong forms.py |
| `get_age` trả về số âm | Ngày sinh nhập sai (năm tương lai) | Validation `clean_date_of_birth` đã bắt, cần migrate |
| `TemplateDoesNotExist` | Chưa tạo thư mục `templates/patients/` | Tạo đúng cấu trúc thư mục |
| Phân trang mất từ khóa tìm kiếm | Quên `&q={{ query }}` trong link phân trang | Thêm vào mọi link chuyển trang |

---

## ✅ Checklist Hoàn thành

- [ ] `patients/forms.py` – PatientForm với validation phone + date
- [ ] `patients/views.py` – 5 views: list, create, update, delete, detail
- [ ] `patients/urls.py` – 5 URL patterns với namespace `patients`
- [ ] `templates/patients/patient_list.html` – bảng + tìm kiếm + phân trang
- [ ] `templates/patients/patient_form.html` – form tạo/sửa chung
- [ ] `templates/patients/patient_detail.html` – chi tiết + lịch sử khám
- [ ] `templates/patients/patient_confirm_delete.html` – trang xác nhận xóa
- [ ] Test thêm bệnh nhân hợp lệ ✅
- [ ] Test validation SĐT sai ✅
- [ ] Test tìm kiếm theo tên + SĐT ✅
- [ ] Test sửa bệnh nhân ✅
- [ ] Test xóa bệnh nhân ✅
