from __future__ import annotations

import logging
import os
from typing import Any, Optional

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

from reduction import (
    DEFAULT_BLOCK_SIZE,
    SUPPORTED_BLOCK_SIZES,
    get_graph,
    graph_json,
    grid_size,
    grid_to_precoloring,
    node_rc,
)
from solver import solve_dsatur, solve_naive
from generator import DIFFICULTIES, EXPERT_BLOCK_SIZE, generate, get_expert

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("sudoku2precoloringextension")

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False

VALID_ALGORITHMS = {"dsatur", "naive", "both"}


def parse_block_size(raw: Any) -> "tuple[Optional[int], Optional[str]]":
    """Valida il parametro n (dimensione blocco). Ritorna (n, errore)."""
    if raw is None:
        return DEFAULT_BLOCK_SIZE, None
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return None, "The block size n must be an integer."
    if n not in SUPPORTED_BLOCK_SIZES:
        allowed = ", ".join(str(x) for x in SUPPORTED_BLOCK_SIZES)
        return None, f"Unsupported block size n={raw!r}. Supported values: {allowed}."
    return n, None


# Cerca un conflitto fra celle precolorate usando le adiacenze del grafo
def find_precoloring_conflict(grid: list, n: int) -> Optional[str]:
    adj, _ = get_graph(n)
    colors = grid_to_precoloring(grid, n)
    for uid, color in colors.items():
        for nb in adj[uid]:
            if nb > uid and colors.get(nb) == color:
                r1, c1 = node_rc(uid, n)
                r2, c2 = node_rc(nb, n)
                return (
                    f"Digit {color} is repeated between cells "
                    f"({r1 + 1}, {c1 + 1}) and ({r2 + 1}, {c2 + 1})."
                )
    return None


# Valida forma e contenuto della griglia, poi delega il controllo conflitti
def validate_grid(grid: Any, n: int) -> Optional[str]:
    N = grid_size(n)
    if not isinstance(grid, list) or len(grid) != N:
        return f"The grid must have exactly {N} rows."
    for row in grid:
        if not isinstance(row, list) or len(row) != N:
            return f"Each row must have exactly {N} cells."
        for value in row:
            if isinstance(value, bool) or not isinstance(value, int) or not (0 <= value <= N):
                return f"Each cell must be an integer between 0 and {N} (0 = empty)."
    return find_precoloring_conflict(grid, n)


# Risposta JSON uniforme per le eccezioni HTTP gestite da Flask/Werkzeug
@app.errorhandler(HTTPException)
def handle_http_error(err: HTTPException):
    return jsonify({"error": err.description}), err.code or 500


# Risposta JSON uniforme per qualunque errore non previsto (con log)
@app.errorhandler(Exception)
def handle_unexpected_error(err: Exception):
    logger.exception("Unhandled error occurred during the request")
    return jsonify({"error": "Internal server error."}), 500


# Pagina principale: passa al template le dimensioni di blocco supportate
@app.route("/")
def index():
    return render_template(
        "index.html",
        supported_sizes=sorted(SUPPORTED_BLOCK_SIZES),
        default_size=DEFAULT_BLOCK_SIZE,
    )


# Ritorna l'istanza del grafo (nodi+archi) per il blocco n richiesto
@app.route("/graph")
def graph():
    n, error = parse_block_size(request.args.get("n"))
    if error:
        return jsonify({"error": error}), 400
    return jsonify(graph_json(n))


# Valida la griglia ricevuta e dispatcha alla risoluzione richiesta (dsatur/naive/both)
@app.route("/solve", methods=["POST"])
def solve():
    data = request.get_json(silent=True) or {}
    grid = data.get("grid")
    algorithm = data.get("algorithm", "dsatur")

    n, error = parse_block_size(data.get("n"))
    if error:
        return jsonify({"error": error}), 400

    error = validate_grid(grid, n)
    if error:
        return jsonify({"error": error}), 400

    if algorithm not in VALID_ALGORITHMS:
        return jsonify({"error": f"Unrecognized algorithm: {algorithm!r}"}), 400

    if algorithm == "dsatur":
        return jsonify({"primary": solve_dsatur(grid, n)})

    if algorithm == "naive":
        return jsonify({"primary": solve_naive(grid, n)})

    return jsonify({
        "primary": solve_dsatur(grid, n),
        "secondary": solve_naive(grid, n),
    })


# Genera (o recupera, per "expert") un puzzle per il blocco/difficolta'/seed richiesti
@app.route("/generate")
def generate_puzzle():
    n, error = parse_block_size(request.args.get("n"))
    if error:
        return jsonify({"error": error}), 400

    difficulty = request.args.get("difficulty", "medium")
    seed_param = request.args.get("seed")

    if difficulty not in DIFFICULTIES and difficulty != "expert":
        return jsonify({"error": f"Unrecognized difficulty: {difficulty!r}"}), 400

    if difficulty == "expert" and n != EXPERT_BLOCK_SIZE:
        return jsonify({
            "error": f"The 'expert' preset is only available for the classic {EXPERT_BLOCK_SIZE * EXPERT_BLOCK_SIZE}x{EXPERT_BLOCK_SIZE * EXPERT_BLOCK_SIZE} Sudoku (n={EXPERT_BLOCK_SIZE})."
        }), 400

    seed: Optional[int] = None
    if seed_param is not None:
        try:
            seed = int(seed_param)
        except ValueError:
            return jsonify({"error": "The seed must be an integer."}), 400

    puzzle = get_expert() if difficulty == "expert" else generate(n=n, difficulty=difficulty, seed=seed)
    return jsonify({"grid": puzzle, "difficulty": difficulty, "seed": seed, "n": n})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5056))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(debug=debug, port=port)
