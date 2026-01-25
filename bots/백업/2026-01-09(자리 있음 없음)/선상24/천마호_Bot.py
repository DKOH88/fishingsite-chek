import sys
import json
import time
import argparse
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from base_bot import BaseFishingBot

class PrinceBot(BaseFishingBot):
    def run(self):
        self.setup_driver()
        wait = WebDriverWait(self.driver, 30)

        # 1. Parse Config
        target_date_str = self.config.get('target_date', '20260802')
        target_time = self.config.get('target_time', '09:00:00')
        test_mode = self.config.get('test_mode', False)
        self.simulation_mode = self.config.get('simulation_mode', False)
        
        user_name = self.config.get('user_name', '')
        user_depositor = self.config.get('user_depositor', '')
        user_phone = self.config.get('user_phone', '')
        configured_count = int(self.config.get('person_count', 1))

        # 2. Build Schedule Page URL based on target month
        try:
            d_target = datetime.strptime(target_date_str, "%Y%m%d")
            year_month = d_target.strftime("%Y%m")
            schedule_url = f"https://metafishingclub.sunsang24.com/ship/schedule_fleet/{year_month}"
            date_class = f"d{d_target.strftime('%Y-%m-%d')}"
            table_id = date_class
            
            self.log(f"🎯 Schedule URL: {schedule_url}")
            self.log(f"🎯 Target Date Class: {date_class}")
            self.log(f"🎯 Target Table ID: #{table_id}")
        except Exception as e:
            self.log(f"❌ Date formatting error: {e}")
            return
        
        # 2.5 Pre-load schedule page
        self.log(f"🌍 스케줄 페이지 사전 로드 중: {schedule_url}")
        try:
            self.driver.get(schedule_url)
            self.log("✅ 스케줄 페이지 로드 완료")
            
            self.log(f"📅 날짜 클릭 중: {date_class}")
            date_link = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, f"a.{date_class}"))
            )
            date_link.click()
            self.log(f"✅ {target_date_str} 날짜 클릭 완료")
            time.sleep(0.5)
        except Exception as e:
            self.log(f"⚠️ Pre-load failed: {e}")

        # 1.5 Scheduling
        if not test_mode:
            self.log(f"⏰ 실행 예약 시간: {target_time}...")
            self.wait_until_target_time(target_time)
        else:
            self.log("🚀 TEST MODE ACTIVE: Skipping wait!")

        # 3. Start Refresh Loop
        self.log(f"🔥 예약 시도 시작 (반복 루프)")
        max_retries = 1000
        reservation_opened = False

        for attempt in range(max_retries):
            try:
                self.driver.refresh()
                
                try:
                    date_link = WebDriverWait(self.driver, 7).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, f"a.{date_class}"))
                    )
                    date_link.click()
                except Exception as e:
                    self.log(f"⚠️ 날짜 링크 감지 실패, 새로고침... ({attempt+1})")
                    continue
                
                try:
                    date_table = WebDriverWait(self.driver, 7).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, f"table#{table_id}"))
                    )
                    
                    reserve_btn = date_table.find_element(By.CSS_SELECTOR, "button.btn_ship_reservation")
                    btn_text = reserve_btn.text.strip()
                    
                    if "바로예약" in btn_text:
                        self.log(f"✅ 바로예약 버튼 발견! 텍스트: '{btn_text}'")
                        
                        main_window = self.driver.current_window_handle
                        reserve_btn.click()
                        self.log("🎉 바로예약 버튼 클릭 완료!")
                        
                        WebDriverWait(self.driver, 7).until(lambda d: len(d.window_handles) > 1)
                        for window in self.driver.window_handles:
                            if window != main_window:
                                self.driver.switch_to.window(window)
                                self.log(f"✅ 새 예약 창으로 전환 완료!")
                                break
                        
                        try:
                            WebDriverWait(self.driver, 7).until(
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

        # ========== 4. 예약 정보 입력 단계 ==========
        process_start_time = time.time()
        
        try:
            # 4.1 낚시 종류 선택
            self.log("🎣 낚시 종류 선택 중...")
            target_keywords = ['쭈갑', '쭈꾸미', '갑오징어']
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

            # 4.2 가용 좌석 수 먼저 파악 (선상24: 체크박스 존재 여부로 판단)
            self.log("📊 가용 좌석 파악 중...")
            time.sleep(0.01)
            
            available_checkboxes = self.driver.find_elements(By.CSS_SELECTOR, "input[name='select_seat_nos[]']")
            available_count = len(available_checkboxes)
            self.log(f"📊 가용 좌석 수: {available_count}석, 설정 인원: {configured_count}명")
            
            # 자동 조정
            target_count = min(configured_count, available_count)
            if target_count < configured_count:
                self.log(f"⚠️ 가용 좌석 부족! 인원을 {configured_count}명 → {target_count}명으로 자동 조정합니다.")
            
            if target_count == 0:
                self.log("❌ 가용 좌석이 없습니다!")
                while True: time.sleep(1)
                return

            # 4.3 인원 선택 (Plus 버튼 빠른 클릭)
            self.log(f"👥 인원 선택 중... ({target_count}명)")
            try:
                plus_btn = self.driver.find_element(By.CSS_SELECTOR, "a.plus")
                for i in range(target_count):
                    plus_btn.click()
                    time.sleep(0.01)
                self.log(f"✅ 인원 {target_count}명 설정 완료")
            except Exception as e:
                self.log(f"⚠️ Person count selection error: {e}")

            # 4.4 좌석 선택 (우선순위: 11, 1, 7, 6, 10, 2, 8, 5, 9, 3, 4)
            self.log(f"💺 좌석 선택 중... ({target_count}석)")
            seat_priority = ['11', '1', '7', '6', '10', '2', '8', '5', '9', '3', '4']
            selected_seats = 0
            
            try:
                # 우선순위 좌석 선택
                for seat_num in seat_priority:
                    if selected_seats >= target_count:
                        break
                    
                    try:
                        checkbox_id = f"select_seat_nos_num_{seat_num}"
                        checkbox = self.driver.find_element(By.ID, checkbox_id)
                        
                        if checkbox.is_selected():
                            continue
                        
                        self.driver.execute_script("arguments[0].click();", checkbox)
                        selected_seats += 1
                        self.log(f"✅ 좌석 {seat_num}번 선택 ({selected_seats}/{target_count})")
                        time.sleep(0.01)
                        
                    except:
                        # 좌석이 존재하지 않음 (이미 예약됨)
                        continue
                
                # Fallback: 우선순위 외 좌석 선택
                if selected_seats < target_count:
                    self.log(f"⚠️ 우선순위 좌석 부족. 남은 좌석 중 선택 ({selected_seats}/{target_count})...")
                    for checkbox in available_checkboxes:
                        if selected_seats >= target_count:
                            break
                        try:
                            if not checkbox.is_selected():
                                seat_value = checkbox.get_attribute("value")
                                if seat_value not in seat_priority:
                                    self.driver.execute_script("arguments[0].click();", checkbox)
                                    selected_seats += 1
                                    self.log(f"🎲 가용 좌석 {seat_value}번 선택 ({selected_seats}/{target_count})")
                                    time.sleep(0.01)
                        except:
                            continue
                
                if selected_seats >= target_count:
                    self.log(f"✅ 좌석 선택 완료! 총 {selected_seats}석")
                else:
                    self.log(f"⚠️ 좌석 선택 부족: {selected_seats}/{target_count}석만 선택됨")
                    
            except Exception as e:
                self.log(f"⚠️ Seat selection error: {e}")

            # 4.5 예약자 정보 입력
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

            # 4.6 전체 동의 체크
            try:
                all_check = self.driver.find_element(By.CSS_SELECTOR, "input[name='all_check']")
                if not all_check.is_selected():
                    self.driver.execute_script("arguments[0].click();", all_check)
                    self.log("✅ 전체 동의 체크")
            except Exception as e:
                self.log(f"⚠️ All check error: {e}")

            # 4.7 예약하기 버튼 클릭
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

        # 소요 시간 표시
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
    bot = PrinceBot(config)
    try: bot.run()
    except KeyboardInterrupt: bot.stop()