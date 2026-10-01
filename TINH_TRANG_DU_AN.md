# Tình trạng dự án ClinicMS

## Tổng quan

ClinicMS là ứng dụng Django quản lý phòng khám với giao diện tiếng Việt. Hệ thống đã hoàn thiện các luồng nghiệp vụ cốt lõi, phân quyền theo vai trò, giao diện responsive, chức năng tra cứu dữ liệu và bản in chuyên nghiệp cho chứng từ y tế.

## Các app hiện tại

- `accounts`: đăng nhập, đăng xuất, Profile và phân quyền theo vai trò.
- `patients`: quản lý thông tin bệnh nhân và ngừng hoạt động bằng soft delete.
- `doctors`: quản lý bác sĩ và lịch làm việc `DoctorSchedule`.
- `appointments`: quản lý lịch khám, trạng thái lịch và `MedicalRecord`.
- `billing`: quản lý thuốc, `Prescription`, dịch vụ và `Invoice`.
- `dashboard`: hiển thị số liệu và lịch khám theo từng vai trò.

## Chức năng đã hoàn thành

### Dashboard và giao diện

- Dashboard riêng cho Admin, Staff và Doctor; dữ liệu của Doctor chỉ giới hạn trong phạm vi phụ trách.
- Giao diện quản trị phòng khám thống nhất, hỗ trợ desktop, tablet và mobile.
- Sidebar thu gọn thành menu đóng/mở trên màn hình nhỏ; topbar, card, form, bảng và nhóm nút thích ứng theo kích thước màn hình.
- Hiệu ứng chuyển động nhẹ, đồng thời tôn trọng thiết lập giảm chuyển động của hệ điều hành.
- Bản in A4 chuyên nghiệp cho hóa đơn và đơn thuốc; khi in chỉ giữ lại nội dung chứng từ cần thiết.

### Quản lý và tra cứu dữ liệu

- Quản lý bệnh nhân, xem chi tiết và lịch sử khám; bệnh nhân được ngừng hoạt động bằng soft delete để bảo toàn dữ liệu liên quan.
- Quản lý bác sĩ và lịch làm việc; bác sĩ được ngừng hoạt động thay vì xóa dữ liệu nghiệp vụ cũ.
- Danh sách Patient, Doctor, Appointment và Invoice có tìm kiếm và phân trang.
- Appointment hỗ trợ lọc theo trạng thái và ngày khám; Invoice hỗ trợ lọc theo trạng thái thanh toán.
- Các tham số tìm kiếm, lọc được giữ lại khi chuyển trang.

### Nghiệp vụ khám và thanh toán

- Kiểm tra lịch hẹn trong tương lai, lịch làm việc đang hoạt động và xung đột giờ khám của bác sĩ.
- Workflow xác nhận, check-in, hủy và hoàn thành `Appointment` theo đúng trạng thái hợp lệ.
- Doctor tạo và cập nhật `MedicalRecord`, kê nhiều dòng `Prescription`, sau đó hoàn thành lịch khám thuộc phạm vi của mình.
- Khi tạo `MedicalRecord`, hệ thống tạo `Invoice` ở trạng thái Pending; Admin/Staff có thể bổ sung dịch vụ và đánh dấu Paid sau khi lịch khám hoàn thành.
- `MedicalRecord` và `Prescription` bị khóa sau khi Appointment hoàn thành; Invoice đã Paid bị khóa chỉnh sửa và tính lại tổng tiền.
- Hỗ trợ in hóa đơn từ trang chi tiết Invoice và in đơn thuốc từ trang chi tiết Appointment khi đã có đơn thuốc.

## Workflow chính

Appointment:

```text
pending -> confirmed -> checked_in -> MedicalRecord -> done
pending/confirmed -> cancelled
```

Appointment chỉ được chuyển từ `checked_in` sang `done` sau khi có `MedicalRecord`.

Billing:

```text
Tạo MedicalRecord -> Invoice Pending
Appointment done -> Admin/Staff hoàn thiện dịch vụ -> Invoice Paid
```

## Phân quyền

- **Admin:** quản lý bệnh nhân, bác sĩ, lịch làm việc, lịch khám, hồ sơ khám và hóa đơn; có quyền ngừng hoạt động bệnh nhân và bác sĩ.
- **Staff:** quản lý tiếp nhận bệnh nhân, lịch bác sĩ, xác nhận/check-in/hủy lịch và hoàn thiện hóa đơn; không chỉnh sửa hồ sơ khám.
- **Doctor:** chỉ xem lịch, bệnh nhân và hóa đơn liên quan đến mình; tạo/sửa hồ sơ khám và đơn thuốc trong workflow cho phép.
- **Superuser:** được truy cập các chức năng nghiệp vụ như quyền quản trị.
- Doctor đã ngừng hoạt động bị chặn khỏi các chức năng dành cho Doctor, kể cả phiên đăng nhập cũ.

## Database, cấu hình và dữ liệu demo

- Môi trường local sử dụng SQLite qua file `db.sqlite3`.
- Cấu hình nhạy cảm và cấu hình môi trường được đọc từ `.env`; file `.env.example` khai báo `SECRET_KEY`, `DEBUG` và `ALLOWED_HOSTS`.
- `SECRET_KEY` là bắt buộc; `ALLOWED_HOSTS` nhận danh sách host cách nhau bằng dấu phẩy.
- `python seed_data.py` tạo dữ liệu demo bằng ORM và có thể chạy lại mà không nhân bản hàng loạt dữ liệu mẫu.
- Dữ liệu demo gồm tài khoản theo vai trò, bệnh nhân, bác sĩ, lịch làm việc, lịch khám, hồ sơ khám, đơn thuốc, dịch vụ và hóa đơn mẫu.

## Kiểm thử

Chạy bộ kiểm tra bằng:

```powershell
python manage.py check
python manage.py test
python manage.py makemigrations --check --dry-run
```

Project hiện có 133 automated test, bao phủ phân quyền, dashboard theo vai trò, workflow Appointment, validation lịch làm việc và trùng lịch, Patient soft delete, Doctor inactive, giới hạn dữ liệu của Doctor, khóa dữ liệu sau khám/thanh toán, tìm kiếm/lọc/phân trang và nút in hóa đơn/đơn thuốc.

## Có thể nâng cấp

- Báo cáo thống kê và biểu đồ theo khoảng thời gian.
- Xuất Excel/PDF nâng cao cho báo cáo nghiệp vụ.
- Thông báo, nhắc lịch khám và nhật ký thao tác.
- Chuyển sang database production, hoàn thiện quy trình deployment và sao lưu/khôi phục dữ liệu.
