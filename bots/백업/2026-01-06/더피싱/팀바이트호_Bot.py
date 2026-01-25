import sys
import json
import time
import argparse
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from base_bot import BaseFishingBot

class ByteBot(BaseFishingBot):
    def run(self):
        self.setup_driver()
        wait = WebDriverWait(self.driver, 30)

        target_date = self.config.get('target_date', '20261218') 
        target_time = self.config.get('target_time', '09:00:00')
        test_mode = self.config.get('test_mode', False)
        self.simulation_mode = self.config.get('simulation_mode', False)
        
        user_name = self.config.get('user_name', '')
        user_depositor = self.config.get('user_depositor', '')
        user_phone = self.config.get('user_phone', '')
        
        # http://teambite.kr/_core/module/reservation_boat_v5.2_seat1/popu2.step1.php?date=20251218&PA_N_UID=5948
        base_url = "http://teambite.kr/_core/module/reservation_boat_v5.2_seat1/popu2.step1.php"
        url = f"{base_url}?date={target_date}&PA_N_UID=5948"
        
        self.log(f"🌍 페이지 사전 로드 중: {url}")
        try:
             self.driver.get(url)
             self.log("✅ 사전 로드 완료. 오픈 시간을 기다립니다...")
        except Exception as e:
             self.log(f"⚠️ 사전 로드 실패 (예약 시간에 재시도함): {e}")

        if not test_mode:
            self.log(f"⏰ 실행 예약 시간: {target_time}...")
            self.wait_until_target_time(target_time)
        else:
            self.log("🚀 테스트 모드 활성화: 대기 없이 즉시 실행합니다!")

        self.log(f"🔥 예약 시도 시작 (반복 루프): {url}")
        
        max_retries = 1000 
        retry_interval = 1 
        step1_success = False

        for attempt in range(max_retries):
            try:
                self.driver.get(url)
                
                if "Bad Gateway" in self.driver.title or "502" in self.driver.page_source:
                    self.log(f"⚠️ 서버 오류 (502). 새로고침 중... ({attempt+1}/{max_retries})")
                    time.sleep(0.5)
                    continue

                try:
                    WebDriverWait(self.driver, 1).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "ps_selis"))
                    )
                except:
                    self.log(f"⏳ Site not ready (Fishing types not found). Retrying... ({attempt+1}/{max_retries})")
                    time.sleep(retry_interval)
                    continue
                
                self.log("🎣 낚시 종류 선택 항목 찾는 중...")
                self.log("⏱️ 휴먼 인식 방지 딜레이 (0.05초)...")
                time.sleep(0.05)

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

                all_spans = self.driver.find_elements(By.CLASS_NAME, "ps_selis")
                self.log(f"🔎 총 {len(all_spans)}개의 낚시 종류 후보를 찾았습니다.")
                
                target_keywords = []
                target_ship_cfg = self.config.get('target_ship', '').strip()
                if target_ship_cfg: target_keywords.append(target_ship_cfg)
                target_keywords.extend(['쭈갑', '쭈꾸미&갑오징어', '쭈&갑', '쭈꾸미', '갑오징어', '문어', '광어', '참돔'])
                
                found_click = False
                for keyword in target_keywords:
                    if found_click: break
                    for span in all_spans:
                        text = span.text.strip()
                        
                        if keyword in text:
                            try:
                                radio = span.find_element(By.XPATH, "./parent::td/preceding-sibling::td//input[@type='radio']")
                                self.driver.execute_script("arguments[0].click();", radio)
                                found_click = True
                                self.log("⏱️ 휴먼 인식 방지 딜레이 (0.05초)...")
                                time.sleep(0.05)
                            except:
                                try:
                                    radio = span.find_element(By.XPATH, "./preceding-sibling::input[@type='radio']")
                                    self.driver.execute_script("arguments[0].click();", radio)
                                    found_click = True
                                    self.log("⏱️ 휴먼 인식 방지 딜레이 (0.05초)...")
                                    time.sleep(0.05)
                                except:
                                    try:
                                        radio = span.find_element(By.XPATH, "..//input[@type='radio']")
                                        self.driver.execute_script("arguments[0].click();", radio)
                                        found_click = True
                                        self.log("⏱️ 휴먼 인식 방지 딜레이 (0.05초)...")
                                        time.sleep(0.05)
                                    except:
                                        try:
                                            span.click()
                                            found_click = True
                                            self.log("⏱️ 휴먼 인식 방지 딜레이 (0.05초)...")
                                            time.sleep(0.05)
                                        except: pass
                            if found_click: break
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
                else:
                     self.log("⚠️ Fishing types found, but no matching keyword.")
                     break 

            except Exception as e:
                self.log(f"⚠️ 연결 오류 발생: {e}. 재시도 중...")
                time.sleep(retry_interval)
        
        if not step1_success: self.log("❌ Failed to enter reservation step 1.")

        self.log("👥 Waiting for Person Count (BI_IN)...")
        try:
            from selenium.webdriver.support.ui import Select
            select_el = wait.until(EC.element_to_be_clickable((By.ID, "BI_IN")))
            select_obj = Select(select_el)
            target_count = self.config.get('person_count', '1')
            if select_obj.first_selected_option.get_attribute("value") != target_count:
                select_obj.select_by_value(target_count)
                self.log("⏱️ 휴먼 인식 방지 딜레이 (0.05초)...")
                time.sleep(0.05)
        except Exception as e: self.log(f"⚠️ Person count error: {e}")

        self.log("🪑 Filling Info...")
        try:
            wait.until(EC.element_to_be_clickable((By.NAME, "BI_NAME"))).send_keys(user_name)
            self.log("⏱️ 휴먼 인식 방지 딜레이 (0.05초)...")
            time.sleep(0.05)
            try: self.driver.find_element(By.ID, "BI_BANK").send_keys(user_depositor if user_depositor else user_name)
            except: pass
            
            p1, p2, p3 = "", "", ""
            if "-" in user_phone: parts = user_phone.split("-"); p1, p2, p3 = parts if len(parts)==3 else ("","","")
            elif len(user_phone) == 11: p1, p2, p3 = user_phone[:3], user_phone[3:7], user_phone[7:]
            if p2:
                 self.driver.find_element(By.ID, "BI_TEL2").send_keys(p2)
                 time.sleep(0.05)
                 self.driver.find_element(By.ID, "BI_TEL3").send_keys(p3)
                 self.log("⏱️ 휴먼 인식 방지 딜레이 (0.05초)...")
                 time.sleep(0.05)

            try: self.driver.execute_script("arguments[0].click();", self.driver.find_element(By.XPATH, "//input[@name='all_agree' and @value='Y']"))
            except: pass

            self.log("🚀 Clicking Submit...")
            try:
                self.driver.execute_script("arguments[0].click();", self.driver.find_element(By.ID, "submit"))
                alert = wait.until(EC.alert_is_present())
                if not self.simulation_mode: alert.accept(); self.log("✅ Submitted!")
                else: self.log("🛑 SIMULATION MODE: Stopped.")
            except Exception as e: self.log(f"⚠️ Submit failed: {e}")

        except Exception as e: self.log(f"ℹ️ Autofill error: {e}")

        self.log("✅ Done.")
        while True: time.sleep(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    with open(args.config, 'r', encoding='utf-8') as f: config = json.load(f)
    bot = ByteBot(config)
    try: bot.run()
    except KeyboardInterrupt: bot.stop()