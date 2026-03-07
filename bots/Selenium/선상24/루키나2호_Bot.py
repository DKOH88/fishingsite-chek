# -*- coding: utf-8 -*-
"""
루키나 2호 예약 봇 (선상24)
패턴 4: 맵핑 없음 + 자리선택 있음
"""

import sys
import json
import argparse
from base_bot import SunSang24BaseBot


class 루키나2호Bot(SunSang24BaseBot):
    SUBDOMAIN = "lukina"
    PROVIDER_NAME = "루키나 2호"
    SHIP_NAME = "루키나 2호"  # 동일 도메인에 루키나호, 루키나2호 있음
    HAS_SEAT_SELECTION = False  # 선상24는 인원 +버튼 방식


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)

    bot = 루키나2호Bot(config)
    try:
        bot.run()
    except KeyboardInterrupt:
        bot.stop()
