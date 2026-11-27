# Search Debugger

Trực quan hóa các thuật toán tìm kiếm cổ điển (môn Introduction to AI).
Hiện có:
- **Thuật toán:** BFS, DFS, UCS (đúng mã giả trên slide, có `REPLACE` nút trong frontier), UCS tối ưu (`best_cost`, bỏ qua nút cũ khi pop), **DLS** và **IDS** (đệ quy theo AIMA, xem mục dưới).
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

`tests/test_golden_traces.py` lưu dấu vân tay của 300 lần chạy: sửa bộ ghi vết mà làm đổi dù một bước, test báo ngay
ca nào đổi. Nếu chủ ý đổi, chạy `python tests/update_golden.py` rồi xem lại diff.

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
│   │   ├── models.py         Node, Problem, Domain, hằng số
│   │   ├── primitives.py     Queue/Stack, child_node, solution
│   │   ├── algorithms.py     BFS, DFS, UCS, UCS_fast, DLS, IDS (bản chạy thuần)
│   │   ├── recursive.py      DLS / IDS đệ quy có ghi vết (ngăn xếp lời gọi thay frontier)
│   │   ├── program.py        mã giả dưới dạng cây lệnh; tắt dòng, đổi chỗ dòng
│   │   ├── engine.py         trình thực thi cây lệnh, ghi từng dòng đã chạy
│   │   ├── recorder.py       ghi nút/bước, gói kết quả JSON
│   │   ├── pseudocode.py     các dòng mã giả để hiển thị
│   │   └── tracing.py        search_trace: điểm vào duy nhất
│   ├── problems/           định nghĩa từng bài toán
│   │   ├── base.py           SolveOptions + hàm đọc tham số
│   │   ├── npuzzle.py        n-Puzzle 2×2 / 3×3 / 4×4
│   │   └── vacuum.py         Vacuum Robot 2–6 phòng
│   └── web/                lớp giao tiếp
│       ├── api.py            handle(method, path, payload), thuần Python
│       └── server.py         máy chủ HTTP cục bộ (mỏng, gọi api.handle)
├── ui/                     giao diện: index.html, styles.css, app.js (trình xem chính),
│                           debugger.js (điểm dừng), whatif.js (tắt/đổi chỗ dòng), theme.js,
│                           pyodide_worker.js (chạy Python trong trình duyệt)
├── tests/                  test_bfs_core, test_ucs, test_program_edits, test_recursive,
│                           test_golden_traces, test_structure
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
bản chạy thuần ở `algorithms.py`, cây lệnh ở `program.py`, hàm xử lý từng dòng ở `engine.py`, tên trong
`ALGORITHMS` (`models.py`). UCS là ví dụ cho thuật toán cần thêm thông tin: `Domain.step_cost` cho chi
phí hành động, các hàm xử lý riêng trong `engine.py` và các sự kiện mới trong giao diện. Độ sâu giới hạn
(DLS) hay heuristic (A*) cũng cần mở rộng bộ máy và giao diện chứ không chỉ thêm một dòng.

## Gỡ lỗi và "nếu bỏ lệnh này thì sao?"

**Điểm dừng** (`ui/debugger.js`, không gọi lại Python vì mọi bước đã được ghi sẵn):
- Bấm *số dòng* trong mã giả để đặt / bỏ điểm dừng; bấm *chữ của dòng* để chạy tới dòng đó.
- Mục "Điểm dừng" thêm điều kiện dừng: frontier dài hơn N, nút ở tầng ≥ N, g ≥ N, chạm nút #k, gặp nút trùng,
  tìm thấy đích, UCS thay nút / bỏ nút cũ. Điều kiện dừng ở bước nó *vừa trở thành đúng*.
- Nút "Tới điểm dừng" (F8, Shift+F8 để lùi), "Hết lượt con", dấu đỏ trên thanh trượt cho biết các bước sẽ dừng.
- Bảng theo dõi hiện frontier, explored, cur_node, child và đổi màu khi giá trị vừa đổi.
- "Quy luật của thuật toán" kiểm trên toàn bộ vết: BFS pop đầu hàng đợi, UCS pop nút có g nhỏ nhất, mỗi trạng thái mở
  rộng một lần... Bấm một quy luật bị vi phạm để nhảy tới bước sai.

**Tắt hoặc đổi chỗ dòng** (`ui/whatif.js` + `searchviz/core/program.py`, `engine.py`): rê chuột lên một dòng,
bấm ⊘ để tắt, ▲ ▼ để đổi chỗ với dòng kế bên cùng khối. Python chạy lại *đúng chương trình đã sửa* rồi so với
bản gốc. Dòng dùng biến chưa tạo cho ra lỗi chương trình dễ hiểu; vòng lặp vô hạn bị chặn bởi giới hạn an toàn.
Các dòng `def`, `while`, `for`, `return` không tắt được, `def` và `return None` không đổi chỗ được.
API: thêm `"program": {"disabled": [tag], "order": {khối: [tag]}}` vào `/api/solve`.

## DLS và IDS (đệ quy)

Viết đúng như giáo trình: `recursive_dls(node, problem, limit)` trả về lời giải, `cutoff` (có nhánh chạm giới hạn
độ sâu) hoặc `failure` (đã duyệt hết cây). IDS lặp với giới hạn 0, 1, 2, ... đến khi kết quả khác `cutoff`.
- Không có frontier: ô "frontier" trên giao diện là **ngăn xếp lời gọi** (mỗi thẻ ghi `l=` là `limit` còn lại của lời gọi đó),
  ô "explored" là các lời gọi **đã trả về xong**.
- Ô **Kiểm tra chu trình** trong Tùy chọn: bật là thêm dòng `if is_cycle(child): continue` (chỉ so với tổ tiên trên đường
  đi hiện tại, bản tối ưu, DLS trả `failure` thật khi vô nghiệm); tắt là đúng mã giả gốc (chưa tối ưu).
- DLS có ô **Giới hạn độ sâu l**; IDS tự tăng. Cây của IDS là cây của vòng sâu nhất (cùng đường đi dùng lại cùng `id`),
  nhưng "Đã sinh / Đã mở rộng" đếm đủ mọi vòng nên thấy rõ chi phí lặp lại của IDS.
- Mã giả DLS / IDS chỉ đọc (không tắt, đổi chỗ dòng) và chưa có chế độ Dự đoán. API: `"depth_limit"` (0 đến 30) cho DLS.

## Lưu ý về UCS

Với các chi phí trên, nút trong frontier gần như không bao giờ được tìm thấy đường rẻ hơn
(đã quét n-Puzzle và Vacuum), nên bước `REPLACE` của UCS và nút "cũ" của bản tối ưu hầu như
không xuất hiện: hai bản UCS chạy giống hệt nhau. Hai trường hợp này được kiểm thử bằng một
đồ thị mẫu trong `tests/test_ucs.py` (S→A tốn 5, S→B→A tốn 1+1).
