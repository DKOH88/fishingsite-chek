"""
🎣 낚시배 취소석 모니터링 봇 v2.0
- 여러 낚시배 동시 감시 가능
- 선택한 날짜(9~11월)의 예약 가능 여부를 8~10분마다 체크
- 예약하기 버튼이 활성화되면 텔레그램 알림 전송
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import json
import os
import time
import random
import re
import requests
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

# ============================================
# 📁 설정
# ============================================
CONFIG_FILE = 'fishing_boat_monitor_config.json'

DEFAULT_CONFIG = {
    "telegram_token": "8538517871:AAEd0Ob4O2oSk-e3NZDDfz6zSHsTf0MGD74",
    "telegram_chat_id": "393163178",
    "target_year": "2026",
    "target_months": ["09", "10", "11"],
    "target_days": {"09": [], "10": [], "11": []},
    "check_interval_min": 8,
    "check_interval_max": 10,
    "headless_mode": True,
    "current_platform": "thefishing",  # thefishing 또는 sunsang24
    "thefishing_boats": [
        {"name": "금땡이호", "enabled": False, "base_url": "http://xn--jj0bj3lvmq92n.kr/index.php", "pa_n_uid": "5492"},
        {"name": "까칠이호", "enabled": False, "base_url": "https://xn--hl0b209b41esvi.com/index.php", "pa_n_uid": "3973"},
        {"name": "깜보호", "enabled": False, "base_url": "https://winner.thefishing.kr/index.php", "pa_n_uid": "3970"},
        {"name": "나폴리호", "enabled": False, "base_url": "https://www.napoliho.net/index.php", "pa_n_uid": "1484"},
        {"name": "뉴신정호", "enabled": False, "base_url": "http://newsj.co.kr/index.php", "pa_n_uid": "4452"},
        {"name": "뉴청남호", "enabled": False, "base_url": "http://www.chungnamho.com/index.php", "pa_n_uid": "5951"},
        {"name": "루디호", "enabled": False, "base_url": "http://www.rudyfishing.com/index.php", "pa_n_uid": "3468"},
        {"name": "마그마호", "enabled": False, "base_url": "http://xn--2i0b07tba4320a.kr/index.php", "pa_n_uid": "5352"},
        {"name": "미라클호", "enabled": False, "base_url": "http://xn--2i0b07tba4320a.kr/index.php", "pa_n_uid": "5361"},
        {"name": "부흥호", "enabled": False, "base_url": "http://www.anhbuh.com/index.php", "pa_n_uid": "2928"},
        {"name": "블레스호", "enabled": False, "base_url": "http://www.blessho.com/index.php", "pa_n_uid": "3288"},
        {"name": "블루호", "enabled": False, "base_url": "https://bluefishing.asia/index.php", "pa_n_uid": "1615"},
        {"name": "샤크호", "enabled": False, "base_url": "http://www.sharkho.com/index.php", "pa_n_uid": "2199"},
        {"name": "솔티가호", "enabled": False, "base_url": "http://www.rudyfishing.com/index.php", "pa_n_uid": "5367"},
        {"name": "아인스호", "enabled": False, "base_url": "https://www.einsho.com/index.php", "pa_n_uid": "349"},
        {"name": "아일랜드호", "enabled": False, "base_url": "http://www.fishingi.net/index.php", "pa_n_uid": "1444"},
        {"name": "야야호", "enabled": False, "base_url": "http://www.yayaho.kr/index.php", "pa_n_uid": "3960"},
        {"name": "여명호", "enabled": False, "base_url": "http://xn--v42bv0rcoar53c6lb.kr/index.php", "pa_n_uid": "5030"},
        {"name": "오디세이호", "enabled": False, "base_url": "http://www.joeunfish.com/index.php", "pa_n_uid": "788"},
        {"name": "유진호", "enabled": False, "base_url": "https://www.eugeneho.kr/index.php", "pa_n_uid": "1190"},
        {"name": "천일호", "enabled": False, "base_url": "http://fishing1001.com/index.php", "pa_n_uid": "1443"},
        {"name": "청광호", "enabled": False, "base_url": "http://www.chungkwangho.net/index.php", "pa_n_uid": "1588"},
        {"name": "청남호", "enabled": False, "base_url": "http://www.chungnamho.com/index.php", "pa_n_uid": "1441"},
        {"name": "청용호", "enabled": False, "base_url": "http://www.changdukho.com/index.php", "pa_n_uid": "271"},
        {"name": "카즈미호", "enabled": False, "base_url": "https://xn--hg3b11w8xdjuj.com/index.php", "pa_n_uid": "4576"},
        {"name": "퀸블레스호", "enabled": False, "base_url": "http://www.blessho.com/index.php", "pa_n_uid": "4675"},
        {"name": "팀루피호", "enabled": False, "base_url": "https://masterfishing.kr/index.php", "pa_n_uid": "2805"},
        {"name": "팀바이트호", "enabled": False, "base_url": "http://teambite.kr/index.php", "pa_n_uid": "5948"},
        {"name": "페라리호", "enabled": False, "base_url": "http://www.xn--oi2bn5b095b4mc.com/index.php", "pa_n_uid": "1264"},
        {"name": "행운호", "enabled": False, "base_url": "http://www.hangwoonho.com/index.php", "pa_n_uid": "3448"},
        {"name": "헤라호", "enabled": False, "base_url": "https://www.ssfish.kr/index.php", "pa_n_uid": "3609"},
        {"name": "골드피싱호", "enabled": False, "base_url": "http://www.mscufishing.com/index.php", "pa_n_uid": "2954"},
        {"name": "뉴찬스호", "enabled": False, "base_url": "http://www.chanceho.com/index.php", "pa_n_uid": "2283"},
        {"name": "만석호", "enabled": False, "base_url": "http://www.mscufishing.com/index.php", "pa_n_uid": "3570"},
        {"name": "베스트3호", "enabled": False, "base_url": "https://khanfishing.com/index.php", "pa_n_uid": "5340"},
        {"name": "스타피싱호", "enabled": False, "base_url": "https://jstar.thefishing.kr/index.php", "pa_n_uid": "1925"},
        {"name": "승주호", "enabled": False, "base_url": "http://www.mscufishing.com/index.php", "pa_n_uid": "2955"},
        {"name": "아라호", "enabled": False, "base_url": "https://www.araho.kr/index.php", "pa_n_uid": "5732"},
        {"name": "아이리스호", "enabled": False, "base_url": "http://www.irisho.kr/index.php", "pa_n_uid": "1545"},
        {"name": "야호", "enabled": False, "base_url": "http://xn--2f5b291a.com/index.php", "pa_n_uid": "3904"},
        {"name": "예린호", "enabled": False, "base_url": "http://www.yerinfishing.com/index.php", "pa_n_uid": "3515"},
        {"name": "와이파이호", "enabled": False, "base_url": "https://khanfishing.com/index.php", "pa_n_uid": "5264"},
        {"name": "으리호", "enabled": False, "base_url": "http://www.mscufishing.com/index.php", "pa_n_uid": "4920"},
        {"name": "제트호", "enabled": False, "base_url": "https://khanfishing.com/index.php", "pa_n_uid": "5341"},
        {"name": "지오디호", "enabled": False, "base_url": "https://www.teamgod.kr/index.php", "pa_n_uid": "5295"},
        {"name": "짱구호", "enabled": False, "base_url": "http://www.ybada.com/index.php", "pa_n_uid": "1677"},
        {"name": "팀만수호", "enabled": False, "base_url": "https://teammansu.kr/index.php", "pa_n_uid": "2829"},
        {"name": "하와이호", "enabled": False, "base_url": "http://www.newhawaii.co.kr/index.php", "pa_n_uid": "4667"},
        {"name": "헌터호", "enabled": False, "base_url": "http://www.mscufishing.com/index.php", "pa_n_uid": "4443"},
        {"name": "헤르메스호", "enabled": False, "base_url": "http://hermes.thefishing.kr/index.php", "pa_n_uid": "5579"},
    ],
    "sunsang24_boats": [
        {"name": "가가호", "enabled": False, "base_url": "https://gagaho.sunsang24.com"},
        {"name": "기가호", "enabled": False, "base_url": "https://giga.sunsang24.com"},
        {"name": "자이언트호", "enabled": False, "base_url": "https://rkclgh.sunsang24.com"},
        {"name": "도지호", "enabled": False, "base_url": "https://doji.sunsang24.com"},
        {"name": "팀에프원", "enabled": False, "base_url": "https://teamf.sunsang24.com"},
        {"name": "팀에프투", "enabled": False, "base_url": "https://teamf.sunsang24.com"},
        {"name": "천마호", "enabled": False, "base_url": "https://metafishingclub.sunsang24.com"},
    ]
}


# ============================================
# 📅 캘린더 팝업
# ============================================
class CalendarPopup:
    """월별 캘린더 팝업 - 여러 날짜 선택 가능"""
    
    def __init__(self, parent, year: int, month: int, selected_days: list = None, callback=None):
        self.parent = parent
        self.year = year
        self.month = month
        self.selected_days = set(selected_days or [])
        self.callback = callback
        self.day_buttons = {}
        
        self.popup = tk.Toplevel(parent)
        self.popup.title(f"📅 {year}년 {month}월 날짜 선택")
        self.popup.transient(parent)
        self.popup.grab_set()
        
        # 창 위치 (부모 창 중앙)
        w, h = 350, 320
        x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (w // 2)
        y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (h // 2)
        self.popup.geometry(f'{w}x{h}+{x}+{y}')
        
        self.create_widgets()
    
    def create_widgets(self):
        main_frame = ttk.Frame(self.popup, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 헤더
        header = ttk.Label(main_frame, text=f"🗓️ {self.year}년 {self.month}월", 
                          font=("맑은 고딕", 14, "bold"))
        header.pack(pady=5)
        
        ttk.Label(main_frame, text="감시할 날짜를 클릭하세요 (여러 개 선택 가능)", 
                 foreground="gray").pack(pady=2)
        
        # 요일 헤더
        day_frame = ttk.Frame(main_frame)
        day_frame.pack(pady=5)
        
        weekdays = ["일", "월", "화", "수", "목", "금", "토"]
        for i, day in enumerate(weekdays):
            color = "#ff4444" if i == 0 else ("#4444ff" if i == 6 else "black")
            lbl = ttk.Label(day_frame, text=day, width=4, anchor='center')
            lbl.grid(row=0, column=i, padx=1, pady=2)
        
        # 달력 생성
        import calendar
        cal = calendar.Calendar(firstweekday=6)  # 일요일 시작
        
        days_in_month = list(cal.itermonthdays(self.year, self.month))
        
        row = 1
        col = 0
        for day in days_in_month:
            if day == 0:
                # 빈 칸
                lbl = ttk.Label(day_frame, text="", width=4)
                lbl.grid(row=row, column=col, padx=1, pady=2)
            else:
                # 날짜 버튼
                is_selected = str(day) in self.selected_days or day in self.selected_days
                btn = tk.Button(
                    day_frame, 
                    text=str(day), 
                    width=4, 
                    height=1,
                    bg="#4CAF50" if is_selected else "white",
                    fg="white" if is_selected else "black",
                    font=("맑은 고딕", 9),
                    command=lambda d=day: self.toggle_day(d)
                )
                btn.grid(row=row, column=col, padx=1, pady=2)
                self.day_buttons[day] = btn
            
            col += 1
            if col > 6:
                col = 0
                row += 1
        
        # 버튼
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=10)
        
        # 작은 버튼 스타일
        style = ttk.Style()
        style.configure('Small.TButton', font=('맑은 고딕', 8))
        
        ttk.Button(btn_frame, text="🔄 전체선택", command=self.select_all, width=10, style='Small.TButton').pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="🚫 전체취소", command=self.clear_all, width=10, style='Small.TButton').pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="✅ 확인", command=self.confirm, width=8, style='Small.TButton').pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="❌ 취소", command=self.cancel, width=8, style='Small.TButton').pack(side=tk.LEFT, padx=3)
        
        # 선택된 날짜 표시
        self.lbl_selected = ttk.Label(main_frame, text=self.get_selection_text(), foreground="blue")
        self.lbl_selected.pack(pady=5)
    
    def toggle_day(self, day):
        """날짜 선택/해제 토글"""
        day_str = str(day)
        if day_str in self.selected_days:
            self.selected_days.remove(day_str)
        elif day in self.selected_days:
            self.selected_days.remove(day)
        else:
            self.selected_days.add(day_str)
        
        # 버튼 색상 업데이트
        is_selected = day_str in self.selected_days or day in self.selected_days
        btn = self.day_buttons.get(day)
        if btn:
            btn.config(
                bg="#4CAF50" if is_selected else "white",
                fg="white" if is_selected else "black"
            )
        
        self.lbl_selected.config(text=self.get_selection_text())
    
    def select_all(self):
        """전체 선택"""
        import calendar
        _, days_count = calendar.monthrange(self.year, self.month)
        for day in range(1, days_count + 1):
            self.selected_days.add(str(day))
        
        for day, btn in self.day_buttons.items():
            btn.config(bg="#4CAF50", fg="white")
        
        self.lbl_selected.config(text=self.get_selection_text())
    
    def clear_all(self):
        """전체 취소"""
        self.selected_days.clear()
        
        for day, btn in self.day_buttons.items():
            btn.config(bg="white", fg="black")
        
        self.lbl_selected.config(text=self.get_selection_text())
    
    def get_selection_text(self):
        """선택된 날짜 텍스트"""
        sorted_days = sorted([int(d) for d in self.selected_days if d])
        if not sorted_days:
            return "선택된 날짜 없음"
        return f"선택: {', '.join(map(str, sorted_days[:10]))}..." if len(sorted_days) > 10 else f"선택: {', '.join(map(str, sorted_days))}"
    
    def confirm(self):
        """확인"""
        sorted_days = sorted([str(int(d)) for d in self.selected_days if d])
        if self.callback:
            self.callback(self.month, sorted_days)
        self.popup.destroy()
    
    def cancel(self):
        """취소"""
        self.popup.destroy()


# ============================================
# 📡 텔레그램 알림
# ============================================
class TelegramNotifier:
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{token}"
    
    def send_message(self, message: str, parse_mode: str = "HTML"):
        if not self.token or not self.chat_id:
            return False
        
        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": parse_mode,
                "disable_web_page_preview": False
            }
            response = requests.post(url, data=data, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"텔레그램 전송 실패: {e}")
            return False
    
    def send_cancellation_alert(self, boat_name: str, date: str, url: str, status: str = ""):
        timestamp = datetime.now().strftime("%H:%M:%S")
        status_line = f"\n🪑 <b>상태:</b> {status}" if status else ""
        
        message = f"""
🎣 <b>취소석 발생!</b>

📍 <b>선박:</b> {boat_name}
📅 <b>날짜:</b> {date}{status_line}
🕐 <b>감지시간:</b> {timestamp}

🔗 <a href="{url}">예약 페이지 바로가기</a>

⚡ 빠르게 예약하세요!
"""
        return self.send_message(message)


# ============================================
# 🤖 통합 모니터링 봇
# ============================================
class FishingBoatMonitor:
    def __init__(self, log_callback, config):
        self.log = log_callback
        self.config = config
        self.driver = None
        self.is_running = False
        self.notifier = TelegramNotifier(
            config.get('telegram_token', ''),
            config.get('telegram_chat_id', '')
        )
        self.alerted_dates = set()  # 이미 알림 보낸 (배이름-날짜) 조합
    
    def setup_driver(self):
        self.log("🚗 크롬 드라이버 설정 중...")
        
        chrome_options = Options()
        
        if self.config.get('headless_mode', True):
            chrome_options.add_argument('--headless=new')
            self.log("👻 헤드리스 모드 활성화")
        
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=1200,900')
        chrome_options.add_argument('--log-level=3')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        service = Service()
        service.log_path = os.devnull
        
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        })
        
        self.log("✅ 드라이버 준비 완료")
    
    def build_calendar_url(self, base_url: str, pa_n_uid: str, year: str, month: str):
        """달력 페이지 URL 생성"""
        return f"{base_url}?mid=bk&year={year}&month={month}&day=01&mode=cal&PA_N_UID={pa_n_uid}#list"
    
    def check_date_availability(self, date_str: str, pa_n_uid: str):
        """
        특정 날짜의 예약 가능 여부 확인
        date_str: YYYYMMDD 형식
        """
        try:
            page_source = self.driver.page_source
            
            # 해당 날짜가 페이지에 있는지 확인
            date_pattern = f"date={date_str}"
            if date_pattern not in page_source:
                return False, "정보없음"
            
            # r_cal_box 단위로 해당 날짜 블록 찾기
            # 패턴: r_cal_box 내에서 date=YYYYMMDD를 포함하는 블록
            cal_box_pattern = rf'<div class="r_cal_box">(.*?)</div>\s*</div>\s*</div>'
            cal_boxes = re.findall(cal_box_pattern, page_source, re.DOTALL)
            
            for box_content in cal_boxes:
                if date_pattern in box_content:
                    # 이 블록이 해당 날짜의 블록
                    
                    # 1. "예약완료" 텍스트가 있으면 → 예약 불가
                    if '예약완료' in box_content:
                        return False, "예약완료"
                    
                    # 2. "예약하기" 버튼이 있으면 → 예약 가능
                    if '>예약하기<' in box_content or '>예약하기 <' in box_content:
                        # 남은 인원 추출
                        remain_match = re.search(r'남은인원.*?(\d+)명', box_content, re.DOTALL)
                        if remain_match:
                            return True, f"남은인원: {remain_match.group(1)}명"
                        return True, "예약가능"
                    
                    # 3. "대기하기" 버튼만 있으면 → 예약 마감
                    if '>대기하기<' in box_content:
                        return False, "예약마감(대기가능)"
                    
                    return False, "정보없음"
            
            # 폴백: r_cal_box 패턴으로 못 찾으면 전체 검색
            # onclick에서 정확히 해당 날짜의 "예약하기" 버튼 찾기
            try:
                xpath_reserve = f"//a[contains(@onclick, 'date={date_str}') and contains(text(), '예약하기')]"
                reserve_btn = self.driver.find_element(By.XPATH, xpath_reserve)
                if reserve_btn:
                    # 버튼 주변 텍스트에서 예약완료 확인
                    try:
                        parent = reserve_btn.find_element(By.XPATH, "./ancestor::div[@class='r_cal_box']")
                        parent_html = parent.get_attribute('innerHTML')
                        if '예약완료' in parent_html:
                            return False, "예약완료"
                        
                        remain_match = re.search(r'남은인원.*?(\d+)명', parent_html, re.DOTALL)
                        if remain_match:
                            return True, f"남은인원: {remain_match.group(1)}명"
                    except:
                        pass
                    return True, "예약가능"
            except:
                pass
            
            # 대기하기 버튼 확인
            try:
                xpath_waiting = f"//a[contains(@onclick, 'date={date_str}') and contains(text(), '대기하기')]"
                waiting_btn = self.driver.find_element(By.XPATH, xpath_waiting)
                if waiting_btn:
                    return False, "예약마감(대기가능)"
            except:
                pass
            
            return False, "정보없음"
            
        except Exception as e:
            return False, f"오류: {e}"
    
    def check_boat(self, boat: dict, year: str, month_days: dict):
        """한 배의 여러 월/날짜를 체크"""
        boat_name = boat['name']
        base_url = boat['base_url']
        pa_n_uid = boat['pa_n_uid']
        
        # 나폴리호는 예약 페이지에서 직접 체크 (캘린더 없음)
        if '나폴리' in boat_name:
            return self.check_napoli_boat(boat, year, month_days)
        
        available_list = []
        
        for month, days in month_days.items():
            if not days:  # 해당 월에 선택된 날짜 없으면 스킵
                continue
            
            url = self.build_calendar_url(base_url, pa_n_uid, year, month)
            self.log(f"🚢 [{boat_name}] {month}월 체크 ({len(days)}일)...")
            
            try:
                self.driver.get(url)
                time.sleep(1.5)
                
                # 앱 설치 팝업 알림 처리 (일부 선사에 나타남)
                try:
                    alert = self.driver.switch_to.alert
                    alert.dismiss()  # 취소 클릭
                    time.sleep(0.3)
                except:
                    pass  # 알림 없으면 무시
                
                for day in days:
                    day_padded = str(day).zfill(2)
                    date_str = f"{year}{month}{day_padded}"
                    
                    is_available, status = self.check_date_availability(date_str, pa_n_uid)
                    
                    if is_available:
                        self.log(f"  🎉 {month}/{day}: ✅ {status}")
                        
                        alert_key = f"{boat_name}-{date_str}"
                        if alert_key not in self.alerted_dates:
                            parsed = urlparse(base_url)
                            domain = f"{parsed.scheme}://{parsed.netloc}"
                            reserve_url = f"{domain}/_core/module/reservation_boat_v5.2_seat1/popup.step1.php?date={date_str}&PA_N_UID={pa_n_uid}"
                            
                            if self.notifier.send_cancellation_alert(
                                boat_name=boat_name,
                                date=f"{year}년 {month}월 {day}일",
                                url=reserve_url,
                                status=status
                            ):
                                self.log(f"  📱 텔레그램 알림 전송!")
                                self.alerted_dates.add(alert_key)
                        
                        available_list.append(f"{month}/{day}")
                    else:
                        if "예약완료" not in status:
                            self.log(f"  📅 {month}/{day}: ❌ {status}")
                            
            except Exception as e:
                self.log(f"  ⚠️ [{boat_name}] 오류: {e}")
        
        return available_list
    
    def check_napoli_boat(self, boat: dict, year: str, month_days: dict):
        """나폴리호 전용 체크 (예약 페이지에서 직접 남은자리 확인)"""
        boat_name = boat['name']
        base_url = boat['base_url']
        pa_n_uid = boat['pa_n_uid']
        
        parsed = urlparse(base_url)
        domain = f"{parsed.scheme}://{parsed.netloc}"
        
        available_list = []
        
        for month, days in month_days.items():
            if not days:
                continue
            
            self.log(f"🚢 [{boat_name}] {month}월 체크 ({len(days)}일)...")
            
            for day in days:
                day_padded = str(day).zfill(2)
                date_str = f"{year}{month}{day_padded}"
                
                # 예약 페이지 직접 접근 (공백 없이)
                reserve_url = domain + "/_core/module/reservation_boat_v3/popup.step1.php?date=" + date_str + "&PA_N_UID=" + pa_n_uid
                
                try:
                    self.driver.get(reserve_url)
                    time.sleep(1.2)
                    
                    # 앱 설치 팝업 알림 처리
                    try:
                        alert = self.driver.switch_to.alert
                        alert.dismiss()
                        time.sleep(0.3)
                    except:
                        pass
                    
                    # 해당 PA_N_UID의 남은자리 확인
                    page_source = self.driver.page_source
                    
                    # PA_N_UID1484 행 전체를 찾아서 남은자리(4번째 td) 추출
                    # 구조: <tr>...<input id="PA_N_UID1484">...<td>배명</td><td>총인원</td><td>남은자리</td></tr>
                    row_pattern = rf'<tr[^>]*>.*?id="PA_N_UID{pa_n_uid}".*?</tr>'
                    row_match = re.search(row_pattern, page_source, re.DOTALL)
                    
                    if row_match:
                        row_html = row_match.group(0)
                        
                        # 해당 행에서 모든 숫자명 패턴 찾기
                        # 총인원은 앞에, 남은자리는 마지막에 있음
                        numbers = re.findall(r'>(\d+)명<', row_html)
                        
                        if len(numbers) >= 2:
                            # 첫번째: 총인원, 두번째: 남은자리
                            remaining = int(numbers[-1])  # 마지막 숫자가 남은자리
                            
                            if remaining >= 1:
                                status = f"남은자리: {remaining}명"
                                self.log(f"  🎉 {month}/{day}: ✅ {status}")
                                
                                alert_key = f"{boat_name}-{date_str}"
                                if alert_key not in self.alerted_dates:
                                    if self.notifier.send_cancellation_alert(
                                        boat_name=boat_name,
                                        date=f"{year}년 {month}월 {day}일",
                                        url=reserve_url,
                                        status=status
                                    ):
                                        self.log(f"  📱 텔레그램 알림 전송!")
                                        self.alerted_dates.add(alert_key)
                                
                                available_list.append(f"{month}/{day}")
                            else:
                                self.log(f"  📅 {month}/{day}: ❌ 예약완료")
                        else:
                            self.log(f"  📅 {month}/{day}: ❌ 정보없음")
                    else:
                        self.log(f"  📅 {month}/{day}: ❌ 정보없음")
                        
                except Exception as e:
                    self.log(f"  ⚠️ {month}/{day}: 오류 - {e}")
        
        return available_list
    
    def run_single_check(self):
        """모든 활성화된 배들을 한 번 체크 (더피싱 + 선상24)"""
        year = self.config['target_year']
        month_days = self.config.get('target_days', {"09": [], "10": [], "11": []})
        
        # 이전 버전 호환 (list -> dict)
        if isinstance(month_days, list):
            month_days = {"09": month_days, "10": [], "11": []}
        
        all_available = []
        
        # 1. 더피싱 선박 체크
        thefishing_boats = self.config.get('thefishing_boats', [])
        enabled_thefishing = [b for b in thefishing_boats if b.get('enabled', False)]
        
        if enabled_thefishing:
            self.log(f"🎣 [더피싱] {len(enabled_thefishing)}개 선박 체크...")
            for boat in enabled_thefishing:
                available = self.check_thefishing_boat(boat, year, month_days)
                if available:
                    all_available.extend([(boat['name'], d) for d in available])
        
        # 2. 선상24 선박 체크
        sunsang24_boats = self.config.get('sunsang24_boats', [])
        enabled_sunsang24 = [b for b in sunsang24_boats if b.get('enabled', False)]
        
        if enabled_sunsang24:
            self.log(f"⛵ [선상24] {len(enabled_sunsang24)}개 선박 체크...")
            for boat in enabled_sunsang24:
                available = self.check_sunsang24_boat(boat, year, month_days)
                if available:
                    all_available.extend([(boat['name'], d) for d in available])
        
        if not enabled_thefishing and not enabled_sunsang24:
            self.log("⚠️ 활성화된 선박이 없습니다!")
        
        return all_available
    
    def check_thefishing_boat(self, boat: dict, year: str, month_days: dict):
        """더피싱 선박 체크 (기존 check_boat 로직)"""
        return self.check_boat(boat, year, month_days)
    
    def check_sunsang24_boat(self, boat: dict, year: str, month_days: dict):
        """선상24 선박 체크"""
        boat_name = boat['name']
        base_url = boat['base_url']  # 예: https://rkclgh.sunsang24.com
        
        available_list = []
        
        for month, days in month_days.items():
            if not days:
                continue
            
            # 선상24 URL 형식: {도메인}/ship/schedule_fleet/{YYYYMM}
            schedule_url = f"{base_url}/ship/schedule_fleet/{year}{month}"
            self.log(f"⛵ [{boat_name}] {month}월 체크 ({len(days)}일)...")
            
            try:
                self.driver.get(schedule_url)
                time.sleep(1.5)
                
                for day in days:
                    day_padded = str(day).zfill(2)
                    date_id = f"d{year}-{month}-{day_padded}"  # 예: d2026-09-01
                    
                    is_available, status = self.check_sunsang24_availability(date_id)
                    
                    if is_available:
                        self.log(f"  🎉 {month}/{day}: ✅ {status}")
                        
                        date_str = f"{year}{month}{day_padded}"
                        alert_key = f"{boat_name}-{date_str}"
                        if alert_key not in self.alerted_dates:
                            reserve_url = schedule_url
                            
                            if self.notifier.send_cancellation_alert(
                                boat_name=boat_name,
                                date=f"{year}년 {month}월 {day}일",
                                url=reserve_url,
                                status=status
                            ):
                                self.log(f"  📱 텔레그램 알림 전송!")
                                self.alerted_dates.add(alert_key)
                        
                        available_list.append(f"{month}/{day}")
                    else:
                        if "예약마감" not in status:
                            self.log(f"  📅 {month}/{day}: ❌ {status}")
                            
            except Exception as e:
                self.log(f"  ⚠️ [{boat_name}] 오류: {e}")
        
        return available_list
    
    def check_sunsang24_availability(self, date_id: str):
        """선상24 날짜별 예약 가능 여부 체크"""
        try:
            # 해당 날짜 테이블 찾기 (id="d2026-09-01")
            date_tables = self.driver.find_elements(By.ID, date_id)
            
            if not date_tables:
                return False, "날짜없음"
            
            date_table = date_tables[0]
            table_html = date_table.get_attribute('innerHTML')
            
            # "바로예약" 버튼이 있으면 예약 가능
            if 'btn_ship_reservation' in table_html and '바로예약' in table_html:
                # 남은 자리 수 추출
                remain_match = re.search(r'남은자리.*?(\d+)명', table_html, re.DOTALL)
                if remain_match:
                    return True, f"남은자리 {remain_match.group(1)}명"
                return True, "예약가능"
            
            # "대기하기" 버튼 또는 "예약마감"이 있으면 예약 불가
            if 'btn_ship_reservation_awaiter' in table_html or '예약마감' in table_html:
                return False, "예약마감"
            
            return False, "정보없음"
            
        except Exception as e:
            return False, f"오류: {e}"
    
    def get_random_interval(self):
        min_sec = self.config.get('check_interval_min', 8) * 60
        max_sec = self.config.get('check_interval_max', 10) * 60
        return random.randint(min_sec, max_sec)
    
    def run(self):
        self.is_running = True
        
        try:
            self.setup_driver()
            
            check_count = 0
            
            while self.is_running:
                check_count += 1
                self.log(f"\n{'='*50}")
                self.log(f"🔍 [{check_count}번째 체크] {datetime.now().strftime('%H:%M:%S')}")
                
                try:
                    available = self.run_single_check()
                    
                    if available:
                        self.log(f"🎣 예약 가능: {available}")
                    else:
                        self.log("😢 현재 예약 가능한 자리 없음")
                    
                except Exception as e:
                    self.log(f"⚠️ 체크 중 오류: {e}")
                
                if not self.is_running:
                    break
                
                interval = self.get_random_interval()
                next_time = datetime.now() + timedelta(seconds=interval)
                self.log(f"⏰ 다음 체크: {next_time.strftime('%H:%M:%S')} ({interval//60}분 {interval%60}초 후)")
                
                for _ in range(interval):
                    if not self.is_running:
                        break
                    time.sleep(1)
        
        except Exception as e:
            self.log(f"🚨 오류 발생: {e}")
        
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
            self.log("🛑 모니터링 종료")
    
    def stop(self):
        self.is_running = False


# ============================================
# 🖥️ GUI
# ============================================
class FishingBoatMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🎣 낚시배 취소석 모니터 v2.0")
        
        w, h = 710, 850
        ws = root.winfo_screenwidth()
        hs = root.winfo_screenheight()
        x = (ws/2) - (w/2)
        y = (hs/2) - (h/2)
        root.geometry('%dx%d+%d+%d' % (w, h, x, y))
        
        self.config = self.load_config()
        self.monitor = None
        self.monitor_thread = None
        
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
        
        # 프로그램 시작 시 모든 선박 OFF 상태로 초기화
        for boat in config.get('boats', []):
            boat['enabled'] = False
        
        return config
    
    def save_config(self):
        self.config['target_year'] = self.entry_year.get()
        
        # 선택된 월들 (날짜가 있는 월만)
        selected_months = [m for m, days in self.month_days.items() if days]
        self.config['target_months'] = selected_months if selected_months else ['09']
        
        # 월별 날짜 저장
        self.config['target_days'] = self.month_days
        
        self.config['check_interval_min'] = int(self.entry_min_interval.get())
        self.config['check_interval_max'] = int(self.entry_max_interval.get())
        self.config['headless_mode'] = self.var_headless.get()
        
        # 선박 목록은 이미 config에 직접 업데이트 됨
        # (버튼 클릭 시 boats[idx]['enabled'] 변경)
        
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)
        
        total_days = sum(len(days) for days in self.month_days.values())
        total_boats = len(self.config.get('thefishing_boats', [])) + len(self.config.get('sunsang24_boats', []))
        self.log_msg(f"💾 설정 저장 완료 (총 {total_days}개 날짜, 선박: {total_boats}개)")
        return self.config
    
    # ========== 프리셋 관련 함수 ==========
    def get_presets_file(self):
        """프리셋 저장 파일 경로"""
        return 'boat_presets.json'
    
    def load_presets(self):
        """저장된 프리셋 목록 불러오기"""
        presets_file = self.get_presets_file()
        if os.path.exists(presets_file):
            try:
                with open(presets_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_presets(self, presets):
        """프리셋 목록 저장"""
        with open(self.get_presets_file(), 'w', encoding='utf-8') as f:
            json.dump(presets, f, indent=2, ensure_ascii=False)
    
    def refresh_preset_list(self):
        """프리셋 드롭다운 목록 새로고침"""
        presets = self.load_presets()
        preset_names = list(presets.keys())
        if hasattr(self, 'preset_combo'):
            self.preset_combo['values'] = preset_names
            if preset_names:
                self.preset_var.set('')
    
    def save_preset(self):
        """현재 선택된 선박들을 프리셋으로 저장 (두 플랫폼 + 날짜)"""
        preset_name = self.entry_preset_name.get().strip()
        if not preset_name or preset_name == "프리셋 이름":
            messagebox.showwarning("경고", "프리셋 이름을 입력하세요!")
            return
        
        # 두 플랫폼의 활성화된 선박들 수집
        thefishing_boats = self.config.get('thefishing_boats', [])
        sunsang24_boats = self.config.get('sunsang24_boats', [])
        
        enabled_thefishing = [b['name'] for b in thefishing_boats if b.get('enabled', False)]
        enabled_sunsang24 = [b['name'] for b in sunsang24_boats if b.get('enabled', False)]
        
        total_enabled = len(enabled_thefishing) + len(enabled_sunsang24)
        
        if total_enabled == 0:
            messagebox.showwarning("경고", "선택된 선박이 없습니다!")
            return
        
        # 프리셋 저장 (두 플랫폼 + 날짜)
        presets = self.load_presets()
        presets[preset_name] = {
            'thefishing_boats': enabled_thefishing,
            'sunsang24_boats': enabled_sunsang24,
            'target_year': self.entry_year.get(),
            'target_days': dict(self.month_days)  # 월별 날짜 저장
        }
        self.save_presets(presets)
        
        # 드롭다운 업데이트
        self.refresh_preset_list()
        self.preset_var.set(preset_name)
        
        total_days = sum(len(days) for days in self.month_days.values())
        self.log_msg(f"💾 프리셋 저장: '{preset_name}' (더피싱:{len(enabled_thefishing)}개, 선상24:{len(enabled_sunsang24)}개, 날짜:{total_days}개)")
        messagebox.showinfo("저장 완료", f"프리셋 '{preset_name}'이(가) 저장되었습니다.\n(더피싱:{len(enabled_thefishing)}개, 선상24:{len(enabled_sunsang24)}개, 날짜:{total_days}개)")
    
    def load_preset(self, event=None):
        """선택된 프리셋 불러오기 (두 플랫폼 + 날짜)"""
        preset_name = self.preset_var.get()
        if not preset_name:
            return
        
        presets = self.load_presets()
        if preset_name not in presets:
            return
        
        preset = presets[preset_name]
        
        # 이전 버전 호환 (단일 플랫폼 형식)
        if 'platform' in preset:
            platform = preset.get('platform', 'thefishing')
            enabled_boats = preset.get('boats', [])
            preset = {
                'thefishing_boats': enabled_boats if platform == 'thefishing' else [],
                'sunsang24_boats': enabled_boats if platform == 'sunsang24' else []
            }
        
        enabled_thefishing = preset.get('thefishing_boats', [])
        enabled_sunsang24 = preset.get('sunsang24_boats', [])
        
        # 더피싱 선박 처리
        thefishing_boats = self.config.get('thefishing_boats', [])
        for boat in thefishing_boats:
            boat['enabled'] = boat['name'] in enabled_thefishing
        
        # 선상24 선박 처리
        sunsang24_boats = self.config.get('sunsang24_boats', [])
        for boat in sunsang24_boats:
            boat['enabled'] = boat['name'] in enabled_sunsang24
        
        # 날짜 정보 불러오기
        if 'target_year' in preset:
            self.entry_year.delete(0, tk.END)
            self.entry_year.insert(0, preset['target_year'])
        
        if 'target_days' in preset:
            self.month_days = preset['target_days']
            # 월별 날짜 라벨 업데이트
            for month_str, lbl in self.month_labels.items():
                days_count = len(self.month_days.get(month_str, []))
                lbl.config(text=f"{days_count}개")
            # 요약 업데이트
            self.lbl_days_summary.config(text=self.get_days_summary())
        
        # UI 업데이트
        self.refresh_boat_grid()
        
        activated_tf = sum(1 for b in thefishing_boats if b.get('enabled'))
        activated_ss = sum(1 for b in sunsang24_boats if b.get('enabled'))
        total_days = sum(len(days) for days in self.month_days.values())
        self.log_msg(f"📂 프리셋 로드: '{preset_name}' (더피싱:{activated_tf}개, 선상24:{activated_ss}개, 날짜:{total_days}개)")
    
    def delete_preset(self):
        """선택된 프리셋 삭제"""
        preset_name = self.preset_var.get()
        if not preset_name:
            messagebox.showwarning("경고", "삭제할 프리셋을 선택하세요!")
            return
        
        if not messagebox.askyesno("확인", f"프리셋 '{preset_name}'을(를) 삭제하시겠습니까?"):
            return
        
        presets = self.load_presets()
        if preset_name in presets:
            del presets[preset_name]
            self.save_presets(presets)
        
        self.refresh_preset_list()
        self.preset_var.set('')
        self.log_msg(f"🗑 프리셋 삭제: '{preset_name}'")
    
    def create_widgets(self):
        style = ttk.Style()
        style.configure('TLabel', font=('맑은 고딕', 10))
        style.configure('TButton', font=('맑은 고딕', 10, 'bold'))
        
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 1. 선박 관리
        boat_frame = ttk.LabelFrame(main_frame, text="🚢 선박 관리", padding="5")
        boat_frame.pack(fill=tk.X, pady=5)
        
        # 플랫폼 선택 버튼
        platform_row = ttk.Frame(boat_frame)
        platform_row.pack(fill=tk.X, pady=2)
        
        ttk.Label(platform_row, text="플랫폼:").pack(side=tk.LEFT, padx=2)
        
        current_platform = self.config.get('current_platform', 'thefishing')
        
        self.btn_thefishing = tk.Button(
            platform_row, text="더피싱", width=10,
            bg='#4CAF50' if current_platform == 'thefishing' else 'SystemButtonFace',
            fg='white' if current_platform == 'thefishing' else 'black',
            command=lambda: self.switch_platform('thefishing')
        )
        self.btn_thefishing.pack(side=tk.LEFT, padx=2)
        
        self.btn_sunsang24 = tk.Button(
            platform_row, text="선상24", width=10,
            bg='#4CAF50' if current_platform == 'sunsang24' else 'SystemButtonFace',
            fg='white' if current_platform == 'sunsang24' else 'black',
            command=lambda: self.switch_platform('sunsang24')
        )
        self.btn_sunsang24.pack(side=tk.LEFT, padx=2)
        
        # 선박 추가 입력
        add_row = ttk.Frame(boat_frame)
        add_row.pack(fill=tk.X, pady=2)
        
        ttk.Label(add_row, text="선박명:").pack(side=tk.LEFT, padx=2)
        self.entry_boat_name = ttk.Entry(add_row, width=12)
        self.entry_boat_name.pack(side=tk.LEFT, padx=2)
        
        ttk.Label(add_row, text="URL:").pack(side=tk.LEFT, padx=2)
        self.entry_boat_url = ttk.Entry(add_row, width=35)
        self.entry_boat_url.pack(side=tk.LEFT, padx=2)
        
        ttk.Button(add_row, text="➕ 추가", command=self.add_boat, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Button(add_row, text="🗑 삭제", command=self.delete_selected_boat, width=8).pack(side=tk.LEFT, padx=2)
        
        # 선박 버튼 그리드 (6열 x 10행)
        grid_frame = ttk.Frame(boat_frame)
        grid_frame.pack(fill=tk.X, pady=5)
        
        self.boat_buttons = {}  # {boat_name: button}
        self.selected_boat = None  # 현재 선택된 선박 (사이트가기용)
        
        # 선박 관리 버튼
        btn_row = ttk.Frame(boat_frame)
        btn_row.pack(fill=tk.X, pady=2)
        
        self.btn_select_all = tk.Button(btn_row, text="☑ 전체선택", command=self.toggle_all_boats, width=10, bg='SystemButtonFace', fg='black')
        self.btn_select_all.pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="🌐 사이트가기", command=self.open_boat_site, width=12).pack(side=tk.LEFT, padx=2)
        
        # 월 선택 버튼 (사이트가기용)
        ttk.Label(btn_row, text="  ").pack(side=tk.LEFT)
        
        self.selected_site_month = tk.StringVar(value="09")
        self.month_buttons = {}
        
        for m in [9, 10, 11]:
            month_str = f"{m:02d}"
            btn = tk.Button(
                btn_row, 
                text=f"{m}월", 
                width=4,
                bg="#4CAF50" if m == 9 else "SystemButtonFace",
                fg="white" if m == 9 else "black",
                command=lambda ms=month_str: self.select_site_month(ms)
            )
            btn.pack(side=tk.LEFT, padx=1)
            self.month_buttons[month_str] = btn
        
        # 프리셋 저장/불러오기 UI
        # 프리셋 드롭다운
        self.preset_var = tk.StringVar()
        self.preset_combo = ttk.Combobox(btn_row, textvariable=self.preset_var, width=15, state='readonly')
        self.preset_combo.pack(side=tk.LEFT, padx=(5,2))
        self.preset_combo.bind('<<ComboboxSelected>>', self.load_preset)
        self.refresh_preset_list()
        
        # 프리셋 이름 입력
        self.entry_preset_name = ttk.Entry(btn_row, width=15)
        self.entry_preset_name.pack(side=tk.LEFT, padx=2)
        self.entry_preset_name.insert(0, "프리셋 이름")
        self.entry_preset_name.bind('<FocusIn>', lambda e: self.entry_preset_name.delete(0, tk.END) if self.entry_preset_name.get() == "프리셋 이름" else None)
        
        # 저장 버튼
        ttk.Button(btn_row, text="💾저장", command=self.save_preset, width=6).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text="🗑", command=self.delete_preset, width=3).pack(side=tk.LEFT, padx=1)
        
        # 선박 버튼 그리드 생성
        self.grid_frame = grid_frame
        self.refresh_boat_grid()
        
        # 3. 모니터링 대상 설정
        target_frame = ttk.LabelFrame(main_frame, text="🎯 모니터링 대상", padding="5")
        target_frame.pack(fill=tk.X, pady=5)
        
        date_row = ttk.Frame(target_frame)
        date_row.pack(fill=tk.X, pady=2)
        
        ttk.Label(date_row, text="년도:").pack(side=tk.LEFT, padx=5)
        self.entry_year = ttk.Entry(date_row, width=6)
        self.entry_year.insert(0, self.config.get('target_year', '2026'))
        self.entry_year.pack(side=tk.LEFT, padx=2)
        
        # 월별 캘린더 버튼 (9~11월)
        month_row = ttk.Frame(target_frame)
        month_row.pack(fill=tk.X, pady=5)
        
        ttk.Label(month_row, text="날짜 선택:").pack(side=tk.LEFT, padx=5)
        
        # 월별 선택 날짜 저장 (딕셔너리)
        self.month_days = self.config.get('target_days', {"09": [], "10": [], "11": []})
        if isinstance(self.month_days, list):  # 이전 버전 호환
            self.month_days = {"09": self.month_days, "10": [], "11": []}
        
        self.month_labels = {}
        
        for month in [9, 10, 11]:
            month_str = f"{month:02d}"
            btn_frame = ttk.Frame(month_row)
            btn_frame.pack(side=tk.LEFT, padx=5)
            
            # 월 버튼
            btn = ttk.Button(
                btn_frame, 
                text=f"📅 {month}월", 
                command=lambda m=month: self.open_calendar(m)
            )
            btn.pack(side=tk.TOP)
            
            # 선택된 날짜 수 표시
            days_count = len(self.month_days.get(month_str, []))
            lbl = ttk.Label(btn_frame, text=f"{days_count}개", foreground="blue")
            lbl.pack(side=tk.TOP)
            self.month_labels[month_str] = lbl
        
        # 선택된 날짜 요약
        summary_row = ttk.Frame(target_frame)
        summary_row.pack(fill=tk.X, pady=2)
        
        self.lbl_days_summary = ttk.Label(summary_row, text=self.get_days_summary(), 
                                          foreground="gray", wraplength=600)
        self.lbl_days_summary.pack(anchor='w', padx=5)
        
        # 4. 체크 간격 설정
        interval_frame = ttk.LabelFrame(main_frame, text="⏰ 체크 간격", padding="5")
        interval_frame.pack(fill=tk.X, pady=5)
        
        interval_row = ttk.Frame(interval_frame)
        interval_row.pack(fill=tk.X, pady=2)
        
        ttk.Label(interval_row, text="최소:").pack(side=tk.LEFT, padx=5)
        self.entry_min_interval = ttk.Entry(interval_row, width=4)
        self.entry_min_interval.insert(0, str(self.config.get('check_interval_min', 8)))
        self.entry_min_interval.pack(side=tk.LEFT, padx=2)
        ttk.Label(interval_row, text="분").pack(side=tk.LEFT)
        
        ttk.Label(interval_row, text="   최대:").pack(side=tk.LEFT, padx=5)
        self.entry_max_interval = ttk.Entry(interval_row, width=4)
        self.entry_max_interval.insert(0, str(self.config.get('check_interval_max', 10)))
        self.entry_max_interval.pack(side=tk.LEFT, padx=2)
        ttk.Label(interval_row, text="분").pack(side=tk.LEFT)
        
        self.var_headless = tk.BooleanVar(value=self.config.get('headless_mode', True))
        ttk.Checkbutton(interval_frame, text="👻 헤드리스 모드 (백그라운드 실행)", 
                        variable=self.var_headless).pack(anchor='w', padx=5, pady=2)
        
        # 5. 버튼
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(btn_frame, text="💾 설정 저장", command=self.save_config).pack(side=tk.LEFT, padx=5)
        
        self.btn_start = ttk.Button(btn_frame, text="🚀 모니터링 시작", command=self.start_monitor)
        self.btn_start.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.btn_stop = ttk.Button(btn_frame, text="🛑 중지", command=self.stop_monitor, state="disabled")
        self.btn_stop.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # 6. 로그창
        log_frame = ttk.LabelFrame(main_frame, text="📝 모니터링 로그", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_area = scrolledtext.ScrolledText(log_frame, height=12, state='disabled', font=("Consolas", 9))
        self.log_area.pack(fill=tk.BOTH, expand=True)
        
        self.log_msg("=" * 50)
        self.log_msg("🎣 낚시배 취소석 모니터 v2.0")
        self.log_msg("=" * 50)
        self.log_msg("1. 텔레그램 설정을 입력하세요")
        self.log_msg("2. 선박을 추가하세요 (이름 + URL)")
        self.log_msg("3. 📅 버튼을 눌러 날짜를 선택하세요")
        self.log_msg("4. '모니터링 시작' 버튼을 클릭하세요")
        self.log_msg("")
    
    def open_calendar(self, month: int):
        """캘린더 팝업 열기"""
        year = int(self.entry_year.get())
        month_str = f"{month:02d}"
        current_days = self.month_days.get(month_str, [])
        
        CalendarPopup(
            self.root,
            year=year,
            month=month,
            selected_days=current_days,
            callback=lambda m, days: self.on_calendar_select(m, days)
        )
    
    def on_calendar_select(self, month: int, days: list):
        """캘린더에서 날짜 선택 완료"""
        month_str = f"{month:02d}"
        self.month_days[month_str] = days
        
        # 라벨 업데이트
        if month_str in self.month_labels:
            self.month_labels[month_str].config(text=f"{len(days)}개")
        
        # 요약 업데이트
        self.lbl_days_summary.config(text=self.get_days_summary())
        
        self.log_msg(f"📅 {month}월: {len(days)}개 날짜 선택됨")
    
    def get_days_summary(self):
        """선택된 날짜 요약 텍스트"""
        parts = []
        for month in [9, 10, 11]:
            month_str = f"{month:02d}"
            days = self.month_days.get(month_str, [])
            if days:
                sorted_days = sorted([int(d) for d in days])
                if len(sorted_days) > 5:
                    days_text = ', '.join(map(str, sorted_days[:5])) + f"... (+{len(sorted_days)-5})"
                else:
                    days_text = ', '.join(map(str, sorted_days))
                parts.append(f"{month}월: {days_text}")
        
        if not parts:
            return "💡 위의 📅 버튼을 눌러 날짜를 선택하세요"
        return " | ".join(parts)
    
    def add_boat(self):
        """선박 추가"""
        name = self.entry_boat_name.get().strip()
        url = self.entry_boat_url.get().strip()
        
        if not name or not url:
            messagebox.showwarning("경고", "선박명과 URL을 입력해주세요.")
            return
        
        platform = self.config.get('current_platform', 'thefishing')
        
        try:
            parsed = urlparse(url)
            domain = f"{parsed.scheme}://{parsed.netloc}"
            
            if platform == 'thefishing':
                # 더피싱: PA_N_UID 필요
                params = parse_qs(parsed.query)
                pa_n_uid = params.get('PA_N_UID', [''])[0]
                
                if not pa_n_uid:
                    messagebox.showwarning("경고", "URL에서 PA_N_UID를 찾을 수 없습니다.\n예시: ...&PA_N_UID=1190")
                    return
                
                base_url = f"{domain}/index.php"
                boat = {
                    "name": name,
                    "enabled": True,
                    "base_url": base_url,
                    "pa_n_uid": pa_n_uid
                }
                self.log_msg(f"✅ [더피싱] 선박 추가: {name} (PA_N_UID: {pa_n_uid})")
                
            else:  # sunsang24
                # 선상24: 도메인만 필요 (예: https://rkclgh.sunsang24.com)
                boat = {
                    "name": name,
                    "enabled": True,
                    "base_url": domain  # 도메인만 저장
                }
                self.log_msg(f"✅ [선상24] 선박 추가: {name} ({domain})")
            
            # 현재 플랫폼의 선박 목록에 추가
            boat_key = f"{platform}_boats"
            if boat_key not in self.config:
                self.config[boat_key] = []
            
            self.config[boat_key].append(boat)
            self.refresh_boat_grid()
            
            self.entry_boat_name.delete(0, tk.END)
            self.entry_boat_url.delete(0, tk.END)
            
        except Exception as e:
            messagebox.showerror("오류", f"URL 파싱 오류: {e}")
    
    def refresh_boat_grid(self):
        """선박 버튼 그리드 새로고침"""
        # 기존 버튼 모두 제거
        for widget in self.grid_frame.winfo_children():
            widget.destroy()
        
        self.boat_buttons = {}
        boats = self.get_current_boats()
        enabled_count = 0
        
        # 8열 그리드 생성
        cols = 8
        for i, boat in enumerate(boats):
            row = i // cols
            col = i % cols
            enabled = boat.get('enabled', False)
            if enabled:
                enabled_count += 1
            
            # 버튼 이름 (너무 길면 자르기)
            name = boat['name']
            if len(name) > 7:
                name = name[:6] + ".."
            
            btn = tk.Button(
                self.grid_frame,
                text=name,
                width=10,
                height=1,
                bg='#4CAF50' if enabled else 'SystemButtonFace',
                fg='white' if enabled else 'black',
                font=('맑은 고딕', 10),
                command=lambda idx=i: self.toggle_boat_by_index(idx)
            )
            btn.grid(row=row, column=col, padx=2, pady=2)
            
            # 우클릭으로 사이트가기용 선택
            btn.bind('<Button-3>', lambda e, idx=i: self.select_boat_for_site(idx))
            
            self.boat_buttons[boat['name']] = btn
        
        # 전체선택 버튼 색상 업데이트 (모든 선박이 ON일 때만 녹색)
        if hasattr(self, 'btn_select_all'):
            if len(boats) > 0 and enabled_count == len(boats):
                self.btn_select_all.config(bg='#4CAF50', fg='white')
            else:
                self.btn_select_all.config(bg='SystemButtonFace', fg='black')
    
    def get_current_boats(self):
        """현재 플랫폼의 선박 목록 반환"""
        platform = self.config.get('current_platform', 'thefishing')
        if platform == 'thefishing':
            return self.config.get('thefishing_boats', [])
        else:
            return self.config.get('sunsang24_boats', [])
    
    def switch_platform(self, platform):
        """플랫폼 전환"""
        self.config['current_platform'] = platform
        
        # 버튼 색상 업데이트
        if platform == 'thefishing':
            self.btn_thefishing.config(bg='#4CAF50', fg='white')
            self.btn_sunsang24.config(bg='SystemButtonFace', fg='black')
        else:
            self.btn_thefishing.config(bg='SystemButtonFace', fg='black')
            self.btn_sunsang24.config(bg='#4CAF50', fg='white')
        
        # 그리드 새로고침
        self.selected_boat = None
        self.refresh_boat_grid()
        
        platform_name = "더피싱" if platform == 'thefishing' else "선상24"
        self.log_msg(f"🔄 플랫폼 전환: {platform_name}")
    
    def toggle_boat_by_index(self, idx):
        """인덱스로 선박 ON/OFF 토글"""
        boats = self.get_current_boats()
        if idx < len(boats):
            # 먼저 선택 설정 (사이트가기용)
            self.selected_boat = idx
            
            # 토글
            boats[idx]['enabled'] = not boats[idx].get('enabled', False)
            self.refresh_boat_grid()
            
            self.log_msg(f"🎯 {boats[idx]['name']} 선택됨")
    
    def select_boat_for_site(self, idx):
        """사이트가기용 선박 선택 (우클릭)"""
        self.selected_boat = idx
        boats = self.get_current_boats()
        if idx < len(boats):
            self.log_msg(f"🎯 {boats[idx]['name']} 선택됨 (사이트가기)")
    
    def toggle_all_boats(self):
        """전체 선박 ON/OFF 토글"""
        boats = self.get_current_boats()
        if not boats:
            return
        
        # 현재 ON인 선박이 있으면 전체 OFF, 없으면 전체 ON
        any_enabled = any(b.get('enabled', False) for b in boats)
        
        for boat in boats:
            boat['enabled'] = not any_enabled
        
        self.refresh_boat_grid()
        
        status = "OFF" if any_enabled else "ON"
        self.log_msg(f"☑ 전체 선박 {status}")
    
    def delete_selected_boat(self):
        """선택된 선박 삭제"""
        if self.selected_boat is None:
            messagebox.showwarning("경고", "삭제할 선박을 먼저 클릭하세요.")
            return
        
        boats = self.get_current_boats()
        if self.selected_boat < len(boats):
            deleted = boats.pop(self.selected_boat)
            self.selected_boat = None
            self.refresh_boat_grid()
            self.log_msg(f"🗑️ 선박 삭제: {deleted['name']}")
    
    def open_boat_site(self):
        """활성화된 모든 선박의 캘린더 사이트 열기"""
        import webbrowser
        
        boats = self.get_current_boats()
        enabled_boats = [b for b in boats if b.get('enabled', False)]
        
        if not enabled_boats:
            messagebox.showwarning("경고", "활성화된 선박이 없습니다.")
            return
        
        year = self.entry_year.get()
        month = self.selected_site_month.get()
        platform = self.config.get('current_platform', 'thefishing')
        
        opened_count = 0
        for boat in enabled_boats:
            if platform == 'thefishing':
                url = f"{boat['base_url']}?mid=bk&year={year}&month={month}&day=01&mode=cal&PA_N_UID={boat['pa_n_uid']}#list"
            else:  # sunsang24
                url = f"{boat['base_url']}/ship/schedule_fleet/{year}{month}"
            
            webbrowser.open(url)
            opened_count += 1
        
        self.log_msg(f"🌐 {opened_count}개 선박 사이트 열림 ({int(month)}월)")
    
    def select_site_month(self, month_str):
        """사이트가기용 월 선택"""
        self.selected_site_month.set(month_str)
        
        # 버튼 색상 업데이트
        for ms, btn in self.month_buttons.items():
            if ms == month_str:
                btn.config(bg="#4CAF50", fg="white")
            else:
                btn.config(bg="SystemButtonFace", fg="black")
    
    def log_msg(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        full_msg = f"[{timestamp}] {msg}\n"
        
        def _update():
            self.log_area.config(state='normal')
            self.log_area.insert(tk.END, full_msg)
            self.log_area.see(tk.END)
            self.log_area.config(state='disabled')
        
        self.root.after(0, _update)
    
    def test_telegram(self):
        """텔레그램 테스트"""
        token = self.config.get('telegram_token', '')
        chat_id = self.config.get('telegram_chat_id', '')
        
        notifier = TelegramNotifier(token, chat_id)
        if notifier.send_message("🎣 낚시배 취소석 모니터 테스트 메시지입니다!"):
            self.log_msg("✅ 텔레그램 테스트 성공!")
            messagebox.showinfo("성공", "텔레그램 메시지가 전송되었습니다!")
        else:
            self.log_msg("❌ 텔레그램 테스트 실패")
            messagebox.showerror("실패", "텔레그램 전송에 실패했습니다.")
    
    def start_monitor(self):
        config = self.save_config()
        
        if not config['target_days']:
            messagebox.showwarning("경고", "감시할 날짜를 입력해주세요.")
            return
        
        # 두 플랫폼에서 활성화된 선박 체크
        thefishing_enabled = [b for b in config.get('thefishing_boats', []) if b.get('enabled', False)]
        sunsang24_enabled = [b for b in config.get('sunsang24_boats', []) if b.get('enabled', False)]
        enabled_boats = thefishing_enabled + sunsang24_enabled
        
        if not enabled_boats:
            messagebox.showwarning("경고", "활성화된 선박이 없습니다.")
            return
        
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        
        self.log_msg("")
        self.log_msg("🚀 모니터링 시작!")
        if thefishing_enabled:
            self.log_msg(f"🎣 [더피싱] {len(thefishing_enabled)}개: {[b['name'] for b in thefishing_enabled]}")
        if sunsang24_enabled:
            self.log_msg(f"⛵ [선상24] {len(sunsang24_enabled)}개: {[b['name'] for b in sunsang24_enabled]}")
        self.log_msg(f"📅 월: {config['target_months']}")
        self.log_msg(f"📆 날짜: {config['target_days']}")
        
        self.monitor = FishingBoatMonitor(self.log_msg, config)
        self.monitor_thread = threading.Thread(target=self.monitor.run, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitor(self):
        if self.monitor:
            self.monitor.stop()
        
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")
        self.log_msg("🛑 모니터링 중지 요청됨")


# ============================================
# 🚀 실행
# ============================================
if __name__ == "__main__":
    root = tk.Tk()
    app = FishingBoatMonitorApp(root)
    root.mainloop()
