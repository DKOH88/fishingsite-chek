# -*- coding: utf-8 -*-
"""
E.스마일 예약 봇 (선상24)
패턴 2: 맵핑 없음 + 자리선택 없음
"""

import sys
import json
import argparse
from base_bot import SunSang24BaseBot


class E스마일Bot(SunSang24BaseBot):
    SUBDOMAIN = "esmile"
    PROVIDER_NAME = "E.스마일"
    HAS_SEAT_SELECTION = False


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)

    bot = E스마일Bot(config)
    try:
        bot.run()
    except KeyboardInterrupt:
        bot.stop()
