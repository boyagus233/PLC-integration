import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox

try:
    import win32print
    PYWIN32_AVAILABLE = True
except ImportError:
    PYWIN32_AVAILABLE = False

class PalletPrintTestApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Yuasa Pallet Label Test Printer")
        self.root.geometry("520x650")
        self.root.resizable(False, False)
        
        # Style
        style = ttk.Style()
        style.theme_use("clam")
        
        # Header
        header_frame = tk.Frame(root, bg="#0f172a", padx=15, pady=15)
        header_frame.pack(fill="x")
        title_lbl = tk.Label(header_frame, text="YUASA PALLET LABEL PRINT TESTER", font=("Arial", 14, "bold"), fg="white", bg="#0f172a")
        title_lbl.pack()
        subtitle_lbl = tk.Label(header_frame, text="Tool Pengujian Cetak Stiker Physical Pallet (TSPL Raw)", font=("Arial", 9), fg="#94a3b8", bg="#0f172a")
        subtitle_lbl.pack()

        # Form Frame
        form_frame = ttk.Frame(root, padding=20)
        form_frame.pack(fill="both", expand=True)
        
        # Printer Dropdown
        ttk.Label(form_frame, text="Pilih Printer Target:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w", pady=5)
        self.printer_cb = ttk.Combobox(form_frame, width=35, state="readonly")
        self.printer_cb.grid(row=0, column=1, sticky="w", pady=5)
        self.refresh_printers()
        
        # Inputs for Pallet Label (Live API Example Data)
        fields = [
            ("Group Code (QR):", "code_entry", "YBID.PLT.260807.000001"),
            ("Order No.:", "order_no_entry", "11500007"),
            ("Customer:", "customer_entry", "AFM (PT. SANTI YOGA)"),
            ("Part Code:", "part_code_entry", "M221RDFWU1B"),
            ("Batt. Type:", "batt_type_entry", "B.UNCH-YTZ4V (Wet-CF) YU-5 YMH(19)"),
            ("Quantity:", "qty_entry", "6 pcs - 1 pkgs"),
            ("Prd/Shift/Mc:", "prd_shift_entry", "07-Aug-2026/2/1"),
            ("Kode Prod (codeProduction):", "kode_prod_entry", "0708269B"),
            ("Kode Prod Qty (codeProductionQuantity):", "kode_prod_qty_entry", "5"),
        ]
        
        self.entries = {}
        for idx, (label_text, var_name, default_val) in enumerate(fields, start=1):
            ttk.Label(form_frame, text=label_text, font=("Arial", 9)).grid(row=idx, column=0, sticky="w", pady=6)
            ent = ttk.Entry(form_frame, width=35)
            ent.insert(0, default_val)
            ent.grid(row=idx, column=1, sticky="w", pady=6)
            self.entries[var_name] = ent

        # Print Button
        print_btn = tk.Button(form_frame, text="🖨️ CETAK LABEL PALLET (TEST)", font=("Arial", 11, "bold"), bg="#10b981", fg="white", activebackground="#059669", activeforeground="white", relief="flat", cursor="hand2", command=self.do_print)
        print_btn.grid(row=len(fields)+1, column=0, columnspan=2, pady=25, ipady=8, sticky="ew")

    def refresh_printers(self):
        if not PYWIN32_AVAILABLE:
            self.printer_cb['values'] = ["pywin32 tidak terinstall"]
            self.printer_cb.current(0)
            return

        try:
            printers = [p[2] for p in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)]
            if printers:
                self.printer_cb['values'] = printers
                self.printer_cb.current(0)
            else:
                self.printer_cb['values'] = ["Tidak ada printer terdeteksi"]
                self.printer_cb.current(0)
        except Exception as e:
            self.printer_cb['values'] = [f"Error enum printer: {e}"]
            self.printer_cb.current(0)

    def do_print(self):
        if not PYWIN32_AVAILABLE:
            messagebox.showerror("Error", "Library 'pywin32' belum terinstall.")
            return

        printer_name = self.printer_cb.get()
        if not printer_name or "Error" in printer_name or "Tidak ada" in printer_name:
            messagebox.showwarning("Peringatan", "Pilih printer yang valid terlebih dahulu!")
            return

        code = self.entries["code_entry"].get().strip()
        order_no = self.entries["order_no_entry"].get().strip()
        customer = self.entries["customer_entry"].get().strip()
        part_code = self.entries["part_code_entry"].get().strip()
        batt_type = self.entries["batt_type_entry"].get().strip()
        quantity = self.entries["qty_entry"].get().strip()
        prd_shift = self.entries["prd_shift_entry"].get().strip()
        kode_prod = self.entries["kode_prod_entry"].get().strip()
        kode_prod_qty = self.entries["kode_prod_qty_entry"].get().strip()
        
        # Parse multi-code production and quantities
        prod_codes = [c.strip() for c in str(kode_prod).split(',') if c.strip()]
        prod_qtys = [q.strip() for q in str(kode_prod_qty).split(',') if q.strip()]
        
        if not prod_codes:
            prod_codes = ["-"]
            
        formatted_prod_items = []
        for idx, c_item in enumerate(prod_codes):
            q_item = prod_qtys[idx] if idx < len(prod_qtys) else (prod_qtys[0] if prod_qtys else "")
            if q_item and q_item != "-":
                formatted_prod_items.append(f"{c_item} - {q_item} pcs")
            else:
                formatted_prod_items.append(c_item)
            
        prod_tspl = f'TEXT 25,294,"0",0,8,8,"Kode Prod"\nTEXT 140,294,"0",0,8,8,": {formatted_prod_items[0]}"'
        if len(formatted_prod_items) > 1:
            prod_tspl += f'\nTEXT 140,322,"0",0,8,8,"  {formatted_prod_items[1]}"'

        # TSPL Command Pallet (70mm x 50mm) - 1.2cm Top Margin Y=95, Font 8,8 (SAME AS MASTERBOX!)
        tspl_command = f"""SIZE 70 mm, 50 mm
GAP 2 mm, 0 mm
DIRECTION 1
CLS
QRCODE 25,95,H,3,A,0,M2,S7,"{code}"
TEXT 160,95,"0",0,8,8,"{code}"
TEXT 160,123,"0",0,8,8,"Order No."
TEXT 250,123,"0",0,8,8,": {order_no}"
TEXT 160,151,"0",0,8,8,"Customer"
TEXT 250,151,"0",0,8,8,": {customer}"
TEXT 160,179,"0",0,8,8,"Part Code"
TEXT 250,179,"0",0,8,8,": {part_code}"
TEXT 25,210,"0",0,8,8,"Batt. Type"
TEXT 140,210,"0",0,8,8,": {batt_type}"
TEXT 25,238,"0",0,8,8,"Quantity"
TEXT 140,238,"0",0,8,8,": {quantity}"
TEXT 25,266,"0",0,8,8,"Prd/Shift/Mc"
TEXT 140,266,"0",0,8,8,": {prd_shift}"
{prod_tspl}
PRINT 1
"""
        try:
            hPrinter = win32print.OpenPrinter(printer_name)
            try:
                hJob = win32print.StartDocPrinter(hPrinter, 1, ("Test Print Pallet Label", None, "RAW"))
                try:
                    win32print.StartPagePrinter(hPrinter)
                    win32print.WritePrinter(hPrinter, tspl_command.encode('utf-8'))
                    win32print.EndPagePrinter(hPrinter)
                    messagebox.showinfo("Sukses", f"Label Pallet sukses dikirim ke printer: {printer_name}")
                finally:
                    win32print.EndDocPrinter(hPrinter)
            finally:
                win32print.ClosePrinter(hPrinter)
        except Exception as e:
            messagebox.showerror("Error Print", f"Gagal mengirim ke printer:\n{e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = PalletPrintTestApp(root)
    root.mainloop()
