import re
import time
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# =============================================================================
# 🚀 만석호 API(Packet) 봇 - (구 일프로님.py 기반)
# =============================================================================
#
# [설명]
# 기존 Selenium(브라우저) 방식이 아닌, Requests(패킷) 방식으로 '만석호'를 예약합니다.
# 속도가 매우 빠르지만(0.1초~0.3초), 서버 로직이 변경되면 작동하지 않을 수 있습니다.
#
# [주의사항]
# - 이 코드는 '만석호_Bot - 복사본.py'를 API 스타일로 변환한 것입니다.
# - 기존 만석호 URL(v5.2_seat1)을 타겟으로 합니다.
# =============================================================================

# 1. 만석호 기본 정보 (v5.2_seat1 사용)
BASE_URL = "http://www.mscufishing.com/_core/module/reservation_boat_v5.2_seat1"
PA_N_UID = "3570"  # 만석호 고유 ID

# 2. 실행 시작 시각 (PC 로컬시간)
TARGET_TIME = "00:00:00"

# 3. 실예약/테스트 모드
TEST_MODE = False   # True: 좌석 확인까지만 함 (예약 X)
DRY_RUN = True     # True: 최종 전송만 생략 (로그 확인용)

# 4. 예약 설정 (날짜별 로직)
RESERVATIONS_PLAN = {
    # 예시: 2026년 9월 1일 예약
    "20260901": [
        {
            "seats": 1,
            "person_info": {
                "PA_N_UID": PA_N_UID,
                "PH_N_UID": "0",
                "BI_NAME": "홍길동",
                "BI_BANK": "홍길동",
                "BI_TEL2": "1234",  # 뒷번호
                "BI_TEL3": "5678",  # 끝번호
                "seat_preference": [1, 2, 3, 4, 13, 14, 15], # 선호 좌석
            },
        },
    ]
}

# 5. 어종 자동 선택 키워드
SEARCH_KEYWORDS = ["쭈꾸미", "갑오징어", "쭈갑", "쭈꾸미&갑오징어"]

# 6. 네트워크 설정
REQUEST_TIMEOUT = (3, 5)

# ─────────────────────────────────────────────────────────────────────────────
# Core Logic
# ─────────────────────────────────────────────────────────────────────────────

def build_session():
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Connection": "keep-alive",
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

# Helper Functions (Parsing)
def parse_naun(html):
    m = re.search(r'name="naun"\s+value="(\d+)"', html)
    return m.group(1) if m else "1"

def parse_price(html):
    if "|^|" in html:
        return html.split("|^|")[0].strip()
    return "0원"

def find_ps_n_uid(html, keywords):
    soup = BeautifulSoup(html, "html.parser")
    radios = soup.find_all("input", {"type": "radio", "name": "PS_N_UID"})
    if not radios: return None
    
    best_uid = None
    if len(radios) == 1:
        return radios[0].get("value")
        
    for r in radios:
        label = r.find_parent(["label", "tr"])
        if label:
            text = label.get_text()
            if any(k in text for k in keywords):
                return r.get("value")
    # 못 찾으면 첫 번째
    return radios[0].get("value") if radios else None

def parse_available_seats(html, date, pa_n_uid):
    # 만석호는 onclick="ticket_seat_click('20261219','3570','1')" 형태
    pattern = rf"ticket_seat_click\('?{date}'?,\s*'?{pa_n_uid}'?,\s*'?(\d+)'?\)"
    found = re.findall(pattern, html)
    return set(map(int, found))

def get_seat_input_ids(html):
    # <input type="checkbox" name="seat[]" id="s2026121935701" ...>
    soup = BeautifulSoup(html, "html.parser")
    inputs = soup.find_all("input", {"name": "seat[]"})
    return [i.get("id") for i in inputs]

def id_to_no(sid):
    # s2026121935701 -> 1
    m = re.search(r"(\d+)$", sid)
    return int(m.group(1)) if m else None

# Main Reservation Function
def do_reservation(session, date, job):
    info = job["person_info"]
    seats_needed = job["seats"]
    
    # 1. Step1 Page Load (SCR=0) - Get PS_N_UID & NAUN
    url_1 = f"{BASE_URL}/popup.step1.php?date={date}&PA_N_UID={PA_N_UID}&scr=0"
    r = session.get(url_1, timeout=REQUEST_TIMEOUT)
    naun = parse_naun(r.text)
    ps_uid = find_ps_n_uid(r.text, SEARCH_KEYWORDS)
    
    if not ps_uid:
        print(f"❌ [실패] 어종 선택 불가 ({date})")
        return False
        
    print(f"✅ [정보] 어종값(PS_N_UID): {ps_uid}, 보안값(naun): {naun}")
    
    # 2. Step1 Page Load (SCR=1) - Get Seat Map
    url_2 = f"{BASE_URL}/popup.step1.php?date={date}&PA_N_UID={PA_N_UID}&PS_N_UID={ps_uid}&scr=1"
    r = session.get(url_2, timeout=REQUEST_TIMEOUT)
    html = r.text
    
    # Check Seat Availability
    available_seats = parse_available_seats(html, date, PA_N_UID)
    input_ids = get_seat_input_ids(html)
    
    # Double check logical availability (must match input ids)
    valid_seats = set()
    for sid in input_ids:
        no = id_to_no(sid)
        if no and no in available_seats:
            valid_seats.add(no)
            
    print(f"📊 [좌석] 가용 좌석: {sorted(list(valid_seats))}")
    
    if len(valid_seats) < seats_needed:
        print(f"⚠️ [부족] 잔여석 {len(valid_seats)} < 요청 {seats_needed}")
        # Proceed with max possible?
        seats_needed = len(valid_seats)
        if seats_needed == 0: return False
        
    # Pick Seats
    selected = []
    prefs = info.get("seat_preference", [])
    
    # 1. Preference
    for p in prefs:
        if p in valid_seats:
            selected.append(p)
            if len(selected) == seats_needed: break
            
    # 2. Fill Rest
    if len(selected) < seats_needed:
        for s in sorted(list(valid_seats)):
            if s not in selected:
                selected.append(s)
                if len(selected) == seats_needed: break
                
    print(f"🎯 [선택] 예약할 좌석: {selected}")
    
    # 3. Submit Payload
    # Construct Seat[] Payload
    # 만석호는 1~22번 등 전체 좌석에 대해 seat[] 값을 보냄 (선택은 번호, 미선택은 빈값)
    payload_seats = []
    # Find max seat number to iterate safely
    max_seat_no = 22 # Default fallback
    if input_ids:
        max_seat_no = max([id_to_no(sid) for sid in input_ids if id_to_no(sid)])
        
    for i in range(1, max_seat_no + 1):
        if i in selected:
            payload_seats.append(("seat[]", str(i)))
        else:
            payload_seats.append(("seat[]", ""))

    payload = [
        ("action", "insert"),
        ("link", f"%2F_core%2Fmodule%2Freservation_boat_v5.2_seat1%2Fpopu2.step2.php"), # seat1 주의
        ("temp_bi_stat", "확인"),
        ("date", date),
        ("PA_N_UID", PA_N_UID),
        ("PH_N_UID", "0"),
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
    payload.extend(payload_seats)
    
    if TEST_MODE or DRY_RUN:
        print("🧪 [테스트] 실전송 생략됨")
        return True
        
    # 4. Action!
    url_action = f"{BASE_URL}/action/popu2.step1.action.php"
    res = session.post(url_action, data=payload, timeout=REQUEST_TIMEOUT)
    
    if res.status_code == 200:
        print(f"🚀 [전송완료] Status: {res.status_code}")
        # Optional: Check Step 3 for confirmation
        return True
    else:
        print(f"❌ [전송실패] Status: {res.status_code}")
        return False

def main():
    wait_until_target_time(TARGET_TIME)
    
    for date, jobs in RESERVATIONS_PLAN.items():
        if not jobs: continue
        session = build_session()
        print(f"\n📅 [처리시작] 날짜: {date}")
        
        # Warm-up / Open Check
        while True:
            try:
                # Check if open by trying to load step1
                url_check = f"{BASE_URL}/popup.step1.php?date={date}&PA_N_UID={PA_N_UID}"
                r = session.get(url_check, timeout=3)
                if "PS_N_UID" in r.text:
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
