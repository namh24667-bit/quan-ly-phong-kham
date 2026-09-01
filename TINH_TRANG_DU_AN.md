# 📋 TÌNH TRẠNG DỰ ÁN — ClinicMS

> **Cách dùng:** Khi chuyển sang tài khoản AI mới, paste toàn bộ file này vào đầu cuộc trò chuyện và nói: *"Đây là tình trạng dự án của tôi, hãy tiếp tục giúp tôi"*

---

## 1. THÔNG TIN DỰ ÁN

| | |
|---|---|
| **Tên** | ClinicMS — Hệ thống Quản lý Phòng khám |
| **Framework** | Django 6.1, Python 3.12.8 |
| **Database** | SQLite (file `db.sqlite3`) |
| **UI** | Bootstrap 5 (CDN) + Bootstrap Icons |
| **Thư mục** | `d:\phong_kham\` |
| **Chạy server** | `cd d:\phong_kham && python manage.py runserver` |
| **URL** | http://127.0.0.1:8000 |

---

## 2. CẤU TRÚC PROJECT (đã build xong)

```
d:\phong_kham\
├── clinicms/           ← settings.py, urls.py
├── accounts/           ← login/logout, UserProfile, role_required decorator
├── patients/           ← CRUD bệnh nhân
├── doctors/            ← CRUD bác sĩ
├── appointments/       ← CRUD lịch hẹn + đổi trạng thái
├── dashboard/          ← Thống kê tổng quan
├── templates/          ← Tất cả HTML (base.html + từng app)
├── static/css/         ← (rỗng, dùng Bootstrap CDN)
├── guides/             ← Tài liệu học cho từng thành viên
├── db.sqlite3          ← Database đã có dữ liệu mẫu
├── manage.py
└── seed_data.py        ← Script tạo dữ liệu mẫu
```

---

## 3. CÁC MODEL

```python
# accounts/models.py
UserProfile: user(1-1 User), role(admin/doctor/staff), phone

# patients/models.py
Patient: full_name, date_of_birth, gender(M/F/O), phone, address, created_at

# doctors/models.py
Doctor: user(1-1 User nullable), full_name, specialty, phone, is_active

# appointments/models.py
Appointment: patient(FK), doctor(FK), date, start_time, end_time,
             status(pending/confirmed/checked_in/done/cancelled), note, created_at
MedicalRecord: appointment(1-1), symptoms, diagnosis, treatment, notes
```

---

## 4. TÀI KHOẢN MẪU (đã tạo)

| Username | Mật khẩu | Role |
|---|---|---|
| admin | admin123 | Quản trị viên |
| nhanvien | nhanvien123 | Nhân viên |
| bacsi_an | bacsi123 | Bác sĩ |
| bacsi_binh | bacsi123 | Bác sĩ |

---

## 5. LOGIC QUAN TRỌNG

### Kiểm tra trùng lịch (`appointments/utils.py`)
```python
def check_appointment_conflict(doctor, date, start_time, end_time, exclude_id=None):
    # Hai khoảng [A,B] và [C,D] trùng khi: A < D và B > C
    # exclude_id: bỏ qua khi CHỈNH SỬA lịch (tránh conflict với chính nó)
```

### Phân quyền (`accounts/decorators.py`)
```python
@role_required('admin')           # Chỉ admin
@role_required('admin', 'staff')  # Admin hoặc staff
```

### Luồng trạng thái lịch hẹn
```
pending → confirmed → checked_in → done
pending/confirmed → cancelled (có thể hủy)
```

---

## 6. ĐÃ HOÀN THÀNH ✅

- [x] Cài Django, khởi tạo project
- [x] Tạo 5 apps: accounts, patients, doctors, appointments, dashboard
- [x] Viết toàn bộ models + migrations
- [x] Viết toàn bộ views (CRUD + logic nghiệp vụ)
- [x] Viết toàn bộ URL routing
- [x] Viết toàn bộ templates HTML (Bootstrap 5)
- [x] Base template với sidebar có phân quyền
- [x] Trang login riêng (không dùng base.html)
- [x] Dashboard với 4 stat cards + bảng lịch hôm nay + lịch 7 ngày tới
- [x] CRUD Bệnh nhân (tìm kiếm Q object + phân trang Paginator)
- [x] CRUD Bác sĩ (không xóa được nếu còn lịch active)
- [x] CRUD Lịch hẹn (kiểm tra trùng giờ)
- [x] Đổi trạng thái lịch hẹn (confirm/checkin/done/cancel)
- [x] Migrate database + seed dữ liệu mẫu
- [x] Server chạy OK, `python manage.py check` = 0 lỗi
- [x] Tạo 4 file guide học cho từng thành viên (trong `guides/`)

---

## 7. CÒN LẠI / CÓ THỂ CẦN

- [ ] Trang báo cáo / in lịch hẹn (nếu yêu cầu)
- [ ] Admin site Django (chạy /admin/ cần tạo superuser)
- [ ] Viết báo cáo đồ án (Word/PDF)
- [ ] Tạo slide thuyết trình
- [ ] Quay video demo

### Tạo superuser (nếu cần vào /admin/):
```powershell
cd d:\phong_kham
python manage.py createsuperuser
```

---

## 8. THÔNG TIN NHÓM

- 4 thành viên, trình độ cơ bản, lần đầu dùng Django
- Đây là **đồ án nhóm môn học** (BaiTapNhom-Tuan9BC.pdf, đề số 4)
- Thời gian: 2 tuần
- Yêu cầu: phân quyền 3 role, quản lý bệnh nhân, quản lý bác sĩ
- Nộp: mã nguồn + báo cáo + slide + video demo
- **Mỗi thành viên phải giải thích được code của mình** khi bảo vệ

---

## 9. LỆNH HAY DÙNG

```powershell
cd d:\phong_kham

# Chạy server
python manage.py runserver

# Tạo migration khi đổi model
python manage.py makemigrations
python manage.py migrate

# Tạo dữ liệu mẫu lại
$env:PYTHONIOENCODING='utf-8'; python seed_data.py

# Chạy tests
python manage.py test appointments

# Mở Django shell
python manage.py shell
```
