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
python run.py             # có backend Python, mở http://127.0.0.1:8765
```

Hoặc thử đúng như bản đưa lên GitHub Pages (không cần máy chủ Python):

```
python tools/build_site.py
python -m http.server 8766 -d dist
```

Chạy test (từ thư mục này):

```
python -m unittest discover -s tests -t .
```

Trang tự nhận biết: có máy chủ thì gọi API, không có thì chạy chính package `searchviz`
trong trình duyệt bằng Pyodide (lần đầu mở mất vài giây để tải).

## Đưa lên GitHub Pages

1. Push lên nhánh `master`.
2. Trên GitHub: Settings → Pages → Source chọn **GitHub Actions** (làm một lần).
3. Mỗi lần push thay đổi trong thư mục này, workflow `.github/workflows/pages.yml`
   tự chạy test rồi deploy.

## Cấu trúc

```
visualize_problem/
├── searchviz/              package Python
│   ├── core/               lõi thuật toán, không biết bài toán cụ thể
│   │   ├── types.py          Node, Problem, Domain, hằng số
│   │   ├── primitives.py     Queue/Stack, child_node, solution
│   │   ├── algorithms.py     BFS, DFS, UCS, UCS_fast (bản chạy thuần)
│   │   ├── pseudocode.py     mã giả hiển thị, mỗi dòng có tag
│   │   └── tracing.py        search_trace: ghi vết từng dòng thành JSON
│   ├── problems/           định nghĩa từng bài toán
│   │   ├── base.py           SolveOptions + hàm đọc tham số
│   │   ├── npuzzle.py        n-Puzzle 2×2 / 3×3 / 4×4
│   │   └── vacuum.py         Vacuum Robot 2–6 phòng
│   └── web/                lớp giao tiếp
│       ├── api.py            handle(method, path, payload), thuần Python
│       └── server.py         máy chủ HTTP cục bộ (mỏng, gọi api.handle)
├── ui/                     giao diện: index.html, styles.css, app.js, theme.js,
│                           pyodide_worker.js (chạy Python trong trình duyệt)
├── tests/                  test_bfs_core, test_ucs, test_structure
├── tools/build_site.py     đóng gói dist/ cho GitHub Pages
└── run.py                  chạy cục bộ
```

Quy tắc phụ thuộc, có test canh giữ (`tests/test_structure.py`):
`core` không import `problems` hay `web`; `problems` không import `web`; giao diện chỉ nói chuyện
với Python qua `/api/*`.

## Thêm bài toán mới

1. Tạo `searchviz/problems/ten_bai.py` theo mẫu `vacuum.py`: khai báo `KIND`, hàm `presets()`,
   hàm `solve(payload, options)` trả về `search_trace(domain, ...)`, và một `Domain`
   (trạng thái đầu, đích, hành động, chuyển trạng thái, chi phí).
2. Thêm module vào `PROBLEMS` trong `searchviz/problems/__init__.py`.
3. Thêm nút chọn bài và cách vẽ trạng thái trong `ui/` nếu bài mới cần hiển thị riêng.

`tools/build_site.py` tự đưa file `.py` mới vào trang, không phải sửa danh sách.

## Thêm thuật toán mới

Thuật toán cùng họ (chỉ đổi cấu trúc frontier) thêm trong `searchviz/core` giống DFS:
bản chạy thuần ở `algorithms.py`, mã giả ở `pseudocode.py`, nhánh ghi vết ở `tracing.py`, tên trong
`ALGORITHMS` (`types.py`). UCS là ví dụ cho thuật toán cần thêm thông tin: `Domain.step_cost` cho chi
phí hành động, trace riêng (`_search_trace_ucs`) và các sự kiện mới trong giao diện. Độ sâu giới hạn
(DLS) hay heuristic (A*) cũng cần mở rộng bộ máy và giao diện chứ không chỉ thêm một dòng.

## Lưu ý về UCS

Với các chi phí trên, nút trong frontier gần như không bao giờ được tìm thấy đường rẻ hơn
(đã quét n-Puzzle và Vacuum), nên bước `REPLACE` của UCS và nút "cũ" của bản tối ưu hầu như
không xuất hiện: hai bản UCS chạy giống hệt nhau. Hai trường hợp này được kiểm thử bằng một
đồ thị mẫu trong `tests/test_ucs.py` (S→A tốn 5, S→B→A tốn 1+1).
