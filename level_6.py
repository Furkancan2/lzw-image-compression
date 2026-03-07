import os
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from PIL import Image, ImageTk
import numpy as np

try:
    from LZW import LZWCoding
    from level_2 import ImageLZWCoding, calculate_entropy as entropy2
    from level_3 import DiffImageLZWCoding, calculate_entropy as entropy3
    from level_4 import ColorImageLZWCoding
    from level_5 import ColorDiffImageLZWCoding
except ImportError as e:
    print(f"Import Error: {e}")

# Color constants used throughout the GUI
BG       = "#f5f5f5"
WHITE    = "#ffffff"
BORDER   = "#d0d0d0"
HEADER   = "#2c3e50"
ACCENT   = "#2980b9"
GREEN    = "#27ae60"
RED      = "#e74c3c"
TEXT     = "#2c3e50"
SUBTEXT  = "#7f8c8d"
STAT_BG  = "#eaf4fb"
STAT_VAL = "#1a5276"
MATCH_OK = "#1e8449"
MATCH_NO = "#c0392b"


class LZWCompressionGUI:

    def __init__(self, root):
        self.root = root
        self.root.title("COMP482 - LZW Compression Tool")
        self.root.geometry("1150x840")
        self.root.configure(bg=BG)
        self.root.resizable(True, True)

        # Variables to track the selected file and compression state
        self.file_path = None
        self.image_name = None
        self.file_dir = None
        self.last_lzw_object = None
        self.compressed_level = None

        self._build()

    def _build(self):
        # Top header bar
        header = tk.Frame(self.root, bg=HEADER, pady=14)
        header.pack(fill="x")
        tk.Label(header, text="LZW Image Compression Tool",
                 font=("Helvetica", 15, "bold"), fg="white", bg=HEADER).pack(side="left", padx=20)
        tk.Label(header, text="COMP482",
                 font=("Helvetica", 10), fg="#aab7c4", bg=HEADER).pack(side="right", padx=20)

        body = tk.Frame(self.root, bg=BG)
        body.pack(fill="both", expand=True, padx=16, pady=14)

        # Left sidebar (scrollable)
        left_outer = tk.Frame(body, bg=BG, width=330)
        left_outer.pack(side="left", fill="y", padx=(0, 14))
        left_outer.pack_propagate(False)

        canvas_sb = tk.Canvas(left_outer, bg=BG, highlightthickness=0, width=320)
        scrollbar = tk.Scrollbar(left_outer, orient="vertical", command=canvas_sb.yview)
        self._sidebar_inner = tk.Frame(canvas_sb, bg=BG)

        self._sidebar_inner.bind(
            "<Configure>",
            lambda e: canvas_sb.configure(scrollregion=canvas_sb.bbox("all"))
        )
        canvas_sb.create_window((0, 0), window=self._sidebar_inner, anchor="nw")
        canvas_sb.configure(yscrollcommand=scrollbar.set)
        canvas_sb.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Allow mouse wheel scrolling
        def _on_mousewheel(event):
            canvas_sb.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas_sb.bind_all("<MouseWheel>", _on_mousewheel)

        # Right side content area
        right = tk.Frame(body, bg=BG)
        right.pack(side="left", fill="both", expand=True)

        self._build_sidebar(self._sidebar_inner)
        self._build_content(right)

        # Status bar at the bottom
        self.status_var = tk.StringVar(value="Ready.")
        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x")
        tk.Label(self.root, textvariable=self.status_var,
                 bg=WHITE, fg=SUBTEXT, font=("Helvetica", 9),
                 anchor="w", padx=14, pady=5).pack(fill="x", side="bottom")

    def _card(self, parent, title):
        # Helper: creates a white card with a title label above it
        outer = tk.Frame(parent, bg=BG)
        outer.pack(fill="x", pady=(0, 12))
        tk.Label(outer, text=title, font=("Helvetica", 9, "bold"),
                 fg=SUBTEXT, bg=BG).pack(anchor="w", pady=(0, 3))
        card = tk.Frame(outer, bg=WHITE,
                        highlightthickness=1, highlightbackground=BORDER,
                        padx=12, pady=10)
        card.pack(fill="x")
        return card

    def _btn(self, parent, text, cmd, bg=ACCENT, fg="white", state="normal"):
        # Helper: creates a styled button
        b = tk.Button(parent, text=text, command=cmd,
                      bg=bg, fg=fg, activebackground=bg, activeforeground=fg,
                      disabledforeground="#aaa",
                      font=("Helvetica", 10, "bold"),
                      relief="flat", cursor="hand2",
                      state=state, pady=7)
        b.pack(fill="x", pady=3)
        return b

    def _build_sidebar(self, parent):
        # FILE section
        c1 = self._card(parent, "FILE")
        self.btn_select = self._btn(c1, "Select File", self.select_file, ACCENT)
        self.lbl_path = tk.Label(c1, text="No file selected.",
                                 fg=SUBTEXT, bg=WHITE, font=("Helvetica", 8),
                                 wraplength=280, justify="left")
        self.lbl_path.pack(anchor="w", pady=(5, 0))

        # METHOD section - radio buttons to choose compression level
        c2 = self._card(parent, "METHOD")
        self.level_var = tk.IntVar(value=2)
        levels = [
            (1, "Level 1 - Text  (Progressive LZW)"),
            (2, "Level 2 - Grayscale"),
            (3, "Level 3 - Gray Differences"),
            (4, "Level 4 - Color RGB"),
            (5, "Level 5 - Color Differences"),
        ]
        for val, label in levels:
            tk.Radiobutton(c2, text=label, variable=self.level_var, value=val,
                           bg=WHITE, fg=TEXT, selectcolor=WHITE,
                           activebackground=WHITE, activeforeground=ACCENT,
                           font=("Helvetica", 10)).pack(anchor="w", pady=2)

        # ACTIONS section
        c3 = self._card(parent, "ACTIONS")
        self.btn_compress = self._btn(c3, "▶  Compress",
                                      self.compress_action, ACCENT, state="disabled")
        self.btn_decompress = self._btn(c3, "◀  Decompress",
                                        self.decompress_action, GREEN, state="disabled")

        # STATISTICS section
        c4 = self._card(parent, "STATISTICS")
        self.stat_vars = {}

        stat_defs = [
            ("entropy",    "Entropy",            "bits/px"),
            ("avg_code",   "Avg Code Length",    "bits/px"),
            ("codelength", "Code Length",         "bits"),
            ("orig_size",  "Original Size",       "bytes"),
            ("comp_size",  "Compressed Size",     "bytes"),
            ("cr",         "Compression Ratio",   ""),
            ("cf",         "Compression Factor",  ""),
            ("ss",         "Space Saving",        ""),
        ]

        for i, (key, label, unit) in enumerate(stat_defs):
            if i % 2 == 0:
                row_bg = STAT_BG
            else:
                row_bg = WHITE

            row = tk.Frame(c4, bg=row_bg, pady=5, padx=6)
            row.pack(fill="x")
            tk.Label(row, text=label, font=("Helvetica", 9),
                     fg=TEXT, bg=row_bg, width=18, anchor="w").pack(side="left")
            var = tk.StringVar(value="-")
            self.stat_vars[key] = var
            tk.Label(row, textvariable=var, font=("Helvetica", 9, "bold"),
                     fg=STAT_VAL, bg=row_bg, anchor="w").pack(side="left")
            if unit:
                tk.Label(row, text=unit, font=("Helvetica", 8),
                         fg=SUBTEXT, bg=row_bg).pack(side="left", padx=(3, 0))
            if key == "comp_size":
                tk.Frame(c4, bg=BORDER, height=1).pack(fill="x", pady=3)

        # VERIFICATION section
        c5 = self._card(parent, "VERIFICATION")
        self.verify_var = tk.StringVar(value="-")
        self.verify_lbl = tk.Label(c5, textvariable=self.verify_var,
                                   font=("Helvetica", 9, "bold"),
                                   fg=SUBTEXT, bg=WHITE, wraplength=280,
                                   justify="left", anchor="w")
        self.verify_lbl.pack(fill="x")

    def _build_content(self, parent):
        # Image display area - side by side
        img_frame = tk.Frame(parent, bg=BG)
        img_frame.pack(fill="both", expand=True)
        img_frame.columnconfigure(0, weight=1)
        img_frame.columnconfigure(1, weight=1)
        img_frame.rowconfigure(1, weight=1)

        for col, title in [(0, "Original / Input"), (1, "Decompressed Output")]:
            tk.Label(img_frame, text=title, font=("Helvetica", 9, "bold"),
                     fg=SUBTEXT, bg=BG).grid(row=0, column=col,
                     sticky="w", padx=4, pady=(0, 4))

        self.lbl_orig = tk.Label(img_frame, text="[ no image ]",
                                  fg=BORDER, bg=WHITE, font=("Helvetica", 10),
                                  highlightthickness=1, highlightbackground=BORDER)
        self.lbl_orig.grid(row=1, column=0, sticky="nsew", padx=(0, 6))

        self.lbl_decomp = tk.Label(img_frame, text="[ no image ]",
                                    fg=BORDER, bg=WHITE, font=("Helvetica", 10),
                                    highlightthickness=1, highlightbackground=BORDER)
        self.lbl_decomp.grid(row=1, column=1, sticky="nsew", padx=(6, 0))

        # Text output area for Level 1 (text files)
        txt_frame = tk.Frame(parent, bg=BG)
        txt_frame.pack(fill="x", pady=(12, 0))
        tk.Label(txt_frame, text="Text Output  (Level 1)",
                 font=("Helvetica", 9, "bold"), fg=SUBTEXT, bg=BG).pack(anchor="w", pady=(0, 4))
        self.text_output = scrolledtext.ScrolledText(
            txt_frame, height=6, bg=WHITE, fg=TEXT,
            font=("Courier", 9), relief="solid", bd=1,
            insertbackground=TEXT, state="disabled", wrap="word",
            padx=8, pady=8)
        self.text_output.pack(fill="x")

    def _stem_path(self):
        # Returns the full path without extension
        return os.path.join(self.file_dir, self.image_name)

    def select_file(self):
        level = self.level_var.get()

        if level == 1:
            ftypes = [("Text Files", "*.txt"), ("All Files", "*.*")]
        else:
            ftypes = [("BMP Files", "*.bmp"), ("PNG Files", "*.png"), ("All Files", "*.*")]

        path = filedialog.askopenfilename(filetypes=ftypes)
        if not path:
            return

        self.file_path = os.path.abspath(path)
        self.image_name = os.path.splitext(os.path.basename(path))[0]
        self.file_dir = os.path.dirname(self.file_path)
        self.last_lzw_object = None
        self.compressed_level = None

        self.lbl_path.config(text=os.path.basename(path), fg=TEXT)
        self._reset_stats()
        self.btn_compress.config(state="normal")
        self.btn_decompress.config(state="disabled")
        self._set_text("")
        self.verify_var.set("-")
        self.verify_lbl.config(fg=SUBTEXT)

        if level != 1:
            self._show_image(self.file_path, self.lbl_orig)
        else:
            self.lbl_orig.config(image="", text="[ text file ]")
            self._load_text(self.file_path)

        self.lbl_decomp.config(image="", text="[ no image ]")
        self._status(f"Loaded: {os.path.basename(path)}")

    def compress_action(self):
        if not self.file_path:
            return

        level = self.level_var.get()
        self._status(f"Compressing - Level {level}...")
        self.root.update_idletasks()

        try:
            print(f"\n{'='*40}\nCompression - Level {level}\n{'='*40}")
            stem = self._stem_path()

            if level == 1:
                lzw = LZWCoding(stem, "text")
                out = lzw.compress_text_file()
                orig = os.path.getsize(self.file_path)
                comp = os.path.getsize(out)
                self._push(codelength=lzw.codelength, orig=orig, comp=comp)

            elif level == 2:
                lzw = ImageLZWCoding(stem)
                lzw.compress_image_file(self.file_path)
                arr = np.array(Image.open(self.file_path).convert("L"))
                comp = os.path.getsize(stem + "_compressed.bin")
                self._push(entropy=entropy2(arr),
                           avg=(comp*8)/arr.size,
                           codelength=lzw.codelength,
                           orig=arr.size, comp=comp)

            elif level == 3:
                lzw = DiffImageLZWCoding(stem)
                lzw.compress_difference_image(self.file_path)
                arr = np.array(Image.open(self.file_path).convert("L"))
                diff = lzw.get_difference_image(arr)
                comp = os.path.getsize(stem + "_diff_compressed.bin")
                self._push(entropy=entropy3(diff),
                           avg=(comp*8)/arr.size,
                           codelength=lzw.codelength,
                           orig=arr.size, comp=comp)
                self.stat_vars["entropy"].set(
                    f"{entropy3(arr):.3f} -> {entropy3(diff):.3f}")

            elif level == 4:
                lzw = ColorImageLZWCoding(stem)
                lzw.compress_color_image(self.file_path)
                arr = np.array(Image.open(self.file_path).convert("RGB"))
                total = arr.shape[0] * arr.shape[1] * 3
                comp = 0
                for c in ["R", "G", "B"]:
                    comp = comp + os.path.getsize(stem + "_" + c + "_compressed.bin")
                self._push(avg=(comp*8)/total, codelength=lzw.codelength,
                           orig=total, comp=comp)

            elif level == 5:
                lzw = ColorDiffImageLZWCoding(stem)
                lzw.compress_color_diff_image(self.file_path)
                arr = np.array(Image.open(self.file_path).convert("RGB"))
                total = arr.shape[0] * arr.shape[1] * 3
                comp = 0
                for c in ["R", "G", "B"]:
                    comp = comp + os.path.getsize(stem + "_" + c + "_diff_compressed.bin")
                self._push(avg=(comp*8)/total, codelength=lzw.codelength,
                           orig=total, comp=comp)
            else:
                return

            self.last_lzw_object = lzw
            self.compressed_level = level
            self.btn_decompress.config(state="normal")
            self.verify_var.set("Compress done. Run Decompress to verify.")
            self.verify_lbl.config(fg=SUBTEXT)
            self._status(f"Compression done - Level {level}")
            messagebox.showinfo("Done", f"Compression complete!  (Level {level})")

        except Exception as e:
            self._status(f"Error: {e}")
            messagebox.showerror("Error", str(e))

    def decompress_action(self):
        if not self.image_name:
            return

        level = self.level_var.get()

        if self.compressed_level is not None and level != self.compressed_level:
            messagebox.showwarning("Level Mismatch",
                f"Compressed with Level {self.compressed_level}, "
                f"selected Level {level}.\n\nSwitching to Level {self.compressed_level}.")
            level = self.compressed_level
            self.level_var.set(level)

        self._status(f"Decompressing - Level {level}...")
        self.root.update_idletasks()

        try:
            print(f"\n{'='*40}\nDecompression - Level {level}\n{'='*40}")
            stem = self._stem_path()
            lzw = self.last_lzw_object
            output_ext = None
            out_path = None

            if level == 1:
                if not isinstance(lzw, LZWCoding) or isinstance(lzw, ImageLZWCoding):
                    lzw = LZWCoding(stem, "text")
                out_path = lzw.decompress_text_file()
                self._load_text(out_path)
                self.lbl_decomp.config(image="", text="[ see text below ]")

                orig_path = stem + ".txt"
                if os.path.exists(orig_path) and os.path.exists(out_path):
                    with open(orig_path, 'r', encoding='utf-8', errors='replace') as f:
                        orig_text = f.read()
                    with open(out_path, 'r', encoding='utf-8', errors='replace') as f:
                        rest_text = f.read()
                    is_same = orig_text == rest_text
                    if is_same:
                        msg = "Texts are IDENTICAL (lossless)."
                    else:
                        msg = "Texts DIFFER - check encoding."
                    self._show_verify(is_same, msg)

            elif level == 2:
                if not isinstance(lzw, ImageLZWCoding):
                    lzw = ImageLZWCoding(stem)
                restored = lzw.decompress_image_file()
                output_ext = "_decompressed.bmp"
                original = np.array(Image.open(self.file_path).convert("L"))
                is_same = np.array_equal(original, restored)
                if is_same:
                    msg = "Images are IDENTICAL (lossless)."
                else:
                    msg = "Images DIFFER."
                self._show_verify(is_same, msg)

            elif level == 3:
                if not isinstance(lzw, DiffImageLZWCoding):
                    lzw = DiffImageLZWCoding(stem)
                restored = lzw.decompress_difference_image()
                output_ext = "_diff_decompressed.bmp"
                original = np.array(Image.open(self.file_path).convert("L"))
                is_same = np.array_equal(original, restored)
                if is_same:
                    msg = "Images are IDENTICAL (lossless)."
                else:
                    msg = "Images DIFFER."
                self._show_verify(is_same, msg)

            elif level == 4:
                if not isinstance(lzw, ColorImageLZWCoding):
                    lzw = ColorImageLZWCoding(stem)
                restored = lzw.decompress_color_image()
                output_ext = "_color_decompressed.bmp"
                original = np.array(Image.open(self.file_path).convert("RGB"))
                is_same = np.array_equal(original, restored)
                if is_same:
                    msg = "Images are IDENTICAL (lossless)."
                else:
                    msg = "Images DIFFER."
                self._show_verify(is_same, msg)

            elif level == 5:
                if not isinstance(lzw, ColorDiffImageLZWCoding):
                    lzw = ColorDiffImageLZWCoding(stem)
                restored = lzw.decompress_color_diff_image()
                output_ext = "_color_diff_decompressed.bmp"
                original = np.array(Image.open(self.file_path).convert("RGB"))
                is_same = np.array_equal(original, restored)
                if is_same:
                    msg = "Images are IDENTICAL (lossless)."
                else:
                    msg = "Images DIFFER."
                self._show_verify(is_same, msg)
            else:
                return

            if output_ext:
                out_path = stem + output_ext
                self._show_image(out_path, self.lbl_decomp)

            self._status(f"Decompression done - Level {level}")
            messagebox.showinfo("Done", f"Decompression complete!\nSaved to: {out_path}")

        except Exception as e:
            self._status(f"Error: {e}")
            messagebox.showerror("Error", f"Compress first!\n\n{e}")

    def _show_verify(self, success, msg):
        if success:
            prefix = "✔  "
        else:
            prefix = "✘  "
        self.verify_var.set(prefix + msg)
        if success:
            color = MATCH_OK
        else:
            color = MATCH_NO
        self.verify_lbl.config(fg=color)

    def _show_image(self, path, lbl):
        try:
            img = Image.open(path)
            lbl.update_idletasks()
            w = max(lbl.winfo_width() - 10, 280)
            h = max(lbl.winfo_height() - 10, 280)
            img.thumbnail((w, h), Image.LANCZOS)
            ph = ImageTk.PhotoImage(img)
            lbl.config(image=ph, text="")
            lbl.image = ph
        except Exception as ex:
            print(f"Image display error: {ex}")

    def _load_text(self, path):
        try:
            with open(path, "r", errors="replace") as f:
                content = f.read(4000)
            if len(content) == 4000:
                content = content + "\n... [truncated]"
            self._set_text(content)
        except Exception:
            self._set_text("[Cannot read file]")

    def _set_text(self, text):
        self.text_output.config(state="normal")
        self.text_output.delete("1.0", "end")
        if text:
            self.text_output.insert("end", text)
        self.text_output.config(state="disabled")

    def _push(self, entropy=None, avg=None, codelength=None, orig=None, comp=None):
        if entropy is not None:
            self.stat_vars["entropy"].set(f"{entropy:.4f}")
        if avg is not None:
            self.stat_vars["avg_code"].set(f"{avg:.4f}")
        if codelength is not None:
            self.stat_vars["codelength"].set(f"{codelength}")
        if orig is not None:
            self.stat_vars["orig_size"].set(f"{orig:,}")
        if comp is not None:
            self.stat_vars["comp_size"].set(f"{comp:,}")
            if orig and orig > 0 and comp > 0:
                cr = comp / orig
                cf = orig / comp
                ss = (orig - comp) / orig * 100
                self.stat_vars["cr"].set(f"{cr:.4f}")
                self.stat_vars["cf"].set(f"{cf:.4f}")
                self.stat_vars["ss"].set(f"{ss:.2f}%")

    def _reset_stats(self):
        for v in self.stat_vars.values():
            v.set("-")

    def _status(self, msg):
        self.status_var.set(msg)
        self.root.update_idletasks()


# -----------------------------------------------------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = LZWCompressionGUI(root)
    root.mainloop()