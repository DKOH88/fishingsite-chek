import os
import time
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import email.utils
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

class BaseFishingBot:
    def __init__(self, config):
        self.config = config
        self.driver = None
        self.log_callback = print  # Default to print, can be overridden by GUI
        self.is_running = True
        
        # Setup File Logging
        self.log_file = None
        try:
            log_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'Log')
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            # Filename based on config info if available, else timestamp
            target_date = config.get('target_date', 'UnknownDate')
            # Filename generation
            now = datetime.now()
            time_str = now.strftime("%Y_%m월%d일_%H시%M분%S초")
            
            p_provider = config.get('provider', 'Unknown')
            
            t_date = config.get('target_date', '00000000')
            if len(t_date) == 8 and t_date.isdigit():
                t_date_fmt = f"{t_date[:4]}_{t_date[4:6]}_{t_date[6:]}"
            else:
                t_date_fmt = t_date
                
            self.log_file = os.path.join(log_dir, f"{time_str}_선상24_{p_provider}_{t_date_fmt}_.txt")
            
            # Write header
            pretty_timestamp = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(f"=== SunSang24 Bot Log Started: {pretty_timestamp} ===\n")
                
                # Formatted Header
                p_port = config.get('port', 'Unknown')
                p_provider = config.get('provider', 'Unknown')
                p_date = config.get('target_date', '')
                if len(p_date) == 8 and p_date.isdigit():
                    p_date = f"{p_date[:4]}-{p_date[4:6]}-{p_date[6:]}"

                p_time = config.get('target_time', '')
                p_name = config.get('user_name', '')
                p_phone = config.get('user_phone', '')
                
                f.write(f"항구: {p_port}\n")
                f.write(f"선사: {p_provider}\n")
                f.write(f"예약날짜: {p_date}\n")
                f.write(f"예약시간: {p_time}\n")
                f.write(f"예약자: {p_name}\n")
                f.write(f"전화번호: {p_phone}\n")
                f.write("-" * 30 + "\n\n")
        except Exception as e:
            print(f"Failed to setup log file: {e}")

    def log(self, msg):
        """Standard log format"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-4]
        formatted_msg = f"[{timestamp}] {msg}"
        
        # Console
        if self.log_callback:
            self.log_callback(formatted_msg)
            
        # File
        if self.log_file:
            try:
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(formatted_msg + "\n")
            except:
                pass

    def setup_driver(self):
        """Initialize Chrome Driver with stealth settings"""
        self.log("🚗 크롬 드라이버를 설정하고 있습니다...")
        chrome_options = Options()
        
        # Check if window position/size is specified in config
        window_x = self.config.get('window_x')
        window_y = self.config.get('window_y')
        window_width = self.config.get('window_width')
        window_height = self.config.get('window_height')
        
        # Only maximize if no grid layout is specified
        if window_x is None:
            chrome_options.add_argument("--start-maximized")
        
        chrome_options.add_experimental_option("detach", True)
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        
        # Performance options
        chrome_options.page_load_strategy = 'eager'

        service = Service() # Assumes chromedriver in PATH or managed automatically
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Save Chrome browser PID for later cleanup
        try:
            import psutil
            # Get ChromeDriver PID and find its child Chrome process
            driver_pid = self.driver.service.process.pid
            driver_proc = psutil.Process(driver_pid)
            chrome_pids = []
            for child in driver_proc.children(recursive=True):
                if 'chrome' in child.name().lower():
                    chrome_pids.append(child.pid)
            
            # Save PIDs to temp file
            pid_file = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'bot_chrome_pids.txt')
            os.makedirs(os.path.dirname(pid_file), exist_ok=True)
            with open(pid_file, 'a', encoding='utf-8') as f:
                for pid in chrome_pids:
                    f.write(f"{pid}\n")
            self.log(f"📝 Chrome PID 저장됨: {chrome_pids}")
        except Exception as e:
            self.log(f"⚠️ Chrome PID 저장 실패 (무시됨): {e}")
        
        # Apply window position and size if specified (grid layout)
        if window_x is not None and window_y is not None:
            self.driver.set_window_position(window_x, window_y)
            self.log(f"📍 창 위치 설정: ({window_x}, {window_y})")
        if window_width is not None and window_height is not None:
            self.driver.set_window_size(window_width, window_height)
            self.log(f"📐 창 크기 설정: {window_width} x {window_height}")
        
        # Bypass webdriver detection
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        })

    def get_server_time(self, url):
        """Fetch server time from headers"""
        try:
            resp = requests.head(url, timeout=3, verify=False)
            date_str = resp.headers.get('Date')
            if date_str:
                gmt = email.utils.parsedate_to_datetime(date_str)
                kst = gmt + timedelta(hours=9)
                return kst.replace(tzinfo=None)
        except Exception as e:
            self.log(f"⚠️ 서버 시간 확인 실패: {e}")
        return datetime.now()

    def wait_until_target_time(self, target_time_str):
        """Precision wait logic"""
        now = datetime.now()
        # Support both HH:MM:SS and HH:MM:SS.f
        try:
            target_dt = datetime.strptime(f"{now.year}-{now.month}-{now.day} {target_time_str}", "%Y-%m-%d %H:%M:%S.%f")
        except ValueError:
            target_dt = datetime.strptime(f"{now.year}-{now.month}-{now.day} {target_time_str}", "%Y-%m-%d %H:%M:%S")
        
        # Adjust target date if time already passed
        if target_dt < now:
             target_dt = target_dt + timedelta(days=1)
             
        self.log(f"⏰ 목표 시간 대기 중: {target_dt} (현재 시간 기준)")
        
        while self.is_running:
            now = datetime.now()
            diff = (target_dt - now).total_seconds()
            
            if diff <= 0:
                print()  # 줄바꿈
                self.log("🚀 예약 오픈 시간입니다! 작업을 시작합니다!")
                break
            
            # 남은 시간 계산
            mins = int(diff // 60)
            secs = int(diff % 60)
            
            # 한 줄에서 실시간 업데이트
            print(f"\r⏳ 남은 시간: {mins:02d}분 {secs:02d}초", end="", flush=True)
            
            if diff > 1:
                time.sleep(0.5)
            else:
                time.sleep(0.01)

    def run(self):
        """Main execution flow (Override this)"""
        raise NotImplementedError("Each provider bot must implement 'run' method")

    def stop(self):
        self.is_running = False
        if self.driver:
            self.driver.quit()
