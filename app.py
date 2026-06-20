from __future__ import annotations

import logging
import os
from typing import Any, Optional

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

from reduction import ADJ, graph_json, grid_to_precoloring, node_rc
from solver import solve_dsatur, solve_naive
from generator import DIFFICULTIES, generate, get_expert

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("sudoku2graphcoloring")

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False

VALID_ALGORITHMS = {"dsatur", "naive", "both"}


def find_precoloring_conflict(grid: list) -> Optional[str]:
    colors = grid_to_precoloring(grid)
    for uid, color in colors.items():
        for nb in ADJ[uid]:
            if nb > uid and colors.get(nb) == color:
                r1, c1 = node_rc(uid)
                r2, c2 = node_rc(nb)
                return (
                    f"Digit {color} is repeated between cells "
                    f"({r1 + 1}, {c1 + 1}) and ({r2 + 1}, {c2 + 1})."
                )
    return None


def validate_grid(grid: Any) -> Optional[str]:
    if not isinstance(grid, list) or len(grid) != 9:
        return "The grid must have exactly 9 rows."
    for row in grid:
        if not isinstance(row, list) or len(row) != 9:
            return "Each row must have exactly 9 cells."
        for value in row:
            if isinstance(value, bool) or not isinstance(value, int) or not (0 <= value <= 9):
                return "Each cell must be an integer between 0 and 9 (0 = empty)."
    return find_precoloring_conflict(grid)


@app.errorhandler(HTTPException)
def handle_http_error(err: HTTPException):
    return jsonify({"error": err.description}), err.code or 500


@app.errorhandler(Exception)
def handle_unexpected_error(err: Exception):
    logger.exception("Unhandled error occurred during the request")
    return jsonify({"error": "Internal server error."}), 500


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/graph")
def graph():
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
        return jsonify({"error": f"Unrecognized algorithm: {algorithm!r}"}), 400

    if algorithm == "dsatur":
        return jsonify({"primary": solve_dsatur(grid)})

    if algorithm == "naive":
        return jsonify({"primary": solve_naive(grid)})

    return jsonify({
        "primary": solve_dsatur(grid),
        "secondary": solve_naive(grid),
    })


@app.route("/generate")
def generate_puzzle():
    difficulty = request.args.get("difficulty", "medium")
    seed_param = request.args.get("seed")

    if difficulty not in DIFFICULTIES and difficulty != "expert":
        return jsonify({"error": f"Unrecognized difficulty: {difficulty!r}"}), 400

    seed: Optional[int] = None
    if seed_param is not None:
        try:
            seed = int(seed_param)
        except ValueError:
            return jsonify({"error": "The seed must be an integer."}), 400

    puzzle = get_expert() if difficulty == "expert" else generate(difficulty=difficulty, seed=seed)
    return jsonify({"grid": puzzle, "difficulty": difficulty, "seed": seed})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5056))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(debug=debug, port=port)