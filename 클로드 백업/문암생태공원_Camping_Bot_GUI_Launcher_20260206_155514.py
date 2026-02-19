import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, Toplevel
import json
import threading
import os
import time
import traceback
import requests
import email.utils
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from PIL import Image, ImageTk
from webdriver_manager.chrome import ChromeDriverManager

# ==============================================================================
# 봇 로직 클래스
# ==============================================================================
class CampingBot:
    def __init__(self, log_callback, config, immediate_mode=False):
        self.log = log_callback
        self.config = config
        self.driver = None
        self.is_running = False
        self.immediate_mode = immediate_mode
        self.skip_next_month = config.get("SKIP_NEXT_MONTH", False)

    # [New] RTT 기반 정밀 시간 동기화 (camping_bot_v9 방식)
    def sync_server_time(self, url):
        try:
            offsets = []
            self.log("⏱️ 서버 시간 동기화 중... (5회 측정 / RTT 보정)")
            for _ in range(5):
                start = datetime.now()
                resp = requests.head(url, timeout=3)
                end = datetime.now()
                
                # Date 헤더 파싱 (GMT -> KST)
                date_str = resp.headers.get('Date')
                if not date_str: continue
                
                server_time_gmt = email.utils.parsedate_to_datetime(date_str)
                # timezone 정보가 있을 수 있으므로 제거 후 계산
                server_time_gmt = server_time_gmt.replace(tzinfo=None)
                server_time_kst = server_time_gmt + timedelta(hours=9)
                
                # RTT 보정: (요청+응답)/2 만큼 서버 시간이 더 흘렀다고 가정
                rtt = (end - start).total_seconds()
                estimated_server_time = server_time_kst + timedelta(seconds=rtt / 2)
                
                # 오차 = 추정 서버시간 - 현재 로컬시간
                # (추정 서버시간) = (현재 로컬시간) + offset
                # offset = (추정 서버시간) - (현재 로컬시간)
                offset = estimated_server_time - end
                offsets.append(offset.total_seconds())
                time.sleep(0.05)
                
            if offsets:
                avg_offset = sum(offsets) / len(offsets)
                self.server_offset = timedelta(seconds=avg_offset) # 클래스 멤버로 저장
                self.log(f"✅ 시간 동기화 완료: 로컬보다 {avg_offset:+.3f}초 (RTT 반영)")
                return True
        except Exception as e:
            self.log(f"⚠️ 시간 동기화 실패: {e}")
        
        self.server_offset = timedelta(seconds=0) # 실패 시 0
        return False
        
    def get_current_server_time(self):
        return datetime.now() + self.server_offset

    def create_driver(self):
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_experimental_option("detach", True)
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        
        # [New] 강력한 리소스 차단 (크롬 설정 레벨)
        # 2 = Block images, CSS, etc.
        prefs = {
            "profile.managed_default_content_settings.images": 2, # 이미지 차단 (강력)
            "profile.default_content_setting_values.notifications": 2, # 알림 차단
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        # [New] webdriver_manager를 사용한 자동 드라이버 설치/매칭
        try:
            self.log("🔧 ChromeDriver 버전 불일치 해결을 위해 자동 업데이트를 시도합니다...")
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
        except Exception as e:
            self.log(f"⚠️ 자동 업데이트 실패 ({e}), 설정된 경로 사용 시도")
            if self.config.get("CHROMEDRIVER_PATH"):
                service = Service(self.config["CHROMEDRIVER_PATH"])
                driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                driver = webdriver.Chrome(options=chrome_options)

        # CDP는 폰트 등 추가적인 것만 차단
        try:
            blocked_urls = ["*.woff", "*.woff2", "*.ttf"] 
            driver.execute_cdp_cmd("Network.setBlockedURLs", {"urls": blocked_urls})
            driver.execute_cdp_cmd("Network.enable", {})
            self.log("🚀 속도 최적화: 이미지(Prefs)/폰트(CDP) 차단 적용")
        except: pass
            
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        })
        return driver

    def run(self):
        self.is_running = True
        try:
            mode_text = "🔥 바로 시작 모드" if self.immediate_mode else "🕒 예약 대기 모드"
            self.log(f"🤖 봇 가동 시작 ({mode_text})")
            
            self.driver = self.create_driver()
            self.driver.get(self.config['TARGET_URL'])

            if not self.perform_login(): return

            if self.immediate_mode:
                self.log("⚡ [바로 시작] 대기 시간을 건너뛰고 즉시 진행합니다.")
            else:
                self.wait_until_opening_time()

            if not self.is_running: return # [Fix] 대기 후 실행 여부 재확인

            # [New] 날짜 선택 비상 재시도 로직 (최대 3회)
            date_selected = False
            for attempt in range(3):
                if not self.is_running: break

                # 1. 다음 달 이동 (필요 시)
                if not self.skip_next_month:
                    self.move_to_next_month()
                else:
                    self.log("⏭️ 사용자 설정에 의해 '다음 달 이동'을 건너뜁니다.")
                
                if not self.is_running: break

                # 2. 날짜 선택 시도
                if self.select_date(self.config["TARGET_DAY"]):
                    date_selected = True
                    break # 성공하면 반복 탈출
                else:
                    # 실패 시 새로고침 후 다시 시도
                    if attempt < 2: # 마지막 시도가 아니면
                        self.log(f"⚠️ 날짜 버튼 미발견! ({attempt+1}/3) -> 비상 새로고침 🔄")
                        self.driver.refresh()
                        self.log(f"⚠️ 날짜 버튼 미발견! ({attempt+1}/3) -> 비상 새로고침 🔄")
                        self.driver.refresh()
                        # [Fix] 사용자 설정 대기 시간 적용 (새로고침 직후)
                        wait_sec = float(self.config.get("WAIT_TIME", 0.0))
                        if wait_sec > 0:
                            self.log(f"⏳ 안정화를 위해 {wait_sec}초 대기...")
                            time.sleep(wait_sec)
                        else:
                            time.sleep(0.2) # 기본값
            
            if not date_selected:
                self.log("❌ 3회 재시도 실패. 예약 불가.")
                return

            if not self.select_stay_duration(self.config["STAY_DURATION"]): return
            if not self.select_stay_duration(self.config["STAY_DURATION"]): return
            if not self.select_specific_site(self.config["TARGET_SITE_NAME"]): return

            self.select_discount(self.config["DISCOUNT_NAME"])

            if self.click_next_step():
                self.check_all_agreements()
                self.input_car_number() # [New] 차량번호 입력
                self.click_final_reservation()
            else:
                self.log("❌ 다음 단계 버튼 실패.")

            self.log("\n✨ 모든 자동화 과정이 끝났습니다. 결제를 진행하세요.")

        except Exception as e:
            self.log(f"🛑 오류 발생: {e}")
            self.log(traceback.format_exc())
        finally:
            self.is_running = False

    def perform_login(self):
        try:
            self.log("🔑 로그인 시도...")
            try:
                btn = self.driver.find_elements(By.XPATH, "//a[contains(text(), '로그인') and not(contains(@href, 'javascript'))]")
                if btn: btn[0].click()
            except: pass

            WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.ID, "usrId"))).send_keys(self.config['LOGIN_ID'])
            self.driver.find_element(By.ID, "usrPwd").send_keys(self.config['LOGIN_PW'])
            self.driver.execute_script("member_login();")
            
            try:
                WebDriverWait(self.driver, 5).until(lambda d: "로그아웃" in d.page_source)
                self.log("✅ 로그인 성공")
                return True
            except:
                self.log("⚠️ 로그인 확인 불가 (진행)")
                return True
        except Exception as e:
            self.log(f"❌ 로그인 실패: {e}")
            return False

    # [Fix] 구버전 호출 호환성을 위한 alias
    def login(self):
        return self.perform_login()

    def wait_until_opening_time(self):
        if not hasattr(self, 'server_offset'):
            self.sync_server_time(self.config["TARGET_URL"])

        # 타겟 시간 설정
        current_server_time = self.get_current_server_time()
        target_time = current_server_time.replace(
            hour=int(self.config["OPEN_HOUR"]), 
            minute=int(self.config["OPEN_MINUTE"]), 
            second=int(self.config["OPEN_SECOND"]), 
            microsecond=0
        )
        cutoff_time = target_time + timedelta(minutes=int(self.config["ACTIVE_MINUTES"]))
        should_refresh = True

        if current_server_time > cutoff_time:
            # [Fix] 테스트 모드일 때는 날짜 안 넘기고 사용자가 설정한 시간 그대로 대기 (오늘 테스트 가능)
            if self.config.get("TEST_MODE", False):
                self.log(f"🧪 [테스트 모드] 이미 지난 시간이지만 넘어가지 않고({target_time.strftime('%H:%M:%S')}) 진행합니다.")
            else:
                target_time = target_time + timedelta(days=1)
                self.log(f"⏰ 오늘 예약 가능 시간이 지났습니다.")
                self.log(f"💤 내일({target_time.strftime('%Y-%m-%d')}) 10시까지 대기합니다...")
            
        elif target_time <= current_server_time <= cutoff_time:
            self.log(f"⚡ 현재 골든 타임입니다! 대기 없이 즉시 시작합니다.")
            return 

        else:
            self.log(f"⏳ 오픈 전입니다. {target_time.strftime('%H:%M:%S')}까지 대기합니다.")

        # 상태 플래그
        resync_30s_done = False
        resync_10s_done = False

        while self.is_running:
            current_server_time = self.get_current_server_time()
            diff = (target_time - current_server_time).total_seconds()
            
            if diff <= 0:
                self.log("⏰ 드디어 오픈 시간입니다! 돌격!")
                break
            
            # 🚀 30초 전 재동기화
            if not resync_30s_done and 30 <= diff < 35:
                self.log("🔄 목표 30초 전: 서버 시간 정밀 재동기화...")
                self.sync_server_time(self.config["TARGET_URL"])
                resync_30s_done = True
            
            # 🚀 10초 전 최종 재동기화
            if not resync_10s_done and 10 <= diff < 15:
                self.log("🔄 목표 10초 전: 최종 서버 시간 재측정...")
                self.sync_server_time(self.config["TARGET_URL"])
                resync_10s_done = True

            if diff <= 10:
                if int(diff * 10) % 10 == 0:
                    self.log(f"🚀 카운트다운: {diff:.1f}초전!!!")
                time.sleep(0.1)
            else:
                if int(diff) % 10 == 0:
                     hours, remainder = divmod(int(diff), 3600)
                     minutes, seconds = divmod(remainder, 60)
                     self.log(f"⏳ 남은 시간: {hours:02d}:{minutes:02d}:{seconds:02d}")
                time.sleep(1)
        
        if should_refresh and self.is_running:
            self.driver.refresh()
            self.log("🔄 페이지 새로고침! 예약을 시작합니다.")
            try:
                WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.CLASS_NAME, "nextmonth")))
            except:
                time.sleep(0.5)

    def move_to_next_month(self):
        while self.is_running:
            try:
                self.log("📅 다음 달 버튼 클릭 시도...")
                btn = WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.CLASS_NAME, "nextmonth")))
                btn.click()
                
                # 텍스트 확인 (웹 페이지 내 문구)
                time.sleep(0.1) # 페이지/내용 갱신 대기 (최소화)
                if "예매 가능한 일자가 없습니다" in self.driver.page_source:
                    self.log(f"🚫 '예매 가능한 일자가 없습니다' 문구 감지 -> 새로고침 후 재시도 🔄")
                    self.driver.refresh()
                    continue # 루프 계속

                break # 성공 시 루프 탈출
                
            except Exception as e:
                self.log(f"⚠️ 다음 달 버튼 처리 중 오류 (패스): {e}")
                break

    def select_date(self, day):
        if not self.is_running: return False # [Fix] 중지 요청 시 즉시 중단
        try:
            day_num = str(int(day))
            self.log(f"📅 {day_num}일 선택 시도...")
            
            # [수정] 사용자가 선택한 예약 유형(캠핑장/캠핑하우스)에 따라 클릭 대상 변경
            target_type = self.config.get("TARGET_TYPE", "캠핑장") # 기본값 캠핑장
            
            # 텍스트로 찾기 (가장 확실함)
            # 예: "캠핑장", "캠핑하우스" 텍스트를 포함하는 a 태그
            xpath = f"//td[@id='calendar_{day_num}']//a[contains(., '{target_type}')]"
            
            # [Fix] 재시도를 위해 대기 시간 단축 (5초 -> 1.5초)
            # 1.5초 안에 안 보이면 "아직 안 열렸다"고 판단하고 빨리 새로고침하는 게 유리함
            element = WebDriverWait(self.driver, 1.5).until(EC.element_to_be_clickable((By.XPATH, xpath)))
            self.driver.execute_script("arguments[0].click();", element)
            # time.sleep(0.5) -> 0.1로 단축 (클릭 후 반응 대기 최소화)
            time.sleep(0.1)
            self.log(f"✅ {day_num}일 ({target_type}) 클릭 성공")
            return True
        except Exception as e:
            self.log(f"❌ 날짜 선택 실패: {e}")
            return False

    def select_stay_duration(self, nights):
        try:
            self.log(f"🛏️ {nights}박 선택 시도...")
            self.driver.find_element(By.ID, "lodge_day_div").click()
            time.sleep(0.1) # 0.3 -> 0.1
            xpath = f"//ul[@id='lodgeDayList']/li[@data-value='{nights}']"
            element = WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.XPATH, xpath)))
            element.click()
            time.sleep(0.1) # 1.0 -> 0.1 (가장 큰 딜레이 원인 제거)
            return True
        except Exception as e:
            self.log(f"❌ 숙박일수 선택 실패: {e}")
            return False

    def select_specific_site(self, target_site):
        try:
            candidates = [target_site]
            
            # [Fallback Logic] 캠핑하우스(14~16)인 경우, 실패 시 다른 호실 자동 시도
            if "캠핑하우스" in target_site:
                house_nums = [14, 15, 16]
                try:
                    target_num = int(target_site.replace("캠핑하우스", "").strip())
                    # 타겟을 맨 앞으로, 나머지를 뒤로
                    others = [n for n in house_nums if n != target_num]
                    candidates = [target_site] + [f"캠핑하우스{n}" for n in others]
                    self.log(f"📋 예약 후보군: {candidates}")
                except: pass

            for site in candidates:
                try:
                    self.log(f"⛺ 구역 '{site}' 시도 중...")
                    xpath = f"//a[contains(text(), '{site}') or contains(@title, '{site}')]"
                    element = WebDriverWait(self.driver, 2).until(EC.presence_of_element_located((By.XPATH, xpath)))
                    
                    # 1. 클래스 확인 (dis 클래스가 있으면 이미 예약됨)
                    if "dis" in element.get_attribute("class"):
                        self.log(f"⚠️ '{site}'는 이미 마감되었습니다. (화면 표시)")
                        continue
                        
                    # 2. 클릭 시도
                    self.driver.execute_script("arguments[0].click();", element)
                    
                    # 3. 팝업 확인 (클릭 후 "이미 예약된..." 뜨는지 체크)
                    try:
                        WebDriverWait(self.driver, 0.3).until(EC.alert_is_present())
                        alert = self.driver.switch_to.alert
                        msg = alert.text
                        if "이미 예약" in msg or "불가능" in msg:
                            self.log(f"🚫 '{site}' 예약 실패 팝업: {msg}")
                            alert.accept()
                            continue # 다음 후보로
                        else:
                            self.log(f"⚡ 팝업 감지 (성공 가능성): {msg}")
                            alert.accept()
                            return True # 성공으로 간주
                    except:
                        # 팝업이 안 떴으면 성공
                        self.log(f"✅ '{site}' 클릭 성공 (팝업 없음)")
                        return True
                        
                except Exception as e:
                    self.log(f"❌ '{site}' 처리 중 오류: {e}")
                    continue
            
            self.log("❌ 모든 후보군 예약 실패 ㅠㅠ")
            return False
        except Exception as e:
            self.log(f"❌ 구역 선택 로직 에러: {e}")
            return False

    def select_discount(self, discount_name):
        try:
            self.log(f"💰 할인 '{discount_name}' 클릭...")
            xpath = f"//a[contains(., '{discount_name}')]"
            element = WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.XPATH, xpath)))
            self.driver.execute_script("arguments[0].click();", element)
            
            try:
                WebDriverWait(self.driver, 0.1).until(EC.alert_is_present())
                self.driver.switch_to.alert.accept()
            except: pass
            
            try:
                WebDriverWait(self.driver, 3).until(
                    lambda d: d.find_element(By.ID, "dc_value").get_attribute("value") != ""
                )
                val = self.driver.find_element(By.ID, "dc_value").get_attribute("value")
                self.log(f"⚡ 할인 데이터 확인됨 (dc_value='{val}')")
            except:
                self.log("⚠️ dc_value 감지 실패 (진행)")
            return True
        except:
            self.log("⚠️ 할인 버튼을 찾지 못함 (패스)")
            return False

    def click_next_step(self):
        try:
            self.log("🚀 [페이지 이동] 다음 단계 클릭!")
            btn = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, "btn_div_area_next")))
            if "on" in btn.get_attribute("class"):
                self.driver.execute_script("arguments[0].click();", btn)
                return True
            else:
                self.log("⚠️ 버튼 비활성화.")
                return False
        except Exception as e:
            self.log(f"❌ 다음 단계 클릭 실패: {e}")
            return False

    def check_all_agreements(self):
        try:
            self.log("✅ 약관 동의 체크 중...")
            try:
                WebDriverWait(self.driver, 5).until(EC.presence_of_element_located((By.ID, "agree1")))
            except: pass
            
            self.driver.execute_script("window.scrollBy(0, 300);")
            
            target_ids = ["agree1", "agree2", "agree4", "agree5"]
            for ag_id in target_ids:
                try:
                    checkbox = self.driver.find_element(By.ID, ag_id)
                    if not checkbox.is_selected():
                        self.driver.execute_script("arguments[0].click();", checkbox)
                        self.log(f"☑️ {ag_id}")
                except: pass
            return True
        except Exception as e:
            self.log(f"❌ 동의 체크 오류: {e}")
            return True

    def input_car_number(self):
        try:
            self.log("🚗 차량번호 입력 중...")
            car_no = "51루8546" # 사용자 지정 번호
            try:
                element = WebDriverWait(self.driver, 3).until(EC.presence_of_element_located((By.ID, "rs_car_no")))
                element.clear()
                element.click()
                element.send_keys(car_no)
                
                # [Fix] 입력값 유지를 위해 포커스 아웃 (빈 곳 클릭 및 blur 이벤트)
                try:
                    self.driver.execute_script("arguments[0].blur();", element)
                    self.driver.find_element(By.TAG_NAME, "body").click()
                except: pass
                
                self.log(f"✅ 차량번호 입력 완료: {car_no}")
                return True
            except:
                self.log("⚠️ 차량번호 입력 필드 없음 (패스)")
                return True
        except Exception as e:
            self.log(f"❌ 차량번호 입력 실패: {e}")
            return False

    def click_final_reservation(self):
        try:
            self.log("🏁 [최종] 예약하기 버튼 클릭 시도...")
            btn = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.ID, "paybtn_layer_next")))
            if "on" in btn.get_attribute("class"):
                self.driver.execute_script("arguments[0].click();", btn)
                self.log("🖱️ 버튼 클릭 완료!")
                try:
                    WebDriverWait(self.driver, 5).until(EC.alert_is_present())
                    alert = self.driver.switch_to.alert
                    self.log(f"🔔 최종 팝업 감지: {alert.text}")
                    
                    # [Fix] 테스트 모드 OR 바로 시작 모드일 때는 최종 팝업 승인 건너뜀 (안전장치)
                    if self.config.get("TEST_MODE", False) or self.config.get("IMMEDIATE_MODE", False):
                        self.log("🛑 [테스트/바로시작] 최종 팝업 승인을 건너뜁니다.")
                        # alert.dismiss() # 취소를 누르려면 주석 해제, 보통은 그냥 둠
                    else:
                        alert.accept()
                        self.log("🎉🎉🎉 최종 팝업 승인 완료! 결제창 대기... 🎉🎉🎉")
                except:
                    self.log("⚠️ 팝업 없음 (통과)")
                return True
            else:
                self.driver.execute_script("arguments[0].click();", btn)
                return True
        except Exception as e:
            self.log(f"❌ 예약하기 처리 실패: {e}")
            return False
    
    # [New] 페이지 로드 속도 측정 기능
    def measure_speed(self):
        self.is_running = True
        try:
            self.log("🚀 페이지 로드 속도 측정을 시작합니다... (Ver.FIX) (5회 반복)")
            
            # 1. 드라이버 생성 및 접속
            self.driver = self.create_driver()
            self.driver.get(self.config['TARGET_URL'])

            # 2. 로그인 및 페이지 진입
            if not self.perform_login(): return

            times = []
            target_day = self.config["TARGET_DAY"]
            
            # 테스트를 위해 다음 달로 이동해둠 (만약 필요하다면)
            if not self.is_running: return
            if not self.config.get("SKIP_NEXT_MONTH", False):
                 self.move_to_next_month()

            for i in range(5):
                if not self.is_running: break
                self.log(f"🔄 측정 시도 {i+1}/5...")
                
                start_time = time.time()
                self.driver.refresh()
                
                try:
                    # 날짜 엘리먼트가 뜰 때까지 대기
                    # (여기선 일부러 넉넉히 10초 줌, 측정 목적이므로)
                    day_num = int(target_day)
                    # "캠핑장" or "캠핑하우스" (예약 구분값)
                    target_type = "캠핑하우스" if self.config["TARGET_TYPE"] == "house" else "캠핑장"
                    xpath = f"//td[@id='calendar_{day_num}']//a[contains(., '{target_type}')]"
                    
                    WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.XPATH, xpath)))
                    
                    elapsed = time.time() - start_time
                    times.append(elapsed)
                    self.log(f"⏱️ 소요 시간: {elapsed:.4f}초")
                    time.sleep(1) # 과부하 방지 쿨타임
                    
                except Exception as e:
                    self.log(f"❌ 측정 실패: {e}")
            
            if times:
                avg_time = sum(times) / len(times)
                min_time = min(times)
                max_time = max(times)
                
                self.log("-" * 30)
                self.log(f"📊 측정 결과 (5회 평균)")
                self.log(f"⚡ 최소: {min_time:.4f}초")
                self.log(f"🐢 최대: {max_time:.4f}초")
                self.log(f"⚖️ 평균: {avg_time:.4f}초")
                self.log("-" * 30)
                
                recommend_wait = avg_time + 0.5 # 평균보다 0.5초 여유 있게
                self.log(f"💡 추천 대기 설정값: 약 {recommend_wait:.1f}초")
                
                # [New] 추천값을 자동으로 설정에 적용
                self.config["WAIT_TIME"] = round(recommend_wait, 1)
                self.root.after(0, lambda: self.entry_wait.delete(0, tk.END))
                self.root.after(0, lambda: self.entry_wait.insert(0, str(self.config["WAIT_TIME"])))
                self.log(f"✅ 설정창의 '대기(초)' 값이 {self.config['WAIT_TIME']}초로 자동 적용되었습니다.")
                
        except Exception as e:
            self.log(f"🛑 측정 중 오류 발생: {e}")
        finally:
            self.is_running = False
            self.log("🏁 측정 종료 (브라우저는 유지됩니다)")

    



# ==============================================================================
# GUI 클래스
# ==============================================================================
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("문암생태공원 캠핑장 예약봇 v4.9")
        
        window_width = 600
        window_height = 700
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        center_x = int((screen_width / 2) - (window_width / 2))
        center_y = int((screen_height / 2) - (window_height / 2))
        self.root.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")
        
        self.config_file = "config.json"

        self.load_config()
        self.bot = None # [New] 봇 인스턴스 저장용
        self.create_widgets()

        # [New] 단축키 바인딩
        self.root.bind('<F2>', lambda e: self.start_bot())
        self.root.bind('<F3>', lambda e: self.stop_bot())

        # [New] 종료 시 자동 저장
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        try:
            self.save_all_config() # 종료 전 모든 설정(예약 목표 포함) 저장
            print("💾 종료 시 자동 저장 완료")
        except: pass
        self.root.destroy()

    def load_config(self):
        default_config = {
            "TARGET_URL": "https://forest.maketicket.co.kr/ticket/GD30",
            "LOGIN_ID": "odk297",
            "LOGIN_PW": "Ehdrbsl5",
            "TARGET_DAY": "15",
            "TARGET_TYPE": "캠핑장", # [New] 기본값
            "TARGET_SITE_NAME": "캠핑장20",
            "STAY_DURATION": "1",
            "DISCOUNT_NAME": "지역주민대상자 할인",
            "OPEN_HOUR": "10",
            "OPEN_MINUTE": "00",
            "OPEN_SECOND": "00",
            "ACTIVE_MINUTES": "10",
            "CHROMEDRIVER_PATH": r"C:\chromedriver-win64\chromedriver.exe",
            "SKIP_NEXT_MONTH": False,
            "TEST_MODE": False,
            "IMMEDIATE_MODE": False,
            "WAIT_TIME": 0.0 # [New] 대기 시간 (초)
        }
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding='utf-8') as f:
                    self.config = json.load(f)
            except:
                self.config = default_config
        else:
            self.config = default_config

    def _save_to_file(self):
        with open(self.config_file, "w", encoding='utf-8') as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)

    def save_login(self):
        self.config["LOGIN_ID"] = self.entry_id.get()
        self.config["LOGIN_PW"] = self.entry_pw.get()
        self._save_to_file()
        messagebox.showinfo("저장 완료", "로그인 정보가 저장되었습니다.")

    def save_target(self):
        self.config["TARGET_DAY"] = self.combo_day.get()
        self.config["TARGET_TYPE"] = self.combo_type.get() # [New]
        self.config["TARGET_SITE_NAME"] = self.combo_site.get()
        self.config["STAY_DURATION"] = self.combo_stay.get()
        self._save_to_file()
        messagebox.showinfo("저장 완료", "예약 목표가 저장되었습니다.")

    # 💾 [추가됨] 시간 설정 저장 함수
    def save_time(self):
        self.config["OPEN_HOUR"] = self.entry_hour.get()
        self.config["OPEN_MINUTE"] = self.entry_min.get()
        self.config["OPEN_MINUTE"] = self.entry_min.get()
        self.config["OPEN_SECOND"] = self.entry_sec.get()
        # [New] 대기 시간 저장
        try:
            self.config["WAIT_TIME"] = float(self.entry_wait.get())
        except:
            self.config["WAIT_TIME"] = 0.0
        self._save_to_file()
        messagebox.showinfo("저장 완료", "오픈 시간이 저장되었습니다.")

    def save_all_config(self):
        self.config["LOGIN_ID"] = self.entry_id.get()
        self.config["LOGIN_PW"] = self.entry_pw.get()
        self.config["TARGET_DAY"] = self.combo_day.get()
        self.config["TARGET_TYPE"] = self.combo_type.get() # [New]
        self.config["TARGET_SITE_NAME"] = self.combo_site.get()
        self.config["STAY_DURATION"] = self.combo_stay.get()
        self.config["STAY_DURATION"] = self.combo_stay.get()
        self.config["DISCOUNT_NAME"] = "지역주민대상자 할인"
        self.config["OPEN_HOUR"] = self.entry_hour.get()   # [Fix] 누락된 시간 저장 추가
        self.config["OPEN_MINUTE"] = self.entry_min.get()  # [Fix] 누락된 분 저장 추가
        self.config["OPEN_MINUTE"] = self.entry_min.get()
        self.config["OPEN_SECOND"] = self.entry_sec.get()
        
        # [New] 대기 시간 저장 (종료 시에도 저장)
        try:
            self.config["WAIT_TIME"] = float(self.entry_wait.get())
        except: 
            self.config["WAIT_TIME"] = 0.0
            
        # self.config["CHROMEDRIVER_PATH"] = self.entry_driver.get() # UI 삭제됨
        self.config["SKIP_NEXT_MONTH"] = self.var_skip_next.get()
        self.config["TEST_MODE"] = self.var_test_mode.get()
        self.config["IMMEDIATE_MODE"] = self.var_immediate.get() # [New]
        self._save_to_file()

    def show_map_popup(self):
        image_path = "문암생태공원.jpg" 
        
        if not os.path.exists(image_path):
            messagebox.showerror("오류", f"이미지 파일을 찾을 수 없습니다.\n({image_path})")
            return

        try:
            top = Toplevel(self.root)
            top.title("캠핑장 맵 - 문암생태공원")
            
            img = Image.open(image_path)
            
            base_width = 1200
            if img.width > base_width:
                w_percent = (base_width / float(img.width))
                h_size = int((float(img.height) * float(w_percent)))
                img = img.resize((base_width, h_size), Image.Resampling.LANCZOS)
            
            tk_img = ImageTk.PhotoImage(img)

            lbl_img = tk.Label(top, image=tk_img)
            lbl_img.image = tk_img 
            lbl_img.pack()
            
        except Exception as e:
            messagebox.showerror("오류", f"이미지를 여는 중 오류가 발생했습니다.\n{e}")

        
    def update_site_list(self, event=None):
        selected_type = self.combo_type.get()
        new_values = []
        
        if selected_type == "캠핑장":
            # 1~28 중 14,15,16 제외
            for i in range(1, 29):
                if i not in [14, 15, 16]:
                    new_values.append(f"캠핑장{i}")
        elif selected_type == "캠핑하우스":
            # 14,15,16 만 포함
            # [수정] 웹사이트 실제 텍스트가 '캠핑하우스XX' 임을 확인 (사용자 제보 이미지 기반)
            new_values = [f"캠핑하우스{i}" for i in [14, 15, 16]]
            
        self.combo_site['values'] = new_values
        
        # 현재 선택된 값이 목록에 없으면 첫 번째 값으로 초기화
        current_val = self.combo_site.get()
        if current_val not in new_values and new_values:
            self.combo_site.current(0)
            
    def create_widgets(self):
        style = ttk.Style()
        style.configure("TLabel", font=("Malgun Gothic", 12))
        style.configure("TButton", font=("Malgun Gothic", 11, "bold"))
        style.configure("TLabelframe.Label", font=("Malgun Gothic", 11, "bold"))
        
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill="both", expand=True)
        
        # 1. 로그인 정보
        lf_login = ttk.LabelFrame(main_frame, text="로그인 정보", padding="10")
        lf_login.pack(fill="x", pady=5)
        
        ttk.Label(lf_login, text="아이디:").grid(row=0, column=0, sticky="e", padx=5)
        self.entry_id = ttk.Entry(lf_login, font=("Malgun Gothic", 11))
        self.entry_id.insert(0, self.config["LOGIN_ID"])
        self.entry_id.grid(row=0, column=1, sticky="ew", padx=5)
        
        ttk.Label(lf_login, text="비밀번호:").grid(row=1, column=0, sticky="e", padx=5)
        self.entry_pw = ttk.Entry(lf_login, show="*", font=("Malgun Gothic", 11))
        self.entry_pw.insert(0, self.config["LOGIN_PW"])
        self.entry_pw.grid(row=1, column=1, sticky="ew", padx=5)
        
        btn_save_login = ttk.Button(lf_login, text="💾 저장", command=self.save_login, width=8)
        btn_save_login.grid(row=0, column=2, rowspan=2, padx=5, sticky="ns")
        
        btn_show_map = ttk.Button(lf_login, text="🗺️ 지도보기", command=self.show_map_popup, width=15)
        btn_show_map.grid(row=0, column=3, rowspan=2, padx=5, sticky="ns")

        # 2. 예약 타겟 설정
        lf_target = ttk.LabelFrame(main_frame, text="예약 목표 설정", padding="10")
        lf_target.pack(fill="x", pady=5)
        
        ttk.Label(lf_target, text="예약 날짜(일):").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        days = [str(i) for i in range(1, 32)]
        self.combo_day = ttk.Combobox(lf_target, values=days, state="readonly", width=5, font=("Malgun Gothic", 11))
        self.combo_day.set(self.config["TARGET_DAY"])
        self.combo_day.grid(row=0, column=1, sticky="w", padx=5)
        
        btn_save_target = ttk.Button(lf_target, text="💾 저장", command=self.save_target, width=8)
        btn_save_target.grid(row=0, column=2, padx=10)
        
        btn_save_target = ttk.Button(lf_target, text="💾 저장", command=self.save_target, width=8)
        btn_save_target.grid(row=0, column=2, padx=10)
        
        # [New] 예약 유형 선택 (캠핑장 vs 캠핑하우스)
        ttk.Label(lf_target, text="예약 유형:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.combo_type = ttk.Combobox(lf_target, values=["캠핑장", "캠핑하우스"], state="readonly", width=15, font=("Malgun Gothic", 11))
        self.combo_type.set(self.config.get("TARGET_TYPE", "캠핑장"))
        self.combo_type.grid(row=1, column=1, sticky="w", padx=5)
        self.combo_type.bind("<<ComboboxSelected>>", self.update_site_list)

        ttk.Label(lf_target, text="사이트 번호:").grid(row=2, column=0, sticky="e", padx=5, pady=5)
        self.combo_site = ttk.Combobox(lf_target, state="readonly", width=15, font=("Malgun Gothic", 11))
        self.combo_site.grid(row=2, column=1, sticky="w", padx=5)
        
        self.update_site_list() # 초기화
        
        # 저장된 값이 있으면 설정 (리스트 업데이트 후)
        if self.config["TARGET_SITE_NAME"] in self.combo_site["values"]:
            self.combo_site.set(self.config["TARGET_SITE_NAME"])
        else:
            if len(self.combo_site["values"]) > 0:
                self.combo_site.current(0)
        
        # 힌트 라벨 삭제 또는 수정 (동적 변경되므로 불필요할 수 있으나 유지)
        # lbl_hint = ttk.Label(lf_target, text="14,15,16 = 캠핑하우스", foreground="blue", font=("Malgun Gothic", 10, "bold"))
        # lbl_hint.grid(row=2, column=2, sticky="w", padx=10)
        
        ttk.Label(lf_target, text="숙박 기간:").grid(row=3, column=0, sticky="e", padx=5, pady=5)
        self.combo_stay = ttk.Combobox(lf_target, values=["1", "2"], state="readonly", width=5, font=("Malgun Gothic", 11))
        self.combo_stay.set(self.config["STAY_DURATION"])
        self.combo_stay.grid(row=3, column=1, sticky="w", padx=5)
        ttk.Label(lf_target, text="(1=1박2일, 2=2박3일)").grid(row=3, column=2, sticky="w")

        # 🚀 [New] 다음달 이동 생략 체크박스
        self.var_skip_next = tk.BooleanVar(value=self.config.get("SKIP_NEXT_MONTH", False))
        chk_skip = ttk.Checkbutton(lf_target, text="다음달 안넘어가기 (이번달 예약 테스트용)", variable=self.var_skip_next)
        chk_skip.grid(row=4, column=0, columnspan=3, sticky="w", padx=5, pady=5)
        
        # 3. 오픈 시간 설정
        lf_time = ttk.LabelFrame(main_frame, text="오픈 시간 설정 (24시간제)", padding="10")
        lf_time.pack(fill="x", pady=5)
        
        # [Left Group] 시간 입력 + 저장 버튼 (첫 번째 줄)
        frame_left = ttk.Frame(lf_time)
        frame_left.pack(anchor="w", pady=5)
        
        # 시간 입력창들
        self.entry_hour = ttk.Entry(frame_left, width=3, justify="center", font=("Malgun Gothic", 11))
        self.entry_hour.insert(0, self.config["OPEN_HOUR"])
        self.entry_hour.pack(side="left")
        ttk.Label(frame_left, text="시").pack(side="left", padx=2)
        
        self.entry_min = ttk.Entry(frame_left, width=3, justify="center", font=("Malgun Gothic", 11))
        self.entry_min.insert(0, self.config["OPEN_MINUTE"])
        self.entry_min.pack(side="left")
        ttk.Label(frame_left, text="분").pack(side="left", padx=2)
        
        self.entry_sec = ttk.Entry(frame_left, width=3, justify="center", font=("Malgun Gothic", 11))
        self.entry_sec.insert(0, self.config["OPEN_SECOND"])
        self.entry_sec.pack(side="left")
        ttk.Label(frame_left, text="초").pack(side="left", padx=2)



        # [New] 대기 시간 (새로고침 후)
        ttk.Label(frame_left, text=" |  대기(초):").pack(side="left", padx=5)
        self.entry_wait = ttk.Entry(frame_left, width=4, justify="center", font=("Malgun Gothic", 11))
        self.entry_wait.insert(0, self.config.get("WAIT_TIME", 0.0))
        self.entry_wait.pack(side="left")
        

        
        # 저장 버튼
        btn_save_time = ttk.Button(frame_left, text="💾 저장", command=self.save_time, width=8)
        btn_save_time.pack(side="left", padx=(20, 0))

        # [Right Group] 체크박스들 (두 번째 줄)
        frame_right = ttk.Frame(lf_time)
        frame_right.pack(anchor="w", pady=5)
        
        # 가로 배치로 변경 (공간 절약)
        # frame_right.pack(side="left") -> anchor="w" (줄바꿈)

        # [New] 상호 배타적 체크박스 로직
        def on_test_click():
            if self.var_test_mode.get():
                self.var_immediate.set(False)

        def on_immediate_click():
            if self.var_immediate.get():
                self.var_test_mode.set(False)

        # 🧪 테스트 모드 체크박스
        self.var_test_mode = tk.BooleanVar(value=self.config.get("TEST_MODE", False))
        chk_test = ttk.Checkbutton(frame_right, text="TestMode(예약시간)", variable=self.var_test_mode, command=on_test_click)
        chk_test.pack(anchor="w", pady=2)

        # 🔥 바로시작 체크박스
        self.var_immediate = tk.BooleanVar(value=self.config.get("IMMEDIATE_MODE", False))
        chk_immediate = ttk.Checkbutton(frame_right, text="TestMode(바로시작)", variable=self.var_immediate, command=on_immediate_click)
        chk_immediate.pack(anchor="w", pady=2)
        


        # 버튼 구역 변경
        frame_btns = ttk.Frame(main_frame)
        frame_btns.pack(fill="x", pady=15)
        
        # [F2] 예약 시작
        self.btn_start = ttk.Button(frame_btns, text="예약시작(Start) (F2)", command=self.start_bot, width=20)
        self.btn_start.pack(side="left", padx=5)
        
        # [F3] 중지
        self.btn_stop = ttk.Button(frame_btns, text="중지(Stop) (F3)", command=self.stop_bot, width=15)
        self.btn_stop.pack(side="left", padx=5)

        # [New] 속도 측정 버튼
        btn_speed = ttk.Button(frame_btns, text="⚡ 속도 측정", command=self.run_speed_test, width=12)
        btn_speed.pack(side="right", padx=5)

        # 로그창
        self.log_area = scrolledtext.ScrolledText(main_frame, height=12, state='disabled', font=("Consolas", 10))
        self.log_area.pack(fill="both", expand=True)

    def log(self, msg):
        now = datetime.now()
        timestamp = f"[{now.strftime('%H:%M:%S')}.{now.microsecond // 10000:02d}]"
        formatted_msg = f"{timestamp} {msg}\n"
        
        def _update():
            self.log_area.config(state='normal')
            self.log_area.insert(tk.END, formatted_msg)
            self.log_area.see(tk.END)
            self.log_area.config(state='disabled')
        
        self.root.after(0, _update)
        print(formatted_msg.strip())

    def validate_inputs(self):
        if not self.entry_id.get() or not self.entry_pw.get():
            messagebox.showwarning("경고", "아이디와 비밀번호를 입력해주세요.")
            return False
        return True

    def toggle_buttons(self, is_running):
        if is_running:
            self.btn_start.config(state="disabled")
            self.btn_stop.config(state="normal")
        else:
            self.btn_start.config(state="normal")
            self.btn_stop.config(state="disabled")

    def start_bot(self):
        if not self.validate_inputs(): return
        self.save_all_config()
        
        immediate = self.var_immediate.get()
        mode_msg = "🔥 바로 시작 모드" if immediate else "🕒 예약 대기 모드"

        self.toggle_buttons(True)
        self.log(f"{mode_msg}로 시작합니다... (F3로 중지 가능)")
        
        threading.Thread(target=self.run_bot_logic, args=(immediate,), daemon=True).start()

    def run_speed_test(self):
        if not self.validate_inputs(): return
        self.toggle_buttons(True)
        
        # 별도 스레드에서 속도 측정 실행


    def run_speed_test(self):
        if not self.validate_inputs(): return
        self.toggle_buttons(True)
        
        # 별도 스레드에서 속도 측정 실행
        def _test_wrapper():
            try:
                # [Fix] 인자 순서 수정: (log_callback, config)
                self.bot = CampingBot(self.log, self.config)
                self.bot.measure_speed()
            except Exception as e:
                self.log(f"오류: {e}")
            finally:
                self.toggle_buttons(False)
                
        threading.Thread(target=_test_wrapper, daemon=True).start()

    def stop_bot(self):
        if self.bot and self.bot.is_running:
            self.bot.is_running = False
            self.log("🛑 중지 요청됨! (현재 작업까지만 수행하고 멈춥니다)")
        else:
            self.log("ℹ️ 실행 중인 봇이 없습니다.")

    def run_bot_logic(self, immediate_mode):
        self.bot = CampingBot(self.log, self.config, immediate_mode=immediate_mode)
        try:
            self.bot.run()
        except Exception as e:
            self.log(f"Err: {e}")
        finally:
            self.root.after(0, lambda: self.toggle_buttons(False))

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()