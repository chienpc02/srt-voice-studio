# SRT Voice Studio

Chuyển file phụ đề (.srt, .vtt) thành một file âm thanh. Có hai cách chọn giọng:

- **Nhân bản giọng của bạn** (XTTS-v2): tải lên hoặc ghi âm 6 đến 30 giây giọng mẫu, app đọc phụ đề bằng giọng đó. Chạy hoàn toàn trên máy, hỗ trợ tiếng Việt và 16 ngôn ngữ khác.
- **Giọng có sẵn** (Edge): nhẹ và nhanh, cần internet, không nhân bản giọng.

App có ba tab:

- **Đọc văn bản**: dán văn bản hoặc mở file .txt, văn bản dài tự chia thành các đoạn.
- **Đọc phụ đề**: đọc file SRT/VTT.
- **Thư viện giọng nói**: lưu, nghe thử, đổi tên, xóa các giọng đã nhân bản. Ở hai tab đọc, mục "Lưu giọng mẫu này vào thư viện" lưu nhanh giọng đang dùng. Giọng lưu trong thư mục `voices` (đã đưa vào `.gitignore` để không bị đẩy lên GitHub).

Hai cách ghép phụ đề: **theo mốc thời gian** (mỗi câu đúng thời điểm trong file, tự tăng tốc khi câu quá dài) hoặc **nối tiếp**.

## Cài đặt

Cần Python 3.10 đến 3.12 (coqui-tts chưa hỗ trợ bản mới hơn).

- Windows: bấm đúp `run.bat`
- macOS / Linux: `bash run.sh`

Lần chạy đầu sẽ cài thư viện (vài GB, gồm PyTorch) và tải mô hình XTTS-v2 khoảng 2 GB. Từ lần sau chạy ngay. Trình duyệt tự mở trang giao diện trên máy bạn.

## Tạo bản .exe (Windows)

Bấm đúp `build_exe.bat`. Script tự tạo môi trường, cài thư viện và build bằng PyInstaller. Kết quả nằm ở `dist\SRT-Voice-Studio\SRT-Voice-Studio.exe`; có thể nén cả thư mục này để chuyển sang máy khác (thư mục nặng vài GB vì có PyTorch). Mô hình XTTS không nằm trong `.exe`, app tải về lần chạy đầu. Build cần Python 3.10 đến 3.12 và mất 10 đến 30 phút.

## Gặp lỗi "PyTorch was not found"

Nguyên nhân thường gặp là Python quá mới (3.13 trở lên) nên PyTorch không cài được. Cài Python 3.11 từ python.org (tick "Add to PATH"), xóa thư mục `.venv`, rồi chạy lại `run.bat`. Bản `run.bat` mới tự kiểm tra và cài PyTorch.

## Gợi ý

- Giọng mẫu càng sạch (không nhạc nền, không vang) thì giọng nhân bản càng giống.
- Có GPU NVIDIA thì nhanh hơn nhiều. Chỉ có CPU vẫn chạy được nhưng mỗi câu mất vài giây.
- File kết quả nằm trong thư mục `output`.
- Chạy kiểm thử phần xử lý phụ đề: `pip install pytest` rồi `pytest tests`.

## Giấy phép và quyền dùng giọng

- Mô hình XTTS-v2 dùng giấy phép Coqui Public Model License, chỉ cho mục đích phi thương mại.
- Chỉ nhân bản giọng của chính bạn hoặc giọng có sự đồng ý của chủ giọng. App yêu cầu tick xác nhận trước khi chạy.
