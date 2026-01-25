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
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_experimental_option("detach", True)
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        
        # Performance options
        chrome_options.page_load_strategy = 'eager'

        service = Service() # Assumes chromedriver in PATH or managed automatically
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        
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
