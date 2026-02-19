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

class TeamF2Bot(BaseFishingBot):
    def __init__(self, config):
        super().__init__(config)
        self.success_event = threading.Event()
        self.browser_threads = []
        self.browsers = []
        self.max_browsers = 3

    def monitor_browser_for_success(self, driver, browser_id):
        self.log(f"🔍 [브라우저{browser_id}] 백그라운드 모니터링 시작...")
        while not self.success_event.is_set():
            try:
                if "reservation_detail" in driver.current_url:
                    self.log(f"🎉 [브라우저{browser_id}] 예약 성공! (URL: reservation_detail)")
                    self.success_event.set()
                    return
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

        target_date_str = self.config.get('target_date', '20260901')
        target_time = self.config.get('target_time', '09:00:00')
        test_mode = self.config.get('test_mode', False)
        self.simulation_mode = self.config.get('simulation_mode', False)
        
        user_name = self.config.get('user_name', '')
        user_depositor = self.config.get('user_depositor', '')
        user_phone = self.config.get('user_phone', '')
        configured_count = int(self.config.get('person_count', 1))

        try:
            d_target = datetime.strptime(target_date_str, "%Y%m%d")
            target_month = d_target.month
            target_day = d_target.day
            
            if target_month == 1:
                target_id = 1668286 + (target_day - 10)
            elif target_month == 3:
                target_id = 1638088 + (target_day - 1)
            elif target_month == 9:
                target_id = 1638241 + (target_day - 1)
            elif target_month == 10:
                target_id = 1638271 + (target_day - 1)
            elif target_month == 11:
                target_id = 1638302 + (target_day - 1)
            else:
                self.log(f"❌ {target_month}월은 ID 매핑이 없습니다. (1월, 3월, 9월~11월 지원)")
                return
            
            url = f"https://teamf.sunsang24.com/mypage/reservation_ready/{target_id}"
            self.log(f"🎯 Target URL: {url} (ID: {target_id}, {target_month}월 {target_day}일)")
            
        except Exception as e:
            self.log(f"❌ Date calculation error: {e}")
            return
        
        self.log(f"🌍 페이지 사전 로드 중: {url}")
        try:
             self.driver.get(url)
             try:
                 alert = WebDriverWait(self.driver, 1).until(EC.alert_is_present())
                 self.log(f"🔔 사전 로드 시 알림 발생: {alert.text}")
                 alert.accept()
             except:
                 pass
             self.log("✅ 사전 로드 완료.")
        except Exception as e:
             self.log(f"⚠️ Pre-load failed: {e}")

        if not test_mode:
            self.log(f"⏰ 실행 예약 시간: {target_time}...")
            self.wait_until_target_time(target_time)
        else:
            self.log("🚀 TEST MODE ACTIVE: Skipping wait!")

        self.log(f"🔥 예약 시도 시작 (반복 루프): {url}")
        max_retries = 5000
        step1_success = False

        for attempt in range(max_retries):
            try:
                self.driver.get(url)
                
                try:
                    alert = WebDriverWait(self.driver, 0.05).until(EC.alert_is_present())
                    alert_text = alert.text
                    if "잘못된" in alert_text or "배일정" in alert_text or "존재하지" in alert_text:
                        self.log(f"⚠️ 서버 미오픈: {alert_text} ({attempt+1}/{max_retries})")
                        alert.accept()
                        time.sleep(0.2)
                        continue
                    else:
                        alert.accept()
                except:
                    pass
                
                if "Bad Gateway" in self.driver.title:
                    continue
                
                if "login" in self.driver.current_url:
                    self.log("🔒 Redirected to Login Page.")
                    time.sleep(0.01)
                    continue

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

        while True:
            if self.success_event.is_set():
                self.log("🎉 예약 성공 감지! 종료합니다.")
                break
            
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
                self.log("🎣 낚시 종류 선택 중...")
                target_keywords = ['갑오징어', '쭈꾸미', '쭈갑']
                found_fish = False
                
                try:
                    radios = self.driver.find_elements(By.CSS_SELECTOR, "input[type='radio'][name='default_schedule_no']")
                    
                    if len(radios) == 1:
                        self.driver.execute_script("arguments[0].click();", radios[0])
                        found_fish = True
                        time.sleep(0.01)
                    elif len(radios) > 1:
                        fish_spans = self.driver.find_elements(By.CSS_SELECTOR, "dt.fishtype span.fish")
                        for keyword in target_keywords:
                            if found_fish: break
                            for fish_span in fish_spans:
                                if keyword in fish_span.text:
                                    try:
                                        parent_dt = fish_span.find_element(By.XPATH, "./ancestor::dt[@class='fishtype']")
                                        radio = parent_dt.find_element(By.CSS_SELECTOR, "input[type='radio'][name='default_schedule_no']")
                                        self.driver.execute_script("arguments[0].click();", radio)
                                        found_fish = True
                                        break
                                    except:
                                        pass
                        if not found_fish and radios:
                            self.driver.execute_script("arguments[0].click();", radios[0])
                except Exception as e:
                    self.log(f"⚠️ Fishing type selection error: {e}")

                has_seat_selection = False
                try:
                    page_text = self.driver.find_element(By.TAG_NAME, "body").text
                    if "자리선택" in page_text or "전체선택" in page_text:
                        has_seat_selection = True
                except:
                    pass

                if has_seat_selection:
                    available_checkboxes = self.driver.find_elements(By.CSS_SELECTOR, "input[name='select_seat_nos[]']")
                    available_count = len(available_checkboxes)
                    target_count = min(configured_count, available_count)
                    
                    if target_count == 0:
                        continue

                    try:
                        plus_btn = self.driver.find_element(By.CSS_SELECTOR, "a.plus")
                        for i in range(target_count):
                            plus_btn.click()
                            time.sleep(0.01)
                    except:
                        pass
                    
                    seat_priority = ['21', '23', '22', '24', '10', '20', '1', '11', '2', '9', '19']
                    selected_seats = 0
                    
                    for seat_num in seat_priority:
                        if selected_seats >= target_count:
                            break
                        try:
                            checkbox = self.driver.find_element(By.ID, f"select_seat_nos_num_{seat_num}")
                            if not checkbox.is_selected():
                                self.driver.execute_script("arguments[0].click();", checkbox)
                                selected_seats += 1
                        except:
                            continue
                    
                    if selected_seats < target_count:
                        for checkbox in available_checkboxes:
                            if selected_seats >= target_count:
                                break
                            try:
                                if not checkbox.is_selected():
                                    self.driver.execute_script("arguments[0].click();", checkbox)
                                    selected_seats += 1
                            except:
                                continue
                else:
                    try:
                        plus_btn = self.driver.find_element(By.CSS_SELECTOR, "a.plus")
                        for i in range(configured_count):
                            plus_btn.click()
                            time.sleep(0.01)
                    except:
                        pass

                try:
                    name_input = self.driver.find_element(By.CSS_SELECTOR, "input[name='name']")
                    name_input.clear()
                    name_input.send_keys(user_name)
                    
                    try:
                        deposit_input = self.driver.find_element(By.CSS_SELECTOR, "input[name='deposit_name']")
                        if user_depositor and user_depositor != user_name:
                            deposit_input.clear()
                            deposit_input.send_keys(user_depositor)
                    except: pass
                    
                    p1, p2, p3 = "", "", ""
                    if "-" in user_phone: 
                        parts = user_phone.split("-")
                        p1, p2, p3 = parts if len(parts)==3 else ("","","")
                    elif len(user_phone) == 11: 
                        p1, p2, p3 = user_phone[:3], user_phone[3:7], user_phone[7:]
                    
                    if p2:
                        self.driver.find_element(By.CSS_SELECTOR, "input[name='phone2']").send_keys(p2)
                        self.driver.find_element(By.CSS_SELECTOR, "input[name='phone3']").send_keys(p3)
                except:
                    pass

                try:
                    all_check = self.driver.find_element(By.CSS_SELECTOR, "input[name='all_check']")
                    if not all_check.is_selected():
                        self.driver.execute_script("arguments[0].click();", all_check)
                except:
                    pass

                time.sleep(0.005)
                
                self.log("🚀 예약하기 버튼 클릭...")
                try:
                    submit_btn = self.driver.find_element(By.CSS_SELECTOR, "#btn_payment, a.btn_payment")
                    self.driver.execute_script("arguments[0].click();", submit_btn)
                    
                    try:
                        alert = WebDriverWait(self.driver, 3).until(EC.alert_is_present())
                        self.log(f"🔔 Alert: {alert.text}")
                        if not self.simulation_mode:
                            alert.accept()
                        else:
                            return
                    except:
                        pass
                    
                    self.log("🔍 예약 결과 확인 중 (최대 10초)...")
                    check_start = time.time()
                    success_detected = False
                    
                    while time.time() - check_start < 10:
                        if self.success_event.is_set():
                            return
                        
                        if "reservation_detail" in self.driver.current_url:
                            self.log("🎉 예약 성공!")
                            self.success_event.set()
                            success_detected = True
                            break
                        
                        try:
                            page_text = self.driver.page_source
                            if any(kw in page_text for kw in ['예약현황', '예약접수 완료!', '총 상품금액', '예약금']):
                                self.log("🎉 예약 성공!")
                                self.success_event.set()
                                success_detected = True
                                break
                        except:
                            pass
                        
                        time.sleep(0.2)
                    
                    if success_detected:
                        self.log("✅ 예약이 정상적으로 완료되었습니다!")
                        self.log(f"⏱️ 총 소요 시간: {time.time() - process_start_time:.2f}초")
                        while True: time.sleep(1)
                        return
                    else:
                        browser_count = len(self.browsers) + 1
                        self.log(f"⏳ [브라우저{browser_count}] 10초 내 성공 확인 불가. 백그라운드 모니터링으로 전환...")
                        
                        old_driver = self.driver
                        self.browsers.append(old_driver)
                        
                        t = threading.Thread(target=self.monitor_browser_for_success, args=(old_driver, browser_count))
                        t.daemon = True
                        t.start()
                        
                        if len(self.browsers) >= self.max_browsers:
                            self.log(f"⚠️ 최대 브라우저 수({self.max_browsers}) 도달. 결과 대기 중...")
                            while not self.success_event.is_set():
                                time.sleep(0.5)
                            return
                        
                        self.log(f"🔄 새 브라우저 열고 재시도...")
                        self.setup_driver()
                        wait = WebDriverWait(self.driver, 30)
                        continue
                        
                except Exception as e:
                    self.log(f"⚠️ Submit error: {e}")
                    continue

            except Exception as e:
                self.log(f"⚠️ Process Error: {e}")
                continue

        self.log("✅ 예약 봇 실행 시퀀스가 모두 완료되었습니다.")
        while True: time.sleep(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    with open(args.config, 'r', encoding='utf-8') as f: config = json.load(f)
    bot = TeamF2Bot(config)
    try: bot.run()
    except KeyboardInterrupt: bot.stop()
