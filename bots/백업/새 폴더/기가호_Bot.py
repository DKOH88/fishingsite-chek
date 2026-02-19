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

class GigaBot(BaseFishingBot):
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
                if any(kw in page_text for kw in ['예약현황', '예약접수 완료!', '총 상품금액', '예약금']):
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

        target_date_str = self.config.get('target_date', '20251219')
        target_time = self.config.get('target_time', '09:00:00')
        test_mode = self.config.get('test_mode', False)
        self.simulation_mode = self.config.get('simulation_mode', False)
        
        user_name = self.config.get('user_name', '')
        user_depositor = self.config.get('user_depositor', '')
        user_phone = self.config.get('user_phone', '')
        person_count = int(self.config.get('person_count', 1))

        # 기가호 ID 계산 (2025-12-19 = 1535125 기준)
        base_date_str = "20251219"
        base_id = 1535125
        
        try:
            d_target = datetime.strptime(target_date_str, "%Y%m%d")
            d_base = datetime.strptime(base_date_str, "%Y%m%d")
            delta_days = (d_target - d_base).days
            target_id = base_id + delta_days
            url = f"https://giga.sunsang24.com/mypage/reservation_ready/{target_id}"
            self.log(f"🎯 Target URL: {url} (ID: {target_id}, Delta: {delta_days})")
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
                        if any(kw in page_text for kw in ['계좌번호', '환불계좌']):
                            self.log("✅ Page Ready! (예약 페이지 오픈 감지)")
                            step1_success = True
                            break
                    except:
                        pass
                    
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, "input[name='seat_col[]'], form[name='reservation_form'], #btn_payment, .btn_reserv")
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
                # 낚시 종류 선택
                self.log("🎣 낚시 종류 선택 중...")
                target_keywords = ['쭈갑', '쭈꾸미', '갑오징어', '문어', '우럭']
                for keyword in target_keywords:
                    try:
                        els = self.driver.find_elements(By.XPATH, f"//*[contains(text(), '{keyword}')]")
                        for el in els:
                            try:
                                radio = el.find_element(By.XPATH, "./preceding-sibling::input[@type='radio'] | ./following-sibling::input[@type='radio'] | ../input[@type='radio']")
                                radio.click()
                                self.log(f"✅ Selected Fishing Type: {keyword}")
                                break
                            except:
                                pass
                    except:
                        pass

                has_seat_selection = False
                try:
                    page_text = self.driver.find_element(By.TAG_NAME, "body").text
                    if "자리선택" in page_text or "전체선택" in page_text:
                        has_seat_selection = True
                except:
                    pass

                if has_seat_selection:
                    seats = self.driver.find_elements(By.XPATH, "//input[@name='seat_col[]' and not(@disabled)]")
                    if seats:
                        self.log(f"🔎 Found {len(seats)} available seats. Selecting {person_count}...")
                        count = 0
                        for seat in seats:
                            if count >= person_count: break
                            try:
                                label = self.driver.find_element(By.CSS_SELECTOR, f"label[for='{seat.get_attribute('id')}']")
                                label.click()
                            except:
                                seat.click()
                            count += 1
                    else:
                        try:
                            plus_btn = self.driver.find_elements(By.XPATH, "//img[contains(@src, 'btn_plus.gif')]")
                            if plus_btn:
                                for _ in range(person_count):
                                    plus_btn[0].click()
                                    time.sleep(0.1)
                        except:
                            pass
                else:
                    self.log(f"👥 인원 선택 중... ({person_count}명)")
                    try:
                        plus_btn = self.driver.find_elements(By.XPATH, "//img[contains(@src, 'btn_plus.gif')]")
                        if plus_btn:
                            for _ in range(person_count):
                                plus_btn[0].click()
                                time.sleep(0.1)
                    except:
                        pass

                self.log("✍️ 예약 정보 입력 중...")
                try:
                    self.driver.find_element(By.NAME, "name").clear()
                    self.driver.find_element(By.NAME, "name").send_keys(user_name)
                    time.sleep(0.1)
                    try:
                        self.driver.find_element(By.NAME, "deposit_name").clear()
                        self.driver.find_element(By.NAME, "deposit_name").send_keys(user_depositor or user_name)
                    except: pass
                    
                    p1, p2, p3 = "", "", ""
                    if "-" in user_phone:
                        parts = user_phone.split("-")
                        p1, p2, p3 = parts if len(parts)==3 else ("","","")
                    elif len(user_phone) == 11:
                        p1, p2, p3 = user_phone[:3], user_phone[3:7], user_phone[7:]
                    
                    if p2:
                        self.driver.find_element(By.NAME, "phone2").send_keys(p2)
                        time.sleep(0.1)
                        self.driver.find_element(By.NAME, "phone3").send_keys(p3)
                except: pass

                try:
                    chk = self.driver.find_element(By.NAME, "all_check")
                    if not chk.is_selected(): chk.click()
                except: pass

                time.sleep(0.005)
                
                self.log("🚀 예약하기 버튼 클릭...")
                try:
                    btn = self.driver.find_element(By.CSS_SELECTOR, "#btn_payment, .btn_reserv")
                    self.driver.execute_script("arguments[0].click();", btn)
                    
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
    bot = GigaBot(config)
    try: bot.run()
    except KeyboardInterrupt: bot.stop()