import re
import time
import requests
import sys
import json
import os
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# =============================================================================
# 🚀 장현호 API(Packet) 봇 - (초고속 버전: AJAX 생략 + GUI 연동)
# =============================================================================
#
# [설명]
# Requests(패킷) 방식으로 '장현호'를 예약합니다.
# **최적화**: AJAX 좌석 조회 단계를 생략하고 바로 예약 요청(Action)을 보냅니다.
# **GUI 연동**: launcher로부터 설정 파일 경로를 인자로 받아 동적으로 실행됩니다.
#
# [사용법]
# python "장현호_Bot - 복사본.py" [config_file_path]
# =============================================================================

# 1. 오닉스호 기본 정보 (xn--bj1bs41a0scq4w.kr / v5.1)
BASE_URL = "http://xn--bj1bs41a0scq4w.kr/_core/module/reservation_boat_v5.1"
PA_N_UID = "4046"  # 오닉스호 고유 ID

# 기본 설정 (GUI 연동 시 덮어씌워짐)
TARGET_TIME = "00:00:00"
TEST_MODE = False
DRY_RUN = False

# 기본 예약 계획 (GUI 연동 시 덮어씌워짐)
RESERVATIONS_PLAN = {
    # 예시: 2026년 10월 1일 예약
    "20261001": [
        {
            "seats": 1,
            "person_info": {
                "PA_N_UID": PA_N_UID,
                "PH_N_UID": "0",
                "BI_NAME": "김선재",
                "BI_BANK": "",
                "BI_TEL2": "1526",  # 뒷번호
                "BI_TEL3": "5638",  # 끝번호
                "seat_preference": [1, 2, 3, 4, 13, 14, 15], 
            },
        },
    ]
}

# 5. 어종 자동 선택 키워드
SEARCH_KEYWORDS = ["주꾸미", "쭈꾸미", "갑오징어", "쭈갑", "문어"]

# 6. 네트워크 설정
REQUEST_TIMEOUT = (3, 5)

# ─────────────────────────────────────────────────────────────────────────────
# Config Loader (GUI Support)
# ─────────────────────────────────────────────────────────────────────────────
def load_config_from_file():
    global TARGET_TIME, TEST_MODE, DRY_RUN, RESERVATIONS_PLAN
    
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                print(f"📂 [설정로드] {config_path}")
                
                # 1. Global Settings
                TARGET_TIME = config.get('target_time', TARGET_TIME)
                # GUI의 Test Mode는 '시간 무시' 등을 포함하므로 여기선 TEST_MODE(전송생략)와 매핑
                # 하지만 봇 내부 TEST_MODE는 '전송 생략' 의미가 강함.
                # Launcher의 'simulation_mode'가 여기의 DRY_RUN/TEST_MODE에 해당
                if config.get('simulation_mode', False):
                    TEST_MODE = True
                    DRY_RUN = True
                else:
                    TEST_MODE = False
                    DRY_RUN = False
                    
                # 2. Reservation Date & User Info (from multi_instance if available, else standard)
                # Launcher passes a specific temp file for *this* instance usually?
                # Actually Launcher passes the *Unified Config*. 
                # We need to find *our* slot configuration from 'multi_instance' list?
                # OR, the launcher creates a *temporary config* specific to this bot instance.
                # Based on launcher code: `temp_data = base_data.copy()` ... `do_run_bot(..., temp_config_path)`
                # It passes a full config. We usually assume the *first* enabled slot or specific one?
                # Wait, the launcher logic loop: `for grid_idx, (i, slot) in enumerate(enabled_slots): ... create temp json ... run`
                # So the JSON file passed to us corresponds to ONE specific slot (it seems).
                # But let's check the launcher code `start_bot`:
                # It copies `base_data` then OVERWRITES `target_time`, and sets `multi_instance` to ONLY [current_slot_data].
                # So `config['multi_instance']` will have exactly 1 item.
                
                multi = config.get('multi_instance', [])
                if multi:
                    item = multi[0] # The one specific item for this bot instance
                    
                    target_date = item.get('date', '')
                    seats_n = int(item.get('person_count', 1))
                    u_name = item.get('user_name', '')
                    u_phone = item.get('user_phone', '')
                    
                    # Parse Phone
                    p2, p3 = "0000", "0000"
                    parts = u_phone.split('-')
                    if len(parts) >= 3:
                        p2, p3 = parts[1], parts[2]
                        
                    # Re-build RESERVATIONS_PLAN
                    RESERVATIONS_PLAN = {
                        target_date: [
                            {
                                "seats": seats_n,
                                "person_info": {
                                    "PA_N_UID": PA_N_UID,
                                    "PH_N_UID": "0",
                                    "BI_NAME": u_name,
                                    "BI_BANK": "", # Not used for auto-bank
                                    "BI_TEL2": p2,
                                    "BI_TEL3": p3,
                                    "seat_preference": [1, 2, 3, 4, 13, 14, 15], # Default pref
                                }
                            }
                        ]
                    }
                    print(f"📅 [설정적용] 날짜: {target_date}, 인원: {seats_n}명, 이름: {u_name}")
                    
            except Exception as e:
                print(f"⚠️ 설정 로드 실패: {e}")
        else:
            print("⚠️ 설정 파일이 존재하지 않습니다.")

# ─────────────────────────────────────────────────────────────────────────────
# Core Logic
# ─────────────────────────────────────────────────────────────────────────────

def build_session():
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Connection": "keep-alive",
        "X-Requested-With": "XMLHttpRequest", 
        "Origin": "http://xn--bj1bs41a0scq4w.kr"
    })
    retry = Retry(total=2, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("http://", adapter)
    return s

def wait_until_target_time(target_time_str):
    print(f"⏰ 타겟 시간 대기 중: {target_time_str}")
    while True:
        now_str = time.strftime("%H:%M:%S")
        if now_str >= target_time_str:
            break
        time.sleep(0.1)

# Helper Functions (Regex Only - Faster)
def parse_naun(html):
    # 1. Try input hidden with regex
    m = re.search(r'name="naun"\s+value="(\d+)"', html)
    if m: return m.group(1)
    
    # 2. Try span id="id_bi_in" with regex
    m2 = re.search(r'<span id="id_bi_in">\s*(\d+)\s*</span>', html)
    if m2: return m2.group(1)
        
    return "1"

def find_ps_n_uid(html, keywords):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    radios = soup.find_all("input", {"type": "radio", "name": "PS_N_UID"})
    if not radios: return None
    
    if len(radios) == 1:
        return radios[0].get("value")
        
    for r in radios:
        parent = r.find_parent(["label", "tr", "td"])
        if parent:
            text = parent.get_text()
            if any(k in text for k in keywords):
                return r.get("value")
                
        rid = r.get("id")
        if rid:
            linked_label = soup.find("label", {"for": rid})
            if linked_label:
                text = linked_label.get_text()
                if any(k in text for k in keywords):
                    return r.get("value")

    return radios[0].get("value") if radios else None

# Main Reservation Function
def do_reservation(session, date, job):
    info = job["person_info"]
    seats_needed = job["seats"]
    ph_n_uid = info.get("PH_N_UID", "0")
    
    print(f"🚀 [시작] 예약 시도: {date} (필요: {seats_needed}석)")

    # 1. Step1 Page Load (SCR=0) - [PRE-SELECTION]
    step_start = time.time()
    url_1 = f"{BASE_URL}/popup.step1.php?date={date}&PA_N_UID={PA_N_UID}&scr=0"
    session.headers.update({"Referer": url_1}) 
    r = session.get(url_1, timeout=REQUEST_TIMEOUT)
    print(f"⏱️ [Step 1-1] 초기 로드(어종파악): {time.time() - step_start:.4f}초")
    
    ps_uid = find_ps_n_uid(r.text, SEARCH_KEYWORDS)
    if not ps_uid:
        print(f"❌ [실패] 어종 선택 불가 ({date})")
        return False

    # =============== [TOTAL TIME START] =================
    # 어종 선택(클릭) 직전부터 시간을 챕니다.
    total_start_time = time.time()

    # 2. Step1 Page Load (SCR=1) - [SELECTION APPLIED]
    # 여기서 naun(잔여석)을 구합니다.
    step_start = time.time()
    url_2 = f"{BASE_URL}/popup.step1.php?date={date}&PA_N_UID={PA_N_UID}&PH_N_UID={ph_n_uid}&PS_N_UID={ps_uid}&scr=1"
    session.headers.update({"Referer": url_1})
    
    r = session.get(url_2, timeout=REQUEST_TIMEOUT)
    html_step1 = r.text
    naun = parse_naun(html_step1)
    
    duration_step1_2 = time.time() - step_start
    print(f"⏱️ [Step 1-2] 어종 선택 및 정보 로드: {duration_step1_2:.4f}초 (잔여석: {naun})")
    
    # 3. AJAX SKIP (Optimization)
    # print("⏩ [SpeedUp] AJAX 좌석 조회 생략 (1 RTT 절약)")

    # 4. Logic (No Seat Selection)
    step_start = time.time()
    # 좌석 선택 로직 생략 -> 바로 빈 값으로 설정
    
    # 5. Submit Payload
    payload = [
        ("action", "insert"),
        ("link", f"%2F_core%2Fmodule%2Freservation_boat_v5.1%2Fpopu2.step2.php"), 
        ("temp_bi_stat", "확인"),
        ("date", date),
        ("PA_N_UID", PA_N_UID),
        ("PH_N_UID", ph_n_uid),
        ("PS_N_UID", ps_uid),
        ("BI_IN", str(seats_needed)),
        ("BI_SO_IN", "N"),
        ("pay_method", "undefined"),
        ("naun", naun),
        ("BI_NAME", info["BI_NAME"]),
        ("BI_BANK", info["BI_BANK"]),
        ("BI_TEL1", "010"),
        ("BI_TEL2", info["BI_TEL2"]),
        ("BI_TEL3", info["BI_TEL3"]),
        ("BI_MEMO", ""),
        ("agree", "Y"),
        ("BI_3JA", "1"),
        ("BI_AD", "1"),
        ("all_agree", "Y"),
    ]
    
    duration_logic = time.time() - step_start
    print(f"⏱️ [Step 3] 로직 처리: {duration_logic:.4f}초")
    
    if TEST_MODE or DRY_RUN:
        print("🧪 [테스트] 실전송 생략됨 (TEST_MODE/DRY_RUN=True)")
        print(f"⏱️ [Total] 총 소요 시간(어종선택부터): {time.time() - total_start_time:.4f}초")
        return True
        
    # 6. Action!
    step_start = time.time()
    url_action = f"{BASE_URL}/action/popu2.step1.action.php"
    session.headers.update({"Referer": url_2})
    
    try:
        res = session.post(url_action, data=payload, timeout=REQUEST_TIMEOUT)
        duration_action = time.time() - step_start
        print(f"⏱️ [Step 4] 최종 전송: {duration_action:.4f}초")
        
        if res.status_code == 200:
            print(f"🚀 [전송완료] Status: {res.status_code}")
            print(f"⏱️ [Total] 총 소요 시간(어종선택부터): {time.time() - total_start_time:.4f}초")
            return True
        else:
            print(f"❌ [전송실패] Status: {res.status_code}")
            return False
    except Exception as e:
        print(f"❌ [통신에러] {e}")
        return False

def main():
    # Load config if arguments provided
    load_config_from_file()
    
    wait_until_target_time(TARGET_TIME)
    
    for date, jobs in RESERVATIONS_PLAN.items():
        if not jobs: continue
        session = build_session()
        print(f"\n📅 [처리시작] 날짜: {date}")
        
        while True:
            try:
                url_check = f"{BASE_URL}/popup.step1.php?date={date}&PA_N_UID={PA_N_UID}"
                session.headers.update({"Referer": f"{BASE_URL}/popup.step1.php"})
                r = session.get(url_check, timeout=3)
                if "PS_N_UID" in r.text or "예약1단계" in r.text :
                    print("✨ 예약 오픈 감지!")
                    break
            except: pass
            print("⏳ 오픈 대기 중...")
            time.sleep(0.5)
            
        for job in jobs:
            try:
                do_reservation(session, date, job)
            except Exception as e:
                print(f"⚠️ 에러 발생: {e}")
                
if __name__ == "__main__":
    main()