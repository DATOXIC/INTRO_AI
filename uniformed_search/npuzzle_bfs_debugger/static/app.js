(() => {
  "use strict";

  const MOVE_ARROWS = {
    "Lên": "↑",
    "Xuống": "↓",
    "Trái": "←",
    "Phải": "→",
    "Hút bụi": "🧹",
  };

  const EVENT_BADGES = {
    init_root: { text: "TẠO NÚT GỐC", cls: "pill-indigo" },
    check_root: { text: "KIỂM TRA GỐC", cls: "pill-neutral" },
    init: { text: "ENQUEUE NÚT GỐC", cls: "pill-emerald" },
    init_explored: { text: "TẠO TẬP EXPLORED", cls: "pill-sky" },
    dequeue: { text: "POP KHỎI HÀNG ĐỢI", cls: "pill-amber" },
    check_late: { text: "KIỂM TRA ĐÍCH", cls: "pill-neutral" },
    explore: { text: "GHI VÀO EXPLORED", cls: "pill-sky" },
    gen_child: { text: "SINH NÚT CON", cls: "pill-indigo" },
    check_pass: { text: "KHÔNG TRÙNG → MỚI", cls: "pill-emerald" },
    skip_explored: { text: "BỎ QUA · ĐÃ CÓ TRONG EXPLORED", cls: "pill-rose" },
    skip_frontier: { text: "BỎ QUA · ĐÃ CÓ TRONG FRONTIER", cls: "pill-rose" },
    check_goal: { text: "KIỂM TRA ĐÍCH", cls: "pill-neutral" },
    enqueue: { text: "ENQUEUE VÀO CUỐI HÀNG ĐỢI", cls: "pill-emerald" },
    goal_init: { text: "ĐÃ TỚI ĐÍCH", cls: "pill-emerald" },
    goal_early: { text: "TỚI ĐÍCH", cls: "pill-emerald" },
    goal_late: { text: "TỚI ĐÍCH", cls: "pill-emerald" },
    limit_reached: { text: "CHẠM GIỚI HẠN", cls: "pill-amber" },
    failure: { text: "VÔ NGHIỆM", cls: "pill-rose" },
  };

  // DFS dùng ngăn xếp nên đổi từ ngữ của ba sự kiện liên quan tới frontier.
  const DFS_BADGES = {
    init: "PUSH NÚT GỐC",
    dequeue: "POP KHỎI NGĂN XẾP",
    enqueue: "PUSH LÊN ĐỈNH NGĂN XẾP",
  };

  function badgeFor(ev, algorithm) {
    const base = EVENT_BADGES[ev] || { text: ev.toUpperCase(), cls: "pill-neutral" };
    if (algorithm === "dfs" && DFS_BADGES[ev]) return { ...base, text: DFS_BADGES[ev] };
    return base;
  }

  const ALGO_LABELS = {
    bfs: { name: "BFS", kind: "hàng đợi FIFO", out: "◀ pop ở ĐẦU", in: "enqueue ở CUỐI ▶", container: "Hàng đợi", next: "Ra tiếp" },
    dfs: { name: "DFS", kind: "ngăn xếp LIFO", out: "đáy", in: "push & pop ở ĐỈNH ▶", container: "Ngăn xếp", next: "Pop tiếp" },
  };

  const state = {
    presets: [],
    problem: "npuzzle",
    algorithm: "bfs",
    vacStart: { robot: 0, dirt: [true, true] },
    compare: { enabled: false, runs: [], sides: [], maxTick: 0 },
    stepMode: "micro",
    size: 3,
    startBoard: [[1, 2, 3], [5, 0, 6], [4, 7, 8]],
    targetBoard: [[1, 2, 3], [4, 5, 6], [7, 8, 0]],
    trace: null,
    currentStep: 0,
    pinnedNodeId: null,
    activeTab: "tree",
    playTimer: null,
    treeTransform: { x: 0, y: 0, scale: 1 },
    treeBounds: { width: 600, height: 400 },
    treeAutoFit: true,
    predict: { enabled: false, pending: null, answered: new Set(), score: { right: 0, total: 0 } },
    editor: {
      activeTarget: "start",
      mode: "slide",
      draftStart: null,
      draftTarget: null,
    },
  };

  const els = {
    caption: document.getElementById("caption"),
    vizRow: document.getElementById("vizRow"),
    graphCard: document.getElementById("graphCard"),
    vacGraphSvg: document.getElementById("vacGraphSvg"),
    predictBtn: document.getElementById("predictBtn"),
    predictScore: document.getElementById("predictScore"),
    predictActions: document.getElementById("predictActions"),
    compareBtn: document.getElementById("compareBtn"),
    cmpSummary: document.getElementById("cmpSummary"),
    cmpInsight: document.getElementById("cmpInsight"),
    cmpDepthChart: document.getElementById("cmpDepthChart"),
    cmpFrontierChart: document.getElementById("cmpFrontierChart"),
    cmpSides: document.getElementById("cmpSides"),
    problemSelector: document.getElementById("problemSelector"),
    algoSelector: document.getElementById("algoSelector"),
    vacRobotSelector: document.getElementById("vacRobotSelector"),
    vacDirtA: document.getElementById("vacDirtA"),
    vacDirtB: document.getElementById("vacDirtB"),
    codeTitle: document.getElementById("codeTitle"),
    frontierKind: document.getElementById("frontierKind"),
    axisOut: document.getElementById("axisOut"),
    axisIn: document.getElementById("axisIn"),
    stage: document.getElementById("stage"),
    optionsBtn: document.getElementById("optionsBtn"),
    optionsPanel: document.getElementById("optionsPanel"),
    stepModeSelector: document.getElementById("stepModeSelector"),
    analysisCard: document.getElementById("analysisCard"),
    curLabel: document.getElementById("curLabel"),
    chkExplored: document.getElementById("chkExplored"),
    chkFrontier: document.getElementById("chkFrontier"),
    chkGoal: document.getElementById("chkGoal"),
    checkVerdict: document.getElementById("checkVerdict"),
    movesRow: document.getElementById("movesRow"),
    kpiSkipped: document.getElementById("kpiSkipped"),
    sizeSelector: document.getElementById("sizeSelector"),
    presetSelect: document.getElementById("presetSelect"),
    shuffleSteps: document.getElementById("shuffleSteps"),
    shuffleBtn: document.getElementById("shuffleBtn"),
    editBoardBtn: document.getElementById("editBoardBtn"),
    graphSearchToggle: document.getElementById("graphSearchToggle"),
    earlyGoalToggle: document.getElementById("earlyGoalToggle"),
    maxNodesInput: document.getElementById("maxNodesInput"),
    runBtn: document.getElementById("runBtn"),
    alertBanner: document.getElementById("alertBanner"),

    firstBtn: document.getElementById("firstBtn"),
    prevBtn: document.getElementById("prevBtn"),
    playBtn: document.getElementById("playBtn"),
    nextBtn: document.getElementById("nextBtn"),
    lastBtn: document.getElementById("lastBtn"),
    stepSlider: document.getElementById("stepSlider"),
    stepCounter: document.getElementById("stepCounter"),
    speedSelect: document.getElementById("speedSelect"),

    eventBadge: document.getElementById("eventBadge"),
    eventMessage: document.getElementById("eventMessage"),
    solvabilityChip: document.getElementById("solvabilityChip"),

    curNodeBadge: document.getElementById("curNodeBadge"),
    curBoardContainer: document.getElementById("curBoardContainer"),
    moveArrowBadge: document.getElementById("moveArrowBadge"),
    moveLabel: document.getElementById("moveLabel"),
    candNodeBadge: document.getElementById("candNodeBadge"),
    candBoardContainer: document.getElementById("candBoardContainer"),
    goalBoardContainer: document.getElementById("goalBoardContainer"),

    modeSummaryTag: document.getElementById("modeSummaryTag"),
    codeLinesContainer: document.getElementById("codeLinesContainer"),
    localVarsContainer: document.getElementById("localVarsContainer"),

    frontierCountBadge: document.getElementById("frontierCountBadge"),
    exploredCountBadge: document.getElementById("exploredCountBadge"),
    frontierList: document.getElementById("frontierList"),
    exploredList: document.getElementById("exploredList"),

    pinnedNodeBar: document.getElementById("pinnedNodeBar"),
    pinnedTitle: document.getElementById("pinnedTitle"),
    pinnedBoard: document.getElementById("pinnedBoard"),
    pinnedMeta: document.getElementById("pinnedMeta"),
    pinnedLineage: document.getElementById("pinnedLineage"),
    jumpCreatedBtn: document.getElementById("jumpCreatedBtn"),
    jumpExpandedBtn: document.getElementById("jumpExpandedBtn"),
    closePinnedBtn: document.getElementById("closePinnedBtn"),

    treeViewport: document.getElementById("treeViewport"),
    treeSvg: document.getElementById("treeSvg"),
    treeZoomIn: document.getElementById("treeZoomIn"),
    treeZoomOut: document.getElementById("treeZoomOut"),
    treeZoomFit: document.getElementById("treeZoomFit"),
    showPrunedToggle: document.getElementById("showPrunedToggle"),

    kpiExpanded: document.getElementById("kpiExpanded"),
    kpiGenerated: document.getElementById("kpiGenerated"),
    kpiMaxFrontier: document.getElementById("kpiMaxFrontier"),
    kpiSolutionBranch: document.getElementById("kpiSolutionBranch"),
    memoryChartSvg: document.getElementById("memoryChartSvg"),
    solvFormula: document.getElementById("solvFormula"),
    solvExplanation: document.getElementById("solvExplanation"),
    solutionStripCard: document.getElementById("solutionStripCard"),
    solutionStrip: document.getElementById("solutionStrip"),

    editorModal: document.getElementById("editorModal"),
    closeEditorBtn: document.getElementById("closeEditorBtn"),
    cancelEditorBtn: document.getElementById("cancelEditorBtn"),
    applyEditorBtn: document.getElementById("applyEditorBtn"),
    resetGoalBtn: document.getElementById("resetGoalBtn"),
    editorBoardWrap: document.getElementById("editorBoardWrap"),
    editorStatus: document.getElementById("editorStatus"),
  };

  function cloneBoard(board) {
    return board.map((row) => row.slice());
  }

  function makeGoalBoard(size) {
    const out = [];
    let val = 1;
    for (let r = 0; r < size; r++) {
      const row = [];
      for (let c = 0; c < size; c++) {
        row.push(r === size - 1 && c === size - 1 ? 0 : val++);
      }
      out.push(row);
    }
    return out;
  }

  async function apiJson(url, options = {}) {
    const resp = await fetch(url, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
    const data = await resp.json();
    if (!resp.ok) {
      throw new Error(data.error || `Lỗi HTTP ${resp.status}`);
    }
    return data;
  }

  function showAlert(kind, title, detail, actionBtn = null) {
    els.alertBanner.className = `alert-banner ${kind ? "alert-" + kind : ""}`;
    els.alertBanner.innerHTML = "";
    const content = document.createElement("div");
    content.className = "alert-content";
    const strong = document.createElement("strong");
    strong.textContent = title;
    const span = document.createElement("span");
    span.textContent = detail;
    content.append(strong, span);
    els.alertBanner.appendChild(content);

    if (actionBtn) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = actionBtn.cls || "btn btn-danger btn-sm";
      btn.textContent = actionBtn.label;
      btn.addEventListener("click", actionBtn.onClick);
      els.alertBanner.appendChild(btn);
    }
    els.alertBanner.classList.remove("hidden");
  }

  function hideAlert() {
    els.alertBanner.classList.add("hidden");
    els.alertBanner.innerHTML = "";
  }

  function stopPlayback() {
    if (state.playTimer !== null) {
      clearInterval(state.playTimer);
      state.playTimer = null;
    }
    els.playBtn.textContent = "▶ Phát";
  }

  function togglePlayback() {
    if (!state.trace || !state.trace.steps.length) return;
    if (state.playTimer !== null) {
      stopPlayback();
      return;
    }
    if (state.currentStep >= state.trace.steps.length - 1) {
      state.currentStep = 0;
      renderStep();
    }
    els.playBtn.textContent = "⏸ Tạm dừng";
    const interval = Number(els.speedSelect.value) || 650;
    state.playTimer = setInterval(() => {
      if (!state.trace || state.currentStep >= state.trace.steps.length - 1) {
        stopPlayback();
        return;
      }
      if (!moveStep(1, state.stepMode === "macro")) stopPlayback();
    }, interval);
  }

  function setSize(newSize, selectMatchingPreset = true) {
    state.size = newSize;
    els.sizeSelector.querySelectorAll(".seg-btn").forEach((btn) => {
      btn.classList.toggle("active", Number(btn.dataset.size) === newSize);
    });
    state.targetBoard = makeGoalBoard(newSize);
    if (selectMatchingPreset) {
      const match = state.presets.find((p) => p.problem === "npuzzle" && p.size === newSize);
      if (match) {
        els.presetSelect.value = match.id;
        state.startBoard = cloneBoard(match.start_board);
        state.targetBoard = cloneBoard(match.target_board);
      } else {
        state.startBoard = makeGoalBoard(newSize);
      }
    }
  }

  const VAC_ROOMS = ["A", "B"];

  // Vẽ thế giới Vacuum: hai phòng cạnh nhau, robot (🤖) ở một phòng, phòng bẩn có bụi (🟤).
  function renderVacuum(container, st, opts = {}) {
    container.innerHTML = "";
    container.classList.remove("board-popped", "board-new", "board-dup", "board-goal", "puzzle-board-empty", "size-2", "size-3", "size-4");
    container.classList.add("vac-board");
    if (opts.boardCls) container.classList.add(opts.boardCls);
    container.style.gridTemplateColumns = "repeat(2, auto)";

    const changed = new Set(opts.changed || []);
    const dup = Boolean(opts.isCollision);
    VAC_ROOMS.forEach((name, i) => {
      const room = document.createElement("div");
      room.className = "room " + (st.dirt[i] ? "room-dirty" : "room-clean");
      if (changed.has(`dirt${i}`)) room.classList.add(dup ? "room-changed-dup" : "room-changed");

      const label = document.createElement("span");
      label.className = "room-name";
      label.textContent = `Phòng ${name}`;

      const body = document.createElement("span");
      body.className = "room-body";
      if (st.robot === i) {
        const robot = document.createElement("span");
        robot.className = "vac-robot" + (changed.has("robot") ? (dup ? " robot-moved-dup" : " robot-moved") : "");
        robot.textContent = "🤖";
        body.appendChild(robot);
      }
      const dirt = document.createElement("span");
      dirt.className = st.dirt[i] ? "vac-dirt" : "vac-clean";
      dirt.textContent = st.dirt[i] ? "🟤🟤" : "✨";
      body.appendChild(dirt);

      room.append(label, body);
      container.appendChild(room);
    });
  }

  // Một hàm vẽ cho mọi bài toán: ma trận (n-Puzzle) hay object {robot, dirt} (Vacuum).
  function renderState(container, st, opts = {}) {
    if (st && !Array.isArray(st)) {
      renderVacuum(container, st, opts);
    } else {
      renderBoard(container, st, opts);
    }
  }

  function renderBoard(container, matrix, opts = {}) {
    container.innerHTML = "";
    container.classList.remove("board-popped", "board-new", "board-dup", "board-goal", "vac-board");
    if (opts.boardCls) container.classList.add(opts.boardCls);
    if (!matrix) {
      container.classList.add("puzzle-board-empty");
      container.style.gridTemplateColumns = "";
      container.textContent = opts.emptyText || "—";
      return;
    }
    const size = matrix.length;
    container.classList.remove("puzzle-board-empty", "size-2", "size-3", "size-4");
    container.classList.add(`size-${size}`);
    container.style.gridTemplateColumns = `repeat(${size}, auto)`;

    const target = opts.targetBoard || null;
    const movedTile = opts.movedTile ?? null;
    const isCollision = Boolean(opts.isCollision);

    for (let r = 0; r < size; r++) {
      for (let c = 0; c < size; c++) {
        const val = matrix[r][c];
        const cell = document.createElement("div");
        cell.className = "puzzle-tile";
        if (val === 0) {
          cell.classList.add("tile-blank");
          cell.textContent = "0";
        } else {
          cell.textContent = String(val);
          if (isCollision && val === movedTile) {
            cell.classList.add("tile-collision");
          } else if (val === movedTile) {
            cell.classList.add("tile-moved");
          } else if (target && target[r][c] === val) {
            cell.classList.add("tile-correct");
          }
        }
        container.appendChild(cell);
      }
    }
  }

  function buildMiniMatrix(matrix) {
    const size = matrix.length;
    const wrap = document.createElement("div");
    wrap.className = `mini-board-cell size-${size}`;
    wrap.style.gridTemplateColumns = `repeat(${size}, auto)`;
    for (let r = 0; r < size; r++) {
      for (let c = 0; c < size; c++) {
        const val = matrix[r][c];
        const cell = document.createElement("div");
        cell.className = val === 0 ? "mini-cell blank" : "mini-cell";
        cell.textContent = val === 0 ? "0" : String(val);
        wrap.appendChild(cell);
      }
    }
    return wrap;
  }

  function buildMiniVacuum(st) {
    const wrap = document.createElement("div");
    wrap.className = "mini-board-cell vac";
    wrap.style.gridTemplateColumns = "repeat(2, auto)";
    VAC_ROOMS.forEach((name, i) => {
      const cell = document.createElement("div");
      cell.className = "mini-cell vac-cell" + (st.dirt[i] ? " dirty" : "");
      cell.textContent = `${name}${st.robot === i ? "🤖" : ""}${st.dirt[i] ? "🟤" : ""}`;
      wrap.appendChild(cell);
    });
    return wrap;
  }

  function buildMiniBoard(st) {
    return Array.isArray(st) ? buildMiniMatrix(st) : buildMiniVacuum(st);
  }

  function renderGoal(trace) {
    const box = els.goalBoardContainer;
    if (trace.problem === "vacuum") {
      box.className = "goal-text";
      box.style.gridTemplateColumns = "";
      box.textContent = trace.goal_description || "";
    } else {
      box.className = "puzzle-board puzzle-board-mini";
      renderBoard(box, trace.target_board);
    }
  }

  function renderCodePanel(sourceLines, activeLine, eventType, localVars) {
    els.codeLinesContainer.innerHTML = "";
    const activeCls =
      eventType === "skip_explored" || eventType === "skip_frontier" || eventType === "failure"
        ? "active-rose"
        : eventType === "goal_early" || eventType === "goal_late" || eventType === "goal_init"
        ? "active-emerald"
        : "active";

    for (const item of sourceLines) {
      const row = document.createElement("div");
      row.className = "code-line" + (item.line === activeLine ? ` ${activeCls}` : "");
      const num = document.createElement("span");
      num.className = "line-num";
      num.textContent = String(item.line);
      const code = document.createElement("span");
      code.textContent = item.code;
      row.append(num, code);
      els.codeLinesContainer.appendChild(row);
    }

    els.localVarsContainer.innerHTML = "";
    const entries = Object.entries(localVars || {});
    if (!entries.length) {
      const empty = document.createElement("span");
      empty.className = "meta-muted";
      empty.textContent = "—";
      els.localVarsContainer.appendChild(empty);
      return;
    }
    for (const [k, v] of entries) {
      const chip = document.createElement("span");
      chip.className = "var-chip";
      chip.textContent = `${k} = ${v}`;
      els.localVarsContainer.appendChild(chip);
    }
  }

  function createNodeCard(node, { cls = "", tag = null, clickable = true } = {}) {
    const card = document.createElement("div");
    card.className = "node-card" + (cls ? ` ${cls}` : "");
    card.title =
      node.parent_id === null
        ? `Nút gốc #${node.id}`
        : `Nút #${node.id} · tầng ${node.depth} · ${node.action} từ #${node.parent_id}`;

    const top = document.createElement("div");
    top.className = "node-card-top";
    const idSpan = document.createElement("span");
    idSpan.textContent = `#${node.id}`;
    const depthSpan = document.createElement("span");
    depthSpan.textContent = `d${node.depth}`;
    top.append(idSpan, depthSpan);
    card.append(top, buildMiniBoard(node.state));

    if (tag) {
      const foot = document.createElement("div");
      foot.className = "node-card-foot";
      const pill = document.createElement("span");
      pill.className = `node-tag-pill ${tag.cls}`;
      pill.textContent = tag.text;
      foot.appendChild(pill);
      card.appendChild(foot);
    }

    if (clickable) {
      card.tabIndex = 0;
      card.setAttribute("role", "button");
      card.setAttribute("aria-label", `Nút #${node.id}, tầng ${node.depth}`);
      card.addEventListener("click", () => selectPinnedNode(node.id));
      card.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          selectPinnedNode(node.id);
        }
      });
    }
    return card;
  }

  function makePlaceholder(text) {
    const p = document.createElement("div");
    p.className = "empty-placeholder";
    p.textContent = text;
    return p;
  }

  // Cuộn riêng container để thẻ nổi bật luôn nằm trong tầm nhìn (không cuộn cả trang).
  function revealInside(container, el) {
    if (!el) return;
    const c = container.getBoundingClientRect();
    const r = el.getBoundingClientRect();
    if (r.bottom > c.bottom) container.scrollTop += r.bottom - c.bottom + 8;
    else if (r.top < c.top) container.scrollTop -= c.top - r.top + 8;
    if (r.right > c.right) container.scrollLeft += r.right - c.right + 8;
    else if (r.left < c.left) container.scrollLeft -= c.left - r.left + 8;
  }

  // Dải thẻ dùng chung cho frontier và explored. Phần giữa rút gọn thành "⋯ N nút ⋯",
  // nhưng thẻ đang nổi bật (mới / trùng) luôn được giữ lại.
  const QUEUE_HEAD = 4;
  const QUEUE_TAIL = 4;
  const EXPLORED_TAIL = 6;

  function renderCardStrip(box, ids, nodes, { head, tail, optsFor, prepend = null, append = null, emptyText }) {
    box.innerHTML = "";
    if (prepend) box.appendChild(prepend);
    if (!ids.length) {
      box.appendChild(makePlaceholder(emptyText));
      if (append) box.appendChild(append);
      return;
    }
    const n = ids.length;
    const visible = new Set();
    for (let i = 0; i < Math.min(head, n); i++) visible.add(i);
    for (let i = Math.max(0, n - tail); i < n; i++) visible.add(i);
    ids.forEach((id, i) => {
      if (optsFor(id, i).highlight) visible.add(i);
    });

    let prev = -1;
    let focusEl = null;
    for (const i of [...visible].sort((a, b) => a - b)) {
      if (i > prev + 1) {
        const gap = document.createElement("div");
        gap.className = "queue-gap";
        gap.textContent = `⋯ ${i - prev - 1} nút ⋯`;
        box.appendChild(gap);
      }
      const opts = optsFor(ids[i], i);
      const card = createNodeCard(nodes[ids[i]], opts);
      box.appendChild(card);
      if (opts.highlight) focusEl = card;
      prev = i;
    }
    if (append) box.appendChild(append);
    revealInside(box, append || focusEl);
  }

  function renderFrontierStrip(step, nodes, algorithm) {
    const labels = ALGO_LABELS[algorithm] || ALGO_LABELS.bfs;
    const dfs = algorithm === "dfs";
    const ev = step.event_type;
    const popId = ev === "dequeue" ? step.cur_id : null;
    const newId = ev === "enqueue" || ev === "init" ? step.candidate_id : null;
    const dupId = ev === "skip_frontier" ? step.collision_id : null;
    const ids = step.frontier_ids;
    // Hàng đợi: nút kế tiếp ở ĐẦU (trái). Ngăn xếp: nút kế tiếp ở ĐỈNH (phải).
    const nextIdx = dfs ? ids.length - 1 : 0;

    // "Bóng" của nút vừa pop: nằm đúng chỗ nó vừa rời khỏi frontier.
    const ghost =
      popId !== null
        ? createNodeCard(nodes[popId], {
            cls: "card-popped",
            tag: { text: "POP ↓", cls: "pill-amber" },
            clickable: false,
          })
        : null;

    renderCardStrip(els.frontierList, ids, nodes, {
      head: QUEUE_HEAD,
      tail: QUEUE_TAIL,
      prepend: dfs ? null : ghost,
      append: dfs ? ghost : null,
      emptyText: `${labels.container} ${popId !== null ? "vừa cạn." : "đang rỗng."}`,
      optsFor: (id, i) => {
        const q = activePredictQuestion();
        if (q && q.type === "pop") {
          // Đang hỏi "nút nào pop tiếp": che nhãn gợi ý và biến mỗi thẻ thành một lựa chọn.
          if (!q.answered) return { cls: "predict-choice" };
          if (id === q.answerId) return { cls: "predict-right", tag: { text: "ĐÁP ÁN", cls: "pill-emerald" }, highlight: true };
          if (id === q.choice) return { cls: "predict-wrong", tag: { text: "BẠN CHỌN", cls: "pill-rose" }, highlight: true };
          return {};
        }
        if (id === dupId) return { cls: "card-collision", tag: { text: "TRÙNG!", cls: "pill-rose" }, highlight: true };
        if (id === newId) return { cls: "card-new", tag: { text: "MỚI", cls: "pill-emerald" }, highlight: true };
        if (i === nextIdx && popId === null) return { cls: "card-front", tag: { text: labels.next, cls: "pill-amber" } };
        return {};
      },
    });
  }

  function renderExploredStrip(step, nodes, cfg) {
    const ev = step.event_type;
    const newId = ev === "explore" ? step.cur_id : null;
    const dupId = ev === "skip_explored" ? step.collision_id : null;
    renderCardStrip(els.exploredList, step.explored_ids, nodes, {
      head: 0,
      tail: EXPLORED_TAIL,
      emptyText: cfg.graph_search ? "Chưa có trạng thái nào được mở rộng xong." : "Tree Search: không có tập explored!",
      optsFor: (id) => {
        if (id === dupId) return { cls: "card-collision", tag: { text: "TRÙNG!", cls: "pill-rose" }, highlight: true };
        if (id === newId) return { cls: "card-new", tag: { text: "MỚI", cls: "pill-emerald" }, highlight: true };
        return {};
      },
    });
  }

  function getLineageIds(nodeId) {
    if (!state.trace || nodeId === null || nodeId === undefined) return [];
    const nodes = state.trace.nodes;
    const ids = [];
    let curr = nodes[nodeId];
    while (curr) {
      ids.push(curr.id);
      curr = curr.parent_id !== null ? nodes[curr.parent_id] : null;
    }
    ids.reverse();
    return ids;
  }

  function selectPinnedNode(nodeId) {
    if (state.trace && state.trace.compare) return; // thẻ ở chế độ so sánh chỉ để xem

    // Khi đang có câu hỏi dự đoán, bấm vào thẻ nghĩa là TRẢ LỜI, không phải xem chi tiết.
    const q = activePredictQuestion();
    if (q && !q.answered) {
      if (q.type === "pop" && state.trace.steps[state.currentStep].frontier_ids.includes(nodeId)) {
        answerPredict(nodeId);
      } else {
        flashCaption();
      }
      return;
    }

    state.pinnedNodeId = nodeId;
    renderPinnedNode();
    if (state.pinnedNodeId !== null) {
      els.pinnedNodeBar.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
    renderSearchTree();
  }

  function renderPinnedNode() {
    if (!state.trace || state.pinnedNodeId === null || !state.trace.nodes[state.pinnedNodeId]) {
      els.pinnedNodeBar.classList.add("hidden");
      return;
    }
    const node = state.trace.nodes[state.pinnedNodeId];
    els.pinnedNodeBar.classList.remove("hidden");
    els.pinnedTitle.textContent = `Chi tiết nút #${node.id}${node.is_duplicate ? ` (Bị cắt — trùng #${node.duplicate_of} ở ${node.duplicate_reason})` : ""}`;
    renderState(els.pinnedBoard, node.state, {
      targetBoard: state.trace.target_board,
      movedTile: node.moved_tile,
      changed: node.changed,
      isCollision: node.is_duplicate,
    });

    els.pinnedMeta.innerHTML = "";
    const metaItems = [
      `depth=${node.depth}`,
      `action=${node.action || "ROOT"}`,
      `parent=${node.parent_id !== null ? "#" + node.parent_id : "None"}`,
    ];
    if (node.manhattan !== undefined && node.manhattan !== null) {
      metaItems.push(`h₁(Manhattan)=${node.manhattan}`, `h₀(Misplaced)=${node.misplaced}`, `inversions=${node.inversions}`);
    }
    for (const m of metaItems) {
      const sp = document.createElement("span");
      sp.className = "var-chip";
      sp.textContent = m;
      els.pinnedMeta.appendChild(sp);
    }

    const lineage = getLineageIds(node.id);
    els.pinnedLineage.textContent = "Đường từ gốc: " + lineage.map((id) => {
      const n = state.trace.nodes[id];
      return n.action ? `${MOVE_ARROWS[n.action]} #${id}` : `#${id}`;
    }).join("  ");

    els.jumpCreatedBtn.disabled = node.created_step === null || node.created_step === undefined;
    els.jumpExpandedBtn.disabled = node.expanded_step === null || node.expanded_step === undefined;
  }

  // ── Cây tìm kiếm: dùng chung cho chế độ thường và cho hai cây nhỏ khi so sánh ──

  function lineageOf(trace, nodeId) {
    const ids = [];
    let curr = trace.nodes[nodeId];
    while (curr) {
      ids.push(curr.id);
      curr = curr.parent_id !== null ? trace.nodes[curr.parent_id] : null;
    }
    return ids.reverse();
  }

  // Thứ tự mở rộng (1, 2, 3, ...) của từng nút theo thời điểm nó bị pop khỏi frontier.
  function expandRanks(trace) {
    if (!trace._ranks) {
      const expanded = trace.nodes
        .filter((n) => n.expanded_step !== null && n.expanded_step !== undefined)
        .sort((a, b) => a.expanded_step - b.expanded_step);
      trace._ranks = new Map(expanded.map((n, i) => [n.id, i + 1]));
    }
    return trace._ranks;
  }

  function fitTransform(svg, bounds) {
    const rect = svg.getBoundingClientRect();
    const vw = rect.width || 640;
    const vh = rect.height || 320;
    const bw = Math.max(bounds.width, 200);
    const bh = Math.max(bounds.height, 160);
    const scale = Math.min(1.15, Math.max(0.1, Math.min((vw - 24) / bw, (vh - 24) / bh)));
    return { scale, x: Math.max(12, (vw - bw * scale) / 2), y: 12 };
  }

  const SVG_NS = "http://www.w3.org/2000/svg";
  function svgEl(tag, attrs = {}) {
    const el = document.createElementNS(SVG_NS, tag);
    for (const [key, val] of Object.entries(attrs)) el.setAttribute(key, String(val));
    return el;
  }

  // Vẽ cây tại bước stepIdx của một trace. o: { transform|null (null = tự vừa khung), pinnedId,
  // showPruned, interactive }. Trả về { bounds, transform }.
  function drawSearchTree(svg, trace, stepIdx, o = {}) {
    svg.innerHTML = "";
    const step = trace.steps[stepIdx];
    const nodes = trace.nodes;
    const showPruned = o.showPruned !== false;

    // Nút con chỉ bị coi là "trùng" từ bước kiểm tra trở đi (không tiết lộ trước).
    const isDupNow = (n) => n.is_duplicate && stepIdx >= (n.resolved_step ?? n.created_step);
    const visibleNodes = nodes.filter((n) => n.created_step <= stepIdx && (showPruned || !isDupNow(n)));

    const MAX_TREE_NODES = 280;
    const capped = visibleNodes.length > MAX_TREE_NODES;
    const drawNodes = capped ? visibleNodes.slice(0, MAX_TREE_NODES) : visibleNodes;
    const drawIdSet = new Set(drawNodes.map((n) => n.id));

    const childrenMap = new Map();
    for (const n of drawNodes) childrenMap.set(n.id, []);
    for (const n of drawNodes) {
      if (n.parent_id !== null && childrenMap.has(n.parent_id)) childrenMap.get(n.parent_id).push(n.id);
    }

    const NODE_DX = 64;
    const LEVEL_DY = 74;
    const PAD_X = 48;
    const PAD_Y = 44;
    const pos = new Map();
    let leafCursor = 0;

    function layout(nodeId) {
      const kids = childrenMap.get(nodeId) || [];
      const depth = nodes[nodeId].depth;
      if (kids.length === 0) {
        const x = PAD_X + leafCursor * NODE_DX;
        leafCursor += 1;
        pos.set(nodeId, { x, y: PAD_Y + depth * LEVEL_DY });
        return x;
      }
      const xs = kids.map((k) => layout(k));
      const midX = (xs[0] + xs[xs.length - 1]) / 2;
      pos.set(nodeId, { x: midX, y: PAD_Y + depth * LEVEL_DY });
      return midX;
    }
    if (drawIdSet.has(0)) layout(0);

    let maxX = 400;
    let maxY = 260;
    for (const pt of pos.values()) {
      if (pt.x + PAD_X > maxX) maxX = pt.x + PAD_X;
      if (pt.y + PAD_Y > maxY) maxY = pt.y + PAD_Y;
    }
    const bounds = { width: maxX, height: maxY };
    const tf = o.transform || fitTransform(svg, bounds);
    const showText = tf.scale >= 0.4; // quá nhỏ thì bỏ chữ, chỉ giữ màu

    const gRoot = svgEl("g", { transform: `translate(${tf.x}, ${tf.y}) scale(${tf.scale})` });
    svg.appendChild(gRoot);

    const frontierSet = new Set(step.frontier_ids);
    const exploredSet = new Set(step.explored_ids);
    const solutionSet = new Set(step.solution_ids || []);
    const pinnedLineage = new Set(o.pinnedId !== null && o.pinnedId !== undefined ? lineageOf(trace, o.pinnedId) : []);
    const ranks = expandRanks(trace);

    // Đường kẻ theo tầng
    const maxDepthDrawn = drawNodes.reduce((acc, n) => Math.max(acc, n.depth), 0);
    for (let d = 0; d <= maxDepthDrawn; d++) {
      const y = PAD_Y + d * LEVEL_DY;
      gRoot.appendChild(svgEl("line", { x1: 10, x2: maxX - 10, y1: y, y2: y, stroke: "#e2e8f0", "stroke-dasharray": "3 4" }));
      if (showText) {
        const dLbl = svgEl("text", { x: 12, y: y - 6, "font-size": 10, "font-family": "var(--font-mono)", fill: "#94a3b8" });
        dLbl.textContent = `d=${d}`;
        gRoot.appendChild(dLbl);
      }
    }

    // Cạnh
    for (const n of drawNodes) {
      if (n.parent_id === null || !pos.has(n.parent_id) || !pos.has(n.id)) continue;
      const p1 = pos.get(n.parent_id);
      const p2 = pos.get(n.id);
      const isSolEdge = solutionSet.has(n.id) && solutionSet.has(n.parent_id);
      const isPinEdge = pinnedLineage.has(n.id) && pinnedLineage.has(n.parent_id);
      const line = svgEl("line", {
        x1: p1.x, y1: p1.y, x2: p2.x, y2: p2.y,
        stroke: isSolEdge ? "#059669" : isPinEdge ? "#4f46e5" : isDupNow(n) ? "#fda4af" : "#cbd5e1",
        "stroke-width": isSolEdge || isPinEdge ? 2.6 : 1.4,
      });
      if (isDupNow(n)) line.setAttribute("stroke-dasharray", "4 3");
      gRoot.appendChild(line);

      if (n.action && showText) {
        const lbl = svgEl("text", { x: (p1.x + p2.x) / 2 + 4, y: (p1.y + p2.y) / 2 + 3, "font-size": 10, fill: isSolEdge ? "#047857" : "#64748b" });
        lbl.textContent = MOVE_ARROWS[n.action] || "";
        gRoot.appendChild(lbl);
      }
    }

    // Nút
    for (const n of drawNodes) {
      const pt = pos.get(n.id);
      if (!pt) continue;
      const g = svgEl("g", { class: o.interactive ? "tree-node-g" : "" });
      if (o.interactive) {
        g.addEventListener("click", (e) => {
          e.stopPropagation();
          selectPinnedNode(n.id);
        });
      }

      let fill = "#ffffff";
      let stroke = "#94a3b8";
      let textFill = "#0f172a";
      let sw = 1.6;
      let dashed = false;

      if (solutionSet.has(n.id)) {
        fill = "#10b981"; stroke = "#047857"; textFill = "#ffffff"; sw = 2.2;
      } else if (n.id === step.cur_id) {
        fill = "#4f46e5"; stroke = "#312e81"; textFill = "#ffffff"; sw = 2.4;
      } else if (n.id === step.collision_id) {
        fill = "#ffe4e6"; stroke = "#e11d48"; textFill = "#9f1239"; sw = 2.5;
      } else if (isDupNow(n)) {
        fill = "#fff1f2"; stroke = "#f43f5e"; textFill = "#be123c"; dashed = true;
      } else if (n.id === step.candidate_id && n.parent_id !== null && step.event_type === "enqueue") {
        fill = "#ecfdf5"; stroke = "#10b981"; textFill = "#065f46"; sw = 2.2;
      } else if (n.id === step.candidate_id && n.parent_id !== null) {
        fill = "#fef9c3"; stroke = "#eab308"; textFill = "#713f12"; sw = 2.2;
      } else if (frontierSet.has(n.id)) {
        fill = "#fffbeb"; stroke = "#f59e0b"; textFill = "#92400e"; sw = 1.8;
      } else if (exploredSet.has(n.id)) {
        fill = "#f0f9ff"; stroke = "#0ea5e9"; textFill = "#075985";
      }
      if (n.id === o.pinnedId) sw = 3;

      const circle = svgEl("circle", { cx: pt.x, cy: pt.y, r: 17, fill, stroke, "stroke-width": sw });
      if (dashed) circle.setAttribute("stroke-dasharray", "3 2");
      g.appendChild(circle);

      if (showText) {
        const text = svgEl("text", {
          x: pt.x, y: pt.y + 4, "text-anchor": "middle", "font-size": 10.5, "font-weight": 700,
          "font-family": "var(--font-mono)", fill: textFill,
        });
        text.textContent = isDupNow(n) ? `#${n.id}✕` : `#${n.id}`;
        g.appendChild(text);

        // Huy hiệu thứ tự mở rộng: nút nào được pop trước, nút nào sau
        if (n.expanded_step !== null && n.expanded_step !== undefined && n.expanded_step <= stepIdx && ranks.has(n.id)) {
          g.appendChild(svgEl("circle", { cx: pt.x + 14, cy: pt.y - 14, r: 7.5, fill: "#0f172a" }));
          const rk = svgEl("text", { x: pt.x + 14, y: pt.y - 11, "text-anchor": "middle", "font-size": 8, "font-weight": 700, fill: "#ffffff" });
          rk.textContent = String(ranks.get(n.id));
          g.appendChild(rk);
        }
      }

      const title = svgEl("title");
      title.textContent = isDupNow(n)
        ? `Nút #${n.id} (BỊ CẮT - trùng #${n.duplicate_of} trong ${n.duplicate_reason})`
        : `Nút #${n.id} | tầng ${n.depth} | ${n.action || "ROOT"}${ranks.has(n.id) && n.expanded_step <= stepIdx ? ` | mở rộng thứ ${ranks.get(n.id)}` : ""}${n.manhattan != null ? " | Manhattan=" + n.manhattan : ""}`;
      g.appendChild(title);
      gRoot.appendChild(g);
    }

    if (capped) {
      const note = svgEl("text", { x: 14, y: 20, "font-size": 11, fill: "#b45309" });
      note.textContent = `Cây có ${visibleNodes.length} nút (đang hiển thị ${MAX_TREE_NODES} nút đầu tiên để giữ tốc độ mượt).`;
      svg.appendChild(note);
    }
    return { bounds, transform: tf };
  }

  function renderSearchTree() {
    const svg = els.treeSvg;
    const trace = state.trace;
    if (!trace || !trace.steps.length || trace.compare) {
      svg.innerHTML = "";
      return;
    }
    const res = drawSearchTree(svg, trace, state.currentStep, {
      transform: state.treeAutoFit ? null : state.treeTransform,
      pinnedId: state.pinnedNodeId,
      showPruned: els.showPrunedToggle.checked,
      interactive: true,
    });
    state.treeBounds = res.bounds;
    if (state.treeAutoFit) state.treeTransform = res.transform;
  }

  function fitTreeToViewport() {
    state.treeAutoFit = true;
    renderSearchTree();
  }

  // ── Đồ thị không gian trạng thái của Vacuum (8 trạng thái) ──
  // Hai hàng = vị trí robot (A / B). Bốn cột = tổ hợp bụi, xếp thành vòng để các cạnh "Hút bụi" liền kề nhau.
  const VG = { cols: ["TT", "FT", "FF", "TF"], x0: 75, dx: 135, yA: 78, yB: 168, w: 84, h: 46 };
  const VG_ACTIONS = ["Trái", "Phải", "Hút bụi"];
  const VG_KEYS = [0, 1].flatMap((r) => VG.cols.map((c) => `${r}${c}`));
  const VG_COLORS = { gray: "#94a3b8", indigo: "#4f46e5", emerald: "#10b981", rose: "#f43f5e", sol: "#059669" };

  const vgKey = (st) => `${st.robot}${st.dirt[0] ? "T" : "F"}${st.dirt[1] ? "T" : "F"}`;
  function vgPos(key) {
    const col = VG.cols.indexOf(key.slice(1));
    return { x: VG.x0 + col * VG.dx, y: key[0] === "0" ? VG.yA : VG.yB };
  }
  function vgNext(key, action) {
    let r = Number(key[0]);
    let a = key[1] === "T";
    let b = key[2] === "T";
    if (action === "Trái") r = 0;
    else if (action === "Phải") r = 1;
    else if (r === 0) a = false;
    else b = false;
    return `${r}${a ? "T" : "F"}${b ? "T" : "F"}`;
  }

  function vgEdge(from, action) {
    const to = vgNext(from, action);
    const p1 = vgPos(from);
    const p2 = vgPos(to);
    const { w, h } = VG;
    if (action === "Phải") {
      const x = p1.x - 14;
      return { d: `M ${x} ${p1.y + h / 2} L ${x} ${p2.y - h / 2}`, lx: x - 5, ly: (p1.y + p2.y) / 2 + 3, anchor: "end", label: "Phải" };
    }
    if (action === "Trái") {
      const x = p1.x + 14;
      return { d: `M ${x} ${p1.y - h / 2} L ${x} ${p2.y + h / 2}`, lx: x + 5, ly: (p1.y + p2.y) / 2 + 3, anchor: "start", label: "Trái" };
    }
    if (Math.abs(p1.x - p2.x) <= VG.dx + 1) {
      const sign = p2.x > p1.x ? 1 : -1;
      return { d: `M ${p1.x + (sign * w) / 2} ${p1.y} L ${p2.x - (sign * w) / 2} ${p2.y}`, lx: (p1.x + p2.x) / 2, ly: p1.y - 7, anchor: "middle", label: "🧹" };
    }
    // Cạnh dài (nối hai đầu của vòng): vẽ cung cong về phía ngoài hàng.
    const down = key0(from) === "1";
    const y0 = p1.y + (down ? h / 2 : -h / 2);
    const bow = down ? 48 : -48;
    return { d: `M ${p1.x} ${y0} C ${p1.x} ${y0 + bow}, ${p2.x} ${y0 + bow}, ${p2.x} ${y0}`, lx: (p1.x + p2.x) / 2, ly: y0 + (down ? 38 : -32), anchor: "middle", label: "🧹" };
  }
  const key0 = (key) => key[0];

  function drawVacuumGraph(svg, trace, stepIdx) {
    svg.innerHTML = "";
    svg.setAttribute("viewBox", "0 0 560 240");
    const step = trace.steps[stepIdx];
    const nodes = trace.nodes;
    const ev = step.event_type;
    const keyOf = (id) => vgKey(nodes[id].state);
    const exploredKeys = new Set(step.explored_ids.map(keyOf));
    const frontierKeys = new Set(step.frontier_ids.map(keyOf));
    const curKey = step.cur_id !== null && step.cur_id !== undefined ? keyOf(step.cur_id) : null;

    // Phép thử hiện tại (nút con đang xét): cạnh từ trạng thái cha tới trạng thái con
    const childShown = step.candidate_id !== null && step.candidate_id !== undefined && CHILD_EVENTS.has(ev);
    let active = null;
    if (childShown) {
      const cand = nodes[step.candidate_id];
      const from = keyOf(cand.parent_id);
      const tone = ev.startsWith("skip") ? "rose" : ev === "enqueue" || ev === "goal_early" ? "emerald" : "indigo";
      active = { from, action: cand.action, to: keyOf(cand.id), tone };
    }
    const candKey = active ? active.to : null;

    // Cạnh thuộc đường lời giải
    const solEdges = new Set();
    const sol = step.solution_ids || [];
    for (let i = 1; i < sol.length; i++) solEdges.add(`${keyOf(sol[i - 1])}|${nodes[sol[i]].action}`);

    // Số nút trong cây ứng với mỗi trạng thái, và thứ tự mở rộng đầu tiên
    const counts = {};
    const minRank = {};
    const ranks = expandRanks(trace);
    for (const n of nodes) {
      if (n.created_step > stepIdx) continue;
      const k = vgKey(n.state);
      counts[k] = (counts[k] || 0) + 1;
      if (n.expanded_step !== null && n.expanded_step !== undefined && n.expanded_step <= stepIdx) {
        minRank[k] = Math.min(minRank[k] ?? Infinity, ranks.get(n.id));
      }
    }

    // Mũi tên
    const defs = svgEl("defs");
    for (const [name, color] of Object.entries(VG_COLORS)) {
      const m = svgEl("marker", { id: `vgm-${name}`, viewBox: "0 0 10 10", refX: 9, refY: 5, markerWidth: 7, markerHeight: 7, orient: "auto-start-reverse" });
      m.appendChild(svgEl("path", { d: "M 0 0 L 10 5 L 0 10 z", fill: color }));
      defs.appendChild(m);
    }
    svg.appendChild(defs);

    // Hai dải nền theo vị trí robot
    for (const [row, y, label] of [[0, VG.yA, "Robot ở A"], [1, VG.yB, "Robot ở B"]]) {
      svg.appendChild(svgEl("rect", { x: 2, y: y - 42, width: 556, height: 84, rx: 10, fill: row === 0 ? "#f8fafc" : "#f1f5f9" }));
      const t = svgEl("text", { x: 13, y, "text-anchor": "middle", "font-size": 10, fill: "#94a3b8", "font-weight": 700, transform: `rotate(-90 13 ${y})` });
      t.textContent = label;
      svg.appendChild(t);
    }

    // Cạnh (bỏ qua các cạnh tự trỏ về chính nó: vẽ thành huy hiệu ↺)
    for (const key of VG_KEYS) {
      for (const action of VG_ACTIONS) {
        if (vgNext(key, action) === key) continue;
        const e = vgEdge(key, action);
        const isSol = solEdges.has(`${key}|${action}`);
        const isActive = active && active.from === key && active.action === action;
        const color = isSol ? "sol" : isActive ? active.tone : "gray";
        const path = svgEl("path", {
          d: e.d, fill: "none", stroke: VG_COLORS[color],
          "stroke-width": isSol ? 3.5 : isActive ? 3 : 1.5,
          "marker-end": `url(#vgm-${color})`,
        });
        if (isActive && active.tone === "rose") path.setAttribute("stroke-dasharray", "5 3");
        svg.appendChild(path);
        const lbl = svgEl("text", { x: e.lx, y: e.ly, "text-anchor": e.anchor, "font-size": e.label === "🧹" ? 12 : 9, fill: VG_COLORS[color === "gray" ? "gray" : color], "font-weight": isActive || isSol ? 700 : 400 });
        lbl.textContent = e.label;
        svg.appendChild(lbl);
      }
    }

    // Huy hiệu vòng lặp ↺ (hành động không đổi trạng thái)
    for (const key of VG_KEYS) {
      const loops = VG_ACTIONS.filter((a) => vgNext(key, a) === key);
      if (!loops.length) continue;
      const pt = vgPos(key);
      const up = key[0] === "0";
      const y = pt.y + (up ? -VG.h / 2 - 10 : VG.h / 2 + 12);
      const hot = active && active.from === key && active.to === key;
      const txt = `↺ ${loops.map((a) => (a === "Trái" ? "←" : a === "Phải" ? "→" : "🧹")).join(" ")}`;
      svg.appendChild(svgEl("rect", { x: pt.x - 29, y: y - 10, width: 58, height: 16, rx: 8, fill: hot ? "#ffe4e6" : "#ffffff", stroke: hot ? "#f43f5e" : "#cbd5e1" }));
      const t = svgEl("text", { x: pt.x, y: y + 2, "text-anchor": "middle", "font-size": 10, fill: hot ? "#be123c" : "#64748b", "font-weight": hot ? 700 : 400 });
      t.textContent = txt;
      svg.appendChild(t);
    }

    // Nút (trạng thái)
    for (const key of VG_KEYS) {
      const pt = vgPos(key);
      const robot = Number(key[0]);
      const dirty = [key[1] === "T", key[2] === "T"];
      const isGoal = !dirty[0] && !dirty[1];
      let fill = "#ffffff";
      let stroke = "#cbd5e1";
      let sw = 1.6;
      if (exploredKeys.has(key)) { fill = "#f0f9ff"; stroke = "#0ea5e9"; }
      else if (frontierKeys.has(key)) { fill = "#fffbeb"; stroke = "#f59e0b"; }
      if (candKey === key) { stroke = VG_COLORS[active.tone]; sw = 3; }
      if (curKey === key) { stroke = "#4f46e5"; fill = "#eef2ff"; sw = 3.4; }

      const g = svgEl("g");
      if (isGoal) g.appendChild(svgEl("rect", { x: pt.x - VG.w / 2 - 4, y: pt.y - VG.h / 2 - 4, width: VG.w + 8, height: VG.h + 8, rx: 11, fill: "none", stroke: "#10b981", "stroke-width": 1.4, "stroke-dasharray": "4 3" }));
      g.appendChild(svgEl("rect", { x: pt.x - VG.w / 2, y: pt.y - VG.h / 2, width: VG.w, height: VG.h, rx: 8, fill, stroke, "stroke-width": sw }));
      [0, 1].forEach((i) => {
        const cx = pt.x - VG.w / 2 + 4 + i * 38;
        const cy = pt.y - VG.h / 2 + 4;
        g.appendChild(svgEl("rect", { x: cx, y: cy, width: 36, height: VG.h - 8, rx: 5, fill: dirty[i] ? "#fdf6e7" : "#ecfdf5", stroke: dirty[i] ? "#d4a76a" : "#a7f3d0" }));
        const nm = svgEl("text", { x: cx + 3, y: cy + 9, "font-size": 8, fill: "#94a3b8", "font-weight": 700 });
        nm.textContent = i === 0 ? "A" : "B";
        g.appendChild(nm);
        if (robot === i) {
          const r = svgEl("text", { x: cx + 5, y: cy + 29, "font-size": 15 });
          r.textContent = "🤖";
          g.appendChild(r);
        }
        const d = svgEl("text", { x: cx + (robot === i ? 22 : 12), y: cy + 28, "font-size": 13 });
        d.textContent = dirty[i] ? "🟤" : "✨";
        g.appendChild(d);
      });
      if (isGoal) {
        const flag = svgEl("text", { x: pt.x + VG.w / 2 - 2, y: pt.y + VG.h / 2 + 14, "text-anchor": "end", "font-size": 11 });
        flag.textContent = "🎯";
        g.appendChild(flag);
      }
      if ((counts[key] || 0) > 1) {
        g.appendChild(svgEl("rect", { x: pt.x - VG.w / 2 - 4, y: pt.y - VG.h / 2 - 8, width: 26, height: 15, rx: 7, fill: "#64748b" }));
        const c = svgEl("text", { x: pt.x - VG.w / 2 + 9, y: pt.y - VG.h / 2 + 3, "text-anchor": "middle", "font-size": 9, "font-weight": 700, fill: "#ffffff" });
        c.textContent = `×${counts[key]}`;
        g.appendChild(c);
      }
      if (minRank[key] !== undefined) {
        g.appendChild(svgEl("circle", { cx: pt.x + VG.w / 2, cy: pt.y - VG.h / 2, r: 8, fill: "#0f172a" }));
        const rk = svgEl("text", { x: pt.x + VG.w / 2, y: pt.y - VG.h / 2 + 3, "text-anchor": "middle", "font-size": 8.5, "font-weight": 700, fill: "#ffffff" });
        rk.textContent = String(minRank[key]);
        g.appendChild(rk);
      }
      const title = svgEl("title");
      title.textContent = `Robot ở ${robot === 0 ? "A" : "B"} · phòng A ${dirty[0] ? "bẩn" : "sạch"} · phòng B ${dirty[1] ? "bẩn" : "sạch"}${counts[key] ? ` · ${counts[key]} nút trong cây` : ""}`;
      g.appendChild(title);
      svg.appendChild(g);
    }
  }

  function renderMemoryChart() {
    const svg = els.memoryChartSvg;
    svg.innerHTML = "";
    if (!state.trace || !state.trace.steps.length) return;

    const steps = state.trace.steps;
    const W = 640;
    const H = 210;
    const padL = 42;
    const padR = 16;
    const padT = 16;
    const padB = 26;
    const plotW = W - padL - padR;
    const plotH = H - padT - padB;

    let maxVal = 1;
    for (const s of steps) {
      maxVal = Math.max(maxVal, s.metrics.frontier_size, s.metrics.explored_size);
    }

    const NS = "http://www.w3.org/2000/svg";
    const xOf = (i) => padL + (steps.length <= 1 ? 0 : (i / (steps.length - 1)) * plotW);
    const yOf = (v) => padT + plotH - (v / maxVal) * plotH;

    // Horizontal grid lines
    for (let g = 0; g <= 4; g++) {
      const v = Math.round((maxVal * g) / 4);
      const y = yOf(v);
      const line = document.createElementNS(NS, "line");
      line.setAttribute("x1", String(padL));
      line.setAttribute("x2", String(W - padR));
      line.setAttribute("y1", String(y));
      line.setAttribute("y2", String(y));
      line.setAttribute("stroke", "#e2e8f0");
      svg.appendChild(line);

      const lbl = document.createElementNS(NS, "text");
      lbl.setAttribute("x", String(padL - 6));
      lbl.setAttribute("y", String(y + 3));
      lbl.setAttribute("text-anchor", "end");
      lbl.setAttribute("font-size", "10");
      lbl.setAttribute("font-family", "var(--font-mono)");
      lbl.setAttribute("fill", "#64748b");
      lbl.textContent = String(v);
      svg.appendChild(lbl);
    }

    const frontierPts = steps.map((s, i) => `${xOf(i).toFixed(1)},${yOf(s.metrics.frontier_size).toFixed(1)}`).join(" ");
    const exploredPts = steps.map((s, i) => `${xOf(i).toFixed(1)},${yOf(s.metrics.explored_size).toFixed(1)}`).join(" ");

    const pExp = document.createElementNS(NS, "polyline");
    pExp.setAttribute("fill", "none");
    pExp.setAttribute("stroke", "#0ea5e9");
    pExp.setAttribute("stroke-width", "2.2");
    pExp.setAttribute("points", exploredPts);
    svg.appendChild(pExp);

    const pFr = document.createElementNS(NS, "polyline");
    pFr.setAttribute("fill", "none");
    pFr.setAttribute("stroke", "#f59e0b");
    pFr.setAttribute("stroke-width", "2.2");
    pFr.setAttribute("points", frontierPts);
    svg.appendChild(pFr);

    // Current step vertical marker
    const curX = xOf(state.currentStep);
    const curMetrics = steps[state.currentStep].metrics;
    const cursor = document.createElementNS(NS, "line");
    cursor.setAttribute("x1", String(curX));
    cursor.setAttribute("x2", String(curX));
    cursor.setAttribute("y1", String(padT));
    cursor.setAttribute("y2", String(padT + plotH));
    cursor.setAttribute("stroke", "#4f46e5");
    cursor.setAttribute("stroke-width", "1.5");
    cursor.setAttribute("stroke-dasharray", "3 2");
    svg.appendChild(cursor);

    for (const [val, color] of [
      [curMetrics.frontier_size, "#f59e0b"],
      [curMetrics.explored_size, "#0ea5e9"],
    ]) {
      const dot = document.createElementNS(NS, "circle");
      dot.setAttribute("cx", String(curX));
      dot.setAttribute("cy", String(yOf(val)));
      dot.setAttribute("r", "4");
      dot.setAttribute("fill", color);
      dot.setAttribute("stroke", "#ffffff");
      dot.setAttribute("stroke-width", "1.5");
      svg.appendChild(dot);
    }

    const xAxisLbl = document.createElementNS(NS, "text");
    xAxisLbl.setAttribute("x", String(W / 2));
    xAxisLbl.setAttribute("y", String(H - 6));
    xAxisLbl.setAttribute("text-anchor", "middle");
    xAxisLbl.setAttribute("font-size", "10");
    xAxisLbl.setAttribute("fill", "#64748b");
    xAxisLbl.textContent = `Bước ${state.currentStep} / ${steps.length - 1} (click lên biểu đồ để nhảy bước)`;
    svg.appendChild(xAxisLbl);
  }

  function renderSolutionStrip() {
    if (!state.trace || !state.trace.solution_ids) {
      els.solutionStripCard.classList.add("hidden");
      return;
    }
    els.solutionStripCard.classList.remove("hidden");
    els.solutionStrip.innerHTML = "";
    const solIds = state.trace.solution_ids;
    solIds.forEach((id, idx) => {
      const node = state.trace.nodes[id];
      const card = document.createElement("div");
      card.className = "node-card" + (idx === solIds.length - 1 ? " card-new" : "");
      card.tabIndex = 0;

      const top = document.createElement("div");
      top.className = "node-card-top";
      top.innerHTML = `<span>B${idx}${idx === solIds.length - 1 ? " (GOAL)" : ""}</span><span>#${id}</span>`;
      const mini = buildMiniBoard(node.state);
      const foot = document.createElement("div");
      foot.className = "node-card-foot";
      foot.textContent = node.action ? `${MOVE_ARROWS[node.action]} ${node.action}` : "Xuất phát";

      card.append(top, mini, foot);
      card.addEventListener("click", () => {
        stopPlayback();
        state.currentStep = node.resolved_step ?? node.created_step;
        selectPinnedNode(id);
        renderStep();
      });
      els.solutionStrip.appendChild(card);
    });
  }

  // Vùng nào trên màn hình chịu tác động của dòng mã đang chạy.
  const FOCUS_ZONES = {
    init_root: ["cur"],
    check_root: ["cur"],
    init: ["frontier"],
    init_explored: ["explored"],
    dequeue: ["frontier", "cur"],
    check_late: ["cur"],
    explore: ["explored", "cur"],
    gen_child: ["child"],
    check_pass: ["check", "child"],
    skip_explored: ["check", "child", "explored"],
    skip_frontier: ["check", "child", "frontier"],
    check_goal: ["check", "child"],
    enqueue: ["frontier", "child"],
    goal_early: ["check", "child"],
    goal_late: ["cur"],
    goal_init: ["cur"],
    limit_reached: [],
    failure: [],
  };

  const ROOT_EVENTS = new Set(["init_root", "check_root", "init", "init_explored"]);
  const CHILD_EVENTS = new Set([
    "gen_child", "check_pass", "check_goal", "skip_explored", "skip_frontier", "enqueue", "goal_early",
  ]);

  function applyFocus(eventType) {
    const zones = new Set(FOCUS_ZONES[eventType] || []);
    document.querySelectorAll("[data-zone]").forEach((el) => {
      el.classList.toggle("zone-focus", zones.has(el.dataset.zone));
    });
    // "Đèn sân khấu": khi có vùng được chiếu sáng thì phần còn lại mờ đi.
    els.stage.classList.toggle("has-focus", zones.size > 0);
  }

  const CHECK_ICONS = { idle: "·", pass: "✓", fail: "✗", hit: "🎯", skipped: "–" };
  const CHECK_DEFAULT_HTML = {
    explored: "<code>child</code> chưa có trong <code>explored</code>",
    frontier: "<code>child</code> chưa có trong <code>frontier</code>",
    goal: "<code>child</code> chưa phải <b>đích</b>",
  };

  function setCheckRow(el, kind, status, html) {
    el.dataset.state = status === "hit" ? "pass" : status;
    el.querySelector(".check-icon").textContent = CHECK_ICONS[status];
    el.querySelector(".check-text").innerHTML = html || CHECK_DEFAULT_HTML[kind];
  }

  // Bảng kiểm tra phản chiếu đúng các dòng `if child not in explored and ...` / `if is_goal(child)`.
  function renderChecklist(step, cfg) {
    els.chkExplored.classList.toggle("hidden", !cfg.graph_search);
    els.chkFrontier.classList.toggle("hidden", !cfg.graph_search);
    els.chkGoal.classList.toggle("hidden", !cfg.early_goal_test);

    const st = { explored: "idle", frontier: "idle", goal: "idle" };
    let goalHtml = null;
    let verdict = null;

    switch (step.event_type) {
      case "gen_child":
        verdict = { cls: "verdict-wait", text: "Vừa sinh nút con — sắp kiểm tra…" };
        break;
      case "check_pass":
        st.explored = "pass";
        st.frontier = "pass";
        verdict = { cls: "verdict-wait", text: "Là trạng thái MỚI" };
        break;
      case "skip_explored":
        st.explored = "fail";
        st.frontier = "skipped";
        st.goal = "skipped";
        verdict = { cls: "verdict-bad", text: "✗ BỎ QUA nút con", soi: step.collision_id };
        break;
      case "skip_frontier":
        st.explored = "pass";
        st.frontier = "fail";
        st.goal = "skipped";
        verdict = { cls: "verdict-bad", text: "✗ BỎ QUA nút con", soi: step.collision_id };
        break;
      case "check_goal":
        st.explored = "pass";
        st.frontier = "pass";
        st.goal = "pass";
        verdict = { cls: "verdict-wait", text: "Chưa phải đích → sẽ enqueue" };
        break;
      case "enqueue":
        st.explored = "pass";
        st.frontier = "pass";
        st.goal = "pass";
        verdict = { cls: "verdict-good", text: "✓ ĐÃ THÊM vào cuối hàng đợi" };
        break;
      case "goal_early":
        st.explored = "pass";
        st.frontier = "pass";
        st.goal = "hit";
        goalHtml = "<code>child</code> <b>LÀ ĐÍCH!</b>";
        verdict = { cls: "verdict-good", text: "Tìm thấy lời giải!" };
        break;
      case "check_late":
        verdict = { cls: "verdict-wait", text: "cur_node chưa phải đích → tiếp tục mở rộng" };
        break;
      case "goal_late":
        verdict = { cls: "verdict-good", text: "cur_node LÀ ĐÍCH — tìm thấy lời giải!" };
        break;
      case "dequeue":
      case "explore":
        verdict = { cls: "verdict-wait", text: "Chờ sinh nút con…" };
        break;
      default:
        break;
    }

    setCheckRow(els.chkExplored, "explored", st.explored);
    setCheckRow(els.chkFrontier, "frontier", st.frontier);
    setCheckRow(els.chkGoal, "goal", st.goal, goalHtml);

    els.checkVerdict.innerHTML = "";
    if (verdict) {
      const span = document.createElement("span");
      span.className = verdict.cls;
      span.textContent = verdict.text;
      els.checkVerdict.appendChild(span);
      if (verdict.soi !== undefined && verdict.soi !== null) {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "btn btn-secondary btn-xs";
        btn.textContent = `Soi nút trùng #${verdict.soi}`;
        btn.addEventListener("click", () => selectPinnedNode(verdict.soi));
        els.checkVerdict.appendChild(btn);
      }
    }
  }

  // Khối "Nút đang xử lý": cur_node → child + các nước đi + bảng kiểm tra.
  function renderWork(step, trace) {
    const nodes = trace.nodes;
    const ev = step.event_type;

    const isRootPhase = ROOT_EVENTS.has(ev);
    let curNode = step.cur_id !== null ? nodes[step.cur_id] : null;
    if (isRootPhase) curNode = nodes[0];
    const candNode = step.candidate_id !== null ? nodes[step.candidate_id] : null;
    const childShown = Boolean(candNode) && CHILD_EVENTS.has(ev);
    const isDup = ev === "skip_explored" || ev === "skip_frontier";
    const isGoalChild = ev === "goal_early";
    const isGoalCur = ev === "goal_late" || ev === "goal_init";

    // cur_node
    els.curLabel.textContent = isRootPhase ? "root" : "cur_node";
    els.curNodeBadge.textContent = curNode ? `#${curNode.id} · d=${curNode.depth}` : "—";
    renderState(els.curBoardContainer, curNode ? curNode.state : null, {
      emptyText: "—",
      targetBoard: trace.target_board,
      movedTile: childShown ? candNode.moved_tile : null,
      changed: childShown ? candNode.changed : null,
      boardCls: ev === "dequeue" ? "board-popped" : isGoalCur ? "board-goal" : null,
    });

    // child
    if (childShown) {
      els.candNodeBadge.textContent = `#${candNode.id} · d=${candNode.depth}`;
      els.candNodeBadge.className = `mono-pill ${isDup ? "pill-rose" : isGoalChild ? "pill-emerald" : "pill-indigo"}`;
      els.moveArrowBadge.textContent = MOVE_ARROWS[candNode.action] || "→";
      els.moveArrowBadge.className = `move-arrow-badge ${isDup ? "collision" : isGoalChild ? "goal" : "active"}`;
      els.moveLabel.textContent = candNode.action || "";
      renderState(els.candBoardContainer, candNode.state, {
        targetBoard: trace.target_board,
        movedTile: candNode.moved_tile,
        changed: candNode.changed,
        isCollision: isDup,
        boardCls: isDup ? "board-dup" : isGoalChild ? "board-goal" : ev === "enqueue" ? "board-new" : null,
      });
    } else {
      els.candNodeBadge.textContent = "—";
      els.candNodeBadge.className = "mono-pill pill-neutral";
      els.moveArrowBadge.textContent = "→";
      els.moveArrowBadge.className = "move-arrow-badge";
      els.moveLabel.textContent = "";
      renderState(els.candBoardContainer, null, { emptyText: "chưa sinh nút con" });
    }

    // Phát lại hiệu ứng đúng thao tác vừa xảy ra
    for (const el of [els.curBoardContainer, els.candBoardContainer]) {
      el.classList.remove("fx-arrive", "fx-drop", "fx-dup");
    }
    void els.curBoardContainer.offsetWidth;
    if (ev === "dequeue") els.curBoardContainer.classList.add("fx-arrive");
    if (ev === "gen_child") els.candBoardContainer.classList.add("fx-drop");
    if (isDup) els.candBoardContainer.classList.add("fx-dup");

    // Các nước đi hợp lệ của ô trống (vòng lặp for move in actions)
    els.movesRow.innerHTML = "";
    const moves = curNode && !isRootPhase ? curNode.actions || [] : [];
    if (!moves.length) {
      const none = document.createElement("span");
      none.className = "meta-muted";
      none.textContent = "—";
      els.movesRow.appendChild(none);
    } else {
      const activeIdx = childShown && candNode.action ? moves.indexOf(candNode.action) : -1;
      moves.forEach((m, i) => {
        const chip = document.createElement("span");
        chip.className = "move-chip" + (i === activeIdx ? " active" : i < activeIdx ? " done" : "");
        chip.textContent = `${MOVE_ARROWS[m] || ""} ${m}`;
        els.movesRow.appendChild(chip);
      });
    }

    renderChecklist(step, trace.config);
  }

  function renderStep() {
    const trace = state.trace;
    if (trace && trace.compare) {
      renderCompare();
      return;
    }
    if (!trace || !trace.steps.length) {
      const vac = state.problem === "vacuum";
      renderState(els.curBoardContainer, vac ? state.vacStart : state.startBoard, { targetBoard: state.targetBoard });
      renderState(els.candBoardContainer, null, { emptyText: "chưa sinh nút con" });
      renderGoal(
        vac
          ? { problem: "vacuum", goal_description: "Cả hai phòng đều sạch" }
          : { problem: "npuzzle", target_board: state.targetBoard }
      );
      els.curLabel.textContent = "root";
      els.curNodeBadge.textContent = "—";
      els.candNodeBadge.textContent = "—";
      els.movesRow.innerHTML = "";
      els.frontierList.innerHTML = "";
      els.frontierList.appendChild(makePlaceholder(`${ALGO_LABELS[state.algorithm].container} đang rỗng.`));
      els.exploredList.innerHTML = "";
      els.exploredList.appendChild(makePlaceholder("Chưa có trạng thái nào được mở rộng xong."));
      els.frontierCountBadge.textContent = "0";
      els.exploredCountBadge.textContent = "0";
      els.stepSlider.max = "0";
      els.stepSlider.value = "0";
      els.stepCounter.textContent = "0 / 0";
      els.eventBadge.textContent = "SẴN SÀNG";
      els.eventBadge.className = "status-pill pill-neutral";
      els.eventMessage.textContent = "Chưa có bước nào để hiển thị.";
      els.firstBtn.disabled = els.prevBtn.disabled = els.nextBtn.disabled = els.lastBtn.disabled = true;
      applyFocus(null);
      els.vizRow.classList.toggle("has-graph", state.problem === "vacuum");
      els.graphCard.classList.toggle("hidden", state.problem !== "vacuum");
      els.vacGraphSvg.innerHTML = "";
      renderSearchTree();
      return;
    }

    const totalSteps = trace.steps.length - 1;
    state.currentStep = Math.max(0, Math.min(state.currentStep, totalSteps));
    const step = trace.steps[state.currentStep];
    const nodes = trace.nodes;

    els.stepSlider.max = String(totalSteps);
    els.stepSlider.value = String(state.currentStep);
    els.stepCounter.textContent = `${state.currentStep} / ${totalSteps}`;

    const atStart = state.currentStep === 0;
    const atEnd = state.currentStep === totalSteps;
    els.firstBtn.disabled = atStart;
    els.prevBtn.disabled = atStart;
    els.nextBtn.disabled = atEnd;
    els.lastBtn.disabled = atEnd;

    // Hero: dòng mã vừa chạy làm gì
    const algorithm = trace.algorithm || state.algorithm;
    const badge = badgeFor(step.event_type, algorithm);
    els.eventBadge.textContent = badge.text;
    els.eventBadge.className = `status-pill ${badge.cls}`;
    els.eventMessage.textContent = step.message;
    applyFocus(step.event_type);

    // Chỉ báo vô nghiệm: chỉ hiện khi có vấn đề, tránh nhiễu
    const solv = trace.solvability;
    if (solv.solvable) {
      els.solvabilityChip.classList.add("hidden");
    } else {
      els.solvabilityChip.textContent = "Vô nghiệm ✕";
      els.solvabilityChip.className = "solvability-chip pill-rose";
    }

    syncPredictQuestion();
    renderGoal(trace);
    renderWork(step, trace);

    // Mã giả + giá trị biến
    els.modeSummaryTag.textContent = `${trace.config.graph_search ? "Graph" : "Tree"} · ${trace.config.early_goal_test ? "Early Goal" : "Late Goal"}`;
    renderCodePanel(trace.source_lines, step.line, step.event_type, step.vars);

    // Hàng đợi và explored
    els.frontierCountBadge.textContent = String(step.frontier_ids.length);
    els.exploredCountBadge.textContent = String(step.explored_ids.length);
    renderFrontierStrip(step, nodes, algorithm);
    renderExploredStrip(step, nodes, trace.config);

    // Thống kê
    const m = step.metrics;
    els.kpiExpanded.textContent = String(m.expanded);
    els.kpiGenerated.textContent = String(m.generated);
    els.kpiSkipped.textContent = String(m.skipped_explored + m.skipped_frontier);
    els.kpiMaxFrontier.textContent = String(m.max_frontier_size);
    const solLen = trace.summary.solution_length !== null ? `${trace.summary.solution_length} bước` : "chưa có";
    els.kpiSolutionBranch.textContent = `${solLen} · b≈${trace.summary.avg_branching_factor}`;
    els.solvFormula.textContent = solv.formula;
    els.solvExplanation.textContent = solv.explanation;

    const isVac = trace.problem === "vacuum";
    els.vizRow.classList.toggle("has-graph", isVac);
    els.graphCard.classList.toggle("hidden", !isVac);
    renderSearchTree();
    if (isVac) drawVacuumGraph(els.vacGraphSvg, trace, state.currentStep);
    if (els.analysisCard.open) renderMemoryChart();
    renderPinnedNode();
    renderPredictPrompt();
  }

  async function runSearch(forceRun = false) {
    if (state.compare.enabled) return runCompare(forceRun);
    stopPlayback();
    hideAlert();
    state.pinnedNodeId = null;
    els.runBtn.disabled = true;
    els.runBtn.textContent = "Đang chạy...";

    try {
      const payload = buildPayload(forceRun);
      const algoName = ALGO_LABELS[state.algorithm].name;
      const data = await apiJson("/api/solve", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      state.trace = data;
      state.currentStep = 0;
      state.treeAutoFit = true;
      resetPredictQuestions();

      if (data.status === "unsolvable_blocked") {
        els.solvabilityChip.textContent = "Vô nghiệm ✕";
        els.solvabilityChip.className = "solvability-chip pill-rose";
        els.solvFormula.textContent = data.solvability.formula;
        els.solvExplanation.textContent = data.solvability.explanation;
        renderCodePanel(data.source_lines, 0, "failure", {});
        renderStep();
        showAlert(
          "",
          "Bảng này VÔ NGHIỆM (không thể đi tới đích)!",
          data.solvability.explanation,
          {
            label: `Vẫn chạy ${algoName} (giới hạn ${payload.max_nodes} nút)`,
            cls: "btn btn-danger btn-sm",
            onClick: () => runSearch(true),
          }
        );
        return;
      }

      if (data.status === "limit_reached") {
        showAlert(
          "warn",
          `${algoName} đã dừng ở giới hạn an toàn ${payload.max_nodes} nút mở rộng.`,
          !payload.graph_search
            ? "Bạn đang tắt Graph Search (Tree Search không lọc trùng), nên thuật toán cứ lặp lại các trạng thái cũ và cây phình to mãi. Hãy bước tới để quan sát vòng lặp!"
            : "Tăng giới hạn nút mở rộng (trong Tùy chọn) nếu muốn tìm tiếp tới đích."
        );
      } else if (data.status === "failure") {
        showAlert(
          "",
          `Frontier đã cạn — ${algoName} xác nhận bài toán KHÔNG CÓ LỜI GIẢI!`,
          data.solvability.explanation
        );
      } else if (data.status === "solved" && !payload.graph_search) {
        showAlert(
          "warn",
          `Tìm thấy lời giải (${data.summary.solution_length} bước) ở chế độ Tree Search (không lọc trùng).`,
          `So sánh với Graph Search: đã sinh ${data.summary.nodes_generated} nút và đỉnh frontier là ${data.summary.max_frontier_size}.`
        );
      }

      renderSolutionStrip();
      renderStep();
      if (els.analysisCard.open) renderMemoryChart();
    } catch (err) {
      showAlert("", "Không thể chạy thuật toán", err.message);
    } finally {
      els.runBtn.disabled = false;
      els.runBtn.textContent = "↻ Chạy lại";
    }
  }

  // ── Chế độ so sánh hai thuật toán ───────────────────────────────────────────
  // Chạy BFS và DFS trên CÙNG bài toán/cấu hình, rồi đặt cạnh nhau. Một "tick" = một lần
  // mở rộng nút (một lần pop), nên hai bên luôn cùng mở rộng nút thứ k tại mỗi thời điểm.

  const COMPARE_ALGOS = ["bfs", "dfs"];
  const ALGO_COLORS = { bfs: "#4f46e5", dfs: "#0d9488" };
  const CMP_HEAD = 3;
  const CMP_TAIL = 4;

  function buildPayload(forceRun) {
    const payload = {
      problem: state.problem,
      algorithm: state.algorithm,
      graph_search: els.graphSearchToggle.checked,
      early_goal_test: els.earlyGoalToggle.checked,
      max_nodes: Number(els.maxNodesInput.value) || 300,
      force_run: forceRun,
    };
    if (state.problem === "vacuum") {
      payload.start_state = state.vacStart;
    } else {
      payload.size = state.size;
      payload.start_board = state.startBoard;
      payload.target_board = state.targetBoard;
    }
    return payload;
  }

  // Từ một trace, tính mốc bước ứng với từng lần mở rộng và các chuỗi số liệu để vẽ biểu đồ.
  function deriveRun(algorithm, trace) {
    const steps = trace.steps;
    const dequeueIdx = [];
    steps.forEach((st, i) => {
      if (st.event_type === "dequeue") dequeueIdx.push(i);
    });
    const n = dequeueIdx.length;
    // tickEnd[k] = chỉ số bước ngay trước lần pop thứ k+1 (tức là khi lần mở rộng thứ k vừa xong).
    const tickEnd = [n > 0 ? dequeueIdx[0] - 1 : steps.length - 1];
    for (let k = 1; k <= n; k++) tickEnd.push((k < n ? dequeueIdx[k] : steps.length) - 1);
    const depthSeries = [0];
    for (let k = 1; k <= n; k++) depthSeries.push(trace.nodes[steps[dequeueIdx[k - 1]].cur_id].depth);
    const frontierSeries = tickEnd.map((idx) => steps[idx].frontier_ids.length);
    return { algorithm, trace, dequeueIdx, n, tickEnd, depthSeries, frontierSeries };
  }

  function resultLabel(status) {
    if (status === "solved") return { text: "✓ Tìm thấy", cls: "pill-emerald" };
    if (status === "limit_reached") return { text: "⚠ Chạm giới hạn", cls: "pill-amber" };
    return { text: "✕ Không có lời giải", cls: "pill-rose" };
  }

  function renderCompareSummary() {
    const runs = state.compare.runs;
    const bothSolved = runs.length === 2 && runs.every((r) => r.trace.status === "solved");
    const total = (r) => r.trace.summary.skipped_explored + r.trace.summary.skipped_frontier;
    const rows = [
      { label: "Kết quả", get: (r) => resultLabel(r.trace.status).text, plain: true },
      { label: "Độ dài lời giải (bước)", get: (r) => r.trace.summary.solution_length, compare: true },
      { label: "Nút đã mở rộng", get: (r) => r.trace.summary.nodes_expanded, compare: true },
      { label: "Nút đã sinh", get: (r) => r.trace.summary.nodes_generated, compare: true },
      { label: "Frontier lớn nhất", get: (r) => r.trace.summary.max_frontier_size, compare: true },
      { label: "Nút bị bỏ qua (trùng)", get: total, compare: false },
    ];

    let html = "<thead><tr><th></th>";
    for (const r of runs) html += `<th class="cmp-${r.algorithm}">${ALGO_LABELS[r.algorithm].name}</th>`;
    html += "</tr></thead><tbody>";
    for (const row of rows) {
      const vals = runs.map((r) => row.get(r));
      let bestIdx = -1;
      if (row.compare && bothSolved && vals[0] !== vals[1]) bestIdx = vals[0] < vals[1] ? 0 : 1;
      html += `<tr><td>${row.label}</td>`;
      vals.forEach((v, i) => {
        const shown = v === null || v === undefined ? "—" : v;
        html += `<td class="num${i === bestIdx ? " best" : ""}">${shown}</td>`;
      });
      html += "</tr>";
    }
    els.cmpSummary.innerHTML = html + "</tbody>";
  }

  function renderCompareInsight() {
    const [a, b] = state.compare.runs;
    const lines = [];
    const name = (r) => ALGO_LABELS[r.algorithm].name;
    const sm = (r) => r.trace.summary;
    const cfg = a.trace.config;

    for (const r of [a, b]) {
      if (r.trace.status === "limit_reached") {
        lines.push(
          cfg.graph_search
            ? `${name(r)} chạm giới hạn ${cfg.max_nodes} nút mà chưa tìm thấy đích.`
            : `${name(r)} chạm giới hạn ${cfg.max_nodes} nút: Tree Search không nhớ trạng thái đã gặp nên cứ lặp lại mãi.`
        );
      } else if (r.trace.status === "failure") {
        lines.push(`${name(r)} đã duyệt hết mà không tìm thấy đích.`);
      }
    }

    if (a.trace.status === "solved" && b.trace.status === "solved") {
      const la = sm(a).solution_length;
      const lb = sm(b).solution_length;
      lines.push(
        la === lb
          ? `Cả hai cùng cho lời giải ${la} bước.`
          : `${la < lb ? name(a) : name(b)} cho lời giải ngắn hơn (${Math.min(la, lb)} so với ${Math.max(la, lb)} bước). BFS luôn tìm được lời giải ngắn nhất khi mọi nước đi tốn như nhau.`
      );
      const ea = sm(a).nodes_expanded;
      const eb = sm(b).nodes_expanded;
      lines.push(
        ea === eb
          ? `Cả hai cùng mở rộng ${ea} nút.`
          : `${ea < eb ? name(a) : name(b)} mở rộng ít nút hơn (${Math.min(ea, eb)} so với ${Math.max(ea, eb)}), tức là nhanh hơn trong lần chạy này.`
      );
    } else if (a.trace.status === "solved" || b.trace.status === "solved") {
      const winner = a.trace.status === "solved" ? a : b;
      lines.push(`Chỉ ${name(winner)} tìm được lời giải (${sm(winner).solution_length} bước).`);
    }

    const fa = sm(a).max_frontier_size;
    const fb = sm(b).max_frontier_size;
    lines.push(
      fa === fb
        ? `Cả hai cần frontier lớn nhất là ${fa} nút.`
        : `${fa < fb ? name(a) : name(b)} cần ít bộ nhớ hơn: frontier lớn nhất ${Math.min(fa, fb)} nút so với ${Math.max(fa, fb)}.`
    );

    els.cmpInsight.innerHTML = "";
    for (const text of lines) {
      const li = document.createElement("li");
      li.textContent = text;
      els.cmpInsight.appendChild(li);
    }
  }

  function buildCompareSides(problem) {
    const isVac = problem === "vacuum";
    els.cmpSides.innerHTML = "";
    state.compare.sides = COMPARE_ALGOS.map((algo) => {
      const labels = ALGO_LABELS[algo];
      const root = document.createElement("section");
      root.className = "cmp-side";
      root.style.setProperty("--algo-color", ALGO_COLORS[algo]);
      root.innerHTML = `
        <div class="cmp-head">
          <strong class="cmp-name">${labels.name}</strong>
          <span class="cmp-status status-pill pill-neutral">đang chạy</span>
          <span class="cmp-live"></span>
        </div>
        <div class="cmp-block">
          <div class="cmp-work-label">Cây tìm kiếm <span class="meta-muted">(số trong nút nhỏ = thứ tự mở rộng)</span></div>
          <svg class="cmp-tree"></svg>
        </div>
        <div class="cmp-block">
          <div class="block-head">
            <span class="block-title"><i class="dot dot-amber"></i>frontier <small>${labels.kind}</small> <span class="count-pill pill-amber cmp-fcount">0</span></span>
            <span class="queue-axis"><span class="axis-out">${labels.out}</span><span class="axis-in">${labels.in}</span></span>
          </div>
          <div class="queue-strip cmp-frontier"></div>
        </div>
        <div class="cmp-block">
          <div class="cmp-work-label"></div>
          ${isVac
            ? '<svg class="cmp-graph" viewBox="0 0 560 240"></svg>'
            : '<div class="cmp-boardwrap"><div class="puzzle-board cmp-board"></div></div>'}
        </div>
        <div class="cmp-solution hidden"></div>`;
      els.cmpSides.appendChild(root);
      const q = (sel) => root.querySelector(sel);
      return {
        root,
        status: q(".cmp-status"),
        live: q(".cmp-live"),
        tree: q(".cmp-tree"),
        frontier: q(".cmp-frontier"),
        fcount: q(".cmp-fcount"),
        workLabel: q(".cmp-block:nth-of-type(3) .cmp-work-label") || q(".cmp-work-label"),
        board: q(".cmp-board"),
        graph: q(".cmp-graph"),
        solution: q(".cmp-solution"),
      };
    });
    // nhãn của khối "nút đang xét" là .cmp-work-label thứ hai
    state.compare.sides.forEach((side) => {
      side.workLabel = side.root.querySelectorAll(".cmp-work-label")[1];
    });
  }

  function renderCompareSide(i, t) {
    const run = state.compare.runs[i];
    const side = state.compare.sides[i];
    const trace = run.trace;
    const nodes = trace.nodes;
    const labels = ALGO_LABELS[run.algorithm];
    const k = Math.min(t, run.n);
    const stepIdx = run.tickEnd[k];
    const step = trace.steps[stepIdx];
    const done = t >= run.n;
    const solved = trace.status === "solved";
    const cur = k >= 1 ? nodes[trace.steps[run.dequeueIdx[k - 1]].cur_id] : nodes[0];

    // Trạng thái chạy
    const res = done ? resultLabel(trace.status) : { text: "đang chạy", cls: "pill-neutral" };
    side.status.textContent = res.text;
    side.status.className = `cmp-status status-pill ${res.cls}`;
    side.live.textContent = `mở rộng ${step.metrics.expanded} · sinh ${step.metrics.generated} · explored ${step.explored_ids.length} · bỏ qua ${step.metrics.skipped_explored + step.metrics.skipped_frontier}`;

    // Cây tìm kiếm thu nhỏ (tự vừa khung): thấy ngay BFS rộng-nông còn DFS hẹp-sâu
    drawSearchTree(side.tree, trace, stepIdx, { transform: null, pinnedId: null, showPruned: true, interactive: false });

    // frontier: các nút MỚI là con của nút vừa mở rộng; nút kế tiếp được đánh dấu theo quy tắc FIFO/LIFO
    const ids = step.frontier_ids;
    const fresh = new Set();
    if (k >= 1) {
      const startIdx = run.dequeueIdx[k - 1];
      for (const id of ids) {
        if (nodes[id].parent_id === cur.id && nodes[id].created_step > startIdx) fresh.add(id);
      }
    }
    const nextIdx = run.algorithm === "dfs" ? ids.length - 1 : 0;
    side.fcount.textContent = String(ids.length);
    renderCardStrip(side.frontier, ids, nodes, {
      head: CMP_HEAD,
      tail: CMP_TAIL,
      emptyText: `${labels.container} rỗng.`,
      optsFor: (id, idx) => {
        if (fresh.has(id)) return { cls: "card-new", tag: { text: "MỚI", cls: "pill-emerald" }, highlight: true };
        if (idx === nextIdx) return { cls: "card-front", tag: { text: labels.next, cls: "pill-amber" } };
        return {};
      },
    });

    // nút vừa mở rộng (hoặc nút đích khi đã xong)
    const goalNode = done && solved ? nodes[trace.solution_ids[trace.solution_ids.length - 1]] : null;
    const shown = goalNode || cur;
    if (side.graph) {
      drawVacuumGraph(side.graph, trace, stepIdx);
    } else {
      renderState(side.board, shown.state, {
        targetBoard: trace.target_board,
        boardCls: goalNode ? "board-goal" : null,
      });
    }
    side.workLabel.textContent = goalNode
      ? `🎯 Nút đích #${shown.id} · tầng ${shown.depth}`
      : k === 0
        ? `Nút gốc #${shown.id} · tầng ${shown.depth}`
        : `Nút vừa mở rộng #${shown.id} · tầng ${shown.depth}`;

    // đường đi lời giải
    if (done && solved) {
      const path = trace.solution_ids.slice(1).map((id) => MOVE_ARROWS[nodes[id].action] || nodes[id].action);
      side.solution.textContent = path.length
        ? `Lời giải (${path.length} bước): ${path.join(" ")}`
        : "Nút gốc đã là đích (0 bước).";
      side.solution.classList.remove("hidden");
    } else {
      side.solution.classList.add("hidden");
    }
  }

  const CMP_CHART = { W: 360, H: 150, padL: 30, padR: 10, padT: 10, padB: 20 };

  function drawCompareChart(svg, getSeries, t) {
    const { W, H, padL, padR, padT, padB } = CMP_CHART;
    const NS = "http://www.w3.org/2000/svg";
    svg.innerHTML = "";
    const runs = state.compare.runs;
    const maxX = Math.max(1, state.compare.maxTick);
    let maxY = 1;
    for (const r of runs) for (const v of getSeries(r)) maxY = Math.max(maxY, v);
    const xOf = (i) => padL + (i / maxX) * (W - padL - padR);
    const yOf = (v) => padT + (1 - v / maxY) * (H - padT - padB);
    const mk = (tag, attrs) => {
      const el = document.createElementNS(NS, tag);
      for (const [key, val] of Object.entries(attrs)) el.setAttribute(key, String(val));
      return el;
    };

    for (const frac of [0, 0.5, 1]) {
      const v = Math.round(maxY * frac);
      const y = yOf(v);
      svg.appendChild(mk("line", { x1: padL, x2: W - padR, y1: y, y2: y, stroke: "#e2e8f0" }));
      const lbl = mk("text", { x: padL - 5, y: y + 3, "text-anchor": "end", "font-size": 9, fill: "#64748b" });
      lbl.textContent = String(v);
      svg.appendChild(lbl);
    }
    const xl = mk("text", { x: W / 2, y: H - 4, "text-anchor": "middle", "font-size": 9, fill: "#64748b" });
    xl.textContent = "lần mở rộng nút";
    svg.appendChild(xl);

    for (const r of runs) {
      const series = getSeries(r);
      const color = ALGO_COLORS[r.algorithm];
      svg.appendChild(
        mk("polyline", {
          fill: "none",
          stroke: color,
          "stroke-width": 2,
          points: series.map((v, i) => `${xOf(i).toFixed(1)},${yOf(v).toFixed(1)}`).join(" "),
        })
      );
      const last = series.length - 1;
      svg.appendChild(
        mk("circle", {
          cx: xOf(last),
          cy: yOf(series[last]),
          r: 4,
          fill: r.trace.status === "solved" ? color : "#ffffff",
          stroke: color,
          "stroke-width": 2,
        })
      );
    }

    svg.appendChild(
      mk("line", {
        x1: xOf(t),
        x2: xOf(t),
        y1: padT,
        y2: H - padB,
        stroke: "#0f172a",
        "stroke-width": 1.2,
        "stroke-dasharray": "3 2",
      })
    );
  }

  function renderCompare() {
    const cmp = state.compare;
    const maxTick = cmp.maxTick;
    state.currentStep = Math.max(0, Math.min(state.currentStep, maxTick));
    const t = state.currentStep;

    els.stepSlider.max = String(maxTick);
    els.stepSlider.value = String(t);
    els.stepCounter.textContent = `${t} / ${maxTick}`;
    els.firstBtn.disabled = els.prevBtn.disabled = t === 0;
    els.nextBtn.disabled = els.lastBtn.disabled = t === maxTick;
    els.solvabilityChip.classList.add("hidden");
    applyFocus(null);

    if (!cmp.runs.length) {
      els.eventBadge.textContent = "SO SÁNH";
      els.eventBadge.className = "status-pill pill-neutral";
      els.eventMessage.textContent = "Chưa có dữ liệu để so sánh.";
      return;
    }

    els.eventBadge.textContent = t === 0 ? "KHỞI TẠO" : `SAU ${t} LẦN MỞ RỘNG`;
    els.eventBadge.className = "status-pill pill-indigo";
    els.eventMessage.textContent = cmp.runs
      .map((run) => {
        const k = Math.min(t, run.n);
        return `${ALGO_LABELS[run.algorithm].name}: tầng ${run.depthSeries[k]}, frontier ${run.frontierSeries[k]}${t >= run.n && t > 0 ? " (xong)" : ""}`;
      })
      .join("   |   ");

    cmp.runs.forEach((_, i) => renderCompareSide(i, t));
    drawCompareChart(els.cmpDepthChart, (r) => r.depthSeries, t);
    drawCompareChart(els.cmpFrontierChart, (r) => r.frontierSeries, t);
  }

  async function runCompare(forceRun = false) {
    stopPlayback();
    hideAlert();
    els.runBtn.disabled = true;
    els.runBtn.textContent = "Đang chạy...";
    try {
      const base = buildPayload(forceRun);
      const results = await Promise.all(
        COMPARE_ALGOS.map((algorithm) =>
          apiJson("/api/solve", { method: "POST", body: JSON.stringify({ ...base, algorithm }) })
        )
      );
      buildCompareSides(results[0].problem);

      if (results[0].status === "unsolvable_blocked") {
        state.compare.runs = [];
        state.compare.maxTick = 0;
        state.trace = { compare: true, steps: [{ is_macro: true }], nodes: [] };
        state.currentStep = 0;
        els.cmpSummary.innerHTML = "";
        els.cmpInsight.innerHTML = "";
        els.cmpSides.innerHTML = "";
        state.compare.sides = [];
        els.cmpDepthChart.innerHTML = "";
        els.cmpFrontierChart.innerHTML = "";
        renderStep();
        showAlert("", "Bảng này VÔ NGHIỆM (không thể đi tới đích)!", results[0].solvability.explanation, {
          label: `Vẫn so sánh (giới hạn ${base.max_nodes} nút)`,
          cls: "btn btn-danger btn-sm",
          onClick: () => runCompare(true),
        });
        return;
      }

      state.compare.runs = results.map((trace, i) => deriveRun(COMPARE_ALGOS[i], trace));
      state.compare.maxTick = Math.max(...state.compare.runs.map((r) => r.n));
      // Trace tổng hợp: mỗi "bước" là một lần mở rộng, để các nút điều khiển phát dùng lại nguyên vẹn.
      state.trace = {
        compare: true,
        steps: Array.from({ length: state.compare.maxTick + 1 }, () => ({ is_macro: true })),
        nodes: [],
      };
      state.currentStep = 0;
      renderCompareSummary();
      renderCompareInsight();
      renderStep();
    } catch (err) {
      showAlert("", "Không thể so sánh", err.message);
    } finally {
      els.runBtn.disabled = false;
      els.runBtn.textContent = "↻ Chạy lại";
    }
  }

  function setCompareMode(on) {
    stopPlayback();
    hideAlert();
    state.compare.enabled = on;
    document.querySelector(".app-shell").classList.toggle("compare-on", on);
    document.body.classList.toggle("compare-on", on); // thanh phát nằm ngoài .app-shell
    if (on) setPredictMode(false);
    els.compareBtn.setAttribute("aria-pressed", String(on));
    els.compareBtn.classList.toggle("btn-primary", on);
    els.compareBtn.classList.toggle("btn-secondary", !on);
    state.trace = null;
    state.currentStep = 0;
    if (on) runCompare(false);
    else runSearch(false);
  }

  // ── Chế độ Dự đoán: tự đoán trước khi xem kết quả ───────────────────────────
  // Hai loại câu hỏi: (1) nút nào sẽ được pop tiếp theo? (2) nút con vừa sinh ra là MỚI hay TRÙNG?

  function activePredictQuestion() {
    const pr = state.predict;
    if (!pr.enabled || !pr.pending || pr.pending.stepIdx !== state.currentStep) return null;
    return pr.pending;
  }

  // Câu hỏi cần trả lời TRƯỚC khi đi từ bước idx sang bước idx+1 (hoặc null).
  function questionBefore(idx) {
    const steps = state.trace.steps;
    const cur = steps[idx];
    const nxt = steps[idx + 1];
    if (!nxt) return null;
    if (nxt.event_type === "dequeue" && cur.frontier_ids.length > 1) {
      return { type: "pop", stepIdx: idx, answerId: nxt.cur_id, answered: false };
    }
    if (cur.event_type === "gen_child" && ["skip_explored", "skip_frontier", "check_pass"].includes(nxt.event_type)) {
      return {
        type: "dup",
        stepIdx: idx,
        childId: cur.candidate_id,
        answer: nxt.event_type === "check_pass" ? "new" : "dup",
        where: nxt.event_type === "skip_explored" ? "explored" : "frontier",
        collisionId: nxt.collision_id,
        answered: false,
      };
    }
    return null;
  }

  function syncPredictQuestion() {
    const pr = state.predict;
    if (!pr.enabled || !state.trace || state.trace.compare) {
      pr.pending = null;
      return;
    }
    if (pr.pending && pr.pending.stepIdx === state.currentStep) return; // giữ nguyên (kể cả đã trả lời)
    const q = questionBefore(state.currentStep);
    pr.pending = q && !pr.answered.has(`${q.stepIdx}:${q.type}`) ? q : null;
  }

  function resetPredictQuestions() {
    state.predict.pending = null;
    state.predict.answered.clear();
  }

  function flashCaption() {
    els.caption.classList.remove("flash");
    void els.caption.offsetWidth;
    els.caption.classList.add("flash");
  }

  function predictExplanation(q) {
    const trace = state.trace;
    const bfs = trace.algorithm !== "dfs";
    if (q.type === "pop") {
      const rule = bfs
        ? "BFS lấy nút ở ĐẦU hàng đợi (vào sớm nhất → ra trước, FIFO)."
        : "DFS lấy nút ở ĐỈNH ngăn xếp (vào gần đây nhất → ra trước, LIFO).";
      return q.skipped
        ? `Đáp án: #${q.answerId}. ${rule}`
        : q.correct
          ? `Đúng! #${q.answerId} sẽ được pop. ${rule}`
          : `Chưa đúng: bạn chọn #${q.choice}, đáp án là #${q.answerId}. ${rule}`;
    }
    const detail =
      q.answer === "dup"
        ? `#${q.childId} trùng với #${q.collisionId} ${q.where === "explored" ? "đã được mở rộng xong (nằm trong explored)" : "đang chờ sẵn trong frontier"} → bị bỏ qua.`
        : `#${q.childId} chưa có trong explored lẫn frontier → là trạng thái MỚI, sẽ được thêm vào.`;
    return q.skipped ? `Đáp án: ${detail}` : q.correct ? `Đúng! ${detail}` : `Chưa đúng. ${detail}`;
  }

  function answerPredict(choice, { skip = false } = {}) {
    const pr = state.predict;
    const q = activePredictQuestion();
    if (!q || q.answered) return;
    q.answered = true;
    q.choice = choice;
    q.skipped = skip;
    q.correct = !skip && (q.type === "pop" ? choice === q.answerId : choice === q.answer);
    pr.answered.add(`${q.stepIdx}:${q.type}`);
    if (!skip) {
      pr.score.total += 1;
      if (q.correct) pr.score.right += 1;
    }
    renderStep();
  }

  // Ghi đè dòng chú thích bằng câu hỏi / phản hồi khi đang ở một bước có câu hỏi.
  function renderPredictPrompt() {
    const pr = state.predict;
    els.caption.classList.remove("predict", "predict-right", "predict-wrong");
    els.predictActions.innerHTML = "";
    els.predictActions.classList.add("hidden");
    els.predictScore.classList.toggle("hidden", !pr.enabled || pr.score.total === 0);
    els.predictScore.textContent = `Đúng ${pr.score.right}/${pr.score.total}`;

    const q = activePredictQuestion();
    if (!q) return;
    const addBtn = (label, cls, onClick) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = `btn btn-sm ${cls}`;
      b.textContent = label;
      b.addEventListener("click", onClick);
      els.predictActions.appendChild(b);
    };

    if (!q.answered) {
      els.caption.classList.add("predict");
      els.eventBadge.textContent = "🎯 DỰ ĐOÁN";
      els.eventBadge.className = "status-pill pill-indigo";
      if (q.type === "pop") {
        els.eventMessage.textContent = "Nút nào sẽ được POP tiếp theo? Bấm vào một thẻ trong frontier.";
      } else {
        els.eventMessage.textContent = `Nút con #${q.childId} sẽ bị bỏ qua (trùng) hay là trạng thái mới?`;
        addBtn("✗ Trùng → bỏ qua", "btn-secondary", () => answerPredict("dup"));
        addBtn("✓ Mới → thêm vào", "btn-secondary", () => answerPredict("new"));
      }
      addBtn("Bỏ qua", "btn-secondary", () => answerPredict(null, { skip: true }));
    } else {
      els.caption.classList.add(q.correct ? "predict-right" : q.skipped ? "predict" : "predict-wrong");
      els.eventBadge.textContent = q.skipped ? "ĐÁP ÁN" : q.correct ? "ĐÚNG ✓" : "CHƯA ĐÚNG ✗";
      els.eventBadge.className = `status-pill ${q.skipped ? "pill-indigo" : q.correct ? "pill-emerald" : "pill-rose"}`;
      els.eventMessage.textContent = predictExplanation(q);
      addBtn("Tiếp tục ▶", "btn-primary", () => stepBy(1));
    }
    els.predictActions.classList.remove("hidden");
  }

  function setPredictMode(on) {
    const pr = state.predict;
    pr.enabled = on;
    pr.pending = null;
    pr.answered.clear();
    pr.score = { right: 0, total: 0 };
    document.querySelector(".app-shell").classList.toggle("predict-on", on);
    document.body.classList.toggle("predict-on", on); // thanh phát nằm ngoài .app-shell
    els.predictBtn.setAttribute("aria-pressed", String(on));
    els.predictBtn.classList.toggle("btn-primary", on);
    els.predictBtn.classList.toggle("btn-secondary", !on);
    if (on) {
      state.stepMode = "micro"; // dự đoán cần đi từng dòng mã
      els.stepModeSelector.querySelectorAll(".seg-btn").forEach((b) => {
        b.classList.toggle("active", b.dataset.mode === "micro");
      });
      stopPlayback();
    }
    if (state.trace && !state.trace.compare) renderStep();
    else renderPredictPrompt();
  }

  // ── Chọn bài toán / thuật toán / đề mẫu ─────────────────────────────────────

  function defaultPresetFor(problem) {
    const list = state.presets.filter((q) => q.problem === problem);
    const preferred = problem === "vacuum" ? "v_both_a" : "p8_branch";
    return list.find((q) => q.id === preferred) || list[0] || null;
  }

  function populatePresets() {
    els.presetSelect.innerHTML = "";
    for (const pr of state.presets.filter((q) => q.problem === state.problem)) {
      const opt = document.createElement("option");
      opt.value = pr.id;
      opt.textContent = pr.name;
      els.presetSelect.appendChild(opt);
    }
    const customOpt = document.createElement("option");
    customOpt.value = "__custom__";
    customOpt.textContent = "— Tùy biến —";
    els.presetSelect.appendChild(customOpt);
  }

  function syncVacuumControls() {
    els.vacRobotSelector.querySelectorAll(".seg-btn").forEach((b) => {
      b.classList.toggle("active", Number(b.dataset.room) === state.vacStart.robot);
    });
    els.vacDirtA.checked = state.vacStart.dirt[0];
    els.vacDirtB.checked = state.vacStart.dirt[1];
  }

  function applyPreset(preset) {
    if (preset.problem === "vacuum") {
      state.vacStart = { robot: preset.start_state.robot, dirt: preset.start_state.dirt.slice() };
      syncVacuumControls();
    } else {
      state.size = preset.size;
      els.sizeSelector.querySelectorAll(".seg-btn").forEach((btn) => {
        btn.classList.toggle("active", Number(btn.dataset.size) === preset.size);
      });
      state.startBoard = cloneBoard(preset.start_board);
      state.targetBoard = cloneBoard(preset.target_board);
    }
  }

  function updateAlgoLabels() {
    const labels = ALGO_LABELS[state.algorithm];
    els.codeTitle.textContent = `Mã giả ${labels.name}`;
    els.frontierKind.textContent = labels.kind;
    els.axisOut.textContent = labels.out;
    els.axisIn.textContent = labels.in;
    els.algoSelector.querySelectorAll(".seg-btn").forEach((b) => {
      b.classList.toggle("active", b.dataset.algo === state.algorithm);
    });
  }

  async function setProblem(problem, { run = true } = {}) {
    state.problem = problem;
    els.problemSelector.querySelectorAll(".seg-btn").forEach((b) => {
      b.classList.toggle("active", b.dataset.problem === problem);
    });
    document.querySelectorAll(".np-only").forEach((el) => el.classList.toggle("hidden", problem !== "npuzzle"));
    document.querySelectorAll(".vac-only").forEach((el) => el.classList.toggle("hidden", problem !== "vacuum"));
    populatePresets();
    const def = defaultPresetFor(problem);
    if (def) {
      els.presetSelect.value = def.id;
      applyPreset(def);
    }
    if (run) await runSearch(false);
  }

  function onVacuumStartEdited() {
    syncVacuumControls();
    els.presetSelect.value = "__custom__";
    runSearch(false);
  }

  // Bước theo chế độ đang chọn; giữ Shift để dùng chế độ còn lại.
  function stepBy(delta, invert = false) {
    const macro = (state.stepMode === "macro") !== invert;
    if (macro) stepMacro(delta);
    else stepMicro(delta);
  }

  // Dịch bước hiện tại: macro = nhảy tới lần pop kế tiếp, micro = đúng một dòng mã.
  function moveStep(delta, macro) {
    if (!state.trace || !state.trace.steps.length) return false;
    // Chế độ Dự đoán: chưa trả lời câu hỏi thì chưa được đi tiếp.
    const q = activePredictQuestion();
    if (delta > 0 && !macro && q && !q.answered) {
      flashCaption();
      return false;
    }
    const steps = state.trace.steps;
    let idx = state.currentStep + delta;
    if (macro) {
      while (idx > 0 && idx < steps.length - 1 && !steps[idx].is_macro) idx += delta;
    }
    const next = Math.max(0, Math.min(steps.length - 1, idx));
    if (next === state.currentStep) return false;
    state.currentStep = next;
    renderStep();
    return true;
  }

  function stepMicro(delta) {
    if (!state.trace || !state.trace.steps.length) return;
    stopPlayback();
    moveStep(delta, false);
  }

  function stepMacro(delta) {
    if (!state.trace || !state.trace.steps.length) return;
    stopPlayback();
    moveStep(delta, true);
  }

  async function doShuffle() {
    stopPlayback();
    try {
      const steps = Math.max(1, Math.min(30, Number(els.shuffleSteps.value) || 5));
      els.shuffleSteps.value = String(steps);
      const data = await apiJson("/api/shuffle", {
        method: "POST",
        body: JSON.stringify({
          size: state.size,
          steps,
          target_board: state.targetBoard,
        }),
      });
      state.startBoard = data.start_board;
      state.targetBoard = data.target_board;
      els.presetSelect.value = "__custom__";
      await runSearch(false);
    } catch (err) {
      showAlert("", "Lỗi xáo trộn bảng", err.message);
    }
  }

  // Board Editor Modal
  function getDraftBoard() {
    return state.editor.activeTarget === "start"
      ? state.editor.draftStart
      : state.editor.draftTarget;
  }

  function setDraftBoard(board) {
    if (state.editor.activeTarget === "start") {
      state.editor.draftStart = board;
    } else {
      state.editor.draftTarget = board;
    }
  }

  async function refreshEditorStatus() {
    try {
      const res = await apiJson("/api/check", {
        method: "POST",
        body: JSON.stringify({
          start_board: state.editor.draftStart,
          target_board: state.editor.draftTarget,
        }),
      });
      const solv = res.solvability;
      els.editorStatus.className = `editor-status ${solv.solvable ? "ok" : "err"}`;
      els.editorStatus.textContent = solv.explanation;
      els.applyEditorBtn.disabled = false;
    } catch (err) {
      els.editorStatus.className = "editor-status err";
      els.editorStatus.textContent = err.message;
      els.applyEditorBtn.disabled = true;
    }
  }

  function renderEditorBoard() {
    const board = getDraftBoard();
    const size = board.length;
    els.editorBoardWrap.innerHTML = "";
    els.editorBoardWrap.style.gridTemplateColumns = `repeat(${size}, auto)`;

    let br = 0;
    let bc = 0;
    for (let r = 0; r < size; r++) {
      for (let c = 0; c < size; c++) {
        if (board[r][c] === 0) {
          br = r;
          bc = c;
        }
      }
    }

    for (let r = 0; r < size; r++) {
      for (let c = 0; c < size; c++) {
        const val = board[r][c];
        if (state.editor.mode === "slide") {
          const btn = document.createElement("button");
          btn.type = "button";
          const adjacent = Math.abs(r - br) + Math.abs(c - bc) === 1;
          btn.className = "editor-tile-btn" + (val === 0 ? " blank" : adjacent ? " movable" : "");
          btn.textContent = val === 0 ? "0" : String(val);
          if (adjacent) {
            btn.addEventListener("click", () => {
              board[br][bc] = val;
              board[r][c] = 0;
              renderEditorBoard();
              refreshEditorStatus();
            });
          }
          els.editorBoardWrap.appendChild(btn);
        } else {
          const inp = document.createElement("input");
          inp.type = "number";
          inp.className = "editor-tile-input";
          inp.min = "0";
          inp.max = String(size * size - 1);
          inp.value = String(val);
          inp.addEventListener("input", () => {
            const parsed = Number.parseInt(inp.value, 10);
            board[r][c] = Number.isNaN(parsed) ? -1 : parsed;
            refreshEditorStatus();
          });
          els.editorBoardWrap.appendChild(inp);
        }
      }
    }
  }

  function openEditorModal() {
    stopPlayback();
    state.editor.draftStart = cloneBoard(state.startBoard);
    state.editor.draftTarget = cloneBoard(state.targetBoard);
    state.editor.activeTarget = "start";
    els.editorModal.querySelectorAll(".editor-tabs .seg-btn").forEach((b) => {
      b.classList.toggle("active", b.dataset.target === "start");
    });
    renderEditorBoard();
    refreshEditorStatus();
    els.editorModal.classList.remove("hidden");
  }

  function closeEditorModal() {
    els.editorModal.classList.add("hidden");
  }

  // Wire up events
  function setupEventListeners() {
    els.sizeSelector.addEventListener("click", (e) => {
      const btn = e.target.closest(".seg-btn");
      if (!btn) return;
      const newSize = Number(btn.dataset.size);
      if (newSize !== state.size) {
        setSize(newSize, true);
        runSearch(false);
      }
    });

    els.compareBtn.addEventListener("click", () => setCompareMode(!state.compare.enabled));
    els.predictBtn.addEventListener("click", () => setPredictMode(!state.predict.enabled));
    for (const chart of [els.cmpDepthChart, els.cmpFrontierChart]) {
      chart.addEventListener("click", (e) => {
        if (!state.compare.enabled || !state.compare.runs.length) return;
        const rect = chart.getBoundingClientRect();
        const { W, padL, padR } = CMP_CHART;
        const x = ((e.clientX - rect.left) / rect.width) * W;
        const norm = Math.max(0, Math.min(1, (x - padL) / (W - padL - padR)));
        stopPlayback();
        state.currentStep = Math.round(norm * state.compare.maxTick);
        renderStep();
      });
    }

    els.problemSelector.addEventListener("click", (e) => {
      const btn = e.target.closest(".seg-btn");
      if (!btn || btn.dataset.problem === state.problem) return;
      stopPlayback();
      setProblem(btn.dataset.problem);
    });

    els.algoSelector.addEventListener("click", (e) => {
      const btn = e.target.closest(".seg-btn");
      if (!btn || btn.dataset.algo === state.algorithm) return;
      state.algorithm = btn.dataset.algo;
      updateAlgoLabels();
      runSearch(false);
    });

    els.vacRobotSelector.addEventListener("click", (e) => {
      const btn = e.target.closest(".seg-btn");
      if (!btn) return;
      state.vacStart.robot = Number(btn.dataset.room);
      onVacuumStartEdited();
    });
    els.vacDirtA.addEventListener("change", () => {
      state.vacStart.dirt[0] = els.vacDirtA.checked;
      onVacuumStartEdited();
    });
    els.vacDirtB.addEventListener("change", () => {
      state.vacStart.dirt[1] = els.vacDirtB.checked;
      onVacuumStartEdited();
    });

    els.presetSelect.addEventListener("change", () => {
      const preset = state.presets.find((q) => q.id === els.presetSelect.value);
      if (!preset) return;
      applyPreset(preset);
      runSearch(false);
    });

    els.shuffleBtn.addEventListener("click", doShuffle);
    els.runBtn.addEventListener("click", () => runSearch(false));
    els.graphSearchToggle.addEventListener("change", () => runSearch(false));
    els.earlyGoalToggle.addEventListener("change", () => runSearch(false));

    els.firstBtn.addEventListener("click", () => {
      stopPlayback();
      state.currentStep = 0;
      renderStep();
    });
    els.lastBtn.addEventListener("click", () => {
      if (!state.trace || !state.trace.steps.length) return;
      stopPlayback();
      state.currentStep = state.trace.steps.length - 1;
      renderStep();
    });
    els.prevBtn.addEventListener("click", () => stepBy(-1));
    els.nextBtn.addEventListener("click", () => stepBy(1));
    els.playBtn.addEventListener("click", togglePlayback);

    els.stepModeSelector.addEventListener("click", (e) => {
      const btn = e.target.closest(".seg-btn");
      if (!btn) return;
      state.stepMode = btn.dataset.mode;
      els.stepModeSelector.querySelectorAll(".seg-btn").forEach((b) => {
        b.classList.toggle("active", b === btn);
      });
    });

    els.analysisCard.addEventListener("toggle", () => {
      if (!els.analysisCard.open || !state.trace) return;
      renderMemoryChart();
    });

    els.optionsBtn.addEventListener("click", () => {
      const open = els.optionsPanel.classList.toggle("hidden") === false;
      els.optionsBtn.setAttribute("aria-expanded", String(open));
    });

    els.stepSlider.addEventListener("input", () => {
      stopPlayback();
      state.currentStep = Number(els.stepSlider.value) || 0;
      renderStep();
    });

    els.speedSelect.addEventListener("change", () => {
      if (state.playTimer !== null) {
        stopPlayback();
        togglePlayback();
      }
    });

    // Tabs
    document.querySelectorAll(".tab-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const tab = btn.dataset.tab;
        state.activeTab = tab;
        document.querySelectorAll(".tab-btn").forEach((b) => {
          const active = b.dataset.tab === tab;
          b.classList.toggle("active", active);
          b.setAttribute("aria-selected", String(active));
        });
        document.querySelectorAll(".tab-panel").forEach((p) => {
          p.classList.toggle("active", p.id === `tab-${tab}`);
        });
        if (tab === "tree") {
          fitTreeToViewport();
        } else if (tab === "telemetry") {
          renderMemoryChart();
        }
      });
    });

    // Pinned node drawer
    els.closePinnedBtn.addEventListener("click", () => {
      state.pinnedNodeId = null;
      renderPinnedNode();
      if (state.activeTab === "tree") renderSearchTree();
    });
    els.jumpCreatedBtn.addEventListener("click", () => {
      if (!state.trace || state.pinnedNodeId === null) return;
      const node = state.trace.nodes[state.pinnedNodeId];
      if (node && node.created_step !== null) {
        stopPlayback();
        state.currentStep = node.created_step;
        renderStep();
      }
    });
    els.jumpExpandedBtn.addEventListener("click", () => {
      if (!state.trace || state.pinnedNodeId === null) return;
      const node = state.trace.nodes[state.pinnedNodeId];
      if (node && node.expanded_step !== null) {
        stopPlayback();
        state.currentStep = node.expanded_step;
        renderStep();
      }
    });

    // Tree zoom & pan
    els.showPrunedToggle.addEventListener("change", renderSearchTree);
    els.treeZoomIn.addEventListener("click", () => {
      state.treeAutoFit = false;
      state.treeTransform.scale = Math.min(2.5, state.treeTransform.scale * 1.2);
      renderSearchTree();
    });
    els.treeZoomOut.addEventListener("click", () => {
      state.treeAutoFit = false;
      state.treeTransform.scale = Math.max(0.1, state.treeTransform.scale / 1.2);
      renderSearchTree();
    });
    els.treeZoomFit.addEventListener("click", fitTreeToViewport);

    let dragging = false;
    let dragStart = { x: 0, y: 0 };
    els.treeViewport.addEventListener("mousedown", (e) => {
      dragging = true;
      state.treeAutoFit = false;
      dragStart = { x: e.clientX - state.treeTransform.x, y: e.clientY - state.treeTransform.y };
    });
    window.addEventListener("mousemove", (e) => {
      if (!dragging) return;
      state.treeTransform.x = e.clientX - dragStart.x;
      state.treeTransform.y = e.clientY - dragStart.y;
      renderSearchTree();
    });
    window.addEventListener("mouseup", () => {
      dragging = false;
    });
    els.treeViewport.addEventListener("wheel", (e) => {
      e.preventDefault();
      const factor = e.deltaY < 0 ? 1.12 : 0.89;
      state.treeAutoFit = false;
      state.treeTransform.scale = Math.min(2.5, Math.max(0.1, state.treeTransform.scale * factor));
      renderSearchTree();
    }, { passive: false });

    // Click chart to jump step
    els.memoryChartSvg.addEventListener("click", (e) => {
      if (!state.trace || state.trace.steps.length <= 1) return;
      const rect = els.memoryChartSvg.getBoundingClientRect();
      const relX = (e.clientX - rect.left) / rect.width;
      const padRatioL = 42 / 640;
      const padRatioR = 16 / 640;
      const norm = Math.max(0, Math.min(1, (relX - padRatioL) / (1 - padRatioL - padRatioR)));
      stopPlayback();
      state.currentStep = Math.round(norm * (state.trace.steps.length - 1));
      renderStep();
    });

    // Editor modal
    els.editBoardBtn.addEventListener("click", openEditorModal);
    els.closeEditorBtn.addEventListener("click", closeEditorModal);
    els.cancelEditorBtn.addEventListener("click", closeEditorModal);
    els.editorModal.addEventListener("click", (e) => {
      if (e.target === els.editorModal) closeEditorModal();
    });

    els.editorModal.querySelectorAll(".editor-tabs .seg-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.editor.activeTarget = btn.dataset.target;
        els.editorModal.querySelectorAll(".editor-tabs .seg-btn").forEach((b) => {
          b.classList.toggle("active", b === btn);
        });
        renderEditorBoard();
      });
    });

    els.editorModal.querySelectorAll('input[name="editMode"]').forEach((rad) => {
      rad.addEventListener("change", () => {
        state.editor.mode = rad.value;
        renderEditorBoard();
      });
    });

    els.resetGoalBtn.addEventListener("click", () => {
      setDraftBoard(makeGoalBoard(state.size));
      renderEditorBoard();
      refreshEditorStatus();
    });

    els.applyEditorBtn.addEventListener("click", () => {
      state.startBoard = cloneBoard(state.editor.draftStart);
      state.targetBoard = cloneBoard(state.editor.draftTarget);
      els.presetSelect.value = "__custom__";
      closeEditorModal();
      runSearch(false);
    });

    // Keyboard shortcuts
    window.addEventListener("keydown", (e) => {
      const tag = document.activeElement?.tagName;
      if (tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA") return;
      if (!els.editorModal.classList.contains("hidden")) {
        if (e.key === "Escape") closeEditorModal();
        return;
      }
      if (e.key === " ") {
        e.preventDefault();
        togglePlayback();
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        stepBy(1, e.shiftKey);
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        stepBy(-1, e.shiftKey);
      } else if (e.key === "Home") {
        e.preventDefault();
        stopPlayback();
        state.currentStep = 0;
        renderStep();
      } else if (e.key === "End" && state.trace?.steps.length) {
        e.preventDefault();
        stopPlayback();
        state.currentStep = state.trace.steps.length - 1;
        renderStep();
      }
    });
  }

  async function init() {
    setupEventListeners();
    try {
      const data = await apiJson("/api/presets");
      state.presets = data.presets || [];
      updateAlgoLabels();
      await setProblem("npuzzle");
    } catch (err) {
      showAlert("", "Không kết nối được tới Python Server", err.message);
    }
  }

  init();
})();
