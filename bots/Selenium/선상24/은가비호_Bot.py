# -*- coding: utf-8 -*-
"""
은가비호 예약 봇 (선상24)
패턴 3: 맵핑 있음 + 자리선택 있음
특이사항: 9월, 11월은 일별 dict 매핑, 1월/10월은 base_id 방식
"""

import sys
import json
import argparse
from base_bot import SunSang24BaseBot


class 은가비호Bot(SunSang24BaseBot):
    SUBDOMAIN = "eungabi"
    PROVIDER_NAME = "은가비호"
    HAS_SEAT_SELECTION = False  # 선상24는 인원 +버튼 방식
    USE_DIRECT_MAPPING = True

    # 월별 ID 매핑 (복합 방식)
    ID_MAPPING = {
        1: 1486284,   # 1월 10일 기준 (day-10 offset)
        10: 1499428,  # 10월 (base_id + day - 1)
        # 9월과 11월은 일별 dict로 별도 처리
        9: {
            1: 1506258, 2: 1506259, 3: 1506501, 4: 1506502, 5: 1506503,
            6: 1506504, 7: 1506505, 8: 1506506, 9: 1506507, 10: 1506508,
            11: 1506509, 12: 1506510, 13: 1506511, 14: 1506512, 15: 1506513,
            16: 1506514, 17: 1506515, 18: 1506516, 19: 1506517, 20: 1506518,
            21: 1506519, 22: 1506520, 23: 1506521, 24: 1506522, 25: 1506523,
            26: 1506524, 27: 1506525, 28: 1506526, 29: 1506527, 30: 1506528
        },
        11: {
            1: 1634448, 2: 1634449, 3: 1634450, 4: 1634451, 5: 1634452,
            6: 1634453, 7: 1631387, 8: 1634454, 9: 1634455, 10: 1634456,
            11: 1634457, 12: 1634458, 13: 1634459, 14: 1634460, 15: 1634461,
            16: 1634462, 17: 1634463, 18: 1634464, 19: 1634465, 20: 1634466,
            21: 1634467, 22: 1634468, 23: 1634469, 24: 1634470, 25: 1634471,
            26: 1634472, 27: 1634473, 28: 1634474, 29: 1634475, 30: 1634476
        },
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)

    bot = 은가비호Bot(config)
    try:
        bot.run()
    except KeyboardInterrupt:
        bot.stop()
