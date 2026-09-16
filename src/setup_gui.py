import os
import sys
import subprocess
import configparser
import tkinter as tk
from tkinter import messagebox, ttk, filedialog

def detect_initial_root_dir():
    """Mendeteksi direktori root aplikasi secara dinamis tanpa hardcode drive"""
    if getattr(sys, 'frozen', False):
        # Berjalan sebagai PyInstaller EXE
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        if os.path.exists(os.path.join(exe_dir, "config.ini")):
            return exe_dir
        parent = os.path.dirname(exe_dir)
        if os.path.exists(os.path.join(parent, "config.ini")):
            return parent
        return exe_dir
    else:
        # Berjalan sebagai skrip Python (.py)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        if os.path.basename(script_dir).lower() == 'src':
            return os.path.dirname(script_dir)
        return script_dir

SERVICE_NAME = "YuasaScannerService"

class SetupInstallerGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Yuasa Battery Indonesia - Service Setup Wizard")
        self.geometry("680x640")
        self.minsize(640, 600)
        self.configure(bg="#f8fafc")
        
        # Direktori target dinamis
        self.root_dir_var = tk.StringVar(value=detect_initial_root_dir())
        
        self.create_widgets()
        self.refresh_all()

    def get_root_dir(self):
        return os.path.abspath(self.root_dir_var.get().strip())

    def get_config_path(self):
        return os.path.join(self.get_root_dir(), "config.ini")

    def get_nssm_path(self):
        return os.path.join(self.get_root_dir(), "bin", "nssm.exe")

    def get_setup_bat_path(self):
        return os.path.join(self.get_root_dir(), "Setup.bat")

    def get_uninstall_bat_path(self):
        return os.path.join(self.get_root_dir(), "tools", "Uninstall_Service.bat")

    def create_widgets(self):
        # 1. Header
        header = tk.Frame(self, bg="#0f172a", height=75)
        header.pack(fill=tk.X, side=tk.TOP)
        header.pack_propagate(False)
        
        lbl_title = tk.Label(header, text="PT. YUASA BATTERY INDONESIA", font=("Segoe UI", 13, "bold"), fg="#ffffff", bg="#0f172a")
        lbl_title.pack(anchor=tk.W, padx=20, pady=(12, 2))
        lbl_subtitle = tk.Label(header, text="Industrial Scanner & PLC Integration - Service Installer", font=("Segoe UI", 9), fg="#94a3b8", bg="#0f172a")
        lbl_subtitle.pack(anchor=tk.W, padx=20)
        
        # 2. Main Content
        content = tk.Frame(self, bg="#f8fafc", padx=20, pady=15)
        content.pack(fill=tk.BOTH, expand=True)
        
        # Pemilihan Direktori Kerja
        lbl_loc_title = tk.Label(content, text="Direktori Kerja Aplikasi (Lokasi config.ini & service):", font=("Segoe UI", 9, "bold"), fg="#334155", bg="#f8fafc")
        lbl_loc_title.pack(anchor=tk.W)
        
        loc_frame = tk.Frame(content, bg="#f8fafc")
        loc_frame.pack(fill=tk.X, pady=(4, 12))
        
        self.ent_loc = tk.Entry(loc_frame, textvariable=self.root_dir_var, font=("Consolas", 10), bg="#ffffff", relief=tk.SOLID, bd=1)
        self.ent_loc.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4, padx=(0, 6))
        self.ent_loc.bind("<FocusOut>", lambda e: self.refresh_all())
        self.ent_loc.bind("<Return>", lambda e: self.refresh_all())
        
        btn_browse = tk.Button(loc_frame, text="📁 Browse...", font=("Segoe UI", 9, "bold"), bg="#e2e8f0", fg="#1e293b", command=self.browse_folder, relief=tk.GROOVE, padx=10, pady=2, cursor="hand2")
        btn_browse.pack(side=tk.RIGHT)
        
        # Status Service Saat Ini
        status_frame = tk.Frame(content, bg="#ffffff", bd=1, relief=tk.SOLID, padx=12, pady=10)
        status_frame.pack(fill=tk.X, pady=(0, 12))
        
        lbl_status_title = tk.Label(status_frame, text="Status Windows Service Saat Ini:", font=("Segoe UI", 9, "bold"), fg="#475569", bg="#ffffff")
        lbl_status_title.pack(anchor=tk.W)
        
        self.lbl_svc_status = tk.Label(status_frame, text="MEMERIKSA...", font=("Segoe UI", 11, "bold"), fg="#f59e0b", bg="#ffffff")
        self.lbl_svc_status.pack(anchor=tk.W, pady=(2, 0))
        
        # Ringkasan Config.ini
        cfg_frame = tk.LabelFrame(content, text=" Ringkasan Konfigurasi Saat Ini (config.ini) ", font=("Segoe UI", 9, "bold"), fg="#1e293b", bg="#ffffff", padx=12, pady=10)
        cfg_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.txt_summary = tk.Text(cfg_frame, height=7, font=("Consolas", 9), bg="#f8fafc", relief=tk.FLAT)
        self.txt_summary.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        self.txt_summary.config(state=tk.DISABLED)
        
        btn_edit_cfg = tk.Button(cfg_frame, text="📝 Buka / Edit config.ini di Notepad", font=("Segoe UI", 9, "bold"), bg="#f1f5f9", fg="#2563eb", activebackground="#e2e8f0", command=self.open_config_notepad, relief=tk.GROOVE, padx=10, pady=4, cursor="hand2")
        btn_edit_cfg.pack(anchor=tk.E)
        
        # 3. Action Buttons (Footer)
        footer = tk.Frame(self, bg="#ffffff", height=80, padx=20, pady=12, bd=1, relief=tk.RIDGE)
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        footer.pack_propagate(False)
        
        btn_uninstall = tk.Button(footer, text="🛑 Copot Service", font=("Segoe UI", 9), bg="#fee2e2", fg="#dc2626", activebackground="#fca5a5", command=self.uninstall_service, relief=tk.FLAT, padx=12, pady=6, cursor="hand2")
        btn_uninstall.pack(side=tk.LEFT)
        
        self.btn_install = tk.Button(footer, text="🚀 Pasang & Nyalakan Windows Service", font=("Segoe UI", 10, "bold"), bg="#16a34a", fg="#ffffff", activebackground="#15803d", command=self.install_and_start_service, relief=tk.FLAT, padx=18, pady=6, cursor="hand2")
        self.btn_install.pack(side=tk.RIGHT)

    def browse_folder(self):
        initial = self.get_root_dir()
        if not os.path.exists(initial):
            initial = "C:\\"
        selected = filedialog.askdirectory(initialdir=initial, title="Pilih Folder Aplikasi Yuasa (Tempat config.ini berada)")
        if selected:
            self.root_dir_var.set(os.path.abspath(selected))
            self.refresh_all()

    def refresh_all(self):
        self.load_config_summary()
        self.check_current_service_status()

    def load_config_summary(self):
        config_file = self.get_config_path()
        if not os.path.exists(config_file):
            summary = (
                f"[PERINGATAN] File config.ini tidak ditemukan di direktori:\n"
                f"{self.get_root_dir()}\n\n"
                f"Silakan klik tombol 'Browse...' untuk memilih folder yang benar!"
            )
        else:
            try:
                cfg = configparser.ConfigParser()
                cfg.read(config_file, encoding='utf-8')
                base_url = cfg.get("SYSTEM_CONFIG", "BASE_URL", fallback="-")
                sc_en = cfg.get("SCANNER_CONFIG", "ENABLE", fallback="no")
                sc_line = cfg.get("SCANNER_CONFIG", "LINE_NO", fallback="-")
                sc_port = cfg.get("SCANNER_CONFIG", "PORT_SCANNER", fallback="-")
                bc_en = cfg.get("BATTERY_COUNTER_CONFIG", "ENABLE", fallback="no")
                bc_ip = cfg.get("BATTERY_COUNTER_CONFIG", "PLC_IP", fallback="-")
                bc_tag = cfg.get("BATTERY_COUNTER_CONFIG", "COUNTER_TAG", fallback="-")
                jop_en = cfg.get("CHANGE_JOP_CONFIG", "ENABLE", fallback="no")
                jop_ip = cfg.get("CHANGE_JOP_CONFIG", "PLC_IP", fallback="-")
                jop_tag = cfg.get("CHANGE_JOP_CONFIG", "BUTTON_TAG", fallback="-")
                
                summary = (
                    f"• File Path     : {config_file}\n"
                    f"• Backend URL   : {base_url}\n"
                    f"• Scanner Barcode: ENABLE={sc_en} | Line: {sc_line} | Port: {sc_port}\n"
                    f"• Battery Counter: ENABLE={bc_en} | PLC IP: {bc_ip} | Tag: {bc_tag}\n"
                    f"• Tombol Ubah JOP: ENABLE={jop_en} | PLC IP: {jop_ip} | Tag: {jop_tag}\n"
                    f"• Masterbox Auto : ENABLE={cfg.get('TIMBANGAN_CONFIG', 'ENABLE', fallback='no')} | PLC: {cfg.get('TIMBANGAN_CONFIG', 'PLC_IP', fallback='-')}\n"
                    f"• Pallet Print   : ENABLE={cfg.get('PRINTER_CONFIG', 'ENABLE', fallback='no')} | Printer: {cfg.get('PRINTER_CONFIG', 'PRINTER_NAME', fallback='-')}"
                )
            except Exception as e:
                summary = f"Error membaca config: {e}"
                
        self.txt_summary.config(state=tk.NORMAL)
        self.txt_summary.delete("1.0", tk.END)
        self.txt_summary.insert(tk.END, summary)
        self.txt_summary.config(state=tk.DISABLED)

    def check_current_service_status(self):
        nssm_exe = self.get_nssm_path()
        if not os.path.exists(nssm_exe):
            self.lbl_svc_status.config(text=f"nssm.exe TIDAK DITEMUKAN di {nssm_exe}!", fg="#dc2626")
            return
            
        try:
            res = subprocess.run([nssm_exe, "status", SERVICE_NAME], capture_output=True, text=True, timeout=3)
            status_text = res.stdout.strip()
            if "SERVICE_RUNNING" in status_text:
                self.lbl_svc_status.config(text="✅ SERVICE SEDANG BERJALAN (RUNNING)", fg="#16a34a")
                self.btn_install.config(text="🔄 Restart / Update Service")
            elif "SERVICE_STOPPED" in status_text or "SERVICE_PAUSED" in status_text:
                self.lbl_svc_status.config(text="⏸ SERVICE TERPASANG TAPI STOPPED", fg="#f59e0b")
                self.btn_install.config(text="🚀 Nyalakan Windows Service")
            else:
                self.lbl_svc_status.config(text="❌ BELUM TERPASANG (NOT INSTALLED)", fg="#64748b")
                self.btn_install.config(text="🚀 Pasang & Nyalakan Windows Service")
        except Exception:
            self.lbl_svc_status.config(text="❌ BELUM TERPASANG (NOT INSTALLED)", fg="#64748b")

    def open_config_notepad(self):
        config_file = self.get_config_path()
        if os.path.exists(config_file):
            subprocess.Popen(["notepad.exe", config_file])
            messagebox.showinfo("Petunjuk Edit Config", f"File config.ini telah dibuka di Notepad:\n{config_file}\n\nSetelah selesai mengubah dan menekan Save di Notepad:\nSilakan klik tombol 'Pasang / Update Service' agar perubahan aktif.")
            self.after(2000, self.load_config_summary)
        else:
            messagebox.showerror("Error", f"File config.ini tidak ditemukan di:\n{config_file}\n\nSilakan periksa folder yang dipilih!")

    def install_and_start_service(self):
        root_dir = self.get_root_dir()
        setup_bat = self.get_setup_bat_path()
        if not os.path.exists(setup_bat):
            messagebox.showerror("Error", f"Setup.bat tidak ditemukan di:\n{setup_bat}\n\nPastikan folder aplikasi lengkap!")
            return
            
        try:
            cmd = f'powershell -Command "Start-Process cmd -ArgumentList \'/c \"\"{setup_bat}\"\"\' -WorkingDirectory \"\"{root_dir}\"\" -Verb RunAs -Wait"'
            subprocess.run(cmd, shell=True)
            self.refresh_all()
            messagebox.showinfo("Instalasi Selesai", f"Proses setup Windows Service telah selesai untuk folder:\n{root_dir}\n\n1. Service sudah berjalan di background 24/7.\n2. Shortcut pengelolaan sudah tersedia di Desktop.")
        except Exception as e:
            messagebox.showerror("Error", f"Gagal menjalankan installer: {e}")

    def uninstall_service(self):
        root_dir = self.get_root_dir()
        if messagebox.askyesno("Konfirmasi", "Apakah Anda yakin ingin mencopot YuasaScannerService dari Windows?"):
            uninstall_bat = self.get_uninstall_bat_path()
            if not os.path.exists(uninstall_bat):
                messagebox.showerror("Error", f"Uninstall_Service.bat tidak ditemukan di:\n{uninstall_bat}")
                return
            try:
                cmd = f'powershell -Command "Start-Process cmd -ArgumentList \'/c \"\"{uninstall_bat}\"\"\' -WorkingDirectory \"\"{root_dir}\"\" -Verb RunAs -Wait"'
                subprocess.run(cmd, shell=True)
                self.refresh_all()
                messagebox.showinfo("Selesai", "Service telah berhasil dicopot.")
            except Exception as e:
                messagebox.showerror("Error", f"Gagal mencopot service: {e}")

if __name__ == "__main__":
    app = SetupInstallerGUI()
    app.mainloop()
