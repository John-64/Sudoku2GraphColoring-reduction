(() => {
  "use strict";

  const SUPPORTED_N = [2, 3, 4];
  const CELL = 10; // unita' di viewBox per cella, indipendente da N
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const els = {
    grid: document.getElementById("sudoku-grid"),
    svg: document.getElementById("graph-svg"),
    boardSize: document.getElementById("board-size"),
    sudokuMeta: document.getElementById("sudoku-meta"),
    graphMeta: document.getElementById("graph-meta"),
    difficulty: document.getElementById("difficulty"),
    algorithm: document.getElementById("algorithm"),
    btnGenerate: document.getElementById("btn-generate"),
    btnClearGrid: document.getElementById("btn-clear-grid"),
    btnClearResults: document.getElementById("btn-clear-results"),
    btnSolve: document.getElementById("btn-solve"),
    stats: document.getElementById("stats"),
    banner: document.getElementById("error-banner"),
  };

  const DIFFICULTY_LABELS = { easy: "Easy", medium: "Medium", hard: "Hard", expert: "Expert" };
  const MAX_HISTORY = 25;

  const state = {
    n: 3,
    N: 9,
    grid: null,
    baseGrid: null,
    given: null,
    adjacency: new Map(),
    selected: null,
    busy: false,
    inputEls: [],
    nodeEls: [],
    edgesGroup: null,
    conflictEdgesGroup: null,
    history: [],
    runCounter: 0,
    puzzleLabel: "—",
  };

  function emptyGrid(N) {
    return Array.from({ length: N }, () => Array(N).fill(0));
  }

  function cloneGrid(g) {
    return g.map((row) => row.slice());
  }

  function idx(r, c) { return r * state.N + c; }

  function maxDigitLength(N) { return String(N).length; }

  // --- DOM construction (rebuilt on every board-size change) ---

  function buildSudokuDOM() {
    const N = state.N, n = state.n;
    els.grid.innerHTML = "";
    els.grid.style.setProperty("--cells", N);
    state.inputEls = [];
    const maxLen = maxDigitLength(N);
    const frag = document.createDocumentFragment();
    for (let r = 0; r < N; r++) {
      state.inputEls.push([]);
      for (let c = 0; c < N; c++) {
        const input = document.createElement("input");
        input.type = "text";
        input.inputMode = "numeric";
        input.maxLength = maxLen;
        input.autocomplete = "off";
        input.dataset.r = r;
        input.dataset.c = c;
        input.setAttribute("aria-label", `Row ${r + 1}, column ${c + 1}`);

        if ((c + 1) % n === 0 && c !== N - 1) input.classList.add("block-edge-col");
        if ((r + 1) % n === 0 && r !== N - 1) input.classList.add("block-edge-row");

        input.addEventListener("focus", () => selectCell(r, c));
        input.addEventListener("click", () => selectCell(r, c));
        input.addEventListener("input", onCellInput);
        input.addEventListener("keydown", onCellKeydown);

        state.inputEls[r].push(input);
        frag.appendChild(input);
      }
    }
    els.grid.appendChild(frag);
  }

  function buildGraphDOM() {
    const N = state.N, n = state.n;
    const svg = els.svg;
    const size = N * CELL;
    svg.setAttribute("viewBox", `0 0 ${size} ${size}`);
    svg.innerHTML = "";

    const guides = document.createElementNS(svg.namespaceURI, "g");
    for (let k = 1; k < n; k++) {
      const pos = k * n * CELL;
      guides.appendChild(line(pos, 0, pos, size, "guide strong"));
      guides.appendChild(line(0, pos, size, pos, "guide strong"));
    }
    svg.appendChild(guides);

    state.edgesGroup = document.createElementNS(svg.namespaceURI, "g");
    state.edgesGroup.setAttribute("id", "edges");
    svg.appendChild(state.edgesGroup);

    state.conflictEdgesGroup = document.createElementNS(svg.namespaceURI, "g");
    state.conflictEdgesGroup.setAttribute("id", "conflict-edges");
    svg.appendChild(state.conflictEdgesGroup);

    const nodesGroup = document.createElementNS(svg.namespaceURI, "g");
    state.nodeEls = [];
    const radius = N > 9 ? 2.0 : 3.1;
    for (let r = 0; r < N; r++) {
      state.nodeEls.push([]);
      for (let c = 0; c < N; c++) {
        const [x, y] = coordsFor(r, c);
        const circle = document.createElementNS(svg.namespaceURI, "circle");
        circle.setAttribute("cx", x);
        circle.setAttribute("cy", y);
        circle.setAttribute("r", radius);
        circle.classList.add("node", "empty");
        circle.dataset.r = r;
        circle.dataset.c = c;
        state.nodeEls[r].push(circle);
        nodesGroup.appendChild(circle);
      }
    }
    svg.appendChild(nodesGroup);
  }

  function coordsFor(r, c) {
    return [c * CELL + CELL / 2, r * CELL + CELL / 2];
  }

  function line(x1, y1, x2, y2, cls) {
    const el = document.createElementNS(els.svg.namespaceURI, "line");
    el.setAttribute("x1", x1); el.setAttribute("y1", y1);
    el.setAttribute("x2", x2); el.setAttribute("y2", y2);
    el.setAttribute("class", cls);
    return el;
  }

  async function loadGraph() {
    try {
      const res = await fetch(`/graph?n=${state.n}`);
      if (!res.ok) throw new Error("graph fetch failed");
      const data = await res.json();
      state.adjacency = new Map(data.nodes.map((nd) => [nd.id, new Set()]));
      data.edges.forEach(({ u, v }) => {
        state.adjacency.get(u).add(v);
        state.adjacency.get(v).add(u);
      });
      updateMeta(data);
    } catch (err) {
      showError("Unable to load the graph structure. Restart the server and refresh the page.");
    }
  }

  function updateMeta(graphData) {
    const N = state.N;
    const vertexCount = graphData.nodes.length;
    const edgeCount = graphData.edges.length;
    els.sudokuMeta.textContent = `${N} × ${N} cells`;
    els.graphMeta.textContent = `${vertexCount} vertices · ${edgeCount} edges`;
  }

  function renderCell(r, c) {
    const v = state.grid[r][c];
    const input = state.inputEls[r][c];
    input.value = v === 0 ? "" : String(v);
    input.dataset.v = v === 0 ? "" : String(v);
    input.readOnly = !!state.given[r][c];
    input.classList.toggle("given", !!state.given[r][c]);

    const node = state.nodeEls[r][c];
    if (v === 0) {
      node.classList.add("empty");
      node.removeAttribute("data-v");
    } else {
      node.classList.remove("empty");
      node.dataset.v = String(v);
    }
  }

  function renderAll() {
    const N = state.N;
    for (let r = 0; r < N; r++) for (let c = 0; c < N; c++) renderCell(r, c);
  }

  function findConflicts(grid) {
    const N = state.N;
    const cells = new Set();
    const edges = [];
    for (let r = 0; r < N; r++) {
      for (let c = 0; c < N; c++) {
        const v = grid[r][c];
        if (v === 0) continue;
        const u = idx(r, c);
        const neighbours = state.adjacency.get(u) || new Set();
        neighbours.forEach((nIdx) => {
          if (nIdx <= u) return;
          const nr = Math.floor(nIdx / N), nc = nIdx % N;
          if (grid[nr][nc] === v) {
            cells.add(u);
            cells.add(nIdx);
            edges.push([u, nIdx]);
          }
        });
      }
    }
    return { cells, edges };
  }

  function renderConflicts() {
    const N = state.N;
    const { cells, edges } = findConflicts(state.grid);

    for (let r = 0; r < N; r++) {
      for (let c = 0; c < N; c++) {
        const flagged = cells.has(idx(r, c));
        state.inputEls[r][c].classList.toggle("conflict", flagged);
        state.nodeEls[r][c].classList.toggle("conflict", flagged);
      }
    }

    state.conflictEdgesGroup.innerHTML = "";
    edges.forEach(([u, v]) => {
      const [x1, y1] = coordsFor(Math.floor(u / N), u % N);
      const [x2, y2] = coordsFor(Math.floor(v / N), v % N);
      state.conflictEdgesGroup.appendChild(line(x1, y1, x2, y2, "edge conflict-edge"));
    });

    return cells.size > 0;
  }

  function refreshGrid() {
    renderAll();
    renderConflicts();
  }

  function selectCell(r, c) {
    if (state.selected && state.selected.r === r && state.selected.c === c) return;
    clearSelection();
    state.selected = { r, c };

    const u = idx(r, c);
    const neighbours = state.adjacency.get(u) || new Set();

    state.inputEls[r][c].classList.add("selected");
    state.nodeEls[r][c].classList.add("selected");

    state.edgesGroup.innerHTML = "";
    const [x1, y1] = coordsFor(r, c);

    neighbours.forEach((nIdx) => {
      const N = state.N;
      const nr = Math.floor(nIdx / N), nc = nIdx % N;
      state.inputEls[nr][nc].classList.add("related");
      state.nodeEls[nr][nc].classList.add("related");
      const [x2, y2] = coordsFor(nr, nc);
      state.edgesGroup.appendChild(line(x1, y1, x2, y2, "edge lit"));
    });
  }

  function clearSelection() {
    if (!state.selected) return;
    document.querySelectorAll(".selected, .related").forEach((el) => {
      el.classList.remove("selected", "related");
    });
    if (state.edgesGroup) state.edgesGroup.innerHTML = "";
    state.selected = null;
  }

  document.addEventListener("click", (e) => {
    if (!e.target.closest(".panel")) clearSelection();
  });

  function onCellInput(e) {
    const input = e.target;
    const r = Number(input.dataset.r), c = Number(input.dataset.c);
    const N = state.N;
    const maxLen = maxDigitLength(N);

    let digits = input.value.replace(/[^0-9]/g, "").slice(-maxLen);
    let value = digits === "" ? 0 : Number(digits);
    if (value > N) {
      digits = digits.slice(-1);
      value = digits === "" ? 0 : Number(digits);
      if (value > N) { digits = ""; value = 0; }
    }

    state.grid[r][c] = value;
    state.baseGrid[r][c] = value;
    state.puzzleLabel = "custom";
    renderCell(r, c);
    renderConflicts();
    input.value = digits;
    if (state.selected && state.selected.r === r && state.selected.c === c) {
      selectCellRefresh();
    }
  }

  function selectCellRefresh() {
    const { r, c } = state.selected;
    state.selected = null;
    selectCell(r, c);
  }

  function onCellKeydown(e) {
    const N = state.N;
    const r = Number(e.target.dataset.r), c = Number(e.target.dataset.c);
    const moves = {
      ArrowUp: [-1, 0], ArrowDown: [1, 0], ArrowLeft: [0, -1], ArrowRight: [0, 1],
    };
    if (moves[e.key]) {
      e.preventDefault();
      const [dr, dc] = moves[e.key];
      const nr = Math.min(N - 1, Math.max(0, r + dr));
      const nc = Math.min(N - 1, Math.max(0, c + dc));
      state.inputEls[nr][nc].focus();
    }
  }

  function setBusy(busy) {
    state.busy = busy;
    [els.btnGenerate, els.btnClearGrid, els.btnClearResults, els.btnSolve, els.boardSize].forEach((b) => (b.disabled = busy));
  }

  function showError(msg) {
    els.banner.textContent = msg;
    els.banner.classList.add("visible");
  }

  function hideError() {
    els.banner.classList.remove("visible");
  }

  function updateExpertAvailability() {
    const expertOption = els.difficulty.querySelector('option[value="expert"]');
    if (!expertOption) return;
    const available = state.n === 3;
    expertOption.disabled = !available;
    expertOption.textContent = available ? "Expert (AI Escargot)" : "Expert (only for 9 × 9)";
    if (!available && els.difficulty.value === "expert") {
      els.difficulty.value = "medium";
    }
  }

  async function generatePuzzle() {
    if (state.busy) return;
    hideError();
    setBusy(true);
    try {
      const params = new URLSearchParams({ difficulty: els.difficulty.value, n: String(state.n) });

      const res = await fetch(`/generate?${params.toString()}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Generation failed");

      clearSelection();
      state.grid = data.grid;
      state.baseGrid = cloneGrid(data.grid);
      state.given = data.grid.map((row) => row.map((v) => (v !== 0 ? 1 : 0)));
      state.puzzleLabel = DIFFICULTY_LABELS[data.difficulty] || data.difficulty;
      if (data.seed !== null && data.seed !== undefined) state.puzzleLabel += ` · seed ${data.seed}`;
      refreshGrid();
    } catch (err) {
      showError(err.message);
    } finally {
      setBusy(false);
    }
  }

  function clearPuzzle() {
    if (state.busy) return;
    hideError();
    clearSelection();
    state.grid = emptyGrid(state.N);
    state.baseGrid = emptyGrid(state.N);
    state.given = emptyGrid(state.N);
    state.puzzleLabel = "—";
    refreshGrid();
  }

  function clearResults() {
    if (state.busy) return;
    hideError();
    resetHistory();
  }

  async function solvePuzzle() {
    if (state.busy) return;
    hideError();

    if (findConflicts(state.baseGrid).cells.size > 0) {
      showError("The grid has repeated digits within the same row, column, or box (highlighted in red): please correct them before solving.");
      return;
    }

    setBusy(true);
    setSolving(true);  // spinner + "Solving..." sul bottone, mentre la richiesta e' in volo
    const algorithm = els.algorithm.value;

    clearSelection();
    state.grid = cloneGrid(state.baseGrid);
    renderAll();

    try {
      const res = await fetch("/solve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ grid: state.grid, algorithm, n: state.n }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Solving failed");

      setSolving(false);  // risposta arrivata: da qui in poi e' l'animazione, non l'attesa
      await animateSteps(data.primary.steps || []);

      state.grid = data.primary.success ? data.primary.solution : cloneGrid(state.baseGrid);
      refreshGrid();
      addRun(data.primary, data.secondary);
    } catch (err) {
      showError(err.message);
    } finally {
      setSolving(false);
      setBusy(false);
    }
  }

  // Mostra/nasconde lo spinner sul bottone Solve e cambia l'etichetta, per far capire
  // che il server sta ancora calcolando (la richiesta /solve e' sincrona: puo' durare
  // anche diversi secondi prima che torni qualcosa da animare)
  function setSolving(isSolving) {
    els.btnSolve.classList.toggle("is-loading", isSolving);
    els.btnSolve.querySelector(".btn-label").textContent = isSolving ? "Solving…" : "Solve";
  }

  function animateSteps(steps) {
    return new Promise((resolve) => {
      if (steps.length === 0 || reducedMotion) {
        steps.forEach(([r, c, v]) => { state.grid[r][c] = v; renderCell(r, c); });
        resolve();
        return;
      }
      const maxFrames = 420;
      const batch = Math.max(1, Math.ceil(steps.length / maxFrames));
      const frameDelay = 16;
      let i = 0;
      const tick = () => {
        for (let k = 0; k < batch && i < steps.length; k++, i++) {
          const [r, c, v] = steps[i];
          state.grid[r][c] = v;
          renderCell(r, c);
        }
        if (i < steps.length) requestAnimationFrame(() => setTimeout(tick, frameDelay));
        else resolve();
      };
      tick();
    });
  }

  function resetHistory() {
    state.history = [];
    state.runCounter = 0;
    renderHistory();
  }

  function computeDelta(primary, secondary) {
    if (primary.nodes > 0 && secondary.nodes > 0) {
      const ratio = secondary.nodes / primary.nodes;
      return `DSATUR explores ${ratio.toFixed(1)}× fewer nodes than naive backtracking on this instance.`;
    }
    return null;
  }

  function outcomeLabel(row) {
    if (row.success) return { cls: "success", text: "Solved" };
    if (row.guard_triggered) {
      const reason = row.guard_reason === "time" ? "time limit" : row.guard_reason === "nodes" ? "node limit" : null;
      return { cls: "fail", text: reason ? `Guard (incomplete – ${reason})` : "Guard (incomplete)" };
    }
    return { cls: "fail", text: "No solution" };
  }

  function addRun(primary, secondary) {
    state.runCounter += 1;
    state.history.unshift({
      run: state.runCounter,
      puzzle: `${state.N}×${state.N} · ${state.puzzleLabel}`,
      rows: secondary ? [primary, secondary] : [primary],
      delta: secondary ? computeDelta(primary, secondary) : null,
    });
    if (state.history.length > MAX_HISTORY) state.history.pop();
    renderHistory();
  }

  function renderHistory() {
    if (state.history.length === 0) {
      els.stats.innerHTML = '<p class="stats-empty">Generate or load a Sudoku puzzle, then click <strong>Solve</strong>. The results will remain visible until you click the clear icon above.</p>';
      return;
    }

    const body = state.history.map((entry, i) => {
      const group = i % 2 === 0 ? "run-a" : "run-b";
      const algoRows = entry.rows.map((r) => {
        const outcome = outcomeLabel(r);
        return `
        <tr class="${group}">
          <td class="num">${entry.run}</td>
          <td>${entry.puzzle}</td>
          <td>${r.algorithm}</td>
          <td><span class="tag ${outcome.cls}">${outcome.text}</span></td>
          <td class="num">${r.nodes.toLocaleString("en-US")}</td>
          <td class="num">${r.time_ms.toLocaleString("en-US")} ms</td>
        </tr>`;
      }).join("");
      const deltaRow = entry.delta
        ? `<tr class="${group} delta-row"><td colspan="6">${entry.delta}</td></tr>`
        : "";
      return algoRows + deltaRow;
    }).join("");

    els.stats.innerHTML = `
      <table class="stat-table">
        <thead><tr><th>Run</th><th>Puzzle</th><th>Algorithm</th><th>Outcome</th><th>Nodes Explored</th><th>Time</th></tr></thead>
        <tbody>${body}</tbody>
      </table>`;
  }

  async function applyBoardSize(n, { resetHistoryToo = true } = {}) {
    state.n = n;
    state.N = n * n;
    clearSelection();
    state.grid = emptyGrid(state.N);
    state.baseGrid = emptyGrid(state.N);
    state.given = emptyGrid(state.N);
    state.puzzleLabel = "—";

    buildSudokuDOM();
    buildGraphDOM();
    updateExpertAvailability();
    await loadGraph();
    refreshGrid();
    if (resetHistoryToo) resetHistory();
  }

  async function onBoardSizeChange() {
    if (state.busy) return;
    hideError();
    setBusy(true);
    try {
      await applyBoardSize(Number(els.boardSize.value));
    } catch (err) {
      showError(err.message);
    } finally {
      setBusy(false);
    }
  }

  els.btnGenerate.addEventListener("click", generatePuzzle);
  els.btnClearGrid.addEventListener("click", clearPuzzle);
  els.btnClearResults.addEventListener("click", clearResults);
  els.btnSolve.addEventListener("click", solvePuzzle);
  els.boardSize.addEventListener("change", onBoardSizeChange);

  (async function init() {
    const initialN = Number(els.boardSize.value) || 3;
    await applyBoardSize(initialN, { resetHistoryToo: false });
  })();
})();
