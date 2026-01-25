"""
🚀 업비트 상장감지봇 GUI v1.1
- 업비트 공지사항 API 실시간 모니터링
- 신규 상장 공지 감지 시 텔레그램 알림
- GUI: 시작/중지, Test모드, 트레이 숨김 기능
"""

import requests
import time
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext
from datetime import datetime
import ctypes
import sys
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import json
import os

# 트레이 아이콘 지원
try:
    import pystray
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False
    print("⚠️ pystray/pillow 미설치 - 트레이 기능 비활성화")

# ============================================
# 📁 설정
# ============================================
TELEGRAM_BOT_TOKEN = "7417808547:AAFAojmo5Dq5BsjK9udJGVWRhC05OhDs-JY"
TELEGRAM_CHAT_ID = "393163178"

UPBIT_NOTICE_API = "https://api-manager.upbit.com/api/v1/notices"
API_PARAMS = {
    "page": 1,
    "per_page": 20,
    # "thread_name": "general"  <-- 모든 카테고리(NFT, 이벤트 등) 감지를 위해 제거
}

ALERT_KEYWORDS = [
    "신규 거래지원 안내 (KRW",
]

POLL_INTERVAL = 1.0
CONFIG_FILE = "upbit_bot_config.json"


# ============================================
# 📡 텔레그램 알림
# ============================================
def send_telegram(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        resp = requests.post(url, json=payload, timeout=5)
        return resp.status_code == 200
    except:
        return False


# ============================================
# 🪟 콘솔 창 숨기기/보이기 (Windows)
# ============================================
def get_console_window():
    """콘솔 창 핸들 가져오기"""
    return ctypes.windll.kernel32.GetConsoleWindow()

def hide_console():
    """콘솔 창 숨기기"""
    hwnd = get_console_window()
    if hwnd:
        # SW_HIDE = 0
        ctypes.windll.user32.ShowWindow(hwnd, 0)
        # 추가: 콘솔 완전히 분리
        try:
            ctypes.windll.kernel32.FreeConsole()
        except:
            pass

def show_console():
    """콘솔 창 보이기"""
    # 콘솔 재할당
    try:
        ctypes.windll.kernel32.AllocConsole()
    except:
        pass
    hwnd = get_console_window()
    if hwnd:
        ctypes.windll.user32.ShowWindow(hwnd, 5)  # SW_SHOW


# ============================================
# 🖥️ GUI 앱
# ============================================
class UpbitMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🚀 업비트 상장감지봇 v1.1")
        
        w, h = 520, 420
        ws = root.winfo_screenwidth()
        hs = root.winfo_screenheight()
        x = (ws/2) - (w/2)
        y = (hs/2) - (h/2)
        root.geometry(f'{w}x{h}+{int(x)}+{int(y)}')
        
        self.is_running = False
        self.monitor_thread = None
        self.session = None
        self.seen_ids = set()
        
        # 트레이 아이콘
        self.tray_icon = None
        self.is_hidden = False
        
        self.is_hidden = False
        
        self.create_widgets()
        self.load_config()  # 설정 불러오기
        
        # 창 닫기 이벤트 처리
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 설정 프레임
        config_frame = ttk.LabelFrame(main_frame, text="⚙️ 설정", padding="5")
        config_frame.pack(fill=tk.X, pady=5)
        
        row1 = ttk.Frame(config_frame)
        row1.pack(fill=tk.X, pady=2)
        
        ttk.Label(row1, text="폴링 간격:").pack(side=tk.LEFT, padx=5)
        self.entry_interval = ttk.Entry(row1, width=5)
        self.entry_interval.insert(0, "1.0")
        self.entry_interval.pack(side=tk.LEFT, padx=2)
        ttk.Label(row1, text="초").pack(side=tk.LEFT)
        
        ttk.Label(row1, text="    ").pack(side=tk.LEFT)
        self.var_test_mode = tk.BooleanVar(value=False)
        ttk.Checkbutton(row1, text="🧪 Test모드", 
                        variable=self.var_test_mode).pack(side=tk.LEFT, padx=5)
        
        row2 = ttk.Frame(config_frame)
        row2.pack(fill=tk.X, pady=2)
        
        ttk.Label(row2, text="감지 키워드:").pack(side=tk.LEFT, padx=5)
        ttk.Label(row2, text=", ".join(ALERT_KEYWORDS), foreground="blue").pack(side=tk.LEFT)
        
        # 버튼 프레임
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        self.btn_start = ttk.Button(btn_frame, text="🚀 시작", command=self.start_monitor, width=10)
        self.btn_start.pack(side=tk.LEFT, padx=5)
        
        self.btn_stop = ttk.Button(btn_frame, text="🛑 중지", command=self.stop_monitor, state="disabled", width=10)
        self.btn_stop.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(btn_frame, text="📡 텔레그램", command=self.test_telegram, width=10).pack(side=tk.LEFT, padx=5)
        
        # 숨김 버튼
        if TRAY_AVAILABLE:
            ttk.Button(btn_frame, text="👁️ 숨김", command=self.hide_to_tray, width=8).pack(side=tk.RIGHT, padx=5)
        
        # 로그 프레임
        log_frame = ttk.LabelFrame(main_frame, text="📝 로그", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.log_area = scrolledtext.ScrolledText(log_frame, height=12, state='disabled', 
                                                   font=("Consolas", 9))
        self.log_area.pack(fill=tk.BOTH, expand=True)
        
        # 상태바
        self.status_var = tk.StringVar(value="⏹️ 대기 중")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(fill=tk.X, pady=2)
        
        self.log("=" * 40)
        self.log("🚀 업비트 상장감지봇 v1.1")
        self.log("=" * 40)
        if TRAY_AVAILABLE:
            self.log("💡 [숨김] 버튼으로 트레이로 최소화 가능")
    
    def log(self, msg):
        def _update():
            self.log_area.config(state='normal')
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.log_area.insert(tk.END, f"[{timestamp}] {msg}\n")
            self.log_area.see(tk.END)
            self.log_area.config(state='disabled')
        self.root.after(0, _update)
    
    def test_telegram(self):
        msg = f"✅ 업비트 상장감지봇 테스트 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})"
        if send_telegram(msg):
            self.log("✅ 텔레그램 연결 성공!")
        else:
            self.log("❌ 텔레그램 연결 실패")
    
    # ========== 트레이 기능 ==========
    def create_tray_icon_image(self):
        """트레이 아이콘 이미지 생성 (로켓 모양)"""
        img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # 파란색 원 배경 (Blue)
        draw.ellipse([8, 8, 56, 56], fill=(33, 150, 243))
        # U 글자
        draw.text((22, 16), "U", fill="white")
        return img
    
    def hide_to_tray(self):
        """트레이로 숨기기"""
        if not TRAY_AVAILABLE:
            self.log("⚠️ 트레이 기능 사용 불가")
            return
        
        self.is_hidden = True
        self.root.withdraw()  # GUI 숨기기
        hide_console()  # 콘솔 숨기기
        
        # 트레이 아이콘 생성
        icon_image = self.create_tray_icon_image()
        
        menu = pystray.Menu(
            pystray.MenuItem("🖥️ 창 열기", self.show_from_tray, default=True),
            pystray.MenuItem("🛑 종료", self.exit_app)
        )
        
        self.tray_icon = pystray.Icon(
            "upbit_monitor",
            icon_image,
            "업비트 상장감지봇",
            menu
        )
        
        # 트레이 아이콘 실행 (별도 스레드)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()
    
    def show_from_tray(self, icon=None, item=None):
        """트레이에서 복원"""
        self.is_hidden = False
        
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None
        
        show_console()  # 콘솔 보이기
        self.root.after(0, self.root.deiconify)  # GUI 보이기
        self.root.after(100, self.root.lift)  # 최상위로
    
    def exit_app(self, icon=None, item=None):
        """앱 종료"""
        self.is_running = False
        
        if self.tray_icon:
            self.tray_icon.stop()
        
        self.root.after(0, self.root.destroy)
    
    def on_close(self):
        """창 닫기 이벤트"""
        self.save_config() # 설정 저장
        if TRAY_AVAILABLE:
            self.hide_to_tray()
        else:
            self.exit_app()
    
    # ========== 설정 저장/로드 ==========
    def load_config(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    interval = config.get('interval', "1.0")
                    self.entry_interval.delete(0, tk.END)
                    self.entry_interval.insert(0, str(interval))
                    self.log(f"⚙️ 설정 로드 완료 (간격: {interval}초)")
        except Exception as e:
            self.log(f"⚠️ 설정 로드 실패: {e}")

    def save_config(self):
        try:
            config = {
                'interval': self.entry_interval.get()
            }
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            print(f"설정 저장 실패: {e}")
    
    # ========== 모니터링 ==========
    def start_monitor(self):
        if self.is_running:
            return
        
        self.is_running = True
        self.seen_ids = set()
        self.seen_ids = set()
        self.create_session() # [Refactor] 세션 생성 분리
        
    def create_session(self):
        """세션 생성 및 재시도 설정"""
        self.session = requests.Session()
        
        # 재시도 전략 설정 (총 3회, 0.5초 간격, 특정 에러 시)
        retries = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Referer": "https://www.upbit.com/"
        })
        
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.status_var.set("🟢 모니터링 중...")
        
        # 폴링 간격 확인
        try:
            current_interval = float(self.entry_interval.get())
        except:
            current_interval = POLL_INTERVAL

        self.log(f"🚀 모니터링 시작! (간격: {current_interval}초)")
        send_telegram(f"🟢 업비트 상장감지봇 시작 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) \n   └ ⏱️ 간격: {current_interval}초")
        
        self.monitor_thread = threading.Thread(target=self.monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitor(self):
        self.is_running = False
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")
        self.status_var.set("⏹️ 대기 중")
        self.log("🛑 모니터링 중지")
    
    def monitor_loop(self):
        first_run = True
        check_count = 0
        
        try:
            poll_interval = float(self.entry_interval.get())
        except:
            poll_interval = POLL_INTERVAL
        
        while self.is_running:
            # [NEW] 쉬는 시간 (PM 10:00 ~ AM 08:00) 체크
            now_hour = datetime.now().hour
            if now_hour >= 22 or now_hour < 8:
                self.log("🌙 쉬는 시간 (22:00~08:00) 진입... 대기 중 zZZ")
                self.root.after(0, lambda: self.status_var.set("😴 수면 모드 (22시~08시)"))
                
                while self.is_running:
                    # 매분 시간 체크
                    now_hour = datetime.now().hour
                    if not (now_hour >= 22 or now_hour < 8):
                        self.log("☀️ 기상! 모니터링을 재개합니다.")
                        self.root.after(0, lambda: self.status_var.set("🟢 모니터링 중..."))
                        break
                    time.sleep(60) # 1분 대기
                continue # 루프 재시작

            try:
                resp = self.session.get(UPBIT_NOTICE_API, params=API_PARAMS, timeout=5)
                
                if resp.status_code == 200:
                    data = resp.json()
                    notices = data.get("data", {}).get("list", [])
                    
                    for notice in notices:
                        notice_id = notice.get("id")
                        title = notice.get("title", "")
                        
                        if notice_id in self.seen_ids:
                            continue
                        
                        self.seen_ids.add(notice_id)
                        
                        if first_run:
                            continue
                        
                        is_match = any(kw in title for kw in ALERT_KEYWORDS)
                        test_mode = self.var_test_mode.get()
                        
                        if test_mode or is_match:
                            icon = "🚨" if is_match else "📢"
                            self.log(f"{icon} 상장 공지: {title[:40]}...")
                            
                            message = f"""🚀 <b>업비트 상장 공지!</b>

📌 {title}

🕐 감지시간: {datetime.now().strftime('%H:%M:%S')}

🔗 <a href="https://www.upbit.com/service_center/notice">공지사항 바로가기</a>"""
                            
                            if send_telegram(message):
                                self.log("   ✅ 텔레그램 전송!")
                            else:
                                self.log("   ❌ 전송 실패")
                        else:
                            self.log(f"📝 새 공지: {title[:40]}...")
                    
                    if first_run:
                        first_run = False
                        self.log(f"📋 기존 공지 {len(self.seen_ids)}개 등록")
                        self.log("🔍 새 공지 대기 중...")
                
                check_count += 1
                if check_count % 60 == 0:
                    self.root.after(0, lambda: self.status_var.set(
                        f"🟢 모니터링 중... ({len(self.seen_ids)}개 추적)"
                    ))
                
                time.sleep(poll_interval)
                
            except Exception as e:
                self.log(f"⚠️ 연결 오류 발생: {e}")
                self.log("🔄 세션 재연결 시도 중...")
                time.sleep(2)
                
                # [Fix] 연결 끊김 시 세션 재생성 (RemoteDisconnected 해결)
                try:
                    self.session.close()
                except: pass
                self.create_session()
                time.sleep(1)


# ============================================
# 🚀 실행
# ============================================
if __name__ == "__main__":
    root = tk.Tk()
    app = UpbitMonitorApp(root)
    root.mainloop()
