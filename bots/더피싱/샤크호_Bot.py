import sys
import json
import time
import argparse
import threading
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from base_bot import BaseFishingBot

class FriendBot(BaseFishingBot):
    def __init__(self, config):
        super().__init__(config)
        self.success_event = threading.Event()
        self.browser_threads = []
        self.browsers = []  # 열린 브라우저 목록
    
    def monitor_browser_for_success(self, driver, browser_id):
        """별도 스레드에서 브라우저 성공 여부 모니터링"""
        self.log(f"🔍 [브라우저{browser_id}] 백그라운드 모니터링 시작...")
        
        while not self.success_event.is_set():
            try:
                # 조건 A: URL
                if "step3.php" in driver.current_url:
                    self.log(f"🎉 [브라우저{browser_id}] 예약 성공! (URL: step3.php)")
                    self.success_event.set()
                    return
                
                # 조건 B: 텍스트
                if "신청이 완료되었습니다" in driver.page_source:
                    self.log(f"🎉 [브라우저{browser_id}] 예약 성공! (텍스트 확인)")
                    self.success_event.set()
                    return
                
                # 조건 C: 탭 (3번째 li의 class="on")
                tabs = driver.find_elements(By.CSS_SELECTOR, ".top_tab_menu li, .top_tab_menu2 li")
                if len(tabs) >= 3 and "on" in (tabs[2].get_attribute("class") or ""):
                    self.log(f"🎉 [브라우저{browser_id}] 예약 성공! (탭 활성화)")
                    self.success_event.set()
                    return
            except:
                pass
            
            time.sleep(0.1)
        
        self.log(f"🛑 [브라우저{browser_id}] 다른 브라우저 성공으로 모니터링 중지")

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
        
        # 2. Build URL
        base_url = "http://www.sharkho.com/_core/module/reservation_boat_v5.2_seat1/popup.step1.php"
        url = f"{base_url}?date={target_date}&PA_N_UID=2199"
        
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
        
        while True:
            # 백그라운드 스레드에서 성공 신호가 왔는지 체크
            if self.success_event.is_set():
                self.log("✅ 예약 완료! (백그라운드 브라우저에서 성공)")
                return
            
            max_retries = 5000 
            retry_interval = 1 
            step1_success = False

            for attempt in range(max_retries):
                try:
                    current_url = self.driver.current_url
                    if base_url not in current_url:
                        self.driver.get(url)
 
                    page_source = self.driver.page_source
                    current_url = self.driver.current_url

                    # ERR_TOO_MANY_REDIRECTS 또는 waitingrequest 리다이렉트 에러 감지
                    if "ERR_TOO_MANY_REDIRECTS" in page_source or "리디렉션한 횟수가 너무 많습니다" in page_source or "waitingrequest" in current_url:
                        self.log(f"⚠️ 리다이렉트 에러 감지! 고속 복구 시도 (쿠키삭제 후 재접속)... ({attempt+1}/{max_retries})")
                        try:
                            self.driver.delete_all_cookies()
                            time.sleep(0.1) 
                            self.driver.get(url)
                        except Exception as e:
                            self.log(f"⚠️ 고속 복구 실패 ({e}), 브라우저 재시작...")
                            try: self.driver.quit()
                            except: pass
                            self.setup_driver()
                            wait = WebDriverWait(self.driver, 30)
                            self.driver.get(url)
                        continue
                    
                    if "Bad Gateway" in self.driver.title:
                        self.log(f"⚠️ 서버 오류 (502). 새로고침 중... ({attempt+1}/{max_retries})")
                        time.sleep(0.1)
                        self.driver.get(url)
                        continue
                    
                    if any(err in page_source for err in ['없는', '권한', '잘못']):
                        self.log(f"⚠️ 에러 페이지 감지 (없는/권한/잘못). 0.1초 후 재시도... ({attempt+1}/{max_retries})")
                        time.sleep(0.1)
                        self.driver.get(url)
                        continue
                    
                    reservation_keywords = ['STEP 01', '예약1단계', '배 선택']
                    matched_keywords = [txt for txt in reservation_keywords if txt in page_source]
                    
                    if matched_keywords:
                        self.log(f"📄 예약 페이지 감지! 감지된 텍스트: {matched_keywords} ({attempt+1}/{max_retries})")
                        try:
                            WebDriverWait(self.driver, 3).until(
                                EC.presence_of_element_located((By.CLASS_NAME, "ps_selis"))
                            )
                        except:
                            self.log(f"⏳ 3초 내 낚시종류 버튼 미발견. 새로고침...")
                            self.driver.refresh()
                            continue
                    else:
                        self.log(f"⏳ 페이지 준비 안됨. 재시도... ({attempt+1}/{max_retries})")
                        time.sleep(0.5)
                        self.driver.refresh() 
                        continue
                    
                    # [TIMING START] - Total process timer
                    process_start_time = time.time()
                    
                    # Step: Find fishing type
                    step_start = time.time()
                    time.sleep(0.05)
                    radios = self.driver.find_elements(By.CSS_SELECTOR, "input.PS_N_UID")
                    self.log(f"🎣 낚시 종류 선택 항목 찾는 중... (소요시간: {time.time()-step_start:.2f}초)")
    
                    if len(radios) == 1:
                        step_start = time.time()
                        try:
                            self.driver.execute_script("arguments[0].click();", radios[0])
                            self.log(f"✨ 단일 선택 항목 감지됨 (CSS). 자동으로 선택합니다. (소요시간: {time.time()-step_start:.2f}초)")
                            step1_success = True
                            break
                        except Exception as e:
                            self.log(f"⚠️ Failed to click single radio: {e}")
                    
                    all_spans = self.driver.find_elements(By.CLASS_NAME, "ps_selis")
                    self.log(f"🔎 총 {len(all_spans)}개의 낚시 종류 후보를 찾았습니다.")
                    
                    target_keywords = []
                    target_ship_cfg = self.config.get('target_ship', '').strip()
                    if target_ship_cfg: target_keywords.append(target_ship_cfg)
                    target_keywords.extend(['쭈갑', '쭈꾸미&갑오징어', '쭈&갑', '쭈꾸미', '갑오징어', '문어'])
                    
                    found_click = False
                    for keyword in target_keywords:
                        if found_click: break
                        for span in all_spans:
                            text = span.text.strip()
                            if keyword in text:
                                step_start = time.time()
                                time.sleep(0.05)
                                try:
                                    radio = span.find_element(By.XPATH, "./parent::td/preceding-sibling::td//input[@type='radio']")
                                    self.driver.execute_script("arguments[0].click();", radio)
                                    time.sleep(0.05)
                                    self.log(f"✨ Match found! '{keyword}' -> Clicked radio (Parent TD). (소요시간: {time.time()-step_start:.2f}초)")
                                    found_click = True
                                except:
                                    try:
                                        radio = span.find_element(By.XPATH, "./preceding-sibling::input[@type='radio']")
                                        self.driver.execute_script("arguments[0].click();", radio)
                                        time.sleep(0.05)
                                        self.log(f"✨ Match found! '{keyword}' -> Clicked radio (Preceding Sibling). (소요시간: {time.time()-step_start:.2f}초)")
                                        found_click = True
                                    except:
                                         try:
                                            span.click()
                                            time.sleep(0.05)
                                            self.log(f"✨ Match found! '{keyword}' -> Clicked span directly. (소요시간: {time.time()-step_start:.2f}초)")
                                            found_click = True
                                         except: pass
                                if found_click: break
                        if found_click: break
                    
                    if found_click:
                        step_start = time.time()
                        self.log("⏳ 인원 선택(BI_IN) 활성화 대기 중 (최대 5초)...")
                        try:
                            WebDriverWait(self.driver, 5).until(
                                EC.element_to_be_clickable((By.ID, "BI_IN"))
                            )
                            self.log(f"✅ 인원 선택 활성화 감지! 2단계 진입 성공! (소요시간: {time.time()-step_start:.2f}초)")
                            step1_success = True
                            break
                        except:
                            self.log("⚠️ 5초 내 인원 선택 미감지. 새로고침 후 재시도...")
                            self.driver.refresh()
                            continue
                    else:
                        self.log("⚠️ 키워드 매칭 없음, 첫번째 어종 자동 선택 시도...")
                        try:
                            radios = self.driver.find_elements(By.CSS_SELECTOR, "input.PS_N_UID")
                            if radios:
                                step_start = time.time()
                                self.driver.execute_script("arguments[0].click();", radios[0])
                                self.log(f"✅ 첫번째 어종 자동 선택 완료! (소요시간: {time.time()-step_start:.2f}초)")
                                try:
                                    WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.ID, "BI_IN")))
                                    step1_success = True
                                    break
                                except:
                                    self.driver.refresh()
                                    continue
                            else:
                                self.log("⚠️ 선택 가능한 어종이 없습니다.")
                                self.driver.refresh()
                                continue
                        except:
                            self.driver.refresh()
                            continue

                except Exception as e:
                    self.log(f"⚠️ Step1 Retry Error: {e}")
                    time.sleep(retry_interval)
            
            if not step1_success:
                 self.log("❌ Step 1 FailedLoop. Restarting outer loop...")
                 continue

            # Step 1.5: Select Person Count
            step_start = time.time()
            time.sleep(0.05)
            try:
                from selenium.webdriver.support.ui import Select
                select_el = wait.until(EC.element_to_be_clickable((By.ID, "BI_IN")))
                select_obj = Select(select_el)
                current_val = select_obj.first_selected_option.get_attribute("value")
                
                configured_count = int(self.config.get('person_count', '1'))
                target_count = str(configured_count)
                
                if current_val != target_count:
                    select_obj.select_by_value(target_count)
                    time.sleep(0.05)
                    self.log(f"👥 인원을 {target_count}명으로 설정합니다... (소요시간: {time.time()-step_start:.2f}초)")
                else:
                    self.log(f"👥 이미 {target_count}명으로 설정되어 있습니다. (소요시간: {time.time()-step_start:.2f}초)")
            except Exception as e:
                self.log(f"⚠️ Error person count: {e}")
                self.driver.refresh()
                continue

            # Step 2: Info Form & Submit
            self.log("🪑 예약 정보 입력 페이지(2단계) 진입 중...")
            should_hard_restart = False

            try:
                # Name Input
                step_start = time.time()
                name_input = wait.until(EC.element_to_be_clickable((By.NAME, "BI_NAME")))
                name_input.clear()
                time.sleep(0.05)
                name_input.send_keys(user_name)
                time.sleep(0.05)
                self.log(f"✍️ 성함 입력 중: {user_name} (소요시간: {time.time()-step_start:.2f}초)")
                
                # Depositor
                if user_depositor:
                    try:
                        step_start = time.time()
                        bank_input = self.driver.find_element(By.ID, "BI_BANK")
                        bank_input.clear()
                        time.sleep(0.05)
                        bank_input.send_keys(user_depositor)
                        time.sleep(0.05)
                        self.log(f"✍️ 입금자명 입력 중: {user_depositor} (소요시간: {time.time()-step_start:.2f}초)")
                    except: pass

                # Phone
                p1, p2, p3 = "", "", ""
                if "-" in user_phone:
                    parts = user_phone.split("-")
                    p1, p2, p3 = parts[0], parts[1], parts[2]
                elif len(user_phone) == 11:
                    p1, p2, p3 = user_phone[:3], user_phone[3:7], user_phone[7:]
                
                if p2 and p3:
                    step_start = time.time()
                    self.driver.find_element(By.ID, "BI_TEL2").send_keys(p2)
                    time.sleep(0.05)
                    self.driver.find_element(By.ID, "BI_TEL3").send_keys(p3)
                    time.sleep(0.05)
                    self.log(f"📞 연락처 입력 중: {p2}-{p3} (소요시간: {time.time()-step_start:.2f}초)")

                # Agree
                try:
                    step_start = time.time()
                    agree_btn = self.driver.find_element(By.XPATH, "//input[@name='all_agree' and @value='Y']")
                    self.driver.execute_script("arguments[0].click();", agree_btn)
                    time.sleep(0.05)
                    self.log(f"✅ '전체 동의' 체크박스 클릭 완료. (소요시간: {time.time()-step_start:.2f}초)")
                except: pass

                # Step 3: Submit Logic (3-Step Process)
                self.log("🚀 [STEP 1] '예약 신청하기' 버튼 클릭 시도...")
                max_submit_retries = 3
                for submit_attempt in range(max_submit_retries):
                    step_start = time.time()
                    self.log(f"🚀 [STEP 1] 제출 시도 ({submit_attempt + 1}/{max_submit_retries})...")
                    try:
                        submit_btn = self.driver.find_element(By.ID, "submit")
                        self.driver.execute_script("arguments[0].click();", submit_btn)
                        
                        self.log("🔔 [STEP 1] 팝업 알림창 대기 중...")
                        alert = wait.until(EC.alert_is_present())
                        alert_text = alert.text
                        self.log(f"🔔 [STEP 1] 알림창 내용: {alert_text} (소요시간: {time.time()-step_start:.2f}초)")
                        
                        if "정상적으로 예약해 주십시오" in alert_text:
                            self.log("⚠️ 오류! 처음부터 다시 시작.")
                            try:
                                time.sleep(0.05)
                                alert.accept()
                                time.sleep(0.05)
                                self.driver.refresh()
                                time.sleep(0.05)
                            except: pass
                            should_hard_restart = True
                            break
                        
                        # Accept Step 1 Alert
                        if "이미" in alert_text or "불가능" in alert_text:
                            self.log("⚠️ 좌석 선점 실패! 즉시 재시도...")
                            alert.accept()
                            self.driver.refresh()
                            should_hard_restart = True
                            break
                        alert.accept()
                        
                        if self.simulation_mode:
                            self.log("🛑 시뮬레이션 종료")
                            try:
                                elapsed_time = time.time() - process_start_time
                                self.log(f"⏱️ 총 소요 시간: {elapsed_time:.2f}초")
                            except: pass
                            self.log("✅ 예약 봇 실행 시퀀스가 모두 완료되었습니다.")
                            return
                            
                        # Wait for Step 2
                        self.log("⏳ [STEP 2] 진입 대기 중 (5초 폴링)...")
                        step2_start_time = time.time()
                        step2_entered = False
                        
                        while time.time() - step2_start_time < 10:
                            try:
                                # Check URL
                                if "step2.php" in self.driver.current_url:
                                    step2_entered = True
                                    self.log("✨ [STEP 2] URL 감지됨 (step2.php)")
                                    time.sleep(0.05)
                                    break
                                    
                                # Check Class (Handle both .top_tab_menu2 and .top_tab_menu)
                                step2_items = self.driver.find_elements(By.CSS_SELECTOR, ".top_tab_menu2 li, .top_tab_menu li")
                                if len(step2_items) >= 2 and "on" in step2_items[1].get_attribute("class"): 
                                    step2_entered = True
                                    self.log("✨ [STEP 2] 탭 활성화 감지됨")
                                    break
                            except: pass
                            time.sleep(0.1)
                            
                        if not step2_entered:
                            self.log("⚠️ [STEP 2] 진입 실패 (타임아웃). 백그라운드 모니터링 + 새 브라우저...")
                            
                            # 현재 브라우저를 백그라운드 모니터링으로 전환
                            old_driver = self.driver
                            browser_id = len(self.browsers) + 1
                            self.browsers.append(old_driver)
                            
                            t = threading.Thread(target=self.monitor_browser_for_success, args=(old_driver, browser_id))
                            t.daemon = True
                            t.start()
                            self.browser_threads.append(t)
                            
                            # 새 브라우저 생성
                            self.setup_driver()
                            wait = WebDriverWait(self.driver, 30)
                            break # Exit to outer while True loop with new browser
                            
                        # Execute Step 2 Submit
                        self.log("🚀 [STEP 2] '예약 신청하기' 버튼 클릭!")
                        try:
                            submit_btn_step2 = self.driver.find_element(By.ID, "submit")
                            self.driver.execute_script("arguments[0].click();", submit_btn_step2)
                        except Exception as e2:
                             self.log(f"⚠️ [STEP 2] 버튼 클릭 실패: {e2}")
                             
                        # Wait for Step 3 (Success)
                        self.log("⏳ [STEP 3] 최종 완료 확인 대기 중 (5초 폴링)...")
                        step3_start_time = time.time()
                        success_detected = False
                        
                        while time.time() - step3_start_time < 10:
                            try:
                                # Indicator A: URL Check (step3.php)
                                if "step3.php" in self.driver.current_url:
                                    success_detected = True
                                    self.log("🎉 [STEP 3] 예약 성공! (URL: step3.php)")
                                    break
                                    
                                # Indicator B: Success Text
                                if "신청이 완료되었습니다" in self.driver.page_source:
                                    success_detected = True
                                    self.log("🎉 [STEP 3] 예약 성공! (텍스트 확인)")
                                    break
                                    
                                # Indicator C: Step 3 Tab
                                step3_items = self.driver.find_elements(By.CSS_SELECTOR, ".top_tab_menu2 li, .top_tab_menu li")
                                if len(step3_items) >= 3 and "on" in step3_items[2].get_attribute("class"):
                                    success_detected = True
                                    self.log("🎉 [STEP 3] 예약 성공! (탭 활성화 확인)")
                                    break
                            except: pass
                            time.sleep(0.1)
                            
                        if success_detected:
                            try:
                                elapsed_time = time.time() - process_start_time
                                self.log(f"⏱️ 총 소요 시간: {elapsed_time:.2f}초")
                            except: pass
                            self.log("✅ 예약 봇 실행 시퀀스가 모두 완료되었습니다.")
                            return

                        self.log("⚠️ [STEP 3] 최종 완료 미확인. 백그라운드 모니터링 + 새 브라우저...")
                        
                        # 현재 브라우저를 백그라운드 모니터링으로 전환
                        old_driver = self.driver
                        browser_id = len(self.browsers) + 1
                        self.browsers.append(old_driver)
                        
                        t = threading.Thread(target=self.monitor_browser_for_success, args=(old_driver, browser_id))
                        t.daemon = True
                        t.start()
                        self.browser_threads.append(t)
                        
                        # 새 브라우저 생성
                        self.setup_driver()
                        wait = WebDriverWait(self.driver, 30)
                        break

                    except Exception as e:
                        self.log(f"⚠️ Submit Error: {e}")
                        break
                
                if should_hard_restart: continue

            except Exception as e:
                self.log(f"⚠️ Step 2 Error: {e}")
                self.driver.refresh()
                continue
            
            self.log("🔄 루프 재시작...")
            time.sleep(0.5)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    with open(args.config, 'r', encoding='utf-8') as f: config = json.load(f)
    bot = FriendBot(config)
    try: bot.run()
    except KeyboardInterrupt: bot.stop()
