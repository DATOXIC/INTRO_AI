/* "Nếu bỏ lệnh này thì sao?": tắt một dòng mã giả hoặc đổi chỗ hai dòng rồi chạy lại thật.
 *
 * Chỉnh sửa gửi lên máy chủ (hoặc Pyodide) dưới dạng {disabled: [tag], order: {khối: [tag]}}; Python chạy
 * đúng chương trình đã sửa và trả về vết mới. Module này giữ trạng thái chỉnh sửa, xử lý nút bấm trên từng
 * dòng mã, và so kết quả của bản sửa với bản gốc.
 */
(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const host = () => window.SearchViz;

  const state = {
    disabled: new Set(),
    order: {},        // {khối: [tag theo thứ tự mới]}
    token: 0,         // để bỏ kết quả so sánh cũ nếu người dùng đã sửa tiếp
  };

  const STATUS_TEXT = {
    solved: "Tìm thấy lời giải",
    failure: "Không tìm thấy (frontier cạn)",
    limit_reached: "Chạm giới hạn, chưa dừng",
    program_error: "Lỗi chương trình",
  };

  const isEdited = () => state.disabled.size > 0 || Object.keys(state.order).length > 0;

  function getEdits() {
    if (!isEdited()) return null;
    return { disabled: [...state.disabled], order: { ...state.order } };
  }

  function reset() {
    state.disabled.clear();
    state.order = {};
    state.token += 1;
    renderBox(null, null);
  }

  // ── Bấm nút trên từng dòng ─────────────────────────────────────────────────
  function currentLines() {
    const t = host() && host().getTrace();
    return t && t.source_lines ? t.source_lines : [];
  }

  function toggle(tag) {
    if (state.disabled.has(tag)) state.disabled.delete(tag);
    else state.disabled.add(tag);
  }

  function move(tag, block, dir) {
    // Thứ tự hiện tại của các "đơn vị" trong khối (dòng if + nhánh elif đi cùng nhau)
    const tags = currentLines().filter((l) => l.block === block && l.unit).map((l) => l.tag);
    const i = tags.indexOf(tag);
    const j = i + dir;
    if (i < 0 || j < 0 || j >= tags.length) return;
    [tags[i], tags[j]] = [tags[j], tags[i]];
    state.order[block] = tags;
  }

  function onToolClick(e) {
    const btn = e.target.closest(".line-tool");
    if (!btn) return;
    e.preventDefault();
    e.stopPropagation();
    const row = btn.closest(".code-line");
    const tag = row.dataset.tag;
    const action = btn.dataset.action;
    if (action === "toggle") toggle(tag);
    else move(tag, row.dataset.block, action === "up" ? -1 : 1);
    state.token += 1;
    host().rerun();
  }

  // ── Hộp so sánh với bản gốc ────────────────────────────────────────────────
  function metric(trace) {
    const s = trace.summary || {};
    return {
      status: trace.status,
      expanded: s.nodes_expanded,
      generated: s.nodes_generated,
      length: s.solution_length,
      cost: s.solution_cost,
      frontier: s.max_frontier_size,
    };
  }

  const ROWS = [
    { key: "status", label: "Kết quả", fmt: (v) => STATUS_TEXT[v] || v },
    { key: "expanded", label: "Nút đã mở rộng", lowerBetter: true },
    { key: "generated", label: "Nút đã sinh", lowerBetter: true },
    { key: "length", label: "Số bước của lời giải", lowerBetter: true },
    { key: "cost", label: "Chi phí lời giải", lowerBetter: true },
    { key: "frontier", label: "Frontier dài nhất", lowerBetter: true },
  ];

  function insight(base, edit) {
    if (edit.status === "program_error") {
      return "Bản đã sửa không chạy được: một dòng dùng thứ mà chưa có ở đó. Hãy đọc thông báo lỗi phía trên.";
    }
    if (base.status === "solved" && edit.status !== "solved") {
      return edit.status === "limit_reached"
        ? "Bản gốc tìm ra lời giải, còn bản đã sửa chạy mãi không dừng: dòng bạn đổi chính là thứ giữ cho thuật toán kết thúc."
        : "Bản gốc tìm ra lời giải, còn bản đã sửa thì không: thay đổi này làm mất lời giải.";
    }
    if (base.status === "solved" && edit.status === "solved") {
      const parts = [];
      if (edit.expanded !== base.expanded) {
        const diff = edit.expanded - base.expanded;
        parts.push(`mở rộng ${diff > 0 ? "nhiều hơn" : "ít hơn"} ${Math.abs(diff)} nút`);
      }
      if (edit.length !== base.length) parts.push(`lời giải ${edit.length} bước thay vì ${base.length}`);
      if (edit.cost !== base.cost) parts.push(`chi phí ${edit.cost} thay vì ${base.cost}`);
      if (edit.frontier !== base.frontier) parts.push(`frontier ${edit.frontier > base.frontier ? "dài hơn" : "ngắn hơn"}`);
      return parts.length
        ? `Vẫn tìm ra lời giải, nhưng ${parts.join(", ")}.`
        : "Kết quả giống hệt bản gốc (chỉ khác ở các bước chạy).";
    }
    return "";
  }

  function renderBox(editTrace, baseTrace) {
    const box = $("whatifBox");
    const hint = $("whatifHint");
    if (!box) return;
    if (!isEdited()) {
      box.classList.add("hidden");
      if (hint) hint.classList.remove("hidden");
      return;
    }
    box.classList.remove("hidden");
    if (hint) hint.classList.add("hidden");
    const diff = $("whatifDiff");
    const note = $("whatifInsight");
    diff.innerHTML = "";
    if (!editTrace || !baseTrace) {
      note.textContent = "Đang chạy lại…";
      return;
    }
    const a = metric(baseTrace);
    const b = metric(editTrace);
    note.textContent = insight(a, b);

    const table = document.createElement("table");
    table.className = "whatif-table";
    table.innerHTML = "<thead><tr><th></th><th>Bản gốc</th><th>Bản sửa</th></tr></thead>";
    const body = document.createElement("tbody");
    for (const row of ROWS) {
      const av = a[row.key];
      const bv = b[row.key];
      if ((av === null || av === undefined) && (bv === null || bv === undefined)) continue;
      const tr = document.createElement("tr");
      const fmt = row.fmt || ((v) => (v === null || v === undefined ? "—" : String(v)));
      const th = document.createElement("th");
      th.textContent = row.label;
      const tdA = document.createElement("td");
      tdA.textContent = fmt(av);
      const tdB = document.createElement("td");
      tdB.textContent = fmt(bv);
      if (av !== bv) {
        const better = row.lowerBetter && typeof av === "number" && typeof bv === "number" ? bv < av : null;
        tdB.className = better === true ? "wf-better" : better === false ? "wf-worse" : "wf-diff";
      }
      tr.append(th, tdA, tdB);
      body.appendChild(tr);
    }
    table.appendChild(body);
    diff.appendChild(table);
  }

  async function onTrace(editTrace) {
    if (!isEdited()) {
      renderBox(null, null);
      return;
    }
    const mine = state.token;
    renderBox(null, null);
    try {
      const base = await host().solveOriginal();
      if (mine !== state.token) return; // người dùng đã sửa tiếp
      renderBox(editTrace, base);
    } catch (err) {
      const note = $("whatifInsight");
      if (note) note.textContent = "Không chạy được bản gốc để so sánh.";
    }
  }

  window.SearchWhatIf = { getEdits, reset, onTrace };

  document.addEventListener("DOMContentLoaded", () => {
    $("codeLinesContainer").addEventListener("click", onToolClick, true); // bắt trước khi debugger.js chạy tới dòng
    $("whatifResetBtn").addEventListener("click", () => {
      reset();
      host().rerun();
    });
  });
})();
