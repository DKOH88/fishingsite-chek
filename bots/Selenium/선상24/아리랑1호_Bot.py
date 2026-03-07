# -*- coding: utf-8 -*-
"""
아리랑1호 예약 봇 (선상24)
패턴: 맵핑 있음 + 자리선택 없음
특이사항: 9월 불규칙 매핑
"""

import sys
import json
import argparse
from base_bot import SunSang24BaseBot


class 아리랑1호Bot(SunSang24BaseBot):
    SUBDOMAIN = "arirang"
    PROVIDER_NAME = "아리랑1호"
    HAS_SEAT_SELECTION = False
    USE_DIRECT_MAPPING = True

    # 월별 ID 매핑 (9월은 불규칙)
    ID_MAPPING = {
        4: 1570425,   # 4월 (base_id + day - 1)
        9: {          # 9월 (불규칙)
            1: 1553688, 2: 1570578, 3: 1570579, 4: 1570580, 5: 1570405,
            **{d: 1570580 + (d - 6) for d in range(6, 31)},
        },
        10: 1570606,  # 10월 (base_id + day - 1)
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)

    bot = 아리랑1호Bot(config)
    try:
        bot.run()
    except KeyboardInterrupt:
        bot.stop()
