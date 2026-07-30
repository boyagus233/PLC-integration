\# PLC Logger (Auto Reconnect + Auto Restart Ready)



Script Python untuk membaca data dari PLC (Allen-Bradley / Logix) menggunakan `pycomm3`, kemudian:



\* Logging data ke file harian

\* Auto reconnect jika koneksi putus

\* Support auto restart via Task Scheduler

\* Error logging terpisah

\* Tampilan terminal clean (single-line status)



\---



\## 🚀 Features



\* ✅ Read multiple PLC tags

\* ✅ Event-based logging (trigger dari `Totalizer\_Box`)

\* ✅ Auto reconnect PLC

\* ✅ Auto restart support (Task Scheduler)

\* ✅ Log file harian (`logs/`)

\* ✅ Error log terpisah (`error\_log/`)

\* ✅ Clean terminal UI (tidak spam)



\---



\## 📦 Requirements



\* Python 3.8+

\* PLC Allen-Bradley (Logix / CompactLogix / ControlLogix)

\* Network connection ke PLC



\---



\## 🔧 Install Dependencies



Install package yang dibutuhkan:



```bash

pip install pycomm3

```



\---



\## 📁 Struktur Folder



Setelah dijalankan:



```

project\_folder/

│

├── logger.py

├── logs/

│   └── log\_YYYYMMDD.txt

│

└── error\_log/

&#x20;   └── error\_log.txt

```



\---



\## ▶️ Cara Menjalankan



```bash

python logger.py

```



\---



\## ⚙️ Konfigurasi



Edit di dalam script:



```python

PLC\_IP = "192.168.1.20/1"

```



Edit tag PLC:



```python

tags = \[

&#x20;   "Recent\_Weight",

&#x20;   "Product\_Weight",

&#x20;   ...

&#x20;   "Totalizer\_Box"

]

```



\---



\## 🔁 Cara Kerja



\* Script membaca data PLC secara loop

\* Jika `Totalizer\_Box` berubah → dianggap event baru

\* Data disimpan ke file log

\* Jika tidak berubah → skip (tidak log ulang)



\---



\## 🔌 Auto Reconnect



Jika koneksi PLC putus:



\* Script akan otomatis reconnect

\* Tidak perlu restart manual



\---



\## 💀 Auto Restart (Task Scheduler)



Jika terjadi error fatal:



\* Script akan exit

\* Task Scheduler akan restart otomatis



\### Setting Task Scheduler:



\* Trigger: \*\*At startup\*\*

\* ✔ Run whether user logged on or not

\* ✔ Restart if fails (1 minute / 999 times)



\---



\## 📝 Log File



Contoh isi:



```

ID: 10

Recent\_Weight: 12.5 (REAL)

Product\_Type: ABC (STRING)

...

Time: 14:32

Timestamp: 12042026 14:32:10

\----------------------------------------

```



\---



\## 🚨 Error Log



File:



```

error\_log/error\_log.txt

```



Contoh:



```

2026-04-12 14:33:01 - RUNTIME ERROR: failed to send message

```



\---



\## ⚠️ Notes (Production)



\* Disable sleep mode Windows

\* Gunakan UPS (recommended)

\* Pastikan network ke PLC stabil

\* Jalankan via Task Scheduler / Service



\---



\## 🧠 Tips



\* Gunakan `Totalizer\_Box` sebagai trigger event

\* Jangan gunakan compare semua value (karena bisa sama)

\* Gunakan counter internal untuk ID



\---



\## 📈 Future Improvements (Optional)



\* Database logging (MySQL / SQLite)

\* Web dashboard

\* Telegram / WA notification

\* Auto delete log lama



\---



\## 👨‍🔧 Author



Internal PLC Logger Tool

For Production Line Monitoring



