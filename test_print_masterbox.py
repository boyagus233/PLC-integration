import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox

try:
    import win32print
    PYWIN32_AVAILABLE = True
except ImportError:
    PYWIN32_AVAILABLE = False

class MasterboxPrintTestApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Yuasa Master Box Label Test Printer")
        self.root.geometry("520x680")
        self.root.resizable(False, False)
        
        # Style
        style = ttk.Style()
        style.theme_use("clam")
        
        # Header
        header_frame = tk.Frame(root, bg="#1e293b", padx=15, pady=15)
        header_frame.pack(fill="x")
        title_lbl = tk.Label(header_frame, text="YUASA MASTER BOX PRINT TESTER", font=("Arial", 14, "bold"), fg="white", bg="#1e293b")
        title_lbl.pack()
        subtitle_lbl = tk.Label(header_frame, text="Tool Pengujian Cetak Stiker Physical Master Box (TSPL Raw)", font=("Arial", 9), fg="#94a3b8", bg="#1e293b")
        subtitle_lbl.pack()

        # Form Frame
        form_frame = ttk.Frame(root, padding=20)
        form_frame.pack(fill="both", expand=True)
        
        # Printer Dropdown
        ttk.Label(form_frame, text="Pilih Printer Target:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w", pady=5)
        self.printer_cb = ttk.Combobox(form_frame, width=35, state="readonly")
        self.printer_cb.grid(row=0, column=1, sticky="w", pady=5)
        self.refresh_printers()
        
        # Inputs
        fields = [
            ("Kode QR (data.code):", "code_entry", "YBID.MB.260806.14.000070"),
            ("Part Code:", "part_code_entry", "M22BUACAD20"),
            ("TYPE (metaData.part_code):", "type_entry", "YTZ7V YU-5 AFM"),
            ("Qty / Berat:", "qty_weight_entry", "1 Pcs / 3.39 KG"),
            ("Prd/Shift/Mc:", "prd_shift_entry", "06-Aug-2026/1/14"),
            ("Waktu (HH:MM:SS):", "waktu_entry", "15:03:11"),
            ("Kode Prod (codeProduction):", "kode_prod_entry", "0608269AA"),
            ("Kode FNS (codeFinishing):", "kode_fns_entry", "07AUG2026I"),
        ]
        
        self.entries = {}
        for idx, (label_text, var_name, default_val) in enumerate(fields, start=1):
            ttk.Label(form_frame, text=label_text, font=("Arial", 9)).grid(row=idx, column=0, sticky="w", pady=6)
            ent = ttk.Entry(form_frame, width=35)
            ent.insert(0, default_val)
            ent.grid(row=idx, column=1, sticky="w", pady=6)
            self.entries[var_name] = ent

        # Print Button
        btn_frame = ttk.Frame(form_frame)
        btn_frame.grid(row=len(fields)+1, column=0, columnspan=2, pady=20)
        
        print_btn = tk.Button(btn_frame, text="🖨️ CETAK LABEL MASTER BOX (TEST)", font=("Arial", 11, "bold"), bg="#22c55e", fg="white", activebackground="#16a34a", activeforeground="white", padx=15, pady=8, command=self.print_test_label)
        print_btn.pack(side="left", padx=5)

    def refresh_printers(self):
        printers = []
        if PYWIN32_AVAILABLE:
            try:
                printer_info = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)
                printers = [p[2] for p in printer_info]
            except Exception as e:
                print(f"Error enum printers: {e}")
        
        if not printers:
            printers = ["TSC TL241", "TSC TTP-244 Pro", "Printer POS"]
            
        self.printer_cb['values'] = printers
        if printers:
            self.printer_cb.current(0)

    def print_test_label(self):
        if not PYWIN32_AVAILABLE:
            messagebox.showerror("Error Library", "Library win32print belum terinstall! Jalankan: pip install pywin32")
            return
            
        printer_name = self.printer_cb.get()
        if not printer_name:
            messagebox.showwarning("Peringatan", "Pilih printer target terlebih dahulu!")
            return
            
        code = self.entries["code_entry"].get().strip()
        part_code = self.entries["part_code_entry"].get().strip()
        batt_type = self.entries["type_entry"].get().strip()
        qty_weight = self.entries["qty_weight_entry"].get().strip()
        prd_shift = self.entries["prd_shift_entry"].get().strip()
        waktu = self.entries["waktu_entry"].get().strip()
        kode_prod = self.entries["kode_prod_entry"].get().strip()
        kode_fns = self.entries["kode_fns_entry"].get().strip()
        
        # Parse multi-code production if separated by comma
        prod_codes = [c.strip() for c in str(kode_prod).split(',') if c.strip()]
        if not prod_codes:
            prod_codes = ["-"]
            
        prod_tspl = f'TEXT 185,260,"0",0,8,8,"Kode Prod"\nTEXT 285,260,"0",0,8,8,": {prod_codes[0]}"'
        if len(prod_codes) > 1:
            prod_tspl += f'\nTEXT 285,290,"0",0,8,8,"  {prod_codes[1]}"'

        # TSPL Command (70mm x 50mm) Masterbox - Header code font 8,8 + Text X=185, Colon X=285
        tspl_command = f"""SIZE 70 mm, 50 mm
GAP 2 mm, 0 mm
DIRECTION 1
CLS
QRCODE 25,45,H,5,A,0,M2,S7,"{code}"
TEXT 185,35,"0",0,8,8,"{code}"
TEXT 185,68,"0",0,8,8,"Part Code"
TEXT 285,68,"0",0,8,8,": {part_code}"
TEXT 185,100,"0",0,8,8,"TYPE"
TEXT 285,100,"0",0,8,8,": {batt_type}"
TEXT 185,132,"0",0,8,8,"Qty / Berat"
TEXT 285,132,"0",0,8,8,": {qty_weight}"
TEXT 185,164,"0",0,8,8,"Prd/Shift/Mc"
TEXT 285,164,"0",0,8,8,": {prd_shift}"
TEXT 185,196,"0",0,8,8,"Waktu"
TEXT 285,196,"0",0,8,8,": {waktu}"
TEXT 185,228,"0",0,8,8,"Kode FNS"
TEXT 285,228,"0",0,8,8,": {kode_fns}"
{prod_tspl}
PRINT 2
"""
        try:
            hPrinter = win32print.OpenPrinter(printer_name)
            try:
                hJob = win32print.StartDocPrinter(hPrinter, 1, ("Test Print Masterbox Label", None, "RAW"))
                try:
                    win32print.StartPagePrinter(hPrinter)
                    win32print.WritePrinter(hPrinter, tspl_command.encode('utf-8'))
                    win32print.EndPagePrinter(hPrinter)
                    messagebox.showinfo("Sukses", f"Label Master Box sukses dikirim ke printer: {printer_name}")
                finally:
                    win32print.EndDocPrinter(hPrinter)
            finally:
                win32print.ClosePrinter(hPrinter)
        except Exception as e:
            messagebox.showerror("Gagal Cetak", f"Gagal mencetak ke printer {printer_name}:\n{e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = MasterboxPrintTestApp(root)
    root.mainloop()
