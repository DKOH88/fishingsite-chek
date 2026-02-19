import sys
import json
import time
import argparse
import threading
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from base_bot import BaseFishingBot

class Arirang1Bot(BaseFishingBot):
    def __init__(self, config):
        super().__init__(config)
        self.success_event = threading.Event()
        self.browser_threads = []
        self.browsers = []
        self.max_browsers = 3  # 최대 브라우저 수 (메인 + 재시도 2회)

    def monitor_browser_for_success(self, driver, browser_id):
        """백그라운드에서 브라우저의 성공 여부를 모니터링"""
        self.log(f"🔍 [브라우저{browser_id}] 백그라운드 모니터링 시작...")
        while not self.success_event.is_set():
            try:
                # URL 확인: reservation_detail
                if "reservation_detail" in driver.current_url:
                    self.log(f"🎉 [브라우저{browser_id}] 예약 성공! (URL: reservation_detail)")
                    self.success_event.set()
                    return
                # 페이지 텍스트 확인
                page_text = driver.page_source
                success_keywords = ['예약현황', '예약접수 완료!', '총 상품금액', '예약금']
                if any(kw in page_text for kw in success_keywords):
                    self.log(f"🎉 [브라우저{browser_id}] 예약 성공! (텍스트 확인)")
                    self.success_event.set()
                    return
            except:
                pass
            time.sleep(0.1)
        self.log(f"🛑 [브라우저{browser_id}] 모니터링 중지")

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

        # ID Mapping Logic
        # 4월: 1일(1570425) ~ 30일(1570454)
        # 9월: 1일(1553688), 2일(1570578), 3일(1570579), 4일(1570580), 5일(1570405), 6일(1570580)~30일(1570605)
        # 10월: 1일(1570606) ~ 30일(1570636)
        
        try:
            d_target = datetime.strptime(target_date_str, "%Y%m%d")
            target_month = d_target.month
            target_day = d_target.day
            
            if target_month == 4:
                # 4월 1일 ~ 30일
                if 1 <= target_day <= 30:
                    target_id = 1570425 + (target_day - 1)
                else: raise ValueError("Invalid day for April")

            elif target_month == 9:
                if target_day == 1: target_id = 1553688
                elif target_day == 2: target_id = 1570578
                elif target_day == 3: target_id = 1570579
                elif target_day == 4: target_id = 1570580
                elif target_day == 5: target_id = 1570405
                elif 6 <= target_day <= 30:
                    # 9월 6일(1570580) ~ 30일(1570604/605?) -> User said ~1570605.
                    # 30-6 = 24. 1570580 + 24 = 1570604. 
                    # If user said 1570605, maybe day 6 starts at 1570581? 
                    # However, strictly following 9/4 is 1570580.
                    # I will trust the start ID for the range 9/6 is 1570580? 
                    # Or maybe 9/6 is 1570581? Let's check user text carefully: "9월6일-1570580 ~ 9월30일-1570605"
                    # Range length: 30-6+1 = 25 days.
                    # ID length: 1570605 - 1570580 + 1 = 26 IDs.
                    # Mismatch by 1. 
                    # Assuming standard increment from start ID:
                    target_id = 1570580 + (target_day - 6)
                else: raise ValueError("Invalid day for September")
            
            elif target_month == 10:
                # 10월 1일(1570606) ~ 30일(1570636)
                if 1 <= target_day <= 30:
                    target_id = 1570606 + (target_day - 1)
                elif target_day == 31:
                     # Extrapolate if possible, or error
                     target_id = 1570636 + 1
                else: raise ValueError("Invalid day for October")
                
            else:
                self.log(f"❌ {target_month}월은 ID 매핑이 없습니다. (4, 9, 10월만 지원)")
                return
            
            url = f"https://arirang.sunsang24.com/mypage/reservation_ready/{target_id}"
            self.log(f"🎯 Target URL: {url} (ID: {target_id}, {target_month}월 {target_day}일)")
            
        except Exception as e:
            self.log(f"❌ Date calculation error: {e}")
            return
        
        # 2.5 Pre-load
        self.log(f"🌍 페이지 사전 로드 중: {url}")
        try:
             self.driver.get(url)
             # Handle "잘못된 접근방식입니다" alert if present
             try:
                 alert = WebDriverWait(self.driver, 1).until(EC.alert_is_present())
                 alert_text = alert.text
                 self.log(f"🔔 사전 로드 시 알림 발생: {alert_text}")
                 alert.accept()
                 self.log("✅ 알림 확인 (오픈 시간 대기)")
             except:
                 pass
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
        max_retries = 5000
        step1_success = False

        for attempt in range(max_retries):
            try:
                self.driver.get(url)
                
                # Handle "잘못된 접근입니다.[배일정이 존재하지 않습니다.]" alert (서버 미오픈 시)
                try:
                    alert = WebDriverWait(self.driver, 0.05).until(EC.alert_is_present())
                    alert_text = alert.text
                    if "잘못된" in alert_text or "배일정" in alert_text or "존재하지" in alert_text:
                        self.log(f"⚠️ 서버 미오픈: {alert_text} ({attempt+1}/{max_retries})")
                        alert.accept()
                        time.sleep(0.2)  # 확인 후 안정화 딜레이
                        continue
                    else:
                        alert.accept()
                except:
                    pass  # 알림창 없음 = 페이지 열림 가능성
                
                if "Bad Gateway" in self.driver.title:
                    continue
                
                if "login" in self.driver.current_url:
                    self.log("🔒 Redirected to Login Page.")
                    time.sleep(0.01)
                    continue

                # 페이지 준비 확인: '계좌번호', '환불계좌' 텍스트 감지 (실제 오픈 시에만 표시됨)
                if "reservation_ready" in self.driver.current_url:
                    try:
                        page_text = self.driver.page_source
                        ready_keywords = ['계좌번호', '환불계좌']
                        if any(kw in page_text for kw in ready_keywords):
                            self.log("✅ Page Ready! (예약 페이지 오픈 감지)")
                            step1_success = True
                            break
                    except:
                        pass
                    
                    # Fallback: 요소 즉시 감지 (대기 없음)
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, "input[name='default_schedule_no'], .fishtype, #btn_payment, a.plus")
                        if len(elements) > 0:
                            self.log("✅ Page Ready! (요소 감지)")
                            step1_success = True
                            break
                    except:
                        pass
                        
            except Exception as e:
                pass

        if not step1_success:
             self.log("❌ Failed to open reservation page.")

        # ========== 4. 예약 정보 입력 단계 (멀티 브라우저 재시도 루프) ==========
        while True:
            # 다른 브라우저에서 성공 감지 시 즉시 종료
            if self.success_event.is_set():
                self.log("🎉 예약 성공 감지! 종료합니다.")
                break
            
            # 새 브라우저인 경우 예약 페이지로 이동
            if len(self.browsers) > 0:
                self.log(f"🌍 새 브라우저로 예약 페이지 접속 중: {url}")
                self.driver.get(url)
                try:
                    alert = WebDriverWait(self.driver, 1).until(EC.alert_is_present())
                    alert.accept()
                except:
                    pass
                time.sleep(0.5)
                
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
                    # 4.2a 가용 좌석 수 파악
                    self.log("📊 가용 좌석 파악 중...")
                    available_checkboxes = self.driver.find_elements(By.CSS_SELECTOR, "input[name='select_seat_nos[]']")
                    available_count = len(available_checkboxes)
                    target_count = min(configured_count, available_count)
                    self.log(f"📊 가용 좌석 수: {available_count}석, 설정 인원: {configured_count}명")
                    
                    if target_count == 0:
                        self.log("❌ 가용 좌석이 없습니다!")
                        continue  # 새 브라우저로 재시도

                    # 4.3a 인원 선택
                    self.log(f"👥 인원 선택 중... ({target_count}명)")
                    try:
                        plus_btn = self.driver.find_element(By.CSS_SELECTOR, "a.plus")
                        for i in range(target_count):
                            plus_btn.click()
                            time.sleep(0.01)
                        self.log(f"✅ 인원 {target_count}명 설정 완료")
                    except Exception as e:
                        self.log(f"⚠️ Person count selection error: {e}")
                    
                    # 4.4a 좌석 선택 (아무 좌석)
                    self.log(f"💺 좌석 선택 중... ({target_count}석)")
                    selected_seats = 0
                    for checkbox in available_checkboxes:
                        if selected_seats >= target_count:
                            break
                        try:
                            if not checkbox.is_selected():
                                self.driver.execute_script("arguments[0].click();", checkbox)
                                selected_seats += 1
                                time.sleep(0.01)
                        except:
                            continue
                    self.log(f"✅ 좌석 선택 완료! 총 {selected_seats}석")
                else:
                    # 4.2b 인원 선택만
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

                time.sleep(0.05)  # 전체 동의 후 안정화 딜레이
                
                # 4.5 예약하기 버튼 클릭
                self.log("🚀 예약하기 버튼 클릭...")
                try:
                    submit_btn = self.driver.find_element(By.CSS_SELECTOR, "#btn_payment, a.btn_payment")
                    self.driver.execute_script("arguments[0].click();", submit_btn)
                    
                    # 알림창 처리
                    try:
                        alert = WebDriverWait(self.driver, 3).until(EC.alert_is_present())
                        alert_text = alert.text
                        self.log(f"🔔 Alert: {alert_text}")
                        
                        if not self.simulation_mode:
                            alert.accept()
                        else:
                            self.log("🛑 시뮬레이션 모드: 알림창 확인 후 중단")
                            return
                    except:
                        pass  # 알림창 없음
                    
                    # 예약 성공 확인 (10초 폴링)
                    self.log("🔍 예약 결과 확인 중 (최대 10초)...")
                    check_start = time.time()
                    success_detected = False
                    
                    while time.time() - check_start < 10:
                        # 다른 브라우저에서 성공 감지 시 즉시 종료
                        if self.success_event.is_set():
                            self.log("🎉 다른 브라우저에서 예약 성공 감지! 종료합니다.")
                            return
                        
                        # 1. URL 확인: reservation_detail
                        if "reservation_detail" in self.driver.current_url:
                            self.log("🎉 예약 성공! (URL: reservation_detail 감지)")
                            self.success_event.set()
                            success_detected = True
                            break
                        
                        # 2. 페이지 텍스트 확인
                        try:
                            page_text = self.driver.page_source
                            success_keywords = ['예약현황', '예약접수 완료!', '총 상품금액', '예약금']
                            if any(kw in page_text for kw in success_keywords):
                                self.log("🎉 예약 성공! (텍스트 확인)")
                                self.success_event.set()
                                success_detected = True
                                break
                        except:
                            pass
                        
                        time.sleep(0.2)
                    
                    if success_detected:
                        self.log("✅ 예약이 정상적으로 완료되었습니다!")
                        try:
                            elapsed_time = time.time() - process_start_time
                            self.log(f"⏱️ 총 소요 시간: {elapsed_time:.2f}초")
                        except: pass
                        self.log("✅ 예약 봇 실행 시퀀스가 모두 완료되었습니다.")
                        while True: time.sleep(1)
                        return
                    else:
                        # 10초 후에도 성공 확인 불가 → 백그라운드 모니터링 시작 + 새 브라우저
                        browser_count = len(self.browsers) + 1
                        self.log(f"⏳ [브라우저{browser_count}] 10초 내 성공 확인 불가. 백그라운드 모니터링으로 전환...")
                        
                        old_driver = self.driver
                        self.browsers.append(old_driver)
                        
                        # 백그라운드 모니터링 스레드 시작
                        t = threading.Thread(target=self.monitor_browser_for_success, args=(old_driver, browser_count))
                        t.daemon = True
                        t.start()
                        self.browser_threads.append(t)
                        
                        # 최대 브라우저 수 체크 (메인 + 재시도 2회 = 최대 3개)
                        if len(self.browsers) >= self.max_browsers:
                            self.log(f"⚠️ 최대 브라우저 수({self.max_browsers}) 도달. 결과 대기 중...")
                            while not self.success_event.is_set():
                                time.sleep(0.5)
                            self.log("🎉 예약 성공 감지! 종료합니다.")
                            return
                        
                        # 새 브라우저로 재시도
                        self.log(f"🔄 새 브라우저 열고 재시도 ({len(self.browsers)+1}/{self.max_browsers})...")
                        self.setup_driver()
                        wait = WebDriverWait(self.driver, 30)
                        continue  # while 루프 재시작
                        
                except Exception as e:
                    self.log(f"⚠️ Submit error: {e}")
                    continue  # 재시도

            except Exception as e:
                self.log(f"⚠️ Process Error: {e}")
                continue  # 재시도

        # 성공하지 못했으면 모니터링 결과 대기
        if not self.success_event.is_set() and self.browsers:
            self.log("⏳ 모든 브라우저 결과 대기 중...")
            while not self.success_event.is_set():
                time.sleep(0.5)
            self.log("🎉 예약 성공 감지!")
        
        self.log("✅ 예약 봇 실행 시퀀스가 모두 완료되었습니다.")
        while True: time.sleep(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    with open(args.config, 'r', encoding='utf-8') as f: config = json.load(f)
    bot = Arirang1Bot(config)
    try: bot.run()
    except KeyboardInterrupt: bot.stop()
