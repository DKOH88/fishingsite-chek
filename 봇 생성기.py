# -*- coding: utf-8 -*-
"""
봇 생성기 GUI
더피싱/선상24 새 선사 봇을 쉽게 추가할 수 있는 도구
ttkbootstrap 적용 모던 UI
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
from bs4 import BeautifulSoup


class BotGeneratorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🎣 봇 생성기")

        # 창 크기
        win_width = 900
        win_height = 1150

        # 화면 중앙 위치 계산
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - win_width) // 2
        y = (screen_height - win_height) // 2

        self.root.geometry(f"{win_width}x{win_height}+{x}+{y}")
        self.root.resizable(True, True)

        # 현재 모드 (더피싱 / 선상24)
        self.current_mode = "더피싱"

        self.create_widgets()

    def create_widgets(self):
        # 메인 프레임
        self.main_frame = ttk.Frame(self.root, padding="15")
        self.main_frame.pack(fill=BOTH, expand=True)

        # ============================================================
        # 모드 선택 버튼 (더피싱 / 선상24)
        # ============================================================
        mode_frame = ttk.Frame(self.main_frame)
        mode_frame.pack(fill=X, pady=(0, 15))

        ttk.Label(mode_frame, text="봇 타입 선택:", font=("맑은 고딕", 11, "bold")).pack(side=LEFT, padx=(0, 15))

        # 더피싱 버튼
        self.btn_thefishing = ttk.Button(
            mode_frame, text="🎣 더피싱",
            bootstyle="success",
            width=15,
            command=lambda: self.switch_mode("더피싱")
        )
        self.btn_thefishing.pack(side=LEFT, padx=5)

        # 선상24 버튼
        self.btn_sunsang24 = ttk.Button(
            mode_frame, text="⛵ 선상24",
            bootstyle="light-outline",
            width=15,
            command=lambda: self.switch_mode("선상24")
        )
        self.btn_sunsang24.pack(side=LEFT, padx=5)

        # 현재 모드 표시
        self.mode_label = ttk.Label(mode_frame, text="현재: 더피싱 모드", font=("맑은 고딕", 10), bootstyle="success")
        self.mode_label.pack(side=LEFT, padx=20)

        # ============================================================
        # 콘텐츠 프레임 (모드별 UI 컨테이너)
        # ============================================================
        self.content_frame = ttk.Frame(self.main_frame)
        self.content_frame.pack(fill=BOTH, expand=True)

        # 더피싱 UI 생성
        self.create_thefishing_ui()

    def switch_mode(self, mode):
        """모드 전환"""
        if self.current_mode == mode:
            return

        self.current_mode = mode

        # 버튼 스타일 변경
        if mode == "더피싱":
            self.btn_thefishing.configure(bootstyle="success")
            self.btn_sunsang24.configure(bootstyle="light-outline")
            self.mode_label.configure(text="현재: 더피싱 모드", bootstyle="success")
        else:
            self.btn_thefishing.configure(bootstyle="light-outline")
            self.btn_sunsang24.configure(bootstyle="success")
            self.mode_label.configure(text="현재: 선상24 모드", bootstyle="success")

        # 기존 콘텐츠 제거
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        # 새 UI 생성
        if mode == "더피싱":
            self.create_thefishing_ui()
        else:
            self.create_sunsang24_ui()

    # ============================================================
    # 더피싱 UI
    # ============================================================
    def create_thefishing_ui(self):
        """더피싱 봇 생성 UI"""
        # 제목 + 도움말 버튼
        title_frame = ttk.Frame(self.content_frame)
        title_frame.pack(fill=X, pady=(0, 15))
        ttk.Label(title_frame, text="🎣 더피싱 새 봇 생성기", font=("맑은 고딕", 16, "bold"), bootstyle="primary").pack(side=LEFT)
        ttk.Button(title_frame, text="❓ 도움말", command=self.tf_show_help, bootstyle="secondary-outline", width=12).pack(side=RIGHT)

        # 1. 예약 URL 입력
        url_frame = ttk.Labelframe(self.content_frame, text="[1] 예약 URL 입력", padding="10", bootstyle="info")
        url_frame.pack(fill=X, pady=(0, 10))

        ttk.Label(url_frame, text="예약 페이지 URL:", font=("맑은 고딕", 10, "bold")).pack(anchor=W)

        self.tf_url_entry = ttk.Entry(url_frame, width=80, font=("맑은 고딕", 10))
        self.tf_url_entry.pack(fill=X, pady=(0, 5))

        parse_btn = ttk.Button(url_frame, text="🔍 URL 분석", command=self.tf_parse_url, bootstyle="info-outline")
        parse_btn.pack(anchor=W)

        # 2. 기본 정보
        info_frame = ttk.Labelframe(self.content_frame, text="[2] 기본 정보 (자동 분석)", padding="10", bootstyle="danger")
        info_frame.pack(fill=X, pady=(0, 10))

        info_grid = ttk.Frame(info_frame)
        info_grid.pack(fill=X)

        # 선사명
        ttk.Label(info_grid, text="선사명 *:", font=("맑은 고딕", 9)).grid(row=0, column=0, sticky=W, pady=5)
        self.tf_provider_name_entry = ttk.Entry(info_grid, width=25, font=("맑은 고딕", 10))
        self.tf_provider_name_entry.grid(row=0, column=1, sticky=W, pady=5, padx=(5, 20))

        # 클래스명
        ttk.Label(info_grid, text="클래스명:", font=("맑은 고딕", 9)).grid(row=0, column=2, sticky=W, pady=5)
        self.tf_class_name_entry = ttk.Entry(info_grid, width=25, font=("맑은 고딕", 10))
        self.tf_class_name_entry.grid(row=0, column=3, sticky=W, pady=5, padx=5)

        # 도메인
        ttk.Label(info_grid, text="도메인:", font=("맑은 고딕", 9)).grid(row=1, column=0, sticky=W, pady=5)
        self.tf_domain_entry = ttk.Entry(info_grid, width=25, font=("맑은 고딕", 10))
        self.tf_domain_entry.grid(row=1, column=1, sticky=W, pady=5, padx=(5, 20))

        # PA_N_UID
        ttk.Label(info_grid, text="PA_N_UID:", font=("맑은 고딕", 9)).grid(row=1, column=2, sticky=W, pady=5)
        self.tf_pa_n_uid_entry = ttk.Entry(info_grid, width=25, font=("맑은 고딕", 10))
        self.tf_pa_n_uid_entry.grid(row=1, column=3, sticky=W, pady=5, padx=5)

        # API 버전
        ttk.Label(info_grid, text="API 버전:", font=("맑은 고딕", 9)).grid(row=2, column=0, sticky=W, pady=5)
        self.tf_api_version_entry = ttk.Entry(info_grid, width=25, font=("맑은 고딕", 10))
        self.tf_api_version_entry.grid(row=2, column=1, sticky=W, pady=5, padx=(5, 20))

        # URL 경로
        ttk.Label(info_grid, text="URL 경로:", font=("맑은 고딕", 9)).grid(row=2, column=2, sticky=W, pady=5)
        self.tf_url_path_entry = ttk.Entry(info_grid, width=25, font=("맑은 고딕", 10))
        self.tf_url_path_entry.grid(row=2, column=3, sticky=W, pady=5, padx=5)

        # 3. 예약 타입 설정
        type_frame = ttk.Labelframe(self.content_frame, text="[3] 예약 타입 설정", padding="10", bootstyle="warning")
        type_frame.pack(fill=X, pady=(0, 10))

        type_grid = ttk.Frame(type_frame)
        type_grid.pack(fill=X)

        # STEPS
        ttk.Label(type_grid, text="예약 단계 (STEPS):", font=("맑은 고딕", 9)).grid(row=0, column=0, sticky=W, pady=5)
        self.tf_steps_var = tk.IntVar(value=2)
        steps_frame = ttk.Frame(type_grid)
        steps_frame.grid(row=0, column=1, sticky=W, padx=5)
        ttk.Radiobutton(steps_frame, text="2-step", variable=self.tf_steps_var, value=2, bootstyle="success-toolbutton").pack(side=LEFT, padx=(0, 10))
        ttk.Radiobutton(steps_frame, text="3-step", variable=self.tf_steps_var, value=3, bootstyle="warning-toolbutton").pack(side=LEFT)

        # HTTPS
        ttk.Label(type_grid, text="HTTPS 사용:", font=("맑은 고딕", 9)).grid(row=1, column=0, sticky=W, pady=5)
        self.tf_https_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(type_grid, text="HTTPS 사용", variable=self.tf_https_var, bootstyle="round-toggle").grid(row=1, column=1, sticky=W, padx=5)

        # 4. 좌석 선택 설정
        seat_frame = ttk.Labelframe(self.content_frame, text="[4] 좌석 선택 설정", padding="10", bootstyle="success")
        seat_frame.pack(fill=X, pady=(0, 10))

        self.tf_has_seat_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(seat_frame, text="자리 선택 기능 있음", variable=self.tf_has_seat_var,
                        command=self.tf_toggle_seat_options, bootstyle="success-round-toggle").pack(anchor=W)

        self.tf_seat_priority_frame = ttk.Frame(seat_frame)
        self.tf_seat_priority_frame.pack(fill=X, pady=(10, 0))

        ttk.Label(self.tf_seat_priority_frame, text="좌석 우선순위 (쉼표로 구분):", font=("맑은 고딕", 9)).pack(anchor=W)
        self.tf_seat_priority_entry = ttk.Entry(self.tf_seat_priority_frame, width=70, font=("맑은 고딕", 10))
        self.tf_seat_priority_entry.pack(fill=X, pady=(5, 0))
        self.tf_seat_priority_entry.insert(0, "1,11,10,20,2,12,9,19,3,13,8,18")
        self.tf_toggle_seat_options()

        # 5. 추가 설정
        extra_frame = ttk.Labelframe(self.content_frame, text="[5] 추가 설정 (선택사항)", padding="10", bootstyle="secondary")
        extra_frame.pack(fill=X, pady=(0, 10))

        extra_grid = ttk.Frame(extra_frame)
        extra_grid.pack(fill=X)

        ttk.Label(extra_grid, text="검색 키워드:", font=("맑은 고딕", 9)).grid(row=0, column=0, sticky=W, pady=5)
        self.tf_keywords_entry = ttk.Entry(extra_grid, width=60, font=("맑은 고딕", 10))
        self.tf_keywords_entry.grid(row=0, column=1, sticky=W, pady=5, padx=5)
        self.tf_keywords_entry.insert(0, "갑오징어,쭈꾸미,쭈갑,쭈꾸미&갑오징어")

        # 6. 버튼
        btn_frame = ttk.Frame(self.content_frame)
        btn_frame.pack(fill=X, pady=(15, 0))

        ttk.Button(btn_frame, text="👁️ 코드 미리보기", command=self.tf_preview_code, bootstyle="info", width=18).pack(side=LEFT, padx=(0, 10))
        ttk.Button(btn_frame, text="💾 봇 파일 생성", command=self.tf_generate_bot_file, bootstyle="success", width=18).pack(side=LEFT, padx=(0, 10))
        ttk.Button(btn_frame, text="🚀 런처 등록", command=self.tf_register_to_launcher, bootstyle="warning", width=18).pack(side=LEFT, padx=(0, 10))
        ttk.Button(btn_frame, text="📄 HTML 업데이트", command=self.tf_update_html, bootstyle="primary", width=18).pack(side=LEFT)

        # 상태 표시
        self.tf_status_var = tk.StringVar(value="URL을 입력하고 '분석' 버튼을 클릭하세요.")
        status_label = ttk.Label(self.content_frame, textvariable=self.tf_status_var, font=("맑은 고딕", 9), foreground="gray")
        status_label.pack(anchor=W, pady=(15, 0))

    def tf_toggle_seat_options(self):
        """더피싱 좌석 옵션 토글"""
        state = 'normal' if self.tf_has_seat_var.get() else 'disabled'
        self.tf_seat_priority_entry.configure(state=state)

    def tf_show_help(self):
        """더피싱 도움말 표시"""
        help_text = """📌 더피싱 봇 생성 도움말

🔗 예시 URL:
   https://teammansu.kr/_core/module/reservation_boat_v5.1/popu2.step1.php?date=20261101&PA_N_UID=2829

📝 URL 구성:
   • 도메인: teammansu.kr (선사별 고유)
   • date: 예약 날짜 (YYYYMMDD 형식)
   • PA_N_UID: 선사 고유 ID

⚙️ 사용 방법:
   1. 예약 페이지 URL을 복사하여 붙여넣기
   2. 🔍 URL 분석 버튼 클릭
   3. 자동으로 선사 정보가 추출됩니다

💡 팁:
   • URL은 예약 페이지에서 복사하세요
   • 날짜와 PA_N_UID가 포함된 URL이어야 합니다"""
        messagebox.showinfo("더피싱 도움말", help_text)

    def tf_parse_url(self):
        """더피싱 URL 분석"""
        url = self.tf_url_entry.get().strip()
        if not url:
            messagebox.showwarning("경고", "URL을 입력해주세요.")
            return

        try:
            parsed = urlparse(url)
            query_params = parse_qs(parsed.query)

            # 도메인
            domain = parsed.netloc
            if domain.startswith("www."):
                domain = domain[4:]
            self.tf_domain_entry.delete(0, tk.END)
            self.tf_domain_entry.insert(0, domain)

            # PA_N_UID
            pa_n_uid = query_params.get('PA_N_UID', [''])[0]
            self.tf_pa_n_uid_entry.delete(0, tk.END)
            self.tf_pa_n_uid_entry.insert(0, pa_n_uid)

            # API 버전
            path = parsed.path
            api_match = re.search(r'reservation_boat_([^/]+)', path)
            if api_match:
                self.tf_api_version_entry.delete(0, tk.END)
                self.tf_api_version_entry.insert(0, api_match.group(1))

            # URL 경로
            path_match = re.search(r'(popu2\.step1\.php|popup\.step1\.php)', path)
            if path_match:
                self.tf_url_path_entry.delete(0, tk.END)
                self.tf_url_path_entry.insert(0, path_match.group(1))
                if "popup.step1.php" in path_match.group(1):
                    self.tf_steps_var.set(3)
                else:
                    self.tf_steps_var.set(2)

            # HTTPS
            self.tf_https_var.set(parsed.scheme == "https")

            # 클래스명
            base_name = domain.replace('.kr', '').replace('.com', '').replace('.net', '')
            base_name = re.sub(r'[^a-zA-Z0-9]', '', base_name)
            if base_name:
                class_name = base_name.capitalize() + 'Bot'
                self.tf_class_name_entry.delete(0, tk.END)
                self.tf_class_name_entry.insert(0, class_name)

            self.tf_provider_name_entry.focus_set()
            self.tf_status_var.set(f"✅ URL 분석 완료! 선사명을 입력해주세요.")

        except Exception as e:
            messagebox.showerror("오류", f"URL 분석 중 오류 발생:\n{str(e)}")

    def tf_generate_code(self):
        """더피싱 봇 코드 생성"""
        provider_name = self.tf_provider_name_entry.get().strip()
        class_name = self.tf_class_name_entry.get().strip()
        site_url = self.tf_domain_entry.get().strip()
        pa_n_uid = self.tf_pa_n_uid_entry.get().strip()
        api_version = self.tf_api_version_entry.get().strip()
        url_path = self.tf_url_path_entry.get().strip()
        steps = self.tf_steps_var.get()
        use_https = self.tf_https_var.get()
        has_seat = self.tf_has_seat_var.get()
        seat_priority = self.tf_seat_priority_entry.get().strip()
        keywords = self.tf_keywords_entry.get().strip()

        if not all([provider_name, class_name, site_url, pa_n_uid]):
            messagebox.showwarning("경고", "선사명, 클래스명, 도메인, PA_N_UID는 필수입니다.")
            return None

        seat_list = [s.strip() for s in seat_priority.split(',') if s.strip()] if has_seat and seat_priority else []
        keyword_list = [k.strip() for k in keywords.split(',') if k.strip()]

        code_lines = [
            "# -*- coding: utf-8 -*-",
            '"""',
            f"{provider_name} 봇 - {steps}-step" + (" + 자리선택" if has_seat else ", 자리선택 없음"),
            '"""',
            "",
            "from base_bot import BaseFishingBot",
            "",
            "",
            f"class {class_name}(BaseFishingBot):",
            f'    """{provider_name} 예약 봇"""',
            "",
            f'    SITE_URL = "{site_url}"',
            f'    PA_N_UID = "{pa_n_uid}"',
            f'    PROVIDER_NAME = "{provider_name}"',
            f"    STEPS = {steps}",
            f"    HAS_SEAT_SELECTION = {has_seat}",
        ]

        if has_seat and seat_list:
            seat_str = ", ".join(f"'{s}'" for s in seat_list)
            code_lines.append(f"    SEAT_PRIORITY = [{seat_str}]")

        if api_version and api_version != "v5.2_seat1":
            code_lines.append(f'    API_VERSION = "{api_version}"')
        if url_path == "popup.step1.php":
            code_lines.append(f'    URL_PATH = "{url_path}"')
        if use_https:
            code_lines.append("    USE_HTTPS = True")

        code_lines.extend([
            "",
            "",
            'if __name__ == "__main__":',
            "    import argparse",
            "    import json",
            "",
            "    parser = argparse.ArgumentParser()",
            '    parser.add_argument("--config", required=True)',
            "    args = parser.parse_args()",
            "",
            "    with open(args.config, 'r', encoding='utf-8') as f:",
            "        config = json.load(f)",
            "",
            f"    bot = {class_name}(config)",
            "    try:",
            "        bot.run()",
            "    except KeyboardInterrupt:",
            "        bot.stop()",
            ""
        ])

        return "\n".join(code_lines)

    def tf_preview_code(self):
        """더피싱 코드 미리보기"""
        code = self.tf_generate_code()
        if not code:
            return

        preview_window = ttk.Toplevel(self.root)
        preview_window.title("📝 코드 미리보기 - 더피싱")
        preview_window.geometry("750x650")

        text_frame = ttk.Frame(preview_window, padding="10")
        text_frame.pack(fill=BOTH, expand=True)

        text_area = tk.Text(text_frame, wrap=tk.NONE, font=("Consolas", 11), bg="#1e1e1e", fg="#d4d4d4", insertbackground="white")
        text_area.pack(fill=BOTH, expand=True, side=LEFT)

        scrollbar = ttk.Scrollbar(text_frame, orient=VERTICAL, command=text_area.yview, bootstyle="round")
        scrollbar.pack(side=RIGHT, fill=Y)
        text_area.configure(yscrollcommand=scrollbar.set)

        text_area.insert(tk.END, code)
        text_area.configure(state='disabled')

    def tf_generate_bot_file(self):
        """더피싱 봇 파일 생성"""
        code = self.tf_generate_code()
        if not code:
            return

        provider_name = self.tf_provider_name_entry.get().strip()
        default_filename = f"{provider_name}_Bot.py"

        current_dir = os.path.dirname(os.path.abspath(__file__))
        bots_dir = os.path.join(current_dir, "bots", "더피싱")

        filepath = filedialog.asksaveasfilename(
            initialdir=bots_dir,
            initialfile=default_filename,
            defaultextension=".py",
            filetypes=[("Python files", "*.py")],
            title="봇 파일 저장"
        )

        if filepath:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(code)
            messagebox.showinfo("성공", f"봇 파일이 생성되었습니다!\n\n{filepath}")
            self.tf_status_var.set(f"✅ 파일 생성 완료: {os.path.basename(filepath)}")

    def tf_register_to_launcher(self):
        """더피싱 런처 등록"""
        self.register_to_launcher_common("더피싱")

    def tf_update_html(self):
        """더피싱 봇_분류_현황.html 파일 업데이트 (더피싱 탭만)"""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            html_path = os.path.join(current_dir, "봇_분류_현황.html")

            # 더피싱 봇 스캔
            tf_data = self._scan_thefishing_bots()

            # 선상24 봇 스캔
            ss_data = self._scan_sunsang24_bots()

            # 통합 HTML 생성
            html_content = self._generate_tabbed_html(tf_data, ss_data)

            # 파일 저장
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)

            messagebox.showinfo("완료",
                f"HTML 파일이 업데이트되었습니다! (더피싱 탭)\n\n"
                f"총 {tf_data['total']}개 선사\n"
                f"- STEP2 + 좌석X: {len(tf_data['type1'])}개\n"
                f"- STEP2 + 좌석O: {len(tf_data['type2'])}개\n"
                f"- STEP3 + 좌석X: {len(tf_data['type3'])}개\n"
                f"- STEP3 + 좌석O: {len(tf_data['type4'])}개\n\n"
                f"파일: {html_path}")

            self.tf_status_var.set(f"✅ HTML 업데이트 완료! 총 {tf_data['total']}개 선사")

        except Exception as e:
            messagebox.showerror("오류", f"HTML 업데이트 중 오류 발생:\n{str(e)}")

    def _scan_sunsang24_bots(self):
        """선상24 봇들 스캔"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        bots_dir = os.path.join(current_dir, "bots", "선상24")
        bot_files = glob.glob(os.path.join(bots_dir, "*_Bot.py"))

        type1, type2, type3, type4 = [], [], [], []

        for bot_file in bot_files:
            try:
                with open(bot_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                name_match = re.search(r'PROVIDER_NAME\s*=\s*["\']([^"\']+)["\']', content)
                if not name_match:
                    continue
                provider_name = name_match.group(1)

                subdomain_match = re.search(r'SUBDOMAIN\s*=\s*["\']([^"\']+)["\']', content)
                subdomain = subdomain_match.group(1) if subdomain_match else ""

                mapping_match = re.search(r'USE_DIRECT_MAPPING\s*=\s*(True|False)', content)
                use_mapping = mapping_match.group(1) == 'True' if mapping_match else False

                seat_match = re.search(r'HAS_SEAT_SELECTION\s*=\s*(True|False)', content)
                has_seat = seat_match.group(1) == 'True' if seat_match else False

                seat_priority = ""
                if has_seat:
                    priority_match = re.search(r'SEAT_PRIORITY\s*=\s*\[([^\]]+)\]', content)
                    if priority_match:
                        seats = re.findall(r"['\"]([^'\"]+)['\"]", priority_match.group(1))
                        if seats:
                            seat_priority = ", ".join(seats[:12]) + ("..." if len(seats) > 12 else "")

                bot_info = {
                    'name': provider_name,
                    'subdomain': subdomain,
                    'use_mapping': use_mapping,
                    'has_seat': has_seat,
                    'seat_priority': seat_priority if seat_priority else "(기본 순서)"
                }

                if not use_mapping and not has_seat:
                    type1.append(bot_info)
                elif not use_mapping and has_seat:
                    type2.append(bot_info)
                elif use_mapping and not has_seat:
                    type3.append(bot_info)
                elif use_mapping and has_seat:
                    type4.append(bot_info)

            except:
                continue

        type1.sort(key=lambda x: x['name'])
        type2.sort(key=lambda x: x['name'])
        type3.sort(key=lambda x: x['name'])
        type4.sort(key=lambda x: x['name'])

        return {
            'type1': type1, 'type2': type2,
            'type3': type3, 'type4': type4,
            'total': len(type1) + len(type2) + len(type3) + len(type4)
        }

    def _generate_tabbed_html(self, tf_data, ss_data):
        """탭 기반 HTML 콘텐츠 생성"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        # 더피싱 행 생성
        def tf_rows(bots, step, has_seat):
            rows = []
            for i, bot in enumerate(bots, 1):
                if has_seat:
                    rows.append(f'<tr data-name="{bot["name"]}"><td>{i}</td><td class="boat-name">{bot["name"]}</td><td class="seat-priority">{bot["seat_priority"]}</td></tr>')
                else:
                    badge = "badge-step2" if step == 2 else "badge-step3"
                    rows.append(f'<tr data-name="{bot["name"]}"><td>{i}</td><td class="boat-name">{bot["name"]}</td><td><span class="badge {badge}">{step}-STEP</span> <span class="badge badge-noseat">좌석X</span></td></tr>')
            return "\n".join(rows)

        # 선상24 행 생성
        def ss_rows(bots, has_mapping, has_seat):
            rows = []
            for i, bot in enumerate(bots, 1):
                if has_seat:
                    rows.append(f'<tr data-name="{bot["name"]}"><td>{i}</td><td class="boat-name">{bot["name"]}</td><td>{bot["subdomain"]}</td><td class="seat-priority">{bot["seat_priority"]}</td></tr>')
                else:
                    mapping_badge = '<span class="badge badge-mapping">맵핑O</span>' if has_mapping else '<span class="badge badge-nomapping">맵핑X</span>'
                    rows.append(f'<tr data-name="{bot["name"]}"><td>{i}</td><td class="boat-name">{bot["name"]}</td><td>{bot["subdomain"]}</td><td>{mapping_badge} <span class="badge badge-noseat">좌석X</span></td></tr>')
            return "\n".join(rows)

        html = f'''<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>봇 분류 현황</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); color: #eee; min-height: 100vh; padding: 20px; }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        h1 {{ text-align: center; color: #00d4ff; margin-bottom: 10px; font-size: 2.5em; text-shadow: 0 0 20px rgba(0, 212, 255, 0.5); }}
        .subtitle {{ text-align: center; color: #888; margin-bottom: 20px; font-size: 1.1em; }}

        /* 탭 스타일 */
        .tab-container {{ display: flex; justify-content: center; gap: 10px; margin-bottom: 30px; }}
        .tab-btn {{ padding: 15px 40px; font-size: 1.2em; font-weight: bold; border: none; border-radius: 15px 15px 0 0; cursor: pointer; transition: all 0.3s ease; }}
        .tab-btn.active {{ background: linear-gradient(135deg, #4CAF50, #45a049); color: white; transform: translateY(-5px); box-shadow: 0 5px 20px rgba(76, 175, 80, 0.4); }}
        .tab-btn.inactive {{ background: rgba(255, 255, 255, 0.1); color: #888; }}
        .tab-btn.inactive:hover {{ background: rgba(255, 255, 255, 0.2); color: #fff; }}
        .tab-btn .emoji {{ font-size: 1.3em; margin-right: 8px; }}

        .tab-content {{ display: none; }}
        .tab-content.active {{ display: block; }}

        .search-container {{ display: flex; justify-content: center; margin-bottom: 30px; position: sticky; top: 10px; z-index: 100; }}
        .search-box {{ display: flex; align-items: center; background: rgba(0, 0, 0, 0.6); border-radius: 50px; padding: 5px 20px; border: 2px solid rgba(0, 212, 255, 0.3); backdrop-filter: blur(10px); box-shadow: 0 5px 20px rgba(0, 0, 0, 0.3); transition: all 0.3s ease; }}
        .search-box:focus-within {{ border-color: #00d4ff; box-shadow: 0 5px 30px rgba(0, 212, 255, 0.3); }}
        .search-box input {{ background: transparent; border: none; outline: none; color: #fff; font-size: 1.1em; padding: 12px 15px; width: 300px; }}
        .search-box input::placeholder {{ color: #666; }}
        .search-box .search-icon {{ font-size: 1.3em; color: #00d4ff; }}
        .search-box button {{ background: linear-gradient(135deg, #00d4ff, #0099cc); border: none; color: #fff; padding: 10px 20px; border-radius: 25px; cursor: pointer; font-weight: 600; transition: all 0.3s ease; }}
        .search-box button:hover {{ transform: scale(1.05); box-shadow: 0 5px 15px rgba(0, 212, 255, 0.4); }}
        .search-result {{ text-align: center; margin-bottom: 20px; padding: 10px; border-radius: 10px; display: none; }}
        .search-result.found {{ display: block; background: rgba(76, 175, 80, 0.2); color: #4CAF50; }}
        .search-result.not-found {{ display: block; background: rgba(244, 67, 54, 0.2); color: #f44336; }}
        .summary {{ display: flex; justify-content: center; gap: 20px; margin-bottom: 40px; flex-wrap: wrap; }}
        .summary-card {{ background: rgba(255, 255, 255, 0.1); border-radius: 15px; padding: 20px 30px; text-align: center; backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.1); }}
        .summary-card .number {{ font-size: 2.5em; font-weight: bold; color: #00d4ff; }}
        .summary-card .label {{ color: #aaa; font-size: 0.9em; }}
        .section {{ background: rgba(255, 255, 255, 0.05); border-radius: 20px; padding: 25px; margin-bottom: 30px; backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.1); }}
        .section h2 {{ display: flex; align-items: center; gap: 10px; margin-bottom: 20px; padding-bottom: 15px; border-bottom: 2px solid rgba(255, 255, 255, 0.1); }}
        .section h2 .icon {{ font-size: 1.5em; }}
        .section h2 .count {{ background: rgba(0, 212, 255, 0.2); color: #00d4ff; padding: 5px 15px; border-radius: 20px; font-size: 0.8em; margin-left: auto; }}
        .type1 h2 {{ color: #4CAF50; }} .type1 h2 .count {{ background: rgba(76, 175, 80, 0.2); color: #4CAF50; }}
        .type2 h2 {{ color: #2196F3; }} .type2 h2 .count {{ background: rgba(33, 150, 243, 0.2); color: #2196F3; }}
        .type3 h2 {{ color: #FF9800; }} .type3 h2 .count {{ background: rgba(255, 152, 0, 0.2); color: #FF9800; }}
        .type4 h2 {{ color: #E91E63; }} .type4 h2 .count {{ background: rgba(233, 30, 99, 0.2); color: #E91E63; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 12px 15px; text-align: left; border-bottom: 1px solid rgba(255, 255, 255, 0.1); }}
        th {{ background: rgba(0, 0, 0, 0.3); color: #00d4ff; font-weight: 600; }}
        tr:hover {{ background: rgba(255, 255, 255, 0.05); }}
        tr.highlight {{ background: rgba(0, 212, 255, 0.3) !important; animation: pulse 1.5s ease-in-out; }}
        @keyframes pulse {{ 0%, 100% {{ background: rgba(0, 212, 255, 0.3); }} 50% {{ background: rgba(0, 212, 255, 0.5); }} }}
        .boat-name {{ font-weight: 600; color: #fff; }}
        .seat-priority {{ font-family: 'Consolas', 'Monaco', monospace; color: #ffd700; font-size: 0.9em; }}
        .badge {{ display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 0.75em; font-weight: 600; }}
        .badge-step2 {{ background: rgba(76, 175, 80, 0.2); color: #4CAF50; }}
        .badge-step3 {{ background: rgba(255, 152, 0, 0.2); color: #FF9800; }}
        .badge-noseat {{ background: rgba(158, 158, 158, 0.2); color: #9E9E9E; }}
        .badge-mapping {{ background: rgba(156, 39, 176, 0.2); color: #9C27B0; }}
        .badge-nomapping {{ background: rgba(96, 125, 139, 0.2); color: #607D8B; }}
        .footer {{ text-align: center; color: #666; margin-top: 40px; padding: 20px; }}
        @media (max-width: 768px) {{ .summary {{ flex-direction: column; align-items: center; }} th, td {{ padding: 8px 10px; font-size: 0.9em; }} .search-box input {{ width: 200px; }} }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🎣 봇 분류 현황</h1>
        <p class="subtitle">base_bot.py 기반 통합 봇 시스템</p>

        <!-- 탭 버튼 -->
        <div class="tab-container">
            <button class="tab-btn active" onclick="switchTab('thefishing')"><span class="emoji">🎣</span>더피싱 ({tf_data['total']})</button>
            <button class="tab-btn inactive" onclick="switchTab('sunsang24')"><span class="emoji">⛵</span>선상24 ({ss_data['total']})</button>
        </div>

        <!-- 더피싱 탭 -->
        <div id="thefishing-tab" class="tab-content active">
            <div class="search-container">
                <div class="search-box">
                    <span class="search-icon">🔍</span>
                    <input type="text" id="tfSearchInput" placeholder="선사명 검색 (예: 만석호)" onkeypress="if(event.key==='Enter') searchBoat('tf')">
                    <button onclick="searchBoat('tf')">검색</button>
                </div>
            </div>
            <div id="tfSearchResult" class="search-result"></div>

            <div class="summary">
                <div class="summary-card"><div class="number">{len(tf_data['type1'])}</div><div class="label">STEP2 + 좌석X</div></div>
                <div class="summary-card"><div class="number">{len(tf_data['type2'])}</div><div class="label">STEP2 + 좌석O</div></div>
                <div class="summary-card"><div class="number">{len(tf_data['type3'])}</div><div class="label">STEP3 + 좌석X</div></div>
                <div class="summary-card"><div class="number">{len(tf_data['type4'])}</div><div class="label">STEP3 + 좌석O</div></div>
            </div>

            <div class="section type1">
                <h2><span class="icon">📋</span>1. STEP2 + 좌석선택 없음<span class="count">{len(tf_data['type1'])}개</span></h2>
                <table><thead><tr><th style="width:50px">#</th><th>선사명</th><th>타입</th></tr></thead>
                <tbody>{tf_rows(tf_data['type1'], 2, False)}</tbody></table>
            </div>

            <div class="section type2">
                <h2><span class="icon">🪑</span>2. STEP2 + 좌석선택 있음<span class="count">{len(tf_data['type2'])}개</span></h2>
                <table><thead><tr><th style="width:50px">#</th><th style="width:150px">선사명</th><th>우선 선택 자리</th></tr></thead>
                <tbody>{tf_rows(tf_data['type2'], 2, True)}</tbody></table>
            </div>

            <div class="section type3">
                <h2><span class="icon">📋</span>3. STEP3 + 좌석선택 없음<span class="count">{len(tf_data['type3'])}개</span></h2>
                <table><thead><tr><th style="width:50px">#</th><th>선사명</th><th>타입</th></tr></thead>
                <tbody>{tf_rows(tf_data['type3'], 3, False)}</tbody></table>
            </div>

            <div class="section type4">
                <h2><span class="icon">🪑</span>4. STEP3 + 좌석선택 있음<span class="count">{len(tf_data['type4'])}개</span></h2>
                <table><thead><tr><th style="width:50px">#</th><th style="width:150px">선사명</th><th>우선 선택 자리</th></tr></thead>
                <tbody>{tf_rows(tf_data['type4'], 3, True)}</tbody></table>
            </div>

            <div class="footer"><p>Generated: {now} | C:\\gemini\\fishing_bot\\bots\\더피싱</p></div>
        </div>

        <!-- 선상24 탭 -->
        <div id="sunsang24-tab" class="tab-content">
            <div class="search-container">
                <div class="search-box">
                    <span class="search-icon">🔍</span>
                    <input type="text" id="ssSearchInput" placeholder="선사명 검색 (예: 빅보스호)" onkeypress="if(event.key==='Enter') searchBoat('ss')">
                    <button onclick="searchBoat('ss')">검색</button>
                </div>
            </div>
            <div id="ssSearchResult" class="search-result"></div>

            <div class="summary">
                <div class="summary-card"><div class="number">{len(ss_data['type1'])}</div><div class="label">맵핑X + 좌석X</div></div>
                <div class="summary-card"><div class="number">{len(ss_data['type2'])}</div><div class="label">맵핑X + 좌석O</div></div>
                <div class="summary-card"><div class="number">{len(ss_data['type3'])}</div><div class="label">맵핑O + 좌석X</div></div>
                <div class="summary-card"><div class="number">{len(ss_data['type4'])}</div><div class="label">맵핑O + 좌석O</div></div>
            </div>

            <div class="section type1">
                <h2><span class="icon">📋</span>1. 맵핑X + 좌석선택 없음<span class="count">{len(ss_data['type1'])}개</span></h2>
                <table><thead><tr><th style="width:50px">#</th><th>선사명</th><th>서브도메인</th><th>타입</th></tr></thead>
                <tbody>{ss_rows(ss_data['type1'], False, False)}</tbody></table>
            </div>

            <div class="section type2">
                <h2><span class="icon">🪑</span>2. 맵핑X + 좌석선택 있음<span class="count">{len(ss_data['type2'])}개</span></h2>
                <table><thead><tr><th style="width:50px">#</th><th style="width:150px">선사명</th><th>서브도메인</th><th>우선 선택 자리</th></tr></thead>
                <tbody>{ss_rows(ss_data['type2'], False, True)}</tbody></table>
            </div>

            <div class="section type3">
                <h2><span class="icon">📋</span>3. 맵핑O + 좌석선택 없음<span class="count">{len(ss_data['type3'])}개</span></h2>
                <table><thead><tr><th style="width:50px">#</th><th>선사명</th><th>서브도메인</th><th>타입</th></tr></thead>
                <tbody>{ss_rows(ss_data['type3'], True, False)}</tbody></table>
            </div>

            <div class="section type4">
                <h2><span class="icon">🪑</span>4. 맵핑O + 좌석선택 있음<span class="count">{len(ss_data['type4'])}개</span></h2>
                <table><thead><tr><th style="width:50px">#</th><th style="width:150px">선사명</th><th>서브도메인</th><th>우선 선택 자리</th></tr></thead>
                <tbody>{ss_rows(ss_data['type4'], True, True)}</tbody></table>
            </div>

            <div class="footer"><p>Generated: {now} | C:\\gemini\\fishing_bot\\bots\\선상24</p></div>
        </div>
    </div>

    <script>
        // 검색 상태 관리 (다음 결과 기능)
        let searchState = {{
            tf: {{ lastQuery: '', currentIndex: 0, matchedRows: [] }},
            ss: {{ lastQuery: '', currentIndex: 0, matchedRows: [] }}
        }};

        function switchTab(tab) {{
            // 모든 탭 비활성화
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(el => {{
                el.classList.remove('active');
                el.classList.add('inactive');
            }});

            // 선택된 탭 활성화
            document.getElementById(tab + '-tab').classList.add('active');
            event.target.closest('.tab-btn').classList.remove('inactive');
            event.target.closest('.tab-btn').classList.add('active');

            // 검색 결과 초기화
            document.querySelectorAll('.search-result').forEach(el => {{
                el.className = 'search-result';
                el.style.display = 'none';
            }});
            document.querySelectorAll('tr.highlight').forEach(tr => tr.classList.remove('highlight'));

            // 검색 상태 초기화
            searchState.tf = {{ lastQuery: '', currentIndex: 0, matchedRows: [] }};
            searchState.ss = {{ lastQuery: '', currentIndex: 0, matchedRows: [] }};
        }}

        function searchBoat(prefix) {{
            const inputId = prefix === 'tf' ? 'tfSearchInput' : 'ssSearchInput';
            const resultId = prefix === 'tf' ? 'tfSearchResult' : 'ssSearchResult';
            const tabId = prefix === 'tf' ? 'thefishing-tab' : 'sunsang24-tab';

            const searchInput = document.getElementById(inputId).value.trim();
            const searchResult = document.getElementById(resultId);
            const tabContent = document.getElementById(tabId);
            const state = searchState[prefix];

            // 하이라이트 제거
            tabContent.querySelectorAll('tr.highlight').forEach(tr => tr.classList.remove('highlight'));

            if (!searchInput) {{
                searchResult.className = 'search-result';
                searchResult.style.display = 'none';
                state.lastQuery = '';
                state.matchedRows = [];
                return;
            }}

            // 같은 검색어로 다시 검색하면 다음 결과로 이동
            if (state.lastQuery === searchInput && state.matchedRows.length > 1) {{
                state.currentIndex = (state.currentIndex + 1) % state.matchedRows.length;
            }} else {{
                // 새로운 검색어 - 매칭되는 행 찾기
                state.matchedRows = [];
                state.currentIndex = 0;
                const rows = tabContent.querySelectorAll('tr[data-name]');
                rows.forEach(row => {{
                    const name = row.getAttribute('data-name');
                    if (name.includes(searchInput)) {{
                        state.matchedRows.push({{ row: row, name: name }});
                    }}
                }});
                state.lastQuery = searchInput;
            }}

            if (state.matchedRows.length > 0) {{
                // 모든 매칭 행 하이라이트
                state.matchedRows.forEach(item => item.row.classList.add('highlight'));

                // 현재 인덱스의 행으로 스크롤
                const currentMatch = state.matchedRows[state.currentIndex];
                currentMatch.row.scrollIntoView({{ behavior: 'smooth', block: 'center' }});

                // 결과 메시지
                if (state.matchedRows.length === 1) {{
                    searchResult.innerHTML = `✅ <strong>${{currentMatch.name}}</strong> 찾았습니다!`;
                }} else {{
                    const position = state.currentIndex + 1;
                    searchResult.innerHTML = `✅ ${{position}}/${{state.matchedRows.length}}: <strong>${{currentMatch.name}}</strong> (다시 검색하면 다음 결과)`;
                }}
                searchResult.className = 'search-result found';
            }} else {{
                searchResult.innerHTML = `❌ "<strong>${{searchInput}}</strong>" 선사를 찾을 수 없습니다.`;
                searchResult.className = 'search-result not-found';
            }}
        }}

        document.addEventListener('DOMContentLoaded', function() {{
            document.getElementById('tfSearchInput').focus();
        }});
    </script>
</body>
</html>'''
        return html

    # ============================================================
    # 선상24 UI
    # ============================================================
    def create_sunsang24_ui(self):
        """선상24 봇 생성 UI"""
        # 제목 + 도움말 버튼
        title_frame = ttk.Frame(self.content_frame)
        title_frame.pack(fill=X, pady=(0, 15))
        ttk.Label(title_frame, text="⛵ 선상24 새 봇 생성기", font=("맑은 고딕", 16, "bold"), bootstyle="primary").pack(side=LEFT)
        ttk.Button(title_frame, text="❓ 도움말", command=self.ss_show_help, bootstyle="secondary-outline", width=12).pack(side=RIGHT)

        # 1. 기본 정보
        info_frame = ttk.Labelframe(self.content_frame, text="[1] 기본 정보", padding="10", bootstyle="info")
        info_frame.pack(fill=X, pady=(0, 10))

        info_grid = ttk.Frame(info_frame)
        info_grid.pack(fill=X)

        # 선사명
        ttk.Label(info_grid, text="선사명 *:", font=("맑은 고딕", 9)).grid(row=0, column=0, sticky=W, pady=5)
        self.ss_provider_name_entry = ttk.Entry(info_grid, width=25, font=("맑은 고딕", 10))
        self.ss_provider_name_entry.grid(row=0, column=1, sticky=W, pady=5, padx=(5, 20))

        # 서브도메인
        ttk.Label(info_grid, text="서브도메인 *:", font=("맑은 고딕", 9)).grid(row=0, column=2, sticky=W, pady=5)
        self.ss_subdomain_entry = ttk.Entry(info_grid, width=25, font=("맑은 고딕", 10))
        self.ss_subdomain_entry.grid(row=0, column=3, sticky=W, pady=5, padx=5)

        # ID 조회 섹션
        id_lookup_frame = ttk.Labelframe(self.content_frame, text="[1-1] 예약 ID 자동 조회", padding="10", bootstyle="danger")
        id_lookup_frame.pack(fill=X, pady=(0, 10))

        id_lookup_grid = ttk.Frame(id_lookup_frame)
        id_lookup_grid.pack(fill=X)

        ttk.Label(id_lookup_grid, text="조회할 년월/연도:", font=("맑은 고딕", 9)).grid(row=0, column=0, sticky=W, pady=5)
        self.ss_lookup_yearmonth_entry = ttk.Entry(id_lookup_grid, width=15, font=("맑은 고딕", 10))
        self.ss_lookup_yearmonth_entry.grid(row=0, column=1, sticky=W, pady=5, padx=(5, 10))
        self.ss_lookup_yearmonth_entry.insert(0, "2026")

        ttk.Button(id_lookup_grid, text="🔍 ID 조회", command=self.ss_lookup_schedule_ids,
                   bootstyle="danger-outline", width=12).grid(row=0, column=2, sticky=W, pady=5, padx=5)

        ttk.Label(id_lookup_grid, text="(YYYY: 연도 전체 / YYYYMM: 해당 월)", font=("맑은 고딕", 8), foreground="gray").grid(row=0, column=3, sticky=W, pady=5)

        # 조회 결과 표시
        self.ss_lookup_result_var = tk.StringVar(value="")
        ttk.Label(id_lookup_frame, textvariable=self.ss_lookup_result_var, font=("맑은 고딕", 9), foreground="green").pack(anchor=W, pady=(5, 0))

        # 2. 예약 타입 설정
        type_frame = ttk.Labelframe(self.content_frame, text="[2] 예약 타입 설정", padding="10", bootstyle="warning")
        type_frame.pack(fill=X, pady=(0, 10))

        type_grid = ttk.Frame(type_frame)
        type_grid.pack(fill=X)

        # 좌석 선택 여부
        ttk.Label(type_grid, text="좌석 선택:", font=("맑은 고딕", 9)).grid(row=0, column=0, sticky=W, pady=5)
        self.ss_has_seat_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(type_grid, text="자리 선택 기능 있음", variable=self.ss_has_seat_var,
                        command=self.ss_toggle_seat_options, bootstyle="success-round-toggle").grid(row=0, column=1, sticky=W, padx=5)

        # 매핑 사용 여부
        ttk.Label(type_grid, text="ID 매핑:", font=("맑은 고딕", 9)).grid(row=1, column=0, sticky=W, pady=5)
        self.ss_use_mapping_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(type_grid, text="USE_DIRECT_MAPPING 사용", variable=self.ss_use_mapping_var,
                        command=self.ss_toggle_mapping_options, bootstyle="info-round-toggle").grid(row=1, column=1, sticky=W, padx=5)

        # 3. 좌석 우선순위 (선택적)
        self.ss_seat_frame = ttk.Labelframe(self.content_frame, text="[3] 좌석 우선순위 (좌석 선택 시)", padding="10", bootstyle="success")
        self.ss_seat_frame.pack(fill=X, pady=(0, 10))

        ttk.Label(self.ss_seat_frame, text="좌석 우선순위 (쉼표로 구분):", font=("맑은 고딕", 9)).pack(anchor=W)
        ttk.Label(self.ss_seat_frame, text="예: 10,11,1,20,9,19,2,12,8,18,3,13", font=("맑은 고딕", 8), foreground="gray").pack(anchor=W)
        self.ss_seat_priority_entry = ttk.Entry(self.ss_seat_frame, width=70, font=("맑은 고딕", 10))
        self.ss_seat_priority_entry.pack(fill=X, pady=(5, 0))
        self.ss_seat_priority_entry.insert(0, "10,11,1,20,9,19,2,12,8,18,3,13")

        # 4. ID 매핑 설정 (선택적)
        self.ss_mapping_frame = ttk.Labelframe(self.content_frame, text="[4] ID 매핑 설정 (매핑 사용 시)", padding="10", bootstyle="primary")
        self.ss_mapping_frame.pack(fill=X, pady=(0, 10))

        ttk.Label(self.ss_mapping_frame, text="매핑 타입:", font=("맑은 고딕", 9)).pack(anchor=W)
        self.ss_mapping_type_var = tk.StringVar(value="monthly")
        mapping_type_frame = ttk.Frame(self.ss_mapping_frame)
        mapping_type_frame.pack(anchor=W, pady=5)
        ttk.Radiobutton(mapping_type_frame, text="월별 base_id", variable=self.ss_mapping_type_var,
                        value="monthly", command=self.ss_update_mapping_example, bootstyle="info-toolbutton").pack(side=LEFT, padx=(0, 10))
        ttk.Radiobutton(mapping_type_frame, text="일별 (월,일)", variable=self.ss_mapping_type_var,
                        value="daily", command=self.ss_update_mapping_example, bootstyle="success-toolbutton").pack(side=LEFT, padx=(0, 10))
        ttk.Radiobutton(mapping_type_frame, text="delta_days 방식", variable=self.ss_mapping_type_var,
                        value="delta", command=self.ss_update_mapping_example, bootstyle="warning-toolbutton").pack(side=LEFT)

        ttk.Label(self.ss_mapping_frame, text="매핑 데이터:", font=("맑은 고딕", 9)).pack(anchor=W, pady=(10, 0))
        self.ss_mapping_example_label = ttk.Label(self.ss_mapping_frame, text="", font=("맑은 고딕", 8), foreground="gray")
        self.ss_mapping_example_label.pack(anchor=W)

        self.ss_mapping_entry = tk.Text(self.ss_mapping_frame, height=5, width=70, font=("Consolas", 10), bg="#1e1e1e", fg="#d4d4d4", insertbackground="white")
        self.ss_mapping_entry.pack(fill=X, pady=(5, 0))

        # 초기 상태 설정
        self.ss_toggle_seat_options()
        self.ss_toggle_mapping_options()
        self.ss_update_mapping_example()

        # 5. 버튼
        btn_frame = ttk.Frame(self.content_frame)
        btn_frame.pack(fill=X, pady=(15, 0))

        ttk.Button(btn_frame, text="👁️ 코드 미리보기", command=self.ss_preview_code, bootstyle="info", width=18).pack(side=LEFT, padx=(0, 10))
        ttk.Button(btn_frame, text="💾 봇 파일 생성", command=self.ss_generate_bot_file, bootstyle="success", width=18).pack(side=LEFT, padx=(0, 10))
        ttk.Button(btn_frame, text="🚀 런처 등록", command=self.ss_register_to_launcher, bootstyle="warning", width=18).pack(side=LEFT, padx=(0, 10))
        ttk.Button(btn_frame, text="📄 HTML 업데이트", command=self.ss_update_html, bootstyle="primary", width=18).pack(side=LEFT)

        # 상태 표시
        self.ss_status_var = tk.StringVar(value="선사명과 서브도메인을 입력하세요.")
        status_label = ttk.Label(self.content_frame, textvariable=self.ss_status_var, font=("맑은 고딕", 9), foreground="gray")
        status_label.pack(anchor=W, pady=(15, 0))

    def ss_lookup_schedule_ids(self):
        """선상24 schedule_fleet 페이지에서 data-schedule_no 자동 추출

        입력 형식:
        - YYYYMM (예: 202611) : 해당 월만 조회
        - YYYY (예: 2026) : 해당 연도 전체 조회 (1월~12월)
        """
        subdomain = self.ss_subdomain_entry.get().strip()
        yearmonth_input = self.ss_lookup_yearmonth_entry.get().strip()

        if not subdomain:
            messagebox.showwarning("경고", "서브도메인을 먼저 입력해주세요.")
            return

        if not yearmonth_input:
            messagebox.showwarning("경고", "년월(YYYYMM) 또는 연도(YYYY)를 입력해주세요.")
            return

        # 연도만 입력했는지 확인 (YYYY vs YYYYMM)
        if len(yearmonth_input) == 4 and yearmonth_input.isdigit():
            # 연도 전체 조회
            year = yearmonth_input
            months_to_query = [f"{year}{m:02d}" for m in range(1, 13)]
            is_yearly = True
        elif len(yearmonth_input) == 6 and yearmonth_input.isdigit():
            # 단일 월 조회
            months_to_query = [yearmonth_input]
            is_yearly = False
        else:
            messagebox.showwarning("경고", "년월을 YYYYMM (예: 202611) 또는 YYYY (예: 2026) 형식으로 입력해주세요.")
            return

        try:
            all_schedule_ids = {}
            successful_months = []
            failed_months = []
            self.ss_ship_names_found = set()  # 선사명 목록 초기화

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            for idx, yearmonth in enumerate(months_to_query):
                if is_yearly:
                    self.ss_lookup_result_var.set(f"🔄 조회 중... ({idx+1}/12) - {yearmonth[:4]}년 {int(yearmonth[4:6])}월")
                else:
                    self.ss_lookup_result_var.set("🔄 조회 중...")
                self.root.update()

                try:
                    url = f"https://{subdomain}.sunsang24.com/ship/schedule_fleet/{yearmonth}"
                    response = requests.get(url, headers=headers, timeout=10, verify=False)
                    response.raise_for_status()

                    soup = BeautifulSoup(response.text, 'html.parser')

                    # data-schedule_no 속성을 가진 모든 요소 찾기
                    schedule_elements = soup.find_all(attrs={"data-schedule_no": True})

                    # 날짜+선사별로 ID 추출
                    month_schedule_ids = {}
                    ship_names_found = set()

                    for elem in schedule_elements:
                        schedule_no = elem.get('data-schedule_no')
                        if schedule_no:
                            # 부모 요소에서 날짜 찾기 (table이 중첩되어 있으므로 모든 상위 table 탐색)
                            date_str = None
                            for parent_table in elem.find_parents('table'):
                                table_id = parent_table.get('id', '')
                                if table_id.startswith('d20'):  # d2026-09-01 형식
                                    date_str = table_id[1:]  # 2026-09-01
                                    break

                            if date_str:
                                # TR의 첫 번째 TD에서 선사명 추출
                                ship_name = ""
                                row = elem.find_parent('tr')
                                if row:
                                    first_td = row.find('td')
                                    if first_td:
                                        # 선사명만 추출 (공백, 탭, 줄바꿈 제거)
                                        text = first_td.get_text().strip()
                                        ship_name = text.split()[0] if text else ""

                                if ship_name:
                                    ship_names_found.add(ship_name)

                                # 키: (날짜, 선사명)
                                key = (date_str, ship_name)
                                if key not in month_schedule_ids:
                                    month_schedule_ids[key] = schedule_no

                    if month_schedule_ids:
                        all_schedule_ids.update(month_schedule_ids)
                        successful_months.append(yearmonth)
                        self.ss_ship_names_found.update(ship_names_found)
                    else:
                        failed_months.append(yearmonth)

                except requests.exceptions.RequestException:
                    failed_months.append(yearmonth)
                    continue

            if not all_schedule_ids:
                if is_yearly:
                    self.ss_lookup_result_var.set(f"⚠️ {yearmonth_input}년 전체에서 예약 ID를 찾을 수 없습니다.")
                else:
                    self.ss_lookup_result_var.set(f"⚠️ {yearmonth_input}에서 예약 ID를 찾을 수 없습니다.")
                return

            # 선사별로 데이터 분류
            ship_names = sorted(self.ss_ship_names_found) if hasattr(self, 'ss_ship_names_found') else []

            # 여러 선사가 있는 경우 선택 다이얼로그
            selected_ship = None
            if len(ship_names) > 1:
                # 선사 선택 다이얼로그
                ship_select_dialog = tk.Toplevel(self.root)
                ship_select_dialog.title("선사 선택")
                ship_select_dialog.geometry("300x200")
                ship_select_dialog.transient(self.root)
                ship_select_dialog.grab_set()

                # 중앙 배치
                ship_select_dialog.update_idletasks()
                x = self.root.winfo_x() + (self.root.winfo_width() - 300) // 2
                y = self.root.winfo_y() + (self.root.winfo_height() - 200) // 2
                ship_select_dialog.geometry(f"+{x}+{y}")

                ttk.Label(ship_select_dialog, text="🚢 여러 선사가 발견되었습니다.\n봇을 생성할 선사를 선택하세요:",
                         font=("맑은 고딕", 10)).pack(pady=15)

                selected_var = tk.StringVar(value=ship_names[0])
                for ship in ship_names:
                    # 해당 선사의 데이터 개수
                    count = sum(1 for k in all_schedule_ids.keys() if k[1] == ship)
                    ttk.Radiobutton(ship_select_dialog, text=f"{ship} ({count}개 일정)",
                                   variable=selected_var, value=ship,
                                   bootstyle="info").pack(anchor=W, padx=30, pady=3)

                def on_select():
                    nonlocal selected_ship
                    selected_ship = selected_var.get()
                    ship_select_dialog.destroy()

                ttk.Button(ship_select_dialog, text="선택", command=on_select,
                          bootstyle="success", width=15).pack(pady=15)

                self.root.wait_window(ship_select_dialog)

                if not selected_ship:
                    self.ss_lookup_result_var.set("⚠️ 선사 선택이 취소되었습니다.")
                    return
            elif len(ship_names) == 1:
                selected_ship = ship_names[0]

            # 선택된 선사의 데이터만 필터링
            if selected_ship:
                filtered_ids = {k: v for k, v in all_schedule_ids.items() if k[1] == selected_ship}
                # 선사명 자동 입력
                current_provider = self.ss_provider_name_entry.get().strip()
                if not current_provider:
                    self.ss_provider_name_entry.delete(0, tk.END)
                    self.ss_provider_name_entry.insert(0, selected_ship)
            else:
                filtered_ids = all_schedule_ids

            # 날짜순 정렬 (키가 (date_str, ship_name) 튜플)
            sorted_keys = sorted(filtered_ids.keys(), key=lambda x: x[0])

            # 결과 표시
            result_count = len(filtered_ids)
            if is_yearly:
                success_month_count = len(successful_months)
                success_months_str = ", ".join([f"{int(m[4:6])}월" for m in successful_months])
                ship_info = f" [{selected_ship}]" if selected_ship else ""
                self.ss_lookup_result_var.set(f"✅ {result_count}개 날짜{ship_info} (총 {success_month_count}개월)")
            else:
                ship_info = f" [{selected_ship}]" if selected_ship else ""
                self.ss_lookup_result_var.set(f"✅ {result_count}개 날짜{ship_info}의 ID를 찾았습니다!")

            # 매핑 사용 체크
            self.ss_use_mapping_var.set(True)
            self.ss_toggle_mapping_options()

            # 일별 매핑으로 설정
            self.ss_mapping_type_var.set("daily")

            # 매핑 데이터 자동 입력
            self.ss_mapping_entry.configure(state='normal')
            self.ss_mapping_entry.delete("1.0", tk.END)

            mapping_lines = []
            for key in sorted_keys:
                date_str, ship_name = key
                schedule_no = filtered_ids[key]
                # 2026-11-02 -> (11, 2)
                parts = date_str.split('-')
                if len(parts) == 3:
                    m = int(parts[1])
                    d = int(parts[2])
                    mapping_lines.append(f"({m}, {d}): {schedule_no},   # {m}월 {d}일")

            self.ss_mapping_entry.insert("1.0", "\n".join(mapping_lines))

            # 월별 통계 계산
            monthly_counts = {}
            for key in sorted_keys:
                date_str, ship_name = key
                parts = date_str.split('-')
                if len(parts) == 3:
                    month = int(parts[1])
                    monthly_counts[month] = monthly_counts.get(month, 0) + 1

            # 월별 통계 문자열 생성 (2줄로 나눔: 1-6월, 7-12월)
            if is_yearly and monthly_counts:
                line1 = ", ".join([f"{m}월-{monthly_counts.get(m, 0)}개" for m in range(1, 7) if m in monthly_counts])
                line2 = ", ".join([f"{m}월-{monthly_counts.get(m, 0)}개" for m in range(7, 13) if m in monthly_counts])
                monthly_stats = f"\n{line1}\n{line2}" if line1 and line2 else f"\n{line1 or line2}"
            else:
                monthly_stats = ""

            if is_yearly:
                ship_info = f" [{selected_ship}]" if selected_ship else ""
                self.ss_status_var.set(f"✅ {subdomain}{ship_info} - {yearmonth_input}년 전체 ID 조회 완료! {result_count}개 날짜 ({success_month_count}개월){monthly_stats}")
            else:
                ship_info = f" [{selected_ship}]" if selected_ship else ""
                self.ss_status_var.set(f"✅ {subdomain}{ship_info} - {yearmonth_input} ID 조회 완료! {result_count}개 날짜")

        except Exception as e:
            self.ss_lookup_result_var.set(f"❌ 오류: {str(e)[:50]}")
            import traceback
            traceback.print_exc()

    def ss_show_help(self):
        """선상24 도움말 표시"""
        help_text = """📌 선상24 봇 생성 도움말

🔗 URL 형식:
   https://{서브도메인}.sunsang24.com

📝 서브도메인 예시:
   • doji (도지호)
   • bigboss24 (빅보스호)
   • dongbaek (동백호)
   • teamf (팀에프원호/팀에프투호)

🔍 ID 자동 조회:
   1. 서브도메인 입력
   2. 조회할 년월 또는 연도 입력
      • YYYYMM (예: 202611) → 해당 월만 조회
      • YYYY (예: 2026) → 연도 전체 조회 (1~12월)
   3. 🔍 ID 조회 버튼 클릭
   4. 자동으로 data-schedule_no 추출!

⚙️ 옵션 설명:
   • 자리 선택 기능: 좌석 체크박스가 있는 선사용
   • ID 매핑: reservation_ready URL 방식 선사용

💡 팁:
   • 선사명에 '호'를 포함하세요 (예: 동백호)
   • 서브도메인은 URL에서 확인 가능합니다
   • ID 조회 기능으로 매핑 데이터 자동 생성!"""
        messagebox.showinfo("선상24 도움말", help_text)

    def ss_toggle_seat_options(self):
        """선상24 좌석 옵션 토글"""
        state = 'normal' if self.ss_has_seat_var.get() else 'disabled'
        self.ss_seat_priority_entry.configure(state=state)

    def ss_toggle_mapping_options(self):
        """선상24 매핑 옵션 토글"""
        state = 'normal' if self.ss_use_mapping_var.get() else 'disabled'
        self.ss_mapping_entry.configure(state=state)

    def ss_update_mapping_example(self):
        """선상24 매핑 예시 업데이트"""
        mapping_type = self.ss_mapping_type_var.get()
        if mapping_type == "monthly":
            self.ss_mapping_example_label.configure(text="예: 9: 1650579,  # 9월\n    10: 1650609,  # 10월")
            self.ss_mapping_entry.delete("1.0", tk.END)
            self.ss_mapping_entry.insert("1.0", "9: 1650579,   # 9월\n10: 1650609,  # 10월\n11: 1650639,  # 11월")
        elif mapping_type == "daily":
            self.ss_mapping_example_label.configure(text="예: (7, 9): 1650579,  # 7월 9일\n    (7, 10): 1650580,  # 7월 10일")
            self.ss_mapping_entry.delete("1.0", tk.END)
            self.ss_mapping_entry.insert("1.0", "(7, 9): 1650579,   # 7월 9일\n(7, 10): 1650580,  # 7월 10일")
        else:
            self.ss_mapping_example_label.configure(text="예: 'base_date': '20251219', 'base_id': 1535125")
            self.ss_mapping_entry.delete("1.0", tk.END)
            self.ss_mapping_entry.insert("1.0", "'base_date': '20251219',\n'base_id': 1535125,")

    def ss_generate_code(self):
        """선상24 봇 코드 생성"""
        provider_name = self.ss_provider_name_entry.get().strip()
        subdomain = self.ss_subdomain_entry.get().strip()
        has_seat = self.ss_has_seat_var.get()
        use_mapping = self.ss_use_mapping_var.get()
        seat_priority = self.ss_seat_priority_entry.get().strip()
        mapping_data = self.ss_mapping_entry.get("1.0", tk.END).strip()

        if not provider_name or not subdomain:
            messagebox.showwarning("경고", "선사명과 서브도메인은 필수입니다.")
            return None

        # 클래스명 생성
        class_name = f"{provider_name}Bot".replace(" ", "").replace("-", "")

        code_lines = [
            "# -*- coding: utf-8 -*-",
            '"""',
            f"{provider_name} 예약 봇 (선상24)",
            f"패턴: 맵핑 {'있음' if use_mapping else '없음'} + 자리선택 {'있음' if has_seat else '없음'}",
            '"""',
            "",
            "import sys",
            "import json",
            "import argparse",
            "from base_bot import SunSang24BaseBot",
            "",
            "",
            f"class {class_name}(SunSang24BaseBot):",
            f'    SUBDOMAIN = "{subdomain}"',
            f'    PROVIDER_NAME = "{provider_name}"',
            f"    HAS_SEAT_SELECTION = {has_seat}",
        ]

        if use_mapping:
            mapping_type = self.ss_mapping_type_var.get()
            code_lines.append("    USE_DIRECT_MAPPING = True")
            code_lines.append("")
            if mapping_type == "daily":
                code_lines.append("    # ID 매핑 (일별: 월, 일)")
            elif mapping_type == "monthly":
                code_lines.append("    # ID 매핑 (월별)")
            else:
                code_lines.append("    # ID 매핑 (delta_days)")
            code_lines.append("    ID_MAPPING = {")
            for line in mapping_data.split('\n'):
                if line.strip():
                    code_lines.append(f"        {line.strip()}")
            code_lines.append("    }")

        if has_seat and seat_priority:
            seat_list = [s.strip() for s in seat_priority.split(',') if s.strip()]
            seat_str = ", ".join(f"'{s}'" for s in seat_list)
            code_lines.append(f"    SEAT_PRIORITY = [{seat_str}]")

        code_lines.extend([
            "",
            "",
            'if __name__ == "__main__":',
            "    parser = argparse.ArgumentParser()",
            '    parser.add_argument("--config", required=True)',
            "    args = parser.parse_args()",
            "",
            "    with open(args.config, 'r', encoding='utf-8') as f:",
            "        config = json.load(f)",
            "",
            f"    bot = {class_name}(config)",
            "    try:",
            "        bot.run()",
            "    except KeyboardInterrupt:",
            "        bot.stop()",
            ""
        ])

        return "\n".join(code_lines)

    def ss_preview_code(self):
        """선상24 코드 미리보기"""
        code = self.ss_generate_code()
        if not code:
            return

        preview_window = ttk.Toplevel(self.root)
        preview_window.title("📝 코드 미리보기 - 선상24")
        preview_window.geometry("750x650")

        text_frame = ttk.Frame(preview_window, padding="10")
        text_frame.pack(fill=BOTH, expand=True)

        text_area = tk.Text(text_frame, wrap=tk.NONE, font=("Consolas", 11), bg="#1e1e1e", fg="#d4d4d4", insertbackground="white")
        text_area.pack(fill=BOTH, expand=True, side=LEFT)

        scrollbar = ttk.Scrollbar(text_frame, orient=VERTICAL, command=text_area.yview, bootstyle="round")
        scrollbar.pack(side=RIGHT, fill=Y)
        text_area.configure(yscrollcommand=scrollbar.set)

        text_area.insert(tk.END, code)
        text_area.configure(state='disabled')

    def ss_generate_bot_file(self):
        """선상24 봇 파일 생성"""
        code = self.ss_generate_code()
        if not code:
            return

        provider_name = self.ss_provider_name_entry.get().strip()
        default_filename = f"{provider_name}_Bot.py"

        current_dir = os.path.dirname(os.path.abspath(__file__))
        bots_dir = os.path.join(current_dir, "bots", "선상24")

        filepath = filedialog.asksaveasfilename(
            initialdir=bots_dir,
            initialfile=default_filename,
            defaultextension=".py",
            filetypes=[("Python files", "*.py")],
            title="봇 파일 저장"
        )

        if filepath:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(code)
            messagebox.showinfo("성공", f"봇 파일이 생성되었습니다!\n\n{filepath}")
            self.ss_status_var.set(f"✅ 파일 생성 완료: {os.path.basename(filepath)}")

    def ss_register_to_launcher(self):
        """선상24 런처 등록"""
        self.register_to_launcher_common("선상24")

    def ss_update_html(self):
        """선상24 봇_분류_현황.html 파일 업데이트 (선상24 탭만)"""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            bots_dir = os.path.join(current_dir, "bots", "선상24")
            html_path = os.path.join(current_dir, "봇_분류_현황.html")

            # 봇 파일들 스캔
            bot_files = glob.glob(os.path.join(bots_dir, "*_Bot.py"))

            # 2가지 타입별로 분류 (맵핑X+좌석X, 맵핑X+좌석O, 맵핑O+좌석X, 맵핑O+좌석O)
            ss_type1 = []  # 맵핑X + 좌석X
            ss_type2 = []  # 맵핑X + 좌석O
            ss_type3 = []  # 맵핑O + 좌석X
            ss_type4 = []  # 맵핑O + 좌석O

            for bot_file in bot_files:
                try:
                    with open(bot_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # 선사명 추출
                    name_match = re.search(r'PROVIDER_NAME\s*=\s*["\']([^"\']+)["\']', content)
                    if not name_match:
                        continue
                    provider_name = name_match.group(1)

                    # SUBDOMAIN 추출
                    subdomain_match = re.search(r'SUBDOMAIN\s*=\s*["\']([^"\']+)["\']', content)
                    subdomain = subdomain_match.group(1) if subdomain_match else ""

                    # USE_DIRECT_MAPPING 추출 (기본값 False)
                    mapping_match = re.search(r'USE_DIRECT_MAPPING\s*=\s*(True|False)', content)
                    use_mapping = mapping_match.group(1) == 'True' if mapping_match else False

                    # HAS_SEAT_SELECTION 추출 (기본값 False)
                    seat_match = re.search(r'HAS_SEAT_SELECTION\s*=\s*(True|False)', content)
                    has_seat = seat_match.group(1) == 'True' if seat_match else False

                    # SEAT_PRIORITY 추출
                    seat_priority = ""
                    if has_seat:
                        priority_match = re.search(r'SEAT_PRIORITY\s*=\s*\[([^\]]+)\]', content)
                        if priority_match:
                            seats = re.findall(r"['\"]([^'\"]+)['\"]", priority_match.group(1))
                            if seats:
                                seat_priority = ", ".join(seats[:12]) + ("..." if len(seats) > 12 else "")

                    bot_info = {
                        'name': provider_name,
                        'subdomain': subdomain,
                        'use_mapping': use_mapping,
                        'has_seat': has_seat,
                        'seat_priority': seat_priority if seat_priority else "(기본 순서)"
                    }

                    if not use_mapping and not has_seat:
                        ss_type1.append(bot_info)
                    elif not use_mapping and has_seat:
                        ss_type2.append(bot_info)
                    elif use_mapping and not has_seat:
                        ss_type3.append(bot_info)
                    elif use_mapping and has_seat:
                        ss_type4.append(bot_info)

                except Exception as e:
                    print(f"봇 파일 분석 오류 ({bot_file}): {e}")
                    continue

            # 정렬
            ss_type1.sort(key=lambda x: x['name'])
            ss_type2.sort(key=lambda x: x['name'])
            ss_type3.sort(key=lambda x: x['name'])
            ss_type4.sort(key=lambda x: x['name'])

            ss_total = len(ss_type1) + len(ss_type2) + len(ss_type3) + len(ss_type4)

            # 기존 HTML에서 더피싱 데이터 읽기 또는 새로 생성
            tf_data = self._scan_thefishing_bots()

            # 통합 HTML 생성
            html_content = self._generate_tabbed_html(tf_data, {
                'type1': ss_type1, 'type2': ss_type2,
                'type3': ss_type3, 'type4': ss_type4,
                'total': ss_total
            })

            # 파일 저장
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)

            messagebox.showinfo("완료",
                f"HTML 파일이 업데이트되었습니다! (선상24 탭)\n\n"
                f"총 {ss_total}개 선사\n"
                f"- 맵핑X + 좌석X: {len(ss_type1)}개\n"
                f"- 맵핑X + 좌석O: {len(ss_type2)}개\n"
                f"- 맵핑O + 좌석X: {len(ss_type3)}개\n"
                f"- 맵핑O + 좌석O: {len(ss_type4)}개\n\n"
                f"파일: {html_path}")

            self.ss_status_var.set(f"✅ HTML 업데이트 완료! 총 {ss_total}개 선사")

        except Exception as e:
            messagebox.showerror("오류", f"HTML 업데이트 중 오류 발생:\n{str(e)}")

    def _scan_thefishing_bots(self):
        """더피싱 봇들 스캔"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        bots_dir = os.path.join(current_dir, "bots", "더피싱")
        bot_files = glob.glob(os.path.join(bots_dir, "*_Bot.py"))

        type1, type2, type3, type4 = [], [], [], []

        for bot_file in bot_files:
            try:
                with open(bot_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                name_match = re.search(r'PROVIDER_NAME\s*=\s*["\']([^"\']+)["\']', content)
                if not name_match:
                    continue
                provider_name = name_match.group(1)

                steps_match = re.search(r'STEPS\s*=\s*(\d+)', content)
                steps = int(steps_match.group(1)) if steps_match else 2

                seat_match = re.search(r'HAS_SEAT_SELECTION\s*=\s*(True|False)', content)
                has_seat = seat_match.group(1) == 'True' if seat_match else False

                seat_priority = ""
                if has_seat:
                    priority_match = re.search(r'SEAT_PRIORITY\s*=\s*\[([^\]]+)\]', content)
                    if priority_match:
                        seats = re.findall(r"['\"]([^'\"]+)['\"]", priority_match.group(1))
                        if seats:
                            seat_priority = ", ".join(seats[:12]) + ("..." if len(seats) > 12 else "")

                bot_info = {
                    'name': provider_name,
                    'steps': steps,
                    'has_seat': has_seat,
                    'seat_priority': seat_priority if seat_priority else "(기본 순서)"
                }

                if steps == 2 and not has_seat:
                    type1.append(bot_info)
                elif steps == 2 and has_seat:
                    type2.append(bot_info)
                elif steps == 3 and not has_seat:
                    type3.append(bot_info)
                elif steps == 3 and has_seat:
                    type4.append(bot_info)

            except:
                continue

        type1.sort(key=lambda x: x['name'])
        type2.sort(key=lambda x: x['name'])
        type3.sort(key=lambda x: x['name'])
        type4.sort(key=lambda x: x['name'])

        return {
            'type1': type1, 'type2': type2,
            'type3': type3, 'type4': type4,
            'total': len(type1) + len(type2) + len(type3) + len(type4)
        }

    # ============================================================
    # 공통 함수
    # ============================================================
    def register_to_launcher_common(self, bot_type):
        """런처에 선사 등록 (공통)"""
        register_window = ttk.Toplevel(self.root)
        register_window.title(f"🚀 런처 등록 - {bot_type}")

        win_width = 500
        win_height = 380
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

        ttk.Label(frame, text=f"런처에 새 선사 등록 ({bot_type})", font=("맑은 고딕", 13, "bold"), bootstyle="primary").pack(pady=(0, 20))

        # 항구 입력
        port_frame = ttk.Frame(frame)
        port_frame.pack(fill=X, pady=8)
        ttk.Label(port_frame, text="항구:", width=10, font=("맑은 고딕", 10)).pack(side=LEFT)

        existing_ports = self.get_existing_ports()
        port_var = tk.StringVar()
        port_combo = ttk.Combobox(port_frame, textvariable=port_var, width=35, font=("맑은 고딕", 10))
        port_combo['values'] = existing_ports
        port_combo.pack(side=LEFT, padx=5)

        # 선사명
        provider_frame = ttk.Frame(frame)
        provider_frame.pack(fill=X, pady=8)
        ttk.Label(provider_frame, text="선사명:", width=10, font=("맑은 고딕", 10)).pack(side=LEFT)
        provider_var = tk.StringVar()

        # 현재 모드에 따라 선사명 가져오기
        if bot_type == "더피싱":
            current_provider = self.tf_provider_name_entry.get().strip()
        else:
            current_provider = self.ss_provider_name_entry.get().strip()
        provider_var.set(current_provider)

        provider_entry = ttk.Entry(provider_frame, textvariable=provider_var, width=37, font=("맑은 고딕", 10))
        provider_entry.pack(side=LEFT, padx=5)

        # 봇 경로
        path_frame = ttk.Frame(frame)
        path_frame.pack(fill=X, pady=8)
        ttk.Label(path_frame, text="봇 경로:", width=10, font=("맑은 고딕", 10)).pack(side=LEFT)
        path_var = tk.StringVar()
        if current_provider:
            path_var.set(f"{bot_type}/{current_provider}_Bot.py")
        path_entry = ttk.Entry(path_frame, textvariable=path_var, width=37, font=("맑은 고딕", 10))
        path_entry.pack(side=LEFT, padx=5)

        # 버튼
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=25)

        def do_register():
            port = port_var.get().strip()
            provider = provider_var.get().strip()
            bot_path = path_var.get().strip()

            if not all([port, provider, bot_path]):
                messagebox.showwarning("경고", "모든 필드를 입력해주세요.", parent=register_window)
                return

            if messagebox.askyesno("확인", f"다음 정보로 런처에 등록하시겠습니까?\n\n항구: {port}\n선사명: {provider}\n봇 경로: {bot_path}", parent=register_window):
                result = self.add_to_launcher_file(port, provider, bot_path)
                if result:
                    messagebox.showinfo("완료", f"런처에 등록되었습니다!\n\n{port} > {provider}", parent=register_window)
                    register_window.destroy()
                else:
                    messagebox.showerror("오류", "런처 파일 수정 중 오류가 발생했습니다.", parent=register_window)

        ttk.Button(btn_frame, text="✅ 등록", command=do_register, width=12, bootstyle="success").pack(side=LEFT, padx=10)
        ttk.Button(btn_frame, text="❌ 취소", command=register_window.destroy, width=12, bootstyle="danger-outline").pack(side=LEFT, padx=10)

    def get_existing_ports(self):
        """런처 파일에서 기존 항구 목록 가져오기"""
        try:
            launcher_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "쭈갑예약_Bot_Launcher.py")
            with open(launcher_path, 'r', encoding='utf-8') as f:
                content = f.read()

            ports = re.findall(r'"([^"]+)":\s*\{[^}]*\}', content)
            return list(dict.fromkeys(ports))
        except:
            return []

    def add_to_launcher_file(self, port, provider, bot_path):
        """런처 파일에 선사 추가"""
        try:
            launcher_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "쭈갑예약_Bot_Launcher.py")

            with open(launcher_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 1. PORTS에 추가
            port_pattern = rf'("{re.escape(port)}":\s*\{{[^}}]*)\}}'
            port_match = re.search(port_pattern, content)

            if port_match:
                port_content = port_match.group(1).rstrip()
                if port_content.endswith(','):
                    new_entry = f'\n        "{provider}": "{bot_path}",'
                else:
                    new_entry = f',\n        "{provider}": "{bot_path}",'
                new_port_content = port_content + new_entry + "\n    }"
                content = content[:port_match.start()] + new_port_content + content[port_match.end():]
            else:
                ports_match = re.search(r'(PORTS\s*=\s*\{)', content)
                if ports_match:
                    insert_pos = ports_match.end()
                    new_port_block = f'\n    "{port}": {{\n        "{provider}": "{bot_path}",\n    }},'
                    content = content[:insert_pos] + new_port_block + content[insert_pos:]
                else:
                    return False

            # 2. 선상24인 경우 SUNSANG24_SITES에도 추가
            if "선상24" in bot_path:
                subdomain = self.ss_subdomain_entry.get().strip() if hasattr(self, 'ss_subdomain_entry') else ""
                if subdomain:
                    # 선사명에서 (선) 접미사 제거
                    clean_provider = provider.replace("(선)", "").strip()
                    # 이미 등록되어 있는지 확인
                    if f'"{clean_provider}"' not in content or f'"{clean_provider}": "{subdomain}"' not in content:
                        # SUNSANG24_SITES 딕셔너리 끝 찾기
                        sites_pattern = r'(SUNSANG24_SITES\s*=\s*\{[^}]*)\}'
                        sites_match = re.search(sites_pattern, content)
                        if sites_match:
                            sites_content = sites_match.group(1).rstrip()
                            if sites_content.endswith(','):
                                new_site_entry = f'\n    "{clean_provider}": "{subdomain}",'
                            else:
                                new_site_entry = f',\n    "{clean_provider}": "{subdomain}",'
                            new_sites_content = sites_content + new_site_entry + "\n}"
                            content = content[:sites_match.start()] + new_sites_content + content[sites_match.end():]

            with open(launcher_path, 'w', encoding='utf-8') as f:
                f.write(content)

            return True
        except Exception as e:
            print(f"런처 파일 수정 오류: {e}")
            return False


def main():
    root = ttk.Window(themename="darkly")
    app = BotGeneratorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
