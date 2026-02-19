# -*- coding: utf-8 -*-
"""
오션스타1호 예약 봇 (선상24)
패턴: 맵핑 없음 + 자리선택 없음
"""

import sys
import json
import argparse
from base_bot import SunSang24BaseBot


class 오션스타1호Bot(SunSang24BaseBot):
    SUBDOMAIN = "ysoceanstar"
    PROVIDER_NAME = "오션스타1호"
    SHIP_NAME = "오션스타1호"  # 동일 도메인에 1호, 2호, 3호 있음
    HAS_SEAT_SELECTION = False
    SEAT_PRIORITY = ['10', '11', '1', '20', '9', '12', '2', '19']


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
