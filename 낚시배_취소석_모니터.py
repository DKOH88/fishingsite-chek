"""
🎣 낚시배 취소석 모니터링 봇 v2.0
- 여러 낚시배 동시 감시 가능
- 선택한 날짜(9~11월)의 예약 가능 여부를 8~10분마다 체크
- 예약하기 버튼이 활성화되면 텔레그램 알림 전송
"""
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import messagebox
import tkinter as tk
import threading
import json
import os
import time
import random
import re
import requests
import ctypes
import subprocess
import tempfile
import calendar
import webbrowser
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs

# 트레이 아이콘 지원
try:
    import pystray
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False

from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ============================================
# 📁 설정
# ============================================
CONFIG_FILE = 'fishing_boat_monitor_config.json'
PRESETS_FILE = 'boat_presets.json'
HTTP_TIMEOUT = (5, 10)               # (connect, read) seconds
SUMMARY_INTERVAL_SECONDS = 4 * 3600  # 종합 알람 간격: 4시간
NIGHT_BREAK_START_RANGE = (-10, 5)   # 랜덤 시작: 23:50 ~ 00:05
NIGHT_BREAK_END_RANGE = (50, 65)     # 랜덤 종료: 06:50 ~ 07:05

# ============================================
# DESIGN TOKENS (ttkbootstrap "darkly" 테마 정렬)
# ============================================

# -- Spacing (8px grid) --
SP_XS, SP_SM, SP_MD, SP_LG, SP_XL = 2, 4, 8, 12, 16

# -- Typography --
FONT_FAMILY, FONT_MONO = '맑은 고딕', 'Consolas'
FONT_SIZE_SM, FONT_SIZE_MD, FONT_SIZE_LG = 9, 10, 12

# -- Theme-aligned colors (darkly palette) --
CLR_BG_SURFACE = '#2f2f2f'
CLR_FG         = '#ffffff'
CLR_FG_MUTED   = '#ADB5BD'
CLR_SUCCESS    = '#00bc8c'   # darkly success
CLR_DANGER     = '#e74c3c'   # darkly danger
CLR_WARNING    = '#f39c12'   # darkly warning
CLR_INFO       = '#3498db'   # darkly info
CLR_SECONDARY  = '#444444'   # darkly secondary

# 보트 모드 → (배경색, 전경색) 매핑
MODE_COLORS = {
    'monitor': (CLR_SUCCESS, CLR_FG),
    'reserve': (CLR_DANGER, CLR_FG),
    'off':     (CLR_SECONDARY, CLR_FG_MUTED),
}

# Log 색상
CLR_LOG_BG        = '#1a1a2e'
CLR_LOG_FG        = '#e0e0e0'
CLR_LOG_TIMESTAMP = '#888888'
CLR_LOG_SUCCESS   = '#00bc8c'
CLR_LOG_ERROR     = '#e74c3c'
CLR_LOG_WARNING   = '#f39c12'
CLR_LOG_INFO      = '#3498db'

# 보트 모드 → ttk.Style 이름 매핑
BOAT_STYLE_MAP = {
    'monitor': 'Monitor.TButton',
    'reserve': 'Reserve.TButton',
    'off':     'Off.TButton',
}

def _toggle_style(is_active: bool, prefix: str = 'Platform') -> str:
    """토글 버튼 스타일 이름 반환"""
    return f'{prefix}Active.TButton' if is_active else f'{prefix}Inactive.TButton'

# 플랫폼 config 키 (load_config, save/load_preset, refresh_boat_grid 등에서 공용)
PLATFORM_KEYS = ('thefishing_boats', 'sunsang24_boats')

# 플랫폼 한글 표시명 (switch_platform, start_monitor, add_boat 등에서 공용)
PLATFORM_NAMES = {'thefishing': '더피싱', 'sunsang24': '선상24'}

# config 키 → 한글 이름 매핑 (pk.replace('_boats','') 제거용)
PLATFORM_KEY_NAMES = {pk: PLATFORM_NAMES[pk.replace('_boats', '')] for pk in PLATFORM_KEYS}
PLATFORM_KEY_ICONS = {'thefishing_boats': '🎣', 'sunsang24_boats': '⛵'}

# 감시 가능 월 (GUI 캘린더, 사이트가기 월 버튼, 날짜 요약에서 공용)
MONITOR_MONTHS = (9, 10, 11)
EMPTY_MONTH_DAYS = {f"{m:02d}": [] for m in MONITOR_MONTHS}  # 빈 월-일 템플릿

# HTTP 치명적 오류 키워드 (is_critical_error에서 사용)
CRITICAL_KEYWORDS = (
    "connection refused",
    "max retries exceeded",
    "connectionerror",
    "timeout",
    "too many redirects",
)

# 봇 폴더 경로 (실행 파일 기준 상대 경로)
BOT_FOLDERS = {
    'thefishing': os.path.join('bots', 'API', '더피싱'),
    'sunsang24': os.path.join('bots', 'API', '선상24'),
}


def scan_bot_folder(platform: str) -> list:
    """봇 폴더에서 *_API.py 파일을 스캔하여 선박명 리스트 반환.
    base_api_bot.py, *봇 생성기*.py 등 유틸리티 파일은 제외."""
    folder = BOT_FOLDERS.get(platform, '')
    if not os.path.isdir(folder):
        return []
    names = []
    for fname in sorted(os.listdir(folder)):
        if fname.endswith('_API.py') and 'base' not in fname.lower() and '생성기' not in fname:
            boat_name = fname.replace('_API.py', '')
            names.append(boat_name)
    return names


DEFAULT_CONFIG = {
    "telegram_token": "8538517871:AAEd0Ob4O2oSk-e3NZDDfz6zSHsTf0MGD74",
    "telegram_chat_id": "393163178",
    "target_year": "2026",
    "target_months": ["09", "10", "11"],
    "target_days": dict(EMPTY_MONTH_DAYS),
    "check_interval_min": 8,
    "check_interval_max": 10,
    "current_platform": "thefishing",  # thefishing 또는 sunsang24
    "thefishing_boats": [
        {"name": "금땡이호", "enabled": False, "base_url": "http://xn--jj0bj3lvmq92n.kr/index.php", "pa_n_uid": "5492"},
        {"name": "까칠이호", "enabled": False, "base_url": "https://xn--hl0b209b41esvi.com/index.php", "pa_n_uid": "3973"},
        {"name": "깜보호", "enabled": False, "base_url": "https://winner.thefishing.kr/index.php", "pa_n_uid": "3970"},
        {"name": "나폴리호", "enabled": False, "base_url": "https://www.napoliho.net/index.php", "pa_n_uid": "1484"},
        {"name": "뉴신정호", "enabled": False, "base_url": "http://newsj.co.kr/index.php", "pa_n_uid": "4452"},
        {"name": "뉴청남호", "enabled": False, "base_url": "http://www.chungnamho.com/index.php", "pa_n_uid": "5951"},
        {"name": "루디호", "enabled": False, "base_url": "http://www.rudyfishing.com/index.php", "pa_n_uid": "3468"},
        {"name": "마그마호", "enabled": False, "base_url": "http://xn--2i0b07tba4320a.kr/index.php", "pa_n_uid": "5352"},
        {"name": "범블비호", "enabled": True, "base_url": "http://xn--xk3bm1aee249g.com/index.php", "pa_n_uid": "3324"},
        {"name": "미라클호", "enabled": False, "base_url": "http://xn--2i0b07tba4320a.kr/index.php", "pa_n_uid": "5361"},
        {"name": "부흥호", "enabled": False, "base_url": "http://www.anhbuh.com/index.php", "pa_n_uid": "2928"},
        {"name": "블레스호", "enabled": False, "base_url": "http://www.blessho.com/index.php", "pa_n_uid": "3288"},
        {"name": "블루호", "enabled": False, "base_url": "https://bluefishing.asia/index.php", "pa_n_uid": "1615"},
        {"name": "샤크호", "enabled": False, "base_url": "http://www.sharkho.com/index.php", "pa_n_uid": "2199"},
        {"name": "솔티가호", "enabled": False, "base_url": "http://www.rudyfishing.com/index.php", "pa_n_uid": "5367"},
        {"name": "아인스호", "enabled": False, "base_url": "https://www.einsho.com/index.php", "pa_n_uid": "349"},
        {"name": "아일랜드호", "enabled": False, "base_url": "http://www.fishingi.net/index.php", "pa_n_uid": "1444"},
        {"name": "야야호", "enabled": False, "base_url": "http://www.yayaho.kr/index.php", "pa_n_uid": "3960"},
        {"name": "여명호", "enabled": False, "base_url": "http://xn--v42bv0rcoar53c6lb.kr/index.php", "pa_n_uid": "5030"},
        {"name": "오디세이호", "enabled": False, "base_url": "http://www.joeunfish.com/index.php", "pa_n_uid": "788"},
        {"name": "유진호", "enabled": False, "base_url": "https://www.eugeneho.kr/index.php", "pa_n_uid": "1190"},
        {"name": "천일호", "enabled": False, "base_url": "http://fishing1001.com/index.php", "pa_n_uid": "1443"},
        {"name": "청광호", "enabled": False, "base_url": "http://www.chungkwangho.net/index.php", "pa_n_uid": "1588"},
        {"name": "청남호", "enabled": False, "base_url": "http://www.chungnamho.com/index.php", "pa_n_uid": "1441"},
        {"name": "청용호", "enabled": False, "base_url": "http://www.changdukho.com/index.php", "pa_n_uid": "271"},
        {"name": "카즈미호", "enabled": False, "base_url": "https://xn--hg3b11w8xdjuj.com/index.php", "pa_n_uid": "4576"},
        {"name": "퀸블레스호", "enabled": False, "base_url": "http://www.blessho.com/index.php", "pa_n_uid": "4675"},
        {"name": "팀루피호", "enabled": False, "base_url": "https://masterfishing.kr/index.php", "pa_n_uid": "2805"},
        {"name": "팀바이트호", "enabled": False, "base_url": "http://teambite.kr/index.php", "pa_n_uid": "5948"},
        {"name": "페라리호", "enabled": False, "base_url": "http://www.xn--oi2bn5b095b4mc.com/index.php", "pa_n_uid": "1264"},
        {"name": "행운호", "enabled": False, "base_url": "http://www.hangwoonho.com/index.php", "pa_n_uid": "3448"},
        {"name": "헤라호", "enabled": False, "base_url": "https://www.ssfish.kr/index.php", "pa_n_uid": "3609"},
        {"name": "골드피싱호", "enabled": False, "base_url": "http://www.mscufishing.com/index.php", "pa_n_uid": "2954"},
        {"name": "뉴찬스호", "enabled": False, "base_url": "http://www.chanceho.com/index.php", "pa_n_uid": "2283"},
        {"name": "만석호", "enabled": False, "base_url": "http://www.mscufishing.com/index.php", "pa_n_uid": "3570"},
        {"name": "베스트3호", "enabled": False, "base_url": "https://khanfishing.com/index.php", "pa_n_uid": "5340"},
        {"name": "스타피싱호", "enabled": False, "base_url": "https://jstar.thefishing.kr/index.php", "pa_n_uid": "1925"},
        {"name": "승주호", "enabled": False, "base_url": "http://www.mscufishing.com/index.php", "pa_n_uid": "2955"},
        {"name": "아라호", "enabled": False, "base_url": "https://www.araho.kr/index.php", "pa_n_uid": "5732"},
        {"name": "아이리스호", "enabled": False, "base_url": "http://www.irisho.kr/index.php", "pa_n_uid": "1545"},
        {"name": "야호", "enabled": False, "base_url": "http://xn--2f5b291a.com/index.php", "pa_n_uid": "3904"},
        {"name": "예린호", "enabled": False, "base_url": "http://www.yerinfishing.com/index.php", "pa_n_uid": "3515"},
        {"name": "와이파이호", "enabled": False, "base_url": "https://khanfishing.com/index.php", "pa_n_uid": "5264"},
        {"name": "으리호", "enabled": False, "base_url": "http://www.mscufishing.com/index.php", "pa_n_uid": "4920"},
        {"name": "제트호", "enabled": False, "base_url": "https://khanfishing.com/index.php", "pa_n_uid": "5341"},
        {"name": "지오디호", "enabled": False, "base_url": "https://www.teamgod.kr/index.php", "pa_n_uid": "5295"},
        {"name": "짱구호", "enabled": False, "base_url": "http://www.ybada.com/index.php", "pa_n_uid": "1677"},
        {"name": "팀만수호", "enabled": False, "base_url": "https://teammansu.kr/index.php", "pa_n_uid": "2829"},
        {"name": "하와이호", "enabled": False, "base_url": "http://www.newhawaii.co.kr/index.php", "pa_n_uid": "4667"},
        {"name": "헌터호", "enabled": False, "base_url": "http://www.mscufishing.com/index.php", "pa_n_uid": "4443"},
        {"name": "헤르메스호", "enabled": False, "base_url": "http://hermes.thefishing.kr/index.php", "pa_n_uid": "5579"},
    ],
    "sunsang24_boats": [
        {"name": "가가호", "enabled": False, "base_url": "https://gagaho.sunsang24.com"},
        {"name": "기가호", "enabled": False, "base_url": "https://giga.sunsang24.com"},
        {"name": "자이언트호", "enabled": False, "base_url": "https://rkclgh.sunsang24.com"},
        {"name": "도지호", "enabled": False, "base_url": "https://doji.sunsang24.com"},
        {"name": "팀에프원", "enabled": False, "base_url": "https://teamf.sunsang24.com"},
        {"name": "팀에프투", "enabled": False, "base_url": "https://teamf.sunsang24.com"},
        {"name": "천마호", "enabled": False, "base_url": "https://metafishingclub.sunsang24.com"},
    ]
}


# ============================================
# 📅 캘린더 팝업
# ============================================
class CalendarPopup:
    """월별 캘린더 팝업 - 여러 날짜 선택 가능"""
    
    def __init__(self, parent, year: int, month: int, selected_days: list = None, callback=None):
        self.parent = parent
        self.year = year
        self.month = month
        self.selected_days = {str(d) for d in (selected_days or [])}
        self.callback = callback
        self.day_buttons = {}
        
        self.popup = tk.Toplevel(parent)
        self.popup.title(f"📅 {year}년 {month}월 날짜 선택")
        self.popup.transient(parent)
        self.popup.grab_set()
        
        # 창 위치 (부모 창 중앙)
        w, h = 400, 450
        x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (w // 2)
        y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (h // 2)
        self.popup.geometry(f'{w}x{h}+{x}+{y}')
        
        self.create_widgets()
    
    # ── Canvas 기반 캘린더 (ttkbootstrap 테마 영향 완전 차단) ──
    CELL_W, CELL_H = 48, 34
    COLS = 7
    BG_CANVAS = '#1a1a2e'
    CLR_SEL_BG = '#00bc8c'
    CLR_SEL_FG = '#ffffff'
    CLR_OFF_BG = '#2f2f2f'
    CLR_OFF_FG = '#ADB5BD'

    def create_widgets(self):
        main_frame = ttk.Frame(self.popup, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 헤더
        ttk.Label(main_frame, text=f"{self.year}년 {self.month}월",
                  font=(FONT_FAMILY, 14, "bold")).pack(pady=5)

        # 선택된 날짜 표시
        self.lbl_selected = ttk.Label(main_frame, text=self.get_selection_text(),
                                      foreground=CLR_INFO)
        self.lbl_selected.pack(pady=(0, SP_SM))

        # 달력 그리드 계산
        cal = calendar.Calendar(firstweekday=6)
        days_in_month = list(cal.itermonthdays(self.year, self.month))
        num_rows = (len(days_in_month) // self.COLS) + 1  # +1 for weekday header

        cw = self.CELL_W * self.COLS
        ch = self.CELL_H * num_rows

        canvas = tk.Canvas(main_frame, width=cw, height=ch,
                           bg=self.BG_CANVAS, highlightthickness=0)
        canvas.pack(pady=5)
        self.canvas = canvas

        # 요일 헤더 그리기
        weekdays = ["일", "월", "화", "수", "목", "금", "토"]
        for i, wd in enumerate(weekdays):
            fg = '#ff6b6b' if i == 0 else ('#6b9fff' if i == 6 else self.CLR_OFF_FG)
            cx = i * self.CELL_W + self.CELL_W // 2
            cy = self.CELL_H // 2
            canvas.create_text(cx, cy, text=wd, fill=fg,
                               font=(FONT_FAMILY, FONT_SIZE_SM, 'bold'))

        # 날짜 셀 그리기
        row, col = 1, 0
        for day in days_in_month:
            if day != 0:
                is_sel = str(day) in self.selected_days
                self._draw_cell(day, row, col, is_sel)
            col += 1
            if col >= self.COLS:
                col = 0
                row += 1

        canvas.bind('<Button-1>', self._on_canvas_click)

        # 확인 / 취소 버튼
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="확인", command=self.confirm, width=8).pack(side=tk.LEFT, padx=SP_SM)
        ttk.Button(btn_frame, text="취소", command=self.cancel, width=8).pack(side=tk.LEFT, padx=SP_SM)

    def _draw_cell(self, day, row, col, is_selected):
        """Canvas 위에 날짜 셀(사각형+텍스트) 그리기"""
        bg = self.CLR_SEL_BG if is_selected else self.CLR_OFF_BG
        fg = self.CLR_SEL_FG if is_selected else self.CLR_OFF_FG
        x1 = col * self.CELL_W + 2
        y1 = row * self.CELL_H + 2
        x2 = x1 + self.CELL_W - 4
        y2 = y1 + self.CELL_H - 4
        tag = f'd{day}'
        self.canvas.delete(tag)
        self.canvas.create_rectangle(x1, y1, x2, y2, fill=bg, outline='', tags=tag)
        self.canvas.create_text((x1 + x2) // 2, (y1 + y2) // 2,
                                text=str(day), fill=fg,
                                font=(FONT_FAMILY, FONT_SIZE_MD), tags=tag)
        # 셀 위치 저장
        self.day_buttons[day] = (row, col)

    def _on_canvas_click(self, event):
        """Canvas 클릭 → 날짜 토글"""
        col = event.x // self.CELL_W
        row = event.y // self.CELL_H
        if row < 1 or col >= self.COLS:
            return
        # 해당 row, col에 매핑된 day 찾기
        for day, (r, c) in self.day_buttons.items():
            if r == row and c == col:
                self.toggle_day(day)
                return


    def toggle_day(self, day):
        """날짜 선택/해제 토글"""
        day_str = str(day)
        if day_str in self.selected_days:
            self.selected_days.discard(day_str)
        else:
            self.selected_days.add(day_str)

        pos = self.day_buttons.get(day)
        if pos:
            row, col = pos
            self._draw_cell(day, row, col, day_str in self.selected_days)
        self.lbl_selected.config(text=self.get_selection_text())

    def select_all(self):
        """전체 선택"""
        _, days_count = calendar.monthrange(self.year, self.month)
        for day in range(1, days_count + 1):
            self.selected_days.add(str(day))
            pos = self.day_buttons.get(day)
            if pos:
                self._draw_cell(day, pos[0], pos[1], True)
        self.lbl_selected.config(text=self.get_selection_text())

    def clear_all(self):
        """전체 취소"""
        self.selected_days.clear()
        for day, (r, c) in self.day_buttons.items():
            self._draw_cell(day, r, c, False)
        self.lbl_selected.config(text=self.get_selection_text())
    
    def get_selection_text(self):
        """선택된 날짜 텍스트"""
        sorted_days = sorted([int(d) for d in self.selected_days if d])
        if not sorted_days:
            return "선택된 날짜 없음"
        cnt = len(sorted_days)
        days_str = ', '.join(f"{d}일" for d in sorted_days[:15])
        if cnt > 15:
            days_str += f" ... (+{cnt - 15})"
        return f"선택된 날짜 - {days_str}"
    
    def confirm(self):
        """확인"""
        sorted_days = sorted([str(int(d)) for d in self.selected_days if d])
        if self.callback:
            self.callback(self.month, sorted_days)
        self.popup.destroy()
    
    def cancel(self):
        """취소"""
        self.popup.destroy()


# ============================================
# ✏️ 선사 편집 팝업
# ============================================
class BoatEditorPopup:
    """선사 편집 팝업 — 봇 폴더 스캔 결과로 체크박스 표시, 체크=그리드에 표시"""

    def __init__(self, parent, platform, boats_config, callback=None):
        self.parent = parent
        self.platform = platform
        self.boats_config = boats_config  # 현재 config의 보트 리스트 (dict 리스트)
        self.callback = callback
        self.check_vars = {}  # {선박명: BooleanVar}

        # 기존 config에서 선박명 → dict 매핑
        self.config_map = {b['name']: b for b in boats_config}

        # 봇 폴더 스캔
        self.folder_names = scan_bot_folder(platform)

        # 통합 선박 목록: 폴더 이름 + config에만 있는 이름
        config_names = set(self.config_map.keys())
        folder_set = set(self.folder_names)
        # 폴더에 있는 것 우선, 그 뒤에 config에만 있는 것 (가나다순)
        config_only = sorted(config_names - folder_set)
        self.all_names = self.folder_names + config_only

        self.popup = tk.Toplevel(parent)
        platform_label = PLATFORM_NAMES.get(platform, platform)
        self.popup.title(f"✏️ {platform_label} 선사 편집")
        self.popup.transient(parent)
        self.popup.grab_set()

        # 창 위치 (부모 창 중앙)
        w, h = 400, 700
        x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (w // 2)
        y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (h // 2)
        self.popup.geometry(f'{w}x{h}+{x}+{y}')

        self._create_widgets()

    def _create_widgets(self):
        main_frame = ttk.Frame(self.popup, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 헤더
        platform_label = PLATFORM_NAMES.get(self.platform, self.platform)
        header = ttk.Label(main_frame, text=f"✏️ {platform_label} 선사 편집",
                           font=("맑은 고딕", 14, "bold"))
        header.pack(pady=5)
        ttk.Label(main_frame, text="체크한 선사만 그리드에 표시됩니다",
                  foreground="gray").pack(pady=2)

        # 모두 선택/해제 행
        sel_row = ttk.Frame(main_frame)
        sel_row.pack(fill=tk.X, pady=(5, 2))
        ttk.Button(sel_row, text="모두 선택", command=self._select_all,
                   width=10).pack(side=tk.LEFT, padx=3)
        ttk.Button(sel_row, text="모두 해제", command=self._clear_all,
                   width=10).pack(side=tk.LEFT, padx=3)
        self.lbl_count = ttk.Label(sel_row, text="", foreground="blue")
        self.lbl_count.pack(side=tk.RIGHT, padx=5)

        # 스크롤 가능한 체크박스 영역 (Canvas + Scrollbar)
        canvas_frame = ttk.Frame(main_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        canvas = tk.Canvas(canvas_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=canvas.yview)
        self.inner_frame = ttk.Frame(canvas)

        self.inner_frame.bind(
            '<Configure>',
            lambda e: canvas.configure(scrollregion=canvas.bbox('all'))
        )
        canvas.create_window((0, 0), window=self.inner_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 마우스 휠 스크롤 바인딩
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all('<MouseWheel>', _on_mousewheel)
        self.popup.bind('<Destroy>', lambda e: canvas.unbind_all('<MouseWheel>'))

        # 체크박스 생성
        for name in self.all_names:
            var = tk.BooleanVar()
            # visible 상태 결정: config에 있으면 visible 필드, 없으면 False (신규)
            if name in self.config_map:
                var.set(self.config_map[name].get('visible', True))
            else:
                var.set(False)

            self.check_vars[name] = var
            cb = ttk.Checkbutton(
                self.inner_frame, text=name, variable=var,
                command=self._update_count_label
            )
            cb.pack(anchor='w', padx=10, pady=1)

        self._update_count_label()

        # 확인/취소 버튼 행
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="확인", command=self._confirm,
                   width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="취소", command=self._cancel,
                   width=10).pack(side=tk.LEFT, padx=5)

    def _update_count_label(self):
        checked = sum(1 for v in self.check_vars.values() if v.get())
        total = len(self.check_vars)
        self.lbl_count.config(text=f"선택: {checked}/{total}")

    def _select_all(self):
        for var in self.check_vars.values():
            var.set(True)
        self._update_count_label()

    def _clear_all(self):
        for var in self.check_vars.values():
            var.set(False)
        self._update_count_label()

    def _confirm(self):
        """확인 — visible 상태를 반영한 보트 리스트를 콜백으로 전달"""
        updated_boats = []

        for name in self.all_names:
            is_visible = self.check_vars[name].get()

            if name in self.config_map:
                # 기존 보트: visible 필드 업데이트 + 숨김 시 비활성화
                boat = dict(self.config_map[name])
                boat['visible'] = is_visible
                if not is_visible:
                    boat['enabled'] = False
                    boat['mode'] = 'off'
            else:
                # 신규 보트: 최소 dict 생성
                boat = {'name': name, 'enabled': False, 'visible': is_visible}
                # 더피싱은 base_url, pa_n_uid 필요하지만 아직 모르므로 빈값
                if self.platform == 'thefishing':
                    boat['base_url'] = ''
                    boat['pa_n_uid'] = ''
                else:
                    boat['base_url'] = ''

            updated_boats.append(boat)

        if self.callback:
            self.callback(updated_boats)
        self.popup.destroy()

    def _cancel(self):
        self.popup.destroy()


# ============================================
# 📡 텔레그램 알림
# ============================================
class TelegramNotifier:
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{token}"
    
    def send_message(self, message: str, parse_mode: str = "HTML"):
        if not self.token or not self.chat_id:
            return False
        
        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": parse_mode,
                "disable_web_page_preview": False
            }
            response = requests.post(url, data=data, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"텔레그램 전송 실패: {e}")
            return False
    
    def send_cancellation_alert(self, boat_name: str, date: str, url: str, status: str = ""):
        timestamp = datetime.now().strftime("%H:%M:%S")
        status_line = f"\n🪑 <b>상태:</b> {status}" if status else ""
        
        message = f"""
🎣 <b>취소석 발생!</b>

📍 <b>선박:</b> {boat_name}
📅 <b>날짜:</b> {date}{status_line}
🕐 <b>감지시간:</b> {timestamp}

🔗 <a href="{url}">예약 페이지 바로가기</a>

⚡ 빠르게 예약하세요!
"""
        return self.send_message(message)


# ============================================
# 🤖 통합 모니터링 봇
# ============================================
class FishingBoatMonitor:
    def __init__(self, log_callback, config):
        self.log = log_callback
        self.config = config
        self.session = None
        self.is_running = False
        self.notifier = TelegramNotifier(
            config.get('telegram_token', ''),
            config.get('telegram_chat_id', '')
        )
        self.alerted_dates = set()  # 이미 알림 보낸 (배이름-날짜) 조합
        self.reserved_dates = set()  # 이미 예약 시도한 (배이름-날짜) 조합
        
        # 종합 알람 타이밍 (처음 1회, 이후 4시간마다)
        self.first_summary_sent = False
        self.last_summary_time = None

        # 야간 브레이크 상태
        self._night_break_started = False
        self._break_start_minute = random.randint(*NIGHT_BREAK_START_RANGE)
        self._break_end_minute = random.randint(*NIGHT_BREAK_END_RANGE)
    
    @staticmethod
    def is_critical_error(error):
        """치명적인 HTTP 오류인지 확인"""
        err_str = str(error).lower()
        return any(k in err_str for k in CRITICAL_KEYWORDS)

    def _handle_available(self, boat: dict, year: str, month: str, day: str,
                          date_str: str, status: str, reserve_url: str, platform: str):
        """취소석 감지 시 알림 전송 + 자동예약 실행 (공통 로직)"""
        boat_name = boat['name']
        alert_key = f"{boat_name}-{date_str}"

        if alert_key not in self.alerted_dates:
            if self.notifier.send_cancellation_alert(
                boat_name=boat_name,
                date=f"{year}년 {month}월 {day}일",
                url=reserve_url,
                status=status
            ):
                self.log(f"  📱 텔레그램 알림 전송!")
                self.alerted_dates.add(alert_key)

            if boat.get('mode') == 'reserve':
                self.run_auto_reserve(boat, date_str, platform)

    def run_auto_reserve(self, boat: dict, date_str: str, platform: str):
        """자동예약 실행 (별도 스레드에서 봇 실행)"""
        boat_name = boat['name']
        reserve_key = f"{boat_name}-{date_str}"
        
        if reserve_key in self.reserved_dates:
            self.log(f"⚠️ [{boat_name}] 이미 예약 시도함")
            return
        
        self.reserved_dates.add(reserve_key)
        
        # 예약 config 생성
        reserve_config = {
            'target_date': date_str,
            'target_time': '00:00:00',  # 즉시 실행
            'test_mode': True,
            'simulation_mode': self.config.get('test_mode', True),  # Test모드면 팝업에서 멈춤
            'user_name': self.config.get('reserve_name', ''),
            'user_depositor': self.config.get('reserve_name', ''),
            'user_phone': self.config.get('reserve_phone', ''),
            'person_count': self.config.get('reserve_count', 1)
        }
        
        # 봇 파일 경로 결정
        bot_dir = os.path.join(os.path.dirname(__file__), 'bots', PLATFORM_NAMES.get(platform, platform))
        bot_file = os.path.join(bot_dir, f"{boat_name}_Bot.py")
        
        if not os.path.exists(bot_file):
            self.log(f"❌ [{boat_name}] 봇 파일 없음: {bot_file}")
            return
        
        self.log(f"🚀 [{boat_name}] 자동예약 시작! 날짜: {date_str}")
        
        # 텔레그램 알림
        self.notifier.send_message(f"🚀 <b>자동예약 시작!</b>\n\n📍 선박: {boat_name}\n📅 날짜: {date_str}")
        
        # config 임시 파일 저장
        config_file = os.path.join(tempfile.gettempdir(), f"reserve_config_{boat_name}.json")
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(reserve_config, f, ensure_ascii=False)
        
        # 봇 실행 (별도 프로세스)
        try:
            subprocess.Popen(
                ['python', bot_file, '--config', config_file],
                cwd=bot_dir,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
            self.log(f"✅ [{boat_name}] 봇 프로세스 시작됨!")
        except Exception as e:
            self.log(f"❌ [{boat_name}] 봇 실행 실패: {e}")
    
    def build_session(self):
        """HTTP 세션 생성 (Selenium 드라이버 대체)"""
        self.log("🌐 HTTP 세션 설정 중...")

        s = requests.Session()
        s.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Connection": "keep-alive",
        })

        retry = Retry(total=2, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        s.mount("http://", adapter)
        s.mount("https://", adapter)

        self.session = s
        self.log("✅ HTTP 세션 준비 완료 (경량 모드)")

    def _fetch_page(self, url: str) -> str:
        """URL에서 HTML 페이지를 가져와 텍스트로 반환"""
        response = self.session.get(url, timeout=HTTP_TIMEOUT)
        return response.text

    def _record_result(self, result_list: list, month: str, day, status: str,
                       is_available: bool, suppress_keyword: str = ""):
        """결과 기록 + 로그 출력 (공통 패턴)"""
        result_list.append((f"{month}/{day}", status, is_available))
        if is_available:
            self.log(f"  🎉 {month}/{day}: ✅ {status}")
        elif suppress_keyword and suppress_keyword in status:
            pass  # 예약완료/예약마감 등 빈번한 상태는 로그 생략
        else:
            self.log(f"  📅 {month}/{day}: ❌ {status}")

    @staticmethod
    def _make_date_str(year: str, month: str, day) -> str:
        """YYYYMMDD 형식 날짜 문자열 생성"""
        return f"{year}{month}{str(day).zfill(2)}"

    @staticmethod
    def _get_domain(url: str) -> str:
        """URL에서 스킴+호스트 도메인 추출 (예: 'https://example.com')"""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"

    @staticmethod
    def build_calendar_url(base_url: str, pa_n_uid: str, year: str, month: str):
        """더피싱 달력 페이지 URL 생성"""
        return f"{base_url}?mid=bk&year={year}&month={month}&day=01&mode=cal&PA_N_UID={pa_n_uid}#list"

    @staticmethod
    def build_schedule_url(base_url: str, year: str, month: str):
        """선상24 스케줄 페이지 URL 생성"""
        return f"{base_url}/ship/schedule_fleet/{year}{month}"
    
    def check_date_availability(self, page_source: str, date_str: str, pa_n_uid: str):
        """
        특정 날짜의 예약 가능 여부 확인 (HTML 문자열 기반)
        page_source: 이미 가져온 HTML 텍스트
        date_str: YYYYMMDD 형식
        """
        try:
            # 해당 날짜가 페이지에 있는지 확인
            date_pattern = f"date={date_str}"
            if date_pattern not in page_source:
                return False, "정보없음"

            # r_cal_box 단위로 해당 날짜 블록 찾기 (기존 regex 로직 유지)
            cal_box_pattern = rf'<div class="r_cal_box">(.*?)</div>\s*</div>\s*</div>'
            cal_boxes = re.findall(cal_box_pattern, page_source, re.DOTALL)

            for box_content in cal_boxes:
                if date_pattern in box_content:
                    if '예약완료' in box_content:
                        return False, "예약완료"

                    if '>예약하기<' in box_content or '>예약하기 <' in box_content:
                        remain_match = re.search(r'남은인원.*?(\d+)명', box_content, re.DOTALL)
                        if remain_match:
                            return True, f"남은인원: {remain_match.group(1)}명"
                        return True, "예약가능"

                    if '>대기하기<' in box_content:
                        return False, "예약마감(대기가능)"

                    return False, "정보없음"

            # 폴백: BeautifulSoup으로 해당 날짜의 예약하기/대기하기 링크 검색
            try:
                soup = BeautifulSoup(page_source, 'html.parser')

                # 예약하기 링크 찾기
                for a_tag in soup.find_all('a', onclick=True):
                    if f'date={date_str}' in a_tag.get('onclick', '') and '예약하기' in a_tag.get_text():
                        parent_box = a_tag.find_parent('div', class_='r_cal_box')
                        if parent_box:
                            box_html = str(parent_box)
                            if '예약완료' in box_html:
                                return False, "예약완료"
                            remain_match = re.search(r'남은인원.*?(\d+)명', box_html, re.DOTALL)
                            if remain_match:
                                return True, f"남은인원: {remain_match.group(1)}명"
                        return True, "예약가능"

                # 대기하기 링크 찾기
                for a_tag in soup.find_all('a', onclick=True):
                    if f'date={date_str}' in a_tag.get('onclick', '') and '대기하기' in a_tag.get_text():
                        return False, "예약마감(대기가능)"
            except Exception:
                pass

            return False, "정보없음"

        except Exception as e:
            return False, f"오류: {e}"
    
    def check_boat(self, boat: dict, year: str, month_days: dict):
        """한 배의 여러 월/날짜를 체크 - 모든 날짜의 상태 반환"""
        boat_name = boat['name']
        base_url = boat['base_url']
        pa_n_uid = boat['pa_n_uid']
        
        # 나폴리호는 예약 페이지에서 직접 체크 (캘린더 없음)
        if '나폴리' in boat_name:
            return self.check_napoli_boat(boat, year, month_days)
        
        # 모든 날짜의 상태를 수집: [(date_str, status, is_available), ...]
        result_list = []
        
        for month, days in month_days.items():
            if not days:  # 해당 월에 선택된 날짜 없으면 스킵
                continue
            
            url = self.build_calendar_url(base_url, pa_n_uid, year, month)
            self.log(f"🚢 [{boat_name}] {month}월 체크 ({len(days)}일)...")
            
            try:
                page_source = self._fetch_page(url)

                for day in days:
                    date_str = self._make_date_str(year, month, day)

                    is_available, status = self.check_date_availability(page_source, date_str, pa_n_uid)
                    self._record_result(result_list, month, day, status, is_available, "예약완료")

                    if is_available:
                        domain = self._get_domain(base_url)
                        reserve_url = f"{domain}/m/_core/module/reservation_boat_v5.2_seat1/m/popu2.step1.php?date={date_str}&PA_N_UID={pa_n_uid}"
                        self._handle_available(boat, year, month, day, date_str, status, reserve_url, 'thefishing')
                            
            except Exception as e:
                self._handle_check_error(e, f"[{boat_name}]")

        return result_list

    def check_napoli_boat(self, boat: dict, year: str, month_days: dict):
        """나폴리호 전용 체크 (예약 페이지에서 직접 남은자리 확인) - 모든 날짜의 상태 반환"""
        boat_name = boat['name']
        base_url = boat['base_url']
        pa_n_uid = boat['pa_n_uid']
        domain = self._get_domain(base_url)
        
        # 모든 날짜의 상태를 수집: [(date_str, status, is_available), ...]
        result_list = []
        
        for month, days in month_days.items():
            if not days:
                continue
            
            self.log(f"🚢 [{boat_name}] {month}월 체크 ({len(days)}일)...")
            
            for day in days:
                date_str = self._make_date_str(year, month, day)

                # 예약 페이지 직접 접근
                reserve_url = f"{domain}/_core/module/reservation_boat_v3/popup.step1.php?date={date_str}&PA_N_UID={pa_n_uid}"
                
                try:
                    page_source = self._fetch_page(reserve_url)

                    # PA_N_UID1484 행 전체를 찾아서 남은자리(4번째 td) 추출
                    # 구조: <tr>...<input id="PA_N_UID1484">...<td>배명</td><td>총인원</td><td>남은자리</td></tr>
                    row_pattern = rf'<tr[^>]*>.*?id="PA_N_UID{pa_n_uid}".*?</tr>'
                    row_match = re.search(row_pattern, page_source, re.DOTALL)
                    
                    # HTML에서 남은자리 파싱
                    is_available, status = False, "정보없음"
                    if row_match:
                        row_html = row_match.group(0)
                        numbers = re.findall(r'>(\d+)명<', row_html)
                        if len(numbers) >= 2:
                            remaining = int(numbers[-1])
                            if remaining >= 1:
                                is_available, status = True, f"남은자리: {remaining}명"
                            else:
                                status = "예약완료"

                    self._record_result(result_list, month, day, status, is_available, "예약완료")

                    if is_available:
                        mobile_url = f"{domain}/m/_core/module/reservation_boat_v3/m/popup.step1.php?date={date_str}&PA_N_UID={pa_n_uid}"
                        self._handle_available(boat, year, month, day, date_str, status, mobile_url, 'thefishing')
                        
                except Exception as e:
                    self._handle_check_error(e, f"{month}/{day}")
                    result_list.append((f"{month}/{day}", "오류", False))
        
        return result_list
    
    def run_single_check(self):
        """모든 활성화된 배들을 한 번 체크 (더피싱 + 선상24)"""
        year = self.config['target_year']
        month_days = self.config.get('target_days', dict(EMPTY_MONTH_DAYS))
        
        # 이전 버전 호환 (list -> dict)
        if isinstance(month_days, list):
            month_days = {"09": month_days, "10": [], "11": []}
        
        all_available = []
        summary_data = {}  # {날짜: [(선사, 상태, 예약가능여부), ...]}

        # 플랫폼별 체크 설정: (config_key, check_func)
        platform_checks = [
            ('thefishing_boats', self.check_boat),
            ('sunsang24_boats', self.check_sunsang24_boat),
        ]

        any_enabled = False
        for config_key, check_func in platform_checks:
            boats = self.config.get(config_key, [])
            enabled = [b for b in boats if b.get('enabled', False) and b.get('visible', True)]
            if not enabled:
                continue
            any_enabled = True
            icon = PLATFORM_KEY_ICONS.get(config_key, '🚢')
            self.log(f"{icon} [{PLATFORM_KEY_NAMES[config_key]}] {len(enabled)}개 선박 체크...")

            for boat in enabled:
                if not self.is_running:
                    return all_available
                result = check_func(boat, year, month_days)
                for date_str, status, is_available in result:
                    if is_available:
                        all_available.append((boat['name'], date_str))
                    summary_data.setdefault(date_str, []).append(
                        (boat['name'], status, is_available)
                    )

        if not any_enabled:
            self.log("⚠️ 활성화된 선박이 없습니다!")
        
        # 종합 알람 전송 (처음 1회 무조건 + 이후는 예약 가능 자리가 있을 때만)
        if summary_data and self.config.get('summary_alert', True):
            should_send = False

            if not self.first_summary_sent:
                should_send = True
                self.first_summary_sent = True
            elif all_available:
                should_send = True

            if should_send:
                self.send_summary_alert(summary_data, year)
        
        return all_available
    
    def send_summary_alert(self, summary_data: dict, year: str):
        """종합 알람 전송 - 날짜별 예약 현황 (가능+불가)"""
        if not summary_data:
            return
        
        lines = ["📊 <b>종합 예약 현황</b>\n"]
        
        # 날짜 정렬 (M/D 형식)
        sorted_dates = sorted(summary_data.keys(), key=lambda x: (int(x.split('/')[0]), int(x.split('/')[1])))
        
        for date_str in sorted_dates:
            boats = summary_data[date_str]
            month, day = date_str.split('/')
            lines.append(f"\n🗓️ <b>{month}월 {day}일</b>")
            for boat_name, status, is_available in boats:
                # 상태에서 남은인원/남은자리 숫자 추출
                if is_available and ("남은인원" in status or "남은자리" in status):
                    match = re.search(r'(\d+)', status)
                    seats = match.group(1) + "자리" if match else "예약가능"
                elif not is_available:
                    seats = "예약마감"
                else:
                    seats = status

                icon = "✅" if is_available else "❌"
                lines.append(f"  └ {icon} {boat_name}: {seats}")
        
        message = '\n'.join(lines)
        self.notifier.send_message(message)
        self.log("📊 종합 알람 전송 완료")
    
    def check_sunsang24_boat(self, boat: dict, year: str, month_days: dict):
        """선상24 선박 체크 - 모든 날짜의 상태 반환"""
        boat_name = boat['name']
        base_url = boat['base_url']  # 예: https://rkclgh.sunsang24.com
        
        # 모든 날짜의 상태를 수집: [(date_str, status, is_available), ...]
        result_list = []
        
        for month, days in month_days.items():
            if not days:
                continue
            
            schedule_url = self.build_schedule_url(base_url, year, month)
            self.log(f"⛵ [{boat_name}] {month}월 체크 ({len(days)}일)...")
            
            try:
                page_source = self._fetch_page(schedule_url)

                for day in days:
                    date_str = self._make_date_str(year, month, day)
                    date_id = f"d{year}-{month}-{str(day).zfill(2)}"  # 예: d2026-09-01

                    is_available, status = self.check_sunsang24_availability(page_source, date_id)
                    self._record_result(result_list, month, day, status, is_available, "예약마감")

                    if is_available:
                        self._handle_available(boat, year, month, day, date_str, status, schedule_url, 'sunsang24')
                            
            except Exception as e:
                self._handle_check_error(e, f"[{boat_name}]")

        return result_list

    def check_sunsang24_availability(self, page_source: str, date_id: str):
        """선상24 날짜별 예약 가능 여부 체크 (HTML 문자열 기반)"""
        try:
            soup = BeautifulSoup(page_source, 'html.parser')
            date_element = soup.find(id=date_id)

            if not date_element:
                return False, "날짜없음"

            table_html = str(date_element)

            # "바로예약" 버튼이 있으면 예약 가능
            if 'btn_ship_reservation' in table_html and '바로예약' in table_html:
                remain_match = re.search(r'남은자리.*?(\d+)명', table_html, re.DOTALL)
                if remain_match:
                    return True, f"남은자리 {remain_match.group(1)}명"
                return True, "예약가능"

            # "대기하기" 버튼 또는 "예약마감"이 있으면 예약 불가
            if 'btn_ship_reservation_awaiter' in table_html or '예약마감' in table_html:
                return False, "예약마감"

            return False, "정보없음"

        except Exception as e:
            return False, f"오류: {e}"
    
    def get_random_interval(self):
        min_sec = self.config.get('check_interval_min', 8) * 60
        max_sec = self.config.get('check_interval_max', 10) * 60
        return random.randint(min_sec, max_sec)
    
    def _handle_check_error(self, error: Exception, context: str):
        """체크 중 발생한 예외 처리: 치명적이면 재raise, 아니면 로그"""
        if self.is_critical_error(error):
            raise error
        self.log(f"  ⚠️ {context}: {error}")

    def _close_session(self):
        """현재 HTTP 세션 안전하게 닫기"""
        try:
            if self.session:
                self.session.close()
        except Exception:
            pass

    def _wait_interruptible(self, seconds: int, step: int = 1):
        """is_running이 False가 되면 즉시 중단하는 대기"""
        for _ in range(0, seconds, step):
            if not self.is_running:
                break
            time.sleep(step)

    def _handle_night_break(self):
        """야간 브레이크 진입 여부 확인 및 대기 처리. 브레이크 대기했으면 True 반환."""
        now = datetime.now()
        hour, minute = now.hour, now.minute

        # 브레이크 시작 조건: 23:50~23:59 또는 00:00~00:05
        in_break_start = (hour == 23 and minute >= (50 + max(0, self._break_start_minute))) or \
                         (hour == 0 and minute <= max(0, self._break_start_minute))
        in_break_zone = (0 <= hour < 7) or in_break_start

        if in_break_zone and not self._night_break_started:
            self._night_break_started = True
            wake_hour, wake_min = divmod(6 * 60 + self._break_end_minute, 60)
            self.log(f"🌙 야간 브레이크 시작! {wake_hour:02d}:{wake_min:02d}까지 대기...")

        if not self._night_break_started:
            return False

        # 기상 시간까지 1분 간격으로 대기
        wake_total = 6 * 60 + self._break_end_minute  # 06:50~07:05
        while self.is_running:
            total_minutes = datetime.now().hour * 60 + datetime.now().minute
            if total_minutes >= wake_total:
                break
            time.sleep(60)

        self._night_break_started = False
        self._break_start_minute = random.randint(*NIGHT_BREAK_START_RANGE)
        self._break_end_minute = random.randint(*NIGHT_BREAK_END_RANGE)
        self.log(f"☀️ 모닝 브레이크 종료! 모니터링 재개")
        return True

    def run(self):
        self.is_running = True

        try:
            self.build_session()

            check_count = 0

            while self.is_running:
                # 야간 브레이크 체크
                self._handle_night_break()
                if not self.is_running:
                    break

                check_count += 1
                self.log(f"\n{'='*50}")
                self.log(f"🔍 [{check_count}번째 체크] {datetime.now().strftime('%H:%M:%S')}")
                
                try:
                    available = self.run_single_check()
                    
                    if available:
                        self.log(f"🎣 예약 가능: {available}")
                    else:
                        self.log("😢 현재 예약 가능한 자리 없음")
                    
                except Exception as e:
                    self.log(f"⚠️ 체크 중 오류: {e}")
                    if self.is_critical_error(e):
                        self.log("🔄 HTTP 연결 오류 감지! 세션을 재생성합니다...")
                        self._close_session()
                        time.sleep(3)
                        self.build_session()
                
                if not self.is_running:
                    break
                
                interval = self.get_random_interval()
                next_time = datetime.now() + timedelta(seconds=interval)
                self.log(f"⏰ 다음 체크: {next_time.strftime('%H:%M:%S')} ({interval//60}분 {interval%60}초 후)")
                
                self._wait_interruptible(interval)
        
        except Exception as e:
            self.log(f"🚨 오류 발생: {e}")
        
        finally:
            self._close_session()
            self.log("🛑 모니터링 종료")
    
    def stop(self):
        self.is_running = False


# ============================================
# 🖥️ GUI
# ============================================
class FishingBoatMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🎣 낚시배 취소석 모니터 v2.0")
        
        w, h = 1080, 950
        ws = root.winfo_screenwidth()
        hs = root.winfo_screenheight()
        x = (ws / 2) - (w / 2)
        y = max(0, (hs / 2) - (h / 2))
        root.geometry('%dx%d+%d+%d' % (w, h, x, y))
        root.minsize(980, 780)

        # 콘솔 핸들 저장 (시작 시 한 번만)
        self._console_hwnd = ctypes.windll.kernel32.GetConsoleWindow() or 0

        # 최소화 시 트레이로 숨기기
        if TRAY_AVAILABLE:
            root.bind('<Unmap>', self._on_minimize)

        self.config = self.load_config()
        self.monitor = None
        self.monitor_thread = None

        # 위젯 초기화 전 None 세팅 (create_widgets 내부 호출 순서 의존 방지)
        self.btn_select_all = None
        self.lbl_boat_status = None
        self.preset_combo = None
        self.tray_icon = None

        self.create_widgets()
    
    def load_config(self):
        # Start with default config (deep copy to avoid reference issues)
        config = json.loads(json.dumps(DEFAULT_CONFIG))
        
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    file_data = json.load(f)
                    
                    # Update scalar values and settings
                    for k, v in file_data.items():
                        if k not in PLATFORM_KEYS:
                            config[k] = v

                    # Merge Boat Lists (Preserve user settings, add new code-defined boats)
                    for platform in PLATFORM_KEYS:
                        file_boats = file_data.get(platform, [])
                        default_boats = config.get(platform, []) # These are from DEFAULT_CONFIG via deepcopy
                        
                        # Create map of existing file boats
                        file_boat_map = {b['name']: b for b in file_boats}
                        
                        merged_list = []
                        # 1. Keep all file boats (user settings)
                        merged_list.extend(file_boats)
                        
                        # 2. Add any default boats that are NOT in file
                        for def_boat in default_boats:
                            if def_boat['name'] not in file_boat_map:
                                merged_list.append(def_boat)
                        
                        config[platform] = merged_list
            except Exception as e:
                print(f"Config load error: {e}")
        
        return config
    
    def save_config(self):
        self.config['target_year'] = self.entry_year.get()
        
        # 선택된 월들 (날짜가 있는 월만)
        selected_months = [m for m, days in self.month_days.items() if days]
        self.config['target_months'] = selected_months if selected_months else ['09']
        
        # 월별 날짜 저장
        self.config['target_days'] = self.month_days
        
        self.config['check_interval_min'] = int(self.entry_min_interval.get())
        self.config['check_interval_max'] = int(self.entry_max_interval.get())
        # 자동예약 정보 저장
        self.config['reserve_name'] = self.entry_reserve_name.get()
        self.config['reserve_phone'] = self.entry_reserve_phone.get()
        self.config['reserve_count'] = int(self.entry_reserve_count.get() or 1)
        self.config['test_mode'] = self.var_test_mode.get()
        self.config['summary_alert'] = self.var_summary_alert.get()
        
        # 선박 목록은 이미 config에 직접 업데이트 됨
        # (버튼 클릭 시 boats[idx]['enabled'] 변경)
        
        self.save_config_quietly()

        total_days = sum(len(days) for days in self.month_days.values())
        total_boats = sum(len(self.config.get(pk, [])) for pk in PLATFORM_KEYS)
        self.log_msg(f"💾 설정 저장 완료 (총 {total_days}개 날짜, 선박: {total_boats}개)")
        return self.config
    
    def save_config_quietly(self):
        """설정을 조용히 저장 (로그 없이)"""
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception:
            pass
    
    # ========== 프리셋 관련 함수 ==========
    def load_presets(self):
        """저장된 프리셋 목록 불러오기"""
        if os.path.exists(PRESETS_FILE):
            try:
                with open(PRESETS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_presets(self, presets):
        """프리셋 목록 저장"""
        with open(PRESETS_FILE, 'w', encoding='utf-8') as f:
            json.dump(presets, f, indent=2, ensure_ascii=False)
    
    def refresh_preset_list(self):
        """프리셋 드롭다운 목록 새로고침"""
        presets = self.load_presets()
        preset_names = list(presets.keys())
        if self.preset_combo:
            self.preset_combo['values'] = preset_names
    
    def save_preset(self):
        """현재 선택된 선박들을 프리셋으로 저장 (두 플랫폼 + 날짜)"""
        preset_name = self.entry_preset_name.get().strip()
        if not preset_name or preset_name == "프리셋 이름":
            messagebox.showwarning("경고", "프리셋 이름을 입력하세요!")
            return
        
        # 두 플랫폼의 활성화된 선박들 수집
        enabled_by_platform = {}
        for platform_key in PLATFORM_KEYS:
            boats = self.config.get(platform_key, [])
            enabled_by_platform[platform_key] = [
                {'name': b['name'], 'mode': b.get('mode', 'monitor')}
                for b in boats if b.get('enabled', False)
            ]

        total_enabled = sum(len(v) for v in enabled_by_platform.values())

        if total_enabled == 0:
            messagebox.showwarning("경고", "선택된 선박이 없습니다!")
            return

        # 프리셋 저장 (두 플랫폼 + 날짜 + mode)
        presets = self.load_presets()
        preset_data = {
            'target_year': self.entry_year.get(),
            'target_days': dict(self.month_days),
        }
        preset_data.update(enabled_by_platform)
        presets[preset_name] = preset_data
        self.save_presets(presets)

        # 드롭다운 업데이트
        self.refresh_preset_list()
        self.preset_var.set(preset_name)

        stats = self._preset_stats()
        self.log_msg(f"💾 프리셋 저장: '{preset_name}' ({stats})")
        messagebox.showinfo("저장 완료", f"프리셋 '{preset_name}'이(가) 저장되었습니다.\n({stats})")
    
    def load_preset(self, event=None):
        """선택된 프리셋 불러오기 (두 플랫폼 + 날짜)"""
        preset_name = self.preset_var.get()
        if not preset_name:
            return
        
        presets = self.load_presets()
        if preset_name not in presets:
            return
        
        preset = presets[preset_name]
        
        # 이전 버전 호환 (단일 플랫폼 형식)
        if 'platform' in preset:
            old_platform = preset.get('platform', 'thefishing')
            enabled_boats = preset.get('boats', [])
            preset = {pk: enabled_boats if pk == f'{old_platform}_boats' else [] for pk in PLATFORM_KEYS}

        # 프리셋 데이터에서 이름→mode 매핑 생성 (새 형식/이전 형식 호환)
        def get_mode_map(preset_data):
            mode_map = {}
            for item in preset_data:
                if isinstance(item, dict):
                    mode_map[item['name']] = item.get('mode', 'monitor')
                else:
                    mode_map[item] = 'monitor'  # 이전 형식 (이름만)
            return mode_map

        # 플랫폼별 모드 매핑 적용
        mode_maps = {pk: get_mode_map(preset.get(pk, [])) for pk in PLATFORM_KEYS}
        for platform_key, mode_map in mode_maps.items():
            for boat in self.config.get(platform_key, []):
                if boat['name'] in mode_map:
                    boat['enabled'] = True
                    boat['mode'] = mode_map[boat['name']]
                else:
                    boat['enabled'] = False
                    boat['mode'] = 'off'
        
        # 날짜 정보 불러오기
        if 'target_year' in preset:
            self.entry_year.delete(0, tk.END)
            self.entry_year.insert(0, preset['target_year'])
        
        if 'target_days' in preset:
            self.month_days = preset['target_days']
            # 월별 날짜 라벨 업데이트
            for month_str, lbl in self.month_labels.items():
                days_count = len(self.month_days.get(month_str, []))
                lbl.config(text=f"{days_count}개")
            # 요약 업데이트
            self.lbl_days_summary.config(text=self.get_days_summary())
        
        # UI 업데이트
        self.refresh_boat_grid()
        
        self.log_msg(f"📂 프리셋 로드: '{preset_name}' ({self._preset_stats()})")
    
    def _preset_stats(self) -> str:
        """현재 프리셋 통계 문자열 (예: '더피싱:3개, 선상24:1개, 날짜:12개')"""
        parts = [
            f"{PLATFORM_KEY_NAMES[pk]}:{sum(1 for b in self.config.get(pk, []) if b.get('enabled'))}개"
            for pk in PLATFORM_KEYS
        ]
        total_days = sum(len(days) for days in self.month_days.values())
        parts.append(f"날짜:{total_days}개")
        return ', '.join(parts)

    def delete_preset(self):
        """선택된 프리셋 삭제"""
        preset_name = self.preset_var.get()
        if not preset_name:
            messagebox.showwarning("경고", "삭제할 프리셋을 선택하세요!")
            return
        
        if not messagebox.askyesno("확인", f"프리셋 '{preset_name}'을(를) 삭제하시겠습니까?"):
            return
        
        presets = self.load_presets()
        if preset_name in presets:
            del presets[preset_name]
            self.save_presets(presets)
        
        self.refresh_preset_list()
        self.preset_var.set('')
        self.log_msg(f"🗑 프리셋 삭제: '{preset_name}'")
    
    def create_widgets(self):
        style = ttk.Style()
        style.configure('TLabel', font=(FONT_FAMILY, FONT_SIZE_MD))
        style.configure('TButton', font=(FONT_FAMILY, FONT_SIZE_MD))
        style.configure('TLabelframe.Label', font=(FONT_FAMILY, FONT_SIZE_MD, 'bold'))

        # -- 보트 그리드 버튼 3상태 스타일 --
        for sname, bg, fg, hover in [
            ('Monitor.TButton', CLR_SUCCESS,   CLR_FG,      '#00a87d'),
            ('Reserve.TButton', CLR_DANGER,    CLR_FG,      '#c0392b'),
            ('Off.TButton',     CLR_SECONDARY, CLR_FG_MUTED, '#555555'),
        ]:
            style.configure(sname, background=bg, foreground=fg,
                            font=(FONT_FAMILY, FONT_SIZE_SM), padding=(2, 1))
            style.map(sname, background=[('active', hover)])

        # -- 플랫폼 토글 버튼 스타일 --
        for sname, bg, fg in [
            ('PlatformActive.TButton',   CLR_SUCCESS,   CLR_FG),
            ('PlatformInactive.TButton', CLR_SECONDARY, CLR_FG_MUTED),
        ]:
            style.configure(sname, background=bg, foreground=fg,
                            font=(FONT_FAMILY, FONT_SIZE_MD, 'bold'), padding=(8, 3))
            style.map(sname, background=[('active', bg)])

        # -- 월 토글 버튼 스타일 --
        for sname, bg, fg in [
            ('MonthActive.TButton',   CLR_SUCCESS,   CLR_FG),
            ('MonthInactive.TButton', CLR_SECONDARY, CLR_FG_MUTED),
        ]:
            style.configure(sname, background=bg, foreground=fg,
                            font=(FONT_FAMILY, FONT_SIZE_SM), padding=(4, 1))
            style.map(sname, background=[('active', bg)])

        main_frame = ttk.Frame(self.root, padding="8")
        main_frame.pack(fill=tk.BOTH, expand=True)

        self._create_boat_section(main_frame)
        self._create_settings_section(main_frame)
        self._create_action_buttons(main_frame)
        self._create_log_section(main_frame)

    # ---------- GUI 섹션별 빌더 ----------

    def _create_boat_section(self, parent):
        """🚢 선박 관리 섹션"""
        boat_frame = ttk.Labelframe(parent, text="  선박 관리", padding=SP_MD, bootstyle="info")
        boat_frame.pack(fill=tk.X, pady=(SP_SM, SP_SM))

        # ── 플랫폼 선택 행 ──
        platform_row = ttk.Frame(boat_frame)
        platform_row.pack(fill=tk.X, pady=(0, SP_SM))
        ttk.Label(platform_row, text="플랫폼:", font=(FONT_FAMILY, FONT_SIZE_MD, 'bold')).pack(side=tk.LEFT, padx=(0, SP_SM))

        for key, name in PLATFORM_NAMES.items():
            btn = ttk.Button(
                platform_row, text=name, width=8,
                style=_toggle_style(self.current_platform == key),
                cursor='hand2',
                command=lambda k=key: self.switch_platform(k)
            )
            btn.pack(side=tk.LEFT, padx=SP_XS)
            setattr(self, f'btn_{key}', btn)

        # 선사 편집 버튼
        ttk.Button(
            platform_row, text="편집", width=8,
            style='PlatformInactive.TButton', cursor='hand2',
            command=self.open_boat_editor
        ).pack(side=tk.LEFT, padx=(SP_MD, SP_XS))

        # ── 선박 버튼 그리드 ──
        grid_frame = ttk.Frame(boat_frame)
        grid_frame.pack(fill=tk.X, pady=SP_SM)
        for c in range(10):
            grid_frame.columnconfigure(c, weight=1, uniform='boat_col')
        self.boat_buttons = {}
        self.selected_boat = None

        # ── 선박 컨트롤 행 1: 전체선택 + 사이트가기 + 월 ──
        ctrl_row1 = ttk.Frame(boat_frame)
        ctrl_row1.pack(fill=tk.X, pady=(SP_XS, 0))

        self.btn_select_all = ttk.Button(
            ctrl_row1, text="전체선택", command=self.toggle_all_boats,
            width=10, style='Off.TButton', cursor='hand2'
        )
        self.btn_select_all.pack(side=tk.LEFT, padx=SP_XS)
        ttk.Button(ctrl_row1, text="사이트가기", command=self.open_boat_site, width=12).pack(side=tk.LEFT, padx=SP_XS)

        # 월 선택 버튼 (사이트가기용)
        ttk.Label(ctrl_row1, text=" ").pack(side=tk.LEFT, padx=SP_XS)
        self.selected_site_month = tk.StringVar(value="09")
        self.month_buttons = {}
        for m in MONITOR_MONTHS:
            month_str = f"{m:02d}"
            btn = ttk.Button(
                ctrl_row1, text=f"{m}월", width=4,
                style=_toggle_style(m == 9, 'Month'),
                cursor='hand2',
                command=lambda ms=month_str: self.select_site_month(ms)
            )
            btn.pack(side=tk.LEFT, padx=SP_XS)
            self.month_buttons[month_str] = btn

        # ── 선박 컨트롤 행 2: 프리셋 ──
        ctrl_row2 = ttk.Frame(boat_frame)
        ctrl_row2.pack(fill=tk.X, pady=(SP_SM, 0))

        ttk.Label(ctrl_row2, text="프리셋:", font=(FONT_FAMILY, FONT_SIZE_SM)).pack(side=tk.LEFT, padx=(SP_XS, SP_SM))
        self.preset_var = tk.StringVar()
        self.preset_combo = ttk.Combobox(ctrl_row2, textvariable=self.preset_var, width=18, state='readonly')
        self.preset_combo.pack(side=tk.LEFT, padx=(0, SP_SM))
        self.preset_combo.bind('<<ComboboxSelected>>', self.load_preset)
        self.refresh_preset_list()

        self.entry_preset_name = ttk.Entry(ctrl_row2, width=16)
        self.entry_preset_name.pack(side=tk.LEFT, padx=SP_XS)
        self.entry_preset_name.insert(0, "프리셋 이름")
        self.entry_preset_name.bind('<FocusIn>', lambda e: self.entry_preset_name.delete(0, tk.END) if self.entry_preset_name.get() == "프리셋 이름" else None)
        ttk.Button(ctrl_row2, text="저장", command=self.save_preset, width=7).pack(side=tk.LEFT, padx=SP_XS)
        ttk.Button(ctrl_row2, text="삭제", command=self.delete_preset, width=7).pack(side=tk.LEFT, padx=SP_XS)

        self.grid_frame = grid_frame
        self.refresh_boat_grid()

    def _create_settings_section(self, parent):
        """Settings: 모니터링 대상 + 예약정보 + 간격 (통합 섹션)"""
        settings_frame = ttk.Labelframe(parent, text="  Settings", padding=(SP_MD, SP_SM, SP_MD, SP_MD), bootstyle="info")
        settings_frame.pack(fill=tk.X, pady=(SP_SM, SP_SM))

        # ── Row 1: 년도 + 월별 캘린더 + 선사 수 ──
        date_row = ttk.Frame(settings_frame)
        date_row.pack(fill=tk.X, pady=(0, SP_SM))

        ttk.Label(date_row, text="년도", font=(FONT_FAMILY, FONT_SIZE_MD, 'bold')).pack(side=tk.LEFT, padx=(0, SP_SM))
        self.entry_year = ttk.Entry(date_row, width=6)
        self.entry_year.insert(0, self.config.get('target_year', '2026'))
        self.entry_year.pack(side=tk.LEFT, padx=(0, SP_LG))

        ttk.Label(date_row, text="날짜", font=(FONT_FAMILY, FONT_SIZE_MD, 'bold')).pack(side=tk.LEFT, padx=(0, SP_SM))

        self.month_days = self.config.get('target_days', dict(EMPTY_MONTH_DAYS))
        if isinstance(self.month_days, list):
            self.month_days = {"09": self.month_days, "10": [], "11": []}

        self.month_labels = {}
        for month in MONITOR_MONTHS:
            month_str = f"{month:02d}"
            btn_frame = ttk.Frame(date_row)
            btn_frame.pack(side=tk.LEFT, padx=SP_XS)
            ttk.Button(btn_frame, text=f"{month}월",
                       command=lambda m=month: self.open_calendar(m)).pack(side=tk.TOP)
            days_count = len(self.month_days.get(month_str, []))
            lbl = ttk.Label(btn_frame, text=f"{days_count}개", foreground=CLR_INFO)
            lbl.pack(side=tk.TOP)
            self.month_labels[month_str] = lbl

        # 활성화된 선사 수 표시
        initial_status = ' | '.join(f"{n} 0/0" for n in PLATFORM_NAMES.values())
        self.lbl_boat_status = ttk.Label(date_row, text=initial_status,
                                         foreground=CLR_INFO, font=(FONT_FAMILY, FONT_SIZE_MD, 'bold'))
        self.lbl_boat_status.pack(side=tk.RIGHT, padx=SP_SM)

        # 날짜 요약
        self.lbl_days_summary = ttk.Label(settings_frame, text=self.get_days_summary(),
                                          foreground=CLR_FG_MUTED, wraplength=800)
        self.lbl_days_summary.pack(anchor='w', padx=SP_SM, pady=(0, SP_SM))

        # ── 구분선 ──
        ttk.Separator(settings_frame, orient='horizontal').pack(fill=tk.X, pady=SP_SM)

        # ── Row 2: 예약정보 + 간격 + 체크박스 (한 줄) ──
        row2 = ttk.Frame(settings_frame)
        row2.pack(fill=tk.X)

        ttk.Label(row2, text="예약자명").pack(side=tk.LEFT, padx=(0, SP_XS))
        self.entry_reserve_name = ttk.Entry(row2, width=8)
        self.entry_reserve_name.insert(0, self.config.get('reserve_name', ''))
        self.entry_reserve_name.pack(side=tk.LEFT, padx=(0, SP_MD))

        ttk.Label(row2, text="전화번호").pack(side=tk.LEFT, padx=(0, SP_XS))
        self.entry_reserve_phone = ttk.Entry(row2, width=13)
        self.entry_reserve_phone.insert(0, self.config.get('reserve_phone', ''))
        self.entry_reserve_phone.pack(side=tk.LEFT, padx=(0, SP_MD))

        ttk.Label(row2, text="인원").pack(side=tk.LEFT, padx=(0, SP_XS))
        self.entry_reserve_count = ttk.Entry(row2, width=3)
        self.entry_reserve_count.insert(0, str(self.config.get('reserve_count', 1)))
        self.entry_reserve_count.pack(side=tk.LEFT, padx=(0, SP_XS))
        ttk.Label(row2, text="명").pack(side=tk.LEFT, padx=(0, SP_LG))

        # 수직 구분선
        ttk.Separator(row2, orient='vertical').pack(side=tk.LEFT, fill=tk.Y, padx=SP_MD, pady=SP_XS)

        ttk.Label(row2, text="간격").pack(side=tk.LEFT, padx=(0, SP_XS))
        self.entry_min_interval = ttk.Entry(row2, width=3)
        self.entry_min_interval.insert(0, str(self.config.get('check_interval_min', 8)))
        self.entry_min_interval.pack(side=tk.LEFT, padx=(0, SP_XS))
        ttk.Label(row2, text="~").pack(side=tk.LEFT)
        self.entry_max_interval = ttk.Entry(row2, width=3)
        self.entry_max_interval.insert(0, str(self.config.get('check_interval_max', 10)))
        self.entry_max_interval.pack(side=tk.LEFT, padx=(0, SP_XS))
        ttk.Label(row2, text="분").pack(side=tk.LEFT, padx=(0, SP_LG))

        # 체크박스 (오른쪽 정렬)
        self.var_test_mode = tk.BooleanVar(value=self.config.get('test_mode', True))
        ttk.Checkbutton(row2, text="Test", variable=self.var_test_mode,
                        bootstyle="warning-round-toggle").pack(side=tk.RIGHT, padx=SP_SM)
        self.var_summary_alert = tk.BooleanVar(value=self.config.get('summary_alert', True))
        ttk.Checkbutton(row2, text="종합알람", variable=self.var_summary_alert,
                        bootstyle="success-round-toggle").pack(side=tk.RIGHT, padx=SP_SM)

    def _create_action_buttons(self, parent):
        """시작/중지/저장 버튼 섹션 (중앙 정렬)"""
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(pady=(SP_SM, SP_SM))

        ttk.Button(btn_frame, text="설정 저장", command=self.save_config, width=16, bootstyle="secondary").pack(side=tk.LEFT, padx=SP_XS, ipady=SP_XS)
        ttk.Separator(btn_frame, orient='vertical').pack(side=tk.LEFT, fill=tk.Y, padx=SP_MD, pady=SP_XS)
        self.btn_start = ttk.Button(btn_frame, text="시작", command=self.start_monitor, width=16, bootstyle="success")
        self.btn_start.pack(side=tk.LEFT, padx=SP_XS, ipady=SP_XS)
        self.btn_stop = ttk.Button(btn_frame, text="중지", command=self.stop_monitor, state="disabled", width=16, bootstyle="danger")
        self.btn_stop.pack(side=tk.LEFT, padx=SP_XS, ipady=SP_XS)
        if TRAY_AVAILABLE:
            ttk.Separator(btn_frame, orient='vertical').pack(side=tk.LEFT, fill=tk.Y, padx=SP_MD, pady=SP_XS)
            ttk.Button(btn_frame, text="숨기기", command=self.hide_to_tray, width=12, bootstyle="info-outline").pack(side=tk.LEFT, padx=SP_XS, ipady=SP_XS)

    def _create_log_section(self, parent):
        """모니터링 로그 섹션"""
        log_frame = ttk.Labelframe(parent, text="  모니터링 로그", padding=SP_SM, bootstyle="secondary")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(SP_SM, 0))

        self.log_area = tk.Text(log_frame, height=30, state='disabled',
                                font=(FONT_MONO, FONT_SIZE_SM), bg=CLR_LOG_BG, fg=CLR_LOG_FG,
                                insertbackground=CLR_LOG_FG, relief='flat', padx=SP_MD, pady=SP_SM)
        self.log_area.pack(fill=tk.BOTH, expand=True)

        # 로그 텍스트 태그 (컬러링)
        self.log_area.tag_configure('timestamp', foreground=CLR_LOG_TIMESTAMP)
        self.log_area.tag_configure('success', foreground=CLR_LOG_SUCCESS)
        self.log_area.tag_configure('error', foreground=CLR_LOG_ERROR)
        self.log_area.tag_configure('warning', foreground=CLR_LOG_WARNING)
        self.log_area.tag_configure('info_msg', foreground=CLR_LOG_INFO)

        self.log_msg("=" * 50)
        self.log_msg("🎣 낚시배 취소석 모니터 v2.0")
        self.log_msg("=" * 50)
        self.log_msg("1. 텔레그램 설정을 입력하세요")
        self.log_msg("2. 선박을 추가하세요 (이름 + URL)")
        self.log_msg("3. 📅 버튼을 눌러 날짜를 선택하세요")
        self.log_msg("4. '모니터링 시작' 버튼을 클릭하세요")
        self.log_msg("")
    
    def open_calendar(self, month: int):
        """캘린더 팝업 열기"""
        year = int(self.entry_year.get())
        month_str = f"{month:02d}"
        current_days = self.month_days.get(month_str, [])
        
        CalendarPopup(
            self.root,
            year=year,
            month=month,
            selected_days=current_days,
            callback=lambda m, days: self.on_calendar_select(m, days)
        )
    
    def on_calendar_select(self, month: int, days: list):
        """캘린더에서 날짜 선택 완료"""
        month_str = f"{month:02d}"
        self.month_days[month_str] = days
        
        # 라벨 업데이트
        if month_str in self.month_labels:
            self.month_labels[month_str].config(text=f"{len(days)}개")
        
        # 요약 업데이트
        self.lbl_days_summary.config(text=self.get_days_summary())
        
        self.log_msg(f"📅 {month}월: {len(days)}개 날짜 선택됨")
    
    def get_days_summary(self):
        """선택된 날짜 요약 텍스트"""
        parts = []
        for month in MONITOR_MONTHS:
            month_str = f"{month:02d}"
            days = self.month_days.get(month_str, [])
            if days:
                sorted_days = sorted([int(d) for d in days])
                if len(sorted_days) > 5:
                    days_text = ', '.join(map(str, sorted_days[:5])) + f"... (+{len(sorted_days)-5})"
                else:
                    days_text = ', '.join(map(str, sorted_days))
                parts.append(f"{month}월: {days_text}")
        
        if not parts:
            return "💡 위의 📅 버튼을 눌러 날짜를 선택하세요"
        return " | ".join(parts)
    
    def add_boat(self):
        """선박 추가"""
        name = self.entry_boat_name.get().strip()
        url = self.entry_boat_url.get().strip()
        
        if not name or not url:
            messagebox.showwarning("경고", "선박명과 URL을 입력해주세요.")
            return
        
        platform = self.current_platform
        
        try:
            parsed = urlparse(url)
            domain = f"{parsed.scheme}://{parsed.netloc}"

            if platform == 'thefishing':
                # 더피싱: PA_N_UID 필요
                params = parse_qs(parsed.query)
                pa_n_uid = params.get('PA_N_UID', [''])[0]
                
                if not pa_n_uid:
                    messagebox.showwarning("경고", "URL에서 PA_N_UID를 찾을 수 없습니다.\n예시: ...&PA_N_UID=1190")
                    return
                
                base_url = f"{domain}/index.php"
                boat = {
                    "name": name,
                    "enabled": True,
                    "base_url": base_url,
                    "pa_n_uid": pa_n_uid
                }
                self.log_msg(f"✅ [{PLATFORM_NAMES[platform]}] 선박 추가: {name} (PA_N_UID: {pa_n_uid})")

            else:  # sunsang24
                # 선상24: 도메인만 필요 (예: https://rkclgh.sunsang24.com)
                boat = {
                    "name": name,
                    "enabled": True,
                    "base_url": domain  # 도메인만 저장
                }
                self.log_msg(f"✅ [{PLATFORM_NAMES[platform]}] 선박 추가: {name} ({domain})")
            
            # 현재 플랫폼의 선박 목록에 추가
            boat_key = f"{platform}_boats"
            if boat_key not in self.config:
                self.config[boat_key] = []
            
            self.config[boat_key].append(boat)
            self.refresh_boat_grid()
            
            self.entry_boat_name.delete(0, tk.END)
            self.entry_boat_url.delete(0, tk.END)
            
        except Exception as e:
            messagebox.showerror("오류", f"URL 파싱 오류: {e}")
    
    def refresh_boat_grid(self):
        """선박 버튼 그리드 새로고침 (visible 보트만 표시)"""
        # 기존 버튼 모두 제거
        for widget in self.grid_frame.winfo_children():
            widget.destroy()

        self.boat_buttons = {}
        boats = self.get_current_boats()

        # visible 필터링: (원래 인덱스, boat) 쌍 유지
        visible_boats = [
            (orig_idx, boat) for orig_idx, boat in enumerate(boats)
            if boat.get('visible', True)
        ]
        enabled_count = 0

        # 10열 그리드 생성
        cols = 10
        for grid_pos, (orig_idx, boat) in enumerate(visible_boats):
            row = grid_pos // cols
            col = grid_pos % cols

            # 3상태 색상: off(회색), monitor(녹색), reserve(빨간색)
            mode = boat.get('mode', 'off') if boat.get('enabled', False) else 'off'
            bg_color, fg_color = MODE_COLORS.get(mode, MODE_COLORS['off'])
            if mode != 'off':
                enabled_count += 1

            # 버튼 이름 (너무 길면 자르기)
            name = boat['name']
            if len(name) > 6:
                name = name[:5] + ".."

            btn = ttk.Button(
                self.grid_frame,
                text=name,
                width=8,
                style=BOAT_STYLE_MAP.get(mode, 'Off.TButton'),
                cursor='hand2',
                command=lambda idx=orig_idx: self.toggle_boat_by_index(idx)
            )
            btn.grid(row=row, column=col, padx=SP_XS, pady=SP_XS, sticky='ew')

            # 우클릭으로 사이트가기용 선택
            btn.bind('<Button-3>', lambda e, idx=orig_idx: self.select_boat_for_site(idx))

            self.boat_buttons[boat['name']] = btn

        # 전체선택 버튼 스타일 업데이트
        if self.btn_select_all:
            all_on = len(visible_boats) > 0 and enabled_count == len(visible_boats)
            self.btn_select_all.configure(style=_toggle_style(all_on, 'Platform'))

        # 활성화된 선사 수 라벨 업데이트
        if self.lbl_boat_status:
            parts = []
            for pk in PLATFORM_KEYS:
                boats_list = self.config.get(pk, [])
                visible = [b for b in boats_list if b.get('visible', True)]
                enabled = sum(1 for b in visible if b.get('enabled', False))
                name = PLATFORM_KEY_NAMES[pk]
                parts.append(f"{name} {enabled}/{len(visible)}")
            self.lbl_boat_status.configure(text=f"{' | '.join(parts)}")
    
    @property
    def current_platform(self) -> str:
        """현재 선택된 플랫폼 키 (thefishing / sunsang24)"""
        return self.config.get('current_platform', 'thefishing')

    def get_current_boats(self):
        """현재 플랫폼의 선박 목록 반환"""
        return self.config.get(f'{self.current_platform}_boats', [])
    
    def switch_platform(self, platform):
        """플랫폼 전환"""
        self.config['current_platform'] = platform

        # 버튼 스타일 업데이트
        for key in PLATFORM_NAMES:
            btn = getattr(self, f'btn_{key}')
            btn.configure(style=_toggle_style(key == platform))

        # 그리드 새로고침
        self.selected_boat = None
        self.refresh_boat_grid()

        self.log_msg(f"🔄 플랫폼 전환: {PLATFORM_NAMES[platform]}")

    def open_boat_editor(self):
        """선사 편집 팝업 열기"""
        platform = self.current_platform
        boats_key = f'{platform}_boats'
        boats = self.config.get(boats_key, [])

        def on_editor_confirm(updated_boats):
            self.config[boats_key] = updated_boats
            self.refresh_boat_grid()
            self.save_config_quietly()
            visible_count = sum(1 for b in updated_boats if b.get('visible', True))
            self.log_msg(f"✏️ {PLATFORM_NAMES[platform]} 선사 편집 완료: "
                         f"{visible_count}/{len(updated_boats)}개 표시")

        BoatEditorPopup(self.root, platform, boats, callback=on_editor_confirm)

    def toggle_boat_by_index(self, idx):
        """인덱스로 선박 상태 순환: off → monitor → reserve → off"""
        boats = self.get_current_boats()
        if idx < len(boats):
            # 먼저 선택 설정 (사이트가기용)
            self.selected_boat = idx
            
            # 3상태 순환: off → monitor(녹색) → reserve(빨간색) → off
            current_mode = boats[idx].get('mode', 'off')
            if not boats[idx].get('enabled', False):
                current_mode = 'off'
            
            if current_mode == 'off':
                boats[idx]['mode'] = 'monitor'
                boats[idx]['enabled'] = True
                status = "🟢 모니터링"
            elif current_mode == 'monitor':
                boats[idx]['mode'] = 'reserve'
                boats[idx]['enabled'] = True
                status = "🔴 자동예약"
            else:  # reserve
                boats[idx]['mode'] = 'off'
                boats[idx]['enabled'] = False
                status = "⚪ 비활성"
            
            self.refresh_boat_grid()
            self.save_config_quietly()  # 자동 저장
            self.log_msg(f"🎯 {boats[idx]['name']}: {status}")
    
    def select_boat_for_site(self, idx):
        """사이트가기용 선박 선택 (우클릭)"""
        self.selected_boat = idx
        boats = self.get_current_boats()
        if idx < len(boats):
            self.log_msg(f"🎯 {boats[idx]['name']} 선택됨 (사이트가기)")
    
    def toggle_all_boats(self):
        """전체 선박 ON/OFF 토글 (visible 보트만 대상)"""
        boats = self.get_current_boats()
        visible = [b for b in boats if b.get('visible', True)]
        if not visible:
            return

        # 현재 visible 중 ON인 선박이 있으면 전체 OFF, 없으면 전체 ON
        any_enabled = any(b.get('enabled', False) for b in visible)

        for boat in visible:
            boat['enabled'] = not any_enabled
            boat['mode'] = 'monitor' if not any_enabled else 'off'

        self.refresh_boat_grid()
        self.save_config_quietly()

        status = "OFF" if any_enabled else "ON"
        self.log_msg(f"☑ 전체 선박 {status}")
    
    def delete_selected_boat(self):
        """선택된 선박 삭제"""
        if self.selected_boat is None:
            messagebox.showwarning("경고", "삭제할 선박을 먼저 클릭하세요.")
            return
        
        boats = self.get_current_boats()
        if self.selected_boat < len(boats):
            deleted = boats.pop(self.selected_boat)
            self.selected_boat = None
            self.refresh_boat_grid()
            self.log_msg(f"🗑️ 선박 삭제: {deleted['name']}")
    
    def open_boat_site(self):
        """활성화된 모든 선박의 캘린더 사이트 열기"""
        boats = self.get_current_boats()
        enabled_boats = [b for b in boats if b.get('enabled', False)]
        
        if not enabled_boats:
            messagebox.showwarning("경고", "활성화된 선박이 없습니다.")
            return
        
        year = self.entry_year.get()
        month = self.selected_site_month.get()
        platform = self.current_platform
        
        opened_count = 0
        for boat in enabled_boats:
            if platform == 'thefishing':
                url = FishingBoatMonitor.build_calendar_url(boat['base_url'], boat['pa_n_uid'], year, month)
            else:  # sunsang24
                url = FishingBoatMonitor.build_schedule_url(boat['base_url'], year, month)

            webbrowser.open(url)
            opened_count += 1
        
        self.log_msg(f"🌐 {opened_count}개 선박 사이트 열림 ({int(month)}월)")
    
    def select_site_month(self, month_str):
        """사이트가기용 월 선택"""
        self.selected_site_month.set(month_str)

        # 버튼 스타일 업데이트
        for ms, btn in self.month_buttons.items():
            btn.configure(style=_toggle_style(ms == month_str, 'Month'))
    
    def log_msg(self, msg):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ts_part = f"[{timestamp}] "
        msg_part = f"{msg}\n"

        # 메시지 내용에 따라 태그 결정
        tag = None
        if any(k in msg for k in ('✅', '성공', '완료', '저장')):
            tag = 'success'
        elif any(k in msg for k in ('❌', '실패', '에러', 'Error', '오류')):
            tag = 'error'
        elif any(k in msg for k in ('⚠', '경고', 'Warning')):
            tag = 'warning'
        elif any(k in msg for k in ('📅', '🔍', '📂', 'ℹ', '🚀', '🛑')):
            tag = 'info_msg'

        def _update():
            self.log_area.config(state='normal')
            self.log_area.insert(tk.END, ts_part, 'timestamp')
            if tag:
                self.log_area.insert(tk.END, msg_part, tag)
            else:
                self.log_area.insert(tk.END, msg_part)
            self.log_area.see(tk.END)
            self.log_area.config(state='disabled')

        self.root.after(0, _update)
    
    def test_telegram(self):
        """텔레그램 테스트"""
        token = self.config.get('telegram_token', '')
        chat_id = self.config.get('telegram_chat_id', '')
        
        notifier = TelegramNotifier(token, chat_id)
        if notifier.send_message("🎣 낚시배 취소석 모니터 테스트 메시지입니다!"):
            self.log_msg("✅ 텔레그램 테스트 성공!")
            messagebox.showinfo("성공", "텔레그램 메시지가 전송되었습니다!")
        else:
            self.log_msg("❌ 텔레그램 테스트 실패")
            messagebox.showerror("실패", "텔레그램 전송에 실패했습니다.")
    
    def start_monitor(self):
        config = self.save_config()
        
        if not config['target_days']:
            messagebox.showwarning("경고", "감시할 날짜를 입력해주세요.")
            return
        
        # 두 플랫폼에서 활성화된 선박 체크
        enabled_by_platform = {
            pk: [b for b in config.get(pk, []) if b.get('enabled', False) and b.get('visible', True)]
            for pk in PLATFORM_KEYS
        }
        total_enabled = sum(len(v) for v in enabled_by_platform.values())

        if total_enabled == 0:
            messagebox.showwarning("경고", "활성화된 선박이 없습니다.")
            return

        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")

        self.log_msg("")
        self.log_msg("🚀 모니터링 시작!")
        for pk in PLATFORM_KEYS:
            boats_list = enabled_by_platform[pk]
            if boats_list:
                icon = PLATFORM_KEY_ICONS.get(pk, '🚢')
                self.log_msg(f"{icon} [{PLATFORM_KEY_NAMES[pk]}] {len(boats_list)}개: {[b['name'] for b in boats_list]}")
        self.log_msg(f"📅 월: {config['target_months']}")
        self.log_msg(f"📆 날짜: {config['target_days']}")
        
        self.monitor = FishingBoatMonitor(self.log_msg, config)
        self.monitor_thread = threading.Thread(target=self.monitor.run, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitor(self):
        if self.monitor:
            self.monitor.stop()
        
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")
        self.log_msg("🛑 모니터링 중지 요청됨")
    
    # ========== 트레이 숨김 기능 ==========
    def get_console_window(self):
        """콘솔 창 핸들 가져오기"""
        return ctypes.windll.kernel32.GetConsoleWindow()
    
    def hide_console(self):
        """콘솔 완전 분리 (창 + 작업표시줄 모두 제거)"""
        try:
            ctypes.windll.kernel32.FreeConsole()
        except Exception:
            pass

    def show_console(self):
        """콘솔 불필요 (GUI 로그창 사용)"""
        pass
    
    def create_tray_icon_image(self):
        """트레이 아이콘 이미지 생성 (빨간색 - 낚시배 모니터)"""
        img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # 빨간색 원 배경
        draw.ellipse([8, 8, 56, 56], fill=(244, 67, 54))
        # F 글자 (Fish)
        draw.text((24, 16), "F", fill="white")
        return img
    
    def _on_minimize(self, event):
        """최소화 버튼 클릭 시 트레이로 숨기기"""
        if event.widget == self.root and self.root.state() == 'iconic':
            self.root.after(10, self.hide_to_tray)

    def hide_to_tray(self):
        """트레이로 숨기기"""
        if not TRAY_AVAILABLE:
            self.log_msg("⚠️ 트레이 기능 사용 불가")
            return
        
        self.root.withdraw()
        self.hide_console()
        
        icon_image = self.create_tray_icon_image()
        
        menu = pystray.Menu(
            pystray.MenuItem("🖥️ 창 열기", self.show_from_tray, default=True),
            pystray.MenuItem("🛑 종료", self.exit_app)
        )
        
        self.tray_icon = pystray.Icon(
            "fishing_monitor",
            icon_image,
            "낚시배 취소석 모니터",
            menu
        )
        
        threading.Thread(target=self.tray_icon.run, daemon=True).start()
        self.log_msg("👁️ 트레이로 숨김")
    
    def show_from_tray(self, icon=None, item=None):
        """트레이에서 복원"""
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None
        
        self.show_console()
        self.root.after(0, self.root.deiconify)
        self.root.after(100, self.root.lift)
    
    def exit_app(self, icon=None, item=None):
        """앱 종료"""
        if self.monitor:
            self.monitor.stop()
        
        if self.tray_icon:
            self.tray_icon.stop()

        self.root.after(0, self.root.destroy)

# ============================================
# 🚀 실행
# ============================================
if __name__ == "__main__":
    # 콘솔 창 즉시 제거 (GUI 앱이므로 콘솔 불필요)
    try:
        ctypes.windll.kernel32.FreeConsole()
    except Exception:
        pass

    root = ttk.Window(themename="darkly")
    app = FishingBoatMonitorApp(root)
    root.mainloop()
