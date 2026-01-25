import sys
import json
import time
import argparse
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from base_bot import BaseFishingBot

class DojiBot(BaseFishingBot):
    def run(self):
        self.setup_driver()
        wait = WebDriverWait(self.driver, 30)

        # 1. Parse Config
        target_date_str = self.config.get('target_date', '20260901')
        target_time = self.config.get('target_time', '09:00:00')
        test_mode = self.config.get('test_mode', False)
        self.simulation_mode = self.config.get('simulation_mode', False)
        
        user_name = self.config.get('user_name', '')
        user_depositor = self.config.get('user_depositor', '')
        user_phone = self.config.get('user_phone', '')
        configured_count = int(self.config.get('person_count', 1))

        # 2. Calculate Target ID (도지호 예약 ID 리스트)
        # 9월: 1일=1650579 ... 30일=1650608 (1650579 + day - 1)
        # 10월: 1일=1650609 ... 31일=1650639 (1650609 + day - 1)
        # 11월: 1일=1650640 ... 30일=1650669 (1650640 + day - 1)
        
        try:
            d_target = datetime.strptime(target_date_str, "%Y%m%d")
            target_month = d_target.month
            target_day = d_target.day
            
            if target_month == 7:
                # 7월: 1일=1650734 (테스트용)
                target_id = 1650734 + (target_day - 1)
            elif target_month == 9:
                target_id = 1650579 + (target_day - 1)
            elif target_month == 10:
                target_id = 1650609 + (target_day - 1)
            elif target_month == 11:
                target_id = 1650640 + (target_day - 1)
            else:
                self.log(f"❌ {target_month}월은 ID 매핑이 없습니다. (7월, 9월~11월만 지원)")
                return
            
            url = f"https://doji.sunsang24.com/mypage/reservation_ready/{target_id}"
            self.log(f"🎯 Target URL: {url} (ID: {target_id}, {target_month}월 {target_day}일)")
            
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
                    time.sleep(0.01)
                    continue
                
                if "login" in self.driver.current_url:
                    self.log("🔒 Redirected to Login Page.")
                    time.sleep(0.01)
                    continue

                if "reservation_ready" in self.driver.current_url:
                    try:
                        WebDriverWait(self.driver, 1).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='default_schedule_no'], .fishtype, #btn_payment, a.plus"))
                        )
                        self.log("✅ Page Ready!")
                        step1_success = True
                        break
                    except:
                        self.log(f"⏳ Waiting for elements... ({attempt})")
                        time.sleep(0.01)
            except Exception as e:
                time.sleep(0.01)

        if not step1_success:
             self.log("❌ Failed to open reservation page.")

        # ========== 4. 예약 정보 입력 단계 ==========
        process_start_time = time.time()
        
        try:
            # 4.1 낚시 종류 선택
            self.log("🎣 낚시 종류 선택 중...")
            target_keywords = ['갑오징어', '쭈꾸미', '쭈갑']
            found_fish = False
            
            try:
                radios = self.driver.find_elements(By.CSS_SELECTOR, "input[type='radio'][name='default_schedule_no']")
                self.log(f"🔎 Found {len(radios)} fish type options")
                
                if len(radios) == 1:
                    self.log("✨ 단일 어종만 있음, 자동 선택")
                    self.driver.execute_script("arguments[0].click();", radios[0])
                    found_fish = True
                    time.sleep(0.01)
                elif len(radios) > 1:
                    fish_spans = self.driver.find_elements(By.CSS_SELECTOR, "dt.fishtype span.fish")
                    
                    for keyword in target_keywords:
                        if found_fish: break
                        for fish_span in fish_spans:
                            if keyword in fish_span.text:
                                self.log(f"✨ Found fish type: {keyword}")
                                try:
                                    parent_dt = fish_span.find_element(By.XPATH, "./ancestor::dt[@class='fishtype']")
                                    radio = parent_dt.find_element(By.CSS_SELECTOR, "input[type='radio'][name='default_schedule_no']")
                                    self.driver.execute_script("arguments[0].click();", radio)
                                    self.log(f"✅ Selected fish type: {keyword}")
                                    time.sleep(0.01)
                                    found_fish = True
                                    break
                                except Exception as e:
                                    self.log(f"⚠️ Failed to click radio for {keyword}: {e}")
                    
                    if not found_fish:
                        self.log("⚠️ 키워드 매칭 없음, 첫번째 어종 선택")
                        self.driver.execute_script("arguments[0].click();", radios[0])
                        found_fish = True
                        time.sleep(0.01)
            except Exception as e:
                self.log(f"⚠️ Fishing type selection error: {e}")

            # 4.2 인원 선택 (Plus 버튼 빠른 클릭)
            self.log(f"👥 인원 선택 중... ({configured_count}명)")
            try:
                plus_btn = self.driver.find_element(By.CSS_SELECTOR, "a.plus")
                for i in range(configured_count):
                    plus_btn.click()
                    time.sleep(0.01)
                self.log(f"✅ 인원 {configured_count}명 설정 완료")
            except Exception as e:
                self.log(f"⚠️ Person count selection error: {e}")

            # 4.3 예약자 정보 입력
            self.log("✍️ 예약 정보 입력 중...")
            try:
                name_input = self.driver.find_element(By.CSS_SELECTOR, "input[name='name']")
                name_input.clear()
                name_input.send_keys(user_name)
                self.log(f"✅ 예약자명 입력: {user_name}")
                time.sleep(0.01)
                
                try:
                    deposit_input = self.driver.find_element(By.CSS_SELECTOR, "input[name='deposit_name']")
                    if user_depositor and user_depositor != user_name:
                        deposit_input.clear()
                        deposit_input.send_keys(user_depositor)
                        self.log(f"✅ 입금자명 입력: {user_depositor}")
                        time.sleep(0.01)
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
                    time.sleep(0.01)
                    phone3_input = self.driver.find_element(By.CSS_SELECTOR, "input[name='phone3']")
                    phone3_input.send_keys(p3)
                    self.log(f"✅ 전화번호 입력: {p2}-{p3}")
                    time.sleep(0.01)
            except Exception as e:
                self.log(f"⚠️ Info input error: {e}")

            # 4.4 전체 동의 체크
            try:
                all_check = self.driver.find_element(By.CSS_SELECTOR, "input[name='all_check']")
                if not all_check.is_selected():
                    self.driver.execute_script("arguments[0].click();", all_check)
                    self.log("✅ 전체 동의 체크")
            except Exception as e:
                self.log(f"⚠️ All check error: {e}")

            # 4.5 예약하기 버튼 클릭
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
    bot = DojiBot(config)
    try: bot.run()
    except KeyboardInterrupt: bot.stop()
