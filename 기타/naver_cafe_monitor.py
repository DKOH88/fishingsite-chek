#!/usr/bin/env python3
"""
네이버 카페 양도게시판 키워드 모니터링 및 텔레그램 알람 시스템
사용법: python naver_cafe_monitor.py
"""

import os
import time
import sys
import json
import requests
import random
from datetime import datetime
from urllib.parse import urlparse
import re

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
    from selenium.webdriver.common.keys import Keys
except ImportError:
    print("❌ Selenium이 설치되어 있지 않습니다.")
    print("다음 명령어로 설치하세요:")
    print("pip install selenium requests")
    print("pip install webdriver-manager")
    sys.exit(1)

try:
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service
except ImportError:
    print("❌ webdriver-manager가 설치되어 있지 않습니다.")
    print("다음 명령어로 설치하세요:")
    print("pip install webdriver-manager")
    sys.exit(1)


class NaverCafeMonitor:
    def __init__(self):
        self.driver = None
        self.monitored_posts = set()  # 이미 알람을 보낸 게시글 ID 추적
        self.last_post_number = 0  # 마지막으로 확인한 게시글 번호
        self.config = self.load_config()
        
    def load_config(self):
        """설정 파일 로드 또는 생성"""
        config_file = "cafe_monitor_config.json"
        default_config = {
            "cafe_url": "https://cafe.naver.com/badajd",
            "keywords": ["제주, 승리호"],
            "telegram_bot_token": "",
            "telegram_chat_id": "",
            "monitor_interval": 10,
            "naver_id": "",
            "naver_password": "",
            "sleep_start_hour": 23,
            "sleep_start_minute": 59,
            "sleep_end_hour": 5,
            "sleep_end_minute": 0
        }
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    print(f"✅ 설정 파일 로드 완료: {config_file}")
                    return loaded_config
            except Exception as e:
                print(f"⚠️ 설정 파일 읽기 실패: {e}")
                print("⚠️ 기존 설정을 사용합니다. 파일이 손상되었다면 삭제 후 다시 실행하세요.")
                return default_config

        # 설정 파일이 없으면 생성
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)

        print(f"📁 설정 파일이 생성되었습니다: {config_file}")
        print("🔧 설정 파일을 편집하여 네이버 계정 정보와 텔레그램 설정을 입력하세요.")

        return default_config
    
    def is_sleep_time(self):
        """현재 시간이 수면 시간대인지 확인"""
        try:
            now = datetime.now()
            current_hour = now.hour
            current_minute = now.minute
            
            # 설정에서 수면 시간대 가져오기
            sleep_start_hour = self.config.get('sleep_start_hour', 23)
            sleep_start_minute = self.config.get('sleep_start_minute', 59) 
            sleep_end_hour = self.config.get('sleep_end_hour', 5)
            sleep_end_minute = self.config.get('sleep_end_minute', 0)
            
            # 현재 시간을 분으로 변환
            current_time_minutes = current_hour * 60 + current_minute
            sleep_start_minutes = sleep_start_hour * 60 + sleep_start_minute
            sleep_end_minutes = sleep_end_hour * 60 + sleep_end_minute
            
            # 자정을 넘나드는 시간대 처리
            if sleep_start_minutes > sleep_end_minutes:
                # 예: 23:59 ~ 05:00 (자정 넘김)
                return current_time_minutes >= sleep_start_minutes or current_time_minutes <= sleep_end_minutes
            else:
                # 예: 02:00 ~ 06:00 (자정 안넘김)
                return sleep_start_minutes <= current_time_minutes <= sleep_end_minutes
                
        except Exception as e:
            print(f"⚠️ 시간 확인 중 오류: {e}")
            return False
    
    def wait_until_wake_time(self):
        """수면 시간이 끝날 때까지 대기"""
        try:
            sleep_end_hour = self.config.get('sleep_end_hour', 5)
            sleep_end_minute = self.config.get('sleep_end_minute', 0)
            
            print(f"\n💤 수면 모드 진입: 오전 {sleep_end_hour:02d}:{sleep_end_minute:02d}까지 대기합니다.")
            print("🌙 모니터링이 일시 중지되었습니다.")
            
            while self.is_sleep_time():
                now = datetime.now()
                
                # 매 30분마다 상태 출력
                if now.minute in [0, 30]:
                    remaining_time = self.get_remaining_sleep_time()
                    if remaining_time:
                        print(f"😴 수면 모드 중... ({now.strftime('%H:%M')}) - {remaining_time}")
                
                # 30초마다 시간 체크
                time.sleep(30)
            
            print(f"\n🌅 수면 모드 해제: {datetime.now().strftime('%H:%M')} - 모니터링을 재개합니다!")
            
        except KeyboardInterrupt:
            print("\n⏹️ 수면 모드에서 사용자에 의해 중단되었습니다.")
            raise
        except Exception as e:
            print(f"⚠️ 수면 모드 대기 중 오류: {e}")
    
    def get_remaining_sleep_time(self):
        """수면 종료까지 남은 시간 계산"""
        try:
            now = datetime.now()
            sleep_end_hour = self.config.get('sleep_end_hour', 5)
            sleep_end_minute = self.config.get('sleep_end_minute', 0)
            
            # 수면 종료 시간 계산
            end_time = now.replace(hour=sleep_end_hour, minute=sleep_end_minute, second=0, microsecond=0)
            
            # 수면 종료가 다음날인 경우
            if end_time <= now:
                end_time = end_time.replace(day=now.day + 1)
            
            # 남은 시간 계산
            remaining = end_time - now
            hours = remaining.seconds // 3600
            minutes = (remaining.seconds % 3600) // 60
            
            if remaining.days > 0:
                hours += remaining.days * 24
            
            return f"약 {hours}시간 {minutes}분 남음"
            
        except Exception as e:
            print(f"⚠️ 남은 시간 계산 오류: {e}")
            return None
        
    def setup_driver(self, headless=False):
        """Chrome 드라이버 설정"""
        chrome_options = Options()
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--allow-running-insecure-content")
        
        # 헤드리스 모드 설정
        if headless:
            chrome_options.add_argument("--headless")
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # 사용자 에이전트 설정
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            print("✅ Chrome 드라이버가 성공적으로 설정되었습니다.")
            return True
            
        except Exception as e:
            print(f"❌ 드라이버 설정 실패: {e}")
            return False
    
    def login_naver(self):
        """네이버 로그인"""
        try:
            print("🔐 네이버 로그인 시도...")
            
            # 네이버 로그인 페이지로 이동
            self.driver.get("https://nid.naver.com/nidlogin.login")
            time.sleep(3)
            
            # 아이디, 비밀번호 입력
            id_input = self.driver.find_element(By.ID, "id")
            pw_input = self.driver.find_element(By.ID, "pw")
            
            # JavaScript로 값 설정 (보안 우회)
            self.driver.execute_script(f"arguments[0].value='{self.config['naver_id']}';", id_input)
            time.sleep(1)
            self.driver.execute_script(f"arguments[0].value='{self.config['naver_password']}';", pw_input)
            time.sleep(1)
            
            # 로그인 버튼 클릭
            login_btn = self.driver.find_element(By.ID, "log.login")
            login_btn.click()
            
            print("⏳ 로그인 처리 중...")
            time.sleep(5)
            
            # 추가 인증 단계 확인 (등록 버튼 등)
            try:
                # 현재 페이지 URL 확인
                current_url = self.driver.current_url
                print(f"🔍 현재 URL: {current_url}")
                
                # 등록안함 버튼을 우선으로 찾는 선택자
                register_selectors = [
                    # 등록안함 관련 버튼들 (우선순위)
                    "a[onclick*='cancel']",  # 취소 관련 onclick
                    "a[onclick*='skip']",  # 건너뛰기 관련 onclick
                    "a[href*='cancel']",  # 취소 관련 href
                    "button[type='button'][onclick*='cancel']",  # 취소 버튼
                    "input[type='button'][value*='안함']",  # 안함 버튼
                    
                    # 일반적인 등록 버튼들 (백업용)
                    "a[id='new.save'][class='btn']",  # 정확한 등록 버튼
                    "span.btn_upload a",  # span 내부의 등록 링크  
                    "a[href='#'][class='btn']",  # # 링크인 버튼
                    "a.btn[id*='new']",  # new로 시작하는 ID의 버튼
                    "fieldset.login_form a.btn",  # 로그인 폼 내의 버튼
                    "a[class='btn'][href='#']",  # 일반 등록 버튼 패턴
                ]
                
                register_found = False
                
                for selector in register_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for element in elements:
                            text = element.text.strip()
                            print(f"🔍 발견된 버튼: '{text}'")
                            
                            # 등록안함 관련 텍스트 우선 확인
                            if any(keyword in text for keyword in ['등록안함', '안함', '나중에', '취소', '건너뛰기']):
                                print(f"🎯 '{text}' 버튼을 클릭합니다.")
                                
                                # JavaScript로 클릭 시도
                                try:
                                    self.driver.execute_script("arguments[0].click();", element)
                                    register_found = True
                                    time.sleep(3)
                                    print("✅ 등록안함 선택 완료")
                                    break
                                except Exception as click_error:
                                    print(f"⚠️ 클릭 실패: {click_error}")
                                    # 일반 클릭 시도
                                    try:
                                        element.click()
                                        register_found = True
                                        time.sleep(3)
                                        print("✅ 등록안함 선택 완료")
                                        break
                                    except:
                                        continue
                            
                            # 등록안함이 없으면 등록 관련 텍스트 확인
                            elif any(keyword in text for keyword in ['등록', '완료', '확인', '저장', '제출']):
                                print(f"🎯 '{text}' 버튼을 클릭합니다. (등록안함을 찾지 못했습니다)")
                                
                                # JavaScript로 클릭 시도
                                try:
                                    self.driver.execute_script("arguments[0].click();", element)
                                    register_found = True
                                    time.sleep(3)
                                    print("✅ 추가 인증 단계 완료")
                                    break
                                except Exception as click_error:
                                    print(f"⚠️ 클릭 실패: {click_error}")
                                    # 일반 클릭 시도
                                    try:
                                        element.click()
                                        register_found = True
                                        time.sleep(3)
                                        print("✅ 추가 인증 단계 완료")
                                        break
                                    except:
                                        continue
                        
                        if register_found:
                            break
                            
                    except Exception as e:
                        continue
                
                if not register_found:
                    # 텍스트 기반으로 '등록안함' 우선 검색
                    try:
                        # 1차: 등록안함 관련 키워드 우선 검색
                        negative_keywords = ['등록안함', '안함', '나중에', '취소', '건너뛰기', '거부']
                        
                        for keyword in negative_keywords:
                            try:
                                elements = self.driver.find_elements(By.XPATH, f"//*[contains(text(), '{keyword}')]")
                                if elements:
                                    for elem in elements:
                                        if elem.tag_name in ['a', 'button', 'input', 'span']:
                                            print(f"🎯 텍스트 기반으로 '{elem.text}' 요소 클릭 시도")
                                            try:
                                                self.driver.execute_script("arguments[0].click();", elem)
                                                register_found = True
                                                time.sleep(3)
                                                print("✅ 등록안함 버튼 클릭 완료")
                                                break
                                            except:
                                                continue
                                    
                                    if register_found:
                                        break
                            except:
                                continue
                        
                        # 2차: 등록안함을 못찾으면 등록 관련 키워드 검색
                        if not register_found:
                            register_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), '등록')]")
                            if register_elements:
                                for elem in register_elements:
                                    if elem.tag_name in ['a', 'button', 'input', 'span']:
                                        print(f"🎯 텍스트 기반으로 '{elem.text}' 요소 클릭 시도 (등록안함을 찾지 못했습니다)")
                                        try:
                                            self.driver.execute_script("arguments[0].click();", elem)
                                            register_found = True
                                            time.sleep(3)
                                            print("✅ 등록 버튼 클릭 완료")
                                            break
                                        except:
                                            continue
                                            
                    except Exception as e:
                        print(f"⚠️ 텍스트 기반 검색 실패: {e}")
                
                if not register_found:
                    print("⚠️ 등록 버튼을 찾지 못했습니다. 자동 로그인 진행...")
                
            except Exception as e:
                print(f"⚠️ 추가 인증 단계 확인 중 오류: {e}")
            
            # 최종 로그인 성공 확인
            time.sleep(3)
            final_url = self.driver.current_url
            
            # 로그인 성공 판단 기준 확장
            success_indicators = [
                "nid.naver.com" not in final_url,  # 로그인 페이지를 벗어남
                "cafe.naver.com" in final_url,     # 카페로 이동됨
                "www.naver.com" in final_url       # 네이버 메인으로 이동됨
            ]
            
            if any(success_indicators):
                print("✅ 네이버 로그인 성공!")
                return True
            else:
                print("❌ 로그인 실패 - 추가 확인이 필요할 수 있습니다.")
                print(f"현재 URL: {final_url}")
                
                # 수동 확인 옵션 제공
                manual_check = input("로그인이 완료되었다면 'y'를 입력하세요 (y/n): ").strip().lower()
                if manual_check == 'y':
                    print("✅ 수동 확인으로 로그인 완료 처리")
                    return True
                else:
                    return False
                
        except Exception as e:
            print(f"❌ 로그인 중 오류 발생: {e}")
            return False
    
    def access_cafe_board(self):
        """카페 양도게시판 접근"""
        try:
            # 방법 1: 직접 양도게시판 URL로 접근
            if 'board_url' in self.config and self.config['board_url']:
                print("🎯 직접 양도게시판 URL로 접근 중...")
                self.driver.get(self.config['board_url'])
                time.sleep(5)
                
                # 게시판 페이지 로드 확인 (더 관대한 기준)
                try:
                    # 충분한 로딩 시간 제공
                    time.sleep(3)
                    
                    # 현재 URL이 MemoList인지 확인
                    current_url = self.driver.current_url
                    if "MemoList.nhn" in current_url:
                        print("✅ 양도게시판 URL 직접 접근 성공!")
                        return True
                    
                    # 게시판 관련 요소가 있는지 간단히 확인
                    page_source = self.driver.page_source
                    board_keywords = ["게시판", "게시글", "작성자", "제목", "등록일", "조회"]
                    
                    if any(keyword in page_source for keyword in board_keywords):
                        print("✅ 게시판 페이지 로드 확인!")
                        return True
                    else:
                        print("⚠️ 게시판 페이지를 확인할 수 없습니다. 메뉴 검색 방식으로 전환...")
                        
                except Exception as e:
                    print(f"⚠️ 게시판 확인 중 오류: {e}")
                    print("⚠️ 메뉴 검색 방식으로 전환...")
            
            # 방법 2: 기존 메뉴 검색 방식
            print("🏠 카페 메인으로 접근 중...")
            self.driver.get(self.config['cafe_url'])
            time.sleep(5)
            
            # 카페 프레임으로 전환
            try:
                cafe_frame = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "cafe_main"))
                )
                self.driver.switch_to.frame(cafe_frame)
                print("✅ 카페 프레임 전환 완료")
                time.sleep(2)
                
            except:
                print("⚠️ 프레임 전환 실패, 일반 페이지로 진행")
            
            # 카페 메뉴에서 양도게시판 찾기 (다중 전략)
            board_found = False
            
            # 전략 1: 사이드바 메뉴 전체 스캔 (더 포괄적)
            sidebar_menu_patterns = [
                # 왼쪽 사이드바 메뉴들
                "div.cafe-menu a",
                "div[class*='menu'] a", 
                "nav a",
                "aside a",
                ".sidebar a",
                ".leftmenu a",
                "#leftSide a",
                
                # 메뉴링크 ID 패턴 (menuLink + 숫자)  
                "a[id^='menuLink']",
                "a[id*='menuLink']",
                "a[id*='menuLink'][class*='gm-tcol-c']",
                
                # 일반적인 메뉴 패턴
                "a[target='cafe_main'][onclick*='goMenu']", 
                "a[class*='gm-tcol-c']",
                "a[onclick*='goMenu']",
                
                # 리스트 기반 메뉴
                "ul li a",
                "ol li a", 
                ".menu_list a",
                
                # 모든 링크 (마지막 백업)
                "a[href*='MemoList']",
                "a[href*='articlelist']",
                "a[href*='board']"
            ]
            
            print("🔍 사이드바 메뉴 전체 검색 중...")
            
            for pattern in sidebar_menu_patterns:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, pattern)
                    if elements:
                        print(f"✅ '{pattern}' 패턴으로 {len(elements)}개 메뉴 링크 발견")
                        
                        for i, element in enumerate(elements):
                            try:
                                text = element.text.strip()
                                menu_id = element.get_attribute("id")
                                onclick = element.get_attribute("onclick")
                                
                                print(f"🔍 [{i+1}] ID: {menu_id}, 텍스트: {text}")
                                
                                # 양도 관련 키워드 확인
                                keywords = ["양도", "거래", "판매", "팝니다", "삽니다", "중고", "나눔"]
                                for keyword in keywords:
                                    if keyword in text:
                                        print(f"🎯 '{keyword}' 키워드 발견: {text}")
                                        
                                        # 클릭 시도
                                        try:
                                            self.driver.execute_script("arguments[0].click();", element)
                                            time.sleep(3)
                                            print(f"✅ '{text}' 게시판에 접근했습니다.")
                                            return True
                                        except Exception as click_error:
                                            print(f"⚠️ 클릭 실패: {click_error}")
                                            continue
                                            
                            except Exception as e:
                                continue
                                
                except Exception as e:
                    print(f"⚠️ 패턴 '{pattern}' 검색 실패: {e}")
                    continue
            
            # 전략 2: 다양한 메뉴 영역 ID 시도 (기존 로직)
            menu_selectors = [
                "#cafe-menu",           # 일반적인 카페 메뉴
                "#menuLayer",           # 메뉴 레이어
                ".cafe-menu",           # 클래스 기반
                "[class*='menu']",      # 메뉴 포함 클래스
                "#gnb",                 # 글로벌 네비게이션
                ".gnb",                 # 글로벌 네비게이션 클래스
                "#leftMenu",            # 왼쪽 메뉴
                ".leftmenu",            # 왼쪽 메뉴 클래스
                "#sideMenu",            # 사이드 메뉴
                "nav",                  # nav 태그
                ".navigation"           # 네비게이션 클래스
            ]
            
            menu_found = False
            menu_area = None
            
            for selector in menu_selectors:
                try:
                    menu_area = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if menu_area:
                        print(f"✅ '{selector}' 선택자로 메뉴 영역 발견")
                        menu_found = True
                        break
                except:
                    continue
            
            if menu_found and menu_area:
                try:
                    # 메뉴 영역에서 링크 찾기
                    menu_links = menu_area.find_elements(By.TAG_NAME, "a")
                    print(f"📋 메뉴 영역에서 {len(menu_links)}개 링크 발견")
                    
                    for i, link in enumerate(menu_links):
                        try:
                            link_text = link.text.strip()
                            href = link.get_attribute("href")
                            
                            if link_text:  # 텍스트가 있는 링크만 확인
                                print(f"🔍 [{i+1}] 메뉴: {link_text}")
                                
                                # 양도 관련 키워드 확인
                                keywords = ["양도", "거래", "판매", "팝니다", "삽니다", "중고", "나눔"]
                                for keyword in keywords:
                                    if keyword in link_text:
                                        print(f"🎯 '{keyword}' 키워드 발견: {link_text}")
                                        
                                        # 클릭 시도
                                        try:
                                            self.driver.execute_script("arguments[0].click();", link)
                                            time.sleep(3)
                                            print(f"✅ '{link_text}' 게시판에 접근했습니다.")
                                            return True
                                        except Exception as click_error:
                                            print(f"⚠️ 클릭 실패: {click_error}")
                                            continue
                                        
                        except Exception as e:
                            continue
                            
                except Exception as e:
                    print(f"⚠️ 메뉴 링크 처리 중 오류: {e}")
            else:
                print("⚠️ 메뉴 영역을 찾을 수 없습니다.")
            
            # 전략 3: 직접 메뉴 링크 ID 검색 (menuLink + 숫자 패턴)
            if not board_found:
                try:
                    print("🔄 메뉴 링크 ID 직접 검색 중...")
                    
                    # menuLink로 시작하는 모든 ID 검색
                    menu_link_elements = self.driver.find_elements(By.CSS_SELECTOR, "a[id^='menuLink']")
                    
                    if menu_link_elements:
                        print(f"📋 {len(menu_link_elements)}개의 menuLink ID 발견")
                        
                        for i, element in enumerate(menu_link_elements):
                            try:
                                text = element.text.strip()
                                menu_id = element.get_attribute("id")
                                href = element.get_attribute("href")
                                
                                print(f"🔍 [{i+1}] ID: {menu_id}, 텍스트: '{text}'")
                                
                                # 양도 관련 키워드 확인 (◈ 기호도 포함)
                                keywords = ["양도", "거래", "판매", "팝니다", "삽니다", "중고", "나눔"]
                                text_clean = text.replace("◈", "").strip()  # ◈ 기호 제거
                                
                                for keyword in keywords:
                                    if keyword in text_clean:
                                        print(f"🎯 '{keyword}' 키워드 발견: {text}")
                                        
                                        # JavaScript로 클릭
                                        try:
                                            self.driver.execute_script("arguments[0].click();", element)
                                            time.sleep(3)
                                            print(f"✅ '{text_clean}' 게시판에 접근했습니다.")
                                            return True
                                        except Exception as click_error:
                                            print(f"⚠️ 클릭 실패, href로 직접 이동 시도: {click_error}")
                                            
                                            # href로 직접 이동 시도
                                            if href:
                                                try:
                                                    self.driver.get(href)
                                                    time.sleep(3)
                                                    print(f"✅ URL로 '{text_clean}' 게시판 접근 완료")
                                                    return True
                                                except Exception as href_error:
                                                    print(f"⚠️ URL 접근도 실패: {href_error}")
                                                    continue
                                            
                            except Exception as e:
                                print(f"⚠️ 요소 처리 중 오류: {e}")
                                continue
                    else:
                        print("⚠️ menuLink ID 패턴을 찾을 수 없습니다.")
                        
                except Exception as e:
                    print(f"⚠️ 메뉴 링크 ID 검색 실패: {e}")
            
            # 전략 4: 페이지 전체에서 양도 관련 링크 검색  
            if not board_found:
                try:
                    print("🔄 전체 페이지에서 양도 관련 메뉴 검색 중...")
                    
                    # XPath로 더 정확한 검색
                    xpath_patterns = [
                        "//a[contains(text(), '◈양도')]",  # ◈ 포함된 패턴
                        "//a[contains(text(), '양도게시판')]",
                        "//a[contains(text(), '양도') and @target='cafe_main']",
                        "//a[contains(text(), '양도') and contains(@onclick, 'goMenu')]",
                        "//a[contains(text(), '거래') and @class='gm-tcol-c']",
                        "//a[contains(text(), '판매') and @target='cafe_main']"
                    ]
                    
                    for pattern in xpath_patterns:
                        try:
                            elements = self.driver.find_elements(By.XPATH, pattern)
                            if elements:
                                for element in elements:
                                    try:
                                        text = element.text.strip()
                                        menu_id = element.get_attribute("id")
                                        print(f"🎯 XPath 패턴으로 발견: {text} (ID: {menu_id})")
                                        
                                        # 클릭 시도
                                        self.driver.execute_script("arguments[0].click();", element)
                                        time.sleep(3)
                                        print(f"✅ '{text}' 게시판 접근 완료")
                                        return True
                                        
                                    except Exception as e:
                                        continue
                                        
                        except Exception as e:
                            continue
                
                except Exception as e:
                    print(f"⚠️ XPath 검색 실패: {e}")
            
            # 전략 5: CSS 클래스 기반 메뉴 검색
            if not board_found:
                try:
                    print("🔄 CSS 클래스 기반 메뉴 검색 중...")
                    
                    class_selectors = [
                        ".board-list a",
                        ".menu-list a", 
                        ".cafe-menu-list a",
                        "[class*='menu'] a",
                        "[class*='board'] a",
                        "[class*='nav'] a"
                    ]
                    
                    for selector in class_selectors:
                        try:
                            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                            if elements:
                                print(f"📋 '{selector}' 선택자로 {len(elements)}개 요소 발견")
                                
                                for element in elements[:10]:  # 처음 10개만 확인
                                    try:
                                        text = element.text.strip()
                                        if text:
                                            print(f"🔍 요소: {text}")
                                            
                                            # 키워드 확인
                                            keywords = ["양도", "거래", "판매", "팝니다", "삽니다"]
                                            for keyword in keywords:
                                                if keyword in text:
                                                    print(f"🎯 '{keyword}' 키워드 발견: {text}")
                                                    
                                                    self.driver.execute_script("arguments[0].click();", element)
                                                    time.sleep(3)
                                                    return True
                                                    
                                    except Exception as e:
                                        continue
                                        
                        except Exception as e:
                            continue
                            
                except Exception as e:
                    print(f"⚠️ CSS 클래스 기반 검색 실패: {e}")
            
            # 전략 6: DOM 구조 분석 및 디버깅
            if not board_found:
                try:
                    print("🔍 페이지 DOM 구조 분석 중...")
                    
                    # 페이지의 모든 링크 텍스트 수집
                    all_links = self.driver.find_elements(By.TAG_NAME, "a")
                    link_texts = []
                    
                    for link in all_links[:30]:  # 처음 30개만 분석
                        try:
                            text = link.text.strip()
                            if text and len(text) < 30:
                                link_texts.append(text)
                        except:
                            continue
                    
                    print(f"📋 페이지의 주요 링크들: {', '.join(link_texts[:15])}")
                    
                    # 특별한 패턴 검색
                    special_patterns = [
                        "//a[contains(@href, 'board') and contains(text(), '양')]",
                        "//a[contains(@href, 'articlelist') and contains(text(), '양')]",
                        "//li[contains(@class, 'menu')]/a[contains(text(), '양')]",
                        "//div[contains(@class, 'menu')]/a[contains(text(), '양')]",
                        "//a[contains(@onclick, 'board') and contains(text(), '양')]"
                    ]
                    
                    for pattern in special_patterns:
                        try:
                            elements = self.driver.find_elements(By.XPATH, pattern)
                            if elements:
                                for element in elements:
                                    try:
                                        text = element.text.strip()
                                        print(f"🎯 특별 패턴으로 발견: {text}")
                                        
                                        self.driver.execute_script("arguments[0].click();", element)
                                        time.sleep(3)
                                        return True
                                        
                                    except Exception as e:
                                        continue
                                        
                        except Exception as e:
                            continue
                            
                except Exception as e:
                    print(f"⚠️ DOM 분석 실패: {e}")
            
            # 최종 백업: 사용자 지원 모드
            if not board_found:
                print("\n" + "="*60)
                print("❌ 자동으로 양도게시판을 찾을 수 없습니다.")
                print("💡 다음 중 하나를 선택해주세요:")
                print("="*60)
                print("1. 브라우저에서 수동으로 양도게시판에 접근 (권장)")
                print("2. URL을 직접 입력하여 접근")
                print("3. 게시판 링크를 수동으로 클릭 후 계속")
                print("4. 프로그램 종료")
                
                choice = input("\n선택하세요 (1/2/3/4): ").strip()
                
                if choice == '1':
                    print("📍 브라우저에서 양도게시판으로 직접 이동해주세요.")
                    input("양도게시판 접근 완료 후 엔터를 누르세요...")
                elif choice == '2':
                    board_url = input("양도게시판 URL을 입력하세요: ").strip()
                    if board_url:
                        try:
                            self.driver.get(board_url)
                            time.sleep(3)
                            print("✅ URL로 게시판 접근 완료")
                        except Exception as e:
                            print(f"❌ URL 접근 실패: {e}")
                            input("수동으로 접근 후 엔터를 누르세요...")
                elif choice == '3':
                    print("📍 브라우저에서 양도게시판 링크를 찾아 클릭하세요.")
                    input("클릭 완료 후 엔터를 누르세요...")
                else:
                    print("🔚 프로그램을 종료합니다.")
                    return False
            
            return True
            
        except Exception as e:
            print(f"❌ 카페 접근 중 오류: {e}")
            return False
    
    def get_latest_post_number(self):
        """최신 게시글 번호 가져오기"""
        try:
            # 직접 board_url로 이동해서 iframe 문제 우회
            current_url = self.driver.current_url
            print(f"🔍 현재 URL: {current_url}")
            
            if 'board_url' in self.config and self.config['board_url'] and "MemoList" not in current_url:
                print("🔄 직접 게시판 URL로 이동 중...")
                self.driver.get(self.config['board_url'])
                time.sleep(3)
                
                new_url = self.driver.current_url
                print(f"🔍 이동 후 URL: {new_url}")
            
            # iframe 프레임 확인 및 전환 (강화)
            try:
                current_url = self.driver.current_url
                
                # 메인 프레임에서 iframe으로 전환 시도 (MemoList가 없는 경우만)
                if "iframe_url" in current_url or ("cafe.naver.com" in current_url and "MemoList" not in current_url):
                    print("🔄 iframe 프레임 전환 시도...")
                    
                    # 가능한 iframe 선택자들 시도
                    iframe_selectors = [
                        "#cafe_main",        # 일반적인 카페 메인 프레임
                        "iframe[name='cafe_main']",
                        "iframe[id='cafe_main']",
                        "iframe[src*='MemoList']",  # MemoList가 포함된 iframe
                        "iframe"             # 첫 번째 iframe
                    ]
                    
                    iframe_switched = False
                    for selector in iframe_selectors:
                        try:
                            print(f"🔍 '{selector}' iframe 검색 중...")
                            iframe_element = WebDriverWait(self.driver, 3).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                            )
                            self.driver.switch_to.frame(iframe_element)
                            iframe_switched = True
                            print(f"✅ '{selector}' 프레임으로 전환 완료")
                            break
                        except Exception as iframe_error:
                            continue
                    
                    if not iframe_switched:
                        print("⚠️ 모든 iframe 전환 시도 실패, 메인 페이지에서 진행")
                    
                    time.sleep(2)  # 프레임 전환 후 대기 시간 증가
                else:
                    print("✅ 이미 게시판 페이지에 있음, iframe 전환 생략")
                
                # 프레임 전환 후 URL 다시 확인
                try:
                    frame_url = self.driver.execute_script("return window.location.href;")
                    print(f"🔍 최종 URL: {frame_url}")
                except:
                    print("⚠️ 최종 URL 확인 실패")
                    
            except Exception as frame_error:
                print(f"⚠️ 프레임 처리 중 오류: {frame_error}")
            
            print("🔍 게시글 번호 추출 시도...")
            
            # 방법 1: memo-box 클래스를 가진 p 태그에서 post_숫자 ID 패턴으로 검색
            post_elements = self.driver.find_elements(By.CSS_SELECTOR, "p.memo-box[id^='post_']")
            print(f"📋 p.memo-box[id^='post_'] 패턴 요소 발견: {len(post_elements)}개")
            
            if post_elements:
                post_numbers = []
                for i, element in enumerate(post_elements):
                    post_id = element.get_attribute("id")
                    print(f"🔍 [{i+1}] ID: {post_id}")
                    
                    if post_id and post_id.startswith("post_"):
                        try:
                            number = int(post_id.replace("post_", ""))
                            post_numbers.append(number)
                        except:
                            continue
                
                if post_numbers:
                    # 맨 위의 게시글이 최신이므로 첫 번째 요소의 번호가 최신
                    first_element_id = post_elements[0].get_attribute("id")
                    if first_element_id and first_element_id.startswith("post_"):
                        latest_number = int(first_element_id.replace("post_", ""))
                        print(f"✅ 첫 번째 p 요소에서 최신 번호: post_{latest_number}")
                        print(f"🔍 발견된 모든 번호: {sorted(post_numbers, reverse=True)[:5]}")
                        return latest_number
                    else:
                        # 백업: 가장 큰 번호 사용
                        latest_number = max(post_numbers)
                        print(f"✅ post_ 패턴에서 최대 번호: post_{latest_number}")
                        return latest_number
            
            # 방법 1-2: memo-box 없이 일반적인 post_ ID 패턴도 시도 (백업)
            print("🔄 일반적인 .memo-box[id^='post_'] 패턴으로 재검색...")
            all_post_elements = self.driver.find_elements(By.CSS_SELECTOR, ".memo-box[id^='post_']")
            print(f"📋 .memo-box[id^='post_'] 패턴 요소 발견: {len(all_post_elements)}개")
            
            if not all_post_elements:
                print("🔄 [id^='post_'] 패턴으로 최종 검색...")
                all_post_elements = self.driver.find_elements(By.CSS_SELECTOR, "[id^='post_']")
                print(f"📋 [id^='post_'] 패턴 요소 발견: {len(all_post_elements)}개")
            
            if all_post_elements:
                post_numbers = []
                for i, element in enumerate(all_post_elements):
                    post_id = element.get_attribute("id")
                    if i < 5:  # 처음 5개만 로그
                        print(f"🔍 [{i+1}] ID: {post_id}")
                    
                    if post_id and post_id.startswith("post_"):
                        try:
                            number = int(post_id.replace("post_", ""))
                            post_numbers.append(number)
                        except:
                            continue
                
                if post_numbers:
                    # DOM 순서상 첫 번째가 최신일 가능성이 높음
                    first_element_id = all_post_elements[0].get_attribute("id")
                    if first_element_id and first_element_id.startswith("post_"):
                        try:
                            latest_number = int(first_element_id.replace("post_", ""))
                            print(f"✅ 첫 번째 요소에서 최신 번호: post_{latest_number}")
                            return latest_number
                        except:
                            pass
                    
                    # 백업: 최대값 사용
                    latest_number = max(post_numbers)
                    print(f"✅ post_ 패턴에서 최대 번호: post_{latest_number}")
                    return latest_number
            
            print("🔄 다른 방법으로 게시글 번호 검색 중...")
            
            # 방법 2: 네이버 카페 게시글 링크에서 번호 추출
            link_patterns = [
                "a[href*='articleid=']",       # articleid 파라미터가 있는 링크
                "a[href*='aid=']",             # aid 파라미터가 있는 링크  
                "a[href*='MemoView']",         # MemoView 링크
                "a[onclick*='articleid']",      # onclick에 articleid가 있는 링크
                "td[id^='td_'] a",             # td_숫자 ID 내부의 링크
                "tr[id^='tr_'] a"              # tr_숫자 ID 내부의 링크
            ]
            
            article_numbers = []
            
            for pattern in link_patterns:
                try:
                    links = self.driver.find_elements(By.CSS_SELECTOR, pattern)
                    print(f"📋 '{pattern}' 패턴 링크: {len(links)}개")
                    
                    for i, link in enumerate(links[:10]):  # 처음 10개만 확인
                        try:
                            href = link.get_attribute("href")
                            onclick = link.get_attribute("onclick")
                            link_text = link.text.strip()
                            
                            if i < 3:  # 처음 3개는 상세 로그
                                print(f"🔍 링크 {i+1}: {link_text[:30]} - {href}")
                            
                            # href에서 게시글 번호 추출
                            if href:
                                import re
                                # articleid 파라미터
                                match = re.search(r'articleid=(\d+)', href)
                                if match:
                                    number = int(match.group(1))
                                    article_numbers.append(number)
                                    continue
                                
                                # aid 파라미터
                                match = re.search(r'aid=(\d+)', href)
                                if match:
                                    number = int(match.group(1))
                                    article_numbers.append(number)
                                    continue
                            
                            # onclick에서 게시글 번호 추출
                            if onclick:
                                match = re.search(r'articleid[=\s]*(\d+)', onclick)
                                if match:
                                    number = int(match.group(1))
                                    article_numbers.append(number)
                                    continue
                                    
                        except Exception as link_error:
                            continue
                            
                except Exception as pattern_error:
                    print(f"⚠️ 패턴 '{pattern}' 검색 실패: {pattern_error}")
                    continue
            
            if article_numbers:
                latest_number = max(article_numbers)
                print(f"✅ 링크 분석에서 최신 번호: {latest_number}")
                return latest_number
            
            # 방법 3: 페이지 소스 전체에서 숫자 패턴 검색
            print("🔄 페이지 소스에서 게시글 번호 검색...")
            try:
                page_source = self.driver.page_source
                import re
                
                # 다양한 패턴으로 게시글 번호 검색 (memo-box 우선)
                patterns = [
                    r'<p[^>]*id="post_(\d+)"[^>]*class="memo-box"',  # 정확한 p 태그 패턴
                    r'<p[^>]*class="memo-box"[^>]*id="post_(\d+)"',  # 정확한 p 태그 패턴 (순서 바뀜)
                    r'class="memo-box"[^>]*id="post_(\d+)"',  # memo-box 클래스의 post_ ID
                    r'id="post_(\d+)"[^>]*class="memo-box"',  # post_ ID의 memo-box 클래스
                    r'post_(\d+)',           # 일반 post_숫자
                    r'articleid=(\d+)',      # articleid=숫자
                    r'aid=(\d+)',            # aid=숫자
                    r'memo-box[^>]*>.*?(\d{5,})',  # memo-box 근처의 5자리 이상 숫자
                    r'id="td_(\d+)"',        # td_숫자 ID
                    r'id="tr_(\d+)"'         # tr_숫자 ID
                ]
                
                all_numbers = []
                for pattern in patterns:
                    matches = re.findall(pattern, page_source, re.IGNORECASE)
                    if matches:
                        numbers = [int(match) for match in matches if match.isdigit() and len(match) >= 4]
                        all_numbers.extend(numbers)
                        print(f"🔍 패턴 '{pattern}': {len(numbers)}개 번호 발견")
                
                if all_numbers:
                    # 최신 번호들 중에서 합리적인 범위 선택 (최신 10개 정도)
                    unique_numbers = sorted(set(all_numbers), reverse=True)[:10]
                    latest_number = max(unique_numbers)
                    print(f"✅ 페이지 소스 분석 결과 최신 번호: {latest_number}")
                    print(f"🔍 발견된 최신 10개 번호: {unique_numbers}")
                    return latest_number
                    
            except Exception as source_error:
                print(f"⚠️ 페이지 소스 검색 실패: {source_error}")
            
            # 방법 4: 사용자 입력으로 직접 설정
            print("❌ 자동으로 게시글 번호를 찾을 수 없습니다.")
            print("💡 수동으로 게시글 번호를 확인해서 입력해주세요.")
            
            try:
                manual_number = input("현재 최신 게시글 번호를 입력하세요 (예: 41787): ").strip()
                if manual_number.isdigit():
                    number = int(manual_number)
                    print(f"✅ 수동 입력된 게시글 번호: {number}")
                    return number
                else:
                    print("❌ 잘못된 번호 형식입니다.")
                    
            except KeyboardInterrupt:
                print("\n⏹️ 사용자 취소")
                return 0
            except Exception as input_error:
                print(f"⚠️ 입력 처리 오류: {input_error}")
                
            return 0
                
        except Exception as e:
            print(f"❌ 최신 게시글 번호 가져오기 실패: {e}")
            return 0
    
    def check_keyword_in_specific_post(self, post_number):
        """특정 게시글 번호에서 키워드 검색"""
        try:
            print(f"🔍 게시글 번호 {post_number}에서 키워드 검색 중...")
            
            # memo-box 클래스를 가진 게시글 요소 패턴 시도 (memo-box 우선)
            post_element = None
            post_selectors = [
                # memo-box 클래스 p 태그 패턴 (최우선)
                f"p.memo-box#post_{post_number}",
                f"p.memo-box[id='post_{post_number}']",
                f".memo-box#post_{post_number}",
                
                # 일반 p 태그 post_ ID 패턴
                f"p#post_{post_number}",
                f"p[id='post_{post_number}']",
                
                # 백업 패턴
                f"#post_{post_number}",
                f"[id='post_{post_number}']",
                
                # 게시글 번호가 다른 속성에 있을 경우
                f"[data-post='{post_number}']",
                f"[data-articleid='{post_number}']",
                f"[articleid='{post_number}']",
                
                # 테이블 행 기반 (tr_숫자, td_숫자)
                f"#tr_{post_number}",
                f"#td_{post_number}",
                f"tr[id='tr_{post_number}']",
                f"td[id='td_{post_number}']",
                
                # 링크에 게시글 번호가 있는 경우
                f"a[href*='articleid={post_number}']",
                f"a[href*='aid={post_number}']"
            ]
            
            for selector in post_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        post_element = elements[0]
                        print(f"✅ '{selector}' 선택자로 게시글 {post_number} 요소 발견")
                        break
                except Exception as selector_error:
                    continue
            
            # 게시글 요소를 찾지 못한 경우 링크 기반으로 게시글 찾기
            if not post_element:
                print(f"🔄 링크 기반으로 게시글 {post_number} 검색...")
                
                try:
                    # articleid 또는 aid 파라미터가 있는 링크 찾기
                    link_patterns = [
                        f"a[href*='articleid={post_number}']",
                        f"a[href*='aid={post_number}']",
                        f"a[onclick*='articleid={post_number}']",
                        f"a[onclick*='{post_number}']"
                    ]
                    
                    target_link = None
                    for pattern in link_patterns:
                        try:
                            links = self.driver.find_elements(By.CSS_SELECTOR, pattern)
                            if links:
                                target_link = links[0]
                                print(f"✅ '{pattern}' 패턴으로 게시글 {post_number} 링크 발견")
                                break
                        except:
                            continue
                    
                    if target_link:
                        # 링크의 부모 요소나 같은 행의 내용을 게시글로 간주
                        try:
                            # 부모 tr 요소 찾기 (테이블 행)
                            parent_tr = target_link.find_element(By.XPATH, "./ancestor::tr[1]")
                            post_element = parent_tr
                            print(f"✅ 링크의 부모 tr 요소를 게시글로 사용")
                        except:
                            try:
                                # 부모 요소 찾기
                                parent_element = target_link.find_element(By.XPATH, "./..")
                                post_element = parent_element  
                                print(f"✅ 링크의 부모 요소를 게시글로 사용")
                            except:
                                post_element = target_link
                                print(f"⚠️ 링크 자체를 게시글로 사용")
                                
                except Exception as link_search_error:
                    print(f"⚠️ 링크 기반 검색 실패: {link_search_error}")
            
            # 그래도 찾지 못한 경우 페이지 소스에서 직접 검색
            if not post_element:
                print(f"⚠️ 게시글 {post_number} 요소를 찾을 수 없습니다. 페이지 소스에서 검색...")
                return self.search_in_page_source_for_post(post_number)
            
            # 게시글 내용 추출
            post_text = ""
            try:
                # 메인 텍스트 추출
                post_text = post_element.text.strip()
                
                # 추가 정보 추출 (하위 요소들)
                try:
                    sub_elements = post_element.find_elements(By.XPATH, ".//*")
                    additional_texts = []
                    
                    for elem in sub_elements:
                        try:
                            elem_text = elem.text.strip()
                            if elem_text and elem_text not in additional_texts and elem_text not in post_text:
                                additional_texts.append(elem_text)
                        except:
                            continue
                    
                    # 모든 텍스트 결합
                    if additional_texts:
                        all_text = " ".join([post_text] + additional_texts).strip()
                        post_text = all_text
                        
                except Exception as sub_error:
                    print(f"⚠️ 하위 요소 텍스트 추출 중 오류: {sub_error}")
                
                print(f"📝 추출된 내용: {post_text[:200]}{'...' if len(post_text) > 200 else ''}")
                
                # 내용이 너무 적으면 경고
                if len(post_text.strip()) < 10:
                    print(f"⚠️ 추출된 텍스트가 너무 짧습니다: '{post_text}'")
                
            except Exception as text_error:
                print(f"⚠️ 게시글 텍스트 추출 실패: {text_error}")
                # 텍스트 추출이 실패해도 페이지 소스 검색으로 백업
                return self.search_in_page_source_for_post(post_number)
            
            # 키워드 검색
            found_posts = []
            search_text = post_text.lower()
            
            for keyword in self.config['keywords']:
                keyword_lower = keyword.lower()
                
                if keyword_lower in search_text:
                    print(f"🎯 키워드 '{keyword}' 발견! 게시글 {post_number}")
                    
                    # 키워드 주변 컨텍스트 추출
                    try:
                        keyword_index = search_text.find(keyword_lower)
                        start = max(0, keyword_index - 50)
                        end = min(len(search_text), keyword_index + 50)
                        context = post_text[start:end]
                        print(f"🔍 컨텍스트: ...{context}...")
                    except:
                        context = post_text[:100] + '...'
                    
                    post_info = {
                        'title': f"게시글 {post_number} - {keyword} 발견",
                        'link': f"{self.driver.current_url}#{post_number}",
                        'keyword': keyword,
                        'post_id': str(post_number),
                        'content': post_text[:500] + '...' if len(post_text) > 500 else post_text,
                        'found_location': "게시글내용"
                    }
                    
                    found_posts.append(post_info)
                    break  # 하나의 키워드만 찾으면 충분
            
            if not found_posts:
                print(f"✅ 게시글 {post_number}에서 키워드 없음")
            
            return found_posts
            
        except Exception as e:
            print(f"❌ 게시글 {post_number} 키워드 검색 중 오류: {e}")
            # 오류가 발생해도 페이지 소스 검색으로 백업 시도
            return self.search_in_page_source_for_post(post_number)
    
    def search_in_page_source_for_post(self, post_number):
        """페이지 소스에서 특정 게시글 번호 주변 키워드 검색"""
        try:
            print(f"🔍 페이지 소스에서 post_{post_number} 주변 키워드 검색...")
            
            page_source = self.driver.page_source
            
            # post_숫자 주변 텍스트 추출
            import re
            pattern = rf'.{{0,500}}post_{post_number}.{{0,500}}'
            matches = re.findall(pattern, page_source, re.IGNORECASE | re.DOTALL)
            
            found_posts = []
            
            for match in matches:
                # HTML 태그 제거
                clean_text = re.sub(r'<[^>]+>', ' ', match)
                clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                
                if len(clean_text) < 20:  # 너무 짧은 텍스트는 제외
                    continue
                
                print(f"📝 post_{post_number} 주변 텍스트: {clean_text[:300]}...")
                
                # 키워드 검색
                search_text = clean_text.lower()
                
                for keyword in self.config['keywords']:
                    keyword_lower = keyword.lower()
                    
                    if keyword_lower in search_text:
                        print(f"🎯 페이지 소스에서 키워드 '{keyword}' 발견! (post_{post_number} 주변)")
                        
                        post_info = {
                            'title': f"페이지소스 post_{post_number} - {keyword} 발견",
                            'link': f"{self.driver.current_url}#post_{post_number}",
                            'keyword': keyword,
                            'post_id': f"source_post_{post_number}",
                            'content': clean_text[:500] + '...' if len(clean_text) > 500 else clean_text,
                            'found_location': "페이지소스"
                        }
                        
                        found_posts.append(post_info)
                        return found_posts  # 첫 번째 발견으로 충분
                
                break  # 첫 번째 매치만 처리
            
            return found_posts
            
        except Exception as e:
            print(f"❌ 페이지 소스 검색 실패: {e}")
            return []
    
    def check_keywords_in_posts(self):
        """게시글에서 키워드 확인"""
        try:
            found_posts = []
            
            # iframe 안의 콘텐츠에 접근하기 위해 프레임 전환 확인
            try:
                # 현재 프레임 상태 확인
                current_url = self.driver.current_url
                print(f"🔍 현재 URL: {current_url}")
                
                # 메인 프레임에 있다면 cafe_main 프레임으로 전환
                if "cafe.naver.com" in current_url and "MemoList" not in current_url:
                    print("🔄 cafe_main 프레임으로 전환 시도...")
                    try:
                        cafe_frame = WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.ID, "cafe_main"))
                        )
                        self.driver.switch_to.frame(cafe_frame)
                        print("✅ cafe_main 프레임 전환 완료")
                        time.sleep(2)
                    except:
                        print("⚠️ cafe_main 프레임 전환 실패, 현재 프레임에서 진행")
                
                # 프레임 전환 후 URL 다시 확인
                try:
                    frame_url = self.driver.execute_script("return window.location.href;")
                    print(f"🔍 프레임 내부 URL: {frame_url}")
                except:
                    print("⚠️ 프레임 내부 URL 확인 실패")
                
            except Exception as frame_error:
                print(f"⚠️ 프레임 처리 중 오류: {frame_error}")
            
            # 페이지 소스에서 루키나 키워드 직접 검색 (디버깅용)
            try:
                page_source = self.driver.page_source
                if "루키나" in page_source.lower():
                    print("🎯 페이지 소스에서 '루키나' 키워드 발견!")
                    # 키워드 주변 텍스트 추출
                    import re
                    pattern = r'.{0,50}루키나.{0,50}'
                    matches = re.findall(pattern, page_source, re.IGNORECASE)
                    for i, match in enumerate(matches[:3]):  # 처음 3개만 출력
                        print(f"🔍 매치 {i+1}: {match}")
                else:
                    print("⚠️ 페이지 소스에서 '루키나' 키워드를 찾을 수 없음")
            except Exception as source_error:
                print(f"⚠️ 페이지 소스 검색 중 오류: {source_error}")
            
            # 여러 게시글 목록 형태 시도 (네이버 카페 전용 셀렉터 추가)
            selectors_to_try = [
                # 네이버 카페 특화 셀렉터
                "table.board_list tr",           # 네이버 카페 게시판 테이블
                "table[summary*='게시판'] tr",   # 게시판 요약이 있는 테이블
                "tbody tr",                      # 일반 테이블 본문
                "tr[align='center']",           # 가운데 정렬 행들
                "tr.list",                      # list 클래스 행들
                
                # 일반적인 게시판 구조
                "table.board-list tr",
                "div.article-board", 
                "tr.board-list",
                "div.list-item",
                
                # 테이블 기반 구조
                "table tr",
                "tbody tr",
                
                # 리스트 기반 구조  
                "ul li",
                "div[class*='list'] div[class*='item']",
                "div[class*='article']",
                
                # 네이버 특화 구조
                "div[class*='cafe'] tr",
                "table[class*='list'] tr"
            ]
            
            post_elements = []
            used_selector = ""
            
            for selector in selectors_to_try:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if len(elements) > 1:  # 최소 2개 이상의 요소가 있어야 게시글 목록으로 판단
                        post_elements = elements
                        used_selector = selector
                        print(f"✅ '{selector}' 선택자로 {len(elements)}개 게시글 발견")
                        break
                except:
                    continue
            
            if not post_elements:
                print("⚠️ 게시글 목록을 찾을 수 없습니다.")
                return []
            
            print(f"📋 총 {len(post_elements)}개 게시글 확인 중...")
            
            # 최근 15개 게시글만 확인 (헤더 제외)
            check_elements = post_elements[1:16] if len(post_elements) > 15 else post_elements[1:]
            
            for i, post in enumerate(check_elements):
                try:
                    # 다양한 방법으로 게시글 제목과 링크 추출 시도
                    title_element = None
                    title = ""
                    link = ""
                    
                    # 방법 1: 일반적인 링크 태그
                    link_selectors = ["a", "a.article", "td.title a", "div.title a", "span.title a"]
                    
                    for link_selector in link_selectors:
                        try:
                            links = post.find_elements(By.CSS_SELECTOR, link_selector)
                            for link_elem in links:
                                href = link_elem.get_attribute("href")
                                text = link_elem.text.strip()
                                
                                # 실제 게시글 링크인지 확인 (articleid 또는 aid 포함)
                                if href and text and ("articleid=" in href or "aid=" in href):
                                    title_element = link_elem
                                    title = text
                                    link = href
                                    break
                            
                            if title_element:
                                break
                                
                        except:
                            continue
                    
                    # 제목이 없으면 텍스트 기반으로 추출 시도
                    if not title:
                        try:
                            all_text = post.text.strip()
                            if all_text and len(all_text) > 3:
                                # 첫 번째 줄을 제목으로 추정
                                lines = all_text.split('\n')
                                potential_title = lines[0].strip() if lines else ""
                                
                                # 제목으로 보이는 텍스트 필터링
                                if len(potential_title) > 3 and not potential_title.isdigit():
                                    title = potential_title
                                    # 링크는 post 엘리먼트의 onclick 등에서 추출 시도
                                    onclick = post.get_attribute("onclick")
                                    if onclick and "articleid" in onclick:
                                        link = f"{self.config['cafe_url']}#{onclick}"
                                    else:
                                        link = f"{self.config['cafe_url']}/board_{i}"
                        except:
                            continue
                    
                    if not title:
                        continue
                    
                    # 게시글 ID 생성 (중복 확인용)
                    post_id = ""
                    if "articleid=" in link:
                        post_id_match = re.search(r'articleid=(\d+)', link)
                        post_id = post_id_match.group(1) if post_id_match else f"post_{i}"
                    elif "aid=" in link:
                        post_id_match = re.search(r'aid=(\d+)', link)  
                        post_id = post_id_match.group(1) if post_id_match else f"post_{i}"
                    else:
                        post_id = f"post_{hash(title)}_{i}"
                    
                    # 이미 확인한 게시글인지 체크
                    if post_id in self.monitored_posts:
                        continue
                    
                    print(f"🔍 [{i+1}] {title[:50]}{'...' if len(title) > 50 else ''}")
                    
                    # 키워드 확인 (제목뿐만 아니라 전체 텍스트에서도 검색)
                    all_text = ""
                    try:
                        # 게시글의 모든 텍스트 추출 (더 상세하게)
                        all_text = post.text.strip()
                        
                        # 추가로 숨겨진 텍스트나 속성에서도 텍스트 추출 시도
                        additional_texts = []
                        
                        # 모든 하위 요소의 텍스트 수집
                        all_elements = post.find_elements(By.XPATH, ".//*")
                        for elem in all_elements:
                            try:
                                elem_text = elem.text.strip()
                                if elem_text and elem_text not in additional_texts:
                                    additional_texts.append(elem_text)
                            except:
                                continue
                        
                        # title 속성이나 alt 속성에서도 텍스트 추출
                        try:
                            title_attr = post.get_attribute("title")
                            if title_attr:
                                additional_texts.append(title_attr.strip())
                        except:
                            pass
                        
                        # 모든 텍스트 결합
                        full_text = " ".join([all_text] + additional_texts)
                        all_text = full_text.strip()
                        
                    except Exception as text_error:
                        print(f"⚠️ 텍스트 추출 중 오류: {text_error}")
                        all_text = ""
                    
                    # 검색할 텍스트 결합 (제목 + 전체 텍스트)
                    search_text = f"{title} {all_text}".lower().strip()
                    
                    # 디버깅: 검색 텍스트 일부 출력 (루키나 관련 디버깅)
                    if "루키나" in search_text or "rukina" in search_text:
                        print(f"🔍 루키나 관련 텍스트 발견: {search_text[:200]}...")
                    
                    for keyword in self.config['keywords']:
                        keyword_lower = keyword.lower()
                        
                        # 키워드 검색 (여러 방법으로)
                        keyword_found = False
                        found_location = ""
                        
                        # 1. 전체 검색 텍스트에서 검색
                        if keyword_lower in search_text:
                            keyword_found = True
                            
                            # 어느 부분에서 발견되었는지 확인
                            if keyword_lower in title.lower():
                                found_location = "제목"
                            else:
                                found_location = "내용"
                        
                        # 2. 개별적으로도 검색 (공백이나 특수문자 문제 대응)
                        if not keyword_found:
                            # 제목에서 검색
                            if title and keyword_lower in title.lower():
                                keyword_found = True
                                found_location = "제목"
                            # 전체 텍스트에서 검색
                            elif all_text and keyword_lower in all_text.lower():
                                keyword_found = True
                                found_location = "내용"
                        
                        # 3. 단어 경계를 무시한 부분 문자열 검색
                        if not keyword_found:
                            # 공백과 특수문자 제거 후 검색
                            clean_search_text = re.sub(r'[^\w가-힣]', '', search_text)
                            clean_keyword = re.sub(r'[^\w가-힣]', '', keyword_lower)
                            
                            if clean_keyword in clean_search_text:
                                keyword_found = True
                                found_location = "내용(정제된텍스트)"
                        
                        if keyword_found:
                            found_posts.append({
                                'title': title if title else all_text[:100] + '...',
                                'link': link,
                                'keyword': keyword,
                                'post_id': post_id,
                                'found_location': found_location,
                                'search_preview': search_text[:300] + '...' if len(search_text) > 300 else search_text
                            })
                            self.monitored_posts.add(post_id)
                            
                            # 키워드가 어디서 발견되었는지 상세 표시
                            print(f"🎯 키워드 '{keyword}' {found_location}에서 발견!")
                            print(f"📋 게시글: {title if title else '제목없음'}")
                            if found_location == "내용":
                                # 키워드 주변 텍스트 표시 (컨텍스트)
                                try:
                                    keyword_index = search_text.lower().find(keyword_lower)
                                    if keyword_index >= 0:
                                        start = max(0, keyword_index - 50)
                                        end = min(len(search_text), keyword_index + 50)
                                        context = search_text[start:end]
                                        print(f"🔍 컨텍스트: ...{context}...")
                                except:
                                    pass
                            break
                            
                except Exception as e:
                    print(f"⚠️ 게시글 {i+1} 처리 중 오류: {e}")
                    continue
            
            # 게시글 목록에서 키워드를 찾지 못한 경우, 페이지 소스 전체에서 직접 검색
            if not found_posts:
                print("🔍 게시글 목록에서 키워드를 찾지 못했습니다. 페이지 소스 전체 검색을 시도합니다...")
                
                try:
                    page_source = self.driver.page_source
                    
                    for keyword in self.config['keywords']:
                        keyword_lower = keyword.lower()
                        
                        if keyword_lower in page_source.lower():
                            print(f"🎯 페이지 소스에서 키워드 '{keyword}' 발견!")
                            
                            # 키워드 주변 컨텍스트 추출
                            import re
                            pattern = rf'.{{0,100}}{re.escape(keyword_lower)}.{{0,100}}'
                            matches = re.findall(pattern, page_source.lower(), re.IGNORECASE)
                            
                            for i, match in enumerate(matches[:2]):  # 처음 2개만 처리
                                # HTML 태그 제거
                                clean_match = re.sub(r'<[^>]+>', '', match)
                                clean_match = re.sub(r'\s+', ' ', clean_match).strip()
                                
                                if len(clean_match) > 10:  # 의미있는 텍스트만
                                    print(f"🔍 컨텍스트 {i+1}: {clean_match}")
                                    
                                    # 고유 ID 생성
                                    post_id = f"source_{keyword}_{hash(clean_match)}"
                                    
                                    if post_id not in self.monitored_posts:
                                        found_posts.append({
                                            'title': f"페이지 소스에서 발견: {clean_match[:100]}...",
                                            'link': self.driver.current_url,
                                            'keyword': keyword,
                                            'post_id': post_id,
                                            'found_location': "페이지소스",
                                            'search_preview': clean_match
                                        })
                                        self.monitored_posts.add(post_id)
                                        print(f"🚨 페이지 소스에서 키워드 '{keyword}' 감지됨!")
                                        break
                            
                            if found_posts:
                                break
                                
                except Exception as source_search_error:
                    print(f"⚠️ 페이지 소스 검색 중 오류: {source_search_error}")
            
            return found_posts
            
        except Exception as e:
            print(f"❌ 키워드 확인 중 오류: {e}")
            # 오류 발생시에도 페이지 소스 검색 시도
            try:
                print("🔄 오류 발생으로 인한 긴급 페이지 소스 검색...")
                page_source = self.driver.page_source
                emergency_posts = []
                
                for keyword in self.config['keywords']:
                    if keyword.lower() in page_source.lower():
                        print(f"🚨 긴급 검색: '{keyword}' 키워드 발견!")
                        emergency_posts.append({
                            'title': f"긴급검색 - {keyword} 키워드 감지",
                            'link': self.driver.current_url,
                            'keyword': keyword,
                            'post_id': f"emergency_{keyword}_{hash(page_source[:1000])}",
                            'found_location': "긴급검색",
                            'search_preview': "페이지 오류로 인한 긴급 검색 결과"
                        })
                        break
                
                return emergency_posts
                
            except:
                return []
    
    def send_telegram_alert(self, post_info):
        """텔레그램 알람 전송"""
        try:
            if not self.config['telegram_bot_token'] or not self.config['telegram_chat_id']:
                print("⚠️ 텔레그램 설정이 없습니다. 콘솔에만 알람 표시됩니다.")
                return False
            
            message = f"""
🚨 키워드 알람! 🚨

📋 제목: {post_info['title']}
🔍 키워드: {post_info['keyword']}
🔗 링크: {post_info['link']}
⏰ 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            
            url = f"https://api.telegram.org/bot{self.config['telegram_bot_token']}/sendMessage"
            data = {
                'chat_id': self.config['telegram_chat_id'],
                'text': message,
                'parse_mode': 'HTML'
            }
            
            response = requests.post(url, data=data, timeout=10)
            
            if response.status_code == 200:
                print("✅ 텔레그램 알람 전송 완료!")
                return True
            else:
                print(f"❌ 텔레그램 전송 실패: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ 텔레그램 알람 전송 중 오류: {e}")
            return False
    
    def monitor_loop(self):
        """게시글 번호 기반 모니터링 루프"""
        print("🔄 게시글 번호 기반 모니터링 시작...")
        print(f"🎯 키워드: {', '.join(self.config['keywords'])}")
        print(f"⏱️ 모니터링 간격: 20-30초 랜덤")
        print("⏹️ 중지하려면 Ctrl+C를 누르세요.")
        
        # 초기 최신 게시글 번호 설정
        print("\n🔍 초기 최신 게시글 번호 확인 중...")
        self.last_post_number = self.get_latest_post_number()
        
        if self.last_post_number == 0:
            print("❌ 초기 게시글 번호를 가져올 수 없습니다.")
            print("💡 수동으로 게시판을 확인하고 다시 시도해주세요.")
            return
        
        print(f"📌 초기 설정: 마지막 확인 게시글 번호 = post_{self.last_post_number}")
        print(f"🎯 다음 모니터링에서는 post_{self.last_post_number + 1} 이상의 새 글을 확인합니다.")
        
        cycle_count = 0
        error_count = 0
        max_errors = 5
        
        try:
            while True:
                # 수면 시간 체크
                if self.is_sleep_time():
                    self.wait_until_wake_time()
                    # 수면에서 깨어난 후 브라우저 상태 확인
                    try:
                        self.driver.refresh()
                        time.sleep(3)
                    except:
                        print("⚠️ 수면 모드 후 브라우저 상태 확인 필요")
                
                cycle_count += 1
                current_time = datetime.now().strftime('%H:%M:%S')
                print(f"\n🔍 [{cycle_count}회차] {current_time} - 새 게시글 확인 중...")
                
                monitoring_success = False
                
                try:
                    # 페이지 새로고침
                    self.driver.refresh()
                    time.sleep(3)
                    
                    # 현재 최신 게시글 번호 확인
                    current_latest_number = self.get_latest_post_number()
                    
                    if current_latest_number == 0:
                        print("⚠️ 현재 최신 게시글 번호를 가져올 수 없습니다.")
                        error_count += 1
                        continue
                    
                    print(f"📊 비교: 이전 최신 post_{self.last_post_number} → 현재 최신 post_{current_latest_number}")
                    
                    # 새로운 게시글이 있는지 확인
                    if current_latest_number > self.last_post_number:
                        new_post_count = current_latest_number - self.last_post_number
                        print(f"🆕 새로운 게시글 {new_post_count}개 발견! (post_{self.last_post_number + 1} ~ post_{current_latest_number})")
                        
                        # 새로운 게시글들에서 키워드 검색
                        found_any = False
                        
                        for post_num in range(self.last_post_number + 1, current_latest_number + 1):
                            print(f"\n🔍 post_{post_num} 검사 중...")
                            
                            # 특정 게시글에서 키워드 검색
                            found_posts = self.check_keyword_in_specific_post(post_num)
                            
                            # 발견된 키워드 처리
                            if found_posts:
                                found_any = True
                                for post in found_posts:
                                    print(f"\n🚨 키워드 알람! 🚨")
                                    print(f"📋 게시글: {post['title']}")
                                    print(f"🎯 키워드: {post['keyword']}")
                                    print(f"🔗 링크: {post['link']}")
                                    print(f"📝 내용: {post.get('content', 'N/A')[:200]}...")
                                    
                                    # 텔레그램 알람 전송
                                    self.send_telegram_alert(post)
                                    
                                    # 모니터링한 게시글로 표시
                                    self.monitored_posts.add(post['post_id'])
                        
                        if not found_any:
                            print(f"✅ 새 게시글 {new_post_count}개에서 키워드 없음")
                        
                        # 마지막 확인 게시글 번호 업데이트
                        self.last_post_number = current_latest_number
                        print(f"📌 마지막 확인 번호 업데이트: post_{self.last_post_number}")
                        
                    else:
                        print("⚠️ 새로운 게시글이 없지만, 현재 발견된 모든 게시글에서 키워드 검색 실행")
                        
                        # 발견된 모든 게시글에서 키워드 검색
                        all_post_elements = self.driver.find_elements(By.CSS_SELECTOR, "p.memo-box[id^='post_']")
                        
                        if all_post_elements:
                            print(f"🔍 발견된 {len(all_post_elements)}개 게시글에서 키워드 검색 중...")
                            
                            found_any = False
                            
                            for i, element in enumerate(all_post_elements):
                                try:
                                    post_id = element.get_attribute("id")
                                    if post_id and post_id.startswith("post_"):
                                        post_number = int(post_id.replace("post_", ""))
                                        
                                        # 이미 확인한 게시글인지 체크
                                        if str(post_number) in self.monitored_posts:
                                            continue
                                        
                                        print(f"🔍 [{i+1}] post_{post_number} 키워드 검색...")
                                        
                                        # 특정 게시글에서 키워드 검색
                                        found_posts = self.check_keyword_in_specific_post(post_number)
                                        
                                        # 발견된 키워드 처리
                                        if found_posts:
                                            found_any = True
                                            for post in found_posts:
                                                print(f"\n🚨 키워드 알람! 🚨")
                                                print(f"📋 게시글: {post['title']}")
                                                print(f"🎯 키워드: {post['keyword']}")
                                                print(f"🔗 링크: {post['link']}")
                                                print(f"📝 내용: {post.get('content', 'N/A')[:200]}...")
                                                
                                                # 텔레그램 알람 전송
                                                self.send_telegram_alert(post)
                                                
                                                # 모니터링한 게시글로 표시
                                                self.monitored_posts.add(str(post_number))
                                        else:
                                            print(f"✅ post_{post_number}: 키워드 없음")
                                            # 키워드가 없어도 확인한 게시글로 표시
                                            self.monitored_posts.add(str(post_number))
                                            
                                except Exception as e:
                                    print(f"⚠️ 게시글 처리 중 오류: {e}")
                                    continue
                            
                            if not found_any:
                                print("✅ 모든 게시글에서 키워드 없음")
                        else:
                            print("⚠️ 게시글 요소를 다시 찾을 수 없습니다.")
                    
                    # 성공적으로 모니터링 완료
                    monitoring_success = True
                    error_count = 0  # 에러 카운트 리셋
                    
                except Exception as e:
                    error_count += 1
                    print(f"⚠️ 모니터링 오류 {error_count}/{max_errors}: {e}")
                    monitoring_success = False
                    
                    if error_count >= max_errors:
                        print(f"❌ 연속 {max_errors}회 오류 발생")
                        print("🔧 브라우저 상태를 확인하고 문제를 해결하세요.")
                        
                        # 사용자 선택지 제공
                        print("선택 옵션:")
                        print("y: 모니터링 계속")
                        print("r: 재연결 및 게시글 번호 재설정")  
                        print("m: 수동 확인 모드")
                        print("q: 모니터링 종료")
                        
                        choice = input("선택하세요 (y/r/m/q): ").strip().lower()
                        
                        if choice == 'y':
                            error_count = 0
                            print("🔄 모니터링을 계속합니다...")
                            monitoring_success = True
                        elif choice == 'r':
                            print("🔄 재연결 및 게시글 번호 재설정...")
                            if self.reconnect():
                                # 게시글 번호 재설정
                                new_latest = self.get_latest_post_number()
                                if new_latest > 0:
                                    self.last_post_number = new_latest
                                    print(f"✅ 재연결 성공, 새 기준 번호: post_{self.last_post_number}")
                                    error_count = 0
                                    monitoring_success = True
                                else:
                                    print("❌ 게시글 번호 재설정 실패")
                            else:
                                print("❌ 재연결 실패")
                                manual_choice = input("수동으로 문제를 해결하시겠습니까? (y/n): ").strip().lower()
                                if manual_choice == 'y':
                                    input("문제 해결 후 엔터를 누르세요...")
                                    error_count = 0
                                    monitoring_success = True
                                else:
                                    print("🔚 모니터링을 종료합니다.")
                                    return
                        elif choice == 'm':
                            print("💡 브라우저에서 수동으로 문제를 확인하세요.")
                            input("문제 해결 후 엔터를 누르면 모니터링이 재개됩니다...")
                            error_count = 0
                            monitoring_success = True
                        else:
                            print("🔚 모니터링을 종료합니다.")
                            return
                    else:
                        print("🔄 자동 재연결을 시도합니다...")
                        try:
                            if self.reconnect():
                                print("✅ 자동 재연결 성공")
                                monitoring_success = True
                                error_count = 0
                            else:
                                print("❌ 자동 재연결 실패, 다음 주기에 재시도합니다.")
                        except Exception as reconnect_error:
                            print(f"⚠️ 재연결 중 오류: {reconnect_error}")
                
                # 모니터링 완료 후 대기 (성공/실패 관계없이 항상 실행)
                try:
                    if monitoring_success:
                        print(f"✅ {cycle_count}회차 모니터링 완료 (기준: post_{self.last_post_number})")
                    else:
                        print(f"⚠️ {cycle_count}회차 모니터링 오류 발생")
                    
                    # 랜덤 대기 (안전을 위해)
                    wait_time = random.randint(2, 4)
                    print(f"⏳ {wait_time}초 대기 중... (다음: {cycle_count + 1}회차)")
                    
                    # 대기 시간을 1초 단위로 나누어서 KeyboardInterrupt 반응성 향상
                    for i in range(wait_time):
                        time.sleep(1)
                        if i == 0:
                            continue  # 첫 초는 출력 생략
                        elif i % 3 == 0:  # 3초마다 출력
                            remaining = wait_time - i
                            print(f"⏳ {remaining}초 남음... (다음 확인: post_{self.last_post_number + 1} 이상)")
                    
                except KeyboardInterrupt:
                    raise  # KeyboardInterrupt 예외는 그대로 전달하여 루프 종료
                
        except KeyboardInterrupt:
            print(f"\n⏹️ 사용자에 의해 모니터링이 중지되었습니다.")
            print(f"📌 마지막 확인 게시글: post_{self.last_post_number}")
        except Exception as e:
            print(f"\n❌ 모니터링 중 심각한 오류: {e}")
            print("🔧 브라우저 상태를 확인하고 문제를 해결하세요.")
            print(f"📌 현재 기준 게시글: post_{self.last_post_number}")
            # 심각한 오류가 발생해도 강제 종료하지 않고 사용자에게 선택권 제공
            try:
                recovery_choice = input("모니터링을 다시 시작하시겠습니까? (y/n): ").strip().lower()
                if recovery_choice == 'y':
                    print("🔄 모니터링을 재시작합니다...")
                    self.monitor_loop()  # 재귀 호출로 모니터링 재시작
                else:
                    print("🔚 모니터링을 종료합니다.")
            except KeyboardInterrupt:
                print("\n⏹️ 사용자에 의해 모니터링이 중지되었습니다.")
    
    def reconnect(self):
        """재연결 시도"""
        try:
            print("🔄 재연결 시도 중...")
            self.driver.get(self.config['cafe_url'])
            time.sleep(3)
            self.access_cafe_board()
            print("✅ 재연결 완료")
            return True
        except:
            print("❌ 재연결 실패")
            return False
    
    def run(self):
        """메인 실행 함수"""
        print("=" * 60)
        print("🔍 네이버 카페 양도게시판 키워드 모니터링 시스템")
        print("=" * 60)
        
        # 설정 확인
        if not self.config['naver_id'] or not self.config['naver_password']:
            print("❌ 네이버 계정 정보가 설정되지 않았습니다.")
            print("📁 cafe_monitor_config.json 파일을 편집하여 계정 정보를 입력하세요.")
            input("아무 키나 누르면 종료됩니다...")
            return
        
        # 드라이버 설정
        if not self.setup_driver():
            print("\n💡 브라우저 설정에 실패했습니다.")
            print("🔧 Chrome 브라우저가 설치되어 있는지 확인하세요.")
            input("아무 키나 누르면 다시 시도합니다...")
            return
        
        try:
            # 네이버 로그인
            login_success = self.login_naver()
            if not login_success:
                print("\n💡 로그인에 실패했습니다.")
                print("🔧 네이버 계정 정보를 확인하거나 수동으로 로그인하세요.")
                
                retry = input("다시 시도하시겠습니까? (y/n) 또는 수동 로그인 후 계속하시겠습니까? (m): ").strip().lower()
                
                if retry == 'y':
                    # 재시도
                    if not self.login_naver():
                        print("❌ 로그인 재시도 실패")
                        input("수동으로 로그인 후 엔터를 누르세요...")
                elif retry == 'm':
                    print("💡 브라우저에서 수동으로 로그인하세요.")
                    input("로그인 완료 후 엔터를 누르세요...")
                else:
                    print("🔚 프로그램을 종료합니다.")
                    input("아무 키나 누르세요...")
                    return
            
            # 카페 게시판 접근
            board_success = self.access_cafe_board()
            if not board_success:
                print("\n💡 카페 접근에 실패했습니다.")
                print("🔧 카페 URL을 확인하거나 수동으로 양도게시판에 접근하세요.")
                
                retry = input("다시 시도하시겠습니까? (y/n) 또는 수동 접근 후 계속하시겠습니까? (m): ").strip().lower()
                
                if retry == 'y':
                    if not self.access_cafe_board():
                        print("❌ 카페 접근 재시도 실패")
                        input("수동으로 양도게시판에 접근 후 엔터를 누르세요...")
                elif retry == 'm':
                    print("💡 브라우저에서 수동으로 양도게시판에 접근하세요.")
                    input("양도게시판 접근 완료 후 엔터를 누르세요...")
                else:
                    print("🔚 프로그램을 종료합니다.")
                    self.wait_for_user_exit()
                    return
            
            # 모니터링 자동 시작
            print("\n🚀 모니터링을 자동으로 시작합니다!")
            print(f"🎯 모니터링 키워드: {', '.join(self.config['keywords'])}")
            print(f"⏱️ 확인 간격: 13-18초 랜덤")
            print("⏹️ 중지하려면 Ctrl+C를 누르세요.")
            
            # 3초 카운트다운 후 자동 시작
            for i in range(3, 0, -1):
                print(f"⏳ {i}초 후 모니터링 시작...")
                time.sleep(1)
            
            print("🔄 모니터링 시작!")
            
            # 모니터링 시작
            self.monitor_loop()
            
        except Exception as e:
            print(f"\n❌ 예상치 못한 오류가 발생했습니다: {e}")
            print("🔧 브라우저를 수동으로 확인하고 문제를 해결하세요.")
            self.wait_for_user_exit()
        
        finally:
            # 종료 전 사용자 확인
            self.wait_for_user_exit()
    
    def wait_for_user_exit(self):
        """사용자가 수동으로 종료할 때까지 대기"""
        print("\n" + "="*50)
        print("🔚 프로그램 종료 옵션")
        print("="*50)
        print("1. 브라우저를 열어두고 수동으로 작업하려면 'k'를 입력")
        print("2. 브라우저를 종료하고 프로그램을 끝내려면 'q'를 입력")
        print("3. 아무것도 입력하지 않으면 브라우저가 계속 실행됩니다")
        
        try:
            choice = input("\n선택하세요 (k/q/엔터): ").strip().lower()
            
            if choice == 'q':
                print("🔚 브라우저를 종료하고 프로그램을 종료합니다.")
                self.close()
            elif choice == 'k':
                print("🌐 브라우저를 열어두고 프로그램만 종료합니다.")
                print("💡 브라우저는 수동으로 닫아주세요.")
                # 브라우저를 닫지 않고 종료
                pass
            else:
                print("🌐 브라우저가 계속 실행 중입니다.")
                print("💡 작업 완료 후 수동으로 브라우저를 닫아주세요.")
                print("⏳ 10초 후 프로그램이 종료됩니다...")
                time.sleep(10)
                
        except KeyboardInterrupt:
            print("\n🔚 강제 종료되었습니다. 브라우저는 열려있을 수 있습니다.")
            pass
    
    def close(self):
        """브라우저 종료"""
        if self.driver:
            self.driver.quit()
            print("🔚 브라우저가 종료되었습니다.")


def main():
    """메인 함수"""
    monitor = NaverCafeMonitor()
    monitor.run()


if __name__ == "__main__":
    main()