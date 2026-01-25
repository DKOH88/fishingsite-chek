import os
import time
import requests
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

    def log(self, msg):
        """Standard log format"""
        if self.log_callback:
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-4]
            self.log_callback(f"[{timestamp}] {msg}")

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
            resp = requests.head(url, timeout=3)
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
        target_dt = datetime.strptime(f"{now.year}-{now.month}-{now.day} {target_time_str}", "%Y-%m-%d %H:%M:%S")
        
        # Adjust target date if time already passed
        if target_dt < now:
             target_dt = target_dt + timedelta(days=1)
             
        self.log(f"⏰ 목표 시간 대기 중: {target_dt} (현재 시간 기준)")
        
        last_display_second = -1
        while self.is_running:
            now = datetime.now()
            diff = (target_dt - now).total_seconds()
            
            if diff <= 0:
                print()  # New line after countdown
                self.log("🚀 예약 오픈 시간입니다! 작업을 시작합니다!")
                break
            
            # Display countdown on same line, updating every second
            current_second = int(diff)
            if current_second != last_display_second:
                minutes = int(diff // 60)
                seconds = int(diff % 60)
                if minutes > 0:
                    print(f"\r⏳ 남은 시간: {minutes}분 {seconds}초    ", end="", flush=True)
                else:
                    print(f"\r⏳ 남은 시간: {diff:.1f}초    ", end="", flush=True)
                last_display_second = current_second
            
            # Sleep interval based on remaining time
            if diff > 10:
                time.sleep(0.1)
            elif diff > 1:
                time.sleep(0.01)
            else:
                time.sleep(0.01)

    def run(self):
        """Main execution flow (Override this)"""
        raise NotImplementedError("Each provider bot must implement 'run' method")

    def stop(self):
        self.is_running = False
        if self.driver:
            self.driver.quit()
