# -*- coding: utf-8 -*-
"""
악바리호2 예약 봇 (선상24)
패턴: 맵핑 있음 + 자리선택 없음
특이사항: 복잡한 월별 매핑 (불규칙 ID) - 악바리호와 동일 도메인
"""

import sys
import json
import argparse
from base_bot import SunSang24BaseBot


class 악바리호2Bot(SunSang24BaseBot):
    SUBDOMAIN = "akbari"
    PROVIDER_NAME = "악바리호2"
    SHIP_NAME = "악바리호2"  # 동일 도메인에 악바리호, 악바리호2 있음
    HAS_SEAT_SELECTION = False
    USE_DIRECT_MAPPING = True

    # 복잡한 월별 ID 매핑 (불규칙 패턴) - 악바리호와 동일 구조이나 ID 다름
    ID_MAPPING = {
        4: {  # 4월 (테스트용)
            **{d: 1642093 + (d - 1) for d in range(1, 25)},
            25: 1603844,
            **{d: 1642117 + (d - 26) for d in range(26, 31)},
        },
        9: 1613277,  # 9월 1일~30일: base + (day-1)
        10: {  # 10월 (불규칙)
            1: 1613308, 2: 1613309, 3: 1568379,
            **{d: 1613310 + (d - 4) for d in range(4, 32)},
        },
        11: {  # 11월 (불규칙)
            **{d: 1676331 + (d - 1) for d in range(1, 6)},
            6: 1651830, 7: 1670177,
            **{d: 1676336 + (d - 8) for d in range(8, 20)},
            20: 1670180, 21: 1670179,
            **{d: 1676348 + (d - 22) for d in range(22, 31)},
        },
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)

    bot = 악바리호2Bot(config)
    try:
        bot.run()
    except KeyboardInterrupt:
        bot.stop()
