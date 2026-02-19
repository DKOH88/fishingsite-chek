# -*- coding: utf-8 -*-
"""
샤크호 API 봇 (더피싱)
패턴: 2단계 + 좌석선택 없음
"""
from base_api_bot import TheFishingAPIBot


class 샤크호APIBot(TheFishingAPIBot):
    BASE_URL = "http://www.yamujinfishing.com/_core/module/reservation_boat_v5.2_seat1"
    PA_N_UID = "3348"
    PROVIDER_NAME = "샤크호"
    RESERVATION_TYPE = "2step"  # popu2 방식
    HAS_SEAT_SELECTION = False


if __name__ == "__main__":
    bot = 샤크호APIBot()
    bot.run()
