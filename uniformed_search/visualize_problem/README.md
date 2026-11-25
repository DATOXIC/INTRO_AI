# Search Debugger

Trực quan hóa các thuật toán tìm kiếm cổ điển (môn Introduction to AI).
Hiện có: BFS, DFS trên n-Puzzle và Vacuum Robot, kèm chế độ so sánh và chế độ dự đoán.

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
| `search_core.py` | Bộ máy tìm kiếm chung (BFS/DFS, sinh trace từng dòng mã giả) |
| `bfs_core.py` | Bài n-Puzzle + danh sách preset |
| `vacuum_world.py` | Bài Vacuum Robot |
| `api.py` | Các endpoint dưới dạng hàm thuần Python (dùng chung server và trình duyệt) |
| `server.py` | Server cục bộ, chỉ là lớp mỏng gọi `api.handle` |
| `static/` | Giao diện; `pyodide_worker.js` chạy Python trong trình duyệt |
| `build_site.py` | Đóng gói `dist/` cho GitHub Pages (tự gom mọi `.py` mới) |

## Thêm bài toán mới

Viết một file `.py` mới (như `vacuum_world.py`) trả về một `Domain`, rồi nối vào
`api.py` (`PROBLEMS`, nhánh trong `_solve`) và `get_presets()`. `build_site.py` tự đưa file mới vào trang.

## Thêm thuật toán mới

Thuật toán cùng họ (chỉ đổi cấu trúc frontier) thêm trong `search_core.py` giống DFS.
Thuật toán cần thông tin mới (chi phí đường đi cho UCS, độ sâu giới hạn cho DLS,
heuristic cho A*) cần mở rộng thêm bộ máy và giao diện, không chỉ thêm một dòng.
