import tkinter as tk
from tkinter import ttk, messagebox
import json
import secrets
from datetime import datetime
import os

# =====================================
# CONFIGURACIÓN GENERAL
# =====================================

SYMBOLS = ["futbol", "trofeo", "camiseta", "porteria", "bota", "bocina"]
WEIGHTS = [30, 4, 10, 8, 6, 12]  # probabilidad relativa
REEL_COUNT = 3
MIN_BET = 1
MAX_BET = 10
START_BALANCE = 100

PAYOUT_3 = {
    "futbol": 5,
    "trofeo": 100,
    "camiseta": 10,
    "porteria": 20,
    "bota": 15,
    "bocina": 3,
}
PAYOUT_2 = 1

# Archivos por modo
SAVE_FILE_FREE = "save_free.json"
SAVE_FILE_REAL = "save_real.json"

# Estado global de modo
MODE_REAL = False


# =====================================
# FUNCIONES AUXILIARES
# =====================================

def weighted_choice(symbols, weights):
    """Elige un símbolo basado en pesos probabilísticos."""
    total = sum(weights)
    r = secrets.randbelow(total)
    upto = 0
    for s, w in zip(symbols, weights):
        if upto + w > r:
            return s
        upto += w
    return symbols[-1]


def spin_reels_once():
    """Genera una tirada completa."""
    return [weighted_choice(SYMBOLS, WEIGHTS) for _ in range(REEL_COUNT)]


def evaluate_spin(symbols, bet):
    """Evalúa la tirada y devuelve (payout, mensaje)."""
    if all(s == symbols[0] for s in symbols):
        mult = PAYOUT_3.get(symbols[0], 0)
        payout = bet * mult
        result = "🎉 JACKPOT!" if mult >= 50 else "¡Tres iguales!"
        return payout, result

    counts = {}
    for s in symbols:
        counts[s] = counts.get(s, 0) + 1
    if 2 in counts.values():
        payout = bet * PAYOUT_2
        return payout, "¡Dos iguales!"
    return 0, "Sin premio"


def save_score(balance, history):
    """Guarda el estado actual según el modo de juego."""
    file = SAVE_FILE_REAL if MODE_REAL else SAVE_FILE_FREE
    data = {"balance": balance, "history": history[-50:]}
    try:
        with open(file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Error guardando:", e)


def load_score():
    """Carga el estado guardado según el modo de juego."""
    file = SAVE_FILE_REAL if MODE_REAL else SAVE_FILE_FREE
    if not os.path.exists(file):
        return START_BALANCE, []
    try:
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("balance", START_BALANCE), data.get("history", [])
    except Exception as e:
        print("Error cargando:", e)
        return START_BALANCE, []


def simple_input(root, title, prompt):
    """Cuadro de entrada simple (sin usar ventanas externas)."""
    top = tk.Toplevel(root)
    top.title(title)
    top.configure(bg="#0b6623")
    tk.Label(top, text=prompt, bg="#0b6623", fg="#fff", font=("Helvetica", 10)).pack(padx=10, pady=5)
    entry = tk.Entry(top, font=("Helvetica", 10))
    entry.pack(padx=10, pady=5)
    entry.focus_set()
    value = []

    def ok():
        value.append(entry.get())
        top.destroy()

    tk.Button(top, text="Aceptar", command=ok, bg="#ffd43b").pack(pady=5)
    root.wait_window(top)
    return value[0] if value else ""


# =====================================
# CLASE PRINCIPAL DE LA APP
# =====================================

class GoalSpinApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.configure(bg="#0b6623")
        self.resizable(False, False)

        self._choose_mode()  # Seleccionar modo antes de cargar datos
        self.balance, self.history = load_score()

        self.bet = tk.IntVar(value=MIN_BET)
        self.spinning = False

        # Crear interfaz
        self._create_header()
        self._create_reels()
        self._create_controls()
        self._create_history_panel()
        self._create_footer()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # -------------------------
    # INTERFAZ
    # -------------------------
    def _create_header(self):
        frame = tk.Frame(self, bg="#0b6623", pady=8)
        frame.pack(fill="x")
        title_text = "GOALSPIN 💰 (Dinero Real)" if MODE_REAL else "GOALSPIN 🎮 (Gratis)"
        title = tk.Label(frame, text=title_text, font=("Helvetica", 24, "bold"),
                         bg="#0b6623", fg="#ffea00")
        title.pack()
        subtitle = tk.Label(frame, text="Tragaperras universitaria",
                            font=("Helvetica", 10), bg="#0b6623", fg="#e6fffa")
        subtitle.pack()

    def _create_reels(self):
        frame = tk.Frame(self, bg="#0b6623", pady=10)
        frame.pack()
        self.reel_labels = []
        for _ in range(REEL_COUNT):
            lbl = tk.Label(frame, text="?", font=("Helvetica", 40, "bold"), width=4, height=1,
                           bg="#e9f5ef", fg="#0b6623", relief="groove", bd=6)
            lbl.pack(side="left", padx=12)
            self.reel_labels.append(lbl)

    def _create_controls(self):
        frame = tk.Frame(self, bg="#0b6623", pady=10)
        frame.pack(fill="x", padx=12)

        left = tk.Frame(frame, bg="#0b6623")
        left.pack(side="left", anchor="w")

        tk.Label(left, text="Apuesta ($):", bg="#0b6623", fg="#fff").pack(anchor="w")
        bet_combo = ttk.Combobox(left, values=list(range(MIN_BET, MAX_BET + 1)),
                                  textvariable=self.bet, width=5, state="readonly")
        bet_combo.pack(anchor="w", pady=4)

        self.spin_button = tk.Button(left, text="🎰 GIRAR", font=("Helvetica", 12, "bold"),
                                     bg="#ffd43b", fg="#000", width=10,
                                     activebackground="#ffea00", command=self._on_spin)
        self.spin_button.pack(anchor="w", pady=6)

        if MODE_REAL:
            deposit_btn = tk.Button(left, text="💵 DEPOSITAR", font=("Helvetica", 10),
                                    bg="#00cc66", fg="#fff", width=10, command=self._deposit_money)
            deposit_btn.pack(anchor="w", pady=3)

        right = tk.Frame(frame, bg="#0b6623")
        right.pack(side="right", anchor="e")
        tk.Label(right, text="Saldo:", bg="#0b6623", fg="#fff").pack(anchor="e")
        self.balance_label = tk.Label(right, text=f"{self.balance}$", font=("Helvetica", 16, "bold"),
                                      bg="#0b6623", fg="#e6fffa")
        self.balance_label.pack(anchor="e")

        self.message_label = tk.Label(self, text="¡Bienvenido! Juega responsablemente.",
                                      bg="#0b6623", fg="#e6fffa")
        self.message_label.pack(pady=6)

    def _create_history_panel(self):
        frame = tk.Frame(self, bg="#0b6623")
        frame.pack(padx=12, pady=6, fill="x")
        tk.Label(frame, text="Historial (últimos 10):", bg="#0b6623", fg="#fff").pack(anchor="w")
        self.history_box = tk.Listbox(frame, height=6, width=50)
        self.history_box.pack()
        self._refresh_history_box()

    def _create_footer(self):
        footer = tk.Frame(self, bg="#0b6623", pady=8)
        footer.pack()
        tk.Label(footer, text="Proyecto Programación Avanzada - GoalSpin 2025",
                 bg="#0b6623", fg="#fff", font=("Helvetica", 8)).pack()

    # -------------------------
    # LÓGICA DE JUEGO
    # -------------------------
    def _choose_mode(self):
        global MODE_REAL
        res = messagebox.askquestion(
            "Modo de juego",
            "¿Quieres jugar con DINERO REAL (simulado)?\n\nSí = Dinero real\nNo = Gratis",
            icon="question"
        )
        if res == "yes":
            MODE_REAL = True
            deposit = simple_input(self, "Depósito inicial", "¿Cuánto dinero quieres depositar? (ej: 50)")
            try:
                deposit = int(deposit)
                if deposit <= 0:
                    deposit = START_BALANCE
            except:
                deposit = START_BALANCE
            self.balance = deposit
            self.title("GoalSpin 💰 Modo Dinero Real")
        else:
            MODE_REAL = False
            self.balance = START_BALANCE
            self.title("GoalSpin 🎮 Modo Gratis")

    def _on_spin(self):
        if self.spinning:
            return

        bet = int(self.bet.get())
        if bet < MIN_BET or bet > MAX_BET:
            messagebox.showwarning("Apuesta inválida", f"Apuesta entre {MIN_BET} y {MAX_BET}")
            return
        if self.balance < bet:
            messagebox.showwarning("Saldo insuficiente", "No tienes suficientes créditos")
            return

        self.balance -= bet
        self._update_balance_label()
        self.message_label.config(text="Girando...")
        self.spinning = True
        self.spin_button.config(state="disabled")

        steps, delay = 12, 80
        self._spin_animation_step(0, steps, delay, bet)

    def _spin_animation_step(self, step, steps, delay, bet):
        for lbl in self.reel_labels:
            sym = weighted_choice(SYMBOLS, WEIGHTS)
            lbl.config(text=sym)

        if step < steps:
            self.after(delay, lambda: self._spin_animation_step(step + 1, steps, delay, bet))
        else:
            result = spin_reels_once()
            for lbl, sym in zip(self.reel_labels, result):
                lbl.config(text=sym)

            payout, msg = evaluate_spin(result, bet)
            if payout > 0:
                self.balance += payout

            now = datetime.now().strftime("%H:%M:%S")
            entry = f"{now} | Apuesta: {bet}$ | {result} → {msg} (+{payout}$)"
            self.history.append(entry)
            self._refresh_history_box()
            self._update_balance_label()
            self.message_label.config(text=msg)
            self.spinning = False
            self.spin_button.config(state="normal")
            save_score(self.balance, self.history)

    def _deposit_money(self):
        amount = simple_input(self, "Depósito", "¿Cuánto dinero quieres añadir?")
        try:
            amount = int(amount)
            if amount <= 0:
                messagebox.showwarning("Cantidad inválida", "Debes ingresar un número positivo.")
                return
            self.balance += amount
            self._update_balance_label()
            self.message_label.config(text=f"Depósito de {amount}$ realizado con éxito.")
            save_score(self.balance, self.history)
        except:
            messagebox.showwarning("Error", "Ingresa una cantidad válida.")

    def _update_balance_label(self):
        self.balance_label.config(text=f"{self.balance}$")

    def _refresh_history_box(self):
        self.history_box.delete(0, tk.END)
        for entry in self.history[-10:][::-1]:
            self.history_box.insert(tk.END, entry)

    def _on_close(self):
        save_score(self.balance, self.history)
        self.destroy()


# =====================================
# EJECUCIÓN
# =====================================
if __name__ == "__main__":
    app = GoalSpinApp()
    app.mainloop()
