# -*- coding: utf-8 -*-
"""
조커호 봇 - 2-step + 자리선택 (알파벳+숫자 좌석)
URL: seasidefishing.kr
특이사항: 좌석에 A, B, C, D 알파벳 포함
"""

from base_bot import BaseFishingBot


class JokerhoBot(BaseFishingBot):
    """조커호 예약 봇 (2-step + 자리선택, 알파벳 좌석)"""

    # === 필수 설정 ===
    SITE_URL = "seasidefishing.kr"
    PA_N_UID = "106"
    PROVIDER_NAME = "조커호"

    # === 예약 타입 설정 ===
    STEPS = 2
    HAS_SEAT_SELECTION = True
    # 숫자 우선, 알파벳 후순위
    SEAT_PRIORITY = [
        '20', '19', '18', '17', '16', '15', '14', '13', '12', '11',
        '10', '9', '8', '7', '6', '5', '4', '3', '2', '1',
        'B', 'A', 'D', 'C'
    ]

    # === 선택적 설정 ===
    # URL_PATH = ""  # 자동: popu2.step1.php
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

    bot = JokerhoBot(config)
    try:
        bot.run()
    except KeyboardInterrupt:
        bot.stop()
