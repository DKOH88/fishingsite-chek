# -*- coding: utf-8 -*-
"""
선상24 API 봇 베이스 클래스
- 공통 예약 로직 (세션, 페이로드, 재시도 등)
- 개별 봇은 이 클래스를 상속받아 설정만 정의
"""
import time
import requests
import sys
import json
import os
import re
import io
import argparse
from datetime import datetime, timedelta
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Windows 콘솔 UTF-8 인코딩 설정
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)


class SunSang24APIBot:
    """선상24 API 봇 베이스 클래스"""

    # ═══════════════════════════════════════════════════════════════
    # 서브클래스에서 오버라이드할 설정
    # ═══════════════════════════════════════════════════════════════
    BASE_URL = ""           # 예: "https://bigboss24.sunsang24.com"
    SUBDOMAIN = ""          # 예: "bigboss24"
    PROVIDER_NAME = ""      # 예: "빅보스호"
    ID_MAPPING = {}         # 날짜별 스케줄 ID 매핑
    HAS_SEAT_SELECTION = False  # 좌석 선택 여부
    SEAT_PRIORITY = []      # 좌석 우선순위 (좌석 선택 선사용)

    # 네트워크 설정
    REQUEST_TIMEOUT = (5, 10)
    MAX_TOTAL_RETRIES = 5000
    MAX_RESERVATION_RETRIES = 5

    def __init__(self):
        self.target_time = "00:00:00"
        self.test_mode = False
        self.dry_run = False
        self.test_mode_skip_wait = False
        self.early_monitor = False
        self.reservations_plan = {}
        self.timer_start = None  # 타이머 시작 시간
        self._log_file_path = None  # 로그 파일 경로

        # 로그용 설정 저장
        self._config_port = ''
        self._config_provider = ''
        self._config_target_date = ''
        self._config_user_name = ''
        self._config_user_phone = ''

    def _ts(self):
        """현재 시간 타임스탬프 반환"""
        return datetime.now().strftime("%H:%M:%S.%f")[:-4]

    def _log(self, message):
        """타임스탬프 포함 로그 출력 + 파일 기록"""
        timestamp = self._ts()
        formatted_msg = f"[{timestamp}] {message}"
        print(formatted_msg, flush=True)

        if self._log_file_path:
            try:
                with open(self._log_file_path, "a", encoding="utf-8") as f:
                    f.write(formatted_msg + "\n")
            except Exception:
                pass

    # ═══════════════════════════════════════════════════════════════
    # Config Loader
    # ═══════════════════════════════════════════════════════════════
    def load_config(self):
        """설정 파일 로드"""
        parser = argparse.ArgumentParser()
        parser.add_argument("--config", required=False)
        args, _ = parser.parse_known_args()

        config_path = args.config if args.config else (sys.argv[1] if len(sys.argv) > 1 else None)

        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                self._log(f"📂 [설정로드] {config_path}")

                self.target_time = config.get('target_time', self.target_time)

                if config.get('test_mode', False):
                    self.test_mode_skip_wait = True
                    self._log(f"🚀 [Test Mode] 시간 대기 없이 즉시 실행합니다!")

                if config.get('simulation_mode', False):
                    self.test_mode = True
                    self.dry_run = True
                    self._log(f"🧪 [Simulation Mode] 실전송 생략 모드 활성화")

                # early_monitor: 조기오픈 감시 (5분전부터 10초마다 HTTP로 오픈 여부 확인)
                if config.get('early_monitor', False):
                    self.early_monitor = True
                    self._log(f"🔍 [조기오픈 감시] 활성화됨")

                target_date = config.get('target_date', '')
                u_name = config.get('user_name', '')
                u_phone = config.get('user_phone', '')
                seats_n = int(config.get('person_count', 1))

                # 로그용 설정 저장
                self._config_port = config.get('port', '')
                self._config_provider = config.get('provider', self.PROVIDER_NAME)
                self._config_target_date = target_date
                self._config_user_name = u_name
                self._config_user_phone = u_phone

                if target_date and u_name:
                    # 날짜 포맷팅 (20260501 -> 2026년05월01일)
                    formatted_date = f"{target_date[:4]}년{target_date[4:6]}월{target_date[6:]}일"
                    self.reservations_plan = {
                        target_date: [{
                            "seats": seats_n,
                            "person_info": {"name": u_name, "phone": u_phone}
                        }]
                    }
                    self._log(f"📅 [설정적용] 날짜: {formatted_date}, 인원: {seats_n}명, 이름: {u_name}")

            except Exception as e:
                self._log(f"❌ 설정 로드 실패: {e}")
        else:
            self._log(f"⚠️ 설정 파일이 존재하지 않습니다.")

    # ═══════════════════════════════════════════════════════════════
    # Core Methods
    # ═══════════════════════════════════════════════════════════════
    def get_schedule_id(self, target_date):
        """날짜에서 스케줄 ID 계산"""
        d_target = datetime.strptime(target_date, "%Y%m%d")
        key = (d_target.month, d_target.day)

        if key in self.ID_MAPPING:
            return self.ID_MAPPING[key]

        self._log(f"⚠️ [ID 조회] {d_target.month}월 {d_target.day}일의 ID 매핑이 없습니다. (동적 조회 대상)")
        return None

    def lookup_schedule_id_dynamic(self, session, target_date):
        """schedule_fleet 페이지에서 대상 날짜의 data-schedule_no를 동적으로 추출

        Args:
            session: requests.Session
            target_date: YYYYMMDD 형식 문자열

        Returns:
            int: schedule_id (없으면 None)
        """
        year_month = target_date[:6]  # YYYYMM
        # 대상 날짜를 d{YYYY-MM-DD} 형식으로 변환 (테이블 ID 매칭용)
        # HTML 구조: <table id="d2026-11-25"> (하이픈 포함)
        target_table_id = f"d{target_date[:4]}-{target_date[4:6]}-{target_date[6:]}"  # d2026-09-01

        url = f"{self.BASE_URL}/ship/schedule_fleet/{year_month}"

        try:
            r = session.get(url, timeout=10)
            if r.status_code != 200:
                return None

            html = r.text

            # data-schedule_no 속성을 가진 요소들 추출
            # 패턴: data-schedule_no="1694158" 또는 data-schedule_no='1694158'
            schedule_pattern = re.compile(
                r'data-schedule_no=["\'](\d+)["\']',
                re.IGNORECASE
            )

            # 날짜별 테이블 블록 분리: <table id="d20260901" ...> ... </table>
            # 각 날짜 블록에서 schedule_no + 선사명 추출
            table_pattern = re.compile(
                r'<table[^>]*id=["\'](' + re.escape(target_table_id) + r')["\'][^>]*>(.*?)</table>',
                re.DOTALL | re.IGNORECASE
            )

            table_match = table_pattern.search(html)
            if not table_match:
                return None

            table_html = table_match.group(2)

            # 테이블 내에서 data-schedule_no 찾기
            schedule_matches = schedule_pattern.findall(table_html)
            if not schedule_matches:
                return None

            # 선사가 1개면 바로 반환
            if len(schedule_matches) == 1:
                return int(schedule_matches[0])

            # 여러 선사가 있으면 PROVIDER_NAME으로 필터링
            # <tr> 단위로 분리하여 선사명 + schedule_no 매칭
            row_pattern = re.compile(r'<tr[^>]*>(.*?)</tr>', re.DOTALL | re.IGNORECASE)
            for row_match in row_pattern.finditer(table_html):
                row_html = row_match.group(1)

                # 이 행에 data-schedule_no가 있는지 확인
                sno_match = schedule_pattern.search(row_html)
                if not sno_match:
                    continue

                # 첫 번째 <td>에서 선사명 추출
                td_pattern = re.compile(r'<td[^>]*>(.*?)</td>', re.DOTALL | re.IGNORECASE)
                td_match = td_pattern.search(row_html)
                if td_match:
                    # HTML 태그 제거 후 선사명 추출
                    ship_name = re.sub(r'<[^>]+>', '', td_match.group(1)).strip()
                    ship_name = ship_name.split()[0] if ship_name else ""

                    if self.PROVIDER_NAME and self.PROVIDER_NAME in ship_name:
                        return int(sno_match.group(1))

            # 선사명 매칭 실패 시 첫 번째 ID 반환 (fallback)
            return int(schedule_matches[0])

        except Exception:
            return None

    def check_reservation_on_fleet(self, session, reserver_name):
        """schedule_fleet 페이지에서 예약자 이름이 예약완료/입금대기에 있는지 확인

        Args:
            session: requests.Session
            reserver_name: 예약자 이름 (예: "오동균")

        Returns:
            True: 이름 발견 (예약 성공), False: 미발견, None: 확인 불가
        """
        target_date = self._config_target_date
        if not target_date or not reserver_name:
            return None

        year_month = target_date[:6]
        target_table_id = f"d{target_date[:4]}-{target_date[4:6]}-{target_date[6:]}"
        url = f"{self.BASE_URL}/ship/schedule_fleet/{year_month}"

        try:
            r = session.get(url, timeout=10)
            if r.status_code != 200:
                return None

            html = r.text

            # 해당 날짜 섹션 추출 (중첩 테이블 대응: 현재 날짜 ~ 다음 날짜 사이)
            start_pattern = re.compile(
                r'<table[^>]*id=["\']' + re.escape(target_table_id) + r'["\']',
                re.IGNORECASE
            )
            start_match = start_pattern.search(html)
            if not start_match:
                return None

            # 다음 날짜 테이블 시작점 찾기
            next_pattern = re.compile(r'<table[^>]*id=["\']d\d{4}-\d{2}-\d{2}["\']', re.IGNORECASE)
            next_match = next_pattern.search(html, start_match.end())
            section_html = html[start_match.start():next_match.start()] if next_match else html[start_match.start():]

            # 선사별 필터링 (같은 날짜에 여러 선사 가능)
            search_html = section_html
            if self.PROVIDER_NAME:
                # ship_unit 테이블 단위로 분리
                ship_blocks = re.split(r'(?=<table\s+class=["\']ship_unit)', section_html, flags=re.IGNORECASE)
                for block in ship_blocks:
                    if self.PROVIDER_NAME in block:
                        search_html = block
                        break

            # 예약대기 이전 영역만 검색 (예약완료 + 입금대기만 대상)
            waitlist_pos = search_html.find('예약대기')
            check_html = search_html[:waitlist_pos] if waitlist_pos > 0 else search_html

            # 이름 패턴 생성 (마스킹 대응: 오동균 → 오*균)
            name = reserver_name.strip()
            if len(name) >= 3:
                # "오동균" → "오.균" (오동균님, 오*균님 모두 매칭)
                name_pattern = re.escape(name[0]) + '.{1,' + str(len(name) - 2) + '}' + re.escape(name[-1]) + r'[님\s]'
            elif len(name) == 2:
                # "김철" → "김." (김철님, 김*님 모두 매칭)
                name_pattern = re.escape(name[0]) + '.' + r'님'
            else:
                name_pattern = re.escape(name) + r'님'

            if re.search(name_pattern, check_html):
                return True

            return False

        except Exception:
            return None

    def poll_schedule_id(self, session, target_date, max_retries=20000):
        """schedule_fleet 폴링으로 동적 ID 조회 (최대 ~43분)

        ID가 비공개인 선사의 경우, 오픈 시간에 ID가 공개될 때까지 반복 조회.

        Args:
            session: requests.Session
            target_date: YYYYMMDD 형식 문자열
            max_retries: 최대 재시도 횟수 (기본 4000 = ~0.35초 간격으로 ~20분)

        Returns:
            int: schedule_id (없으면 None)
        """
        d_target = datetime.strptime(target_date, "%Y%m%d")
        formatted = f"{d_target.month}월 {d_target.day}일"

        for retry in range(max_retries):
            schedule_id = self.lookup_schedule_id_dynamic(session, target_date)
            if schedule_id:
                self._log(f"✨ [동적 조회] {formatted} 스케줄 ID 발견: {schedule_id} ({retry + 1}회 시도)")
                return schedule_id
            if retry % 20 == 0:
                self._log(f"🔍 [동적 조회] {formatted} 대기 중... ({retry + 1}/{max_retries})")
            time.sleep(0.05)

        self._log(f"❌ [동적 조회] {formatted} 최대 재시도({max_retries}) 초과!")
        return None

    def build_session(self):
        """세션 빌드"""
        s = requests.Session()
        s.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Connection": "keep-alive",
            "Origin": self.BASE_URL,
        })
        retry = Retry(total=2, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        s.mount("http://", adapter)
        s.mount("https://", adapter)
        return s

    def wait_until_target_time(self):
        """목표 시간까지 대기 + 조기오픈 감시
        Returns: 조기오픈 감지 시 HTML 응답 텍스트, 아니면 None
        """
        parts = self.target_time.split(':')
        if len(parts) == 3:
            h, m, s = int(parts[0]), int(float(parts[1])), float(parts[2])
        else:
            h, m, s = 0, 0, 0

        now = datetime.now()
        target = now.replace(hour=h, minute=m, second=int(s), microsecond=int((s % 1) * 1000000))

        if datetime.now() >= target:
            self._log(f"⏰ [시간] 타겟 시간 {self.target_time} 이미 경과 - 즉시 시작!")
            return None

        self._log(f"⏰ [시간] 타겟 시간: {self.target_time}")
        self._log(f"⏰ 현재 시간: {now.strftime('%H:%M:%S')}")

        # 처음 한번 남은 시간 표시
        remaining = (target - now).total_seconds()
        mins, secs = divmod(remaining, 60)
        hours, mins = divmod(mins, 60)
        self._log(f"⏳ 남은 시간: {int(hours):02d}:{int(mins):02d}:{secs:05.2f}")

        # 조기오픈 감시 설정
        last_early_check = None

        if self.early_monitor:
            self._log(f"🔍 조기오픈 감시 활성화: 지금부터 10초마다 HTTP 확인")

        # 알림 포인트 (초 단위) - 처음 남은 시간보다 큰 알림은 이미 통과한 것으로 처리
        notified = set()
        alert_points = [600, 300, 60, 30, 10]
        for point in alert_points:
            if remaining <= point:
                notified.add(point)

        while True:
            now = datetime.now()
            if now >= target:
                self._log(f"🎯 타겟 시간 도달! 예약 시작!")
                break

            remaining = (target - now).total_seconds()

            # ── 조기오픈 감시: 봇 실행 시점부터 10초마다 HTTP로 오픈 여부 확인 ──
            if self.early_monitor:
                should_check = False
                if last_early_check is None:
                    should_check = True
                elif (now - last_early_check).total_seconds() >= 10:
                    should_check = True

                if should_check:
                    last_early_check = now
                    try:
                        first_date = next(iter(self.reservations_plan), None)
                        if first_date:
                            schedule_id = self.get_schedule_id(first_date)
                            if schedule_id:
                                url_check = f"{self.BASE_URL}/mypage/reservation_ready/{schedule_id}"
                                session = self.build_session()
                                r = session.get(url_check, timeout=5)

                                # 오픈 판별: reservation_method_bank_view가 있고 no-view가 아닌 경우
                                is_open = ("reservation_method_bank_view" in r.text and
                                           "reservation_method_bank_view no-view" not in r.text)
                                is_closed = ("배일정이 존재하지 않습니다" in r.text or
                                             "예약불가" in r.text or "마감" in r.text)

                                if is_open and not is_closed:
                                    self._log(f"🎉🎉🎉 조기 오픈 감지! 예약 페이지가 열렸습니다!")
                                    self._log(f"   (예정: {target.strftime('%H:%M:%S')}, 실제: {now.strftime('%H:%M:%S')}, {remaining:.0f}초 일찍 오픈)")
                                    return r.text  # 오픈 감지 HTML 반환 → Step 1 스킵용
                                else:
                                    self._log(f"🔍 조기오픈 체크: 아직 미오픈 (남은시간: {int(remaining)}초)")
                    except Exception as e:
                        self._log(f"⚠️ 조기오픈 체크 오류: {e}")

            # 특정 시점에만 알림 (큰 값부터 체크)
            if remaining <= 5:
                # 5초부터 카운트다운 (정수로 표시)
                print(f"\r[{self._ts()}] ⏳ {int(remaining) + 1}초", end="", flush=True)
            elif remaining <= 10 and 10 not in notified:
                self._log(f"⏳ 10초 전")
                notified.add(10)
            elif remaining <= 30 and 30 not in notified:
                self._log(f"⏳ 30초 전")
                notified.add(30)
            elif remaining <= 60 and 60 not in notified:
                self._log(f"⏳ 1분 전")
                notified.add(60)
            elif remaining <= 300 and 300 not in notified:
                self._log(f"⏳ 5분 전")
                notified.add(300)
            elif remaining <= 600 and 600 not in notified:
                self._log(f"⏳ 10분 전")
                notified.add(600)

            time.sleep(0.1)

        return None  # 정상 시간 도달 (조기오픈 아님)

    # ═══════════════════════════════════════════════════════════════
    # 좌석 선택 (좌석 선택 선사용)
    # ═══════════════════════════════════════════════════════════════
    def has_seat_selection_ui(self, html_content):
        """HTML에 좌석 선택 <input> 태그가 실제로 존재하는지 확인 (JS코드 내 문자열 제외)"""
        return bool(re.search(
            r'<input[^>]*name=["\']select_seat_nos\[\]["\'][^>]*>',
            html_content, re.IGNORECASE
        ))

    def parse_available_seats(self, html_content):
        """HTML에서 예약 가능한 좌석 번호 추출"""
        available_seats = []

        # 좌석 체크박스 패턴
        seat_pattern = re.compile(
            r'<input[^>]*name=["\']select_seat_nos\[\]["\'][^>]*value=["\'](\d+)["\'][^>]*>',
            re.IGNORECASE
        )
        seat_pattern2 = re.compile(
            r'<input[^>]*value=["\'](\d+)["\'][^>]*name=["\']select_seat_nos\[\]["\'][^>]*>',
            re.IGNORECASE
        )

        for pattern in [seat_pattern, seat_pattern2]:
            for match in pattern.finditer(html_content):
                seat_no = match.group(1)
                full_tag = match.group(0)
                if 'disabled' not in full_tag.lower() and seat_no not in available_seats:
                    available_seats.append(seat_no)

        return available_seats

    def select_best_seats(self, available_seats, count):
        """우선순위에 따라 최적 좌석 선택"""
        selected = []

        # 우선순위에 따라 선택
        for seat in self.SEAT_PRIORITY:
            if seat in available_seats and seat not in selected:
                selected.append(seat)
                if len(selected) >= count:
                    break

        # 우선순위에 없는 좌석도 필요하면 추가
        if len(selected) < count:
            for seat in available_seats:
                if seat not in selected:
                    selected.append(seat)
                    if len(selected) >= count:
                        break

        return selected

    # ═══════════════════════════════════════════════════════════════
    # 예약 실행
    # ═══════════════════════════════════════════════════════════════
    def do_reservation(self, session, schedule_id, job, initial_html=None):
        """예약 실행 (initial_html: 조기오픈 감지 시 이미 받은 HTML → Step 1 스킵)"""
        info = job["person_info"]
        seats_needed = job["seats"]

        # 전화번호 파싱
        phone = info.get("phone", "")
        p1, p2, p3 = "010", "", ""
        if "-" in phone:
            parts = phone.split("-")
            if len(parts) == 3:
                p1, p2, p3 = parts
        elif len(phone) == 11:
            p1, p2, p3 = phone[:3], phone[3:7], phone[7:]

        # 타이머 시작
        self.timer_start = time.time()
        self._log(f"✨ 예약 시도 시작 (스케줄 ID: {schedule_id}, 인원: {seats_needed}명)")
        self._log(f"👤 예약자: {info['name']} | 연락처: {p1}-{p2}-{p3}")

        # ─────────────────────────────────────────────────────────────
        # Step 1: GET 요청으로 예약 페이지 로드
        # ─────────────────────────────────────────────────────────────
        step_start = time.time()
        url = f"{self.BASE_URL}/mypage/reservation_ready/{schedule_id}"

        # 조기오픈 감지 HTML이 있으면 Step 1 GET 스킵
        if initial_html:
            self._log(f"⚡ [Step 1] 조기오픈 감지 HTML 재활용 (GET 스킵)")

            class FakeResponse:
                def __init__(self, text):
                    self.text = text
                    self.status_code = 200

            r = FakeResponse(initial_html)
            step_duration = 0
        else:
            self._log(f"📡 [Step 1] GET 요청 전송...")
            self._log(f"🔗 URL: {url}")

        try:
            if not initial_html:
                r = session.get(url, timeout=self.REQUEST_TIMEOUT)
                step_duration = time.time() - step_start
                self._log(f"✅ 응답 수신: Status={r.status_code}, Size={len(r.text)}bytes")

            if r.status_code != 200:
                self._log(f"❌ [오류] 페이지 로드 실패! Status: {r.status_code}")
                return False

            # 예약 페이지 오픈 확인
            # 미오픈: '배일정이 존재하지 않습니다' (alert 메시지)
            if "배일정이 존재하지 않습니다" in r.text:
                self._log(f"⏳ [대기] 서버 미오픈 (배일정 없음) - 0.1초 후 재시도...")
                time.sleep(0.1)
                return "RETRY_IMMEDIATE"

            # 미오픈: 'reservation_method_bank_view no-view' (환불계좌 숨김 상태)
            if "reservation_method_bank_view no-view" in r.text:
                self._log(f"⏳ [대기] 서버 미오픈 (예약폼 숨김) - 0.1초 후 재시도...")
                time.sleep(0.1)
                return "RETRY_IMMEDIATE"

            if "예약불가" in r.text or "마감" in r.text:
                self._log(f"⚠️ [오류] 예약 불가 상태 - 0.1초 후 재시도...")
                time.sleep(0.1)
                return "RETRY_IMMEDIATE"

            # 오픈됨: 'reservation_method_bank_view ' (no-view 없음)
            if "reservation_method_bank_view" in r.text and "reservation_method_bank_view no-view" not in r.text:
                # 잔여석 계산: 좌석 UI가 있으면 체크박스 수, 없으면 remain_embarkation_num
                if self.has_seat_selection_ui(r.text):
                    available_seats = self.parse_available_seats(r.text)
                    remaining_seats = len(available_seats)
                    seat_offset = getattr(self, 'SEAT_OFFSET', 0)
                    if seat_offset:
                        remaining_seats = max(0, remaining_seats - seat_offset)
                else:
                    remain_match = re.search(r'"remain_embarkation_num"\s*:\s*(\d+)', r.text)
                    remaining_seats = int(remain_match.group(1)) if remain_match else -1

                self._log(f"⏱️ [Step 1] 페이지 로드 완료: {step_duration:.4f}초")
                if remaining_seats >= 0:
                    self._log(f"🪑 잔여석: {remaining_seats}석")
                else:
                    self._log(f"🪑 잔여석: 확인 불가")
            else:
                self._log(f"⚠️ [오류] 예약 페이지가 아닙니다 - 0.1초 후 재시도...")
                time.sleep(0.1)
                return "RETRY_IMMEDIATE"
            page_html = r.text

        except requests.exceptions.Timeout:
            self._log(f"❌ [오류] 타임아웃!")
            return "RETRY_IMMEDIATE"
        except Exception as e:
            self._log(f"❌ [오류] {e}")
            return "RETRY_FULL"

        # ─────────────────────────────────────────────────────────────
        # Step 1.5: 좌석 선택 (HTML에서 좌석 UI 자동 감지)
        # ─────────────────────────────────────────────────────────────
        selected_seats = []
        page_has_seats = self.has_seat_selection_ui(page_html)

        if page_has_seats:
            step_start = time.time()
            self._log(f"🪑 [Step 1.5] 좌석 선택 UI 감지 → 좌석 선택 중...")

            seat_priority = getattr(self, 'SEAT_PRIORITY', [])
            if seat_priority:
                self._log(f"🪑 우선선택 좌석: {seat_priority}")

            available_seats = self.parse_available_seats(page_html)
            self._log(f"🪑 예약 가능 좌석: {available_seats}")

            if not available_seats:
                self._log(f"❌ [오류] 예약 가능한 좌석이 없습니다!")
                return "RETRY_IMMEDIATE"

            # SEAT_OFFSET 적용된 실제 가용 좌석 수 계산
            seat_offset = getattr(self, 'SEAT_OFFSET', 0)
            actual_available = max(0, len(available_seats) - seat_offset)

            if actual_available == 0:
                self._log(f"❌ [오류] 예약 가능한 좌석이 없습니다! (선장석 제외 후)")
                return "RETRY_IMMEDIATE"

            # 요청 인원과 실제 가용 좌석 중 작은 값으로 선택
            seats_to_select = min(seats_needed, actual_available)

            selected_seats = self.select_best_seats(available_seats, seats_to_select)
            self._log(f"✅ 선택된 좌석: {selected_seats}")

            # 가용 좌석이 요청보다 적으면 가용 좌석 수로 조정
            if seats_to_select < seats_needed:
                self._log(f"⚠️ [조정] 요청 {seats_needed}명 → 가용 {seats_to_select}명으로 변경")
                seats_needed = seats_to_select

            seat_duration = time.time() - step_start
            self._log(f"⏱️ [Step 1.5] 좌석 선택 완료: {seat_duration:.4f}초")
        else:
            self._log(f"⏩ [Step 1.5] 좌석 선택 UI 없음 → 건너뜀")

        # ─────────────────────────────────────────────────────────────
        # Step 2: 페이로드 구성
        # ─────────────────────────────────────────────────────────────
        step_start = time.time()
        self._log(f"📝 [Step 2] 예약 페이로드 구성 중...")

        payload = [
            ("ship_schedule_no", str(schedule_id)),
            ("petc_data", '{"mode":"p"}'),
            ("person_count", str(seats_needed)),
            ("coupon_no", "0"),
            ("phone", ""),
            ("price_option", ""),
        ]

        # 좌석 정보 추가 (좌석 선택 UI 감지된 경우)
        if selected_seats:
            for seat in selected_seats:
                payload.append(("select_seat_nos[]", seat))

        payload.extend([
            ("name", info["name"]),
            ("deposit_name", ""),
            ("phone1", p1),
            ("phone2", p2),
            ("phone3", p3),
            ("ready_cancel_bank_code_no", ""),
            ("ready_cancel_bank_owner", ""),
            ("ready_cancel_bank_account", ""),
            ("memo", ""),
            ("all_check", "on"),
            ("agree_rule[]", "on"),
            ("agree_rule[]", "on"),
            ("agree_rule[]", "on"),
            ("pay_method", ""),
            ("reservation_method", "bank"),
        ])

        payload_duration = time.time() - step_start
        self._log(f"📋 페이로드 항목 수: {len(payload)}개")
        self._log(f"📋 주요 데이터: schedule_id={schedule_id}, person_count={seats_needed}")
        self._log(f"📋 사용자: {info['name']}, {p1}-{p2}-{p3}")
        self._log(f"⏱️ [Step 2] 페이로드 구성 완료: {payload_duration:.4f}초")

        # ─────────────────────────────────────────────────────────────
        # Step 3: 시뮬레이션 모드 체크
        # ─────────────────────────────────────────────────────────────
        if self.test_mode or self.dry_run:
            total_time = time.time() - self.timer_start if self.timer_start else 0
            self._log(f"🧪 [테스트 모드] 실전송 생략됨 (TEST_MODE=True, DRY_RUN=True)")
            self._log(f"⏱️ [Total] 총 소요 시간: {total_time:.4f}초")
            self._log(f"🎉 시뮬레이션 완료!")
            return True

        # ─────────────────────────────────────────────────────────────
        # Step 4: POST 예약 전송
        # ─────────────────────────────────────────────────────────────
        step_start = time.time()
        reservation_url = f"{self.BASE_URL}/mypage/reservation_end"
        self._log(f"📡 [Step 3] POST 예약 전송 (AJAX)...")
        self._log(f"🔗 URL: {reservation_url}")

        session.headers.update({
            "Referer": url,
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json, text/javascript, */*; q=0.01",
        })

        try:
            res = session.post(reservation_url, data=payload, timeout=self.REQUEST_TIMEOUT)
            http_duration = time.time() - step_start
            total_time = time.time() - self.timer_start if self.timer_start else 0

            self._log(f"✅ 응답 수신: Status={res.status_code}, Size={len(res.text)}bytes")
            self._log(f"⏱️ [Step 3] POST 전송 완료: {http_duration:.4f}초")

            if res.status_code == 200:
                try:
                    result = res.json()
                    self._log(f"📦 [DEBUG] 응답: {result}")

                    # null 응답 처리 (서버가 "null" 반환 시)
                    if result is None:
                        self._log(f"⚠️ [경고] 서버 응답이 null (4bytes) → 예약 확인 중...")
                        fleet_check = self.check_reservation_on_fleet(session, info['name'])
                        if fleet_check == True:
                            self._log(f"⏱️ [Total] 총 소요 시간: {total_time:.4f}초")
                            self._log(f"🎉 ★★★ 예약 성공! (schedule_fleet 확인) ★★★")
                            return True
                        elif fleet_check == False:
                            self._log(f"❌ 예약 미확인 → 재시도")
                        else:
                            self._log(f"⚠️ 확인 불가 → 재시도")
                        return "RETRY_IMMEDIATE"

                    reservation_no = result.get("reservation_no")
                    if reservation_no:
                        self._log(f"⏱️ [Total] 총 소요 시간: {total_time:.4f}초")
                        self._log(f"🎉 ★★★ 예약 성공! ★★★")
                        self._log(f"🎫 예약번호: {reservation_no}")
                        return True

                    response_code = result.get("code")
                    if response_code == 200:
                        self._log(f"⏱️ [Total] 총 소요 시간: {total_time:.4f}초")
                        self._log(f"🎉 ★★★ 예약 성공! ★★★")
                        return True

                    response_message = result.get("message", "")
                    if response_code:
                        error_msg = response_message.replace('\n', ' | ')
                        self._log(f"❌ [결과] 예약 실패 - 코드: {response_code}")
                        self._log(f"❌ 에러: {error_msg}")

                        if "마감" in response_message or "만석" in response_message:
                            return "RETRY_IMMEDIATE"
                        if "이미" in response_message and "예약" in response_message:
                            return False
                        return "RETRY_IMMEDIATE"

                    self._log(f"⚠️ [경고] 예상치 못한 응답 형식: {result}")
                    return "RETRY_IMMEDIATE"

                except json.JSONDecodeError:
                    self._log(f"⚠️ [경고] JSON 파싱 실패")
                    if "reservation_detail" in res.url:
                        self._log(f"⏱️ [Total] 총 소요 시간: {total_time:.4f}초")
                        self._log(f"🎉 예약 성공! (URL 확인)")
                        return True
                    return "RETRY_IMMEDIATE"
            else:
                self._log(f"❌ [오류] 전송 실패! Status: {res.status_code}")
                # 서버 과부하 관련 에러 - 0.1초 후 재시도
                if res.status_code in [429, 500, 502, 503, 504] or (520 <= res.status_code <= 529):
                    self._log(f"🔄 [서버 과부하] 0.1초 후 재시도...")
                    time.sleep(0.1)
                    return "RETRY_IMMEDIATE"
                return False

        except requests.exceptions.Timeout:
            self._log(f"❌ [오류] 타임아웃! → 예약 확인 중...")
            fleet_check = self.check_reservation_on_fleet(session, info['name'])
            if fleet_check == True:
                total_time = time.time() - self.timer_start if self.timer_start else 0
                self._log(f"⏱️ [Total] 총 소요 시간: {total_time:.4f}초")
                self._log(f"🎉 ★★★ 예약 성공! (schedule_fleet 확인) ★★★")
                return True
            elif fleet_check == False:
                self._log(f"❌ 예약 미확인 → 재시도")
            else:
                self._log(f"⚠️ 확인 불가 → 재시도")
            return "RETRY_IMMEDIATE"
        except requests.exceptions.ConnectionError:
            self._log(f"❌ [오류] 연결 실패!")
            return "RETRY_FULL"
        except Exception as e:
            self._log(f"❌ [오류] {e}")
            return False

    # ═══════════════════════════════════════════════════════════════
    # 로그 파일 시스템
    # ═══════════════════════════════════════════════════════════════
    def _setup_log_file(self):
        """로그 파일 초기화 (Selenium 봇과 동일한 양식)"""
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

            log_file = os.path.join(log_dir, f"{mode_prefix}{time_str}_선상24_{p_provider}_{t_date_fmt}_.txt")
            self._log_file_path = log_file

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

            self._log(f"📝 로그 파일 생성: {os.path.basename(log_file)}")
        except Exception as e:
            print(f"Failed to setup log file: {e}")

    # ═══════════════════════════════════════════════════════════════
    # Main Run
    # ═══════════════════════════════════════════════════════════════
    def run(self):
        """봇 실행"""
        self.load_config()
        self._setup_log_file()

        # 봇 시작 정보 출력
        self._log(f"🚢 {self.PROVIDER_NAME} API 봇 시작")
        self._log(f"🪑 좌석 선택: 자동 감지 (HTML 기반)")

        early_open_html = None
        if not self.test_mode_skip_wait:
            early_open_html = self.wait_until_target_time()
        else:
            self._log(f"⏩ [Test Mode] 시간 대기를 건너뜁니다!")

        for date, jobs in self.reservations_plan.items():
            if not jobs:
                continue

            schedule_id = self.get_schedule_id(date)
            if schedule_id is None:
                # 동적 ID 조회 모드: schedule_fleet 페이지에서 실시간 추출
                self._log(f"🔍 [동적 조회] ID_MAPPING에 없음 → schedule_fleet 실시간 조회 시작...")
                dynamic_session = self.build_session()
                schedule_id = self.poll_schedule_id(dynamic_session, date)
                if schedule_id is None:
                    self._log(f"❌ [동적 조회] 스케줄 ID를 찾을 수 없습니다. 스킵.")
                    continue
                self._log(f"✅ [동적 조회] 스케줄 ID: {schedule_id} → 예약 진행!")

            formatted_date = f"{date[:4]}년{date[4:6]}월{date[6:]}일"
            self._log(f"📋 [예약 준비] 날짜: {formatted_date}, 스케줄 ID: {schedule_id}")

            total_attempts = 0
            while total_attempts < self.MAX_TOTAL_RETRIES:
                total_attempts += 1
                session = self.build_session()

                for job in jobs:
                    for res_attempt in range(self.MAX_RESERVATION_RETRIES):
                        try:
                            # 첫 시도에만 조기오픈 HTML 재활용
                            use_html = None
                            if early_open_html and total_attempts == 1 and res_attempt == 0:
                                use_html = early_open_html
                                early_open_html = None  # 한 번만 사용
                            self._log(f"🔄 예약 시도 #{total_attempts} ({res_attempt + 1}/{self.MAX_RESERVATION_RETRIES})")
                            result = self.do_reservation(session, schedule_id, job, initial_html=use_html)
                            use_html = None  # 이후 재시도에서는 사용하지 않음

                            if result == True:
                                self._log(f"🎉 예약 성공! 봇 실행 완료!")
                                return

                            elif result == "RETRY_FULL":
                                self._log(f"🔄 [재시도] 전체 플로우 재시도...")
                                session = self.build_session()
                                time.sleep(0.1)
                                break

                            elif result == "RETRY_IMMEDIATE":
                                self._log(f"🔄 [재시도] 즉시 재시도...")
                                continue

                            else:
                                self._log(f"⚠️ [실패] 예약 실패. 재시도 중...")
                                time.sleep(0.1)
                                continue

                        except requests.exceptions.Timeout:
                            self._log(f"❌ [타임아웃] 재시도...")
                        except requests.exceptions.ConnectionError:
                            self._log(f"❌ [연결실패] 재시도...")
                        except Exception as e:
                            self._log(f"❌ [예외] {e}")

                        time.sleep(0.05)
                    else:
                        self._log(f"❌ [실패] 예약 재시도 최대 횟수 초과.")
                        continue
                    break
                else:
                    continue

            self._log(f"❌ [실패] 전체 재시도 최대 횟수({self.MAX_TOTAL_RETRIES}) 초과!")
