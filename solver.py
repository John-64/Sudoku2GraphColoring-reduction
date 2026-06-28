import time
from typing import Dict, List, Tuple

from reduction import (
    DEFAULT_BLOCK_SIZE,
    get_graph,
    grid_size,
    grid_to_precoloring,
    coloring_to_grid,
    node_rc,
)


MAX_STEPS = 8_000   # limite step per l'animazione (non per il conteggio nodi)
MAX_NODES = 2_000_000  # guard per puzzle irrisolvibili / buggy input
MAX_SECONDS = 8.0   # guard sul tempo di parete: a n=4 (16 colori) la ricerca
                     # puo' esplodere combinatoriamente molto piu' in fretta
                     # che a n=3, anche restando sotto MAX_NODES

# Helper


def available_colors(uid: int, colors: Dict[int, int], adj: List[set], N: int) -> List[int]:
    """Cifre 1..N non usate dai vicini colorati di uid."""
    used = {colors[nb] for nb in adj[uid] if nb in colors}  # colori gia' presi dai vicini
    return [c for c in range(1, N + 1) if c not in used]  # domino residuo del nodo


def saturation(uid: int, colors: Dict[int, int], adj: List[set]) -> int:
    """Numero di colori distinti usati dai vicini di uid."""
    return len({colors[nb] for nb in adj[uid] if nb in colors})  # grado di saturazione (DSATUR)

# 1. DSATUR + Forward Checking


# Risolve l'istanza di Pre-coloring Extension con DSATUR + forward checking sul grafo
def solve_dsatur(grid: List[List[int]], n: int = DEFAULT_BLOCK_SIZE) -> dict:
    start = time.perf_counter()
    N = grid_size(n)
    adj, _ = get_graph(n)

    colors = grid_to_precoloring(grid, n)  # pre-colorazione fissata dalle celle gia' piene
    uncolored = [u for u in range(N * N) if u not in colors]

    nodes_explored = [0]  # liste di un elemento: stato mutabile condiviso dalle closure sotto
    anim_steps: List[Tuple[int, int, int]] = []  # log (r, c, val) per l'animazione frontend
    overflow = [False]
    guard_triggered = [False]

    # Aggiunge uno step al log per l'animazione, se non si e' superato il limite
    def _record(r, c, val):
        if not overflow[0]:
            anim_steps.append((r, c, val))
            if len(anim_steps) >= MAX_STEPS:
                overflow[0] = True

    # Controlla se i guard (nodi esplorati / tempo) sono scattati
    def _guard_hit() -> bool:
        if nodes_explored[0] > MAX_NODES:  # troppi nodi esplorati
            return True
        if nodes_explored[0] % 2048 == 0 and (time.perf_counter() - start) > MAX_SECONDS:  # troppo tempo
            return True
        return False

    # Ricerca ricorsiva: assegna un colore al nodo piu' vincolato, con forward checking
    def backtrack(uncolored_set: set, colors: Dict[int, int]) -> bool:
        if _guard_hit():
            guard_triggered[0] = True  # ricerca abortita: non e' una prova di "nessuna soluzione"
            return False
        if not uncolored_set:
            return True  # tutti i nodi colorati -> soluzione trovata

        # DSATUR: scegli il nodo con saturazione massima; a parita', grado massimo
        uid = max(
            uncolored_set,
            key=lambda u: (saturation(u, colors, adj), len(adj[u]))
        )

        for color in available_colors(uid, colors, adj, N):  # prova ogni colore ammissibile
            nodes_explored[0] += 1
            colors[uid] = color  # assegna (tentativo)
            r, c = node_rc(uid, n)
            _record(r, c, color)

            remaining = uncolored_set - {uid}
            affected = adj[uid] & remaining  # vicini non colorati impattati dalla scelta
            ok = all(available_colors(nb, colors, adj, N) for nb in affected)  # forward checking

            if ok and backtrack(remaining, colors):  # ricorsione solo se nessun vicino e' in stallo
                return True

            del colors[uid]  # backtrack: disfa l'assegnazione
            _record(r, c, 0)

        return False  # nessun colore ha funzionato per uid

    success = backtrack(set(uncolored), colors)
    elapsed_ms = (time.perf_counter() - start) * 1000

    return {
        "algorithm": "DSATUR + Forward Checking",  # stessa "forma" di solve_naive: confronto diretto nel frontend
        "success": success,
        "solution": coloring_to_grid(colors, n) if success else None,
        "nodes": nodes_explored[0],
        "time_ms": round(elapsed_ms, 2),
        "steps": anim_steps,
        "steps_overflow": overflow[0],
        "guard_triggered": guard_triggered[0],
    }

# 2. Backtracking Naive (riga-per-riga)


# Risolve lo stesso Sudoku con backtracking puro, senza grafo o euristiche
def solve_naive(grid: List[List[int]], n: int = DEFAULT_BLOCK_SIZE) -> dict:
    start = time.perf_counter()
    N = grid_size(n)
    board = [row[:] for row in grid]
    nodes_explored = [0]
    anim_steps: List[Tuple[int, int, int]] = []
    overflow = [False]
    guard_triggered = [False]

    # Aggiunge uno step al log per l'animazione, se non si e' superato il limite
    def _record(r, c, val):
        if not overflow[0]:
            anim_steps.append((r, c, val))
            if len(anim_steps) >= MAX_STEPS:
                overflow[0] = True

    # Controlla se i guard (nodi esplorati / tempo) sono scattati
    def _guard_hit() -> bool:
        if nodes_explored[0] > MAX_NODES:
            return True
        if nodes_explored[0] % 2048 == 0 and (time.perf_counter() - start) > MAX_SECONDS:
            return True
        return False

    # Verifica che val non sia gia' presente in riga, colonna o blocco di (r, c)
    def is_valid(r: int, c: int, val: int) -> bool:
        # nessun grafo qui: controlla riga, colonna e blocco direttamente sulla griglia
        if val in board[r]:
            return False
        if any(board[i][c] == val for i in range(N)):
            return False
        br, bc = (r // n) * n, (c // n) * n
        for dr in range(n):
            for dc in range(n):
                if board[br + dr][bc + dc] == val:
                    return False
        return True

    # Ricerca ricorsiva riga-per-riga: prima cella vuota, prima cifra valida
    def backtrack() -> bool:
        if _guard_hit():
            guard_triggered[0] = True
            return False
        for r in range(N):
            for c in range(N):
                if board[r][c] == 0:  # prima cella vuota in ordine riga-per-riga (no heuristica)
                    for val in range(1, N + 1):  # prova le cifre in ordine crescente
                        nodes_explored[0] += 1
                        if is_valid(r, c, val):
                            board[r][c] = val
                            _record(r, c, val)
                            if backtrack():
                                return True
                            board[r][c] = 0  # backtrack: disfa il tentativo
                            _record(r, c, 0)
                    return False  # nessuna cifra valida per questa cella -> fallimento
        return True  # nessuna cella vuota rimasta -> soluzione trovata

    success = backtrack()
    elapsed_ms = (time.perf_counter() - start) * 1000

    return {
        "algorithm": "Backtracking Naive",  # nessun uso del grafo/adiacenze, solo la griglia
        "success": success,
        "solution": board if success else None,
        "nodes": nodes_explored[0],
        "time_ms": round(elapsed_ms, 2),
        "steps": anim_steps,
        "steps_overflow": overflow[0],
        "guard_triggered": guard_triggered[0],
    }
