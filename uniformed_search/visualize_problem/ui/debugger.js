/* Bộ gỡ lỗi cho trình xem thuật toán: điểm dừng (breakpoint), điều kiện dừng, chạy tới dòng,
 * bảng theo dõi biến và các "quy luật" của thuật toán.
 *
 * Toàn bộ các bước đã được ghi sẵn khi chạy, nên mọi thứ ở đây chỉ là duyệt qua danh sách bước:
 * không gọi lại Python. app.js cung cấp window.SearchViz (đọc trace, nhảy tới bước) và gọi
 * onTrace / afterRender / pausesAt / stopped ở các thời điểm tương ứng.
 */
(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const host = () => window.SearchViz;

  // ── Điều kiện dừng ─────────────────────────────────────────────────────────
  // edge = true: chỉ dừng ở bước điều kiện VỪA trở thành đúng (không dừng lặp lại ở mọi bước sau đó).
  const nodeOf = (t, id) => (id === null || id === undefined ? null : t.nodes[id]);
  const CONDITIONS = {
    frontier_gt: {
      label: "frontier dài hơn", unit: "nút", def: 5, edge: true,
      test: (s, t, v) => s.metrics.frontier_size > v,
      why: (s, v) => `frontier có ${s.metrics.frontier_size} nút (> ${v})`,
    },
    explored_ge: {
      label: "explored có từ", unit: "nút", def: 5, edge: true,
      test: (s, t, v) => s.metrics.explored_size >= v,
      why: (s, v) => `explored đã có ${s.metrics.explored_size} nút (≥ ${v})`,
    },
    expanded_ge: {
      label: "đã mở rộng từ", unit: "nút", def: 5, edge: true,
      test: (s, t, v) => s.metrics.expanded >= v,
      why: (s, v) => `đã mở rộng ${s.metrics.expanded} nút (≥ ${v})`,
    },
    depth_ge: {
      label: "nút đang xét ở tầng ≥", unit: "", def: 3, edge: true,
      test: (s, t, v) => { const n = nodeOf(t, s.cur_id); return !!n && n.depth >= v; },
      why: (s, v, t) => `nút #${s.cur_id} ở tầng ${nodeOf(t, s.cur_id).depth} (≥ ${v})`,
    },
    g_ge: {
      label: "chi phí g của nút đang xét ≥", unit: "", def: 4, edge: true,
      test: (s, t, v) => { const n = nodeOf(t, s.cur_id); return !!n && n.path_cost >= v; },
      why: (s, v, t) => `nút #${s.cur_id} có g = ${nodeOf(t, s.cur_id).path_cost} (≥ ${v})`,
    },
    node_is: {
      label: "chạm tới nút #", unit: "", def: 10, edge: true,
      test: (s, t, v) => s.cur_id === v || s.candidate_id === v,
      why: (s, v) => `nút #${v} xuất hiện`,
    },
    event_dup: {
      label: "gặp nút trùng", noValue: true,
      test: (s) => s.event_type === "skip_explored" || s.event_type === "skip_frontier",
      why: () => "vừa gặp một nút trùng (bị bỏ qua)",
    },
    event_goal: {
      label: "tìm thấy đích", noValue: true,
      test: (s) => s.event_type === "goal_init" || s.event_type === "goal_early" || s.event_type === "goal_late",
      why: () => "vừa tìm thấy đích",
    },
    event_replace: {
      label: "UCS thay nút trong frontier", noValue: true,
      test: (s) => s.event_type === "replace",
      why: () => "vừa thay một nút trong frontier bằng đường rẻ hơn",
    },
    event_stale: {
      label: "UCS bỏ qua nút cũ", noValue: true,
      test: (s) => s.event_type === "skip_stale",
      why: () => "vừa bỏ qua một nút cũ",
    },
  };

  // ── Trạng thái ─────────────────────────────────────────────────────────────
  const state = {
    tags: new Set(),      // điểm dừng theo dòng, lưu theo tag nên còn hiệu lực khi đổi tùy chọn
    conds: [],            // [{type, value, on}]
    hits: new Map(),      // chỉ số bước -> lý do dừng đầu tiên
    invariants: [],
    status: null,         // {step, text, kind}
  };

  const trace = () => {
    const t = host() && host().getTrace();
    return t && t.steps && t.steps.length && !t.compare ? t : null;
  };

  function lineOfTag(t, tag) {
    return t.source_lines.find((l) => l.tag === tag) || null;
  }

  // ── Tính các bước sẽ dừng ──────────────────────────────────────────────────
  function stopReason(t, i) {
    const s = t.steps[i];
    const prev = i > 0 ? t.steps[i - 1] : null;
    if (state.tags.has(s.code_tag)) {
      const ln = lineOfTag(t, s.code_tag);
      return `điểm dừng ở dòng ${ln ? ln.line : s.line}`;
    }
    for (const c of state.conds) {
      if (!c.on) continue;
      const def = CONDITIONS[c.type];
      if (!def.test(s, t, c.value)) continue;
      if (def.edge && prev && def.test(prev, t, c.value)) continue;
      return def.why(s, c.value, t);
    }
    return null;
  }

  function recomputeHits() {
    state.hits.clear();
    const t = trace();
    if (!t) return;
    for (let i = 0; i < t.steps.length; i += 1) {
      const why = stopReason(t, i);
      if (why) state.hits.set(i, why);
    }
  }

  // ── Quy luật của thuật toán (kiểm trên toàn bộ trace, một lần) ─────────────
  function stateKey(t, id) {
    return JSON.stringify(t.nodes[id].state);
  }

  function computeInvariants(t) {
    const algo = t.algorithm;
    const ucs = algo === "ucs" || algo === "ucs_fast";
    const defs = [];

    if (algo === "bfs") {
      defs.push({
        label: "Pop lấy nút ĐẦU hàng đợi",
        tip: "BFS dùng hàng đợi FIFO: nút được lấy ra phải là nút vào sớm nhất.",
        check: (prevFrontier, cur) => prevFrontier[0] === cur,
        bad: (prevFrontier, cur) => `lấy #${cur} nhưng nút ở đầu là #${prevFrontier[0]}`,
      });
      defs.push({
        label: "Độ sâu của nút được pop không giảm",
        tip: "Nhờ lấy theo thứ tự vào, BFS mở rộng hết tầng d rồi mới sang tầng d+1.",
        stateful: true,
        check: (prevFrontier, cur, mem) => {
          const d = t.nodes[cur].depth;
          const ok = mem.last === undefined || d >= mem.last;
          mem.bad = ok ? null : `nút #${cur} ở tầng ${d}, sau khi đã mở rộng nút ở tầng ${mem.last}`;
          mem.last = Math.max(d, mem.last === undefined ? d : mem.last);
          return ok;
        },
      });
    } else if (algo === "dfs") {
      defs.push({
        label: "Pop lấy nút ĐỈNH ngăn xếp",
        tip: "DFS dùng ngăn xếp LIFO: nút được lấy ra phải là nút vừa được push gần nhất.",
        check: (prevFrontier, cur) => prevFrontier[prevFrontier.length - 1] === cur,
        bad: (prevFrontier, cur) => `lấy #${cur} nhưng nút ở đỉnh là #${prevFrontier[prevFrontier.length - 1]}`,
      });
    } else if (ucs) {
      defs.push({
        label: "Pop lấy nút có g NHỎ NHẤT",
        tip: "UCS luôn mở rộng nút rẻ nhất trong frontier; đó là lý do lời giải đầu tiên tìm được là tối ưu.",
        check: (prevFrontier, cur) => {
          const g = t.nodes[cur].path_cost;
          return prevFrontier.every((id) => t.nodes[id].path_cost >= g);
        },
        bad: (prevFrontier, cur) => {
          const cheaper = prevFrontier.find((id) => t.nodes[id].path_cost < t.nodes[cur].path_cost);
          return `lấy #${cur} (g=${t.nodes[cur].path_cost}) nhưng #${cheaper} chỉ tốn g=${t.nodes[cheaper].path_cost}`;
        },
      });
      defs.push({
        label: "g của nút được pop không giảm",
        tip: "Chi phí g của các nút được mở rộng tăng dần.",
        stateful: true,
        check: (prevFrontier, cur, mem) => {
          const g = t.nodes[cur].path_cost;
          const ok = mem.last === undefined || g >= mem.last;
          mem.bad = ok ? null : `nút #${cur} có g=${g}, sau khi đã mở rộng nút có g=${mem.last}`;
          mem.last = Math.max(g, mem.last === undefined ? g : mem.last);
          return ok;
        },
      });
    }
    if (t.config.graph_search || ucs) {
      defs.push({
        label: "Mỗi trạng thái chỉ được mở rộng một lần",
        tip: "Tập explored giúp không mở rộng lại trạng thái đã xong.",
        stateful: true,
        check: (prevFrontier, cur, mem, stepIdx) => {
          mem.seen = mem.seen || new Map();
          const key = stateKey(t, cur);
          // UCS tối ưu có thể pop nút cũ rồi bỏ qua: chỉ tính khi nút thật sự được mở rộng
          const next = t.steps[stepIdx + 1];
          if (next && (next.event_type === "skip_stale")) return true;
          if (mem.seen.has(key)) {
            mem.bad = `trạng thái của #${cur} đã được mở rộng ở nút #${mem.seen.get(key)}`;
            return false;
          }
          mem.seen.set(key, cur);
          mem.bad = null;
          return true;
        },
      });
    }

    const out = defs.map((d) => ({ ...d, mem: {}, violation: null, popsSeen: 0, firstPop: null }));
    for (let i = 1; i < t.steps.length; i += 1) {
      const s = t.steps[i];
      if (s.event_type !== "dequeue" || s.cur_id === null) continue;
      const prevFrontier = t.steps[i - 1].frontier_ids;
      for (const inv of out) {
        if (inv.firstPop === null) inv.firstPop = i;
        if (inv.violation) continue;
        const ok = inv.check(prevFrontier, s.cur_id, inv.mem, i);
        if (!ok) {
          inv.violation = { step: i, text: inv.stateful ? inv.mem.bad : inv.bad(prevFrontier, s.cur_id) };
        }
      }
    }
    return out;
  }

  // ── Giao diện ──────────────────────────────────────────────────────────────
  function toast(text, kind = "info") {
    const t = trace();
    state.status = { step: t ? host().getStep() : -1, text, kind };
    renderStatus();
  }

  function renderStatus() {
    const box = $("bpStatus");
    if (!box) return;
    const t = trace();
    const s = state.status;
    if (!t || !s || s.step !== host().getStep()) {
      box.classList.add("hidden");
      return;
    }
    box.textContent = s.text;
    box.className = `bp-status bp-${s.kind}`;
  }

  function renderBpPanel() {
    const list = $("bpList");
    if (!list) return;
    const t = trace();
    list.innerHTML = "";
    const addChip = (text, { on = true, onToggle, onRemove, title = "" }) => {
      const chip = document.createElement("div");
      chip.className = "bp-chip" + (on ? "" : " off");
      chip.title = title;
      const cb = document.createElement("input");
      cb.type = "checkbox";
      cb.checked = on;
      cb.setAttribute("aria-label", "Bật/tắt điểm dừng");
      cb.addEventListener("change", () => onToggle(cb.checked));
      const label = document.createElement("span");
      label.textContent = text;
      const rm = document.createElement("button");
      rm.type = "button";
      rm.className = "bp-remove";
      rm.setAttribute("aria-label", "Xóa điểm dừng");
      rm.textContent = "✕";
      rm.addEventListener("click", onRemove);
      chip.append(cb, label, rm);
      list.appendChild(chip);
    };

    for (const tag of state.tags) {
      const ln = t ? lineOfTag(t, tag) : null;
      addChip(ln ? `dòng ${ln.line}: ${ln.code.trim()}` : `dòng "${tag}"`, {
        on: true,
        title: "Dừng mỗi lần chạy tới dòng này",
        onToggle: () => {},
        onRemove: () => { state.tags.delete(tag); changed(); },
      });
    }
    state.conds.forEach((c, idx) => {
      const def = CONDITIONS[c.type];
      addChip(def.noValue ? def.label : `${def.label} ${c.value}${def.unit ? " " + def.unit : ""}`, {
        on: c.on,
        title: def.edge ? "Dừng ở bước điều kiện vừa trở thành đúng" : "Dừng mỗi khi sự kiện xảy ra",
        onToggle: (v) => { c.on = v; changed(); },
        onRemove: () => { state.conds.splice(idx, 1); changed(); },
      });
    });

    const count = state.tags.size + state.conds.filter((c) => c.on).length;
    const badge = $("bpCount");
    if (badge) badge.textContent = String(count);
    if (!state.tags.size && !state.conds.length) {
      const hint = document.createElement("p");
      hint.className = "bp-hint";
      hint.textContent = "Bấm SỐ DÒNG trong mã giả để đặt điểm dừng. Bấm vào CHỮ của dòng để chạy tới dòng đó.";
      list.appendChild(hint);
    }
  }

  function renderMarks() {
    const box = $("bpMarks");
    if (!box) return;
    box.innerHTML = "";
    const t = trace();
    if (!t || t.steps.length < 2) return;
    const last = t.steps.length - 1;
    const seen = new Set();
    for (const i of state.hits.keys()) {
      const slot = Math.round((i / last) * 400);
      if (seen.has(slot)) continue;
      seen.add(slot);
      const m = document.createElement("i");
      m.className = "bp-mark";
      m.style.left = `${(i / last) * 100}%`;
      m.title = `Bước ${i}: dừng vì ${state.hits.get(i)}`;
      box.appendChild(m);
    }
  }

  function renderWatch() {
    const box = $("watchContainer");
    if (!box) return;
    box.innerHTML = "";
    const t = trace();
    if (!t) return;
    const idx = host().getStep();
    const s = t.steps[idx];
    const p = idx > 0 ? t.steps[idx - 1] : null;
    const cur = nodeOf(t, s.cur_id);
    const cand = nodeOf(t, s.candidate_id);
    const items = [
      { k: "frontier", v: s.metrics.frontier_size, pv: p && p.metrics.frontier_size, num: true },
      { k: "explored", v: s.metrics.explored_size, pv: p && p.metrics.explored_size, num: true },
      { k: "cur_node", v: cur ? `#${cur.id} · d=${cur.depth}${cur.path_cost !== cur.depth ? ` · g=${cur.path_cost}` : ""}` : "—",
        pv: p && (nodeOf(t, p.cur_id) ? `#${p.cur_id}` : "—"), key: cur ? `#${cur.id}` : "—" },
      { k: "child", v: cand ? `#${cand.id}` : "—", pv: p && (p.candidate_id !== null ? `#${p.candidate_id}` : "—"), key: cand ? `#${cand.id}` : "—" },
      { k: "đã mở rộng", v: s.metrics.expanded, pv: p && p.metrics.expanded, num: true },
      { k: "đã sinh", v: s.metrics.generated, pv: p && p.metrics.generated, num: true },
    ];
    for (const it of items) {
      const el = document.createElement("div");
      const same = it.pv === null || it.pv === undefined || (it.key !== undefined ? it.key === it.pv : it.v === it.pv);
      el.className = "watch-item" + (same ? "" : " changed");
      const k = document.createElement("span");
      k.className = "watch-k";
      k.textContent = it.k;
      const v = document.createElement("span");
      v.className = "watch-v";
      v.textContent = String(it.v);
      if (!same && it.num) {
        const arrow = document.createElement("i");
        arrow.className = "watch-arrow";
        arrow.textContent = it.v > it.pv ? "▲" : "▼";
        v.appendChild(arrow);
      }
      el.append(k, v);
      box.appendChild(el);
    }
  }

  function renderInvariants() {
    const box = $("invariantRow");
    if (!box) return;
    box.innerHTML = "";
    const t = trace();
    if (!t || !state.invariants.length) return;
    const idx = host().getStep();
    const head = document.createElement("div");
    head.className = "inv-head";
    head.textContent = "Quy luật của thuật toán";
    box.appendChild(head);
    for (const inv of state.invariants) {
      const broken = inv.violation && inv.violation.step <= idx;
      const started = inv.firstPop !== null && inv.firstPop <= idx;
      const row = document.createElement(broken ? "button" : "div");
      row.className = `inv-row ${broken ? "inv-bad" : started ? "inv-ok" : "inv-wait"}`;
      if (broken) {
        row.type = "button";
        row.addEventListener("click", () => host().goTo(inv.violation.step));
      }
      const icon = document.createElement("span");
      icon.className = "inv-icon";
      icon.textContent = broken ? "✗" : started ? "✓" : "·";
      const text = document.createElement("span");
      text.className = "inv-text";
      text.textContent = broken ? `${inv.label} — sai ở bước ${inv.violation.step}: ${inv.violation.text}` : inv.label;
      row.title = broken ? "Bấm để tới bước vi phạm" : inv.tip;
      row.append(icon, text);
      box.appendChild(row);
    }
  }

  function decorateCode() {
    const box = $("codeLinesContainer");
    if (!box) return;
    box.querySelectorAll(".code-line").forEach((row) => {
      row.classList.toggle("has-bp", state.tags.has(row.dataset.tag));
    });
  }

  function toolbarState() {
    const t = trace();
    const idx = t ? host().getStep() : 0;
    const hasAny = state.hits.size > 0;
    const next = $("bpNextBtn");
    const prev = $("bpPrevBtn");
    const over = $("stepOverBtn");
    if (!next) return;
    const blocked = !t || host().predictActive();
    next.disabled = blocked || !hasAny || ![...state.hits.keys()].some((i) => i > idx);
    prev.disabled = blocked || !hasAny || ![...state.hits.keys()].some((i) => i < idx);
    over.disabled = blocked || idx >= t.steps.length - 1;
    next.title = host() && host().predictActive() ? "Tắt chế độ Dự đoán để dùng điểm dừng" : "Chạy tới điểm dừng kế tiếp (F8)";
  }

  function changed() {
    recomputeHits();
    renderBpPanel();
    renderMarks();
    decorateCode();
    toolbarState();
  }

  // ── Điều hướng ─────────────────────────────────────────────────────────────
  function runToBreakpoint(dir) {
    const t = trace();
    if (!t) return;
    if (host().predictActive()) {
      toast("Hãy tắt chế độ Dự đoán để dùng điểm dừng.", "warn");
      return;
    }
    const n = t.steps.length;
    for (let i = host().getStep() + dir; i >= 0 && i < n; i += dir) {
      if (state.hits.has(i)) {
        state.status = { step: i, text: `Dừng vì ${state.hits.get(i)}.`, kind: "hit" };
        host().goTo(i);
        return;
      }
    }
    const edge = dir > 0 ? n - 1 : 0;
    state.status = {
      step: edge,
      text: state.hits.size
        ? `Không còn điểm dừng nào ${dir > 0 ? "phía sau" : "phía trước"}.`
        : "Chưa có điểm dừng nào. Hãy đặt điểm dừng trước.",
      kind: "info",
    };
    host().goTo(edge);
  }

  function stepOver() {
    const t = trace();
    if (!t || host().predictActive()) return;
    const boundary = new Set(["gen_child", "dequeue", "goal_init", "goal_early", "goal_late", "failure", "limit_reached"]);
    let i = host().getStep() + 1;
    while (i < t.steps.length - 1 && !boundary.has(t.steps[i].event_type)) i += 1;
    host().goTo(Math.min(i, t.steps.length - 1));
  }

  function runToLine(tag) {
    const t = trace();
    if (!t || host().predictActive()) return;
    for (let i = host().getStep() + 1; i < t.steps.length; i += 1) {
      if (t.steps[i].code_tag === tag) {
        const ln = lineOfTag(t, tag);
        state.status = { step: i, text: `Đã chạy tới dòng ${ln ? ln.line : ""}.`, kind: "info" };
        host().goTo(i);
        return;
      }
    }
    const ln = lineOfTag(t, tag);
    toast(`Phía sau không còn lần nào chạy tới dòng ${ln ? ln.line : ""}.`, "info");
  }

  // ── Móc nối với app.js ─────────────────────────────────────────────────────
  window.SearchDebugger = {
    hasBreakpoint: (tag) => state.tags.has(tag),
    onTrace() {
      state.status = null;
      state.invariants = trace() ? computeInvariants(trace()) : [];
      changed();
    },
    afterRender() {
      renderStatus();
      renderWatch();
      renderInvariants();
      decorateCode();
      toolbarState();
    },
    pausesAt(idx) {
      const t = trace();
      if (!t || host().predictActive()) return null;
      return state.hits.get(idx) || null;
    },
    stopped(idx, why) {
      state.status = { step: idx, text: `Dừng vì ${why}.`, kind: "hit" };
      renderStatus();
    },
  };

  document.addEventListener("DOMContentLoaded", () => {
    const code = $("codeLinesContainer");
    code.addEventListener("click", (e) => {
      const row = e.target.closest(".code-line");
      if (!row || !row.dataset.tag) return;
      if (e.target.closest(".line-num")) {
        const tag = row.dataset.tag;
        if (state.tags.has(tag)) state.tags.delete(tag);
        else state.tags.add(tag);
        changed();
      } else if (!e.target.closest(".line-tools")) {
        runToLine(row.dataset.tag);
      }
    });

    $("bpNextBtn").addEventListener("click", () => runToBreakpoint(1));
    $("bpPrevBtn").addEventListener("click", () => runToBreakpoint(-1));
    $("stepOverBtn").addEventListener("click", stepOver);

    const typeSel = $("bpCondType");
    const valInput = $("bpCondValue");
    const valWrap = $("bpCondValueWrap");
    for (const [id, def] of Object.entries(CONDITIONS)) {
      const opt = document.createElement("option");
      opt.value = id;
      opt.textContent = def.label;
      typeSel.appendChild(opt);
    }
    const syncValue = () => {
      const def = CONDITIONS[typeSel.value];
      valWrap.classList.toggle("hidden", !!def.noValue);
      if (!def.noValue) valInput.value = String(def.def);
    };
    typeSel.addEventListener("change", syncValue);
    syncValue();

    $("bpForm").addEventListener("submit", (e) => {
      e.preventDefault();
      const def = CONDITIONS[typeSel.value];
      const value = def.noValue ? null : Math.max(0, Math.floor(Number(valInput.value) || 0));
      const dup = state.conds.some((c) => c.type === typeSel.value && c.value === value);
      if (!dup) state.conds.push({ type: typeSel.value, value, on: true });
      changed();
    });

    $("bpClearBtn").addEventListener("click", () => {
      state.tags.clear();
      state.conds = [];
      changed();
    });

    window.addEventListener("keydown", (e) => {
      const tag = document.activeElement && document.activeElement.tagName;
      if (tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA") return;
      if (e.key === "F8") {
        e.preventDefault();
        runToBreakpoint(e.shiftKey ? -1 : 1);
      }
    });

    renderBpPanel();
  });
})();
