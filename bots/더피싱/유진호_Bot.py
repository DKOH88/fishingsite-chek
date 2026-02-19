# -*- coding: utf-8 -*-
"""
유진호 봇 - 2-step, 자리선택 없음
URL: eugeneho.kr
"""

from base_bot import BaseFishingBot


class EugenehoBot(BaseFishingBot):
    """유진호 예약 봇 (2-step, 자리선택 없음)"""

    # === 필수 설정 ===
    SITE_URL = "eugeneho.kr"
    PA_N_UID = "1190"
    PROVIDER_NAME = "유진호"

    # === 예약 타입 설정 ===
    STEPS = 2
    HAS_SEAT_SELECTION = False

    # === 선택적 설정 ===
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

    bot = EugenehoBot(config)
    try:
        bot.run()
    except KeyboardInterrupt:
        bot.stop()
