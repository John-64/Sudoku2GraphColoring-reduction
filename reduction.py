"""
Riduzione (famiglia di riduzioni, una per ogni n) da Sudoku generalizzato
n^2 x n^2 a Pre-coloring Extension (caso particolare di Graph Coloring in
cui parte dei nodi e' gia' colorata in partenza).

Per ogni dimensione di blocco n:
- ogni cella (r, c) della griglia n^2 x n^2 diventa un nodo  -> n^4 nodi;
- due nodi sono collegati se le celle condividono un vincolo (stessa riga,
  stessa colonna o stesso blocco n x n)                      -> grado 3n^2-2n-1;
- le celle gia' riempite diventano una pre-colorazione fissata.

n=3 e' il Sudoku classico 9x9 (81 nodi, grado 20, 810 archi); n=2 e n=4
generalizzano la stessa costruzione a 4x4 e 16x16. La mappa istanza->istanza
e' calcolabile in tempo Theta(n^6) (n^4 celle, O(n^2) lavoro ciascuna per
riga/colonna/blocco) -- bound stretto, non solo upper bound, perche' il
grafo stesso ha Theta(n^6) archi, quindi nessun algoritmo che li scriva
tutti puo' fare meglio. Questo e' il punto centrale per discutere la
riduzione come oggetto a dimensione variabile e non come singola istanza
fissata. Si veda il README per la discussione completa su cosa questa
riduzione prova (e cosa non prova) circa NP-completezza.
"""

from functools import lru_cache
from typing import Dict, List, Set, Tuple

# Dimensioni di blocco supportate: n=2 -> griglia 4x4, n=3 -> 9x9 (classico),
# n=4 -> 16x16. n^2 e' sia il lato della griglia sia il numero di colori.
SUPPORTED_BLOCK_SIZES: Tuple[int, ...] = (2, 3, 4)
DEFAULT_BLOCK_SIZE = 3


def grid_size(n: int) -> int:
    """Lato della griglia (e numero di colori) per blocco n x n."""
    return n * n


def node_id(r: int, c: int, n: int) -> int:
    """Indice lineare del nodo (r, c) per una griglia di blocco n."""
    return r * grid_size(n) + c


def node_rc(idx: int, n: int) -> Tuple[int, int]:
    """Ritorna (riga, colonna) dall'indice lineare per blocco n."""
    return divmod(idx, grid_size(n))


def build_graph(n: int) -> Tuple[List[Set[int]], List[Tuple[int, int]]]:
    """
    Costruisce il grafo dell'istanza di Pre-coloring Extension per il
    Sudoku generalizzato di blocco n (griglia n^2 x n^2).

    Returns
    -------
    adj   : list[set[int]]  - adj[u] = vicini del nodo u
    edges : list[(u,v)]     - archi con u < v
    """
    N = grid_size(n)
    adj: List[Set[int]] = [set() for _ in range(N * N)]

    def add_edge(a: int, b: int) -> None:
        if a != b:
            adj[a].add(b)
            adj[b].add(a)

    for r in range(N):
        for c in range(N):
            u = node_id(r, c, n)
            # stessa riga
            for c2 in range(N):
                if c2 != c:
                    add_edge(u, node_id(r, c2, n))
            # stessa colonna
            for r2 in range(N):
                if r2 != r:
                    add_edge(u, node_id(r2, c, n))
            # stesso blocco n x n
            br, bc = (r // n) * n, (c // n) * n
            for dr in range(n):
                for dc in range(n):
                    r2, c2 = br + dr, bc + dc
                    if (r2, c2) != (r, c):
                        add_edge(u, node_id(r2, c2, n))

    edges: List[Tuple[int, int]] = []
    for u in range(N * N):
        for v in adj[u]:
            if v > u:
                edges.append((u, v))

    return adj, edges


def _check_supported(n: int) -> None:
    if n not in SUPPORTED_BLOCK_SIZES:
        raise ValueError(
            f"Unsupported block size n={n!r}; supported: {SUPPORTED_BLOCK_SIZES}"
        )


@lru_cache(maxsize=None)
def get_graph(n: int) -> Tuple[List[Set[int]], List[Tuple[int, int]]]:
    """Grafo (adj, edges) per blocco n, calcolato una sola volta e cacheato."""
    _check_supported(n)
    return build_graph(n)


def grid_to_precoloring(grid: List[List[int]], n: int) -> Dict[int, int]:
    """Converte la griglia Sudoku (blocco n) in una pre-colorazione parziale."""
    N = grid_size(n)
    colors: Dict[int, int] = {}
    for r in range(N):
        for c in range(N):
            if grid[r][c] != 0:
                colors[node_id(r, c, n)] = grid[r][c]
    return colors


def coloring_to_grid(colors: Dict[int, int], n: int) -> List[List[int]]:
    """Converte la colorazione completa nella griglia Sudoku soluzione."""
    N = grid_size(n)
    grid = [[0] * N for _ in range(N)]
    for uid, color in colors.items():
        r, c = node_rc(uid, n)
        grid[r][c] = color
    return grid


def graph_json(n: int = DEFAULT_BLOCK_SIZE) -> dict:
    """Serializzazione JSON per il frontend (grafo per blocco n)."""
    _check_supported(n)
    N = grid_size(n)
    _, edges = get_graph(n)
    return {
        "n": n,
        "size": N,
        "nodes": [{"id": i, "r": i // N, "c": i % N} for i in range(N * N)],
        "edges": [{"u": u, "v": v} for u, v in edges],
    }
