import os
import sys
import time
import requests
import urllib3
import threading
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import email.utils
from datetime import datetime, timedelta

# Windows 콘솔 한글/이모지 출력 설정
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoAlertPresentException, NoSuchElementException, StaleElementReferenceException,
    TimeoutException, WebDriverException, UnexpectedAlertPresentException
)

# [Speed Optimization] Force Disable Proxy
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''
os.environ['http_proxy'] = ''
os.environ['https_proxy'] = ''
os.environ['NO_PROXY'] = '*'


class BaseFishingBot:
    """
    더피싱 예약 봇 공통 베이스 클래스.

    각 선사 봇은 이 클래스를 상속받고 설정값만 오버라이드하면 됩니다.

    필수 오버라이드:
        SITE_URL        - 선사 도메인 (예: "teammansu.kr")
        PA_N_UID        - 선사 고유 ID (예: "2829")

    선택 오버라이드:
        STEPS           - 예약 완료 단계 (2 또는 3, 기본값: 2)
        HAS_SEAT_SELECTION - 자리 선택 여부 (기본값: False)
        SEAT_PRIORITY   - 자리 우선순위 리스트 (기본값: [])
        TARGET_KEYWORDS - 낚시 종류 검색 키워드 (기본값: 일반 키워드)
        URL_PATH        - URL 경로 (기본값: STEPS에 따라 자동 결정)
        API_VERSION     - API 버전 (기본값: "v5.2_seat1")
        TAB_SELECTOR    - 탭 CSS 셀렉터 (기본값: STEPS에 따라 자동)
        PROVIDER_NAME   - 로그에 표시할 선사 이름
        SLEEP_INTERVAL  - 클릭 간 대기 시간 (기본값: 0.01)
        MAX_SUBMIT_RETRIES - 제출 최대 재시도 (기본값: 2)
        CLICK_STRATEGY  - 클릭 전략 ("id_first" 또는 "xpath_first", 기본값: 자동)
        USE_HTTPS       - HTTPS 사용 여부 (기본값: False → http)
        MAX_BACKGROUND_BROWSERS - 백그라운드 브라우저 최대 개수 (기본값: 3)
        MAX_OUTER_RETRIES - 외부 루프 최대 재시도 횟수 (기본값: 50)
    """

    # ============================================================
    # 🔧 선사별 설정값 (각 봇에서 오버라이드)
    # ============================================================
    SITE_URL = ""                   # 필수: 선사 도메인
    PA_N_UID = ""                   # 필수: 선사 고유 ID
    STEPS = 2                       # 2-step 또는 3-step
    HAS_SEAT_SELECTION = False      # 자리 선택 여부
    SEAT_PRIORITY = []              # 자리 우선순위 (예: ['1','15','2','9'])
    TARGET_KEYWORDS = ['갑오징어', '쭈꾸미', '쭈갑', '쭈꾸미&갑오징어']
    URL_PATH = ""                   # 빈값이면 자동 결정
    API_VERSION = "v5.2_seat1"      # reservation_boat 버전
    TAB_SELECTOR = ""               # 빈값이면 STEPS에 따라 자동
    PROVIDER_NAME = ""              # 빈값이면 클래스명 사용
    SLEEP_INTERVAL = 0.01           # 클릭/입력 간 대기 시간
    MAX_SUBMIT_RETRIES = 2          # 제출 최대 재시도
    CLICK_STRATEGY = "auto"         # "id_first", "xpath_first", "auto"
    USE_HTTPS = False               # HTTPS 사용 여부
    MAX_BACKGROUND_BROWSERS = 3     # 백그라운드 브라우저 최대 개수
    MAX_OUTER_RETRIES = 3           # 외부 루프 최대 재시도

    # ============================================================
    # 초기화
    # ============================================================
    def __init__(self, config):
        self.config = config
        self.driver = None
        self.log_callback = print
        self.is_running = True
        self.success_event = threading.Event()
        self.browser_threads = []
        self.browsers = []
        self._monitor_counter = {}

        # URL 자동 구성
        self._build_url_components()

        # 로그 파일 설정
        self.log_file = None
        self._setup_log_file()

    def _build_url_components(self):
        """URL 경로 및 탭 셀렉터 자동 결정"""
        # URL 경로: 명시적 설정이 없으면 STEPS와 HAS_SEAT_SELECTION 기반으로 결정
        if not self.URL_PATH:
            if self.HAS_SEAT_SELECTION or "seat" in self.API_VERSION:
                self.URL_PATH = "popu2.step1.php"
            else:
                self.URL_PATH = "popup.step1.php"

        # 탭 셀렉터: 명시적 설정이 없으면 STEPS 기반으로 결정
        if not self.TAB_SELECTOR:
            if self.STEPS == 3:
                self.TAB_SELECTOR = ".top_tab_menu li, .top_tab_menu2 li"
            else:
                self.TAB_SELECTOR = ".top_tab_menu2 li"

        # 성공 URL 키워드
        if self.STEPS == 3:
            self.SUCCESS_URL_KEYWORD = "step3.php"
            self.SUCCESS_TAB_INDEX = 2  # 3번째 탭 (0-indexed)
        else:
            self.SUCCESS_URL_KEYWORD = "step2.php"
            self.SUCCESS_TAB_INDEX = 1  # 2번째 탭 (0-indexed)

        # 클릭 전략 자동 결정
        if self.CLICK_STRATEGY == "auto":
            # id_first: PS1 ID로 매핑하는 방식 (팀만수호, 만석호, 조커호, 예린호 등)
            # xpath_first: XPath로 라디오 찾는 방식 (장현호, 청남호, 샤크호 등)
            if self.HAS_SEAT_SELECTION:
                self.CLICK_STRATEGY = "id_first"
            else:
                self.CLICK_STRATEGY = "xpath_first"

        # 프로토콜
        self._protocol = "https" if self.USE_HTTPS else "http"

    def _get_provider_name(self):
        """선사 이름 반환"""
        if self.PROVIDER_NAME:
            return self.PROVIDER_NAME
        return self.__class__.__name__.replace("Bot", "")

    def _build_reservation_url(self, target_date):
        """예약 URL 생성"""
        base_url = f"{self._protocol}://{self.SITE_URL}/_core/module/reservation_boat_{self.API_VERSION}/{self.URL_PATH}"
        return base_url, f"{base_url}?date={target_date}&PA_N_UID={self.PA_N_UID}"

    # ============================================================
    # 로그 시스템
    # ============================================================
    def _setup_log_file(self):
        """로그 파일 초기화"""
        try:
            log_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'Log')
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)

            now = datetime.now()
            time_str = now.strftime("%Y_%m월%d일_%H시%M분%S초")

            p_provider = self.config.get('provider', self._get_provider_name())

            t_date = self.config.get('target_date', '00000000')
            if len(t_date) == 8 and t_date.isdigit():
                t_date_fmt = f"{t_date[:4]}_{t_date[4:6]}_{t_date[6:]}"
            else:
                t_date_fmt = t_date

            self.log_file = os.path.join(log_dir, f"{time_str}_더피싱_{p_provider}_{t_date_fmt}_.txt")

            pretty_timestamp = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(f"=== Bot Log Started: {pretty_timestamp} ===\n")

                p_port = self.config.get('port', 'Unknown')
                p_date = self.config.get('target_date', '')
                if len(p_date) == 8 and p_date.isdigit():
                    p_date = f"{p_date[:4]}-{p_date[4:6]}-{p_date[6:]}"

                p_time = self.config.get('target_time', '')
                p_name = self.config.get('user_name', '')
                p_phone = self.config.get('user_phone', '')

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
        """타임스탬프 포함 로그 출력 + 파일 기록"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-4]
        formatted_msg = f"[{timestamp}] {msg}"

        if self.log_callback:
            try:
                self.log_callback(formatted_msg)
                sys.stdout.flush()
            except UnicodeEncodeError:
                # Windows 콘솔에서 이모지 출력 시 오류 방지 - 이모지를 텍스트로 대체
                safe_msg = formatted_msg.encode('ascii', errors='replace').decode('ascii')
                self.log_callback(safe_msg)
                sys.stdout.flush()
            except Exception:
                # 그 외 오류는 무시
                pass

        if self.log_file:
            try:
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(formatted_msg + "\n")
            except Exception:
                pass

    # ============================================================
    # 크롬 드라이버 설정
    # ============================================================
    def setup_driver(self):
        """Chrome Driver 초기화 (스텔스 설정 포함)"""
        self.log("🚗 크롬 드라이버를 설정하고 있습니다...")
        chrome_options = Options()

        window_x = self.config.get('window_x')
        window_y = self.config.get('window_y')
        window_width = self.config.get('window_width')
        window_height = self.config.get('window_height')

        if window_x is None:
            chrome_options.add_argument("--start-maximized")

        chrome_options.add_experimental_option("detach", True)
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--no-proxy-server")
        chrome_options.page_load_strategy = 'eager'

        service = Service()
        self.driver = webdriver.Chrome(service=service, options=chrome_options)

        # Chrome PID 저장
        try:
            import psutil
            driver_pid = self.driver.service.process.pid
            driver_proc = psutil.Process(driver_pid)
            chrome_pids = []
            for child in driver_proc.children(recursive=True):
                if 'chrome' in child.name().lower():
                    chrome_pids.append(child.pid)

            pid_file = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'bot_chrome_pids.txt')
            os.makedirs(os.path.dirname(pid_file), exist_ok=True)
            with open(pid_file, 'a', encoding='utf-8') as f:
                for pid in chrome_pids:
                    f.write(f"{pid}\n")
            self.log(f"📝 Chrome PID 저장됨: {chrome_pids}")
        except Exception as e:
            self.log(f"⚠️ Chrome PID 저장 실패 (무시됨): {e}")

        if window_x is not None and window_y is not None:
            self.driver.set_window_position(window_x, window_y)
            self.log(f"📍 창 위치 설정: ({window_x}, {window_y})")
        if window_width is not None and window_height is not None:
            self.driver.set_window_size(window_width, window_height)
            self.log(f"📐 창 크기 설정: {window_width} x {window_height}")

        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        })

    # ============================================================
    # 서버 시간 / 대기
    # ============================================================
    def get_server_time(self, url):
        """서버 헤더에서 시간 가져오기"""
        try:
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
        """정밀 대기 + 조기오픈 감시"""
        now = datetime.now()
        try:
            target_dt = datetime.strptime(f"{now.year}-{now.month}-{now.day} {target_time_str}", "%Y-%m-%d %H:%M:%S.%f")
        except ValueError:
            target_dt = datetime.strptime(f"{now.year}-{now.month}-{now.day} {target_time_str}", "%Y-%m-%d %H:%M:%S")

        if target_dt < now:
             target_dt = target_dt + timedelta(days=1)

        early_monitor = self.config.get('early_monitor', False)
        early_monitor_start = target_dt - timedelta(minutes=5)

        if early_monitor:
            self.log(f"🔍 조기오픈 감시 활성화: {early_monitor_start.strftime('%H:%M:%S')}부터 10초마다 페이지 확인")

        self.log(f"⏰ 목표 시간 대기 중: {target_dt} (현재 시간 기준)")

        last_display_second = -1
        last_early_check = None
        first_display = True

        while self.is_running:
            now = datetime.now()
            diff = (target_dt - now).total_seconds()

            if diff <= 0:
                self.log("🚀 예약 오픈 시간입니다! 작업을 시작합니다!")
                break

            if early_monitor and now >= early_monitor_start:
                should_check = False
                if last_early_check is None:
                    should_check = True
                elif (now - last_early_check).total_seconds() >= 10:
                    should_check = True

                if should_check:
                    last_early_check = now
                    try:
                        self.driver.refresh()
                        time.sleep(0.5)
                        page_source = self.driver.page_source

                        open_keywords = ['STEP 01', '예약1단계', '배 선택', 'ps_selis', 'PS_N_UID']
                        closed_keywords = ['준비 중', '오픈 예정', '예약 불가', '접수 마감', '없는', '권한', '잘못']

                        is_open = any(kw in page_source for kw in open_keywords)
                        is_closed = any(kw in page_source for kw in closed_keywords)

                        if is_open and not is_closed:
                            self.log("🎉🎉🎉 조기 오픈 감지! 예약 페이지가 열렸습니다!")
                            self.log(f"   (예정: {target_dt.strftime('%H:%M:%S')}, 실제: {now.strftime('%H:%M:%S')}, {diff:.0f}초 일찍 오픈)")
                            break
                        else:
                            self.log(f"🔍 조기오픈 체크: 아직 미오픈 (남은시간: {int(diff)}초)")
                    except Exception as e:
                        self.log(f"⚠️ 조기오픈 체크 오류: {e}")

            current_second = int(diff)
            if current_second != last_display_second:
                minutes = int(diff // 60)
                seconds = int(diff % 60)

                # 로그 출력 조건
                should_print = False

                if first_display:
                    # 처음 남은 시간 표시
                    should_print = True
                    first_display = False
                elif current_second <= 5:
                    # 마지막 5초: 매초
                    should_print = True
                elif current_second <= 60 and current_second in [10, 30]:
                    # 1분 이하: 10초, 30초
                    should_print = True
                elif current_second > 60 and current_second % 300 == 0:
                    # 1분 초과: 5분 간격
                    should_print = True
                elif current_second == 60:
                    # 1분 정각
                    should_print = True

                if should_print:
                    if current_second <= 5:
                        self.log(f"⏳ {seconds}초")
                    else:
                        self.log(f"⏳ 남은 시간: {minutes}분 {seconds:02d}초")

                last_display_second = current_second

            if diff > 10:
                time.sleep(0.5)
            elif diff > 1:
                time.sleep(0.1)
            else:
                time.sleep(0.01)

    # ============================================================
    # 🧹 브라우저 정리
    # ============================================================
    def cleanup_all_browsers(self):
        """모든 백그라운드 브라우저를 안전하게 종료"""
        self.log("🧹 백그라운드 브라우저 정리 시작...")
        for i, browser in enumerate(self.browsers):
            try:
                browser.quit()
                self.log(f"🧹 백그라운드 브라우저 {i+1} 종료 완료")
            except WebDriverException:
                pass
        self.browsers.clear()
        self.browser_threads.clear()

    def cleanup_old_browsers(self):
        """MAX_BACKGROUND_BROWSERS 초과 시 오래된 브라우저 정리"""
        while len(self.browsers) > self.MAX_BACKGROUND_BROWSERS:
            old_browser = self.browsers.pop(0)
            if self.browser_threads:
                self.browser_threads.pop(0)
            try:
                old_browser.quit()
                self.log(f"🧹 오래된 백그라운드 브라우저 종료 (현재: {len(self.browsers)}개)")
            except WebDriverException:
                pass

    def _move_to_background(self, wait):
        """현재 브라우저를 백그라운드 모니터링으로 전환 + 새 브라우저 생성"""
        self.cleanup_old_browsers()

        old_driver = self.driver
        browser_id = len(self.browsers) + 1
        self.browsers.append(old_driver)
        t = threading.Thread(target=self.monitor_browser_for_success, args=(old_driver, browser_id))
        t.daemon = True
        t.start()
        self.browser_threads.append(t)

        self.setup_driver()
        return WebDriverWait(self.driver, 30)

    def _move_to_background_with_extended_wait(self, wait, extended_timeout=15):
        """현재 브라우저를 백그라운드에서 추가 대기 + 새 브라우저 생성

        서버 과부하 시 낚시 종류 선택 후 좌석 페이지가 늦게 로딩되는 경우:
        - 현재 브라우저: 백그라운드에서 extended_timeout초 더 대기
        - 새 브라우저: 즉시 시작하여 처음부터 진행
        - 어느 쪽이든 성공하면 나머지 종료
        """
        self.cleanup_old_browsers()

        old_driver = self.driver
        browser_id = len(self.browsers) + 1
        self.browsers.append(old_driver)

        # 확장 대기 모니터링 스레드 시작
        t = threading.Thread(
            target=self._monitor_with_extended_wait,
            args=(old_driver, browser_id, extended_timeout)
        )
        t.daemon = True
        t.start()
        self.browser_threads.append(t)

        self.log(f"🔄 [브라우저{browser_id}] 백그라운드에서 {extended_timeout}초 추가 대기 중...")
        self.setup_driver()
        return WebDriverWait(self.driver, 30)

    def _monitor_with_extended_wait(self, driver, browser_id, extended_timeout):
        """백그라운드에서 확장 대기 후 성공 여부 모니터링"""
        start_time = time.time()

        # Phase 1: 인원 선택(BI_IN) 활성화 대기
        self.log(f"🔍 [브라우저{browser_id}] 인원 선택 활성화 대기 중 ({extended_timeout}초)...")

        while time.time() - start_time < extended_timeout:
            if self.success_event.is_set():
                self.log(f"🛑 [브라우저{browser_id}] 다른 브라우저 성공 감지, 종료")
                return

            try:
                # 인원 선택 드롭다운 확인
                bi_in = driver.find_element(By.ID, "BI_IN")
                if bi_in.is_enabled() and bi_in.is_displayed():
                    self.log(f"✨ [브라우저{browser_id}] 인원 선택 활성화 감지! ({time.time()-start_time:.1f}초)")
                    # 성공: 이후 예약 진행을 위해 일반 모니터링으로 전환
                    self._continue_reservation_in_background(driver, browser_id)
                    return
            except (NoSuchElementException, WebDriverException):
                pass

            time.sleep(0.2)

        # Phase 2: 타임아웃 - 브라우저 종료
        self.log(f"⏰ [브라우저{browser_id}] {extended_timeout}초 타임아웃, 브라우저 종료")
        try:
            driver.quit()
        except WebDriverException:
            pass

        # browsers 리스트에서 제거
        if driver in self.browsers:
            self.browsers.remove(driver)

    def _continue_reservation_in_background(self, driver, browser_id):
        """백그라운드 브라우저에서 예약 계속 진행"""
        self.log(f"🚀 [브라우저{browser_id}] 백그라운드에서 예약 진행 중...")

        try:
            # 인원 설정
            configured_count = int(self.config.get('person_count', '1'))
            user_name = self.config.get('user_name', '')
            user_depositor = self.config.get('user_depositor', '')
            user_phone = self.config.get('user_phone', '')

            # 좌석 선택 (HAS_SEAT_SELECTION인 경우)
            if self.HAS_SEAT_SELECTION:
                selected_seats = self._select_seats_in_driver(driver, configured_count, browser_id)
                final_count = selected_seats if selected_seats > 0 else 1
            else:
                final_count = configured_count

            # 인원 선택
            try:
                select_el = driver.find_element(By.ID, "BI_IN")
                Select(select_el).select_by_value(str(final_count))
                self.log(f"👥 [브라우저{browser_id}] 인원 {final_count}명 설정")
            except WebDriverException as e:
                self.log(f"⚠️ [브라우저{browser_id}] 인원 설정 실패: {e}")

            # 이름 입력
            try:
                name_input = driver.find_element(By.NAME, "BI_NAME")
                name_input.clear()
                name_input.send_keys(user_name)
            except WebDriverException:
                pass

            # 입금자명
            if user_depositor:
                try:
                    bank_input = driver.find_element(By.ID, "BI_BANK")
                    bank_input.clear()
                    bank_input.send_keys(user_depositor)
                except WebDriverException:
                    pass

            # 전화번호
            p2, p3 = "", ""
            if "-" in user_phone:
                parts = user_phone.split("-")
                if len(parts) == 3:
                    p2, p3 = parts[1], parts[2]
            elif len(user_phone) == 11:
                p2, p3 = user_phone[3:7], user_phone[7:]

            if p2 and p3:
                try:
                    driver.find_element(By.ID, "BI_TEL2").clear()
                    driver.find_element(By.ID, "BI_TEL2").send_keys(p2)
                    driver.find_element(By.ID, "BI_TEL3").clear()
                    driver.find_element(By.ID, "BI_TEL3").send_keys(p3)
                except WebDriverException:
                    pass

            # 전체 동의
            try:
                agree_btn = driver.find_element(By.XPATH, "//input[@name='all_agree' and @value='Y']")
                driver.execute_script("arguments[0].click();", agree_btn)
            except WebDriverException:
                pass

            # Submit 클릭
            try:
                submit_btn = driver.find_element(By.ID, "submit")
                driver.execute_script("arguments[0].click();", submit_btn)
                self.log(f"🚀 [브라우저{browser_id}] 예약 신청 버튼 클릭!")
            except WebDriverException as e:
                self.log(f"⚠️ [브라우저{browser_id}] 제출 버튼 클릭 실패: {e}")

            # 이후 일반 모니터링으로 전환
            self.monitor_browser_for_success(driver, browser_id)

        except WebDriverException as e:
            self.log(f"⚠️ [브라우저{browser_id}] 백그라운드 예약 진행 실패: {e}")
            try:
                driver.quit()
            except WebDriverException:
                pass

    def _select_seats_in_driver(self, driver, configured_count, browser_id):
        """특정 드라이버에서 좌석 선택 (백그라운드용)"""
        seat_priority = self.SEAT_PRIORITY
        selected_seats = 0

        try:
            seat_class = None
            try:
                driver.find_element(By.CLASS_NAME, "res_num_view")
                seat_class = "res_num_view"
            except NoSuchElementException:
                try:
                    driver.find_element(By.CLASS_NAME, "num_view")
                    seat_class = "num_view"
                except NoSuchElementException:
                    return 0

            available_seats = driver.find_elements(By.XPATH, f"//span[@class='{seat_class}']")
            target_count = min(configured_count, len(available_seats))

            for seat_num in seat_priority:
                if selected_seats >= target_count:
                    break
                try:
                    seat_spans = driver.find_elements(By.XPATH, f"//span[@class='{seat_class}' and text()='{seat_num}']")
                    for seat_span in seat_spans:
                        if seat_span.is_displayed():
                            driver.execute_script("arguments[0].click();", seat_span)
                            selected_seats += 1
                            self.log(f"🪑 [브라우저{browser_id}] 좌석 {seat_num}번 선택")
                            break
                except WebDriverException:
                    continue

        except WebDriverException:
            pass

        return selected_seats

    # ============================================================
    # 🔍 백그라운드 모니터링 (공통)
    # ============================================================
    def monitor_browser_for_success(self, driver, browser_id):
        """별도 스레드에서 브라우저 성공 여부 모니터링"""
        self.log(f"🔍 [브라우저{browser_id}] 백그라운드 모니터링 시작...")

        while not self.success_event.is_set():
            try:
                # 0. 알림창 확인 (성공 or 확인)
                try:
                    alert = driver.switch_to.alert
                    txt = alert.text
                    if "완료" in txt or "성공" in txt:
                        self.log(f"🎉 [브라우저{browser_id}] 예약 성공! (알림창: {txt})")
                        alert.accept()
                        self.success_event.set()
                        return
                    else:
                        alert.accept()
                except NoAlertPresentException:
                    pass
                except WebDriverException:
                    self.log(f"⚠️ [브라우저{browser_id}] 알림창 확인 중 오류, 모니터링 종료")
                    break

                # 1. URL 기반 성공 확인
                try:
                    current_url = driver.current_url
                    if self.SUCCESS_URL_KEYWORD in current_url:
                        self.log(f"🎉 [브라우저{browser_id}] 예약 성공! (URL: {self.SUCCESS_URL_KEYWORD})")
                        self.success_event.set()
                        return
                except WebDriverException:
                    self.log(f"⚠️ [브라우저{browser_id}] 브라우저 연결 끊김, 모니터링 종료")
                    break

                # 2. page_source 체크 (5회에 1번 - 성능 최적화)
                self._monitor_counter[browser_id] = self._monitor_counter.get(browser_id, 0) + 1
                if self._monitor_counter[browser_id] % 5 == 0:
                    try:
                        page_src = driver.page_source
                        if "신청이 완료되었습니다" in page_src or "예약 신청이 완료되었습니다" in page_src:
                            self.log(f"🎉 [브라우저{browser_id}] 예약 성공! (텍스트)")
                            self.success_event.set()
                            return
                    except WebDriverException:
                        break

                # 3. 탭 활성화 확인
                try:
                    tabs = driver.find_elements(By.CSS_SELECTOR, self.TAB_SELECTOR)
                    if len(tabs) > self.SUCCESS_TAB_INDEX:
                        tab_class = tabs[self.SUCCESS_TAB_INDEX].get_attribute("class") or ""
                        if "on" in tab_class:
                            self.log(f"🎉 [브라우저{browser_id}] 예약 성공! (탭 활성화)")
                            self.success_event.set()
                            return
                except (StaleElementReferenceException, WebDriverException):
                    break

                # 4. 구조 로직: submit 버튼 클릭 시도
                try:
                    # 3-step 봇: step2에서 submit 클릭 시도
                    if self.STEPS == 3 and "step2.php" in driver.current_url:
                        btn = driver.find_element(By.ID, "submit")
                        driver.execute_script("arguments[0].click();", btn)
                    # 2-step 봇: step1에서 submit 클릭 시도
                    elif self.STEPS == 2:
                        btn = driver.find_element(By.ID, "submit")
                        driver.execute_script("arguments[0].click();", btn)
                except (NoSuchElementException, WebDriverException):
                    pass

            except WebDriverException:
                self.log(f"⚠️ [브라우저{browser_id}] 브라우저 연결 끊김")
                break

            time.sleep(0.1)

        self.log(f"🛑 [브라우저{browser_id}] 모니터링 중지")

    # ============================================================
    # 🎯 메인 실행 플로우
    # ============================================================
    def run(self):
        """메인 예약 로직 (모든 선사 공통)"""
        self.setup_driver()
        wait = WebDriverWait(self.driver, 30)

        # 1. Config 파싱
        target_date = self.config.get('target_date', '20260101')
        target_time = self.config.get('target_time', '09:00:00')
        test_mode = self.config.get('test_mode', False)
        self.simulation_mode = self.config.get('simulation_mode', False)

        user_name = self.config.get('user_name', '')
        user_depositor = self.config.get('user_depositor', '')
        user_phone = self.config.get('user_phone', '')

        # 2. URL 구성
        base_url, url = self._build_reservation_url(target_date)

        # target_keywords: config 우선, 없으면 클래스 기본값
        target_keywords = []
        target_ship_cfg = self.config.get('target_ship', '').strip()
        if target_ship_cfg:
            target_keywords.append(target_ship_cfg)
        target_keywords.extend(self.TARGET_KEYWORDS)

        # 2.5 사전 로드
        provider_name = self._get_provider_name()
        self.log(f"🌍 페이지 사전 로드 중: {url}")
        self.log(f"#########🔎 {provider_name} 예약로직 시작!##########")
        try:
            self.driver.get(url)
            self.log("✅ 사전 로드 완료. 오픈 시간을 기다립니다...")
        except Exception as e:
            self.log(f"⚠️ 사전 로드 실패 (예약 시간에 재시도함): {e}")

        # 1.5 스케줄링
        if not test_mode:
            self.log(f"⏰ 실행 예약 시간: {target_time}...")
            self.wait_until_target_time(target_time)
        else:
            self.log("🚀 테스트 모드 활성화: 대기 없이 즉시 실행합니다!")

        # 3. 메인 루프
        self.log(f"🔥 예약 시도 시작 (반복 루프): {url}")

        outer_attempt = 0
        try:
            while outer_attempt < self.MAX_OUTER_RETRIES and not self.success_event.is_set():
                outer_attempt += 1
                self.log(f"🔄 외부 루프 시도 {outer_attempt}/{self.MAX_OUTER_RETRIES}")

                max_retries = 5000
                retry_interval = 0.2
                step1_success = False
                retry_counts = {"redirect": 0, "bad_gateway": 0, "error_page": 0, "not_ready": 0, "no_button": 0}

                # ============================
                # STEP 1: 낚시 종류 선택
                # ============================
                for attempt in range(max_retries):
                    if self.success_event.is_set():
                        self.log("🎉 다른 브라우저에서 예약 성공 감지! 중단합니다.")
                        return

                    try:
                        self.driver.get(url)
                        page_source = self.driver.page_source
                        current_url = self.driver.current_url

                        # 리다이렉트 에러 감지
                        if "ERR_TOO_MANY_REDIRECTS" in page_source or "리디렉션한 횟수가 너무 많습니다" in page_source or "waitingrequest" in current_url:
                            retry_counts["redirect"] += 1
                            print(f"\r⚠️ 리다이렉트 에러! 고속 복구 중... ({retry_counts['redirect']}회)", end="", flush=True)
                            try:
                                self.driver.delete_all_cookies()
                                time.sleep(0.1)
                                self.driver.get(url)
                            except WebDriverException as e:
                                print()  # 줄바꿈
                                self.log(f"⚠️ 고속 복구 실패 ({e}), 브라우저 재시작...")
                                try:
                                    self.driver.quit()
                                except WebDriverException:
                                    pass
                                self.setup_driver()
                                wait = WebDriverWait(self.driver, 30)
                                self.driver.get(url)
                            continue

                        # 서버 에러
                        if "Bad Gateway" in self.driver.title:
                            retry_counts["bad_gateway"] += 1
                            print(f"\r⚠️ 서버 오류 (502). 재시도 중... ({retry_counts['bad_gateway']}회)", end="", flush=True)
                            time.sleep(0.5)
                            continue

                        # 에러 텍스트
                        if any(err in page_source for err in ['없는', '권한', '잘못']):
                            retry_counts["error_page"] += 1
                            print(f"\r⚠️ 에러 페이지 감지. 재시도 중... ({retry_counts['error_page']}회)", end="", flush=True)
                            time.sleep(0.3)
                            continue

                        # 예약 페이지 감지
                        reservation_keywords = ['STEP 01', '예약1단계', '배 선택']
                        matched_keywords = [txt for txt in reservation_keywords if txt in page_source]
                        if matched_keywords:
                            # 이전 재시도 로그 정리 및 성공 로그 출력
                            total_retries = sum(retry_counts.values())
                            if total_retries > 0:
                                print()  # 줄바꿈
                                self.log(f"📄 예약 페이지 감지! (재시도 {total_retries}회 후 성공)")
                            else:
                                self.log(f"📄 예약 페이지 감지! 텍스트: {matched_keywords}")
                            try:
                                WebDriverWait(self.driver, 3).until(
                                    EC.presence_of_element_located((By.CLASS_NAME, "ps_selis"))
                                )
                            except TimeoutException:
                                retry_counts["no_button"] += 1
                                print(f"\r⏳ 낚시종류 버튼 미발견. 새로고침 중... ({retry_counts['no_button']}회)", end="", flush=True)
                                continue
                        else:
                            retry_counts["not_ready"] += 1
                            print(f"\r⏳ 페이지 준비 안됨. 재시도 중... ({retry_counts['not_ready']}회)", end="", flush=True)
                            time.sleep(0.1)
                            continue

                        process_start_time = time.time()
                        step_start = time.time()
                        if self.SLEEP_INTERVAL > 0.01:
                            time.sleep(self.SLEEP_INTERVAL)
                        radios = self.driver.find_elements(By.CSS_SELECTOR, "input.PS_N_UID")
                        self.log(f"🎣 낚시 종류 선택 항목 찾는 중... (소요시간: {time.time()-step_start:.2f}초)")

                        # 단일 항목 자동 선택
                        if len(radios) == 1:
                            try:
                                self.driver.execute_script("arguments[0].click();", radios[0])
                                self.log("✨ 단일 선택 항목 감지됨. 자동 선택 완료.")
                                step1_success = True
                                break
                            except WebDriverException as e:
                                self.log(f"⚠️ 단일 라디오 클릭 실패: {e}")

                        # 키워드 매칭
                        all_spans = self.driver.find_elements(By.CLASS_NAME, "ps_selis")
                        self.log(f"🔎 총 {len(all_spans)}개의 낚시 종류 후보를 찾았습니다.")

                        found_click = False
                        for keyword in target_keywords:
                            if found_click:
                                break
                            for span in all_spans:
                                text = span.text.strip()
                                if keyword in text:
                                    match_start = time.time()
                                    if self.SLEEP_INTERVAL > 0.01:
                                        time.sleep(self.SLEEP_INTERVAL)
                                    self.log(f"✨ Match found! '{keyword}' in '{text}'")
                                    found_click = self._click_fishing_type(span)
                                    if found_click:
                                        self.log(f"⚡ 클릭 완료 (소요시간: {time.time()-match_start:.2f}초)")
                                        break
                            if found_click:
                                break

                        if found_click:
                            step_start = time.time()
                            self.log("⏳ 인원 선택(BI_IN) 활성화 대기 중 (최대 5초)...")
                            try:
                                WebDriverWait(self.driver, 5).until(
                                    EC.element_to_be_clickable((By.ID, "BI_IN"))
                                )
                                self.log(f"✅ 인원 선택 활성화! 2단계 진입 성공! (소요시간: {time.time()-step_start:.2f}초)")
                                step1_success = True
                                break
                            except TimeoutException:
                                # 5초 타임아웃: 현재 브라우저는 백그라운드에서 15초 더 대기, 새 브라우저 시작
                                self.log("⚠️ 5초 내 인원 선택 미감지. 백그라운드 전환 + 새 브라우저 시작...")
                                wait = self._move_to_background_with_extended_wait(wait, 15)
                                continue
                        else:
                            # 첫번째 어종 자동 선택
                            self.log("⚠️ 키워드 매칭 없음, 첫번째 어종 자동 선택 시도...")
                            try:
                                radios = self.driver.find_elements(By.CSS_SELECTOR, "input.PS_N_UID")
                                if radios:
                                    self.driver.execute_script("arguments[0].click();", radios[0])
                                    self.log("✅ 첫번째 어종 자동 선택 완료!")
                                    try:
                                        WebDriverWait(self.driver, 5).until(
                                            EC.element_to_be_clickable((By.ID, "BI_IN"))
                                        )
                                        step1_success = True
                                        break
                                    except TimeoutException:
                                        # 5초 타임아웃: 현재 브라우저는 백그라운드에서 15초 더 대기, 새 브라우저 시작
                                        self.log("⚠️ 5초 내 인원 선택 미감지. 백그라운드 전환 + 새 브라우저 시작...")
                                        wait = self._move_to_background_with_extended_wait(wait, 15)
                                        continue
                                else:
                                    self.log("⚠️ 선택 가능한 어종이 없습니다.")
                                    break
                            except WebDriverException as e:
                                self.log(f"⚠️ 첫번째 어종 선택 실패: {e}")
                                break

                    except WebDriverException as e:
                        self.log(f"⚠️ 연결 오류 발생: {e}. 재시도 중...")
                        time.sleep(retry_interval)

                if not step1_success:
                    self.log("❌ Step 1 실패. 외부 루프 재시작...")
                    continue

                # ============================
                # STEP 1.2: 남은 좌석 확인 (자리선택 봇만)
                # ============================
                configured_count = int(self.config.get('person_count', '1'))
                selected_seats = 0

                if self.HAS_SEAT_SELECTION:
                    step_start = time.time()
                    try:
                        remaining_seats_el = self.driver.find_element(By.ID, "id_bi_in")
                        remaining_seats = int(remaining_seats_el.text.strip())
                        self.log(f"📊 남은 좌석 확인: {remaining_seats}석, 설정 인원: {configured_count}명 (소요시간: {time.time()-step_start:.2f}초)")
                        if remaining_seats < configured_count:
                            self.log(f"⚠️ 남은 좌석 부족! {configured_count}명 → {remaining_seats}명으로 자동 조정.")
                            configured_count = remaining_seats
                    except (NoSuchElementException, ValueError) as e:
                        self.log(f"⚠️ 남은 좌석 수 확인 실패, 설정값 사용: {e}")

                    # 자리 선택
                    selected_seats = self._select_seats(configured_count)

                # ============================
                # STEP 1.5: 인원 설정
                # ============================
                step_start = time.time()
                if self.SLEEP_INTERVAL > 0.01:
                    time.sleep(self.SLEEP_INTERVAL)
                try:
                    select_el = wait.until(EC.element_to_be_clickable((By.ID, "BI_IN")))
                    select_obj = Select(select_el)
                    current_val = select_obj.first_selected_option.get_attribute("value")

                    if self.HAS_SEAT_SELECTION:
                        final_count = selected_seats if selected_seats > 0 else 1
                    else:
                        final_count = configured_count
                    final_count_str = str(final_count)

                    if current_val != final_count_str:
                        select_obj.select_by_value(final_count_str)
                        if self.SLEEP_INTERVAL > 0.01:
                            time.sleep(self.SLEEP_INTERVAL)
                        self.log(f"👥 인원 {final_count_str}명 설정 완료 (소요시간: {time.time()-step_start:.2f}초)")
                    else:
                        self.log(f"👥 이미 {final_count_str}명으로 설정됨 (소요시간: {time.time()-step_start:.2f}초)")
                except (TimeoutException, WebDriverException) as e:
                    self.log(f"⚠️ 인원 선택 오류: {e}")
                    try:
                        self.driver.refresh()
                    except WebDriverException:
                        pass
                    continue

                # ============================
                # STEP 2: 정보 입력 + 제출
                # ============================
                self.log("🪑 예약 정보 입력 페이지(2단계) 진입 중...")
                should_hard_restart = False

                try:
                    # 이름 입력
                    step_start = time.time()
                    name_input = wait.until(EC.element_to_be_clickable((By.NAME, "BI_NAME")))
                    name_input.clear()
                    if self.SLEEP_INTERVAL > 0.01:
                        time.sleep(self.SLEEP_INTERVAL)
                    name_input.send_keys(user_name)
                    time.sleep(self.SLEEP_INTERVAL)
                    self.log(f"✍️ 성함 입력: {user_name} (소요시간: {time.time()-step_start:.2f}초)")

                    # 입금자명
                    if user_depositor:
                        try:
                            step_start = time.time()
                            bank_input = self.driver.find_element(By.ID, "BI_BANK")
                            bank_input.clear()
                            if self.SLEEP_INTERVAL > 0.01:
                                time.sleep(self.SLEEP_INTERVAL)
                            bank_input.send_keys(user_depositor)
                            time.sleep(self.SLEEP_INTERVAL)
                            self.log(f"✍️ 입금자명 입력: {user_depositor} (소요시간: {time.time()-step_start:.2f}초)")
                        except NoSuchElementException:
                            self.log("⚠️ 입금자명 필드(BI_BANK) 없음")

                    # 전화번호
                    p1, p2, p3 = "", "", ""
                    if "-" in user_phone:
                        parts = user_phone.split("-")
                        if len(parts) == 3:
                            p1, p2, p3 = parts
                    elif len(user_phone) == 11:
                        p1, p2, p3 = user_phone[:3], user_phone[3:7], user_phone[7:]

                    if p2 and p3:
                        step_start = time.time()
                        try:
                            t2 = self.driver.find_element(By.ID, "BI_TEL2")
                            t2.clear()
                            if self.SLEEP_INTERVAL > 0.01:
                                time.sleep(self.SLEEP_INTERVAL)
                            t2.send_keys(p2)
                            time.sleep(self.SLEEP_INTERVAL)
                            t3 = self.driver.find_element(By.ID, "BI_TEL3")
                            t3.clear()
                            if self.SLEEP_INTERVAL > 0.01:
                                time.sleep(self.SLEEP_INTERVAL)
                            t3.send_keys(p3)
                            time.sleep(self.SLEEP_INTERVAL)
                            self.log(f"📞 연락처 입력: {p2}-{p3} (소요시간: {time.time()-step_start:.2f}초)")
                        except NoSuchElementException as e:
                            self.log(f"⚠️ 전화번호 필드 없음: {e}")

                    # 전체 동의
                    try:
                        step_start = time.time()
                        agree_btn = self.driver.find_element(By.XPATH, "//input[@name='all_agree' and @value='Y']")
                        self.driver.execute_script("arguments[0].click();", agree_btn)
                        time.sleep(self.SLEEP_INTERVAL)
                        self.log(f"✅ '전체 동의' 체크 완료 (소요시간: {time.time()-step_start:.2f}초)")
                    except NoSuchElementException:
                        self.log("⚠️ '전체 동의' 체크박스 없음")

                    # ============================
                    # 제출 로직 (2-step vs 3-step 분기)
                    # ============================
                    if self.STEPS == 2:
                        should_hard_restart = self._submit_2step(wait, process_start_time)
                    else:
                        should_hard_restart = self._submit_3step(wait, process_start_time)

                    if should_hard_restart:
                        continue

                    # success_event가 설정되었으면 종료
                    if self.success_event.is_set():
                        return

                except (TimeoutException, WebDriverException) as e:
                    self.log(f"⚠️ Step 2 Error: {e}")
                    try:
                        self.driver.refresh()
                    except WebDriverException:
                        self.log("⚠️ 페이지 새로고침 실패, 브라우저 재시작...")
                        try:
                            self.driver.quit()
                        except WebDriverException:
                            pass
                        self.setup_driver()
                        wait = WebDriverWait(self.driver, 30)
                    continue

                self.log("🔄 루프 재시작...")
                time.sleep(0.05)

            # 외부 루프 종료
            if outer_attempt >= self.MAX_OUTER_RETRIES:
                self.log(f"❌ 최대 외부 루프 횟수({self.MAX_OUTER_RETRIES})에 도달. 봇 종료.")
            elif self.success_event.is_set():
                self.log("🎉 예약 성공 감지!")

        finally:
            # 백그라운드 브라우저만 정리 (메인 브라우저는 유지)
            self.cleanup_all_browsers()

            if self.success_event.is_set():
                # 성공 시 브라우저 유지하고 대기
                self.log("✅ 예약 완료! 브라우저를 유지합니다. (Ctrl+C로 종료)")
                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    self.log("🛑 사용자 종료 요청...")

            # 종료 시 메인 브라우저 정리
            try:
                if self.driver:
                    self.driver.quit()
                    self.log("🧹 메인 브라우저 종료 완료")
            except WebDriverException:
                pass

    # ============================================================
    # 클릭 전략
    # ============================================================
    def _click_fishing_type(self, span):
        """낚시 종류 클릭 (id_first 또는 xpath_first 전략)"""
        if self.CLICK_STRATEGY == "id_first":
            return self._click_by_id_first(span)
        else:
            return self._click_by_xpath_first(span)

    def _click_by_id_first(self, span):
        """PS1 ID → label → ancestor TD → span 직접 클릭"""
        try:
            span_id = span.get_attribute("id")
            if span_id and span_id.startswith("PS1"):
                uid = span_id[3:]
                input_id = f"PS_N_UID{uid}"
                try:
                    target_input = self.driver.find_element(By.ID, input_id)
                    self.driver.execute_script("arguments[0].click();", target_input)
                    self.log(f"⚡ Clicked input by ID: {input_id}")
                    if self.SLEEP_INTERVAL > 0.01:
                        time.sleep(self.SLEEP_INTERVAL)
                    return True
                except (NoSuchElementException, WebDriverException) as e:
                    self.log(f"⚠️ ID 클릭 실패 ({input_id}): {e}")

            # Fallback: parent label
            try:
                label = span.find_element(By.XPATH, "./parent::label")
                self.driver.execute_script("arguments[0].click();", label)
                self.log("⚡ Clicked parent label.")
                if self.SLEEP_INTERVAL > 0.01:
                    time.sleep(self.SLEEP_INTERVAL)
                return True
            except (NoSuchElementException, WebDriverException):
                pass

            # Fallback: ancestor TD radio
            try:
                radio = span.find_element(By.XPATH, "./ancestor::td/preceding-sibling::td//input[@type='radio']")
                self.driver.execute_script("arguments[0].click();", radio)
                self.log("⚡ Clicked radio (Ancestor TD).")
                if self.SLEEP_INTERVAL > 0.01:
                    time.sleep(self.SLEEP_INTERVAL)
                return True
            except (NoSuchElementException, WebDriverException):
                pass

            # Fallback: span 직접 클릭
            try:
                span.click()
                self.log("⚡ Clicked span directly.")
                if self.SLEEP_INTERVAL > 0.01:
                    time.sleep(self.SLEEP_INTERVAL)
                return True
            except WebDriverException:
                pass

        except (StaleElementReferenceException, WebDriverException) as e:
            self.log(f"⚠️ Click Logic Error: {e}")

        return False

    def _click_by_xpath_first(self, span):
        """XPath parent TD → preceding-sibling → span 직접 클릭"""
        try:
            # parent TD
            try:
                radio = span.find_element(By.XPATH, "./parent::td/preceding-sibling::td//input[@type='radio']")
                self.driver.execute_script("arguments[0].click();", radio)
                self.log("⚡ Clicked radio (Parent TD).")
                return True
            except (NoSuchElementException, WebDriverException):
                pass

            # preceding-sibling
            try:
                radio = span.find_element(By.XPATH, "./preceding-sibling::input[@type='radio']")
                self.driver.execute_script("arguments[0].click();", radio)
                self.log("⚡ Clicked radio (Preceding Sibling).")
                return True
            except (NoSuchElementException, WebDriverException):
                pass

            # span 직접 클릭
            try:
                span.click()
                self.log("⚡ Clicked span directly.")
                return True
            except WebDriverException:
                pass

        except (StaleElementReferenceException, WebDriverException) as e:
            self.log(f"⚠️ Click Logic Error: {e}")

        return False

    # ============================================================
    # 자리 선택
    # ============================================================
    def _select_seats(self, configured_count):
        """좌석 선택 로직 (HAS_SEAT_SELECTION=True인 봇에서만 호출)"""
        step_start = time.time()
        seat_priority = self.SEAT_PRIORITY
        selected_seats = 0
        selected_seats_list = []

        try:
            # 좌석 클래스 감지
            seat_class = None
            try:
                self.driver.find_element(By.CLASS_NAME, "res_num_view")
                seat_class = "res_num_view"
                self.log("✅ 좌석 클래스 감지: res_num_view")
            except NoSuchElementException:
                try:
                    self.driver.find_element(By.CLASS_NAME, "num_view")
                    seat_class = "num_view"
                    self.log("✅ 좌석 클래스 감지: num_view")
                except NoSuchElementException:
                    self.log("⚠️ 좌석 선택 영역을 찾을 수 없습니다.")

            if seat_class:
                if self.SLEEP_INTERVAL > 0.01:
                    time.sleep(self.SLEEP_INTERVAL)
                available_seats = self.driver.find_elements(By.XPATH, f"//span[@class='{seat_class}']")
                available_count = len(available_seats)
                self.log(f"📊 가용 좌석 수: {available_count}석, 설정 인원: {configured_count}명")

                target_count = min(configured_count, available_count)
                if target_count < configured_count:
                    self.log(f"⚠️ 가용 좌석 부족! {configured_count}명 → {target_count}명으로 자동 조정.")

                # 우선순위 좌석 선택
                for seat_num in seat_priority:
                    if selected_seats >= target_count:
                        break
                    try:
                        seat_spans = self.driver.find_elements(By.XPATH, f"//span[@class='{seat_class}' and text()='{seat_num}']")
                        for seat_span in seat_spans:
                            if seat_span.is_displayed():
                                self.log(f"✨ 우선순위 좌석 {seat_num}번 발견! ({selected_seats+1}/{target_count})")
                                class_before = seat_span.get_attribute("class") or ""
                                self.driver.execute_script("arguments[0].click();", seat_span)
                                if self.SLEEP_INTERVAL > 0.01:
                                    time.sleep(self.SLEEP_INTERVAL)
                                class_after = seat_span.get_attribute("class") or ""

                                if class_after != class_before:
                                    selected_seats += 1
                                    selected_seats_list.append(seat_num)
                                    self.log(f"✅ 좌석 {seat_num}번 선택 성공! ({selected_seats}/{target_count})")
                                    if self.SLEEP_INTERVAL > 0.01:
                                        time.sleep(self.SLEEP_INTERVAL)
                                else:
                                    self.log(f"⚠️ 좌석 {seat_num}번 선택 실패. 다음 순번으로...")
                                break
                    except (StaleElementReferenceException, WebDriverException) as e:
                        self.log(f"⚠️ 좌석 {seat_num}번 접근 오류: {e}")
                        continue

                # 우선순위 좌석 부족시 무작위 선택
                if selected_seats < target_count:
                    self.log(f"⚠️ 우선순위 좌석 부족. 남은 좌석 중 무작위 선택 ({selected_seats}/{target_count})...")
                    try:
                        all_seats = self.driver.find_elements(By.CLASS_NAME, seat_class)
                        seat_priority_set = set(seat_priority)
                        for seat_span in all_seats:
                            if selected_seats >= target_count:
                                break
                            try:
                                seat_text = seat_span.text.strip()
                                if seat_span.is_displayed() and seat_text not in seat_priority_set:
                                    self.log(f"🎲 무작위 좌석 {seat_text}번 선택 중... ({selected_seats+1}/{target_count})")
                                    self.driver.execute_script("arguments[0].click();", seat_span)
                                    selected_seats += 1
                                    selected_seats_list.append(seat_text)
                                    if self.SLEEP_INTERVAL > 0.01:
                                        time.sleep(self.SLEEP_INTERVAL)
                            except (StaleElementReferenceException, WebDriverException):
                                continue
                    except WebDriverException as ex:
                        self.log(f"⚠️ 무작위 좌석 선택 오류: {ex}")

                if selected_seats >= target_count:
                    self.log(f"✅ 좌석 선택 완료! 총 {selected_seats}석 (순서: {' → '.join(selected_seats_list)}) (소요시간: {time.time()-step_start:.2f}초)")
                    self.log(f"📋 좌석 우선순위: {seat_priority}")
                else:
                    self.log(f"⚠️ 좌석 선택 부족: {selected_seats}/{target_count}석만 선택됨.")

        except WebDriverException as e:
            self.log(f"⚠️ 좌석 선택 오류 (건너뜀): {e}")

        return selected_seats

    # ============================================================
    # 2-Step 제출 로직
    # ============================================================
    def _submit_2step(self, wait, process_start_time):
        """2-step 예약 제출 (step2.php에서 완료)"""
        self.log("🚀 '예약 신청하기' 버튼 클릭 시도...")

        for submit_attempt in range(self.MAX_SUBMIT_RETRIES):
            step_start = time.time()
            self.log(f"🚀 제출 시도 ({submit_attempt + 1}/{self.MAX_SUBMIT_RETRIES})...")
            try:
                submit_btn = self.driver.find_element(By.ID, "submit")
                self.driver.execute_script("arguments[0].click();", submit_btn)

                self.log("🔔 예약 확인창 대기 중...")
                alert = wait.until(EC.alert_is_present())
                alert_text = alert.text
                self.log(f"🔔 알림창: {alert_text} (소요시간: {time.time()-step_start:.2f}초)")

                # 에러 → 처음부터
                if "정상적으로 예약해 주십시오" in alert_text:
                    self.log("⚠️ 오류! 처음부터 다시 시작.")
                    try:
                        time.sleep(self.SLEEP_INTERVAL)
                        alert.accept()
                        time.sleep(self.SLEEP_INTERVAL)
                        self.driver.refresh()
                    except WebDriverException as e:
                        self.log(f"⚠️ 하드 리스타트 중 오류: {e}")
                    return True  # should_hard_restart

                if not self.simulation_mode:
                    alert.accept()

                    self.log("🔔 결과 확인 대기 중 (3초 타임아웃)...")
                    check_start_time = time.time()
                    success_detected = False
                    should_hard_restart = False

                    while time.time() - check_start_time < 3:
                        # 실패 알림 확인
                        try:
                            alert = self.driver.switch_to.alert
                            alert_text = alert.text
                            self.log(f"🔔 알림창 감지: {alert_text}")

                            if "정상적으로 예약해 주십시오" in alert_text:
                                alert.accept()
                                self.driver.refresh()
                                return True
                            elif "이미" in alert_text or "불가능" in alert_text:
                                self.log("⚠️ 좌석 선점 실패! 즉시 재시도...")
                                alert.accept()
                                self.driver.refresh()
                                return True
                            else:
                                alert.accept()
                        except NoAlertPresentException:
                            pass

                        # 성공 확인
                        try:
                            if "step2.php" in self.driver.current_url:
                                success_detected = True
                                self.log("🎉 예약 성공! (URL: step2.php)")
                                break
                            if "예약 신청이 완료되었습니다" in self.driver.page_source:
                                success_detected = True
                                self.log("🎉 예약 성공! (텍스트 확인)")
                                break
                            tabs = self.driver.find_elements(By.CSS_SELECTOR, self.TAB_SELECTOR)
                            if len(tabs) > self.SUCCESS_TAB_INDEX:
                                if "on" in (tabs[self.SUCCESS_TAB_INDEX].get_attribute("class") or ""):
                                    success_detected = True
                                    self.log("🎉 예약 성공! (탭 활성화 확인)")
                                    break
                        except WebDriverException:
                            pass

                        time.sleep(0.01)

                    if success_detected:
                        self.success_event.set()
                        try:
                            self.log(f"⏱️ 총 소요 시간: {time.time() - process_start_time:.2f}초")
                        except NameError:
                            pass
                        self.log("✅ 예약 봇 실행 시퀀스가 모두 완료되었습니다.")
                        return False

                    self.log("⚠️ 3초 대기 후에도 결과 미확인. 백그라운드 전환 + 새 브라우저...")
                    wait = self._move_to_background(wait)
                    return False  # 외부 루프에서 계속
                else:
                    self.log("🛑 시뮬레이션 종료")
                    try:
                        self.log(f"⏱️ 총 소요 시간: {time.time() - process_start_time:.2f}초")
                    except NameError:
                        pass
                    self.log("✅ 예약 봇 실행 시퀀스가 모두 완료되었습니다.")
                    self.success_event.set()
                    return False

            except (TimeoutException, WebDriverException) as e:
                self.log(f"⚠️ Submit Error: {e}")
                break

        return False

    # ============================================================
    # 3-Step 제출 로직
    # ============================================================
    def _submit_3step(self, wait, process_start_time):
        """3-step 예약 제출 (step3.php에서 완료)"""
        self.log("🚀 [STEP 1] '예약 신청하기' 버튼 클릭 시도...")

        for submit_attempt in range(self.MAX_SUBMIT_RETRIES):
            step_start = time.time()
            self.log(f"🚀 [STEP 1] 제출 시도 ({submit_attempt + 1}/{self.MAX_SUBMIT_RETRIES})...")
            try:
                submit_btn = self.driver.find_element(By.ID, "submit")
                self.driver.execute_script("arguments[0].click();", submit_btn)

                self.log("🔔 [STEP 1] 팝업 알림창 대기 중...")
                alert = wait.until(EC.alert_is_present())
                alert_text = alert.text
                self.log(f"🔔 [STEP 1] 알림창: {alert_text} (소요시간: {time.time()-step_start:.2f}초)")

                if "정상적으로 예약해 주십시오" in alert_text:
                    self.log("⚠️ 오류! 처음부터 다시 시작.")
                    try:
                        time.sleep(self.SLEEP_INTERVAL)
                        alert.accept()
                        time.sleep(self.SLEEP_INTERVAL)
                        self.driver.refresh()
                    except WebDriverException:
                        pass
                    return True

                if "이미" in alert_text or "불가능" in alert_text:
                    self.log("⚠️ 좌석 선점 실패! 즉시 재시도...")
                    alert.accept()
                    self.driver.refresh()
                    return True

                alert.accept()

                # STEP 2 진입 대기
                self.log("⏳ [STEP 2] 진입 대기 중 (3초 폴링)...")
                step2_start_time = time.time()
                step2_entered = False
                detection_method = ""

                while time.time() - step2_start_time < 3:
                    try:
                        if "step2.php" in self.driver.current_url:
                            step2_entered = True
                            detection_method = "URL (step2.php)"
                            self.log("✨ [STEP 2] URL 감지됨 (step2.php)")
                            time.sleep(0.05)
                            break

                        step2_items = self.driver.find_elements(By.CSS_SELECTOR, self.TAB_SELECTOR)
                        if len(step2_items) >= 2 and "on" in (step2_items[1].get_attribute("class") or ""):
                            step2_entered = True
                            detection_method = "탭 활성화"
                            self.log("✨ [STEP 2] 탭 활성화 감지됨")
                            break
                    except WebDriverException:
                        pass
                    time.sleep(0.02)

                if not step2_entered:
                    self.log("⚠️ [STEP 2] 진입 실패 (3초 타임아웃). 백그라운드 + 새 브라우저...")
                    wait = self._move_to_background(wait)
                    return False

                if self.simulation_mode:
                    self.log(f"✨ [ Simulation ] STEP 2 진입 확인 ({detection_method})")
                    self.log("🛑 시뮬레이션 종료")
                    try:
                        self.log(f"⏱️ 총 소요 시간: {time.time() - process_start_time:.2f}초")
                    except NameError:
                        pass
                    self.log("✅ 예약 봇 실행 시퀀스가 모두 완료되었습니다.")
                    self.success_event.set()
                    return False

                # STEP 2 Submit
                self.log("🚀 [STEP 2] '예약 신청하기' 버튼 클릭...")
                try:
                    submit_btn_step2 = WebDriverWait(self.driver, 2).until(
                        EC.element_to_be_clickable((By.ID, "submit"))
                    )
                    self.driver.execute_script("arguments[0].click();", submit_btn_step2)
                    self.log("✨ [STEP 2] 버튼 클릭 성공!")
                except (TimeoutException, WebDriverException) as e2:
                    self.log(f"⚠️ [STEP 2] 버튼 클릭 실패: {e2}")
                    self.log("🔄 백그라운드 모니터링으로 전환 + 새 브라우저...")
                    wait = self._move_to_background(wait)
                    return False

                # STEP 3 성공 대기
                self.log("⏳ [STEP 3] 최종 완료 확인 대기 중 (10초 폴링)...")
                step3_start_time = time.time()
                success_detected = False

                while time.time() - step3_start_time < 10:
                    try:
                        if "step3.php" in self.driver.current_url:
                            success_detected = True
                            self.log("🎉 [STEP 3] 예약 성공! (URL: step3.php)")
                            break
                        if "신청이 완료되었습니다" in self.driver.page_source:
                            success_detected = True
                            self.log("🎉 [STEP 3] 예약 성공! (텍스트 확인)")
                            break
                        tabs = self.driver.find_elements(By.CSS_SELECTOR, self.TAB_SELECTOR)
                        if len(tabs) > self.SUCCESS_TAB_INDEX:
                            if "on" in (tabs[self.SUCCESS_TAB_INDEX].get_attribute("class") or ""):
                                success_detected = True
                                self.log("🎉 [STEP 3] 예약 성공! (탭 활성화)")
                                break
                    except WebDriverException:
                        pass
                    time.sleep(0.1)

                if success_detected:
                    self.success_event.set()
                    try:
                        self.log(f"⏱️ 총 소요 시간: {time.time() - process_start_time:.2f}초")
                    except NameError:
                        pass
                    self.log("✅ 예약 봇 실행 시퀀스가 모두 완료되었습니다.")
                    return False

                self.log("⚠️ [STEP 3] 최종 완료 미확인. 백그라운드 + 새 브라우저...")
                wait = self._move_to_background(wait)
                return False

            except (TimeoutException, WebDriverException) as e:
                self.log(f"⚠️ Submit Error: {e}")
                break

        return False

    # ============================================================
    # 정지
    # ============================================================
    def stop(self):
        """봇 정지 및 리소스 정리"""
        self.is_running = False
        self.success_event.set()
        self.cleanup_all_browsers()
        if self.driver:
            try:
                self.driver.quit()
            except WebDriverException:
                pass
