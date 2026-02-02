import re
import time
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# =============================================================================
# ✅✅✅ 사용자 설정 구역 (여기만 바꾸면 됩니다) ✅✅✅
# =============================================================================
#
# [A] 선사(사이트) 변경 시 반드시 확인/수정할 것  ★★★★★
#   1) BASE_URL : 선사별 모듈 경로가 다를 수 있음 (v5.2_seat / seat1 등)
#   2) 날짜/PA_N_UID/PH_N_UID : 선사/계정별로 다름
#   3) SEARCH_KEYWORDS : 어종/상품 라디오(PS_N_UID) 자동 선택 키워드
#
# [B] 실예약/테스트 모드  ★★★★★★★★★★ (가장 중요)
#   - TEST_MODE=True  : 좌석 선택/매핑 검증까지만 하고 종료 (절대 실예약 안 됨)
#   - DRY_RUN=True    : 최종 예약 제출(action.php)을 생략 (실예약 안 됨)
#
#   ▶ 실예약하려면 반드시 아래처럼 설정
#      TEST_MODE = False
#      DRY_RUN  = False
#
# -----------------------------------------------------------------------------


# =========================
# 1) 선사/사이트 기본 정보  ★★★★★ (선사 바뀌면 수정)
# =========================
BASE_URL = "http://www.mscufishing.com/_core/module/reservation_boat_v5.2_seat"
# 예) "http://www.newhawaii.co.kr/_core/module/reservation_boat_v5.2_seat"
# 예) "http://www.mscufishing.com/_core/module/reservation_boat_v5.2_seat"

# =========================
# 2) 실행 시작 시각 (PC 로컬시간)
#    - 테스트는 00:00:00 권장
# =========================
TARGET_TIME = "00:00:00"

# =========================
# 3) 실예약/테스트 모드  ★★★★★★★★★★
# =========================
TEST_MODE = False   # True: (실예약 로직 진입 금지)
DRY_RUN = False     # True: (최종 예약 제출(action) 생략)

# =========================
# 4) 예약 파라미터(일정/프로필)  ★★★★★ (선사/날짜/계정 바뀌면 수정)
# =========================
RESERVATIONS_PLAN = {
    "20260905": [
        # === 1번 프로필: 8석 ===
        # 15석 선사 기준 상위(15~8) 우선
        {
            "seats": 8,
            "person_info": {
                "PA_N_UID": "3570",
                "PH_N_UID": "0",
                "BI_NAME": "똥길홍",
                "BI_BANK": "똥길홍",
                "BI_TEL2": "6666",
                "BI_TEL3": "6666",
                # 15석 기준 선호: 15~1
                # 8석이면 기본적으로 15,14,13,12,11,10,9,8을 우선 시도
                "seat_preference": [15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1],
            },
        },

        # === 2번 프로필: 7석 ===
        # 1번이 상위(15~8)를 우선이라면, 2번은 하위(7~1) 우선으로 분리
        {
            "seats": 7,
            "person_info": {
                "PA_N_UID": "3570",
                "PH_N_UID": "0",
                "BI_NAME": "홍길똥",
                "BI_BANK": "홍길똥",
                "BI_TEL2": "5555",
                "BI_TEL3": "3333",
                # 7석이면 기본적으로 7,6,5,4,3,2,1을 우선 시도
                # (뒤에 15~8을 붙여두면, 하위가 부족할 때 상위 잔여를 주워 담음)
                "seat_preference": [7, 6, 5, 4, 3, 2, 1, 15, 14, 13, 12, 11, 10, 9, 8],
            },
        },
    ],

    "20260906": [
        # === 다른 날짜: 15석 ===
        {
            "seats": 15,
            "person_info": {
                "PA_N_UID": "3570",
                "PH_N_UID": "0",
                "BI_NAME": "홍길동",
                "BI_BANK": "홍길동",
                "BI_TEL2": "0000",
                "BI_TEL3": "0000",
                "seat_preference": [15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1],
            },
        },
    ],
}

# =========================
# 5) 어종/상품(PS_N_UID) 자동 선택 키워드  ★★★★★ (선사 바뀌면 조정)
# =========================
SEARCH_KEYWORDS = ["쭈꾸미", "갑오징어", "광어", "우럭", "주꾸미", "쭈갑"]

# =========================
# 6) 좌석 기본 우선순위(전역 기본값)
#    - 선사 좌석 수가 15면 15~1, 20이면 20~1처럼 두는 것을 권장
# =========================
SEAT_PREFERENCE = list(range(20, 0, -1))

# =========================
# 7) 공통 payload (대부분 변경 불필요)
# =========================
COMMON_PAYLOAD = {
    "PH_N_UID": "0",
    "BI_SO_IN": "N",
    "pay_method": "undefined",
}

# =========================
# 8) 네트워크/성능 옵션 (대부분 변경 불필요)
# =========================
REQUEST_TIMEOUT = (3, 8)  # (connect timeout, read timeout)
FETCH_STEP2_PAGE = False  # 완료 페이지 GET (기본 OFF 권장)

# =============================================================================
# ✅✅✅ 사용자 설정 구역 끝
# =============================================================================


# =============================================================================
# 아래부터는 "변경 불필요" 영역 (로직/파서/실예약 처리)
# =============================================================================

# ─────────────────────────────────────────────────────────────────────────────
# 세션 최적화 (변경 불필요)
# ─────────────────────────────────────────────────────────────────────────────
def build_session():
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Accept": "*/*",
        "Connection": "keep-alive",
    })
    retry = Retry(
        total=2,
        backoff_factor=0.15,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    return s


# ─────────────────────────────────────────────────────────────────────────────
# 시간 대기 (변경 불필요)
# ─────────────────────────────────────────────────────────────────────────────
def wait_until_target_time(target_time_str):
    while True:
        now_str = time.strftime("%H:%M:%S")
        if now_str >= target_time_str:
            break
        print(f"[대기] 현재시각={now_str}, 예약오픈시각={target_time_str}")
        time.sleep(0.5)


# ─────────────────────────────────────────────────────────────────────────────
# HTML 파서 유틸 (변경 불필요)
# ─────────────────────────────────────────────────────────────────────────────
def parse_naun(html_text):
    m = re.search(r'name="naun"\s+value="(\d+)"', html_text)
    return m.group(1) if m else "1"


def parse_price(html_text):
    if "|^|" in html_text:
        first = html_text.split("|^|", 1)[0].strip()
        if first.endswith("원"):
            return first
    m = re.search(r'id="price_total">([\d,]+원)<', html_text)
    return m.group(1) if m else "0원"


def extract_ajax_parts(text):
    parts = text.split("|^|")
    while len(parts) < 4:
        parts.append("")
    return {
        "ye": parts[0].strip(),
        "to": parts[1].strip(),
        "stat": parts[2].strip(),
        "seat_html": parts[3],
    }


def find_ps_n_uid_by_keyword(html_text, keywords):
    soup = BeautifulSoup(html_text, "html.parser")
    radios = soup.find_all("input", {"type": "radio", "name": "PS_N_UID"})
    if not radios:
        return None

    best = None
    best_score = -1
    for r in radios:
        tr = r.find_parent("tr")
        text_block = tr.get_text(strip=True) if tr else ""
        score = sum(1 for kw in keywords if kw in text_block)
        if score > best_score:
            best_score = score
            best = r

    return best.get("value") if best else None


def extract_link_value(html_text):
    soup = BeautifulSoup(html_text, "html.parser")
    inp = soup.find("input", {"name": "link"})
    if inp and inp.get("value"):
        return inp.get("value")
    inp = soup.find("input", {"id": "link"})
    if inp and inp.get("value"):
        return inp.get("value")
    return None


def parse_seat_ids_order(html_text):
    soup = BeautifulSoup(html_text, "html.parser")
    form = soup.find("form", {"id": "insert_form"}) or soup.find("form")
    if not form:
        return []
    seat_inputs = form.find_all("input", {"name": "seat[]"})
    return [x.get("id") for x in seat_inputs if x.get("id")]


def seat_no_from_id(seat_id, date=None, pa_n_uid=None):
    """
    seat[] input id -> 좌석번호 변환
    (대부분: s{date}{PA_N_UID}{seatNo} 형태)
    """
    if not seat_id:
        return None
    if date and pa_n_uid:
        m = re.match(rf"^s{date}{pa_n_uid}(\d+)$", seat_id)
        if m:
            return int(m.group(1))
    # 범용 fallback: 끝자리 숫자
    m = re.search(r"(\d+)$", seat_id)
    return int(m.group(1)) if m else None


# ─────────────────────────────────────────────────────────────────────────────
# 좌석 파싱 (변경 불필요 / 핵심 로직)
# ─────────────────────────────────────────────────────────────────────────────
def parse_available_seats_from_onclick_html(html_text, date, pa_n_uid):
    """
    scr=1 최종 HTML(popup 또는 popu2)에서 onclick의
      ticket_seat_click('date','pa','seatno')
      ticket_seat_bus_click('date','pa','seatno')
    를 파싱하여 가용좌석 집합으로 반환
    """
    soup = BeautifulSoup(html_text, "html.parser")
    available = set()

    for tag in soup.find_all(onclick=True):
        oc = tag.get("onclick", "")
        if "ticket_seat_click" not in oc and "ticket_seat_bus_click" not in oc:
            continue

        m = re.search(
            r"(ticket_seat_click|ticket_seat_bus_click)\(\s*['\"]?(\d{8})['\"]?\s*,\s*['\"]?(\d+)['\"]?\s*,\s*['\"]?(\d+)['\"]?\s*\)",
            oc
        )
        if not m:
            continue

        d = m.group(2)
        pa = m.group(3)
        seat = m.group(4)

        if d == date and pa == str(pa_n_uid):
            available.add(int(seat))

    return available


def parse_available_seats_from_seat_html(seat_html):
    """
    일부 선사는 ajax seat_html을 제공할 수 있어 보조로 유지
    """
    soup = BeautifulSoup(seat_html, "html.parser")
    available = set()

    for tag in soup.find_all(onclick=True):
        oc = tag.get("onclick", "")
        if "ticket_seat_click" not in oc and "ticket_seat_bus_click" not in oc:
            continue
        m = re.search(r"\([^,]+,[^,]+,['\"]?(\d+)['\"]?\)", oc)
        if m:
            available.add(int(m.group(1)))

    return available


def choose_seats_with_fallback(requested_count, preference, available_seats):
    """
    preference 우선 선택 -> 부족하면 남은 좌석 오름차순으로 채움
    """
    chosen = []
    used = set()

    for s in preference:
        if s in available_seats and s not in used:
            chosen.append(s)
            used.add(s)
            if len(chosen) >= requested_count:
                return chosen

    for s in sorted(available_seats):
        if s not in used:
            chosen.append(s)
            used.add(s)
            if len(chosen) >= requested_count:
                return chosen

    return chosen


# ─────────────────────────────────────────────────────────────────────────────
# 오픈 대기 (변경 불필요)
# ─────────────────────────────────────────────────────────────────────────────
def is_site_open(session, date, person_info):
    url = (
        f"{BASE_URL}/popup.step1.php"
        f"?date={date}"
        f"&PA_N_UID={person_info['PA_N_UID']}"
        f"&PH_N_UID={person_info['PH_N_UID']}"
        "&scr=0"
    )
    r = session.get(url, allow_redirects=True, timeout=REQUEST_TIMEOUT)
    soup = BeautifulSoup(r.text, "html.parser")
    radios = soup.find_all("input", {"type": "radio", "name": "PS_N_UID"})
    return (len(radios) > 0)


def wait_until_site_open(session, date, person_info):
    while True:
        if is_site_open(session, date, person_info):
            print(f"[{date} 오픈 확인] 라디오 버튼 파싱 성공.")
            return
        print(f"[{date} 새로고침] 아직 사이트 오픈 안 됨. 0.5초 후 재시도.")
        time.sleep(0.5)


# ─────────────────────────────────────────────────────────────────────────────
# 예약 처리 (변경 불필요 / 실예약 로직 포함)
# ─────────────────────────────────────────────────────────────────────────────
def do_single_reservation(session, date, requested_seats, person_info):
    pa = person_info["PA_N_UID"]
    ph = person_info["PH_N_UID"]

    # 1) scr=0: PS_N_UID(상품/어종) + naun 확보
    url_scr0 = f"{BASE_URL}/popup.step1.php?date={date}&PA_N_UID={pa}&PH_N_UID={ph}&scr=0"
    r = session.get(url_scr0, allow_redirects=True, timeout=REQUEST_TIMEOUT)
    if r.status_code != 200:
        print(f"[에러] scr=0 GET 실패 status={r.status_code}")
        return False

    ps_n_uid = find_ps_n_uid_by_keyword(r.text, SEARCH_KEYWORDS)
    if not ps_n_uid:
        print(f"[에러] PS_N_UID 찾기 실패 => date={date}, name={person_info['BI_NAME']}")
        return False

    naun_value = parse_naun(r.text)
    print(f"[STEP1] date={date} name={person_info['BI_NAME']} PS_N_UID={ps_n_uid} naun={naun_value}")

    # 2) scr=1: 좌석 화면 (popup.step1 또는 popu2.step1로 리다이렉트될 수 있음)
    url_scr1 = f"{BASE_URL}/popup.step1.php?date={date}&PA_N_UID={pa}&PH_N_UID={ph}&PS_N_UID={ps_n_uid}&scr=1"
    r = session.get(url_scr1, allow_redirects=True, timeout=REQUEST_TIMEOUT)
    if r.status_code != 200:
        print(f"[에러] scr=1 GET 실패 status={r.status_code}")
        return False

    page_html = r.text
    print("[PAGE] final_url =", r.url)

    # 3) seat[] 폼 후보 (서버에 제출 가능한 좌석 슬롯)
    seat_ids_order = parse_seat_ids_order(page_html)
    seat_no_candidates = []
    for sid in seat_ids_order:
        no = seat_no_from_id(sid, date, pa)
        if no is not None:
            seat_no_candidates.append(no)
    cand_set = set(seat_no_candidates)

    print("[FORM] seat_ids_order len =", len(seat_ids_order))
    print("[FORM] seat_no_candidates =", sorted(seat_no_candidates))

    # 4) 가용좌석: HTML onclick 우선 (seat_html 의존 제거)
    available = parse_available_seats_from_onclick_html(page_html, date, pa)

    # 4-1) onclick으로 못 찾는 사이트를 위한 보조: ajax seat_html
    parsed_price = "0원"
    temp_bi_stat = "확인"
    if not available:
        url_ajax = f"{BASE_URL}/action/popup.step1.ajax.php"
        payload_ajax = {
            **COMMON_PAYLOAD,
            "date": date,
            "PA_N_UID": pa,
            "PH_N_UID": ph,
            "PS_N_UID": ps_n_uid,
            "BI_IN": str(requested_seats),
            "naun": naun_value
        }
        rr = session.post(url_ajax, data=payload_ajax, timeout=REQUEST_TIMEOUT)
        ajax_info = extract_ajax_parts(rr.text)
        parsed_price = parse_price(rr.text)
        temp_bi_stat = ajax_info["stat"] or "확인"
        seat_html = (ajax_info["seat_html"] or "").strip()
        if seat_html:
            available = parse_available_seats_from_seat_html(seat_html)

    # 4-2) 가격/상태는 가급적 확보 (일부 사이트는 필요)
    if parsed_price == "0원":
        url_ajax = f"{BASE_URL}/action/popup.step1.ajax.php"
        payload_ajax = {
            **COMMON_PAYLOAD,
            "date": date,
            "PA_N_UID": pa,
            "PH_N_UID": ph,
            "PS_N_UID": ps_n_uid,
            "BI_IN": str(requested_seats),
            "naun": naun_value
        }
        rr = session.post(url_ajax, data=payload_ajax, timeout=REQUEST_TIMEOUT)
        ajax_info = extract_ajax_parts(rr.text)
        parsed_price = parse_price(rr.text)
        temp_bi_stat = ajax_info["stat"] or temp_bi_stat

    if not available:
        print(f"[좌석] 가용좌석 0개 => date={date}, name={person_info['BI_NAME']}")
        return False

    print("[SEAT] available_raw count =", len(available))
    print("[SEAT] available_raw =", sorted(list(available)))

    # 5) 안정화 핵심: 가용좌석 ∩ seat[] 후보
    if cand_set:
        before = len(available)
        available = set(available) & cand_set
        after = len(available)
        print(f"[SEAT] intersect form: {before} -> {after}")

    if not available:
        print(f"[좌석] 교집합 후 가용좌석 0개 => date={date}, name={person_info['BI_NAME']}")
        return False

    # 6) 인원수(가용좌석 부족 시 자동 다운그레이드)
    seats_to_book = min(int(requested_seats), len(available))

    # 7) 좌석 선택
    preference = person_info.get("seat_preference") or SEAT_PREFERENCE
    chosen = choose_seats_with_fallback(seats_to_book, preference, available)

    if len(chosen) < seats_to_book:
        seats_to_book = len(chosen)

    if seats_to_book <= 0:
        print(f"[좌석] 선택 가능한 좌석 없음 => date={date}, name={person_info['BI_NAME']}")
        return False

    print(f"[CHOOSE] req={requested_seats} -> book={seats_to_book}, chosen={chosen}")

    # 8) 가격 반영(대부분 변경 불필요)
    try:
        url_price_php = f"{BASE_URL}/action/popup.step1.price.php"
        session.post(url_price_php, data={"ye": parsed_price, "buga_total": ""}, timeout=REQUEST_TIMEOUT)
    except Exception:
        pass

    # 9) seat[] payload 구성 + 검증 (좌석 없이 예약 방지)
    chosen_set = set(chosen)
    seat_values = []
    if seat_ids_order:
        for sid in seat_ids_order:
            no = seat_no_from_id(sid, date, pa)
            seat_values.append(str(no) if (no in chosen_set) else "")
    else:
        # 폼 파싱 실패는 예외 케이스 (추가 분석 필요)
        max_seat = max(available)
        for no in range(1, max_seat + 1):
            seat_values.append(str(no) if (no in chosen_set) else "")
        print(f"[경고] seat_ids_order 파싱 실패. 1~{max_seat} fallback 적용.")

    selected_in_payload = [v for v in seat_values if v.strip()]
    print("[VERIFY] seat_values filled =", selected_in_payload)

    if len(selected_in_payload) != seats_to_book:
        print(f"[치명] seat[] 매핑 실패: payload={len(selected_in_payload)}, 기대={seats_to_book}")
        print("       => 좌석 없이 예약될 위험이 있어 중단합니다.")
        return False

    # ======================================================================
    # ★★★★★★★★★★ 테스트 모드(절대 실예약 안 됨) ★★★★★★★★★★
    # ======================================================================
    if TEST_MODE:
        print("[TEST_MODE] 좌석 선택/매핑 검증 완료. (실제 예약 제출 없음)")
        return True

    # 10) link 추출(없으면 fallback)
    link_value = extract_link_value(page_html)
    if not link_value:
        link_value = "%2F_core%2Fmodule%2Freservation_boat_v5.2_seat%2Fpopu2.step2.php"
        print("[경고] link 자동 추출 실패. fallback link 사용:", link_value)

    # 11) 최종 제출(실예약)
    url_action = f"{BASE_URL}/action/popu2.step1.action.php"
    payload_items = [
        ("action", "insert"),
        ("link", link_value),
        ("temp_bi_stat", temp_bi_stat),

        ("date", date),
        ("PA_N_UID", pa),
        ("PH_N_UID", ph),
        ("PS_N_UID", ps_n_uid),

        ("BI_IN", str(seats_to_book)),
        ("BI_SO_IN", COMMON_PAYLOAD.get("BI_SO_IN", "N")),
        ("pay_method", COMMON_PAYLOAD.get("pay_method", "undefined")),
        ("naun", naun_value),

        ("BI_NAME", person_info["BI_NAME"]),
        ("BI_BANK", person_info["BI_BANK"]),
        ("BI_TEL1", "010"),  # (필요 시 수정)
        ("BI_TEL2", person_info["BI_TEL2"]),
        ("BI_TEL3", person_info["BI_TEL3"]),
        ("BI_MEMO", ""),

        ("agree", "Y"),
        ("BI_3JA", "1"),
        ("BI_AD", "1"),
        ("all_agree", "Y"),
    ]
    for v in seat_values:
        payload_items.append(("seat[]", v))

    # ======================================================================
    # ★★★★★★★★★★ DRY_RUN(실예약 제출 생략) ★★★★★★★★★★
    # ======================================================================
    if DRY_RUN:
        print("[DRY_RUN] 최종 제출(action.php) 생략. 여기까지 정상 흐름입니다.")
        return True

    rr = session.post(url_action, data=payload_items, timeout=REQUEST_TIMEOUT)
    print(f"[RESERVED] date={date}, book={seats_to_book}, name={person_info['BI_NAME']}, status={rr.status_code}")

    if FETCH_STEP2_PAGE:
        try:
            rr2 = session.get(f"{BASE_URL}/popu2.step2.php", timeout=REQUEST_TIMEOUT)
            print(f"[STEP2] status={rr2.status_code}")
        except Exception:
            pass

    return True


# ─────────────────────────────────────────────────────────────────────────────
# 메인 (변경 불필요)
# ─────────────────────────────────────────────────────────────────────────────
def main():
    wait_until_target_time(TARGET_TIME)

    for date, jobs in RESERVATIONS_PLAN.items():
        if not jobs:
            continue

        # 날짜별 오픈 대기(대표 프로필로 확인)
        tmp = build_session()
        wait_until_site_open(tmp, date, jobs[0]["person_info"])
        tmp.close()

        print(f"=== [날짜: {date}] 처리 시작(순차) ===")

        # 같은 날짜 여러 건은 반드시 순차 처리(좌석 갱신 반영)
        for job in jobs:
            session = build_session()
            try:
                ok = do_single_reservation(session, date, job["seats"], job["person_info"])
                if not ok:
                    print(f"[실패] date={date}, name={job['person_info'].get('BI_NAME','?')}")
            except Exception as e:
                print(f"[예외] date={date}, name={job['person_info'].get('BI_NAME','?')} => {e}")
            finally:
                session.close()

    print("[모든 날짜 처리 완료]")


if __name__ == "__main__":
    main()
