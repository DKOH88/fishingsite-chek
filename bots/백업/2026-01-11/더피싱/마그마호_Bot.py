import sys
import json
import time
import argparse
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from base_bot import BaseFishingBot

class MagmaBot(BaseFishingBot):
    def run(self):
        self.setup_driver()
        wait = WebDriverWait(self.driver, 30)

        target_date = self.config.get('target_date', '20251221') 
        target_time = self.config.get('target_time', '09:00:00')
        test_mode = self.config.get('test_mode', False)
        self.simulation_mode = self.config.get('simulation_mode', False)
        
        user_name = self.config.get('user_name', '')
        user_depositor = self.config.get('user_depositor', '')
        user_phone = self.config.get('user_phone', '')
        
        # Yeomyeong v5.2 UID 5352
        base_url = "http://xn--2i0b07tba4320a.kr/_core/module/reservation_boat_v5.2_seat1/popu2.step1.php"
        url = f"{base_url}?date={target_date}&PA_N_UID=5352"
        
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
                
                self.log("🎣 Looking for fishing type (Multi-Strategy)...")
                
                # Strategy: Search broadly for any element containing the keyword
                # Priorities: LABEL > SPAN > TD
                keywords = ['갑오징어', '쭈꾸미', '쭈갑', '우럭', '광어', '다운샷'] 
                found_click = False
                
                # 1. Collect candidate elements
                candidates = []
                candidates.extend(self.driver.find_elements(By.TAG_NAME, "label"))

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

                candidates.extend(self.driver.find_elements(By.CLASS_NAME, "ps_selis"))
                candidates.extend(self.driver.find_elements(By.TAG_NAME, "td")) 
                
                for kw in keywords:
                    for el in candidates:
                        try:
                            text = el.text.strip()
                            if kw in text or kw in text.replace(" ", ""):
                                self.log(f"✨ Match found in <{el.tag_name}>: '{text}' (Kw: {kw})")
                                
                                # Strategy 1: Find Sibling Radio Button (Miracle/Magma fix)
                                try:
                                    tr = el.find_element(By.XPATH, "./ancestor::tr")
                                    radio = tr.find_element(By.CLASS_NAME, "PS_N_UID")
                                    self.log("   -> Found radio button in row, clicking...")
                                    radio.click()
                                    found_click = True
                                    self.log("⏱️ 휴먼 인식 방지 딜레이 (0.05초)...")
                                    time.sleep(0.05)
                                    break
                                except: pass

                                # Strategy 2: Click element directly
                                try: 
                                    el.click()
                                    found_click = True
                                    self.log("⏱️ 휴먼 인식 방지 딜레이 (0.05초)...")
                                    time.sleep(0.05)
                                    self.log("   -> Clicked element directly.")
                                except: pass
                                
                                # Strategy 3: Click parent
                                try:
                                    el.find_element(By.XPATH, "./parent::*").click()
                                    found_click = True
                                    self.log("⏱️ 휴먼 인식 방지 딜레이 (0.05초)...")
                                    time.sleep(0.05)
                                    self.log("   -> Clicked parent.")
                                    break
                                except: pass
                                
                                # Strategy 4: JS Click
                                try:
                                    self.driver.execute_script("arguments[0].click();", el)
                                    found_click = True
                                    self.log("⏱️ 휴먼 인식 방지 딜레이 (0.05초)...")
                                    time.sleep(0.05)
                                    break
                                except: pass
                                
                        except: continue
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
        self.log("👥 인원 선택(BI_IN) 대기 중...")
        try:
            from selenium.webdriver.support.ui import Select
            select_el = wait.until(EC.element_to_be_clickable((By.ID, "BI_IN")))
            select_obj = Select(select_el)
            current_val = select_obj.first_selected_option.get_attribute("value")
            
            configured_count = int(self.config.get('person_count', '1'))
            
            # 남은 좌석 수 확인 및 자동 조정
            try:
                remaining_seats_el = self.driver.find_element(By.ID, "id_bi_in")
                remaining_seats = int(remaining_seats_el.text.strip())
                self.log(f"📊 남은 좌석 수: {remaining_seats}석, 설정 인원: {configured_count}명")
                
                if remaining_seats < configured_count:
                    self.log(f"⚠️ 남은 좌석 부족! 인원을 {configured_count}명 → {remaining_seats}명으로 자동 조정합니다.")
                    target_count = str(remaining_seats)
                else:
                    target_count = str(configured_count)
            except Exception as e:
                self.log(f"⚠️ 남은 좌석 수 확인 실패, 설정값 사용: {e}")
                target_count = str(configured_count)
            
            if current_val != target_count:
                select_obj.select_by_value(target_count)
                self.log(f"👥 인원 {target_count}명 선택 완료.")
                time.sleep(0.05)
            else:
                self.log(f"👥 인원이 이미 {target_count}명으로 설정되어 있습니다.")
        except: pass
        
        # Step 2: Input
        process_start_time = time.time()
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
    bot = MagmaBot(config)
    try: bot.run()
    except KeyboardInterrupt: bot.stop()