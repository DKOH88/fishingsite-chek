# -*- coding: utf-8 -*-
"""
팀만수호 봇 - 2-step + 자리선택
URL: teammansu.kr
"""

from base_bot import BaseFishingBot


class TeammansuBot(BaseFishingBot):
    """팀만수호 예약 봇 (2-step + 자리선택)"""

    # === 필수 설정 ===
    SITE_URL = "teammansu.kr"
    PA_N_UID = "2829"
    PROVIDER_NAME = "팀만수호"

    # === 예약 타입 설정 ===
    STEPS = 2
    HAS_SEAT_SELECTION = True
    SEAT_PRIORITY = ['1', '11', '10', '20', '2', '12', '9', '19', '3', '13', '8', '18']

    # === 선택적 설정 (기본값 사용) ===
    # TARGET_KEYWORDS = ['갑오징어', '쭈꾸미', '쭈갑', '쭈꾸미&갑오징어']
    # URL_PATH = ""  # 자동: popu2.step1.php
    # API_VERSION = "v5.2_seat1"
    # CLICK_STRATEGY = "auto"  # 자동: id_first (자리선택 있음)
    USE_HTTPS = True


# 직접 실행 테스트용
if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)

    bot = TeammansuBot(config)
    try:
        bot.run()
    except KeyboardInterrupt:
        bot.stop()
