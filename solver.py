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

# Impostazione per i limiti
MAX_STEPS = 100_000      # limite step per l'animazione
MAX_NODES = 500_000_000  # guard per puzzle irrisolvibili
MAX_SECONDS = 300.0     # guard sul tempo

#=== Helper ===#

# Restituisce i ancora disponibili per un nodo (visitando i vicini)
def available_colors(uid: int, colors: Dict[int, int], adj: List[set], N: int) -> List[int]:
    used = {colors[nb] for nb in adj[uid] if nb in colors}  # colori già presi dai vicini
    return [c for c in range(1, N + 1) if c not in used]  # domino residuo del nodo

# Uguale a available_colors ma non restituisce l'insieme, bensì solo la quantità
def saturation(uid: int, colors: Dict[int, int], adj: List[set]) -> int:
    return len({colors[nb] for nb in adj[uid] if nb in colors})  # grado di saturazione (DSATUR)

#=== Algoritmo 1: DSATUR + Forward Checking ===#
def solve_dsatur(grid: List[List[int]], n: int = DEFAULT_BLOCK_SIZE) -> dict:
    # Preparazione iniziale
    start = time.perf_counter()
    N = grid_size(n)
    adj, _ = get_graph(n) # ottiene il grafo
    colors = grid_to_precoloring(grid, n)  # converte la griglia in pre-colorazione fissata
    uncolored = [u for u in range(N * N) if u not in colors]

    # Contatori e flags
    nodes_explored = [0]
    overflow = [False]
    guard_triggered = [False]
    guard_reason = [None]

    # Animazione per il frontend
    anim_steps: List[Tuple[int, int, int]] = []
    def _record(r, c, val):
        if not overflow[0]:
            anim_steps.append((r, c, val))
            if len(anim_steps) >= MAX_STEPS:
                overflow[0] = True

    # Controllo sui limiti (guard); tempo controllato a ogni chiamata
    def _guard_hit() -> bool:
        if nodes_explored[0] > MAX_NODES:  # troppi nodi esplorati
            guard_reason[0] = "nodes"
            return True
        if (time.perf_counter() - start) > MAX_SECONDS:  # troppo tempo
            guard_reason[0] = "time"
            return True
        return False

    # Ricerca ricorsiva: assegna un colore al nodo più vincolato, con forward checking
    def backtrack(uncolored_set: set, colors: Dict[int, int]) -> bool:
        # Guard check
        if _guard_hit():
            guard_triggered[0] = True
            return False

        # Condizione di arresto
        if not uncolored_set:
            return True  # tutti i nodi colorati -> soluzione trovata!

        # DSATUR: scegli il nodo con saturazione massima; a parità, grado massimo
        uid = max(
            uncolored_set,
            key=lambda u: (saturation(u, colors, adj), len(adj[u]))
        )

        # Per ogni colore ammissibile
        for color in available_colors(uid, colors, adj, N):
            nodes_explored[0] += 1
            colors[uid] = color  # assegna un colore al nodo uid (tentativo)
            r, c = node_rc(uid, n)
            _record(r, c, color)

            remaining = uncolored_set - {uid}
            affected = adj[uid] & remaining  # vicini non colorati impattati dalla scelta

            # Forward checking: assume valore vero solo se ogni vicino non colorato ha ancora almeno una cifra disponibile
            ok = all(available_colors(nb, colors, adj, N) for nb in affected)  # se false, si scarta subito

            if ok and backtrack(remaining, colors):  # ricorsione solo se nessun vicino è in stallo
                return True

            # Backtrack: colore successivo
            del colors[uid]
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
        "guard_reason": guard_reason[0],
    }

#=== Algoritmo 2: Backtracking Naive (senza euristica) ===#
def solve_naive(grid: List[List[int]], n: int = DEFAULT_BLOCK_SIZE) -> dict:
    # Preparazione iniziale (identica a solve_dsatur)
    start = time.perf_counter()
    N = grid_size(n)
    adj, _ = get_graph(n)  # ottiene il grafo
    colors = grid_to_precoloring(grid, n)  # converte la griglia in pre-colorazione fissata
    uncolored = [u for u in range(N * N) if u not in colors]

    # Contatori e flags
    nodes_explored = [0]
    overflow = [False]
    guard_triggered = [False]
    guard_reason = [None]

    # Animazione per il frontend
    anim_steps: List[Tuple[int, int, int]] = []
    def _record(r, c, val):
        if not overflow[0]:
            anim_steps.append((r, c, val))
            if len(anim_steps) >= MAX_STEPS:
                overflow[0] = True

    # Controllo sui limiti (guard); tempo controllato a ogni chiamata
    def _guard_hit() -> bool:
        if nodes_explored[0] > MAX_NODES:
            guard_reason[0] = "nodes"
            return True
        if (time.perf_counter() - start) > MAX_SECONDS:
            guard_reason[0] = "time"
            return True
        return False

    # Ricerca ricorsiva: stesso schema di solve_dsatur senza euristica
    def backtrack(uncolored_set: set, colors: Dict[int, int]) -> bool:
        # Guard check
        if _guard_hit():
            guard_triggered[0] = True
            return False

        # Condizione di arresto
        if not uncolored_set:
            return True  # tutti i nodi colorati -> soluzione trovata!

        # Nessuna euristica: si prende sempre il nodo con id piu' piccolo (un ordine
        # fisso e arbitrario, equivalente al "riga per riga" di prima ma sui nodi)
        uid = min(uncolored_set)

        # Per ogni colore ammissibile, in ordine crescente (nessuna scelta "furba")
        for color in available_colors(uid, colors, adj, N):
            nodes_explored[0] += 1
            colors[uid] = color  # assegna un colore al nodo uid (tentativo)
            r, c = node_rc(uid, n)
            _record(r, c, color)

            remaining = uncolored_set - {uid}

            # Nessun forward checking: un eventuale vicino bloccato si scopre solo
            # quando la ricorsione ci arriva sopra, non prima -- per questo naive
            # esplora rami "morti" che DSATUR avrebbe scartato subito
            if backtrack(remaining, colors):
                return True

            # Backtrack: colore successivo
            del colors[uid]
            _record(r, c, 0)

        return False  # nessun colore ha funzionato per uid

    success = backtrack(set(uncolored), colors)
    elapsed_ms = (time.perf_counter() - start) * 1000

    return {
        "algorithm": "Backtracking Naive",  # stessa "forma" di solve_dsatur: confronto diretto nel frontend
        "success": success,
        "solution": coloring_to_grid(colors, n) if success else None,
        "nodes": nodes_explored[0],
        "time_ms": round(elapsed_ms, 2),
        "steps": anim_steps,
        "steps_overflow": overflow[0],
        "guard_triggered": guard_triggered[0],
        "guard_reason": guard_reason[0],
    }
