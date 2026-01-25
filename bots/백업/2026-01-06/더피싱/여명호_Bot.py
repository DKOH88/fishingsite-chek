import sys
import json
import time
import argparse
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from base_bot import BaseFishingBot

class YeomyeongBot(BaseFishingBot):
    def run(self):
        self.setup_driver()
        wait = WebDriverWait(self.driver, 30)

        # 1. Parse Config
        target_date = self.config.get('target_date', '20260302')
        target_time = self.config.get('target_time', '09:00:00')
        test_mode = self.config.get('test_mode', False)
        self.simulation_mode = self.config.get('simulation_mode', False)
        
        user_name = self.config.get('user_name', '')
        user_depositor = self.config.get('user_depositor', '')
        user_phone = self.config.get('user_phone', '')
        user_pw = self.config.get('user_pw', '1234')
        
        user_pw = self.config.get('user_pw', '1234')
        
        # 2. Build URL (Prepare Early)
        base_url = "http://xn--v42bv0rcoar53c6lb.kr/_core/module/reservation_boat_v5.2_seat1/popu2.step1.php"
        url = f"{base_url}?date={target_date}&PA_N_UID=5030"
        
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

        # 3. Start "Smart Refresh Loop" at target time
        self.log(f"🔥 예약 시도 시작 (반복 루프): {url}")
        
        # Retry config
        max_retries = 1000 # Try for about 20~30 minutes
        retry_interval = 1 # seconds
        
        step1_success = False

        for attempt in range(max_retries):
            try:
                self.driver.get(url)
                
                # Check for Server Errors
                if "Bad Gateway" in self.driver.title or "502" in self.driver.page_source:
                    self.log(f"⚠️ 서버 오류 (502). 새로고침 중... ({attempt+1}/{max_retries})")
                    time.sleep(0.5)
                    continue

                # Check if we are potentially on the right page
                # target: class="ps_selis" which holds the fishing names
                try:
                    # Quick check for presence
                    WebDriverWait(self.driver, 1).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "ps_selis"))
                    )
                except:
                    # Not found yet, maybe site not open or loading
                    self.log(f"⏳ Site not ready (Fishing types not found). Retrying... ({attempt+1}/{max_retries})")
                    time.sleep(retry_interval)
                    continue
                
                # If we get here, the elements are likely present. Try to select.
                self.log("🎣 낚시 종류 선택 항목 찾는 중...")
                self.log("⏱️ 휴먼 인식 방지 딜레이 (0.05초)...")
                time.sleep(0.05)
                
                target_keywords = []
                target_ship_cfg = self.config.get('target_ship', '').strip()
                if target_ship_cfg:
                    target_keywords.append(target_ship_cfg)
                # Default preference: Prioritize combined catch as requested
                # 1.쭈갑 2.쭈꾸미&갑오징어 3.쭈&갑 4.쭈꾸미 5.갑오징어 6.문어
                target_keywords.extend(['쭈갑', '쭈꾸미&갑오징어', '쭈&갑', '쭈꾸미', '갑오징어', '문어'])
                
                found_click = False
                for keyword in target_keywords:
                    # Logic same as before
                    # ...
                    xpath_span = f"//span[contains(@class, 'ps_selis') and contains(text(), '{keyword}')]"
                    spans = self.driver.find_elements(By.XPATH, xpath_span)
                    
                    if not spans: continue
                        
                    for span in spans:
                        label = span.find_element(By.XPATH, "./..")
                        target_id = label.get_attribute("for")
                        if target_id:
                            radio_btn = self.driver.find_element(By.ID, target_id)
                            self.log(f"⚡ Found target: '{keyword}' (ID: {target_id}) -> Clicking!")
                            self.driver.execute_script("arguments[0].click();", radio_btn)
                            found_click = True
                            self.log("⏱️ 휴먼 인식 방지 딜레이 (0.05초)...")
                            time.sleep(0.05)
                            break
                    if found_click: break
                
                if found_click:
                    self.log("⏳ 인원 선택(BI_IN) 활성화 대기 중 (최대 5초)...")
                    try:
                        WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.ID, "BI_IN"))
                        )
                        self.log("✅ 인원 선택 활성화 감지! 2단계 진입 성공!")
                        step1_success = True
                        break
                    except:
                        self.log("⚠️ 5초 내 인원 선택 미감지. 새로고침 후 재시도...")
                        continue # Success!
                else:
                     self.log("⚠️ 낚시 종류는 찾았으나, 일치하는 키워드가 없습니다. 설정을 확인해 주세요.")
                     # In this specific case, maybe we should stop or manual intervention. 
                     # For safety, let's break and let user handle it, assuming page loaded but target is full/not listed.
                     break 

            except Exception as e:
                self.log(f"⚠️ 연결 오류 발생: {e}. 재시도 중...")
                time.sleep(retry_interval)
        
        if not step1_success:
             self.log("❌ 최대 재시도 횟수 초과로 예약 1단계 진입에 실패했습니다.")
             # return or exit? For now just try to proceed or exit
             # return 


        # 4. Step 1.5: Select Person Count (BI_IN)
        # The select box might appear dynamically or be present but disabled.
        # We wait for it to be visible.
        self.log("👥 인원 선택(BI_IN) 대기 중...")
        self.log("⏱️ 휴먼 인식 방지 딜레이 (0.05초)...")
        time.sleep(0.05)
        try:
            from selenium.webdriver.support.ui import Select
            
            # Wait for element
            select_el = wait.until(EC.element_to_be_clickable((By.ID, "BI_IN")))
            
            # Check current value to avoid redundant selection
            select_obj = Select(select_el)
            current_val = select_obj.first_selected_option.get_attribute("value")
            
            target_count = self.config.get('person_count', '1')
            
            if current_val != target_count:
                self.log(f"👥 인원을 {target_count}명으로 설정합니다...")
                select_obj.select_by_value(target_count)
                self.log("⏱️ 휴먼 인식 방지 딜레이 (0.05초)...")
                time.sleep(0.05)
            else:
                self.log(f"👥 이미 {target_count}명으로 설정되어 있습니다.")
                
        except Exception as e:
            self.log(f"⚠️ Error selecting person count: {e}")

        except Exception as e:
            self.log(f"⚠️ Error in Step 1: {e}")

        # 5. Step 2: Seat Selection & Info
        self.log("🪑 예약 정보 입력 페이지(2단계) 진입 중...")
        try:
            # 5.1 Fill Name (BI_NAME)
            # It has no ID, only name="BI_NAME"
            name_input = wait.until(EC.element_to_be_clickable((By.NAME, "BI_NAME")))
            self.log(f"✍️ 성함 입력 중: {user_name}")
            name_input.clear()
            time.sleep(0.05)
            name_input.send_keys(user_name)
            self.log("⏱️ 휴먼 인식 방지 딜레이 (0.05초)...")
            time.sleep(0.05)
            
            # 5.2 Fill Depositor (BI_BANK)
            # It has ID="BI_BANK"
            bank_input = self.driver.find_element(By.ID, "BI_BANK")
            depositor = user_depositor if user_depositor else user_name
            self.log(f"✍️ 입금자명 입력 중: {depositor}")
            bank_input.clear()
            bank_input.send_keys(depositor)
            self.log("⏱️ 휴먼 인식 방지 딜레이 (0.05초)...")
            time.sleep(0.05)

            # 5.3 Fill Phone Number (BI_TEL1, BI_TEL2, BI_TEL3)
            # Parse phone number (e.g., 010-1234-5678 or 01012345678)
            p1, p2, p3 = "", "", ""
            if "-" in user_phone:
                parts = user_phone.split("-")
                if len(parts) == 3:
                    p1, p2, p3 = parts
            elif len(user_phone) == 11:
                p1, p2, p3 = user_phone[:3], user_phone[3:7], user_phone[7:]
            
            if p1 and p2 and p3:
                self.log(f"📞 Filling Phone: {p2}-{p3} (Skipping 010)")
                
                # t1 = self.driver.find_element(By.ID, "BI_TEL1")
                # t1.clear()
                # t1.send_keys(p1)
                
                t2 = self.driver.find_element(By.ID, "BI_TEL2")
                t2.clear()
                t2.send_keys(p2)
                self.log("⏱️ 휴먼 인식 방지 딜레이 (0.05초)...")
                time.sleep(0.05)
                
                t3 = self.driver.find_element(By.ID, "BI_TEL3")
                t3.clear()
                t3.send_keys(p3)
                self.log("⏱️ 휴먼 인식 방지 딜레이 (0.05초)...")
                time.sleep(0.05)
            else:
                self.log(f"⚠️ Phone number format warning: {user_phone}")

            # 5.4 Agree All
            # <input type="radio" name="all_agree" value="Y" ...>
            self.log("✅ '전체 동의' 체크박스 클릭 중...")
            try:
                agree_btn = self.driver.find_element(By.XPATH, "//input[@name='all_agree' and @value='Y']")
                self.driver.execute_script("arguments[0].click();", agree_btn)
                self.log("⏱️ 휴먼 인식 방지 딜레이 (0.05초)...")
                time.sleep(0.05)
            except Exception as e:
                self.log(f"⚠️ 'Agree All' button not found or error: {e}")

            # 5.5 Submit Button
            # 5.5 Submit Button
            self.log("🚀 '예약 신청하기' 버튼 클릭 시도...")
            try:
                submit_btn = self.driver.find_element(By.ID, "submit")
                self.driver.execute_script("arguments[0].click();", submit_btn)
                
                # Handle Confirmation Alert
                self.log("🔔 예약 확인창 대기 중...")
                alert = wait.until(EC.alert_is_present())
                alert_text = alert.text
                self.log(f"🔔 알림창 확인: {alert_text}")
                
                if not self.simulation_mode:
                    self.log("🚀 최종 실행: 알림창 '확인' 클릭...")
                    alert.accept()
                    self.log("✅ 예약 신청 완료! 브라우저 창을 확인해 주세요.")
                else:
                    self.log("🛑 시묘레이션 모드: 버튼 클릭 및 알림창 확인 후 작업을 중단합니다.")
                    
            except Exception as e:
                self.log(f"⚠️ 전송 버튼/알림창 처리 오류: {e}")

        except Exception as e:
            self.log(f"ℹ️ Input Autofill skipped or failed: {e}")

        self.log("✅ Bot setup complete. Monitor the browser for further actions.")
        
        # Keep alive
        while True:
            time.sleep(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="Path to config JSON")
    args = parser.parse_args()

    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)

    bot = YeomyeongBot(config)
    try:
        bot.run()
    except KeyboardInterrupt:
        bot.stop()