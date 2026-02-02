import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
import os
import subprocess
import threading
import sys
from datetime import datetime

# =============================================================================
# 🚀 API Bot Launcher (High Performance)
# =============================================================================
#
# [설명]
# 새로운 API(Requests) 기반 봇들을 위한 전용 런처입니다.
# 기존 Selenium 런처보다 가볍고, API 봇의 빠른 속도에 맞춰진 설정을 제공합니다.
#
# [지원 봇]
# - 장현호 (더피싱/장현호_Bot - 복사본.py)
#
# =============================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(BASE_DIR, "config")
BOTS_DIR = os.path.join(BASE_DIR, "bots")
LAUNCHER_CONFIG_FILE = os.path.join(CONFIG_DIR, "api_launcher_config.json")

# 봇 목록 (표시이름: 상대경로)
AVAILABLE_BOTS = {
    "장현호 (API)": "더피싱/장현호_Bot - 복사본.py"
}

class ApiBotLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("⚡ API Fishing Bot Launcher (Pro)")
        self.root.geometry("800x650")
        
        self.center_window(800, 650)
        
        # Style
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Variables
        self.slots = []
        self.processes = []
        
        self.create_widgets()
        self.load_config()
        
    def center_window(self, width, height):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def create_widgets(self):
        # 1. Global Settings Frame
        lf_global = ttk.LabelFrame(self.root, text="⚙️ 전역 설정 (Global Settings)", padding=10)
        lf_global.pack(fill="x", padx=10, pady=5)
        
        # Target Time
        f_time = ttk.Frame(lf_global)
        f_time.pack(fill="x", pady=2)
        ttk.Label(f_time, text="⏰ 타겟 시간:").pack(side="left")
        
        self.ent_hour = ttk.Entry(f_time, width=3, justify="center")
        self.ent_hour.insert(0, "00")
        self.ent_hour.pack(side="left")
        ttk.Label(f_time, text=":").pack(side="left")
        
        self.ent_min = ttk.Entry(f_time, width=3, justify="center")
        self.ent_min.insert(0, "00")
        self.ent_min.pack(side="left")
        ttk.Label(f_time, text=":").pack(side="left")
        
        self.ent_sec = ttk.Entry(f_time, width=5, justify="center")
        self.ent_sec.insert(0, "00.0")
        self.ent_sec.pack(side="left")
        
        # Options
        self.var_test_mode = tk.BooleanVar(value=False)
        ttk.Checkbutton(f_time, text="🧪 테스트 모드 (전송 생략)", variable=self.var_test_mode).pack(side="left", padx=20)
        
        # 2. Slot Container (Scrollable if needed, but simple for now)
        self.lf_slots = ttk.LabelFrame(self.root, text="📅 예약 슬롯 (Registration Slots)", padding=10)
        self.lf_slots.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Control Buttons for Slots
        f_slot_ctrl = ttk.Frame(self.lf_slots)
        f_slot_ctrl.pack(fill="x", pady=(0, 5))
        ttk.Button(f_slot_ctrl, text="➕ 슬롯 추가", command=self.add_slot).pack(side="left")
        ttk.Button(f_slot_ctrl, text="➖ 마지막 제거", command=self.remove_slot).pack(side="left", padx=5)
        ttk.Button(f_slot_ctrl, text="📝 예시 정보 채우기", command=self.fill_example).pack(side="left", padx=5)
        
        # Canvas/Frame for Scrollable Slots (Simple pack used here for simplicity as API users usually have few slots)
        self.f_slot_list = ttk.Frame(self.lf_slots)
        self.f_slot_list.pack(fill="both", expand=True)

        # 3. Action & Logs
        lf_action = ttk.LabelFrame(self.root, text="🚀 실행 및 로그 (Execution & Logs)", padding=10)
        lf_action.pack(fill="both", expand=True, padx=10, pady=5)
        
        f_btns = ttk.Frame(lf_action)
        f_btns.pack(fill="x", pady=(0, 5))
        
        btn_start = ttk.Button(f_btns, text="🔥 ALL START (F2)", command=self.start_all)
        btn_start.pack(side="left", fill="x", expand=True, padx=5)
        
        btn_stop = ttk.Button(f_btns, text="🛑 STOP ALL (F3)", command=self.stop_all)
        btn_stop.pack(side="left", fill="x", expand=True, padx=5)
        
        # Log Console
        self.console = scrolledtext.ScrolledText(lf_action, height=10, state="disabled", bg="black", fg="lime", font=("Consolas", 10))
        self.console.pack(fill="both", expand=True)

        # Bind Keys
        self.root.bind('<F2>', lambda e: self.start_all())
        self.root.bind('<F3>', lambda e: self.stop_all())
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def add_slot(self):
        idx = len(self.slots)
        f_item = ttk.Frame(self.f_slot_list, relief="groove", borderwidth=2)
        f_item.pack(fill="x", pady=2, padx=2)
        
        # Header (Slot #)
        ttk.Label(f_item, text=f"#{idx+1}", font=("Arial", 10, "bold")).pack(side="left", padx=5)
        
        # Bot Select
        ttk.Label(f_item, text="Bot:").pack(side="left")
        cb_bot = ttk.Combobox(f_item, values=list(AVAILABLE_BOTS.keys()), state="readonly", width=15)
        if AVAILABLE_BOTS: cb_bot.current(0)
        cb_bot.pack(side="left", padx=2)
        
        # Date
        ttk.Label(f_item, text="날짜(YYYYMMDD):").pack(side="left")
        ent_date = ttk.Entry(f_item, width=10, justify="center")
        ent_date.insert(0, "20261001")
        ent_date.pack(side="left", padx=2)
        
        # User Info
        ttk.Label(f_item, text="이름:").pack(side="left")
        ent_name = ttk.Entry(f_item, width=6, justify="center")
        ent_name.pack(side="left", padx=2)
        
        ttk.Label(f_item, text="전화:").pack(side="left")
        ent_phone = ttk.Entry(f_item, width=13, justify="center")
        ent_phone.insert(0, "010-")
        ent_phone.pack(side="left", padx=2)
        
        ttk.Label(f_item, text="인원:").pack(side="left")
        cb_person = ttk.Combobox(f_item, values=["1", "2", "3", "4", "5"], width=3, state="readonly")
        cb_person.current(0)
        cb_person.pack(side="left", padx=2)
        
        slot_data = {
            "frame": f_item,
            "bot": cb_bot,
            "date": ent_date,
            "name": ent_name,
            "phone": ent_phone,
            "person": cb_person
        }
        self.slots.append(slot_data)
        
    def remove_slot(self):
        if not self.slots: return
        slot = self.slots.pop()
        slot["frame"].destroy()
        
    def fill_example(self):
        if not self.slots: self.add_slot()
        slot = self.slots[0]
        slot['name'].delete(0, tk.END); slot['name'].insert(0, "김선재")
        slot['phone'].delete(0, tk.END); slot['phone'].insert(0, "010-1234-5678")
        
    def log(self, msg):
        timestamp = datetime.now().strftime("[%H:%M:%S]")
        full_msg = f"{timestamp} {msg}\n"
        self.console.config(state="normal")
        self.console.insert(tk.END, full_msg)
        self.console.see(tk.END)
        self.console.config(state="disabled")

    def run_bot_process(self, script_path, config_file):
        try:
            # Creation flags to hide console window
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            cmd = [sys.executable, script_path, config_file]
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startupinfo=startupinfo,
                text=True,
                encoding='utf-8', 
                bufsize=1,            # Line buffered
                universal_newlines=True
            )
            self.processes.append(process)
            
            # Thread to read stdout
            def read_output(proc):
                for line in iter(proc.stdout.readline, ''):
                    if line:
                        self.root.after(0, lambda l=line: self.log(l.strip()))
                proc.stdout.close()
                
            t = threading.Thread(target=read_output, args=(process,), daemon=True)
            t.start()
            
            # Thread to wait execution
            def wait_proc(proc):
                proc.wait()
                self.root.after(0, lambda: self.log(f"🏁 프로세스 종료 (Code: {proc.returncode})"))
                if proc in self.processes:
                    self.processes.remove(proc)
                    
            t2 = threading.Thread(target=wait_proc, args=(process,), daemon=True)
            t2.start()
            
        except Exception as e:
            self.log(f"❌ 실행 에러: {e}")

    def start_all(self):
        self.save_config()
        self.log("🚀 Start All Bots...")
        
        target_time = f"{self.ent_hour.get()}:{self.ent_min.get()}:{self.ent_sec.get()}"
        is_test = self.var_test_mode.get()
        
        for i, slot in enumerate(self.slots):
            bot_name = slot['bot'].get()
            script_rel = AVAILABLE_BOTS.get(bot_name)
            if not script_rel: continue
            
            script_path = os.path.join(BOTS_DIR, script_rel)
            if not os.path.exists(script_path):
                self.log(f"❌ 파일 없음: {script_path}")
                continue
                
            # Create Temp Config for this slot
            config_data = {
                "target_time": target_time,
                "simulation_mode": is_test, # Mapping to dry_run logic
                "multi_instance": [{
                    "date": slot['date'].get(),
                    "person_count": slot['person'].get(),
                    "user_name": slot['name'].get(),
                    "user_phone": slot['phone'].get()
                }]
            }
            
            # Save Temp Config
            tmp_cfg_path = os.path.join(CONFIG_DIR, f"temp_api_config_{i}.json")
            with open(tmp_cfg_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, ensure_ascii=False, indent=4)
                
            self.log(f"▶️ Slot #{i+1} : {bot_name} 실행 -> ({tmp_cfg_path})")
            self.run_bot_process(script_path, tmp_cfg_path)

    def stop_all(self):
        self.log("🛑 Stop All Requests...")
        for p in self.processes:
            p.terminate()
        self.processes.clear()

    def save_config(self):
        if not os.path.exists(CONFIG_DIR): os.makedirs(CONFIG_DIR)
        
        data = {
            "target_hour": self.ent_hour.get(),
            "target_min": self.ent_min.get(),
            "target_sec": self.ent_sec.get(),
            "test_mode": self.var_test_mode.get(),
            "slots": []
        }
        
        for slot in self.slots:
            data["slots"].append({
                "bot": slot['bot'].get(),
                "date": slot['date'].get(),
                "name": slot['name'].get(),
                "phone": slot['phone'].get(),
                "person": slot['person'].get()
            })
            
        with open(LAUNCHER_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print("Config Saved.")

    def load_config(self):
        if not os.path.exists(LAUNCHER_CONFIG_FILE):
            self.add_slot() # Default 1
            return
            
        try:
            with open(LAUNCHER_CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            self.ent_hour.delete(0, tk.END); self.ent_hour.insert(0, data.get("target_hour", "00"))
            self.ent_min.delete(0, tk.END); self.ent_min.insert(0, data.get("target_min", "00"))
            self.ent_sec.delete(0, tk.END); self.ent_sec.insert(0, data.get("target_sec", "00.0"))
            self.var_test_mode.set(data.get("test_mode", False))
            
            for s_data in data.get("slots", []):
                self.add_slot()
                slot = self.slots[-1]
                slot['bot'].set(s_data.get("bot", ""))
                slot['date'].delete(0, tk.END); slot['date'].insert(0, s_data.get("date", ""))
                slot['name'].delete(0, tk.END); slot['name'].insert(0, s_data.get("name", ""))
                slot['phone'].delete(0, tk.END); slot['phone'].insert(0, s_data.get("phone", ""))
                slot['person'].set(s_data.get("person", "1"))
                
            if not self.slots: self.add_slot()
            
        except Exception as e:
            print(f"Config Load Error: {e}")
            self.add_slot()

    def on_close(self):
        self.save_config()
        self.stop_all()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ApiBotLauncher(root)
    root.mainloop()
