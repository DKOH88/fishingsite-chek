# -*- coding: utf-8 -*-
"""
제비호 예약 봇 (선상24)
패턴 3: 맵핑 있음 + 자리선택 있음
"""

import sys
import json
import argparse
from base_bot import SunSang24BaseBot


class 제비호Bot(SunSang24BaseBot):
    SUBDOMAIN = "jebi"
    PROVIDER_NAME = "제비호"
    HAS_SEAT_SELECTION = False  # 선상24는 인원 +버튼 방식
    USE_DIRECT_MAPPING = True

    # 월별 ID 매핑
    ID_MAPPING = {
        4: 1622758,   # 4월 (테스트용)
        9: 1640560,   # 9월
        10: 1640590,  # 10월
        11: 1640621,  # 11월
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)

    bot = 제비호Bot(config)
    try:
        bot.run()
    except KeyboardInterrupt:
        bot.stop()
