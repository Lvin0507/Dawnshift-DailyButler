"""A small "about to start" window for scheduled runs, shown only when someone is at the PC."""

import tkinter as tk

from .i18n import t

NIGHT, PANEL, TEXT, MUTED, DAWN = "#141B2D", "#1C2540", "#E9E7F2", "#98A1BE", "#F4B860"


def ask_before_start(lang, seconds=60):
    """Return True to go ahead, False if the user chose to skip this run. Nobody answering
    means nobody is there after all, so the run starts when the countdown ends."""
    result = {"go": True}
    root = tk.Tk()
    root.title("Gachashift")
    root.configure(bg=NIGHT)
    root.attributes("-topmost", True)
    root.resizable(False, False)
    family = "Microsoft YaHei UI" if lang == "zh" else "Segoe UI"

    tk.Label(root, text=t(lang, "prompt.title"), font=(family, 14, "bold"), bg=NIGHT, fg=TEXT
             ).pack(anchor="w", padx=22, pady=(18, 6))
    message = tk.Label(root, font=(family, 11), bg=NIGHT, fg=MUTED, wraplength=380, justify="left")
    message.pack(anchor="w", padx=22)
    buttons = tk.Frame(root, bg=NIGHT)
    buttons.pack(fill="x", padx=22, pady=(14, 18))

    def finish(go):
        result["go"] = go
        root.destroy()

    tk.Button(buttons, text=t(lang, "prompt.skip"), font=(family, 11), bg=PANEL, fg=TEXT,
              activebackground=PANEL, relief="flat", padx=14, pady=6,
              command=lambda: finish(False)).pack(side="left")
    tk.Button(buttons, text=t(lang, "prompt.start"), font=(family, 11, "bold"), bg=DAWN, fg=NIGHT,
              activebackground=DAWN, relief="flat", padx=14, pady=6,
              command=lambda: finish(True)).pack(side="right")

    def tick(n):
        if n <= 0:
            finish(True)
            return
        message.configure(text=t(lang, "prompt.text", n=n))
        root.after(1000, tick, n - 1)

    root.protocol("WM_DELETE_WINDOW", lambda: finish(False))  # closing it counts as "skip"
    tick(seconds)
    # centre it on the screen, where someone at the PC will notice it
    root.update_idletasks()
    x = (root.winfo_screenwidth() - root.winfo_width()) // 2
    y = (root.winfo_screenheight() - root.winfo_height()) // 3
    root.geometry(f"+{x}+{y}")
    root.mainloop()
    return result["go"]
