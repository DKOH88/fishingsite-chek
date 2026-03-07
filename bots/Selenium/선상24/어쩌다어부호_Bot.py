# -*- coding: utf-8 -*-
"""
어쩌다어부호 예약 봇 (선상24)
패턴 2: 맵핑 없음 + 자리선택 없음
"""

import sys
import json
import argparse
from base_bot import SunSang24BaseBot


class 어쩌다어부호Bot(SunSang24BaseBot):
    SUBDOMAIN = "fisherman"
    PROVIDER_NAME = "어쩌다어부호"
    HAS_SEAT_SELECTION = False


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)

    bot = 어쩌다어부호Bot(config)
    try:
        bot.run()
    except KeyboardInterrupt:
        bot.stop()
