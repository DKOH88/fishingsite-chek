# -*- coding: utf-8 -*-
"""
더피싱 봇 파일 정보 추출 및 엑셀 저장 (STEP2/STEP3 시트 분리)
"""

import os
import re
import sys

# pandas와 openpyxl 설치 확인
try:
    import pandas as pd
except ImportError:
    print("pandas 설치 중...")
    os.system("pip install pandas openpyxl")
    import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BOTS_DIR = os.path.join(BASE_DIR, "bots")

# 더피싱 선사만 (항구: {선사명: 스크립트경로})
PORTS = {
    "오천항": {
        "금땡이호": "더피싱/금땡이호_Bot.py",
        "나폴리호": "더피싱/나폴리호_Bot.py",
        "뉴성령호": "더피싱/뉴성령호_Bot.py",
        "뉴찬스호": "더피싱/뉴찬스호_Bot.py",
        "범블비호": "더피싱/범블비호_Bot.py",
        "블루호": "더피싱/블루호_Bot.py",
        "비엔나호": "더피싱/비엔나호_Bot.py",
        "샤크호": "더피싱/샤크호_Bot.py",
        "오디세이호": "더피싱/오디세이호_Bot.py",
        "유진호": "더피싱/유진호_Bot.py",
        "카즈미호": "더피싱/카즈미호_Bot.py",
        "캡틴호": "더피싱/캡틴호_Bot.py",
        "프랜드호": "더피싱/프랜드호_Bot.py",
        "바이트호": "더피싱/바이트호_Bot.py",
    },
    "안흥·신진항": {
        "골드피싱호(안흥)": "더피싱/안흥골드피싱호_Bot.py",
        "뉴신정호": "더피싱/뉴신정호_Bot.py",
        "루디호": "더피싱/루디호_Bot.py",
        "마그마호": "더피싱/마그마호_Bot.py",
        "미라클호": "더피싱/미라클호_Bot.py",
        "부흥호": "더피싱/부흥호_Bot.py",
        "솔티가호": "더피싱/솔티가호_Bot.py",
        "여명호": "더피싱/여명호_Bot.py",
        "청용호": "더피싱/청용호_Bot.py",
        "퀸블레스호": "더피싱/퀸블레스호_Bot.py",
        "행운호": "더피싱/행운호_Bot.py",
    },
    "영흥도": {
        "god호": "더피싱/지오디호_Bot.py",
        "만수피싱호": "더피싱/만수피싱호_Bot.py",
        "스타피싱호": "더피싱/스타피싱호_Bot.py",
        "아라호": "더피싱/아라호_Bot.py",
        "아이리스호": "더피싱/아이리스호_Bot.py",
        "야호": "더피싱/야호_Bot.py",
        "짱구호": "더피싱/짱구호_Bot.py",
        "크루즈호": "더피싱/크루즈호_Bot.py",
        "팀만수호": "더피싱/팀만수호_Bot.py",
        "팀만수호2": "더피싱/팀만수호2_Bot.py",
        "페라리호": "더피싱/페라리호_Bot.py",
    },
    "삼길포항": {
        "골드피싱호": "더피싱/골드피싱호_Bot.py",
        "만석호": "더피싱/만석호_Bot.py",
        "승주호": "더피싱/승주호_Bot.py",
        "으리호": "더피싱/으리호_Bot.py",
        "헌터호": "더피싱/헌터호_Bot.py",
        "헤르메스호": "더피싱/헤르메스호_Bot.py",
    },
    "대천항": {
        "까칠이호": "더피싱/까칠이호_Bot.py",
        "아인스호": "더피싱/아인스호_Bot.py",
        "야야호": "더피싱/야야호_Bot.py",
        "예린호": "더피싱/예린호_Bot.py",
        "청춘호": "더피싱/청춘호_Bot.py",
        "팀루피호": "더피싱/팀루피호_Bot.py",
        "승하호": "더피싱/승하호_Bot.py",
        "하이피싱호": "더피싱/하이피싱호_Bot.py",
        "양파호": "더피싱/양파호_Bot.py",
    },
    "마검포항": {
        "천일호": "더피싱/천일호_Bot.py",
        "팀바이트호": "더피싱/팀바이트호_Bot.py",
        "하와이호": "더피싱/하와이호_Bot.py",
    },
    "무창포항": {
        "깜보호": "더피싱/깜보호_Bot.py",
        "헤라호": "더피싱/헤라호_Bot.py",
    },
    "영목항": {
        "청광호": "더피싱/청광호_Bot.py",
        "뉴청남호": "더피싱/뉴청남호_Bot.py",
        "청남호": "더피싱/청남호_Bot.py",
        "청남호2": "더피싱/청남호2_Bot.py",
    },
    "인천": {
        "와이파이호": "더피싱/와이파이호_Bot.py",
        "욜로호": "더피싱/욜로호_Bot.py",
        "제트호": "더피싱/제트호_Bot.py",
    },
    "남당항": {
        "장현호": "더피싱/장현호_Bot.py",
        "장현호2": "더피싱/장현호2_Bot.py",
    },
    "대야도": {
        "아일랜드호": "더피싱/아일랜드호_Bot.py",
        "블루오션호": "더피싱/블루오션호_Bot.py",
    },
    "백사장항": {
        "영차호": "더피싱/영차호_Bot.py",
    },
    "평택항": {
        "오닉스호": "더피싱/오닉스호_Bot.py",
    },
    "홍원항": {
        "조커호": "더피싱/조커호_Bot.py",
    },
}


def extract_bot_info(file_path):
    """봇 파일에서 정보 추출"""
    info = {
        "STEPS": "",
        "HAS_SEAT_SELECTION": "",
        "SEAT_PRIORITY": "",
        "SITE_URL": "",
        "PA_N_UID": "",
        "SUBDOMAIN": "",
        "USE_HTTPS": "",
        "API_VERSION": "",
    }

    if not os.path.exists(file_path):
        return info

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # STEPS
        match = re.search(r'STEPS\s*=\s*(\d+)', content)
        if match:
            info["STEPS"] = match.group(1) + "단계"

        # HAS_SEAT_SELECTION
        match = re.search(r'HAS_SEAT_SELECTION\s*=\s*(True|False)', content)
        if match:
            info["HAS_SEAT_SELECTION"] = "있음" if match.group(1) == "True" else "없음"

        # SEAT_PRIORITY
        match = re.search(r"SEAT_PRIORITY\s*=\s*\[(.*?)\]", content, re.DOTALL)
        if match:
            seats = re.findall(r"'(\d+)'", match.group(1))
            info["SEAT_PRIORITY"] = str(seats) if seats else ""

        # SITE_URL
        match = re.search(r'SITE_URL\s*=\s*["\']([^"\']+)["\']', content)
        if match:
            info["SITE_URL"] = match.group(1)

        # PA_N_UID
        match = re.search(r'PA_N_UID\s*=\s*["\']?(\d+)["\']?', content)
        if match:
            info["PA_N_UID"] = match.group(1)

        # SUBDOMAIN (선상24)
        match = re.search(r'SUBDOMAIN\s*=\s*["\']([^"\']+)["\']', content)
        if match:
            info["SUBDOMAIN"] = match.group(1)

        # USE_HTTPS
        match = re.search(r'USE_HTTPS\s*=\s*(True|False)', content)
        if match:
            info["USE_HTTPS"] = "HTTPS" if match.group(1) == "True" else "HTTP"

        # API_VERSION
        match = re.search(r'API_VERSION\s*=\s*["\']([^"\']+)["\']', content)
        if match:
            info["API_VERSION"] = match.group(1)

        # BASE_URL (API용)
        match = re.search(r'BASE_URL\s*=\s*["\']([^"\']+)["\']', content)
        if match:
            info["BASE_URL"] = match.group(1)

    except Exception as e:
        print(f"Error reading {file_path}: {e}")

    return info


def generate_reservation_url(info, steps):
    """예약 페이지 URL 생성"""
    site_url = info.get("SITE_URL", "")
    pa_n_uid = info.get("PA_N_UID", "")
    api_version = info.get("API_VERSION", "v5.2_seat1")
    use_https = info.get("USE_HTTPS", "HTTP")

    if site_url and pa_n_uid:
        protocol = "https" if use_https == "HTTPS" else "http"
        if steps == 3:
            return f"{protocol}://www.{site_url}/_core/module/reservation_boat_{api_version}/popup.step1.php?date=[YYYYMMDD]&PA_N_UID={pa_n_uid}"
        else:
            return f"{protocol}://www.{site_url}/_core/module/reservation_boat_{api_version}/popu2.step1.php?date=[YYYYMMDD]&PA_N_UID={pa_n_uid}"
    return ""


def main():
    step2_data = []
    step3_data = []

    for port, providers in PORTS.items():
        for provider_name, script_path in providers.items():
            if not script_path:
                continue

            file_path = os.path.join(BOTS_DIR, script_path)
            info = extract_bot_info(file_path)

            steps_str = info.get("STEPS", "")
            steps_num = int(steps_str.replace("단계", "")) if steps_str else 0

            row = {
                "항구": port,
                "선사명": provider_name,
                "STEP 단계": steps_str,
                "자리선택": info.get("HAS_SEAT_SELECTION", ""),
                "좌석 우선순위": info.get("SEAT_PRIORITY", ""),
                "예약페이지주소": generate_reservation_url(info, steps_num),
                "UID": info.get("PA_N_UID", ""),
            }

            if steps_num == 2:
                step2_data.append(row)
            elif steps_num == 3:
                step3_data.append(row)

    # DataFrame 생성
    df_step2 = pd.DataFrame(step2_data)
    df_step3 = pd.DataFrame(step3_data)

    # 자리선택 기준으로 정렬 (없음 먼저, 있음 나중에) + 항구 + 선사명
    if not df_step2.empty:
        df_step2 = df_step2.sort_values(by=["자리선택", "항구", "선사명"])
    if not df_step3.empty:
        df_step3 = df_step3.sort_values(by=["자리선택", "항구", "선사명"])

    # 엑셀 저장
    output_path = os.path.join(BASE_DIR, "더피싱_봇_정보.xlsx")

    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # STEP2 시트
        if not df_step2.empty:
            df_step2.to_excel(writer, sheet_name='STEP2 (2단계)', index=False)
            worksheet = writer.sheets['STEP2 (2단계)']
            for idx, col in enumerate(df_step2.columns):
                max_length = max(df_step2[col].astype(str).map(len).max(), len(col))
                col_letter = chr(65 + idx) if idx < 26 else 'A' + chr(65 + idx - 26)
                worksheet.column_dimensions[col_letter].width = min(max_length * 1.5 + 2, 100)

        # STEP3 시트
        if not df_step3.empty:
            df_step3.to_excel(writer, sheet_name='STEP3 (3단계)', index=False)
            worksheet = writer.sheets['STEP3 (3단계)']
            for idx, col in enumerate(df_step3.columns):
                max_length = max(df_step3[col].astype(str).map(len).max(), len(col))
                col_letter = chr(65 + idx) if idx < 26 else 'A' + chr(65 + idx - 26)
                worksheet.column_dimensions[col_letter].width = min(max_length * 1.5 + 2, 100)

    print(f"✅ 엑셀 파일 저장 완료: {output_path}")
    print(f"   STEP2: {len(df_step2)}개 선사 (자리선택 없음 → 있음 순)")
    print(f"   STEP3: {len(df_step3)}개 선사 (자리선택 없음 → 있음 순)")


if __name__ == "__main__":
    main()
