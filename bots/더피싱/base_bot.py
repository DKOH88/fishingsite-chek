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
import os
# 🚀 [Speed Optimization] Force Disable Proxy
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''
os.environ['http_proxy'] = ''
os.environ['https_proxy'] = ''
os.environ['NO_PROXY'] = '*'


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
            provider_name = 'Bot' # Can't get provider easily here without passing it? 
            # Filename generation
            now = datetime.now()
            time_str = now.strftime("%Y_%m월%d일_%H시%M분%S초")
            
            p_provider = config.get('provider', 'Unknown')
            
            t_date = config.get('target_date', '00000000')
            if len(t_date) == 8 and t_date.isdigit():
                t_date_fmt = f"{t_date[:4]}_{t_date[4:6]}_{t_date[6:]}"
            else:
                t_date_fmt = t_date
                
            self.log_file = os.path.join(log_dir, f"{time_str}_더피싱_{p_provider}_{t_date_fmt}_.txt")
            
            # Write header
            pretty_timestamp = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(f"=== Bot Log Started: {pretty_timestamp} ===\n")
                
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
        
        # 1. Print to Console (so user sees it in black window)
        if self.log_callback:
            self.log_callback(formatted_msg)
            
        # 2. Write to File
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
        chrome_options.add_argument("--no-proxy-server") # 🚀 [Speed] Force direct connection
        
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
            # 🚀 Use Session with trust_env=False to speed up request (Bypass Proxy Check)
            with requests.Session() as s:
                s.trust_env = False
                resp = s.head(url, timeout=3, verify=False)
            
            date_str = resp.headers.get('Date')
            if date_str:
                gmt = email.utils.parsedate_to_datetime(date_str)
                kst = gmt + timedelta(hours=9)
                return kst.replace(tzinfo=None)
        except Exception as e:
            self.log(f"⚠️ 서버 시간 확인 실패: {e}")
        return datetime.now()

    def wait_until_target_time(self, target_time_str):
        """Precision wait logic with early open monitoring"""
        now = datetime.now()
        # Support both HH:MM:SS and HH:MM:SS.f
        try:
            target_dt = datetime.strptime(f"{now.year}-{now.month}-{now.day} {target_time_str}", "%Y-%m-%d %H:%M:%S.%f")
        except ValueError:
            target_dt = datetime.strptime(f"{now.year}-{now.month}-{now.day} {target_time_str}", "%Y-%m-%d %H:%M:%S")
        
        # Adjust target date if time already passed
        if target_dt < now:
             target_dt = target_dt + timedelta(days=1)
        
        # 🔍 조기오픈 감시 설정 확인
        early_monitor = self.config.get('early_monitor', False)
        early_monitor_start = target_dt - timedelta(minutes=5)  # 5분 전부터 감시
        
        if early_monitor:
            self.log(f"🔍 조기오픈 감시 활성화: {early_monitor_start.strftime('%H:%M:%S')}부터 10초마다 페이지 확인")
             
        self.log(f"⏰ 목표 시간 대기 중: {target_dt} (현재 시간 기준)")
        
        last_display_second = -1
        last_early_check = None  # 마지막 조기오픈 체크 시간
        
        while self.is_running:
            now = datetime.now()
            diff = (target_dt - now).total_seconds()
            
            if diff <= 0:
                print()  # New line after countdown
                self.log("🚀 예약 오픈 시간입니다! 작업을 시작합니다!")
                break
            
            # 🔍 조기오픈 감시 로직 (5분 전부터 10초마다)
            if early_monitor and now >= early_monitor_start:
                should_check = False
                if last_early_check is None:
                    should_check = True
                elif (now - last_early_check).total_seconds() >= 10:
                    should_check = True
                
                if should_check:
                    last_early_check = now
                    try:
                        # 페이지 새로고침 후 소스 확인
                        self.driver.refresh()
                        time.sleep(0.5)  # 잠시 대기
                        page_source = self.driver.page_source
                        
                        # 예약 페이지 감지 키워드
                        open_keywords = ['STEP 01', '예약1단계', '배 선택', 'ps_selis', 'PS_N_UID']
                        closed_keywords = ['준비 중', '오픈 예정', '예약 불가', '접수 마감', '없는', '권한', '잘못']
                        
                        # 페이지 오픈 여부 판단
                        is_open = any(kw in page_source for kw in open_keywords)
                        is_closed = any(kw in page_source for kw in closed_keywords)
                        
                        if is_open and not is_closed:
                            print()  # New line
                            self.log("🎉🎉🎉 조기 오픈 감지! 예약 페이지가 열렸습니다!")
                            self.log(f"   (예정: {target_dt.strftime('%H:%M:%S')}, 실제: {now.strftime('%H:%M:%S')}, {diff:.0f}초 일찍 오픈)")
                            break  # 즉시 예약 로직 시작
                        else:
                            self.log(f"🔍 조기오픈 체크: 아직 미오픈 (남은시간: {int(diff)}초)")
                    except Exception as e:
                        self.log(f"⚠️ 조기오픈 체크 오류: {e}")
            
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