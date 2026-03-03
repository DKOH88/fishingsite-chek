import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import messagebox
import tkinter as tk
import json
import os
import sys
import subprocess
import threading
import ctypes
import webbrowser
import re
from datetime import datetime
from PIL import Image, ImageTk # 📝 [추가] 이미지 표시를 위한 라이브러리

# Windows 콘솔 UTF-8 설정
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

    # DPI 스케일링 인식 설정 (실제 해상도 얻기 위해)
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-Monitor DPI Aware
    except:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except:
            pass

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(BASE_DIR, "config")
LAUNCHER_STATE_FILE = os.path.join(CONFIG_DIR, "launcher_state.json")
BOTS_DIR = os.path.join(BASE_DIR, "bots")

# 더피싱 선사 홈페이지 URL 매핑 (선사명 -> 도메인)
THEFISHING_SITES = {
    "금땡이호": "xn--jj0bj3lvmq92n.kr",
    "나폴리호": "napoliho.net",
    "뉴성령호": "sungryungho.com",
    "뉴찬스호": "chanceho.com",
    "범블비호": "xn--2i0b07tba4320a.kr",
    "블루호": "bluefishing.asia",
    "비엔나호": "vinaho.com",
    "샤크호": "yamujinfishing.com",
    "오디세이호": "joeunfish.com",
    "유진호": "eugeneho.kr",
    "카즈미호": "xn--hg3b11w8xdjuj.com",
    "캡틴호": "captainfishing.net",
    "프랜드호": "friendho.com",
    "바이트호": "biteho.kr",
    "골드피싱호": "mscufishing.com",
    "뉴신정호": "newsj.co.kr",
    "루디호": "rudyfishing.com",
    "마그마호": "xn--2i0b07tba4320a.kr",
    "미라클호": "xn--xk3bm1aee249g.com",
    "부흥호": "khanfishing.com",
    "솔티가호": "rudyfishing.com",
    "여명호": "xn--v42bv0rcoar53c6lb.kr",
    "청용호": "changdukho.com",
    "퀸블레스호": "blessho.com",
    "행운호": "hangwoonho.com",
    "god호": "teamgod.kr",
    "만수피싱호": "xn--lz2bu5mvsau18c.kr",
    "스타피싱호": "jstar.thefishing.kr",
    "아라호": "araho.kr",
    "아이리스호": "irisho.kr",
    "야호": "xn--2f5b291a.com",
    "짱구호": "ybada.com",
    "크루즈호": "cruiseho.com",
    "팀만수호": "teammansu.kr",
    "팀만수호2": "teammansu.kr",
    "페라리호": "xn--oi2bn5b095b4mc.com",
    "만석호": "mscufishing.com",
    "승주호": "mscufishing.com",
    "으리호": "mscufishing.com",
    "헌터호": "mscufishing.com",
    "헤르메스호": "hermes.thefishing.kr",
    "까칠이호": "hl0b209b41esvi.com",
    "아인스호": "einsho.com",
    "야야호": "yayaho.kr",
    "예린호": "yerinfishing.com",
    "청춘호": "xn--ox6bwq60s.kr",
    "팀루피호": "changdukho.com",
    "승하호": "seungha.kr",
    "하이피싱호": "hifishing.net",
    "양파호": "xn--og5bo0wvnc.kr",
    "천일호": "fishing1001.com",
    "팀바이트호": "teambite.kr",
    "하와이호": "newhawaii.co.kr",
    "깜보호": "winner.thefishing.kr",
    "헤라호": "ssfish.kr",
    "청광호": "chungkwangho.net",
    "뉴청남호": "chungnamho.com",
    "청남호": "chungnamho.com",
    "청남호2": "chungnamho.com",
    "와이파이호": "khanfishing.com",
    "욜로호": "khanfishing.com",
    "제트호": "khanfishing.com",
    "장현호": "namdangfishing.com",
    "장현호2": "namdangfishing.com",
    "아일랜드호": "fishingi.net",
    "블루오션호": "blueoceanho.kr",
    "영차호": "xn--hw4b19c9whvpk.kr",
    "오닉스호": "xn--bj1bs41a0scq4w.kr",
    "조커호": "seasidefishing.kr",
}

# 선상24 선사 서브도메인 매핑 (선사명 -> 서브도메인)
SUNSANG24_SITES = {
    "가즈아호": "ocpro",
    "도지호": "doji",
    "빅보스호": "bigboss24",
    "어쩌다어부호": "fisherman",
    "자이언트호": "rkclgh",
    "프린스호": "princeho",
    "호랭이호": "horeng2",
    "아리랑1호": "arirang",
    "넘버원호": "no1",
    "뉴항구호": "daebak",
    "천마호": "metafishingclub",
    "기가호": "giga",
    "아이언호": "iron",
    "가가호": "gagaho",
    "루키나호": "lukina",
    "루키나 2호": "lukina",
    "팀에프원호": "teamf",
    "팀에프투호": "teamf",
    "악바리호": "akbari",
    "악바리호2": "akbari",
    "은가비호": "eungabi",
    "동백호": "dongbaek",
    "제비호": "jebi",
    "오션스타1호": "ysoceanstar",
    "오션스타2호": "ysoceanstar",
    "오션스타3호": "ysoceanstar",
    "E.스마일호": "esmile",
}

# Data Structure: Port -> { ProviderName: ScriptName }
# 항구 정렬: 선사 수 내림차순
PORTS = {
    "오천항": {
        "가즈아호": "선상24/가즈아호_Bot.py",
        "가즈아호(API)": "api/선상24/가즈아호_API.py",
        "금땡이호": "더피싱/금땡이호_Bot.py",
        "금땡이호(API)": "api/더피싱/금땡이호_API.py",
        "꽃돼지호": None,
        "꽃돼지호(API)": "api/선상24/꽃돼지호_API.py",
        "나폴리호": "더피싱/나폴리호_Bot.py",
        "나폴리호(API)": "api/더피싱/나폴리호_API.py",
        "뉴성령호": "더피싱/뉴성령호_Bot.py",
        "뉴찬스호(선)": "더피싱/뉴찬스호_Bot.py",
        "도지호": "선상24/도지호_Bot.py",
        "도지호(API)": "api/선상24/도지호_API.py",
        "라라호(API)": "api/더피싱/라라호_API.py",
        "바이트호": "더피싱/바이트호_Bot.py",
        "바이트호(API)": "api/더피싱/바이트호_API.py",
        "범블비호": "더피싱/범블비호_Bot.py",
        "범블비호(API)": "api/더피싱/범블비호_API.py",
        "블루호": "더피싱/블루호_Bot.py",
        "블루호(API)": "api/더피싱/블루호_API.py",
        "비엔나호": "더피싱/비엔나호_Bot.py",
        "비엔나호(API)": "api/비엔나호_API.py",
        "빅보스호": "선상24/빅보스호_Bot.py",
        "빅보스호(API)": "api/선상24/빅보스호_API.py",
        "샤크호": "더피싱/샤크호_Bot.py",
        "샤크호(API)": "api/더피싱/샤크호_API.py",
        "싸부호": None,
        "아리랑1호": "선상24/아리랑1호.py",
        "어쩌다어부호(선)": "선상24/어쩌다어부호_Bot.py",
        "오디세이호": "더피싱/오디세이호_Bot.py",
        "오디세이호(API)": "api/더피싱/오디세이호_API.py",
        "유진호": "더피싱/유진호_Bot.py",
        "유진호(API)": "api/더피싱/유진호_API.py",
        "자이언트호": "선상24/자이언트호_Bot.py",
        "카즈미호": "더피싱/카즈미호_Bot.py",
        "카즈미호(API)": "api/더피싱/카즈미호_API.py",
        "캡틴호": "더피싱/캡틴호_Bot.py",
        "캡틴호(API)": "api/더피싱/캡틴호_API.py",
        "프랜드호": "더피싱/프랜드호_Bot.py",
        "프랜드호(API)": "api/더피싱/프랜드호_API.py",
        "프린스호": "선상24/프린스호_Bot.py",
        "호랭이호": "선상24/호랭이호_Bot.py",
        "호랭이호(API)": "api/선상24/호랭이호_API.py",
        "흑돼지호(API)": "api/더피싱/흑돼지호_API.py",
        "자이언트호(API)": "api/선상24/자이언트호_API.py",
    },
    "안흥·신진항": {
        "골드피싱호": "더피싱/안흥골드피싱호_Bot.py",
        "낭만어부호": None,
        "뉴신정호": "더피싱/뉴신정호_Bot.py",
        "루디호": "더피싱/루디호_Bot.py",
        "루디호(API)": "api/더피싱/루디호_API.py",
        "마그마호": "더피싱/마그마호_Bot.py",
        "마그마호(API)": "api/더피싱/마그마호_API.py",
        "미라클호": "더피싱/미라클호_Bot.py",
        "부흥호": "더피싱/부흥호_Bot.py",
        "블레스호": None,
        "블레스호(API)": "api/더피싱/블레스호_API.py",
        "솔티가호": "더피싱/솔티가호_Bot.py",
        "여명호": "더피싱/여명호_Bot.py",
        "여명호(API)": "api/더피싱/여명호_API.py",
        "지도호": None,
        "청용호": "더피싱/청용호_Bot.py",
        "퀸블레스호": "더피싱/퀸블레스호_Bot.py",
        "퀸블레스호(API)": "api/더피싱/퀸블레스호_API.py",
        "킹스타호": None,
        "행운호": "더피싱/행운호_Bot.py",
        "뉴신정호(API)": "api/더피싱/뉴신정호_API.py",
    },
    "영흥도": {
        "god호(선)": "더피싱/지오디호_Bot.py",
        "금강7호(API)": "api/더피싱/금강7호_API.py",
        "루키나 2호(선)": "선상24/루키나 2호_Bot.py",
        "루키나호(선)": "선상24/루키나호_Bot.py",
        "만수피싱호": "더피싱/만수피싱호_Bot.py",
        "스타피싱호(선)": "더피싱/스타피싱호_Bot.py",
        "아라호(선)": "더피싱/아라호_Bot.py",
        "아이리스호(선)": "더피싱/아이리스호_Bot.py",
        "야호(API)": "api/더피싱/야호_API.py",
        "야호(선)": "더피싱/야호_Bot.py",
        "지오디호(API)": "api/더피싱/지오디호_API.py",
        "짱구호(선)": "더피싱/짱구호_Bot.py",
        "크루즈호": "더피싱/크루즈호_Bot.py",
        "팀만수호(API)": "api/더피싱/팀만수호_API.py",
        "팀만수호(선)": "더피싱/팀만수호_Bot.py",
        "팀에프원호": "선상24/팀에프원_Bot.py",
        "팀에프원호(API)": "api/선상24/팀에프원_API.py",
        "팀에프투호": "선상24/팀에프투_Bot.py",
        "팀에프투호(API)": "api/선상24/팀에프투호_API.py",
        "페라리호(선)": "더피싱/페라리호_Bot.py",
        "영동2호(API)": "api/더피싱/영동2호_API.py",
    },
    "삼길포항": {
        "(신)블루오션호(API)": "api/더피싱/(신)블루오션호_API.py",
        "골드피싱호": "더피싱/골드피싱호_Bot.py",
        "골드피싱호(API)": "api/더피싱/골드피싱_API.py",
        "넘버원호": "선상24/넘버원호_Bot.py",
        "넘버원호(API)": "api/선상24/넘버원호_API.py",
        "뉴항구호": "선상24/뉴항구호_Bot.py",
        "만석호": "더피싱/만석호_Bot.py",
        "만석호(API)": "api/더피싱/만석호_API.py",
        "박찬호(API)": "api/더피싱/박찬호_API.py",
        "승주호": "더피싱/승주호_Bot.py",
        "승주호(API)": "api/더피싱/승주호_API.py",
        "으리호": "더피싱/으리호_Bot.py",
        "으리호(API)": "api/더피싱/으리호_API.py",
        "천마호": "선상24/천마호_Bot.py",
        "헌터호": "더피싱/헌터호_Bot.py",
        "헌터호(API)": "api/더피싱/헌터호_API.py",
        "헤르메스호": "더피싱/헤르메스호_Bot.py",
        "헤르메스호(API)": "api/더피싱/헤르메스호_API.py",
    },
    "대천항": {
        "기가호": "선상24/기가호_Bot.py",
        "까칠이호": "더피싱/까칠이호_Bot.py",
        "승하호": "더피싱/승하호_Bot.py",
        "승하호(API)": "api/더피싱/승하호_API.py",
        "아이언호": "선상24/아이언호_Bot.py",
        "아인스호": "더피싱/아인스호_Bot.py",
        "야야호": "더피싱/야야호_Bot.py",
        "야야호(API)": "api/더피싱/야야호_API.py",
        "양파호": "더피싱/양파호_Bot.py",
        "양파호(API)": "api/더피싱/양파호_API.py",
        "예린호(API)": "api/더피싱/예린호_API.py",
        "예린호(선)": "더피싱/예린호_Bot.py",
        "청춘호": "더피싱/청춘호_Bot.py",
        "청춘호(API)": "api/더피싱/청춘호_API.py",
        "팀루피호": "더피싱/팀루피호_Bot.py",
        "팀루피호(API)": "api/더피싱/팀루피호_API.py",
        "하이피싱호": "더피싱/하이피싱호_Bot.py",
        "하이피싱호(API)": "api/더피싱/하이피싱호_API.py",
        "기가호(API)": "api/선상24/기가호_API.py",
    },
    "마검포항": {
        "❌ 가가호": "선상24/가가호_Bot.py",
        "팀바이트호": "더피싱/팀바이트호_Bot.py",
        "팀바이트호(API)": "api/더피싱/팀바이트호_API.py",
        "하와이호(API)": "api/더피싱/하와이호_API.py",
        "하와이호(선)": "더피싱/하와이호_Bot.py",
    },
    "무창포항": {
        "가가호": "선상24/가가호_Bot.py",
        "깜보호": "더피싱/깜보호_Bot.py",
        "깜보호(API)": "api/더피싱/깜보호_API.py",
        "페가수스호(API)": "api/페가수스_API.py",
        "헤라호": "더피싱/헤라호_Bot.py",
        "헤라호(API)": "api/더피싱/헤라호_API.py",
        "수지호(API)": "api/더피싱/수지호_API.py",
    },
    "영목항": {
        "❌ 청광호": "더피싱/청광호_Bot.py",
        "뉴청남호": "더피싱/뉴청남호_Bot.py",
        "천일호(API)": "api/더피싱/천일호_API.py",
        "청광호(API)": "api/더피싱/청광호_API.py",
        "청남호": "더피싱/청남호_Bot.py",
        "청남호(API)": "api/더피싱/청남호_API.py",
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
        "동백호": "선상24/동백호_Bot.py",
        "은가비호(선)": "선상24/은가비호_Bot.py",
        "장현호": "더피싱/장현호_Bot.py",
        "장현호(API)": "api/장현호_API.py",
        "장현호2": "더피싱/장현호2_Bot.py",
        "피크닉호(API)": "api/선상24/피크닉호_API.py",
        "정환호(API)": "api/선상24/정환호_API.py",
        "동백호(API)": "api/선상24/동백호_API.py",
    },
    "대야도": {
        "❌ 아일랜드호(선)": "더피싱/아일랜드호_Bot.py",
        "블루오션호": "더피싱/블루오션호_Bot.py",
    },
    "백사장항": {
        "영차호": "더피싱/영차호_Bot.py",
        "무야호(API)": "api/선상24/무야호_API.py",
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
        "빅스타호(API)": "api/더피싱/빅스타호_API.py",
        "오닉스호": "더피싱/오닉스호_Bot.py",
        "오닉스호(API)": "api/더피싱/오닉스호_API.py",
        "제우스호(API)": "api/더피싱/제우스호_API.py",
        "평택항피싱호(API)": "api/더피싱/평택항피싱호_API.py",
    },
    "전곡항": {
        "(전곡항)빅보스호(API)": "api/선상24/(전곡항)빅보스호_API.py",
        "제비호": "선상24/제비호_Bot.py",
        "뉴신명호(API)": "api/더피싱/뉴신명호_API.py",
    },
    "홍원항": {
        "조커호": "더피싱/조커호_Bot.py",
        "블랙호(API)": "api/더피싱/블랙호_API.py",
    },
}

class FishingLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("🎣 2026 낚시 예약 봇 통합 런처")
        self.root.geometry("1460x1200")

        self.center_window(1460, 1200)
        
        self.current_provider = None
        self.entries = {}
        self.processes = [] # 실행 중인 봇 프로세스 관리
        self.bot_logs = [] # 📝 [추가] 봇 로그 저장용 리스트
        self.bot_mode = "API"  # "API" 또는 "Selenium" - 기본값 API

        self.create_widgets()

        self.root.bind('<F2>', lambda event: self.start_bot())
        self.root.bind('<F3>', lambda event: self.stop_bots())
        self.root.bind_all('<Button-1>', self.on_global_click)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.load_config()
    
    def on_close(self):
        """Save config, clean up temp files, and close window"""
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
        self.lf_config = ttk.Labelframe(self.root, text="⚙️ 예약 설정", padding=10, bootstyle="info")
        self.lf_config.pack(fill=X, padx=10, pady=5)

        # Row 2: Slots container frame
        self.slots = []
        self.slot_frames = []  # Store frame references for deletion
        self.port_list = list(PORTS.keys())
        self.current_mapping_info = None  # 매핑 정보 저장용

        # Slots container
        self.slots_container = ttk.Frame(self.lf_config)
        self.slots_container.grid(row=2, column=0, columnspan=5, sticky=W, padx=5, pady=2)

        # ALL checkbox (above slot list, inside slots_container)
        self.var_select_all = tk.BooleanVar(value=False)
        frame_all = ttk.Frame(self.slots_container)
        frame_all.pack(fill=X, pady=(0, 5))
        ttk.Checkbutton(frame_all, text="ALL", variable=self.var_select_all, command=self.toggle_all_slots, bootstyle="info-round-toggle").pack(side=LEFT, padx=(0, 10))
        ttk.Button(frame_all, text="📅 예약일 정보", command=self.open_reservation_info, bootstyle="info-outline").pack(side=LEFT, padx=(0, 20))

        # Execution Time (Moved next to Reservation Info)
        ttk.Label(frame_all, text="실행 시간:", font=("맑은 고딕", 9)).pack(side=LEFT, padx=(0, 5))

        self.cb_hour = ttk.Combobox(frame_all, values=[f"{i:02d}" for i in range(24)], width=3, state="readonly", height=24)
        self.cb_hour.set("09")
        self.cb_hour.pack(side=LEFT)
        ttk.Label(frame_all, text="시").pack(side=LEFT)

        self.cb_min = ttk.Entry(frame_all, width=3)
        self.cb_min.insert(0, "00")
        self.cb_min.pack(side=LEFT)
        ttk.Label(frame_all, text="분").pack(side=LEFT)

        self.cb_sec = ttk.Entry(frame_all, width=5)
        self.cb_sec.insert(0, "00.0")
        self.cb_sec.pack(side=LEFT)
        ttk.Label(frame_all, text="초").pack(side=LEFT)

        # 조기오픈 감시 체크박스 (5분전부터 10초마다 페이지 오픈 여부 확인)
        self.var_early_monitor = tk.BooleanVar(value=False)
        ttk.Checkbutton(frame_all, text="🔍 조기오픈감시", variable=self.var_early_monitor, bootstyle="warning-round-toggle").pack(side=LEFT, padx=(10, 0))

        # Add/Remove/Copy buttons (Moved next to Execution Time)
        ttk.Button(frame_all, text="➕ 추가", width=8, command=self.add_slot, bootstyle="success-outline").pack(side=LEFT, padx=(10, 2))
        ttk.Button(frame_all, text="➖ 제거", width=8, command=self.remove_slot, bootstyle="danger-outline").pack(side=LEFT, padx=2)
        ttk.Button(frame_all, text="📋 일괄복사", width=10, command=self.copy_first_slot, bootstyle="info-outline").pack(side=LEFT, padx=2)
        ttk.Button(frame_all, text="📝 정보입력", width=10, command=self.fill_user_info, bootstyle="warning-outline").pack(side=LEFT, padx=2)
        ttk.Button(frame_all, text="🧹 비우기", width=10, command=self.clear_user_info, bootstyle="light-outline").pack(side=LEFT, padx=2)

        # Create initial 4 slots
        for _ in range(4):
            self.add_slot()

        # Test Mode - Row 3
        self.var_test_mode = tk.BooleanVar()
        ttk.Checkbutton(self.lf_config, text="🚀 즉시실행 모드(실행시간 무시)", variable=self.var_test_mode, bootstyle="success-round-toggle").grid(row=3, column=0, columnspan=2, sticky=W, padx=5, pady=5)

        # Simulation Mode - Row 4
        self.var_sim_mode = tk.BooleanVar()
        ttk.Checkbutton(self.lf_config, text="🚫 시뮬레이션 모드(예약실행 안함)", variable=self.var_sim_mode, bootstyle="warning-round-toggle").grid(row=4, column=0, columnspan=2, sticky=W, padx=5, pady=5)

        # Save Button - Row 5
        btn_frame_row5 = ttk.Frame(self.lf_config)
        btn_frame_row5.grid(row=5, column=0, columnspan=5, sticky=W, padx=5, pady=10)
        ttk.Button(btn_frame_row5, text="💾 설정 저장", command=self.save_config, bootstyle="success").pack(side=LEFT, padx=(0, 10))
        ttk.Button(btn_frame_row5, text="✏️ 항구/선사 편집", command=self.open_port_editor, bootstyle="warning-outline").pack(side=LEFT)

        # 선사 검색 프레임 (Row 5 오른쪽)
        search_frame = ttk.Frame(self.lf_config)
        search_frame.grid(row=5, column=2, sticky=E, padx=10, pady=5)

        # 모드 토글 버튼 (API / Selenium)
        self.btn_mode_api = ttk.Button(search_frame, text="API", width=8,
            command=lambda: self.set_bot_mode("API"), bootstyle="info")
        self.btn_mode_api.pack(side=LEFT, padx=(0, 2))

        self.btn_mode_selenium = ttk.Button(search_frame, text="Selenium", width=8,
            command=lambda: self.set_bot_mode("Selenium"), bootstyle="secondary-outline")
        self.btn_mode_selenium.pack(side=LEFT, padx=(0, 2))

        # 새로고침 버튼 (봇 폴더 재스캔)
        ttk.Button(search_frame, text="🔄", width=3,
            command=self.refresh_bot_list, bootstyle="success").pack(side=LEFT, padx=(0, 10))

        ttk.Button(search_frame, text="🌐 사이트 이동", width=13, command=self.open_provider_site, bootstyle="secondary").pack(side=LEFT, padx=(0, 10))
        ttk.Label(search_frame, text="🔍 선사 검색:", font=("맑은 고딕", 9)).pack(side=LEFT, padx=(0, 5))
        self.entry_provider_search = ttk.Entry(search_frame, width=15)
        self.entry_provider_search.pack(side=LEFT, padx=(0, 5))
        self.entry_provider_search.bind("<Return>", lambda e: self.search_and_apply_provider())
        ttk.Button(search_frame, text="검색", width=6, command=self.search_and_apply_provider, bootstyle="info").pack(side=LEFT, padx=(0, 5))

        # 매핑 여부 버튼
        self.btn_mapping_info = ttk.Button(search_frame, text="📅 선상24 맵핑", width=13, command=self.show_mapping_info, bootstyle="secondary")
        self.btn_mapping_info.pack(side=LEFT, padx=(5, 0))


        # 3. Execution (Matching User Screenshot)
        lf_action = ttk.Labelframe(self.root, text="🚀 실행 제어", padding=10, bootstyle="danger")
        lf_action.pack(fill=BOTH, expand=True, padx=10, pady=5) # 📝 [수정] expand=True 추가하여 남은 공간 모두 차지

        # Button Frame
        f_btns = ttk.Frame(lf_action)
        f_btns.pack(fill=X, pady=5)
        ttk.Button(f_btns, text="🔥 봇 실행 (Start) (F2)", command=self.start_bot, bootstyle="success", width=22).pack(side=LEFT, padx=5)
        ttk.Button(f_btns, text="🚫 봇 종료 (Stop) (F3)", command=self.stop_bots, bootstyle="danger", width=22).pack(side=LEFT, padx=5)
        ttk.Button(f_btns, text="🌐 브라우저 종료", command=self.close_browsers, bootstyle="warning", width=15).pack(side=LEFT, padx=5)
        ttk.Button(f_btns, text="📅 캘린더형", command=self.open_provider_site_calendar, bootstyle="info-outline", width=12).pack(side=LEFT, padx=5)

        # Log Label and Area
        ttk.Label(lf_action, text="로그", font=("맑은 고딕", 10, "bold")).pack(anchor=W, pady=(10, 2))
        self.log_area = tk.Text(lf_action, height=15, state="disabled", font=("Consolas", 10), bg="#1e1e1e", fg="#d4d4d4", insertbackground="white") # 📝 [수정] 다크테마 스타일
        self.log_area.pack(fill=BOTH, expand=True, pady=5)

        self.log("✅ 낚시 예약 봇 통합 런처 준비 완료")
        
        
        # Init
        # self.combo_port.current(0)
        # self.on_port_change(None)

    def get_clean_provider_name(self, display_name):
        """Remove '❌ ' prefix and suffixes like (API), (선) for search matching"""
        if not display_name: return ""
        name = display_name.replace("❌ ", "")
        # 검색 매칭을 위해 접미사 제거 (API), (선) 등
        name = re.sub(r'\(API\)|\(선\)|\(셀\)', '', name).strip()
        return name

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
        chk.pack(side="left", padx=(0, 15))

        # Port
        ttk.Label(frame_slot, text="항구:").pack(side="left", padx=(0, 2))
        cb_port = ttk.Combobox(frame_slot, values=self.port_list, width=10, state="readonly", height=30)
        cb_port.set(self.port_list[0] if self.port_list else "")
        cb_port.pack(side="left", padx=(0, 15))

        # Provider
        ttk.Label(frame_slot, text="선사:").pack(side="left", padx=(0, 2))
        cb_provider = ttk.Combobox(frame_slot, width=12, state="readonly", height=35)
        cb_provider.pack(side="left", padx=(0, 15))
        
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
        cb_day.bind("<Return>", lambda e, entry=cb_day: self.pad_day_input(entry))
        ttk.Label(frame_slot, text="일").pack(side="left", padx=(0, 15))

        # Person
        ttk.Label(frame_slot, text="인원:").pack(side="left")
        cb_person = ttk.Combobox(frame_slot, values=[str(p) for p in range(1, 6)], width=2, state="readonly")
        cb_person.set("1")
        cb_person.pack(side="left")
        ttk.Label(frame_slot, text="명").pack(side="left", padx=(0, 10))

        # Name
        ttk.Label(frame_slot, text="이름:").pack(side="left")
        entry_name = ttk.Entry(frame_slot, width=6)
        entry_name.pack(side="left", padx=(0, 10))

        # Depositor
        ttk.Label(frame_slot, text="입금자명:").pack(side="left")
        entry_depositor = ttk.Entry(frame_slot, width=6)
        entry_depositor.pack(side="left", padx=(0, 10))

        # Phone
        ttk.Label(frame_slot, text="전화번호:").pack(side="left")
        entry_phone = ttk.Entry(frame_slot, width=14)
        entry_phone.insert(0, "010-")
        entry_phone.pack(side="left", padx=(0, 5))
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

    def open_in_chrome(self, url):
        """Chrome 브라우저로 URL 열기"""
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        ]

        for chrome_path in chrome_paths:
            if os.path.exists(chrome_path):
                try:
                    subprocess.Popen([chrome_path, url])
                    return True
                except Exception as e:
                    self.log(f"⚠️ Chrome 실행 실패: {e}")

        # Chrome을 찾지 못하면 기본 브라우저로 열기
        self.log("⚠️ Chrome을 찾지 못해 기본 브라우저로 엽니다.")
        webbrowser.open(url)
        return False

    def get_api_bot_base_url(self, script_path):
        """API 봇 파일에서 도메인만 추출 (http://, https://, www. 모두 제거)"""
        full_path = os.path.join(BOTS_DIR, script_path)
        if not os.path.exists(full_path):
            return None

        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # BASE_URL = "http://..." 패턴 찾기
            match = re.search(r'BASE_URL\s*=\s*["\']([^"\']+)["\']', content)
            if match:
                base_url = match.group(1)
                # http://www.mscufishing.com/_core/... → mscufishing.com (도메인만)
                domain_match = re.match(r'https?://(www\.)?([^/]+)', base_url)
                if domain_match:
                    return domain_match.group(2)  # 도메인만 반환 (fishingi.net)
        except Exception as e:
            self.log(f"⚠️ BASE_URL 추출 실패: {e}")

        return None

    def open_provider_site(self):
        """체크된 슬롯의 선사 홈페이지로 이동"""
        # 체크된 슬롯 찾기
        checked_slots = [i for i, slot in enumerate(self.slots) if slot['enable'].get()]
        if not checked_slots:
            self.log("⚠️ 체크된 슬롯이 없습니다.")
            messagebox.showwarning("알림", "먼저 슬롯을 체크해주세요.")
            return

        # 첫 번째 체크된 슬롯의 선사 정보 가져오기
        slot_idx = checked_slots[0]
        slot = self.slots[slot_idx]
        provider_name = slot['provider'].get()

        if not provider_name:
            self.log("⚠️ 선사가 선택되지 않았습니다.")
            messagebox.showwarning("알림", "선사를 선택해주세요.")
            return

        # 선사 이름에서 접미사 제거 (선), (API) 등
        clean_name = self.get_clean_provider_name(provider_name)
        for suffix in ['(선)', '(API)', '(선상24)']:
            clean_name = clean_name.replace(suffix, '').strip()

        # 날짜 정보 가져오기
        year = slot['year'].get()
        month = slot['month'].get()

        # 년/월/일 파싱
        day = slot['day'].get()
        try:
            year_num = int(year)
            month_num = int(month)
            day_num = int(day)
        except:
            year_num = 2026
            month_num = 1
            day_num = 1

        # 0. API 모드일 때: API 봇 파일에서 BASE_URL 추출
        if self.bot_mode == "API":
            port = slot['port'].get()
            script_path = PORTS.get(port, {}).get(provider_name)

            if script_path and script_path.startswith("api/"):
                domain = self.get_api_bot_base_url(script_path)
                if domain:
                    url = f"{domain}/index.php?mid=bk&year={year_num}&month={month_num:02d}&day={day_num:02d}#list"
                    self.log(f"🌐 {clean_name} (API) 홈페이지 이동: {url}")
                    self.open_in_chrome(url)
                    return

        # 1. 선상24 사이트 확인
        subdomain = SUNSANG24_SITES.get(clean_name)
        if subdomain:
            # 선상24 URL: {subdomain}.sunsang24.com/ship/schedule_fleet/YYYYMM
            url = f"{subdomain}.sunsang24.com/ship/schedule_fleet/{year_num}{month_num:02d}"
            self.log(f"🌐 {clean_name} (선상24) 홈페이지 이동: {url}")
            self.open_in_chrome(url)
            return

        # 2. 더피싱 사이트 확인
        site_domain = THEFISHING_SITES.get(clean_name)
        if site_domain:
            # 더피싱 URL: {domain}/index.php?mid=bk&year=2026&month=11&day=01#list
            url = f"{site_domain}/index.php?mid=bk&year={year_num}&month={month_num:02d}&day={day_num:02d}#list"
            self.log(f"🌐 {clean_name} (더피싱) 홈페이지 이동: {url}")
            self.open_in_chrome(url)
            return

        # 3. 둘 다 없으면 에러
        self.log(f"⚠️ '{clean_name}'의 홈페이지 정보가 없습니다.")
        messagebox.showwarning("알림", f"'{clean_name}'의 홈페이지 정보가 등록되지 않았습니다.")

    def open_provider_site_calendar(self):
        """체크된 슬롯의 선사 홈페이지로 캘린더형으로 이동 (mode=cal&PA_N_UID 포함)"""
        # 체크된 슬롯 찾기
        checked_slots = [i for i, slot in enumerate(self.slots) if slot['enable'].get()]
        if not checked_slots:
            self.log("⚠️ 체크된 슬롯이 없습니다.")
            messagebox.showwarning("알림", "먼저 슬롯을 체크해주세요.")
            return

        # 첫 번째 체크된 슬롯의 선사 정보 가져오기
        slot_idx = checked_slots[0]
        slot = self.slots[slot_idx]
        provider_name = slot['provider'].get()

        if not provider_name:
            self.log("⚠️ 선사가 선택되지 않았습니다.")
            messagebox.showwarning("알림", "선사를 선택해주세요.")
            return

        # 선사 이름에서 접미사 제거 (선), (API) 등
        clean_name = self.get_clean_provider_name(provider_name)
        for suffix in ['(선)', '(API)', '(선상24)']:
            clean_name = clean_name.replace(suffix, '').strip()

        # 날짜 정보 가져오기
        year = slot['year'].get()
        month = slot['month'].get()
        day = slot['day'].get()
        try:
            year_num = int(year)
            month_num = int(month)
            day_num = int(day)
        except:
            year_num = 2026
            month_num = 1
            day_num = 1

        # PA_N_UID 추출 (API 봇 → Selenium 봇 순서로 찾기)
        pa_n_uid = None
        port = slot['port'].get()
        script_path = PORTS.get(port, {}).get(provider_name)

        # 1. API 봇 파일에서 PA_N_UID 찾기
        if script_path and script_path.startswith("api/"):
            full_path = os.path.join(BOTS_DIR, script_path)
            if os.path.exists(full_path):
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    # PA_N_UID = "..." 패턴 찾기
                    match = re.search(r'PA_N_UID\s*=\s*["\']([^"\']+)["\']', content)
                    if match:
                        pa_n_uid = match.group(1)
                except:
                    pass

        # 2. API 봇에서 못 찾으면 Selenium 봇 폴더에서 찾기
        if not pa_n_uid:
            selenium_bot_path = os.path.join(BOTS_DIR, "더피싱", f"{clean_name}_Bot.py")
            if os.path.exists(selenium_bot_path):
                try:
                    with open(selenium_bot_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    # PA_N_UID = "..." 패턴 찾기
                    match = re.search(r'PA_N_UID\s*=\s*["\']([^"\']+)["\']', content)
                    if match:
                        pa_n_uid = match.group(1)
                        self.log(f"ℹ️ Selenium 봇에서 PA_N_UID 추출: {pa_n_uid}")
                except:
                    pass

        # 도메인 추출 (도메인만, 프로토콜 없음)
        domain = None

        # 1. API 봇에서 도메인 찾기
        if script_path and script_path.startswith("api/"):
            domain = self.get_api_bot_base_url(script_path)

        # 2. API 봇에서 못 찾으면 Selenium 봇에서 SITE_URL 찾기
        if not domain:
            selenium_bot_path = os.path.join(BOTS_DIR, "더피싱", f"{clean_name}_Bot.py")
            if os.path.exists(selenium_bot_path):
                try:
                    with open(selenium_bot_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    # SITE_URL = "..." 패턴 찾기
                    match = re.search(r'SITE_URL\s*=\s*["\']([^"\']+)["\']', content)
                    if match:
                        domain = match.group(1)
                        # http://, https://, www. 제거
                        domain = re.sub(r'^https?://', '', domain)
                        domain = re.sub(r'^www\.', '', domain)
                        self.log(f"ℹ️ Selenium 봇에서 도메인 추출: {domain}")
                except:
                    pass

        # 3. THEFISHING_SITES에서 도메인 찾기
        if not domain:
            domain = THEFISHING_SITES.get(clean_name)

        if domain and pa_n_uid:
            # 캘린더형 URL: mode=cal&PA_N_UID=xxx
            url = f"{domain}/index.php?mid=bk&year={year_num}&month={month_num:02d}&day={day_num:02d}&mode=cal&PA_N_UID={pa_n_uid}#list"
            self.log(f"📅 {clean_name} 캘린더형 이동: {url}")
            self.open_in_chrome(url)
        elif domain:
            # PA_N_UID 없이 캘린더형 URL
            url = f"{domain}/index.php?mid=bk&year={year_num}&month={month_num:02d}&day={day_num:02d}&mode=cal#list"
            self.log(f"📅 {clean_name} 캘린더형 이동 (PA_N_UID 없음): {url}")
            self.open_in_chrome(url)
        else:
            self.log(f"⚠️ '{clean_name}'의 홈페이지 정보가 없습니다.")
            messagebox.showwarning("알림", f"'{clean_name}'의 홈페이지 정보가 등록되지 않았습니다.")

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

        # 정확히 일치하는 선사들 먼저 필터링
        exact_matches = []
        for port, provider_name, script_path in found_providers:
            clean_name = self.get_clean_provider_name(provider_name)
            if clean_name.lower() == search_term.lower():
                exact_matches.append((port, provider_name, script_path))

        # 선택할 선사 결정 (정확히 일치하는 것들 우선)
        candidates = exact_matches if exact_matches else found_providers

        if len(candidates) == 1:
            selected = candidates[0]
        else:
            # 여러 개 발견 시 선택 다이얼로그 표시
            selected = self.show_provider_selection_dialog(search_term, candidates)
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
            # 매핑 정보 확인 및 버튼 색상 변경
            self.update_mapping_button_state(selected)
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
            listbox.insert(tk.END, f"{provider}  ({port})")

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

    def on_global_click(self, event):
        """전역 클릭 시 모든 슬롯의 날짜 입력란 패딩 적용"""
        for slot in self.slots:
            day_entry = slot.get('day')
            if day_entry:
                self.pad_day_input(day_entry)

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

    def set_bot_mode(self, mode):
        """봇 모드 전환 (API / Selenium)"""
        self.bot_mode = mode

        # 버튼 스타일 업데이트
        if mode == "API":
            self.btn_mode_api.configure(bootstyle="info")
            self.btn_mode_selenium.configure(bootstyle="secondary-outline")
        else:
            self.btn_mode_api.configure(bootstyle="secondary-outline")
            self.btn_mode_selenium.configure(bootstyle="info")

        # 모든 슬롯의 선사 리스트 업데이트
        for i in range(len(self.slots)):
            self.update_slot_provider(i)

        self.log(f"🔄 봇 모드 변경: {mode}")

    def refresh_bot_list(self):
        """봇 폴더를 스캔하여 새로 추가된 봇을 PORTS에 반영"""
        global PORTS

        added_count = 0

        # API 봇 스캔 (bots/api/ 하위)
        api_base = os.path.join(BOTS_DIR, "api")
        if os.path.exists(api_base):
            for root, dirs, files in os.walk(api_base):
                for f in files:
                    if f.endswith("_API.py") or f.endswith("_api.py"):
                        # 상대 경로 생성 (bots/ 기준)
                        full_path = os.path.join(root, f)
                        rel_path = os.path.relpath(full_path, BOTS_DIR).replace("\\", "/")

                        # 선사명 추출 (예: 만석호_API.py → 만석호(API))
                        boat_name = f.replace("_API.py", "").replace("_api.py", "")
                        display_name = f"{boat_name}(API)"

                        # 모든 항구에서 해당 봇이 없으면 추가 시도
                        for port_name, providers in PORTS.items():
                            # 이미 등록된 경우 스킵
                            if display_name in providers:
                                continue
                            # 같은 선사의 Selenium 버전이 있는 항구에 추가
                            for prov_name in list(providers.keys()):
                                clean_name = self.get_clean_provider_name(prov_name)
                                if clean_name == boat_name and display_name not in providers:
                                    PORTS[port_name][display_name] = rel_path
                                    added_count += 1
                                    break

        # Selenium 봇 스캔 (bots/ 직접 하위, api 제외)
        for subdir in os.listdir(BOTS_DIR):
            subdir_path = os.path.join(BOTS_DIR, subdir)
            if subdir == "api" or not os.path.isdir(subdir_path):
                continue

            for f in os.listdir(subdir_path):
                if f.endswith("_Bot.py"):
                    rel_path = f"{subdir}/{f}"
                    boat_name = f.replace("_Bot.py", "")

                    # 이미 PORTS에 있는지 확인
                    already_exists = False
                    for port_name, providers in PORTS.items():
                        for prov_name, script_path in providers.items():
                            if script_path == rel_path:
                                already_exists = True
                                break
                        if already_exists:
                            break

                    if not already_exists:
                        # 새 봇 발견 - 로그만 출력 (항구 정보 없이 자동 추가 불가)
                        self.log(f"ℹ️ 미등록 봇 발견: {rel_path}")

        # 모든 슬롯 업데이트
        for i in range(len(self.slots)):
            self.update_slot_provider(i)

        if added_count > 0:
            self.log(f"🔄 봇 리스트 새로고침 완료! ({added_count}개 추가)")
        else:
            self.log(f"🔄 봇 리스트 새로고침 완료 (변경 없음)")

    def update_slot_provider(self, slot_idx):
        """Update the provider combobox for a specific slot based on its port selection"""
        slot = self.slots[slot_idx]
        port = slot["port"].get()
        raw_providers = PORTS.get(port, {})

        # 모드에 따른 필터링
        if self.bot_mode == "API":
            # API 모드: api/ 경로 포함된 것만 + ㄱㄴㄷ 정렬
            display_values = sorted([k for k, v in raw_providers.items()
                             if v and v.startswith("api/")], key=lambda x: x.replace("(", "").replace(")", ""))
        else:
            # Selenium 모드: api/ 경로 아닌 것만
            display_values = [k for k, v in raw_providers.items()
                             if v and not v.startswith("api/")]

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

                    # 봇 모드 로드 (API가 기본값)
                    saved_bot_mode = data.get('bot_mode', 'API')
                    self.set_bot_mode(saved_bot_mode)

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
                                
                                # Load provider (원본 이름 우선 매칭)
                                saved_provider = slot_data.get("provider", "")
                                if saved_provider:
                                    current_providers = self.slots[i]["provider"]["values"]
                                    # 1차: 원본 이름 정확히 매칭
                                    if saved_provider in current_providers:
                                        self.slots[i]["provider"].set(saved_provider)
                                    else:
                                        # 2차: clean_name으로 매칭 (하위 호환성)
                                        for prov in current_providers:
                                            clean_prov = self.get_clean_provider_name(prov)
                                            if clean_prov == saved_provider:
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
            provider_name = slot['provider'].get()  # 원본 이름 그대로 저장 (API, 선, 셀 포함)
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
            "early_monitor": self.var_early_monitor.get(),
            "bot_mode": self.bot_mode  # API 또는 Selenium
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
        
        # Get work area size - Windows 작업 영역 크기 가져오기 (작업 표시줄 제외, DPI 스케일링 적용)
        try:
            user32 = ctypes.windll.user32

            # DPI 스케일 팩터 가져오기
            try:
                # SetProcessDPIAware를 호출하여 DPI 인식 모드 활성화
                user32.SetProcessDPIAware()
                # 모니터 DPI 가져오기 (기본 96 DPI 기준)
                hdc = user32.GetDC(0)
                gdi32 = ctypes.windll.gdi32
                dpi = gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX = 88
                user32.ReleaseDC(0, hdc)
                scale_factor = dpi / 96.0  # 96 DPI가 100% 스케일
            except:
                scale_factor = 1.0

            # SPI_GETWORKAREA를 사용하여 작업 영역 가져오기 (물리적 픽셀)
            class RECT(ctypes.Structure):
                _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                            ("right", ctypes.c_long), ("bottom", ctypes.c_long)]
            rect = RECT()
            user32.SystemParametersInfoW(48, 0, ctypes.byref(rect), 0)  # SPI_GETWORKAREA = 48

            # 물리적 픽셀을 논리적 픽셀로 변환 (DPI 스케일링 적용)
            screen_width = int((rect.right - rect.left) / scale_factor)
            screen_height = int((rect.bottom - rect.top) / scale_factor)

            self.log(f"🖥️ DPI 스케일: {int(scale_factor * 100)}% (논리적 해상도: {screen_width} x {screen_height})")
        except:
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight() - 40  # 작업표시줄 대략 40px
            self.log(f"🖥️ 작업 영역 크기 (fallback): {screen_width} x {screen_height}")
        
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
            current_line = ""
            while True:
                char = proc.stdout.read(1)
                if not char:  # EOF
                    break

                if char == '\r':
                    # 캐리지 리턴: 같은 줄에서 덮어쓰기
                    if current_line:
                        print(f"\r{prefix} {current_line}    ", end="", flush=True)
                    current_line = ""
                elif char == '\n':
                    # 줄바꿈: 현재 줄 출력 후 새 줄
                    if current_line:
                        log_entry = f"{prefix} {current_line}"
                        self.bot_logs.append(log_entry)
                        print(f"\r{log_entry}    ", flush=True)
                    current_line = ""
                else:
                    current_line += char

        except Exception as e:
            print(f"[ERROR] 봇 출력 읽기 오류: {e}", flush=True)
        finally:
            try:
                proc.stdout.close()
            except:
                pass

    def reload_ports_from_file(self):
        """런처 파일에서 PORTS 딕셔너리를 다시 로드"""
        global PORTS
        launcher_path = os.path.abspath(__file__)

        try:
            with open(launcher_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # PORTS = { ... } 부분 추출
            match = re.search(r'^PORTS\s*=\s*\{', content, re.MULTILINE)
            if not match:
                return False

            start_idx = match.start()
            # 중괄호 매칭으로 끝 찾기
            brace_count = 0
            end_idx = start_idx
            in_string = False
            string_char = None

            for i, char in enumerate(content[start_idx:], start_idx):
                if not in_string:
                    if char in '"\'':
                        in_string = True
                        string_char = char
                    elif char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_idx = i + 1
                            break
                else:
                    if char == string_char and content[i-1] != '\\':
                        in_string = False

            ports_code = content[start_idx:end_idx]

            # 안전하게 실행
            local_vars = {}
            exec(ports_code, {}, local_vars)
            PORTS = local_vars['PORTS']
            return True

        except Exception as e:
            self.log(f"⚠️ PORTS 리로드 실패: {e}")
            return False

    def open_port_editor(self):
        """항구/선사 편집 창 열기"""
        # 최신 PORTS 로드
        self.reload_ports_from_file()

        editor_win = tk.Toplevel(self.root)
        editor_win.title("✏️ 항구/선사 편집")

        # 창 크기
        win_width = 800
        win_height = 700

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
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # 왼쪽: 항구 목록
        left_frame = ttk.LabelFrame(content_frame, text="항구 목록")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

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
        right_frame = ttk.LabelFrame(content_frame, text="선사 목록")
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

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
        self.deleted_providers = set()  # 삭제된 선사 추적 (port_name::provider_name 형식)

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
        """현재 선택된 항구의 선사 목록 갱신 (수정/삭제된 선사를 맨 위에 표시)"""
        if not self.current_edit_port:
            return

        port_name = self.current_edit_port

        # 선사 리스트박스 업데이트
        self.editor_provider_listbox.delete(0, tk.END)
        if port_name in self.edited_ports:
            # 삭제/수정된 선사와 일반 선사 분리
            deleted_list = []
            modified_list = []
            unmodified_list = []

            for provider, path in self.edited_ports[port_name].items():
                key = f"{port_name}::{provider}"

                if key in self.deleted_providers:
                    deleted_list.append(provider)
                elif key in self.modified_providers:
                    modified_list.append(provider)
                else:
                    unmodified_list.append(provider)

            idx = 0
            # 삭제 예정 선사 먼저 표시 (빨간색 + [삭제] 표시)
            for provider in deleted_list:
                self.editor_provider_listbox.insert(tk.END, f"[삭제] {provider}")
                self.editor_provider_listbox.itemconfig(idx, fg='red')
                idx += 1

            # 수정된 선사 표시 (주황색)
            for provider in modified_list:
                self.editor_provider_listbox.insert(tk.END, provider)
                self.editor_provider_listbox.itemconfig(idx, fg='orange')
                idx += 1

            # 일반 선사 표시
            for provider in unmodified_list:
                self.editor_provider_listbox.insert(tk.END, provider)
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
            # 삭제된 선사 추적 (실제 삭제는 저장 시 수행)
            key = f"{self.current_edit_port}::{provider_name}"
            self.deleted_providers.add(key)
            self.refresh_provider_listbox()
            self.log(f"🗑️ 선사 삭제 예정: {provider_name}")

    def refresh_port_listbox(self):
        """항구 리스트박스 새로고침"""
        self.editor_port_listbox.delete(0, tk.END)
        idx = 0
        for port in self.edited_ports.keys():
            self.editor_port_listbox.insert(tk.END, f"{port} ({len(self.edited_ports[port])}개)")
            # 해당 항구에 수정/삭제된 선사가 있으면 빨간색 표시
            has_modified = any(key.startswith(f"{port}::") for key in self.modified_providers)
            has_deleted = any(key.startswith(f"{port}::") for key in self.deleted_providers)
            if has_modified or has_deleted:
                self.editor_port_listbox.itemconfig(idx, fg='red')
            idx += 1

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

            # 삭제 예정 선사 실제 삭제
            for key in self.deleted_providers:
                port, provider = key.split("::", 1)
                if port in self.edited_ports and provider in self.edited_ports[port]:
                    del self.edited_ports[port][provider]

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

                # PORTS 다시 로드하여 즉시 반영
                self.reload_ports_from_file()

                # 모든 슬롯의 선사 콤보박스 업데이트
                for i in range(len(self.slots)):
                    self.update_slot_provider(i)

                self.log("✅ 항구/선사 정보가 저장되었습니다.")
                messagebox.showinfo("저장 완료",
                    "항구/선사 정보가 저장되었습니다.\n\n변경사항이 즉시 반영되었습니다.",
                    parent=parent)
                parent.destroy()
            else:
                messagebox.showerror("오류", "PORTS 데이터를 찾을 수 없습니다.", parent=parent)

        except Exception as e:
            self.log(f"❌ 저장 오류: {e}")
            messagebox.showerror("오류", f"저장 중 오류가 발생했습니다:\n{e}", parent=parent)

    def get_mapping_info_from_bot(self, script_path):
        """봇 파일에서 ID_MAPPING 정보 추출"""
        if not script_path or not os.path.exists(script_path):
            return None

        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # ID_MAPPING 딕셔너리 찾기
            import re
            # 패턴 1: ID_MAPPING = { ... } (월별 base_id)
            pattern1 = r'ID_MAPPING\s*=\s*\{([^}]+)\}'
            match = re.search(pattern1, content, re.DOTALL)

            if match:
                mapping_str = match.group(1)
                # 월 번호 추출 (키가 숫자인 경우)
                month_pattern = r'(\d+)\s*:'
                months = re.findall(month_pattern, mapping_str)
                if months:
                    return sorted([int(m) for m in months])

            # 패턴 2: (월, 일): schedule_no 형식
            pattern2 = r'\((\d+),\s*\d+\)\s*:'
            matches = re.findall(pattern2, content)
            if matches:
                months = sorted(set([int(m) for m in matches]))
                return months

            return None
        except Exception:
            return None

    def update_mapping_button_state(self, selected_provider):
        """검색된 선사의 매핑 여부에 따라 버튼 상태 변경"""
        self.current_mapping_info = None  # 저장용

        if not selected_provider:
            self.btn_mapping_info.configure(bootstyle="secondary", text="📅 선상24 맵핑")
            return

        port, provider_name, script_path = selected_provider

        # 선상24 봇만 매핑 정보 확인
        if "선상24" not in script_path:
            self.btn_mapping_info.configure(bootstyle="secondary", text="📅 선상24 맵핑")
            return

        # 봇 파일에서 매핑 정보 추출
        full_path = os.path.join(BOTS_DIR, script_path)
        mapping_months = self.get_mapping_info_from_bot(full_path)

        if mapping_months:
            self.current_mapping_info = {
                'provider': self.get_clean_provider_name(provider_name),
                'months': mapping_months,
                'path': full_path
            }
            self.btn_mapping_info.configure(bootstyle="success", text=f"📅 맵핑 ({len(mapping_months)}개월)")
        else:
            self.btn_mapping_info.configure(bootstyle="secondary", text="📅 선상24 맵핑")

    def show_mapping_info(self):
        """매핑 정보 표시"""
        if not hasattr(self, 'current_mapping_info') or not self.current_mapping_info:
            messagebox.showinfo("매핑 정보", "선상24 선사를 검색하면 매핑 정보를 확인할 수 있습니다.")
            return

        info = self.current_mapping_info
        provider = info['provider']
        months = info['months']

        # 월별 통계 문자열 생성
        month_names = [f"{m}월" for m in months]

        # 2줄로 나눔 (1-6월, 7-12월)
        line1 = [f"{m}월" for m in months if m <= 6]
        line2 = [f"{m}월" for m in months if m > 6]

        msg = f"🚢 {provider}\n\n"
        msg += f"📅 선상24 맵핑된 월: {len(months)}개월\n\n"
        if line1:
            msg += f"  {', '.join(line1)}\n"
        if line2:
            msg += f"  {', '.join(line2)}\n"

        # 빠진 월 표시
        all_months = set(range(1, 13))
        missing = sorted(all_months - set(months))
        if missing:
            msg += f"\n⚠️ 미등록: {', '.join([f'{m}월' for m in missing])}"

        messagebox.showinfo("매핑 정보", msg)

if __name__ == "__main__":
    if not os.path.exists(CONFIG_DIR): os.makedirs(CONFIG_DIR)
    root = ttk.Window(themename="darkly")
    app = FishingLauncher(root)
    root.mainloop()
