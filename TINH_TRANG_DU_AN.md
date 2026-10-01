# Tình trạng dự án ClinicMS

## Tổng quan

ClinicMS là project Django quản lý phòng khám dành cho bài tập môn học. Source hiện tập trung vào nghiệp vụ cơ bản, phân quyền theo vai trò và kiểm tra workflow bằng automated test.

## Các app hiện tại

- `accounts`: đăng nhập, đăng xuất, Profile và role.
- `patients`: quản lý bệnh nhân và ngừng hoạt động bằng soft delete.
- `doctors`: quản lý bác sĩ và lịch làm việc.
- `appointments`: lịch khám, trạng thái lịch và hồ sơ khám.
- `billing`: thuốc, đơn thuốc, dịch vụ và hóa đơn.
- `dashboard`: số liệu và lịch khám tổng quan.

## Chức năng đã hoàn thành

- Phân quyền Admin, Staff và Doctor; superuser được phép truy cập như quản trị.
- Quản lý bệnh nhân, bác sĩ và DoctorSchedule.
- Kiểm tra lịch hẹn trong tương lai, giờ làm việc và trùng lịch bác sĩ.
- Workflow xác nhận, check-in, hủy và hoàn thành Appointment.
- MedicalRecord, Prescription, Medicine, Service và Invoice.
- Khóa chỉnh sửa hồ sơ đã hoàn thành và hóa đơn đã thanh toán.
- Dữ liệu demo có thể tạo bằng `python seed_data.py`.

## Workflow chính

```text
pending -> confirmed -> checked_in -> MedicalRecord -> done
pending/confirmed -> cancelled
```

Doctor chỉ hoàn thành Appointment của mình khi đã có MedicalRecord. Khi tạo MedicalRecord, hệ thống tạo Invoice Pending. Sau khi Appointment `done`, Admin/Staff có thể hoàn thiện dịch vụ và chuyển Invoice sang `Paid`; dữ liệu đã thanh toán bị khóa chỉnh sửa.

## Phân quyền

- **Admin:** thực hiện các thao tác quản lý và nghiệp vụ theo các view hiện tại.
- **Staff:** phụ trách bệnh nhân, tiếp nhận lịch khám, lịch làm việc và billing; không xử lý MedicalRecord.
- **Doctor:** chỉ truy cập Appointment, Patient, MedicalRecord và Invoice liên quan đến mình.
- Doctor inactive bị chặn khỏi chức năng dành cho Doctor.

## Database

Project đang dùng SQLite qua file local `db.sqlite3`. File database và `.env` được bỏ qua trong Git.

## Test

Chạy kiểm tra bằng:

```powershell
python manage.py check
python manage.py test
```

Test hiện bao phủ permission, workflow Appointment, Patient soft delete, DoctorSchedule, Doctor inactive, validation thời gian/trùng lịch và khóa Invoice Paid.

## Có thể nâng cấp

- Làm dashboard theo từng role rõ hơn.
- Cải thiện giao diện và trải nghiệm sử dụng.
- Bổ sung chức năng in hóa đơn, đơn thuốc hoặc báo cáo nếu môn học yêu cầu.
