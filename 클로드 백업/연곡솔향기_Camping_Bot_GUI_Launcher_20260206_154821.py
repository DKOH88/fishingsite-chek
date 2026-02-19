import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import os
import json
import threading
from datetime import datetime

# ============================================================
# 기본 설정값
# ============================================================
DEFAULT_YEAR = 2026
DEFAULT_MONTH = 1
DEFAULT_DAY = 6
DEFAULT_PERIOD = "1"  # 1: 1박2일, 2: 2박3일...
DEFAULT_PRE_REFRESH = 6  # 사전 새로고침 기본 시간(초)

# 절대 경로 기반으로 스크립트 및 설정 파일 경로 결정
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_SCRIPT = os.path.join(_SCRIPT_DIR, "camping_bot_v9.py")
SETTINGS_FILE = os.path.join(_SCRIPT_DIR, "launcher_settings_main.json")

# [로그 경로]
LOG_TARGET_DIR = r"C:\gemini\logs\연곡"

# 우선순위 로테이션 생성 함수
def generate_rotated_list(items):
    result = []
    n = len(items)
    for i in range(n):
        rotated = items[i:] + items[:i]
        result.append(", ".join(map(str, rotated)))
    return result

# 구역별 설정 (좌석 옵션 리스트 & 설명 텍스트)
ZONE_INFO = {
    "B(2)-일반형데크": {
        "li": 2,
        "options": generate_rotated_list([
            192, 191, 190, 189, 188, 82, 81, 80, 79, 78, 77, 76, 75, 74,
            73, 72, 71, 70, 69, 68, 67, 66, 65, 64, 63, 62, 61, 60, 59,
            58, 57, 56, 55, 54, 53, 52, 51, 50, 49, 48, 47, 46, 45, 44, 43, 42
        ]),
        "desc": "B201(42)~B241(82) / B242(188)~B246(192)"
    },
    "D(4)-카라반": {
        "li": 4,
        "options": generate_rotated_list([
            168, 169, 170, 171, 172, 174, 175, 177
        ]),
        "desc": "D701=168 ~ D709=177 (D706 장애인 제외)"
    },
    "E(5)-차박": {
        "li": 5,
        "options": generate_rotated_list([
            123, 124, 125, 126, 127
        ]),
        "desc": "123=오른쪽 사이드 / 127=왼쪽 사이드"
    },
    "H(7)-고급카라반": {
        "li": 7,
        "options": generate_rotated_list([
            193, 194, 195
        ]),
        "desc": "193=오른쪽 / 195=호텔형(조리불가)"
    }
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
]

class CampingBotLauncherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🏕️ 메인 캠핑 예약 런처 GUI v2.2 (CLI 연동)")

        # 화면 중앙 배치
        window_width = 750
        window_height = 830

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        center_x = int((screen_width / 2) - (window_width / 2))
        center_y = int((screen_height / 2) - (window_height / 2))

        self.root.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")
        self.root.resizable(False, False)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.processes = []  # [{"proc": Popen, "id": int, "zone": str}]
        self._is_launching = False  # 중복 실행 방지 플래그
        self._monitor_job = None   # 모니터링 after job ID

        self.create_widgets()
        self.load_settings()

    def create_widgets(self):
        # 1. 날짜 및 공통 옵션 설정 프레임
        target_frame = ttk.LabelFrame(self.root, text="📅 예약 공통 설정", padding=15)
        target_frame.pack(fill="x", padx=10, pady=10)

        # [행 1] 년/월/일 입력
        frame_date = ttk.Frame(target_frame)
        frame_date.pack(fill="x", pady=5)

        ttk.Label(frame_date, text="년도:").pack(side="left")
        self.entry_year = ttk.Entry(frame_date, width=6, justify="center")
        self.entry_year.insert(0, str(DEFAULT_YEAR))
        self.entry_year.pack(side="left", padx=5)

        ttk.Label(frame_date, text="월:").pack(side="left")
        self.combo_month = ttk.Combobox(frame_date, values=[str(i) for i in range(1, 13)], state="readonly", width=4, justify="center")
        self.combo_month.set(str(DEFAULT_MONTH))
        self.combo_month.pack(side="left", padx=5)

        ttk.Label(frame_date, text="일:").pack(side="left")
        self.combo_day = ttk.Combobox(frame_date, values=[str(i) for i in range(1, 32)], state="readonly", width=4, justify="center")
        self.combo_day.set(str(DEFAULT_DAY))
        self.combo_day.pack(side="left", padx=5)

        # [행 2] 숙박 기간 및 사전새로고침
        frame_opt = ttk.Frame(target_frame)
        frame_opt.pack(fill="x", pady=5)

        ttk.Label(frame_opt, text="숙박 기간:").pack(side="left")
        self.combo_period = ttk.Combobox(frame_opt, values=["1박 2일", "2박 3일", "3박 4일"], state="readonly", width=10)
        self.combo_period.set("1박 2일")
        self.combo_period.pack(side="left", padx=5)

        ttk.Label(frame_opt, text="사전새로고침(초):").pack(side="left", padx=(20, 0))
        self.entry_pre_refresh = ttk.Entry(frame_opt, width=5, justify="center")
        self.entry_pre_refresh.insert(0, str(DEFAULT_PRE_REFRESH))
        self.entry_pre_refresh.pack(side="left", padx=5)

        # 2. 봇 인스턴스 설정 (구역/좌석 우선순위 포함)
        bot_frame = ttk.LabelFrame(self.root, text="🤖 봇 인스턴스별 맞춤 설정", padding=15)
        bot_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.instance_vars = []
        self.auto_lead_vars = []
        self.time_entries = []
        self.zone_combos = []
        self.seat_combos = []
        self.desc_labels = []
        self.status_labels = []  # 프로세스 상태 라벨

        # [Grid Headers]
        ttk.Label(bot_frame, text="번호", width=4, anchor="center").grid(row=0, column=0, pady=(0, 5))
        ttk.Label(bot_frame, text="사용", width=4, anchor="center").grid(row=0, column=1, pady=(0, 5))
        ttk.Label(bot_frame, text="구역 선택", width=16, anchor="center").grid(row=0, column=2, pady=(0, 5))
        ttk.Label(bot_frame, text="좌석 우선순위", width=22, anchor="center").grid(row=0, column=3, pady=(0, 5))
        ttk.Label(bot_frame, text="리드타임", width=10, anchor="center").grid(row=0, column=4, pady=(0, 5))
        ttk.Label(bot_frame, text="Auto", width=6, anchor="center").grid(row=0, column=5, pady=(0, 5))
        ttk.Label(bot_frame, text="설명", width=8, anchor="center").grid(row=0, column=6, pady=(0, 5))
        ttk.Label(bot_frame, text="상태", width=6, anchor="center").grid(row=0, column=7, pady=(0, 5))

        # 3. 봇 인스턴스 설정 기초 데이타
        default_leads = [0.6, 0.63, 0.65, 0.68]
        default_desc = ["600ms", "630ms", "650ms", "680ms"]
        default_enables = [True, True, False, False]
        default_auto = [True, True, True, True]

        for i in range(4):
            row_idx = i + 1

            # Instance Number
            ttk.Label(bot_frame, text=f"{i+1}번", width=4, anchor="center").grid(row=row_idx, column=0, pady=5)

            var_enable = tk.BooleanVar(value=default_enables[i])
            chk = ttk.Checkbutton(bot_frame, variable=var_enable)
            chk.grid(row=row_idx, column=1, pady=5)
            self.instance_vars.append(var_enable)

            # Zone Selection
            cb_zone = ttk.Combobox(bot_frame, values=list(ZONE_INFO.keys()), state="readonly", width=14)
            cb_zone.current(0)
            cb_zone.grid(row=row_idx, column=2, padx=5, pady=5)
            self.zone_combos.append(cb_zone)

            # Seat Priority
            cb_seats = ttk.Combobox(bot_frame, state="readonly", width=22)
            cb_seats.grid(row=row_idx, column=3, padx=5, pady=5)
            self.seat_combos.append(cb_seats)

            cb_zone.bind("<<ComboboxSelected>>", lambda event, idx=i: self.on_zone_change(event, idx))

            entry_time = ttk.Entry(bot_frame, width=8, justify="center")
            entry_time.insert(0, str(default_leads[i]))
            entry_time.grid(row=row_idx, column=4, padx=5, pady=5)
            self.time_entries.append(entry_time)

            var_auto = tk.BooleanVar(value=default_auto[i])
            chk_auto = ttk.Checkbutton(bot_frame, variable=var_auto)
            chk_auto.grid(row=row_idx, column=5, pady=5)
            self.auto_lead_vars.append(var_auto)

            entry_time.bind("<KeyRelease>", lambda event, idx=i: self.on_lead_time_change(event, idx))

            lbl_desc = ttk.Label(bot_frame, text=default_desc[i], width=8, anchor="center", foreground="gray")
            lbl_desc.grid(row=row_idx, column=6, pady=5)
            self.desc_labels.append(lbl_desc)

            # 상태 라벨
            lbl_status = ttk.Label(bot_frame, text="-", width=6, anchor="center", foreground="gray")
            lbl_status.grid(row=row_idx, column=7, pady=5)
            self.status_labels.append(lbl_status)

        # Grid column configure for centering
        for col in range(8):
            bot_frame.columnconfigure(col, weight=1)

        # 사용자 요청 텍스트 추가 (4번 봇 아래 빈 공간)
        info_text = (
            "\n"
            "*고급 카라반\n"
            "-193(H901): 오른쪽, 침대없음\n"
            "-194(H902): 중간, 침대\n"
            "-195(H903): 왼쪽, 조리불가, 침대\n\n"
            "*차박\n"
            "-123(E503): 오른쪽\n"
            "-127(E507): 왼쪽"
        )
        ttk.Label(bot_frame, text=info_text, justify="left", font=("Consolas", 9), foreground="blue").grid(row=5, column=0, columnspan=8, pady=10, sticky="w", padx=20)

        # 4. 실행 버튼 및 로그
        action_frame = ttk.Frame(self.root, padding=10)
        action_frame.pack(fill="both", expand=True)

        self.var_test_mode = tk.BooleanVar(value=False)
        self.chk_test_mode = ttk.Checkbutton(action_frame, text="🧪 테스트 모드 (캡차 입력까지만 실행하고 중단)", variable=self.var_test_mode)
        self.chk_test_mode.pack(fill="x", pady=2)

        self.btn_start = ttk.Button(action_frame, text="🚀 멀티 봇 실행 시작 (Start / F2)", command=self.start_bots)
        self.btn_start.pack(fill="x", pady=5, ipady=5)

        self.btn_stop = ttk.Button(action_frame, text="🛑 실행 중인 봇 모두 종료 (Stop / F3)", command=self.stop_bots)
        self.btn_stop.pack(fill="x", pady=5)

        # 단축키 바인딩
        self.root.bind('<F2>', lambda e: self.start_bots())
        self.root.bind('<F3>', lambda e: self.stop_bots())

        self.log_area = tk.Text(action_frame, height=10, state="disabled", font=("Consolas", 9))
        self.log_area.pack(fill="both", expand=True, pady=5)

        self.log("✅ 메인 컴퓨터용 멀티 런처 준비 완료")
        self.log(f"ℹ️ 인스턴스별로 서로 다른 구역과 좌석을 설정할 수 있습니다.")

        # Initialize seat options for all rows
        for i in range(4):
            self.on_zone_change(None, i)

    def on_lead_time_change(self, event, idx):
        try:
            val_str = self.time_entries[idx].get()
            if not val_str:
                self.desc_labels[idx].config(text="???")
                return
            val_float = float(val_str)
            ms_val = int(val_float * 1000)
            self.desc_labels[idx].config(text=f"{ms_val}ms")
        except ValueError:
            self.desc_labels[idx].config(text="Invalid")

    def on_zone_change(self, event, idx):
        selected_zone = self.zone_combos[idx].get()
        if selected_zone in ZONE_INFO:
            data = ZONE_INFO[selected_zone]
            self.seat_combos[idx]['values'] = data['options']
            self.seat_combos[idx].current(0)

    def save_settings(self):
        settings = {
            "year": self.entry_year.get(),
            "month": self.combo_month.get(),
            "day": self.combo_day.get(),
            "period_idx": self.combo_period.current(),
            "pre_refresh": self.entry_pre_refresh.get(),
            "instance_enabled": [v.get() for v in self.instance_vars],
            "lead_times": [e.get() for e in self.time_entries],
            "auto_lead_enabled": [v.get() for v in self.auto_lead_vars],
            "instance_zones": [c.get() for c in self.zone_combos],
            "instance_seats": [c.get() for c in self.seat_combos],
            "test_mode": self.var_test_mode.get()
        }
        try:
            with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=4)
        except OSError as e:
            self.log(f"⚠️ 설정 저장 실패: {e}")

    def load_settings(self):
        if not os.path.exists(SETTINGS_FILE):
            return

        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                settings = json.load(f)

            if "year" in settings:
                self.entry_year.delete(0, tk.END)
                self.entry_year.insert(0, settings["year"])
            if "month" in settings: self.combo_month.set(settings["month"])
            if "day" in settings: self.combo_day.set(settings["day"])
            if "period_idx" in settings:
                try:
                    self.combo_period.current(settings["period_idx"])
                except (tk.TclError, IndexError):
                    pass
            if "pre_refresh" in settings:
                self.entry_pre_refresh.delete(0, tk.END)
                self.entry_pre_refresh.insert(0, str(settings["pre_refresh"]))

            if "instance_enabled" in settings:
                for i, val in enumerate(settings["instance_enabled"]):
                    if i < len(self.instance_vars):
                        self.instance_vars[i].set(val)

            if "lead_times" in settings:
                for i, val in enumerate(settings["lead_times"]):
                    if i < len(self.time_entries):
                        self.time_entries[i].delete(0, tk.END)
                        self.time_entries[i].insert(0, str(val))
                        self.on_lead_time_change(None, i)

            if "auto_lead_enabled" in settings:
                for i, val in enumerate(settings["auto_lead_enabled"]):
                    if i < len(self.auto_lead_vars):
                        self.auto_lead_vars[i].set(val)

            # Load per-instance zone/seats (구역 불일치 검증 포함)
            if "instance_zones" in settings:
                for i, val in enumerate(settings["instance_zones"]):
                    if i < len(self.zone_combos):
                        if val in ZONE_INFO:
                            self.zone_combos[i].set(val)
                        else:
                            self.log(f"⚠️ 인스턴스 #{i+1}: 저장된 구역 '{val}'이 존재하지 않아 기본값 사용")
                            self.zone_combos[i].current(0)
                        self.on_zone_change(None, i)

            if "instance_seats" in settings:
                for i, val in enumerate(settings["instance_seats"]):
                    if i < len(self.seat_combos):
                        available = list(self.seat_combos[i]['values'])
                        if val in available:
                            self.seat_combos[i].set(val)
                        else:
                            self.log(f"⚠️ 인스턴스 #{i+1}: 저장된 좌석 설정이 현재 구역과 맞지 않아 기본값 사용")
                            if available:
                                self.seat_combos[i].current(0)

            if "test_mode" in settings:
                self.var_test_mode.set(settings["test_mode"])

            self.log("📂 이전 설정을 불러왔습니다.")
        except (json.JSONDecodeError, OSError) as e:
            self.log(f"⚠️ 설정 로드 실패: {e}")

    def on_close(self):
        self.save_settings()
        self.stop_bots()
        # 프로세스 종료 대기 후 창 닫기
        self.root.after(300, self.root.destroy)

    def log(self, message):
        self.log_area.configure(state="normal")
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_area.insert("end", f"[{timestamp}] {message}\n")
        self.log_area.see("end")
        self.log_area.configure(state="disabled")

    def _log_threadsafe(self, message):
        """워커 스레드에서 안전하게 로그를 남기기 위한 메서드"""
        self.root.after(0, self.log, message)

    def get_period_value(self):
        val = self.combo_period.get()
        if "1박" in val: return "1"
        if "2박" in val: return "2"
        if "3박" in val: return "3"
        return "1"

    def _validate_date(self, year, month, day):
        """날짜 유효성 검증"""
        try:
            datetime(year, month, day)
            return True
        except ValueError:
            return False

    def start_bots(self):
        # 중복 실행 방지
        if self._is_launching:
            return

        # 스크립트 파일 존재 확인
        if not os.path.exists(BASE_SCRIPT):
            messagebox.showerror("오류", f"봇 스크립트를 찾을 수 없습니다:\n{BASE_SCRIPT}")
            return

        try:
            year = int(self.entry_year.get())
            month = int(self.combo_month.get())
            day = int(self.combo_day.get())
            period = self.get_period_value()
            test_mode = self.var_test_mode.get()
        except ValueError:
            messagebox.showerror("오류", "날짜는 숫자여야 합니다.")
            return

        # 날짜 유효성 검증
        if not self._validate_date(year, month, day):
            messagebox.showerror("오류", f"{year}년 {month}월 {day}일은 유효하지 않은 날짜입니다.")
            return

        # 사전 새로고침 시간 검증
        try:
            pre_refresh_sec = int(self.entry_pre_refresh.get())
            if pre_refresh_sec < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("오류", "사전 새로고침 시간은 0 이상의 정수여야 합니다.")
            return

        active_configs = []
        for i in range(4):
            if self.instance_vars[i].get():
                try:
                    lead_time = float(self.time_entries[i].get())
                    auto_lead_val = self.auto_lead_vars[i].get()

                    sel_zone = self.zone_combos[i].get()
                    li_index = ZONE_INFO[sel_zone]["li"] if sel_zone in ZONE_INFO else 5

                    raw_seats = self.seat_combos[i].get().split(',')
                    seat_priority = [s.strip() for s in raw_seats if s.strip()]
                    seat_priority_str = ",".join(seat_priority)

                    if not seat_priority:
                        self.log(f"⚠️ 인스턴스 #{i+1} 좌석 정보 없음 -> 스킵")
                        continue

                    active_configs.append({
                        "id": i + 1,
                        "refresh_lead_time": lead_time,
                        "year": year, "month": month, "day": day,
                        "li": li_index,
                        "period": period,
                        "seat_priority": seat_priority_str,
                        "auto_lead": auto_lead_val,
                        "zone_name": sel_zone,
                        "test_mode": test_mode,
                        "pre_refresh": pre_refresh_sec
                    })
                except ValueError:
                    messagebox.showerror("오류", f"인스턴스 #{i+1}의 리드타임이 숫자가 아닙니다.")
                    return

        if not active_configs:
            messagebox.showwarning("알림", "실행할 활성 봇 인스턴스가 없습니다.")
            return

        self.save_settings()

        self.log("🧹 기존 프로세스 정리 중...")
        self.stop_bots()

        # 버튼 비활성화 (중복 실행 방지)
        self._is_launching = True
        self.btn_start.configure(state="disabled")

        self.log(f"🚀 총 {len(active_configs)}개의 봇 실행을 시작합니다...")

        # 별도 스레드에서 순차 실행 (GUI 블로킹 방지)
        thread = threading.Thread(
            target=self._launch_bots_worker,
            args=(active_configs,),
            daemon=True
        )
        thread.start()

    def _launch_bots_worker(self, active_configs):
        """워커 스레드: 봇 프로세스를 순차적으로 실행"""
        import time as _time

        for config in active_configs:
            cmd = [
                "python", BASE_SCRIPT,
                "--instance-id", str(config["id"]),
                "--year", str(config["year"]),
                "--month", str(config["month"]),
                "--day", str(config["day"]),
                "--li-index", str(config["li"]),
                "--period", str(config["period"]),
                "--lead-time", str(config["refresh_lead_time"]),
                "--seat-priority", config["seat_priority"],
                "--pre-refresh", str(config["pre_refresh"])
            ]

            if config["auto_lead"]:
                cmd.append("--auto-lead-time")
            else:
                cmd.append("--no-auto-lead-time")

            if config["test_mode"]:
                cmd.append("--test-mode")

            idx = config['id']
            user_agent = USER_AGENTS[(idx - 1) % len(USER_AGENTS)]
            cmd.extend(["--user-agent", user_agent])

            creation_flags = subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0

            try:
                proc = subprocess.Popen(cmd, creationflags=creation_flags)
                self.processes.append({"proc": proc, "id": config["id"], "zone": config["zone_name"]})

                auto_msg = "⚡Auto" if config["auto_lead"] else "🚫Manual"
                self._log_threadsafe(
                    f" ▶ 인스턴스 #{config['id']} ({config['zone_name']}) 실행됨 "
                    f"(Lead: {config['refresh_lead_time']}s, Pre: {config['pre_refresh']}s, {auto_msg})"
                )

                _time.sleep(1.5)
            except FileNotFoundError:
                self._log_threadsafe(f" ❌ 실행 실패 (#{config['id']}): python 실행 파일을 찾을 수 없습니다.")
            except OSError as e:
                self._log_threadsafe(f" ❌ 실행 실패 (#{config['id']}): {e}")

        self._log_threadsafe("✅ 모든 명령이 전달되었습니다. (현황 창들을 확인하세요)")

        # 실행 완료 후 버튼 재활성화 + 모니터링 시작
        self.root.after(0, self._on_launch_complete)

    def _on_launch_complete(self):
        """봇 실행 완료 후 GUI 스레드에서 호출"""
        self._is_launching = False
        self.btn_start.configure(state="normal")
        self._start_monitoring()

    def _start_monitoring(self):
        """프로세스 상태 주기적 모니터링 시작"""
        if self._monitor_job is not None:
            self.root.after_cancel(self._monitor_job)
        self._check_processes()

    def _check_processes(self):
        """3초마다 프로세스 상태를 확인하고 상태 라벨 업데이트"""
        # 상태 라벨 초기화
        for lbl in self.status_labels:
            lbl.config(text="-", foreground="gray")

        still_running = False
        for item in self.processes:
            proc = item["proc"]
            inst_id = item["id"]
            idx = inst_id - 1  # 0-based index

            if idx >= len(self.status_labels):
                continue

            returncode = proc.poll()
            if returncode is None:
                # 실행 중
                self.status_labels[idx].config(text="실행중", foreground="green")
                still_running = True
            elif returncode == 0:
                self.status_labels[idx].config(text="완료", foreground="blue")
            else:
                self.status_labels[idx].config(text=f"종료({returncode})", foreground="red")
                self.log(f"⚠️ 인스턴스 #{inst_id} ({item['zone']}) 비정상 종료 (코드: {returncode})")
                # 중복 로그 방지: returncode를 표시한 뒤 processes에서 제거
                item["_logged"] = True

        # 이미 로그된 비정상 종료 항목 제거 (중복 로그 방지)
        self.processes = [p for p in self.processes if p["proc"].poll() is None or not p.get("_logged")]

        if still_running or self.processes:
            self._monitor_job = self.root.after(3000, self._check_processes)
        else:
            self._monitor_job = None

    def stop_bots(self):
        # 모니터링 중지
        if self._monitor_job is not None:
            self.root.after_cancel(self._monitor_job)
            self._monitor_job = None

        count = 0
        for item in self.processes:
            proc = item["proc"]
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    try:
                        proc.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        pass
                count += 1

        self.processes = []

        # 상태 라벨 초기화
        for lbl in self.status_labels:
            lbl.config(text="-", foreground="gray")

        if count > 0:
            self.log(f"🛑 실행 중인 봇 {count}개를 종료했습니다.")

if __name__ == "__main__":
    root = tk.Tk()
    app = CampingBotLauncherApp(root)
    root.mainloop()
