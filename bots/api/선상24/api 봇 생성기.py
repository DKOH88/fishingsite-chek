# -*- coding: utf-8 -*-
"""
선상24 API 봇 생성기 GUI
ttkbootstrap 적용 모던 UI
예약 ID 자동 조회 기능 포함
"""
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import messagebox
import tkinter as tk
import re
import os
import calendar
from datetime import datetime
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 항구 목록 (런처 등록용) - 런처와 동일하게 유지
PORTS = ["오천항", "안흥·신진항", "영흥도", "삼길포항", "대천항",
         "마검포항", "무창포항", "영목항", "인천", "구매항",
         "남당항", "대야도", "백사장항", "여수", "녹동항",
         "평택항", "전곡항", "홍원항"]


class SunSang24BotGeneratorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🚢 선상24 API 봇 생성기")

        # 창 크기 및 위치
        win_width = 1100
        win_height = 2000
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - win_width) // 2
        y = max(0, (screen_height - win_height) // 2 - 50)
        self.root.geometry(f"{win_width}x{win_height}+{x}+{y}")
        self.root.resizable(True, True)

        # 현재 디렉토리
        self.current_dir = os.path.dirname(os.path.abspath(__file__))

        # 선사명 입력 완료 플래그
        self.provider_name_ready = False
        self.provider_name_timer = None

        # ID 매핑 데이터
        self.id_mapping_data = {}
        self.dynamic_mapping_mode = False  # 맵핑없음(동적 조회) 모드

        # 선사명 목록 (조회용)
        self.ship_names_found = set()

        self.create_widgets()
        self.load_existing_bots()

    def create_widgets(self):
        """위젯 생성"""
        # 스크롤 가능한 캔버스
        canvas = tk.Canvas(self.root)
        scrollbar = ttk.Scrollbar(self.root, orient=VERTICAL, command=canvas.yview, bootstyle="round")
        self.scrollable_frame = ttk.Frame(canvas, padding="15")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.pack(side=RIGHT, fill=Y)

        # 마우스 휠 바인딩
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", on_mousewheel)

        self.main_frame = self.scrollable_frame

        # ============================================================
        # 제목 + 도움말
        # ============================================================
        title_frame = ttk.Frame(self.main_frame)
        title_frame.pack(fill=X, pady=(0, 15))
        ttk.Label(title_frame, text="🚢 선상24 API 봇 생성기", font=("맑은 고딕", 16, "bold"), bootstyle="primary").pack(side=LEFT)
        ttk.Button(title_frame, text="❓ 도움말", command=self.show_help, bootstyle="secondary-outline", width=12).pack(side=RIGHT)

        # ============================================================
        # 기존 봇 목록
        # ============================================================
        existing_frame = ttk.Labelframe(self.main_frame, text="📋 기존 API 봇 목록", padding="10", bootstyle="info")
        existing_frame.pack(fill=X, pady=(0, 10))

        list_frame = ttk.Frame(existing_frame)
        list_frame.pack(fill=X)

        self.bot_listbox = tk.Listbox(list_frame, height=4, font=("Consolas", 10), bg="#1e1e1e", fg="#d4d4d4", selectbackground="#0078d4")
        self.bot_listbox.pack(fill=X, side=LEFT, expand=True)
        self.bot_listbox.bind('<<ListboxSelect>>', self.on_bot_select)

        scrollbar2 = ttk.Scrollbar(list_frame, orient=VERTICAL, command=self.bot_listbox.yview, bootstyle="round")
        scrollbar2.pack(side=RIGHT, fill=Y)
        self.bot_listbox.config(yscrollcommand=scrollbar2.set)

        # ============================================================
        # [1] URL 입력
        # ============================================================
        url_frame = ttk.Labelframe(self.main_frame, text="[1] 선상24 URL 입력 (자동 분석)", padding="10", bootstyle="danger")
        url_frame.pack(fill=X, pady=(0, 10))

        ttk.Label(url_frame, text="선상24 캘린더 URL:", font=("맑은 고딕", 10, "bold")).pack(anchor=W)
        ttk.Label(url_frame, text="예: https://bigboss24.sunsang24.com/ship/schedule_fleet/202609", font=("맑은 고딕", 8), foreground="gray").pack(anchor=W)
        self.url_entry = ttk.Entry(url_frame, width=80, font=("맑은 고딕", 10))
        self.url_entry.pack(fill=X, pady=(0, 5))

        btn_row = ttk.Frame(url_frame)
        btn_row.pack(anchor=W)
        ttk.Button(btn_row, text="🔍 URL 분석", command=self.parse_url, bootstyle="danger-outline", width=15).pack(side=LEFT, padx=(0, 10))
        ttk.Button(btn_row, text="🔄 리셋", command=self.reset_inputs, bootstyle="secondary-outline", width=10).pack(side=LEFT)

        # ============================================================
        # [2] 기본 정보
        # ============================================================
        info_frame = ttk.Labelframe(self.main_frame, text="[2] 기본 정보", padding="10", bootstyle="success")
        info_frame.pack(fill=X, pady=(0, 10))

        info_grid = ttk.Frame(info_frame)
        info_grid.pack(fill=X)

        # 선사명
        ttk.Label(info_grid, text="선사명 *:", font=("맑은 고딕", 9)).grid(row=0, column=0, sticky=W, pady=5)
        self.provider_name_entry = ttk.Entry(info_grid, width=20, font=("맑은 고딕", 10))
        self.provider_name_entry.grid(row=0, column=1, sticky=W, pady=5, padx=(5, 20))
        self.provider_name_entry.bind("<KeyRelease>", self.on_provider_name_change)
        self.provider_name_entry.bind("<FocusOut>", self.on_provider_name_focusout)

        # SUBDOMAIN
        ttk.Label(info_grid, text="SUBDOMAIN *:", font=("맑은 고딕", 9)).grid(row=0, column=2, sticky=W, pady=5)
        self.subdomain_entry = ttk.Entry(info_grid, width=20, font=("맑은 고딕", 10))
        self.subdomain_entry.grid(row=0, column=3, sticky=W, pady=5, padx=5)

        # BASE_URL
        ttk.Label(info_grid, text="BASE_URL *:", font=("맑은 고딕", 9)).grid(row=1, column=0, sticky=W, pady=5)
        self.base_url_entry = ttk.Entry(info_grid, width=70, font=("맑은 고딕", 10))
        self.base_url_entry.grid(row=1, column=1, columnspan=3, sticky=W, pady=5, padx=5)

        # ============================================================
        # [3] 예약 ID 자동 조회 ⭐ (핵심 기능)
        # ============================================================
        lookup_frame = ttk.Labelframe(self.main_frame, text="[3] 예약 ID 자동 조회 ⭐", padding="10", bootstyle="primary")
        lookup_frame.pack(fill=X, pady=(0, 10))

        ttk.Label(lookup_frame, text="선상24 schedule_fleet 페이지에서 data-schedule_no를 자동으로 추출합니다.",
                 font=("맑은 고딕", 9), foreground="gray").pack(anchor=W)

        lookup_grid = ttk.Frame(lookup_frame)
        lookup_grid.pack(fill=X, pady=(10, 0))

        # 년월 입력
        ttk.Label(lookup_grid, text="조회 년월:", font=("맑은 고딕", 9)).grid(row=0, column=0, sticky=W, pady=5)
        self.lookup_yearmonth_entry = ttk.Entry(lookup_grid, width=12, font=("맑은 고딕", 10))
        self.lookup_yearmonth_entry.grid(row=0, column=1, sticky=W, pady=5, padx=5)
        self.lookup_yearmonth_entry.insert(0, "2026")  # 기본값

        ttk.Label(lookup_grid, text="(YYYYMM: 단일 월 / YYYY: 연도 전체)", font=("맑은 고딕", 8), foreground="gray").grid(row=0, column=2, sticky=W, pady=5, padx=5)

        # 조회 버튼
        ttk.Button(lookup_grid, text="🔍 ID 자동 조회", command=self.lookup_schedule_ids, bootstyle="primary", width=18).grid(row=0, column=3, sticky=W, padx=10)

        # 조회 결과
        self.lookup_result_var = tk.StringVar(value="")
        ttk.Label(lookup_frame, textvariable=self.lookup_result_var, font=("맑은 고딕", 10, "bold"), bootstyle="info").pack(anchor=W, pady=(5, 0))

        # ============================================================
        # [4] 좌석 선택 설정
        # ============================================================
        seat_frame = ttk.Labelframe(self.main_frame, text="[4] 좌석 선택 설정", padding="10", bootstyle="warning")
        seat_frame.pack(fill=X, pady=(0, 10))

        self.has_seat_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(seat_frame, text="자리 선택 기능 있음 (HAS_SEAT_SELECTION = True)",
                       variable=self.has_seat_var, command=self.toggle_seat_options,
                       bootstyle="warning-round-toggle").pack(anchor=W)

        self.seat_priority_frame = ttk.Frame(seat_frame)
        self.seat_priority_frame.pack(fill=X, pady=(10, 0))

        seat_label_frame = ttk.Frame(self.seat_priority_frame)
        seat_label_frame.pack(fill=X)
        ttk.Label(seat_label_frame, text="좌석 우선순위 (쉼표로 구분):", font=("맑은 고딕", 9)).pack(side=LEFT)
        ttk.Button(seat_label_frame, text="Reset", command=self.reset_seat_priority, bootstyle="secondary-outline", width=6).pack(side=LEFT, padx=(10, 0))
        ttk.Label(seat_label_frame, text="SEAT_OFFSET:", font=("맑은 고딕", 9)).pack(side=LEFT, padx=(20, 0))
        self.seat_offset_entry = ttk.Entry(seat_label_frame, width=5, font=("맑은 고딕", 10))
        self.seat_offset_entry.pack(side=LEFT, padx=(5, 0))
        self.seat_offset_entry.insert(0, "0")

        self.seat_priority_entry = ttk.Entry(self.seat_priority_frame, width=70, font=("맑은 고딕", 10))
        self.seat_priority_entry.pack(fill=X, pady=(5, 0))
        self.seat_priority_entry.insert(0, "15, 14, 1, 8, 7, 13, 2, 9, 6, 12, 3, 10, 5, 11, 4")
        self.toggle_seat_options()

        # ============================================================
        # [5] ID 매핑 생성기
        # ============================================================
        mapping_frame = ttk.Labelframe(self.main_frame, text="[5] ID_MAPPING 설정", padding="10", bootstyle="secondary")
        mapping_frame.pack(fill=X, pady=(0, 10))

        # 매핑 타입 선택
        type_frame = ttk.Frame(mapping_frame)
        type_frame.pack(fill=X)

        ttk.Label(type_frame, text="매핑 타입:", font=("맑은 고딕", 9)).pack(side=LEFT)
        self.mapping_type_var = tk.StringVar(value="daily")
        ttk.Radiobutton(type_frame, text="일별 (월,일):ID", variable=self.mapping_type_var, value="daily",
                       bootstyle="info").pack(side=LEFT, padx=10)
        ttk.Radiobutton(type_frame, text="월별 단일 ID", variable=self.mapping_type_var, value="monthly",
                       bootstyle="info").pack(side=LEFT, padx=10)
        ttk.Radiobutton(type_frame, text="델타 (시작ID+오프셋)", variable=self.mapping_type_var, value="delta",
                       bootstyle="info").pack(side=LEFT, padx=10)

        ttk.Label(mapping_frame, text="자동 조회 또는 수동 입력으로 ID 매핑을 생성할 수 있습니다.", font=("맑은 고딕", 9), foreground="gray").pack(anchor=W, pady=(10, 5))

        # 수동 생성 영역
        manual_frame = ttk.Frame(mapping_frame)
        manual_frame.pack(fill=X, pady=(5, 0))

        ttk.Label(manual_frame, text="수동 생성:", font=("맑은 고딕", 9, "bold")).pack(anchor=W)

        manual_grid = ttk.Frame(manual_frame)
        manual_grid.pack(fill=X, pady=(5, 0))

        # 시작 월
        ttk.Label(manual_grid, text="시작 월:", font=("맑은 고딕", 9)).grid(row=0, column=0, sticky=W, pady=5)
        self.start_month_entry = ttk.Combobox(manual_grid, values=[str(i) for i in range(1, 13)], width=5, state="readonly")
        self.start_month_entry.grid(row=0, column=1, sticky=W, pady=5, padx=5)
        self.start_month_entry.set("9")

        # 시작 일
        ttk.Label(manual_grid, text="시작 일:", font=("맑은 고딕", 9)).grid(row=0, column=2, sticky=W, pady=5, padx=(20, 0))
        self.start_day_entry = ttk.Combobox(manual_grid, values=[str(i) for i in range(1, 32)], width=5, state="readonly")
        self.start_day_entry.grid(row=0, column=3, sticky=W, pady=5, padx=5)
        self.start_day_entry.set("1")

        # 시작 ID
        ttk.Label(manual_grid, text="시작 ID:", font=("맑은 고딕", 9)).grid(row=0, column=4, sticky=W, pady=5, padx=(20, 0))
        self.start_id_entry = ttk.Entry(manual_grid, width=15, font=("맑은 고딕", 10))
        self.start_id_entry.grid(row=0, column=5, sticky=W, pady=5, padx=5)

        # 종료 월
        ttk.Label(manual_grid, text="종료 월:", font=("맑은 고딕", 9)).grid(row=1, column=0, sticky=W, pady=5)
        self.end_month_entry = ttk.Combobox(manual_grid, values=[str(i) for i in range(1, 13)], width=5, state="readonly")
        self.end_month_entry.grid(row=1, column=1, sticky=W, pady=5, padx=5)
        self.end_month_entry.set("12")

        # 종료 일
        ttk.Label(manual_grid, text="종료 일:", font=("맑은 고딕", 9)).grid(row=1, column=2, sticky=W, pady=5, padx=(20, 0))
        self.end_day_entry = ttk.Combobox(manual_grid, values=[str(i) for i in range(1, 32)], width=5, state="readonly")
        self.end_day_entry.grid(row=1, column=3, sticky=W, pady=5, padx=5)
        self.end_day_entry.set("31")

        # 생성 버튼
        btn_frame = ttk.Frame(manual_grid)
        btn_frame.grid(row=0, column=6, rowspan=2, sticky=W, padx=20)
        ttk.Button(btn_frame, text="🔢 수동 매핑 생성", command=self.generate_id_mapping, bootstyle="secondary", width=18).pack(pady=(0, 5))
        ttk.Button(btn_frame, text="🔄 맵핑없음 (동적 조회)", command=self.set_no_mapping, bootstyle="warning-outline", width=18).pack()

        # 매핑 미리보기
        ttk.Label(mapping_frame, text="ID 매핑 미리보기:", font=("맑은 고딕", 9)).pack(anchor=W, pady=(10, 5))
        self.mapping_preview = tk.Text(mapping_frame, height=6, font=("Consolas", 9), bg="#1e1e1e", fg="#d4d4d4", wrap=tk.NONE)
        self.mapping_preview.pack(fill=X)

        mapping_scroll = ttk.Scrollbar(mapping_frame, orient=HORIZONTAL, command=self.mapping_preview.xview, bootstyle="round")
        mapping_scroll.pack(fill=X)
        self.mapping_preview.config(xscrollcommand=mapping_scroll.set)

        # ============================================================
        # 코드 미리보기
        # ============================================================
        preview_frame = ttk.Labelframe(self.main_frame, text="👁️ 코드 미리보기", padding="10", bootstyle="info")
        preview_frame.pack(fill=BOTH, expand=True, pady=(0, 10))

        self.preview_text = tk.Text(preview_frame, height=12, font=("Consolas", 10),
                                   bg="#1e1e1e", fg="#d4d4d4", insertbackground="white", wrap=tk.NONE)
        self.preview_text.pack(fill=BOTH, expand=True, side=LEFT)

        scrollbar3 = ttk.Scrollbar(preview_frame, orient=VERTICAL, command=self.preview_text.yview, bootstyle="round")
        scrollbar3.pack(side=RIGHT, fill=Y)
        self.preview_text.config(yscrollcommand=scrollbar3.set)

        # ============================================================
        # 버튼
        # ============================================================
        btn_frame = ttk.Frame(self.main_frame)
        btn_frame.pack(fill=X, pady=(0, 10))

        ttk.Button(btn_frame, text="🔄 미리보기 갱신", command=self.update_preview, bootstyle="info", width=18).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="💾 봇 파일 생성", command=self.generate_bot, bootstyle="success", width=18).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="🚀 런처 등록", command=self.register_to_launcher, bootstyle="warning", width=18).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="📂 폴더 열기", command=self.open_folder, bootstyle="secondary-outline", width=12).pack(side=RIGHT, padx=5)

        # 상태 표시
        self.status_var = tk.StringVar(value="URL을 입력하고 '분석' 버튼을 클릭하세요.")
        status_label = ttk.Label(self.main_frame, textvariable=self.status_var, font=("맑은 고딕", 9), foreground="gray")
        status_label.pack(anchor=W)

    def toggle_seat_options(self):
        """좌석 옵션 토글"""
        state = 'normal' if self.has_seat_var.get() else 'disabled'
        self.seat_priority_entry.configure(state=state)
        self.seat_offset_entry.configure(state=state)

    def reset_seat_priority(self):
        """좌석 우선순위 입력 초기화"""
        self.seat_priority_entry.delete(0, tk.END)

    def show_help(self):
        """도움말 표시"""
        help_text = """📌 선상24 API 봇 생성 도움말

🔗 예시 URL:
   https://bigboss24.sunsang24.com/ship/schedule_fleet/202609

📝 URL 구성:
   • SUBDOMAIN: bigboss24, doji 등
   • BASE_URL: https://서브도메인.sunsang24.com

⭐ ID 자동 조회 (권장):
   1. URL 분석으로 SUBDOMAIN 추출
   2. 년월 입력 (YYYY: 연도 전체, YYYYMM: 단일 월)
   3. "ID 자동 조회" 클릭
   4. 선사 선택 (여러 선사 있는 경우)
   → ID_MAPPING 자동 생성!

🔢 ID_MAPPING 수동 생성:
   • 예약 페이지 F12 → Network에서 ID 확인
   • 시작 ID를 입력하면 연속된 ID가 자동 생성됩니다

📊 매핑 타입:
   • 일별: (월, 일): ID 형식 (대부분의 경우)
   • 월별: 월별 단일 ID 사용
   • 델타: 시작 ID + 일수 오프셋

⚙️ 사용 방법:
   1. 선상24 캘린더 URL 붙여넣기
   2. 🔍 URL 분석 → SUBDOMAIN, BASE_URL 자동 추출
   3. 🔍 ID 자동 조회 (권장) 또는 수동 매핑 생성
   4. 봇 파일 생성!

💡 팁:
   • 기존 봇 클릭하면 정보 자동 로드
   • 연도 전체 조회시 월별 통계 제공"""
        messagebox.showinfo("도움말", help_text)

    def load_existing_bots(self):
        """기존 봇 목록 로드"""
        self.bot_listbox.delete(0, tk.END)

        for file in os.listdir(self.current_dir):
            if file.endswith("_API.py") and file != "base_api_bot.py":
                try:
                    with open(os.path.join(self.current_dir, file), 'r', encoding='utf-8') as f:
                        content = f.read()

                    provider = re.search(r'PROVIDER_NAME\s*=\s*["\']([^"\']+)["\']', content)
                    has_seat = "HAS_SEAT_SELECTION = True" in content

                    provider_name = provider.group(1) if provider else file.replace("_API.py", "")
                    seat_status = "✅좌석" if has_seat else "❌좌석"

                    self.bot_listbox.insert(tk.END, f"{provider_name} | {seat_status} | {file}")
                except:
                    self.bot_listbox.insert(tk.END, f"? | {file}")

    def on_bot_select(self, event):
        """기존 봇 선택 시 정보 로드"""
        selection = self.bot_listbox.curselection()
        if not selection:
            return

        item = self.bot_listbox.get(selection[0])
        filename = item.split(" | ")[-1]

        try:
            with open(os.path.join(self.current_dir, filename), 'r', encoding='utf-8') as f:
                content = f.read()

            # 정보 추출
            provider = re.search(r'PROVIDER_NAME\s*=\s*["\']([^"\']+)["\']', content)
            base_url = re.search(r'BASE_URL\s*=\s*["\']([^"\']+)["\']', content)
            subdomain = re.search(r'SUBDOMAIN\s*=\s*["\']([^"\']+)["\']', content)
            seat_priority = re.search(r'SEAT_PRIORITY\s*=\s*\[([^\]]+)\]', content)
            seat_offset = re.search(r'SEAT_OFFSET\s*=\s*(\d+)', content)

            # ID_MAPPING 추출
            mapping_match = re.search(r'ID_MAPPING\s*=\s*\{([^}]+)\}', content, re.DOTALL)

            # 입력 필드에 설정
            if provider:
                self.provider_name_entry.delete(0, tk.END)
                self.provider_name_entry.insert(0, provider.group(1))

            if base_url:
                self.base_url_entry.delete(0, tk.END)
                self.base_url_entry.insert(0, base_url.group(1))

            if subdomain:
                self.subdomain_entry.delete(0, tk.END)
                self.subdomain_entry.insert(0, subdomain.group(1))

            self.has_seat_var.set("HAS_SEAT_SELECTION = True" in content)
            self.toggle_seat_options()

            if seat_priority and self.has_seat_var.get():
                seats = seat_priority.group(1).replace("'", "").replace('"', "").strip()
                self.seat_priority_entry.delete(0, tk.END)
                self.seat_priority_entry.insert(0, seats)

            # SEAT_OFFSET 로드
            self.seat_offset_entry.delete(0, tk.END)
            if seat_offset and self.has_seat_var.get():
                self.seat_offset_entry.insert(0, seat_offset.group(1))
            else:
                self.seat_offset_entry.insert(0, "0")

            # ID_MAPPING 파싱
            if mapping_match:
                mapping_str = mapping_match.group(1)
                self.id_mapping_data = {}

                # (월, 일): ID 패턴 찾기
                pattern = re.compile(r'\((\d+),\s*(\d+)\):\s*(\d+)')
                for match in pattern.finditer(mapping_str):
                    month, day, id_val = int(match.group(1)), int(match.group(2)), int(match.group(3))
                    self.id_mapping_data[(month, day)] = id_val

                # 빈 매핑이면 동적 조회 모드로 인식
                self.dynamic_mapping_mode = len(self.id_mapping_data) == 0

                self.update_mapping_preview()

            self.update_preview()
            self.status_var.set(f"✅ {filename} 정보 로드 완료")

        except Exception as e:
            messagebox.showerror("오류", f"봇 정보 로드 실패: {e}")

    def on_provider_name_change(self, event=None):
        """선사명 입력 변경 감지"""
        if self.provider_name_timer:
            self.root.after_cancel(self.provider_name_timer)
            self.provider_name_timer = None

        self.provider_name_ready = False
        provider = self.provider_name_entry.get().strip()
        if provider.endswith("호"):
            self.provider_name_timer = self.root.after(500, self.set_provider_name_ready)

    def set_provider_name_ready(self):
        """선사명 입력 완료 상태로 설정"""
        self.provider_name_ready = True
        self.provider_name_timer = None

    def on_provider_name_focusout(self, event=None):
        """선사명 입력란에서 포커스 벗어날 때"""
        if self.provider_name_timer:
            self.root.after_cancel(self.provider_name_timer)
            self.provider_name_timer = None
        provider = self.provider_name_entry.get().strip()
        if provider.endswith("호"):
            self.provider_name_ready = True

    def reset_inputs(self):
        """입력 필드 초기화"""
        self.url_entry.delete(0, tk.END)
        self.provider_name_entry.delete(0, tk.END)
        self.subdomain_entry.delete(0, tk.END)
        self.base_url_entry.delete(0, tk.END)
        self.has_seat_var.set(False)
        self.toggle_seat_options()
        self.seat_priority_entry.delete(0, tk.END)
        self.seat_priority_entry.insert(0, "15, 14, 1, 8, 7, 13, 2, 9, 6, 12, 3, 10, 5, 11, 4")
        self.seat_offset_entry.delete(0, tk.END)
        self.seat_offset_entry.insert(0, "0")
        self.start_id_entry.delete(0, tk.END)
        self.lookup_yearmonth_entry.delete(0, tk.END)
        self.lookup_yearmonth_entry.insert(0, "2026")
        self.lookup_result_var.set("")
        self.id_mapping_data = {}
        self.dynamic_mapping_mode = False
        self.mapping_preview.delete("1.0", tk.END)
        self.preview_text.delete("1.0", tk.END)
        self.preview_text.insert("1.0", "# 선사명, SUBDOMAIN, BASE_URL, ID_MAPPING을 입력해주세요.")
        self.status_var.set("🔄 입력 필드가 초기화되었습니다.")

    def parse_url(self):
        """URL 분석"""
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("경고", "URL을 입력해주세요.")
            return

        try:
            parsed = urlparse(url)
            host = parsed.netloc

            # 선상24 URL 패턴: 서브도메인.sunsang24.com
            if "sunsang24.com" in host:
                subdomain = host.replace(".sunsang24.com", "")
                base_url = f"https://{host}"

                self.subdomain_entry.delete(0, tk.END)
                self.subdomain_entry.insert(0, subdomain)

                self.base_url_entry.delete(0, tk.END)
                self.base_url_entry.insert(0, base_url)

                self.provider_name_entry.focus_set()
                self.status_var.set(f"✅ URL 분석 완료! SUBDOMAIN: {subdomain}")
            else:
                messagebox.showwarning("경고", "선상24 URL이 아닙니다.\n예: https://bigboss24.sunsang24.com/...")

        except Exception as e:
            messagebox.showerror("오류", f"URL 분석 중 오류 발생:\n{str(e)}")

    def lookup_schedule_ids(self):
        """선상24 schedule_fleet 페이지에서 data-schedule_no 자동 추출

        입력 형식:
        - YYYYMM (예: 202611) : 해당 월만 조회
        - YYYY (예: 2026) : 해당 연도 전체 조회 (1월~12월)
        """
        subdomain = self.subdomain_entry.get().strip()
        yearmonth_input = self.lookup_yearmonth_entry.get().strip()

        if not subdomain:
            messagebox.showwarning("경고", "서브도메인을 먼저 입력해주세요.\nURL을 분석하거나 직접 입력하세요.")
            return

        if not yearmonth_input:
            messagebox.showwarning("경고", "년월(YYYYMM) 또는 연도(YYYY)를 입력해주세요.")
            return

        # 연도만 입력했는지 확인 (YYYY vs YYYYMM)
        if len(yearmonth_input) == 4 and yearmonth_input.isdigit():
            # 연도 전체 조회
            year = yearmonth_input
            months_to_query = [f"{year}{m:02d}" for m in range(1, 13)]
            is_yearly = True
        elif len(yearmonth_input) == 6 and yearmonth_input.isdigit():
            # 단일 월 조회
            months_to_query = [yearmonth_input]
            is_yearly = False
        else:
            messagebox.showwarning("경고", "년월을 YYYYMM (예: 202611) 또는 YYYY (예: 2026) 형식으로 입력해주세요.")
            return

        try:
            all_schedule_ids = {}
            successful_months = []
            failed_months = []
            self.ship_names_found = set()  # 선사명 목록 초기화

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            for idx, yearmonth in enumerate(months_to_query):
                if is_yearly:
                    self.lookup_result_var.set(f"🔄 조회 중... ({idx+1}/12) - {yearmonth[:4]}년 {int(yearmonth[4:6])}월")
                else:
                    self.lookup_result_var.set("🔄 조회 중...")
                self.root.update()

                try:
                    url = f"https://{subdomain}.sunsang24.com/ship/schedule_fleet/{yearmonth}"
                    response = requests.get(url, headers=headers, timeout=10, verify=False)
                    response.raise_for_status()

                    soup = BeautifulSoup(response.text, 'html.parser')

                    # data-schedule_no 속성을 가진 모든 요소 찾기
                    schedule_elements = soup.find_all(attrs={"data-schedule_no": True})

                    # 날짜+선사별로 ID 추출
                    month_schedule_ids = {}
                    ship_names_found = set()

                    for elem in schedule_elements:
                        schedule_no = elem.get('data-schedule_no')
                        if schedule_no:
                            # 부모 요소에서 날짜 찾기 (table이 중첩되어 있으므로 모든 상위 table 탐색)
                            date_str = None
                            for parent_table in elem.find_parents('table'):
                                table_id = parent_table.get('id', '')
                                if table_id.startswith('d20'):  # d2026-09-01 형식
                                    date_str = table_id[1:]  # 2026-09-01
                                    break

                            if date_str:
                                # TR의 첫 번째 TD에서 선사명 추출
                                ship_name = ""
                                row = elem.find_parent('tr')
                                if row:
                                    first_td = row.find('td')
                                    if first_td:
                                        # 선사명만 추출 (공백, 탭, 줄바꿈 제거)
                                        text = first_td.get_text().strip()
                                        ship_name = text.split()[0] if text else ""

                                if ship_name:
                                    ship_names_found.add(ship_name)

                                # 키: (날짜, 선사명)
                                key = (date_str, ship_name)
                                if key not in month_schedule_ids:
                                    month_schedule_ids[key] = schedule_no

                    if month_schedule_ids:
                        all_schedule_ids.update(month_schedule_ids)
                        successful_months.append(yearmonth)
                        self.ship_names_found.update(ship_names_found)
                    else:
                        failed_months.append(yearmonth)

                except requests.exceptions.RequestException:
                    failed_months.append(yearmonth)
                    continue

            if not all_schedule_ids:
                if is_yearly:
                    self.lookup_result_var.set(f"⚠️ {yearmonth_input}년 전체에서 예약 ID를 찾을 수 없습니다.")
                else:
                    self.lookup_result_var.set(f"⚠️ {yearmonth_input}에서 예약 ID를 찾을 수 없습니다.")
                return

            # 선사별로 데이터 분류
            ship_names = sorted(self.ship_names_found) if self.ship_names_found else []

            # 여러 선사가 있는 경우 선택 다이얼로그
            selected_ship = None
            if len(ship_names) > 1:
                # 선사 선택 다이얼로그
                ship_select_dialog = tk.Toplevel(self.root)
                ship_select_dialog.title("선사 선택")
                ship_select_dialog.geometry("350x250")
                ship_select_dialog.transient(self.root)
                ship_select_dialog.grab_set()

                # 중앙 배치
                ship_select_dialog.update_idletasks()
                x = self.root.winfo_x() + (self.root.winfo_width() - 350) // 2
                y = self.root.winfo_y() + (self.root.winfo_height() - 250) // 2
                ship_select_dialog.geometry(f"+{x}+{y}")

                ttk.Label(ship_select_dialog, text="🚢 여러 선사가 발견되었습니다.\n봇을 생성할 선사를 선택하세요:",
                         font=("맑은 고딕", 10)).pack(pady=15)

                selected_var = tk.StringVar(value=ship_names[0])
                for ship in ship_names:
                    # 해당 선사의 데이터 개수
                    count = sum(1 for k in all_schedule_ids.keys() if k[1] == ship)
                    ttk.Radiobutton(ship_select_dialog, text=f"{ship} ({count}개 일정)",
                                   variable=selected_var, value=ship,
                                   bootstyle="info").pack(anchor=W, padx=30, pady=3)

                def on_select():
                    nonlocal selected_ship
                    selected_ship = selected_var.get()
                    ship_select_dialog.destroy()

                ttk.Button(ship_select_dialog, text="선택", command=on_select,
                          bootstyle="success", width=15).pack(pady=15)

                self.root.wait_window(ship_select_dialog)

                if not selected_ship:
                    self.lookup_result_var.set("⚠️ 선사 선택이 취소되었습니다.")
                    return
            elif len(ship_names) == 1:
                selected_ship = ship_names[0]

            # 선택된 선사의 데이터만 필터링
            if selected_ship:
                filtered_ids = {k: v for k, v in all_schedule_ids.items() if k[1] == selected_ship}
                # 선사명 자동 입력
                current_provider = self.provider_name_entry.get().strip()
                if not current_provider:
                    self.provider_name_entry.delete(0, tk.END)
                    self.provider_name_entry.insert(0, selected_ship)
            else:
                filtered_ids = all_schedule_ids

            # 날짜순 정렬 (키가 (date_str, ship_name) 튜플)
            sorted_keys = sorted(filtered_ids.keys(), key=lambda x: x[0])

            # 결과 표시
            result_count = len(filtered_ids)
            if is_yearly:
                success_month_count = len(successful_months)
                ship_info = f" [{selected_ship}]" if selected_ship else ""
                self.lookup_result_var.set(f"✅ {result_count}개 날짜{ship_info} (총 {success_month_count}개월)")
            else:
                ship_info = f" [{selected_ship}]" if selected_ship else ""
                self.lookup_result_var.set(f"✅ {result_count}개 날짜{ship_info}의 ID를 찾았습니다!")

            # 일별 매핑으로 설정
            self.mapping_type_var.set("daily")

            # ID 매핑 데이터 저장
            self.id_mapping_data = {}
            self.dynamic_mapping_mode = False  # 자동 조회 시 동적 모드 해제
            for key in sorted_keys:
                date_str, ship_name = key
                schedule_no = filtered_ids[key]
                # 2026-11-02 -> (11, 2)
                parts = date_str.split('-')
                if len(parts) == 3:
                    m = int(parts[1])
                    d = int(parts[2])
                    self.id_mapping_data[(m, d)] = int(schedule_no)

            self.update_mapping_preview()
            self.update_preview()

            # 월별 통계 계산
            monthly_counts = {}
            for key in sorted_keys:
                date_str, ship_name = key
                parts = date_str.split('-')
                if len(parts) == 3:
                    month = int(parts[1])
                    monthly_counts[month] = monthly_counts.get(month, 0) + 1

            # 상태 업데이트
            if is_yearly:
                success_month_count = len(successful_months)
                ship_info = f" [{selected_ship}]" if selected_ship else ""
                line1 = ", ".join([f"{m}월-{monthly_counts.get(m, 0)}개" for m in range(1, 7) if m in monthly_counts])
                line2 = ", ".join([f"{m}월-{monthly_counts.get(m, 0)}개" for m in range(7, 13) if m in monthly_counts])
                monthly_stats = f" | {line1}" if line1 else ""
                if line2:
                    monthly_stats += f" | {line2}" if monthly_stats else f" | {line2}"
                self.status_var.set(f"✅ {subdomain}{ship_info} - {yearmonth_input}년 전체 ID 조회 완료! {result_count}개 날짜 ({success_month_count}개월){monthly_stats}")
            else:
                ship_info = f" [{selected_ship}]" if selected_ship else ""
                self.status_var.set(f"✅ {subdomain}{ship_info} - {yearmonth_input} ID 조회 완료! {result_count}개 날짜")

        except Exception as e:
            self.lookup_result_var.set(f"❌ 오류: {str(e)[:50]}")
            import traceback
            traceback.print_exc()

    def set_no_mapping(self):
        """맵핑없음 (동적 조회) 모드 설정"""
        self.id_mapping_data = {}
        self.dynamic_mapping_mode = True
        self.update_mapping_preview()
        self.update_preview()
        self.status_var.set("🔄 동적 조회 모드 설정 완료! (예약 오픈 시 schedule_fleet에서 자동 파싱)")

    def generate_id_mapping(self):
        """ID 매핑 생성 (수동)"""
        try:
            start_month = int(self.start_month_entry.get())
            start_day = int(self.start_day_entry.get())
            end_month = int(self.end_month_entry.get())
            end_day = int(self.end_day_entry.get())
            start_id = self.start_id_entry.get().strip()

            if not start_id:
                messagebox.showwarning("경고", "시작 ID를 입력해주세요.")
                return

            start_id = int(start_id)

            # 매핑 생성
            self.id_mapping_data = {}
            self.dynamic_mapping_mode = False  # 수동 매핑 시 동적 모드 해제
            current_id = start_id
            year = 2026  # 기본 연도

            for month in range(start_month, end_month + 1):
                # 해당 월의 마지막 일
                last_day = calendar.monthrange(year, month)[1]

                # 시작일과 종료일 결정
                day_start = start_day if month == start_month else 1
                day_end = min(end_day, last_day) if month == end_month else last_day

                for day in range(day_start, day_end + 1):
                    self.id_mapping_data[(month, day)] = current_id
                    current_id += 1

            self.update_mapping_preview()
            self.update_preview()

            total_days = len(self.id_mapping_data)
            self.status_var.set(f"✅ ID 매핑 생성 완료! ({total_days}일)")

        except ValueError as e:
            messagebox.showerror("오류", f"입력값 오류: {e}")

    def update_mapping_preview(self):
        """매핑 미리보기 업데이트"""
        self.mapping_preview.delete("1.0", tk.END)

        if not self.id_mapping_data:
            if self.dynamic_mapping_mode:
                self.mapping_preview.insert("1.0",
                    "# 🔄 동적 조회 모드 (ID_MAPPING = {})\n"
                    "# 예약 오픈 시 schedule_fleet 페이지에서 자동으로 스케줄 ID를 파싱합니다.\n"
                    "# ID가 비공개인 선사(피크닉호 등)에 사용합니다.")
            else:
                self.mapping_preview.insert("1.0", "# ID 매핑을 생성해주세요.")
            return

        # 모든 매핑 표시
        lines = []
        current_month = None
        for (m, d), id_val in sorted(self.id_mapping_data.items()):
            if current_month != m:
                if current_month is not None:
                    lines.append("")  # 월 구분
                current_month = m
                lines.append(f"# {m}월")
            lines.append(f"({m}, {d}): {id_val},")

        self.mapping_preview.insert("1.0", "\n".join(lines))

    def generate_code(self):
        """봇 코드 생성"""
        provider = self.provider_name_entry.get().strip()
        base_url = self.base_url_entry.get().strip()
        subdomain = self.subdomain_entry.get().strip()
        has_seat = self.has_seat_var.get()
        seats = self.seat_priority_entry.get().strip()
        seat_offset = self.seat_offset_entry.get().strip()

        if not all([provider, base_url, subdomain]):
            return None

        # 좌석 우선순위 파싱
        seat_list = ""
        if has_seat and seats:
            seat_items = [s.strip() for s in seats.split(",") if s.strip()]
            seat_list = ", ".join([f"'{s}'" for s in seat_items])

        # SEAT_OFFSET 파싱
        try:
            seat_offset_val = int(seat_offset) if seat_offset else 0
        except ValueError:
            seat_offset_val = 0

        # ID 매핑 문자열 생성
        mapping_str = self.generate_mapping_string()

        # 패턴 설명
        if self.dynamic_mapping_mode:
            mapping_desc = "동적 조회 (오픈 시 자동 파싱)"
        else:
            mapping_desc = "매핑 있음"

        # 코드 생성
        code = f'''# -*- coding: utf-8 -*-
"""
{provider} API 봇 (선상24)
패턴: {mapping_desc} + 자리선택 {'활성화' if has_seat else '비활성화'}
"""
from base_api_bot import SunSang24APIBot


class {provider}APIBot(SunSang24APIBot):
    BASE_URL = "{base_url}"
    SUBDOMAIN = "{subdomain}"
    PROVIDER_NAME = "{provider}"
    HAS_SEAT_SELECTION = {str(has_seat)}
'''

        if has_seat and seat_offset_val > 0:
            code += f'''    SEAT_OFFSET = {seat_offset_val}  # 잔여석 표시 시 선장석 {seat_offset_val}석 차감
'''

        if has_seat and seat_list:
            code += f'''
    SEAT_PRIORITY = [{seat_list}]
'''

        code += f'''
    ID_MAPPING = {{
{mapping_str}
    }}


if __name__ == "__main__":
    bot = {provider}APIBot()
    bot.run()
'''

        return code

    def generate_mapping_string(self):
        """ID 매핑 문자열 생성 (코드용)"""
        if not self.id_mapping_data:
            if self.dynamic_mapping_mode:
                return "        # 동적 조회 모드: 예약 오픈 시 schedule_fleet에서 자동 파싱"
            return "        # ID 매핑을 생성해주세요"

        lines = []
        current_month = None
        line_items = []

        for (month, day), id_val in sorted(self.id_mapping_data.items()):
            if current_month != month:
                if line_items:
                    lines.append("        " + " ".join(line_items))
                    line_items = []
                current_month = month

            line_items.append(f"({month}, {day}): {id_val},")

            if len(line_items) >= 5:
                lines.append("        " + " ".join(line_items))
                line_items = []

        if line_items:
            lines.append("        " + " ".join(line_items))

        return "\n".join(lines)

    def update_preview(self):
        """미리보기 갱신"""
        code = self.generate_code()
        self.preview_text.delete("1.0", tk.END)

        if code:
            self.preview_text.insert("1.0", code)
            self._apply_syntax_highlighting()
        else:
            self.preview_text.insert("1.0", "# 선사명, SUBDOMAIN, BASE_URL, ID_MAPPING을 입력해주세요.")

    def _apply_syntax_highlighting(self):
        """간단한 구문 강조"""
        self.preview_text.tag_configure("keyword", foreground="#569cd6")
        self.preview_text.tag_configure("string", foreground="#ce9178")
        self.preview_text.tag_configure("comment", foreground="#6a9955")
        self.preview_text.tag_configure("class", foreground="#4ec9b0")
        self.preview_text.tag_configure("bool", foreground="#569cd6")

        keywords = ["from", "import", "class", "def", "if", "True", "False", "None"]
        for kw in keywords:
            start = "1.0"
            while True:
                pos = self.preview_text.search(rf"\b{kw}\b", start, stopindex=tk.END, regexp=True)
                if not pos:
                    break
                end = f"{pos}+{len(kw)}c"
                self.preview_text.tag_add("keyword", pos, end)
                start = end

    def validate_inputs(self):
        """입력 검증"""
        provider = self.provider_name_entry.get().strip()
        if not provider:
            messagebox.showerror("오류", "선사명을 입력해주세요.")
            return False
        if not provider.endswith("호"):
            messagebox.showwarning("경고", "선사명이 '호'로 끝나지 않습니다.\n예: 빅보스호, 도지호")
            return False
        if not self.subdomain_entry.get().strip():
            messagebox.showerror("오류", "SUBDOMAIN을 입력해주세요.")
            return False
        if not self.base_url_entry.get().strip():
            messagebox.showerror("오류", "BASE_URL을 입력해주세요.")
            return False
        if not self.id_mapping_data and not self.dynamic_mapping_mode:
            messagebox.showerror("오류", "ID 매핑을 생성해주세요.")
            return False
        return True

    def generate_bot(self):
        """봇 파일 생성"""
        if not self.validate_inputs():
            return

        provider = self.provider_name_entry.get().strip()
        filename = f"{provider}_API.py"
        filepath = os.path.join(self.current_dir, filename)

        # 파일 존재 확인
        if os.path.exists(filepath):
            if not messagebox.askyesno("확인", f"'{filename}'이 이미 존재합니다.\n덮어쓰시겠습니까?"):
                return

        code = self.generate_code()
        if not code:
            messagebox.showerror("오류", "코드 생성에 실패했습니다.")
            return

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(code)

            messagebox.showinfo("성공", f"✅ {filename} 생성 완료!")
            self.status_var.set(f"✅ {filename} 생성 완료!")
            self.load_existing_bots()

        except Exception as e:
            messagebox.showerror("오류", f"파일 생성 실패: {e}")

    def register_to_launcher(self):
        """런처에 등록"""
        provider = self.provider_name_entry.get().strip()
        if not provider:
            messagebox.showerror("오류", "선사명을 입력해주세요.")
            return

        # 등록 팝업
        register_window = tk.Toplevel(self.root)
        register_window.title("🚀 런처 등록")
        register_window.transient(self.root)
        register_window.grab_set()

        # 팝업창 크기 및 중앙 배치
        popup_width = 500
        popup_height = 350
        register_window.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - popup_width) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - popup_height) // 2
        register_window.geometry(f"{popup_width}x{popup_height}+{x}+{y}")

        frame = ttk.Frame(register_window, padding="20")
        frame.pack(fill=BOTH, expand=True)

        ttk.Label(frame, text="런처에 새 API 봇 등록", font=("맑은 고딕", 13, "bold"), bootstyle="primary").pack(pady=(0, 20))

        # 항구 선택
        port_frame = ttk.Frame(frame)
        port_frame.pack(fill=X, pady=8)
        ttk.Label(port_frame, text="항구:", width=10, font=("맑은 고딕", 10)).pack(side=LEFT)
        port_var = tk.StringVar()
        port_combo = ttk.Combobox(port_frame, textvariable=port_var, values=PORTS, width=35, font=("맑은 고딕", 10), state="readonly")
        port_combo.pack(side=LEFT, padx=5)

        # 선사명 (자동 입력)
        provider_frame = ttk.Frame(frame)
        provider_frame.pack(fill=X, pady=8)
        ttk.Label(provider_frame, text="선사명:", width=10, font=("맑은 고딕", 10)).pack(side=LEFT)
        provider_var = tk.StringVar(value=f"{provider}(API)")
        ttk.Entry(provider_frame, textvariable=provider_var, width=35, font=("맑은 고딕", 10)).pack(side=LEFT, padx=5)

        # 경로 (자동)
        path_frame = ttk.Frame(frame)
        path_frame.pack(fill=X, pady=8)
        ttk.Label(path_frame, text="경로:", width=10, font=("맑은 고딕", 10)).pack(side=LEFT)
        path_var = tk.StringVar(value=f"api/선상24/{provider}_API.py")
        ttk.Entry(path_frame, textvariable=path_var, width=35, font=("맑은 고딕", 10), state="readonly").pack(side=LEFT, padx=5)

        # 버튼
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=25)

        def do_register():
            port = port_var.get().strip()
            bot_key = provider_var.get().strip()
            bot_path = path_var.get().strip()

            if not port:
                messagebox.showwarning("경고", "항구를 선택해주세요.", parent=register_window)
                return

            if not bot_key:
                messagebox.showwarning("경고", "선사명을 입력해주세요.", parent=register_window)
                return

            # 런처 파일 수정
            launcher_path = os.path.join(os.path.dirname(self.current_dir), "..", "..", "쭈갑예약_Bot_Launcher.py")
            launcher_path = os.path.normpath(launcher_path)

            try:
                with open(launcher_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 해당 항구 섹션 찾기
                port_pattern = rf'("{re.escape(port)}":\s*\{{[^}}]*)\}}'
                match = re.search(port_pattern, content)

                if not match:
                    messagebox.showerror("오류", f"런처에서 '{port}' 항구를 찾을 수 없습니다.", parent=register_window)
                    return

                # 항구 섹션 끝에 새 항목 추가
                port_content = match.group(1).rstrip()
                if port_content.endswith(','):
                    new_entry = f'\n        "{bot_key}": "{bot_path}",'
                else:
                    new_entry = f',\n        "{bot_key}": "{bot_path}",'
                new_port_content = port_content + new_entry + "\n    }"

                new_content = content[:match.start()] + new_port_content + content[match.end():]

                with open(launcher_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)

                messagebox.showinfo("성공", f"✅ {bot_key}가 {port}에 등록되었습니다!", parent=register_window)
                self.status_var.set(f"✅ 런처 등록 완료: {bot_key} → {port}")
                register_window.destroy()

            except FileNotFoundError:
                messagebox.showerror("오류", "런처 파일을 찾을 수 없습니다.", parent=register_window)
            except Exception as e:
                messagebox.showerror("오류", f"등록 실패: {e}", parent=register_window)

        ttk.Button(btn_frame, text="✅ 등록", command=do_register, bootstyle="success", width=12).pack(side=LEFT, padx=10)
        ttk.Button(btn_frame, text="❌ 취소", command=register_window.destroy, bootstyle="secondary", width=12).pack(side=LEFT, padx=10)

    def open_folder(self):
        """폴더 열기"""
        os.startfile(self.current_dir)


def main():
    root = ttk.Window(themename="darkly")
    app = SunSang24BotGeneratorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
