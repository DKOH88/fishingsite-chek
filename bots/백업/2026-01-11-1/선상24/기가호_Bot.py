import sys
import json
import time
import argparse
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from base_bot import BaseFishingBot

# Based on Gaga-ho/Horangi-ho (SunSang24)
class GigaBot(BaseFishingBot):
    def run(self):
        self.setup_driver()
        wait = WebDriverWait(self.driver, 30)

        # 1. Parse Config
        target_date_str = self.config.get('target_date', '20251219') 
        target_time = self.config.get('target_time', '09:00:00')
        test_mode = self.config.get('test_mode', False)
        self.simulation_mode = self.config.get('simulation_mode', False)
        
        user_name = self.config.get('user_name', '')
        user_depositor = self.config.get('user_depositor', '')
        user_phone = self.config.get('user_phone', '')
        person_count = int(self.config.get('person_count', 1))

        # 2. Calculate Target ID (SunSang24 Sequential Logic)
        # Assumed Base: 2025-12-19 = 1535125 (Corrected by user)
        base_date_str = "20251219"
        base_id = 1535125
        
        try:
            d_target = datetime.strptime(target_date_str, "%Y%m%d")
            d_base = datetime.strptime(base_date_str, "%Y%m%d")
            delta_days = (d_target - d_base).days
            target_id = base_id + delta_days
            url = f"https://giga.sunsang24.com/mypage/reservation_ready/{target_id}"
            self.log(f"🎯 Target URL Calculated: {url} (ID: {target_id}, Delta: {delta_days})")
        except Exception as e:
            self.log(f"❌ Date calculation error: {e}")
            return
        
        # 2.5 Pre-load
        self.log(f"🌍 페이지 사전 로드 중: {url}")
        try:
             self.driver.get(url)
             self.log("✅ 사전 로드 완료. 오픈 시간을 기다립니다...")
        except Exception as e:
             self.log(f"⚠️ Pre-load failed: {e}")

        # 1.5 Scheduling
        if not test_mode:
            self.log(f"⏰ 실행 예약 시간: {target_time}...")
            self.wait_until_target_time(target_time)
        else:
            self.log("🚀 TEST MODE ACTIVE: Skipping wait!")

        # 3. Start Attack Loop
        self.log(f"🔥 예약 시도 시작 (반복 루프): {url}")
        max_retries = 1000
        step1_success = False

        for attempt in range(max_retries):
            try:
                self.driver.get(url)
                
                if "Bad Gateway" in self.driver.title:
                    time.sleep(0.5); continue
                
                if "login" in self.driver.current_url:
                    self.log("🔒 Redirected to Login Page.")
                    time.sleep(1)
                    continue

                if "reservation_ready" in self.driver.current_url:
                    try:
                        WebDriverWait(self.driver, 1).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='seat_col[]'], form[name='reservation_form'], #btn_payment, .btn_reserv, input[type='radio']"))
                        )
                        self.log("✅ Page Ready!")
                        step1_success = True
                        break
                    except:
                        self.log(f"⏳ Waiting for elements... ({attempt})")
                        time.sleep(0.5)
            except Exception as e:
                time.sleep(0.5)

        if not step1_success:
             self.log("❌ Failed to open reservation page.")
             # return 

        # 4. Interaction Logic
        process_start_time = time.time()
        try:
            # 4.1 Fishing Type Selection
            self.log("🎣 Checking for fishing type selection...")
            target_keywords = ['쭈갑', '쭈꾸미', '갑오징어', '문어', '우럭']
            for keyword in target_keywords:
                 try:
                     els = self.driver.find_elements(By.XPATH, f"//*[contains(text(), '{keyword}')]")
                     for el in els:
                         try:
                             radio = el.find_element(By.XPATH, "./preceding-sibling::input[@type='radio'] | ./following-sibling::input[@type='radio'] | ../input[@type='radio']")
                             radio.click(); self.log(f"✅ Selected Fishing Type: {keyword}"); time.sleep(0.5)  # Natural delay for UI update; break
                         except: pass
                 except: pass

            # 4.2 좌석 선택 기능 확인
            has_seat_selection = False
            try:
                page_text = self.driver.find_element(By.TAG_NAME, "body").text
                if "자리선택" in page_text or "전체선택" in page_text:
                    has_seat_selection = True
                    self.log("📌 좌석 선택 기능 있음")
                else:
                    self.log("📌 좌석 선택 기능 없음 (인원만 선택)")
            except:
                self.log("⚠️ 좌석 선택 기능 확인 실패")

            if has_seat_selection:
                # Seat Selection / Person Count
                self.log("🪑 Checking for Seat/Person Selection...")
                seats = self.driver.find_elements(By.XPATH, "//input[@name='seat_col[]' and not(@disabled)]")
                if seats:
                    self.log(f"🔎 Found {len(seats)} available seats. Selecting {person_count}...")
                    count = 0
                    for seat in seats:
                        if count >= person_count: break
                        try:
                             label = self.driver.find_element(By.CSS_SELECTOR, f"label[for='{seat.get_attribute('id')}']")
                             label.click()
                        except: seat.click()
                        count += 1
                else:
                    try:
                        plus_btn = self.driver.find_elements(By.XPATH, "//img[contains(@src, 'btn_plus.gif')]")
                        if plus_btn:
                            for _ in range(person_count):
                                plus_btn[0].click()
                                time.sleep(0.1)
                    except: pass
            else:
                # 4.2b Person Count Only
                self.log(f"👥 인원 선택 중... ({person_count}명)")
                try:
                    plus_btn = self.driver.find_elements(By.XPATH, "//img[contains(@src, 'btn_plus.gif')]")
                    if plus_btn:
                        for _ in range(person_count):
                            plus_btn[0].click()
                            time.sleep(0.1)
                except: pass

            # 4.4 Fill Info
            self.log("✍️ Filling Info...")
            try:
                self.driver.find_element(By.NAME, "name").clear()
                self.driver.find_element(By.NAME, "name").send_keys(user_name)
                self.log("⏱️ 휴먼 인식 방지 딜레이 (0.1초)...")
                time.sleep(0.1)
                try:
                    self.driver.find_element(By.NAME, "deposit_name").clear()
                    self.driver.find_element(By.NAME, "deposit_name").send_keys(user_depositor or user_name)
                except: pass
                
                p1, p2, p3 = "", "", ""
                if "-" in user_phone: parts = user_phone.split("-"); p1, p2, p3 = parts if len(parts)==3 else ("","","")
                elif len(user_phone) == 11: p1, p2, p3 = user_phone[:3], user_phone[3:7], user_phone[7:]
                
                if p2:
                    self.driver.find_element(By.NAME, "phone2").send_keys(p2)
                    time.sleep(0.1)
                    self.driver.find_element(By.NAME, "phone3").send_keys(p3)
                    self.log("⏱️ 휴먼 인식 방지 딜레이 (0.1초)...")
                    time.sleep(0.1)
            except: pass

            # 4.5 Agree & Submit
            try:
                chk = self.driver.find_element(By.NAME, "all_check")
                if not chk.is_selected(): chk.click()
            except: pass

            self.log("🚀 Clicking Submit...")
            try:
                btn = self.driver.find_element(By.CSS_SELECTOR, "#btn_payment, .btn_reserv")
                self.driver.execute_script("arguments[0].click();", btn)
                alert = wait.until(EC.alert_is_present())
                self.log(f"🔔 Alert: {alert.text}")
                if not self.simulation_mode: alert.accept()
            except: pass

        except Exception as e:
            self.log(f"⚠️ Process Error: {e}")

        try:
            elapsed_time = time.time() - process_start_time
            self.log(f"⏱️ 총 소요 시간: {elapsed_time:.2f}초")
        except:
            pass

        self.log("✅ 예약 봇 실행 시퀀스가 모두 완료되었습니다.")
        while True: time.sleep(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    with open(args.config, 'r', encoding='utf-8') as f: config = json.load(f)
    bot = GigaBot(config)
    try: bot.run()
    except KeyboardInterrupt: bot.stop()