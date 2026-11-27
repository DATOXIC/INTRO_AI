const PYODIDE_VERSION = "0.26.4";
const PYODIDE_BASE = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;

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
    const dest = "/home/pyodide/" + name;
    pyodide.FS.mkdirTree(dest.slice(0, dest.lastIndexOf("/")));
    pyodide.FS.writeFile(dest, await resp.text());
  }
  pyodide.runPython(`
import sys, json
sys.path.insert(0, "/home/pyodide")
from searchviz.web import api

def _call(method, path, payload_json):
    status, body = api.handle(method, path, json.loads(payload_json) if payload_json else {})
    return json.dumps([status, body], ensure_ascii=False)
`);
  return pyodide;
}

function describeError(err) {
  if (err && typeof err.message === "string" && err.message) return err.message;
  try {
    return JSON.stringify(err, Object.getOwnPropertyNames(err || {}));
  } catch (_) {
    return String(err);
  }
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
    ready = null;
    postMessage({ id, fatal: describeError(err) });
  }
};
