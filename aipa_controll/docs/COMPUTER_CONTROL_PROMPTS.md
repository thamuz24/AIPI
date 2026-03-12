# AIPA Computer Control Prompt Catalog

Bạn có thể nhập prompt trực tiếp vào chat. Để tránh nhầm với câu hỏi bình thường, nên thêm tiền tố:
- `máy tính:` hoặc `pc:` hoặc `lệnh:`

Ví dụ: `máy tính: mở chrome`

## 1) Ứng dụng
- `máy tính: mở chrome`
- `máy tính: mở edge`
- `máy tính: mở notepad`
- `máy tính: đóng chrome`
- `máy tính: tắt app edge`

## 2) Chuột
Hỗ trợ 2 kiểu tọa độ:
- Pixel: `x,y` (ví dụ `1200,700`)
- Lưới: `a1`, `b3`... (tính theo `AIPA_CONTROL_GRID_ROWS` và `AIPA_CONTROL_GRID_COLS`, mặc định 6x6)

Ví dụ:
- `máy tính: click a1`
- `máy tính: click 1200,700`
- `máy tính: click phải b2`
- `máy tính: kéo chuột a1 -> c3`
- `máy tính: kéo chuột 100,200 -> 400,500`
- `máy tính: cuộn lên`
- `máy tính: cuộn xuống`

## 3) Bàn phím
- `máy tính: gõ chữ xin chào`
- `máy tính: nhấn phím ctrl+c`
- `máy tính: nhấn phím alt+tab`
- `máy tính: phím tắt ctrl+l`

## 4) File/Thư mục (mặc định trong Desktop)
Các thao tác file/thư mục mặc định bị giới hạn trong Desktop để an toàn.

- Liệt kê Desktop:
  - `máy tính: liệt kê desktop`
  - `máy tính: xem desktop`
- Mở/đọc file hoặc liệt kê thư mục:
  - `máy tính: mở file ghi_chu.txt`
  - `máy tính: xem thư mục MyFolder`
- Tạo/ghi file:
  - `máy tính: tạo file ghi_chu.txt`
  - `máy tính: ghi đè file ghi_chu.txt nội dung hôm nay`
  - `máy tính: ghi file ghi_chu.txt: nội dung bất kỳ` (có thể dùng `:` hoặc `|` để ngăn cách)
  - `máy tính: thêm vào file ghi_chu.txt dòng mới` (tự thêm xuống dòng)
- Tạo/xóa:
  - `máy tính: tạo thư mục test`
  - `máy tính: xóa file ghi_chu.txt`
  - `máy tính: xóa thư mục test`

## 5) Tiện ích
- `máy tính: thực hiện tác vụ: kiểm tra thời gian`
- `máy tính: chờ 1.5`
- `máy tính: mở web openai.com`

## 6) File dự án (control root)
Các prompt sau mở file trong thư mục service (`COMPUTER_CONTROL_ROOT`):
- `máy tính: mở file train`
- `máy tính: xem lịch sử hội thoại`
- `máy tính: liệt kê model`
- `máy tính: hướng dẫn điều khiển`

## 7) Tuỳ biến danh sách lệnh
Sửa file:
- `model/keyword_train/computer_control_train.txt`

Định dạng:
- `trigger => ACTION|arg1|arg2||ACTION2|...`

Placeholder hỗ trợ:
- `{REST}`: phần còn lại sau trigger
- `{NOW}`: thời gian hiện tại
- `{NL}`: xuống dòng
