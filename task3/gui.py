import os
import sys
from typing import Dict, List, Optional, Tuple
import pygame
from kakuro_csp import BlockCell, ClueCell, KakuroCSP, WhiteCell
from solver import KakuroSolver, SearchStep, SolverResult

pygame.init()
pygame.font.init()

# Light / White Theme Color Palette
BG_COLOR = (250, 251, 253)          # Main window background (off-white)
PANEL_COLOR = (242, 244, 248)       # Right control panel background
CARD_COLOR = (255, 255, 255)        # Info cards background (pure white)
BORDER_COLOR = (205, 212, 222)      # Subtle borders for panel & cards
GRID_LINE_COLOR = (35, 40, 48)      # Crisp dark border for Kakuro grid
TEXT_COLOR = (28, 33, 43)           # Primary dark text
MUTED_TEXT = (95, 105, 120)         # Secondary muted label text

BTN_BG = (232, 236, 242)
BTN_HOVER = (218, 225, 236)
BTN_ACTIVE = (37, 99, 235)          # Royal blue for active state
BTN_DISABLED_BG = (238, 240, 244)

# Board Cell Colors (Matching Assignment PDF Kakuro style)
BLOCK_CELL_BG = (206, 210, 216)     # Classic light grey blocked cell
CLUE_CELL_BG = (206, 210, 216)      # Classic light grey clue cell
CLUE_LINE_COLOR = (45, 50, 60)      # Diagonal slash line
DOWN_CLUE_COLOR = (20, 25, 35)      # Dark bold vertical clue
RIGHT_CLUE_COLOR = (20, 25, 35)     # Dark bold horizontal clue

WHITE_CELL_BG = (255, 255, 255)     # Playable white cell
ASSIGNED_CELL_BG = (238, 245, 255)  # Soft ice-blue for assigned cells
SOLVED_CELL_BG = (220, 248, 230)    # Soft mint green when solved

# Step Highlight Colors
FOCUS_ASSIGN_BG = (255, 243, 196)
FOCUS_ASSIGN_BORDER = (230, 155, 10)

PROPAGATE_BG = (218, 242, 255)
PROPAGATE_BORDER = (20, 145, 215)

BACKTRACK_BG = (255, 220, 220)
BACKTRACK_BORDER = (220, 50, 50)

SELECTED_BORDER = (115, 75, 230)

DIGIT_COLOR = (20, 28, 42)
DOMAIN_DIGIT_COLOR = (45, 95, 175)
DOMAIN_PRUNED_COLOR = (205, 212, 220)


def get_puzzle_files(puzzles_dir: str = "puzzles") -> List[str]:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    full_dir = os.path.join(base_dir, puzzles_dir)
    if not os.path.exists(full_dir):
        os.makedirs(full_dir, exist_ok=True)
    files = [
        os.path.join(full_dir, f)
        for f in os.listdir(full_dir)
        if f.endswith(".txt")
    ]
    return sorted(files)


class KakuroGUI:
    """
    Graphical User Interface for Kakuro CSP Solver.
    Visualizes:
      1. Variable domains (3x3 candidate matrix inside each unassigned cell).
      2. Constraint propagation (real-time domain reduction & neighbor highlighting).
      3. Backtracking search process (step-by-step assignments, conflicts, and backtracks).
    """

    def __init__(self, initial_puzzle: Optional[str] = None):
        self.w, self.h = 1280, 760
        self.board_area_w = 760
        self.screen = pygame.display.set_mode((self.w, self.h))
        pygame.display.set_caption("Kakuro CSP Solver & Visualizer — Task 3")
        self.clock = pygame.time.Clock()

        # Fonts
        self.font_xs = pygame.font.SysFont("Segoe UI, Arial", 12)
        self.font_sm = pygame.font.SysFont("Segoe UI, Arial", 14)
        self.font_sm_bold = pygame.font.SysFont("Segoe UI, Arial", 14, bold=True)
        self.font_md = pygame.font.SysFont("Segoe UI, Arial", 16, bold=True)
        self.font_title = pygame.font.SysFont("Segoe UI, Arial", 20, bold=True)

        # Puzzle & Solver state
        self.puzzle_files = get_puzzle_files()
        self.puzzle_idx = 0
        if initial_puzzle and os.path.exists(initial_puzzle):
            abs_init = os.path.abspath(initial_puzzle)
            for i, p in enumerate(self.puzzle_files):
                if os.path.abspath(p) == abs_init:
                    self.puzzle_idx = i
                    break

        self.modes = ["BT+FC+Heuristics", "BT+FC", "Standard BT"]
        self.mode_idx = 0

        self.speeds = [("1x", 450), ("5x", 110), ("20x", 25), ("Max", 2)]
        self.speed_idx = 1

        self.show_domains = True
        self.paused = True
        self.last_step_tick = 0
        self.selected_cell: Optional[Tuple[int, int]] = None

        self.csp: Optional[KakuroCSP] = None
        self.solver_result: Optional[SolverResult] = None
        self.steps: List[SearchStep] = []
        self.step_idx = 0

        self.cell_size = 64
        self.grid_offset_x = 40
        self.grid_offset_y = 40

        self.load_puzzle(self.puzzle_files[self.puzzle_idx])

    def load_puzzle(self, filepath: str) -> None:
        self.csp = KakuroCSP(filepath)
        max_cell_w = (self.board_area_w - 80) // max(1, self.csp.cols)
        max_cell_h = (self.h - 100) // max(1, self.csp.rows)
        self.cell_size = min(96, max(48, min(max_cell_w, max_cell_h)))

        grid_w = self.csp.cols * self.cell_size
        grid_h = self.csp.rows * self.cell_size
        self.grid_offset_x = (self.board_area_w - grid_w) // 2
        self.grid_offset_y = (self.h - grid_h) // 2

        self.selected_cell = self.csp.variables[0] if self.csp.variables else None
        self.run_solver()

    def run_solver(self) -> None:
        if not self.csp:
            return
        solver = KakuroSolver(self.csp)
        mode = self.modes[self.mode_idx]
        self.solver_result = solver.solve(mode=mode, record_steps=True)
        self.steps = self.solver_result.steps
        self.step_idx = 0
        self.paused = True
        self.last_step_tick = pygame.time.get_ticks()

    def current_step(self) -> Optional[SearchStep]:
        if not self.steps:
            return None
        return self.steps[min(self.step_idx, len(self.steps) - 1)]

    def draw_button(
        self,
        rect: pygame.Rect,
        label: str,
        active: bool = False,
        enabled: bool = True,
        font: Optional[pygame.font.Font] = None,
    ) -> None:
        mouse_pos = pygame.mouse.get_pos()
        hovered = enabled and rect.collidepoint(mouse_pos)
        if active:
            bg = BTN_ACTIVE
            fg = (255, 255, 255)
        elif hovered:
            bg = BTN_HOVER
            fg = TEXT_COLOR
        elif enabled:
            bg = BTN_BG
            fg = TEXT_COLOR
        else:
            bg = BTN_DISABLED_BG
            fg = (165, 172, 184)

        pygame.draw.rect(self.screen, bg, rect, border_radius=5)
        border_col = BTN_ACTIVE if active else BORDER_COLOR
        pygame.draw.rect(self.screen, border_col, rect, 1, border_radius=5)

        use_font = font or self.font_sm_bold
        surf = use_font.render(label, True, fg)
        self.screen.blit(
            surf,
            (rect.x + (rect.w - surf.get_width()) // 2, rect.y + (rect.h - surf.get_height()) // 2),
        )

    def draw_board(self) -> None:
        if not self.csp:
            return

        step = self.current_step()
        assignment = step.assignment if step else {}
        domains = step.domains if step else self.csp.initial_domains
        focus_var = step.focus_var if step else None
        affected_vars = set(step.affected_vars) if step else set()
        step_type = step.step_type if step else "INITIAL"

        # Dynamically sized fonts based on cell_size
        digit_font = pygame.font.SysFont("Segoe UI, Arial", max(20, int(self.cell_size * 0.46)), bold=True)
        clue_font = pygame.font.SysFont("Segoe UI, Arial", max(11, int(self.cell_size * 0.22)), bold=True)
        cand_font = pygame.font.SysFont("Segoe UI, Arial", max(10, int(self.cell_size * 0.19)), bold=True)

        # Outer board frame
        board_rect = pygame.Rect(
            self.grid_offset_x - 2,
            self.grid_offset_y - 2,
            self.csp.cols * self.cell_size + 4,
            self.csp.rows * self.cell_size + 4,
        )
        pygame.draw.rect(self.screen, GRID_LINE_COLOR, board_rect, border_radius=2)

        for r in range(self.csp.rows):
            for c in range(self.csp.cols):
                x = self.grid_offset_x + c * self.cell_size
                y = self.grid_offset_y + r * self.cell_size
                rect = pygame.Rect(x, y, self.cell_size, self.cell_size)
                cell = self.csp.grid[r][c]

                if isinstance(cell, BlockCell):
                    pygame.draw.rect(self.screen, BLOCK_CELL_BG, rect)
                    pygame.draw.line(self.screen, CLUE_LINE_COLOR, (x, y), (x + self.cell_size, y + self.cell_size), 2)
                    pygame.draw.rect(self.screen, GRID_LINE_COLOR, rect, 1)

                elif isinstance(cell, ClueCell):
                    pygame.draw.rect(self.screen, CLUE_CELL_BG, rect)
                    pygame.draw.line(self.screen, CLUE_LINE_COLOR, (x, y), (x + self.cell_size, y + self.cell_size), 2)
                    pygame.draw.rect(self.screen, GRID_LINE_COLOR, rect, 1)

                    # Down clue in bottom-left triangle
                    if cell.down_clue is not None:
                        s_down = clue_font.render(str(cell.down_clue), True, DOWN_CLUE_COLOR)
                        dx = x + int(self.cell_size * 0.26) - s_down.get_width() // 2
                        dy = y + int(self.cell_size * 0.72) - s_down.get_height() // 2
                        self.screen.blit(s_down, (dx, dy))

                    # Right clue in top-right triangle
                    if cell.right_clue is not None:
                        s_right = clue_font.render(str(cell.right_clue), True, RIGHT_CLUE_COLOR)
                        rx = x + int(self.cell_size * 0.72) - s_right.get_width() // 2
                        ry = y + int(self.cell_size * 0.26) - s_right.get_height() // 2
                        self.screen.blit(s_right, (rx, ry))

                elif isinstance(cell, WhiteCell):
                    pos = (r, c)
                    is_assigned = pos in assignment

                    # Choose cell background & highlight border
                    bg = WHITE_CELL_BG
                    highlight_border = None

                    if step_type == "SOLVED":
                        bg = SOLVED_CELL_BG
                    elif step_type == "UNSOLVABLE":
                        bg = BACKTRACK_BG
                        highlight_border = BACKTRACK_BORDER
                    elif pos == focus_var:
                        if step_type == "BACKTRACK":
                            bg = BACKTRACK_BG
                            highlight_border = BACKTRACK_BORDER
                        else:
                            bg = FOCUS_ASSIGN_BG
                            highlight_border = FOCUS_ASSIGN_BORDER
                    elif pos in affected_vars and step_type in ("PROPAGATE", "PRUNE"):
                        bg = PROPAGATE_BG
                        highlight_border = PROPAGATE_BORDER
                    elif is_assigned:
                        bg = ASSIGNED_CELL_BG

                    pygame.draw.rect(self.screen, bg, rect)
                    pygame.draw.rect(self.screen, GRID_LINE_COLOR, rect, 1)

                    if highlight_border:
                        pygame.draw.rect(self.screen, highlight_border, rect.inflate(-2, -2), 3)

                    if pos == self.selected_cell:
                        pygame.draw.rect(self.screen, SELECTED_BORDER, rect.inflate(-4, -4), 2)

                    # Render either the assigned value, backtracking value, or candidate domain
                    if pos == focus_var and step_type == "BACKTRACK" and step and step.focus_val is not None:
                        # Show retracted value in red
                        s_val = digit_font.render(str(step.focus_val), True, (200, 35, 35))
                        self.screen.blit(
                            s_val,
                            (x + (self.cell_size - s_val.get_width()) // 2, y + (self.cell_size - s_val.get_height()) // 2),
                        )
                    elif is_assigned:
                        val = assignment[pos]
                        s_val = digit_font.render(str(val), True, DIGIT_COLOR)
                        self.screen.blit(
                            s_val,
                            (x + (self.cell_size - s_val.get_width()) // 2, y + (self.cell_size - s_val.get_height()) // 2),
                        )
                    elif self.show_domains:
                        # Draw 3x3 candidate domain matrix for numbers 1..9
                        cell_dom = domains.get(pos, set())
                        sub_w = self.cell_size / 3.0
                        sub_h = self.cell_size / 3.0
                        for d in range(1, 10):
                            dr = (d - 1) // 3
                            dc = (d - 1) % 3
                            cx = x + int((dc + 0.5) * sub_w)
                            cy = y + int((dr + 0.5) * sub_h)
                            if d in cell_dom:
                                s_cand = cand_font.render(str(d), True, DOMAIN_DIGIT_COLOR)
                                self.screen.blit(
                                    s_cand,
                                    (cx - s_cand.get_width() // 2, cy - s_cand.get_height() // 2),
                                )
                            else:
                                s_cand = cand_font.render("·", True, DOMAIN_PRUNED_COLOR)
                                self.screen.blit(
                                    s_cand,
                                    (cx - s_cand.get_width() // 2, cy - s_cand.get_height() // 2),
                                )

    def draw_wrapped_text(
        self, text: str, x: int, y: int, max_width: int, font: pygame.font.Font, color: Tuple[int, int, int]
    ) -> int:
        words = text.split()
        lines: List[str] = []
        current = ""
        for w in words:
            test = f"{current} {w}".strip()
            if font.size(test)[0] <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = w
        if current:
            lines.append(current)

        cur_y = y
        for line in lines:
            surf = font.render(line, True, color)
            self.screen.blit(surf, (x, cur_y))
            cur_y += surf.get_height() + 3
        return cur_y

    def build_ui_rects(self) -> Dict[str, pygame.Rect]:
        px = self.board_area_w + 18
        pw = self.w - px - 18
        rects: Dict[str, pygame.Rect] = {}

        # Puzzle buttons
        y = 58
        n_puz = max(1, len(self.puzzle_files))
        puz_w = (pw - 6 * (n_puz - 1)) // n_puz
        for i in range(len(self.puzzle_files)):
            rects[f"puzzle_{i}"] = pygame.Rect(px + i * (puz_w + 6), y, puz_w, 32)

        # Mode buttons (3 columns)
        y = 122
        bw = (pw - 12) // 3
        for i in range(len(self.modes)):
            rects[f"mode_{i}"] = pygame.Rect(px + i * (bw + 6), y, bw, 32)

        # Playback controls
        y = 190
        ctrl_w = (pw - 18) // 4
        rects["btn_prev"] = pygame.Rect(px, y, ctrl_w, 34)
        rects["btn_play"] = pygame.Rect(px + ctrl_w + 6, y, ctrl_w, 34)
        rects["btn_next"] = pygame.Rect(px + 2 * (ctrl_w + 6), y, ctrl_w, 34)
        rects["btn_reset"] = pygame.Rect(px + 3 * (ctrl_w + 6), y, ctrl_w, 34)

        y = 232
        half_w = (pw - 6) // 2
        rects["btn_end"] = pygame.Rect(px, y, half_w, 30)
        rects["btn_domains"] = pygame.Rect(px + half_w + 6, y, half_w, 30)

        # Speed buttons
        y = 294
        sp_w = (pw - 18) // 4
        for i in range(len(self.speeds)):
            rects[f"speed_{i}"] = pygame.Rect(px + i * (sp_w + 6), y, sp_w, 28)

        return rects

    def draw_panel(self, rects: Dict[str, pygame.Rect]) -> None:
        panel_rect = pygame.Rect(self.board_area_w, 0, self.w - self.board_area_w, self.h)
        pygame.draw.rect(self.screen, PANEL_COLOR, panel_rect)
        pygame.draw.line(self.screen, BORDER_COLOR, (self.board_area_w, 0), (self.board_area_w, self.h), 2)

        px = self.board_area_w + 18
        pw = self.w - px - 18

        # Header
        title_s = self.font_title.render("KAKURO CSP VISUALIZER", True, TEXT_COLOR)
        self.screen.blit(title_s, (px, 14))

        # 1. Puzzle Selection
        self.screen.blit(self.font_sm_bold.render("1. Select Puzzle Board:", True, MUTED_TEXT), (px, 38))
        for i, path in enumerate(self.puzzle_files):
            bname = os.path.splitext(os.path.basename(path))[0]
            self.draw_button(rects[f"puzzle_{i}"], bname, active=(i == self.puzzle_idx), font=self.font_xs)

        # 2. Algorithm Selection
        self.screen.blit(self.font_sm_bold.render("2. CSP Algorithm Configuration:", True, MUTED_TEXT), (px, 100))
        for i, m in enumerate(self.modes):
            self.draw_button(rects[f"mode_{i}"], m, active=(i == self.mode_idx), font=self.font_xs)

        # 3. Playback Controls
        self.screen.blit(self.font_sm_bold.render("3. Step-by-Step Search Playback:", True, MUTED_TEXT), (px, 166))
        self.draw_button(rects["btn_prev"], "< Step", enabled=(self.step_idx > 0))
        self.draw_button(
            rects["btn_play"],
            "Pause" if not self.paused else "Play",
            active=not self.paused,
            enabled=(self.step_idx < len(self.steps) - 1),
        )
        self.draw_button(rects["btn_next"], "Step >", enabled=(self.step_idx < len(self.steps) - 1))
        self.draw_button(rects["btn_reset"], "Reset", enabled=(self.step_idx > 0))

        self.draw_button(rects["btn_end"], "Jump to End", enabled=(self.step_idx < len(self.steps) - 1))
        dom_label = f"Candidate Domains: {'ON' if self.show_domains else 'OFF'}"
        self.draw_button(rects["btn_domains"], dom_label, active=self.show_domains)

        # 4. Speed Selector
        self.screen.blit(self.font_sm_bold.render("Animation Speed:", True, MUTED_TEXT), (px, 272))
        for i, (label, _) in enumerate(self.speeds):
            self.draw_button(rects[f"speed_{i}"], label, active=(i == self.speed_idx), font=self.font_xs)

        # 5. Current Step Status Card
        step = self.current_step()
        card_y = 336
        card_rect = pygame.Rect(px, card_y, pw, 112)
        pygame.draw.rect(self.screen, CARD_COLOR, card_rect, border_radius=6)
        pygame.draw.rect(self.screen, BORDER_COLOR, card_rect, 1, border_radius=6)

        if step:
            badge_colors = {
                "INITIAL": (100, 115, 140),
                "PRUNE": (30, 155, 210),
                "ASSIGN": (215, 150, 20),
                "PROPAGATE": (25, 160, 220),
                "BACKTRACK": (215, 55, 55),
                "SOLVED": (40, 175, 95),
                "UNSOLVABLE": (190, 30, 30),
            }
            b_col = badge_colors.get(step.step_type, BTN_ACTIVE)
            badge_rect = pygame.Rect(px + 12, card_y + 10, 105, 24)
            pygame.draw.rect(self.screen, b_col, badge_rect, border_radius=4)
            b_surf = self.font_xs.render(step.step_type, True, (255, 255, 255))
            self.screen.blit(
                b_surf,
                (badge_rect.x + (badge_rect.w - b_surf.get_width()) // 2, badge_rect.y + 4),
            )

            step_counter = f"Step {self.step_idx + 1} / {len(self.steps)}"
            sc_surf = self.font_sm_bold.render(step_counter, True, TEXT_COLOR)
            self.screen.blit(sc_surf, (px + pw - sc_surf.get_width() - 12, card_y + 12))

            self.draw_wrapped_text(
                step.description,
                px + 12,
                card_y + 42,
                pw - 24,
                self.font_sm,
                TEXT_COLOR,
            )

        # 6. Solver Performance Metrics Card
        met_y = 458
        met_rect = pygame.Rect(px, met_y, pw, 134)
        pygame.draw.rect(self.screen, CARD_COLOR, met_rect, border_radius=6)
        pygame.draw.rect(self.screen, BORDER_COLOR, met_rect, 1, border_radius=6)

        self.screen.blit(self.font_sm_bold.render("Solver Metrics & Statistics:", True, BTN_ACTIVE), (px + 12, met_y + 8))
        if self.solver_result and self.csp and step:
            res = self.solver_result
            rows_info = [
                ("Assigned Variables:", f"{len(step.assignment)} / {len(self.csp.variables)} cells"),
                ("Total Assignments Tried:", f"{res.assignments_count}"),
                ("Total Backtracks:", f"{res.backtracks_count}"),
                ("Total Domain Values Pruned:", f"{res.pruned_values_count}"),
                ("Solver Execution Time:", f"{res.execution_time_ms:.3f} ms"),
            ]
            ry = met_y + 30
            for k_str, v_str in rows_info:
                ks = self.font_sm.render(k_str, True, MUTED_TEXT)
                vs = self.font_sm_bold.render(v_str, True, TEXT_COLOR)
                self.screen.blit(ks, (px + 12, ry))
                self.screen.blit(vs, (px + pw - vs.get_width() - 12, ry))
                ry += 20

        # 7. Selected Cell Inspector & Color Legend
        insp_y = 602
        insp_rect = pygame.Rect(px, insp_y, pw, 144)
        pygame.draw.rect(self.screen, CARD_COLOR, insp_rect, border_radius=6)
        pygame.draw.rect(self.screen, BORDER_COLOR, insp_rect, 1, border_radius=6)

        self.screen.blit(
            self.font_sm_bold.render("Variable Inspector (Click any white cell):", True, BTN_ACTIVE),
            (px + 12, insp_y + 8),
        )
        if self.selected_cell and self.csp and step:
            sr, sc = self.selected_cell
            val_assigned = step.assignment.get(self.selected_cell)
            dom_set = sorted(step.domains.get(self.selected_cell, set()))
            runs = self.csp.cell_to_runs.get(self.selected_cell, [])
            run_desc = ", ".join(
                f"{r.direction.capitalize()} Sum={r.target_sum} ({r.length} cells)" for r in runs
            )

            info_lines = [
                f"Variable: X({sr}, {sc})   |   Assigned Value: {val_assigned if val_assigned else 'None'}",
                f"Current Domain D(X): {dom_set}",
                f"Constraints: {run_desc}",
            ]
            iy = insp_y + 30
            for line in info_lines:
                s = self.font_xs.render(line, True, TEXT_COLOR)
                self.screen.blit(s, (px + 12, iy))
                iy += 19

        # Color Legend at bottom of inspector card
        leg_y = insp_y + 96
        pygame.draw.line(self.screen, BORDER_COLOR, (px + 10, leg_y - 4), (px + pw - 10, leg_y - 4), 1)
        legends = [
            (FOCUS_ASSIGN_BORDER, "Assign (MRV/LCV)"),
            (PROPAGATE_BORDER, "Propagate (FC Pruned)"),
            (BACKTRACK_BORDER, "Backtrack"),
            ((40, 175, 95), "Solved"),
        ]
        lx = px + 12
        for col, text in legends:
            pygame.draw.rect(self.screen, col, (lx, leg_y + 4, 12, 12), border_radius=2)
            ls = self.font_xs.render(text, True, MUTED_TEXT)
            self.screen.blit(ls, (lx + 16, leg_y + 2))
            lx += ls.get_width() + 28

        # Shortcut hint
        hint = self.font_xs.render("Shortcuts: [Space] Play/Pause  |  [Left/Right] Step  |  [R] Reset  |  [D] Toggle Domains", True, MUTED_TEXT)
        self.screen.blit(hint, (px + 12, leg_y + 24))

    def handle_board_click(self, pos: Tuple[int, int]) -> None:
        if not self.csp:
            return
        mx, my = pos
        c = (mx - self.grid_offset_x) // self.cell_size
        r = (my - self.grid_offset_y) // self.cell_size
        if 0 <= r < self.csp.rows and 0 <= c < self.csp.cols:
            if isinstance(self.csp.grid[r][c], WhiteCell):
                self.selected_cell = (r, c)

    def run(self) -> None:
        running = True
        while running:
            now = pygame.time.get_ticks()
            rects = self.build_ui_rects()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        if self.step_idx >= len(self.steps) - 1:
                            self.step_idx = 0
                        self.paused = not self.paused
                        self.last_step_tick = now
                    elif event.key == pygame.K_RIGHT:
                        self.paused = True
                        if self.step_idx < len(self.steps) - 1:
                            self.step_idx += 1
                            if self.steps[self.step_idx].focus_var:
                                self.selected_cell = self.steps[self.step_idx].focus_var
                    elif event.key == pygame.K_LEFT:
                        self.paused = True
                        if self.step_idx > 0:
                            self.step_idx -= 1
                            if self.steps[self.step_idx].focus_var:
                                self.selected_cell = self.steps[self.step_idx].focus_var
                    elif event.key == pygame.K_r:
                        self.paused = True
                        self.step_idx = 0
                    elif event.key == pygame.K_e:
                        self.paused = True
                        self.step_idx = max(0, len(self.steps) - 1)
                    elif event.key == pygame.K_d:
                        self.show_domains = not self.show_domains

                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mpos = event.pos
                    if mpos[0] < self.board_area_w:
                        self.handle_board_click(mpos)
                    else:
                        # Check puzzle buttons
                        for i in range(len(self.puzzle_files)):
                            if rects[f"puzzle_{i}"].collidepoint(mpos) and i != self.puzzle_idx:
                                self.puzzle_idx = i
                                self.load_puzzle(self.puzzle_files[i])
                                break

                        # Check mode buttons
                        for i in range(len(self.modes)):
                            if rects[f"mode_{i}"].collidepoint(mpos) and i != self.mode_idx:
                                self.mode_idx = i
                                self.run_solver()
                                break

                        # Check playback controls
                        if rects["btn_prev"].collidepoint(mpos) and self.step_idx > 0:
                            self.paused = True
                            self.step_idx -= 1
                        elif rects["btn_play"].collidepoint(mpos):
                            if self.step_idx >= len(self.steps) - 1:
                                self.step_idx = 0
                            self.paused = not self.paused
                            self.last_step_tick = now
                        elif rects["btn_next"].collidepoint(mpos) and self.step_idx < len(self.steps) - 1:
                            self.paused = True
                            self.step_idx += 1
                        elif rects["btn_reset"].collidepoint(mpos):
                            self.paused = True
                            self.step_idx = 0
                        elif rects["btn_end"].collidepoint(mpos):
                            self.paused = True
                            self.step_idx = max(0, len(self.steps) - 1)
                        elif rects["btn_domains"].collidepoint(mpos):
                            self.show_domains = not self.show_domains

                        # Check speed buttons
                        for i in range(len(self.speeds)):
                            if rects[f"speed_{i}"].collidepoint(mpos):
                                self.speed_idx = i
                                break

            # Auto-advance step when playing
            if not self.paused and self.steps:
                delay_ms = self.speeds[self.speed_idx][1]
                if now - self.last_step_tick >= delay_ms:
                    self.last_step_tick = now
                    if self.step_idx < len(self.steps) - 1:
                        self.step_idx += 1
                        if self.steps[self.step_idx].focus_var:
                            self.selected_cell = self.steps[self.step_idx].focus_var
                    else:
                        self.paused = True

            self.screen.fill(BG_COLOR)
            self.draw_board()
            self.draw_panel(rects)
            pygame.display.flip()
            self.clock.tick(60)

        pygame.quit()
