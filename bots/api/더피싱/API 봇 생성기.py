# -*- coding: utf-8 -*-
"""
더피싱 API 봇 생성기 GUI
ttkbootstrap 적용 모던 UI - 기존 봇 생성기.py 스타일 호환
"""
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import messagebox, filedialog
import tkinter as tk
import re
import os
import glob
from datetime import datetime
from urllib.parse import urlparse, parse_qs
import requests

# 항구 목록 (런처 등록용) - 런처와 동일하게 유지
PORTS = ["오천항", "안흥·신진항", "영흥도", "삼길포항", "대천항",
         "마검포항", "무창포항", "영목항", "인천", "구매항",
         "남당항", "대야도", "백사장항", "여수", "녹동항",
         "평택항", "전곡항", "홍원항"]


class APIBotGeneratorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🚢 더피싱 API 봇 생성기")

        # 창 크기 및 위치
        win_width = 1100
        win_height = 1350
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - win_width) // 2
        y = (screen_height - win_height) // 2
        self.root.geometry(f"{win_width}x{win_height}+{x}+{y}")
        self.root.resizable(True, True)

        # 현재 디렉토리
        self.current_dir = os.path.dirname(os.path.abspath(__file__))

        # 선사명 입력 완료 플래그 ("호" 입력 후 0.5초 경과 시 True)
        self.provider_name_ready = False
        self.provider_name_timer = None

        self.create_widgets()
        self.load_existing_bots()

    def create_widgets(self):
        """위젯 생성"""
        self.main_frame = ttk.Frame(self.root, padding="15")
        self.main_frame.pack(fill=BOTH, expand=True)

        # ============================================================
        # 제목 + 도움말
        # ============================================================
        title_frame = ttk.Frame(self.main_frame)
        title_frame.pack(fill=X, pady=(0, 15))
        ttk.Label(title_frame, text="🚢 더피싱 API 봇 생성기", font=("맑은 고딕", 16, "bold"), bootstyle="primary").pack(side=LEFT)
        ttk.Button(title_frame, text="❓ 도움말", command=self.show_help, bootstyle="secondary-outline", width=12).pack(side=RIGHT)

        # ============================================================
        # 기존 봇 목록
        # ============================================================
        existing_frame = ttk.Labelframe(self.main_frame, text="📋 기존 API 봇 목록", padding="10", bootstyle="info")
        existing_frame.pack(fill=X, pady=(0, 10))

        list_frame = ttk.Frame(existing_frame)
        list_frame.pack(fill=X)

        self.bot_listbox = tk.Listbox(list_frame, height=4, font=("Consolas", 10), bg="#1e1e1e", fg="#d4d4d4", selectbackground="#0078d4")
        self.bot_listbox.pack(fill=X, side=LEFT, expand=True)
        self.bot_listbox.bind('<<ListboxSelect>>', self.on_bot_select)

        scrollbar = ttk.Scrollbar(list_frame, orient=VERTICAL, command=self.bot_listbox.yview, bootstyle="round")
        scrollbar.pack(side=RIGHT, fill=Y)
        self.bot_listbox.config(yscrollcommand=scrollbar.set)

        # ============================================================
        # [1] 예약 URL 입력
        # ============================================================
        url_frame = ttk.Labelframe(self.main_frame, text="[1] 예약 URL 입력 (자동 분석)", padding="10", bootstyle="danger")
        url_frame.pack(fill=X, pady=(0, 10))

        ttk.Label(url_frame, text="예약 페이지 URL:", font=("맑은 고딕", 10, "bold")).pack(anchor=W)
        self.url_entry = ttk.Entry(url_frame, width=80, font=("맑은 고딕", 10))
        self.url_entry.pack(fill=X, pady=(0, 5))

        btn_row = ttk.Frame(url_frame)
        btn_row.pack(anchor=W)
        ttk.Button(btn_row, text="🔍 URL 분석", command=self.parse_url, bootstyle="danger-outline", width=15).pack(side=LEFT, padx=(0, 10))
        ttk.Button(btn_row, text="🧪 URL 테스트", command=self.test_url, bootstyle="warning-outline", width=15).pack(side=LEFT, padx=(0, 10))
        ttk.Button(btn_row, text="🔄 리셋", command=self.reset_inputs, bootstyle="secondary-outline", width=10).pack(side=LEFT)

        # ============================================================
        # [2] 기본 정보
        # ============================================================
        info_frame = ttk.Labelframe(self.main_frame, text="[2] 기본 정보", padding="10", bootstyle="success")
        info_frame.pack(fill=X, pady=(0, 10))

        info_grid = ttk.Frame(info_frame)
        info_grid.pack(fill=X)

        # 선사명
        ttk.Label(info_grid, text="선사명 *:", font=("맑은 고딕", 9)).grid(row=0, column=0, sticky=W, pady=5)
        self.provider_name_entry = ttk.Entry(info_grid, width=20, font=("맑은 고딕", 10))
        self.provider_name_entry.grid(row=0, column=1, sticky=W, pady=5, padx=(5, 20))
        self.provider_name_entry.bind("<KeyRelease>", self.on_provider_name_change)
        self.provider_name_entry.bind("<FocusOut>", self.on_provider_name_focusout)

        # PA_N_UID
        ttk.Label(info_grid, text="PA_N_UID *:", font=("맑은 고딕", 9)).grid(row=0, column=2, sticky=W, pady=5)
        self.pa_n_uid_entry = ttk.Entry(info_grid, width=15, font=("맑은 고딕", 10))
        self.pa_n_uid_entry.grid(row=0, column=3, sticky=W, pady=5, padx=5)

        # BASE_URL
        ttk.Label(info_grid, text="BASE_URL *:", font=("맑은 고딕", 9)).grid(row=1, column=0, sticky=W, pady=5)
        self.base_url_entry = ttk.Entry(info_grid, width=70, font=("맑은 고딕", 10))
        self.base_url_entry.grid(row=1, column=1, columnspan=3, sticky=W, pady=5, padx=5)

        # 예약 단계 (STEPS) 표시
        ttk.Label(info_grid, text="예약 단계 (STEPS):", font=("맑은 고딕", 9)).grid(row=2, column=0, sticky=W, pady=5)
        step_frame = ttk.Frame(info_grid)
        step_frame.grid(row=2, column=1, columnspan=3, sticky=W, pady=5, padx=5)

        self.step2_label = ttk.Label(step_frame, text=" 2-step ", font=("맑은 고딕", 10, "bold"),
                                     background="#333333", foreground="#888888")
        self.step2_label.pack(side=LEFT, padx=(0, 5))
        self.step3_label = ttk.Label(step_frame, text=" 3-step ", font=("맑은 고딕", 10, "bold"),
                                     background="#333333", foreground="#888888")
        self.step3_label.pack(side=LEFT)

        # ============================================================
        # [3] 좌석 선택 설정
        # ============================================================
        seat_frame = ttk.Labelframe(self.main_frame, text="[3] 좌석 선택 설정", padding="10", bootstyle="warning")
        seat_frame.pack(fill=X, pady=(0, 10))

        self.has_seat_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(seat_frame, text="자리 선택 기능 있음 (HAS_SEAT_SELECTION = True)",
                       variable=self.has_seat_var, command=self.toggle_seat_options,
                       bootstyle="warning-round-toggle").pack(anchor=W)

        self.seat_priority_frame = ttk.Frame(seat_frame)
        self.seat_priority_frame.pack(fill=X, pady=(10, 0))

        ttk.Label(self.seat_priority_frame, text="좌석 우선순위 (쉼표로 구분):", font=("맑은 고딕", 9)).pack(anchor=W)
        self.seat_priority_entry = ttk.Entry(self.seat_priority_frame, width=70, font=("맑은 고딕", 10))
        self.seat_priority_entry.pack(fill=X, pady=(5, 0))
        self.seat_priority_entry.insert(0, "15, 14, 1, 8, 7, 13, 2, 9, 6, 12, 3, 10, 5, 11, 4")
        self.toggle_seat_options()

        # ============================================================
        # [4] 추가 설정
        # ============================================================
        extra_frame = ttk.Labelframe(self.main_frame, text="[4] 추가 설정 (선택사항)", padding="10", bootstyle="secondary")
        extra_frame.pack(fill=X, pady=(0, 10))

        extra_grid = ttk.Frame(extra_frame)
        extra_grid.pack(fill=X)

        # 검색 키워드 체크박스 + 입력란
        self.var_keywords_enable = tk.BooleanVar(value=False)
        ttk.Checkbutton(extra_grid, text="검색 키워드:", variable=self.var_keywords_enable,
                       command=self.toggle_keywords_entry, bootstyle="info-round-toggle").grid(row=0, column=0, sticky=W, pady=5)
        self.keywords_entry = ttk.Entry(extra_grid, width=60, font=("맑은 고딕", 10))
        self.keywords_entry.grid(row=0, column=1, sticky=W, pady=5, padx=5)
        self.keywords_entry.insert(0, "쭈갑, 쭈꾸미&갑오징어, 쭈꾸미, 갑오징어, 문어")
        self.keywords_entry.config(state="readonly")  # 읽기 전용 (텍스트는 보이지만 수정 불가)

        ttk.Label(extra_grid, text="(체크 시 커스텀 키워드 사용)", font=("맑은 고딕", 8), foreground="gray").grid(row=0, column=2, sticky=W, pady=5)

        # ============================================================
        # 코드 미리보기
        # ============================================================
        preview_frame = ttk.Labelframe(self.main_frame, text="👁️ 코드 미리보기", padding="10", bootstyle="primary")
        preview_frame.pack(fill=BOTH, expand=True, pady=(0, 10))

        self.preview_text = tk.Text(preview_frame, height=12, font=("Consolas", 10),
                                   bg="#1e1e1e", fg="#d4d4d4", insertbackground="white", wrap=tk.NONE)
        self.preview_text.pack(fill=BOTH, expand=True, side=LEFT)

        scrollbar2 = ttk.Scrollbar(preview_frame, orient=VERTICAL, command=self.preview_text.yview, bootstyle="round")
        scrollbar2.pack(side=RIGHT, fill=Y)
        self.preview_text.config(yscrollcommand=scrollbar2.set)

        # ============================================================
        # 버튼
        # ============================================================
        btn_frame = ttk.Frame(self.main_frame)
        btn_frame.pack(fill=X, pady=(0, 10))

        ttk.Button(btn_frame, text="🔄 미리보기 갱신", command=self.update_preview, bootstyle="info", width=18).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="💾 봇 파일 생성", command=self.generate_bot, bootstyle="success", width=18).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="🚀 런처 등록", command=self.register_to_launcher, bootstyle="warning", width=18).pack(side=LEFT, padx=5)
        ttk.Button(btn_frame, text="📂 폴더 열기", command=self.open_folder, bootstyle="secondary-outline", width=12).pack(side=RIGHT, padx=5)

        # 상태 표시
        self.status_var = tk.StringVar(value="URL을 입력하고 '분석' 버튼을 클릭하세요.")
        status_label = ttk.Label(self.main_frame, textvariable=self.status_var, font=("맑은 고딕", 9), foreground="gray")
        status_label.pack(anchor=W)

    def toggle_seat_options(self):
        """좌석 옵션 토글"""
        state = 'normal' if self.has_seat_var.get() else 'disabled'
        self.seat_priority_entry.configure(state=state)

    def show_help(self):
        """도움말 표시"""
        help_text = """📌 더피싱 API 봇 생성 도움말

🔗 예시 URL:
   http://www.yamujinfishing.com/_core/module/reservation_boat_v5.2_seat1/popu2.step1.php?date=20261201&PA_N_UID=3348

📝 URL 구성:
   • BASE_URL: http://도메인/_core/module/reservation_boat_버전
   • date: 예약 날짜 (YYYYMMDD 형식)
   • PA_N_UID: 선사 고유 ID

⚙️ 사용 방법:
   1. 예약 페이지 URL을 복사하여 붙여넣기
   2. 🔍 URL 분석 버튼 클릭 → 자동으로 정보 추출
   3. 선사명 입력 (예: 샤크호)
   4. 좌석 선택 여부 설정
   5. 봇 파일 생성!

💡 팁:
   • F12 → Network 탭에서 URL 확인
   • 좌석 우선순위는 쉼표로 구분
   • 기존 봇 클릭하면 정보 자동 로드"""
        messagebox.showinfo("도움말", help_text)

    def load_existing_bots(self):
        """기존 봇 목록 로드"""
        self.bot_listbox.delete(0, tk.END)

        for file in os.listdir(self.current_dir):
            if file.endswith("_API.py") and file != "base_api_bot.py":
                try:
                    with open(os.path.join(self.current_dir, file), 'r', encoding='utf-8') as f:
                        content = f.read()

                    provider = re.search(r'PROVIDER_NAME\s*=\s*["\']([^"\']+)["\']', content)
                    has_seat = "HAS_SEAT_SELECTION = True" in content

                    provider_name = provider.group(1) if provider else file.replace("_API.py", "")
                    seat_status = "✅좌석" if has_seat else "❌좌석"

                    self.bot_listbox.insert(tk.END, f"{provider_name} | {seat_status} | {file}")
                except:
                    self.bot_listbox.insert(tk.END, f"? | {file}")

    def on_bot_select(self, event):
        """기존 봇 선택 시 정보 로드"""
        selection = self.bot_listbox.curselection()
        if not selection:
            return

        item = self.bot_listbox.get(selection[0])
        filename = item.split(" | ")[-1]

        try:
            with open(os.path.join(self.current_dir, filename), 'r', encoding='utf-8') as f:
                content = f.read()

            # 정보 추출
            provider = re.search(r'PROVIDER_NAME\s*=\s*["\']([^"\']+)["\']', content)
            base_url = re.search(r'BASE_URL\s*=\s*["\']([^"\']+)["\']', content)
            pa_n_uid = re.search(r'PA_N_UID\s*=\s*["\']([^"\']+)["\']', content)
            seat_priority = re.search(r'SEAT_PRIORITY\s*=\s*\[([^\]]+)\]', content)

            # 입력 필드에 설정
            if provider:
                self.provider_name_entry.delete(0, tk.END)
                self.provider_name_entry.insert(0, provider.group(1))

            if base_url:
                self.base_url_entry.delete(0, tk.END)
                self.base_url_entry.insert(0, base_url.group(1))

            if pa_n_uid:
                self.pa_n_uid_entry.delete(0, tk.END)
                self.pa_n_uid_entry.insert(0, pa_n_uid.group(1))

            self.has_seat_var.set("HAS_SEAT_SELECTION = True" in content)
            self.toggle_seat_options()

            if seat_priority and self.has_seat_var.get():
                seats = seat_priority.group(1).replace("'", "").replace('"', "").strip()
                self.seat_priority_entry.delete(0, tk.END)
                self.seat_priority_entry.insert(0, seats)

            self.update_preview()
            self.status_var.set(f"✅ {filename} 정보 로드 완료")

        except Exception as e:
            messagebox.showerror("오류", f"봇 정보 로드 실패: {e}")

    def toggle_keywords_entry(self):
        """검색 키워드 입력란 활성화/비활성화"""
        if self.var_keywords_enable.get():
            self.keywords_entry.config(state="normal")
        else:
            self.keywords_entry.config(state="readonly")  # 읽기 전용 (텍스트는 보이지만 수정 불가)

    def on_provider_name_change(self, event=None):
        """선사명 입력 변경 감지 - '호'로 끝나면 0.5초 후 입력 완료로 간주"""
        # 기존 타이머 취소
        if self.provider_name_timer:
            self.root.after_cancel(self.provider_name_timer)
            self.provider_name_timer = None

        self.provider_name_ready = False

        # 현재 입력값 확인
        provider = self.provider_name_entry.get().strip()
        if provider.endswith("호"):
            # 0.5초 후 입력 완료로 표시
            self.provider_name_timer = self.root.after(500, self.set_provider_name_ready)

    def set_provider_name_ready(self):
        """선사명 입력 완료 상태로 설정"""
        self.provider_name_ready = True
        self.provider_name_timer = None

    def on_provider_name_focusout(self, event=None):
        """선사명 입력란에서 포커스 벗어날 때 - IME 조합 완료로 간주"""
        # 타이머 취소
        if self.provider_name_timer:
            self.root.after_cancel(self.provider_name_timer)
            self.provider_name_timer = None
        # 포커스가 벗어나면 IME 조합이 완료된 것이므로 바로 ready
        provider = self.provider_name_entry.get().strip()
        if provider.endswith("호"):
            self.provider_name_ready = True

    def update_step_display(self):
        """예약 단계 GUI 표시 업데이트"""
        # 기본: 둘 다 비활성 (회색)
        inactive_bg = "#333333"
        inactive_fg = "#888888"
        active_2step_bg = "#28a745"  # 녹색
        active_3step_bg = "#17a2b8"  # 청록색
        active_fg = "#ffffff"

        if self.detected_reservation_type == "2step":
            self.step2_label.configure(background=active_2step_bg, foreground=active_fg)
            self.step3_label.configure(background=inactive_bg, foreground=inactive_fg)
        elif self.detected_reservation_type == "3step":
            self.step2_label.configure(background=inactive_bg, foreground=inactive_fg)
            self.step3_label.configure(background=active_3step_bg, foreground=active_fg)
        else:
            self.step2_label.configure(background=inactive_bg, foreground=inactive_fg)
            self.step3_label.configure(background=inactive_bg, foreground=inactive_fg)

    def reset_inputs(self):
        """입력 필드 초기화 (검색 키워드 제외)"""
        self.url_entry.delete(0, tk.END)
        self.provider_name_entry.delete(0, tk.END)
        self.pa_n_uid_entry.delete(0, tk.END)
        self.base_url_entry.delete(0, tk.END)
        self.has_seat_var.set(False)
        self.toggle_seat_options()
        self.seat_priority_entry.delete(0, tk.END)
        self.seat_priority_entry.insert(0, "15, 14, 1, 8, 7, 13, 2, 9, 6, 12, 3, 10, 5, 11, 4")
        self.preview_text.delete("1.0", tk.END)
        self.preview_text.insert("1.0", "# 선사명, BASE_URL, PA_N_UID를 입력해주세요.")
        self.detected_reservation_type = None
        self.update_step_display()
        self.status_var.set("🔄 입력 필드가 초기화되었습니다.")

    def parse_url(self):
        """URL 분석"""
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("경고", "URL을 입력해주세요.")
            return

        try:
            parsed = urlparse(url)
            query_params = parse_qs(parsed.query)

            # PA_N_UID 추출
            pa_n_uid = query_params.get('PA_N_UID', [''])[0]
            if pa_n_uid:
                self.pa_n_uid_entry.delete(0, tk.END)
                self.pa_n_uid_entry.insert(0, pa_n_uid)

            # BASE_URL 추출
            path = parsed.path
            base_url_match = re.search(r'(.*?/_core/module/reservation_boat_[^/]+)', url)
            if base_url_match:
                base_url = base_url_match.group(1)
                self.base_url_entry.delete(0, tk.END)
                self.base_url_entry.insert(0, base_url)

            # 예약 타입 자동 감지 (popu2 = 2step, popup = 3step)
            if "popu2.step" in url or "/popu2" in url:
                self.detected_reservation_type = "2step"
            elif "popup.step" in url or "/popup" in url:
                self.detected_reservation_type = "3step"
            else:
                self.detected_reservation_type = None

            # 예약 단계 GUI 업데이트
            self.update_step_display()

            # 도메인에서 선사명 추정 (옵션)
            domain = parsed.netloc
            if domain.startswith("www."):
                domain = domain[4:]

            self.provider_name_entry.focus_set()
            self.update_preview()

            # 상태 메시지에 예약 타입 표시
            if self.detected_reservation_type == "2step":
                type_msg = " [STEP2 - popu2]"
            elif self.detected_reservation_type == "3step":
                type_msg = " [STEP3 - popup]"
            else:
                type_msg = ""
            self.status_var.set(f"✅ URL 분석 완료!{type_msg} 선사명을 입력해주세요.")

        except Exception as e:
            messagebox.showerror("오류", f"URL 분석 중 오류 발생:\n{str(e)}")

    def test_url(self):
        """URL 연결 테스트"""
        base_url = self.base_url_entry.get().strip()
        pa_uid = self.pa_n_uid_entry.get().strip()

        if not base_url or not pa_uid:
            messagebox.showerror("오류", "BASE_URL과 PA_N_UID를 입력해주세요.")
            return

        try:
            session = requests.Session()
            session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            })

            # 1차: popu2.step1.php 테스트 (2단계 방식)
            test_url_2step = f"{base_url}/popu2.step1.php?date=20261201&PA_N_UID={pa_uid}"
            response = session.get(test_url_2step, timeout=10)

            reservation_type = None
            test_url = test_url_2step

            if response.status_code == 200 and "PS_N_UID" in response.text:
                reservation_type = "2단계"
            else:
                # 2차: popup.step1.php 테스트 (3단계 방식)
                test_url_3step = f"{base_url}/popup.step1.php?date=20261201&PA_N_UID={pa_uid}"
                response = session.get(test_url_3step, timeout=10)
                test_url = test_url_3step

                if response.status_code == 200 and "PS_N_UID" in response.text:
                    reservation_type = "3단계"

            status = response.status_code
            size = len(response.text)
            has_ps_uid = "PS_N_UID" in response.text
            has_step = "STEP" in response.text or "step" in response.text
            has_seat = "seat" in response.text.lower() or "num_view" in response.text

            if reservation_type:
                type_msg = f"✅ 예약 타입: {reservation_type} ({'popu2' if reservation_type == '2단계' else 'popup'})"
                status_msg = f"✅ 정상적인 더피싱 예약 페이지입니다! ({reservation_type} 방식)"
                # 감지 결과 저장
                self.detected_reservation_type = "2step" if reservation_type == "2단계" else "3step"
            else:
                type_msg = "❌ 예약 타입: 감지 실패"
                status_msg = "⚠️ 예약 페이지가 아니거나 접근이 불가능합니다."
                self.detected_reservation_type = None

            result_msg = f"""📊 URL 테스트 결과

🔗 테스트 URL:
{test_url}

📡 응답 상태: {status}
📦 응답 크기: {size:,} bytes

{type_msg}
✅ PS_N_UID 발견: {'예' if has_ps_uid else '아니오'}
✅ STEP 키워드: {'예' if has_step else '아니오'}
✅ 좌석 관련: {'예' if has_seat else '아니오'}

{status_msg}"""

            messagebox.showinfo("URL 테스트 결과", result_msg)
            self.status_var.set(f"✅ URL 테스트 완료 - Status: {status}")

        except requests.exceptions.Timeout:
            messagebox.showerror("오류", "연결 시간 초과")
        except requests.exceptions.ConnectionError:
            messagebox.showerror("오류", "연결 실패 - URL 확인 필요")
        except Exception as e:
            messagebox.showerror("오류", f"테스트 실패: {e}")

    def generate_code(self):
        """봇 코드 생성"""
        provider = self.provider_name_entry.get().strip()
        base_url = self.base_url_entry.get().strip()
        pa_uid = self.pa_n_uid_entry.get().strip()
        has_seat = self.has_seat_var.get()
        seats = self.seat_priority_entry.get().strip()
        keywords = self.keywords_entry.get().strip()

        if not all([provider, base_url, pa_uid]):
            return None

        # 좌석 우선순위 파싱 (띄어쓰기 유무 상관없이 처리)
        seat_list = ""
        if has_seat and seats:
            seat_items = [s.strip() for s in seats.split(",") if s.strip()]
            seat_list = ", ".join([f"'{s}'" for s in seat_items])

        # 커스텀 키워드 체크 (체크박스 활성화 시에만)
        use_custom_keywords = self.var_keywords_enable.get() and keywords.strip() != ""

        # 예약 타입 (URL 테스트 결과 사용, 없으면 기본값 2step)
        reservation_type = getattr(self, 'detected_reservation_type', None) or "2step"

        # 코드 생성
        code = f'''# -*- coding: utf-8 -*-
"""
{provider} API 봇 (더피싱)
패턴: {'2단계' if reservation_type == '2step' else '3단계'} + 좌석선택 {'활성화' if has_seat else '비활성화'}
"""
from base_api_bot import TheFishingAPIBot


class {provider}APIBot(TheFishingAPIBot):
    BASE_URL = "{base_url}"
    PA_N_UID = "{pa_uid}"
    PROVIDER_NAME = "{provider}"
    RESERVATION_TYPE = "{reservation_type}"  # 2step(popu2) 또는 3step(popup)
    HAS_SEAT_SELECTION = {str(has_seat)}
'''

        if has_seat and seat_list:
            code += f'''
    # 좌석 우선순위
    SEAT_PRIORITY = [{seat_list}]
'''

        if use_custom_keywords:
            kw_items = [k.strip() for k in keywords.split(",")]
            kw_list = ", ".join([f'"{k}"' for k in kw_items])
            code += f'''
    # 어종 검색 키워드 (커스텀)
    SEARCH_KEYWORDS = [{kw_list}]
'''

        code += f'''

if __name__ == "__main__":
    bot = {provider}APIBot()
    bot.run()
'''

        return code

    def update_preview(self):
        """미리보기 갱신"""
        code = self.generate_code()
        self.preview_text.delete("1.0", tk.END)

        if code:
            self.preview_text.insert("1.0", code)
            # 구문 강조
            self._apply_syntax_highlighting()
        else:
            self.preview_text.insert("1.0", "# 선사명, BASE_URL, PA_N_UID를 입력해주세요.")

    def _apply_syntax_highlighting(self):
        """간단한 구문 강조"""
        self.preview_text.tag_configure("keyword", foreground="#569cd6")
        self.preview_text.tag_configure("string", foreground="#ce9178")
        self.preview_text.tag_configure("comment", foreground="#6a9955")
        self.preview_text.tag_configure("class", foreground="#4ec9b0")
        self.preview_text.tag_configure("bool", foreground="#569cd6")

        keywords = ["from", "import", "class", "def", "if", "True", "False", "None"]
        for kw in keywords:
            start = "1.0"
            while True:
                pos = self.preview_text.search(rf"\b{kw}\b", start, stopindex=tk.END, regexp=True)
                if not pos:
                    break
                end = f"{pos}+{len(kw)}c"
                self.preview_text.tag_add("keyword", pos, end)
                start = end

    def validate_inputs(self):
        """입력 검증"""
        if not self.provider_name_entry.get().strip():
            messagebox.showerror("오류", "선사명을 입력해주세요.")
            return False

        if not self.base_url_entry.get().strip():
            messagebox.showerror("오류", "BASE_URL을 입력해주세요.")
            return False

        if not self.pa_n_uid_entry.get().strip():
            messagebox.showerror("오류", "PA_N_UID를 입력해주세요.")
            return False

        url = self.base_url_entry.get().strip()
        if not url.startswith("http"):
            messagebox.showerror("오류", "BASE_URL은 http:// 또는 https://로 시작해야 합니다.")
            return False

        return True

    def generate_bot(self):
        """봇 파일 생성"""
        # 선사명이 '호'로 끝나는지 확인 (IME 조합 완료 체크)
        provider = self.provider_name_entry.get().strip()
        if provider and not provider.endswith("호"):
            messagebox.showwarning("입력 확인", "선사명이 '호'로 끝나지 않습니다.\n입력을 확인해주세요.")
            self.provider_name_entry.focus_set()
            return

        # '호'로 끝나지만 0.5초가 지나지 않은 경우 (IME 조합 중)
        if provider and provider.endswith("호") and not self.provider_name_ready:
            messagebox.showinfo("잠시만요", "선사명 입력 중입니다.\n잠시 후 다시 시도해주세요.")
            return

        if not self.validate_inputs():
            return

        code = self.generate_code()
        if not code:
            return

        provider = self.provider_name_entry.get().strip()
        filename = f"{provider}_API.py"
        filepath = os.path.join(self.current_dir, filename)

        # 파일 존재 확인
        if os.path.exists(filepath):
            result = messagebox.askyesno("확인", f"{filename} 파일이 이미 존재합니다.\n덮어쓰시겠습니까?")
            if not result:
                return

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(code)

            messagebox.showinfo("성공", f"✅ {filename} 파일이 생성되었습니다!\n\n경로: {filepath}")
            self.load_existing_bots()
            self.status_var.set(f"✅ 파일 생성 완료: {filename}")

        except Exception as e:
            messagebox.showerror("오류", f"파일 생성 실패: {e}")

    def register_to_launcher(self):
        """런처에 등록 (팝업창 방식)"""
        provider = self.provider_name_entry.get().strip()
        if not provider:
            messagebox.showerror("오류", "선사명을 입력해주세요.")
            return

        # 선사명이 '호'로 끝나는지 확인
        if not provider.endswith("호"):
            messagebox.showwarning("입력 확인", "선사명이 '호'로 끝나지 않습니다.\n입력을 확인해주세요.")
            self.provider_name_entry.focus_set()
            return

        # '호'로 끝나지만 0.5초가 지나지 않은 경우 (IME 조합 중)
        if not self.provider_name_ready:
            messagebox.showinfo("잠시만요", "선사명 입력 중입니다.\n잠시 후 다시 시도해주세요.")
            return

        filename = f"{provider}_API.py"
        filepath = os.path.join(self.current_dir, filename)

        if not os.path.exists(filepath):
            result = messagebox.askyesno("확인", f"{filename} 파일이 없습니다.\n먼저 생성하시겠습니까?")
            if result:
                self.generate_bot()
            return

        # 런처 파일 찾기
        launcher_path = os.path.normpath(os.path.join(self.current_dir, "..", "..", "..", "쭈갑예약_Bot_Launcher.py"))

        if not os.path.exists(launcher_path):
            messagebox.showerror("오류", f"런처 파일을 찾을 수 없습니다.\n{launcher_path}")
            return

        # 런처 등록 팝업창
        register_window = ttk.Toplevel(self.root)
        register_window.title("🚀 런처 등록 - API 봇")

        win_width = 500
        win_height = 400
        screen_width = register_window.winfo_screenwidth()
        screen_height = register_window.winfo_screenheight()
        x = (screen_width - win_width) // 2
        y = (screen_height - win_height) // 2
        register_window.geometry(f"{win_width}x{win_height}+{x}+{y}")
        register_window.resizable(False, False)
        register_window.transient(self.root)
        register_window.grab_set()

        frame = ttk.Frame(register_window, padding="20")
        frame.pack(fill=BOTH, expand=True)

        ttk.Label(frame, text="런처에 새 API 봇 등록", font=("맑은 고딕", 13, "bold"), bootstyle="primary").pack(pady=(0, 20))

        # 항구 선택
        port_frame = ttk.Frame(frame)
        port_frame.pack(fill=X, pady=8)
        ttk.Label(port_frame, text="항구:", width=10, font=("맑은 고딕", 10)).pack(side=LEFT)
        port_var = tk.StringVar()
        port_combo = ttk.Combobox(port_frame, textvariable=port_var, values=PORTS, width=35, font=("맑은 고딕", 10), state="readonly")
        port_combo.pack(side=LEFT, padx=5)

        # 선사명
        provider_frame = ttk.Frame(frame)
        provider_frame.pack(fill=X, pady=8)
        ttk.Label(provider_frame, text="선사명:", width=10, font=("맑은 고딕", 10)).pack(side=LEFT)
        provider_var = tk.StringVar(value=f"{provider}(API)")
        provider_entry = ttk.Entry(provider_frame, textvariable=provider_var, width=37, font=("맑은 고딕", 10))
        provider_entry.pack(side=LEFT, padx=5)

        # 봇 경로
        path_frame = ttk.Frame(frame)
        path_frame.pack(fill=X, pady=8)
        ttk.Label(path_frame, text="봇 경로:", width=10, font=("맑은 고딕", 10)).pack(side=LEFT)
        path_var = tk.StringVar(value=f"api/더피싱/{filename}")
        path_entry = ttk.Entry(path_frame, textvariable=path_var, width=37, font=("맑은 고딕", 10), state="readonly")
        path_entry.pack(side=LEFT, padx=5)

        # 버튼
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=25)

        def do_register():
            port = port_var.get().strip()
            bot_key = provider_var.get().strip()
            bot_path = path_var.get().strip()

            if not port:
                messagebox.showwarning("경고", "항구를 선택해주세요.", parent=register_window)
                return

            if not bot_key:
                messagebox.showwarning("경고", "선사명을 입력해주세요.", parent=register_window)
                return

            try:
                with open(launcher_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 이미 등록되어 있는지 확인
                if f'"{bot_key}"' in content:
                    messagebox.showinfo("알림", f"{bot_key}는 이미 런처에 등록되어 있습니다.", parent=register_window)
                    return

                # 해당 항구 섹션 찾기
                port_pattern = rf'("{re.escape(port)}":\s*\{{[^}}]*)\}}'
                match = re.search(port_pattern, content)

                if not match:
                    messagebox.showerror("오류", f"런처에서 '{port}' 항구를 찾을 수 없습니다.", parent=register_window)
                    return

                # 항구 섹션 끝에 새 항목 추가
                port_content = match.group(1).rstrip()
                if port_content.endswith(','):
                    new_entry = f'\n        "{bot_key}": "{bot_path}",'
                else:
                    new_entry = f',\n        "{bot_key}": "{bot_path}",'
                new_port_content = port_content + new_entry + "\n    }"

                new_content = content[:match.start()] + new_port_content + content[match.end():]

                with open(launcher_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)

                messagebox.showinfo("성공", f"✅ {bot_key}가 {port}에 등록되었습니다!", parent=register_window)
                self.status_var.set(f"✅ 런처 등록 완료: {bot_key} → {port}")
                register_window.destroy()

            except Exception as e:
                messagebox.showerror("오류", f"런처 등록 실패: {e}", parent=register_window)

        ttk.Button(btn_frame, text="✅ 등록", command=do_register, width=12, bootstyle="success").pack(side=LEFT, padx=10)
        ttk.Button(btn_frame, text="❌ 취소", command=register_window.destroy, width=12, bootstyle="danger-outline").pack(side=LEFT, padx=10)

    def open_folder(self):
        """폴더 열기"""
        os.startfile(self.current_dir)


def main():
    root = ttk.Window(themename="darkly")  # 다크 테마
    app = APIBotGeneratorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
