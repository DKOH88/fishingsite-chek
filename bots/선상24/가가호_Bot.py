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

class GagahoBot(BaseFishingBot):
    def __init__(self, config):
        super().__init__(config)
        self.success_event = threading.Event()
        self.browsers = []
        self.max_browsers = 2

    def monitor_browser_for_success(self, driver, browser_id):
        while not self.success_event.is_set():
            try:
                if "reservation_detail" in driver.current_url or any(kw in driver.page_source for kw in ['예약현황', '예약접수 완료!']):
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
        user_phone = self.config.get('user_phone', '')
        person_count = int(self.config.get('person_count', 1))

        try:
            d_target = datetime.strptime(target_date_str, "%Y%m%d")
            schedule_url = f"https://gagaho.sunsang24.com/ship/schedule_fleet/{d_target.strftime('%Y%m')}"
            date_class = f"d{d_target.strftime('%Y-%m-%d')}"
            table_id = date_class
            self.log(f"🎯 Schedule URL: {schedule_url}")
        except Exception as e:
            self.log(f"❌ Error: {e}")
            return

        self.log(f"🌍 스케줄 페이지 사전 로드 중...")
        try:
            self.driver.get(schedule_url)
            try:
                date_link = self.driver.find_element(By.CSS_SELECTOR, f"a.{date_class}")
                if "no_schedule" not in (date_link.get_attribute("class") or ""):
                    date_link.click()
                    wait_sec = 1.2 if test_mode else 1.5
                    time.sleep(wait_sec)
                    schedule_preloaded = True
            except: pass
        except: pass

        if not test_mode: self.wait_until_target_time(target_time)
        else: self.log("🚀 TEST MODE")

        self.log(f"🔥 예약 시도 시작")
        reservation_opened = False
        for attempt in range(5000):
            if self.success_event.is_set(): return
            try:
                if not (test_mode and schedule_preloaded and attempt == 0):
                    self.driver.refresh()
                try:
                    if not (schedule_preloaded and attempt == 0):
                        WebDriverWait(self.driver, 0.05).until(EC.element_to_be_clickable((By.CSS_SELECTOR, f"a.{date_class}"))).click()
                except: continue
                
                try:
                    # 가가호 테이블에서 바로예약 버튼 찾기 (선박명 필터링)
                    date_table = self.driver.find_element(By.CSS_SELECTOR, f"table#{table_id}")
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", date_table)
                    ship_tables = date_table.find_elements(By.CSS_SELECTOR, "table.ship_unit")
                    reserve_btn = None
                    for ship_table in ship_tables:
                        try:
                            title = ship_table.find_element(By.CSS_SELECTOR, "div.title").text
                            if "가가호" in title:
                                self.log(f"🚢 가가호 테이블 발견!")
                                reserve_btn = ship_table.find_element(By.CSS_SELECTOR, "button.btn_ship_reservation")
                                break
                        except: continue
                    
                    if not reserve_btn:
                        reserve_btn = WebDriverWait(self.driver, 1.2).until(EC.presence_of_element_located((By.CSS_SELECTOR, f"table#{table_id} button.btn_ship_reservation")))
                    
                    if "바로예약" in reserve_btn.text:
                        self.log(f"✅ 가가호 바로예약 버튼 발견!")
                        main_window = self.driver.current_window_handle
                        reserve_btn.click()
                        self.log("🎉 바로예약 버튼 클릭 완료!")
                        WebDriverWait(self.driver, 7).until(lambda d: len(d.window_handles) > 1)
                        for w in self.driver.window_handles:
                            if w != main_window: self.driver.switch_to.window(w); break
                        try: WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, "a.plus")))
                        except: pass
                        reservation_opened = True
                        break
                    else: self.log(f"⏳ 대기 상태... ({attempt+1})")
                except: self.log(f"⏳ 버튼 대기 중... ({attempt+1})")
            except: pass

        if not reservation_opened:
            self.log("❌ 실패")
            while True: time.sleep(1)

        while True:
            if self.success_event.is_set(): break
            process_start_time = time.time()
            try:
                self.log("🎣 낚시 종류 선택 중...")
                radios = self.driver.find_elements(By.CSS_SELECTOR, "input[type='radio'][name='default_schedule_no']")
                self.log(f"🔎 Found {len(radios)} fish type options")
                if radios: 
                    self.driver.execute_script("arguments[0].click();", radios[0])
                
                has_seat_selection = False
                try:
                    page_text = self.driver.find_element(By.TAG_NAME, "body").text
                    if "자리선택" in page_text or "전체선택" in page_text:
                        has_seat_selection = True
                        self.log("📌 좌석 선택 기능 있음")
                    else:
                        self.log("📌 좌석 선택 기능 없음 (인원만 선택)")
                except: pass

                self.log(f"👥 인원 선택 중... ({person_count}명)")
                plus_btns = self.driver.find_elements(By.CSS_SELECTOR, "a.plus")
                if plus_btns:
                    for _ in range(person_count): plus_btns[0].click(); time.sleep(0.01)
                    self.log(f"✅ 인원 {person_count}명 설정 완료")

                if has_seat_selection:
                    seat_priority = ['21', '23', '22', '24', '10', '20', '1', '11', '2', '9', '19']
                    selected = 0
                    for seat in seat_priority:
                        if selected >= person_count: break
                        try:
                            checkbox = self.driver.find_element(By.CSS_SELECTOR, f"input[name='select_seat_nos[]'][value='{seat}']")
                            if checkbox.is_displayed() and not checkbox.is_selected():
                                label = self.driver.find_element(By.CSS_SELECTOR, f"label[for='select_seat_nos_num_{seat}']")
                                self.driver.execute_script("arguments[0].click();", label)
                                selected += 1
                        except: continue

                self.log("✍️ 예약 정보 입력 중...")
                self.driver.find_element(By.CSS_SELECTOR, "input[name='name']").send_keys(user_name)
                self.log(f"✅ 예약자명 입력: {user_name}")
                if len(user_phone) == 11:
                    self.driver.find_element(By.CSS_SELECTOR, "input[name='phone2']").send_keys(user_phone[3:7])
                    self.driver.find_element(By.CSS_SELECTOR, "input[name='phone3']").send_keys(user_phone[7:])
                    self.log(f"✅ 전화번호 입력")
                try: 
                    all_check = self.driver.find_element(By.CSS_SELECTOR, "input[name='all_check']")
                    self.driver.execute_script("arguments[0].click();", all_check)
                    self.log("✅ 전체 동의 체크")
                except: pass

                self.log("🚀 예약하기 버튼 클릭...")
                self.driver.execute_script("arguments[0].click();", self.driver.find_element(By.CSS_SELECTOR, "#btn_payment, a.btn_payment"))
                try:
                    alert = WebDriverWait(self.driver, 3).until(EC.alert_is_present())
                    self.log(f"🔔 Alert: {alert.text}")
                    if not self.simulation_mode: alert.accept()
                    else: return
                except: pass

                self.log("🔍 예약 결과 확인 중 (최대 10초)...")
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
                self.log(f"⏳ [브라우저{browser_count}] 10초 내 성공 확인 불가. 백그라운드 모니터링 전환...")
                self.browsers.append(self.driver)
                t = threading.Thread(target=self.monitor_browser_for_success, args=(self.driver, browser_count)); t.daemon = True; t.start()
                if len(self.browsers) >= self.max_browsers:
                    self.log(f"⚠️ 최대 브라우저 수({self.max_browsers}) 도달. 결과 대기 중...")
                    while not self.success_event.is_set(): time.sleep(0.5)
                    return
                self.log(f"🔄 새 브라우저 열고 재시도...")
                self.setup_driver()
                self.driver.get(schedule_url)
                try:
                    WebDriverWait(self.driver, 3).until(EC.element_to_be_clickable((By.CSS_SELECTOR, f"a.{date_class}"))).click()
                    date_table = self.driver.find_element(By.CSS_SELECTOR, f"table#{table_id}")
                    ship_tables = date_table.find_elements(By.CSS_SELECTOR, "table.ship_unit")
                    for ship_table in ship_tables:
                        try:
                            if "가가호" in ship_table.find_element(By.CSS_SELECTOR, "div.title").text:
                                ship_table.find_element(By.CSS_SELECTOR, "button.btn_ship_reservation").click()
                                break
                        except: continue
                    WebDriverWait(self.driver, 7).until(lambda d: len(d.window_handles) > 1)
                    for w in self.driver.window_handles:
                        if w != self.driver.current_window_handle: self.driver.switch_to.window(w); break
                except: pass
            except Exception as e:
                self.log(f"⚠️ Error: {e}")
        
        self.log("✅ 예약 봇 실행 시퀀스가 모두 완료되었습니다.")
        while True: time.sleep(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    with open(args.config, 'r', encoding='utf-8') as f: config = json.load(f)
    bot = GagahoBot(config)
    try: bot.run()
    except KeyboardInterrupt: bot.stop()
