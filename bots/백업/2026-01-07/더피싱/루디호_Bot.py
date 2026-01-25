import sys
import json
import time
import argparse
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from base_bot import BaseFishingBot

class RudyBot(BaseFishingBot):
    def run(self):
        self.setup_driver()
        wait = WebDriverWait(self.driver, 30)

        target_date = self.config.get('target_date', '20251230') 
        target_time = self.config.get('target_time', '09:00:00')
        test_mode = self.config.get('test_mode', False)
        self.simulation_mode = self.config.get('simulation_mode', False)
        
        user_name = self.config.get('user_name', '')
        user_depositor = self.config.get('user_depositor', '')
        user_phone = self.config.get('user_phone', '')
        
        # Yeomyeong v5.2 UID 3468
        base_url = "http://www.rudyfishing.com/_core/module/reservation_boat_v5.2_seat1/popu2.step1.php"
        url = f"{base_url}?date={target_date}&PA_N_UID=3468"
        
        self.log(f"🌍 페이지 사전 로드 중: {url}")
        try: self.driver.get(url)
        except: pass

        if not test_mode:
            self.log(f"⏰ 실행 예약 시간: {target_time}...")
            self.wait_until_target_time(target_time)
        else: self.log("🚀 TEST MODE")

        self.log(f"🔥 예약 시도 시작 (반복 루프): {url}")
        max_retries = 1000
        step1_success = False

        for attempt in range(max_retries):
            try:
                self.driver.get(url)
                if "Bad Gateway" in self.driver.title: time.sleep(0.5); continue
                
                try:
                    WebDriverWait(self.driver, 1).until(EC.presence_of_element_located((By.CLASS_NAME, "ps_selis")))
                except:
                    time.sleep(1); continue
                
                self.log("🎣 Looking for fishing type...")

                # [New] If only 1 radio button exists, click it blindly
                radios = self.driver.find_elements(By.CSS_SELECTOR, "input.PS_N_UID")
                if len(radios) == 1:
                    self.log("✨ 단일 선택 항목 감지됨 (CSS). 자동으로 선택합니다.")
                    try:
                        self.driver.execute_script("arguments[0].click();", radios[0])
                        step1_success = True
                        break
                    except Exception as e:
                        self.log(f"⚠️ Failed to click single radio: {e}")

                spans = self.driver.find_elements(By.CLASS_NAME, "ps_selis")
                keywords = ['갑오징어', '쭈꾸미', '쭈갑', '우럭'] 
                found_click = False
                
                for kw in keywords:
                    for span in spans:
                        if kw in span.text:
                             self.log(f"✨ Match: {kw}")
                             time.sleep(0.2)
                             try: span.click(); found_click = True; break
                             time.sleep(0.05)
                             except:
                                 try: span.find_element(By.XPATH, "./parent::label").click(); found_click = True; break
                                 self.log("⏱️ 휴먼 인식 방지 딜레이 (0.05초)...")
                                 time.sleep(0.05)
                                 except: pass
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
                        continue
            except Exception as e: time.sleep(1)

        if not step1_success: self.log("❌ Failed Step 1"); return

        # Step 1.5: Person Count
        try:
            from selenium.webdriver.support.ui import Select
            select_el = wait.until(EC.element_to_be_clickable((By.ID, "BI_IN")))
            select_obj = Select(select_el)
            target_count = self.config.get('person_count', '1')
            select_obj.select_by_value(target_count)
            self.log("⏱️ 휴먼 인식 방지 딜레이 (0.05초)...")
            time.sleep(0.05)
        except: pass
        
        # Step 2: Input
        self.log("✍️ Waiting for Input Form...")
        try:
            name_input = wait.until(EC.element_to_be_clickable((By.NAME, "BI_NAME")))
            name_input.clear(); name_input.send_keys(user_name)
            self.log("⏱️ 휴먼 인식 방지 딜레이 (0.05초)...")
            time.sleep(0.05)
            
            try:
                bank_input = self.driver.find_element(By.ID, "BI_BANK")
                depositor = user_depositor if user_depositor else user_name
                bank_input.clear(); self.log(f"✍️ 입금자명 입력 중: {depositor}")
                bank_input.send_keys(depositor)
                self.log("⏱️ 휴먼 인식 방지 딜레이 (0.05초)...")
                time.sleep(0.05)
            except: pass
            
            p1, p2, p3 = "", "", ""
            if "-" in user_phone:
                parts = user_phone.split("-")
                if len(parts) == 3: p1, p2, p3 = parts
            elif len(user_phone) == 11: 
                p1, p2, p3 = user_phone[:3], user_phone[3:7], user_phone[7:]
            
            if p2:
                try:
                    self.driver.find_element(By.ID, "BI_TEL2").send_keys(p2)
                    time.sleep(0.05)
                    self.driver.find_element(By.ID, "BI_TEL3").send_keys(p3)
                    self.log("⏱️ 휴먼 인식 방지 딜레이 (0.05초)...")
                    time.sleep(0.05)
                except: pass

            try: self.driver.execute_script("arguments[0].click();", self.driver.find_element(By.XPATH, "//input[@name='all_agree']"))
            except: pass
            
            self.log("🚀 Submitting...")
            try:
                self.driver.execute_script("arguments[0].click();", self.driver.find_element(By.ID, "submit"))
                alert = wait.until(EC.alert_is_present())
                self.log(f"🔔 {alert.text}")
                if not self.simulation_mode: alert.accept()
            except: pass 
        except Exception as e: self.log(f"⚠️ Form Error: {e}")

        while True: time.sleep(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    with open(args.config, 'r', encoding='utf-8') as f: config = json.load(f)
    bot = RudyBot(config)
    try: bot.run()
    except KeyboardInterrupt: bot.stop()