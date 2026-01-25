import sys
import json
import time
import argparse
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from base_bot import BaseFishingBot

class NumberOneBot(BaseFishingBot):
    def run(self):
        self.setup_driver()
        wait = WebDriverWait(self.driver, 30)

        # 1. Parse Config
        target_date_str = self.config.get('target_date', '20261220')
        target_time = self.config.get('target_time', '09:00:00')
        test_mode = self.config.get('test_mode', False)
        self.simulation_mode = self.config.get('simulation_mode', False)
        
        user_name = self.config.get('user_name', '')
        user_depositor = self.config.get('user_depositor', '')
        user_phone = self.config.get('user_phone', '')
        
        # 2. Calculate URL (Date-based ID)
        # Base: 2025-12-19 -> 1214231
        base_date_str = "20251219"
        base_id = 1214231
        
        try:
            d_target = datetime.strptime(target_date_str, "%Y%m%d")
            d_base = datetime.strptime(base_date_str, "%Y%m%d")
            delta_days = (d_target - d_base).days
            target_id = base_id + delta_days
            
            # https://no1.sunsang24.com/mypage/reservation_ready/1214231
            url = f"https://no1.sunsang24.com/mypage/reservation_ready/{target_id}"
            self.log(f"🎯 Target URL Calculated: {url} (ID: {target_id}, Delta: {delta_days})")
            
        except Exception as e:
            self.log(f"❌ Date URL Calculation Failed: {e}")
            return

        # 2.5 Pre-load / Warm-up
        self.log(f"🌍 페이지 사전 로드 중: {url}")
        try:
             self.driver.get(url)
             self.log("✅ 사전 로드 완료. 오픈 시간을 기다립니다...")
        except Exception as e:
             self.log(f"⚠️ 사전 로드 실패 (예약 시간에 재시도함): {e}")

        # 1.5 Scheduling
        if not test_mode:
            self.log(f"⏰ 실행 예약 시간: {target_time}...")
            self.wait_until_target_time(target_time)
        else:
            self.log("🚀 테스트 모드 활성화: 대기 없이 즉시 실행합니다!")

        # 3. Start Attack Loop
        self.log(f"🔥 예약 시도 시작 (반복 루프): {url}")
        
        max_retries = 1000
        retry_interval = 1 
        page_opened = False
        
        for attempt in range(max_retries):
            try:
                self.driver.get(url)
                
                if "Bad Gateway" in self.driver.title:
                    self.log(f"⚠️ 서버 오류 (502). 새로고침 중... ({attempt+1}/{max_retries})")
                    time.sleep(0.5)
                    continue

                if "reservation_ready" in self.driver.current_url:
                    self.log("✅ 페이지 로드 완료! 정보 입력을 시작합니다...")
                    page_opened = True
                    break
                    
            except Exception as e:
                self.log(f"⚠️ 연결 오류 발생: {e}. 재시도 중...")
                time.sleep(retry_interval)
                
        if not page_opened:
            self.log("❌ Failed to open page.")
            return

        # 4. Form Filling
        try:
            # 4.0 Fishing Type Selection
            self.log("🎣 Checking for fishing type selection...")
            target_keywords = ['쭈갑', '쭈꾸미&갑오징어', '쭈&갑', '쭈꾸미', '갑오징어', '문어']
            type_selected = False
            for keyword in target_keywords:
                try:
                    text_xpath = f"//*[contains(text(), '{keyword}')]"
                    text_elements = self.driver.find_elements(By.XPATH, text_xpath)
                    for el in text_elements:
                        if el.is_displayed():
                            try:
                                radio = el.find_element(By.XPATH, "./preceding-sibling::input[@type='radio']")
                                self.driver.execute_script("arguments[0].click();", radio)
                                type_selected = True; time.sleep(0.5); break
                            except:
                                try:
                                    radio = el.find_element(By.XPATH, "..//input[@type='radio']")
                                    self.driver.execute_script("arguments[0].click();", radio)
                                    type_selected = True; time.sleep(0.5); break
                                except: pass
                    if type_selected: break
                except: pass
            
            # 4.1 Person Count
            self.log("👥 인원수 설정 중...")
            self.log("⏱️ 휴먼 인식 방지 딜레이 (0.1초)...")
            time.sleep(0.1)
            target_count = int(self.config.get('person_count', 1))
            try:
                plus_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//img[contains(@src, 'btn_plus.gif')]")))
                for i in range(target_count):
                    plus_btn.click()
                    self.log("⏱️ 휴먼 인식 방지 딜레이 (0.1초)...")
                    time.sleep(0.1)
            except: pass

            # 4.1.5 Seat Selection (Number One-ho Specific)
            self.log("💺 Checking for seat selection...")
            try:
                # Priority: 22 > 23 > 10 > 11 > 21 > 24
                seat_priority = ['22', '23', '10', '11', '21', '24']
                selected_seats = 0
                
                for seat_num in seat_priority:
                     if selected_seats >= target_count: break
                     try:
                         # Try finding checkbox by ID pattern
                         seat_id = f"select_seat_nos_num_{seat_num}"
                         checkbox = self.driver.find_element(By.ID, seat_id)
                         
                         if checkbox.is_enabled() and not checkbox.is_selected():
                             self.log(f"✨ Seat {seat_num} available! Clicking... ({selected_seats+1}/{target_count})")
                             # Click label usually safer for hidden checkboxes
                             try:
                                 label = self.driver.find_element(By.XPATH, f"//label[@for='{seat_id}']")
                                 self.driver.execute_script("arguments[0].click();", label)
                             except:
                                 self.driver.execute_script("arguments[0].click();", checkbox)
                                 
                             selected_seats += 1
                     except: continue
                
                if selected_seats < target_count:
                    self.log(f"⚠️ Only selected {selected_seats}/{target_count} preferred seats. Filling remaining with ANY available...")
                    try:
                         # Fallback: Find all seat checkboxes
                         all_seats = self.driver.find_elements(By.XPATH, "//input[@name='select_seat_nos[]']")
                         for seat in all_seats:
                             if selected_seats >= target_count: break
                             try:
                                 if seat.is_enabled() and not seat.is_selected():
                                      seat_num = seat.get_attribute("value")
                                      self.log(f"🎲 Fallback: Clicking Seat {seat_num}... ({selected_seats+1}/{target_count})")
                                      self.driver.execute_script("arguments[0].click();", seat)
                                      selected_seats += 1
                             except: continue
                    except Exception as ex: 
                         self.log(f"⚠️ Fallback selection error: {ex}")

                if selected_seats < target_count:
                    self.log(f"❌ Failed to reach target count. Selected {selected_seats}/{target_count}.")
                else:
                    self.log(f"✅ Successfully selected {selected_seats} seats.")
            except Exception as e:
                self.log(f"⚠️ Seat selection error: {e}")

            # 4.2 Fill Info
            self.log(f"✍️ Filling Info...")
            self.driver.find_element(By.NAME, "name").clear()
            self.driver.find_element(By.NAME, "name").send_keys(user_name)
            self.log("⏱️ 휴먼 인식 방지 딜레이 (0.1초)...")
            time.sleep(0.1)
            
            depositor = user_depositor if user_depositor else user_name
            self.driver.find_element(By.NAME, "deposit_name").clear()
            self.driver.find_element(By.NAME, "deposit_name").send_keys(depositor)
            self.log("⏱️ 휴먼 인식 방지 딜레이 (0.1초)...")
            time.sleep(0.1)
            
            p1, p2, p3 = "", "", ""
            if "-" in user_phone: parts = user_phone.split("-"); p1, p2, p3 = parts if len(parts)==3 else ("","","")
            elif len(user_phone) == 11: p1, p2, p3 = user_phone[:3], user_phone[3:7], user_phone[7:]
            
            if p2:
                 self.driver.find_element(By.NAME, "phone2").send_keys(p2)
                 time.sleep(0.1)
                 self.driver.find_element(By.NAME, "phone3").send_keys(p3)
                 self.log("⏱️ 휴먼 인식 방지 딜레이 (0.1초)...")
                 time.sleep(0.1)

            # 4.5 Agree
            try:
                agree_chk = self.driver.find_element(By.NAME, "all_check")
                self.log("✅ '전체 동의' 체크박스 클릭 중...")
                if not agree_chk.is_selected(): agree_chk.click()
                self.log("⏱️ 휴먼 인식 방지 딜레이 (0.1초)...")
                time.sleep(0.1)
            except: pass

            # 4.6 Submit
            self.log("🚀 Clicking Submit...")
            try:
                submit_btn = self.driver.find_element(By.ID, "btn_payment")
                self.driver.execute_script("arguments[0].click();", submit_btn)
                
                self.log("🔔 Alert check...")
                try: 
                    alert = wait.until(EC.alert_is_present())
                    self.log(f"🔔 Alert: {alert.text}")
                    if not self.simulation_mode: alert.accept()
                except: pass
                
                self.log("✅ Submitted!")
                
            except Exception as e: self.log(f"⚠️ Submit failed: {e}")

        except Exception as e: self.log(f"⚠️ Form Error: {e}")
        
        while True: time.sleep(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    with open(args.config, 'r', encoding='utf-8') as f: config = json.load(f)
    bot = NumberOneBot(config)
    try: bot.run()
    except KeyboardInterrupt: bot.stop()