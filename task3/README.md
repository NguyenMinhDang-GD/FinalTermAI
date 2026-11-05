# Task 3: Kakuro Solver — Constraint Satisfaction Problems (CSP)

An Object-Oriented Python implementation of a Kakuro puzzle solver using **Backtracking Search**, **Constraint Propagation** (Sum-Combination Filtering, Arc Consistency, Forward Checking), and **Heuristics** (**MRV**, **Degree Heuristic**, **LCV**), with an interactive **Pygame** visualization interface.

## Project Structure

```text
task3/
├── main.py             # Entry point to launch the Pygame GUI
├── kakuro_csp.py       # CSP formulation (Cell classes, ConstraintRun, KakuroCSP)
├── solver.py           # Backtracking Search, Forward Checking, MRV, Degree, LCV
├── gui.py              # Interactive Pygame GUI for visualizing domains & search steps
├── benchmark.py        # Experimental comparison script across solver configurations
├── puzzles/
│   ├── 1_example_5x5.txt   # Example Kakuro board from the assignment (5x5)
│   ├── 2_complex_9x9.txt   # Complex test case from the assignment (9x9)
│   └── 3_medium_8x6.txt    # Additional medium test case (8x6)
├── requirement.txt     # Dependencies
└── README.md           # Project setup and usage instructions
```

## Setup Instructions

1. Create and activate a virtual environment (or use an existing environment):

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install dependencies:

   ```powershell
   python -m pip install -r requirement.txt
   ```

## Running the Application

### 1. Launch the Interactive Pygame GUI

```powershell
python main.py
```

Or specify a puzzle file directly:

```powershell
python main.py puzzles\2_complex_9x9.txt
```

### 2. Run the Experimental Benchmark

```powershell
python benchmark.py
```
