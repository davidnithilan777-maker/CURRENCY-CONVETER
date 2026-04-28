import tkinter as tk
from tkinter import ttk, messagebox
import urllib.request
import json
import threading
from datetime import datetime

# ── Major currencies ──────────────────────────────────────────────────────────
CURRENCIES = [
    "USD", "EUR", "GBP", "INR", "JPY", "CAD", "AUD", "CHF",
    "CNY", "SGD", "HKD", "MXN", "BRL", "KRW", "SEK", "NOK",
    "NZD", "ZAR", "AED", "SAR",
]

CURRENCY_NAMES = {
    "USD": "US Dollar",        "EUR": "Euro",              "GBP": "British Pound",
    "INR": "Indian Rupee",     "JPY": "Japanese Yen",      "CAD": "Canadian Dollar",
    "AUD": "Australian Dollar","CHF": "Swiss Franc",       "CNY": "Chinese Yuan",
    "SGD": "Singapore Dollar", "HKD": "Hong Kong Dollar",  "MXN": "Mexican Peso",
    "BRL": "Brazilian Real",   "KRW": "South Korean Won",  "SEK": "Swedish Krona",
    "NOK": "Norwegian Krone",  "NZD": "New Zealand Dollar","ZAR": "South African Rand",
    "AED": "UAE Dirham",       "SAR": "Saudi Riyal",
}

CURRENCY_SYMBOLS = {
    "USD": "$",  "EUR": "€",  "GBP": "£",  "INR": "₹",  "JPY": "¥",
    "CAD": "C$", "AUD": "A$", "CHF": "₣",  "CNY": "¥",  "SGD": "S$",
    "HKD": "HK$","MXN": "MX$","BRL": "R$", "KRW": "₩",  "SEK": "kr",
    "NOK": "kr", "NZD": "NZ$","ZAR": "R",  "AED": "د.إ","SAR": "﷼",
}

# ── Color palette (dark, refined) ─────────────────────────────────────────────
BG        = "#0f1117"
CARD      = "#1a1d27"
ACCENT    = "#6c63ff"
ACCENT2   = "#ff6584"
TEXT      = "#e8e8f0"
SUBTEXT   = "#8888aa"
BORDER    = "#2a2d3e"
SUCCESS   = "#43d9ad"
INPUT_BG  = "#22253a"

FONT_TITLE  = ("Trebuchet MS", 22, "bold")
FONT_LABEL  = ("Trebuchet MS", 10)
FONT_BOLD   = ("Trebuchet MS", 11, "bold")
FONT_RESULT = ("Trebuchet MS", 28, "bold")
FONT_RATE   = ("Trebuchet MS", 9)
FONT_SMALL  = ("Trebuchet MS", 8)


class CurrencyConverter(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Currency Converter")
        self.resizable(False, False)
        self.configure(bg=BG)

        # State
        self.rates: dict = {}
        self.last_updated = tk.StringVar(value="Fetching rates…")
        self.status_var   = tk.StringVar(value="")
        self.result_var   = tk.StringVar(value="—")
        self.rate_var     = tk.StringVar(value="")
        self._after_id    = None

        self._build_ui()
        self._center_window(560, 540)
        self.fetch_rates()          # initial fetch
        self._schedule_refresh()    # auto-refresh every 60 s

    # ── UI ────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        # ── Header ────────────────────────────────────────────────────────────
        header = tk.Frame(self, bg=BG)
        header.pack(fill="x", padx=30, pady=(28, 0))

        tk.Label(header, text="💱", font=("Segoe UI Emoji", 26),
                 bg=BG, fg=ACCENT).pack(side="left")
        tk.Label(header, text=" Currency Converter", font=FONT_TITLE,
                 bg=BG, fg=TEXT).pack(side="left")

        # refresh button (top-right)
        self.refresh_btn = tk.Button(
            header, text="⟳  Refresh", font=FONT_SMALL,
            bg=ACCENT, fg="white", relief="flat", cursor="hand2",
            activebackground="#5550dd", activeforeground="white",
            padx=10, pady=4, command=self.fetch_rates
        )
        self.refresh_btn.pack(side="right")

        # last-updated line
        tk.Label(self, textvariable=self.last_updated,
                 font=FONT_SMALL, bg=BG, fg=SUBTEXT).pack(anchor="e", padx=30)

        # ── Card ──────────────────────────────────────────────────────────────
        card = tk.Frame(self, bg=CARD, bd=0, highlightthickness=1,
                        highlightbackground=BORDER)
        card.pack(fill="both", padx=30, pady=14, ipady=20)

        # Amount
        tk.Label(card, text="AMOUNT", font=FONT_SMALL,
                 bg=CARD, fg=SUBTEXT).grid(row=0, column=0, sticky="w",
                                           padx=22, pady=(18, 2))
        self.amount_var = tk.StringVar(value="1")
        amount_entry = tk.Entry(
            card, textvariable=self.amount_var, font=("Trebuchet MS", 18, "bold"),
            bg=INPUT_BG, fg=TEXT, insertbackground=TEXT,
            relief="flat", width=18, bd=0
        )
        amount_entry.grid(row=1, column=0, columnspan=3, padx=22, pady=(0, 14),
                          sticky="ew", ipady=8)
        amount_entry.bind("<KeyRelease>", lambda e: self._on_input_change())

        # From / To selectors
        tk.Label(card, text="FROM", font=FONT_SMALL,
                 bg=CARD, fg=SUBTEXT).grid(row=2, column=0, sticky="w", padx=22)
        tk.Label(card, text="TO",   font=FONT_SMALL,
                 bg=CARD, fg=SUBTEXT).grid(row=2, column=2, sticky="w", padx=22)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Dark.TCombobox",
                         fieldbackground=INPUT_BG, background=INPUT_BG,
                         foreground=TEXT, selectbackground=ACCENT,
                         selectforeground="white", borderwidth=0,
                         arrowcolor=ACCENT)
        style.map("Dark.TCombobox",
                  fieldbackground=[("readonly", INPUT_BG)],
                  foreground=[("readonly", TEXT)])

        self.from_var = tk.StringVar(value="USD")
        self.to_var   = tk.StringVar(value="INR")

        self.from_cb = ttk.Combobox(card, textvariable=self.from_var,
                                    values=CURRENCIES, state="readonly",
                                    style="Dark.TCombobox", width=10,
                                    font=FONT_BOLD)
        self.from_cb.grid(row=3, column=0, padx=22, pady=4, sticky="ew", ipady=6)

        # Swap button
        swap_btn = tk.Button(card, text="⇄", font=("Trebuchet MS", 16, "bold"),
                             bg=CARD, fg=ACCENT, relief="flat", cursor="hand2",
                             activebackground=CARD, activeforeground=ACCENT2,
                             command=self._swap)
        swap_btn.grid(row=3, column=1, padx=4)

        self.to_cb = ttk.Combobox(card, textvariable=self.to_var,
                                  values=CURRENCIES, state="readonly",
                                  style="Dark.TCombobox", width=10,
                                  font=FONT_BOLD)
        self.to_cb.grid(row=3, column=2, padx=22, pady=4, sticky="ew", ipady=6)

        self.from_cb.bind("<<ComboboxSelected>>", lambda e: self._on_input_change())
        self.to_cb.bind  ("<<ComboboxSelected>>", lambda e: self._on_input_change())

        # Convert button
        conv_btn = tk.Button(
            card, text="Convert", font=FONT_BOLD,
            bg=ACCENT, fg="white", relief="flat", cursor="hand2",
            activebackground="#5550dd", activeforeground="white",
            padx=0, pady=10, command=self.convert
        )
        conv_btn.grid(row=4, column=0, columnspan=3, padx=22, pady=(16, 0),
                      sticky="ew")

        # ── Result area ───────────────────────────────────────────────────────
        result_frame = tk.Frame(self, bg=BG)
        result_frame.pack(fill="x", padx=30, pady=(4, 0))

        self.result_label = tk.Label(
            result_frame, textvariable=self.result_var,
            font=FONT_RESULT, bg=BG, fg=SUCCESS
        )
        self.result_label.pack()

        tk.Label(result_frame, textvariable=self.rate_var,
                 font=FONT_RATE, bg=BG, fg=SUBTEXT).pack()

        # Status / error bar
        tk.Label(self, textvariable=self.status_var,
                 font=FONT_SMALL, bg=BG, fg=ACCENT2).pack(pady=(4, 10))

    # ── Core logic ────────────────────────────────────────────────────────────
    def fetch_rates(self):
        """Fetch live rates from open.er-api.com (free, no key needed)."""
        self.last_updated.set("🔄 Fetching live rates…")
        self.refresh_btn.config(state="disabled")
        threading.Thread(target=self._fetch_thread, daemon=True).start()

    def _fetch_thread(self):
        url = "https://open.er-api.com/v6/latest/USD"
        try:
            with urllib.request.urlopen(url, timeout=10) as r:
                data = json.loads(r.read().decode())
            if data.get("result") == "success":
                self.rates = data["rates"]
                ts = datetime.now().strftime("%d %b %Y  %H:%M:%S")
                self.after(0, lambda: self.last_updated.set(f"✅ Live rates as of {ts}"))
                self.after(0, self.convert)
            else:
                self.after(0, lambda: self._show_error("API returned an error."))
        except Exception as exc:
            self.after(0, lambda: self._show_error(f"Network error: {exc}"))
        finally:
            self.after(0, lambda: self.refresh_btn.config(state="normal"))

    def _show_error(self, msg: str):
        self.last_updated.set("⚠️  Could not fetch rates")
        self.status_var.set(msg)

    def convert(self):
        if not self.rates:
            self.status_var.set("⚠️  Rates not loaded yet. Click Refresh.")
            return
        try:
            amount = float(self.amount_var.get().replace(",", ""))
            if amount < 0:
                raise ValueError
        except ValueError:
            self.result_var.set("Invalid")
            self.rate_var.set("")
            self.status_var.set("Please enter a valid positive number.")
            return

        frm = self.from_var.get()
        to  = self.to_var.get()

        if frm not in self.rates or to not in self.rates:
            self.status_var.set("Currency not available in live data.")
            return

        # All rates are relative to USD
        rate = self.rates[to] / self.rates[frm]
        converted = amount * rate

        sym_to = CURRENCY_SYMBOLS.get(to, "")
        # Format result
        if converted >= 1_000_000:
            result_str = f"{sym_to}{converted:,.2f}"
        elif converted < 0.01:
            result_str = f"{sym_to}{converted:.6f}"
        else:
            result_str = f"{sym_to}{converted:,.4f}".rstrip("0").rstrip(".")

        self.result_var.set(result_str)
        sym_frm = CURRENCY_SYMBOLS.get(frm, "")
        self.rate_var.set(
            f"1 {frm}  =  {sym_to}{rate:,.4f} {to}   |   "
            f"{CURRENCY_NAMES.get(frm, frm)} → {CURRENCY_NAMES.get(to, to)}"
        )
        self.status_var.set("")

    def _on_input_change(self):
        if self._after_id:
            self.after_cancel(self._after_id)
        self._after_id = self.after(400, self.convert)   # debounce 400 ms

    def _swap(self):
        frm, to = self.from_var.get(), self.to_var.get()
        self.from_var.set(to)
        self.to_var.set(frm)
        self.convert()

    def _schedule_refresh(self):
        self.fetch_rates()
        self.after(60_000, self._schedule_refresh)   # refresh every 60 s

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _center_window(self, w: int, h: int):
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x  = (sw - w) // 2
        y  = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")


if __name__ == "__main__":
    app = CurrencyConverter()
    app.mainloop()
