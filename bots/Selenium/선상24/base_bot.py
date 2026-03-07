# -*- coding: utf-8 -*-
"""
선상24 통합 베이스 봇
모든 선상24 봇의 공통 로직을 담당

패턴 분류:
- 패턴 2: 맵핑 없음 + 자리선택 없음 (schedule_fleet 방식)
- 패턴 3: 맵핑 있음 + 자리선택 있음 (reservation_ready 방식)
- 패턴 4: 맵핑 없음 + 자리선택 있음 (schedule_fleet 방식)

선사별 봇은 이 클래스를 상속받아 최소한의 설정만 오버라이드
"""

import os
import sys
import json
import time
import argparse
import threading
import urllib3
import requests
import email.utils
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, WebDriverException,
    StaleElementReferenceException, NoAlertPresentException
)


class SunSang24BaseBot:
    """
    선상24 통합 베이스 봇

    필수 오버라이드:
        SUBDOMAIN       - 선사 서브도메인 (예: "ocpro", "no1", "iron")
        PROVIDER_NAME   - 선사명 (예: "가즈아호", "넘버원호")

    선택 오버라이드:
        HAS_SEAT_SELECTION  - 자리선택 기능 여부 (기본값: False)
        USE_DIRECT_MAPPING  - ID 맵핑 방식 사용 여부 (기본값: False)
        SHIP_NAME           - 선박명 필터링용 (동일 도메인에 여러 선박 있을 때)
        SEAT_PRIORITY       - 좌석 우선순위 리스트 (자리선택 시)
        ID_MAPPING          - 날짜별 ID 맵핑 (reservation_ready 방식)
        MAX_BROWSERS        - 최대 브라우저 수 (기본값: 2)
    """

    # ============================================================
    # 필수 설정 (선사별 오버라이드)
    # ============================================================
    SUBDOMAIN = ""          # 필수: ocpro, no1, iron 등
    PROVIDER_NAME = ""      # 필수: 가즈아호, 넘버원호 등

    # ============================================================
    # 선택 설정
    # ============================================================
    HAS_SEAT_SELECTION = False      # 자리선택 기능 여부
    USE_DIRECT_MAPPING = False      # reservation_ready 방식 사용 여부
    SHIP_NAME = ""                  # 선박명 필터링 (동일 도메인 여러 선박)
    SEAT_PRIORITY = []              # 좌석 우선순위
    ID_MAPPING = {}                 # 월별 ID 맵핑 {month: {day: id}}
    MAX_BROWSERS = 2                # 최대 브라우저 수
    MAX_RETRIES = 5000              # 최대 재시도 횟수

    # ============================================================
    # 초기화
    # ============================================================
    def __init__(self, config):
        self.config = config
        self.driver = None
        self.log_callback = None
        self.is_running = True
        self.success_event = threading.Event()
        self.browsers = []
        self.browser_threads = []

        # Windows 콘솔 UTF-8 인코딩 설정
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except:
            pass

        # 로그 파일 설정
        self.log_file = None
        self._setup_log_file()

    def _setup_log_file(self):
        """로그 파일 초기화"""
        try:
            log_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'Log')
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)

            now = datetime.now()
            time_str = now.strftime("%Y_%m월%d일_%H시%M분%S초")

            provider = self.PROVIDER_NAME or self.config.get('provider', 'Unknown')
            t_date = self.config.get('target_date', '00000000')
            if len(t_date) == 8 and t_date.isdigit():
                t_date_fmt = f"{t_date[:4]}_{t_date[4:6]}_{t_date[6:]}"
            else:
                t_date_fmt = t_date

            self.log_file = os.path.join(log_dir, f"{time_str}_선상24_{provider}_{t_date_fmt}_.txt")

            # 헤더 작성
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(f"=== SunSang24 Bot Log Started: {now.strftime('%Y-%m-%d_%H:%M:%S')} ===\n")
                f.write(f"항구: {self.config.get('port', 'Unknown')}\n")
                f.write(f"선사: {provider}\n")
                f.write(f"예약날짜: {t_date}\n")
                f.write(f"예약시간: {self.config.get('target_time', '')}\n")
                f.write(f"예약자: {self.config.get('user_name', '')}\n")
                f.write(f"전화번호: {self.config.get('user_phone', '')}\n")
                f.write("-" * 30 + "\n\n")
        except Exception as e:
            print(f"Failed to setup log file: {e}")

    def log(self, msg):
        """로그 출력"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-4]
        formatted_msg = f"[{timestamp}] {msg}"

        # 콘솔 출력 (UTF-8 강제)
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except:
            pass
        try:
            print(formatted_msg, flush=True)
        except UnicodeEncodeError:
            try:
                print(formatted_msg.encode('utf-8').decode('utf-8'), flush=True)
            except:
                pass
        except Exception:
            pass

        # GUI 콜백
        if self.log_callback:
            try:
                self.log_callback(formatted_msg)
            except Exception:
                pass

        # 파일 기록
        if self.log_file:
            try:
                with open(self.log_file, "a", encoding="utf-8") as f:
                    f.write(formatted_msg + "\n")
            except Exception:
                pass

    # ============================================================
    # 드라이버 설정
    # ============================================================
    def setup_driver(self):
        """Chrome 드라이버 초기화"""
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
        chrome_options.page_load_strategy = 'eager'

        service = Service()
        self.driver = webdriver.Chrome(service=service, options=chrome_options)

        # PID 저장
        try:
            import psutil
            driver_pid = self.driver.service.process.pid
            driver_proc = psutil.Process(driver_pid)
            chrome_pids = [child.pid for child in driver_proc.children(recursive=True)
                          if 'chrome' in child.name().lower()]

            pid_file = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'bot_chrome_pids.txt')
            os.makedirs(os.path.dirname(pid_file), exist_ok=True)
            with open(pid_file, 'a', encoding='utf-8') as f:
                for pid in chrome_pids:
                    f.write(f"{pid}\n")
            self.log(f"📝 Chrome PID 저장됨: {chrome_pids}")
        except Exception as e:
            self.log(f"⚠️ Chrome PID 저장 실패 (무시됨): {e}")

        # 창 위치/크기 설정
        if window_x is not None and window_y is not None:
            self.driver.set_window_position(window_x, window_y)
        if window_width is not None and window_height is not None:
            self.driver.set_window_size(window_width, window_height)

        # webdriver 감지 우회
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        })

    # ============================================================
    # 시간 관련
    # ============================================================
    def get_server_time(self, url):
        """서버 시간 확인"""
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
        """목표 시간까지 대기"""
        now = datetime.now()
        try:
            target_dt = datetime.strptime(f"{now.year}-{now.month}-{now.day} {target_time_str}", "%Y-%m-%d %H:%M:%S.%f")
        except ValueError:
            target_dt = datetime.strptime(f"{now.year}-{now.month}-{now.day} {target_time_str}", "%Y-%m-%d %H:%M:%S")

        if target_dt < now:
            target_dt = target_dt + timedelta(days=1)

        self.log(f"⏰ 목표 시간 대기 중: {target_dt}")

        last_printed_sec = -1
        first_display = True
        while self.is_running:
            now = datetime.now()
            diff = (target_dt - now).total_seconds()

            if diff <= 0:
                self.log("🚀 예약 오픈 시간입니다! 작업을 시작합니다!")
                break

            mins = int(diff // 60)
            secs = int(diff % 60)
            current_sec = mins * 60 + secs

            # 로그 출력 조건
            if current_sec != last_printed_sec:
                should_print = False

                if first_display:
                    # 처음 남은 시간 표시
                    should_print = True
                    first_display = False
                elif current_sec <= 5:
                    # 마지막 5초: 매초
                    should_print = True
                elif current_sec <= 60 and current_sec in [10, 30]:
                    # 1분 이하: 10초, 30초
                    should_print = True
                elif current_sec > 60 and current_sec % 300 == 0:
                    # 1분 초과: 5분 간격
                    should_print = True
                elif current_sec == 60:
                    # 1분 정각
                    should_print = True

                if should_print:
                    if current_sec <= 5:
                        self.log(f"⏳ {secs}초")
                    else:
                        self.log(f"⏳ 남은 시간: {mins}분 {secs:02d}초")

                last_printed_sec = current_sec

            if diff > 10:
                time.sleep(0.5)
            elif diff > 1:
                time.sleep(0.1)
            else:
                time.sleep(0.01)

    # ============================================================
    # 성공 모니터링
    # ============================================================
    def monitor_browser_for_success(self, driver, browser_id):
        """백그라운드 브라우저 성공 모니터링"""
        self.log(f"🔍 [브라우저{browser_id}] 백그라운드 모니터링 시작...")
        while not self.success_event.is_set():
            try:
                if "reservation_detail" in driver.current_url:
                    self.log(f"🎉 [브라우저{browser_id}] 예약 성공! (URL)")
                    self.success_event.set()
                    return
                page_text = driver.page_source
                if any(kw in page_text for kw in ['예약현황', '예약접수 완료!', '총 상품금액', '예약금']):
                    self.log(f"🎉 [브라우저{browser_id}] 예약 성공! (텍스트)")
                    self.success_event.set()
                    return
            except:
                pass
            time.sleep(0.1)
        self.log(f"🛑 [브라우저{browser_id}] 모니터링 중지")

    # ============================================================
    # 예약 오픈 확인
    # ============================================================
    def _check_reservation_open(self):
        """
        예약이 실제로 오픈되었는지 확인 (전체동의 방식)

        전체동의 클릭 → 하위 체크박스(agree_rule[]) 활성화 여부로 판단
        - 오픈됨: 전체동의 클릭 시 하위 3개 체크박스 모두 체크됨 (체크 상태 유지)
        - 미오픈: 전체동의 클릭해도 하위 체크박스 체크 안됨

        Returns:
            tuple: (bool 오픈여부, str 상세사유)
        """
        try:
            all_check = self.driver.find_element(By.CSS_SELECTOR, "input[name='all_check']")
        except Exception as e:
            return False, "동의 체크박스 미활성화"

        try:
            # 클릭 전 하위 체크박스 상태 저장
            sub_checks = self.driver.find_elements(By.CSS_SELECTOR, "input[name='agree_rule[]']")
            if not sub_checks:
                return False, "동의 체크박스 미활성화"

            before_selected = sum(1 for cb in sub_checks if cb.is_selected())

            # 전체동의 클릭
            self.driver.execute_script("arguments[0].click();", all_check)
            time.sleep(0.05)

            # 클릭 후 하위 체크박스 상태 확인
            after_selected = sum(1 for cb in sub_checks if cb.is_selected())

            # 하위 체크박스가 체크되었으면 오픈됨 (체크 상태 유지 - 원복 안함)
            if after_selected > before_selected:
                self.log("✅ 전체 동의 체크 완료 (오픈 확인)")
                return True, "오픈됨"

            return False, "동의 체크박스 미활성화"
        except Exception as e:
            return False, "동의 체크박스 미활성화"

    # ============================================================
    # URL 생성
    # ============================================================
    def get_schedule_url(self, year_month):
        """스케줄 페이지 URL 생성"""
        return f"https://{self.SUBDOMAIN}.sunsang24.com/ship/schedule_fleet/{year_month}"

    def get_reservation_url(self, target_id):
        """예약 페이지 URL 생성 (ID 맵핑 방식)"""
        return f"https://{self.SUBDOMAIN}.sunsang24.com/mypage/reservation_ready/{target_id}"

    def get_target_id(self, target_date):
        """
        날짜에 해당하는 예약 ID 계산

        지원하는 ID_MAPPING 형식:
        1. 월별 base_id: {9: 1650579}  → ID = base_id + (day - 1)
        2. 월별 dict: {9: {1: 1506258, 2: 1506259, ...}}  → ID = dict[day]
        3. delta_days 방식: {'base_date': '20251219', 'base_id': 1535125}
        4. 일별 튜플: {(7, 9): 1724015, (7, 10): 1724016}  → ID = dict[(month, day)]
        """
        if not self.ID_MAPPING:
            return None

        d_target = datetime.strptime(target_date, "%Y%m%d")
        month = d_target.month
        day = d_target.day

        # 일별 튜플 방식: (월, 일) 키 확인
        tuple_key = (month, day)
        if tuple_key in self.ID_MAPPING:
            return self.ID_MAPPING[tuple_key]

        # delta_days 방식 (기가호 등)
        if 'base_date' in self.ID_MAPPING and 'base_id' in self.ID_MAPPING:
            d_base = datetime.strptime(self.ID_MAPPING['base_date'], "%Y%m%d")
            delta = (d_target - d_base).days
            return self.ID_MAPPING['base_id'] + delta

        # 월별 매핑
        if month not in self.ID_MAPPING:
            return None

        month_mapping = self.ID_MAPPING[month]

        # dict 형태 (일별 매핑)
        if isinstance(month_mapping, dict):
            if day in month_mapping:
                return month_mapping[day]
            return None

        # int 형태 (base_id + day - 1)
        if isinstance(month_mapping, int):
            return month_mapping + (day - 1)

        return None

    # ============================================================
    # 메인 실행 로직
    # ============================================================
    def run(self):
        """메인 실행"""
        self.setup_driver()

        # 설정값 로드
        target_date_str = self.config.get('target_date', '20260901')
        target_time = self.config.get('target_time', '09:00:00')
        test_mode = self.config.get('test_mode', False)
        self.simulation_mode = self.config.get('simulation_mode', False)
        user_name = self.config.get('user_name', '')
        user_phone = self.config.get('user_phone', '')
        person_count = int(self.config.get('person_count', 1))

        # URL 계산
        try:
            d_target = datetime.strptime(target_date_str, "%Y%m%d")
            year_month = d_target.strftime("%Y%m")
            date_class = f"d{d_target.strftime('%Y-%m-%d')}"
            table_id = date_class

            if self.USE_DIRECT_MAPPING:
                target_id = self.get_target_id(target_date_str)
                if target_id is None:
                    self.log(f"❌ {d_target.month}월은 ID 매핑이 없습니다.")
                    return
                url = self.get_reservation_url(target_id)
                self.log(f"🎯 Target URL: {url} (ID: {target_id})")
            else:
                schedule_url = self.get_schedule_url(year_month)
                self.log(f"🎯 Schedule URL: {schedule_url}")
        except Exception as e:
            self.log(f"❌ Date formatting error: {e}")
            return

        # 분기: 맵핑 방식 vs 스케줄 방식
        if self.USE_DIRECT_MAPPING:
            self._run_direct_mapping(url, target_time, test_mode, user_name, user_phone, person_count)
        else:
            self._run_schedule_fleet(schedule_url, date_class, table_id, target_time, test_mode, user_name, user_phone, person_count)

    # ============================================================
    # 스케줄 방식 (패턴 2, 4)
    # ============================================================
    def _run_schedule_fleet(self, schedule_url, date_class, table_id, target_time, test_mode, user_name, user_phone, person_count):
        """schedule_fleet 방식 실행"""

        # 전체 예약 시작 시간 기록
        reservation_start_time = time.time()

        # 사전 로드
        preload_start = time.time()
        self.log(f"🌍 스케줄 페이지 사전 로드 중: {schedule_url}")
        schedule_preloaded = False
        try:
            self.driver.get(schedule_url)
            preload_elapsed = time.time() - preload_start
            self.log(f"✅ 스케줄 페이지 로드 완료 (⏱️ {preload_elapsed:.3f}초)")
            try:
                date_link = self.driver.find_element(By.CSS_SELECTOR, f"a.{date_class}")
                if "no_schedule" not in (date_link.get_attribute("class") or ""):
                    self.log(f"📅 스케줄 활성화 상태! 날짜 미리 클릭")
                    date_link.click()
                    wait_sec = 1.2 if test_mode else 1.5
                    time.sleep(wait_sec)
                    schedule_preloaded = True
            except:
                pass
        except Exception as e:
            self.log(f"⚠️ 사전 로드 실패: {e}")

        # 시간 대기
        if not test_mode:
            self.log(f"⏰ 실행 예약 시간: {target_time}...")
            self.wait_until_target_time(target_time)
        else:
            self.log("🚀 TEST MODE: 대기 없이 즉시 실행!")

        # 바로예약 버튼 찾기 루프
        btn_search_start = time.time()
        self.log(f"🔥 예약 시도 시작")
        reservation_opened = False
        retry_count = 0

        for attempt in range(self.MAX_RETRIES):
            if self.success_event.is_set():
                return

            try:
                is_gap_attempt = (test_mode and schedule_preloaded and attempt == 0)

                if not is_gap_attempt:
                    self.driver.refresh()
                    try:
                        if not (schedule_preloaded and attempt == 0):
                            WebDriverWait(self.driver, 0.05).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, f"a.{date_class}"))
                            ).click()
                    except:
                        retry_count += 1
                        print(f"\r⏳ 날짜 링크 대기 중... ({retry_count}회)", end="", flush=True)
                        continue

                try:
                    # 선박명 필터링 (동일 도메인에 여러 선박)
                    reserve_btn = None
                    if self.SHIP_NAME:
                        ship_tables = self.driver.find_elements(By.CSS_SELECTOR, f"table#{table_id} td.ships_warp table.ship_unit")
                        for table in ship_tables:
                            try:
                                title_div = table.find_element(By.CSS_SELECTOR, "div.title")
                                if self.SHIP_NAME in title_div.text:
                                    reserve_btn = table.find_element(By.CSS_SELECTOR, "button.btn_ship_reservation")
                                    break
                            except:
                                continue

                    if not reserve_btn:
                        reserve_btn = WebDriverWait(self.driver, 1.2).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, f"table#{table_id} button.btn_ship_reservation"))
                        )

                    btn_text = reserve_btn.text.strip()
                    if not btn_text:
                        for _ in range(12):
                            time.sleep(0.1)
                            btn_text = reserve_btn.text.strip()
                            if btn_text:
                                break

                    if "바로예약" in btn_text:
                        btn_search_elapsed = time.time() - btn_search_start
                        if retry_count > 0:
                            print()
                            self.log(f"✅ 바로예약 버튼 발견! (재시도 {retry_count}회, ⏱️ {btn_search_elapsed:.3f}초)")
                        else:
                            self.log(f"✅ 바로예약 버튼 발견! (⏱️ {btn_search_elapsed:.3f}초)")

                        main_window = self.driver.current_window_handle
                        reserve_btn.click()
                        WebDriverWait(self.driver, 7).until(lambda d: len(d.window_handles) > 1)

                        for w in self.driver.window_handles:
                            if w != main_window:
                                self.driver.switch_to.window(w)
                                break

                        try:
                            WebDriverWait(self.driver, 5).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, "a.plus"))
                            )
                        except:
                            pass

                        reservation_opened = True
                        break
                    else:
                        retry_count += 1
                        print(f"\r⏳ 대기 상태... ({retry_count}회)", end="", flush=True)
                except:
                    retry_count += 1
                    print(f"\r⏳ 버튼 대기 중... ({retry_count}회)", end="", flush=True)
            except:
                pass

        if not reservation_opened:
            print()
            self.log("❌ 최대 재시도 횟수 초과")
            while True:
                time.sleep(1)
            return

        # 예약 정보 입력 루프
        self._reservation_loop(schedule_url, date_class, table_id, user_name, user_phone, person_count)

    # ============================================================
    # ID 맵핑 방식 (패턴 3)
    # ============================================================
    def _run_direct_mapping(self, url, target_time, test_mode, user_name, user_phone, person_count):
        """reservation_ready 방식 실행"""

        # 전체 예약 시작 시간 기록
        reservation_start_time = time.time()

        # 사전 로드
        preload_start = time.time()
        self.log(f"🌍 페이지 사전 로드 중: {url}")
        try:
            self.driver.get(url)
            try:
                alert = WebDriverWait(self.driver, 1).until(EC.alert_is_present())
                self.log(f"🔔 사전 로드 시 알림: {alert.text}")
                alert.accept()
            except:
                pass
            preload_elapsed = time.time() - preload_start
            self.log(f"✅ 사전 로드 완료 (⏱️ {preload_elapsed:.3f}초). 오픈 시간을 기다립니다...")
        except Exception as e:
            self.log(f"⚠️ 사전 로드 실패: {e}")

        # 시간 대기
        if not test_mode:
            self.log(f"⏰ 실행 예약 시간: {target_time}...")
            self.wait_until_target_time(target_time)
        else:
            self.log("🚀 TEST MODE: 대기 없이 즉시 실행!")

        # 예약 페이지 접근 루프
        page_access_start = time.time()
        self.log(f"🔥 예약 시도 시작: {url}")
        step1_success = False
        retry_count = 0

        for attempt in range(self.MAX_RETRIES):
            try:
                self.driver.get(url)

                # 알림창 처리
                try:
                    alert = WebDriverWait(self.driver, 0.05).until(EC.alert_is_present())
                    alert_text = alert.text
                    if "잘못된" in alert_text or "배일정" in alert_text or "존재하지" in alert_text:
                        retry_count += 1
                        print(f"\r⚠️ 서버 미오픈 [Alert: {alert_text[:30]}] ({retry_count}회)", end="", flush=True)
                        alert.accept()
                        time.sleep(0.2)
                        continue
                    else:
                        alert.accept()
                except:
                    pass

                if "Bad Gateway" in self.driver.title:
                    retry_count += 1
                    print(f"\r⚠️ Bad Gateway... ({retry_count}회)", end="", flush=True)
                    continue

                if "login" in self.driver.current_url:
                    retry_count += 1
                    print(f"\r⚠️ 로그인 리다이렉트... ({retry_count}회)", end="", flush=True)
                    time.sleep(0.01)
                    continue

                # 페이지 준비 확인
                if "reservation_ready" in self.driver.current_url:
                    page_text = self.driver.page_source
                    if any(kw in page_text for kw in ['계좌번호', '환불계좌']):
                        # 실제 오픈 여부 확인: 전체동의 클릭 → 하위 체크박스 활성화 확인
                        is_open, reason = self._check_reservation_open()
                        if is_open:
                            page_access_elapsed = time.time() - page_access_start
                            if retry_count > 0:
                                print()
                                self.log(f"📄 예약 페이지 오픈 확인! (재시도 {retry_count}회, ⏱️ {page_access_elapsed:.3f}초)")
                            else:
                                self.log(f"📄 예약 페이지 오픈 확인! (⏱️ {page_access_elapsed:.3f}초)")
                            step1_success = True
                            break
                        else:
                            retry_count += 1
                            print(f"\r⏳ 예약 미오픈 [{reason}] ({retry_count}회)", end="", flush=True)
                            continue

                retry_count += 1
                print(f"\r⏳ 페이지 준비 안됨... ({retry_count}회)", end="", flush=True)

            except Exception as e:
                retry_count += 1
                print(f"\r⚠️ 오류 발생... ({retry_count}회)", end="", flush=True)

        if not step1_success:
            print()
            self.log("❌ 최대 재시도 횟수 초과")
            while True:
                time.sleep(1)
            return

        # 예약 정보 입력
        self._reservation_loop_direct(url, user_name, user_phone, person_count)

    # ============================================================
    # 예약 정보 입력 (공통)
    # ============================================================
    def _reservation_loop(self, schedule_url, date_class, table_id, user_name, user_phone, person_count):
        """예약 정보 입력 루프 (schedule_fleet 방식)"""

        while True:
            if self.success_event.is_set():
                break

            process_start_time = time.time()
            self.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            self.log("🏁 예약 프로세스 시작")

            try:
                # 낚시 종류 선택
                step_start = time.time()
                radios = self.driver.find_elements(By.CSS_SELECTOR, "input[type='radio'][name='default_schedule_no']")
                if radios:
                    self.driver.execute_script("arguments[0].click();", radios[0])
                    elapsed = time.time() - step_start
                    self.log(f"🎣 낚시 종류 선택 완료 ({len(radios)}개 옵션) (⏱️ {elapsed:.3f}초)")

                # 1. 인원 선택 (+버튼)
                step_start = time.time()
                plus_btns = self.driver.find_elements(By.CSS_SELECTOR, "a.plus")
                if plus_btns:
                    for _ in range(person_count):
                        plus_btns[0].click()
                        time.sleep(0.01)
                    elapsed = time.time() - step_start
                    self.log(f"👥 인원 {person_count}명 설정 완료 (⏱️ {elapsed:.3f}초)")

                # 2. 좌석 선택 (HAS_SEAT_SELECTION이 True인 경우에만)
                if self.HAS_SEAT_SELECTION:
                    has_seat = False
                    try:
                        page_text = self.driver.find_element(By.TAG_NAME, "body").text
                        has_seat = "자리선택" in page_text or "전체선택" in page_text
                    except:
                        pass
                    if has_seat:
                        self.log("📌 좌석 선택 기능 있음")
                        step_start = time.time()
                        self._select_seats(person_count)
                        elapsed = time.time() - step_start
                        self.log(f"💺 좌석 선택 소요시간: ⏱️ {elapsed:.3f}초")

                # 정보 입력
                step_start = time.time()
                self._fill_reservation_info(user_name, user_phone)
                elapsed = time.time() - step_start
                self.log(f"✍️ 정보 입력 소요시간: ⏱️ {elapsed:.3f}초")

                # 제출
                step_start = time.time()
                success = self._submit_reservation(process_start_time)
                if success:
                    return

                # 실패 시 백그라운드 전환 및 새 브라우저
                self._handle_retry(schedule_url, date_class, table_id)

            except Exception as e:
                self.log(f"⚠️ Error: {e}")

        while True:
            time.sleep(1)

    def _reservation_loop_direct(self, url, user_name, user_phone, person_count):
        """예약 정보 입력 루프 (reservation_ready 방식)"""

        while True:
            if self.success_event.is_set():
                break

            process_start_time = time.time()
            self.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            self.log("🏁 예약 프로세스 시작")

            try:
                # 낚시 종류 선택
                step_start = time.time()
                radios = self.driver.find_elements(By.CSS_SELECTOR, "input[type='radio'][name='default_schedule_no']")
                if radios:
                    self.driver.execute_script("arguments[0].click();", radios[0])
                    elapsed = time.time() - step_start
                    self.log(f"🎣 낚시 종류 선택 완료 (⏱️ {elapsed:.3f}초)")

                # 1. 인원 선택 (+버튼)
                step_start = time.time()
                plus_btns = self.driver.find_elements(By.CSS_SELECTOR, "a.plus")
                if plus_btns:
                    for _ in range(person_count):
                        plus_btns[0].click()
                        time.sleep(0.01)
                    elapsed = time.time() - step_start
                    self.log(f"👥 인원 {person_count}명 설정 완료 (⏱️ {elapsed:.3f}초)")

                # 2. 좌석 선택 (HAS_SEAT_SELECTION이 True인 경우에만)
                if self.HAS_SEAT_SELECTION:
                    step_start = time.time()
                    self._select_seats(person_count)
                    elapsed = time.time() - step_start
                    self.log(f"💺 좌석 선택 소요시간: ⏱️ {elapsed:.3f}초")

                # 정보 입력
                step_start = time.time()
                self._fill_reservation_info(user_name, user_phone)
                elapsed = time.time() - step_start
                self.log(f"✍️ 정보 입력 소요시간: ⏱️ {elapsed:.3f}초")

                # 제출
                step_start = time.time()
                success = self._submit_reservation(process_start_time)
                if success:
                    return

                # 실패 시 백그라운드 전환 및 새 브라우저
                self._handle_retry_direct(url)

            except Exception as e:
                self.log(f"⚠️ Error: {e}")

        while True:
            time.sleep(1)

    # ============================================================
    # 좌석 선택
    # ============================================================
    def _select_seats(self, person_count):
        """좌석 선택"""
        seat_priority = self.SEAT_PRIORITY or ['10', '11', '1', '20', '9', '12', '2', '19', '21', '23', '22', '24']
        selected = 0

        self.log(f"💺 좌석 선택 중... (우선순위: {', '.join(seat_priority[:5])}...)")

        # 우선순위 좌석 선택
        for seat in seat_priority:
            if selected >= person_count:
                break
            try:
                checkbox = self.driver.find_element(By.CSS_SELECTOR, f"input[name='select_seat_nos[]'][value='{seat}']")
                if checkbox.is_enabled() and not checkbox.is_selected():
                    label = self.driver.find_element(By.CSS_SELECTOR, f"label[for='select_seat_nos_num_{seat}']")
                    self.driver.execute_script("arguments[0].click();", label)
                    selected += 1
                    self.log(f"  ✅ {seat}번 좌석 선택")
            except:
                continue

        # 우선순위 좌석 부족 시 나머지 좌석 선택
        if selected < person_count:
            self.log(f"⚠️ 우선순위 좌석 부족, 남은 좌석 선택 중...")
            try:
                all_checkboxes = self.driver.find_elements(By.CSS_SELECTOR, "input[name='select_seat_nos[]']")
                for cb in all_checkboxes:
                    if selected >= person_count:
                        break
                    try:
                        if cb.is_enabled() and not cb.is_selected():
                            seat_val = cb.get_attribute("value")
                            label = self.driver.find_element(By.CSS_SELECTOR, f"label[for='select_seat_nos_num_{seat_val}']")
                            self.driver.execute_script("arguments[0].click();", label)
                            selected += 1
                            self.log(f"  ✅ {seat_val}번 좌석 선택 (대체)")
                    except:
                        continue
            except:
                pass

        self.log(f"💺 총 {selected}석 선택 완료")

    # ============================================================
    # 정보 입력
    # ============================================================
    def _fill_reservation_info(self, user_name, user_phone):
        """예약 정보 입력"""
        self.log("✍️ 예약 정보 입력 중...")

        # 예약자명
        try:
            name_input = self.driver.find_element(By.CSS_SELECTOR, "input[name='name']")
            name_input.clear()
            name_input.send_keys(user_name)
            self.log(f"✅ 예약자명: {user_name}")
        except:
            pass

        # 전화번호
        try:
            p2, p3 = "", ""
            if len(user_phone) == 11:
                p2, p3 = user_phone[3:7], user_phone[7:]
            elif "-" in user_phone:
                parts = user_phone.split("-")
                if len(parts) == 3:
                    p2, p3 = parts[1], parts[2]

            if p2:
                self.driver.find_element(By.CSS_SELECTOR, "input[name='phone2']").send_keys(p2)
                self.driver.find_element(By.CSS_SELECTOR, "input[name='phone3']").send_keys(p3)
                self.log(f"✅ 전화번호 입력 완료")
        except:
            pass

        # 전체 동의 (이미 _check_reservation_open에서 체크했으면 스킵)
        try:
            all_check = self.driver.find_element(By.CSS_SELECTOR, "input[name='all_check']")
            if not all_check.is_selected():
                self.driver.execute_script("arguments[0].click();", all_check)
                self.log("✅ 전체 동의 체크")
        except:
            pass

    # ============================================================
    # 제출
    # ============================================================
    def _submit_reservation(self, process_start_time):
        """예약 제출 및 결과 확인"""
        self.log("🚀 예약하기 버튼 클릭...")

        try:
            submit_btn = self.driver.find_element(By.CSS_SELECTOR, "#btn_payment, a.btn_payment")
            self.driver.execute_script("arguments[0].click();", submit_btn)
        except:
            pass

        # Alert 처리
        try:
            alert = WebDriverWait(self.driver, 3).until(EC.alert_is_present())
            alert_text = alert.text
            self.log(f"🔔 Alert: {alert_text}")
            if not self.simulation_mode:
                alert.accept()
            else:
                # 시뮬레이션 모드: 소요시간 표시 후 종료
                self.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                self.log("🎉🎉🎉 시뮬레이션 완료! 🎉🎉🎉")
                self.success_event.set()
                elapsed = time.time() - process_start_time
                self.log(f"⏱️ 예약 프로세스 총 소요시간: {elapsed:.3f}초")
                self.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                return True
        except:
            pass

        # 결과 확인
        self.log("🔍 예약 결과 확인 중...")
        check_start = time.time()
        while time.time() - check_start < 10:
            try:
                if "reservation_detail" in self.driver.current_url:
                    submit_elapsed = time.time() - check_start
                    self.log(f"🚀 제출 및 결과 확인 소요시간: ⏱️ {submit_elapsed:.3f}초")
                    self.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                    self.log("🎉🎉🎉 예약 성공! 🎉🎉🎉")
                    self.success_event.set()
                    elapsed = time.time() - process_start_time
                    self.log(f"⏱️ 예약 프로세스 총 소요시간: {elapsed:.3f}초")
                    self.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                    while True:
                        time.sleep(1)
                    return True

                page_text = self.driver.page_source
                if any(kw in page_text for kw in ['예약현황', '예약접수 완료!']):
                    submit_elapsed = time.time() - check_start
                    self.log(f"🚀 제출 및 결과 확인 소요시간: ⏱️ {submit_elapsed:.3f}초")
                    self.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                    self.log("🎉🎉🎉 예약 성공! 🎉🎉🎉")
                    self.success_event.set()
                    elapsed = time.time() - process_start_time
                    self.log(f"⏱️ 예약 프로세스 총 소요시간: {elapsed:.3f}초")
                    self.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                    while True:
                        time.sleep(1)
                    return True
            except:
                pass
            time.sleep(0.2)

        return False

    # ============================================================
    # 재시도 처리
    # ============================================================
    def _handle_retry(self, schedule_url, date_class, table_id):
        """재시도 처리 (schedule_fleet 방식)"""
        browser_count = len(self.browsers) + 1
        self.log(f"⏳ [브라우저{browser_count}] 백그라운드 모니터링 전환...")

        self.browsers.append(self.driver)
        t = threading.Thread(target=self.monitor_browser_for_success, args=(self.driver, browser_count))
        t.daemon = True
        t.start()
        self.browser_threads.append(t)

        if len(self.browsers) >= self.MAX_BROWSERS:
            self.log(f"⏳ 최대 브라우저 수 도달. 모니터링 대기...")
            while not self.success_event.is_set():
                time.sleep(0.5)
            return

        # 새 브라우저로 재시도
        self.log(f"🔄 새 브라우저 재시도...")
        self.setup_driver()
        self.driver.get(schedule_url)

        try:
            WebDriverWait(self.driver, 3).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, f"a.{date_class}"))
            ).click()
            WebDriverWait(self.driver, 3).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, f"table#{table_id} button.btn_ship_reservation"))
            ).click()
            WebDriverWait(self.driver, 7).until(lambda d: len(d.window_handles) > 1)

            for w in self.driver.window_handles:
                if w != self.driver.current_window_handle:
                    self.driver.switch_to.window(w)
                    break
        except:
            pass

    def _handle_retry_direct(self, url):
        """재시도 처리 (reservation_ready 방식)"""
        browser_count = len(self.browsers) + 1
        self.log(f"⏳ [브라우저{browser_count}] 백그라운드 모니터링 전환...")

        self.browsers.append(self.driver)
        t = threading.Thread(target=self.monitor_browser_for_success, args=(self.driver, browser_count))
        t.daemon = True
        t.start()
        self.browser_threads.append(t)

        if len(self.browsers) >= self.MAX_BROWSERS:
            self.log(f"⏳ 최대 브라우저 수 도달. 모니터링 대기...")
            while not self.success_event.is_set():
                time.sleep(0.5)
            return

        # 새 브라우저로 재시도
        self.log(f"🔄 새 브라우저 재시도...")
        self.setup_driver()
        self.driver.get(url)

    # ============================================================
    # 종료
    # ============================================================
    def stop(self):
        """봇 종료"""
        self.is_running = False
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass


# ============================================================
# 메인 실행
# ============================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="Config JSON file path")
    args = parser.parse_args()

    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)

    bot = SunSang24BaseBot(config)
    try:
        bot.run()
    except KeyboardInterrupt:
        bot.stop()
