# -*- coding: utf-8 -*-
"""
뉴항구호 예약 봇 (선상24)
패턴 2: 맵핑 없음 + 자리선택 없음
"""

import sys
import json
import argparse
from base_bot import SunSang24BaseBot


class 뉴항구호Bot(SunSang24BaseBot):
    SUBDOMAIN = "daebak"
    PROVIDER_NAME = "뉴항구호"
    HAS_SEAT_SELECTION = False


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)

    bot = 뉴항구호Bot(config)
    try:
        bot.run()
    except KeyboardInterrupt:
        bot.stop()
