import sys
import json
import time
import argparse
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from base_bot import BaseFishingBot

class EungabiBot(BaseFishingBot):
    def run(self):
        self.setup_driver()
        wait = WebDriverWait(self.driver, 30)

        # 1. Parse Config
        target_date_str = self.config.get('target_date', '20260821') 
        target_time = self.config.get('target_time', '09:00:00')
        test_mode = self.config.get('test_mode', False)
        self.simulation_mode = self.config.get('simulation_mode', False)
        
        user_name = self.config.get('user_name', '')
        user_depositor = self.config.get('user_depositor', '')
        user_phone = self.config.get('user_phone', '')
        person_count = int(self.config.get('person_count', 1))

        # 2. Calculate Target ID (Month-specific Base System)
        # Format: (base_date, base_id, daily_increment)
        month_bases = {
            1: ("20260103", 1486286, 1),   # January 3rd
            2: ("20260201", 1486315, 1),   # February 1st
            3: ("20260301", 1555180, 1),   # March 1st
            4: ("20260404", 1645913, 1),   # April 4th
            5: ("20260503", 1455849, 1),   # May 3rd
            6: ("20260606", 1578739, 1),   # June 6th
            7: ("20260725", 1646593, 1),   # July 25th
            8: ("20260828", 1499425, 1),   # August 28th (corrected)
            10: ("20261001", 1499428, 1),  # October 1st
            12: ("20261205", 1638500, 1)   # December 5th
        }
        
        try:
            d_target = datetime.strptime(target_date_str, "%Y%m%d")
            target_month = d_target.month
            target_day = d_target.day
            
            # Special handling for 9월 (irregular pattern)
            if target_month == 9:
                if target_day == 1:
                    target_id = 1506258
                elif target_day == 2:
                    target_id = 1506259
                else:  # 3일~30일
                    target_id = 1506501 + (target_day - 3)
                url = f"https://eungabi.sunsang24.com/mypage/reservation_ready/{target_id}"
                self.log(f"🎯 Target URL: {url} (ID: {target_id}, 9월 {target_day}일)")
            
            # Special handling for 11월 (7일 outlier)
            elif target_month == 11:
                if 1 <= target_day <= 6:
                    target_id = 1634448 + (target_day - 1)
                elif target_day == 7:
                    target_id = 1631387  # 특이 케이스
                else:  # 8일~30일
                    target_id = 1634454 + (target_day - 8)
                url = f"https://eungabi.sunsang24.com/mypage/reservation_ready/{target_id}"
                self.log(f"🎯 Target URL: {url} (ID: {target_id}, 11월 {target_day}일)")
            
            # Standard month_bases calculation
            elif target_month in month_bases:
                base_date_str, base_id, daily_increment = month_bases[target_month]
                d_base = datetime.strptime(base_date_str, "%Y%m%d")
                delta_days = (d_target - d_base).days
                target_id = int(base_id + (delta_days * daily_increment))
                url = f"https://eungabi.sunsang24.com/mypage/reservation_ready/{target_id}"
                self.log(f"🎯 Target URL: {url} (ID: {target_id}, {delta_days} days from {base_date_str})")
            else:
                self.log(f"❌ No base ID configured for month {target_month}.")
                self.log(f"Available months: {list(month_bases.keys()) + [9, 11]}")
                return
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
                            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='default_schedule_no'], .fishtype, #btn_payment"))
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
        try:
            # 4.1 Fishing Type Selection
            self.log("🎣 어종 선택 중...")
            target_keywords = ['갑오징어', '쭈꾸미']
            found_fish = False
            
            for keyword in target_keywords:
                if found_fish:
                    break
                try:
                    fish_spans = self.driver.find_elements(By.CSS_SELECTOR, "dt.fishtype span.fish")
                    self.log(f"🔎 Found {len(fish_spans)} fish type options")
                    
                    for fish_span in fish_spans:
                        if keyword in fish_span.text:
                            self.log(f"✨ Found fish type: {keyword}")
                            try:
                                parent_dt = fish_span.find_element(By.XPATH, "./ancestor::dt[@class='fishtype']")
                                radio = parent_dt.find_element(By.CSS_SELECTOR, "input[type='radio'][name='default_schedule_no']")
                                self.driver.execute_script("arguments[0].click();", radio)
                                self.log(f"✅ Selected fish type: {keyword}")
                                time.sleep(0.2)
                                found_fish = True
                                break
                            except Exception as e:
                                self.log(f"⚠️ Failed to click radio for {keyword}: {e}")
                except Exception as e:
                    self.log(f"⚠️ Error finding fish type {keyword}: {e}")
            
            if not found_fish:
                try:
                    radios = self.driver.find_elements(By.CSS_SELECTOR, "input[type='radio'][name='default_schedule_no']")
                    if len(radios) == 1:
                        self.log("✨ Only 1 fish type available, selecting it")
                        self.driver.execute_script("arguments[0].click();", radios[0])
                        time.sleep(0.2)
                except: pass

            # 4.2 Person Count Selection
            self.log(f"👥 인원 선택 중... ({person_count}명)")
            try:
                plus_btns = self.driver.find_elements(By.CSS_SELECTOR, "a.plus")
                if plus_btns:
                    for i in range(person_count):
                        plus_btns[0].click()
                        self.log(f"➕ Clicked plus button ({i+1}/{person_count})")
                        time.sleep(0.1)
            except Exception as e:
                self.log(f"⚠️ Person count selection error: {e}")

            # 4.3 Seat Selection
            self.log("💺 좌석 선택 중...")
            seat_priority = ['21', '23', '22', '24', '10', '20', '1', '11', '2', '9', '19']
            selected_seats = 0
            
            try:
                # Get all available seats
                all_seats = self.driver.find_elements(By.CSS_SELECTOR, "input[name='select_seat_nos[]']")
                self.log(f"🔎 총 {len(all_seats)}개 좌석 발견")
                
                # First pass: priority seats
                for seat_num in seat_priority:
                    if selected_seats >= person_count:
                        break
                    try:
                        checkbox = self.driver.find_element(By.CSS_SELECTOR, f"input#select_seat_nos_num_{seat_num}")
                        if not checkbox.is_selected():
                            label = self.driver.find_element(By.CSS_SELECTOR, f"label[for='select_seat_nos_num_{seat_num}']")
                            label.click()
                            self.log(f"✨ 우선순위 좌석 선택: {seat_num} ({selected_seats+1}/{person_count})")
                            selected_seats += 1
                            time.sleep(0.05)
                    except:
                        continue
                
                # Second pass: remaining seats if needed
                if selected_seats < person_count:
                    self.log(f"⚠️ 우선순위 좌석 부족. 남은 좌석 선택 중...")
                    for seat in all_seats:
                        if selected_seats >= person_count:
                            break
                        try:
                            seat_value = seat.get_attribute('value')
                            if seat_value not in seat_priority and not seat.is_selected():
                                seat_id = seat.get_attribute('id')
                                label = self.driver.find_element(By.CSS_SELECTOR, f"label[for='{seat_id}']")
                                label.click()
                                self.log(f"🎲 남은 좌석 선택: {seat_value}")
                                selected_seats += 1
                                time.sleep(0.05)
                        except:
                            continue
                
                self.log(f"✅ 좌석 선택 완료: {selected_seats}/{person_count}석")
            except Exception as e:
                self.log(f"⚠️ Seat selection error: {e}")

            # 4.4 Fill Info
            self.log("✍️ 예약 정보 입력 중...")
            try:
                name_input = self.driver.find_element(By.CSS_SELECTOR, "input[name='name']")
                name_input.clear()
                name_input.send_keys(user_name)
                self.log(f"✅ 예약자명 입력: {user_name}")
                time.sleep(0.1)
                
                try:
                    deposit_input = self.driver.find_element(By.CSS_SELECTOR, "input[name='deposit_name']")
                    if user_depositor and user_depositor != user_name:
                        deposit_input.clear()
                        deposit_input.send_keys(user_depositor)
                        self.log(f"✅ 입금자명 입력: {user_depositor}")
                except: pass
                
                p1, p2, p3 = "", "", ""
                if "-" in user_phone: 
                    parts = user_phone.split("-")
                    p1, p2, p3 = parts if len(parts)==3 else ("","","")
                elif len(user_phone) == 11: 
                    p1, p2, p3 = user_phone[:3], user_phone[3:7], user_phone[7:]
                
                if p2:
                    phone2_input = self.driver.find_element(By.CSS_SELECTOR, "input[name='phone2']")
                    phone2_input.send_keys(p2)
                    time.sleep(0.05)
                    phone3_input = self.driver.find_element(By.CSS_SELECTOR, "input[name='phone3']")
                    phone3_input.send_keys(p3)
                    self.log(f"✅ 전화번호 입력: {p2}-{p3}")
                    time.sleep(0.1)
            except Exception as e:
                self.log(f"⚠️ Info input error: {e}")

            # 4.5 All Check Agreement
            try:
                all_check = self.driver.find_element(By.CSS_SELECTOR, "input[name='all_check']")
                if not all_check.is_selected():
                    self.driver.execute_script("arguments[0].click();", all_check)
                    self.log("✅ 전체 동의 체크")
            except Exception as e:
                self.log(f"⚠️ All check error: {e}")

            # 4.6 Submit
            self.log("🚀 예약하기 버튼 클릭...")
            try:
                submit_btn = self.driver.find_element(By.CSS_SELECTOR, "#btn_payment, a.btn_payment")
                self.driver.execute_script("arguments[0].click();", submit_btn)
                
                try:
                    alert = wait.until(EC.alert_is_present())
                    self.log(f"🔔 Alert: {alert.text}")
                    if not self.simulation_mode:
                        alert.accept()
                        self.log("✅ 예약 완료!")
                    else:
                        self.log("🛑 시뮬레이션 모드: 알림창 확인 후 중단")
                except:
                    self.log("✅ Submit completed (no alert)")
            except Exception as e:
                self.log(f"⚠️ Submit error: {e}")

        except Exception as e:
            self.log(f"⚠️ Process Error: {e}")

        self.log("✅ 예약 봇 실행 시퀀스가 모두 완료되었습니다.")
        while True: time.sleep(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    with open(args.config, 'r', encoding='utf-8') as f: config = json.load(f)
    bot = EungabiBot(config)
    try: bot.run()
    except KeyboardInterrupt: bot.stop()
