import os
from itertools import combinations
from typing import Dict, List, Optional, Set, Tuple


class Cell:
    """Base class for a cell on the Kakuro board."""

    def __init__(self, row: int, col: int):
        self.row = row
        self.col = col


class BlockCell(Cell):
    """A solid black cell with no clues."""
    pass


class ClueCell(Cell):
    """A diagonal-split black cell holding a vertical (down) and/or horizontal (right) sum clue."""

    def __init__(self, row: int, col: int, down_clue: Optional[int] = None, right_clue: Optional[int] = None):
        super().__init__(row, col)
        self.down_clue = down_clue
        self.right_clue = right_clue


class WhiteCell(Cell):
    """A playable empty cell representing a CSP variable X_(r, c)."""

    def __init__(self, row: int, col: int):
        super().__init__(row, col)
        self.value: Optional[int] = None
        self.domain: Set[int] = set(range(1, 10))


class ConstraintRun:
    """
    Represents a horizontal or vertical line of contiguous WhiteCells governed by a sum clue.
    Enforces two constraints:
      1. All-Different: All cells in the run must hold distinct digits from {1..9}.
      2. Exact Sum: The sum of digits in the run must equal target_sum.
    """

    def __init__(self, clue_pos: Tuple[int, int], direction: str, target_sum: int, cells: List[Tuple[int, int]]):
        self.clue_pos = clue_pos
        self.direction = direction  # "horizontal" or "vertical"
        self.target_sum = target_sum
        self.cells = cells
        self.length = len(cells)

        # Precompute all valid sets of k distinct digits in {1..9} that add up to target_sum
        self.valid_combinations: List[Set[int]] = [
            set(comb)
            for comb in combinations(range(1, 10), self.length)
            if sum(comb) == self.target_sum
        ]

    def allowed_digits(self) -> Set[int]:
        """Return the union of all digits that can participate in at least one valid sum combination."""
        allowed: Set[int] = set()
        for comb in self.valid_combinations:
            allowed.update(comb)
        return allowed

    def is_satisfied(self, assignment: Dict[Tuple[int, int], int]) -> bool:
        """Check if a complete assignment for this run satisfies All-Different and Sum constraints."""
        vals = [assignment[c] for c in self.cells if c in assignment]
        if len(vals) != self.length:
            return False
        return len(set(vals)) == self.length and sum(vals) == self.target_sum


class KakuroCSP:
    """
    Formulates a Kakuro board as a Constraint Satisfaction Problem (CSP) = (X, D, C).
      - Variables (X): Coordinates (r, c) of all WhiteCells.
      - Domains (D): Subset of {1..9} for each variable.
      - Constraints (C): Horizontal and vertical ConstraintRuns (All-Different + Sum).
    """

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.rows = 0
        self.cols = 0
        self.grid: List[List[Cell]] = []
        self.variables: List[Tuple[int, int]] = []
        self.runs: List[ConstraintRun] = []
        self.cell_to_runs: Dict[Tuple[int, int], List[ConstraintRun]] = {}
        self.neighbors: Dict[Tuple[int, int], Set[Tuple[int, int]]] = {}
        self.initial_domains: Dict[Tuple[int, int], Set[int]] = {}
        self.pruned_domains: Dict[Tuple[int, int], Set[int]] = {}

        self._load_file(filepath)
        self._build_constraints()
        self._build_domains_and_neighbors()

    def _load_file(self, filepath: str) -> None:
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Puzzle file not found: {filepath}")

        with open(filepath, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip() and not line.strip().startswith(";")]

        header = lines[0].split()
        self.rows, self.cols = int(header[0]), int(header[1])

        self.grid = []
        for r in range(self.rows):
            tokens = lines[r + 1].split()
            row_cells: List[Cell] = []
            for c in range(self.cols):
                tok = tokens[c]
                if tok == "#":
                    row_cells.append(BlockCell(r, c))
                elif tok == "_":
                    cell = WhiteCell(r, c)
                    row_cells.append(cell)
                    self.variables.append((r, c))
                elif "\\" in tok:
                    parts = tok.split("\\")
                    down_val = int(parts[0]) if parts[0] != "" else None
                    right_val = int(parts[1]) if parts[1] != "" else None
                    row_cells.append(ClueCell(r, c, down_val, right_val))
                else:
                    raise ValueError(f"Invalid cell token '{tok}' at ({r}, {c})")
            self.grid.append(row_cells)

    def _build_constraints(self) -> None:
        self.cell_to_runs = {var: [] for var in self.variables}

        for r in range(self.rows):
            for c in range(self.cols):
                cell = self.grid[r][c]
                if not isinstance(cell, ClueCell):
                    continue

                # Horizontal run (to the right)
                if cell.right_clue is not None:
                    run_cells: List[Tuple[int, int]] = []
                    cc = c + 1
                    while cc < self.cols and isinstance(self.grid[r][cc], WhiteCell):
                        run_cells.append((r, cc))
                        cc += 1
                    if run_cells:
                        run = ConstraintRun((r, c), "horizontal", cell.right_clue, run_cells)
                        self.runs.append(run)
                        for pos in run_cells:
                            self.cell_to_runs[pos].append(run)

                # Vertical run (downward)
                if cell.down_clue is not None:
                    run_cells = []
                    rr = r + 1
                    while rr < self.rows and isinstance(self.grid[rr][c], WhiteCell):
                        run_cells.append((rr, c))
                        rr += 1
                    if run_cells:
                        run = ConstraintRun((r, c), "vertical", cell.down_clue, run_cells)
                        self.runs.append(run)
                        for pos in run_cells:
                            self.cell_to_runs[pos].append(run)

    def _build_domains_and_neighbors(self) -> None:
        for var in self.variables:
            self.initial_domains[var] = set(range(1, 10))

            # Prune initial domain using intersection of allowed sum combinations
            pruned = set(range(1, 10))
            for run in self.cell_to_runs[var]:
                pruned &= run.allowed_digits()
            self.pruned_domains[var] = pruned

            # Build neighbor set (variables sharing a row run or column run)
            nbrs: Set[Tuple[int, int]] = set()
            for run in self.cell_to_runs[var]:
                for other in run.cells:
                    if other != var:
                        nbrs.add(other)
            self.neighbors[var] = nbrs

    def is_consistent(
        self,
        var: Tuple[int, int],
        val: int,
        assignment: Dict[Tuple[int, int], int],
        domains: Optional[Dict[Tuple[int, int], Set[int]]] = None,
    ) -> bool:
        """
        Check whether assigning var = val is consistent with current partial assignment:
          1. No duplicate value in any shared run.
          2. If a run becomes full, its sum must equal target_sum.
          3. If a run is partially filled, the remaining sum must be achievable using
             distinct unused digits from {1..9} (and within current domains if provided).
        """
        for run in self.cell_to_runs[var]:
            used_vals: Set[int] = {val}
            current_sum = val
            unassigned_cells: List[Tuple[int, int]] = []

            for cell_pos in run.cells:
                if cell_pos == var:
                    continue
                if cell_pos in assignment:
                    v = assignment[cell_pos]
                    if v in used_vals:
                        return False  # Violates All-Different
                    used_vals.add(v)
                    current_sum += v
                else:
                    unassigned_cells.append(cell_pos)

            remaining_count = len(unassigned_cells)
            remaining_sum = run.target_sum - current_sum

            if remaining_count == 0:
                if remaining_sum != 0:
                    return False
            else:
                # Available digits that haven't been used in this run
                available = [d for d in range(1, 10) if d not in used_vals]
                if len(available) < remaining_count:
                    return False

                # Minimum and maximum possible sums with distinct available digits
                min_possible = sum(available[:remaining_count])
                max_possible = sum(available[-remaining_count:])
                if remaining_sum < min_possible or remaining_sum > max_possible:
                    return False

                # Check if at least one valid combination matches the assigned values
                if domains is not None:
                    has_supporting_comb = False
                    for comb in run.valid_combinations:
                        if used_vals.issubset(comb):
                            rem_digits = comb - used_vals
                            # Check if every unassigned cell has at least one candidate in rem_digits
                            if all( bool(domains[u] & rem_digits) for u in unassigned_cells ):
                                has_supporting_comb = True
                                break
                    if not has_supporting_comb:
                        return False

        return True

    def verify_solution(self, assignment: Dict[Tuple[int, int], int]) -> bool:
        """Verify that all variables are assigned and every constraint run is satisfied."""
        if len(assignment) != len(self.variables):
            return False
        for var, val in assignment.items():
            if not (1 <= val <= 9):
                return False
        return all(run.is_satisfied(assignment) for run in self.runs)
