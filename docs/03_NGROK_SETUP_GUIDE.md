# Hướng dẫn thiết lập Ngrok cho AI Server (Môi trường Hybrid)

Tài liệu này hướng dẫn cách sử dụng **Ngrok** với tên miền tĩnh (Static Domain) để kết nối máy chủ ảo (Google Cloud VM) với AI Server đang chạy trên máy tính cá nhân (Localhost) của bạn.

## 1. Tại sao phải dùng Ngrok?
Trong mô hình kiến trúc Hybrid của đồ án:
- Frontend và Backend được deploy lên mạng thật (Google Cloud VM) với tên miền `duongquockiet.id.vn`.
- AI Server (FastAPI) vì yêu cầu cấu hình phần cứng (RAM/GPU) nên được chạy trực tiếp trên máy tính cá nhân của bạn ở cổng `8000`.

Để Backend trên mạng có thể "nhìn thấy" và gửi dữ liệu xuống AI Server trên máy tính của bạn, chúng ta cần một đường hầm an toàn vượt qua tường lửa của mạng nhà bạn. Ngrok chính là đường hầm đó.

## 2. Chuẩn bị tài khoản và Tên miền tĩnh
Ngrok hiện tại tặng miễn phí **1 tên miền tĩnh (Static Domain)** cho mỗi tài khoản, giúp bạn không bị đổi link mỗi khi tắt máy.

1. Truy cập [ngrok.com](https://ngrok.com/) và đăng nhập/đăng ký tài khoản.
2. Tại thanh menu bên trái, chọn **Domains**.
3. Bấm **Create Domain** (hoặc *Claim free static domain*). Ngrok sẽ cấp cho bạn một tên miền ngẫu nhiên (Ví dụ: `judiciary-suitably-perpetual.ngrok-free.dev`).
4. Tại thanh menu bên trái, chọn **Your Authtoken** và copy đoạn mã token của bạn.

## 3. Cài đặt Ngrok trên Windows
1. Truy cập trang Download của Ngrok, tải bản `.zip` dành cho Windows.
2. Giải nén file `.zip` ra, bạn sẽ nhận được 1 file tên là `ngrok.exe`.
3. Copy/Cắt file `ngrok.exe` này bỏ vào chung thư mục chứa code AI (thư mục `clinic-ai-chat`) cho tiện quản lý.

## 4. Cấu hình và Khởi chạy (Chỉ cần làm 1 lần)

Mở **Terminal (CMD hoặc PowerShell)** tại thư mục chứa file `ngrok.exe` và chạy lệnh sau để khai báo Token:
```bash
ngrok config add-authtoken <DÁN_TOKEN_CỦA_BẠN_VÀO_ĐÂY>
```
*(Bạn chỉ cần làm thao tác này 1 lần duy nhất trên máy tính của mình).*

## 5. Quy trình sử dụng hằng ngày (Khi bảo vệ đồ án/chạy test)

Mỗi khi bạn muốn bật hệ thống lên để sử dụng hoặc demo cho giáo viên, hãy làm theo đúng thứ tự 2 bước sau:

**Bước 1: Bật AI Server**
Mở Terminal tại thư mục `clinic-ai-chat` và gõ:
```bash
uvicorn app.main:app --reload --port 8000
```
*(Lúc này AI đang chạy ở `http://localhost:8000`)*

**Bước 2: Bật Ngrok để mở đường hầm**
Mở thêm 1 Terminal thứ 2 (cũng tại thư mục `clinic-ai-chat`), chạy lệnh:
```bash
ngrok http --url=judiciary-suitably-perpetual.ngrok-free.dev 8000
```
*(Lưu ý: Thay `judiciary-suitably-perpetual.ngrok-free.dev` bằng tên miền tĩnh mà bạn đã nhận ở mục 2)*.

Khi Terminal của Ngrok hiện chữ **Session Status: Online** màu xanh lá cây, mọi thứ đã hoàn tất! Bạn cứ treo 2 cửa sổ Terminal này và có thể lên thẳng trang web `duongquockiet.id.vn` để tận hưởng tính năng Chat AI.

## 6. Lưu ý về Cấu hình Backend
Backend trên Google Cloud đã được cấu hình sẵn biến môi trường để trỏ về tên miền Ngrok của bạn (thông qua file `deploy/docker-compose.yml`):
```yaml
APPLICATION_AI_SERVER_URL=https://judiciary-suitably-perpetual.ngrok-free.dev
```
Nếu sau này bạn đổi tài khoản Ngrok hoặc đổi tên miền khác, bạn chỉ cần vào file `deploy/docker-compose.yml` cập nhật lại link này, commit code lên Github và để Action tự động chạy là xong!
