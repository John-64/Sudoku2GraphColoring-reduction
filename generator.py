import random
from typing import List, Optional

from reduction import DEFAULT_BLOCK_SIZE, SUPPORTED_BLOCK_SIZES, grid_size

DIFFICULTY_FRACTIONS = {"easy": 34 / 81, "medium": 46 / 81, "hard": 54 / 81}

# Difficolta' gestite da generate(); "expert" e' un caso a parte (get_expert()),
# disponibile solo per il Sudoku classico (n=3).
DIFFICULTIES = tuple(DIFFICULTY_FRACTIONS.keys())


# Copia profonda di una griglia (lista di liste) per non mutare l'originale
def _copy(grid: List[List[int]]) -> List[List[int]]:
    return [row[:] for row in grid]


# Solleva un errore se n non e' una delle dimensioni di blocco supportate
def _check_supported(n: int) -> None:
    if n not in SUPPORTED_BLOCK_SIZES:
        raise ValueError(
            f"Unsupported block size n={n!r}; supported: {SUPPORTED_BLOCK_SIZES}"
        )


def base_grid(n: int) -> List[List[int]]:
    """
    Griglia soluzione 'canonica' per blocco n x n (lato N = n^2), costruita
    con la formula generale:

        pattern(r, c) = (n * (r % n) + r // n + c) mod n^2

    Per qualunque n questa formula produce un Sudoku valido (righe, colonne
    e blocchi n x n tutti permutazioni di 1..n^2): e' la stessa costruzione
    a meno di rietichettatura per n=2, n=3 (il Sudoku classico) e n=4 -
    il punto e' che la *stessa funzione*, parametrizzata in n, genera
    un'istanza valida per ogni dimensione, rispecchiando la riduzione che
    e' anch'essa definita per famiglia e non solo per il caso 9x9.
    """
    _check_supported(n)
    N = grid_size(n)
    return [
        [((n * (r % n) + r // n + c) % N) + 1 for c in range(N)]
        for r in range(N)
    ]


# Genera un puzzle risolvibile: griglia base -> randomizzazione -> rimozione celle
def generate(n: int = DEFAULT_BLOCK_SIZE, difficulty: str = "medium", seed: Optional[int] = None) -> List[List[int]]:
    _check_supported(n)
    N = grid_size(n)
    rng = random.Random(seed)

    grid = base_grid(n)

    # --- Permuta le cifre 1..N ---
    digit_perm = list(range(1, N + 1))
    rng.shuffle(digit_perm)
    mapping = {old: new for old, new in zip(range(1, N + 1), digit_perm)}
    grid = [[mapping[v] for v in row] for row in grid]

    # --- Shuffle righe dentro ogni banda orizzontale (n bande di n righe) ---
    for band in range(n):
        rows = list(range(band * n, band * n + n))
        shuffled = rows[:]
        rng.shuffle(shuffled)
        band_data = [grid[r][:] for r in shuffled]
        for i, r in enumerate(range(band * n, band * n + n)):
            grid[r] = band_data[i]

    # --- Shuffle colonne dentro ogni banda verticale ---
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

    # --- Shuffle bande orizzontali ---
    bands = list(range(n))
    rng.shuffle(bands)
    new_grid = []
    for b in bands:
        for r in range(b * n, b * n + n):
            new_grid.append(grid[r][:])
    grid = new_grid

    # --- Rimuovi celle con simmetria di punto (180 gradi) ---
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

    # Se il target e' dispari (o la griglia ha un numero pari di celle ma il
    # target richiesto e' dispari), tocca anche la cella centrale: rompe la
    # simmetria di un singolo punto ma resta corretto per qualunque n.
    if removed < n_remove:
        cr, cc = divmod(center, N)
        puzzle[cr][cc] = 0
        removed += 1

    return puzzle


# Puzzle pre-costruito extra-difficile per test, solo per il Sudoku
# classico 9x9 (n=3): non esiste un analogo "famoso" per n=2/4.
EXPERT_PUZZLES = [
    # "AI Escargot" - uno dei Sudoku piu' difficili al mondo
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


# Ritorna una copia del puzzle "esperto" precostruito (solo n=3)
def get_expert() -> List[List[int]]:
    return _copy(EXPERT_PUZZLES[0])
