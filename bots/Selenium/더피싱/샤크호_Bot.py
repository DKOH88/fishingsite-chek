# -*- coding: utf-8 -*-
"""
샤크호 봇 - 2-step, 자리선택 없음
URL: yamujinfishing.com
"""

from base_bot import BaseFishingBot


class SharkHoBot(BaseFishingBot):
    """샤크호 예약 봇 (2-step, 자리선택 없음)"""

    # === 필수 설정 ===
    SITE_URL = "yamujinfishing.com"
    PA_N_UID = "3348"
    PROVIDER_NAME = "샤크호"

    # === 예약 타입 설정 ===
    STEPS = 2
    HAS_SEAT_SELECTION = False

    # === 선택적 설정 ===
    TARGET_KEYWORDS = ['쭈갑', '쭈꾸미&갑오징어', '쭈&갑', '쭈꾸미', '갑오징어', '문어']
    # URL_PATH = ""  # 자동: popu2.step1.php
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

    bot = SharkHoBot(config)
    try:
        bot.run()
    except KeyboardInterrupt:
        bot.stop()
