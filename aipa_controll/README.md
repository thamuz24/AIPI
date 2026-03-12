# AIPA Controll Service

FastAPI service nhận `prompt` qua `POST /api/chat` và có thể thực thi một số lệnh điều khiển máy tính dựa trên file train.

## Chạy nhanh (Windows)
- Chạy: `run_aipa_all.bat`
- Service mặc định: `http://127.0.0.1:8001`

## Computer Control (Prompt -> Action)
Danh sách lệnh điều khiển mặc định nằm ở:
- `model/keyword_train/computer_control_train.txt`

Catalog prompt tham khảo:
- `docs/COMPUTER_CONTROL_PROMPTS.md`

Bạn cũng có thể hỏi ngay trong chat:
- `hướng dẫn điều khiển`
- `danh sách lệnh`

API hỗ trợ:
- `GET /api/computer-control/help`
- `GET /api/computer-control/rules`

Gợi ý: dùng tiền tố `máy tính:` hoặc `pc:` hoặc `lệnh:` để tránh nhầm với câu hỏi bình thường.

