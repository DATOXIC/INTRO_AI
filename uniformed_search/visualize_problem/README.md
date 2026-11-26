# Search Debugger

Trực quan hóa các thuật toán tìm kiếm cổ điển (môn Introduction to AI).
Hiện có:
- **Thuật toán:** BFS, DFS, UCS (đúng mã giả trên slide, có `REPLACE` nút trong frontier) và UCS tối ưu (`best_cost`, bỏ qua nút cũ khi pop).
- **Bài toán:** n-Puzzle (2×2, 3×3, 4×4) và Vacuum Robot với 2–6 phòng.
- **Chi phí hành động** (chỉ UCS dùng để chọn nút; BFS/DFS vẫn báo chi phí lời giải): n-Puzzle Lên/Xuống = 1, Trái/Phải = 2; Vacuum di chuyển = 2, hút bụi = 1.
- Chế độ **so sánh** hai thuật toán bất kỳ trên cùng bài toán và chế độ **dự đoán**.

Trang web: https://datoxic.github.io/INTRO_AI/

## Chạy cục bộ

```
python server.py          # có backend Python, mở http://127.0.0.1:8765
```

Hoặc thử đúng như bản đưa lên GitHub Pages (không cần server.py):

```
python build_site.py
python -m http.server 8766 -d dist
```

Chạy test:

```
python -m unittest discover -p "test_*.py"
```

Trang tự nhận biết: có `server.py` thì gọi API, không có thì chạy chính các file `.py`
trong trình duyệt bằng Pyodide (lần đầu mở mất vài giây để tải).

## Đưa lên GitHub Pages

1. Push lên nhánh `master`.
2. Trên GitHub: Settings → Pages → Source chọn **GitHub Actions** (làm một lần).
3. Mỗi lần push thay đổi trong thư mục này, workflow `.github/workflows/pages.yml`
   tự chạy test rồi deploy.

## Cấu trúc

| File | Vai trò |
| --- | --- |
| `search_core.py` | Bộ máy tìm kiếm chung (BFS/DFS/UCS, sinh trace từng dòng mã giả) |
| `bfs_core.py` | Bài n-Puzzle + danh sách preset |
| `vacuum_world.py` | Bài Vacuum Robot (2–6 phòng) |
| `api.py` | Các endpoint dưới dạng hàm thuần Python (dùng chung server và trình duyệt) |
| `server.py` | Server cục bộ, chỉ là lớp mỏng gọi `api.handle` |
| `static/` | Giao diện; `pyodide_worker.js` chạy Python trong trình duyệt |
| `build_site.py` | Đóng gói `dist/` cho GitHub Pages (tự gom mọi `.py` mới) |

## Thêm bài toán mới

Viết một file `.py` mới (như `vacuum_world.py`) trả về một `Domain`, rồi nối vào
`api.py` (`PROBLEMS`, nhánh trong `_solve`) và `get_presets()`. `build_site.py` tự đưa file mới vào trang.

## Thêm thuật toán mới

Thuật toán cùng họ (chỉ đổi cấu trúc frontier) thêm trong `search_core.py` giống DFS.
UCS là ví dụ cho thuật toán cần thêm thông tin: `Domain.step_cost` cho chi phí hành động,
trace riêng (`_search_trace_ucs`) và các sự kiện mới trong giao diện. Độ sâu giới hạn (DLS)
hay heuristic (A*) cũng cần mở rộng bộ máy và giao diện chứ không chỉ thêm một dòng.

## Lưu ý về UCS

Với các chi phí trên, nút trong frontier gần như không bao giờ được tìm thấy đường rẻ hơn
(đã quét n-Puzzle và Vacuum), nên bước `REPLACE` của UCS và nút "cũ" của bản tối ưu hầu như
không xuất hiện: hai bản UCS chạy giống hệt nhau. Hai trường hợp này được kiểm thử bằng một
đồ thị mẫu trong `test_ucs.py` (S→A tốn 5, S→B→A tốn 1+1).
