import sys
import json
import time
import argparse
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from base_bot import BaseFishingBot

class GagahoBot(BaseFishingBot):
    def get_target_schedule_no(self, month, day):
        """Precision mapping based on user-provided data for Gaga-ho 2026"""
        if month == 3:
            return 1630664 + (day - 1)
        elif month == 4:
            return 1630695 + (day - 1)
        elif month == 5:
            return 1630725 + (day - 1)
        elif month == 6:
            # 6/1 is 1630830, 6/30 is 1630853. Not +1 pattern exactly.
            # Using interpolation or simple +1 from June 1st but may need adjustment
            return 1630830 + int((day - 1) * (23/29))
        elif month == 7:
            return 1631002 + (day - 1)
        elif month == 8:
            # 8/1 is 1631124, 8/31 is 1631134. Very few IDs.
            return 1631124 + int((day - 1) * (10/30))
        elif month == 9:
            return 1640949 + int((day - 1) * (28/29))
        elif month == 10:
            return 1640978 + (day - 1)
        elif month == 11:
            # 11/1 is 1641030, 11/30 is 1641029. Decreasing?
            if day == 1: return 1641030
            return 1641030 - int((day - 1) * (1/29))
        elif month == 12:
            return 1641039 + (day - 1)
        return None

    def run(self):
        self.setup_driver()
        self.wait = WebDriverWait(self.driver, 30)

        # 1. Parse Config
        self.target_date_str = self.config.get('target_date', '20260301') 
        self.target_time = self.config.get('target_time', '09:00:00')
        self.test_mode = self.config.get('test_mode', False)
        self.simulation_mode = self.config.get('simulation_mode', False)
        
        self.user_name = self.config.get('user_name', '')
        self.user_depositor = self.config.get('user_depositor', '')
        self.user_phone = self.config.get('user_phone', '')
        self.person_count = int(self.config.get('person_count', 1))

        # 2. Build Schedule Page URL
        try:
            d_target = datetime.strptime(self.target_date_str, "%Y%m%d")
            year_month = d_target.strftime("%Y%m")
            schedule_url = f"https://gagaho.sunsang24.com/ship/schedule_fleet/{year_month}"
            self.date_class = f"d{d_target.strftime('%Y-%m-%d')}"
            
            # 2.1 Calculate Precise Schedule ID
            self.target_schedule_no = self.get_target_schedule_no(d_target.month, d_target.day)
            
            self.log(f"🎯 Schedule URL: {schedule_url}")
            self.log(f"🎯 Target Date Class: {self.date_class}")
            if self.target_schedule_no:
                self.log(f"🎯 Target Schedule No: {self.target_schedule_no}")
        except Exception as e:
            self.log(f"❌ Date formatting error: {e}")
            return
        
        # 2.5 Pre-load schedule page and click date
        self.log(f"🌍 페이지 사전 로드 중: {schedule_url}")
        try:
            self.driver.get(schedule_url)
            self.log("✅ 스케줄 페이지 로드 완료")
            
            # Click target date
            self.log(f"📅 날짜 클릭 중: {self.date_class}")
            date_link = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, f"a.{self.date_class}"))
            )
            date_link.click()
            self.log(f"✅ {self.target_date_str} 날짜 클릭 완료")
            time.sleep(1)
        except Exception as e:
            self.log(f"⚠️ Pre-load failed: {e}")

        # 1.5 Scheduling
        if not self.test_mode:
            self.log(f"⏰ 실행 예약 시간: {self.target_time}...")
            self.wait_until_target_time(self.target_time)
        else:
            self.log("🚀 TEST MODE ACTIVE: Skipping wait!")

        # 3. Start Refresh Loop
        self.log(f"🔥 예약 시도 시작 (반복 루프)")
        max_retries = 1000
        reservation_opened = False

        for attempt in range(max_retries):
            try:
                self.driver.refresh()
                time.sleep(0.5)
                
                try:
                    date_link = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, f"a.{self.date_class}"))
                    )
                    date_link.click()
                    time.sleep(0.3)
                except Exception as e:
                    self.log(f"⚠️ Date click failed after refresh: {e}")
                    continue
                
                try:
                    found_button = None
                    if self.target_schedule_no:
                        try:
                            # Use exact ID from user mapping
                            btn = self.driver.find_element(By.CSS_SELECTOR, f"button[data-schedule_no='{self.target_schedule_no}']")
                            btn_text = btn.text.strip()
                            if "바로예약" in btn_text or "예약하기" in btn_text:
                                found_button = btn
                            elif "대기" in btn_text:
                                self.log(f"⏳ [{self.target_schedule_no}] 아직 대기 상태...")
                        except: pass

                    if not found_button:
                        buttons = self.driver.find_elements(By.CSS_SELECTOR, "button.btn_ship_reservation_awaiter, button[class*='btn_reserv']")
                        for button in buttons:
                            button_text = button.text.strip()
                            if "바로예약" in button_text or "예약하기" in button_text:
                                found_button = button
                                break
                    
                    if found_button:
                        self.log(f"✅ 예약 버튼 발견! 텍스트: '{found_button.text.strip()}'")
                        main_window = self.driver.current_window_handle
                        found_button.click()
                        self.log("🎉 예약 버튼 클릭! 새 창 대기 중...")
                        
                        WebDriverWait(self.driver, 10).until(lambda d: len(d.window_handles) > 1)
                        all_windows = self.driver.window_handles
                        for window in all_windows:
                            if window != main_window:
                                self.driver.switch_to.window(window)
                                self.log(f"✅ 새 예약 창으로 전환 완료! URL: {self.driver.current_url}")
                                break
                        
                        try:
                            WebDriverWait(self.driver, 15).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, "a.plus"))
                            )
                            self.log("✅ Plus 버튼 활성화 감지! 페이지 로드 완료")
                        except:
                            self.log("⚠️ Plus 버튼 대기 시간 초과, 진행합니다...")
                        
                        reservation_opened = True
                        break
                    
                except Exception as e:
                    self.log(f"⚠️ Button check error: {e}")
                
                time.sleep(0.5)
                
            except Exception as e:
                self.log(f"⚠️ Refresh loop error: {e}")
                time.sleep(1)

        if not reservation_opened:
            self.log("❌ 최대 재시도 횟수 초과로 예약 페이지 진입에 실패했습니다.")
            return

        self.run_interaction()

    def run_interaction(self):
        try:
            # 4.1 Fish Type
            target_keywords = ['갑오징어', '쭈꾸미']
            found_fish = False
            for keyword in target_keywords:
                if found_fish: break
                try:
                    fish_spans = self.driver.find_elements(By.CSS_SELECTOR, "dt.fishtype span.fish")
                    for fish_span in fish_spans:
                        if keyword in fish_span.text:
                            parent_dt = fish_span.find_element(By.XPATH, "./ancestor::dt[@class='fishtype']")
                            radio = parent_dt.find_element(By.CSS_SELECTOR, "input[type='radio'][name='default_schedule_no']")
                            self.driver.execute_script("arguments[0].click();", radio)
                            self.log(f"✅ Selected fish type: {keyword}")
                            time.sleep(0.2)
                            found_fish = True
                            break
                except: pass

            # 4.2 Person Count
            self.log(f"👥 인원 선택 중... ({self.person_count}명)")
            try:
                plus_btns = self.driver.find_elements(By.CSS_SELECTOR, "a.plus")
                if plus_btns:
                    for i in range(self.person_count):
                        plus_btns[0].click()
                        time.sleep(0.1)
            except: pass

            # 4.3 Seats
            seat_priority = ['21', '23', '22', '24', '10', '20', '1', '11', '2', '9', '19']
            selected_seats = 0
            try:
                for seat_num in seat_priority:
                    if selected_seats >= self.person_count: break
                    try:
                        checkbox = self.driver.find_element(By.CSS_SELECTOR, f"input[name='select_seat_nos[]'][value='{seat_num}']")
                        if checkbox.is_displayed() and not checkbox.is_selected():
                            label = self.driver.find_element(By.CSS_SELECTOR, f"label[for='select_seat_nos_num_{seat_num}']")
                            self.driver.execute_script("arguments[0].click();", label)
                            selected_seats += 1
                            time.sleep(0.05)
                    except: continue
                
                if selected_seats < self.person_count:
                    all_checkboxes = self.driver.find_elements(By.CSS_SELECTOR, "input[name='select_seat_nos[]']")
                    for checkbox in all_checkboxes:
                        if selected_seats >= self.person_count: break
                        if checkbox.is_displayed() and not checkbox.is_selected():
                            checkbox.click()
                            selected_seats += 1
                            time.sleep(0.05)
            except: pass

            # 4.4 Info
            self.log("✍️ 예약 정보 입력 중...")
            try:
                self.driver.find_element(By.CSS_SELECTOR, "input[name='name']").send_keys(self.user_name)
                try:
                    if self.user_depositor and self.user_depositor != self.user_name:
                        self.driver.find_element(By.CSS_SELECTOR, "input[name='deposit_name']").send_keys(self.user_depositor)
                except: pass
                
                phone = self.user_phone.replace("-", "")
                if len(phone) == 11:
                    self.driver.find_element(By.CSS_SELECTOR, "input[name='phone2']").send_keys(phone[3:7])
                    self.driver.find_element(By.CSS_SELECTOR, "input[name='phone3']").send_keys(phone[7:])
            except: pass

            # 4.5 Agreement
            try:
                all_check = self.driver.find_element(By.CSS_SELECTOR, "input[name='all_check']")
                self.driver.execute_script("arguments[0].click();", all_check)
            except: pass

            # 4.6 Submit
            self.log("🚀 예약 시도...")
            try:
                submit_btn = self.driver.find_element(By.CSS_SELECTOR, "#btn_payment, a.btn_payment")
                self.driver.execute_script("arguments[0].click();", submit_btn)
                try:
                    alert = WebDriverWait(self.driver, 5).until(EC.alert_is_present())
                    if not self.simulation_mode: alert.accept()
                except: pass
            except: pass

        except Exception as e:
            self.log(f"⚠️ Interaction Error: {e}")
        
        self.log("✅ 완료")
        while True: time.sleep(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    with open(args.config, 'r', encoding='utf-8') as f: config = json.load(f)
    bot = GagahoBot(config)
    try: bot.run()
    except KeyboardInterrupt: bot.stop()
