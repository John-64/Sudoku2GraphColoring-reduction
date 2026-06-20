# Sudoku2GraphColoring reduction
Sudoku solved as a graph-coloring instance: a polynomial reduction, two backtracking algorithms side by side, and an interface that shows both representations — grid and graph — as the same object seen from two angles.

<p align="center"> 
    <img src="media/icon.png" alt="Sudoku2GraphColoring" width="15%">
</p>

## The reduction
- Each cell `(r, c)` of the 9×9 grid becomes a node → **81 nodes**.
- Two nodes are connected if their cells share a constraint (same row, same column, or same 3×3 block) → **810 edges**, degree 20 per node.
- Cells already filled in become a fixed pre-coloring.
A 9-coloring of the graph that respects the pre-coloring corresponds exactly to a Sudoku solution. Generalized Sudoku is NP-complete (Yato & Seta, 2003); k-coloring is NP-complete for k ≥ 3 — which is why this problem makes a good case study for the course.

## Two algorithms, same problem
 
- **Naive** — row-by-row backtracking, first valid digit, no heuristics.
- **DSATUR + Forward Checking** (Brélaz, 1979) — at each step, colors the node with maximum saturation (MRV: fewer available colors means a tighter constraint, so it fails earlier), and propagates the constraint to direct neighbors immediately after each assignment.
Same worst-case complexity (the problem is still NP-hard), but DSATUR explores a search tree orders of magnitude smaller in practice — the app makes this visible by comparing nodes explored by both algorithms on the same instance.

## Interface
 
- The Sudoku grid and the graph share the same `(r, c)` coordinates: selecting a cell draws its 20 edges in the graph panel, live.
- Puzzle generation by difficulty (easy / medium / hard) or fixed seed, plus an "expert" preset (AI Escargot).
- Step-by-step animated solving, with a run history that accumulates (useful for comparing DSATUR vs naive across several instances) — only cleared by "Clear".


## Instruction to run the project
1. Install all the requirements in the file by executing:
    ```
    pip install -r requirements.txt
    ```
2. Run the main server by executing:
    ```
    python app.py
    ```
3. Then go to: http://localhost:5050 (or any other port selected in the app.py file)

## Screenshots
<div align="center">
    <div>
        <h5>Creating the Sudoku Grid</h5>
    </div>
    <img src="media/sudokuGenerate.png" alt="Creating the Sudoku Grid" width="80%">
</div>

<div align="center">
    <div>
        <h5>Incorrect input</h5>
    </div>
    <img src="media/incorrectInput.png" alt="Incorrect input" width="80%">
</div>

<div align="center">
    <div>
        <h5>During resolution</h5>
    </div>
    <img src="media/solving.png" alt="During resolution" width="80%">
</div>

<div align="center">
    <div>
        <h5>Reduction completed</h5>
    </div>
    <img src="media/solved.png" alt="Reduction completed" width="80%">
</div>

## Contribution
If you'd like to contribute, please follow these steps:
- Fork the repository;
- Create a new branch (```git checkout -b feature/YourFeatureName```);
- Commit your changes (```git commit -m 'Add some feature'```);
- Push to the branch (```git push origin feature/YourFeatureName```);
- Open a pull request.

## License
This project is licensed under the MIT License. See the LICENSE file for details.
