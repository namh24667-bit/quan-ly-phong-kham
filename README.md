# ClinicMS - Quản lý phòng khám

ClinicMS là ứng dụng Django phục vụ bài tập quản lý phòng khám. Hệ thống gồm quản lý bệnh nhân, bác sĩ, lịch làm việc, lịch khám, hồ sơ khám, đơn thuốc, dịch vụ, hóa đơn, dashboard và phân quyền Admin/Staff/Doctor.

## Công nghệ

- Python 3.12 trở lên
- Django 6.1
- SQLite
- HTML, Bootstrap 5 và Bootstrap Icons

## Cài đặt trên Windows PowerShell

Yêu cầu máy đã cài Git, Python, `pip` và có thể tạo virtual environment.

```powershell
git clone https://github.com/namh24667-bit/quan-ly-phong-kham.git
cd quan-ly-phong-kham

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

Copy-Item .env.example .env
```

Mở `.env` và thay `SECRET_KEY` bằng một giá trị phù hợp cho môi trường local. Sau đó chạy:

```powershell
python manage.py migrate
python seed_data.py
python manage.py runserver
```

Truy cập `http://127.0.0.1:8000/`. File `.env` chứa cấu hình local và không được commit.

## Cấu hình `.env`

Project sử dụng đúng ba biến trong `.env.example`:

- `SECRET_KEY`: khóa bí mật của Django; bắt buộc phải có.
- `DEBUG`: dùng `True` khi phát triển local và `False` khi không cần chế độ debug.
- `ALLOWED_HOSTS`: danh sách host cách nhau bằng dấu phẩy, mặc định gồm `127.0.0.1,localhost`.

## Migration và dữ liệu demo

`python manage.py migrate` tạo hoặc cập nhật cấu trúc database SQLite.

`python seed_data.py` tạo dữ liệu demo bằng ORM và có thể chạy lại mà không nhân bản hàng loạt dữ liệu mẫu. Các tài khoản dưới đây chỉ dùng cho local/demo:

Lưu ý: `seed_data.py` chỉ dùng cho môi trường local/demo; khi chạy lại, script có thể đặt lại mật khẩu, đưa các tài khoản demo về trạng thái active và cập nhật lại dữ liệu demo cố định.

| Vai trò | Tài khoản | Mật khẩu |
|---|---|---|
| Admin | `admin` | `admin123` |
| Staff | `nhanvien` | `nhanvien123` |
| Doctor | `bacsi_an` | `bacsi123` |
| Doctor | `bacsi_binh` | `bacsi123` |

Seed còn tạo bệnh nhân, lịch làm việc Thứ Hai-Thứ Sáu, lịch khám theo ngày tương đối, một hồ sơ khám, đơn thuốc và hóa đơn Pending để demo.

## Phân quyền

- **Admin:** quản lý bệnh nhân, bác sĩ, lịch làm việc, lịch khám, hồ sơ khám và hóa đơn theo các workflow hiện tại.
- **Staff:** quản lý tiếp nhận bệnh nhân, lịch bác sĩ, các bước xác nhận/check-in/hủy lịch và hoàn thiện hóa đơn; không chỉnh hồ sơ khám.
- **Doctor:** chỉ xem lịch của mình, bệnh nhân liên quan, tạo/sửa hồ sơ khám và đơn thuốc khi Appointment đang `checked_in`, sau đó hoàn thành Appointment; chỉ xem hóa đơn thuộc lịch của mình.
- **Superuser:** được decorator cho phép truy cập như quyền quản trị.

Doctor đã ngừng hoạt động không thể tiếp tục dùng các chức năng dành cho Doctor.

## Workflow chính

Appointment:

```text
pending -> confirmed -> checked_in -> MedicalRecord -> done
pending/confirmed -> cancelled
```

Appointment chỉ được chuyển từ `checked_in` sang `done` sau khi đã có MedicalRecord. MedicalRecord và đơn thuốc bị khóa sau khi Appointment hoàn thành.

Billing:

```text
Tạo MedicalRecord -> Invoice Pending
Appointment done -> Staff/Admin hoàn thiện dịch vụ -> Paid
```

Chỉ Invoice của Appointment `done` mới được đánh dấu `Paid`. Invoice `Paid` không được sửa dịch vụ, tính lại tổng hoặc chỉnh hồ sơ/đơn thuốc liên quan.

## Kiểm tra project

```powershell
python manage.py check
python manage.py test
```

Project có automated test cho phân quyền, workflow, lịch làm việc, validation Appointment, khóa hồ sơ và tính toàn vẹn hóa đơn.
