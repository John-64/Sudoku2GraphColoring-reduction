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

# Impostazione per i limiti (alzati per dare margine al caso peggiore, 16x16 hard
# con naive; per n=2/3 questi limiti non vengono mai raggiunti, quindi non cambia nulla)
MAX_STEPS = 8_000      # limite step per l'animazione
MAX_NODES = 30_000_000  # guard per puzzle irrisolvibili
MAX_SECONDS = 25.0     # guard sul tempo

#=== Helper ===#

# Calcola quali colori sono ancora disponibili per un nodo (visitando i vicini)
def available_colors(uid: int, colors: Dict[int, int], adj: List[set], N: int) -> List[int]:
    used = {colors[nb] for nb in adj[uid] if nb in colors}  # colori già presi dai vicini
    return [c for c in range(1, N + 1) if c not in used]  # domino residuo del nodo

# Uguale a available_colors ma non restituisce l'insieme, bensì solo la quantità
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

    # Contatori
    nodes_explored = [0]
    overflow = [False]
    guard_triggered = [False]
    guard_reason = [None]  # "nodes" o "time": dice al frontend QUALE guard e' scattato

    # Animazione per il frontend
    anim_steps: List[Tuple[int, int, int]] = []
    def _record(r, c, val):
        if not overflow[0]:
            anim_steps.append((r, c, val))
            if len(anim_steps) >= MAX_STEPS:
                overflow[0] = True

    # Controllo sui limiti (guard). Il tempo va controllato a OGNI chiamata, non ogni
    # 2048 nodi: nelle fasi iniziali (poche celle colorate) la selezione DSATUR scorre
    # tutti i nodi non colorati, quindi i nodi arrivano molto piu' lentamente e il
    # 2048-esimo potrebbe non arrivare mai in tempo utile, lasciando il guard sul
    # tempo "muto" proprio nei casi peggiori.
    def _guard_hit() -> bool:
        if nodes_explored[0] > MAX_NODES:  # troppi nodi esplorati
            guard_reason[0] = "nodes"
            return True
        if (time.perf_counter() - start) > MAX_SECONDS:  # troppo tempo
            guard_reason[0] = "time"
            return True
        return False

    # Ricerca ricorsiva: assegna un colore al nodo piu' vincolato, con forward checking
    def backtrack(uncolored_set: set, colors: Dict[int, int]) -> bool:
        # Guard check
        if _guard_hit():
            guard_triggered[0] = True 
            return False
        
        # Condizione di arresto
        if not uncolored_set:
            return True  # tutti i nodi colorati -> soluzione trovata!

        # DSATUR: scegli il nodo con saturazione massima; a parita', grado massimo
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

            # Forward checking: assume valore vero solo se ogni vicino non colorato ha ancora almeno una cifra disponibile
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

#=== Algoritmo 2: Backtracking Naive (riga per riga) ===#
def solve_naive(grid: List[List[int]], n: int = DEFAULT_BLOCK_SIZE) -> dict:
    # Preparazione iniziale
    start = time.perf_counter()
    N = grid_size(n)
    board = [row[:] for row in grid]

    # Contatori
    nodes_explored = [0]
    overflow = [False]
    guard_triggered = [False]
    guard_reason = [None]  # "nodes" o "time": dice al frontend QUALE guard e' scattato

    # Animazione per il frontend
    anim_steps: List[Tuple[int, int, int]] = []
    def _record(r, c, val):
        if not overflow[0]:
            anim_steps.append((r, c, val))
            if len(anim_steps) >= MAX_STEPS:
                overflow[0] = True

    # Controllo sui limiti (guard); tempo controllato a ogni chiamata, non a campione
    def _guard_hit() -> bool:
        if nodes_explored[0] > MAX_NODES:
            guard_reason[0] = "nodes"
            return True
        if (time.perf_counter() - start) > MAX_SECONDS:
            guard_reason[0] = "time"
            return True
        return False

    # Verifica che "val" non sia già presente in: riga, colonna o blocco di (r, c)
    def is_valid(r: int, c: int, val: int) -> bool:
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
        # Guard check
        if _guard_hit():
            guard_triggered[0] = True
            return False
        
        for r in range(N):
            for c in range(N):
                if board[r][c] == 0:  # Seleziona la prima cella vuota in ordine riga-per-riga (non ci sono euristiche!)
                    # Per quella cella prova tutte le cifre
                    for val in range(1, N + 1): # tentativi in ordine crescente
                        nodes_explored[0] += 1
                        # Se è valido, la scrive e fa la ricorsione
                        if is_valid(r, c, val):
                            board[r][c] = val
                            _record(r, c, val)
                            if backtrack():
                                return True
                            # Se la ricorsione fallisce, cancella il valore e prova la cifra successiva
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
        "guard_reason": guard_reason[0],
    }