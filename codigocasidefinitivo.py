# goalspin_with_golden_ball.py
"""
GoalSpin - Football Edition (Golden Ball + Free Spins)
- Windows recommended (winsound fallback)
- Optional assets: gold_ball.png, spin.wav, win.wav
- Optional libraries: pygame, pillow (PIL)
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import random
import os

# Optional libs
try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

try:
    import pygame
    PYGAME_AVAILABLE = True
except Exception:
    PYGAME_AVAILABLE = False

try:
    import winsound
    WINSOUND_AVAILABLE = True
except Exception:
    WINSOUND_AVAILABLE = False

# -----------------------
# CONFIG
# -----------------------
REELS = 5
ROWS = 3

# Symbols:
# - normal ball "⚽"
# - golden ball key "GOLD" (displayed with image if available or emoji 🥇)
# - other symbols
SYMBOLS_TEXT = {
    "BALL": "⚽",
    "GOAL": "🥅",
    "SHIRT": "👕",
    "BOOT": "👟",
    "TROPHY": "🏆",
    "MEGAPHONE": "📣",
    "WILD": "🏁",
    "GOLD": "🥇"   # golden ball special symbol (for free spins)
}

# Probability weights: lower weight => rarer
SYMBOL_WEIGHTS = {
    "BALL": 35,
    "MEGAPHONE": 18,
    "BOOT": 12,
    "SHIRT": 10,
    "GOAL": 8,
    "TROPHY": 3,
    "WILD": 4,
    "GOLD": 2    # golden ball rare
}

BET_OPTIONS = [1, 5, 10, 20, 30, 40, 50, 100, 200]
MAX_INITIAL_DEPOSIT = 10000

# Base payouts per symbol (used when line wins)
BASE_PAYOUT = {
    "BALL": 3,
    "MEGAPHONE": 2,
    "BOOT": 5,
    "SHIRT": 8,
    "GOAL": 12,
    "TROPHY": 40,
    "WILD": 0,
    "GOLD": 3   # golden ball pays like a ball (but mainly used for free spins)
}
COUNT_MULT = {3: 1, 4: 4, 5: 12}  # multipliers depending on consecutive count

# Paylines (row index per column)
PAYLINES = [
    [1] * REELS,            # middle
    [0] * REELS,            # top
    [2] * REELS,            # bottom
    [0, 1, 2, 1, 0],        # zig-zag down
    [2, 1, 0, 1, 2],        # zig-zag up
]

# UI colors
COLOR_FIELD_1 = "#006837"
COLOR_FIELD_2 = "#00a86b"
COLOR_BOARD = "#ffd700"
COLOR_SLOT_BG = "#083a1f"
COLOR_TEXT = "#ffffff"
COLOR_HIGHLIGHT = "#ffef00"

# Music / assets filenames (optional)
SPIN_SOUND_FILE = "spin.wav"
WIN_SOUND_FILE = "win.wav"
GOLD_BALL_IMAGE = "gold_ball.png"  # if present, used to render GOLD symbol

# Free spins mapping: count_of_gold -> free spins
FREE_SPINS_MAP = {3: 10, 4: 15, 5: 20}

# -----------------------
# Helpers
# -----------------------
def weighted_choice_from_dict(d):
    keys = list(d.keys())
    weights = [d[k] for k in keys]
    total = sum(weights)
    r = random.randint(1, total)
    upto = 0
    for k, w in zip(keys, weights):
        if upto + w >= r:
            return k
        upto += w
    return keys[-1]

def generate_grid():
    # grid[reel][row] with keys like "BALL","GOLD",...
    return [[weighted_choice_from_dict(SYMBOL_WEIGHTS) for _ in range(ROWS)] for _ in range(REELS)]

# Sound control (pygame preferred for music files)
def play_spin_music(app):
    # Play spin music loop (only while spinning)
    if PYGAME_AVAILABLE and os.path.exists(SPIN_SOUND_FILE):
        try:
            pygame.mixer.init()
            app._spin_sound = pygame.mixer.Sound(SPIN_SOUND_FILE)
            app._spin_sound.play(loops=-1)
            app._using_pygame_spin = True
            return
        except Exception:
            pass
    # fallback to winsound beep loop emulation via after
    if WINSOUND_AVAILABLE:
        app._spin_beep_flag = True
        def beep_loop():
            if not getattr(app, "_spin_beep_flag", False):
                return
            try:
                winsound.Beep(700, 45)
            except Exception:
                pass
            app.after(90, beep_loop)
        beep_loop()

def stop_spin_music(app):
    if PYGAME_AVAILABLE and getattr(app, "_spin_sound", None):
        try:
            app._spin_sound.stop()
        except Exception:
            pass
        app._spin_sound = None
    # disable beep loop
    app._spin_beep_flag = False

def play_win_sound_once():
    if PYGAME_AVAILABLE and os.path.exists(WIN_SOUND_FILE):
        try:
            s = pygame.mixer.Sound(WIN_SOUND_FILE)
            s.play()
            return
        except Exception:
            pass
    if WINSOUND_AVAILABLE:
        try:
            winsound.Beep(950, 120)
            winsound.Beep(1150, 90)
            winsound.Beep(1350, 70)
        except Exception:
            pass

# -----------------------
# App
# -----------------------
class GoalSpinApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("GOALSPIN - Football (Golden Ball Edition)")
        self.attributes("-fullscreen", True)
        self.bind("<Escape>", lambda e: self._on_close())

        # state
        self.balance = 0
        self.bet = tk.IntVar(value=BET_OPTIONS[0])
        self.is_spinning = False
        self.free_spins = 0
        self.highlight_cells = []  # persistent highlight until next spin

        # assets
        self.gold_img = None
        if PIL_AVAILABLE and os.path.exists(GOLD_BALL_IMAGE):
            try:
                img = Image.open(GOLD_BALL_IMAGE)
                # resize to fit labels (approx)
                img = img.resize((64, 64), Image.LANCZOS)
                self.gold_img = ImageTk.PhotoImage(img)
            except Exception:
                self.gold_img = None

        # ask deposit (limit)
        dep = simpledialog.askstring("Depósito inicial", f"Introduce saldo inicial (máx. {MAX_INITIAL_DEPOSIT} €):")
        try:
            x = int(dep) if dep else 100
        except Exception:
            x = 100
        self.balance = min(max(1, x), MAX_INITIAL_DEPOSIT)

        # build UI
        self._build_ui()
        self._update_balance_label()

    def _build_ui(self):
        # Top
        top = tk.Frame(self, bg=COLOR_FIELD_1)
        top.pack(fill="x")
        tk.Label(top, text="🏟️ GOALSPIN - GOLDEN BALL EDITION", font=("Impact", 32), bg=COLOR_FIELD_1, fg="#ffd700").pack(pady=6)
        self.banner = tk.Label(top, text="¡Gira y gana free spins con el balón dorado!", bg=COLOR_FIELD_1, fg=COLOR_TEXT, font=("Helvetica", 12))
        self.banner.pack()

        # Main center area
        main = tk.Frame(self, bg=COLOR_FIELD_2)
        main.pack(expand=True, fill="both", padx=20, pady=10)

        # Left and right panels (we'll add nicer patterns)
        left_panel = tk.Canvas(main, width=180, bg="#043920", highlightthickness=0)
        left_panel.pack(side="left", fill="y")
        self._decorate_stand_graphic(left_panel, left=True)

        right_panel = tk.Canvas(main, width=180, bg="#043920", highlightthickness=0)
        right_panel.pack(side="right", fill="y")
        self._decorate_stand_graphic(right_panel, left=False)

        # Board in center
        center = tk.Frame(main, bg=COLOR_FIELD_2)
        center.pack(expand=True)

        board_outer = tk.Frame(center, bg=COLOR_BOARD, bd=10, relief="ridge")
        board_outer.pack()
        board_inner = tk.Frame(board_outer, bg=COLOR_SLOT_BG, padx=12, pady=12)
        board_inner.pack()

        # Reels labels grid
        self.reel_labels = []
        for c in range(REELS):
            col_frame = tk.Frame(board_inner, bg=COLOR_SLOT_BG)
            col_frame.grid(row=0, column=c, padx=8)
            col = []
            for r in range(ROWS):
                lbl = tk.Label(col_frame, text="?", font=("Arial Black", 30), width=3, height=1,
                               bg=COLOR_SLOT_BG, fg=COLOR_TEXT, bd=6, relief="raised", compound="center")
                lbl.pack(pady=6)
                col.append(lbl)
            self.reel_labels.append(col)

        # Controls
        controls = tk.Frame(self, bg=COLOR_FIELD_1)
        controls.pack(fill="x", pady=10)
        leftc = tk.Frame(controls, bg=COLOR_FIELD_1)
        leftc.pack(side="left", padx=20)
        tk.Label(leftc, text="Apuesta (€):", bg=COLOR_FIELD_1, fg=COLOR_TEXT).pack(anchor="w")
        bet_combo = ttk.Combobox(leftc, values=BET_OPTIONS, textvariable=self.bet, state="readonly", width=10)
        bet_combo.pack(pady=6)
        tk.Button(leftc, text="🎰 GIRAR", bg="#ffd43b", fg="#000", font=("Helvetica", 12, "bold"), command=self.spin).pack(side="left", padx=6)
        tk.Button(leftc, text="💥 ALL IN", bg="#ff4d4d", fg="#fff", font=("Helvetica", 12, "bold"), command=self.all_in).pack(side="left", padx=6)

        centerc = tk.Frame(controls, bg=COLOR_FIELD_1)
        centerc.pack(side="left", padx=80)
        tk.Label(centerc, text="Saldo actual:", bg=COLOR_FIELD_1, fg=COLOR_TEXT).pack()
        self.balance_lbl = tk.Label(centerc, text="", bg=COLOR_FIELD_1, fg="#00ffcc", font=("Helvetica", 16, "bold"))
        self.balance_lbl.pack()
        self.free_spins_lbl = tk.Label(centerc, text="", bg=COLOR_FIELD_1, fg="#ffd700", font=("Helvetica", 12, "bold"))
        self.free_spins_lbl.pack()

        rightc = tk.Frame(controls, bg=COLOR_FIELD_1)
        rightc.pack(side="right", padx=20)
        self.result_banner = tk.Label(rightc, text="", bg=COLOR_FIELD_1, fg="#ffd700", font=("Impact", 20))
        self.result_banner.pack()
        tk.Label(rightc, text=f"Depósito máximo al iniciar: {MAX_INITIAL_DEPOSIT} €", bg=COLOR_FIELD_1, fg=COLOR_TEXT).pack()

    def _decorate_stand_graphic(self, canvas, left=True):
        # draw stylized crowd rectangles and stadium lights for more flair
        canvas.update()
        w = canvas.winfo_reqwidth() or 180
        h = canvas.winfo_reqheight() or 600
        # crowd stripes
        for i in range(12):
            y0 = i * h / 12
            y1 = (i + 1) * h / 12
            color = "#052e1c" if i % 2 == 0 else "#083a28"
            canvas.create_rectangle(0, y0, w, y1, fill=color, outline="")
        # stadium vertical lights
        for i in range(6):
            x = 40 if left else w - 40
            y = 40 + i * 90
            canvas.create_oval(x - 18, y - 18, x + 18, y + 18, fill="#ffd43b", outline="")

    # -----------------------
    # Spin mechanics
    # -----------------------
    def spin(self):
        if self.is_spinning:
            return

        # Clear previous highlights only at new spin start (they must stay until next spin)
        self._clear_highlights()

        bet = int(self.bet.get())
        if bet <= 0:
            messagebox.showwarning("Apuesta inválida", "Selecciona una apuesta válida.")
            return

        if self.free_spins > 0:
            # during free spins do not deduct bet
            self.free_spins -= 1
            self.free_spins_lbl.config(text=f"Tiradas gratis restantes: {self.free_spins}")
            is_free = True
        else:
            if bet > self.balance:
                messagebox.showwarning("Saldo insuficiente", "No tienes suficiente saldo.")
                return
            self.balance -= bet
            self._update_balance_label()
            is_free = False

        self.is_spinning = True
        self.result_banner.config(text="GIRANDO...", fg="#ffffff")

        # start spin music
        play_spin_music(self)

        # visual animation: random symbols for a short time, then finalize
        frames = 16
        delay_ms = 70
        self._spin_animation(frames, delay_ms, bet, is_free)

    def _spin_animation(self, remaining, delay_ms, bet, is_free):
        # display random symbols while spinning
        for c in range(REELS):
            for r in range(ROWS):
                key = random.choice(list(SYMBOL_WEIGHTS.keys()))
                # if GOLD and we have image, show image; else show text
                if key == "GOLD" and self.gold_img:
                    self.reel_labels[c][r].config(image=self.gold_img, text="", bg=COLOR_SLOT_BG)
                    self.reel_labels[c][r].image = self.gold_img
                else:
                    text = SYMBOLS_TEXT.get(key, "?")
                    self.reel_labels[c][r].config(text=text, image="", bg=COLOR_SLOT_BG, fg=COLOR_TEXT)
                    self.reel_labels[c][r].image = None
        if remaining > 0:
            self.after(delay_ms, lambda: self._spin_animation(remaining - 1, delay_ms, bet, is_free))
        else:
            stop_spin_music(self)
            self._finalize_spin(bet, is_free)

    def _finalize_spin(self, bet, is_free):
        grid = generate_grid()
        # render final grid
        for c in range(REELS):
            for r in range(ROWS):
                key = grid[c][r]
                if key == "GOLD" and self.gold_img:
                    self.reel_labels[c][r].config(image=self.gold_img, text="", bg=COLOR_SLOT_BG)
                    self.reel_labels[c][r].image = self.gold_img
                else:
                    txt = SYMBOLS_TEXT.get(key, "?")
                    self.reel_labels[c][r].config(text=txt, image="", bg=COLOR_SLOT_BG, fg=COLOR_TEXT)
                    self.reel_labels[c][r].image = None

        # Evaluate payouts (lines) and free spins (based on GOLD total)
        payout, winning_positions = self._evaluate_lines(grid, bet)
        gold_count = self._count_gold(grid)

        # apply payout
        if payout > 0:
            self.balance += payout
            # play win sound/music
            play_win_sound_once()
            # animate banner depending on ratio
            ratio = payout / (bet if bet > 0 else 1)
            self._animate_win_banner(payout, ratio)
            # highlight winning positions and keep them lit until next spin
            self.highlight_cells = winning_positions[:]
            self._apply_highlights(self.highlight_cells)
        else:
            self.result_banner.config(text="SIN PREMIO 😢", fg="#cccccc")

        # handle free spins awarding based on gold_count
        awarded = 0
        if gold_count >= 5:
            awarded = FREE_SPINS_MAP[5]
        elif gold_count == 4:
            awarded = FREE_SPINS_MAP[4]
        elif gold_count == 3:
            awarded = FREE_SPINS_MAP[3]
        if awarded > 0:
            # add to free spins pool
            self.free_spins += awarded
            # show message big
            self._show_free_spins_animation(awarded)
            self.free_spins_lbl.config(text=f"Tiradas gratis: {self.free_spins}")
        else:
            # if not awarded, clear free spins label (or show remaining)
            if self.free_spins > 0:
                self.free_spins_lbl.config(text=f"Tiradas gratis restantes: {self.free_spins}")
            else:
                self.free_spins_lbl.config(text="")

        self._update_balance_label()
        self.is_spinning = False

    # -----------------------
    # Evaluation and payouts
    # -----------------------
    def _evaluate_lines(self, grid, bet):
        total_payout = 0
        winning_positions = []
        # for each payline evaluate consecutive from left with wild substitution
        for pattern in PAYLINES:
            line_keys = [grid[col][pattern[col]] for col in range(REELS)]
            payout, count, used_sym = self._eval_line_consecutive(line_keys, bet)
            if payout > 0:
                total_payout += payout
                # mark leftmost 'count' positions on that line as winning positions
                for c in range(count):
                    winning_positions.append((c, pattern[c]))
        return total_payout, winning_positions

    def _eval_line_consecutive(self, symbols_line, bet):
        wild_key = "WILD"
        # find first non-wild
        first_non = None
        for s in symbols_line:
            if s != wild_key:
                first_non = s
                break
        # if all wild
        if first_non is None:
            cnt = len(symbols_line)
            if cnt >= 3:
                return bet * 5, cnt, wild_key
            return 0, 0, None
        # count consecutive from left
        cnt = 0
        for s in symbols_line:
            if s == first_non or s == wild_key:
                cnt += 1
            else:
                break
        if cnt >= 3:
            base = BASE_PAYOUT.get(first_non, 0)
            mult = COUNT_MULT.get(cnt, COUNT_MULT[max(COUNT_MULT.keys())])
            payout = bet * base * mult
            return payout, cnt, first_non
        return 0, 0, None

    def _count_gold(self, grid):
        c = 0
        for col in grid:
            for key in col:
                if key == "GOLD":
                    c += 1
        return c

    # -----------------------
    # Visual: highlights and animations
    # -----------------------
    def _apply_highlights(self, cells):
        for (c, r) in cells:
            if 0 <= c < REELS and 0 <= r < ROWS:
                self.reel_labels[c][r].config(bg=COLOR_HIGHLIGHT, fg="#000000")

    def _clear_highlights(self):
        if not self.highlight_cells:
            return
        for (c, r) in self.highlight_cells:
            if 0 <= c < REELS and 0 <= r < ROWS:
                self.reel_labels[c][r].config(bg=COLOR_SLOT_BG, fg=COLOR_TEXT)
                self.reel_labels[c][r].image = None
        self.highlight_cells = []

    def _animate_win_banner(self, payout, ratio):
        # choose tier
        if ratio >= 200:
            label = "SUPER MEGA WIN"
            color = "#ff3b3b"
        elif ratio >= 50:
            label = "MEGA WIN"
            color = "#ff7f00"
        elif ratio >= 20:
            label = "BIG WIN"
            color = "#ffd700"
        elif ratio >= 5:
            label = "WIN"
            color = "#00ff88"
        else:
            label = "MINI WIN"
            color = "#3fa9f5"

        text = f"{label}  +{payout} €  (x{ratio:.1f})"
        self.result_banner.config(text=text, fg=color)

        # simple pulse animation by changing font size
        sizes = [20, 26, 34, 26, 20]
        def pulse(i=0):
            if i >= len(sizes):
                self.result_banner.config(font=("Impact", 20))
                return
            self.result_banner.config(font=("Impact", sizes[i]))
            self.after(120, lambda: pulse(i + 1))
        pulse()

    def _show_free_spins_animation(self, awarded):
        # center popup-like label that pulses and stays briefly
        popup = tk.Toplevel(self)
        popup.overrideredirect(True)
        popup.attributes("-topmost", True)
        popup.configure(bg="#000000")
        w = 450; h = 140
        sw = self.winfo_screenwidth(); sh = self.winfo_screenheight()
        popup.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        lbl = tk.Label(popup, text=f"🎉 ¡{awarded} TIRADAS GRATIS!", font=("Impact", 26), bg="#000000", fg="#ffd700")
        lbl.pack(expand=True, fill="both")
        # pulse
        def pulse(i=0):
            if i > 8:
                popup.destroy()
                return
            scale = 1.0 + 0.06 * (1 if i % 2 == 0 else -1)
            lbl.config(font=("Impact", int(26 * scale)))
            self.after(180, lambda: pulse(i + 1))
        pulse()

    # -----------------------
    # All in and balance
    # -----------------------
    def all_in(self):
        if self.is_spinning:
            return
        if self.balance <= 0:
            messagebox.showinfo("Sin saldo", "No tienes saldo para All In.")
            return
        self.bet.set(self.balance)
        self.spin()

    def _update_balance_label(self):
        self.balance_lbl.config(text=f"{self.balance} €")
        if self.balance < 20:
            self.balance_lbl.config(fg="#ff4444")
        else:
            self.balance_lbl.config(fg="#00ffcc")
        if self.free_spins > 0:
            self.free_spins_lbl.config(text=f"Tiradas gratis restantes: {self.free_spins}")
        else:
            self.free_spins_lbl.config(text="")

    # -----------------------
    # Close and cleanup
    # -----------------------
    def _on_close(self):
        stop_spin_music(self)
        messagebox.showinfo("Gracias", "Gracias por jugar GoalSpin 2025. ¡Hasta la próxima!")
        self.destroy()

# -----------------------
# Run
# -----------------------
if __name__ == "__main__":
    app = GoalSpinApp()
    app.mainloop()
