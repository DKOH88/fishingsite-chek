import sys
import json
import time
import argparse
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from base_bot import BaseFishingBot

class YahoBot(BaseFishingBot):
    def run(self):
        self.setup_driver()
        wait = WebDriverWait(self.driver, 30)

        # 1. Parse Config
        target_date = self.config.get('target_date', '20261219') 
        target_time = self.config.get('target_time', '09:00:00')
        test_mode = self.config.get('test_mode', False)
        self.simulation_mode = self.config.get('simulation_mode', False)
        
        user_name = self.config.get('user_name', '')
        user_depositor = self.config.get('user_depositor', '')
        user_phone = self.config.get('user_phone', '')
        
        # 2. Build URL
        # http://xn--2f5b291a.com/_core/module/reservation_boat_v5.2_seat1/popu2.step1.php?date=20270901&PA_N_UID=3904
        base_url = "http://xn--2f5b291a.com/_core/module/reservation_boat_v5.2_seat1/popu2.step1.php"
        url = f"{base_url}?date={target_date}&PA_N_UID=3904"
        
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
        
        max_retries = 1000 
        retry_interval = 0.01 
        
        step1_success = False

        for attempt in range(max_retries):
            try:
                self.driver.get(url)
                page_source = self.driver.page_source
                
                # Check for Server Errors
                if "Bad Gateway" in self.driver.title or "502" in page_source:
                    self.log(f"⚠️ 서버 오류 (502). 새로고침 중... ({attempt+1}/{max_retries})")
                    time.sleep(0.5)
                    continue
                
                # Check for error texts - 0.5초 후 새로고침
                if any(err in page_source for err in ['없는', '권한', '잘못']):
                    self.log(f"⚠️ 에러 페이지 감지 (없는/권한/잘못). 0.5초 후 재시도... ({attempt+1}/{max_retries})")
                    time.sleep(0.5)
                    continue
                
                # Check for reservation page texts - 최대 3초 대기
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
                        continue
                else:
                    # 예약 페이지 텍스트도 없으면 빠르게 재시도
                    self.log(f"⏳ 페이지 준비 안됨. 재시도... ({attempt+1}/{max_retries})")
                    time.sleep(0.5)
                    continue
                
                process_start_time = time.time()  # 소요 시간 측정 시작
                self.log("🎣 낚시 종류 선택 항목 찾는 중...")
                self.log("⏱️ 휴먼 인식 방지 딜레이 (0.01초)...")
                time.sleep(0.01)

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
                target_keywords.extend(['갑오징어', '쭈꾸미', '쭈갑', '쭈꾸미&갑오징어'])
                
                found_click = False
                for keyword in target_keywords:
                    for span in all_spans:
                        text = span.text.strip()
                        if keyword in text:
                            self.log(f"✨ Match found! '{keyword}' in '{text}'")
                            time.sleep(0.01)

                            try:
                                span_id = span.get_attribute("id")
                                if span_id and span_id.startswith("PS1"):
                                    uid = span_id[3:] 
                                    input_id = f"PS_N_UID{uid}"
                                    try:
                                        target_input = self.driver.find_element(By.ID, input_id)
                                        self.driver.execute_script("arguments[0].click();", target_input)
                                        self.log(f"⚡ Clicked input by ID: {input_id}")
                                        found_click = True
                                        time.sleep(0.01)
                                    except: pass
                                
                                if not found_click:
                                    try:
                                        label = span.find_element(By.XPATH, "./parent::label")
                                        self.driver.execute_script("arguments[0].click();", label)
                                        self.log(f"⚡ Clicked parent label.")
                                        found_click = True
                                        time.sleep(0.01)
                                    except: pass

                                if not found_click:
                                    try:
                                        radio = span.find_element(By.XPATH, "./ancestor::td/preceding-sibling::td//input[@type='radio']")
                                        self.driver.execute_script("arguments[0].click();", radio)
                                        self.log(f"⚡ Clicked radio (Ancestor TD).")
                                        found_click = True
                                        time.sleep(0.01)
                                    except: pass

                                if not found_click:
                                    try:
                                        span.click()
                                        self.log(f"⚡ Clicked span directly.")
                                        found_click = True
                                        time.sleep(0.01)
                                    except: pass
                            except Exception as e:
                                self.log(f"⚠️ Click Logic Error: {e}")
                            
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
                    # 키워드 없으면 첫번째 항목 자동 선택
                    self.log("⚠️ 키워드 매칭 없음, 첫번째 어종 자동 선택 시도...")
                    try:
                        radios = self.driver.find_elements(By.CSS_SELECTOR, "input.PS_N_UID")
                        if radios:
                            self.driver.execute_script("arguments[0].click();", radios[0])
                            self.log("✅ 첫번째 어종 자동 선택 완료!")
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
                            self.log("⚠️ 선택 가능한 어종이 없습니다.")
                            break
                    except Exception as e:
                        self.log(f"⚠️ 첫번째 어종 선택 실패: {e}")
                        break

            except Exception as e:
                self.log(f"⚠️ 연결 오류 발생: {e}. 재시도 중...")
                time.sleep(retry_interval)
        
        if not step1_success:
             self.log("❌ 최대 재시도 횟수 초과로 예약 1단계 진입에 실패했습니다.")

        # Step 1.2: Check remaining seats from id_bi_in and adjust target count
        self.log("👥 남은 좌석 확인 및 인원 자동 조정 중...")
        configured_count = int(self.config.get('person_count', '1'))
        
        try:
            remaining_seats_el = self.driver.find_element(By.ID, "id_bi_in")
            remaining_seats = int(remaining_seats_el.text.strip())
            self.log(f"📊 남은 좌석 수: {remaining_seats}석, 설정 인원: {configured_count}명")
            
            if remaining_seats < configured_count:
                self.log(f"⚠️ 남은 좌석 부족! 인원을 {configured_count}명 → {remaining_seats}명으로 자동 조정합니다.")
                configured_count = remaining_seats
        except Exception as e:
            self.log(f"⚠️ 남은 좌석 수 확인 실패, 설정값 사용: {e}")

        # Step 1.25: Seat Selection (Yahoo-ho Specific)
        self.log("💺 좌석 선택 단계 시작...")
        seat_priority = ['1', '11', '2', '12', '10', '20', '3', '13', '9', '19', '4', '14', '8', '18']
        selected_seats = 0
        selected_seats_list = []  # 선택된 좌석 목록 추적
        
        try:
            # 좌석 클래스 자동 감지 (res_num_view 또는 num_view)
            seat_class = None
            try:
                self.driver.find_element(By.CLASS_NAME, "res_num_view")
                seat_class = "res_num_view"
                self.log("✅ 좌석 클래스 감지: res_num_view")
            except:
                try:
                    self.driver.find_element(By.CLASS_NAME, "num_view")
                    seat_class = "num_view"
                    self.log("✅ 좌석 클래스 감지: num_view")
                except:
                    self.log("⚠️ 좌석 선택 영역을 찾을 수 없습니다.")
                    raise Exception("No seat class found")
            
            time.sleep(0.01)
            
            available_seats = self.driver.find_elements(By.XPATH, f"//span[@class='{seat_class}']")
            available_count = len(available_seats)
            self.log(f"📊 가용 좌석 수: {available_count}석, 설정 인원: {configured_count}명")
            
            target_count = min(configured_count, available_count)
            if target_count < configured_count:
                self.log(f"⚠️ 가용 좌석 부족! 인원을 {configured_count}명 → {target_count}명으로 자동 조정합니다.")
            
            for seat_num in seat_priority:
                if selected_seats >= target_count:
                    break
                try:
                    seat_spans = self.driver.find_elements(By.XPATH, f"//span[@class='{seat_class}' and text()='{seat_num}']")
                    
                    for seat_span in seat_spans:
                        if seat_span.is_displayed():
                            self.log(f"✨ 우선순위 좌석 {seat_num}번 발견! 선택 시도 중... ({selected_seats+1}/{target_count})")
                            class_before = seat_span.get_attribute("class") or ""
                            self.driver.execute_script("arguments[0].click();", seat_span)
                            time.sleep(0.01)
                            class_after = seat_span.get_attribute("class") or ""
                            
                            if class_after != class_before:
                                selected_seats += 1
                                selected_seats_list.append(seat_num)
                                self.log(f"✅ 좌석 {seat_num}번 선택 성공! (현재: {selected_seats}/{target_count})")
                                time.sleep(0.01)
                            else:
                                self.log(f"⚠️ 좌석 {seat_num}번 선택 실패. 다음 순번으로...")
                            break
                except:
                    continue
            
            if selected_seats < target_count:
                self.log(f"⚠️ 우선순위 좌석 부족. 남은 좌석 중 무작위 선택 ({selected_seats}/{target_count})...")
                try:
                    all_seats = self.driver.find_elements(By.CLASS_NAME, seat_class)
                    for seat_span in all_seats:
                        if selected_seats >= target_count:
                            break
                        try:
                            seat_text = seat_span.text.strip()
                            if seat_span.is_displayed() and seat_text not in seat_priority:
                                self.log(f"🎲 무작위 좌석 {seat_text}번 선택 중... ({selected_seats+1}/{target_count})")
                                self.driver.execute_script("arguments[0].click();", seat_span)
                                selected_seats += 1
                                selected_seats_list.append(seat_text)
                                time.sleep(0.01)
                        except:
                            continue
                except Exception as ex:
                    self.log(f"⚠️ 무작위 좌석 선택 오류: {ex}")
            
            if selected_seats >= target_count:
                self.log(f"✅ 좌석 선택 완료! 총 {selected_seats}석 선택됨. (선택순서: {' → '.join(selected_seats_list)})")
                self.log(f"📋 좌석 우선순위: {seat_priority}")
            else:
                self.log(f"⚠️ 좌석 선택 부족: {selected_seats}/{target_count}석만 선택됨.")
                
        except Exception as e:
            self.log(f"⚠️ 좌석 선택 오류 (건너뜀): {e}")

        # Step 1.5: Person Count (use selected_seats, not config value)
        self.log("👥 인원 선택(BI_IN) 대기 중...")
        time.sleep(0.01)
        try:
            from selenium.webdriver.support.ui import Select
            select_el = wait.until(EC.element_to_be_clickable((By.ID, "BI_IN")))
            select_obj = Select(select_el)
            current_val = select_obj.first_selected_option.get_attribute("value")
            
            final_count = selected_seats if selected_seats > 0 else 1
            final_count_str = str(final_count)
            
            if current_val != final_count_str:
                self.log(f"👥 인원을 {final_count_str}명으로 설정합니다... (선택된 좌석: {selected_seats}석)")
                select_obj.select_by_value(final_count_str)
                time.sleep(0.01)
            else:
                self.log(f"👥 이미 {final_count_str}명으로 설정되어 있습니다.")
        except Exception as e:
            self.log(f"⚠️ Error selecting person count: {e}")

        # Step 2: Info Form
        self.log("🪑 예약 정보 입력 페이지(2단계) 진입 중...")
        try:
            name_input = wait.until(EC.element_to_be_clickable((By.NAME, "BI_NAME")))
            self.log(f"✍️ 성함 입력 중: {user_name}")
            name_input.clear()
            time.sleep(0.01)
            name_input.send_keys(user_name)
            time.sleep(0.01)
            
            try:
                bank_input = self.driver.find_element(By.ID, "BI_BANK")
                depositor = user_depositor if user_depositor else user_name
                self.log(f"✍️ 입금자명 입력 중: {depositor}")
                bank_input.clear()
                time.sleep(0.01)
                bank_input.send_keys(depositor)
                time.sleep(0.01)
            except: pass

            p1, p2, p3 = "", "", ""
            if "-" in user_phone:
                parts = user_phone.split("-")
                if len(parts) == 3: p1, p2, p3 = parts
            elif len(user_phone) == 11:
                p1, p2, p3 = user_phone[:3], user_phone[3:7], user_phone[7:]
            
            if p1 and p2 and p3:
                self.log(f"📞 연락처 입력 중: {p2}-{p3}")
                try:
                    t2 = self.driver.find_element(By.ID, "BI_TEL2")
                    t2.clear()
                    time.sleep(0.01)
                    t2.send_keys(p2)
                    time.sleep(0.01)
                    t3 = self.driver.find_element(By.ID, "BI_TEL3")
                    t3.clear()
                    time.sleep(0.01)
                    t3.send_keys(p3)
                    time.sleep(0.01)
                except: pass

            self.log("✅ '전체 동의' 체크박스 클릭 중...")
            try:
                agree_btn = self.driver.find_element(By.XPATH, "//input[@name='all_agree' and @value='Y']")
                self.driver.execute_script("arguments[0].click();", agree_btn)
                time.sleep(0.01)
            except: pass

            self.log("🚀 '예약 신청하기' 버튼 클릭 시도 (1단계)...")
            try:
                submit_btn = self.driver.find_element(By.ID, "submit")
                self.driver.execute_script("arguments[0].click();", submit_btn)
                
                self.log("🔔 예약 확인창 대기 중...")
                alert = wait.until(EC.alert_is_present())
                self.log(f"🔔 알림창 확인: {alert.text}")
                
                if not self.simulation_mode:
                    alert.accept()
                    self.log("✅ 첫 번째 확인창 통과!")
                    
                    self.log("🚀 최종 '예약 신청하기' 클릭 (2단계)...")
                    time.sleep(0.01)
                    try:
                        submit_btn2 = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.ID, "submit"))
                        )
                        self.driver.execute_script("arguments[0].click();", submit_btn2)
                        try:
                            alert2 = WebDriverWait(self.driver, 3).until(EC.alert_is_present())
                            self.log(f"🔔 두 번째 알림창: {alert2.text}")
                            alert2.accept()
                            self.log("✅ 예약이 최종 완료되었습니다! (확인창 accept)")
                        except:
                            self.log("✅ 예약 신청이 성공적으로 제출되었습니다!")
                    except Exception as e2:
                        self.log(f"⚠️ Second submit not found: {e2}")
                else:
                    self.log("🛑 시뮬레이션 모드: 알림창 확인 후 작업을 중단합니다.")
            except Exception as e:
                self.log(f"⚠️ Submit error: {e}")

        except Exception as e:
            self.log(f"ℹ️ Input Autofill skipped/failed: {e}")

        # Calculate and display elapsed time
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
    bot = YahoBot(config)
    try: bot.run()
    except KeyboardInterrupt: bot.stop()