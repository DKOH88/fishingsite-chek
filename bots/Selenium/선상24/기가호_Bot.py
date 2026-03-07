# -*- coding: utf-8 -*-
"""
기가호 예약 봇 (선상24)
패턴: 맵핑 있음 + 자리선택 없음
특이사항: delta_days 방식 (기준일: 2025-12-19 = 1535125)
"""

import sys
import json
import argparse
from base_bot import SunSang24BaseBot


class 기가호Bot(SunSang24BaseBot):
    SUBDOMAIN = "giga"
    PROVIDER_NAME = "기가호"
    HAS_SEAT_SELECTION = False
    USE_DIRECT_MAPPING = True

    # delta_days 방식 매핑 (기준일: 2025-12-19 = 1535125)
    ID_MAPPING = {
        'base_date': '20251219',
        'base_id': 1535125,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)

    bot = 기가호Bot(config)
    try:
        bot.run()
    except KeyboardInterrupt:
        bot.stop()
