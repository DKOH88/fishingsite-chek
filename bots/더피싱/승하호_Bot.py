# -*- coding: utf-8 -*-
"""
승하호 봇 - 2-step, 자리선택 없음
URL: seungha.kr
"""

from base_bot import BaseFishingBot


class SeunghaBot(BaseFishingBot):
    """승하호 예약 봇 (2-step, 자리선택 없음)"""

    # === 필수 설정 ===
    SITE_URL = "seungha.kr"
    PA_N_UID = "5760"
    PROVIDER_NAME = "승하호"

    # === 예약 타입 설정 ===
    STEPS = 2
    HAS_SEAT_SELECTION = False

    # === 선택적 설정 ===


# 직접 실행 테스트용
if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)

    bot = SeunghaBot(config)
    try:
        bot.run()
    except KeyboardInterrupt:
        bot.stop()
