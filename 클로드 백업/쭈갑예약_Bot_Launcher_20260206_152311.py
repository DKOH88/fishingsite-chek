import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import sys
import subprocess
import threading
from datetime import datetime
from PIL import Image, ImageTk # 📝 [추가] 이미지 표시를 위한 라이브러리

# Windows 콘솔 UTF-8 설정
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(BASE_DIR, "config")
LAUNCHER_STATE_FILE = os.path.join(CONFIG_DIR, "launcher_state.json")
BOTS_DIR = os.path.join(BASE_DIR, "bots")

# Data Structure: Port -> { ProviderName: ScriptName }
# 항구 정렬: 선사 수 내림차순
PORTS = {
    "오천항": {
        "가즈아호": "선상24/가즈아호_Bot.py",
        "금땡이호": "더피싱/금땡이호_Bot.py",
        "꽃돼지호": None,
        "나폴리호": "더피싱/나폴리호_Bot.py",
        "뉴성령호": "더피싱/뉴성령호_Bot.py",
        "뉴찬스호(선)": "더피싱/뉴찬스호_Bot.py",
        "도지호": "선상24/도지호_Bot.py",
        "범블비호": "더피싱/범블비호_Bot.py",
        "블루호": "더피싱/블루호_Bot.py",
        "비엔나호": "더피싱/비엔나호_Bot.py",
        "빅보스호": "선상24/빅보스호_Bot.py",
        "샤크호": "더피싱/샤크호_Bot.py",
        "샤크호(API)": "api/샤크호_API.py",
        "싸부호": None,
        "아리랑1호": "선상24/아리랑1호.py",
        "어쩌다어부호(선)": "선상24/어쩌다어부호_Bot.py",
        "오디세이호": "더피싱/오디세이호_Bot.py",
        "유진호": "더피싱/유진호_Bot.py",
        "자이언트호": "선상24/자이언트호_Bot.py",
        "카즈미호": "더피싱/카즈미호_Bot.py",
        "캡틴호": "더피싱/캡틴호_Bot.py",
        "프랜드호": "더피싱/프랜드호_Bot.py",
        "프린스호": "선상24/프린스호_Bot.py",
        "호랭이호": "선상24/호랭이호_Bot.py",
    },
    "안흥·신진항": {
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
        "퀸블레스호": "더피싱/퀸블레스호_Bot.py",
        "킹스타호": None,
        "행운호": "더피싱/행운호_Bot.py",
    },
    "영흥도": {
        "god호(선)": "더피싱/지오디호_Bot.py",
        "루키나 2호(선)": "선상24/루키나 2호_Bot.py",
        "루키나호(선)": "선상24/루키나호_Bot.py",
        "만수피싱호": "더피싱/만수피싱호_Bot.py",
        "스타피싱호(선)": "더피싱/스타피싱호_Bot.py",
        "아라호(선)": "더피싱/아라호_Bot.py",
        "아이리스호(선)": "더피싱/아이리스호_Bot.py",
        "야호(선)": "더피싱/야호_Bot.py",
        "짱구호(선)": "더피싱/짱구호_Bot.py",
        "크루즈호": "더피싱/크루즈호_Bot.py",
        "팀만수호(API)": "api/팀만수호_API.py",
        "팀만수호(선)": "더피싱/팀만수호_Bot.py",
        "팀만수호2(선)": "더피싱/팀만수호2_Bot.py",
        "팀에프원호(선)": "선상24/팀에프원호_Bot.py",
        "팀에프투호(선)": "선상24/팀에프투호_Bot.py",
        "페라리호(선)": "더피싱/페라리호_Bot.py",
    },
    "삼길포항": {
        "골드피싱호(선)": "더피싱/골드피싱호_Bot.py",
        "넘버원호(선)": "선상24/넘버원호_Bot.py",
        "뉴항구호(선)": "선상24/뉴항구호_Bot.py",
        "만석호(선)": "더피싱/만석호_Bot.py",
        "만석호2(선)": "더피싱/만석호2_Bot.py",
        "승주호(선)": "더피싱/승주호_Bot.py",
        "으리호(선)": "더피싱/으리호_Bot.py",
        "천마호(선)": "선상24/천마호_Bot.py",
        "헌터호(선)": "더피싱/헌터호_Bot.py",
        "헤르메스호(API)": "api/헤르메스호_API.py",
        "헤르메스호(선)": "더피싱/헤르메스호_Bot.py",
    },
    "대천항": {
        "기가호": "선상24/기가호_Bot.py",
        "까칠이호": "더피싱/까칠이호_Bot.py",
        "아이언호": "선상24/아이언호_Bot.py",
        "아인스호": "더피싱/아인스호_Bot.py",
        "야야호": "더피싱/야야호_Bot.py",
        "예린호(선)": "더피싱/예린호_Bot.py",
        "청춘호": "더피싱/청춘호_Bot.py",
        "팀루피호": "더피싱/팀루피호_Bot.py",
        "승하호": "더피싱/승하호_Bot.py",
        "하이피싱호": "더피싱/하이피싱호_Bot.py",
    },
    "마검포항": {
        "❌ 가가호": "선상24/가가호_Bot.py",
        "❌ 천일호": "더피싱/천일호_Bot.py",
        "팀바이트호": "더피싱/팀바이트호_Bot.py",
        "하와이호(선)": "더피싱/하와이호_Bot.py",
    },
    "무창포항": {
        "가가호": "선상24/가가호_Bot.py",
        "깜보호": "더피싱/깜보호_Bot.py",
        "페가수스호(API)": "api/페가수스_API.py",
        "헤라호": "더피싱/헤라호_Bot.py",
    },
    "영목항": {
        "❌ 청광호": "더피싱/청광호_Bot.py",
        "뉴청남호": "더피싱/뉴청남호_Bot.py",
        "청남호": "더피싱/청남호_Bot.py",
        "청남호2": "더피싱/청남호2_Bot.py",
    },
    "인천": {
        "와이파이호(선)": "더피싱/와이파이호_Bot.py",
        "욜로호": "더피싱/욜로호_Bot.py",
        "제트호(선)": "더피싱/제트호_Bot.py",
    },
    "구매항": {
        "악바리호": "선상24/악바리호_Bot.py",
        "악바리호2": "선상24/악바리호2_Bot.py",
    },
    "남당항": {
        "은가비호(선)": "선상24/은가비호_Bot.py",
        "장현호": "더피싱/장현호_Bot.py",
        "장현호(API)": "api/장현호_API.py",
        "장현호2": "더피싱/장현호2_Bot.py",
    },
    "대야도": {
        "❌ 아일랜드호(선)": "더피싱/아일랜드호_Bot.py",
        "블루오션호": "더피싱/블루오션호_Bot.py",
    },
    "백사장항": {
        "영차호": "더피싱/영차호_Bot.py",
    },
    "여수": {
        "오션스타1호": "선상24/오션스타1호_Bot.py",
        "오션스타2호": "선상24/오션스타2호_Bot.py",
        "오션스타3호": "선상24/오션스타3호_Bot.py",
    },
    "녹동항": {
        "E.스마일호": "선상24/E.스마일_Bot.py",
    },
    "평택항": {
        "오닉스호": "더피싱/오닉스호_Bot.py",
    },
    "전곡항": {
        "제비호": "선상24/제비호_Bot.py",
    },
    "홍원항": {
        "조커호": "더피싱/조커호_Bot.py",
    },
}

class FishingLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("🎣 2026 낚시 예약 봇 통합 런처")
        self.root.geometry("980x800") # 📝 [수정] 너비 재조정 (1100 -> 980)
        
        self.center_window(980, 800)
        
        self.current_provider = None
        self.entries = {}
        self.processes = [] # 실행 중인 봇 프로세스 관리
        self.bot_logs = [] # 📝 [추가] 봇 로그 저장용 리스트
        
        self.create_widgets()

        self.root.bind('<F2>', lambda event: self.start_bot())
        self.root.bind('<F3>', lambda event: self.stop_bots())
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.load_config()
    
    def save_log_to_file(self):
        """Save current log content to file"""
        try:
            log_dir = os.path.join(BASE_DIR, "Log")
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"GUI_Close_{timestamp}.txt"
            filepath = os.path.join(log_dir, filename)
            
            # log_area might not be initialized if closed very early, but typically it is.
            if self.bot_logs:
                log_content = "".join(self.bot_logs)
                if log_content.strip():
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(log_content)
                    print(f"Bot Log saved to {filepath}")
            else:
                 # Fallback if empty or requested? User said "Bot logs".
                 pass
        except Exception as e:
            print(f"Failed to save log: {e}")

    def on_close(self):
        """Save config, clean up temp files, and close window"""
        self.save_log_to_file()
        self.save_config(silent=True)
        self._cleanup_temp_configs()
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
        
        # 조기오픈 감시 체크박스 (5분전부터 10초마다 페이지 오픈 여부 확인)
        self.var_early_monitor = tk.BooleanVar(value=False)
        ttk.Checkbutton(frame_all, text="🔍 조기오픈감시", variable=self.var_early_monitor).pack(side="left", padx=(10, 0))
        
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

        # 선사 검색 프레임 (Row 3~4 오른쪽)
        search_frame = ttk.Frame(self.lf_config)
        search_frame.grid(row=3, column=2, rowspan=2, sticky="e", padx=10, pady=5)

        ttk.Label(search_frame, text="🔍 선사 검색:").pack(side="left", padx=(0, 5))
        self.entry_provider_search = ttk.Entry(search_frame, width=15)
        self.entry_provider_search.pack(side="left", padx=(0, 5))
        self.entry_provider_search.bind("<Return>", lambda e: self.search_and_apply_provider())
        ttk.Button(search_frame, text="검색", width=6, command=self.search_and_apply_provider).pack(side="left")

        # Simulation Mode - Row 4
        self.var_sim_mode = tk.BooleanVar()
        ttk.Checkbutton(self.lf_config, text="🚫 예약 실행 안함 (시뮬레이션 모드)", variable=self.var_sim_mode).grid(row=4, column=0, columnspan=2, sticky="w", padx=5, pady=5)

        # Save Button - Row 5
        btn_frame_row5 = ttk.Frame(self.lf_config)
        btn_frame_row5.grid(row=5, column=0, columnspan=5, sticky="w", padx=5, pady=10)
        ttk.Button(btn_frame_row5, text="💾 설정 저장", command=self.save_config).pack(side="left", padx=(0, 10))
        ttk.Button(btn_frame_row5, text="✏️ 항구/선사 편집", command=self.open_port_editor).pack(side="left")


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
        cb_port = ttk.Combobox(frame_slot, values=self.port_list, width=8, state="readonly", height=30)
        cb_port.set(self.port_list[0] if self.port_list else "")
        cb_port.pack(side="left", padx=(0, 10))
        
        # Provider
        ttk.Label(frame_slot, text="선사:").pack(side="left", padx=(0, 2))
        cb_provider = ttk.Combobox(frame_slot, width=12, state="readonly", height=35)
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
        """Fill user info from saved config into all checked slots"""
        # 설정 파일에서 사용자 정보를 읽어옴
        default_name = ""
        default_depositor = ""
        default_phone = "010-"

        config_path = self.get_config_path()
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # multi_instance의 첫 번째 슬롯에서 사용자 정보 가져오기
                multi = data.get('multi_instance', [])
                if multi:
                    default_name = multi[0].get('user_name', '')
                    default_depositor = multi[0].get('user_depositor', '')
                    default_phone = multi[0].get('user_phone', '010-')
            except Exception as e:
                self.log(f"⚠️ 설정 파일 읽기 실패: {e}")

        if not default_name:
            self.log("⚠️ 저장된 사용자 정보가 없습니다. 먼저 1번 슬롯에 정보를 입력하고 저장해주세요.")
            return

        filled_count = 0
        for slot in self.slots:
            if slot["enable"].get():
                slot["name"].delete(0, tk.END)
                slot["name"].insert(0, default_name)
                slot["depositor"].delete(0, tk.END)
                slot["depositor"].insert(0, default_depositor)
                slot["phone"].delete(0, tk.END)
                slot["phone"].insert(0, default_phone)
                filled_count += 1

        if filled_count > 0:
            self.log(f"📝 {filled_count}개 슬롯에 사용자 정보 입력 완료 ({default_name})")
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

    def eng_to_kor(self, text):
        """영타자(한글 자판)를 한글로 변환"""
        # 영문 키 -> 한글 자모 매핑
        ENG_MAP = {
            'q': 'ㅂ', 'w': 'ㅈ', 'e': 'ㄷ', 'r': 'ㄱ', 't': 'ㅅ',
            'y': 'ㅛ', 'u': 'ㅕ', 'i': 'ㅑ', 'o': 'ㅐ', 'p': 'ㅔ',
            'a': 'ㅁ', 's': 'ㄴ', 'd': 'ㅇ', 'f': 'ㄹ', 'g': 'ㅎ',
            'h': 'ㅗ', 'j': 'ㅓ', 'k': 'ㅏ', 'l': 'ㅣ',
            'z': 'ㅋ', 'x': 'ㅌ', 'c': 'ㅊ', 'v': 'ㅍ', 'b': 'ㅠ',
            'n': 'ㅜ', 'm': 'ㅡ',
            'Q': 'ㅃ', 'W': 'ㅉ', 'E': 'ㄸ', 'R': 'ㄲ', 'T': 'ㅆ',
            'O': 'ㅒ', 'P': 'ㅖ'
        }

        # 유니코드 조합용 리스트
        CHOSUNG = ['ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']
        JUNGSUNG = ['ㅏ', 'ㅐ', 'ㅑ', 'ㅒ', 'ㅓ', 'ㅔ', 'ㅕ', 'ㅖ', 'ㅗ', 'ㅘ', 'ㅙ', 'ㅚ', 'ㅛ', 'ㅜ', 'ㅝ', 'ㅞ', 'ㅟ', 'ㅠ', 'ㅡ', 'ㅢ', 'ㅣ']
        JONGSUNG = ['', 'ㄱ', 'ㄲ', 'ㄳ', 'ㄴ', 'ㄵ', 'ㄶ', 'ㄷ', 'ㄹ', 'ㄺ', 'ㄻ', 'ㄼ', 'ㄽ', 'ㄾ', 'ㄿ', 'ㅀ', 'ㅁ', 'ㅂ', 'ㅄ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']

        # 단순 모음만 (키보드에서 직접 입력 가능한 것들)
        SIMPLE_MOUM = {'ㅏ', 'ㅐ', 'ㅑ', 'ㅒ', 'ㅓ', 'ㅔ', 'ㅕ', 'ㅖ', 'ㅗ', 'ㅛ', 'ㅜ', 'ㅠ', 'ㅡ', 'ㅣ'}

        # 복합 모음 조합
        DOUBLE_MOUM = {
            ('ㅗ', 'ㅏ'): 'ㅘ', ('ㅗ', 'ㅐ'): 'ㅙ', ('ㅗ', 'ㅣ'): 'ㅚ',
            ('ㅜ', 'ㅓ'): 'ㅝ', ('ㅜ', 'ㅔ'): 'ㅞ', ('ㅜ', 'ㅣ'): 'ㅟ',
            ('ㅡ', 'ㅣ'): 'ㅢ'
        }

        # 복합 종성 조합
        DOUBLE_JONG = {
            ('ㄱ', 'ㅅ'): 'ㄳ', ('ㄴ', 'ㅈ'): 'ㄵ', ('ㄴ', 'ㅎ'): 'ㄶ',
            ('ㄹ', 'ㄱ'): 'ㄺ', ('ㄹ', 'ㅁ'): 'ㄻ', ('ㄹ', 'ㅂ'): 'ㄼ',
            ('ㄹ', 'ㅅ'): 'ㄽ', ('ㄹ', 'ㅌ'): 'ㄾ', ('ㄹ', 'ㅍ'): 'ㄿ',
            ('ㄹ', 'ㅎ'): 'ㅀ', ('ㅂ', 'ㅅ'): 'ㅄ'
        }

        # 영문 -> 자모 변환
        jamos = [ENG_MAP.get(ch, ch) for ch in text]

        # 자모 -> 한글 조합
        result = []
        i = 0
        while i < len(jamos):
            ch = jamos[i]

            # 초성 + 중성 조합 가능 여부 확인
            if ch in CHOSUNG and i + 1 < len(jamos) and jamos[i + 1] in SIMPLE_MOUM:
                cho = CHOSUNG.index(ch)
                i += 1

                # 중성 처리
                jung_ch = jamos[i]
                i += 1

                # 복합 모음 체크
                if i < len(jamos) and (jung_ch, jamos[i]) in DOUBLE_MOUM:
                    jung_ch = DOUBLE_MOUM[(jung_ch, jamos[i])]
                    i += 1

                jung = JUNGSUNG.index(jung_ch)

                # 종성 처리
                jong = 0
                if i < len(jamos) and jamos[i] in JONGSUNG[1:]:
                    # 다음이 모음이면 현재 자음은 다음 글자의 초성
                    if i + 1 < len(jamos) and jamos[i + 1] in SIMPLE_MOUM:
                        pass  # 종성 없음
                    else:
                        # 복합 종성 체크
                        if i + 1 < len(jamos) and (jamos[i], jamos[i + 1]) in DOUBLE_JONG:
                            # 복합 종성 다음이 모음이면 두번째 자음은 다음 초성
                            if i + 2 < len(jamos) and jamos[i + 2] in SIMPLE_MOUM:
                                jong = JONGSUNG.index(jamos[i])
                                i += 1
                            else:
                                jong_ch = DOUBLE_JONG[(jamos[i], jamos[i + 1])]
                                jong = JONGSUNG.index(jong_ch)
                                i += 2
                        else:
                            jong = JONGSUNG.index(jamos[i])
                            i += 1

                # 한글 유니코드 조합
                code = 0xAC00 + (cho * 21 + jung) * 28 + jong
                result.append(chr(code))
            else:
                result.append(ch)
                i += 1

        return ''.join(result)

    def search_and_apply_provider(self):
        """검색어로 선사를 찾아 체크된 슬롯에 적용"""
        search_term = self.entry_provider_search.get().strip()
        if not search_term:
            self.log("⚠️ 검색어를 입력해주세요.")
            return

        # 영타자 -> 한글 변환 시도
        converted_term = self.eng_to_kor(search_term)
        if converted_term != search_term:
            self.log(f"🔄 영타 변환: {search_term} → {converted_term}")
            search_term = converted_term

        # 모든 항구에서 일치하는 선사 찾기
        found_providers = []  # [(port, provider_name, script_path), ...]

        for port, providers in PORTS.items():
            for provider_name, script_path in providers.items():
                # 검색어가 선사 이름에 포함되어 있는지 확인 (대소문자 무시)
                clean_name = self.get_clean_provider_name(provider_name)
                if search_term.lower() in clean_name.lower():
                    found_providers.append((port, provider_name, script_path))

        if not found_providers:
            self.log(f"⚠️ '{search_term}'와 일치하는 선사를 찾을 수 없습니다.")
            messagebox.showwarning("검색 결과 없음", f"'{search_term}'와 일치하는 선사를 찾을 수 없습니다.")
            return

        # 정확히 일치하는 선사 우선, 그 다음 부분 일치
        exact_match = None
        for port, provider_name, script_path in found_providers:
            clean_name = self.get_clean_provider_name(provider_name)
            if clean_name.lower() == search_term.lower():
                exact_match = (port, provider_name, script_path)
                break

        # 선택할 선사 결정
        if exact_match:
            selected = exact_match
        elif len(found_providers) == 1:
            selected = found_providers[0]
        else:
            # 여러 개 발견 시 선택 다이얼로그 표시
            selected = self.show_provider_selection_dialog(search_term, found_providers)
            if not selected:
                return

        target_port, target_provider, _ = selected
        target_clean = self.get_clean_provider_name(target_provider)

        # 체크된 슬롯에 적용
        applied_count = 0
        for i, slot in enumerate(self.slots):
            if slot["enable"].get():
                # 항구 설정
                slot["port"].set(target_port)
                self.update_slot_provider(i)

                # 선사 설정
                slot["provider"].set(target_provider)
                applied_count += 1

        if applied_count > 0:
            self.log(f"✅ '{target_clean}' ({target_port}) → {applied_count}개 슬롯에 적용 완료")
        else:
            self.log("⚠️ 체크된 슬롯이 없습니다.")

    def show_provider_selection_dialog(self, search_term, providers):
        """여러 선사 중 선택하는 다이얼로그"""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"선사 선택 - '{search_term}'")

        # 창 크기 및 위치
        win_width = 400
        win_height = 350
        x = self.root.winfo_x() + (self.root.winfo_width() - win_width) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - win_height) // 2
        dialog.geometry(f"{win_width}x{win_height}+{x}+{y}")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text=f"'{search_term}' 검색 결과 ({len(providers)}개)", font=("맑은 고딕", 11, "bold")).pack(pady=10)
        ttk.Label(dialog, text="적용할 선사를 선택하세요:").pack(pady=5)

        # 리스트박스
        list_frame = ttk.Frame(dialog)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, font=("맑은 고딕", 10), height=10)
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=listbox.yview)

        for port, provider, _ in providers:
            clean_name = self.get_clean_provider_name(provider)
            listbox.insert(tk.END, f"{clean_name}  ({port})")

        if providers:
            listbox.selection_set(0)

        result = [None]

        def on_select():
            sel = listbox.curselection()
            if sel:
                result[0] = providers[sel[0]]
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        # 버튼
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="선택", command=on_select, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="취소", command=on_cancel, width=10).pack(side=tk.LEFT, padx=5)

        listbox.bind('<Double-Button-1>', lambda e: on_select())
        listbox.bind('<Return>', lambda e: on_select())
        dialog.bind('<Escape>', lambda e: on_cancel())

        dialog.wait_window()
        return result[0]

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
                    self.var_early_monitor.set(data.get('early_monitor', False))
                    
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
            except json.JSONDecodeError as e:
                self.log(f"⚠️ 설정 파일 JSON 파싱 오류: {e}")
                messagebox.showwarning("설정 오류", f"설정 파일이 손상되었습니다.\n{e}")
            except Exception as e:
                self.log(f"⚠️ 설정 파일 로드 오류: {e}")
                messagebox.showwarning("설정 오류", f"설정을 불러오는 중 오류가 발생했습니다.\n{e}")

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
            "simulation_mode": self.var_sim_mode.get(),
            "early_monitor": self.var_early_monitor.get()
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

        # 📝 [추가] 필수 입력값 검증 (이름 & 전화번호 11자리 - 상세 안내)
        for idx, (i, slot) in enumerate(enabled_slots):
            u_name = slot['name'].get().strip()
            u_phone = slot['phone'].get().strip()
            phone_digits = u_phone.replace('-', '')
            
            error_msg = ""
            if not u_name:
                error_msg = "이름이 입력되지 않았습니다."
            elif not u_phone:
                error_msg = "전화번호가 입력되지 않았습니다."
            elif not u_phone.startswith("010-"):
                error_msg = "전화번호는 '010-'으로 시작해야 합니다."
            elif len(phone_digits) != 11:
                error_msg = f"전화번호 자릿수가 부족합니다.\n현재: {len(phone_digits)}자 (010 포함 11자리가 필요합니다)"
            
            if error_msg:
                self.log(f"⚠️ Slot {i+1}: 입력 오류 - {error_msg.splitlines()[0]}")
                messagebox.showwarning("입력 오류", f"{i+1}번 슬롯을 확인해주세요.\n\n⚠️ {error_msg}")
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
            
            # Inject identity
            temp_data['port'] = port
            temp_data['provider'] = provider_clean
            
            temp_data['window_x'] = win_x
            temp_data['window_y'] = win_y
            temp_data['window_width'] = win_width
            temp_data['window_height'] = win_height
            temp_data['early_monitor'] = self.var_early_monitor.get()
            
            temp_config_name = f"temp_config_{provider_clean}_{i}.json"
            temp_config_path = os.path.join(CONFIG_DIR, temp_config_name)
            
            with open(temp_config_path, 'w', encoding='utf-8') as f:
                json.dump(temp_data, f, ensure_ascii=False, indent=4)
            
            self.log(f"🚀 Slot {i+1} 시작: {port} - {provider_clean} | {d_str} | {slot['person'].get()}명 | {slot['name'].get()} | 위치:({win_x},{win_y})")
            cmd = ["python", "-u", script_path, "--config", temp_config_path]  # -u: unbuffered output
            # stdout 캡처하여 런처 cmd 창에 출력
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
                universal_newlines=True,
                encoding='utf-8',
                errors='replace'
            )
            self.processes.append(proc)

            # 봇 출력 모니터링 쓰레드 시작 (런처 cmd 창에 출력)
            prefix = f"[{provider_clean}]"
            monitor_thread = threading.Thread(
                target=self.monitor_bot_output,
                args=(proc, prefix),
                daemon=True
            )
            monitor_thread.start()
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
        """Terminate all running bot processes and clean up temp configs"""
        if not self.processes:
            self.log("ℹ️ 현재 실행 중인 봇이 없습니다.")
            return

        self.log(f"🛑 총 {len(self.processes)}개의 봇 인스턴스 종료 시도 중...")
        terminated_count = 0
        for proc in self.processes:
            if proc.poll() is None:  # Still running
                proc.terminate()
                try:
                    proc.wait(timeout=5)  # 좀비 프로세스 방지
                except subprocess.TimeoutExpired:
                    proc.kill()  # 5초 내 종료 안 되면 강제 종료
                    proc.wait()
                terminated_count += 1

        self.processes = []  # Clear the list

        # 임시 설정 파일 정리
        self._cleanup_temp_configs()

        self.log(f"✅ {terminated_count}개의 봇 프로세스가 종료되었습니다.")
        messagebox.showinfo("종료 완료", f"{terminated_count}개의 봇 프로세스가 종료되었습니다.")

    def _cleanup_temp_configs(self):
        """Remove temporary config files created for bot instances"""
        try:
            for filename in os.listdir(CONFIG_DIR):
                if filename.startswith("temp_config_") and filename.endswith(".json"):
                    filepath = os.path.join(CONFIG_DIR, filename)
                    os.remove(filepath)
                    self.log(f"🧹 임시 파일 삭제: {filename}")
        except Exception as e:
            self.log(f"⚠️ 임시 파일 정리 중 오류: {e}")

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

    def monitor_bot_output(self, proc, prefix):
        """Monitor stdout of bot process and print to launcher's cmd window"""
        try:
            for line in iter(proc.stdout.readline, ''):
                if line:
                    line = line.rstrip('\n\r')
                    if line:  # 빈 줄 제외
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        log_entry = f"[{timestamp}] {prefix} {line}"
                        self.bot_logs.append(log_entry)
                        # 런처의 cmd 창에 출력
                        print(log_entry, flush=True)
                else:
                    break
        except Exception as e:
            print(f"[ERROR] 봇 출력 읽기 오류: {e}", flush=True)
        finally:
            try:
                proc.stdout.close()
            except:
                pass

    def open_port_editor(self):
        """항구/선사 편집 창 열기"""
        editor_win = tk.Toplevel(self.root)
        editor_win.title("✏️ 항구/선사 편집")

        # 창 크기
        win_width = 700
        win_height = 550

        # 화면 중앙 위치 계산
        screen_width = editor_win.winfo_screenwidth()
        screen_height = editor_win.winfo_screenheight()
        x = (screen_width - win_width) // 2
        y = (screen_height - win_height) // 2

        editor_win.geometry(f"{win_width}x{win_height}+{x}+{y}")
        editor_win.resizable(True, True)
        editor_win.transient(self.root)
        editor_win.grab_set()

        # 메인 프레임
        main_frame = ttk.Frame(editor_win, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 상단 안내
        ttk.Label(main_frame, text="항구/선사 편집", font=("맑은 고딕", 12, "bold")).pack(pady=(0, 10))
        ttk.Label(main_frame, text="※ 변경사항은 '저장' 버튼을 눌러야 반영됩니다. 프로그램 재시작 후 적용됩니다.",
                  foreground="gray").pack(pady=(0, 10))

        # 좌우 분할 프레임
        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, pady=5)

        # 왼쪽: 항구 목록
        left_frame = ttk.LabelFrame(paned, text="항구 목록", padding="5")
        paned.add(left_frame, weight=1)

        # 항구 리스트박스
        port_list_frame = ttk.Frame(left_frame)
        port_list_frame.pack(fill=tk.BOTH, expand=True)

        port_scrollbar = ttk.Scrollbar(port_list_frame)
        port_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.editor_port_listbox = tk.Listbox(port_list_frame, yscrollcommand=port_scrollbar.set,
                                               font=("맑은 고딕", 10), height=15)
        self.editor_port_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        port_scrollbar.config(command=self.editor_port_listbox.yview)

        # 항구 목록 채우기
        for port in PORTS.keys():
            self.editor_port_listbox.insert(tk.END, f"{port} ({len(PORTS[port])}개)")

        # 항구 선택 시 선사 목록 업데이트
        self.editor_port_listbox.bind('<<ListboxSelect>>', lambda e: self.on_editor_port_select(e))

        # 항구 버튼
        port_btn_frame = ttk.Frame(left_frame)
        port_btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(port_btn_frame, text="이름 수정", command=lambda: self.edit_port_name(editor_win)).pack(side=tk.LEFT, padx=2)
        ttk.Button(port_btn_frame, text="삭제", command=lambda: self.delete_port(editor_win)).pack(side=tk.LEFT, padx=2)

        # 오른쪽: 선사 목록
        right_frame = ttk.LabelFrame(paned, text="선사 목록", padding="5")
        paned.add(right_frame, weight=2)

        # 선사 리스트박스
        provider_list_frame = ttk.Frame(right_frame)
        provider_list_frame.pack(fill=tk.BOTH, expand=True)

        provider_scrollbar = ttk.Scrollbar(provider_list_frame)
        provider_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.editor_provider_listbox = tk.Listbox(provider_list_frame, yscrollcommand=provider_scrollbar.set,
                                                   font=("맑은 고딕", 10), height=15)
        self.editor_provider_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        provider_scrollbar.config(command=self.editor_provider_listbox.yview)

        # 선사 버튼
        provider_btn_frame = ttk.Frame(right_frame)
        provider_btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(provider_btn_frame, text="이름 수정", command=lambda: self.edit_provider_name(editor_win)).pack(side=tk.LEFT, padx=2)
        ttk.Button(provider_btn_frame, text="삭제", command=lambda: self.delete_provider(editor_win)).pack(side=tk.LEFT, padx=2)

        # 하단 버튼
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X, pady=10)
        ttk.Button(bottom_frame, text="💾 저장", command=lambda: self.save_ports_edit(editor_win), width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(bottom_frame, text="❌ 취소", command=editor_win.destroy, width=15).pack(side=tk.LEFT, padx=5)

        # 편집용 데이터 복사본 생성
        self.edited_ports = {}
        for port, providers in PORTS.items():
            self.edited_ports[port] = dict(providers)

        self.current_edit_port = None
        self.modified_providers = set()  # 수정된 선사 추적 (port_name::provider_name 형식)

        # 선사 더블클릭/엔터 시 이름 수정
        self.editor_provider_listbox.bind('<Double-Button-1>', lambda e: self.edit_provider_name(editor_win))
        self.editor_provider_listbox.bind('<Return>', lambda e: self.edit_provider_name(editor_win))

    def on_editor_port_select(self, event):
        """항구 선택 시 선사 목록 업데이트"""
        selection = self.editor_port_listbox.curselection()
        if not selection:
            return

        # 선택된 항구 이름 추출 (개수 부분 제거)
        port_text = self.editor_port_listbox.get(selection[0])
        port_name = port_text.rsplit(' (', 1)[0]
        self.current_edit_port = port_name

        # 선사 목록 갱신
        self.refresh_provider_listbox()

    def refresh_provider_listbox(self):
        """현재 선택된 항구의 선사 목록 갱신 (수정된 선사를 맨 위에 표시)"""
        if not self.current_edit_port:
            return

        port_name = self.current_edit_port

        # 선사 리스트박스 업데이트
        self.editor_provider_listbox.delete(0, tk.END)
        if port_name in self.edited_ports:
            # 수정된 선사와 수정되지 않은 선사 분리
            modified_list = []
            unmodified_list = []

            for provider, path in self.edited_ports[port_name].items():
                key = f"{port_name}::{provider}"
                path_str = path if path else "(봇 없음)"
                item = (provider, path_str, key in self.modified_providers)

                if key in self.modified_providers:
                    modified_list.append(item)
                else:
                    unmodified_list.append(item)

            # 수정된 선사를 먼저 표시 (빨간색)
            idx = 0
            for provider, path_str, is_modified in modified_list:
                self.editor_provider_listbox.insert(tk.END, f"{provider}  →  {path_str}")
                self.editor_provider_listbox.itemconfig(idx, fg='red')
                idx += 1

            # 수정되지 않은 선사 표시
            for provider, path_str, is_modified in unmodified_list:
                self.editor_provider_listbox.insert(tk.END, f"{provider}  →  {path_str}")
                idx += 1

    def edit_port_name(self, parent):
        """항구 이름 수정"""
        selection = self.editor_port_listbox.curselection()
        if not selection:
            messagebox.showwarning("경고", "수정할 항구를 선택해주세요.", parent=parent)
            return

        port_text = self.editor_port_listbox.get(selection[0])
        old_name = port_text.rsplit(' (', 1)[0]

        # 입력 다이얼로그
        new_name = self.simple_input_dialog(parent, "항구 이름 수정", "새 항구 이름:", old_name)
        if new_name and new_name != old_name:
            if new_name in self.edited_ports:
                messagebox.showwarning("경고", "이미 존재하는 항구 이름입니다.", parent=parent)
                return

            # 이름 변경
            self.edited_ports[new_name] = self.edited_ports.pop(old_name)
            self.current_edit_port = new_name

            # 리스트 업데이트
            self.refresh_port_listbox()
            self.log(f"✏️ 항구 이름 변경: {old_name} → {new_name}")

    def delete_port(self, parent):
        """항구 삭제"""
        selection = self.editor_port_listbox.curselection()
        if not selection:
            messagebox.showwarning("경고", "삭제할 항구를 선택해주세요.", parent=parent)
            return

        port_text = self.editor_port_listbox.get(selection[0])
        port_name = port_text.rsplit(' (', 1)[0]

        if messagebox.askyesno("확인", f"'{port_name}' 항구를 삭제하시겠습니까?\n\n포함된 모든 선사도 함께 삭제됩니다.", parent=parent):
            del self.edited_ports[port_name]
            self.current_edit_port = None
            self.refresh_port_listbox()
            self.editor_provider_listbox.delete(0, tk.END)
            self.log(f"🗑️ 항구 삭제: {port_name}")

    def edit_provider_name(self, parent):
        """선사 이름 수정"""
        selection = self.editor_provider_listbox.curselection()
        if not selection:
            messagebox.showwarning("경고", "수정할 선사를 선택해주세요.", parent=parent)
            return

        if not self.current_edit_port:
            return

        provider_text = self.editor_provider_listbox.get(selection[0])
        old_name = provider_text.split('  →  ')[0]

        # 입력 다이얼로그
        new_name = self.simple_input_dialog(parent, "선사 이름 수정", "새 선사 이름:", old_name)
        if new_name and new_name != old_name:
            if new_name in self.edited_ports[self.current_edit_port]:
                messagebox.showwarning("경고", "이미 존재하는 선사 이름입니다.", parent=parent)
                return

            # 이름 변경 (경로는 유지)
            path = self.edited_ports[self.current_edit_port].pop(old_name)
            self.edited_ports[self.current_edit_port][new_name] = path

            # 수정된 선사 추적
            old_key = f"{self.current_edit_port}::{old_name}"
            new_key = f"{self.current_edit_port}::{new_name}"
            if old_key in self.modified_providers:
                self.modified_providers.remove(old_key)
            self.modified_providers.add(new_key)

            # 리스트 업데이트 (수정된 이름으로 갱신)
            self.refresh_provider_listbox()
            self.refresh_port_listbox()
            self.log(f"✏️ 선사 이름 변경: {old_name} → {new_name}")

    def delete_provider(self, parent):
        """선사 삭제"""
        selection = self.editor_provider_listbox.curselection()
        if not selection:
            messagebox.showwarning("경고", "삭제할 선사를 선택해주세요.", parent=parent)
            return

        if not self.current_edit_port:
            return

        provider_text = self.editor_provider_listbox.get(selection[0])
        provider_name = provider_text.split('  →  ')[0]

        if messagebox.askyesno("확인", f"'{provider_name}' 선사를 삭제하시겠습니까?", parent=parent):
            del self.edited_ports[self.current_edit_port][provider_name]
            self.on_editor_port_select(None)
            self.refresh_port_listbox()
            self.log(f"🗑️ 선사 삭제: {provider_name}")

    def refresh_port_listbox(self):
        """항구 리스트박스 새로고침"""
        self.editor_port_listbox.delete(0, tk.END)
        for port in self.edited_ports.keys():
            self.editor_port_listbox.insert(tk.END, f"{port} ({len(self.edited_ports[port])}개)")

    def simple_input_dialog(self, parent, title, prompt, initial_value=""):
        """간단한 입력 다이얼로그"""
        dialog = tk.Toplevel(parent)
        dialog.title(title)

        # 창 크기 및 화면 중앙 위치 계산
        win_width = 350
        win_height = 120
        screen_width = dialog.winfo_screenwidth()
        screen_height = dialog.winfo_screenheight()
        x = (screen_width - win_width) // 2
        y = (screen_height - win_height) // 2
        dialog.geometry(f"{win_width}x{win_height}+{x}+{y}")

        dialog.resizable(False, False)
        dialog.transient(parent)
        dialog.grab_set()

        ttk.Label(dialog, text=prompt).pack(pady=(15, 5))

        entry_var = tk.StringVar(value=initial_value)
        entry = ttk.Entry(dialog, textvariable=entry_var, width=40)
        entry.pack(pady=5)
        entry.select_range(0, tk.END)
        entry.focus_set()

        result = [None]

        def on_ok():
            result[0] = entry_var.get().strip()
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="확인", command=on_ok, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="취소", command=on_cancel, width=10).pack(side=tk.LEFT, padx=5)

        entry.bind('<Return>', lambda e: on_ok())
        entry.bind('<Escape>', lambda e: on_cancel())

        dialog.wait_window()
        return result[0]

    def save_ports_edit(self, parent):
        """편집된 항구/선사 정보를 파일에 저장"""
        import re
        import locale

        try:
            launcher_path = os.path.join(BASE_DIR, "쭈갑예약_Bot_Launcher.py")

            with open(launcher_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # PORTS 딕셔너리 부분 찾기
            ports_pattern = r'PORTS\s*=\s*\{.*?\n\}'

            # 선사 이름 ㄱㄴㄷ 순 정렬 함수
            def korean_sort_key(name):
                """한글 자모 순서로 정렬하기 위한 키"""
                return locale.strxfrm(name)

            # 로케일 설정 (한글 정렬용)
            try:
                locale.setlocale(locale.LC_COLLATE, 'ko_KR.UTF-8')
            except:
                try:
                    locale.setlocale(locale.LC_COLLATE, 'Korean_Korea.949')
                except:
                    pass  # 기본 정렬 사용

            # 새 PORTS 문자열 생성 (선사 이름 ㄱㄴㄷ순 정렬)
            new_ports_str = "PORTS = {\n"
            for port, providers in self.edited_ports.items():
                new_ports_str += f'    "{port}": {{\n'
                # 선사 이름 ㄱㄴㄷ순 정렬
                sorted_providers = sorted(providers.items(), key=lambda x: korean_sort_key(x[0]))
                for provider, path in sorted_providers:
                    if path:
                        new_ports_str += f'        "{provider}": "{path}",\n'
                    else:
                        new_ports_str += f'        "{provider}": None,\n'
                new_ports_str += '    },\n'
            new_ports_str += "}"

            # PORTS 블록 찾아서 교체
            # 더 정확한 패턴: PORTS = { 로 시작해서 닫는 } 까지
            match = re.search(r'(PORTS\s*=\s*\{)', content)
            if match:
                start = match.start()
                # 중첩된 중괄호 처리
                brace_count = 0
                end = start
                for i, char in enumerate(content[start:]):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end = start + i + 1
                            break

                content = content[:start] + new_ports_str + content[end:]

                with open(launcher_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                self.log("✅ 항구/선사 정보가 저장되었습니다.")
                messagebox.showinfo("저장 완료",
                    "항구/선사 정보가 저장되었습니다.\n\n변경사항을 적용하려면 프로그램을 재시작해주세요.",
                    parent=parent)
                parent.destroy()
            else:
                messagebox.showerror("오류", "PORTS 데이터를 찾을 수 없습니다.", parent=parent)

        except Exception as e:
            self.log(f"❌ 저장 오류: {e}")
            messagebox.showerror("오류", f"저장 중 오류가 발생했습니다:\n{e}", parent=parent)

if __name__ == "__main__":
    if not os.path.exists(CONFIG_DIR): os.makedirs(CONFIG_DIR)
    root = tk.Tk()
    app = FishingLauncher(root)
    root.mainloop()
