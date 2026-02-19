# -*- coding: utf-8 -*-
"""
동백호 예약 봇 (선상24)
패턴: 맵핑 없음 + 자리선택 있음
"""

import sys
import json
import argparse
from base_bot import SunSang24BaseBot


class 동백호Bot(SunSang24BaseBot):
    SUBDOMAIN = "dongbaek"
    PROVIDER_NAME = "동백호"
    HAS_SEAT_SELECTION = True
    SEAT_PRIORITY = ['1', '21', '10', '11', '2', '20']


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)

    bot = 동백호Bot(config)
    try:
        bot.run()
    except KeyboardInterrupt:
        bot.stop()
