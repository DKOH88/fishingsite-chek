# -*- coding: utf-8 -*-
"""
더피싱 플랫폼 API 봇 베이스 클래스
실제 작동하는 샤크호/비엔나호/헤르메스호 패턴 기반

플로우:
1. popu2.step1.php 로드 (PS_N_UID 파싱)
2. /action/popu2.step1.action.php 전송 → step2.php 도달 = 성공
"""
import re
import time
import requests
import sys
import json
from urllib.parse import quote
import os
import io
import argparse
from datetime import datetime
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Windows 콘솔 UTF-8 인코딩 설정
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)


# 모듈 레벨 로그 파일 경로 (setup_log_file 호출 시 설정됨)
_log_file_path = None


def log(message, end="\n", flush=False):
    """시간 포함 로그 출력 + 파일 기록"""
    global _log_file_path
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-4]  # 10:32:08.89 형식
    formatted_msg = f"[{timestamp}] {message}"
    print(formatted_msg, end=end, flush=flush)

    # 파일 기록
    if _log_file_path:
        try:
            with open(_log_file_path, "a", encoding="utf-8") as f:
                f.write(formatted_msg + "\n")
        except Exception:
            pass


class TheFishingAPIBot:
    """더피싱 플랫폼 API 봇 베이스 클래스"""

    # =========================================================================
    # 서브클래스에서 오버라이드할 설정
    # =========================================================================
    BASE_URL = ""               # 예: "http://www.yamujinfishing.com/_core/module/reservation_boat_v5.2_seat1"
    PA_N_UID = ""               # 코스 ID (선사별 고정)
    PROVIDER_NAME = ""          # 예: 샤크호
    HAS_SEAT_SELECTION = False  # 좌석 선택 여부
    SEAT_PRIORITY = []          # 좌석 우선순위 (예: ['15', '14', '1', ...])
    RESERVATION_TYPE = "2step"  # 예약 타입: "2step" (popu2) 또는 "3step" (popup)

    # 어종 자동 선택 키워드
    SEARCH_KEYWORDS = ["쭈갑", "쭈꾸미&갑오징어", "쭈&갑", "쭈꾸미", "갑오징어", "문어"]

    # 네트워크 설정
    REQUEST_TIMEOUT = (3, 5)

    def __init__(self):
        # 기본 설정
        self.target_time = "00:00:00"
        self.test_mode = False
        self.dry_run = False
        self.test_mode_skip_wait = False
        self.reservations_plan = {}

        # 로그용 설정 저장
        self._config_port = ''
        self._config_provider = ''
        self._config_target_date = ''
        self._config_user_name = ''
        self._config_user_phone = ''

        # 예약 타입 - 클래스 변수에서 복사 (서브클래스에서 오버라이드 가능)
        self.reservation_type = self.RESERVATION_TYPE

        # 설정 로드
        self.load_config_from_file()

    # =========================================================================
    # Config Loader (GUI Support)
    # =========================================================================
    def load_config_from_file(self):
        """설정 파일 로드"""
        parser = argparse.ArgumentParser()
        parser.add_argument("--config", required=False)
        args, _ = parser.parse_known_args()

        config_path = args.config if args.config else (sys.argv[1] if len(sys.argv) > 1 else None)

        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                log(f"📂 [설정로드] {config_path}")

                # 1. Global Settings
                self.target_time = config.get('target_time', self.target_time)

                # test_mode: 시간 대기 건너뛰기
                if config.get('test_mode', False):
                    self.test_mode_skip_wait = True
                    log("🚀 [Test Mode] 시간 대기 없이 즉시 실행합니다!")

                # simulation_mode: 실전송 생략
                if config.get('simulation_mode', False):
                    self.test_mode = True
                    self.dry_run = True
                    log("🧪 [Simulation Mode] 실전송 생략 모드 활성화")
                else:
                    self.test_mode = False
                    self.dry_run = False

                # 2. 런처에서 직접 전달된 값 확인 (temp_config 방식)
                target_date = config.get('target_date', '')
                u_name = config.get('user_name', '')
                u_phone = config.get('user_phone', '')
                u_depositor = config.get('user_depositor', '')
                seats_n = int(config.get('person_count', 1))

                # 로그용 설정 저장
                self._config_port = config.get('port', '')
                self._config_provider = config.get('provider', self.PROVIDER_NAME)
                self._config_target_date = target_date
                self._config_user_name = u_name
                self._config_user_phone = u_phone

                if target_date and u_name:
                    # 전화번호 파싱
                    p2, p3 = "0000", "0000"
                    parts = u_phone.split('-')
                    if len(parts) >= 3:
                        p2, p3 = parts[1], parts[2]
                    elif len(u_phone) == 11:
                        p2, p3 = u_phone[3:7], u_phone[7:]

                    self.reservations_plan = {
                        target_date: [
                            {
                                "seats": seats_n,
                                "person_info": {
                                    "PA_N_UID": self.PA_N_UID,
                                    "PH_N_UID": "0",
                                    "BI_NAME": u_name,
                                    "BI_BANK": u_depositor,
                                    "BI_TEL2": p2,
                                    "BI_TEL3": p3,
                                    "seat_preference": self.SEAT_PRIORITY if self.HAS_SEAT_SELECTION else [],
                                }
                            }
                        ]
                    }
                    formatted_date = f"{target_date[:4]}년{target_date[4:6]}월{target_date[6:8]}일"
                    log(f"📅 [설정적용] 날짜: {formatted_date}, 인원: {seats_n}명, 이름: {u_name}")

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

                        # 로그용 설정 저장 (multi_instance 방식)
                        self._config_port = item.get('port', config.get('port', ''))
                        self._config_provider = item.get('provider', self.PROVIDER_NAME)
                        self._config_target_date = target_date
                        self._config_user_name = u_name
                        self._config_user_phone = u_phone

                        p2, p3 = "0000", "0000"
                        parts = u_phone.split('-')
                        if len(parts) >= 3:
                            p2, p3 = parts[1], parts[2]
                        elif len(u_phone) == 11:
                            p2, p3 = u_phone[3:7], u_phone[7:]

                        self.reservations_plan = {
                            target_date: [
                                {
                                    "seats": seats_n,
                                    "person_info": {
                                        "PA_N_UID": self.PA_N_UID,
                                        "PH_N_UID": "0",
                                        "BI_NAME": u_name,
                                        "BI_BANK": u_depositor,
                                        "BI_TEL2": p2,
                                        "BI_TEL3": p3,
                                        "seat_preference": self.SEAT_PRIORITY if self.HAS_SEAT_SELECTION else [],
                                    }
                                }
                            ]
                        }
                        formatted_date = f"{target_date[:4]}년{target_date[4:6]}월{target_date[6:8]}일"
                        log(f"📅 [설정적용] 날짜: {formatted_date}, 인원: {seats_n}명, 이름: {u_name}")

            except Exception as e:
                log(f"⚠️ 설정 로드 실패: {e}")
        else:
            log("⚠️ 설정 파일이 존재하지 않습니다.")

    # =========================================================================
    # Session & Network
    # =========================================================================
    def build_session(self):
        """세션 생성"""
        s = requests.Session()
        # Origin URL 추출 (BASE_URL에서 도메인까지)
        origin = self.BASE_URL.split("/_core")[0] if "/_core" in self.BASE_URL else self.BASE_URL

        s.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Connection": "keep-alive",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": origin
        })
        retry = Retry(total=2, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        s.mount("http://", adapter)
        s.mount("https://", adapter)
        return s

    # =========================================================================
    # Time Management
    # =========================================================================
    def wait_until_target_time(self, target_time_str):
        """목표 시간까지 대기 (마일스톤 기반 알림)"""
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
            log(f"⏰ 타겟 시간 {target_time_str} 이미 경과 - 즉시 시작!")
            return

        log(f"⏰ 타겟 시간: {target_time_str}")
        log(f"현재 시간: {now.strftime('%H:%M:%S')}")

        # 초기 남은 시간 표시
        initial_remaining = (target - now).total_seconds()
        init_mins, init_secs = divmod(initial_remaining, 60)
        log(f"⏳ 남은 시간: {int(init_mins)}분 {int(init_secs)}초")

        # 마일스톤 알림 플래그 (이미 지난 마일스톤은 건너뛰기)
        notified_1min = initial_remaining <= 60
        notified_30sec = initial_remaining <= 30
        notified_10sec = initial_remaining <= 10
        notified_countdown = {
            5: initial_remaining <= 5,
            4: initial_remaining <= 4,
            3: initial_remaining <= 3,
            2: initial_remaining <= 2,
            1: initial_remaining <= 1
        }

        while True:
            now = datetime.now()
            if now >= target:
                log(f"🔔 타겟 시간 도달! 예약 시작!")
                break

            remaining = (target - now).total_seconds()

            # 마일스톤 알림
            if remaining <= 60 and not notified_1min:
                log(f"⏳ 1분 전!")
                notified_1min = True
            elif remaining <= 30 and not notified_30sec:
                log(f"⏳ 30초 전!")
                notified_30sec = True
            elif remaining <= 10 and not notified_10sec:
                log(f"⏳ 10초 전!")
                notified_10sec = True

            # 5초 카운트다운
            for sec in [5, 4, 3, 2, 1]:
                if remaining <= sec and not notified_countdown[sec]:
                    log(f"⏳ {sec}...")
                    notified_countdown[sec] = True

            time.sleep(0.05)  # 정밀도를 위해 0.05초 간격

    # =========================================================================
    # Helper Functions (Regex Only - Faster)
    # =========================================================================
    def parse_naun(self, html):
        """잔여석(naun) 파싱"""
        # 1. Try input hidden with regex
        m = re.search(r'name="naun"\s+value="(\d+)"', html)
        if m:
            return m.group(1)

        # 2. Try span id="id_bi_in" with regex
        m2 = re.search(r'<span id="id_bi_in">\s*(\d+)\s*</span>', html)
        if m2:
            return m2.group(1)

        return "1"

    def find_ps_n_uid(self, html, keywords):
        """어종 PS_N_UID 파싱"""
        soup = BeautifulSoup(html, "html.parser")
        radios = soup.find_all("input", {"type": "radio", "name": "PS_N_UID"})
        if not radios:
            # CSS 클래스로도 찾아볼 수 있음
            radios = soup.find_all("input", {"class": "PS_N_UID"})
        if not radios:
            return None

        if len(radios) == 1:
            return radios[0].get("value")

        for r in radios:
            # ps_selis 클래스를 가진 span을 찾아봄
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

    def parse_available_seats(self, html):
        """예약 가능한 좌석 파싱 (HTML 방식)"""
        soup = BeautifulSoup(html, "html.parser")

        available_seats = []
        reserved_seats = []
        seat_class = None
        reserved_classes = []

        # 선사마다 다른 클래스: res_num_view 또는 num_view
        if soup.find("span", class_="res_num_view"):
            seat_class = "res_num_view"
            # 예약된 좌석: res_num_view_disable (주로 사용) 또는 res_num_view_end (일부 선사)
            reserved_classes = ["res_num_view_disable", "res_num_view_end"]
            log(f"✅ 좌석 클래스 감지: res_num_view")
        elif soup.find("span", class_="num_view"):
            seat_class = "num_view"
            reserved_classes = ["num_view_disable", "num_view_end"]
            log(f"✅ 좌석 클래스 감지: num_view")
        else:
            log(f"⚠️ 좌석 클래스를 찾을 수 없습니다.")
            return []

        # 빈 좌석: class="{seat_class}" + onclick 속성
        for span in soup.find_all("span", class_=seat_class):
            if span.get("onclick"):  # onclick이 있으면 예약 가능
                seat_num = span.get_text(strip=True)
                if seat_num:  # 빈 문자열만 제외, 모든 좌석명 허용 (선22, 선21 등)
                    available_seats.append(seat_num)

        # 예약된 좌석: res_num_view_disable 또는 res_num_view_end (여러 클래스 지원)
        for reserved_class in reserved_classes:
            for span in soup.find_all("span", class_=reserved_class):
                seat_num = span.get_text(strip=True)
                if seat_num:  # 빈 문자열만 제외, 모든 좌석명 허용 (선22, 선21 등)
                    if seat_num not in reserved_seats:  # 중복 방지
                        reserved_seats.append(seat_num)

        log(f"📊 빈 좌석: {available_seats}")
        log(f"🚫 예약된 좌석: {reserved_seats}")

        return available_seats

    def select_best_seats(self, available_seats, seat_preference, count):
        """우선순위에 따라 최적 좌석 선택"""
        selected_seats = []

        # 선호 좌석 중 빈 좌석 선택
        for pref in seat_preference:
            pref_str = str(pref)
            if pref_str in available_seats and len(selected_seats) < count:
                selected_seats.append(pref_str)
                log(f"✨ 우선순위 좌석 {pref_str}번 선택! ({len(selected_seats)}/{count})")

        # 선호 좌석이 다 차있으면 아무 빈 좌석 선택
        if len(selected_seats) < count:
            log(f"⚠️ 우선순위 좌석 부족. 남은 좌석 중 선택...")
            for seat in available_seats:
                if seat not in selected_seats and len(selected_seats) < count:
                    selected_seats.append(seat)
                    log(f"🎲 무작위 좌석 {seat}번 선택! ({len(selected_seats)}/{count})")

        return selected_seats

    # =========================================================================
    # Main Reservation Function
    # =========================================================================
    def do_reservation(self, session, date, job):
        """예약 실행"""
        info = job["person_info"]
        seats_needed = job["seats"]
        ph_n_uid = info.get("PH_N_UID", "0")

        # ─────────────────────────────────────────────────────────────
        # Step 1-1: 초기 페이지 로드 (어종 목록 파악)
        # ─────────────────────────────────────────────────────────────
        step_start = time.time()
        url_1 = f"{self.BASE_URL}/popu2.step1.php?date={date}&PA_N_UID={self.PA_N_UID}"
        log(f"📡 [Step 1-1] GET 요청 전송...")
        log(f"🔗 URL: {url_1}")

        session.headers.update({"Referer": url_1})
        r = session.get(url_1, timeout=self.REQUEST_TIMEOUT)

        step_duration = time.time() - step_start
        log(f"✅ 응답 수신: Status={r.status_code}, Size={len(r.text)}bytes")
        log(f"⏱️ [Step 1-1] 초기 로드 완료: {step_duration:.4f}초")

        # ─────────────────────────────────────────────────────────────
        # Step 1-1-2: 어종 파싱
        # ─────────────────────────────────────────────────────────────
        parse_start = time.time()
        ps_uid = self.find_ps_n_uid(r.text, self.SEARCH_KEYWORDS)
        parse_duration = time.time() - parse_start

        if not ps_uid:
            log(f"❌ [실패] 어종 선택 불가 ({date})")
            log(f"🔍 검색 키워드: {self.SEARCH_KEYWORDS}")
            return False

        log(f"🎣 어종 PS_N_UID 파싱: {ps_uid} ({parse_duration:.4f}초)")

        # =============== [TOTAL TIME START] =================
        total_start_time = time.time()
        log(f"⏱️ [타이머 시작] 어종 선택부터 측정 시작...")

        # ─────────────────────────────────────────────────────────────
        # 좌석 선점 실패 시 재파싱 루프 (Step 1-2 ~ Step 3)
        # ─────────────────────────────────────────────────────────────
        MAX_SEAT_RETRIES = 5  # 좌석 재파싱 최대 시도
        original_seats_needed = seats_needed  # 원본 저장

        for seat_retry in range(MAX_SEAT_RETRIES):
            if seat_retry > 0:
                log(f"🔄 [좌석 재파싱 {seat_retry}/{MAX_SEAT_RETRIES}] 최신 잔여석 정보 다시 가져오기...")
                seats_needed = original_seats_needed  # 원본으로 복원

            # ─────────────────────────────────────────────────────────────
            # Step 1-2: 어종 선택 적용 및 잔여석(naun) 파악
            # ─────────────────────────────────────────────────────────────
            step_start = time.time()
            url_2 = f"{self.BASE_URL}/popu2.step1.php?date={date}&PA_N_UID={self.PA_N_UID}&PS_N_UID={ps_uid}"
            log(f"📡 [Step 1-2] GET 요청 전송 (어종 선택 적용)...")
            log(f"🔗 URL: {url_2}")

            session.headers.update({"Referer": url_1})
            r = session.get(url_2, timeout=self.REQUEST_TIMEOUT)

            http_duration = time.time() - step_start
            log(f"✅ 응답 수신: Status={r.status_code}, Size={len(r.text)}bytes ({http_duration:.4f}초)")

            # 잔여석 파싱
            parse_start = time.time()
            html_step1 = r.text
            naun = self.parse_naun(html_step1)
            parse_duration = time.time() - parse_start

            log(f"🪑 잔여석(naun) 파싱: {naun}석 ({parse_duration:.4f}초)")

            # ─────────────────────────────────────────────────────────────
            # 잔여석 자동 조정: naun < seats_needed 이면 naun으로 조정
            # ─────────────────────────────────────────────────────────────
            try:
                naun_int = int(naun)
                if naun_int == 0:
                    log(f"❌ 잔여석 0석 - 만석으로 예약 불가!")
                    log(f"⏸️ 봇 중지. 브라우저는 대기 상태 유지.")
                    return "SOLD_OUT"
                elif naun_int < seats_needed:
                    log(f"⚠️ 잔여석({naun}) < 요청({seats_needed}) → {naun}석으로 자동 조정!")
                    seats_needed = naun_int
            except ValueError:
                log(f"⚠️ naun 파싱 오류: {naun}")

            log(f"⏱️ [Step 1-2] 어종 선택 및 정보 로드: {time.time() - step_start:.4f}초")

            # ─────────────────────────────────────────────────────────────
            # Step 1-3: 좌석 선택 (seat_preference 기반)
            # ─────────────────────────────────────────────────────────────
            step_start = time.time()
            seat_preference = info.get("seat_preference", [])
            selected_seats = []
            final_seats_needed = seats_needed

            if self.HAS_SEAT_SELECTION:
                if seat_preference:
                    log(f"🪑 [Step 1-3] 좌석 선택 처리 중...")
                    log(f"📋 선호 좌석 우선순위: {seat_preference}")
                    log(f"👥 설정 인원: {seats_needed}명")

                    # HTML에서 빈 좌석 파싱
                    available_seats = self.parse_available_seats(html_step1)
                    available_count = len(available_seats)

                    # naun(서버 잔여석)과 HTML 파싱 결과 비교
                    try:
                        naun_int = int(naun)
                        if available_count != naun_int:
                            log(f"📊 HTML 빈좌석: {available_count}석 (서버 잔여석: {naun_int}석)")
                            log(f"ℹ️ 서버 잔여석({naun_int})을 기준으로 처리합니다.")
                            # 서버 잔여석이 더 적으면 그 값을 신뢰
                            effective_available = min(available_count, naun_int)
                        else:
                            log(f"📊 가용 좌석 수: {available_count}석")
                            effective_available = available_count
                    except ValueError:
                        log(f"📊 가용 좌석 수: {available_count}석")
                        effective_available = available_count

                    # 가용 좌석이 설정 인원보다 적으면 자동 조정
                    if effective_available < seats_needed:
                        log(f"⚠️ 가용 좌석 부족! 인원을 {seats_needed}명 → {effective_available}명으로 자동 조정합니다.")
                        final_seats_needed = effective_available

                    # 좌석 선택
                    if available_seats:
                        selected_seats = self.select_best_seats(available_seats, seat_preference, final_seats_needed)

                    if selected_seats:
                        log(f"✅ 좌석 선택 완료! 총 {len(selected_seats)}석 선택됨. (선택순서: {' → '.join(selected_seats)})")
                    else:
                        log(f"⚠️ 빈 좌석 없음 또는 선호 좌석 모두 예약됨")

                    log(f"⏱️ [Step 1-4] 좌석 선택 완료: {time.time() - step_start:.4f}초")
                else:
                    log(f"⏩ [Step 1-3] 좌석 선택 생략 (seat_preference 없음)")
            else:
                log(f"⏩ [Step 1-3] 좌석 선택 비활성화 (HAS_SEAT_SELECTION=False)")

            # ─────────────────────────────────────────────────────────────
            # Step 2: 페이로드 구성
            # ─────────────────────────────────────────────────────────────
            step_start = time.time()
            log(f"📝 [Step 2] 예약 페이로드 구성 중...")

            payload = [
                ("action", "insert"),
                ("link", f"/_core/module/{self.BASE_URL.split('/module/')[-1]}/popu2.step2.php"),
                ("temp_bi_stat", "확인"),
                ("date", date),
                ("PA_N_UID", self.PA_N_UID),
                ("PH_N_UID", ph_n_uid),
                ("PS_N_UID", ps_uid),
                ("BI_IN", str(len(selected_seats) if selected_seats else final_seats_needed)),
                ("BI_SO_IN", "N"),
                ("pay_method", "undefined"),
                ("naun", naun),
                ("BI_NAME", info["BI_NAME"]),
                ("BI_BANK", info.get("BI_BANK", "")),
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
                    payload.append(("seat[]", str(seat)))  # 브라우저 실제 전송 형식
                log(f"🪑 좌석 정보 추가: {selected_seats}")

            payload_duration = time.time() - step_start
            log(f"📋 페이로드 항목 수: {len(payload)}개")
            log(f"📋 주요 데이터: date={date}, PA={self.PA_N_UID}, PS={ps_uid}, BI_IN={len(selected_seats) if selected_seats else final_seats_needed}, naun={naun}")
            log(f"📋 사용자: {info['BI_NAME']}, 010-{info['BI_TEL2']}-{info['BI_TEL3']}")
            log(f"⏱️ [Step 2] 페이로드 구성 완료: {payload_duration:.4f}초")

            # ─────────────────────────────────────────────────────────────
            # 테스트/시뮬레이션 모드 체크
            # ─────────────────────────────────────────────────────────────
            if self.test_mode or self.dry_run:
                log(f"🧪 [테스트 모드] 실전송 생략됨 (TEST_MODE={self.test_mode}, DRY_RUN={self.dry_run})")
                total_duration = time.time() - total_start_time
                log(f"⏱️ [Total] 총 소요 시간(어종선택부터): {total_duration:.4f}초")
                return True

            # ─────────────────────────────────────────────────────────────
            # Step 3: 예약 전송 (Action)
            # ─────────────────────────────────────────────────────────────
            step_start = time.time()
            url_action = f"{self.BASE_URL}/action/popu2.step1.action.php"
            log(f"📡 [Step 3] POST 예약 전송...")
            log(f"🔗 URL: {url_action}")

            session.headers.update({"Referer": url_2})

            try:
                res = session.post(url_action, data=payload, timeout=self.REQUEST_TIMEOUT)
                http_duration = time.time() - step_start

                log(f"✅ 응답 수신: Status={res.status_code}, Size={len(res.text)}bytes")
                log(f"⏱️ [Step 3] 최종 전송 완료: {http_duration:.4f}초")

                if res.status_code == 200:
                    response_text = res.text.strip()
                    log(f"📊 [응답 분석]")
                    log(f"📄 응답 내용: {response_text[:200]}..." if len(response_text) > 200 else f"📄 응답 내용: {response_text}")

                    # 성공/실패 메시지 확인
                    if "예약 신청이 완료되었습니다" in response_text or "step2" in response_text.lower():
                        log("🎉 [결과] 예약 성공!")
                        total_duration = time.time() - total_start_time
                        log(f"⏱️ [Total] 총 소요 시간(어종선택부터): {total_duration:.4f}초")
                        return True

                    elif "정상적으로 예약해 주십시오" in response_text:
                        log("⚠️ [결과] 예약 오류 - 처음부터 다시 시도 필요")
                        return "RETRY_FULL"  # 전체 재시도 (외부로 반환)

                    elif any(kw in response_text for kw in ["이미", "불가능", "선점", "마감", "없습니다", "예약할 수 없습니다"]):
                        log("⚠️ [결과] 좌석 선점 실패 - 잔여석 재파싱 후 재시도")
                        time.sleep(0.05)
                        continue  # 루프 계속 (Step 1-2부터 재시작)

                    else:
                        log("⚠️ [결과] 예상 밖 응답 - 재파싱 후 재시도")
                        log(f"📄 응답: {response_text[:300]}")
                        continue  # 재파싱 루프 계속
                else:
                    log(f"❌ [전송실패] Status: {res.status_code}")
                    if res.status_code in [502, 503]:
                        return "RETRY_FULL"  # 서버 에러 - 전체 재시도
                    continue  # 다시 시도

            except requests.exceptions.Timeout:
                log(f"❌ [타임아웃] 서버 응답 없음 - 재파싱 후 재시도")
                continue  # 루프 계속
            except requests.exceptions.ConnectionError:
                log(f"❌ [연결실패] 서버 연결 불가")
                return "RETRY_FULL"
            except Exception as e:
                log(f"❌ [통신에러] {e}")
                continue  # 루프 계속

        # 모든 재시도 소진
        log(f"❌ 좌석 재파싱 최대 시도({MAX_SEAT_RETRIES}회) 초과!")
        return "RETRY_FULL"

    # =========================================================================
    # 3단계 예약 (popup.step1 → popup.step2 → popup.step3)
    # =========================================================================
    def do_reservation_3step(self, session, date, job):
        """3단계 예약 실행 (popup 방식 - v5.1)"""
        info = job["person_info"]
        seats_needed = job["seats"]
        ph_n_uid = info.get("PH_N_UID", "0")

        # ─────────────────────────────────────────────────────────────
        # Step 1-1: 초기 페이지 로드 (어종 목록 파악)
        # ─────────────────────────────────────────────────────────────
        step_start = time.time()
        url_1 = f"{self.BASE_URL}/popup.step1.php?date={date}&PA_N_UID={self.PA_N_UID}"
        log(f"📡 [Step 1-1] GET 요청 전송...")
        log(f"🔗 URL: {url_1}")

        session.headers.update({"Referer": url_1})
        # 3단계는 일반 Form Submit이므로 XMLHttpRequest 헤더 제거
        if "X-Requested-With" in session.headers:
            del session.headers["X-Requested-With"]

        r = session.get(url_1, timeout=self.REQUEST_TIMEOUT)

        step_duration = time.time() - step_start
        log(f"✅ 응답 수신: Status={r.status_code}, Size={len(r.text)}bytes")
        log(f"⏱️ [Step 1-1] 초기 로드 완료: {step_duration:.4f}초")

        # ─────────────────────────────────────────────────────────────
        # Step 1-1-2: 어종 파싱
        # ─────────────────────────────────────────────────────────────
        parse_start = time.time()
        ps_uid = self.find_ps_n_uid(r.text, self.SEARCH_KEYWORDS)
        parse_duration = time.time() - parse_start

        if not ps_uid:
            log(f"❌ [실패] 어종 선택 불가 ({date})")
            log(f"🔍 검색 키워드: {self.SEARCH_KEYWORDS}")
            return False

        log(f"🎣 어종 PS_N_UID 파싱: {ps_uid} ({parse_duration:.4f}초)")

        # =============== [TOTAL TIME START] =================
        total_start_time = time.time()
        log(f"⏱️ [타이머 시작] 어종 선택부터 측정 시작...")

        # ─────────────────────────────────────────────────────────────
        # Step 1-2: 어종 선택 적용 및 잔여석(naun) 파악
        # ─────────────────────────────────────────────────────────────
        step_start = time.time()
        url_2 = f"{self.BASE_URL}/popup.step1.php?date={date}&PA_N_UID={self.PA_N_UID}&PS_N_UID={ps_uid}"
        log(f"📡 [Step 1-2] GET 요청 전송 (어종 선택 적용)...")
        log(f"🔗 URL: {url_2}")

        session.headers.update({"Referer": url_1})
        r = session.get(url_2, timeout=self.REQUEST_TIMEOUT)

        http_duration = time.time() - step_start
        log(f"✅ 응답 수신: Status={r.status_code}, Size={len(r.text)}bytes ({http_duration:.4f}초)")

        # 잔여석 파싱
        parse_start = time.time()
        html_step1 = r.text
        naun = self.parse_naun(html_step1)
        parse_duration = time.time() - parse_start

        log(f"🪑 잔여석(naun) 파싱: {naun}석 ({parse_duration:.4f}초)")

        # 잔여석 자동 조정
        try:
            naun_int = int(naun)
            if naun_int == 0:
                log(f"❌ 잔여석 0석 - 만석으로 예약 불가!")
                log(f"⏸️ 봇 중지. 브라우저는 대기 상태 유지.")
                return "SOLD_OUT"
            elif naun_int < seats_needed:
                log(f"⚠️ 잔여석({naun}) < 요청({seats_needed}) → {naun}석으로 자동 조정!")
                seats_needed = naun_int
        except ValueError:
            log(f"⚠️ naun 파싱 오류: {naun}")

        log(f"⏱️ [Step 1-2] 어종 선택 및 정보 로드: {time.time() - step_start:.4f}초")

        # ─────────────────────────────────────────────────────────────
        # Step 1-3: 좌석 선택 (seat_preference 기반)
        # ─────────────────────────────────────────────────────────────
        step_start = time.time()
        seat_preference = info.get("seat_preference", [])
        selected_seats = []
        final_seats_needed = seats_needed

        if self.HAS_SEAT_SELECTION:
            if seat_preference:
                log(f"🪑 [Step 1-3] 좌석 선택 처리 중...")
                log(f"📋 선호 좌석 우선순위: {seat_preference}")
                log(f"👥 설정 인원: {seats_needed}명")

                available_seats = self.parse_available_seats(html_step1)
                available_count = len(available_seats)

                try:
                    naun_int = int(naun)
                    if available_count != naun_int:
                        log(f"📊 HTML 빈좌석: {available_count}석 (서버 잔여석: {naun_int}석)")
                        effective_available = min(available_count, naun_int)
                    else:
                        log(f"📊 가용 좌석 수: {available_count}석")
                        effective_available = available_count
                except ValueError:
                    log(f"📊 가용 좌석 수: {available_count}석")
                    effective_available = available_count

                if effective_available < seats_needed:
                    log(f"⚠️ 가용 좌석 부족! 인원을 {seats_needed}명 → {effective_available}명으로 자동 조정합니다.")
                    final_seats_needed = effective_available

                if available_seats:
                    selected_seats = self.select_best_seats(available_seats, seat_preference, final_seats_needed)

                if selected_seats:
                    log(f"✅ 좌석 선택 완료! 총 {len(selected_seats)}석 선택됨. (선택순서: {' → '.join(selected_seats)})")
                else:
                    log(f"⚠️ 빈 좌석 없음 또는 선호 좌석 모두 예약됨")

                log(f"⏱️ [Step 1-4] 좌석 선택 완료: {time.time() - step_start:.4f}초")
            else:
                log(f"⏩ [Step 1-3] 좌석 선택 생략 (seat_preference 없음)")
        else:
            log(f"⏩ [Step 1-3] 좌석 선택 비활성화 (HAS_SEAT_SELECTION=False)")

        # ─────────────────────────────────────────────────────────────
        # Step 1.5: 인원/가격 AJAX (popup.step1.ajax.php)
        # 브라우저에서 인원(BI_IN) 선택 시 호출되는 핵심 AJAX
        # 이 호출이 PHP 세션에 가격 데이터를 기록함
        # ─────────────────────────────────────────────────────────────
        step_start = time.time()
        bi_in_count = len(selected_seats) if selected_seats else final_seats_needed
        log(f"📡 [Step 1.5] 인원/가격 AJAX 전송 (BI_IN={bi_in_count})...")

        ajax_step1_url = f"{self.BASE_URL}/action/popup.step1.ajax.php"
        ph_n_uid = info.get("PH_N_UID", "0")
        ajax_data = f"date={date}&PA_N_UID={self.PA_N_UID}&PH_N_UID={ph_n_uid}&PS_N_UID={ps_uid}&BI_IN={bi_in_count}&BI_SO_IN=N&pay_method=&naun={naun}"

        try:
            session.headers.update({
                "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "Referer": url_2,
            })
            resp_ajax = session.post(ajax_step1_url, data=ajax_data.encode('utf-8'), timeout=self.REQUEST_TIMEOUT)
            ajax_text = resp_ajax.text.strip()
            log(f"✅ 인원/가격 AJAX 응답: {ajax_text[:200]}")

            # 응답 파싱: "가격표시|^|총액표시|^|확인상태|^|좌석HTML"
            ajax_parts = ajax_text.split("|^|")
            if len(ajax_parts) >= 3:
                ye_display = ajax_parts[0]   # e.g. "110,000원"
                to_display = ajax_parts[1]   # e.g. "110,000원"
                bi_stat = ajax_parts[2]      # "확인" or error status
                log(f"📊 가격: {ye_display}, 총액: {to_display}, 상태: {bi_stat}")

                if "초과" in bi_stat or "불가" in bi_stat:
                    log(f"⚠️ 인원 초과/불가 응답: {bi_stat}")
                    return "RETRY_FULL"
            else:
                ye_display = ""
                log(f"⚠️ 인원/가격 AJAX 응답 형식 이상 (무시하고 진행)")
        except Exception as e:
            ye_display = ""
            log(f"⚠️ 인원/가격 AJAX 실패 (무시): {e}")
        finally:
            if "X-Requested-With" in session.headers:
                del session.headers["X-Requested-With"]
            if "Content-Type" in session.headers:
                del session.headers["Content-Type"]

        log(f"⏱️ [Step 1.5] 인원/가격 AJAX: {time.time() - step_start:.4f}초")

        # ─────────────────────────────────────────────────────────────
        # Step 2: 페이로드 구성
        # ─────────────────────────────────────────────────────────────
        step_start = time.time()
        log(f"📝 [Step 2] 예약 페이로드 구성 중...")

        # 3단계용 link (popup.step2.php)
        module_path = self.BASE_URL.split('/module/')[-1] if '/module/' in self.BASE_URL else ""

        # link를 브라우저와 동일하게 URL-인코딩
        encoded_link = quote(f"/_core/module/{module_path}/popup.step2.php", safe='')

        payload = [
            ("action", "insert"),
            ("link", encoded_link),
            ("temp_bi_stat", "확인"),
            ("PA_N_UID", self.PA_N_UID),
            ("PS_N_UID", ps_uid),
            ("BI_IN", str(len(selected_seats) if selected_seats else final_seats_needed)),
            ("BI_NAME", info["BI_NAME"]),
            ("BI_BANK", info.get("BI_BANK", "")),
            ("BI_TEL1", "010"),
            ("BI_TEL2", info["BI_TEL2"]),
            ("BI_TEL3", info["BI_TEL3"]),
            ("BI_MEMO", ""),
            ("agree", "Y"),
            ("BI_3JA", "1"),
            ("BI_AD", "1"),
            ("all_agree", "Y"),
        ]

        if selected_seats:
            for seat in selected_seats:
                payload.append(("seat[]", str(seat)))
            log(f"🪑 좌석 정보 추가: {selected_seats}")

        payload_duration = time.time() - step_start
        log(f"📋 페이로드 항목 수: {len(payload)}개")
        log(f"📋 주요 데이터: date={date}, PA={self.PA_N_UID}, PS={ps_uid}, BI_IN={len(selected_seats) if selected_seats else final_seats_needed}, naun={naun}")
        log(f"📋 사용자: {info['BI_NAME']}, 010-{info['BI_TEL2']}-{info['BI_TEL3']}")
        log(f"⏱️ [Step 2] 페이로드 구성 완료: {payload_duration:.4f}초")

        # ─────────────────────────────────────────────────────────────
        # 테스트/시뮬레이션 모드 체크
        # ─────────────────────────────────────────────────────────────
        if self.test_mode or self.dry_run:
            log(f"🧪 [테스트 모드] 실전송 생략됨 (TEST_MODE={self.test_mode}, DRY_RUN={self.dry_run})")
            total_duration = time.time() - total_start_time
            log(f"⏱️ [Total] 총 소요 시간(어종선택부터): {total_duration:.4f}초")
            return True

        # ─────────────────────────────────────────────────────────────
        # Step 2.5: 가격 검증 AJAX (브라우저 form_check → popup_price)
        # Step 1.5에서 세션에 기록된 가격을 검증하는 보조 호출
        # ─────────────────────────────────────────────────────────────
        step_start = time.time()
        log(f"📡 [Step 2.5] 가격 검증 AJAX 전송...")

        # ye_display는 Step 1.5에서 서버가 반환한 가격 문자열 사용
        # Step 1.5 실패 시 HTML에서 파싱
        if not ye_display:
            ye_per_person = 0
            price_matches = re.findall(r'([\d,]+)원', html_step1)
            if price_matches:
                try:
                    prices = [int(p.replace(',', '')) for p in price_matches if p.replace(',', '').isdigit()]
                    prices = [p for p in prices if p >= 10000]
                    if prices:
                        ye_per_person = prices[0]
                except (ValueError, IndexError):
                    pass
            bi_in_count_price = len(selected_seats) if selected_seats else final_seats_needed
            ye_total = ye_per_person * bi_in_count_price
            ye_display = f"{ye_total:,}원"

        # 부가금 파싱
        buga_total = ""
        buga_match = re.search(r'id="id_buga_total"[^>]*>([\d,]*)', html_step1)
        if buga_match:
            buga_total = buga_match.group(1)

        price_url = f"{self.BASE_URL}/action/popup.step1.price.php"
        price_data_str = f"ye={ye_display}&buga_total={buga_total}"

        try:
            session.headers.update({
                "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            })
            resp_price = session.post(price_url, data=price_data_str.encode('utf-8'), timeout=self.REQUEST_TIMEOUT)
            log(f"✅ 가격 검증 완료: ye={ye_display}, buga_total={buga_total}, 응답={resp_price.text.strip()}")
        except Exception as e:
            log(f"⚠️ 가격 검증 AJAX 실패 (무시): {e}")
        finally:
            if "X-Requested-With" in session.headers:
                del session.headers["X-Requested-With"]
            if "Content-Type" in session.headers:
                del session.headers["Content-Type"]

        log(f"⏱️ [Step 2.5] 가격 검증: {time.time() - step_start:.4f}초")

        # ─────────────────────────────────────────────────────────────
        # Step 3: 첫 번째 예약 전송 (popup.step1.action.php)
        # ─────────────────────────────────────────────────────────────
        step_start = time.time()
        url_step1_action = f"{self.BASE_URL}/action/popup.step1.action.php"
        log(f"📡 [Step 3] POST 첫 번째 예약 전송...")
        log(f"🔗 URL: {url_step1_action}")

        session.headers.update({"Referer": url_2})

        try:
            res1 = session.post(url_step1_action, data=payload, timeout=self.REQUEST_TIMEOUT)
            http_duration = time.time() - step_start

            log(f"✅ 응답 수신: Status={res1.status_code}, Size={len(res1.text)}bytes")
            log(f"⏱️ [Step 3] 첫 번째 전송 완료: {http_duration:.4f}초")

            if res1.status_code != 200:
                log(f"❌ [Step 3] 전송 실패! Status: {res1.status_code}")
                if res1.status_code in [502, 503]:
                    return "RETRY_FULL"
                return False

            response_text = res1.text.strip()
            log(f"📄 응답 내용: {response_text[:200]}..." if len(response_text) > 200 else f"📄 응답 내용: {response_text}")

            # 에러 체크
            if "정상적으로 예약해 주십시오" in response_text:
                log("⚠️ [Step 3] 오류! 처음부터 다시 시도 필요")
                return "RETRY_FULL"
            if any(kw in response_text for kw in ["이미", "불가능", "선점", "마감"]):
                log("⚠️ [Step 3] 좌석 선점 실패!")
                return "RETRY_FULL"

        except requests.exceptions.Timeout:
            log(f"❌ [Step 3] 타임아웃!")
            return "RETRY_FULL"
        except requests.exceptions.ConnectionError:
            log(f"❌ [Step 3] 연결 실패!")
            return "RETRY_FULL"
        except Exception as e:
            log(f"❌ [Step 3] 오류: {e}")
            return False

        # ─────────────────────────────────────────────────────────────
        # Step 4: 두 번째 페이지 로드 (popup.step2.php)
        # ─────────────────────────────────────────────────────────────
        step_start = time.time()
        url_step2 = f"{self.BASE_URL}/popup.step2.php"
        log(f"📡 [Step 4] 두 번째 페이지 로드...")
        log(f"🔗 URL: {url_step2}")

        try:
            session.headers.update({"Referer": url_step1_action})
            res2_page = session.get(url_step2, timeout=self.REQUEST_TIMEOUT)

            log(f"✅ Step 2 페이지 로드: Status={res2_page.status_code}, Size={len(res2_page.text)}bytes")

            step2_html = res2_page.text
            if "STEP 02" in step2_html or "예약확인" in step2_html or "예약2단계" in step2_html:
                log(f"✅ Step 2 페이지 확인됨! (예약확인 단계)")
            elif "STEP 01" in step2_html or "예약1단계" in step2_html:
                log(f"⚠️ Step 1 페이지가 표시됨! 세션 데이터 누락?")

            if res2_page.status_code != 200:
                log(f"⚠️ [Step 4] 페이지 로드 실패! Status: {res2_page.status_code}")
                return "RETRY_FULL"

            # Step 2 submit 전송
            url_step2_action = f"{self.BASE_URL}/action/popup.step2.action.php"
            log(f"📡 [Step 4] POST 두 번째 예약 전송...")
            log(f"🔗 URL: {url_step2_action}")

            # Step 2 페이로드: <form> 안의 필드만 파싱 (페이지 전체 X)
            soup_step2 = BeautifulSoup(res2_page.text, "html.parser")
            payload_step2 = []

            # step2.action을 타겟으로 하는 form 찾기
            target_form = None
            for form in soup_step2.find_all("form"):
                form_action = form.get("action", "")
                if "step2.action" in form_action or "step2" in form_action:
                    target_form = form
                    break
            if not target_form:
                # form을 못 찾으면 첫 번째 form 사용
                target_form = soup_step2.find("form")

            if target_form:
                # form 내부의 input만 파싱
                for inp in target_form.find_all("input"):
                    name = inp.get("name")
                    if not name:
                        continue
                    inp_type = inp.get("type", "text").lower()
                    if inp_type in ("submit", "button", "image", "reset"):
                        continue
                    payload_step2.append((name, inp.get("value", "")))

                # form 내부의 textarea 파싱
                for textarea in target_form.find_all("textarea"):
                    name = textarea.get("name")
                    if name:
                        payload_step2.append((name, textarea.get_text() or ""))

            if not any(p[0] == "action" for p in payload_step2):
                payload_step2.append(("action", "update"))

            log(f"📋 [Step 4] 페이로드 항목 수: {len(payload_step2)}개")
            for k, v in payload_step2:
                log(f"  📌 {k}={v}")

            session.headers.update({"Referer": url_step2})
            res2 = session.post(url_step2_action, data=payload_step2, timeout=self.REQUEST_TIMEOUT)
            http_duration = time.time() - step_start

            log(f"✅ 응답 수신: Status={res2.status_code}, Size={len(res2.text)}bytes")
            log(f"⏱️ [Step 4] 두 번째 전송 완료: {http_duration:.4f}초")

            if res2.status_code != 200:
                log(f"⚠️ [Step 4] 전송 실패! Status: {res2.status_code}")
                return "RETRY_FULL"

            response_text2 = res2.text.strip()
            log(f"📄 응답 내용: {response_text2[:200]}..." if len(response_text2) > 200 else f"📄 응답 내용: {response_text2}")

            # 에러 체크
            if "예약할 수 없습니다" in response_text2 or "관리자에게 문의" in response_text2:
                log("🛑 [Step 4] 예약 불가 에러 - 봇 정지")
                return True  # 봇 정지 (성공 처리로 루프 탈출)
            if "정상적으로 예약해 주십시오" in response_text2:
                log("⚠️ [Step 4] 오류! 처음부터 다시 시도 필요")
                return "RETRY_FULL"

        except requests.exceptions.Timeout:
            log(f"❌ [Step 4] 타임아웃!")
            return "RETRY_FULL"
        except requests.exceptions.ConnectionError:
            log(f"❌ [Step 4] 연결 실패!")
            return "RETRY_FULL"
        except Exception as e:
            log(f"❌ [Step 4] 오류: {e}")
            return False

        # ─────────────────────────────────────────────────────────────
        # Step 5: 최종 성공 확인 (popup.step3.php)
        # ─────────────────────────────────────────────────────────────
        step_start = time.time()
        url_step3 = f"{self.BASE_URL}/popup.step3.php"
        log(f"📡 [Step 5] 최종 성공 확인 중...")
        log(f"🔗 URL: {url_step3}")

        try:
            session.headers.update({"Referer": url_step2_action})
            res3 = session.get(url_step3, timeout=self.REQUEST_TIMEOUT)

            log(f"✅ Step 3 페이지 응답: Status={res3.status_code}, Size={len(res3.text)}bytes")

            response_text3 = res3.text

            success_indicators = ["완료", "성공", "예약이 완료", "신청이 완료"]
            if any(ind in response_text3 for ind in success_indicators):
                log("🎉 [결과] 예약 성공!")
                total_duration = time.time() - total_start_time
                log(f"⏱️ [Total] 총 소요 시간(어종선택부터): {total_duration:.4f}초")
                return True
            else:
                # Step 2 응답이 성공적이었다면 성공으로 간주
                if "step3" in response_text2.lower() or res2.status_code == 200:
                    log("🎉 [결과] 예약 성공으로 간주 (Step 2 성공 기반)")
                    total_duration = time.time() - total_start_time
                    log(f"⏱️ [Total] 총 소요 시간(어종선택부터): {total_duration:.4f}초")
                    return True

            log("⚠️ [Step 5] 성공 확인 실패")
            return False

        except Exception as e:
            log(f"⚠️ [Step 5] 확인 중 오류: {e}")
            # Step 2까지 성공했으면 성공으로 간주
            log("🎉 [결과] Step 2 성공 기반으로 예약 성공 간주")
            total_duration = time.time() - total_start_time
            log(f"⏱️ [Total] 총 소요 시간(어종선택부터): {total_duration:.4f}초")
            return True

    # =========================================================================
    # 로그 파일 시스템
    # =========================================================================
    def _setup_log_file(self):
        """로그 파일 초기화 (Selenium 봇과 동일한 양식)"""
        global _log_file_path
        try:
            log_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'Log'))
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)

            now = datetime.now()
            time_str = now.strftime("%Y_%m월%d일_%H시%M분%S초")

            p_provider = self._config_provider or self.PROVIDER_NAME

            t_date = self._config_target_date
            if len(t_date) == 8 and t_date.isdigit():
                t_date_fmt = f"{t_date[:4]}_{t_date[4:6]}_{t_date[6:]}"
            else:
                t_date_fmt = t_date

            # 시뮬레이션 모드일 때만 파일명에 [TestMode] 접두사
            mode_prefix = "[TestMode]_" if self.dry_run else ""

            log_file = os.path.join(log_dir, f"{mode_prefix}{time_str}_더피싱_{p_provider}_{t_date_fmt}_.txt")
            _log_file_path = log_file

            pretty_timestamp = now.strftime("%Y-%m-%d_%H:%M:%S")
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"=== Bot Log Started: {pretty_timestamp} ===\n")

                p_port = self._config_port or 'Unknown'
                p_date = self._config_target_date
                if len(p_date) == 8 and p_date.isdigit():
                    p_date = f"{p_date[:4]}-{p_date[4:6]}-{p_date[6:]}"

                p_time = self.target_time
                p_name = self._config_user_name
                p_phone = self._config_user_phone

                f.write(f"항구: {p_port}\n")
                f.write(f"선사: {p_provider}\n")
                f.write(f"예약날짜: {p_date}\n")
                f.write(f"예약시간: {p_time}\n")
                f.write(f"예약자: {p_name}\n")
                f.write(f"전화번호: {p_phone}\n")
                f.write("-" * 30 + "\n\n")

            log(f"📝 로그 파일 생성: {os.path.basename(log_file)}")
        except Exception as e:
            print(f"Failed to setup log file: {e}")

    # =========================================================================
    # Main Run Loop
    # =========================================================================
    def run(self):
        """메인 실행"""
        self._setup_log_file()
        log(f"🚢 {self.PROVIDER_NAME} API 봇 시작")
        log(f"📋 예약 타입: {self.reservation_type} ({'popu2' if self.reservation_type == '2step' else 'popup'})")
        log(f"🪑 좌석 선택: {'활성화' if self.HAS_SEAT_SELECTION else '비활성화'}")
        if self.HAS_SEAT_SELECTION and self.SEAT_PRIORITY:
            log(f"🪑 좌석 우선순위: {self.SEAT_PRIORITY[:5]}...")

        # Test Mode면 시간 대기 건너뛰기
        if not self.test_mode_skip_wait:
            self.wait_until_target_time(self.target_time)
        else:
            log("⏩ [Test Mode] 시간 대기를 건너뜁니다!")

        for date, jobs in self.reservations_plan.items():
            if not jobs:
                continue

            # ═══════════════════════════════════════════════════════════════
            # 메인 예약 루프 (Selenium 스타일 무한 재시도)
            # ═══════════════════════════════════════════════════════════════
            MAX_TOTAL_RETRIES = 100  # 전체 최대 재시도 횟수
            total_attempts = 0

            while total_attempts < MAX_TOTAL_RETRIES:
                total_attempts += 1
                session = self.build_session()

                # ─────────────────────────────────────────────────────────
                # Phase 1: 예약 오픈 대기 (서버 안정화 대기)
                # ─────────────────────────────────────────────────────────
                open_retry = 0
                MAX_OPEN_RETRIES = 10000  # 약 30~40분 재시도 (10000 * 0.2초)

                # 예약 타입에 따른 URL 설정
                step1_file = "popu2.step1.php" if self.reservation_type == "2step" else "popup.step1.php"

                while open_retry < MAX_OPEN_RETRIES:
                    open_retry += 1
                    try:
                        url_check = f"{self.BASE_URL}/{step1_file}?date={date}&PA_N_UID={self.PA_N_UID}"
                        session.headers.update({"Referer": f"{self.BASE_URL}/{step1_file}"})
                        r = session.get(url_check, timeout=3)

                        # ✅ 성공: 예약 페이지 오픈 감지
                        if "PS_N_UID" in r.text or "STEP 01" in r.text or "예약1단계" in r.text:
                            break

                        # ⚠️ 에러: 502 Bad Gateway
                        if r.status_code == 502:
                            log(f"⚠️ [502] 서버 오류. 재시도... ({open_retry}/{MAX_OPEN_RETRIES})")
                            time.sleep(0.1)
                            continue

                        # ⚠️ 에러: 503 Service Unavailable
                        if r.status_code == 503:
                            log(f"⚠️ [503] 서비스 불가. 재시도... ({open_retry}/{MAX_OPEN_RETRIES})")
                            time.sleep(0.1)
                            continue

                        # ⚠️ 에러: 리다이렉트 에러
                        if "waitingrequest" in r.url or "ERR_TOO_MANY_REDIRECTS" in r.text:
                            log(f"⚠️ 리다이렉트 에러! 세션 재생성... ({open_retry}/{MAX_OPEN_RETRIES})")
                            session = self.build_session()  # 세션 재생성
                            time.sleep(0.1)
                            continue

                        # ⚠️ 에러: 페이지 에러 (없는/권한/잘못)
                        error_keywords = ['없는', '권한', '잘못', '예약할 수 없', '존재하지']
                        matched_errors = [err for err in error_keywords if err in r.text]
                        if matched_errors:
                            # 응답 내용 일부 추출 (100자)
                            error_preview = r.text.strip()[:100].replace('\n', ' ')
                            log(f"⚠️ 에러 페이지 감지 [{matched_errors[0]}]: {error_preview}... ({open_retry}/{MAX_OPEN_RETRIES})")
                            time.sleep(0.1)
                            continue

                        # 아직 오픈 안됨
                        log(f"⏳ 오픈 대기 중... ({open_retry})")

                    except requests.exceptions.Timeout:
                        log(f"⚠️ 타임아웃! 재시도... ({open_retry}/{MAX_OPEN_RETRIES})")
                    except requests.exceptions.ConnectionError:
                        log(f"⚠️ 연결 실패! 세션 재생성... ({open_retry}/{MAX_OPEN_RETRIES})")
                        session = self.build_session()
                    except Exception as e:
                        log(f"⚠️ 예외: {e} ({open_retry}/{MAX_OPEN_RETRIES})")

                    time.sleep(0.1)

                if open_retry >= MAX_OPEN_RETRIES:
                    log("❌ 오픈 대기 최대 재시도 초과!")
                    continue

                # ─────────────────────────────────────────────────────────
                # Phase 2: 예약 실행 (재시도 포함)
                # ─────────────────────────────────────────────────────────
                for job in jobs:
                    MAX_RESERVATION_RETRIES = 3

                    for res_attempt in range(MAX_RESERVATION_RETRIES):
                        try:
                            log(f"✨ 예약 오픈 감지! (예약 시도 {res_attempt + 1}/{MAX_RESERVATION_RETRIES})")
                            # 예약 타입에 따라 다른 메서드 호출
                            if self.reservation_type == "3step":
                                result = self.do_reservation_3step(session, date, job)
                            else:
                                result = self.do_reservation(session, date, job)

                            if result == True:
                                # 성공!
                                log("🎉 예약 성공! 봇 실행 완료!")
                                return  # 프로그램 종료

                            elif result == "SOLD_OUT":
                                # 만석 (잔여석 0)
                                log("🛑 만석으로 봇 종료. 브라우저는 대기 상태 유지.")
                                return  # 프로그램 종료 (재시도 안함)

                            elif result == "RETRY_FULL":
                                # "정상적으로 예약해 주십시오" - 처음부터 재시도
                                log("🔄 전체 플로우 재시도...")
                                session = self.build_session()
                                time.sleep(0.1)
                                break  # 내부 루프 탈출, 외부 루프에서 재시도

                            elif result == "RETRY_IMMEDIATE":
                                # 좌석 선점 실패 - 즉시 재시도
                                log("🔄 즉시 재시도...")
                                session = self.build_session()
                                continue

                            else:
                                # 일반 실패
                                log(f"⚠️ 예약 실패. 재시도 중... ({res_attempt + 1}/{MAX_RESERVATION_RETRIES})")
                                time.sleep(0.1)
                                continue

                        except requests.exceptions.Timeout:
                            log(f"⚠️ 타임아웃! 재시도... ({res_attempt + 1}/{MAX_RESERVATION_RETRIES})")
                            session = self.build_session()
                        except requests.exceptions.ConnectionError:
                            log(f"⚠️ 연결 실패! 세션 재생성... ({res_attempt + 1}/{MAX_RESERVATION_RETRIES})")
                            session = self.build_session()
                        except Exception as e:
                            log(f"⚠️ 예외: {e} ({res_attempt + 1}/{MAX_RESERVATION_RETRIES})")

                        time.sleep(0.05)
                    else:
                        # 예약 재시도 모두 실패
                        log("❌ 예약 재시도 최대 횟수 초과. 전체 재시도...")
                        continue

                    # break로 빠져나온 경우 (RETRY_FULL)
                    break
                else:
                    # 모든 job 처리 완료 (성공 없이)
                    continue

                # 외부 루프 계속 (RETRY_FULL로 인한 재시도)

            log(f"❌ 전체 재시도 최대 횟수({MAX_TOTAL_RETRIES}) 초과!")
