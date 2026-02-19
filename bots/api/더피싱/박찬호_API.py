# -*- coding: utf-8 -*-
"""
박찬호 API 봇 (더피싱)
패턴: 2단계 + 좌석선택 활성화
"""
from base_api_bot import TheFishingAPIBot


class 박찬호APIBot(TheFishingAPIBot):
    BASE_URL = "http://www.mscufishing.com/_core/module/reservation_boat_v5.2_seat1"
    PA_N_UID = "2950"
    PROVIDER_NAME = "박찬호"
    RESERVATION_TYPE = "3step"
    HAS_SEAT_SELECTION = True

    # 좌석 우선순위
    SEAT_PRIORITY = ['1', '6', '3', '7', '4', '8', '5', '9']


if __name__ == "__main__":
    bot = 박찬호APIBot()
    bot.run()
