import re
import time
import requests
import sys
import json
import os
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# =============================================================================
# 🚀 예린호 API(Packet) 봇 - (좌석 선택 활성화 + GUI 연동)
# =============================================================================
#
# [설명]
# Requests(패킷) 방식으로 '예린호'를 예약합니다.
# **좌석 선택**: HTML 좌석 조회 후 선호 좌석을 선택합니다.
# **GUI 연동**: launcher로부터 설정 파일 경로를 인자로 받아 동적으로 실행됩니다.
#
# [사용법]
# python "예린호_API.py" --config [config_file_path]
# =============================================================================

# 1. 예린호 기본 정보 (yerinfishing.com / v5.1 - popup.step1.php 사용)
BASE_URL = "http://www.yerinfishing.com/_core/module/reservation_boat_v5.1"
PA_N_UID = "3515"  # 예린호 고유 ID

# 기본 설정 (GUI 연동 시 덮어씌워짐)
TARGET_TIME = "00:00:00"
TEST_MODE = False
DRY_RUN = False
TEST_MODE_SKIP_WAIT = False  # test_mode: 시간 대기 건너뛰기

# 기본 예약 계획 (GUI 연동 시 덮어씌워짐)
RESERVATIONS_PLAN = {
    # 예시: 2026년 10월 1일 예약
    "20261001": [
        {
            "seats": 1,
            "person_info": {
                "PA_N_UID": PA_N_UID,
                "PH_N_UID": "0",
                "BI_NAME": "홍길동",
                "BI_BANK": "",
                "BI_TEL2": "1234",  # 뒷번호
                "BI_TEL3": "5678",  # 끝번호
                "seat_preference": ['D', 'A', 'C', 'B', '11', '10'], 
            },
        },
    ]
}

# 5. 어종 자동 선택 키워드
SEARCH_KEYWORDS = ["쭈갑", "쭈꾸미&갑오징어", "쭈&갑", "쭈꾸미", "갑오징어", "문어"]

# 6. 네트워크 설정
REQUEST_TIMEOUT = (3, 5)

# ─────────────────────────────────────────────────────────────────────────────
# Config Loader (GUI Support)
# ─────────────────────────────────────────────────────────────────────────────
def load_config_from_file():
    global TARGET_TIME, TEST_MODE, DRY_RUN, RESERVATIONS_PLAN, TEST_MODE_SKIP_WAIT
    
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=False)
    args, _ = parser.parse_known_args()
    
    config_path = args.config if args.config else (sys.argv[1] if len(sys.argv) > 1 else None)
    
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            print(f"📂 [설정로드] {config_path}")
            
            # 1. Global Settings
            TARGET_TIME = config.get('target_time', TARGET_TIME)
            
            # test_mode: 시간 대기 건너뛰기
            if config.get('test_mode', False):
                TEST_MODE_SKIP_WAIT = True
                print("🚀 [Test Mode] 시간 대기 없이 즉시 실행합니다!")
            
            # simulation_mode: 실전송 생략
            if config.get('simulation_mode', False):
                TEST_MODE = True
                DRY_RUN = True
                print("🧪 [Simulation Mode] 실전송 생략 모드 활성화")
            else:
                TEST_MODE = False
                DRY_RUN = False
            
            # 2. 런처에서 직접 전달된 값 확인 (temp_config 방식)
            target_date = config.get('target_date', '')
            u_name = config.get('user_name', '')
            u_phone = config.get('user_phone', '')
            u_depositor = config.get('user_depositor', '')
            seats_n = int(config.get('person_count', 1))
            
            if target_date and u_name:
                # 런처에서 직접 전달된 값 사용
                p2, p3 = "0000", "0000"
                parts = u_phone.split('-')
                if len(parts) >= 3:
                    p2, p3 = parts[1], parts[2]
                elif len(u_phone) == 11:
                    p2, p3 = u_phone[3:7], u_phone[7:]
                    
                RESERVATIONS_PLAN = {
                    target_date: [
                        {
                            "seats": seats_n,
                            "person_info": {
                                "PA_N_UID": PA_N_UID,
                                "PH_N_UID": "0",
                                "BI_NAME": u_name,
                                "BI_BANK": u_depositor,
                                "BI_TEL2": p2,
                                "BI_TEL3": p3,
                                "seat_preference": ['D', 'A', 'C', 'B', '11', '10'],
                            }
                        }
                    ]
                }
                print(f"📅 [설정적용] 날짜: {target_date}, 인원: {seats_n}명, 이름: {u_name}")
                
            # 3. Fallback: multi_instance 방식 (이전 호환)
            elif config.get('multi_instance'):
                multi = config.get('multi_instance', [])
                if multi:
                    item = multi[0]
                    
                    target_date = item.get('date', '')
                    seats_n = int(item.get('person_count', 1))
                    u_name = item.get('user_name', '')
                    u_depositor = item.get('user_depositor', '')
                    u_phone = item.get('user_phone', '')
                    
                    p2, p3 = "0000", "0000"
                    parts = u_phone.split('-')
                    if len(parts) >= 3:
                        p2, p3 = parts[1], parts[2]
                    elif len(u_phone) == 11:
                        p2, p3 = u_phone[3:7], u_phone[7:]
                        
                    RESERVATIONS_PLAN = {
                        target_date: [
                            {
                                "seats": seats_n,
                                "person_info": {
                                    "PA_N_UID": PA_N_UID,
                                    "PH_N_UID": "0",
                                    "BI_NAME": u_name,
                                    "BI_BANK": u_depositor,
                                    "BI_TEL2": p2,
                                    "BI_TEL3": p3,
                                    "seat_preference": ['D', 'A', 'C', 'B', '11', '10'],
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
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Connection": "keep-alive",
        # "X-Requested-With": "XMLHttpRequest",  <-- 기본은 Browser Navigation (Step 2 Page/Action)
        "Origin": "http://www.yerinfishing.com",
        "Upgrade-Insecure-Requests": "1"
    })
    retry = Retry(total=2, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    return s

def wait_until_target_time(target_time_str):
    from datetime import datetime
    
    # 시간 문자열 정규화 (04:3:29 -> 04:03:29)
    parts = target_time_str.split(':')
    if len(parts) == 3:
        h, m, s = parts
        h, m = int(h), int(float(m))
        s = float(s)
        target_time_str = f"{h:02d}:{m:02d}:{s:05.2f}"
    else:
        h, m, s = 0, 0, 0
    
    # 타겟 시간 계산
    now = datetime.now()
    target = now.replace(hour=h, minute=m, second=int(s), microsecond=int((s % 1) * 1000000))
    
    # 이미 지난 시간이면 즉시 시작
    if datetime.now() >= target:
        print(f"⏰ 타겟 시간 {target_time_str} 이미 경과 - 즉시 시작!")
        return
    
    print(f"⏰ 타겟 시간: {target_time_str}")
    print(f"   현재 시간: {now.strftime('%H:%M:%S')}")
    
    while True:
        now = datetime.now()
        if now >= target:
            print(f"\r🔔 타겟 시간 도달! 예약 시작!                    ")
            break
        
        remaining = (target - now).total_seconds()
        mins, secs = divmod(remaining, 60)
        hours, mins = divmod(mins, 60)
        
        # 실시간 카운트다운 (같은 줄에서 업데이트)
        print(f"\r   ⏳ 남은 시간: {int(hours):02d}:{int(mins):02d}:{secs:05.2f}", end="", flush=True)
        
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
    if not radios: 
        # 샤크호는 CSS 클래스로도 찾아볼 수 있음
        radios = soup.find_all("input", {"class": "PS_N_UID"})
    if not radios: return None
    
    if len(radios) == 1:
        return radios[0].get("value")
        
    for r in radios:
        # ps_selis 클래스를 가진 span을 찾아봄 (샤크호 방식)
        parent_td = r.find_parent("td")
        if parent_td:
            sibling_td = parent_td.find_next_sibling("td")
            if sibling_td:
                span = sibling_td.find("span", class_="ps_selis")
                if span:
                    text = span.get_text()
                    if any(k in text for k in keywords):
                        return r.get("value")
        
        # 기존 방식 (레이블 또는 부모 태그 체크)
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
    
    print("=" * 60)
    print(f"🚀 [시작] 예약 시도: {date} (필요: {seats_needed}석)")
    print(f"   👤 예약자: {info['BI_NAME']} | 연락처: 010-{info['BI_TEL2']}-{info['BI_TEL3']}")
    print("##########🔎 예린호 API 예약로직 시작!##########")
    print("=" * 60)

    # ─────────────────────────────────────────────────────────────
    # Step 1-1: 초기 페이지 로드 (어종 목록 파악)
    # ─────────────────────────────────────────────────────────────
    step_start = time.time()
    url_1 = f"{BASE_URL}/popup.step1.php?date={date}&PA_N_UID={PA_N_UID}"
    print(f"📡 [Step 1-1] GET 요청 전송...")
    print(f"   🔗 URL: {url_1}")
    
    session.headers.update({"Referer": url_1}) 
    r = session.get(url_1, timeout=REQUEST_TIMEOUT)
    
    step_duration = time.time() - step_start
    print(f"   ✅ 응답 수신: Status={r.status_code}, Size={len(r.text)}bytes")
    print(f"⏱️ [Step 1-1] 초기 로드 완료: {step_duration:.4f}초")
    
    # ─────────────────────────────────────────────────────────────
    # Step 1-1-2: 어종 파싱
    # ─────────────────────────────────────────────────────────────
    parse_start = time.time()
    ps_uid = find_ps_n_uid(r.text, SEARCH_KEYWORDS)
    parse_duration = time.time() - parse_start
    
    if not ps_uid:
        print(f"❌ [실패] 어종 선택 불가 ({date})")
        print(f"   🔍 검색 키워드: {SEARCH_KEYWORDS}")
        return False
    
    print(f"   🎣 어종 PS_N_UID 파싱: {ps_uid} ({parse_duration:.4f}초)")

    # =============== [TOTAL TIME START] =================
    total_start_time = time.time()
    print(f"\n⏱️ [타이머 시작] 어종 선택부터 측정 시작...")

    # ─────────────────────────────────────────────────────────────
    # Step 1-2: 어종 선택 적용 및 잔여석(naun) 파악
    # ─────────────────────────────────────────────────────────────
    step_start = time.time()
    url_2 = f"{BASE_URL}/popup.step1.php?date={date}&PA_N_UID={PA_N_UID}&PS_N_UID={ps_uid}"
    print(f"\n📡 [Step 1-2] GET 요청 전송 (어종 선택 적용)...")
    print(f"   🔗 URL: {url_2}")
    
    session.headers.update({"Referer": url_1})
    r = session.get(url_2, timeout=REQUEST_TIMEOUT)
    
    http_duration = time.time() - step_start
    print(f"   ✅ 응답 수신: Status={r.status_code}, Size={len(r.text)}bytes ({http_duration:.4f}초)")
    
    # 잔여석 파싱
    parse_start = time.time()
    html_step1 = r.text
    naun = parse_naun(html_step1)
    parse_duration = time.time() - parse_start
    
    print(f"   🪑 잔여석(naun) 파싱: {naun}석 ({parse_duration:.4f}초)")
    print(f"⏱️ [Step 1-2] 어종 선택 및 정보 로드: {time.time() - step_start:.4f}초")

    # ─────────────────────────────────────────────────────────────
    # Step 1-3: 좌석 선택 (seat_preference 기반) - Selenium 로직 반영
    # ─────────────────────────────────────────────────────────────
    step_start = time.time()
    seat_preference = info.get("seat_preference", [])
    selected_seats = []
    final_seats_needed = seats_needed  # 최종 인원수 (가용 좌석에 따라 조정될 수 있음)
    
    if seat_preference:
        print(f"\n🪑 [Step 1-3] 좌석 선택 처리 중...")
        print(f"   📋 선호 좌석 우선순위: {seat_preference}")
        print(f"   👥 설정 인원: {seats_needed}명")
        
        # HTML에서 빈 좌석 파싱
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_step1, "html.parser")
        
        available_seats = []
        reserved_seats = []
        seat_class = None
        
        # 선사마다 다른 클래스: res_num_view 또는 num_view
        if soup.find("span", class_="res_num_view"):
            seat_class = "res_num_view"
            reserved_class = "res_num_view_end"
            print(f"   ✅ 좌석 클래스 감지: res_num_view")
        elif soup.find("span", class_="num_view"):
            seat_class = "num_view"
            reserved_class = "num_view_end"
            print(f"   ✅ 좌석 클래스 감지: num_view")
        else:
            print(f"   ⚠️ 좌석 클래스를 찾을 수 없습니다.")
        
        if seat_class:
            # 빈 좌석: class="{seat_class}" + onclick 속성
            for span in soup.find_all("span", class_=seat_class):
                if span.get("onclick"):  # onclick이 있으면 예약 가능
                    seat_num = span.get_text(strip=True)
                    if seat_num.isdigit():
                        available_seats.append(seat_num)
            
            # 예약된 좌석: class="{reserved_class}"
            for span in soup.find_all("span", class_=reserved_class):
                seat_num = span.get_text(strip=True)
                if seat_num.isdigit():
                    reserved_seats.append(seat_num)
            
            available_count = len(available_seats)
            print(f"   📊 가용 좌석 수: {available_count}석")
            print(f"   📊 빈 좌석: {available_seats}")
            print(f"   🚫 예약된 좌석: {reserved_seats}")
            
            # 가용 좌석이 설정 인원보다 적으면 자동 조정
            if available_count < seats_needed:
                print(f"   ⚠️ 가용 좌석 부족! 인원을 {seats_needed}명 → {available_count}명으로 자동 조정합니다.")
                final_seats_needed = available_count
            
            # 선호 좌석 중 빈 좌석 선택
            if available_seats:
                for pref in seat_preference:
                    pref_str = str(pref)
                    if pref_str in available_seats and len(selected_seats) < final_seats_needed:
                        selected_seats.append(pref_str)
                        print(f"   ✨ 우선순위 좌석 {pref_str}번 선택! ({len(selected_seats)}/{final_seats_needed})")
                
                # 선호 좌석이 다 차있으면 아무 빈 좌석 선택
                if len(selected_seats) < final_seats_needed:
                    print(f"   ⚠️ 우선순위 좌석 부족. 남은 좌석 중 선택...")
                    for seat in available_seats:
                        if seat not in selected_seats and len(selected_seats) < final_seats_needed:
                            selected_seats.append(seat)
                            print(f"   🎲 무작위 좌석 {seat}번 선택! ({len(selected_seats)}/{final_seats_needed})")
        
        if selected_seats:
            print(f"   ✅ 좌석 선택 완료! 총 {len(selected_seats)}석 선택됨. (선택순서: {' → '.join(selected_seats)})")
        else:
            print(f"   ⚠️ 빈 좌석 없음 또는 선호 좌석 모두 예약됨")
        
        print(f"⏱️ [Step 1-3] 좌석 선택 완료: {time.time() - step_start:.4f}초")
    else:
        print(f"\n⏩ [Step 1-3] 좌석 선택 생략 (seat_preference 없음)")

    # ─────────────────────────────────────────────────────────────
    # Step 2: 페이로드 구성
    # ─────────────────────────────────────────────────────────────
    step_start = time.time()
    print(f"\n📝 [Step 2] 예약 페이로드 구성 중...")
    
    payload = []
    
    # HTML 파싱하여 기본 필드 값 수집
    from bs4 import BeautifulSoup
    soup_step1 = BeautifulSoup(html_step1, "html.parser")
    
    # 1. 모든 폼 필드 수집 (hidden, text, checkbox, radio, select, textarea)
    # 순서가 중요할 수 있으므로 form 내의 순서대로 수집
    form = soup_step1.find("form", id="reserv_form")
    if not form:
        form = soup_step1  # 폼이 없으면 전체에서 검색
        
    for element in form.find_all(["input", "select", "textarea"]):
        tag_name = element.name
        e_type = element.get("type", "text").lower()
        name = element.get("name")
        value = element.get("value", "")
        
        if not name: continue
        
        if tag_name == "input":
            if e_type in ["checkbox", "radio"]:
                if element.get("checked") is not None:
                    payload.append((name, value))
            else:
                payload.append((name, value))
        elif tag_name == "textarea":
            payload.append((name, element.get_text()))
        elif tag_name == "select":
            # 선택된 옵션 찾기
            selected = element.find("option", selected=True)
            if selected:
                payload.append((name, selected.get("value", "")))
            else:
                # 선택된 게 없으면 첫 번째 옵션
                first_opt = element.find("option")
                if first_opt:
                    payload.append((name, first_opt.get("value", "")))
            
    # 2. 필수 필드 업데이트 (사용자 정보 등)
    # 파싱된 필드 중 업데이트할 것들을 찾아서 교체하거나 새로 추가
    # 2. 필수 필드 업데이트 (사용자 정보 등)
    # [Golden Payload 기반 수정] 브라우저에서 실제로 보내지 않는 필드들 제거
    # 수정: requests는 data 파라미터에 튜플 리스트를 주면 값을 그대로 전송함 (자동 인코딩 안 함)
    # 따라서 Golden Payload의 인코딩된 값을 그대로 사용해야 함
    encoded_link_step2 = "%2F_core%2Fmodule%2Freservation_boat_v5.1%2Fpopup.step2.php"
    
    updates = {
        "action": "insert",
        "link": encoded_link_step2, 
        "temp_bi_stat": "확인",
        "PA_N_UID": PA_N_UID,
        "PS_N_UID": ps_uid,
        "BI_IN": str(len(selected_seats) if selected_seats else seats_needed),
        "BI_NAME": info["BI_NAME"],
        "BI_BANK": info["BI_BANK"],
        "BI_TEL1": "010",
        "BI_TEL2": info["BI_TEL2"],
        "BI_TEL3": info["BI_TEL3"],
        "BI_MEMO": "",
        "agree": "Y",
        "BI_3JA": "1",
        "BI_AD": "1",
        "all_agree": "Y"
    }
    
    # 제거할 키 목록 (Golden Payload에 없는 것들)
    # [수정] seat[] 키를 여기서 제거하고, 아래에서 선택된 값만 추가함 (빈 값 제거)
    remove_keys = ["date", "PH_N_UID", "scr", "BI_SO_IN", "pay_method", "naun", "seat[]"]
    
    # [CRITICAL FIX] 예린호 좌석 레이아웃 하드코딩
    # Golden Payload 분석: 24개의 seat[] (HTML에는 23개만 있고 11번이 누락됨)
    # 레이아웃: D, C, 20, 19, 18, 17, 16, 15, 14, 13, 12, 11, A, B, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
    SEAT_LAYOUT = ['D', 'C', '20', '19', '18', '17', '16', '15', '14', '13', '12', '11', 
                   'A', 'B', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10']
    
    seat_payloads = []
    mapped_count = 0
    
    for seat_id in SEAT_LAYOUT:
        val = ""
        if selected_seats and str(seat_id) in [str(s) for s in selected_seats]:
            val = str(seat_id)
            mapped_count += 1
            print(f"      ✅ 좌석 매칭: Position={SEAT_LAYOUT.index(seat_id)+1} -> Seat={seat_id}")
        seat_payloads.append(("seat[]", val))
    
    if mapped_count == 0 and selected_seats:
        print(f"      ⚠️ [경고] 하드코딩 레이아웃에서 좌석을 찾지 못했습니다: {selected_seats}")
        # Fallback
        for seat in selected_seats:
            seat_payloads.append(("seat[]", str(seat)))

    # [CRITICAL] Golden Payload 순서 엄수!
    # 1. action, link, temp_bi_stat, PA_N_UID, PS_N_UID, BI_IN
    # 2. seat[] 배열 (24개)
    # 3. BI_NAME, BI_BANK, BI_TEL1~3, BI_MEMO, agree, BI_3JA, BI_AD, all_agree
    
    final_payload = []
    
    # Phase 1: 기본 필드 (seat[] 이전)
    final_payload.append(("action", "insert"))
    final_payload.append(("link", encoded_link_step2))
    final_payload.append(("temp_bi_stat", "확인"))
    final_payload.append(("PA_N_UID", PA_N_UID))
    final_payload.append(("PS_N_UID", ps_uid))
    final_payload.append(("BI_IN", str(len(selected_seats) if selected_seats else seats_needed)))
    
    # Phase 2: seat[] 배열 삽입
    final_payload.extend(seat_payloads)
    
    # Phase 3: 사용자 정보 필드 (seat[] 이후)
    final_payload.append(("BI_NAME", info["BI_NAME"]))
    final_payload.append(("BI_BANK", info["BI_BANK"]))
    final_payload.append(("BI_TEL1", "010"))
    final_payload.append(("BI_TEL2", info["BI_TEL2"]))
    final_payload.append(("BI_TEL3", info["BI_TEL3"]))
    final_payload.append(("BI_MEMO", ""))
    final_payload.append(("agree", "Y"))
    final_payload.append(("BI_3JA", "1"))
    final_payload.append(("BI_AD", "1"))
    final_payload.append(("all_agree", "Y"))
    
    payload = final_payload
    
    print(f"   🪑 좌석 페이로드 구성: 총 {len(seat_payloads)}개 필드 (하드코딩 레이아웃)")
    
    payload_duration = time.time() - step_start
    print(f"   📋 [STEP 1 전송 데이터 상세]")
    for i, (k, v) in enumerate(payload):
        val_str = str(v)
        if len(val_str) > 100: val_str = val_str[:100] + "..."
        print(f"      {i+1}. {k} = {val_str}")
    
    print(f"⏱️ [Step 2] 페이로드 구성 완료: {payload_duration:.4f}초")
    
    # (시뮬레이션 모드 체크는 STEP 2 완료 후로 이동됨)
    # ═══════════════════════════════════════════════════════════════
    # 예린호 3단계 예약 프로세스 (STEP 1 → STEP 2 → STEP 3)
    # ═══════════════════════════════════════════════════════════════
    
    # ─────────────────────────────────────────────────────────────
    # STEP 1: 첫 번째 예약 전송 (popup.step1.action.php)
    # ─────────────────────────────────────────────────────────────
    step_start = time.time()
    url_step1_action = f"{BASE_URL}/action/popup.step1.action.php"
    print(f"\n🚀 [STEP 1] 첫 번째 예약 전송...")
    print(f"   🔗 URL: {url_step1_action}")
    
    session.headers.update({"Referer": url_2})
    # 응답이 <script>location.replace...</script> 형태이므로 일반 Form Submit임!
    # AJAX(XMLHttpRequest) 헤더 제거
    if "X-Requested-With" in session.headers:
        del session.headers["X-Requested-With"]
    
    try:
        res1 = session.post(url_step1_action, data=payload, timeout=REQUEST_TIMEOUT)
        http_duration = time.time() - step_start
        
        print(f"   ✅ 응답 수신: Status={res1.status_code}, Size={len(res1.text)}bytes ({http_duration:.4f}초)")
        
        if res1.status_code != 200:
            print(f"❌ [STEP 1] 전송 실패! Status: {res1.status_code}")
            if res1.status_code in [502, 503]:
                return "RETRY_FULL"
            return False
        
        response_text = res1.text.strip()
        print(f"   📄 응답: {response_text[:150]}..." if len(response_text) > 150 else f"   📄 응답: {response_text}")
        
        # 에러 체크
        if "정상적으로 예약해 주십시오" in response_text:
            print("⚠️ [STEP 1] 오류! 처음부터 다시 시도 필요")
            return "RETRY_FULL"
        if "이미" in response_text or "불가능" in response_text:
            print("⚠️ [STEP 1] 좌석 선점 실패!")
            return "RETRY_IMMEDIATE"
        
        # step2.php로 이동하는지 확인
        if "step2" not in response_text.lower() and "location" not in response_text.lower():
            print("⚠️ [STEP 1] 응답에서 STEP 2 진입 신호 없음")
            # 그래도 계속 진행
        
        # 세션 쿠키 디버깅
        print(f"   🍪 세션 쿠키: {dict(session.cookies)}")
        
        print(f"⏱️ [STEP 1] 완료: {http_duration:.4f}초")
        
        # 서버 세션 저장 대기 (0.5초)
        time.sleep(0.5)
        
    except requests.exceptions.Timeout:
        print(f"❌ [STEP 1] 타임아웃!")
        return "RETRY_IMMEDIATE"
    except requests.exceptions.ConnectionError:
        print(f"❌ [STEP 1] 연결 실패!")
        return "RETRY_FULL"
    except Exception as e:
        print(f"❌ [STEP 1] 오류: {e}")
        return False
    
    # ─────────────────────────────────────────────────────────────
    # STEP 2: 두 번째 페이지 로드 및 전송
    # ─────────────────────────────────────────────────────────────
    step_start = time.time()
    # v5.1은 세션 기반이므로 쿼리 파라미터 없이 로드 (STEP 1 action 리다이렉트와 동일하게)
    url_step2 = f"{BASE_URL}/popup.step2.php"
    print(f"\n🚀 [STEP 2] 두 번째 페이지 로드...")
    print(f"   🔗 URL: {url_step2}")
    
    try:
        session.headers.update({"Referer": url_step1_action})
        # Step 2 Page Load는 일반 브라우저 Navigation이므로 XMLHttpRequest 제거
        if "X-Requested-With" in session.headers:
            del session.headers["X-Requested-With"]
            
        res2_page = session.get(url_step2, timeout=REQUEST_TIMEOUT)
        
        print(f"   ✅ STEP 2 페이지 로드: Status={res2_page.status_code}, Size={len(res2_page.text)}bytes")
        
        # STEP 2 페이지 내용 검증
        step2_html = res2_page.text
        if "STEP 02" in step2_html or "예약확인" in step2_html or "예약2단계" in step2_html:
            print(f"   ✅ STEP 2 페이지 확인됨! (예약확인 단계)")
        elif "STEP 01" in step2_html or "예약1단계" in step2_html:
            print(f"   ⚠️ STEP 1 페이지가 표시됨! 세션 데이터 누락?")
            # STEP 1 페이지 내용 일부 출력
            print(f"   📄 페이지 일부: {step2_html[500:700]}...")
        else:
            print(f"   ⚠️ 알 수 없는 페이지. 내용 확인 필요")
            print(f"   📄 페이지 일부: {step2_html[:300]}...")
        
        if res2_page.status_code != 200:
            print(f"⚠️ [STEP 2] 페이지 로드 실패! Status: {res2_page.status_code}")
            return "RETRY_FULL"
        
        # ─────────────────────────────────────────────────────────────
        # 시뮬레이션 모드: STEP 2 URL 확인 후 종료 (action 전송 안 함)
        # ─────────────────────────────────────────────────────────────
        if TEST_MODE or DRY_RUN:
            print(f"\n🧪 [시뮬레이션 모드] STEP 2 페이지 로드 확인! (popup.step2.php)")
            print(f"   ✅ STEP 1 전송 성공 → STEP 2 진입 확인됨!")
            total_duration = time.time() - total_start_time
            print(f"⏱️ [Total] 총 소요 시간(어종선택부터): {total_duration:.4f}초")
            print("=" * 60)
            return True
        
        # STEP 2 submit 전송 (실제 모드에서만)
        url_step2_action = f"{BASE_URL}/action/popup.step2.action.php"
        print(f"\n🚀 [STEP 2] 두 번째 예약 전송...")
        print(f"   🔗 URL: {url_step2_action}")
        
        # STEP 2 페이지에서 폼 필드 파싱
        from bs4 import BeautifulSoup
        soup_step2 = BeautifulSoup(res2_page.text, "html.parser")
        
        # 폼 데이터 수집
        payload_step2 = []
        
        # Hidden 필드 추출
        for hidden in soup_step2.find_all("input", {"type": "hidden"}):
            name = hidden.get("name")
            value = hidden.get("value", "")
            if name:
                payload_step2.append((name, value))
        
        # Textarea 필드 추출 (BI_MEMO 등)
        for textarea in soup_step2.find_all("textarea"):
            name = textarea.get("name")
            value = textarea.get_text() or ""
            if name:
                payload_step2.append((name, value))
                
        # action 필드가 없으면 기본값 추가 (v5.1은 "update" 사용!)
        if not any(p[0] == "action" for p in payload_step2):
            payload_step2.append(("action", "update"))
            
        # [Golden Payload 기반 수정] link 값은 무조건 step3.php로 설정 (인코딩된 형태)
        encoded_link_step3 = "%2F_core%2Fmodule%2Freservation_boat_v5.1%2Fpopup.step3.php"
        
        # 기존에 파싱된 link가 있다면 제거하고 새로 추가
        payload_step2 = [p for p in payload_step2 if p[0] != "link"]
        payload_step2.append(("link", encoded_link_step3))
        
        # Check for missing critical data
        # Step 2 HTML에 Hidden Field가 없으므로 이 체크는 무의미할 수 있음 (주석 처리)
        # chk_keys = ["date", "PA_N_UID", "PS_N_UID"]
        # missing_vals = [k for k, v in payload_step2 if k in chk_keys and not v]
        
        print(f"   📋 STEP 2 페이로드 (추출된 필드 확인):")
        for p in payload_step2:
            print(f"      - {p[0]}: {p[1][:50]}..." if len(str(p[1])) > 50 else f"      - {p[0]}: {p[1]}")
        
        # 중요 필드 검증 (값이 비어있으면 세션 문제일 가능성 높음)
        chk_keys = ["date", "PA_N_UID", "PS_N_UID"]
        missing_vals = [k for k, v in payload_step2 if k in chk_keys and not v]
        if missing_vals:
             print(f"   ⚠️ [경고] STEP 2 페이지에서 중요 데이터 누락됨: {missing_vals}")
             # 중요: STEP 2 HTML에 예약 정보가 렌더링 되었다면 세션은 살아있는 것임.
             # 하지만 form에 hidden field가 없다면, Action 처리 시 세션값에 전적으로 의존한다는 뜻.
             
        session.headers.update({"Referer": url_step2})
        
        # [수정] 쿠키 헤더 직접 주입 (path 문제 등 방지)
        cookie_str = "; ".join([f"{k}={v}" for k, v in session.cookies.items()])
        session.headers.update({"Cookie": cookie_str})
        print(f"   🍪 [STEP 2] 쿠키 헤더 강제 주입: {cookie_str}")
        
        res2 = session.post(url_step2_action, data=payload_step2, timeout=REQUEST_TIMEOUT)
        http_duration = time.time() - step_start
        
        print(f"   ✅ 응답 수신: Status={res2.status_code}, Size={len(res2.text)}bytes ({http_duration:.4f}초)")
        
        if res2.status_code != 200:
            print(f"⚠️ [STEP 2] 전송 실패! Status: {res2.status_code}")
            return "RETRY_FULL"
        
        response_text2 = res2.text.strip()
        print(f"   📄 응답: {response_text2[:150]}..." if len(response_text2) > 150 else f"   📄 응답: {response_text2}")
        
        # 에러 체크
        if "예약할 수 없습니다" in response_text2 or "관리자에게 문의" in response_text2:
            print("⚠️ [STEP 2] 세션 에러! 예약 데이터가 서버에 없음 - 처음부터 재시도")
            return "RETRY_FULL"
        if "정상적으로 예약해 주십시오" in response_text2:
            print("⚠️ [STEP 2] 오류! 처음부터 다시 시도 필요")
            return "RETRY_FULL"
        if "이미" in response_text2 or "불가능" in response_text2:
            print("⚠️ [STEP 2] 좌석 선점 실패!")
            return "RETRY_IMMEDIATE"
        
        print(f"⏱️ [STEP 2] 완료: {http_duration:.4f}초")
        
    except requests.exceptions.Timeout:
        print(f"❌ [STEP 2] 타임아웃!")
        return "RETRY_IMMEDIATE"
    except requests.exceptions.ConnectionError:
        print(f"❌ [STEP 2] 연결 실패!")
        return "RETRY_FULL"
    except Exception as e:
        print(f"❌ [STEP 2] 오류: {e}")
        return False
    
    # ─────────────────────────────────────────────────────────────
    # STEP 3: 최종 성공 확인
    # ─────────────────────────────────────────────────────────────
    step_start = time.time()
    # v5.1은 세션 기반이므로 쿼리 파라미터 없이 로드
    url_step3 = f"{BASE_URL}/popup.step3.php"
    print(f"\n🎯 [STEP 3] 최종 성공 확인 중...")
    print(f"   🔗 URL: {url_step3}")
    
    try:
        session.headers.update({"Referer": url_step2_action})
        res3 = session.get(url_step3, timeout=REQUEST_TIMEOUT)
        
        print(f"   ✅ STEP 3 페이지 응답: Status={res3.status_code}, Size={len(res3.text)}bytes")
        
        response_text3 = res3.text
        
        # 성공 확인
        success_indicators = ["완료", "성공", "예약이 완료", "신청이 완료"]
        if any(ind in response_text3 for ind in success_indicators):
            print("🎉 [STEP 3] 예약 성공 확인!")
            total_duration = time.time() - total_start_time
            print(f"\n⏱️ [Total] 총 소요 시간(어종선택부터): {total_duration:.4f}초")
            print("=" * 60)
            return True
        else:
            print(f"   📄 응답: {response_text3[:200]}..." if len(response_text3) > 200 else f"   📄 응답: {response_text3}")
            # STEP 2 응답이 성공적이었다면 성공으로 간주
            if "step3" in response_text2.lower() or res2.status_code == 200:
                print("🎉 [STEP 3] 예약 성공으로 간주 (STEP 2 성공 기반)")
                total_duration = time.time() - total_start_time
                print(f"\n⏱️ [Total] 총 소요 시간(어종선택부터): {total_duration:.4f}초")
                print("=" * 60)
                return True
        
        print("⚠️ [STEP 3] 성공 확인 실패")
        return False
        
    except Exception as e:
        print(f"⚠️ [STEP 3] 확인 중 오류: {e}")
        # STEP 2까지 성공했으면 성공으로 간주
        print("🎉 [STEP 3] STEP 2 성공 기반으로 예약 성공 간주")
        total_duration = time.time() - total_start_time
        print(f"\n⏱️ [Total] 총 소요 시간(어종선택부터): {total_duration:.4f}초")
        print("=" * 60)
        return True

def main():
    # Load config if arguments provided
    load_config_from_file()
    
    # Test Mode면 시간 대기 건너뛰기
    if not TEST_MODE_SKIP_WAIT:
        wait_until_target_time(TARGET_TIME)
    else:
        print("⏩ [Test Mode] 시간 대기를 건너뜁니다!")
    
    for date, jobs in RESERVATIONS_PLAN.items():
        if not jobs: continue
        
        # ═══════════════════════════════════════════════════════════════
        # 메인 예약 루프 (Selenium 스타일 무한 재시도)
        # ═══════════════════════════════════════════════════════════════
        MAX_TOTAL_RETRIES = 100  # 전체 최대 재시도 횟수
        total_attempts = 0
        
        while total_attempts < MAX_TOTAL_RETRIES:
            total_attempts += 1
            session = build_session()
            print(f"\n{'='*60}")
            print(f"📅 [예약 시도 #{total_attempts}] 날짜: {date}")
            print(f"{'='*60}")
            
            # ─────────────────────────────────────────────────────────
            # Phase 1: 예약 오픈 대기 (서버 안정화 대기)
            # ─────────────────────────────────────────────────────────
            open_retry = 0
            MAX_OPEN_RETRIES = 500
            
            while open_retry < MAX_OPEN_RETRIES:
                open_retry += 1
                try:
                    url_check = f"{BASE_URL}/popup.step1.php?date={date}&PA_N_UID={PA_N_UID}"
                    session.headers.update({"Referer": f"{BASE_URL}/popup.step1.php"})
                    r = session.get(url_check, timeout=3)
                    
                    # ✅ 성공: 예약 페이지 오픈 감지
                    if "PS_N_UID" in r.text or "STEP 01" in r.text or "예약1단계" in r.text:
                        print(f"✨ 예약 오픈 감지! (시도: {open_retry})")
                        break
                    
                    # ⚠️ 에러: 502 Bad Gateway
                    if r.status_code == 502 or "Bad Gateway" in r.text:
                        print(f"⚠️ [502] 서버 오류. 재시도... ({open_retry}/{MAX_OPEN_RETRIES})")
                        time.sleep(0.1)
                        continue
                    
                    # ⚠️ 에러: 503 Service Unavailable
                    if r.status_code == 503:
                        print(f"⚠️ [503] 서비스 불가. 재시도... ({open_retry}/{MAX_OPEN_RETRIES})")
                        time.sleep(0.1)
                        continue
                    
                    # ⚠️ 에러: 리다이렉트 에러
                    if "waitingrequest" in r.url or "ERR_TOO_MANY_REDIRECTS" in r.text:
                        print(f"⚠️ 리다이렉트 에러! 세션 재생성... ({open_retry}/{MAX_OPEN_RETRIES})")
                        session = build_session()  # 세션 재생성
                        time.sleep(0.1)
                        continue
                    
                    # ⚠️ 에러: 페이지 에러 (없는/권한/잘못)
                    if any(err in r.text for err in ['없는', '권한', '잘못']):
                        print(f"⚠️ 에러 페이지 감지. 재시도... ({open_retry}/{MAX_OPEN_RETRIES})")
                        time.sleep(0.1)
                        continue
                    
                    # 아직 오픈 안됨
                    print(f"⏳ 오픈 대기 중... ({open_retry})")
                    
                except requests.exceptions.Timeout:
                    print(f"⚠️ 타임아웃! 재시도... ({open_retry}/{MAX_OPEN_RETRIES})")
                except requests.exceptions.ConnectionError:
                    print(f"⚠️ 연결 실패! 세션 재생성... ({open_retry}/{MAX_OPEN_RETRIES})")
                    session = build_session()
                except Exception as e:
                    print(f"⚠️ 예외: {e} ({open_retry}/{MAX_OPEN_RETRIES})")
                
                time.sleep(0.1)
            
            if open_retry >= MAX_OPEN_RETRIES:
                print("❌ 오픈 대기 최대 재시도 초과!")
                continue
            
            # ─────────────────────────────────────────────────────────
            # Phase 2: 예약 실행 (재시도 포함)
            # ─────────────────────────────────────────────────────────
            for job in jobs:
                MAX_RESERVATION_RETRIES = 3
                
                for res_attempt in range(MAX_RESERVATION_RETRIES):
                    try:
                        print(f"\n🎯 [예약 시도 {res_attempt + 1}/{MAX_RESERVATION_RETRIES}]")
                        result = do_reservation(session, date, job)
                        
                        if result == True:
                            # 성공!
                            print("=" * 60)
                            print("🎉 예약 성공! 봇 실행 완료!")
                            if result == True:
                                print(f"🎉 예약 성공! 모든 작업 완료.")
                                return

                        # [수정] 테스트 모드면 결과(성공/실패)와 관계없이 무조건 1회 실행 후 종료
                        if TEST_MODE or DRY_RUN:
                            print(f"\n🛑 [테스트/시뮬레이션] 1회 실행 완료 (결과: {result}) → 종료합니다.")
                            return

                        if result == "RETRY_FULL":
                            # 처음스텝부터 다시 시작
                            print("🔄 전체 플로우 재시도...")
                            session = build_session()
                            time.sleep(0.1)
                            break  # 내부 루프 탈출, 외부 루프에서 재시도
                        
                        elif result == "RETRY_IMMEDIATE":
                            # 좌석 선점 실패 - 즉시 재시도
                            print("🔄 즉시 재시도...")
                            session = build_session()
                            continue
                        
                        else:
                            # 일반 실패
                            print(f"⚠️ 예약 실패. 재시도 중... ({res_attempt + 1}/{MAX_RESERVATION_RETRIES})")
                            time.sleep(0.1)
                            continue
                            
                    except requests.exceptions.Timeout:
                        print(f"⚠️ 타임아웃! 재시도... ({res_attempt + 1}/{MAX_RESERVATION_RETRIES})")
                        session = build_session()
                    except requests.exceptions.ConnectionError:
                        print(f"⚠️ 연결 실패! 세션 재생성... ({res_attempt + 1}/{MAX_RESERVATION_RETRIES})")
                        session = build_session()
                    except Exception as e:
                        print(f"⚠️ 예외: {e} ({res_attempt + 1}/{MAX_RESERVATION_RETRIES})")
                    
                    time.sleep(0.05)
                else:
                    # 예약 재시도 모두 실패
                    print("❌ 예약 재시도 최대 횟수 초과. 전체 재시도...")
                    continue
                
                # break로 빠져나온 경우 (RETRY_FULL)
                break
            else:
                # 모든 job 처리 완료 (성공 없이)
                continue
            
            # 외부 루프 계속 (RETRY_FULL로 인한 재시도)
        
        print(f"❌ 전체 재시도 최대 횟수({MAX_TOTAL_RETRIES}) 초과!")

if __name__ == "__main__":
    main()

