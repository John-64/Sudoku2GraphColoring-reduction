from functools import lru_cache
from typing import Dict, List, Set, Tuple

SUPPORTED_BLOCK_SIZES: Tuple[int, ...] = (2, 3, 4)
DEFAULT_BLOCK_SIZE = 3

# Stabilisce il numero di colori e la grandezza del "lato" della griglia
def grid_size(n: int) -> int:
    return n * n

# Trasforma una cella in un numero unico (serve perché il grafo non lavora con coordinate)
def node_id(r: int, c: int, n: int) -> int:
    return r * grid_size(n) + c

# L'inverso di node_id
def node_rc(idx: int, n: int) -> Tuple[int, int]:
    return divmod(idx, grid_size(n))

# Costruisce il grafo:
# - un nodo per ogni cella
# - un arco fra i due nodi se le celle sono in "conflitto" (stessa riga, stessa colonna, o stesso blocco)
def build_graph(n: int) -> Tuple[List[Set[int]], List[Tuple[int, int]]]:
    N = grid_size(n)
    # Lista contenente tutti i nodi vicini di un certo elemento
    adj: List[Set[int]] = [set() for _ in range(N * N)]

    # Aggiunge un arco non orientato fra a e b (ignorato se a == b)
    def add_edge(a: int, b: int) -> None:
        if a != b:
            adj[a].add(b)
            adj[b].add(a)

    # Scorre tutte le cella
    for r in range(N):
        for c in range(N):
            u = node_id(r, c, n)
            # Colleghiamo nodi sulla stessa riga
            for c2 in range(N):
                if c2 != c:
                    add_edge(u, node_id(r, c2, n))
            # Colleghiamo nodi sulla stessa colonna
            for r2 in range(N):
                if r2 != r:
                    add_edge(u, node_id(r2, c, n))
            # Colleghiamo nodi nello stesso blocco n x n
            br, bc = (r // n) * n, (c // n) * n
            for dr in range(n):
                for dc in range(n):
                    r2, c2 = br + dr, bc + dc
                    if (r2, c2) != (r, c):
                        add_edge(u, node_id(r2, c2, n))

    # Lista di archi univoci per il frontend
    edges: List[Tuple[int, int]] = []
    for u in range(N * N):
        for v in adj[u]:
            if v > u:
                edges.append((u, v))

    return adj, edges

# Solleva un errore se n non è una delle dimensioni di blocco supportate
def _check_supported(n: int) -> None:
    if n not in SUPPORTED_BLOCK_SIZES:
        raise ValueError(
            f"Unsupported block size n={n!r}; supported: {SUPPORTED_BLOCK_SIZES}"
        )

# Metodo che restituisce il grafo costruito
@lru_cache(maxsize=None) # Memorizziamo il risultato O(n⁶)
def get_graph(n: int) -> Tuple[List[Set[int]], List[Tuple[int, int]]]:
    _check_supported(n)
    return build_graph(n)

# Converte la griglia Sudoku in una pre-colorazione parziale del grafo
def grid_to_precoloring(grid: List[List[int]], n: int) -> Dict[int, int]:
    N = grid_size(n)
    colors: Dict[int, int] = {}
    for r in range(N):
        for c in range(N):
            # Per ogni cella non vuota viene salvato il colore per quel nodo
            if grid[r][c] != 0:
                colors[node_id(r, c, n)] = grid[r][c]
    return colors

# Inverso di grid_to_precoloring
def coloring_to_grid(colors: Dict[int, int], n: int) -> List[List[int]]:
    N = grid_size(n)
    grid = [[0] * N for _ in range(N)]
    for uid, color in colors.items():
        r, c = node_rc(uid, n)
        grid[r][c] = color
    return grid

# Serializzazione JSON per il frontend
def graph_json(n: int = DEFAULT_BLOCK_SIZE) -> dict:
    _check_supported(n)
    N = grid_size(n)
    _, edges = get_graph(n)
    return {
        "n": n,
        "size": N,
        "nodes": [{"id": i, "r": i // N, "c": i % N} for i in range(N * N)],
        "edges": [{"u": u, "v": v} for u, v in edges],
    }