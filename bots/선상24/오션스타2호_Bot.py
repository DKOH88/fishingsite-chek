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

class OceanStar2Bot(BaseFishingBot):
    def __init__(self, config):
        super().__init__(config)
        self.success_event = threading.Event()
        self.browser_threads = []
        self.browsers = []
        self.max_browsers = 2

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
            except: pass
            time.sleep(0.1)
        self.log(f"🛑 [브라우저{browser_id}] 모니터링 중지")

    def run(self):
        self.setup_driver()
        wait = WebDriverWait(self.driver, 30)

        target_date_str = self.config.get('target_date', '20260802')
        target_time = self.config.get('target_time', '09:00:00')
        test_mode = self.config.get('test_mode', False)
        self.simulation_mode = self.config.get('simulation_mode', False)
        
        user_name = self.config.get('user_name', '')
        user_depositor = self.config.get('user_depositor', '')
        user_phone = self.config.get('user_phone', '')
        person_count = int(self.config.get('person_count', 1))

        try:
            d_target = datetime.strptime(target_date_str, "%Y%m%d")
            year_month = d_target.strftime("%Y%m")
            schedule_url = f"https://ysoceanstar.sunsang24.com/ship/schedule_fleet/{year_month}"
            date_class = f"d{d_target.strftime('%Y-%m-%d')}"
            table_id = date_class
            
            self.log(f"🎯 Schedule URL: {schedule_url}")
            self.log(f"🎯 Target Date Class: {date_class}")
        except Exception as e:
            self.log(f"❌ Date formatting error: {e}")
            return
        
        self.log(f"🌍 스케줄 페이지 사전 로드 중: {schedule_url}")
        self.log("##########🔎 오션스타2호 예약로직 시작!##########")
        schedule_preloaded = False
        try:
            self.driver.get(schedule_url)
            self.log("✅ 스케줄 페이지 로드 완료")
            
            try:
                date_link = self.driver.find_element(By.CSS_SELECTOR, f"a.{date_class}")
                date_classes = date_link.get_attribute("class") or ""
                
                if "no_schedule" in date_classes:
                    self.log(f"📌 스케줄 비활성화 상태 (no_schedule) - 오픈 시간까지 대기")
                else:
                    self.log(f"📅 스케줄 활성화 상태! 날짜 미리 클릭: {date_class}")
                    date_link.click()
                    # 사용자 요구사항: 날짜 클릭 후 1.5초(실전) 혹은 1.2초(테스트) 대기
                    wait_sec = 1.2 if test_mode else 1.5
                    time.sleep(wait_sec)
                    schedule_preloaded = True
            except Exception as e:
                self.log(f"⚠️ 날짜 링크 확인 실패: {e}")
        except Exception as e:
            self.log(f"⚠️ Pre-load failed: {e}")

        if not test_mode:
            self.log(f"⏰ 실행 예약 시간: {target_time}...")
            self.wait_until_target_time(target_time)
        else:
            self.log("🚀 TEST MODE ACTIVE: Skipping wait!")

        self.log(f"🔥 예약 시도 시작 (반복 루프)")
        max_retries = 5000
        reservation_opened = False

        for attempt in range(max_retries):
            if self.success_event.is_set():
                self.log("🎉 다른 브라우저에서 예약 성공 감지! 종료합니다.")
                return
                
            try:
                # 테스트모드 & 사전로드됨 & 첫 시도 -> 새로고침/날짜클릭 스킵하고 바로 버튼 찾기
                is_gap_attempt = (test_mode and schedule_preloaded and attempt == 0)
                
                if not is_gap_attempt:
                    self.driver.refresh()
                
                    try:
                        if not (schedule_preloaded and attempt == 0):
                            date_link = WebDriverWait(self.driver, 0.05).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, f"a.{date_class}"))
                            )
                            date_link.click()
                    except Exception as e:
                        self.log(f"⚠️ 날짜 링크 감지 실패, 새로고침... ({attempt+1})")
                        continue
                
                try:
                    try:
                        # 선박명 필터링 로직 추가
                        target_ship_name = "오션스타2호"
                        found_btn = None
                        
                        # 해당 날짜의 모든 선박 테이블 조회
                        ship_tables = self.driver.find_elements(By.CSS_SELECTOR, f"table#{table_id} td.ships_warp table.ship_unit")
                        
                        for table in ship_tables:
                            try:
                                title_div = table.find_element(By.CSS_SELECTOR, "div.title")
                                if target_ship_name == title_div.text.strip():
                                    found_btn = table.find_element(By.CSS_SELECTOR, "button.btn_ship_reservation")
                                    break
                            except: continue
                        
                        if found_btn:
                            reserve_btn = found_btn
                        else:
                            # 못 찾았을 경우 기존 방식(Fallback) - 다만 루키나호는 이름이 겹칠 수 있으므로 주의
                            reserve_btn = WebDriverWait(self.driver, 1.2).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, f"table#{table_id} button.btn_ship_reservation"))
                            )

                        btn_text = reserve_btn.text.strip()
                        
                        if not btn_text:
                            for _ in range(12):
                                time.sleep(0.1)
                                btn_text = reserve_btn.text.strip()
                                if btn_text:
                                    break
                    except:
                        try:
                            # 대기 버튼 확인 로직 (이름 필터링 포함)
                            waiter_found = False
                            ship_tables = self.driver.find_elements(By.CSS_SELECTOR, f"table#{table_id} td.ships_warp table.ship_unit")
                            for table in ship_tables:
                                try:
                                    title_div = table.find_element(By.CSS_SELECTOR, "div.title")
                                    if target_ship_name == title_div.text.strip():
                                        awaiter_btn = table.find_element(By.CSS_SELECTOR, "button.btn_ship_reservation_awaiter")
                                        if awaiter_btn and awaiter_btn.is_displayed():
                                            waiter_found = True
                                            break
                                except: continue
                            
                            if waiter_found:
                                self.log("❌ 이미 예약이 끝났습니다(대기하기 상태)")
                                while True: time.sleep(1)
                                return
                        except: pass
                        self.log(f"⏳ 버튼 대기 중... ({attempt+1})")
                        continue
                    
                    if "바로예약" in btn_text:
                        self.log(f"✅ 바로예약 버튼 발견! 텍스트: '{btn_text}'")
                        
                        main_window = self.driver.current_window_handle
                        reserve_btn.click()
                        self.log("🎉 바로예약 버튼 클릭 완료!")
                        
                        WebDriverWait(self.driver, 7).until(lambda d: len(d.window_handles) > 1)
                        for window in self.driver.window_handles:
                            if window != main_window:
                                self.driver.switch_to.window(window)
                                self.log(f"✅ 새 예약 창으로 전환 완료! URL: {self.driver.current_url}")
                                break
                        
                        try:
                            WebDriverWait(self.driver, 5).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, "a.plus"))
                            )
                            self.log("✅ Plus 버튼 감지! 페이지 로드 완료")
                        except:
                            self.log("⚠️ Plus 버튼 대기 시간 초과, 진행합니다...")
                        
                        reservation_opened = True
                        break
                    elif "대기" in btn_text:
                        self.log(f"⏳ 아직 대기 상태... ({attempt+1}/{max_retries})")
                    else:
                        self.log(f"⏳ 버튼 상태: '{btn_text}' ({attempt+1})")
                        
                except Exception as e:
                    self.log(f"⏳ 테이블/버튼 대기 중... ({attempt+1})")
                
            except Exception as e:
                self.log(f"⚠️ Refresh loop error: {e}")

        if not reservation_opened:
            self.log("❌ 최대 재시도 횟수 초과로 예약 페이지 진입에 실패했습니다.")
            while True: time.sleep(1)
            return

        while True:
            if self.success_event.is_set():
                self.log("🎉 예약 성공 감지! 종료합니다.")
                break
                
            process_start_time = time.time()
            
            try:
                # 4.1 낚시 종류 선택
                step_start = time.time()
                self.log("🎣 낚시 종류 선택 중...")
                target_keywords = ['쭈갑', '쭈꾸미', '갑오징어']
                found_fish = False
                
                try:
                    radios = self.driver.find_elements(By.CSS_SELECTOR, "input[type='radio'][name='default_schedule_no']")
                    self.log(f"🔎 Found {len(radios)} fish type options")
                    
                    if len(radios) == 1:
                        self.log(f"✨ 단일 어종만 있음, 자동 선택 (소요시간: {time.time()-step_start:.2f}초)")
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
                                        self.log(f"✅ Selected fish type: {keyword} (소요시간: {time.time()-step_start:.2f}초)")
                                        found_fish = True
                                        break
                                    except: pass
                        
                        if not found_fish and radios:
                            self.log("⚠️ 키워드 매칭 없음, 첫번째 어종 선택")
                            self.driver.execute_script("arguments[0].click();", radios[0])
                            self.log(f"✅ Default fish selected (First Option) (소요시간: {time.time()-step_start:.2f}초)")
                except Exception as e:
                    self.log(f"⚠️ Fishing type selection error: {e}")

                # 좌석 선택 기능 확인
                has_seat_selection = False
                try:
                    page_text = self.driver.find_element(By.TAG_NAME, "body").text
                    if "자리선택" in page_text or "전체선택" in page_text:
                        has_seat_selection = True
                        self.log("📌 좌석 선택 기능 있음")
                    else:
                        self.log("📌 좌석 선택 기능 없음 (인원만 선택)")
                except: pass

                # 4.2 인원 선택
                step_start = time.time()
                self.log(f"👥 인원 선택 중... ({person_count}명)")
                try:
                    plus_btns = self.driver.find_elements(By.CSS_SELECTOR, "a.plus")
                    if plus_btns:
                        for i in range(person_count):
                            plus_btns[0].click()
                            time.sleep(0.01)
                        self.log(f"✅ 인원 {person_count}명 설정 완료 (소요시간: {time.time()-step_start:.2f}초)")
                except Exception as e:
                    self.log(f"⚠️ Person count selection error: {e}")

                # 좌석 선택 로직 (우선순위: 10,11,1,20,9,12,2,19, 없으면 아무거나)
                if has_seat_selection:
                    step_start = time.time()
                    seat_priority = ['10', '11', '1', '20', '9', '12', '2', '19']
                    selected = 0
                    self.log(f"💺 좌석 선택 중... (우선순위: {', '.join(seat_priority)})")
                    
                    for seat in seat_priority:
                        if selected >= person_count: break
                        try:
                            checkbox = self.driver.find_element(By.CSS_SELECTOR, f"input[name='select_seat_nos[]'][value='{seat}']")
                            if checkbox.is_enabled() and not checkbox.is_selected():
                                label = self.driver.find_element(By.CSS_SELECTOR, f"label[for='select_seat_nos_num_{seat}']")
                                self.driver.execute_script("arguments[0].click();", label)
                                selected += 1
                                self.log(f"  → 좌석 {seat} 선택")
                        except: continue
                    
                    if selected < person_count:
                        self.log(f"⚠️ 우선순위 좌석 부족, 남은 좌석 선택 중...")
                        all_checkboxes = self.driver.find_elements(By.CSS_SELECTOR, "input[name='select_seat_nos[]']")
                        for checkbox in all_checkboxes:
                            if selected >= person_count: break
                            try:
                                if checkbox.is_enabled() and not checkbox.is_selected():
                                    seat_val = checkbox.get_attribute('value')
                                    label = self.driver.find_element(By.CSS_SELECTOR, f"label[for='select_seat_nos_num_{seat_val}']")
                                    self.driver.execute_script("arguments[0].click();", label)
                                    selected += 1
                                    self.log(f"  → 좌석 {seat_val} 선택 (대체)")
                            except: continue
                    
                    self.log(f"✅ 총 {selected}석 선택 완료 (소요시간: {time.time()-step_start:.2f}초)")

                # 4.3 예약 정보 입력
                step_start = time.time()
                self.log("✍️ 예약 정보 입력 중...")
                try:
                    name_input = self.driver.find_element(By.CSS_SELECTOR, "input[name='name']")
                    name_input.clear()
                    name_input.send_keys(user_name)
                    self.log(f"✅ 예약자명 입력: {user_name}")
                    
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
                        self.driver.find_element(By.CSS_SELECTOR, "input[name='phone2']").send_keys(p2)
                        self.driver.find_element(By.CSS_SELECTOR, "input[name='phone3']").send_keys(p3)
                        self.log(f"✅ 전화번호 입력: {p2}-{p3} (소요시간: {time.time()-step_start:.2f}초)")
                except Exception as e:
                    self.log(f"⚠️ Info input error: {e}")

                try:
                    step_start_check = time.time()
                    all_check = self.driver.find_element(By.CSS_SELECTOR, "input[name='all_check']")
                    if not all_check.is_selected():
                        self.driver.execute_script("arguments[0].click();", all_check)
                        self.log(f"✅ 전체 동의 체크 (소요시간: {time.time()-step_start_check:.2f}초)")
                except: pass

                time.sleep(0.05)
                
                self.log("🚀 예약하기 버튼 클릭...")
                step_start = time.time()
                try:
                    submit_btn = self.driver.find_element(By.CSS_SELECTOR, "#btn_payment, a.btn_payment")
                    self.driver.execute_script("arguments[0].click();", submit_btn)
                    
                    try:
                        alert = WebDriverWait(self.driver, 3).until(EC.alert_is_present())
                        self.log(f"🔔 Alert: {alert.text} (소요시간: {time.time()-step_start:.2f}초)")
                        if not self.simulation_mode:
                            alert.accept()
                        else:
                            self.log("🛑 시뮬레이션 모드: 알림창 확인 후 중단")
                            try:
                                elapsed_time = time.time() - process_start_time
                                self.log(f"⏱️ 총 소요 시간: {elapsed_time:.2f}초")
                            except: pass
                            self.log("✅ 예약 봇 실행 시퀀스가 모두 완료되었습니다.")
                            return
                    except: pass
                    
                    self.log("🔍 예약 결과 확인 중 (최대 10초)...")
                    check_start = time.time()
                    success_detected = False
                    
                    while time.time() - check_start < 10:
                        if self.success_event.is_set():
                            self.log("🎉 다른 브라우저에서 예약 성공 감지! 종료합니다.")
                            return
                        
                        if "reservation_detail" in self.driver.current_url:
                            self.log("🎉 예약 성공! (URL: reservation_detail 감지)")
                            self.success_event.set()
                            success_detected = True
                            break
                        
                        try:
                            page_text = self.driver.page_source
                            if any(kw in page_text for kw in ['예약현황', '예약접수 완료!', '총 상품금액', '예약금']):
                                self.log("🎉 예약 성공! (텍스트 확인)")
                                self.success_event.set()
                                success_detected = True
                                break
                        except: pass
                        
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
                        self.browser_threads.append(t)
                        
                        if len(self.browsers) >= self.max_browsers:
                            self.log(f"⚠️ 최대 브라우저 수({self.max_browsers}) 도달. 결과 대기 중...")
                            while not self.success_event.is_set():
                                time.sleep(0.5)
                            self.log("🎉 예약 성공 감지! 종료합니다.")
                            return
                        
                        self.log(f"🔄 새 브라우저 열고 재시도 ({len(self.browsers)+1}/{self.max_browsers})...")
                        self.setup_driver()
                        
                        self.driver.get(schedule_url)
                        try:
                            date_link = WebDriverWait(self.driver, 3).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, f"a.{date_class}"))
                            )
                            date_link.click()
                            
                            reserve_btn = WebDriverWait(self.driver, 3).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, f"table#{table_id} button.btn_ship_reservation"))
                            )
                            reserve_btn.click()
                            
                            WebDriverWait(self.driver, 7).until(lambda d: len(d.window_handles) > 1)
                            main_window = self.driver.current_window_handle
                            for window in self.driver.window_handles:
                                if window != main_window:
                                    self.driver.switch_to.window(window)
                                    break
                            time.sleep(0.5)
                        except Exception as e:
                            self.log(f"⚠️ 새 브라우저 예약 페이지 진입 실패: {e}")
                        
                        continue
                        
                except Exception as e:
                    self.log(f"⚠️ Submit error: {e}")
                    continue

            except Exception as e:
                self.log(f"⚠️ Process Error: {e}")
                continue

        if not self.success_event.is_set() and self.browsers:
            self.log("⏳ 모든 브라우저 결과 대기 중...")
            while not self.success_event.is_set():
                time.sleep(0.5)
            self.log("🎉 예약 성공 감지!")
        
        while True: time.sleep(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    with open(args.config, 'r', encoding='utf-8') as f: config = json.load(f)
    bot = OceanStar2Bot(config)
    try: bot.run()
    except KeyboardInterrupt: bot.stop()
