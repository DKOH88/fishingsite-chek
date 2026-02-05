import re
import time
import requests
import sys
import json
import os
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# =============================================================================
# 🚀 팀만수호 API(Packet) 봇 - (좌석 선택 활성화 + GUI 연동)
# =============================================================================
#
# [설명]
# Requests(패킷) 방식으로 '팀만수호'를 예약합니다.
# **좌석 선택**: AJAX 좌석 조회 후 선호 좌석을 선택합니다.
# **GUI 연동**: launcher로부터 설정 파일 경로를 인자로 받아 동적으로 실행됩니다.
#
# [사용법]
# python "팀만수호_API.py" --config [config_file_path]
# =============================================================================

# 1. 팀만수호 기본 정보 (teammansu.kr / v5.1)
BASE_URL = "https://teammansu.kr/_core/module/reservation_boat_v5.1"
PA_N_UID = "2829"  # 팀만수호 고유 ID

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
                "seat_preference": ['1', '11', '10', '20', '2', '12', '9', '19', '3', '13', '8', '18'], 
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
                                "seat_preference": ['1', '11', '10', '20', '2', '12', '9', '19', '3', '13', '8', '18'],
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
                                    "seat_preference": ['1', '11', '10', '20', '2', '12', '9', '19', '3', '13', '8', '18'],
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
        "Origin": "https://teammansu.kr"
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
    print("##########🔎 팀만수호 API 예약로직 시작!##########")
    print("=" * 60)

    # ─────────────────────────────────────────────────────────────
    # Step 1-1: 초기 페이지 로드 (어종 목록 파악)
    # ─────────────────────────────────────────────────────────────
    step_start = time.time()
    url_1 = f"{BASE_URL}/popu2.step1.php?date={date}&PA_N_UID={PA_N_UID}"
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
    url_2 = f"{BASE_URL}/popu2.step1.php?date={date}&PA_N_UID={PA_N_UID}&PS_N_UID={ps_uid}"
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
    
    payload = [
        ("action", "insert"),
        ("link", f"/_core/module/reservation_boat_v5.1/popu2.step2.php"),  # v5.1 모듈
        ("temp_bi_stat", "확인"),
        ("date", date),
        ("PA_N_UID", PA_N_UID),
        ("PH_N_UID", ph_n_uid),
        ("PS_N_UID", ps_uid),
        ("BI_IN", str(len(selected_seats) if selected_seats else seats_needed)),
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
    
    # 선택된 좌석이 있으면 페이로드에 추가
    if selected_seats:
        for seat in selected_seats:
            payload.append(("BI_SEAT[]", str(seat)))
        print(f"   🪑 좌석 페이로드 추가: {selected_seats}")
    
    payload_duration = time.time() - step_start
    print(f"   📋 페이로드 항목 수: {len(payload)}개")
    print(f"   📋 주요 데이터: date={date}, PA={PA_N_UID}, PS={ps_uid}, BI_IN={seats_needed}, naun={naun}")
    print(f"   📋 사용자: {info['BI_NAME']}, 010-{info['BI_TEL2']}-{info['BI_TEL3']}")
    print(f"⏱️ [Step 2] 페이로드 구성 완료: {payload_duration:.4f}초")
    
    # ─────────────────────────────────────────────────────────────
    # Step 3: 테스트/시뮬레이션 모드 체크
    # ─────────────────────────────────────────────────────────────
    if TEST_MODE or DRY_RUN:
        print(f"\n🧪 [테스트 모드] 실전송 생략됨 (TEST_MODE={TEST_MODE}, DRY_RUN={DRY_RUN})")
        total_duration = time.time() - total_start_time
        print(f"⏱️ [Total] 총 소요 시간(어종선택부터): {total_duration:.4f}초")
        print("=" * 60)
        return True
        
    # ─────────────────────────────────────────────────────────────
    # Step 4: 예약 전송 (Action)
    # ─────────────────────────────────────────────────────────────
    step_start = time.time()
    url_action = f"{BASE_URL}/action/popu2.step1.action.php"
    print(f"\n📡 [Step 4] POST 예약 전송...")
    print(f"   🔗 URL: {url_action}")
    
    session.headers.update({"Referer": url_2})
    
    try:
        res = session.post(url_action, data=payload, timeout=REQUEST_TIMEOUT)
        http_duration = time.time() - step_start
        
        print(f"   ✅ 응답 수신: Status={res.status_code}, Size={len(res.text)}bytes")
        print(f"⏱️ [Step 4] 최종 전송 완료: {http_duration:.4f}초")
        
        if res.status_code == 200:
            response_text = res.text.strip()
            print(f"\n� [응답 분석]")
            print(f"   📄 응답 내용: {response_text[:200]}..." if len(response_text) > 200 else f"   📄 응답 내용: {response_text}")
            
            # 성공/실패 메시지 확인
            if "예약 신청이 완료되었습니다" in response_text or "step2" in response_text.lower():
                print("🎉 [결과] 예약 성공!")
            elif "정상적으로 예약해 주십시오" in response_text:
                print("⚠️ [결과] 예약 오류 - 처음부터 다시 시도 필요")
                return "RETRY_FULL"  # 전체 재시도
            elif "이미" in response_text or "불가능" in response_text:
                print("⚠️ [결과] 좌석 선점 실패 - 즉시 재시도")
                return "RETRY_IMMEDIATE"  # 즉시 재시도
            else:
                print("ℹ️ [결과] 응답 확인 필요")
            
            total_duration = time.time() - total_start_time
            print(f"\n⏱️ [Total] 총 소요 시간(어종선택부터): {total_duration:.4f}초")
            print("=" * 60)
            return True
        else:
            print(f"❌ [전송실패] Status: {res.status_code}")
            if res.status_code in [502, 503]:
                return "RETRY_FULL"  # 서버 에러 - 전체 재시도
            return False
    except requests.exceptions.Timeout:
        print(f"❌ [타임아웃] 서버 응답 없음")
        return "RETRY_IMMEDIATE"
    except requests.exceptions.ConnectionError:
        print(f"❌ [연결실패] 서버 연결 불가")
        return "RETRY_FULL" 
    except Exception as e:
        print(f"❌ [통신에러] {e}")
        return False

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
                    url_check = f"{BASE_URL}/popu2.step1.php?date={date}&PA_N_UID={PA_N_UID}"
                    session.headers.update({"Referer": f"{BASE_URL}/popu2.step1.php"})
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
                            print("=" * 60)
                            return  # 프로그램 종료
                        
                        elif result == "RETRY_FULL":
                            # "정상적으로 예약해 주십시오" - 처음부터 재시도
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

