/* Chạy mã Python của bài ngay trong trình duyệt (Pyodide) để trang chạy được trên
 * GitHub Pages mà không cần máy chủ. Chạy trong Web Worker nên giao diện không bị đơ
 * khi thuật toán tính toán lâu.
 *
 * Giao thức: main -> worker  {id, method, path, payload}
 *            worker -> main  {id, status, body}  hoặc  {id, fatal}
 *            worker -> main  {progress: "..."}   (thông báo tiến độ tải)
 */
const PYODIDE_VERSION = "0.26.4";
const PYODIDE_BASE = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;

// Mọi file .py của bài nằm trong thư mục py/ cạnh trang. Thêm bài mới = thêm tên file vào py/manifest.json
// (build_site.py tự sinh file này), không phải sửa ở đây.
const PY_DIR = "py/";

let ready = null;

async function boot() {
  postMessage({ progress: "Đang tải trình chạy Python (lần đầu mất vài giây)…" });
  importScripts(PYODIDE_BASE + "pyodide.js");
  const pyodide = await loadPyodide({ indexURL: PYODIDE_BASE });

  postMessage({ progress: "Đang nạp mã thuật toán…" });
  const manifest = await (await fetch(PY_DIR + "manifest.json", { cache: "no-store" })).json();
  for (const name of manifest.files) {
    const resp = await fetch(PY_DIR + name, { cache: "no-store" });
    if (!resp.ok) throw new Error(`Không tải được ${name} (HTTP ${resp.status})`);
    pyodide.FS.writeFile("/home/pyodide/" + name, await resp.text());
  }
  pyodide.runPython(`
import sys, json
sys.path.insert(0, "/home/pyodide")
import api

def _call(method, path, payload_json):
    status, body = api.handle(method, path, json.loads(payload_json) if payload_json else {})
    return json.dumps([status, body], ensure_ascii=False)
`);
  return pyodide;
}

onmessage = async (event) => {
  const { id, method, path, payload } = event.data;
  try {
    if (!ready) ready = boot();
    const pyodide = await ready;
    const call = pyodide.globals.get("_call");
    const raw = call(method, path, JSON.stringify(payload || {}));
    call.destroy();
    const [status, body] = JSON.parse(raw);
    postMessage({ id, status, body });
  } catch (err) {
    ready = null; // cho phép thử lại ở lần gọi sau
    postMessage({ id, fatal: String(err && err.message ? err.message : err) });
  }
};
