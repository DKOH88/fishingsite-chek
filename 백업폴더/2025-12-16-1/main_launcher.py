import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import subprocess
from datetime import datetime

# Configuration
CONFIG_DIR = "config"
LAUNCHER_STATE_FILE = os.path.join(CONFIG_DIR, "launcher_state.json")
BOTS_DIR = "bots"

# Data Structure: Port -> { ProviderName: ScriptName }
PORTS = {
    "오천항": {
        "가즈아호": "가즈아호_Bot.py", "금땡이호": "금땡이호_Bot.py", "꽃돼지호": None, "나폴리(신조선)": None, 
        "나폴리2": None, "나폴리7": None, "뉴나폴리": None, "빅보스호": "빅보스호_Bot.py", 
        "싸부호": None, "오디세이호": None, "자이언트호": None, "카즈미호": None, 
        "팀바이트호": None, "프랜드호": None, "프린스호": "프린스호_Bot.py", "호랭이호": None
    },
    "삼길포항": {
        "골드피싱호": None, "넘버원호": None, "뉴항구호": None, "만석호": None, 
        "승주호": None, "헌터호": None, "헤르메스호": None
    },
    "안흥·신진·모항항": {
        "골드피싱호": None, "낭만어부호": None, "뉴신정호": None, "루디호": None, 
        "마그마호": None, "미라클호": None, "부흥호": None, "블레스호": None, 
        "여명호": "여명호_Bot.py", "지도호": None, "청용호": None, 
        "퀸블레스호": None, "킹스타호": None, "행운호": None
    },
    "마검포항": {
        "가가호": None, "천일호": None, "청광호": None, "청남호": None, "하와이호": None
    },
    "대천항": {
        "기가호": None, "까칠이호": None, "뉴아인스호": None, "아인스호": None, 
        "야야호": None, "팀 야크호": None, "팀루피호": None
    },
    "무창포항": {
        "깜보호": None, "뉴체스호": None, "헤라호": None
    },
    "영흥항": {
        "god호": None, "아라호": None
    },
    "여수": {}
}

class FishingLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("🎣 2026 낚시 예약 봇 통합 런처")
        self.root.geometry("650x800")
        
        self.current_provider = None
        self.entries = {}
        
        self.create_widgets()
        self.load_last_selection()

    def create_widgets(self):
        # 1. Port & Provider Selection
        lf_select = ttk.LabelFrame(self.root, text="🚢 선사 선택", padding=10)
        lf_select.pack(fill="x", padx=10, pady=5)
        
        # Port
        ttk.Label(lf_select, text="항구:").grid(row=0, column=0, sticky="e", padx=5)
        self.combo_port = ttk.Combobox(lf_select, state="readonly", values=list(PORTS.keys()), width=15)
        self.combo_port.grid(row=0, column=1, sticky="w", padx=5)
        self.combo_port.bind("<<ComboboxSelected>>", self.on_port_change)
        
        # Provider
        ttk.Label(lf_select, text="선사:").grid(row=0, column=2, sticky="e", padx=5)
        self.combo_provider = ttk.Combobox(lf_select, state="readonly", width=25)
        self.combo_provider.grid(row=0, column=3, sticky="w", padx=5)
        self.combo_provider.bind("<<ComboboxSelected>>", self.on_provider_change)
        
        # 2. Configuration Form
        self.lf_config = ttk.LabelFrame(self.root, text="⚙️ 예약 설정", padding=10)
        self.lf_config.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Name
        ttk.Label(self.lf_config, text="예약자 이름").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.entry_name = ttk.Entry(self.lf_config, width=20)
        self.entry_name.insert(0, "DK")
        self.entry_name.grid(row=0, column=1, sticky="w", padx=5)

        # Depositor Name
        ttk.Label(self.lf_config, text="입금자명").grid(row=0, column=2, sticky="e", padx=5, pady=5)
        self.entry_depositor = ttk.Entry(self.lf_config, width=20)
        self.entry_depositor.insert(0, "DK")
        self.entry_depositor.grid(row=0, column=3, sticky="w", padx=5)
        
        # Phone
        ttk.Label(self.lf_config, text="휴대폰 번호").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.entry_phone = ttk.Entry(self.lf_config, width=20)
        self.entry_phone.insert(0, "010-2345-6149")
        self.entry_phone.grid(row=1, column=1, sticky="w", padx=5)
        
        # Target Date (Dropdowns)
        # Target Date (Multi-Instance Slots)
        ttk.Label(self.lf_config, text="예약 날짜 (다중 실행)").grid(row=2, column=0, sticky="ne", padx=5, pady=5)
        
        frame_slots = ttk.Frame(self.lf_config)
        frame_slots.grid(row=2, column=1, sticky="w", padx=5)
        
        self.slots = []
        for i in range(4):
            f_slot = ttk.Frame(frame_slots)
            f_slot.pack(fill="x", pady=2)
            
            # Checkbox
            var_enable = tk.BooleanVar(value=(i==0))
            chk = ttk.Checkbutton(f_slot, text=f"Slot {i+1}", variable=var_enable)
            chk.pack(side="left", padx=2)
            
            # Date
            cb_year = ttk.Combobox(f_slot, values=["2025", "2026"], width=5, state="readonly")
            cb_year.set("2026")
            cb_year.pack(side="left")
            ttk.Label(f_slot, text="년").pack(side="left")
            
            cb_month = ttk.Combobox(f_slot, values=[f"{i:02d}" for i in range(1, 13)], width=3, state="readonly")
            cb_month.set("09")
            cb_month.pack(side="left")
            ttk.Label(f_slot, text="월").pack(side="left")
            
            cb_day = ttk.Combobox(f_slot, values=[f"{i:02d}" for i in range(1, 32)], width=3, state="readonly")
            cb_day.set("01")
            cb_day.pack(side="left")
            ttk.Label(f_slot, text="일").pack(side="left", padx=(0, 10))

            # Person Count (Per Slot)
            ttk.Label(f_slot, text="인원:").pack(side="left")
            cb_person = ttk.Combobox(f_slot, values=[str(p) for p in range(1, 6)], width=3, state="readonly")
            cb_person.set("1")
            cb_person.pack(side="left")
            ttk.Label(f_slot, text="명").pack(side="left")
            
            self.slots.append({
                "enable": var_enable,
                "year": cb_year,
                "month": cb_month,
                "day": cb_day,
                "person": cb_person
            })

        # Target Time (Dropdowns)
        ttk.Label(self.lf_config, text="실행 시간").grid(row=3, column=0, sticky="e", padx=5, pady=5)
        frame_time = ttk.Frame(self.lf_config)
        frame_time.grid(row=3, column=1, sticky="w", padx=5)
        
        self.cb_hour = ttk.Combobox(frame_time, values=[f"{i:02d}" for i in range(24)], width=3, state="readonly")
        self.cb_hour.set("09")
        self.cb_hour.pack(side="left")
        ttk.Label(frame_time, text="시").pack(side="left")
        
        self.cb_min = ttk.Combobox(frame_time, values=[f"{i:02d}" for i in range(60)], width=3, state="readonly")
        self.cb_min.set("00")
        self.cb_min.pack(side="left")
        ttk.Label(frame_time, text="분").pack(side="left")
        
        self.cb_sec = ttk.Combobox(frame_time, values=[f"{i:02d}" for i in range(60)], width=3, state="readonly")
        self.cb_sec.set("00")
        self.cb_sec.pack(side="left")
        ttk.Label(frame_time, text="초").pack(side="left")

        # Target Ship
        ttk.Label(self.lf_config, text="대상 선박 (선택)").grid(row=4, column=0, sticky="e", padx=5, pady=5)
        self.entry_ship = ttk.Entry(self.lf_config, width=20)
        self.entry_ship.grid(row=4, column=1, sticky="w", padx=5)

        # Person Count - Global Removed
        # ttk.Label(self.lf_config, text="예약 인원").grid(row=5, column=0, sticky="e", padx=5, pady=5)
        # self.cb_person = ... (Moved to slots)

        # Test Mode
        self.var_test_mode = tk.BooleanVar()
        ttk.Checkbutton(self.lf_config, text="🚀 Test Mode (시간 무시/즉시 실행)", variable=self.var_test_mode).grid(row=6, column=1, sticky="w", padx=5, pady=5)

        # Simulation Mode
        self.var_sim_mode = tk.BooleanVar()
        ttk.Checkbutton(self.lf_config, text="🚫 예약 실행 안함 (시뮬레이션 모드)", variable=self.var_sim_mode).grid(row=7, column=1, sticky="w", padx=5, pady=5)

        # Save Button
        ttk.Button(self.lf_config, text="💾 설정 저장", command=self.save_config).grid(row=99, column=1, sticky="e", pady=10)

        # 3. Execution
        lf_action = ttk.LabelFrame(self.root, text="🚀 실행 제어", padding=10)
        lf_action.pack(fill="x", padx=10, pady=10)
        
        ttk.Button(lf_action, text="🔥 봇 실행 (Start)", command=self.start_bot).pack(fill="x", pady=5)
        
        
        # Init
        # self.combo_port.current(0)
        # self.on_port_change(None)

    def save_last_selection(self):
        """Save current Port and Provider to state file"""
        port = self.combo_port.get()
        provider = self.combo_provider.get()
        if not port or not provider: return
        
        data = {
            "last_port": port,
            "last_provider": provider
        }
        
        if not os.path.exists(CONFIG_DIR):
            os.makedirs(CONFIG_DIR)
            
        with open(LAUNCHER_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def load_last_selection(self):
        """Load last selected Port and Provider, or default"""
        try:
            if os.path.exists(LAUNCHER_STATE_FILE):
                with open(LAUNCHER_STATE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    last_port = data.get("last_port")
                    last_provider = data.get("last_provider")
                    
                    if last_port in PORTS:
                        self.combo_port.set(last_port)
                        self.on_port_change(None) # Load providers for this port
                        
                        # Check if last provider is valid for this port
                        valid_providers = PORTS[last_port].keys()
                        if last_provider in valid_providers:
                            self.combo_provider.set(last_provider)
                            self.on_provider_change(None) # Load config for this provider
                            return

        except Exception as e:
            print(f"Failed to load last state: {e}")
            
        # Default Fallback
        if not self.combo_port.get():
            self.combo_port.current(0)
            self.on_port_change(None)

    def on_port_change(self, event):
        port = self.combo_port.get()
        providers = list(PORTS.get(port, {}).keys())
        self.combo_provider['values'] = providers
        if providers:
            self.combo_provider.current(0)
            self.on_provider_change(None)
        else:
            self.combo_provider.set('')
            self.current_provider = None

    def on_provider_change(self, event):
        self.current_provider = self.combo_provider.get()
        self.load_config(self.current_provider)
        self.save_last_selection()
        
    def get_config_path(self, provider_name):
        safe_name = provider_name.replace(" ", "_").replace("(", "").replace(")", "")
        return os.path.join(CONFIG_DIR, f"{safe_name}.json")

    def load_config(self, provider_name):
        path = self.get_config_path(provider_name)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.entry_name.delete(0, tk.END)
                    self.entry_name.insert(0, data.get('user_name', 'DK'))
                    self.entry_depositor.delete(0, tk.END)
                    self.entry_depositor.insert(0, data.get('user_depositor', 'DK'))
                    self.entry_phone.delete(0, tk.END)
                    self.entry_phone.insert(0, data.get('user_phone', '010-2345-6149'))
                    self.entry_ship.delete(0, tk.END)
                    self.entry_ship.insert(0, data.get('target_ship', ''))
                    self.cb_person.set(data.get('person_count', '1'))
                    self.var_test_mode.set(data.get('test_mode', False))
                    self.var_sim_mode.set(data.get('simulation_mode', False))
                    
                    
                    # Date (Legacy & Multi-Instance)
                    legacy_date = data.get('target_date', '20260901')
                    multi_data = data.get('multi_instance', [])
                    
                    # If multi_instance exists, load it. Else load legacy to Slot 1.
                    if multi_data:
                        for i, slot_data in enumerate(multi_data):
                            if i < len(self.slots):
                                self.slots[i]["enable"].set(slot_data.get("enable", False))
                                d_str = slot_data.get("date", "20260901")
                                if len(d_str) == 8:
                                    self.slots[i]["year"].set(d_str[:4])
                                    self.slots[i]["month"].set(d_str[4:6])
                                    self.slots[i]["day"].set(d_str[6:8])
                                self.slots[i]["person"].set(slot_data.get("person_count", "1"))
                    else:
                        # Legacy fallback
                        if len(legacy_date) == 8:
                            self.slots[0]["year"].set(legacy_date[:4])
                            self.slots[0]["month"].set(legacy_date[4:6])
                            self.slots[0]["day"].set(legacy_date[6:8])
                            self.slots[0]["enable"].set(True)
                            self.slots[0]["person"].set(data.get('person_count', '1'))
                        # Disable others
                        for i in range(1, 4):
                             self.slots[i]["enable"].set(False)
                        
                    # Time
                    time_val = data.get('target_time', '09:00:00')
                    parts = time_val.split(':')
                    if len(parts) == 3:
                        self.cb_hour.set(parts[0])
                        self.cb_min.set(parts[1])
                        self.cb_sec.set(parts[2])
            except: pass

    def save_config(self, silent=False):
        if not self.current_provider: return
        
        # Build Date/Time strings & Multi Instance Data
        # Default legacy target_date is Slot 1
        t_date_legacy = f"{self.slots[0]['year'].get()}{self.slots[0]['month'].get()}{self.slots[0]['day'].get()}"
        t_time = f"{self.cb_hour.get()}:{self.cb_min.get()}:{self.cb_sec.get()}"
        
        multi_instance_data = []
        for slot in self.slots:
            d_str = f"{slot['year'].get()}{slot['month'].get()}{slot['day'].get()}"
            multi_instance_data.append({
                "enable": slot['enable'].get(),
                "date": d_str,
                "person_count": slot['person'].get()
            })
        
        data = {
            "user_name": self.entry_name.get(),
            "user_depositor": self.entry_depositor.get(),
            "user_phone": self.entry_phone.get(),
            "target_date": t_date_legacy, # Keep main key for legacy/single compatibility
            "multi_instance": multi_instance_data, # New structure
            "target_time": t_time,
            "target_ship": self.entry_ship.get(),
            "person_count": self.slots[0]['person'].get(), # Default to Slot 1 for legacy
            "test_mode": self.var_test_mode.get(),
            "simulation_mode": self.var_sim_mode.get()
        }
        
        if not os.path.exists(CONFIG_DIR):
            os.makedirs(CONFIG_DIR)
            
        path = self.get_config_path(self.current_provider)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
            
        if not silent:
            messagebox.showinfo("Success", "설정이 저장되었습니다.")

    def start_bot(self):
        if not self.current_provider: return
        self.save_config(silent=True)
        
        # Find script
        port = self.combo_port.get()
        script_name = PORTS[port].get(self.current_provider)
        
        if not script_name:
            messagebox.showerror("Error", "스크립트 정보가 없습니다.")
            return

        script_path = os.path.join(BOTS_DIR, script_name)
        base_config_path = self.get_config_path(self.current_provider)
        
        if not os.path.exists(script_path):
            messagebox.showerror("Error", f"스크립트 파일 없음:\n{script_path}")
            return
            
        # Launch Multiple Instances
        launched_count = 0
        
        # Load base config
        with open(base_config_path, 'r', encoding='utf-8') as f:
            base_data = json.load(f)
            
        multi_data = base_data.get('multi_instance', [])
        # If no multi data, create a dummy one from legacy
        if not multi_data:
             multi_data = [{"enable": True, "date": base_data.get('target_date', '20260901')}]
             
        for i, slot in enumerate(multi_data):
            if slot.get('enable'):
                # Create Temp Config for this instance
                temp_data = base_data.copy()
                temp_data['target_date'] = slot['date']
                temp_data['person_count'] = slot.get('person_count', '1')
                
                temp_config_name = f"temp_config_{self.current_provider}_{i}.json"
                temp_config_path = os.path.join(CONFIG_DIR, temp_config_name)
                
                with open(temp_config_path, 'w', encoding='utf-8') as f:
                    json.dump(temp_data, f, ensure_ascii=False, indent=4)
                
                print(f"🚀 Launching Instance {i+1}: Date {slot['date']}")
                cmd = ["python", script_path, "--config", temp_config_path]
                subprocess.Popen(cmd)
                launched_count += 1
                
        if launched_count == 0:
            messagebox.showwarning("Warning", "선택된 슬롯(체크박스)이 없습니다.")

if __name__ == "__main__":
    if not os.path.exists(CONFIG_DIR): os.makedirs(CONFIG_DIR)
    root = tk.Tk()
    app = FishingLauncher(root)
    root.mainloop()
