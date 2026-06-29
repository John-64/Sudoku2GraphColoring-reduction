import random
from typing import List, Optional
from reduction import DEFAULT_BLOCK_SIZE, SUPPORTED_BLOCK_SIZES, grid_size

DIFFICULTY_FRACTIONS = {"easy": 34 / 81, "medium": 46 / 81, "hard": 54 / 81}
DIFFICULTIES = tuple(DIFFICULTY_FRACTIONS.keys())

# Solleva un errore se n non è una delle dimensioni di blocco supportate
def _check_supported(n: int) -> None:
    if n not in SUPPORTED_BLOCK_SIZES:
        raise ValueError(
            f"Unsupported block size n={n!r}; supported: {SUPPORTED_BLOCK_SIZES}"
        )

# Copia di una griglia
def _copy(grid: List[List[int]]) -> List[List[int]]:
    return [row[:] for row in grid]

# Costruzione di una griglia completa
def base_grid(n: int) -> List[List[int]]:
    _check_supported(n)
    N = grid_size(n)
    return [
        # Per ogni riga calcolo un punto di partenza e per ogni colonna faccio avanzare quel punto ciclicamente (modulo N)
        [((n * (r % n) + r // n + c) % N) + 1 for c in range(N)]
        for r in range(N)
    ]

# Genera un puzzle risolvibile: griglia base -> permutazione -> rimozione celle in base alla difficoltà
def generate(n: int = DEFAULT_BLOCK_SIZE, difficulty: str = "medium", seed: Optional[int] = None) -> List[List[int]]:
    _check_supported(n)
    N = grid_size(n)
    rng = random.Random(seed)

    grid = base_grid(n)

    # Permutazione 
    digit_perm = list(range(1, N + 1))
    rng.shuffle(digit_perm)
    mapping = {old: new for old, new in zip(range(1, N + 1), digit_perm)}
    grid = [[mapping[v] for v in row] for row in grid]

    # Shuffle righe dentro ogni banda orizzontale (n bande di n righe)
    for band in range(n):
        rows = list(range(band * n, band * n + n))
        shuffled = rows[:]
        rng.shuffle(shuffled)
        band_data = [grid[r][:] for r in shuffled]
        for i, r in enumerate(range(band * n, band * n + n)):
            grid[r] = band_data[i]

    # Shuffle colonne dentro ogni banda verticale
    for band in range(n):
        cols = list(range(band * n, band * n + n))
        shuffled = cols[:]
        rng.shuffle(shuffled)
        col_map = {orig: shuf for orig, shuf in zip(cols, shuffled)}
        new_grid = _copy(grid)
        for r in range(N):
            for c in cols:
                new_grid[r][c] = grid[r][col_map[c]]
        grid = new_grid

    # Shuffle bande orizzontali
    bands = list(range(n))
    rng.shuffle(bands)
    new_grid = []
    for b in bands:
        for r in range(b * n, b * n + n):
            new_grid.append(grid[r][:])
    grid = new_grid

    # Rimuove celle con simmetria di punto (180 gradi: prima con ultima, seconda con penultima...)
    puzzle = _copy(grid)
    fraction = DIFFICULTY_FRACTIONS.get(difficulty, DIFFICULTY_FRACTIONS["medium"])
    total_cells = N * N
    n_remove = round(total_cells * fraction)
    center = total_cells // 2

    half_indices = list(range(center))
    rng.shuffle(half_indices)

    removed = 0
    for idx in half_indices:
        if removed >= n_remove:
            break
        r1, c1 = divmod(idx, N)
        r2, c2 = divmod(total_cells - 1 - idx, N)
        puzzle[r1][c1] = 0
        puzzle[r2][c2] = 0
        removed += 2

    # Se il target è dispari, la simmetria viene rotta dalla cella centrale, quindi viene rimossa
    if removed < n_remove:
        cr, cc = divmod(center, N)
        puzzle[cr][cc] = 0
        removed += 1

    return puzzle

# AI Escargot
EXPERT_PUZZLES = [
    [
        [1, 0, 0, 0, 0, 7, 0, 9, 0],
        [0, 3, 0, 0, 2, 0, 0, 0, 8],
        [0, 0, 9, 6, 0, 0, 5, 0, 0],
        [0, 0, 5, 3, 0, 0, 9, 0, 0],
        [0, 1, 0, 0, 8, 0, 0, 0, 2],
        [6, 0, 0, 0, 0, 4, 0, 0, 0],
        [3, 0, 0, 0, 0, 0, 0, 1, 0],
        [0, 4, 0, 0, 0, 0, 0, 0, 7],
        [0, 0, 7, 0, 0, 0, 3, 0, 0],
    ]
]

EXPERT_BLOCK_SIZE = 3

# Restituisce una copia del puzzle AI Escargot
def get_expert() -> List[List[int]]:
    return _copy(EXPERT_PUZZLES[0])