import time
from typing import Dict, List, Optional, Set, Tuple
from kakuro_csp import KakuroCSP


class SearchStep:
    """Snapshot of a single step in the CSP solving process for UI visualization."""

    def __init__(
        self,
        step_type: str,
        assignment: Dict[Tuple[int, int], int],
        domains: Dict[Tuple[int, int], Set[int]],
        focus_var: Optional[Tuple[int, int]] = None,
        focus_val: Optional[int] = None,
        affected_vars: Optional[List[Tuple[int, int]]] = None,
        description: str = "",
    ):
        self.step_type = step_type  # "INITIAL", "PRUNE", "ASSIGN", "PROPAGATE", "BACKTRACK", "SOLVED"
        self.assignment = dict(assignment)
        self.domains = {k: set(v) for k, v in domains.items()}
        self.focus_var = focus_var
        self.focus_val = focus_val
        self.affected_vars = list(affected_vars) if affected_vars else []
        self.description = description


class SolverResult:
    """Stores the final outcome and performance metrics of a CSP solver run."""

    def __init__(
        self,
        algorithm_name: str,
        success: bool,
        solution: Dict[Tuple[int, int], int],
        assignments_count: int,
        backtracks_count: int,
        pruned_values_count: int,
        execution_time_ms: float,
        steps: List[SearchStep],
    ):
        self.algorithm_name = algorithm_name
        self.success = success
        self.solution = solution
        self.assignments_count = assignments_count
        self.backtracks_count = backtracks_count
        self.pruned_values_count = pruned_values_count
        self.execution_time_ms = execution_time_ms
        self.steps = steps


class KakuroSolver:
    """
    CSP Solver for Kakuro combining Backtracking Search, Constraint Propagation
    (Sum-Combination Pruning + Forward Checking / Arc Consistency), and
    Lecture 08 Heuristics (MRV, Degree Heuristic, LCV).
    """

    def __init__(self, csp: KakuroCSP):
        self.csp = csp

    def select_unassigned_variable(
        self,
        assignment: Dict[Tuple[int, int], int],
        domains: Dict[Tuple[int, int], Set[int]],
        use_heuristics: bool = True,
    ) -> Tuple[int, int]:
        """
        Select the next unassigned variable.
          - If use_heuristics is True:
              1. MRV (Minimum Remaining Values): fewest legal values left in domain.
              2. Degree Heuristic (tie-breaker): most unassigned neighbors.
              3. Coordinate order (final tie-breaker).
          - Otherwise: static row-major order.
        """
        unassigned = [v for v in self.csp.variables if v not in assignment]
        if not use_heuristics:
            return unassigned[0]

        def mrv_degree_key(var: Tuple[int, int]) -> Tuple[int, int, Tuple[int, int]]:
            domain_size = len(domains[var])
            degree = sum(1 for nbr in self.csp.neighbors[var] if nbr not in assignment)
            return (domain_size, -degree, var)

        return min(unassigned, key=mrv_degree_key)

    def order_domain_values(
        self,
        var: Tuple[int, int],
        assignment: Dict[Tuple[int, int], int],
        domains: Dict[Tuple[int, int], Set[int]],
        use_heuristics: bool = True,
    ) -> List[int]:
        """
        Order values in the domain of var.
          - If use_heuristics is True: LCV (Least Constraining Value) — sort values by
            how few options they eliminate from unassigned neighboring variables.
          - Otherwise: ascending numerical order.
        """
        values = sorted(domains[var])
        if not use_heuristics or len(values) <= 1:
            return values

        def lcv_cost(val: int) -> int:
            eliminated = 0
            for run in self.csp.cell_to_runs[var]:
                # Allowed digits in this run if var is set to val
                used = {val} | {assignment[c] for c in run.cells if c in assignment and c != var}
                allowed_in_run: Set[int] = set()
                for comb in run.valid_combinations:
                    if used.issubset(comb):
                        allowed_in_run.update(comb - used)

                for nbr in run.cells:
                    if nbr != var and nbr not in assignment:
                        for d in domains[nbr]:
                            if d == val or d not in allowed_in_run:
                                eliminated += 1
            return eliminated

        return sorted(values, key=lambda v: (lcv_cost(v), v))

    def forward_check(
        self,
        var: Tuple[int, int],
        val: int,
        assignment: Dict[Tuple[int, int], int],
        domains: Dict[Tuple[int, int], Set[int]],
        full_propagation: bool = True,
    ) -> Tuple[bool, List[Tuple[Tuple[int, int], int]], List[Tuple[int, int]]]:
        """
        Perform Constraint Propagation after assigning var = val.
          - Basic Forward Checking (full_propagation=False): Prunes direct neighbors in the
            same row/col runs using All-Different and min/max sum bounds.
          - Full Propagation (full_propagation=True): Filters using exact Kakuro sum combinations
            and cascades across intersecting runs when a singleton/reduced domain is found.
        """
        pruned_log: List[Tuple[Tuple[int, int], int]] = []
        affected_set: Set[Tuple[int, int]] = set()

        if not full_propagation:
            # Standard 1-step Forward Checking on direct neighbors of var
            for run in self.csp.cell_to_runs[var]:
                used_vals = {assignment[c] for c in run.cells if c in assignment}
                current_sum = sum(assignment[c] for c in run.cells if c in assignment)
                unassigned = [c for c in run.cells if c not in assignment]
                rem_count = len(unassigned)
                rem_sum = run.target_sum - current_sum

                if rem_count == 0:
                    if rem_sum != 0:
                        return False, pruned_log, list(affected_set)
                    continue

                avail = [d for d in range(1, 10) if d not in used_vals]
                if len(avail) < rem_count:
                    return False, pruned_log, list(affected_set)

                min_others = sum(avail[: rem_count - 1]) if rem_count > 1 else 0
                max_others = sum(avail[-(rem_count - 1) :]) if rem_count > 1 else 0

                for u in unassigned:
                    to_remove = []
                    for d in domains[u]:
                        if d in used_vals:
                            to_remove.append(d)
                        elif rem_count == 1 and d != rem_sum:
                            to_remove.append(d)
                        elif d + min_others > rem_sum or d + max_others < rem_sum:
                            to_remove.append(d)

                    if to_remove:
                        for d in to_remove:
                            domains[u].remove(d)
                            pruned_log.append((u, d))
                        affected_set.add(u)
                        if not domains[u]:
                            return False, pruned_log, list(affected_set)

            return True, pruned_log, sorted(affected_set)

        # Full Combination-based Forward Checking + Propagation
        run_queue = list(self.csp.cell_to_runs[var])
        in_queue = set(run_queue)

        while run_queue:
            run = run_queue.pop(0)
            in_queue.discard(run)

            assigned_vals: Set[int] = set()
            unassigned_cells: List[Tuple[int, int]] = []
            for c in run.cells:
                if c in assignment:
                    assigned_vals.add(assignment[c])
                else:
                    unassigned_cells.append(c)

            if not unassigned_cells:
                actual_sum = sum(assignment[c] for c in run.cells)
                if actual_sum != run.target_sum or len(assigned_vals) != run.length:
                    return False, pruned_log, list(affected_set)
                continue

            # Identify any unassigned cells that are already restricted to a single value
            singleton_vals: Set[int] = set()
            singleton_conflict = False
            for u in unassigned_cells:
                if len(domains[u]) == 1:
                    s_val = next(iter(domains[u]))
                    if s_val in assigned_vals or s_val in singleton_vals:
                        singleton_conflict = True
                        break
                    singleton_vals.add(s_val)

            if singleton_conflict:
                return False, pruned_log, list(affected_set)

            required_vals = assigned_vals | singleton_vals
            non_singleton_cells = [u for u in unassigned_cells if len(domains[u]) > 1]

            supported_digits: Set[int] = set()
            for comb in run.valid_combinations:
                if not required_vals.issubset(comb):
                    continue
                rem = comb - required_vals
                if all(bool(domains[u] & rem) for u in non_singleton_cells):
                    supported_digits.update(rem)

            if non_singleton_cells and not supported_digits:
                return False, pruned_log, list(affected_set)

            for u in non_singleton_cells:
                to_remove = [d for d in domains[u] if d in required_vals or d not in supported_digits]
                if to_remove:
                    for d in to_remove:
                        domains[u].remove(d)
                        pruned_log.append((u, d))
                    affected_set.add(u)

                    if not domains[u]:
                        return False, pruned_log, list(affected_set)

                    for other_run in self.csp.cell_to_runs[u]:
                        if other_run != run and other_run not in in_queue:
                            run_queue.append(other_run)
                            in_queue.add(other_run)

        return True, pruned_log, sorted(affected_set)

    def initial_arc_consistency(
        self, domains: Dict[Tuple[int, int], Set[int]]
    ) -> Tuple[int, List[Tuple[int, int]]]:
        """
        Enforce initial Arc Consistency across intersecting runs before search begins.
        Filters out candidate values that have no supporting valid combination in their runs.
        """
        total_pruned = 0
        affected: Set[Tuple[int, int]] = set()

        for _ in range(2):
            changed = False
            for run in self.csp.runs:
                supported_digits: Set[int] = set()
                singletons = {next(iter(domains[c])) for c in run.cells if len(domains[c]) == 1}
                num_singletons = sum(1 for c in run.cells if len(domains[c]) == 1)
                if len(singletons) < num_singletons:
                    continue

                for comb in run.valid_combinations:
                    if singletons.issubset(comb) and all(bool(domains[c] & comb) for c in run.cells):
                        supported_digits.update(comb)

                for c in run.cells:
                    if len(domains[c]) > 1:
                        allowed = (domains[c] & supported_digits) - singletons
                    else:
                        allowed = domains[c] & supported_digits
                    removed = domains[c] - allowed
                    if removed:
                        domains[c] = allowed
                        total_pruned += len(removed)
                        affected.add(c)
                        changed = True
            if not changed:
                break

        return total_pruned, sorted(affected)

    def solve(
        self,
        mode: str = "BT+FC+Heuristics",
        record_steps: bool = True,
        max_assignments: int = 200000,
    ) -> SolverResult:
        """
        Solve the Kakuro CSP using the specified algorithm configuration:
          - "Standard BT": Backtracking with static ordering and basic consistency check.
          - "BT+FC": Backtracking + Forward Checking / Combination Pruning (static ordering).
          - "BT+FC+Heuristics": Backtracking + Forward Checking + MRV + Degree + LCV.
        """
        use_fc = mode in ("BT+FC", "BT+FC+Heuristics")
        use_heuristics = mode == "BT+FC+Heuristics"

        start_time = time.perf_counter()
        assignment: Dict[Tuple[int, int], int] = {}
        steps: List[SearchStep] = []

        assignments_count = 0
        backtracks_count = 0
        pruned_values_count = 0

        # Step 1: Initialize domains
        if use_heuristics:
            domains = {v: set(self.csp.pruned_domains[v]) for v in self.csp.variables}
            initial_comb_pruned = sum(9 - len(domains[v]) for v in self.csp.variables)
            pruned_values_count += initial_comb_pruned

            if record_steps:
                steps.append(
                    SearchStep(
                        step_type="INITIAL",
                        assignment=assignment,
                        domains=domains,
                        affected_vars=list(self.csp.variables),
                        description=f"Initialized CSP. Sum-combination filter pruned {initial_comb_pruned} invalid candidates.",
                    )
                )

            ac_pruned, ac_affected = self.initial_arc_consistency(domains)
            pruned_values_count += ac_pruned
            if record_steps and ac_pruned > 0:
                steps.append(
                    SearchStep(
                        step_type="PRUNE",
                        assignment=assignment,
                        domains=domains,
                        affected_vars=ac_affected,
                        description=f"Arc Consistency pruned {ac_pruned} unsupported candidates across intersecting runs.",
                    )
                )
        else:
            domains = {v: set(self.csp.initial_domains[v]) for v in self.csp.variables}
            if record_steps:
                steps.append(
                    SearchStep(
                        step_type="INITIAL",
                        assignment=assignment,
                        domains=domains,
                        description=f"Initialized {mode} with full domains {{1..9}}.",
                    )
                )

        def backtrack() -> bool:
            nonlocal assignments_count, backtracks_count, pruned_values_count

            if len(assignment) == len(self.csp.variables):
                if record_steps:
                    steps.append(
                        SearchStep(
                            step_type="SOLVED",
                            assignment=assignment,
                            domains=domains,
                            description="All variables assigned and all constraints satisfied!",
                        )
                    )
                return True

            if assignments_count >= max_assignments:
                return False

            var = self.select_unassigned_variable(assignment, domains, use_heuristics=use_heuristics)
            ordered_vals = self.order_domain_values(var, assignment, domains, use_heuristics=use_heuristics)

            for val in ordered_vals:
                if not self.csp.is_consistent(var, val, assignment, domains if use_fc else None):
                    continue

                # Assign var = val
                assignment[var] = val
                saved_var_domain = set(domains[var])
                domains[var] = {val}
                assignments_count += 1

                if record_steps and len(steps) < 5000:
                    steps.append(
                        SearchStep(
                            step_type="ASSIGN",
                            assignment=assignment,
                            domains=domains,
                            focus_var=var,
                            focus_val=val,
                            description=f"Assign X{var} = {val} (Domain size: {len(saved_var_domain)})",
                        )
                    )

                if use_fc:
                    ok, pruned_log, affected = self.forward_check(
                        var, val, assignment, domains, full_propagation=use_heuristics
                    )
                    pruned_values_count += len(pruned_log)

                    if record_steps and affected and len(steps) < 5000:
                        steps.append(
                            SearchStep(
                                step_type="PROPAGATE",
                                assignment=assignment,
                                domains=domains,
                                focus_var=var,
                                focus_val=val,
                                affected_vars=affected,
                                description=f"Constraint propagation from X{var}={val} pruned {len(pruned_log)} values from {len(affected)} neighbors.",
                            )
                        )

                    if ok and backtrack():
                        return True

                    # Restore pruned domains on backtrack
                    for cell_pos, removed_val in pruned_log:
                        domains[cell_pos].add(removed_val)
                else:
                    if backtrack():
                        return True

                # Undo assignment (Backtrack)
                del assignment[var]
                domains[var] = saved_var_domain
                backtracks_count += 1

                if record_steps and len(steps) < 5000:
                    steps.append(
                        SearchStep(
                            step_type="BACKTRACK",
                            assignment=assignment,
                            domains=domains,
                            focus_var=var,
                            focus_val=val,
                            description=f"Dead-end after X{var} = {val}. Backtracking and restoring domains.",
                        )
                    )

            return False

        solved = backtrack()
        if not solved and record_steps:
            steps.append(
                SearchStep(
                    step_type="UNSOLVABLE",
                    assignment=assignment,
                    domains=domains,
                    description="No valid solution exists! All candidate branches exhausted due to constraint conflicts.",
                )
            )
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return SolverResult(
            algorithm_name=mode,
            success=solved and self.csp.verify_solution(assignment),
            solution=dict(assignment) if solved else {},
            assignments_count=assignments_count,
            backtracks_count=backtracks_count,
            pruned_values_count=pruned_values_count,
            execution_time_ms=elapsed_ms,
            steps=steps,
        )
