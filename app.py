from __future__ import annotations

import logging
import os
from typing import Any, Optional

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

from reduction import graph_json
from solver import solve_dsatur, solve_naive
from generator import DIFFICULTIES, generate, get_expert

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("sudoku2graphcoloring")

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False

VALID_ALGORITHMS = {"dsatur", "naive", "both"}


def validate_grid(grid: Any) -> Optional[str]:
    """Verifica struttura e contenuto della griglia inviata dal client.

    Ritorna un messaggio d'errore (str) se la griglia non è valida,
    altrimenti None. Le celle vuote sono rappresentate da 0.
    """
    if not isinstance(grid, list) or len(grid) != 9:
        return "La griglia deve avere esattamente 9 righe."
    for row in grid:
        if not isinstance(row, list) or len(row) != 9:
            return "Ogni riga deve avere esattamente 9 celle."
        for value in row:
            # bool è sottoclasse di int in Python: lo escludiamo esplicitamente.
            if isinstance(value, bool) or not isinstance(value, int) or not (0 <= value <= 9):
                return "Ogni cella deve essere un intero tra 0 e 9 (0 = vuota)."
    return None


@app.errorhandler(HTTPException)
def handle_http_error(err: HTTPException):
    return jsonify({"error": err.description}), err.code or 500


@app.errorhandler(Exception)
def handle_unexpected_error(err: Exception):
    logger.exception("Errore non gestito durante la richiesta")
    return jsonify({"error": "Errore interno del server."}), 500


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/graph")
def graph():
    """Restituisce nodi e archi del grafo GraphColoring per il frontend."""
    return jsonify(graph_json())


@app.route("/solve", methods=["POST"])
def solve():
    data = request.get_json(silent=True) or {}
    grid = data.get("grid")
    algorithm = data.get("algorithm", "dsatur")

    error = validate_grid(grid)
    if error:
        return jsonify({"error": error}), 400

    if algorithm not in VALID_ALGORITHMS:
        return jsonify({"error": f"Algoritmo non riconosciuto: {algorithm!r}"}), 400

    if algorithm == "dsatur":
        return jsonify({"primary": solve_dsatur(grid)})

    if algorithm == "naive":
        return jsonify({"primary": solve_naive(grid)})

    # algorithm == "both": esegue entrambi per il confronto diretto
    return jsonify({
        "primary": solve_dsatur(grid),
        "secondary": solve_naive(grid),
    })


@app.route("/generate")
def generate_puzzle():
    difficulty = request.args.get("difficulty", "medium")
    seed_param = request.args.get("seed")

    if difficulty not in DIFFICULTIES and difficulty != "expert":
        return jsonify({"error": f"Difficoltà non riconosciuta: {difficulty!r}"}), 400

    seed: Optional[int] = None
    if seed_param is not None:
        try:
            seed = int(seed_param)
        except ValueError:
            return jsonify({"error": "Il seed deve essere un intero."}), 400

    puzzle = get_expert() if difficulty == "expert" else generate(difficulty=difficulty, seed=seed)
    return jsonify({"grid": puzzle, "difficulty": difficulty, "seed": seed})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5059))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(debug=debug, port=port)