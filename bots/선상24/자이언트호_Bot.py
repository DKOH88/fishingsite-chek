# -*- coding: utf-8 -*-
"""
자이언트호 예약 봇 (선상24)
패턴: 맵핑 있음 + 자리선택 없음
"""

import sys
import json
import argparse
from base_bot import SunSang24BaseBot


class 자이언트호Bot(SunSang24BaseBot):
    SUBDOMAIN = "rkclgh"
    PROVIDER_NAME = "자이언트호"
    HAS_SEAT_SELECTION = False
    USE_DIRECT_MAPPING = True

    # ID 매핑 (일별: 월, 일)
    ID_MAPPING = {
        (11, 1): 1649858,   # 11월 1일
        (11, 2): 1649859,   # 11월 2일
        (11, 3): 1649860,   # 11월 3일
        (11, 4): 1649861,   # 11월 4일
        (11, 5): 1649862,   # 11월 5일
        (11, 6): 1649863,   # 11월 6일
        (11, 7): 1649864,   # 11월 7일
        (11, 8): 1649865,   # 11월 8일
        (11, 9): 1649866,   # 11월 9일
        (11, 10): 1649867,   # 11월 10일
        (11, 11): 1649868,   # 11월 11일
        (11, 12): 1649869,   # 11월 12일
        (11, 13): 1649870,   # 11월 13일
        (11, 14): 1649871,   # 11월 14일
        (11, 15): 1649872,   # 11월 15일
        (11, 16): 1649873,   # 11월 16일
        (11, 17): 1649874,   # 11월 17일
        (11, 18): 1649875,   # 11월 18일
        (11, 19): 1649876,   # 11월 19일
        (11, 20): 1649877,   # 11월 20일
        (11, 21): 1649878,   # 11월 21일
        (11, 22): 1649879,   # 11월 22일
        (11, 23): 1649880,   # 11월 23일
        (11, 24): 1649881,   # 11월 24일
        (11, 25): 1649882,   # 11월 25일
        (11, 26): 1649883,   # 11월 26일
        (11, 27): 1649884,   # 11월 27일
        (11, 28): 1649885,   # 11월 28일
        (11, 29): 1649886,   # 11월 29일
        (11, 30): 1649887,   # 11월 30일
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)

    bot = 자이언트호Bot(config)
    try:
        bot.run()
    except KeyboardInterrupt:
        bot.stop()
