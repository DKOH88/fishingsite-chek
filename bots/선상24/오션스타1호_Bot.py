# -*- coding: utf-8 -*-
"""
오션스타1호 예약 봇 (선상24)
패턴: 맵핑 있음 + 자리선택 없음
"""

import sys
import json
import argparse
from base_bot import SunSang24BaseBot


class 오션스타1호Bot(SunSang24BaseBot):
    SUBDOMAIN = "ysoceanstar"
    PROVIDER_NAME = "오션스타1호"
    HAS_SEAT_SELECTION = False
    USE_DIRECT_MAPPING = True

    # ID 매핑 (일별: 월, 일)
    ID_MAPPING = {
        (2, 9): 1683339,   # 2월 9일
        (7, 9): 1724015,   # 7월 9일
        (7, 10): 1724016,  # 7월 10일
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)

    bot = 오션스타1호Bot(config)
    try:
        bot.run()
    except KeyboardInterrupt:
        bot.stop()
