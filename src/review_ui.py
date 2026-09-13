import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GOLDEN_PATH = ROOT / "data" / "golden" / "golden_set.csv"
TAXONOMY_PATH = ROOT / "data" / "processed" / "intent_taxonomy.json"

class ReviewApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Golden Set Review Tool")
        self.root.geometry("1000x800")
        
        self.df = pd.read_csv(GOLDEN_PATH)
        self.current_idx = 0
        
        import json
        with open(TAXONOMY_PATH, encoding="utf-8") as f:
            tax = json.load(f)
        self.intent_options = [t["intent_name"] for t in tax]
        
        self.setup_ui()
        self.load_current()
        
    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header
        self.header_var = tk.StringVar()
        ttk.Label(main_frame, textvariable=self.header_var, font=("Arial", 14, "bold")).pack(anchor=tk.W, pady=5)
        
        # Context (Preceding)
        ttk.Label(main_frame, text="Preceding Context:").pack(anchor=tk.W)
        self.context_text = tk.Text(main_frame, height=4, width=100, wrap=tk.WORD, bg="#f0f0f0")
        self.context_text.pack(fill=tk.X, pady=5)
        
        # Customer Message
        ttk.Label(main_frame, text="Customer Message (TARGET):", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        self.msg_text = tk.Text(main_frame, height=5, width=100, wrap=tk.WORD)
        self.msg_text.pack(fill=tk.X, pady=5)
        
        # Brand Response
        ttk.Label(main_frame, text="Following Brand Response:").pack(anchor=tk.W)
        self.brand_text = tk.Text(main_frame, height=4, width=100, wrap=tk.WORD, bg="#f0f0f0")
        self.brand_text.pack(fill=tk.X, pady=5)
        
        # Form
        form_frame = ttk.Frame(main_frame)
        form_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(form_frame, text="Intent:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.intent_var = tk.StringVar()
        self.intent_combo = ttk.Combobox(form_frame, textvariable=self.intent_var, values=self.intent_options, width=30)
        self.intent_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        self.auto_intent_var = tk.StringVar()
        ttk.Label(form_frame, textvariable=self.auto_intent_var, foreground="gray").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(form_frame, text="Escalate?").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.escalate_var = tk.BooleanVar()
        ttk.Checkbutton(form_frame, variable=self.escalate_var).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        self.auto_escalate_var = tk.StringVar()
        ttk.Label(form_frame, textvariable=self.auto_escalate_var, foreground="gray").grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(form_frame, text="Escalation Reason:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.reason_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.reason_var, width=50).grid(row=2, column=1, columnspan=2, sticky=tk.W, padx=5, pady=5)
        
        # Stats
        self.stats_var = tk.StringVar()
        ttk.Label(form_frame, textvariable=self.stats_var).grid(row=3, column=0, columnspan=3, sticky=tk.W, padx=5, pady=10)
        
        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(btn_frame, text="<< Prev", command=self.prev).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Next >>", command=self.next).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text="Mark Reviewed & Next", command=self.mark_reviewed, style="Accent.TButton").pack(side=tk.LEFT, padx=20)
        ttk.Button(btn_frame, text="Save to CSV", command=self.save_csv).pack(side=tk.RIGHT, padx=5)
        
    def load_current(self):
        row = self.df.iloc[self.current_idx]
        
        self.header_var.set(f"Example {self.current_idx + 1} of {len(self.df)} ({row['example_id']}) - Status: {row['label_status']}")
        
        self.context_text.config(state=tk.NORMAL)
        self.context_text.delete(1.0, tk.END)
        self.context_text.insert(tk.END, str(row.get("context", "")))
        self.context_text.config(state=tk.DISABLED)
        
        self.msg_text.config(state=tk.NORMAL)
        self.msg_text.delete(1.0, tk.END)
        self.msg_text.insert(tk.END, str(row["text"]))
        self.msg_text.config(state=tk.DISABLED)
        
        self.brand_text.config(state=tk.NORMAL)
        self.brand_text.delete(1.0, tk.END)
        self.brand_text.insert(tk.END, str(row.get("following_brand_response", "")))
        self.brand_text.config(state=tk.DISABLED)
        
        self.intent_var.set(row["human_editable_intent"])
        self.escalate_var.set(bool(row["human_editable_escalation"]))
        self.reason_var.set(str(row.get("escalation_reason", "")))
        
        self.auto_intent_var.set(f"(Auto: {row['intent']})")
        self.auto_escalate_var.set(f"(Auto: {row['should_escalate_auto']})")
        
        prec = row.get("historical_precedent_quality", "")
        self.stats_var.set(f"Precedent Quality: {prec} | Thread Depth: {row['thread_depth']}")
        
    def save_current(self):
        self.df.at[self.current_idx, "human_editable_intent"] = self.intent_var.get()
        self.df.at[self.current_idx, "human_editable_escalation"] = self.escalate_var.get()
        self.df.at[self.current_idx, "escalation_reason"] = self.reason_var.get()
        
    def next(self):
        self.save_current()
        if self.current_idx < len(self.df) - 1:
            self.current_idx += 1
            self.load_current()
            
    def prev(self):
        self.save_current()
        if self.current_idx > 0:
            self.current_idx -= 1
            self.load_current()
            
    def mark_reviewed(self):
        self.df.at[self.current_idx, "label_status"] = "human_reviewed"
        self.save_current()
        if self.current_idx < len(self.df) - 1:
            self.current_idx += 1
            self.load_current()
        else:
            self.load_current()
            messagebox.showinfo("Done", "You reached the end of the set!")
            
    def save_csv(self):
        self.save_current()
        self.df.to_csv(GOLDEN_PATH, index=False)
        messagebox.showinfo("Saved", f"Saved successfully to {GOLDEN_PATH.name}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ReviewApp(root)
    root.mainloop()
