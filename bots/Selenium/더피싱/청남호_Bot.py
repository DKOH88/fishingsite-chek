# -*- coding: utf-8 -*-
"""
청남호 봇 - 3-step, 자리선택 없음
URL: chungnamho.com
"""

from base_bot import BaseFishingBot


class CheongNamHoBot(BaseFishingBot):
    """청남호 예약 봇 (3-step, 자리선택 없음)"""

    # === 필수 설정 ===
    SITE_URL = "chungnamho.com"
    PA_N_UID = "1441"
    PROVIDER_NAME = "청남호"

    # === 예약 타입 설정 ===
    STEPS = 3
    HAS_SEAT_SELECTION = False

    # === 선택적 설정 ===
    TARGET_KEYWORDS = ['쭈갑', '쭈꾸미&갑오징어', '쭈&갑', '쭈꾸미', '갑오징어', '문어']
    URL_PATH = "popup.step1.php"  # 3-step은 popup 사용
    # CLICK_STRATEGY = "auto"  # 자동: xpath_first (자리선택 없음)


# 직접 실행 테스트용
if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)

    bot = CheongNamHoBot(config)
    try:
        bot.run()
    except KeyboardInterrupt:
        bot.stop()
