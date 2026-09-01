# 📘 GUIDE A — Thành viên A: Hệ thống Đăng nhập & Kiểm tra Trùng lịch

> **Phụ trách:** `accounts/` app (toàn bộ) + `appointments/` app (phần logic)  
> **Framework:** Django 5.x | **Thời gian ước tính:** ~5.5 giờ

---

## TỔNG QUAN

| Nhiệm vụ | File | Độ khó |
|---|---|---|
| Đăng nhập / Đăng xuất | `accounts/views.py` | ⭐⭐ |
| Decorator phân quyền | `accounts/decorators.py` | ⭐⭐⭐ |
| URL routing | `accounts/urls.py` | ⭐ |
| Trang login HTML | `templates/accounts/login.html` | ⭐⭐ |
| **Hàm kiểm tra trùng lịch** | `appointments/utils.py` | ⭐⭐⭐⭐ |
| View tạo/sửa lịch | `appointments/views.py` | ⭐⭐⭐ |
| Form validation | `appointments/forms.py` | ⭐⭐ |

### Thứ tự thực hiện
```
Bước 1: accounts/urls.py
Bước 2: accounts/views.py (login + logout)
Bước 3: accounts/decorators.py
Bước 4: templates/accounts/login.html
Bước 5: appointments/forms.py
Bước 6: appointments/utils.py  <- QUAN TRỌNG NHẤT
Bước 7: appointments/views.py (create + update)
Bước 8: Test toàn bộ
```

---

## PHẦN 1: accounts App

### 1.1. accounts/views.py

```python
# accounts/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages


def login_view(request):
    """
    Xử lý đăng nhập.
    GET  -> hiển thị form trống
    POST -> kiểm tra tài khoản, nếu đúng thì đăng nhập
    """
    # Đã đăng nhập rồi -> về dashboard luôn
    if request.user.is_authenticated:
        return redirect('dashboard:index')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        # authenticate() kiểm tra username + password đã hash trong DB
        # KHÔNG BAO GIỜ dùng User.objects.get(password=...) vì password đã hash
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)   # Tạo session
            messages.success(request, f'Chào mừng {user.get_full_name() or user.username}!')
            # Nếu có ?next=... thì redirect về trang đó
            next_url = request.GET.get('next') or 'dashboard:index'
            return redirect(next_url)
        else:
            messages.error(request, 'Tên đăng nhập hoặc mật khẩu không đúng!')

    return render(request, 'accounts/login.html')


@login_required
def logout_view(request):
    """Đăng xuất - chỉ chấp nhận POST để tránh bị logout vô tình."""
    if request.method == 'POST':
        logout(request)
        messages.info(request, 'Bạn đã đăng xuất thành công.')
    return redirect('accounts:login')
```

> **Tại sao dùng `authenticate()`?**  
> `authenticate()` so sánh password đã hash, kiểm tra tài khoản `is_active`, và chạy qua tất cả auth backends. Tuyệt đối không tự query `User.objects.get(password=...)`.

---

### 1.2. accounts/decorators.py

```python
# accounts/decorators.py
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def role_required(*roles):
    """
    Decorator kiểm tra role của user.

    Cách dùng:
        @role_required('admin')            # Chỉ admin
        @role_required('admin', 'staff')   # Admin HOẶC staff
    """
    def decorator(view_func):
        @wraps(view_func)  # Giữ metadata của view gốc (quan trọng cho URL reverse)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.warning(request, 'Vui lòng đăng nhập để tiếp tục.')
                return redirect('accounts:login')

            # Superuser có toàn quyền
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            # Lấy role từ profile
            if hasattr(request.user, 'profile'):
                if request.user.profile.role in roles:
                    return view_func(request, *args, **kwargs)

            # Không có quyền
            messages.error(request, f'Bạn không có quyền truy cập. (Cần: {", ".join(roles)})')
            return redirect('dashboard:index')

        return wrapper
    return decorator
```

> **Tại sao dùng `@wraps`?**  
> Không có `@wraps`, Django bị nhầm khi dùng `reverse()` hoặc debug vì function tên bị thay đổi.

---

### 1.3. accounts/urls.py

```python
# accounts/urls.py
from django.urls import path
from . import views

app_name = 'accounts'  # Namespace: gọi bằng 'accounts:login', 'accounts:logout'

urlpatterns = [
    path('login/', views.login_view, name='login'),    # /accounts/login/
    path('logout/', views.logout_view, name='logout'), # /accounts/logout/
]
```

### 1.4. Thêm vào cuối clinicms/settings.py

```python
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
```

---

### 1.5. templates/accounts/login.html

Tạo thư mục `templates/accounts/` trước, rồi tạo file `login.html`:

```html
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Đăng nhập – ClinicMS</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css" rel="stylesheet">
    <style>
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .login-card { border: none; border-radius: 16px; box-shadow: 0 20px 60px rgba(0,0,0,.3); max-width: 420px; width: 100%; }
        .login-header { background: linear-gradient(135deg, #0d6efd, #0a58ca); border-radius: 16px 16px 0 0; padding: 2rem; text-align: center; }
    </style>
</head>
<body>
<div class="login-card card">
    <div class="login-header text-white">
        <i class="bi bi-hospital fs-1"></i>
        <h4 class="fw-bold mt-2 mb-0">ClinicMS</h4>
        <small class="opacity-75">Hệ thống Quản lý Phòng khám</small>
    </div>
    <div class="card-body p-4">
        {% if messages %}
            {% for message in messages %}
                <div class="alert alert-{{ message.tags }} alert-dismissible fade show">
                    {{ message }}
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                </div>
            {% endfor %}
        {% endif %}

        <h5 class="text-center text-muted mb-4">Đăng nhập tài khoản</h5>

        <form method="post" action="{% url 'accounts:login' %}">
            {% csrf_token %}
            <div class="mb-3">
                <label class="form-label fw-semibold">
                    <i class="bi bi-person me-1"></i>Tên đăng nhập
                </label>
                <input type="text" class="form-control form-control-lg"
                       name="username" placeholder="Nhập tên đăng nhập..."
                       value="{{ request.POST.username }}" required>
            </div>
            <div class="mb-4">
                <label class="form-label fw-semibold">
                    <i class="bi bi-lock me-1"></i>Mật khẩu
                </label>
                <div class="input-group">
                    <input type="password" class="form-control form-control-lg"
                           id="password" name="password"
                           placeholder="Nhập mật khẩu..." required>
                    <button class="btn btn-outline-secondary" type="button" id="togglePwd">
                        <i class="bi bi-eye" id="eyeIcon"></i>
                    </button>
                </div>
            </div>
            <div class="d-grid">
                <button type="submit" class="btn btn-primary btn-lg">
                    <i class="bi bi-box-arrow-in-right me-2"></i>Đăng nhập
                </button>
            </div>
        </form>
    </div>
    <div class="card-footer text-center text-muted small py-3">
        <i class="bi bi-shield-lock me-1"></i>Liên hệ admin nếu quên mật khẩu
    </div>
</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script>
    document.getElementById('togglePwd').onclick = function() {
        var p = document.getElementById('password');
        var i = document.getElementById('eyeIcon');
        p.type = p.type === 'password' ? 'text' : 'password';
        i.className = p.type === 'password' ? 'bi bi-eye' : 'bi bi-eye-slash';
    };
</script>
</body>
</html>
```

> **Tại sao KHÔNG extend `base.html`?**  
> `base.html` có sidebar cần `user.profile` nhưng user chưa đăng nhập sẽ gây lỗi. Trang login dùng layout riêng, độc lập.

---

## PHẦN 2: appointments App – Logic

### 2.1. appointments/forms.py

```python
# appointments/forms.py
from django import forms
from .models import Appointment


class AppointmentForm(forms.ModelForm):
    """Form tạo/sửa lịch hẹn, tự động tạo từ model Appointment."""

    class Meta:
        model = Appointment
        fields = ['patient', 'doctor', 'date', 'start_time', 'end_time', 'note']
        widgets = {
            'date':       forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'end_time':   forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'patient':    forms.Select(attrs={'class': 'form-select'}),
            'doctor':     forms.Select(attrs={'class': 'form-select'}),
            'note':       forms.Textarea(attrs={'class': 'form-control', 'rows': 3,
                                                'placeholder': 'Ghi chú (không bắt buộc)...'}),
        }

    def clean(self):
        """Kiểm tra giờ kết thúc phải sau giờ bắt đầu."""
        cleaned_data = super().clean()
        start = cleaned_data.get('start_time')
        end   = cleaned_data.get('end_time')
        if start and end and end <= start:
            raise forms.ValidationError(
                f'Giờ kết thúc ({end.strftime("%H:%M")}) phải sau giờ bắt đầu ({start.strftime("%H:%M")}).'
            )
        return cleaned_data
```

---

### 2.2. appointments/utils.py — HÀM KIỂM TRA TRÙNG LỊCH ⚡

**Hiểu logic toán học trước khi code:**

```
Lịch cũ (A):  [====A_start=========A_end====]
Lịch mới (B):       [====B_start=========B_end====]

Hai khoảng TRÙNG khi: B_start < A_end  VÀ  B_end > A_start
Hai khoảng KHÔNG TRÙNG khi: B_end <= A_start  HOẶC  B_start >= A_end
```

```python
# appointments/utils.py
from .models import Appointment


def check_appointment_conflict(doctor, date, start_time, end_time, exclude_id=None):
    """
    Kiểm tra lịch hẹn mới có trùng giờ với lịch hiện có không.

    Logic toán học:
        [A_start, A_end] và [B_start, B_end] TRÙNG khi:
        A_start < B_end  VÀ  A_end > B_start

        Django ORM dịch thành:
        start_time__lt = end_time   (lịch cũ bắt đầu TRƯỚC khi lịch mới kết thúc)
        end_time__gt   = start_time (lịch cũ kết thúc SAU khi lịch mới bắt đầu)

    Tham số:
        doctor      : đối tượng Doctor
        date        : ngày khám (date object)
        start_time  : giờ bắt đầu (time object)
        end_time    : giờ kết thúc (time object)
        exclude_id  : ID lịch cần bỏ qua khi CHỈNH SỬA (không conflict với chính nó)

    Trả về:
        None        -> không trùng, an toàn để tạo
        Appointment -> lịch hẹn bị trùng đầu tiên
    """
    conflicts = Appointment.objects.filter(
        doctor=doctor,
        date=date,
        # Chỉ kiểm tra với lịch chưa hủy (whitelist an toàn hơn blacklist)
        status__in=['pending', 'confirmed', 'checked_in'],
        # Điều kiện trùng thời gian
        start_time__lt=end_time,   # lịch cũ bắt đầu TRƯỚC khi lịch mới kết thúc
        end_time__gt=start_time,   # lịch cũ kết thúc SAU khi lịch mới bắt đầu
    )

    # Khi CHỈNH SỬA: loại trừ chính lịch đang sửa để không conflict với bản thân
    if exclude_id is not None:
        conflicts = conflicts.exclude(id=exclude_id)

    return conflicts.first()  # None nếu không có lịch trùng


def get_doctor_schedule(doctor, date):
    """Lấy lịch khám của bác sĩ trong một ngày (Thành viên C dùng)."""
    return Appointment.objects.filter(
        doctor=doctor,
        date=date,
    ).exclude(status='cancelled').order_by('start_time')
```

> **Tại sao dùng whitelist `status__in=[...]` thay vì `status != 'cancelled'`?**  
> Nếu sau này thêm status mới, whitelist tự bỏ qua, blacklist sẽ tính trùng với status lạ đó — gây bug tiềm ẩn.

---

### 2.3. appointments/views.py

```python
# appointments/views.py — phần Thành viên A viết
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.decorators import role_required
from .models import Appointment
from .forms import AppointmentForm
from .utils import check_appointment_conflict


@login_required
@role_required('admin', 'staff')   # Chỉ admin và nhân viên tạo được lịch
def appointment_create(request):
    """Tạo lịch hẹn mới."""
    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        if form.is_valid():
            doctor     = form.cleaned_data['doctor']
            date       = form.cleaned_data['date']
            start_time = form.cleaned_data['start_time']
            end_time   = form.cleaned_data['end_time']

            # === KIỂM TRA TRÙNG LỊCH ===
            conflict = check_appointment_conflict(doctor, date, start_time, end_time)

            if conflict:
                # Có trùng -> thông báo rõ ràng, KHÔNG lưu
                messages.error(
                    request,
                    f'Trùng lịch! Bác sĩ {doctor} đã có lịch '
                    f'{conflict.start_time.strftime("%H:%M")}–{conflict.end_time.strftime("%H:%M")} '
                    f'với bệnh nhân {conflict.patient}.'
                )
            else:
                # Không trùng -> lưu vào database
                appt = form.save()
                messages.success(request, f'Đã tạo lịch hẹn cho {appt.patient} thành công!')
                return redirect('appointments:list')
    else:
        form = AppointmentForm()

    return render(request, 'appointments/appointment_form.html', {
        'form': form, 'action': 'Tạo mới', 'title': 'Tạo lịch hẹn mới'
    })


@login_required
@role_required('admin', 'staff')
def appointment_update(request, pk):
    """Chỉnh sửa lịch hẹn. get_object_or_404 tự trả 404 nếu không tìm thấy."""
    appointment = get_object_or_404(Appointment, pk=pk)

    if request.method == 'POST':
        form = AppointmentForm(request.POST, instance=appointment)  # instance -> UPDATE
        if form.is_valid():
            doctor     = form.cleaned_data['doctor']
            date       = form.cleaned_data['date']
            start_time = form.cleaned_data['start_time']
            end_time   = form.cleaned_data['end_time']

            # === KIỂM TRA TRÙNG LỊCH, LOẠI TRỪ CHÍNH NÓ ===
            # exclude_id quan trọng: nếu không có, lịch sẽ conflict với chính nó!
            conflict = check_appointment_conflict(doctor, date, start_time, end_time,
                                                  exclude_id=appointment.pk)

            if conflict:
                messages.error(
                    request,
                    f'Trùng lịch! Bác sĩ {doctor} đã có lịch '
                    f'{conflict.start_time.strftime("%H:%M")}–{conflict.end_time.strftime("%H:%M")}.'
                )
            else:
                form.save()
                messages.success(request, 'Đã cập nhật lịch hẹn thành công!')
                return redirect('appointments:list')
    else:
        form = AppointmentForm(instance=appointment)  # Điền sẵn dữ liệu hiện tại

    return render(request, 'appointments/appointment_form.html', {
        'form': form, 'appointment': appointment,
        'action': 'Cập nhật', 'title': f'Chỉnh sửa lịch hẹn #{pk}'
    })
```

> **Tại sao cần `exclude_id` khi update?**  
> Khi sửa lịch ID=5 (9:00–10:00), nếu không loại trừ, hàm tìm thấy chính lịch ID=5 trong DB và báo trùng — dù không đổi giờ. `exclude_id=appointment.pk` giải quyết vấn đề này.

---

## PHẦN 3: Tích hợp với Thành viên Khác

**Thành viên C** dùng utils của bạn:
```python
from appointments.utils import check_appointment_conflict, get_doctor_schedule
```

**Thành viên D** dùng decorator của bạn:
```python
from accounts.decorators import role_required

@login_required
@role_required('admin')
def dashboard_index(request):
    ...
```

---

## PHẦN 4: Test Nhanh

### Tạo tài khoản test (chạy trong Django shell)
```powershell
python manage.py shell
```
```python
from django.contrib.auth.models import User

# Admin
u = User.objects.create_user('admin_test', password='Admin@123', first_name='Admin')
u.profile.role = 'admin'; u.profile.save()

# Doctor
d = User.objects.create_user('doctor_test', password='Doctor@123', first_name='Bác sĩ')
d.profile.role = 'doctor'; d.profile.save()

print("Xong!"); exit()
```

| Test | Thao tác | Kết quả mong đợi |
|---|---|---|
| 1 | Login đúng | Chuyển về dashboard, có lời chào |
| 2 | Login sai | Hiện "Tên đăng nhập hoặc mật khẩu không đúng!" |
| 3 | doctor_test vào /appointments/create/ | Bị redirect về dashboard + thông báo không có quyền |
| 4 | Tạo lịch 09:00–10:00 | Thành công |
| 5 | Tạo thêm lịch 09:30–10:30 (cùng bác sĩ, cùng ngày) | Báo lỗi trùng lịch |
| 6 | Tạo lịch 10:00–11:00 (sau lịch cũ) | Thành công (không trùng) |
| 7 | Sửa lịch, chỉ đổi ghi chú | Lưu thành công, không báo trùng với chính nó |

---

## PHẦN 5: Câu hỏi Giảng viên có thể Hỏi

**Q1: Authentication và Authorization khác nhau thế nào?**
> Authentication (Xác thực): Kiểm tra BẠN LÀ AI — Django dùng `authenticate()` và `login()`.  
> Authorization (Phân quyền): Kiểm tra BẠN ĐƯỢC LÀM GÌ — project này dùng `role_required()` decorator.

**Q2: `@login_required` và `@role_required` khác gì?**
> `@login_required`: chỉ kiểm tra đã đăng nhập chưa.  
> `@role_required('admin')`: kiểm tra đã đăng nhập VÀ có đúng role.

**Q3: Giải thích logic `check_appointment_conflict`. Tại sao dùng `start_time__lt=end_time`?**
> Hai khoảng [A_start, A_end] và [B_start, B_end] trùng khi: A_start < B_end VÀ A_end > B_start.  
> `start_time__lt=end_time`: lịch cũ bắt đầu trước khi lịch mới kết thúc.  
> `end_time__gt=start_time`: lịch cũ kết thúc sau khi lịch mới bắt đầu.

**Q4: Tại sao logout dùng POST thay vì GET?**
> Bảo mật CSRF. Nếu dùng GET, kẻ tấn công có thể nhúng link `<img src="/logout/">` và logout người dùng. POST yêu cầu CSRF token.

**Q5: Signal `post_save` trong `accounts/models.py` hoạt động thế nào?**
> Signal phát ra sau khi bất kỳ model nào được lưu. Kết nối với `sender=User`, tự động tạo `UserProfile` mỗi khi User mới được tạo — hoạt động với mọi cách tạo User.

**Q6: `exclude_id` giải quyết vấn đề gì khi update?**
> Khi sửa lịch ID=5, không có exclude, hàm tìm thấy chính lịch ID=5 và báo lỗi trùng dù không đổi giờ. `exclude_id=5` bảo Django bỏ qua lịch này.

**Q7: Điều gì xảy ra nếu quên `{% csrf_token %}` trong form?**
> Django trả về 403 Forbidden "CSRF verification failed". Bắt buộc với mọi form POST.

---

## PHẦN 6: Lỗi Thường Gặp

| Lỗi | Nguyên nhân | Cách sửa |
|---|---|---|
| `User has no profile` | Signal chưa chạy | `UserProfile.objects.create(user=user)` trong shell |
| `NoReverseMatch: dashboard:index` | Thiếu `app_name = 'dashboard'` | Thêm vào `dashboard/urls.py` |
| `403 CSRF verification failed` | Quên `{% csrf_token %}` | Thêm vào mọi form POST |
| Lịch không báo trùng | Quên gọi `check_appointment_conflict` | Kiểm tra lại view |
| `no such table` | Chưa migrate | `python manage.py makemigrations && python manage.py migrate` |
| `@role_required` không chặn | Quên truyền tham số | Phải viết `@role_required('admin')`, không phải `@role_required` |
| Form luôn báo lỗi giờ | Định dạng time không khớp | Thêm `TIME_INPUT_FORMATS = ['%H:%M']` vào settings.py |

---

## ✅ Checklist Hoàn thành

- [ ] `accounts/views.py` – login_view và logout_view
- [ ] `accounts/decorators.py` – role_required decorator
- [ ] `accounts/urls.py` – routes đăng nhập/đăng xuất
- [ ] `clinicms/settings.py` – thêm LOGIN_URL
- [ ] `templates/accounts/login.html` – giao diện Bootstrap 5
- [ ] `appointments/forms.py` – AppointmentForm với validation
- [ ] `appointments/utils.py` – check_appointment_conflict
- [ ] `appointments/views.py` – appointment_create và appointment_update
- [ ] Test đăng nhập đúng/sai ✅
- [ ] Test phân quyền role ✅
- [ ] Test tạo lịch hợp lệ ✅
- [ ] Test phát hiện trùng lịch ✅
- [ ] Test sửa lịch không conflict với chính nó ✅
