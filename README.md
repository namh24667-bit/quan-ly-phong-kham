# ClinicMS - Quản lý phòng khám

Ứng dụng quản lý phòng khám bằng Django, hỗ trợ quản lý bệnh nhân, bác sĩ, lịch hẹn và dashboard.

## Yêu cầu

- Python 3.10+
- Git
- Virtual environment (khuyến nghị)

## Cài đặt

1. Clone repo:
   ```bash
   git clone <repo-url>
   cd quan-ly-phong-kham
   ```

2. Tạo môi trường ảo:
   ```bash
   python -m venv .venv
   ```

3. Kích hoạt môi trường ảo:

   Windows PowerShell:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

   Windows CMD:
   ```cmd
   .\.venv\Scripts\activate.bat
   ```

   macOS/Linux:
   ```bash
   source .venv/bin/activate
   ```

4. Cài đặt dependency:
   ```bash
   pip install -r requirements.txt
   ```

5. Chạy migration:
   ```bash
   python manage.py migrate
   ```

6. (Tùy chọn) Tạo dữ liệu mẫu:
   ```bash
   python seed_data.py
   ```

7. Tạo superuser nếu cần:
   ```bash
   python manage.py createsuperuser
   ```

## Chạy ứng dụng

```bash
python manage.py runserver
```

Mở trình duyệt tại:

```text
http://127.0.0.1:8000/
```

## Tài khoản mẫu

- Admin: `admin / admin123`
- Nhân viên: `nhanvien / nhanvien123`
- Bác sĩ An: `bacsi_an / bacsi123`

## Lưu ý

- File `db.sqlite3` và môi trường ảo đã được đưa vào `.gitignore` để tránh commit nhầm.
- Nếu cần chạy lại từ đầu, xóa file `db.sqlite3` local và chạy lại migration.
