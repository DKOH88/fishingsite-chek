# -*- coding: utf-8 -*-
"""
만석호 봇 - 3-step + 자리선택
URL: mscufishing.com
"""

from base_bot import BaseFishingBot


class ManseokBot(BaseFishingBot):
    """만석호 예약 봇 (3-step + 자리선택)"""

    # === 필수 설정 ===
    SITE_URL = "mscufishing.com"
    PA_N_UID = "3570"
    PROVIDER_NAME = "만석호"

    # === 예약 타입 설정 ===
    STEPS = 3
    HAS_SEAT_SELECTION = True
    SEAT_PRIORITY = ['1', '15', '2', '9', '8', '10', '7', '14', '3', '11', '6', '13', '4', '12', '5']

    # === 선택적 설정 ===
    URL_PATH = "popup.step1.php"  # 3-step은 popup 사용
    # CLICK_STRATEGY = "auto"  # 자동: id_first (자리선택 있음)


# 직접 실행 테스트용
if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)

    bot = ManseokBot(config)
    try:
        bot.run()
    except KeyboardInterrupt:
        bot.stop()
