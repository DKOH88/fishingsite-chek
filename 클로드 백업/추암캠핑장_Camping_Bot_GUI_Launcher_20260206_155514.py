import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import json
import os
import sys
import time
import requests
import email.utils
from io import BytesIO
from datetime import date, datetime, timedelta, timezone
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.service import Service
from PIL import Image, ImageOps 
import ddddocr 

# ============================================
# 📁 설정 파일 관리
# ============================================
CONFIG_FILE = 'camping_config.json'
DEFAULT_CONFIG = {
    "user_id": "",
    "user_pw": "",
    "year": "2025",
    "month": "07",
    "day": "15",
    "stay_period": "1001",
    "month_nav": "1",
    "target_time": "14:00:00",
    "lead_time": "0",  # [추가] 리드타임 (ms)
    "priorities": "D5, D4, D3, D2, D1",
    "test_mode": False,
    "stop_early": False
}

SITE_MAP = {
    'D5': '4132', 'D4': '4131', 'D3': '4130', 
    'D2': '4129', 'D1': '4128'
}

MASTER_PRIORITY_LIST = ['D5', 'D4', 'D3', 'D2', 'D1']

# [숙박 기간 매핑]
STAY_PERIOD_MAP = {
    "1박 2일": "1001",
    "2박 3일": "1002",
    "3박 4일": "1003"
}
STAY_PERIOD_MAP_REV = {v: k for k, v in STAY_PERIOD_MAP.items()}

# ============================================
# 🤖 봇 로직 클래스
# ============================================
class CampingBot:
    def __init__(self, log_callback):
        self.driver = None
        self.log = log_callback
        self.is_running = False
        self.server_offset = timedelta(seconds=0)
        self.target_url = "https://www.campingkorea.or.kr/user/reservation/BD_reservation.do"

    def sync_server_time(self):
        try:
            offsets = []
            self.log("⏱️ 서버 시간 동기화 중... (3회 측정)")
            for _ in range(3):
                start = datetime.now(timezone.utc)
                resp = requests.head(self.target_url, timeout=3)
                end = datetime.now(timezone.utc)
                
                server_dt_utc = email.utils.parsedate_to_datetime(resp.headers['Date'])
                rtt = (end - start).total_seconds()
                estimated_server_time = server_dt_utc + timedelta(seconds=rtt / 2)
                offset = estimated_server_time - end
                offsets.append(offset.total_seconds())
                time.sleep(0.05)
                
            avg_offset = sum(offsets) / len(offsets)
            self.server_offset = timedelta(seconds=avg_offset)
            self.log(f"✅ 시간 동기화 완료: 서버 시간은 로컬보다 {avg_offset:+.3f}초 차이가 납니다.")
        except Exception as e:
            self.log(f"⚠️ 시간 동기화 실패: {e}")

    def get_current_server_time(self):
        return (datetime.now(timezone.utc) + self.server_offset).astimezone(timezone(timedelta(hours=9)))
        
    def stop(self):
        self.is_running = False
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
        self.log("🛑 봇이 중지되었습니다.")

    def setup_driver(self):
        self.log("🚗 크롬 드라이버 실행 (Eager Mode)")
        chrome_service = Service()
        chrome_service.log_path = os.devnull
        chrome_options = webdriver.ChromeOptions()
        chrome_options.page_load_strategy = 'eager'
        
        prefs = {"credentials_enable_service": False, "profile.password_manager_enabled": False}
        chrome_options.add_experimental_option("prefs", prefs)
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_argument("--start-maximized")
        
        self.driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

    def clear_popups(self):
        try:
            try:
                self.driver.switch_to.alert.accept()
            except:
                pass
            
            main_handle = self.driver.current_window_handle
            if len(self.driver.window_handles) > 1:
                for handle in self.driver.window_handles:
                    if handle != main_handle:
                        self.driver.switch_to.window(handle)
                        self.driver.close()
                self.driver.switch_to.window(main_handle)
            
            popup_closers = ["//a[contains(text(), '닫기')]", "//button[contains(text(), '닫기')]"]
            for xpath in popup_closers:
                btns = self.driver.find_elements(By.XPATH, xpath)
                for btn in btns:
                    if btn.is_displayed():
                        btn.click()
        except:
            pass

    def run(self, config):
        self.is_running = True
        wait = None
        
        try:
            self.setup_driver()
            wait = WebDriverWait(self.driver, 60)
            
            # 1. 로그인
            self.log("🌐 로그인 페이지 접속 시도...")
            self.driver.get("https://www.campingkorea.or.kr/login/BD_loginForm.do")
            self.clear_popups()
            
            id_box = wait.until(EC.element_to_be_clickable((By.ID, "userId")))
            id_box.click()
            id_box.send_keys(config['user_id'])
            self.driver.find_element(By.ID, "userPassword").send_keys(config['user_pw'])
            self.driver.find_element(By.ID, "userPassword").send_keys(u'\ue007')
            self.log("🔐 로그인 엔터 입력! (2초 대기)")
            time.sleep(2)
            
            # 2. 예약 페이지 접속
            url = self.target_url
            self.sync_server_time()
            while self.is_running:
                try:
                    self.log("📄 예약 페이지 진입...")
                    self.driver.get(url)
                    try:
                        self.driver.switch_to.alert.accept()
                    except:
                        pass
                    
                    self.clear_popups()
                    
                    try:
                        WebDriverWait(self.driver, 0.5).until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), '대기')]")))
                        self.log("🚦 대기열 감지! 대기합니다...")
                        WebDriverWait(self.driver, 600).until(EC.invisibility_of_element_located((By.XPATH, "//*[contains(text(), '대기')]")))
                    except:
                        pass
                    
                    # [수정] 버튼이 보일 때까지 대기하되, Stale 에러 방지를 위해 presence로 체크
                    wait.until(EC.presence_of_element_located((By.XPATH, f"//a[contains(@onclick, '4000')]")))
                    self.log("✅ 페이지 로딩 성공")
                    break
                except Exception as e:
                    self.log("🔄 재접속 시도...")
                    time.sleep(1)

            if not self.is_running: return

            # 3. 설정 및 타임어택 대기 (수정된 부분)
            self.clear_popups()
            
            camp_click_success = False
            # [수정] 반복 횟수 증가 및 JS 실행 방식 도입
            for i in range(10):
                if not self.is_running: break
                try:
                    # 방법 1: JS 직접 호출 (Stale Error 방지, 속도 빠름)
                    self.driver.execute_script("chgTrrsrt('4000');")
                    camp_click_success = True
                    self.log(f"⚡ 캠핑장 선택(JS) 성공 - 시도 {i+1}")
                    break
                except Exception:
                    # 방법 2: 실패 시 기존 클릭 방식 시도
                    try:
                        camp_btn = self.driver.find_element(By.XPATH, f"//a[contains(@onclick, \"chgTrrsrt('4000')\")]")
                        camp_btn.click()
                        camp_click_success = True
                        self.log(f"👆 캠핑장 선택(클릭) 성공 - 시도 {i+1}")
                        break
                    except:
                        time.sleep(0.2)
            
            if not camp_click_success:
                self.log("❌ 초기 캠핑장 선택 실패")
                return
            
            month_nav = int(config['month_nav'])
            for i in range(month_nav):
                wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@onclick, 'opNextMonth')]"))).click()
                time.sleep(0.2)
                
            self.log(f"⏰ [타임 어택] {config['target_time']} 대기 중...")
            
            if config.get('test_mode', False):
                self.log("⚡ [TEST 모드] 즉시 새로고침!")
                self.driver.refresh()
            else:
                # [수정] 리드타임 로직 적용을 위한 시간 계산
                target_str = config['target_time']
                lead_ms = int(config.get('lead_time', 0))
                
                try:
                    target_dt = datetime.strptime(target_str, "%H:%M:%S")
                    pre_target_dt = target_dt - timedelta(seconds=1)
                    pre_target_str = pre_target_dt.strftime("%H:%M:%S")
                except:
                    self.log("⚠️ 시간 형식 파싱 실패. 리드타임 없이 진행합니다.")
                    pre_target_str = ""
                    
                self.log(f"🎯 목표: {target_str} (보정: {lead_ms}ms) | 감지대상: {pre_target_str}")

                last_log_time = 0
                
                while self.is_running:
                    now_server = self.get_current_server_time()
                    curr_time = now_server.strftime("%H:%M:%S")
                    
                    # 1. 리드타임 적용: 1초 전 감지 시
                    if lead_ms > 0 and curr_time == pre_target_str:
                        # 현재 초의 밀리초가 lead_ms가 될 때까지 정밀 대기
                        # 예: 13:59:59.000 에서 600ms 리드타임이면 400ms 대기 후 발사
                        ms_now = now_server.microsecond / 1000.0
                        delay_sec = (1000 - lead_ms - ms_now) / 1000.0
                        if delay_sec < 0: delay_sec = 0
                        
                        self.log(f"⚡ [{curr_time}.{int(ms_now):03d}] 1초 전 감지! {delay_sec:.3f}초 대기 후 발사...")
                        if delay_sec > 0:
                            time.sleep(delay_sec)
                        self.log("🚀 [LEAD] 리드타임 새로고침!")
                        self.driver.refresh()
                        break
                        
                    # 2. 정시 도달 (리드타입 없거나 놓쳤을 경우)
                    if curr_time >= target_str:
                        self.log(f"⚡ [OPEN] {curr_time} 도달! 즉시 새로고침!")
                        self.driver.refresh()
                        break
                        
                    if time.time() - last_log_time > 1:
                        ms = now_server.strftime(".%f")[:3]
                        self.log(f"⏳ 서버시간: {curr_time}{ms} (목표: {target_str})")
                        last_log_time = time.time()
                    time.sleep(0.01) # CPU 부하 감소 및 정밀도 균형

            if not self.is_running: return

            # 4. 새로고침 후 바로 날짜 선택
            self.log("🔄 새로고침 완료! 날짜 선택 대기...")
            
            try:
                wait.until(lambda d: d.execute_script("return typeof jsChkInDt !== 'undefined'"))
            except:
                time.sleep(0.5)

            self.log(f"📆 {config['day']}일 선택 (즉시 실행)")
            self.driver.execute_script(f"jsChkInDt('{config['year']}','{config['month']}','{config['day']}', null);")
            
            # 숙박기간 설정
            self.log("🛌 숙박기간 설정 (스마트 JS 주입)")
            target_period = config['stay_period']
            
            stay_script = f"""
            var el = document.getElementById('stayngPd');
            if (!el) return false;
            
            var optionExists = false;
            for (var i = 0; i < el.options.length; i++) {{
                if (el.options[i].value == '{target_period}') {{
                    optionExists = true;
                    break;
                }}
            }}
            
            if (optionExists) {{
                el.value = '{target_period}';
                el.dispatchEvent(new Event('change'));
                return el.value == '{target_period}';
            }}
            return false;
            """
            
            end_wait = time.time() + 5
            success_stay = False
            while time.time() < end_wait:
                if self.driver.execute_script(stay_script):
                    self.log(f"✅ 숙박기간 설정 완료: {target_period}")
                    success_stay = True
                    break
                time.sleep(0.1)
                
            if not success_stay:
                self.log("⚠️ 경고: 숙박기간 설정 지연/실패")

            # 5. 캡차 해결
            self.solve_captcha(wait)
            
            # 6. 광클 (여기에 config 전체 전달)
            self.quick_reservation(config)
            
        except Exception as e:
            self.log(f"🚨 오류 발생: {e}")
            
    def solve_captcha(self, wait):
        self.log("🤖 캡차 해독 시작 (블루 헌터 모드)...")
        try:
            ocr = ddddocr.DdddOcr(show_ad=False)
        except:
            ocr = ddddocr.DdddOcr(show_ad=False)
        
        for attempt in range(30):
            if not self.is_running: return
            try:
                self.log(f"📸 캡차 시도 {attempt+1}")
                img_elem = wait.until(EC.presence_of_element_located((By.XPATH, "//div[@class='capture']/img")))
                img = Image.open(BytesIO(img_elem.screenshot_as_png)).convert('RGB')
                
                pixels = img.load()
                w, h = img.size
                blue_cnt = sum(1 for x in range(int(w*0.2), int(w*0.8)) for y in range(int(h*0.2), int(h*0.8)) 
                               if pixels[x,y][2] > pixels[x,y][0]+30 and pixels[x,y][2] > pixels[x,y][1]+30)
                
                is_blue = blue_cnt > 50
                
                if not is_blue:
                    self.log("⚫ 검은글자 감지 -> ❌ 스킵 (새로고침)")
                    self.driver.execute_script("captchaReload('0');")
                    time.sleep(0.1)
                    continue

                self.log("🔹 파란글자 감지 -> ⭕ 해독 시도")
                for x in range(w):
                    for y in range(h):
                        r,g,b = pixels[x,y]
                        if not (b>r+25 and b>g+25):
                            pixels[x,y] = (255,255,255)
                        else:
                            pixels[x,y] = (0,0,0)

                res = ocr.classification(img)
                if len(res) == 5:
                    self.log(f"⚡ 입력: {res}")
                    inp = self.driver.find_element(By.ID, "answer")
                    inp.clear()
                    inp.send_keys(res)
                    
                    self.driver.execute_script("nextPage();")
                    self.log(f"🚀 [NO-DELAY] '{res}' 입력 후 즉시 Next 실행!")
                    return
                else:
                    self.log(f"⚠️ 글자수 오류({len(res)})")
                    raise Exception("Length")
            except:
                try:
                    self.driver.execute_script("captchaReload('0');")
                    time.sleep(0.1)
                except:
                    pass
        self.log("❌ 캡차 실패")

    def quick_reservation(self, config):
        self.log("⏳ 광클 준비 (탭 전환 중)...")
        priorities_str = config['priorities']
        stop_early = config.get('stop_early', False)
        
        site_list = [s.strip() for s in priorities_str.split(',')]
        target_ids = [SITE_MAP[s] for s in site_list if s in SITE_MAP]
        js_ids = str(target_ids)
        self.log(f"🚀 우선순위: {site_list}")
        
        end_time = time.time() + 20
        tab_clicked = False
        
        while time.time() < end_time and self.is_running:
            try:
                # 1. 자동차캠핑장 탭 찾기 및 클릭
                if self.driver.find_elements(By.XPATH, "//a[contains(@href, \"selUpperFclty('4100'\")]"):
                    if self.driver.execute_script("return typeof selUpperFclty !== 'undefined';"):
                        self.driver.execute_script("selUpperFclty('4100','CR','CC_001');")
                        tab_clicked = True
                        
                        # 예약 직전 멈춤 모드 체크
                        if stop_early:
                            self.log("🛑 [테스트 모드] '자동차캠핑장' 탭 진입 후 멈췄습니다.")
                            self.log("⚠️ 실제 예약(광클)은 진행하지 않습니다.")
                            return
                        break
            except:
                pass
            time.sleep(0.05)
            
        if not tab_clicked:
            self.log("❌ 탭 전환 실패")
            return

        time.sleep(0.3)
        self.log("🔥 자리 선점 시도 중...")
        
        script = f"""
        var targetIds = {js_ids};
        for (var i = 0; i < targetIds.length; i++) {{
            var siteId = targetIds[i];
            var el = document.getElementById(siteId);
            if (el && !el.className.includes('r_end')) {{
                insertPreocpc(siteId, 'CR', 'CC_001');
                return siteId;
            }}
        }}
        return null;
        """
        
        start = time.time()
        while time.time() - start < 10 and self.is_running:
            try:
                res = self.driver.execute_script(script)
                if res:
                    self.log(f"🎉 성공! 사이트 ID: {res}")
                    try:
                        WebDriverWait(self.driver, 5).until(EC.alert_is_present())
                        self.driver.switch_to.alert.accept()
                        self.driver.execute_script("nextPage();")
                    except: 
                        try:
                            self.driver.execute_script("nextPage();")
                        except:
                            pass
                    self.log("🎉🎉🎉 결제 페이지로 이동했습니다! 🎉🎉🎉")
                    return
                time.sleep(0.1)
            except:
                pass
        self.log("😭 실패: 모든 자리가 마감되었습니다.")

# ============================================
# 🖥️ GUI 클래스
# ============================================
class CampingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("추암 캠핑장 예약 봇 (DK Edition)")
        
        w, h = 520, 800
        ws = root.winfo_screenwidth()
        hs = root.winfo_screenheight()
        x = (ws/2) - (w/2)
        y = (hs/2) - (h/2)
        root.geometry('%dx%d+%d+%d' % (w, h, x, y))

        # [수정] 로그 저장 경로 설정 (사용자 지정 경로)
        log_dir = r"C:\gemini\logs\추암"

        # 폴더가 없으면 자동 생성
        if not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir)
            except Exception as e:
                print(f"폴더 생성 실패: {e}")

        # 파일명 생성 및 전체 경로 결합
        now_str = datetime.now().strftime("%Y-%m-%d-%H-%M")
        self.log_filename = os.path.join(log_dir, f"{now_str}_추암캠핑장_Log.txt")
        
        self.bot = CampingBot(self.log_msg)
        self.var_test_mode = tk.BooleanVar()
        self.var_stop_early = tk.BooleanVar()
        self.config = self.load_config()
        
        self.create_widgets()

    def load_config(self):
        config = DEFAULT_CONFIG.copy()
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    config.update(data)
            except:
                pass
        self.var_test_mode.set(config.get('test_mode', False))
        self.var_stop_early.set(config.get('stop_early', False))
        return config

    def get_rotated_priority(self, start_site):
        try:
            idx = MASTER_PRIORITY_LIST.index(start_site)
            rotated = MASTER_PRIORITY_LIST[idx:] + MASTER_PRIORITY_LIST[:idx]
            return ", ".join(rotated)
        except:
            return "D5, D4, D3, D2, D1"

    def save_config(self):
        selected_site = self.combo_priority.get()
        priority_string = self.get_rotated_priority(selected_site)
        
        display_period = self.combo_period.get()
        code_period = STAY_PERIOD_MAP.get(display_period, "1001")

        new_config = {
            "user_id": self.entry_id.get(),
            "user_pw": self.entry_pw.get(),
            "year": self.entry_year.get(),
            "month": self.entry_month.get(),
            "day": self.entry_day.get(),
            "stay_period": code_period,
            "month_nav": self.entry_nav.get(),
            "target_time": self.entry_time.get(),
            "lead_time": self.entry_lead.get(),
            "priorities": priority_string,
            "test_mode": self.var_test_mode.get(),
            "stop_early": self.var_stop_early.get()
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(new_config, f, indent=4)
        return new_config

    def save_category_msg(self, category_name):
        self.save_config()
        if category_name == "타임어택/우선순위":
            selected = self.combo_priority.get()
            result = self.get_rotated_priority(selected)
            self.log_msg(f"💾 저장됨! 우선순위 설정: {result}")
        messagebox.showinfo("저장 완료", f"{category_name} 설정이 저장되었습니다.")

    def create_widgets(self):
        style = ttk.Style()
        style.configure('TLabel', font=('맑은 고딕', 10))
        style.configure('TButton', font=('맑은 고딕', 10, 'bold'))
        
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 1. 로그인 정보
        info_frame = ttk.LabelFrame(main_frame, text="🔒 로그인 정보", padding="5")
        info_frame.pack(fill=tk.X, pady=5)
        info_frame.columnconfigure(4, weight=1)

        ttk.Label(info_frame, text="아이디:").grid(row=0, column=0, padx=5)
        self.entry_id = ttk.Entry(info_frame, width=12)
        self.entry_id.insert(0, self.config['user_id'])
        self.entry_id.grid(row=0, column=1, padx=5)
        
        ttk.Label(info_frame, text="비밀번호:").grid(row=0, column=2, padx=5)
        self.entry_pw = ttk.Entry(info_frame, show="*", width=12)
        self.entry_pw.insert(0, self.config['user_pw'])
        self.entry_pw.grid(row=0, column=3, padx=5)
        
        ttk.Button(info_frame, text="💾 저장", width=8, 
                   command=lambda: self.save_category_msg("로그인")).grid(row=0, column=5, padx=5, sticky='e')

        # 2. 예약 설정
        res_frame = ttk.LabelFrame(main_frame, text="📅 예약 설정", padding="5")
        res_frame.pack(fill=tk.X, pady=5)
        
        date_frame = ttk.Frame(res_frame)
        date_frame.pack(fill=tk.X, pady=2)
        ttk.Label(date_frame, text="날짜(Y/M/D):").pack(side=tk.LEFT)
        self.entry_year = ttk.Entry(date_frame, width=5)
        self.entry_year.insert(0, self.config['year'])
        self.entry_year.pack(side=tk.LEFT, padx=2)
        self.entry_month = ttk.Entry(date_frame, width=3)
        self.entry_month.insert(0, self.config['month'])
        self.entry_month.pack(side=tk.LEFT, padx=2)
        self.entry_day = ttk.Entry(date_frame, width=3)
        self.entry_day.insert(0, self.config['day'])
        self.entry_day.pack(side=tk.LEFT, padx=2)
        
        period_frame = ttk.Frame(res_frame)
        period_frame.pack(fill=tk.X, pady=2)
        ttk.Label(period_frame, text="숙박기간:").pack(side=tk.LEFT)
        self.combo_period = ttk.Combobox(period_frame, values=list(STAY_PERIOD_MAP.keys()), state="readonly", width=15)
        
        saved_code = self.config.get('stay_period', '1001')
        self.combo_period.set(STAY_PERIOD_MAP_REV.get(saved_code, "1박 2일"))
        
        self.combo_period.pack(side=tk.LEFT, padx=5)
        
        nav_frame = ttk.Frame(res_frame)
        nav_frame.pack(fill=tk.X, pady=2)
        ttk.Label(nav_frame, text="다음달 이동 횟수:").pack(side=tk.LEFT)
        self.entry_nav = ttk.Entry(nav_frame, width=5)
        self.entry_nav.insert(0, self.config['month_nav'])
        self.entry_nav.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(res_frame, text="💾 저장", width=8,
                   command=lambda: self.save_category_msg("예약")).pack(anchor='e', pady=5, padx=5)

        # 3. 타임어택 & 우선순위
        adv_frame = ttk.LabelFrame(main_frame, text="⚡ 타임어택 & 우선순위", padding="5")
        adv_frame.pack(fill=tk.X, pady=5)
        adv_frame.columnconfigure(1, weight=1)
        
        ttk.Label(adv_frame, text="타겟 오픈 시간:").grid(row=0, column=0, sticky="w", pady=2)
        self.entry_time = ttk.Entry(adv_frame)
        self.entry_time.insert(0, self.config['target_time'])
        self.entry_time.grid(row=0, column=1, padx=5, sticky="ew")

        # [추가] 리드타임 설정
        ttk.Label(adv_frame, text="새로고침 보정(ms):").grid(row=1, column=0, sticky="w", pady=2)
        self.entry_lead = ttk.Entry(adv_frame)
        self.entry_lead.insert(0, self.config.get('lead_time', '0'))
        self.entry_lead.grid(row=1, column=1, padx=5, sticky="ew")
        
        ttk.Label(adv_frame, text="1순위 사이트:").grid(row=2, column=0, sticky="w", pady=2)
        self.combo_priority = ttk.Combobox(adv_frame, values=MASTER_PRIORITY_LIST, state="readonly")
        
        saved_first_prio = self.config['priorities'].split(',')[0].strip()
        if saved_first_prio in MASTER_PRIORITY_LIST:
            self.combo_priority.set(saved_first_prio)
        else:
            self.combo_priority.current(0)
        self.combo_priority.grid(row=2, column=1, padx=5, sticky="ew")
        
        # 체크박스 배치
        self.chk_test = ttk.Checkbutton(adv_frame, text="🚀 Test 모드 (시간무시)", variable=self.var_test_mode)
        self.chk_test.grid(row=3, column=0, columnspan=2, sticky='w', pady=2)
        
        self.chk_stop = ttk.Checkbutton(adv_frame, text="🛑 예약 직전 멈춤 (사이트클릭 X)", variable=self.var_stop_early)
        self.chk_stop.grid(row=4, column=0, columnspan=2, sticky='w', pady=2)
        
        ttk.Button(adv_frame, text="💾 저장", width=8,
                   command=lambda: self.save_category_msg("타임어택/우선순위")).grid(row=4, column=1, pady=5, sticky='e')

        # 4. 버튼
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        self.btn_start = ttk.Button(btn_frame, text="🚀 예약 시작", command=self.start_bot)
        self.btn_start.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        self.btn_stop = ttk.Button(btn_frame, text="🛑 중지", command=self.stop_bot, state="disabled")
        self.btn_stop.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

        # 5. 로그창
        log_frame = ttk.LabelFrame(main_frame, text="📝 실행 로그", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_area = scrolledtext.ScrolledText(log_frame, height=15, state='disabled')
        self.log_area.pack(fill=tk.BOTH, expand=True)

    def log_msg(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-4]
        full_msg = f"[{timestamp}] {msg}\n"
        
        # 1. GUI에 출력
        def _update():
            self.log_area.config(state='normal')
            self.log_area.insert(tk.END, full_msg)
            self.log_area.see(tk.END)
            self.log_area.config(state='disabled')
        self.root.after(0, _update)

        # 2. 파일에 저장
        try:
            with open(self.log_filename, "a", encoding="utf-8") as f:
                f.write(full_msg)
        except Exception as e:
            # 파일 쓰기 실패시 콘솔에만 에러 출력 (봇 작동은 계속됨)
            print(f"로그 파일 저장 실패: {e}")

    def start_bot(self):
        config = self.save_config()
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.log_msg("=== 봇을 시작합니다 ===")
        
        # 로그 파일 시작 알림
        self.log_msg(f"📂 로그 저장 경로: {self.log_filename}")
        
        if config['test_mode']:
            self.log_msg("⚠️ TEST 모드 활성화됨: 타임어택을 건너뜁니다.")
        if config['stop_early']:
            self.log_msg("⚠️ 안전 모드 활성화됨: 예약 직전에 멈춥니다.")
        self.log_msg(f"🎯 설정된 우선순위: {config['priorities']}")
        
        t = threading.Thread(target=self.run_bot_thread, args=(config,))
        t.daemon = True
        t.start()

    def run_bot_thread(self, config):
        self.bot.run(config)
        self.root.after(0, lambda: self.btn_start.config(state="normal"))
        self.root.after(0, lambda: self.btn_stop.config(state="disabled"))
        self.log_msg("=== 봇이 종료되었습니다 ===")

    def stop_bot(self):
        self.bot.stop()
        self.log_msg("🛑 중지 명령을 보냈습니다.")

if __name__ == "__main__":
    root = tk.Tk()
    app = CampingApp(root)
    root.mainloop()