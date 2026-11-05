import os
import sys
from typing import List
from kakuro_csp import KakuroCSP
from solver import KakuroSolver

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def format_board_solution(csp: KakuroCSP, solution: dict) -> str:
    """Format the solved Kakuro grid as an ASCII table."""
    lines = []
    for r in range(csp.rows):
        row_strs = []
        for c in range(csp.cols):
            if (r, c) in solution:
                row_strs.append(f"  {solution[(r, c)]}   ")
            else:
                cell = csp.grid[r][c]
                from kakuro_csp import ClueCell
                if isinstance(cell, ClueCell):
                    d = str(cell.down_clue) if cell.down_clue is not None else ""
                    rt = str(cell.right_clue) if cell.right_clue is not None else ""
                    tok = f"{d}\\{rt}"
                    row_strs.append(f"{tok:^6}")
                else:
                    row_strs.append("  #   ")
        lines.append(" | ".join(row_strs))
    return "\n".join(lines)


def run_experiments(puzzle_files: List[str]) -> None:
    print("=" * 98)
    print("TASK 3: KAKURO CSP SOLVER — EXPERIMENTAL EVALUATION & COMPARISON")
    print("=" * 98)

    header = (
        f"{'Puzzle':<20} | {'Algorithm Configuration':<20} | {'Solved':<6} | "
        f"{'Assigns':<8} | {'Backtracks':<10} | {'Pruned':<8} | {'Time (ms)':<10}"
    )
    print(header)
    print("-" * len(header))

    modes = ["Standard BT", "BT+FC", "BT+FC+Heuristics"]

    for path in puzzle_files:
        if not os.path.exists(path):
            continue
        csp = KakuroCSP(path)
        solver = KakuroSolver(csp)
        bname = os.path.basename(path)

        for mode in modes:
            res = solver.solve(mode=mode, record_steps=False, max_assignments=100000)
            status = "Yes" if res.success else ("No" if res.assignments_count < 100000 else "Limit")
            print(
                f"{bname:<20} | {mode:<20} | {status:<6} | "
                f"{res.assignments_count:<8} | {res.backtracks_count:<10} | "
                f"{res.pruned_values_count:<8} | {res.execution_time_ms:<10.3f}"
            )
        print("-" * len(header))

    print("\n" + "=" * 98)
    print("SOLVED BOARD VERIFICATION (BT+FC+Heuristics)")
    print("=" * 98)
    for path in puzzle_files:
        if not os.path.exists(path):
            continue
        csp = KakuroCSP(path)
        solver = KakuroSolver(csp)
        res = solver.solve(mode="BT+FC+Heuristics", record_steps=False)
        print(f"\n>>> Puzzle: {os.path.basename(path)} ({csp.rows}x{csp.cols}, {len(csp.variables)} variables, {len(csp.runs)} constraint runs)")
        if res.success:
            print(f"    Verified Valid Solution: {csp.verify_solution(res.solution)}")
            print(format_board_solution(csp, res.solution))
        else:
            print("    Status: UNSOLVABLE (No valid solution exists due to conflicting constraints)")


if __name__ == "__main__":
    puzzles_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "puzzles")
    files = sorted(
        os.path.join(puzzles_dir, f)
        for f in os.listdir(puzzles_dir)
        if f.endswith(".txt")
    )
    run_experiments(files)
