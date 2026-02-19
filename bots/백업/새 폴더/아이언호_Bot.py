import sys
import json
import time
import argparse
import threading
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from base_bot import BaseFishingBot

class IronBot(BaseFishingBot):
    def __init__(self, config):
        super().__init__(config)
        self.success_event = threading.Event()
        self.browsers = []
        self.max_browsers = 2

    def monitor_browser_for_success(self, driver, browser_id):
        self.log(f"🔍 [브라우저{browser_id}] 백그라운드 모니터링 시작...")
        while not self.success_event.is_set():
            try:
                if "reservation_detail" in driver.current_url:
                    self.log(f"🎉 [브라우저{browser_id}] 예약 성공!")
                    self.success_event.set()
                    return
                page_text = driver.page_source
                if any(kw in page_text for kw in ['예약현황', '예약접수 완료!', '총 상품금액', '예약금']):
                    self.log(f"🎉 [브라우저{browser_id}] 예약 성공!")
                    self.success_event.set()
                    return
            except: pass
            time.sleep(0.1)

    def run(self):
        self.setup_driver()
        target_date_str = self.config.get('target_date', '20260901')
        target_time = self.config.get('target_time', '09:00:00')
        test_mode = self.config.get('test_mode', False)
        self.simulation_mode = self.config.get('simulation_mode', False)
        user_name = self.config.get('user_name', '')
        user_depositor = self.config.get('user_depositor', '')
        user_phone = self.config.get('user_phone', '')
        person_count = int(self.config.get('person_count', 1))

        try:
            d_target = datetime.strptime(target_date_str, "%Y%m%d")
            year_month = d_target.strftime("%Y%m")
            schedule_url = f"https://iron.sunsang24.com/ship/schedule_fleet/{year_month}"
            date_class = f"d{d_target.strftime('%Y-%m-%d')}"
            table_id = date_class
            self.log(f"🎯 Schedule URL: {schedule_url}")
        except Exception as e:
            self.log(f"❌ Date formatting error: {e}")
            return

        self.log(f"🌍 스케줄 페이지 사전 로드 중: {schedule_url}")
        schedule_preloaded = False
        try:
            self.driver.get(schedule_url)
            self.log("✅ 스케줄 페이지 로드 완료")
            try:
                date_link = self.driver.find_element(By.CSS_SELECTOR, f"a.{date_class}")
                if "no_schedule" not in (date_link.get_attribute("class") or ""):
                    date_link.click()
                    wait_sec = 1.2 if test_mode else 1.5
                    time.sleep(wait_sec)
                    schedule_preloaded = True
            except: pass
        except: pass

        if not test_mode:
            self.wait_until_target_time(target_time)
        else:
            self.log("🚀 TEST MODE ACTIVE: Skipping wait!")

        self.log(f"🔥 예약 시도 시작 (반복 루프)")
        reservation_opened = False
        for attempt in range(5000):
            if self.success_event.is_set(): return
            try:
                is_gap_attempt = (test_mode and schedule_preloaded and attempt == 0)
                
                if not is_gap_attempt:
                    self.driver.refresh()
                    try:
                        if not (schedule_preloaded and attempt == 0):
                            date_link = WebDriverWait(self.driver, 0.05).until(EC.element_to_be_clickable((By.CSS_SELECTOR, f"a.{date_class}")))
                            date_link.click()
                    except: continue
                try:
                    reserve_btn = WebDriverWait(self.driver, 1.2).until(EC.presence_of_element_located((By.CSS_SELECTOR, f"table#{table_id} button.btn_ship_reservation")))
                    btn_text = reserve_btn.text.strip()
                    if not btn_text:
                        for _ in range(12):
                            time.sleep(0.1)
                            btn_text = reserve_btn.text.strip()
                            if btn_text: break
                    if "바로예약" in btn_text:
                        self.log(f"✅ 바로예약 버튼 발견!")
                        main_window = self.driver.current_window_handle
                        reserve_btn.click()
                        WebDriverWait(self.driver, 7).until(lambda d: len(d.window_handles) > 1)
                        for window in self.driver.window_handles:
                            if window != main_window:
                                self.driver.switch_to.window(window)
                                break
                        try: WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, "a.plus")))
                        except: pass
                        reservation_opened = True
                        break
                    elif "대기" in btn_text:
                        self.log(f"⏳ 아직 대기 상태... ({attempt+1})")
                except:
                    self.log(f"⏳ 버튼 대기 중... ({attempt+1})")
            except: pass

        if not reservation_opened:
            self.log("❌ 최대 재시도 횟수 초과")
            while True: time.sleep(1)
            return

        while True:
            if self.success_event.is_set(): break
            process_start_time = time.time()
            try:
                radios = self.driver.find_elements(By.CSS_SELECTOR, "input[type='radio'][name='default_schedule_no']")
                self.log(f"🔎 Found {len(radios)} fish type options")
                if radios: self.driver.execute_script("arguments[0].click();", radios[0])
                
                self.log(f"👥 인원 선택 중... ({person_count}명)")
                plus_btns = self.driver.find_elements(By.CSS_SELECTOR, "a.plus")
                if plus_btns:
                    for i in range(person_count): plus_btns[0].click(); time.sleep(0.01)
                    self.log(f"✅ 인원 {person_count}명 설정 완료")

                self.log("✍️ 예약 정보 입력 중...")
                self.driver.find_element(By.CSS_SELECTOR, "input[name='name']").send_keys(user_name)
                self.log(f"✅ 예약자명 입력: {user_name}")
                p2, p3 = "", ""
                if len(user_phone) == 11: p2, p3 = user_phone[3:7], user_phone[7:]
                elif "-" in user_phone: parts = user_phone.split("-"); p2, p3 = parts[1], parts[2] if len(parts)==3 else ("","")
                if p2:
                    self.driver.find_element(By.CSS_SELECTOR, "input[name='phone2']").send_keys(p2)
                    self.driver.find_element(By.CSS_SELECTOR, "input[name='phone3']").send_keys(p3)
                    self.log(f"✅ 전화번호 입력: {p2}-{p3}")
                try:
                    all_check = self.driver.find_element(By.CSS_SELECTOR, "input[name='all_check']")
                    if not all_check.is_selected(): self.driver.execute_script("arguments[0].click();", all_check)
                    self.log("✅ 전체 동의 체크")
                except: pass

                self.log("🚀 예약하기 버튼 클릭...")
                self.driver.execute_script("arguments[0].click();", self.driver.find_element(By.CSS_SELECTOR, "#btn_payment, a.btn_payment"))
                try:
                    alert = WebDriverWait(self.driver, 3).until(EC.alert_is_present())
                    if not self.simulation_mode: alert.accept()
                    else: return
                except: pass

                self.log("🔍 예약 결과 확인 중...")
                check_start = time.time()
                while time.time() - check_start < 10:
                    if "reservation_detail" in self.driver.current_url or any(kw in self.driver.page_source for kw in ['예약현황', '예약접수 완료!']):
                        self.log("🎉 예약 성공!")
                        self.success_event.set()
                        self.log(f"⏱️ 총 소요 시간: {time.time() - process_start_time:.2f}초")
                        while True: time.sleep(1)
                        return
                    time.sleep(0.2)

                browser_count = len(self.browsers) + 1
                self.log(f"⏳ [브라우저{browser_count}] 백그라운드 모니터링 전환...")
                self.browsers.append(self.driver)
                t = threading.Thread(target=self.monitor_browser_for_success, args=(self.driver, browser_count)); t.daemon = True; t.start()
                if len(self.browsers) >= self.max_browsers:
                    while not self.success_event.is_set(): time.sleep(0.5)
                    return
                self.setup_driver()
                self.driver.get(schedule_url)
                try:
                    WebDriverWait(self.driver, 3).until(EC.element_to_be_clickable((By.CSS_SELECTOR, f"a.{date_class}"))).click()
                    WebDriverWait(self.driver, 3).until(EC.presence_of_element_located((By.CSS_SELECTOR, f"table#{table_id} button.btn_ship_reservation"))).click()
                    WebDriverWait(self.driver, 7).until(lambda d: len(d.window_handles) > 1)
                    for w in self.driver.window_handles:
                        if w != self.driver.current_window_handle: self.driver.switch_to.window(w); break
                except: pass
            except Exception as e:
                self.log(f"⚠️ Error: {e}")
        while True: time.sleep(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    with open(args.config, 'r', encoding='utf-8') as f: config = json.load(f)
    bot = IronBot(config)
    try: bot.run()
    except KeyboardInterrupt: bot.stop()