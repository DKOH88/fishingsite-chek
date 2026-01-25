import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import subprocess
from datetime import datetime
from PIL import Image, ImageTk # 📝 [추가] 이미지 표시를 위한 라이브러리

# Configuration
# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(BASE_DIR, "config")
LAUNCHER_STATE_FILE = os.path.join(CONFIG_DIR, "launcher_state.json")
BOTS_DIR = os.path.join(BASE_DIR, "bots")

# Data Structure: Port -> { ProviderName: ScriptName }
# 항구 정렬: 선사 수 내림차순
PORTS = {
    "오천항": {  # 17개
        "가즈아호": "선상24/가즈아호_Bot.py",
        "❌ 금땡이호": "더피싱/금땡이호_Bot.py",
        "꽃돼지호": None,
        "❌ 나폴리호": "더피싱/나폴리호_Bot.py",
        "뉴찬스호(선)": "더피싱/뉴찬스호_Bot.py",
        "❌ 도지호": "선상24/도지호_Bot.py",
        "❌ 블루호": "더피싱/블루호_Bot.py",
        "빅보스호": "선상24/빅보스호_Bot.py", 
        "샤크호": "더피싱/샤크호_Bot.py",
        "싸부호": None,
        "어쩌다어부호(선)": "선상24/어쩌다어부호_Bot.py",
        "❌ 오디세이호": "더피싱/오디세이호_Bot.py", 
        "유진호": "더피싱/유진호_Bot.py",
        "❌ 자이언트호": "선상24/자이언트호_Bot.py",
        "❌ 카즈미호": "더피싱/카즈미호_Bot.py", 
        "프랜드호": "더피싱/프랜드호_Bot.py", 
        "프린스호": "선상24/프린스호_Bot.py", 
        "호랭이호": "선상24/호랭이호_Bot.py",
        "범블비호": "더피싱/범블비호_Bot.py"
    },
    "안흥·신진항": {  # 15개
        "골드피싱호": "더피싱/안흥골드피싱호_Bot.py", 
        "낭만어부호": None, 
        "뉴신정호": "더피싱/뉴신정호_Bot.py", 
        "루디호": "더피싱/루디호_Bot.py", 
        "마그마호": "더피싱/마그마호_Bot.py", 
        "미라클호": "더피싱/미라클호_Bot.py", 
        "부흥호": "더피싱/부흥호_Bot.py", 
        "블레스호": None, 
        "솔티가호": "더피싱/솔티가호_Bot.py",
        "여명호": "더피싱/여명호_Bot.py", 
        "지도호": None, 
        "청용호": "더피싱/청용호_Bot.py", 
        "킹스타호": None, 
        "퀸블레스호": "더피싱/퀸블레스호_Bot.py", 
        "행운호": "더피싱/행운호_Bot.py"
    },
    "영흥도": {  # 12개
        "❌ god호(선)": "더피싱/지오디호_Bot.py", 
        "루키나호(선)": "선상24/루키나호_Bot.py",
        "루키나 2호(선)": "선상24/루키나 2호_Bot.py",
        "❌ 스타피싱호(선)": "더피싱/스타피싱호_Bot.py", 
        "❌ 아라호(선)": "더피싱/아라호_Bot.py", 
        "❌ 아이리스호(선)": "더피싱/아이리스호_Bot.py", 
        "야호(선)": "더피싱/야호_Bot.py", 
        "짱구호(선)": "더피싱/짱구호_Bot.py", 
        "팀만수호(선)": "더피싱/팀만수호_Bot.py", 
        "팀에프원호(선)": "선상24/팀에프원호_Bot.py", 
        "팀에프투호(선)": "선상24/팀에프투호_Bot.py",
        "페라리호(선)": "더피싱/페라리호_Bot.py"
    },
    "삼길포항": {  # 9개
        "골드피싱호(선)": "더피싱/골드피싱호_Bot.py", 
        "넘버원호(선)": "선상24/넘버원호_Bot.py", 
        "뉴항구호(선)": "선상24/뉴항구호_Bot.py", 
        "만석호(선)": "더피싱/만석호_Bot.py", 
        "승주호(선)": "더피싱/승주호_Bot.py", 
        "으리호(선)": "더피싱/으리호_Bot.py",
        "천마호(선)": "선상24/천마호_Bot.py", 
        "헌터호(선)": "더피싱/헌터호_Bot.py", 
        "헤르메스호(선)": "더피싱/헤르메스호_Bot.py"
    },
    "대천항": {  # 7개
        "기가호": "선상24/기가호_Bot.py", 
        "아이언호": "선상24/아이언호_Bot.py",
        "까칠이호": "더피싱/까칠이호_Bot.py", 
        "아인스호": "더피싱/아인스호_Bot.py", 
        "야야호": "더피싱/야야호_Bot.py", 
        "예린호(선)": "더피싱/예린호_Bot.py",
        "팀루피호": "더피싱/팀루피호_Bot.py"
    },
    "마검포항": {  # 4개
        "❌ 가가호": "선상24/가가호_Bot.py",
        "❌ 천일호": "더피싱/천일호_Bot.py", 
        "팀바이트호": "더피싱/팀바이트호_Bot.py", 
        "하와이호(선)": "더피싱/하와이호_Bot.py"
    },
    "무창포항": {  # 3개
        "가가호": "선상24/가가호_Bot.py", 
        "깜보호": "더피싱/깜보호_Bot.py", 
        "헤라호": "더피싱/헤라호_Bot.py"
    },
    "영목항": {  # 3개
        "뉴청남호": "더피싱/뉴청남호_Bot.py", 
        "❌ 청광호": "더피싱/청광호_Bot.py", 
        "청남호": "더피싱/청남호_Bot.py"
    },
    "인천": {  # 2개
        "와이파이호(선)": "더피싱/와이파이호_Bot.py",
        "욜로호": "더피싱/욜로호_Bot.py",
        "제트호(선)": "더피싱/제트호_Bot.py"
    },
    "남당항": {  # 1개
        "은가비호(선)": "선상24/은가비호_Bot.py"
    },
    "대야도": {  # 1개
        "❌ 아일랜드호(선)": "더피싱/아일랜드호_Bot.py"
    },
    "여수": {}  # 0개
}

class FishingLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("🎣 2026 낚시 예약 봇 통합 런처")
        self.root.geometry("980x800") # 📝 [수정] 너비 재조정 (1100 -> 980)
        
        self.center_window(980, 800)
        
        self.current_provider = None
        self.entries = {}
        self.processes = [] # 📝 [추가] 실행 중인 봇 프로세스 관리
        
        self.create_widgets()

        self.root.bind('<F2>', lambda event: self.start_bot())
        self.root.bind('<F3>', lambda event: self.stop_bots())
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.load_config()
    
    def on_close(self):
        """Save config and close window"""
        self.save_config(silent=True)
        self.root.destroy()

    def center_window(self, width, height):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Center Horizontal
        x = (screen_width - width) // 2
        
        # Top 30% Vertical (User requested "70% 상단위", interpreted as leaving 70% below)
        y = int(screen_height * 0.15) 
        
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def create_widgets(self):
        # 1. Configuration Form
        self.lf_config = ttk.LabelFrame(self.root, text="⚙️ 예약 설정", padding=10)
        self.lf_config.pack(fill="x", padx=10, pady=5)
        
        # Row 2: Slots container frame
        self.slots = []
        self.slot_frames = []  # Store frame references for deletion
        self.port_list = list(PORTS.keys())
        
        # Slots container
        self.slots_container = ttk.Frame(self.lf_config)
        self.slots_container.grid(row=2, column=0, columnspan=5, sticky="w", padx=5, pady=2)
        
        # ALL checkbox (above slot list, inside slots_container)
        self.var_select_all = tk.BooleanVar(value=False)
        frame_all = ttk.Frame(self.slots_container)
        frame_all.pack(fill="x", pady=(0, 5))
        ttk.Checkbutton(frame_all, text="ALL", variable=self.var_select_all, command=self.toggle_all_slots).pack(side="left", padx=(0, 10))
        ttk.Button(frame_all, text="📅 예약일 정보", command=self.open_reservation_info).pack(side="left", padx=(0, 20))

        # Execution Time (Moved next to Reservation Info)
        ttk.Label(frame_all, text="실행 시간:").pack(side="left", padx=(0, 5))
        
        self.cb_hour = ttk.Combobox(frame_all, values=[f"{i:02d}" for i in range(24)], width=3, state="readonly", height=24)
        self.cb_hour.set("09")
        self.cb_hour.pack(side="left")
        ttk.Label(frame_all, text="시").pack(side="left")
        
        self.cb_min = ttk.Entry(frame_all, width=3)
        self.cb_min.insert(0, "00")
        self.cb_min.pack(side="left")
        ttk.Label(frame_all, text="분").pack(side="left")
        
        self.cb_sec = ttk.Entry(frame_all, width=5)
        self.cb_sec.insert(0, "00.0")
        self.cb_sec.pack(side="left")
        ttk.Label(frame_all, text="초").pack(side="left")
        
        # Add/Remove/Copy buttons (Moved next to Execution Time)
        ttk.Button(frame_all, text="➕ 추가", width=8, command=self.add_slot).pack(side="left", padx=(10, 2))
        ttk.Button(frame_all, text="➖ 제거", width=8, command=self.remove_slot).pack(side="left", padx=2)
        ttk.Button(frame_all, text="📋 일괄복사", width=10, command=self.copy_first_slot).pack(side="left", padx=2)
        ttk.Button(frame_all, text="📝 정보입력", width=10, command=self.fill_user_info).pack(side="left", padx=2)
        ttk.Button(frame_all, text="🧹 비우기", width=8, command=self.clear_user_info).pack(side="left", padx=2)
        
        # Create initial 4 slots
        for _ in range(4):
            self.add_slot()

        # Test Mode - Row 3
        self.var_test_mode = tk.BooleanVar()
        ttk.Checkbutton(self.lf_config, text="🚀 Test Mode (시간 무시/즉시 실행)", variable=self.var_test_mode).grid(row=3, column=0, columnspan=2, sticky="w", padx=5, pady=5)



        # Simulation Mode - Row 4
        self.var_sim_mode = tk.BooleanVar()
        ttk.Checkbutton(self.lf_config, text="🚫 예약 실행 안함 (시뮬레이션 모드)", variable=self.var_sim_mode).grid(row=4, column=0, columnspan=3, sticky="w", padx=5, pady=5)

        # Save Button - Row 5
        ttk.Button(self.lf_config, text="💾 설정 저장", command=self.save_config).grid(row=5, column=0, sticky="w", padx=5, pady=10)


        # 3. Execution (Matching User Screenshot)
        lf_action = ttk.LabelFrame(self.root, text="🚀 실행 제어", padding=10)
        lf_action.pack(fill="both", expand=True, padx=10, pady=5) # 📝 [수정] expand=True 추가하여 남은 공간 모두 차지
        
        # Button Frame
        f_btns = ttk.Frame(lf_action)
        f_btns.pack(fill="x", pady=5)
        ttk.Button(f_btns, text="🔥 봇 실행 (Start) (F2)", command=self.start_bot).pack(side="left", padx=5)
        ttk.Button(f_btns, text="🚫 봇 종료 (Stop) (F3)", command=self.stop_bots).pack(side="left", padx=5)
        ttk.Button(f_btns, text="🌐 브라우저 종료", command=self.close_browsers).pack(side="left", padx=5)
        
        # Log Label and Area
        ttk.Label(lf_action, text="로그").pack(anchor="w", pady=(10, 2))
        self.log_area = tk.Text(lf_action, height=15, state="disabled", font=("Consolas", 9)) # 📝 [수정] 기본 높이 증가
        self.log_area.pack(fill="both", expand=True, pady=5)

        self.log("✅ 낚시 예약 봇 통합 런처 준비 완료")
        
        
        # Init
        # self.combo_port.current(0)
        # self.on_port_change(None)

    def get_clean_provider_name(self, display_name):
        """Remove '❌ ' prefix if present"""
        if not display_name: return ""
        return display_name.replace("❌ ", "")

    def add_slot(self):
        """Add a new slot row"""
        i = len(self.slots)
        default_y, default_m, default_d = "2026", "09", "01"
        
        # Create a frame for the slot row
        frame_slot = ttk.Frame(self.slots_container)
        frame_slot.pack(fill="x", pady=2)
        
        # Slot Enable Checkbox (leftmost)
        var_enable = tk.BooleanVar(value=(i==0))
        chk = ttk.Checkbutton(frame_slot, text=f"{i+1}번", variable=var_enable)
        chk.pack(side="left", padx=(0, 10))
        
        # Port
        ttk.Label(frame_slot, text="항구:").pack(side="left", padx=(0, 2))
        cb_port = ttk.Combobox(frame_slot, values=self.port_list, width=8, state="readonly", height=15)
        cb_port.set(self.port_list[0] if self.port_list else "")
        cb_port.pack(side="left", padx=(0, 10))
        
        # Provider
        ttk.Label(frame_slot, text="선사:").pack(side="left", padx=(0, 2))
        cb_provider = ttk.Combobox(frame_slot, width=12, state="readonly", height=20)
        cb_provider.pack(side="left", padx=(0, 10))
        
        # Bind port change to update provider list
        cb_port.bind("<<ComboboxSelected>>", lambda e, idx=i: self.on_slot_port_change(idx))
        
        # Date
        cb_year = ttk.Entry(frame_slot, width=5)
        cb_year.insert(0, default_y)
        cb_year.pack(side="left")
        ttk.Label(frame_slot, text="년").pack(side="left")
        
        cb_month = ttk.Combobox(frame_slot, values=[f"{m:02d}" for m in range(1, 13)], width=3, state="readonly", height=12)
        cb_month.set(default_m)
        cb_month.pack(side="left")
        ttk.Label(frame_slot, text="월").pack(side="left")
        
        cb_day = ttk.Entry(frame_slot, width=3)
        cb_day.insert(0, default_d)
        cb_day.pack(side="left")
        cb_day.bind("<FocusOut>", lambda e, entry=cb_day: self.pad_day_input(entry))
        ttk.Label(frame_slot, text="일").pack(side="left", padx=(0, 10))

        # Person
        ttk.Label(frame_slot, text="인원:").pack(side="left")
        cb_person = ttk.Combobox(frame_slot, values=[str(p) for p in range(1, 6)], width=2, state="readonly")
        cb_person.set("1")
        cb_person.pack(side="left") # 여백 제거
        ttk.Label(frame_slot, text="명").pack(side="left", padx=(0, 5))

        # Name
        ttk.Label(frame_slot, text="이름:").pack(side="left")
        entry_name = ttk.Entry(frame_slot, width=6)
        # entry_name.insert(0, "")
        entry_name.pack(side="left", padx=(0, 5))

        # Depositor
        ttk.Label(frame_slot, text="입금자명:").pack(side="left")
        entry_depositor = ttk.Entry(frame_slot, width=6)
        # entry_depositor.insert(0, "")
        entry_depositor.pack(side="left", padx=(0, 5))

        # Phone
        ttk.Label(frame_slot, text="전화번호:").pack(side="left")
        entry_phone = ttk.Entry(frame_slot, width=13)
        entry_phone.insert(0, "010-")
        entry_phone.pack(side="left")
        entry_phone.bind("<KeyRelease>", lambda e, entry=entry_phone: self.on_phone_key_release(e, entry))
        
        self.slots.append({
            "enable": var_enable,
            "port": cb_port,
            "provider": cb_provider,
            "year": cb_year,
            "month": cb_month,
            "day": cb_day,
            "person": cb_person,
            "checkbox": chk,
            "name": entry_name,
            "depositor": entry_depositor,
            "phone": entry_phone
        })
        self.slot_frames.append(frame_slot)
        
        # Initialize provider list for this slot
        self.update_slot_provider(i)
        
    def remove_slot(self):
        """Remove the last slot row"""
        if len(self.slots) <= 1:
            return  # Keep at least one slot
        
        # Remove the last slot
        self.slots.pop()
        frame = self.slot_frames.pop()
        frame.destroy()
        
        # Renumber remaining slots
        self.renumber_slots()
    
    def renumber_slots(self):
        """Update slot numbers after removal"""
        for i, slot in enumerate(self.slots):
            slot["checkbox"].config(text=f"{i+1}번")
            # Update port change binding
            slot["port"].unbind("<<ComboboxSelected>>")
            slot["port"].bind("<<ComboboxSelected>>", lambda e, idx=i: self.on_slot_port_change(idx))

    def copy_first_slot(self):
        """Copy first checked slot settings (including name/dep/phone) to all other checked slots"""
        # Find first checked slot
        first_checked = None
        first_idx = -1
        for i, slot in enumerate(self.slots):
            if slot["enable"].get():
                first_checked = slot
                first_idx = i
                break
        
        if not first_checked:
            self.log("⚠️ 체크된 슬롯이 없습니다.")
            return
        
        # Get settings from first checked slot
        source_port = first_checked["port"].get()
        source_provider = first_checked["provider"].get()
        source_year = first_checked["year"].get()
        source_month = first_checked["month"].get()
        source_day = first_checked["day"].get()
        source_person = first_checked["person"].get()
        
        source_name = first_checked["name"].get()
        source_depositor = first_checked["depositor"].get()
        source_phone = first_checked["phone"].get()
        
        # Copy to other checked slots
        copied_count = 0
        for i, slot in enumerate(self.slots):
            if slot["enable"].get() and i != first_idx:
                # Set port and update provider list
                slot["port"].set(source_port)
                self.update_slot_provider(i)
                
                # Set provider
                slot["provider"].set(source_provider)
                
                # Set date
                slot["year"].delete(0, tk.END)
                slot["year"].insert(0, source_year)
                slot["month"].set(source_month)
                slot["day"].delete(0, tk.END)
                slot["day"].insert(0, source_day)
                
                # Set person count
                slot["person"].set(source_person)

                # Set user info
                slot["name"].delete(0, tk.END)
                slot["name"].insert(0, source_name)
                slot["depositor"].delete(0, tk.END)
                slot["depositor"].insert(0, source_depositor)
                slot["phone"].delete(0, tk.END)
                slot["phone"].insert(0, source_phone)

                copied_count += 1
        
        if copied_count > 0:
            self.log(f"📋 {first_idx+1}번 슬롯 설정을 {copied_count}개 슬롯에 복사 완료")
        else:
            self.log("ℹ️ 복사할 대상 슬롯이 없습니다. (2개 이상 체크 필요)")

    def fill_user_info(self):
        """Fill specific user info into all checked slots"""
        filled_count = 0
        for slot in self.slots:
            if slot["enable"].get():
                slot["name"].delete(0, tk.END)
                slot["name"].insert(0, "오동균")
                slot["depositor"].delete(0, tk.END)
                slot["depositor"].insert(0, "오동균")
                slot["phone"].delete(0, tk.END)
                slot["phone"].insert(0, "010-2345-6149")
                filled_count += 1
        
        if filled_count > 0:
            self.log(f"📝 {filled_count}개 슬롯에 사용자 정보 입력 완료")
        else:
            self.log("⚠️ 체크된 슬롯이 없습니다.")

    def clear_user_info(self):
        """Clear user info in all checked slots"""
        cleared_count = 0
        for slot in self.slots:
            if slot["enable"].get():
                slot["name"].delete(0, tk.END)
                slot["depositor"].delete(0, tk.END)
                slot["phone"].delete(0, tk.END)
                slot["phone"].insert(0, "010-") # Reset to default prefix
                cleared_count += 1
        
        if cleared_count > 0:
            self.log(f"🧹 {cleared_count}개 슬롯의 사용자 정보를 비웠습니다.")
        else:
            self.log("⚠️ 체크된 슬롯이 없습니다.")

    def toggle_all_slots(self):
        """Toggle all slot checkboxes based on ALL checkbox state"""
        select_all = self.var_select_all.get()
        for slot in self.slots:
            slot["enable"].set(select_all)

    def highlight_year(self, cb_year):
        """Highlight 2027 year selection with orange foreground"""
        year = cb_year.get()
        if year == "2027":
            cb_year.configure(foreground="orange")
        else:
            cb_year.configure(foreground="black")
    
    def pad_day_input(self, entry):
        """Pad day input to 2 digits (e.g., 7 -> 07)"""
        val = entry.get().strip()
        if val.isdigit() and len(val) == 1:
            entry.delete(0, tk.END)
            entry.insert(0, f"0{val}")

    def on_phone_key_release(self, event, entry):
        """Real-time phone number formatting"""
        if event.keysym in ('BackSpace', 'Delete', 'Left', 'Right', 'Tab', 'Shift_L', 'Shift_R', 'Control_L', 'Control_R'):
            return

        # Get raw digits
        val = entry.get().replace('-', '')
        if not val and not entry.get(): return # Empty
        if val and not val.isdigit(): return # Contains non-digits (handle if needed, or just ignore format)

        # Max 11 digits
        if len(val) > 11: val = val[:11]
        
        formatted = val
        if len(val) > 3:
            formatted = val[:3] + '-' + val[3:]
        if len(val) > 7:
             # First hyphen is at index 3, so next part starts at 4.
             # formatted so far: "010-1234" (len 8)
             # we want "010-1234-" + rest
             formatted = formatted[:8] + '-' + formatted[8:]
             
        if entry.get() != formatted:
            entry.delete(0, tk.END)
            entry.insert(0, formatted)
            entry.icursor(tk.END) # Keep cursor at end for linear typing

    def on_slot_port_change(self, slot_idx):
        """Update provider list when port changes for a specific slot"""
        self.update_slot_provider(slot_idx)
    
    def update_slot_provider(self, slot_idx):
        """Update the provider combobox for a specific slot based on its port selection"""
        slot = self.slots[slot_idx]
        port = slot["port"].get()
        raw_providers = PORTS.get(port, {})
        display_values = list(raw_providers.keys())
        
        slot["provider"]["values"] = display_values
        if display_values:
            slot["provider"].current(0)
        else:
            slot["provider"].set("")
        
    def get_config_path(self, provider_name=None):
        """Always return the global config path (Unified Settings)"""
        return os.path.join(CONFIG_DIR, "global_reservation_settings.json")

    def load_config(self, provider_name=None):
        path = self.get_config_path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                    self.var_test_mode.set(data.get('test_mode', False))
                    self.var_sim_mode.set(data.get('simulation_mode', False))
                    
                    multi_data = data.get('multi_instance', [])
                    
                    # If multi_instance exists, load it including port/provider
                    if multi_data:
                        # Adjust slot count to match saved data
                        while len(self.slots) < len(multi_data):
                            self.add_slot()
                        while len(self.slots) > len(multi_data) and len(self.slots) > 1:
                            self.remove_slot()
                        
                        for i, slot_data in enumerate(multi_data):
                            if i < len(self.slots):
                                # Load port and update provider list
                                saved_port = slot_data.get("port", list(PORTS.keys())[0])
                                if saved_port in PORTS:
                                    self.slots[i]["port"].set(saved_port)
                                    self.update_slot_provider(i)
                                
                                # Load provider
                                saved_provider = slot_data.get("provider", "")
                                if saved_provider:
                                    current_providers = self.slots[i]["provider"]["values"]
                                    for prov in current_providers:
                                        clean_prov = self.get_clean_provider_name(prov)
                                        if clean_prov == saved_provider or prov == saved_provider:
                                            self.slots[i]["provider"].set(prov)
                                            break
                                
                                self.slots[i]["enable"].set(slot_data.get("enable", False))
                                d_str = slot_data.get("date", "20260901")
                                if len(d_str) == 8:
                                    self.slots[i]["year"].delete(0, tk.END)
                                    self.slots[i]["year"].insert(0, d_str[:4])
                                    self.slots[i]["month"].set(d_str[4:6])
                                    self.slots[i]["day"].delete(0, tk.END)
                                    self.slots[i]["day"].insert(0, d_str[6:8])
                                self.slots[i]["person"].set(slot_data.get("person_count", "1"))
                                
                                # Load user info
                                self.slots[i]["name"].delete(0, tk.END)
                                self.slots[i]["name"].insert(0, slot_data.get("user_name", "홍길동"))
                                self.slots[i]["depositor"].delete(0, tk.END)
                                self.slots[i]["depositor"].insert(0, slot_data.get("user_depositor", "홍길동"))
                                self.slots[i]["phone"].delete(0, tk.END)
                                self.slots[i]["phone"].insert(0, slot_data.get("user_phone", "010-0000-0000"))

                    else:
                        # Fallback for old configs: use global user info for first slot
                        user_name = data.get('user_name', 'DK')
                        user_depositor = data.get('user_depositor', 'DK')
                        user_phone = data.get('user_phone', '010-2345-6149')
                        
                        if multi_data: # Should not happen if multi_data was empty inside 'if'
                            pass
                        else:
                            # If absolutely no multi data (really old config), fill slot 0
                            self.slots[0]["name"].delete(0, tk.END)
                            self.slots[0]["name"].insert(0, user_name)
                            self.slots[0]["depositor"].delete(0, tk.END)
                            self.slots[0]["depositor"].insert(0, user_depositor)
                            self.slots[0]["phone"].delete(0, tk.END)
                            self.slots[0]["phone"].insert(0, user_phone)

                        
                    # Time
                    time_val = data.get('target_time', '09:00:00')
                    parts = time_val.split(':')
                    if len(parts) == 3:
                        self.cb_hour.set(parts[0])
                        self.cb_min.delete(0, tk.END)
                        self.cb_min.insert(0, parts[1])
                        self.cb_sec.delete(0, tk.END)
                        self.cb_sec.insert(0, parts[2])
            except Exception as e:
                print(f"Error loading config: {e}")

    def save_config(self, silent=False):
        # Build Date/Time strings & Multi Instance Data (with port/provider)
        t_time = f"{self.cb_hour.get()}:{self.cb_min.get()}:{self.cb_sec.get()}"
        
        multi_instance_data = []
        for slot in self.slots:
            d_str = f"{slot['year'].get()}{slot['month'].get()}{slot['day'].get()}"
            provider_name = self.get_clean_provider_name(slot['provider'].get())
            multi_instance_data.append({
                "enable": slot['enable'].get(),
                "port": slot['port'].get(),
                "provider": provider_name,
                "date": d_str,
                "person_count": slot['person'].get(),
                "user_name": slot['name'].get(),
                "user_depositor": slot['depositor'].get(),
                "user_phone": slot['phone'].get()
            })
        
        data = {
            # Global user info removed, now in multi_instance
            "target_time": t_time,
            "multi_instance": multi_instance_data,
            "test_mode": self.var_test_mode.get(),
            "simulation_mode": self.var_sim_mode.get()
        }
        
        if not os.path.exists(CONFIG_DIR):
            os.makedirs(CONFIG_DIR)
            
        path = self.get_config_path()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
            
        if not silent:
            msg = f"💾 '{self.current_provider}' 설정이 통합 저장되었습니다." if self.current_provider else "💾 예약 설정이 통합 저장되었습니다."
            self.log(msg)
            messagebox.showinfo("성공", "설정이 통합 저장되었습니다.")

    def start_bot(self):
        self.save_config(silent=True)
        self.log("🔍 봇 실행 준비 중...")
        
        launched_count = 0
        base_config_path = self.get_config_path()
        
        # Load base config
        with open(base_config_path, 'r', encoding='utf-8') as f:
            base_data = json.load(f)
        
        # Count enabled slots first for grid calculation
        enabled_slots = [(i, slot) for i, slot in enumerate(self.slots) if slot['enable'].get()]
        total_bots = len(enabled_slots)
        
        if total_bots == 0:
            self.log("⚠️ 실행된 봇이 없습니다. 슬롯 체크박스를 확인해주세요.")
            messagebox.showwarning("경고", "선택된 슬롯(체크박스)이 없습니다.")
            return
        
        # Get display size - use root window's screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        self.log(f"🖥️ 디스플레이 크기 감지: {screen_width} x {screen_height}")
        
        # Calculate grid layout
        if total_bots == 1:
            cols, rows = 1, 1
        elif total_bots == 2:
            cols, rows = 2, 1
        elif total_bots == 3:
            cols, rows = 3, 1
        elif total_bots == 4:
            cols, rows = 2, 2
        elif total_bots <= 6:
            cols, rows = 3, 2
        elif total_bots <= 9:
            cols, rows = 3, 3
        else:
            cols, rows = 4, 3
        
        win_width = screen_width // cols
        win_height = screen_height // rows
        self.log(f"📐 그리드 레이아웃: {cols}x{rows} (창 크기: {win_width}x{win_height})")
        
        # Iterate through each enabled slot
        for grid_idx, (i, slot) in enumerate(enabled_slots):
            port = slot['port'].get()
            provider_raw = slot['provider'].get()  # Keep raw name for PORTS lookup
            provider_clean = self.get_clean_provider_name(provider_raw)  # For display/logging
            
            if not provider_raw:
                self.log(f"⚠️ Slot {i+1}: 선사가 선택되지 않았습니다.")
                continue
            
            # Find script using raw provider name (may include ❌ prefix)
            script_name = PORTS.get(port, {}).get(provider_raw)
            if not script_name:
                self.log(f"⚠️ Slot {i+1}: '{provider_clean}'의 스크립트가 없습니다.")
                continue
            
            script_path = os.path.join(BOTS_DIR, script_name)
            if not os.path.exists(script_path):
                self.log(f"❌ Slot {i+1}: 스크립트 파일 없음 - {script_path}")
                continue
            
            # Build date string
            d_str = f"{slot['year'].get()}{slot['month'].get()}{slot['day'].get()}"
            
            # Calculate window position based on grid index
            col = grid_idx % cols
            row = grid_idx // cols
            win_x = col * win_width
            win_y = row * win_height
            
            # Create Temp Config for this instance with window position
            temp_data = base_data.copy()
            temp_data['target_date'] = d_str
            temp_data['person_count'] = slot['person'].get()
            
            # Inject per-slot user info
            temp_data['user_name'] = slot['name'].get()
            temp_data['user_depositor'] = slot['depositor'].get()
            temp_data['user_phone'] = slot['phone'].get()
            
            temp_data['window_x'] = win_x
            temp_data['window_y'] = win_y
            temp_data['window_width'] = win_width
            temp_data['window_height'] = win_height
            
            temp_config_name = f"temp_config_{provider_clean}_{i}.json"
            temp_config_path = os.path.join(CONFIG_DIR, temp_config_name)
            
            with open(temp_config_path, 'w', encoding='utf-8') as f:
                json.dump(temp_data, f, ensure_ascii=False, indent=4)
            
            self.log(f"🚀 Slot {i+1} 시작: {port} - {provider_clean} | {d_str} | {slot['person'].get()}명 | {slot['name'].get()} | 위치:({win_x},{win_y})")
            cmd = ["python", script_path, "--config", temp_config_path]
            proc = subprocess.Popen(cmd)
            self.processes.append(proc)
            launched_count += 1
                
        if launched_count > 0:
            self.log(f"✅ 총 {launched_count}개의 봇 인스턴스가 성공적으로 실행되었습니다.")

    def log(self, message):
        self.log_area.configure(state="normal")
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-4]
        self.log_area.insert("end", f"[{timestamp}] {message}\n")
        self.log_area.see("end")
        self.log_area.configure(state="disabled")

    def stop_bots(self, event=None):
        """Terminate all running bot processes"""
        if not self.processes:
            self.log("ℹ️ 현재 실행 중인 봇이 없습니다.")
            return

        self.log(f"🛑 총 {len(self.processes)}개의 봇 인스턴스 종료 시도 중...")
        terminated_count = 0
        for proc in self.processes:
            if proc.poll() is None: # Still running
                proc.terminate()
                terminated_count += 1
        
        self.processes = [] # Clear the list
        self.log(f"✅ {terminated_count}개의 봇 프로세스가 종료되었습니다.")
        messagebox.showinfo("종료 완료", f"{terminated_count}개의 봇 프로세스가 종료되었습니다.")

    def close_browsers(self):
        """Close only browser windows opened by bots (using saved PIDs)"""
        # Show confirmation dialog
        result = messagebox.askokcancel(
            "브라우저 종료 확인",
            "확인을 누르면 봇이 실행한 브라우저 창만 종료됩니다.\n(다른 Chrome 창은 유지됩니다)\n\n계속하시겠습니까?"
        )
        
        if not result:
            self.log("ℹ️ 브라우저 종료가 취소되었습니다.")
            return
        
        # Read saved PIDs and kill only those
        pid_file = os.path.join(CONFIG_DIR, 'bot_chrome_pids.txt')
        
        if not os.path.exists(pid_file):
            # Fallback: Ask if user wants to close ALL Chrome
            fallback = messagebox.askyesno(
                "봇 PID 없음",
                "봇 Chrome PID 기록이 없습니다.\n\n대신 모든 Chrome 창을 종료할까요?\n(주의: 개인 Chrome 창도 함께 종료됩니다)"
            )
            if fallback:
                import subprocess as sp
                sp.run(["taskkill", "/F", "/IM", "chromedriver.exe"], capture_output=True, check=False)
                sp.run(["taskkill", "/F", "/IM", "chrome.exe"], capture_output=True, check=False)
                self.log("🌐 모든 Chrome 브라우저 창을 종료했습니다.")
                messagebox.showinfo("브라우저 종료", "모든 Chrome 창이 종료되었습니다.")
            else:
                self.log("ℹ️ 브라우저 종료가 취소되었습니다.")
            return
        
        try:
            import psutil
            
            # Read PIDs
            with open(pid_file, 'r', encoding='utf-8') as f:
                pids = [int(line.strip()) for line in f.readlines() if line.strip().isdigit()]
            
            closed_count = 0
            for pid in pids:
                try:
                    proc = psutil.Process(pid)
                    proc.terminate()
                    closed_count += 1
                    self.log(f"🌐 Chrome PID {pid} 종료됨")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass  # Already terminated or access denied
            
            # Clear the PID file
            os.remove(pid_file)
            
            self.log(f"🌐 봇 브라우저 {closed_count}개 종료 완료")
            messagebox.showinfo("브라우저 종료", f"봇 브라우저 {closed_count}개가 종료되었습니다.\n(다른 Chrome 창은 유지됩니다)")
        except Exception as e:
            self.log(f"⚠️ 브라우저 종료 오류: {e}")
            messagebox.showerror("오류", f"브라우저 종료 중 오류 발생: {e}")

    def open_reservation_info(self):
        img_path = os.path.join(BASE_DIR, "예약일정보.png")
        if os.path.exists(img_path):
            try:
                self.log("📅 예약일 정보 창을 생성합니다.")
                
                # Load image
                pil_img = Image.open(img_path)
                width, height = pil_img.size
                
                # Create Toplevel Window
                info_win = tk.Toplevel(self.root)
                info_win.title("📅 2026 낚시 예약 일정 정보")
                
                # Resize window to image size
                info_win.geometry(f"{width}x{height}")
                info_win.resizable(False, False)
                
                # Convert to Tkinter format
                tk_img = ImageTk.PhotoImage(pil_img)
                
                # Display in label
                lbl = tk.Label(info_win, image=tk_img)
                lbl.image = tk_img # Keep reference
                lbl.pack()
                
                # Center window relative to main launcher
                x = self.root.winfo_x() + (self.root.winfo_width() - width) // 2
                y = self.root.winfo_y() + (self.root.winfo_height() - height) // 2
                info_win.geometry(f"+{x}+{y}")
                
            except Exception as e:
                self.log(f"❌ 이미지 로드 실패: {e}")
                messagebox.showerror("오류", f"이미지를 불러오는 중 오류가 발생했습니다.\n{e}")
        else:
            self.log(f"❌ 파일을 찾을 수 없습니다: {img_path}")
            messagebox.showerror("오류", f"예약일 정보 파일을 찾을 수 없습니다.\n파일이 {BASE_DIR} 폴더에 있는지 확인해주세요.")

if __name__ == "__main__":
    if not os.path.exists(CONFIG_DIR): os.makedirs(CONFIG_DIR)
    root = tk.Tk()
    app = FishingLauncher(root)
    root.mainloop()
