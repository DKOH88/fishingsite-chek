#!/usr/bin/env python3
"""
네이버 카페 양도게시판 모니터 GUI
기존 naver_cafe_monitor.py의 GUI 버전
"""

import os
import sys
import json
import time
import random
import threading
import requests
import calendar
import ctypes
from datetime import datetime
from tkinter import *
from tkinter import ttk, messagebox, scrolledtext

# 트레이 아이콘 지원
try:
    import pystray
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service
except ImportError:
    print("❌ 필요한 패키지를 설치하세요: pip install selenium webdriver-manager requests")
    sys.exit(1)

CONFIG_FILE = "cafe_monitor_config.json"
PRESETS_FILE = "cafe_keyword_presets.json"


class NaverCafeMonitorGUI:
    def __init__(self):
        self.root = Tk()
        self.root.title("🔔 네이버 카페 양도게시판 모니터")
        
        # 창 크기 및 화면 중앙 위치
        win_width, win_height = 650, 700
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - win_width) // 2
        y = (screen_height - win_height) // 2
        self.root.geometry(f"{win_width}x{win_height}+{x}+{y}")
        self.root.resizable(True, True)
        
        # 상태 변수
        self.is_running = False
        self.driver = None
        self.monitored_posts = set()
        self.monitor_thread = None
        
        # 키워드 버튼들
        self.keyword_buttons = {}  # {keyword: (button, enabled)}
        
        # 통계
        self.stats = {
            'check_count': 0,
            'alert_count': 0,
            'start_time': None
        }
        
        # 알림 히스토리
        self.alert_history = []
        
        # 설정 로드
        self.config = self.load_config()
        self.presets = self.load_presets()
        
        # GUI 생성
        self.create_widgets()
        self.load_keywords_to_gui()
        
        # 트레이 아이콘 관련
        self.tray_icon = None
        self.is_hidden = False
        
        # 윈도우 종료 시 처리
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 선택된 월 (기본: 9월)
        self.selected_month = 9
        self.month_buttons = {}
    
    def load_config(self):
        """설정 파일 로드"""
        default_config = {
            "cafe_url": "https://cafe.naver.com/badajd",
            "board_url": "",
            "keywords": [],
            "telegram_bot_token": "",
            "telegram_chat_id": "",
            "naver_id": "",
            "naver_password": "",
            "check_interval_min": 20,
            "check_interval_max": 30,
            "sleep_start_hour": 23,
            "sleep_start_minute": 59,
            "sleep_end_hour": 5,
            "sleep_end_minute": 0,
            "headless_mode": False,
            "active_keywords": []  # 활성화된 키워드 목록
        }
        
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    default_config.update(loaded)
            except:
                pass
        
        return default_config
    
    def save_config(self):
        """설정 저장"""
        # 활성화된 키워드 저장
        active_keywords = [kw for kw, (btn, enabled) in self.keyword_buttons.items() if enabled]
        self.config['active_keywords'] = active_keywords
        self.config['keywords'] = list(self.keyword_buttons.keys())
        
        # 체크간격 및 헤드리스 저장
        self.config['check_interval_min'] = int(self.entry_interval_min.get() or 20)
        self.config['check_interval_max'] = int(self.entry_interval_max.get() or 30)
        self.config['headless_mode'] = self.var_headless.get()
        
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)
        
        self.log_msg("💾 설정 저장 완료")
    
    def save_config_quietly(self):
        """설정 조용히 저장"""
        try:
            active_keywords = [kw for kw, (btn, enabled) in self.keyword_buttons.items() if enabled]
            self.config['active_keywords'] = active_keywords
            self.config['keywords'] = list(self.keyword_buttons.keys())
            
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except:
            pass
    
    def load_presets(self):
        """키워드 프리셋 로드"""
        if os.path.exists(PRESETS_FILE):
            try:
                with open(PRESETS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def save_presets(self):
        """키워드 프리셋 저장"""
        with open(PRESETS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.presets, f, ensure_ascii=False, indent=2)
    
    def load_keywords_to_gui(self):
        """키워드를 GUI 버튼으로 로드"""
        keywords = self.config.get('keywords', [])
        active_keywords = self.config.get('active_keywords', keywords)  # 기본값: 모두 활성
        
        for keyword in keywords:
            enabled = keyword in active_keywords
            self.add_keyword_button(keyword, enabled)
        
        self.update_select_all_button()
    
    def create_widgets(self):
        """GUI 위젯 생성"""
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=BOTH, expand=True)
        
        # ========== 키워드 관리 ==========
        keyword_frame = ttk.LabelFrame(main_frame, text="🔑 키워드 관리", padding="10")
        keyword_frame.pack(fill=X, pady=5)
        
        # 키워드 입력
        input_frame = ttk.Frame(keyword_frame)
        input_frame.pack(fill=X, pady=5)
        
        ttk.Label(input_frame, text="키워드:").pack(side=LEFT)
        self.entry_keyword = ttk.Entry(input_frame, width=25)
        self.entry_keyword.pack(side=LEFT, padx=5)
        self.entry_keyword.bind('<Return>', lambda e: self.add_keyword())
        
        ttk.Button(input_frame, text="추가", command=self.add_keyword, width=8).pack(side=LEFT, padx=2)
        ttk.Button(input_frame, text="선택삭제", command=self.delete_selected_keywords, width=8).pack(side=LEFT, padx=2)
        
        # 전체선택 버튼
        self.btn_select_all = Button(input_frame, text="전체선택", command=self.toggle_all_keywords, 
                                     width=10, bg='SystemButtonFace')
        self.btn_select_all.pack(side=RIGHT, padx=5)
        
        # 키워드 버튼 그리드
        self.keyword_grid_frame = ttk.Frame(keyword_frame)
        self.keyword_grid_frame.pack(fill=X, pady=10)
        
        # ========== 키워드 프리셋 ==========
        preset_frame = ttk.Frame(keyword_frame)
        preset_frame.pack(fill=X, pady=5)
        
        ttk.Label(preset_frame, text="프리셋:").pack(side=LEFT)
        self.preset_var = StringVar()
        self.combo_preset = ttk.Combobox(preset_frame, textvariable=self.preset_var, width=15, state='readonly')
        self.combo_preset.pack(side=LEFT, padx=5)
        self.combo_preset.bind('<<ComboboxSelected>>', self.load_preset)
        self.refresh_preset_dropdown()
        
        ttk.Button(preset_frame, text="불러오기", command=self.load_preset, width=8).pack(side=LEFT, padx=2)
        ttk.Button(preset_frame, text="저장", command=self.save_preset, width=8).pack(side=LEFT, padx=2)
        ttk.Button(preset_frame, text="삭제", command=self.delete_preset, width=8).pack(side=LEFT, padx=2)
        ttk.Button(preset_frame, text="📅캘린더", command=self.show_calendar_popup, width=8).pack(side=LEFT, padx=2)
        
        # 월 선택 버튼
        self.btn_month_9 = Button(preset_frame, text="9월", width=4, bg='#4CAF50', fg='white',
                                   command=lambda: self.select_month(9))
        self.btn_month_9.pack(side=LEFT, padx=1)
        
        self.btn_month_10 = Button(preset_frame, text="10월", width=4, bg='SystemButtonFace',
                                    command=lambda: self.select_month(10))
        self.btn_month_10.pack(side=LEFT, padx=1)
        
        self.btn_month_11 = Button(preset_frame, text="11월", width=4, bg='SystemButtonFace',
                                    command=lambda: self.select_month(11))
        self.btn_month_11.pack(side=LEFT, padx=1)
        
        # ========== 설정 ==========
        settings_frame = ttk.LabelFrame(main_frame, text="⚙️ 설정", padding="5")
        settings_frame.pack(fill=X, pady=5)
        
        # 체크 간격
        interval_frame = ttk.Frame(settings_frame)
        interval_frame.pack(fill=X)
        
        ttk.Label(interval_frame, text="체크 간격:").pack(side=LEFT)
        self.entry_interval_min = ttk.Entry(interval_frame, width=5)
        self.entry_interval_min.pack(side=LEFT, padx=2)
        self.entry_interval_min.insert(0, str(self.config.get('check_interval_min', 20)))
        ttk.Label(interval_frame, text="~").pack(side=LEFT)
        self.entry_interval_max = ttk.Entry(interval_frame, width=5)
        self.entry_interval_max.pack(side=LEFT, padx=2)
        self.entry_interval_max.insert(0, str(self.config.get('check_interval_max', 30)))
        ttk.Label(interval_frame, text="초").pack(side=LEFT)
        
        self.var_headless = BooleanVar(value=self.config.get('headless_mode', False))
        ttk.Checkbutton(interval_frame, text="헤드리스 모드", variable=self.var_headless).pack(side=LEFT, padx=20)
        
        # ========== 통계 패널 ==========
        stats_frame = ttk.LabelFrame(main_frame, text="📊 통계", padding="5")
        stats_frame.pack(fill=X, pady=5)
        
        self.lbl_stats = ttk.Label(stats_frame, text="체크: 0회 | 알림: 0건 | 실행시간: -")
        self.lbl_stats.pack(side=LEFT)
        
        self.lbl_status = ttk.Label(stats_frame, text="⚪ 대기 중", foreground="gray")
        self.lbl_status.pack(side=RIGHT)
        
        # ========== 버튼 ==========
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=X, pady=10)
        
        self.btn_start = ttk.Button(btn_frame, text="▶ 모니터링 시작", command=self.start_monitoring)
        self.btn_start.pack(side=LEFT, padx=5)
        
        self.btn_stop = ttk.Button(btn_frame, text="⬛ 중지", command=self.stop_monitoring, state=DISABLED)
        self.btn_stop.pack(side=LEFT, padx=5)
        
        ttk.Button(btn_frame, text="💾 설정 저장", command=self.save_config).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="📋 알림 히스토리", command=self.show_alert_history).pack(side=RIGHT, padx=5)
        
        # 숨김 버튼 (트레이로 숨기기)
        if TRAY_AVAILABLE:
            ttk.Button(btn_frame, text="👁️ 숨김", command=self.hide_to_tray).pack(side=RIGHT, padx=5)
        
        # ========== 로그 ==========
        log_frame = ttk.LabelFrame(main_frame, text="📋 로그", padding="5")
        log_frame.pack(fill=BOTH, expand=True, pady=5)
        
        self.log_area = scrolledtext.ScrolledText(log_frame, height=15, wrap=WORD, state=DISABLED)
        self.log_area.pack(fill=BOTH, expand=True)
    
    def log_msg(self, msg):
        """로그 메시지 추가"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_area.config(state=NORMAL)
        self.log_area.insert(END, f"[{timestamp}] {msg}\n")
        self.log_area.see(END)
        self.log_area.config(state=DISABLED)
    
    def add_keyword_button(self, keyword, enabled=True):
        """키워드 버튼 추가"""
        if keyword in self.keyword_buttons:
            return
        
        btn = Button(self.keyword_grid_frame, text=keyword, width=12,
                     command=lambda k=keyword: self.toggle_keyword(k))
        
        if enabled:
            btn.config(bg='#4CAF50', fg='white', activebackground='#45a049')
        else:
            btn.config(bg='SystemButtonFace', fg='black')
        
        self.keyword_buttons[keyword] = (btn, enabled)
        self.refresh_keyword_grid()
    
    def refresh_keyword_grid(self):
        """키워드 버튼 그리드 새로고침"""
        # 기존 버튼 제거
        for widget in self.keyword_grid_frame.winfo_children():
            widget.grid_forget()
        
        # 버튼 재배치 (5열)
        col = 0
        row = 0
        for keyword, (btn, enabled) in self.keyword_buttons.items():
            btn.grid(row=row, column=col, padx=3, pady=3)
            col += 1
            if col >= 5:
                col = 0
                row += 1
    
    def toggle_keyword(self, keyword):
        """키워드 토글 (활성/비활성)"""
        if keyword not in self.keyword_buttons:
            return
        
        btn, enabled = self.keyword_buttons[keyword]
        new_enabled = not enabled
        
        if new_enabled:
            btn.config(bg='#4CAF50', fg='white', activebackground='#45a049')
        else:
            btn.config(bg='SystemButtonFace', fg='black')
        
        self.keyword_buttons[keyword] = (btn, new_enabled)
        self.update_select_all_button()
        self.save_config_quietly()
        
        status = "✅ 활성화" if new_enabled else "⬜ 비활성화"
        self.log_msg(f"🔑 {keyword}: {status}")
    
    def toggle_all_keywords(self):
        """전체 키워드 토글"""
        if not self.keyword_buttons:
            return
        
        # 현재 활성화된 키워드 수
        enabled_count = sum(1 for _, (_, enabled) in self.keyword_buttons.items() if enabled)
        all_enabled = enabled_count == len(self.keyword_buttons)
        
        # 전체 활성 → 전체 비활성, 아니면 → 전체 활성
        new_state = not all_enabled
        
        for keyword in self.keyword_buttons:
            btn, _ = self.keyword_buttons[keyword]
            if new_state:
                btn.config(bg='#4CAF50', fg='white', activebackground='#45a049')
            else:
                btn.config(bg='SystemButtonFace', fg='black')
            self.keyword_buttons[keyword] = (btn, new_state)
        
        self.update_select_all_button()
        self.save_config_quietly()
        
        status = "전체 활성화" if new_state else "전체 비활성화"
        self.log_msg(f"☑ 키워드 {status}")
    
    def update_select_all_button(self):
        """전체선택 버튼 상태 업데이트"""
        if not self.keyword_buttons:
            self.btn_select_all.config(bg='SystemButtonFace', text='전체선택')
            return
        
        enabled_count = sum(1 for _, (_, enabled) in self.keyword_buttons.items() if enabled)
        
        if enabled_count == len(self.keyword_buttons):
            self.btn_select_all.config(bg='#4CAF50', fg='white', text='전체해제')
        else:
            self.btn_select_all.config(bg='SystemButtonFace', fg='black', text='전체선택')
    
    def add_keyword(self):
        """키워드 추가"""
        keyword = self.entry_keyword.get().strip()
        if keyword:
            if keyword not in self.keyword_buttons:
                self.add_keyword_button(keyword, enabled=True)
                self.entry_keyword.delete(0, END)
                self.save_config_quietly()
                self.log_msg(f"🔑 키워드 추가: {keyword}")
            else:
                messagebox.showwarning("경고", "이미 존재하는 키워드입니다.")
    
    def delete_selected_keywords(self):
        """비활성화된 키워드 삭제"""
        to_delete = [kw for kw, (_, enabled) in self.keyword_buttons.items() if not enabled]
        
        if not to_delete:
            messagebox.showinfo("안내", "삭제할 비활성화된 키워드가 없습니다.\n삭제하려면 키워드를 클릭하여 비활성화(회색)하세요.")
            return
        
        if messagebox.askyesno("확인", f"{len(to_delete)}개의 비활성화된 키워드를 삭제하시겠습니까?"):
            for kw in to_delete:
                btn, _ = self.keyword_buttons[kw]
                btn.destroy()
                del self.keyword_buttons[kw]
            
            self.refresh_keyword_grid()
            self.save_config_quietly()
            self.log_msg(f"🗑️ {len(to_delete)}개 키워드 삭제")
    
    def refresh_preset_dropdown(self):
        """프리셋 드롭다운 업데이트"""
        self.combo_preset['values'] = list(self.presets.keys())
    
    def save_preset(self):
        """현재 키워드를 프리셋으로 저장"""
        keywords = list(self.keyword_buttons.keys())
        if not keywords:
            messagebox.showwarning("경고", "저장할 키워드가 없습니다.")
            return
        
        from tkinter.simpledialog import askstring
        name = askstring("프리셋 저장", "프리셋 이름을 입력하세요:")
        if name:
            self.presets[name] = keywords
            self.save_presets()
            self.refresh_preset_dropdown()
            self.preset_var.set(name)
            self.log_msg(f"💾 프리셋 저장: {name} ({len(keywords)}개 키워드)")
    
    def load_preset(self, event=None):
        """프리셋 불러오기"""
        name = self.preset_var.get()
        if name and name in self.presets:
            # 기존 버튼 제거
            for kw in list(self.keyword_buttons.keys()):
                btn, _ = self.keyword_buttons[kw]
                btn.destroy()
            self.keyword_buttons.clear()
            
            # 새 버튼 추가
            for kw in self.presets[name]:
                self.add_keyword_button(kw, enabled=True)
            
            self.save_config_quietly()
            self.log_msg(f"📂 프리셋 불러오기: {name}")
    
    def delete_preset(self):
        """프리셋 삭제"""
        name = self.preset_var.get()
        if name and name in self.presets:
            if messagebox.askyesno("확인", f"프리셋 '{name}'을(를) 삭제하시겠습니까?"):
                del self.presets[name]
                self.save_presets()
                self.refresh_preset_dropdown()
                self.preset_var.set('')
                self.log_msg(f"🗑️ 프리셋 삭제: {name}")
    
    def select_month(self, month):
        """월 선택 버튼 토글"""
        self.selected_month = month
        
        # 모든 월 버튼 초기화
        self.btn_month_9.config(bg='SystemButtonFace', fg='black')
        self.btn_month_10.config(bg='SystemButtonFace', fg='black')
        self.btn_month_11.config(bg='SystemButtonFace', fg='black')
        
        # 선택된 월 활성화
        if month == 9:
            self.btn_month_9.config(bg='#4CAF50', fg='white')
        elif month == 10:
            self.btn_month_10.config(bg='#4CAF50', fg='white')
        elif month == 11:
            self.btn_month_11.config(bg='#4CAF50', fg='white')
        
        self.log_msg(f"📅 {month}월 선택")
    
    def show_calendar_popup(self):
        """캘린더 팝업 표시 (선택된 월만)"""
        month = self.selected_month
        
        cal_win = Toplevel(self.root)
        cal_win.title(f"📅 {month}월 날짜 선택")
        
        # 창 크기 및 화면 중앙 위치
        win_width, win_height = 270, 300
        screen_width = cal_win.winfo_screenwidth()
        screen_height = cal_win.winfo_screenheight()
        x = (screen_width - win_width) // 2
        y = (screen_height - win_height) // 2
        cal_win.geometry(f"{win_width}x{win_height}+{x}+{y}")
        cal_win.resizable(False, False)
        
        # 선택된 날짜 저장
        self.selected_dates = set()
        self.date_buttons = {}
        
        # 현재 연도
        current_year = datetime.now().year
        
        # 캘린더 프레임
        months_frame = ttk.Frame(cal_win, padding="10")
        months_frame.pack(fill=BOTH, expand=True)
        
        # 선택된 월 캘린더 생성
        month_frame = ttk.LabelFrame(months_frame, text=f"{month}월", padding="5")
        month_frame.pack(fill=BOTH, expand=True)
        
        # 요일 헤더
        days = ['일', '월', '화', '수', '목', '금', '토']
        for i, day in enumerate(days):
            lbl = ttk.Label(month_frame, text=day, width=3, anchor='center')
            lbl.grid(row=0, column=i)
            if day == '일':
                lbl.config(foreground='red')
            elif day == '토':
                lbl.config(foreground='blue')
        
        # 달력 데이터
        cal = calendar.Calendar(firstweekday=6)  # 일요일 시작
        month_days = cal.monthdayscalendar(current_year, month)
        
        for week_idx, week in enumerate(month_days):
            for day_idx, day in enumerate(week):
                if day == 0:
                    # 빈 칸
                    lbl = ttk.Label(month_frame, text="", width=3)
                    lbl.grid(row=week_idx + 1, column=day_idx)
                else:
                    # 날짜 버튼
                    date_key = f"{month}월{day}일"
                    btn = Button(month_frame, text=str(day), width=3,
                                 command=lambda m=month, d=day: self.toggle_calendar_date(m, d))
                    btn.grid(row=week_idx + 1, column=day_idx, padx=1, pady=1)
                    
                    # 색상 설정
                    if day_idx == 0:  # 일요일
                        btn.config(fg='red')
                    elif day_idx == 6:  # 토요일
                        btn.config(fg='blue')
                    
                    self.date_buttons[date_key] = btn
        # 선택 상태 라벨 (달력 테이블 내부 하단에 배치)
        last_row = len(month_days) + 2
        self.lbl_selected = ttk.Label(month_frame, text="0개", foreground="green")
        self.lbl_selected.grid(row=last_row, column=0, columnspan=2, sticky='w', padx=5, pady=(15, 5))
        
        # 버튼 프레임
        btn_frame = ttk.Frame(cal_win, padding="10")
        btn_frame.pack(fill=X)
        
        ttk.Button(btn_frame, text="✅ 확인", width=7,
                   command=lambda: self.add_selected_dates(cal_win)).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="전체선택", width=7,
                   command=self.select_all_calendar_dates).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="전체해제", width=7,
                   command=self.deselect_all_calendar_dates).pack(side=LEFT, padx=5)
    
    def toggle_calendar_date(self, month, day):
        """캘린더 날짜 토글"""
        date_key = f"{month}월{day}일"
        
        if date_key in self.selected_dates:
            self.selected_dates.remove(date_key)
            self.date_buttons[date_key].config(bg='SystemButtonFace')
        else:
            self.selected_dates.add(date_key)
            self.date_buttons[date_key].config(bg='#4CAF50', fg='white')
        
        self.lbl_selected.config(text=f"선택: {len(self.selected_dates)}개")
    
    def select_all_calendar_dates(self):
        """캘린더 전체 선택"""
        for date_key, btn in self.date_buttons.items():
            self.selected_dates.add(date_key)
            btn.config(bg='#4CAF50', fg='white')
        self.lbl_selected.config(text=f"선택: {len(self.selected_dates)}개")
    
    def deselect_all_calendar_dates(self):
        """캘린더 전체 해제"""
        for date_key, btn in self.date_buttons.items():
            btn.config(bg='SystemButtonFace', fg='black')
        self.selected_dates.clear()
        self.lbl_selected.config(text="선택: 0개")
    
    def add_selected_dates(self, cal_win):
        """선택된 날짜를 키워드로 추가"""
        if not self.selected_dates:
            messagebox.showinfo("안내", "선택된 날짜가 없습니다.")
            return
        
        added_count = 0
        for date_key in sorted(self.selected_dates):
            # 두 가지 형식으로 추가: "9월5일", "9월 5일"
            # date_key = "9월5일"
            parts = date_key.replace('월', ' ').replace('일', '').split()
            month = parts[0]
            day = parts[1]
            
            format1 = f"{month}월{day}일"     # 9월5일
            format2 = f"{month}월 {day}일"    # 9월 5일
            
            for kw in [format1, format2]:
                if kw not in self.keyword_buttons:
                    self.add_keyword_button(kw, enabled=True)
                    added_count += 1
        
        self.save_config_quietly()
        self.log_msg(f"📅 {len(self.selected_dates)}개 날짜 → {added_count}개 키워드 추가")
        cal_win.destroy()
    
    def show_alert_history(self):
        """알림 히스토리 창"""
        history_win = Toplevel(self.root)
        history_win.title("📋 알림 히스토리")
        history_win.geometry("500x400")
        
        text = scrolledtext.ScrolledText(history_win, wrap=WORD)
        text.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        if self.alert_history:
            for alert in reversed(self.alert_history):
                text.insert(END, f"{alert}\n{'─'*50}\n")
        else:
            text.insert(END, "알림 히스토리가 없습니다.")
        
        text.config(state=DISABLED)
    
    def update_stats(self):
        """통계 업데이트"""
        check = self.stats['check_count']
        alert = self.stats['alert_count']
        
        if self.stats['start_time']:
            elapsed = datetime.now() - self.stats['start_time']
            hours = elapsed.seconds // 3600
            mins = (elapsed.seconds % 3600) // 60
            time_str = f"{hours}시간 {mins}분"
        else:
            time_str = "-"
        
        self.lbl_stats.config(text=f"체크: {check}회 | 알림: {alert}건 | 실행시간: {time_str}")
    
    def get_active_keywords(self):
        """활성화된 키워드 목록 반환"""
        return [kw for kw, (_, enabled) in self.keyword_buttons.items() if enabled]
    
    def start_monitoring(self):
        """모니터링 시작"""
        self.save_config()
        
        active_keywords = self.get_active_keywords()
        if not active_keywords:
            messagebox.showwarning("경고", "활성화된 키워드가 없습니다.\n키워드를 클릭하여 활성화(녹색)하세요.")
            return
        
        self.is_running = True
        self.stats['start_time'] = datetime.now()
        self.stats['check_count'] = 0
        self.stats['alert_count'] = 0
        
        self.btn_start.config(state=DISABLED)
        self.btn_stop.config(state=NORMAL)
        self.lbl_status.config(text="🟢 모니터링 중", foreground="green")
        
        self.log_msg(f"▶ 모니터링 시작 (활성 키워드: {len(active_keywords)}개)")
        
        self.monitor_thread = threading.Thread(target=self.monitoring_loop, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """모니터링 중지"""
        self.is_running = False
        self.btn_start.config(state=NORMAL)
        self.btn_stop.config(state=DISABLED)
        self.lbl_status.config(text="⚪ 대기 중", foreground="gray")
        self.log_msg("⬛ 모니터링 중지")
        
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
    
    def monitoring_loop(self):
        """모니터링 루프 (별도 스레드)"""
        try:
            # 드라이버 설정
            if not self.setup_driver():
                self.root.after(0, lambda: messagebox.showerror("오류", "Chrome 드라이버 설정 실패"))
                self.root.after(0, self.stop_monitoring)
                return
            
            # 네이버 로그인
            if not self.login_naver():
                self.root.after(0, lambda: messagebox.showerror("오류", "네이버 로그인 실패"))
                self.root.after(0, self.stop_monitoring)
                return
            
            # 게시판 접근
            if not self.access_board():
                self.root.after(0, lambda: messagebox.showerror("오류", "게시판 접근 실패"))
                self.root.after(0, self.stop_monitoring)
                return
            
            # 메인 모니터링 루프
            while self.is_running:
                # 수면 시간 체크
                if self.is_sleep_time():
                    self.root.after(0, lambda: self.log_msg("🌙 수면 시간대 - 대기 중..."))
                    self.root.after(0, lambda: self.lbl_status.config(text="😴 수면 모드", foreground="purple"))
                    while self.is_running and self.is_sleep_time():
                        time.sleep(60)
                    if self.is_running:
                        self.root.after(0, lambda: self.log_msg("☀️ 수면 종료 - 모니터링 재개"))
                        self.root.after(0, lambda: self.lbl_status.config(text="🟢 모니터링 중", foreground="green"))
                    continue
                
                # 게시글 체크
                self.check_posts()
                self.stats['check_count'] += 1
                self.root.after(0, self.update_stats)
                
                # 랜덤 대기
                if self.is_running:
                    interval = random.randint(
                        int(self.entry_interval_min.get() or 20),
                        int(self.entry_interval_max.get() or 30)
                    )
                    self.root.after(0, lambda i=interval: self.log_msg(f"⏰ 다음 체크까지 {i}초 대기..."))
                    
                    for _ in range(interval):
                        if not self.is_running:
                            break
                        time.sleep(1)
        
        except Exception as e:
            self.root.after(0, lambda: self.log_msg(f"❌ 오류 발생: {e}"))
        
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None
            self.root.after(0, self.stop_monitoring)
    
    def setup_driver(self):
        """Chrome 드라이버 설정"""
        try:
            chrome_options = Options()
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            if self.var_headless.get():
                chrome_options.add_argument("--headless")
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            self.root.after(0, lambda: self.log_msg("✅ Chrome 드라이버 설정 완료"))
            return True
        except Exception as e:
            self.root.after(0, lambda: self.log_msg(f"❌ 드라이버 설정 실패: {e}"))
            return False
    
    def login_naver(self):
        """네이버 로그인"""
        try:
            self.root.after(0, lambda: self.log_msg("🔐 네이버 로그인 시도..."))
            
            self.driver.get("https://nid.naver.com/nidlogin.login")
            time.sleep(3)
            
            id_input = self.driver.find_element(By.ID, "id")
            pw_input = self.driver.find_element(By.ID, "pw")
            
            self.driver.execute_script(f"arguments[0].value='{self.config['naver_id']}';", id_input)
            time.sleep(0.5)
            self.driver.execute_script(f"arguments[0].value='{self.config['naver_password']}';", pw_input)
            time.sleep(0.5)
            
            login_btn = self.driver.find_element(By.ID, "log.login")
            login_btn.click()
            
            time.sleep(5)
            
            # 등록안함 버튼 처리
            try:
                elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), '등록안함')]")
                for elem in elements:
                    if elem.is_displayed():
                        self.driver.execute_script("arguments[0].click();", elem)
                        time.sleep(2)
                        break
            except:
                pass
            
            if "nid.naver.com" not in self.driver.current_url:
                self.root.after(0, lambda: self.log_msg("✅ 네이버 로그인 성공!"))
                return True
            else:
                self.root.after(0, lambda: self.log_msg("❌ 로그인 실패"))
                return False
                
        except Exception as e:
            self.root.after(0, lambda: self.log_msg(f"❌ 로그인 오류: {e}"))
            return False
    
    def access_board(self):
        """게시판 접근"""
        try:
            board_url = self.config.get('board_url', '')
            if board_url:
                self.driver.get(board_url)
                time.sleep(3)
                self.root.after(0, lambda: self.log_msg("✅ 게시판 접근 완료"))
                return True
            else:
                self.root.after(0, lambda: self.log_msg("❌ 게시판 URL이 설정되지 않음"))
                return False
        except Exception as e:
            self.root.after(0, lambda: self.log_msg(f"❌ 게시판 접근 실패: {e}"))
            return False
    
    def check_posts(self):
        """게시글 체크 (원본 naver_cafe_monitor.py 방식)"""
        try:
            self.driver.refresh()
            time.sleep(3)
            
            # 프레임 전환
            try:
                cafe_frame = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.ID, "cafe_main"))
                )
                self.driver.switch_to.frame(cafe_frame)
                self.root.after(0, lambda: self.log_msg("🔄 cafe_main 프레임 전환 완료"))
            except:
                self.root.after(0, lambda: self.log_msg("⚠️ 프레임 전환 실패, 현재 프레임에서 진행"))
            
            # 네이버 카페 양도게시판 전용 셀렉터 (p.memo-box 패턴)
            post_elements = []
            
            # 1차: p.memo-box[id^='post_'] 패턴 시도 (가장 정확)
            try:
                post_elements = self.driver.find_elements(By.CSS_SELECTOR, "p.memo-box[id^='post_']")
                if post_elements:
                    self.root.after(0, lambda n=len(post_elements): self.log_msg(f"✅ 'p.memo-box' 패턴으로 {n}개 게시글 발견"))
            except:
                pass
            
            # 2차: 일반 셀렉터 시도
            if not post_elements:
                selectors_to_try = [
                    "div.memo-box",
                    "article.memo",
                    "div[class*='article']",
                    "tbody tr",
                    "table tr",
                ]
                for selector in selectors_to_try:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if len(elements) > 1:
                            post_elements = elements
                            self.root.after(0, lambda s=selector, n=len(elements): self.log_msg(f"✅ '{s}' 선택자로 {n}개 요소 발견"))
                            break
                    except:
                        continue
            
            if not post_elements:
                self.root.after(0, lambda: self.log_msg("⚠️ 게시글 목록을 찾을 수 없습니다."))
                self.driver.switch_to.default_content()
                return
            
            active_keywords = self.get_active_keywords()
            new_count = 0
            
            # 최근 10개만 확인
            check_elements = post_elements[:10]
            
            for i, post in enumerate(check_elements):
                try:
                    # 게시글 ID 추출
                    post_id = post.get_attribute("id") or f"post_{i}"
                    
                    if post_id in self.monitored_posts:
                        continue
                    
                    # 게시글의 전체 내용 추출
                    all_text = post.text.strip()
                    if not all_text or len(all_text) < 10:
                        continue
                    
                    # 제목 추출 (첫 줄)
                    lines = all_text.split('\n')
                    title = lines[0].strip() if lines else all_text[:50]
                    
                    # 링크 추출
                    href = ""
                    try:
                        link = post.find_element(By.CSS_SELECTOR, "a")
                        href = link.get_attribute("href") or ""
                    except:
                        href = f"https://cafe.naver.com/badajd#{post_id}"
                    
                    # 키워드 매칭 (전체 내용에서 검색)
                    for keyword in active_keywords:
                        if keyword in all_text:
                            self.monitored_posts.add(post_id)
                            new_count += 1
                            
                            # 알림 전송
                            self.send_alert(title, href, keyword)
                            self.root.after(0, lambda k=keyword, t=title[:30]: self.log_msg(f"🎯 키워드 발견: {k} → {t}..."))
                            break
                    
                    self.monitored_posts.add(post_id)
                    
                except Exception as e:
                    continue
            
            self.root.after(0, lambda n=new_count: self.log_msg(f"🔍 게시글 체크 완료 ({n}개 키워드 매칭)"))
            self.driver.switch_to.default_content()
            
        except Exception as e:
            self.root.after(0, lambda err=str(e): self.log_msg(f"⚠️ 게시글 체크 중 오류: {err}"))
    
    def send_alert(self, title, url, keyword):
        """텔레그램 알림 전송"""
        token = self.config.get('telegram_bot_token', '')
        chat_id = self.config.get('telegram_chat_id', '')
        
        if not token or not chat_id:
            return
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f"""🔔 <b>양도 게시글 발견!</b>

📋 <b>제목:</b> {title}
🔑 <b>키워드:</b> {keyword}
🕐 <b>감지시간:</b> {timestamp}

🔗 <a href="{url}">게시글 바로가기</a>"""
        
        try:
            api_url = f"https://api.telegram.org/bot{token}/sendMessage"
            data = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
            requests.post(api_url, data=data, timeout=10)
            
            self.stats['alert_count'] += 1
            self.alert_history.append(f"[{timestamp}] 키워드: {keyword}\n제목: {title}\nURL: {url}")
            
            self.root.after(0, lambda: self.log_msg(f"📱 알림 전송: {keyword} - {title[:30]}..."))
            
        except Exception as e:
            self.root.after(0, lambda: self.log_msg(f"⚠️ 알림 전송 실패: {e}"))
    
    def is_sleep_time(self):
        """수면 시간대 체크"""
        now = datetime.now()
        current_mins = now.hour * 60 + now.minute
        
        start_mins = self.config.get('sleep_start_hour', 23) * 60 + self.config.get('sleep_start_minute', 59)
        end_mins = self.config.get('sleep_end_hour', 5) * 60 + self.config.get('sleep_end_minute', 0)
        
        if start_mins > end_mins:
            return current_mins >= start_mins or current_mins <= end_mins
        else:
            return start_mins <= current_mins <= end_mins
    
    # ========== 트레이 숨김 기능 ==========
    def get_console_window(self):
        """콘솔 창 핸들 가져오기"""
        return ctypes.windll.kernel32.GetConsoleWindow()
    
    def hide_console(self):
        """콘솔 창 숨기기"""
        hwnd = self.get_console_window()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)
            try:
                ctypes.windll.kernel32.FreeConsole()
            except:
                pass
    
    def show_console(self):
        """콘솔 창 보이기"""
        try:
            ctypes.windll.kernel32.AllocConsole()
        except:
            pass
        hwnd = self.get_console_window()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 5)
    
    def create_tray_icon_image(self):
        """트레이 아이콘 이미지 생성 (녹색 - 카페 모니터)"""
        img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # 녹색 원 배경
        draw.ellipse([8, 8, 56, 56], fill=(76, 175, 80))
        # C 글자 (Cafe)
        draw.text((24, 16), "C", fill="white")
        return img
    
    def hide_to_tray(self):
        """트레이로 숨기기"""
        if not TRAY_AVAILABLE:
            self.log_msg("⚠️ 트레이 기능 사용 불가")
            return
        
        self.is_hidden = True
        self.root.withdraw()
        self.hide_console()
        
        icon_image = self.create_tray_icon_image()
        
        menu = pystray.Menu(
            pystray.MenuItem("🖥️ 창 열기", self.show_from_tray, default=True),
            pystray.MenuItem("🛑 종료", self.exit_app)
        )
        
        self.tray_icon = pystray.Icon(
            "cafe_monitor",
            icon_image,
            "네이버 카페 모니터",
            menu
        )
        
        threading.Thread(target=self.tray_icon.run, daemon=True).start()
        self.log_msg("👁️ 트레이로 숨김")
    
    def show_from_tray(self, icon=None, item=None):
        """트레이에서 복원"""
        self.is_hidden = False
        
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None
        
        self.show_console()
        self.root.after(0, self.root.deiconify)
        self.root.after(100, self.root.lift)
    
    def exit_app(self, icon=None, item=None):
        """앱 종료"""
        if self.is_running:
            self.stop_monitoring()
        
        if self.tray_icon:
            self.tray_icon.stop()
        
        self.root.after(0, self.root.destroy)
    
    def on_closing(self):
        """윈도우 종료 시 (트레이로 숨김)"""
        if TRAY_AVAILABLE:
            self.hide_to_tray()
        else:
            if self.is_running:
                if messagebox.askyesno("확인", "모니터링 중입니다. 종료하시겠습니까?"):
                    self.stop_monitoring()
                    self.root.destroy()
            else:
                self.root.destroy()
    
    def run(self):
        """GUI 실행"""
        self.root.mainloop()


if __name__ == "__main__":
    app = NaverCafeMonitorGUI()
    app.run()
